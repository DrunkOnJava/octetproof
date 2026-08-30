# Provenance — g-2026-0001 (magnetar-2024-core-interior)

SPEC.md §8, §12. This file states what is recorded and, more usefully, what
is not.

## The chain, as far as it goes

| Element | Value |
|---|---|
| Artifact id | `g-2026-0001` |
| Alias | `magnetar-2024-core-interior` (the id this artifact carries inside rvt-rs) |
| Edge | `rvt-to-ifc:revit-export:core-interior` — RVT → IFC |
| Authoring witness | `autodesk-revit-exporter` |
| Source build (`S_build`) | Autodesk Revit 2024 |
| Source hash (`S_hash`) | `c805df445d613b408e37337765572021265e3f5dfdc7d1fa53b22ba1600b8014` (33,718,272 bytes) |
| Bridge hash (`B_hash`) | `d07c7462aee22640661faed5262cf802ce0fcbc663f312961a39be92bf857050` (20,392 bytes, IFC4) |
| Witness set (`W_set`) | rvt-rs 0.1.2 → `b6d9b67c10c3350b69b58cbd2c6caeca405f63ce182e7291feba3e3ff10f3e00`; IfcOpenShell 0.8.5 → `8cf4046509bb788406e93261f0dcb10708fbf33ae195d12f8ddc99b41a93398f`; IFClite 7.1.1 → `8cf4046509bb788406e93261f0dcb10708fbf33ae195d12f8ddc99b41a93398f` |
| Verdict (`V`) | PASS — 8 surface fields, 0 diffs, 4 excluded, independence satisfied across three lineages |
| Origin | magnetar-io/revit-test-datasets, MIT, both files |

Both files are fetched from their public origins and verified against those
hashes. Neither is redistributed here.

## Three lineages, two of which hash identically

The verdict recorded here spans three implementation lineages (§9.3): rvt-rs
reads the `.rvt` as the source witness; IfcOpenShell (C++/Python, LGPL-3.0)
and IFClite (`ifc-lite-core` 7.1.1, Rust, MPL-2.0, own byte-level STEP
scanner) each read Revit's `.ifc` as bridge witnesses, with no shared code
between them.

**The IFClite observation's canonical payload hash is identical to
IfcOpenShell's, `8cf4046509bb788406e93261f0dcb10708fbf33ae195d12f8ddc99b41a93398f`.**
Two unrelated readers, in different languages, with different parsing
strategies, produced byte-identical canonical payloads for all twelve entity
types. That is corroboration of the bridge-side reading and nothing more: it
says the two agree about what is in the file, not that the file says much.
Seven of the eight surface fields are still zero on both sides, and a third
reader agreeing that a 20 KB fixture contains no doors adds a lineage, not
semantic weight. The weight is in
[g-2026-0002](../g-2026-0002/PROVENANCE.md), the full-project export of the
same model.

**Why this is not an immutability violation (§8.3).** Nothing that identifies
the artifact changed: the source and bridge hashes, the `counts` block, the
claimed semantic surface and the four exclusions are exactly what was merged.
What changed is the evidence *about* it — a third witness observation, and a
verdict recomputed over the larger witness set with the same status, the same
surface, the same exclusions and the same zero diffs. §8.3 forbids editing an
artifact to fix a mistake in it; it does not freeze the witness set, and a
protocol whose whole claim is "N independent witnesses" cannot forbid the
arrival of witness N+1. The manifest additionally gained the `runner_kind`
field on its bridge witnesses, which names how a runner is invoked and
changes nothing the diff function reads.

## What is NOT recorded

**There is no export recording for this dataset, and there never will be.**
SPEC.md §8.2 and §12.3 require, for the first artifact of each export-mode
class, a screen recording or structured event log of the export session
showing the file open, the export dialog with settings visible, the export
running, and the resulting file hash. **No such recording exists for
g-2026-0001.** `source.recording_uri` is `null` and
`bridge.export_settings_hash` is `null`.

The reason is that this project did not perform the export. The authoring
witness here is **the magnetar dataset's own Revit export** — the `.rvt` and
the `.ifc` were both authored upstream by magnetar-io and published together
as a pair. What is known about the export is what the artifacts themselves
say and what the upstream repository states: the source was authored by
Autodesk Revit 2024, and the `.ifc` is a Revit-exporter output of that same
project. The exact Revit build string, the IFC exporter version, the exporter
settings, the date, and the operator are all unrecorded.

