#!/usr/bin/env python3
"""Bridge witness: IfcOpenShell reads the golden bridge file and emits an
OctetProof observation (SPEC.md §6.2).

Usage: witness-ifcopenshell.py <manifest.json> <bridge_file>
                               --observation observations/ifcopenshell.json

The manifest (§6.1) is the only source of truth for what is counted: every
`counts` category carrying a `source_ifc_type` is counted, whatever its
status. Excluded (`known_gap` / `unsupported`) types are counted and recorded
too — the verdict tool is what refuses to diff them (§7.1 rule 3), not the
witness. A witness that silently dropped them would make the exclusion
unauditable.

The bridge file's SHA-256 must equal `bridge.file_hash_sha256` (a golden
artifact is the exact bytes the manifest names) and its schema must equal
`bridge.schema`.

Counts use `by_type(..., include_subtypes=False)` — exact type, no subtypes.
The payload is canonicalised (sorted keys, no whitespace, UTF-8) and hashed
so a replay can prove the witness saw the same thing.

Dependencies: Python 3.12 standard library + ifcopenshell (>=0.8,<0.9).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import ifcopenshell


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def entity_types(manifest: dict) -> list[str]:
    types: list[str] = []
    for spec in manifest.get("counts", {}).values():
        ifc_type = spec.get("source_ifc_type")
        if ifc_type and ifc_type not in types:
            types.append(ifc_type)
    return types


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("manifest", type=Path)
    ap.add_argument("bridge_file", type=Path)
    ap.add_argument("--observation", type=Path, required=True)
    args = ap.parse_args()

    manifest = json.loads(args.manifest.read_text())
    bridge = manifest.get("bridge", {})

    if not args.bridge_file.is_file():
        print(f"error: bridge file missing at {args.bridge_file}", file=sys.stderr)
        return 1

    expected_sha = bridge.get("file_hash_sha256")
    actual_sha = sha256_of(args.bridge_file)
    if expected_sha and actual_sha != expected_sha:
        print(f"error: {args.bridge_file.name} sha256 {actual_sha} != manifest {expected_sha}", file=sys.stderr)
        return 1
    expected_bytes = bridge.get("bytes")
    actual_bytes = args.bridge_file.stat().st_size
    if expected_bytes and actual_bytes != expected_bytes:
        print(f"error: {args.bridge_file.name} is {actual_bytes} bytes, manifest says {expected_bytes}", file=sys.stderr)
        return 1

    model = ifcopenshell.open(str(args.bridge_file))
    expected_schema = bridge.get("schema")
    if expected_schema and model.schema != expected_schema:
        print(f"error: schema {model.schema} != manifest {expected_schema}", file=sys.stderr)
        return 1

    types = entity_types(manifest)
    if not types:
        print("error: no manifest count category carries source_ifc_type — nothing to witness", file=sys.stderr)
        return 1

    counts: dict[str, int] = {}
    for ifc_type in types:
        try:
            counts[ifc_type] = len(model.by_type(ifc_type, include_subtypes=False))
        except RuntimeError:
            counts[ifc_type] = 0  # type absent from this schema → zero instances

    payload = {"entity_counts": counts, "ifc_schema": model.schema}
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

    origin = bridge.get("origin") or ""
    input_file = origin.rsplit("/", 1)[-1] or args.bridge_file.name

    observation = {
        "schema_version": "1.0.0",
        "witness_id": "ifcopenshell",
        "witness_version": str(getattr(ifcopenshell, "version", "?")),
        "artifact_id": manifest.get("artifact_id"),
        "input_role": "bridge",
        "input_file": input_file,
        "input_hash_sha256": actual_sha,
        "deterministic": True,
        "semantic_surface_covered": ["entity_counts"],
        "observation": payload,
        "observation_hash_sha256": hashlib.sha256(canonical).hexdigest(),
        "unsupported_entities": [],
        "warnings": [],
    }
    args.observation.parent.mkdir(parents=True, exist_ok=True)
    args.observation.write_text(json.dumps(observation, indent=2, sort_keys=True) + "\n")

    print(f"{manifest.get('artifact_id')}: {input_file} ({model.schema}, sha256 {actual_sha[:12]}…)")
    print(f"{'ifc type':<24} {'count':>6}")
    for ifc_type in types:
        print(f"{ifc_type:<24} {counts[ifc_type]:>6}")
    print(f"observation_hash_sha256: {observation['observation_hash_sha256']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
