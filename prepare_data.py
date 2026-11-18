"""Restore original benchmark files that are intentionally not published here.

The archived oracle includes a historical private key in one Chef sample.
Its source file is excluded from Git; the exact original can be restored from
the authors' checksum-verified public artifact for local static evaluation.
"""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
SAMPLE = ROOT / "artifact/RESULTS/chef/oracle-dataset/recipes/chef-boneyard_qa-chef-server-cluster-attributes-default.rb"


def main():
    if SAMPLE.exists():
        print("Original oracle files are present; no dataset download needed.")
        return
    print("Restoring one excluded oracle sample from the verified author artifact (1.82 GB).", flush=True)
    subprocess.run([sys.executable, str(ROOT / "download_artifact.py")], check=True)
    subprocess.run([sys.executable, str(ROOT / "extract_artifact.py")], check=True)
    if not SAMPLE.exists():
        raise FileNotFoundError("The original oracle sample was not restored")
    print("Oracle restored for local static analysis. Never commit the excluded sample.")


if __name__ == "__main__":
    main()
