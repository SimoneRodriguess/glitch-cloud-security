"""Recover selected regular files from Docker layers without running the image.

Apply whiteouts in memory; never extract arbitrary archive paths or symlinks.
Full large-dataset reruns are outside this oracle-focused evaluation.
"""
import hashlib
import json
from pathlib import Path, PurePosixPath
import tarfile

ROOT = Path(__file__).resolve().parent


def wanted(name):
    p = PurePosixPath(name)
    if p.is_absolute() or ".." in p.parts:
        raise ValueError("Unsafe artifact path")
    if ".git" in p.parts:
        return False
    if name == "README":
        return True
    if name.startswith("usr/local/lib/") and path_is_puppet_egg(p):
        return True
    if p.parts and p.parts[0] in ["GLITCH", "puppet-parser"]:
        if any(part in [".mypy_cache", ".pytest_cache", "__pycache__", "build", "dist", "objects", "hooks"] for part in p.parts):
            return False
        return p.suffix in [".py", ".ini", ".txt", ".md", ".template", ".rb"] or p.name in ["LICENSE", "HEAD", "main", "master", "PKG-INFO"]
    if len(p.parts) >= 3 and p.parts[0] == "RESULTS":
        return p.parts[2] in ["oracle-dataset", "oracle-dataset-analysis"] or p.name == "README.md" or p.name == "dump-dataset-stats.py"
    return False


def path_is_puppet_egg(path):
    return path.name.startswith("puppetparser-") and path.suffix == ".egg"


def main():
    files, versions = {}, {}
    with tarfile.open(ROOT / "data/glitch-latest.tar") as outer:
        manifest = json.load(outer.extractfile("manifest.json"))[0]
        config = json.load(outer.extractfile(manifest["Config"]))
        for layer in manifest["Layers"]:
            print("Reading", layer, flush=True)
            with tarfile.open(fileobj=outer.extractfile(layer), mode="r|*") as archive:
                for entry in archive:
                    name = entry.name.removeprefix("./")
                    path = PurePosixPath(name)
                    if path.name.startswith(".wh."):
                        parent = str(path.parent)
                        if path.name == ".wh..wh..opq":
                            remove = [n for n in files if n.startswith(parent + "/")]
                        else:
                            target = str(path.parent / path.name[4:])
                            remove = [n for n in files if n == target or n.startswith(target + "/")]
                        for key in remove:
                            del files[key]
                    elif entry.isfile() and wanted(name):
                        files[name] = archive.extractfile(entry).read()
                    elif entry.isfile() and name.endswith(".dist-info/METADATA"):
                        text = archive.extractfile(entry).read().decode(errors="replace")
                        name_line = next((s[6:] for s in text.splitlines() if s.startswith("Name: ")), "")
                        version = next((s[9:] for s in text.splitlines() if s.startswith("Version: ")), "")
                        versions[name_line] = version
    destination = ROOT / "artifact"
    records = []
    for name, content in sorted(files.items()):
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        records.append({"path": name, "bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()})
    (ROOT / "data/extracted-manifest.json").write_text(json.dumps({"files": records, "container_architecture": config["architecture"], "container_created": config["created"], "container_packages": versions}, indent=2))
    print("Extracted", len(files), "regular files; original source, oracle data and annotations retained.", flush=True)


if __name__ == "__main__":
    main()
