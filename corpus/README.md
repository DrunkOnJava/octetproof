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
    g-2026-0002/               same shape, same .rvt, the full project export
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
| the `decoder_*` fields are dropped | they are the decoder repository's own regression baseline, which the gate explicitly ignores (§6.1). A category that exists *only* as a decoder baseline goes with them — `levels` in g-2026-0001's upstream, which carries no `source_ifc_type` and so no bridge witness can see it. Where the same category does carry a `source_ifc_type`, as `levels` does in g-2026-0002, it stays: it is a real cross-witness observation (15 exported storeys against 12 recovered) and is excluded first-class rather than dropped. Dropping it would hide a measured disagreement behind a formatting rule |
| `octetproof_version` names the protocol document each manifest was authored against | g-2026-0001 says `1.0.0`, g-2026-0002 says `1.0.1`. 1.0.1 is a patch release with no schema, diff-function or provenance change (SPEC.md §19a), so the two conform identically; the field records history rather than a difference in obligations, and an immutable manifest is not rewritten to chase a patch number |

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

Two artifacts, one edge, three witnesses.

| Artifact | Alias | Bridge file | Verdict |
|---|---|---|---|
| `g-2026-0001` | magnetar-2024-core-interior | `2024_Core_Interior.ifc`, 20,392 bytes — an element-export fixture | PASS, 8 surface fields, 4 excluded |
| `g-2026-0002` | magnetar-2024-core-interior-slim | `2024_Core_Interior_slim.ifc`, 1,665,968 bytes — the full project export | PASS, 4 surface fields, 9 excluded |

**They share the same `.rvt` and the same committed rvt-rs observation.** Only
the Revit-authored bridge file differs, which makes the pair a direct measure
of how much of the first artifact's agreement was real: the second has a
narrower surface and five times the exclusions, because the full export shows
360 walls, 132 doors, 256 columns, 116 spaces and 80 slabs where rvt-rs
recovers 0, 0, 0, 18 and 64.

See the top-level [README](../README.md#what-exists-today) for what that is
worth, and each artifact's PROVENANCE.md
([g-2026-0001](artifacts/g-2026-0001/PROVENANCE.md),
[g-2026-0002](artifacts/g-2026-0002/PROVENANCE.md)) for what is not recorded
about it.

## Adding one

See [CONTRIBUTING.md](../CONTRIBUTING.md#2-recording-an-edge).
