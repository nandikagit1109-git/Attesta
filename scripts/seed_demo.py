"""Seed the demo dataset: ./make seed.

Wipes the backend database and rebuilds the canonical demo state (demo
users, 3 real certificate PDFs, 2 on-chain credentials, 1 revoked, 1
tampered copy, 2 projects). Uses the same code path as the UI "Reset demo
data" button so the two can never drift.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"

# Run with the backend's working directory so sqlite:///./attesta.db and
# settings resolve exactly as they do for the API server.
import os  # noqa: E402

os.chdir(BACKEND)
sys.path.insert(0, str(BACKEND))


def main() -> int:
    from app.db import SessionLocal, init_db
    from app.services.demo_seed import reset_demo_data

    init_db()
    db = SessionLocal()
    try:
        summary = reset_demo_data(db)
    finally:
        db.close()

    print("Demo data seeded (Sample data throughout):")
    print(f"  student  {summary['student']['email']}  wallet {summary['student']['wallet']}")
    print(f"  issuer   {summary['issuer']['email']}")
    print(f"  verified credential for hash {summary['verified']['sha256'][:16]}...")
    print(f"  revoked  credential for hash {summary['revoked']['sha256'][:16]}...")
    print(f"  unverified (AI-extracted) hash {summary['unverified']['sha256'][:16]}...")
    print(f"  tampered copy hash {summary['tampered']['sha256'][:16]}...")
    return 0


if __name__ == "__main__":
    sys.exit(main())
