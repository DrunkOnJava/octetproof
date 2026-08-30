# Layer 2 — the golden artifact corpus

Each artifact is one recorded edge: a file in a source format, a file in a
bridge format produced from it by a named authoring witness, and everything
needed to prove that two independent readers agreed about them.

```
corpus/
  MANIFEST_INDEX.json          hash chain over every manifest
  artifacts/
    g-2026-0001/
      manifest.json            SPEC.md §6.1 — hashes, origins, counts,
                               relations, storeys, surface
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
| the `decoder_*` fields are dropped | they are the decoder repository's own regression baseline, which the gate explicitly ignores (§6.1). A category that exists *only* as a decoder baseline goes with them — one that carries no `source_ifc_type` (or, in the 1.1.0 blocks, no `relation_ifc_type` / `storey_ifc_type`) is invisible to every bridge witness and is not a cross-witness category at all. A category that *does* carry its type key stays even when its status excludes it: `relations.IFCRELFILLSELEMENT` on g-2026-0001 is `decoder_baseline` and is kept, because dropping it would hide behind a formatting rule the fact that the two sides of that edge cannot be compared on it |
| `octetproof_version` names the protocol document each manifest was authored against | both say `1.1.0`, because both now carry the `relations` and `storeys` blocks that 1.1.0 introduced (SPEC.md §20). A manifest using a 1.1.0 block while declaring 1.0.0 would be misdescribing itself. The field records which document the manifest was written against, not a difference in obligations — 1.1.0 is additive and a 1.0.0 document is still conformant input (§16.2) |

Everything the gate reads is unchanged in kind: the normative `counts` block,
with `source_ifc_type`, `status` (`known` / `known_gap` / `unsupported` /
`decoder_baseline`), `tolerance`, `tracking_issue` and `unsupported_feature`
carrying exactly the §6.1 meanings — joined since 1.1.0 by two blocks that
work the same way. `relations` categories carry `relation_ifc_type` and
`expected_pairs`; `storeys` categories carry `storey_ifc_type` and
`expected_storeys`. Neither has a `tolerance`: their field class is exact set
equality and §7.2 gives it no tolerance concept.

The manifest additionally declares `semantic_surface` and `excluded` — the
result those three blocks imply. `tools/verdict.py` derives both and raises
`MANIFEST_ERROR` if the declaration disagrees, so flipping a category's
status without noticing is loud rather than a silent change to what is being
claimed.

## What is in the corpus today

Two artifacts, one edge, three witnesses, three agreement classes.

| Artifact | Alias | Bridge file | Verdict |
|---|---|---|---|
| `g-2026-0001` | magnetar-2024-core-interior | `2024_Core_Interior.ifc`, 20,392 bytes — an element-export fixture | PASS, 6 surface fields, 10 excluded |
| `g-2026-0002` | magnetar-2024-core-interior-slim | `2024_Core_Interior_slim.ifc`, 1,665,968 bytes — the full project export | PASS, 13 surface fields, 3 excluded |

**They share the same `.rvt` and the same committed rvt-rs observation.** Only
the Revit-authored bridge file differs, which makes the pair a direct measure
of what a thin reference can support. The full export scores 360 walls, 132
doors, 256 columns, 80 slabs, 20 shading devices and 15 storeys as exact
matches, plus 138 `IfcRelFillsElement` host/filling pairs and the 15
`[name, elevation]` storeys; the 20 KB fixture can score none of the element
counts and no relation, but carries the same complete fifteen-storey
hierarchy and so supports `storeys.IFCBUILDINGSTOREY` exactly as strongly.

See the top-level [README](../README.md#what-exists-today) for what that is
worth, and each artifact's PROVENANCE.md
([g-2026-0001](artifacts/g-2026-0001/PROVENANCE.md),
[g-2026-0002](artifacts/g-2026-0002/PROVENANCE.md)) for what is not recorded
about it.

## Adding one

See [CONTRIBUTING.md](../CONTRIBUTING.md#2-recording-an-edge).
