"""Native, oracle-focused evaluation of the exact ASE 2022 GLITCH artifact."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "artifact"
sys.path.insert(0, str(ARTIFACT / "GLITCH"))
eggs = list((ARTIFACT / "usr/local/lib").rglob("puppetparser-*.egg"))
if not eggs:
    raise ImportError("Extract the official artifact before running the evaluation")
sys.path.insert(0, str(eggs[0]))
