#!/usr/bin/env bash
# OctetProof replay (SPEC.md §8.4, §13): re-derive one golden artifact's
# verdict from scratch and prove it matches the committed record.
#
#   tools/replay.sh [ARTIFACT_DIR] [WORK_DIR]
#
# Defaults: ARTIFACT_DIR=corpus/artifacts/g-2026-0001, WORK_DIR=_replay/<id>.
#
# What it does:
#   1. Fetch the bridge file from its public origin and verify its SHA-256
#      against the manifest. The corpus never redistributes those bytes.
#   2. Create a venv and install the registry-pinned Python bridge witness
#      (IfcOpenShell) into it, and `cargo build --locked` every pinned cargo
#      bridge witness glue (IFClite) the manifest names.
#   3. Run every `ci-runnable` bridge witness the manifest names; each writes
#      a fresh observation.
#   4. Copy in the committed source-witness observation. The umbrella never
#      builds a decoder — regenerating the rvt-rs observation happens in
#      rvt-rs (`rvt-ifc --observation PATH --artifact-id ID`).
#   5. Validate the committed corpus and the fresh observations against the
#      OctetProof 1.0.0 observation and verdict schemas.
#   6. Run the verdict with --compare-committed, so each fresh observation's
#      canonical hash must equal the committed one.
#   7. Compare the fresh verdict against the committed verdict.
#
# Exits non-zero unless the verdict is PASS, every replay entry is `match`,
# and the fresh verdict agrees with the committed one. Fail-closed.
#
# Dependencies: bash, python3 (>=3.12), a Rust toolchain >= 1.87 if the
# manifest names a `cargo` bridge witness, and network access for steps 1-2.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ARTIFACT_DIR="${1:-$REPO_ROOT/corpus/artifacts/g-2026-0001}"
ARTIFACT_DIR="$(cd "$ARTIFACT_DIR" && pwd)"
MANIFEST="$ARTIFACT_DIR/manifest.json"
[ -f "$MANIFEST" ] || { echo "error: no manifest.json under $ARTIFACT_DIR" >&2; exit 1; }

ARTIFACT_ID="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["artifact_id"])' "$MANIFEST")"
WORK_DIR="${2:-$REPO_ROOT/_replay/$ARTIFACT_ID}"
mkdir -p "$WORK_DIR/observations"

echo "== OctetProof replay: $ARTIFACT_ID"
echo "   artifact: $ARTIFACT_DIR"
echo "   work:     $WORK_DIR"

# --- 1. fetch the bridge file by origin URL, verified by hash ---------------
BRIDGE_NAME="$(python3 -c 'import json,sys; m=json.load(open(sys.argv[1])); print(m["bridge"]["origin"].rsplit("/",1)[-1])' "$MANIFEST")"
BRIDGE_FILE="$WORK_DIR/$BRIDGE_NAME"
python3 "$REPO_ROOT/tools/fetch.py" "$MANIFEST" --which bridge --out "$BRIDGE_FILE"

# --- 2. venv with the pinned bridge witness --------------------------------
VENV="${OCTETPROOF_VENV:-$WORK_DIR/.venv}"
# IfcOpenShell ships prebuilt wheels for a lagging set of CPython versions.
# CI pins 3.12; set OCTETPROOF_PYTHON to point at one locally if your default
# python3 is newer than the wheels available for the pinned release.
VENV_PYTHON="${OCTETPROOF_PYTHON:-python3}"
if [ ! -x "$VENV/bin/python" ]; then
  echo "== creating venv at $VENV ($VENV_PYTHON)"
  "$VENV_PYTHON" -m venv "$VENV"
fi
PIN="$(python3 -c 'import json,sys; m=json.load(open(sys.argv[1])); print(next(w["version_pin"] for w in m["witnesses"]["bridge"] if w["witness_id"]=="ifcopenshell"))' "$MANIFEST")"
echo "== installing bridge witness: $PIN"
"$VENV/bin/python" -m pip install --quiet --upgrade pip
"$VENV/bin/python" -m pip install --quiet "$PIN"

# --- 3. run each ci-runnable bridge witness --------------------------------
# `runner_kind` says how the runner is invoked, never what it means: `python`
# runs under the venv above, `cargo` is glue this repository builds from a
# pinned, out-of-workspace crate and executes as its own process. Either way
# the umbrella parses no format bytes itself — the witness process does, and
# tools/check-registry.py holds the §9.6 pin to one number.
python3 -c '
import json,sys
m=json.load(open(sys.argv[1]))
for w in m["witnesses"]["bridge"]:
    if w.get("mode")=="ci-runnable":
        print(w["witness_id"], w.get("runner_kind","python"), w["runner"])
' "$MANIFEST" > "$WORK_DIR/bridge-witnesses.txt"

while read -r WID KIND RUNNER; do
  [ -n "$WID" ] || continue
  echo "== bridge witness: $WID ($KIND, $RUNNER)"
  case "$KIND" in
    python)
      "$VENV/bin/python" "$REPO_ROOT/$RUNNER" "$MANIFEST" "$BRIDGE_FILE" \
        --observation "$WORK_DIR/observations/$WID.json"
      ;;
    cargo)
      cargo build --release --locked --manifest-path "$REPO_ROOT/$RUNNER/Cargo.toml"
      BIN_NAME="$(python3 -c 'import sys,tomllib; print(tomllib.load(open(sys.argv[1],"rb"))["package"]["name"])' "$REPO_ROOT/$RUNNER/Cargo.toml")"
      "$REPO_ROOT/$RUNNER/target/release/$BIN_NAME" "$MANIFEST" "$BRIDGE_FILE" \
        --observation "$WORK_DIR/observations/$WID.json"
      ;;
    *)
      echo "error: unknown runner_kind '$KIND' for witness $WID" >&2
      exit 1
      ;;
  esac
done < "$WORK_DIR/bridge-witnesses.txt"

# --- 4. committed source-witness observation -------------------------------
SOURCE_WID="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["witnesses"]["source"]["witness_id"])' "$MANIFEST")"
echo "== source witness: $SOURCE_WID (committed; the umbrella never builds a decoder)"
cp "$ARTIFACT_DIR/observations/$SOURCE_WID.json" "$WORK_DIR/observations/$SOURCE_WID.json"

# --- 4b. schemas: committed corpus + the freshly produced observations -----
echo "== schema validation (SPEC.md §6.2, §6.3)"
python3 "$REPO_ROOT/tools/validate-corpus.py" --extra-observations "$WORK_DIR/observations"

# --- 5. verdict, with replay against the committed observations ------------
echo "== verdict"
python3 "$REPO_ROOT/tools/verdict.py" \
  "$MANIFEST" \
  "$WORK_DIR/observations" \
  --out "$WORK_DIR/verdict.json" \
  --registry "$REPO_ROOT/registry/witnesses.json" \
  --compare-committed "$ARTIFACT_DIR/observations"

# --- 6. fresh verdict vs committed verdict ---------------------------------
echo "== verdict comparison"
python3 "$REPO_ROOT/tools/compare-verdict.py" \
  "$ARTIFACT_DIR/verdict.json" \
  "$WORK_DIR/verdict.json" \
  --ignore artifact_id --ignore verdict_hash_sha256

echo "== replay OK: $ARTIFACT_ID PASS, observations replayed, verdict matches"
