"""Portable gate runner for Attesta.

Same targets as the Makefile, implemented in the Python stdlib so the gates
run on any laptop (including Windows machines without GNU make). The Makefile
delegates here, so there is exactly one implementation.

Usage: python scripts/make.py <target>   (or ./make <target>)
"""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
BLOCKCHAIN = ROOT / "blockchain"
DATA = ROOT / "data"
CHAIN_CONFIG = DATA / "chain.json"
CHAIN_RPC = os.environ.get("CHAIN_RPC_URL", "http://127.0.0.1:8545")


def venv_python() -> str:
    """Prefer the backend venv (3.11, has all deps); fall back to the current one."""
    exe = "python.exe" if os.name == "nt" else "python"
    cand = BACKEND / ".venv" / ("Scripts" if os.name == "nt" else "bin") / exe
    return str(cand) if cand.exists() else sys.executable


def npm_cmd() -> str:
    found = shutil.which("npm.cmd" if os.name == "nt" else "npm")
    return found or "npm"


def npx_cmd() -> str:
    found = shutil.which("npx.cmd" if os.name == "nt" else "npx")
    return found or "npx"


def run(cmd: list[str], cwd: Path, timeout: int = 300) -> int:
    print(f"$ {' '.join(cmd)}  (cwd={cwd.name or cwd})")
    proc = subprocess.run(cmd, cwd=cwd)
    return proc.returncode


def sh(cmd: str, cwd: Path, timeout: int = 300) -> int:
    return run([cmd], cwd=cwd, timeout=timeout) if os.name != "nt" else _sh_nt(cmd, cwd)


def _sh_nt(cmd: str, cwd: Path) -> int:
    return subprocess.run(["cmd", "/c", cmd], cwd=cwd).returncode


def rpc_alive(url: str, timeout: float = 1.5) -> bool:
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "eth_chainId", "params": []}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status == 200
    except Exception:
        return False


def node_modules_ready(d: Path) -> bool:
    return (d / "node_modules" / ".package-lock.json").exists()


def spawn_detached(cmd: list[str], cwd: Path, log_path: Path) -> subprocess.Popen:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log = open(log_path, "ab")
    kwargs: dict = {}
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    proc = subprocess.Popen(cmd, cwd=cwd, stdout=log, stderr=subprocess.STDOUT, **kwargs)
    print(f"detached: {' '.join(cmd)} (pid={proc.pid}, log={log_path.name})")
    return proc


def ensure_chain() -> int:
    """Start the Hardhat node if needed, then deploy and record the address."""
    if not node_modules_ready(BLOCKCHAIN):
        if install_blockchain() != 0:
            return 1
    if not rpc_alive(CHAIN_RPC):
        print(f"chain not reachable at {CHAIN_RPC}; starting hardhat node...")
        spawn_detached([npx_cmd(), "hardhat", "node"], BLOCKCHAIN, BLOCKCHAIN / "hardhat-node.log")
        for _ in range(60):
            time.sleep(1.5)
            if rpc_alive(CHAIN_RPC):
                break
        else:
            print("FAIL: hardhat node did not come up; see blockchain/hardhat-node.log")
            return 1
        print("chain is up.")
    code = run([npx_cmd(), "hardhat", "run", "scripts/deploy.ts", "--network", "localhost"], BLOCKCHAIN, 300)
    if code == 0 and CHAIN_CONFIG.exists():
        addr = json.loads(CHAIN_CONFIG.read_text()).get("contractAddress")
        print(f"contract deployed at {addr} (written to {CHAIN_CONFIG.relative_to(ROOT)})")
    return code


def install_backend() -> int:
    return run([venv_python(), "-m", "pip", "install", "-e", f".[dev,extraction,chain]"], BACKEND, 900)


def install_frontend() -> int:
    return run([npm_cmd(), "install"], FRONTEND, 900)


def install_blockchain() -> int:
    return run([npm_cmd(), "install"], BLOCKCHAIN, 900)


def install() -> int:
    for step in (install_backend, install_frontend, install_blockchain):
        code = step()
        if code != 0:
            print(f"FAIL: {step.__name__}")
            return code
    print("all dependencies installed.")
    return 0


