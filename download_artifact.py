"""Download and verify the exact ASE 2022 Figshare v2 replication image."""
import hashlib
import json
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent


def main():
    data = ROOT / "data"
    data.mkdir(parents=True, exist_ok=True)
    url = "https://api.figshare.com/v2/articles/19726603/versions/2"
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    metadata = response.json()
    (data / "figshare-metadata.json").write_text(json.dumps(metadata, indent=2))
    entry = metadata["files"][0]
    target = data / entry["name"]
    if not target.exists():
        partial = target.with_suffix(".partial")
        with requests.get(entry["download_url"], stream=True, timeout=(30, 180)) as result:
            result.raise_for_status()
            with partial.open("wb") as stream:
                for block in result.iter_content(4 * 1024 * 1024):
                    stream.write(block)
        if partial.stat().st_size != entry["size"]:
            raise ValueError("Downloaded size differs from Figshare metadata")
        partial.rename(target)
    digests = {"md5": hashlib.md5(), "sha1": hashlib.sha1(), "sha256": hashlib.sha256()}
    with target.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            for digest in digests.values():
                digest.update(block)
    hashes = {key: value.hexdigest() for key, value in digests.items()}
    if hashes["md5"] != entry["computed_md5"]:
        raise ValueError("Artifact MD5 does not match official metadata")
    result = {"doi": metadata["doi"], "metadata_url": url, "download_url": entry["download_url"],
              "bytes": target.stat().st_size, **hashes, "md5_verified": True}
    (data / "artifact-provenance.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    main()
