# Layer 2 — the golden artifact corpus

Each artifact is one recorded edge: a file in a source format, a file in a
bridge format produced from it by a named authoring witness, and everything
needed to prove that two independent readers agreed about them.

```
corpus/
  MANIFEST_INDEX.json          hash chain over every manifest
  artifacts/
    g-2026-0001/
      manifest.json            SPEC.md §6.1 — hashes, origins, counts, surface
      PROVENANCE.md            what is recorded and what is not
      observations/            SPEC.md §6.2 — one per witness, committed
      verdict.json             SPEC.md §6.3 — the recorded decision
```

Artifact ids are `g-YYYY-NNNN`, assigned in order. An artifact is immutable
once merged with a passing verdict (§8.3); corrections create a new id with a
link back and a reason.

## The corpus stores hashes, not bytes

**No source or bridge file is committed here.** Each manifest records the
SHA-256, the byte length, the license and the public origin URL of both
files. `tools/fetch.py` downloads from that origin and rejects anything that
does not hash to the recorded value.

Three reasons, in order of weight:

1. **Redistribution.** These are third-party files under third-party licenses,
   some multi-megabyte, some derived from proprietary applications. Recording
   a hash makes no redistribution claim.
2. **Detectability.** "The bytes were swapped" becomes a build failure rather
   than a silent change to what everyone thinks was verified.
3. **Size.** g-2026-0001 alone would add 33.7 MB of `.rvt` to every clone.

The cost is that replay needs network access once, and that an artifact
becomes unreplayable if its origin disappears. That is a real fragility and
the reason CONTRIBUTING.md requires an origin that is publicly fetchable and
licensed to be before an artifact is accepted.

## MANIFEST_INDEX.json

The hash chain (§12.2). One entry per artifact, ordered, each carrying the
SHA-256 of that artifact's `manifest.json` bytes and `prev_hash`, the
canonical hash of the preceding entry. The first entry's `prev_hash` is
`null`. Editing a merged manifest changes its `manifest_sha256`, which changes
its entry's canonical hash, which invalidates every `prev_hash` after it.

Rebuild with `python3 tools/index.py`; CI runs `--check` and fails if the
committed index is not the chain the corpus implies.

**Signing is not implemented.** §12.2 also requires an Ed25519 signature over
the chain root, published in this file. There is no maintainer key yet, so
`signature` is `null` and `signing_status` says so. Until that exists the
chain is tamper-evident against accidental drift and against anyone who
cannot also rewrite `MANIFEST_INDEX.json` in the same commit — which is to
say, it detects mistakes, not a determined maintainer.

## The manifest shape

`manifest.json` follows SPEC.md §6.1 with three documented departures, all
driven by the umbrella's different job:

| Departure | Why |
|---|---|
| `artifact_id` + `alias` instead of `id` | the umbrella assigns `g-YYYY-NNNN`; `alias` keeps the id the decoder repository uses, so observations from either side resolve. See the artifact's PROVENANCE.md. |
| `source` / `bridge` blocks carry `origin`, `license` and `bytes` | the corpus fetches by hash instead of committing bytes; without an origin an artifact is not replayable |
| the `decoder_*` fields are dropped | they are the decoder repository's own regression baseline, which the gate explicitly ignores (§6.1). Categories that exist only as decoder baselines — `levels` in this manifest's upstream — are dropped with them |

Everything the gate reads is unchanged: the normative `counts` block, with
`source_ifc_type`, `status` (`known` / `known_gap` / `unsupported`),
`tolerance`, `tracking_issue` and `unsupported_feature` carrying exactly the
§6.1 meanings.

The manifest additionally declares `semantic_surface` and `excluded` — the
result that `counts` implies. `tools/verdict.py` derives both from `counts`
and raises `MANIFEST_ERROR` if the declaration disagrees, so flipping a
category's status without noticing is loud rather than a silent change to
what is being claimed.

## What is in the corpus today

One artifact. See the top-level [README](../README.md#what-exists-today) for
what it is worth, and
[g-2026-0001/PROVENANCE.md](artifacts/g-2026-0001/PROVENANCE.md) for what is
not recorded about it.

## Adding one

See [CONTRIBUTING.md](../CONTRIBUTING.md#2-recording-an-edge).
