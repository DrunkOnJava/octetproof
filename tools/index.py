#!/usr/bin/env python3
"""Build (or check) corpus/MANIFEST_INDEX.json — the hash chain over the
golden artifact corpus (SPEC.md §12.2).

Usage: index.py [--corpus corpus] [--check]

Each entry records the artifact id, its alias, the path to its manifest, the
SHA-256 of the manifest bytes, the committed verdict's status and hash, and
`prev_hash`: the canonical SHA-256 of the preceding entry. The first entry's
`prev_hash` is null. Altering any historical manifest changes its
`manifest_sha256`, which changes that entry's canonical hash, which
invalidates every `prev_hash` after it.

Not implemented: the Ed25519 chain-root signature §12.2 also requires. The
index carries `"signature": null` and says so; the chain is tamper-evident
against accidental drift and against anyone who cannot also rewrite this
file, but it is not yet cryptographically anchored to a maintainer key.

`--check` recomputes the chain and exits non-zero if the committed
MANIFEST_INDEX.json differs. This is what CI runs.

Python 3.12 standard library only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


def canonical_hash(obj) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def build(corpus: Path) -> dict:
    artifacts_dir = corpus / "artifacts"
    if not artifacts_dir.is_dir():
        raise SystemExit(f"error: {artifacts_dir} does not exist — nothing to chain")
    entries = []
    prev_hash = None
    for artifact_dir in sorted(artifacts_dir.iterdir()):
        manifest_path = artifact_dir / "manifest.json"
        if not manifest_path.is_file():
            continue
        manifest_bytes = manifest_path.read_bytes()
        manifest = json.loads(manifest_bytes)
        verdict_path = artifact_dir / "verdict.json"
        verdict = json.loads(verdict_path.read_text()) if verdict_path.is_file() else {}
        entry = {
            "artifact_id": manifest.get("artifact_id"),
            "alias": manifest.get("alias"),
            "manifest_path": str(manifest_path.relative_to(corpus.parent)),
            "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
            "bridge_sha256": manifest.get("bridge", {}).get("file_hash_sha256"),
            "source_sha256": manifest.get("source", {}).get("source_hash_sha256"),
            "verdict_status": verdict.get("status"),
            "verdict_hash_sha256": verdict.get("verdict_hash_sha256"),
            "prev_hash": prev_hash,
        }
        entries.append(entry)
        prev_hash = canonical_hash(entry)
    return {
        "schema_version": "1.0.0",
        "chain_algorithm": "sha256 over JCS-lite canonical entries (sorted keys, no whitespace, UTF-8)",
        "chain_head": prev_hash,
        "signature": None,
        "signing_status": "not implemented — SPEC.md §12.2 requires an Ed25519 signature over the chain head; no maintainer key is published yet, so this chain is tamper-evident but not cryptographically anchored",
        "artifacts": entries,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--corpus", type=Path, default=Path(__file__).resolve().parent.parent / "corpus")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    index = build(args.corpus)
    if not index["artifacts"]:
        # Fail closed: an empty corpus is a broken checkout, not a valid chain.
        print(f"error: no manifests under {args.corpus / 'artifacts'}", file=sys.stderr)
        return 1
    rendered = json.dumps(index, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    out = args.corpus / "MANIFEST_INDEX.json"

    if args.check:
        if not out.is_file():
            print(f"error: {out} does not exist", file=sys.stderr)
            return 1
        if out.read_text() != rendered:
            print(f"error: {out} is stale — run tools/index.py", file=sys.stderr)
            return 1
        print(f"{out}: chain head {index['chain_head'][:12]}… ok ({len(index['artifacts'])} artifact(s))")
        return 0

    out.write_text(rendered)
    print(f"{out}: {len(index['artifacts'])} artifact(s), chain head {index['chain_head']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