The pairing therefore rests on the upstream dataset's word, corroborated by
the two files being published together and by the IFC's own header. It is
**not** a §12.3-conformant provenance record. Anyone reasoning from this
artifact should treat "these two files describe the same model" as a claim
inherited from magnetar-io, not one this project verified.

`export_mode` is recorded as `revit-ifc-exporter (element export fixture)`,
which is a description of the observed output, not a setting read off a
dialog.

**The first artifact that will carry a real §12.3 recording is the RVT → DWG
edge**, because that export has to be performed here, in one licensed Revit
session, and can be recorded while it happens.

## What the bridge file actually is

A 20 KB element-export fixture, not a full project schedule. Concretely:

- Of the eight fields in the claimed semantic surface, **seven are zero on
  both sides**. Only `entity_counts.IFCUNITASSIGNMENT` is non-zero, at 1.
- The `.rvt` is 33.7 MB and rvt-rs recovers 12 storeys, 64 slabs, 18 spaces
  and 102 materials from it. The paired `.ifc` contains essentially none of
  that. The two witnesses agree on the surface because the surface was drawn
  where the export is faithful, and the export is faithful about very little.
- Four further categories — floors, rooms/spaces, materials, property sets —
  are excluded first-class because rvt-rs and the export disagree in ways that
  are tracked decoder gaps, not verification failures (rvt-rs issues 31, 33,
  34, 35). The verdict lists them with their tracking issues and never diffs
  them.

The full-project export of the same model,
`2024_Core_Interior_slim.ifc` (1,665,968 bytes, sha256 `bfdf36ff…`, header
"Autodesk Revit 24.0.20.20 (ENU)"), exists in the same upstream dataset. It
is now [g-2026-0002](../g-2026-0002/PROVENANCE.md), manifested and gated, and
it is where this decoder's recovery is actually measured: 360 walls, 132
doors, 256 columns, 116 spaces and 80 slabs in the export against 0, 0, 0, 18
and 64 recovered. The two artifacts share the same `.rvt` and the same
committed rvt-rs observation, so the comparison between them is exactly the
question of how much of the agreement here was real.

## Verdict id, and why it differs from the manifest id

`verdict.json` and all three files under `observations/` are **verbatim
copies** from `research/witness/magnetar-2024-core-interior/` in
[DrunkOnJava/rvt-rs](https://github.com/DrunkOnJava/rvt-rs). They are copied
unmodified so the two repositories stay byte-diffable and so nothing about
the recorded evidence depends on this repository having re-derived it.

A consequence: they carry `artifact_id: "magnetar-2024-core-interior"` — the
id rvt-rs uses — rather than the umbrella id `g-2026-0001`. This is handled
explicitly rather than papered over:

- `manifest.json` declares both, as `artifact_id` and `alias`.
- `tools/verdict.py` accepts an observation whose `artifact_id` is either one
  and rejects anything else as `MANIFEST_ERROR`. It is a real check, not a
  skipped one.
- A freshly computed verdict carries `artifact_id: "g-2026-0001"` and
  therefore a different `verdict_hash_sha256`, since the hash covers the id.
  `tools/compare-verdict.py` ignores exactly those two keys and compares
  everything else — status, witnesses, input hashes and roles, surface,
  exclusions, diffs, independence — for exact equality.

When the umbrella becomes the canonical home of the corpus, the observations
will be regenerated under the umbrella id and this note goes away.

## Immutability

Per §8.3 this artifact is immutable now that it is committed with a passing
verdict. Corrections create a new artifact id with a link back and a reason.
Do not edit this directory to fix a mistake in it. Adding the third witness
was not such a correction — see "Three lineages, two of which hash
identically" above for why, and for what did and did not change.

## Replay

```
tools/replay.sh corpus/artifacts/g-2026-0001
```

Fetches the bridge file, installs the pinned IfcOpenShell, builds the pinned
IFClite glue in `witnesses/ifc-lite`, re-derives both bridge observations,
validates them against the 1.0.0 schema, re-runs the verdict against the
committed observations, and compares the result to `verdict.json`. Exits
non-zero on anything short of a full match.

The source-witness observation is **not** regenerated: the umbrella never
builds a decoder. To regenerate it, run in rvt-rs:

```
rvt-ifc 2024_Core_Interior.rvt -o out.ifc \
  --observation observations/rvt-rs.json \
  --artifact-id magnetar-2024-core-interior
```

and copy the result here. Its committed hash is what the replay checks
against, so a decoder change that alters what rvt-rs sees on this artifact
fails the gate here as well as in rvt-rs.
