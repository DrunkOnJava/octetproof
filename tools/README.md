# Layer 4 — the gate

The reference implementation of the diff function, the canonicalizer, the
replay protocol and the corpus hash chain. Apache-2.0.

**These tools never parse a binary format.** They fetch files by hash, drive
witnesses as separate processes, and compare the JSON those witnesses emit.
No `.rvt`, `.dwg` or `.ifc` is decoded by anything in this directory.

**Python 3.12 standard library only**, plus the witnesses themselves
(IfcOpenShell today, installed at run time and executed as a subprocess). The
replay protocol's value is that a stranger can run it years from now; every
added dependency is a reason it will not.

| Tool | Does |
|---|---|
| `fetch.py` | fetch a golden file from its recorded origin, verify SHA-256 and byte length, reuse a correct cached copy |
| `witness-ifcopenshell.py` | drive IfcOpenShell over the bridge file, emit a §6.2 observation |
| `verdict.py` | the diff function, the §9.3 independence set, replay, the §10.5 status vocabulary |
| `compare-verdict.py` | fresh verdict against the committed record (§13 step 6) |
| `replay.sh` | all of the above end to end, for one artifact |
| `validate-corpus.py` | observations and verdicts against the 1.0.0 schemas, plus hash self-consistency |
| `check-registry.py` | registry against its schema, plus cross-references the schema cannot express |
| `index.py` | rebuild or check `corpus/MANIFEST_INDEX.json` (§12.2) |
| `jsonschema_mini.py` | the JSON Schema subset the two validators use; not a general engine |

## Replay one artifact

```bash
tools/replay.sh                                # defaults to g-2026-0001
tools/replay.sh corpus/artifacts/g-2026-0001   # explicit
OCTETPROOF_PYTHON=python3.12 tools/replay.sh   # if your default python3 has no IfcOpenShell wheels
```

Exits non-zero unless the verdict is PASS, every observation replays
byte-for-byte, and the fresh verdict matches the committed one. Fail-closed.

## Statuses

`verdict.py` exits 0 only on `PASS`. The full §10.5 vocabulary it emits:

| Status | Means |
|---|---|
| `PASS` | at least two independent witnesses agreed on the whole claimed surface |
| `DISAGREE` | a diff inside the surface, beyond the category's tolerance |
| `INSUFFICIENT_WITNESSES` | fewer than two observations — never treated as agreement |
| `INSUFFICIENT_INDEPENDENT_WITNESSES` | the §9.3 set was not satisfied even though the observations agreed |
| `REJECTED_INPUT` | a witness read bytes that are not this artifact, or did not attest determinism |
| `REPLAY_DRIFT` | a fresh observation's canonical hash differs from the committed one |
| `MANIFEST_ERROR` | the manifest and the observations do not fit together |

`NON_DETERMINISTIC` and `WITNESS_ERROR` are in the schema's vocabulary but are
not produced here: they need the cross-platform attestation harness (§9.5) and
container supervision (§10.3), neither of which is implemented. A failed
determinism flag collapses into `REJECTED_INPUT` instead. That is a real gap,
not a shortcut — a witness that is non-deterministic in a way it does not
self-report will not be caught.

## Canonicalization

Sorted keys, no insignificant whitespace, UTF-8, SHA-256 (§7.3). The payloads
in scope carry integers and ASCII strings only, so RFC 8785's float
formatting and Unicode normalization rules are not exercised and are not
implemented. **A payload with floats or non-ASCII strings would need the full
RFC 8785 rules before its hash could be trusted across implementations** —
geometry surfaces will need this, and it is not here yet.

Any change to canonicalization changes every committed observation hash and
is a major version bump of the spec (§16.1).

## What is deliberately not here

- **No decoder.** Layer 5 lives in its own repositories.
- **No container isolation** (§10.3). Witnesses run as subprocesses on the
  runner, not in per-witness containers with resource limits and no network.
- **No Ed25519 chain-root signature** (§12.2). The chain exists; the signature
  does not.
- **No determinism attestation across OS and architecture** (§9.5). CI runs
  one runner, one architecture, once.
- **No `jsonschema` dependency.** `jsonschema_mini.py` implements the subset
  the schemas use and fails loudly on any keyword it does not implement, so a
  future schema construct cannot silently stop being enforced.
