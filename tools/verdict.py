#!/usr/bin/env python3
"""OctetProof verdict: compare independent witness observations of one golden
artifact and emit verdict.json (SPEC.md 1.0.0 §6.3, §7, §9.3, §10.5).

Usage: verdict.py <manifest.json> <observations_dir> --out verdict.json
                  [--registry registry/witnesses.json]
                  [--compare-committed DIR] [--timestamp ISO8601]

Every `observations/*.json` is an observation in the §6.2 shape. Unlike the
in-decoder ancestor (`tools/ci/witness-verdict.py` in rvt-rs) this tool is
generalised: the claimed semantic surface, the per-category tolerances and the
first-class exclusions all come from the umbrella `manifest.json` (§6.1),
never from a decoder's test fixture, and the manifest also names the accepted
input hashes and the origins the bytes are fetched from. The umbrella never
parses a byte of any binary format.

The manifest's `counts` block is normative (§6.1): a category carrying
`source_ifc_type` with status `known` puts `entity_counts.<TYPE>` inside the
surface; status `known_gap` or `unsupported` excludes it first-class (§7.1
rule 3) and records it in the verdict with its tracking issue, never diffed.
The manifest's declared `semantic_surface` and `excluded` are cross-checked
against what `counts` implies; a mismatch is a MANIFEST_ERROR, so an
accidental status flip cannot silently shrink the surface.

Fail-closed (§5.4, §10.5): fewer than two observations →
INSUFFICIENT_WITNESSES; any diff inside the surface → DISAGREE; an
observation whose `input_hash_sha256` matches neither the manifest's source
nor bridge hash, or whose `deterministic` flag is not true → REJECTED_INPUT;
an observation that does not declare `entity_counts`, names an artifact the
manifest does not, or names a witness absent from the registry →
MANIFEST_ERROR. With `--registry` the §9.3 independence set is enforced: the
agreeing witnesses must span at least two lineages, include one bridge-format
reader and one source-format reader, must not be a GPL/AGPL-only pair, and
commercial witnesses are dropped from the gate — otherwise
INSUFFICIENT_INDEPENDENT_WITNESSES. Only PASS exits 0.

`--compare-committed DIR` replays §8.4: the canonical hash of each fresh
`observation` payload must equal the hash recorded in the committed
observation of the same witness, else REPLAY_DRIFT.

Canonicalisation is §7.3: sorted keys, no insignificant whitespace, UTF-8,
SHA-256. The payloads in scope carry integers and ASCII strings only, so
RFC 8785's number rules are moot.

Python 3.12 standard library only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

PREFIX = "entity_counts."


def canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def canonical_hash(obj) -> str:
    return hashlib.sha256(canonical(obj)).hexdigest()


def load_observations(directory: Path) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for path in sorted(directory.glob("*.json")):
        data = json.loads(path.read_text())
        wid = data.get("witness_id") or path.stem
        if wid in out:
            raise SystemExit(f"error: duplicate observation for witness {wid}")
        out[wid] = data
    return out


def partition(manifest: dict) -> tuple[list[tuple[str, str, int]], list[dict]]:
    """Split the normative `counts` block into (surface, excluded).

    surface entries are (field, category, tolerance); excluded entries are the
    §6.3 records. Categories without `source_ifc_type` are not part of the
    cross-witness surface at all (§6.1) and are skipped silently.
    """
    surface: list[tuple[str, str, int]] = []
    excluded: list[dict] = []
    for category, spec in manifest.get("counts", {}).items():
        ifc_type = spec.get("source_ifc_type")
        if not ifc_type:
            continue
        field = PREFIX + ifc_type
        if spec.get("status") == "known":
            surface.append((field, category, int(spec.get("tolerance", 0))))
        else:
            excluded.append({
                "field": field,
                "category": category,
                "reason": spec.get("status"),
                "tracking_issue": spec.get("tracking_issue"),
                "unsupported_feature": spec.get("unsupported_feature"),
            })
    return surface, excluded


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("manifest", type=Path)
    ap.add_argument("observations_dir", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--compare-committed", type=Path)
    ap.add_argument("--registry", type=Path, help="registry/witnesses.json for the §9.3 independence set")
    ap.add_argument("--timestamp", default=None, help="ISO-8601; omitted → deterministic verdict without a timestamp")
    args = ap.parse_args()

    manifest = json.loads(args.manifest.read_text())
    source = manifest.get("source", {})
    bridge = manifest.get("bridge", {})
    accepted_inputs = {
        source.get("source_hash_sha256"): "source",
        bridge.get("file_hash_sha256"): "bridge",
    }
    accepted_inputs.pop(None, None)
    accepted_ids = {manifest.get("artifact_id"), manifest.get("alias")}
    accepted_ids.discard(None)

    observations = load_observations(args.observations_dir)
    verdict = {
        "schema_version": "1.0.0",
        "artifact_id": manifest.get("artifact_id"),
        "status": "PASS",
        "witnesses_compared": sorted(observations),
        "inputs": {},
        "semantic_surface": [],
        "excluded": [],
        "diffs": [],
        "insufficient_witnesses": False,
    }
    if args.timestamp:
        verdict["timestamp"] = args.timestamp

    rejected = []
    for wid, obs in observations.items():
        h = obs.get("input_hash_sha256")
        role = accepted_inputs.get(h)
        verdict["inputs"][wid] = {
            "input_hash_sha256": h,
            "role": role,
            "witness_version": obs.get("witness_version"),
        }
        if role is None:
            rejected.append(wid)
        if obs.get("deterministic") is not True:
            rejected.append(wid)
    if rejected:
        verdict["status"] = "REJECTED_INPUT"
        verdict["rejected"] = sorted(set(rejected))

    for wid, obs in observations.items():
        if "entity_counts" not in (obs.get("semantic_surface_covered") or []):
            verdict["status"] = "MANIFEST_ERROR"
            verdict.setdefault("manifest_errors", []).append(f"{wid} does not declare entity_counts")
        if obs.get("artifact_id") not in accepted_ids:
            verdict["status"] = "MANIFEST_ERROR"
            verdict.setdefault("manifest_errors", []).append(
                f"{wid} observes artifact {obs.get('artifact_id')!r}, not one of {sorted(accepted_ids)}"
            )

    if args.registry:
        registry = {w["id"]: w for w in json.loads(args.registry.read_text())["witnesses"]}
        commercial = [wid for wid in observations if "commercial" in registry.get(wid, {}).get("license", "").lower()]
        for wid in commercial:
            observations.pop(wid)
        gate = {}
        for wid in observations:
            entry = registry.get(wid)
            if entry is None:
                verdict["status"] = "MANIFEST_ERROR"
                verdict.setdefault("manifest_errors", []).append(f"{wid} is not in the registry")
                continue
            gate[wid] = entry
        lineages = {w.get("lineage", wid) for wid, w in gate.items()}
        roles = {verdict["inputs"][wid]["role"] for wid in gate}
        strong_copyleft = [wid for wid, w in gate.items() if w.get("license", "").upper().startswith(("GPL", "AGPL"))]
        independence = {
            "lineages": sorted(lineages),
            "roles": sorted(r for r in roles if r),
            "commercial_dropped": sorted(commercial),
            "strong_copyleft": sorted(strong_copyleft),
            "satisfied": len(lineages) >= 2 and {"bridge", "source"} <= roles and len(strong_copyleft) < len(gate),
        }
        verdict["independence"] = independence
        verdict["witnesses_compared"] = sorted(observations)
        if not independence["satisfied"] and verdict["status"] == "PASS":
            verdict["status"] = "INSUFFICIENT_INDEPENDENT_WITNESSES"

    if len(observations) < 2:
        verdict["status"] = "INSUFFICIENT_WITNESSES"
        verdict["insufficient_witnesses"] = True

    surface, excluded = partition(manifest)
    verdict["excluded"] = excluded

    # The manifest declares its own surface and exclusions as well as the
    # `counts` block they derive from. Disagreement between the two means the
    # manifest is wrong, and §7.1 rule 3 makes that the manifest's fault.
    declared_surface = manifest.get("semantic_surface")
    if declared_surface is not None and declared_surface != [f for f, _, _ in surface]:
        verdict["status"] = "MANIFEST_ERROR"
        verdict.setdefault("manifest_errors", []).append(
            "declared semantic_surface does not match the `known` categories in counts"
        )
    declared_excluded = manifest.get("excluded")
    if declared_excluded is not None and declared_excluded != excluded:
        verdict["status"] = "MANIFEST_ERROR"
        verdict.setdefault("manifest_errors", []).append(
            "declared excluded does not match the non-`known` categories in counts"
        )

    for field, _category, tolerance in surface:
        verdict["semantic_surface"].append(field)
        if verdict["status"] != "PASS":
            continue
        ifc_type = field[len(PREFIX):]
        values = {
            wid: int(obs.get("observation", {}).get("entity_counts", {}).get(ifc_type, 0))
            for wid, obs in observations.items()
        }
        wids = sorted(values)
        for i, a in enumerate(wids):
            for b in wids[i + 1:]:
                if abs(values[a] - values[b]) > tolerance:
                    verdict["diffs"].append({
                        "field": field,
                        "witness_a": a, "value_a": values[a],
                        "witness_b": b, "value_b": values[b],
                        "tolerance_applied": tolerance,
                    })
    if verdict["diffs"] and verdict["status"] == "PASS":
        verdict["status"] = "DISAGREE"

    if args.compare_committed:
        replay = {}
        for wid, obs in observations.items():
            committed_path = args.compare_committed / f"{wid}.json"
            if not committed_path.is_file():
                replay[wid] = "missing"
                continue
            committed = json.loads(committed_path.read_text())
            fresh = canonical_hash(obs.get("observation"))
            committed_hash = committed.get("observation_hash_sha256")
            replay[wid] = "match" if fresh == committed_hash else f"drift (committed {committed_hash}, fresh {fresh})"
        verdict["replay"] = replay
        if any(v != "match" for v in replay.values()) and verdict["status"] == "PASS":
            verdict["status"] = "REPLAY_DRIFT"

    verdict["verdict_hash_sha256"] = canonical_hash({k: v for k, v in verdict.items() if k not in ("timestamp",)})
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(verdict, indent=2, sort_keys=True) + "\n")

    print(f"{verdict['artifact_id']}: {verdict['status']} — witnesses {', '.join(verdict['witnesses_compared'])}")
    print(f"  surface: {len(verdict['semantic_surface'])} fields, "
          f"excluded: {len(verdict['excluded'])}, diffs: {len(verdict['diffs'])}")
    for d in verdict["diffs"]:
        print(f"  DISAGREE {d['field']}: {d['witness_a']}={d['value_a']} vs {d['witness_b']}={d['value_b']}")
    for wid, r in verdict.get("replay", {}).items():
        print(f"  replay {wid}: {r}")
    for m in verdict.get("manifest_errors", []):
        print(f"  MANIFEST_ERROR {m}", file=sys.stderr)
    return 0 if verdict["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