def test_contracts() -> int:
    if not node_modules_ready(BLOCKCHAIN):
        if install_blockchain() != 0:
            return 1
    if run([npx_cmd(), "hardhat", "compile"], BLOCKCHAIN, 300) != 0:
        return 1
    return run([npx_cmd(), "hardhat", "test"], BLOCKCHAIN, 300)


def test_backend() -> int:
    return run([venv_python(), "-m", "pytest", "-q"], BACKEND, 600)


def test_agents() -> int:
    tests = BACKEND / "tests" / "test_agents.py"
    if not tests.exists():
        print("no agent tests yet (Phase 3 adds them)")
        return 0
    return run([venv_python(), "-m", "pytest", "-q", "tests/test_agents.py"], BACKEND, 600)


def build() -> int:
    if not node_modules_ready(FRONTEND):
        if install_frontend() != 0:
            return 1
    if os.name == "nt":
        return _sh_nt("npm run build", FRONTEND)
    return run([npm_cmd(), "run", "build"], FRONTEND, 600)


def seed() -> int:
    script = ROOT / "scripts" / "seed_demo.py"
    if not script.exists():
        print("scripts/seed_demo.py not built yet (Phase 5)")
        return 0
    return run([venv_python(), str(script)], ROOT, 600)


def demo_check() -> int:
    script = ROOT / "scripts" / "demo_check.py"
    if not script.exists():
        print("scripts/demo_check.py not built yet (Phase 5)")
        return 0
    return run([venv_python(), str(script)], ROOT, 600)


def check() -> int:
    """Phase 5 gate: everything the live demo depends on, in order."""
    for name in (test_backend, test_agents, build, seed, demo_check):
        print(f"=== {name.__name__} ===")
        code = name()
        if code != 0:
            print(f"CHECK FAILED at {name.__name__}")
            return code
    print("CHECK PASSED")
    return 0


def check_all() -> int:
    for name in (test_contracts, test_backend, test_agents, build, seed, demo_check):
        print(f"=== {name.__name__} ===")
        code = name()
        if code != 0:
            print(f"CHECK FAILED at {name.__name__}")
            return code
    print("CHECK-ALL PASSED")
    return 0


def lint() -> int:
    ruff = run([venv_python(), "-m", "ruff", "check", "app", "tests"], BACKEND, 120)
    tsc = run([npx_cmd(), "tsc", "--noEmit"], FRONTEND, 300) if node_modules_ready(FRONTEND) else 0
    return max(ruff, tsc)


TARGETS = {
    "help": None,
    "install": install,
    "install:backend": install_backend,
    "install:frontend": install_frontend,
    "install:blockchain": install_blockchain,
    "chain": ensure_chain,
    "test-contracts": test_contracts,
    "test-backend": test_backend,
    "test-agents": test_agents,
    "build": build,
    "seed": seed,
    "demo-check": demo_check,
    "check": check,
    "check-all": check_all,
    "lint": lint,
}

HELP = """Attesta gate runner (same targets as the Makefile)

  ./make install           install backend (venv), frontend and blockchain deps
  ./make chain             start hardhat node if needed + deploy registry contract
  ./make test-contracts    Phase 1 gate: hardhat compile + contract tests
  ./make test-backend      Phase 2 gate: backend pytest suite
  ./make test-agents       Phase 3 gate: agent tests (pass with no API key)
  ./make build             Phase 4 gate: typecheck + production frontend build
  ./make seed              regenerate demo data (PDFs, users, credentials)
  ./make demo-check        drive the full demo through the API
  ./make check             Phase 5 gate: test-backend, test-agents, build, seed, demo-check
  ./make check-all         everything including contract tests
  ./make lint              ruff + frontend tsc
"""


def main(argv: list[str]) -> int:
    target = argv[1] if len(argv) > 1 else "help"
    if target in ("help", "-h", "--help") or target not in TARGETS:
        print(HELP, file=sys.stderr)
        return 0 if target == "help" else 1
    return TARGETS[target]() or 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
