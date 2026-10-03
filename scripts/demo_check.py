"""Drive the full demo through the running API: ./make demo-check.

Starts the FastAPI server itself (so the gate needs nothing else running),
resets the demo data, then walks the exact demo path: upload, analyze,
issue, verify, tamper, fail, revoke, show revoked. Exits non-zero on the
first broken step so a demo-path regression can never hide.
"""

import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"

import os  # noqa: E402

os.chdir(BACKEND)
sys.path.insert(0, str(BACKEND))

import httpx  # noqa: E402

TIMEOUT = httpx.Timeout(600.0)  # first issue starts the chain; give it room

_STEPS: list[tuple[str, bool, str]] = []


def step(name: str, ok: bool, detail: str = "") -> bool:
    _STEPS.append((name, ok, detail))
    mark = "PASS" if ok else "FAIL"
    print(f"[{mark}] {name}" + (f" | {detail}" if detail else ""))
    return ok


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def make_certificate_pdf(title: str) -> bytes:
    from app.services.sample_docs import write_sample_certificate_pdf

    class _S:
        full_name = "Ananya Sharma"

    path, _sha = write_sample_certificate_pdf(_S(), title, "Springfield College", out_dir=None)
    return Path(path).read_bytes()


def main() -> int:
    port = free_port()
    base = f"http://127.0.0.1:{port}"
    server = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
        cwd=BACKEND,
    )
    try:
        # Wait for boot (up to 2 minutes: fresh DB init included).
        healthy = False
        for _ in range(120):
            try:
                r = httpx.get(f"{base}/api/health", timeout=5)
                if r.status_code == 200:
                    healthy = True
                    health = r.json()
                    break
            except Exception:
                time.sleep(1.0)
        if not step("server boots and /api/health responds", healthy):
            return 1
        step(
            "agents run in deterministic fallback (no API key)",
            health.get("llm_mode") == "deterministic-fallback",
            f"llm_mode={health.get('llm_mode')}",
        )
        client = httpx.Client(base_url=base, timeout=TIMEOUT)

        # 1. Reset / seed through the API (same path the UI button uses).
        r = client.post("/api/demo/reset")
        if not step("demo data resets via POST /api/demo/reset", r.status_code == 200, r.text[:200]):
            return 1
        seed = r.json()

        # 2. Student logs in with one click.
        r = client.post("/api/auth/demo/student")
        if not step("one-click student demo login", r.status_code == 200):
            return 1
        student = {"Authorization": f"Bearer {r.json()['token']}"}

        # 3. Upload a real certificate; agents analyze it; state stays unverified.
        pdf = make_certificate_pdf("Python Programming")
        r = client.post(
            "/api/evidence",
            headers=student,
            files={"file": ("python-certificate.pdf", pdf, "application/pdf")},
        )
        if not step("student uploads a certificate", r.status_code == 200, r.text[:200]):
            return 1
        ev = r.json()
        step(
            "fresh evidence is AI-extracted (unverified)",
            ev["trust_state"] == "AI-extracted (unverified)",
            f"trust_state={ev['trust_state']}",
        )
        step(
            "agents extracted fields and skills",
            bool(ev["extracted"].get("student_name")) and bool(ev["skills"]),
            f"student_name={ev['extracted'].get('student_name')}, skills={[s['id'] for s in ev['skills']]}",
        )
        step("agent trace has runs", len(ev.get("agent_runs", [])) >= 2)

        # 4. Skill graph includes the evidence; a project can be added.
        r = client.get("/api/skills/graph", headers=student)
        kinds = {n["kind"] for n in r.json()["nodes"]}
        step("skill graph built from evidence", "evidence" in kinds and "skill" in kinds)
        r = client.post(
            "/api/projects",
            headers=student,
            json={"title": "Demo check project (Sample data)", "description": "added by demo_check", "skills": ["python"]},
        )
        step("student adds a project", r.status_code == 200)

        # 5. Career gap against the default role (data-analyst).
        r = client.get("/api/career/gap", headers=student)
        gap = r.json() if r.status_code == 200 else {}
        step("career gap scores against data-analyst", 0 <= gap.get("score", -1) <= 100, f"score={gap.get('score')}")

        # 6. Issuer approves; the hash is anchored on-chain.
        r = client.post("/api/auth/demo/issuer")
        issuer = {"Authorization": f"Bearer {r.json()['token']}"}
        r = client.get("/api/credentials/queue", headers=issuer)
        pending_ids = [e["id"] for e in r.json()["pending"]]
        step("issuer sees the upload in the queue", ev["id"] in pending_ids)
        r = client.post("/api/credentials/issue", headers=issuer, json={"evidence_id": ev["id"]})
        if not step("issuer issues the credential on-chain", r.status_code == 200, r.text[:200]):
            return 1
        cred = r.json()["credential"]
        ev = r.json()["evidence"]
        step(
            "status becomes Issuer-verified",
            ev["trust_state"] == "Issuer-verified",
            f"tx={cred['tx_hash'][:14]}... block={cred['block_number']}",
        )

        # 7. Public verification of the untouched file.
        r = client.post("/api/verify/hash", json={"sha256": ev["sha256"]})
        step(
            "public verify: Issuer-verified",
            r.json().get("state") == "Issuer-verified",
            f"issuer={r.json().get('issuer_address', '')[:12]}... block={r.json().get('block_number')}",
        )

        # 8. Tamper with the file; verification fails with a hash mismatch.
        r = client.post(f"/api/evidence/{ev['id']}/tamper", headers=student)
        tampered = r.json()["tampered_sha256"]
        # The receipt permalink / QR carries the credential id, exactly as the
        # public verify flow does when checking a copy against a credential.
        r = client.post("/api/verify/hash", json={"sha256": tampered, "credential_id": cred["id"]})
        body = r.json()
        step(
            "tampered file shows Tampered with a hash mismatch",
            body.get("state") == "Tampered" and body.get("hash_match") is False,
            "diffs between presented and on-chain hash highlighted in the UI",
        )

        # 9. Issuer revokes; the public page shows Revoked with the reason.
        r = client.post(
            f"/api/credentials/{cred['id']}/revoke",
            headers=issuer,
            json={"reason": "Demo check: certificate replaced by a corrected copy"},
        )
        step("issuer revokes with a reason", r.status_code == 200)
        r = client.post("/api/verify/hash", json={"sha256": ev["sha256"]})
        body = r.json()
        step(
            "public verify now shows Revoked + reason",
            body.get("state") == "Revoked" and bool(body.get("revoke_reason")),
            f"reason={body.get('revoke_reason')}",
        )

        # 10. Seeded dataset behaves: verified / revoked / unverified / tampered.
        r = client.post("/api/verify/hash", json={"sha256": seed["verified"]["sha256"]})
        step("seeded Python certificate verifies", r.json().get("state") == "Issuer-verified")
        r = client.post("/api/verify/hash", json={"sha256": seed["revoked"]["sha256"]})
        step("seeded SQL credential shows Revoked", r.json().get("state") == "Revoked")
        r = client.post("/api/verify/hash", json={"sha256": seed["unverified"]["sha256"]})
        step("seeded Excel certificate stays Unknown on-chain", r.json().get("state") == "Unknown")
        r = client.post(
            "/api/verify/hash",
            json={"sha256": seed["tampered"]["sha256"], "credential_id": seed["tampered"]["credential_id"]},
        )
        step("seeded tampered copy shows Tampered", r.json().get("state") == "Tampered")

        # 11. Recruiter: directory + verified-only job match.
        r = client.post("/api/auth/demo/recruiter")
        recruiter = {"Authorization": f"Bearer {r.json()['token']}"}
        r = client.get("/api/profiles", headers=recruiter)
        step("recruiter searches the candidate directory", any(
            e.get("full_name") == "Ananya Sharma" for e in r.json()
        ))
        r = client.post(
            "/api/career/job-match",
            headers=recruiter,
            json={
                "job_description": (
                    "We are hiring a data analyst. Strong SQL and Excel required; Python for "
                    "automation is a plus. You will build dashboards and reports."
                ),
                "role_hint": "data-analyst",
                "candidate_id": seed["student"]["id"],
            },
        )
        body = r.json() if r.status_code == 200 else {}
        step(
            "job match scores from verified skills with reasoning",
            isinstance(body.get("score"), int) and bool(body.get("reasoning")),
            f"score={body.get('score')}",
        )

        # 12. Audit log captured the trail.
        r = client.get("/api/audit?limit=500", headers=recruiter)
        actions = {row["action"] for row in r.json()}
        step(
            "audit log records issue, revoke, verify and agent runs",
            {"ISSUE", "REVOKE", "VERIFY", "AGENT_RUN"} <= actions,
            f"actions seen: {sorted(actions)[:8]}",
        )

        failed = [name for name, ok, _ in _STEPS if not ok]
        print()
        if failed:
            print(f"DEMO CHECK FAILED ({len(failed)} step(s))")
            return 1
        print(f"DEMO CHECK PASSED ({len(_STEPS)} steps)")
        return 0
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()


if __name__ == "__main__":
    sys.exit(main())
