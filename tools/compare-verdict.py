#!/usr/bin/env python3
"""Compare a freshly computed verdict against the committed one (SPEC.md §13
step 6: "confirm the verdict matches verdict.json").

Usage: compare-verdict.py <committed_verdict.json> <fresh_verdict.json>
                          [--ignore KEY ...]

Every key is compared. `--ignore` names keys that are expected to differ and
must be justified by the caller; `tools/replay.sh` ignores exactly two:

  artifact_id          the committed verdict is a verbatim copy of the one
                       produced inside rvt-rs, so it carries the artifact's
                       alias (`magnetar-2024-core-interior`) rather than the
                       umbrella id (`g-2026-0001`). See the artifact's
                       PROVENANCE.md.
  verdict_hash_sha256  a function of artifact_id, so it differs for the same
                       reason.

`timestamp`, `inputs.*.witness_version` and `replay` are also ignored, since
a replay legitimately runs a newer patch release of a witness and adds a
replay block the committed verdict does not have. Everything that carries
the protocol's meaning — status, witnesses compared, input hashes and roles,
semantic surface, exclusions, diffs, independence — must match exactly.

Exit 0 on match, 1 on any difference.

Python 3.12 standard library only.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ALWAYS_IGNORED = {"timestamp", "replay"}


def strip(verdict: dict, ignored: set[str]) -> dict:
    out = {k: v for k, v in verdict.items() if k not in ignored}
    inputs = out.get("inputs")
    if isinstance(inputs, dict):
        out["inputs"] = {
            wid: {k: v for k, v in entry.items() if k != "witness_version"}
            for wid, entry in inputs.items()
        }
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("committed", type=Path)
    ap.add_argument("fresh", type=Path)
    ap.add_argument("--ignore", action="append", default=[])
    args = ap.parse_args()

    ignored = ALWAYS_IGNORED | set(args.ignore)
    a = strip(json.loads(args.committed.read_text()), ignored)
    b = strip(json.loads(args.fresh.read_text()), ignored)

    differences = []
    for key in sorted(set(a) | set(b)):
        if a.get(key) != b.get(key):
            differences.append(key)

    if differences:
        print(f"verdict mismatch on {len(differences)} key(s): {', '.join(differences)}", file=sys.stderr)
        for key in differences:
            print(f"  committed {key} = {json.dumps(a.get(key), sort_keys=True)}", file=sys.stderr)
            print(f"  fresh     {key} = {json.dumps(b.get(key), sort_keys=True)}", file=sys.stderr)
        return 1

    print(f"verdict matches the committed record (ignored: {', '.join(sorted(ignored))})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
