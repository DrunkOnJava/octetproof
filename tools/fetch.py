#!/usr/bin/env python3
"""Fetch a golden artifact's file by its public origin URL and verify it
against the hash the manifest names (SPEC.md §6.1, §8.4).

Usage: fetch.py <manifest.json> --which bridge|source --out PATH [--force]

The corpus never redistributes the bridge or source bytes. It records their
SHA-256, byte length, licence and origin; this tool is the fetch half of the
replay protocol. A byte that does not hash to the recorded value is not the
golden artifact, and this exits non-zero.

If PATH already exists and hashes correctly it is reused (no network).

Python 3.12 standard library only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

USER_AGENT = "octetproof-fetch/1.0 (+https://github.com/DrunkOnJava/octetproof)"


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("manifest", type=Path)
    ap.add_argument("--which", choices=("bridge", "source"), default="bridge")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--force", action="store_true", help="re-download even if a correct copy exists")
    args = ap.parse_args()

    manifest = json.loads(args.manifest.read_text())
    section = manifest.get(args.which, {})
    origin = section.get("origin")
    expected = section.get("file_hash_sha256") or section.get("source_hash_sha256")
    expected_bytes = section.get("bytes")
    if not origin or not expected:
        print(f"error: manifest {args.which} has no origin/hash", file=sys.stderr)
        return 1

    if args.out.is_file() and not args.force:
        have = sha256_of(args.out)
        if have == expected:
            print(f"{args.which}: cached {args.out} sha256 {have[:12]}… ok")
            return 0
        print(f"{args.which}: cached copy hashes {have[:12]}… — re-fetching", file=sys.stderr)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    print(f"{args.which}: fetching {origin}")
    request = urllib.request.Request(origin, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=120) as response, args.out.open("wb") as fh:
        while chunk := response.read(1 << 20):
            fh.write(chunk)

    actual = sha256_of(args.out)
    actual_bytes = args.out.stat().st_size
    if actual != expected:
        print(f"error: {args.out.name} sha256 {actual} != manifest {expected}", file=sys.stderr)
        return 1
    if expected_bytes and actual_bytes != expected_bytes:
        print(f"error: {args.out.name} is {actual_bytes} bytes, manifest says {expected_bytes}", file=sys.stderr)
        return 1
    print(f"{args.which}: {args.out} {actual_bytes} bytes sha256 {actual[:12]}… ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
