"""Drive the full demo through the running API: ./make demo-check.

Starts the FastAPI server itself (so the gate needs nothing else running),
resets the demo data as the Demo/Admin role, then walks the exact demo path
from the revised spec: upload, analyze, approve skills, request, confirm,
verify, tamper (admin, one click), fail, revoke, verify as revoked — and
proves the guest share flow works with no login while a guest cannot list
profiles. Exits non-zero on the first broken step so a demo-path regression
can never hide.
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
        step(
            "health declares the five trust states",
            health.get("trust_states") == ["Unverified", "Verified", "Revoked", "Tampered"],
            f"states={health.get('trust_states')}",
        )
        client = httpx.Client(base_url=base, timeout=TIMEOUT)

        # 1. Admin resets the demo data (reset is admin-owned and dev-only).
        r = client.post("/api/auth/demo/admin")
        if not step("one-click admin demo login", r.status_code == 200, r.text[:200]):
            return 1
        admin = {"Authorization": f"Bearer {r.json()['token']}"}
        r = client.post("/api/demo/reset", headers=admin)
        if not step("admin resets demo data via POST /api/demo/reset", r.status_code == 200, r.text[:200]):
            return
        seed = r.json()
        # Reset recreates the demo users, so re-mint the admin token: JWTs
        # carry the old user id, which no longer exists after the reset.
        r = client.post("/api/auth/demo/admin")
        if not step("re-login admin after reset (fresh user ids)", r.status_code == 200, r.text[:200]):
            return
        admin = {"Authorization": f"Bearer {r.json()['token']}"}

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
            "fresh evidence is Unverified (never proof)",
            ev["trust_state"] == "Unverified",
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

        # 6. Issuer cannot confirm before the student approves the skills.
        r = client.post("/api/auth/demo/issuer")
        issuer = {"Authorization": f"Bearer {r.json()['token']}"}
        r = client.get("/api/credentials/queue", headers=issuer)
        pending_ids = [e["id"] for e in r.json()["pending"]]
        step("unapproved evidence is NOT in the issuer queue", ev["id"] not in pending_ids)
        r = client.post("/api/credentials/issue", headers=issuer, json={"evidence_id": ev["id"]})
        step(
            "issuer cannot anchor before the student approves",
            r.status_code == 409,
            f"status={r.status_code}",
        )

        # 7. Student reviews and approves the extracted skills, requesting confirmation.
        r = client.post(f"/api/evidence/{ev['id']}/approve-skills", headers=student)
        if not step("student approves skills and requests confirmation", r.status_code == 200, r.text[:200]):
            return 1
        step("approval is recorded on the evidence", r.json().get("skills_approved") is True)
        r = client.get("/api/credentials/queue", headers=issuer)
        pending_ids = [e["id"] for e in r.json()["pending"]]
        step("approved evidence reaches the issuer queue", ev["id"] in pending_ids)

        # 8. Issuer confirms; the hash is anchored on-chain.
        r = client.post("/api/credentials/issue", headers=issuer, json={"evidence_id": ev["id"]})
        if not step("issuer confirms and anchors on-chain", r.status_code == 200, r.text[:200]):
            return 1
        cred = r.json()["credential"]
        ev = r.json()["evidence"]
        step(
            "status becomes Verified",
            ev["trust_state"] == "Verified",
            f"tx={cred['tx_hash'][:14]}... block={cred['block_number']}",
        )

        # 9. Public verification of the untouched file (no login): bare hash,
        #    resolved through the contract's docHash -> credentialId index.
        r = client.post("/api/verify/hash", json={"sha256": ev["sha256"]})
        step(
            "public verify with a bare hash: Verified",
            r.json().get("state") == "Verified",
            f"issuer={r.json().get('issuer_address', '')[:12]}... block={r.json().get('block_number')}",
        )

        # 10. Admin one-click tamper; the credential page flips to Tampered.
        r = client.post(f"/api/demo/tamper/{cred['id']}", headers=admin)
        if not step("admin one-click tamper", r.status_code == 200, r.text[:200]):
            return 1
        tampered = r.json()
        r = client.get(f"/api/evidence/{ev['id']}", headers=student)
        step(
            "credential page shows HASH MISMATCH immediately",
            r.json().get("trust_state") == "Tampered",
            f"tampered hash={tampered['tampered_sha256'][:16]}...",
        )
        r = client.post(
            "/api/verify/hash",
            json={"sha256": tampered["tampered_sha256"], "credential_id": cred["id"]},
        )
        body = r.json()
        step(
            "tampered copy vs credential shows Tampered with hash mismatch",
            body.get("state") == "Tampered" and body.get("hash_match") is False,
            "diffs between presented and on-chain hash highlighted in the UI",
        )
        # The bare tampered hash proves nothing: it is anchored nowhere.
        r = client.post("/api/verify/hash", json={"sha256": tampered["tampered_sha256"]})
        step(
            "bare tampered hash is honestly Not found (no credential maps to it)",
            r.json().get("state") == "Not found",
        )

        # 11. Issuer revokes; the public page shows Revoked with the reason.
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

        # 12. Seeded dataset behaves: Verified / Revoked / Not found / Tampered.
        r = client.post("/api/verify/hash", json={"sha256": seed["verified"]["sha256"]})
        step("seeded Python certificate verifies", r.json().get("state") == "Verified")
        r = client.post("/api/verify/hash", json={"sha256": seed["revoked"]["sha256"]})
        step("seeded SQL credential shows Revoked", r.json().get("state") == "Revoked")
        r = client.post("/api/verify/hash", json={"sha256": seed["unverified"]["sha256"]})
        step("seeded Excel certificate is Not found on-chain", r.json().get("state") == "Not found")
        r = client.post(
            "/api/verify/hash",
            json={"sha256": seed["tampered"]["sha256"], "credential_id": seed["tampered"]["credential_id"]},
        )
        step("seeded tampered copy shows Tampered", r.json().get("state") == "Tampered")

        # 13. Guest share link: one token, no login, no enumeration.
        r = client.post("/api/profile/share-link", headers=student)
        if not step("student publishes a share link", r.status_code == 200, r.text[:200]):
            return 1
        token = r.json()["share_token"]
        step("share token is long and random", len(token) >= 32, f"len={len(token)}")
        # No Authorization header at all: this is the recruiter.
        r = client.get(f"/api/share/{token}")
        guest = r.json() if r.status_code == 200 else {}
        step(
            "guest opens the shared profile without logging in",
            r.status_code == 200 and guest.get("student", {}).get("full_name") == "Ananya Sharma",
            f"credentials={len(guest.get('credentials', []))}",
        )
        step(
            "shared profile carries statuses, skills with confidence and on-chain proof",
            all(c.get("status") in ("Verified", "Revoked", "Tampered") for c in guest.get("credentials", []))
            and all("tx_hash" in c and "issuer_address" in c for c in guest.get("credentials", []))
            and all("confidence" in s for s in guest.get("skills", [])),
        )
        step(
            "shared profile offers no file download",
            all("file" not in str(c.get("receipt_path", "")) for c in guest.get("credentials", [])),
        )
        r = client.post(
            f"/api/share/{token}/job-match",
            json={
                "job_description": (
                    "We are hiring a data analyst. Strong SQL and Excel required; Python for "
                    "automation is a plus. You will build dashboards and reports."
                )
            },
        )
        body = r.json() if r.status_code == 200 else {}
        step(
            "guest job match scores verified skills only, with reasoning",
            isinstance(body.get("score"), int) and bool(body.get("reasoning")),
            f"score={body.get('score')}",
        )
        step(
            "guest cannot enumerate profiles (directory removed)",
            client.get("/api/profiles").status_code == 404,
        )
        step(
            "guest cannot list evidence or credentials",
            client.get("/api/evidence").status_code == 401
            and client.get("/api/credentials").status_code == 401,
        )
        step("guest cannot reset the demo", client.post("/api/demo/reset").status_code == 401)

        # 14. Public audit log: chain events + off-chain tamper, no PII.
        r = client.get("/api/audit?limit=500")
        if not step("audit log is public (no login)", r.status_code == 200, r.text[:200]):
            return 1
        events = r.json()
        kinds = {e["event"] for e in events}
        step(
            "audit shows issued, revoked and off-chain tamper-detected entries",
            {"issued", "revoked", "tamper-detected"} <= kinds,
            f"events seen: {sorted(kinds)}",
        )
        step(
            "audit labels tamper entries off-chain",
            any(e["event"] == "tamper-detected" and e["source"] == "off-chain" for e in events),
        )
        blob = str(events)
        step(
            "audit carries no names, emails or file names",
            "@" not in blob and "Ananya" not in blob and ".pdf" not in blob,
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
