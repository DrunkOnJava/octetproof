#!/usr/bin/env python3
"""Bridge witness: IfcOpenShell reads the golden bridge file and emits an
OctetProof observation (SPEC.md §6.2).

Usage: witness-ifcopenshell.py <manifest.json> <bridge_file>
                               --observation observations/ifcopenshell.json

The manifest (§6.1) is the only source of truth for what is read: every
`counts` category carrying a `source_ifc_type` is counted, every `relations`
category carrying a `relation_ifc_type` contributes its pair set and every
`storeys` category carrying a `storey_ifc_type` contributes its storey set,
whatever the category's status. Excluded (`known_gap` / `unsupported` /
`decoder_baseline`) categories are read and recorded too — the verdict tool is
what refuses to diff them (§7.1 rule 3), not the witness. A witness that
silently dropped them would make the exclusion unauditable.

The bridge file's SHA-256 must equal `bridge.file_hash_sha256` (a golden
artifact is the exact bytes the manifest names) and its schema must equal
`bridge.schema`.

Counts use `by_type(..., include_subtypes=False)` — exact type, no subtypes.
Relation pair sets and storey sets are the 1.1.0 field classes (§7.2, §20.1,
§20.2): sorted multisets of two-element string pairs, with a storey elevation
resolved through this model's own declared `LENGTHUNIT` and rendered in feet
at 1e-6 as a fixed six-decimal string. The payload is canonicalised (sorted
keys, no whitespace, UTF-8) and hashed so a replay can prove the witness saw
the same thing.

Dependencies: Python 3.12 standard library + ifcopenshell (>=0.8,<0.9).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import ifcopenshell
import ifcopenshell.util.unit


def fills_element_pairs(model) -> list[list[str]]:
    """`IfcRelFillsElement` host/filling `Tag` pairs, canonically sorted.

    The chain is Revit's own: `IfcRelVoidsElement` binds an opening to the
    element it voids, `IfcRelFillsElement` binds that opening to the element
    that fills it, so the pair `[host Tag, filling Tag]` is the door/window
    to host-wall relation as an IFC reader sees it (SPEC.md §7.2, field class
    *relation pair sets*).

    An unset `Tag`, or an opening with no `IfcRelVoidsElement`, contributes an
    empty string rather than dropping the pair: a missing half must surface as
    a disagreement, never as a silent omission. Duplicates are kept, so the
    value is a sorted multiset.
    """
    voided_by = {}
    for rel in model.by_type("IfcRelVoidsElement", include_subtypes=False):
        voided_by[rel.RelatedOpeningElement.id()] = rel.RelatingBuildingElement

    def tag_of(entity) -> str:
        return "" if entity is None else (getattr(entity, "Tag", None) or "")

    pairs = []
    for rel in model.by_type("IfcRelFillsElement", include_subtypes=False):
        host = voided_by.get(rel.RelatingOpeningElement.id())
        pairs.append([tag_of(host), tag_of(rel.RelatedBuildingElement)])
    return sorted(pairs)


RELATION_READERS = {"IFCRELFILLSELEMENT": fills_element_pairs}

#: Metres in one international foot, exactly.
METRES_PER_FOOT = 0.3048


def format_elevation_feet(feet: float) -> str:
    """Render an elevation in feet at 1e-6 ft, as a string.

    A string, not a JSON number, because the canonical form (SPEC.md §7.3) is
    defined over integers and strings only — two runtimes must not be trusted
    to print the same float the same way. `-0` normalises to `0`.
    """
    rendered = f"{feet:.6f}"
    return "0.000000" if rendered == "-0.000000" else rendered


def building_storey_set(model, ifc_type: str) -> list[list[str]]:
    """`IfcBuildingStorey` `[Name, Elevation]` pairs, canonically sorted.

    The elevation is converted from the model's declared `LENGTHUNIT` to feet,
    so the field compares across witnesses whose files declare different units
    — Revit's own export of this corpus declares `FOOT` while rvt-rs writes
    `METRE` (SPEC.md §7.2, field class *storey sets*). An unset `Name` or
    `Elevation` contributes an empty string rather than dropping the storey: a
    missing half must surface as a disagreement, never as a silent omission. A
    model with no resolvable length unit yields an empty set rather than a
    guess — an unmeasured storey is not a measurement.
    """
    scale = ifcopenshell.util.unit.calculate_unit_scale(model)
    if not scale:
        return []
    out = []
    for storey in model.by_type(ifc_type, include_subtypes=False):
        name = storey.Name or ""
        elevation = getattr(storey, "Elevation", None)
        feet = "" if elevation is None else format_elevation_feet(elevation * scale / METRES_PER_FOOT)
        out.append([name, feet])
    return sorted(out)


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

    relations: dict[str, list[list[str]]] = {}
    for category, spec in manifest.get("relations", {}).items():
        relation_type = spec.get("relation_ifc_type")
        if not relation_type:
            continue
        reader = RELATION_READERS.get(relation_type)
        if reader is None:
            print(f"error: {category}: no reader for relation type {relation_type}", file=sys.stderr)
            return 1
        relations[relation_type] = reader(model)

    storeys: dict[str, list[list[str]]] = {}
    for category, spec in manifest.get("storeys", {}).items():
        storey_type = spec.get("storey_ifc_type")
        if not storey_type:
            continue
        if storey_type != "IFCBUILDINGSTOREY":
            print(f"error: {category}: no reader for storey type {storey_type}", file=sys.stderr)
            return 1
        storeys[storey_type] = building_storey_set(model, storey_type)

    payload = {
        "entity_counts": counts,
        "relations": relations,
        "storeys": storeys,
        "ifc_schema": model.schema,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

    origin = bridge.get("origin") or ""
    input_file = origin.rsplit("/", 1)[-1] or args.bridge_file.name

    observation = {
        "schema_version": "1.1.0",
        "witness_id": "ifcopenshell",
        "witness_version": str(getattr(ifcopenshell, "version", "?")),
        "artifact_id": manifest.get("artifact_id"),
        "input_role": "bridge",
        "input_file": input_file,
        "input_hash_sha256": actual_sha,
        "deterministic": True,
        "semantic_surface_covered": ["entity_counts", "relations", "storeys"],
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
    for relation_type, pairs in relations.items():
        print(f"{relation_type:<24} {len(pairs):>6}  pairs")
    for storey_type, pairs in storeys.items():
        print(f"{storey_type:<24} {len(pairs):>6}  storeys")
    print(f"observation_hash_sha256: {observation['observation_hash_sha256']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
