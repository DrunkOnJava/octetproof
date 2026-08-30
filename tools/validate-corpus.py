#!/usr/bin/env python3
"""Validate every committed observation and verdict in the corpus against the
OctetProof 1.1.0 schemas (SPEC.md §6.2, §6.3).

The schemas are additive over 1.0.0 (§16.2): `schema_version` accepts both
`1.0.0` and `1.1.0`, and the `relations` / `storeys` payload keys are optional,
so a document written under either version validates here.

Usage: validate-corpus.py [--corpus corpus] [--schemas schemas]
                          [--extra-observations DIR ...]

Checks, per artifact:

  * observations/*.json against schemas/witness-observation.schema.json;
  * verdict.json against schemas/witness-verdict.schema.json;
  * each observation's `observation_hash_sha256` actually equals the
    canonical hash of its own `observation` payload — a committed
    self-inconsistent observation would make every replay meaningless;
  * the verdict's `verdict_hash_sha256` equals the canonical hash of the
    verdict excluding `timestamp` and the hash field itself;
  * each observation's `input_hash_sha256` is one of the manifest's two
    accepted hashes, and its `input_role` matches which one;
  * each observation's `artifact_id` is the manifest's `artifact_id` or its
    `alias`.

`--extra-observations` validates freshly produced observations too, which is
how CI checks that a witness run in the gate emits a conforming document and
not just a hash that happens to match.

Python 3.12 standard library only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from jsonschema_mini import check  # noqa: E402


def canonical_hash(obj) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def validate_observation(path: Path, schema: dict, manifest: dict | None, errors: list[str]) -> None:
    obs = json.loads(path.read_text())
    check(obs, schema, path.name, errors)

    recomputed = canonical_hash(obs.get("observation"))
    if recomputed != obs.get("observation_hash_sha256"):
        errors.append(
            f"{path.name}: observation_hash_sha256 is {obs.get('observation_hash_sha256')}, "
            f"canonical payload hashes to {recomputed}"
        )

    if manifest is None:
        return
    accepted = {
        manifest.get("source", {}).get("source_hash_sha256"): "source",
        manifest.get("bridge", {}).get("file_hash_sha256"): "bridge",
    }
    accepted.pop(None, None)
    role = accepted.get(obs.get("input_hash_sha256"))
    if role is None:
        errors.append(f"{path.name}: input_hash_sha256 matches neither manifest hash")
    elif role != obs.get("input_role"):
        errors.append(f"{path.name}: input_role is {obs.get('input_role')!r} but that hash is the {role}")
    ids = {manifest.get("artifact_id"), manifest.get("alias")}
    ids.discard(None)
    if obs.get("artifact_id") not in ids:
        errors.append(f"{path.name}: artifact_id {obs.get('artifact_id')!r} is not one of {sorted(ids)}")


def validate_verdict(path: Path, schema: dict, errors: list[str]) -> None:
    verdict = json.loads(path.read_text())
    check(verdict, schema, path.name, errors)
    recomputed = canonical_hash(
        {k: v for k, v in verdict.items() if k not in ("timestamp", "verdict_hash_sha256")}
    )
    # The producer hashes the verdict before inserting the hash field, so the
    # committed value is over everything except `timestamp` and itself.
    if recomputed != verdict.get("verdict_hash_sha256"):
        errors.append(
            f"{path.name}: verdict_hash_sha256 is {verdict.get('verdict_hash_sha256')}, "
            f"canonical verdict hashes to {recomputed}"
        )


def main() -> int:
    here = Path(__file__).resolve().parent.parent
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--corpus", type=Path, default=here / "corpus")
    ap.add_argument("--schemas", type=Path, default=here / "schemas")
    ap.add_argument("--extra-observations", type=Path, action="append", default=[])
    args = ap.parse_args()

    obs_schema = json.loads((args.schemas / "witness-observation.schema.json").read_text())
    verdict_schema = json.loads((args.schemas / "witness-verdict.schema.json").read_text())

    errors: list[str] = []
    checked_obs = 0
    checked_verdicts = 0

    for manifest_path in sorted((args.corpus / "artifacts").glob("*/manifest.json")):
        manifest = json.loads(manifest_path.read_text())
        artifact_dir = manifest_path.parent
        for obs_path in sorted((artifact_dir / "observations").glob("*.json")):
            validate_observation(obs_path, obs_schema, manifest, errors)
            checked_obs += 1
        verdict_path = artifact_dir / "verdict.json"
        if verdict_path.is_file():
            validate_verdict(verdict_path, verdict_schema, errors)
            checked_verdicts += 1

    for extra in args.extra_observations:
        for obs_path in sorted(Path(extra).glob("*.json")):
            validate_observation(obs_path, obs_schema, None, errors)
            checked_obs += 1

    if errors:
        for e in errors:
            print(f"error: {e}", file=sys.stderr)
        print(f"{len(errors)} corpus problem(s)", file=sys.stderr)
        return 1

    print(f"corpus: {checked_obs} observation(s) and {checked_verdicts} verdict(s) conform to the 1.1.0 schemas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
