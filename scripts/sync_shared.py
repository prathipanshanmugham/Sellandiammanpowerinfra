"""Copies the calculator definitions and constants from the backend to the frontend (they must stay identical),
then rewrites the parity cases. Run after editing backend/calc/tools.json or constants.json:
    python scripts/sync_shared.py && (cd frontend && npm run test:calc)"""
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for name in ("tools.json", "constants.json"):
    shutil.copyfile(ROOT / "backend" / "calc" / name, ROOT / "frontend" / "src" / "shared" / name)
    print("copied", name)
subprocess.run([sys.executable, str(ROOT / "backend" / "tests" / "make_calc_cases.py")], check=True)
