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
| Witness set (`W_set`) | rvt-rs 0.1.2 → `70f8df9dd188b7e42947bfa167b2810333b3d0dc4398019ea40570b7fcb87c24`; IfcOpenShell 0.8.5 → `99e6cd7a2feceef26c8953d5f383291a6b8bece8e5fef378d510dac62a189f6c`; IFClite 7.1.1 → `99e6cd7a2feceef26c8953d5f383291a6b8bece8e5fef378d510dac62a189f6c` |
| Verdict (`V`) | PASS — 6 surface fields, 0 diffs, 10 excluded, independence satisfied across three lineages |
| Protocol | OctetProof 1.1.0 (`manifest.json`'s `octetproof_version`) |
| Origin | magnetar-io/revit-test-datasets, MIT, both files |

Both files are fetched from their public origins and verified against those
hashes. Neither is redistributed here.

## What the six surface fields are

Five entity counts and one storey set:

| Field | Class | Value on both sides |
|---|---|---|
| `entity_counts.IFCBUILDINGSTOREY` | count | 15 |
| `entity_counts.IFCROOF` | count | 0 |
| `entity_counts.IFCBEAM` | count | 0 |
| `entity_counts.IFCFLOWTERMINAL` | count | 0 |
| `entity_counts.IFCUNITASSIGNMENT` | count | 1 |
| `storeys.IFCBUILDINGSTOREY` | storey set (§7.2, 1.1.0) | the same 15 (name, elevation) pairs |

**The storey set is the interesting one, and it is interesting precisely
because this artifact is thin.** Revit writes the model's complete
fifteen-storey spatial hierarchy into a 20 KB export that carries a single
building element, so the reference side is as authoritative here as it is on
the full-project sibling. All three witnesses reproduce the same pairs —
`Basement 2` at −40 ft through `Level 13` at 185.5 ft — with the elevation
resolved by each witness through its own file's declared `LENGTHUNIT`
(Revit's export declares `FOOT`, rvt-rs writes `METRE`) and rendered in feet
at 1e-6 as a fixed six-decimal string. That is a decoder-recovered *label*
matched against Revit's own, not another zero count.

Three of the five counts are still zero on both sides. A 20 KB element
fixture cannot support much more, and the claim is narrow because the file is.

## What is excluded, and why

Ten categories are excluded first-class (§7.1 rule 3) and never diffed. Nine
are `decoder_baseline` or `known_gap` entity counts; the tenth is the
relation pair set:

| Excluded field | Category | Fixture | rvt-rs | Reason | Tracking |
|---|---|---|---|---|---|
| entity_counts.IFCWALL | walls | 0 | 360 | decoder_baseline | rvt-rs#211 |
| entity_counts.IFCSLAB | floors | 0 | 80 | decoder_baseline | rvt-rs#212 |
| entity_counts.IFCDOOR | doors | 0 | 132 | decoder_baseline | rvt-rs#211 |
| entity_counts.IFCWINDOW | windows | 0 | 6 | decoder_baseline | rvt-rs#211 |
| entity_counts.IFCSPACE | rooms_spaces | 0 | 18 | known_gap | rvt-rs#33 |
| entity_counts.IFCCOLUMN | columns | 0 | 256 | decoder_baseline | rvt-rs#204 |
| entity_counts.IFCMATERIAL | materials | 1 | 102 | known_gap | rvt-rs#34 |
| entity_counts.IFCPROPERTYSET | property_sets | 25 | 854 | known_gap | rvt-rs#35 |
| entity_counts.IFCSHADINGDEVICE | shading_devices | 1 | 20 | decoder_baseline | rvt-rs#212 |
| relations.IFCRELFILLSELEMENT | opening_fills | 0 | 138 | decoder_baseline | rvt-rs#222 |

The `decoder_baseline` rows are not decoder failures. rvt-rs recovers 360
walls, 132 doors, 6 windows, 256 columns, 80 slabs, 20 shading devices and
138 door/window-to-host-wall bindings from this `.rvt`, and every one of them
is scored as an exact set match on the sibling artifact
[g-2026-0002](../g-2026-0002/PROVENANCE.md). They are excluded *here* because
the reference side of this edge is a one-element fixture that carries none of
them: two files that cannot be compared on a field must say so rather than
record a zero-against-zero agreement.

`relations.IFCRELFILLSELEMENT` is the clearest case. The fixture holds no
`IfcRelFillsElement` at all, so the strongest topological claim in the corpus
is simply not available on this edge, and is claimed only where it can be
measured. SPEC.md §20.1 records the same split.

## Three lineages, two of which hash identically

The verdict recorded here spans three implementation lineages (§9.3): rvt-rs
reads the `.rvt` as the source witness; IfcOpenShell (C++/Python, LGPL-3.0)
and IFClite (`ifc-lite-core` 7.1.1, Rust, MPL-2.0, own byte-level STEP
scanner) each read Revit's `.ifc` as bridge witnesses, with no shared code
between them.

**The IFClite observation's canonical payload hash is identical to
IfcOpenShell's, `99e6cd7a2feceef26c8953d5f383291a6b8bece8e5fef378d510dac62a189f6c`.**
Two unrelated readers, in different languages, with different parsing
strategies, produced byte-identical canonical payloads for all fourteen
entity types, the relation pair set and the storey set — including the unit
normalisation, which each resolved with its own code
(`ifcopenshell.util.unit.calculate_unit_scale` against
`ifc_lite_core::extract_length_unit_scale`). That is corroboration of the
bridge-side reading, and on the storey set it is corroboration of something
with content rather than of a shared zero.

**Why the updates here are not immutability violations (§8.3).** Nothing that
identifies the artifact has changed across any of them: the source and bridge
hashes, the edge, the authoring witness and the origins are exactly what was
merged. What changes is the evidence *about* it — witnesses arriving, and a
decoder recovering fields it previously could not. §8.3 forbids editing an
artifact to fix a mistake in it; it does not freeze the witness set or the
decoder, and a protocol whose whole claim is "N independent witnesses agree
on a stated surface" cannot forbid witness N+1 or a widened surface. Every
such change is a new recorded verdict over the same bytes, and the manifest's
`counts` / `relations` / `storeys` blocks state the surface each time.

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

- Its one building element is an `IFCSHADINGDEVICE`,
  `Floor:Structural Slab:71411`. It carries 1 `IFCMATERIAL`, 25
  `IFCPROPERTYSET`, no walls, no doors, no windows, no columns, no slabs, no
  spaces and no `IfcRelFillsElement`.
- It nevertheless carries the full fifteen-storey spatial hierarchy, which is
  why `entity_counts.IFCBUILDINGSTOREY` and `storeys.IFCBUILDINGSTOREY` are
  the two fields on this artifact that mean something.
- Of the other four surface fields, three are zero on both sides.

The full-project export of the same model,
`2024_Core_Interior_slim.ifc` (1,665,968 bytes, sha256 `bfdf36ff…`, header
"Autodesk Revit 24.0.20.20 (ENU)"), exists in the same upstream dataset. It
is [g-2026-0002](../g-2026-0002/PROVENANCE.md), manifested and gated, and it
is where this decoder's recovery is actually measured across thirteen fields.
The two artifacts share the same `.rvt` and the same committed rvt-rs
observation, so the comparison between them is exactly the question of what a
thin reference can and cannot support.

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

Per §8.3 this artifact is immutable in the sense that matters: the bytes it
names, the edge it records and the id it carries do not change, and a
correction to any of those creates a new artifact id with a link back and a
reason. Do not edit this directory to fix a mistake in it. Re-recording the
verdict when a witness is added or the decoder recovers more is not such a
correction — see "Three lineages, two of which hash identically" above.

## Replay

```
tools/replay.sh corpus/artifacts/g-2026-0001
```

Fetches the bridge file, installs the pinned IfcOpenShell, builds the pinned
IFClite glue in `witnesses/ifc-lite`, re-derives both bridge observations,
validates them against the 1.1.0 schemas, re-runs the verdict against the
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
