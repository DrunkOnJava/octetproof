#!/usr/bin/env python3
"""Validate registry/witnesses.json against registry/witness-registry.schema.json
and check the cross-references the schema cannot express.

Usage: check-registry.py [--registry PATH] [--schema PATH] [--corpus PATH]

Schema validation uses tools/jsonschema_mini.py — the subset of JSON Schema
this repository's schemas use, implemented in the standard library so the
protocol keeps its "Python 3.12 stdlib plus the witness" dependency budget.

Beyond the schema, three invariants:

  * every `witnesses[].node`, `witnesses[].lineage`, `artifacts[].node`,
    `artifacts[].via`, `edges[].from|to|via`, `agreements[].edge` and
    `agreements[].witnesses[]` resolves to something declared here;
  * every corpus manifest's witnesses resolve to registry entries, and every
    `ci-runnable` bridge witness is `adopted`;
  * every corpus manifest's edge is a declared edge.

Python 3.12 standard library only.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from jsonschema_mini import check  # noqa: E402


def main() -> int:
    here = Path(__file__).resolve().parent.parent
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--registry", type=Path, default=here / "registry" / "witnesses.json")
    ap.add_argument("--schema", type=Path, default=here / "registry" / "witness-registry.schema.json")
    ap.add_argument("--corpus", type=Path, default=here / "corpus")
    args = ap.parse_args()

    registry = json.loads(args.registry.read_text())
    schema = json.loads(args.schema.read_text())
    errors: list[str] = []
    check(registry, schema, "registry", errors)

    nodes = {n["id"] for n in registry.get("nodes", [])}
    witnesses = {w["id"]: w for w in registry.get("witnesses", [])}
    edges = {e["id"] for e in registry.get("edges", [])}

    for w in registry.get("witnesses", []):
        if w["node"] not in nodes:
            errors.append(f"witness {w['id']}: node {w['node']!r} is not declared")
        lineage = w.get("lineage")
        if lineage and lineage not in witnesses:
            errors.append(f"witness {w['id']}: lineage {lineage!r} is not a declared witness")
    for a in registry.get("artifacts", []):
        if a["node"] not in nodes:
            errors.append(f"artifact {a['id']}: node {a['node']!r} is not declared")
        if a.get("via") and a["via"] not in witnesses:
            errors.append(f"artifact {a['id']}: via {a['via']!r} is not a declared witness")
    for e in registry.get("edges", []):
        for side in ("from", "to"):
            if e[side] not in nodes:
                errors.append(f"edge {e['id']}: {side} {e[side]!r} is not a declared node")
        if e["via"] not in witnesses:
            errors.append(f"edge {e['id']}: via {e['via']!r} is not a declared witness")
    for g in registry.get("agreements", []):
        if g.get("edge") and g["edge"] not in edges:
            errors.append(f"agreement {g['id']}: edge {g['edge']!r} is not declared")
        for wid in g.get("witnesses", []):
            if wid not in witnesses:
                errors.append(f"agreement {g['id']}: witness {wid!r} is not declared")

    artifacts_dir = args.corpus / "artifacts"
    manifests = sorted(artifacts_dir.glob("*/manifest.json")) if artifacts_dir.is_dir() else []
    for manifest_path in manifests:
        manifest = json.loads(manifest_path.read_text())
        label = manifest.get("artifact_id", manifest_path.parent.name)
        claimed = [manifest["witnesses"]["source"]] + list(manifest["witnesses"]["bridge"])
        for w in claimed:
            wid = w["witness_id"]
            entry = witnesses.get(wid)
            if entry is None:
                errors.append(f"{label}: witness {wid!r} is not in the registry")
                continue
            if w.get("mode") == "ci-runnable" and entry.get("status") != "adopted":
                errors.append(f"{label}: {wid} is ci-runnable but registry status is {entry.get('status')!r}")
            declared_status = w.get("registry_status")
            if declared_status and declared_status != entry.get("status"):
                errors.append(
                    f"{label}: {wid} manifest says registry_status {declared_status!r}, "
                    f"registry says {entry.get('status')!r}"
                )
        authoring = manifest.get("bridge", {}).get("authoring_witness")
        if authoring and authoring not in witnesses:
            errors.append(f"{label}: authoring_witness {authoring!r} is not in the registry")
        edge_id = manifest.get("edge", {}).get("id")
        if edge_id and edge_id not in edges:
            errors.append(f"{label}: edge {edge_id!r} is not in the registry")

    if errors:
        for e in errors:
            print(f"error: {e}", file=sys.stderr)
        print(f"{len(errors)} registry problem(s)", file=sys.stderr)
        return 1

    print(
        f"{args.registry.name}: valid — {len(nodes)} nodes, {len(witnesses)} witnesses, "
        f"{len(registry.get('artifacts', []))} artifacts, {len(edges)} edges, "
        f"{len(registry.get('agreements', []))} agreements; "
        f"{len(manifests)} corpus manifest(s) resolve"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
