#!/usr/bin/env python3
"""Validate registry/witnesses.json against registry/witness-registry.schema.json
and check the cross-references the schema cannot express.

Usage: check-registry.py [--registry PATH] [--schema PATH] [--corpus PATH]

Schema validation uses tools/jsonschema_mini.py — the subset of JSON Schema
this repository's schemas use, implemented in the standard library so the
protocol keeps its "Python 3.12 stdlib plus the witness" dependency budget.

Beyond the schema, four invariants:

  * every `witnesses[].node`, `witnesses[].lineage`, `artifacts[].node`,
    `artifacts[].via`, `edges[].from|to|via`, `agreements[].edge` and
    `agreements[].witnesses[]` resolves to something declared here;
  * every corpus manifest's witnesses resolve to registry entries, and every
    `ci-runnable` bridge witness is `adopted`;
  * every corpus manifest's edge is a declared edge;
  * §9.6 version pinning holds mechanically for every witness the umbrella
    builds itself: for a bridge witness with `runner_kind: "cargo"`, the
    registry's `version`, the exact `crate = "=X.Y.Z"` pin in the runner's
    Cargo.toml, the manifest's `version_pin` string and the `WITNESS_VERSION`
    (and `WITNESS_ID`) constants the binary stamps into every observation must
    all agree. This mirrors rvt-rs's
    `tests/witness_registry.rs::ifc_lite_gate_is_wired_and_version_pinned`,
    which the umbrella cannot import because it has no Rust test harness.

Python 3.12 standard library only.
"""

from __future__ import annotations

import argparse
import json
import sys
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from jsonschema_mini import check  # noqa: E402


def check_cargo_pin(root: Path, label: str, witness: dict, entry: dict, errors: list[str]) -> None:
    """§9.6: the Cargo pin, the registry version, the manifest pin string and
    the binary's own WITNESS_VERSION must be one number, not four."""
    wid = witness["witness_id"]
    runner = root / witness["runner"]
    crate = entry.get("crate")
    version = entry.get("version")
    if not crate or not version:
        errors.append(f"{label}: {wid} is a cargo witness but the registry entry has no crate/version")
        return

    cargo_toml = runner / "Cargo.toml"
    if not cargo_toml.is_file():
        errors.append(f"{label}: {wid} runner {witness['runner']} has no Cargo.toml")
        return
    cargo = tomllib.loads(cargo_toml.read_text())
    pinned = cargo.get("dependencies", {}).get(crate)
    if isinstance(pinned, dict):
        pinned = pinned.get("version")
    if pinned != f"={version}":
        errors.append(
            f"{label}: {wid} Cargo.toml pins {crate} = {pinned!r}, registry says version {version!r} "
            f"(expected \"={version}\")"
        )
    if not (runner / "Cargo.lock").is_file():
        errors.append(f"{label}: {wid} has no committed Cargo.lock — transitive deps are unpinned")

    expected_pin = f'{crate} = "={version}"'
    if witness.get("version_pin") != expected_pin:
        errors.append(
            f"{label}: {wid} manifest version_pin is {witness.get('version_pin')!r}, expected {expected_pin!r}"
        )

    main_rs = runner / "src" / "main.rs"
    if not main_rs.is_file():
        errors.append(f"{label}: {wid} runner has no src/main.rs")
        return
    source = main_rs.read_text()
    for const, value in (("WITNESS_ID", wid), ("WITNESS_VERSION", version)):
        needle = f'const {const}: &str = "{value}";'
        if needle not in source:
            errors.append(f"{label}: {wid} src/main.rs does not declare `{needle}`")


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
            if w.get("mode") == "ci-runnable" and w.get("runner_kind") == "cargo":
                check_cargo_pin(here, label, w, entry, errors)
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
