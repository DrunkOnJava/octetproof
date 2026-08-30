# Provenance — g-2026-0002 (magnetar-2024-core-interior-slim)

SPEC.md §8, §12. This file states what is recorded and, more usefully, what
is not.

## The chain, as far as it goes

| Element | Value |
|---|---|
| Artifact id | `g-2026-0002` |
| Alias | `magnetar-2024-core-interior-slim` (the id this artifact carries inside rvt-rs) |
| Edge | `rvt-to-ifc:revit-export:core-interior-slim` — RVT → IFC |
| Authoring witness | `autodesk-revit-exporter` |
| Source build (`S_build`) | Autodesk Revit 2024 |
| Source hash (`S_hash`) | `c805df445d613b408e37337765572021265e3f5dfdc7d1fa53b22ba1600b8014` (33,718,272 bytes) |
| Bridge hash (`B_hash`) | `bfdf36ffb0bb768f3409d818403990e64d4c262c6780603be87f8077387ad86d` (1,665,968 bytes, IFC4, 19,879 entity instances) |
| Witness set (`W_set`) | rvt-rs 0.1.2 → `b6d9b67c10c3350b69b58cbd2c6caeca405f63ce182e7291feba3e3ff10f3e00`; IfcOpenShell 0.8.5 → `882e1e0f7d546bed2b4cf94e0cb8867f257321235203adcb0ed48e8ef521b4f8`; IFClite 7.1.1 → `882e1e0f7d546bed2b4cf94e0cb8867f257321235203adcb0ed48e8ef521b4f8` |
| Verdict (`V`) | PASS — 4 surface fields, 0 diffs, 9 excluded, independence satisfied across three lineages |
| Origin | magnetar-io/revit-test-datasets, MIT, both files |

Both files are fetched from their public origins and verified against those
hashes. Neither is redistributed here.

## The same source, a different bridge

The `.rvt` is byte-for-byte the one behind
[g-2026-0001](../g-2026-0001/PROVENANCE.md), and the committed rvt-rs
observation here is byte-for-byte the one committed there. **That is the
point.** What changes is the bridge file: g-2026-0001 pairs the model with a
20 KB element-export fixture, this artifact pairs it with the full project
export from the same upstream dataset. One decoder reading, measured against
two different exports of the same model, is exactly the comparison that says
how much of the earlier agreement was real and how much was an artifact of a
near-empty reference.

The answer is not flattering to the decoder, and the manifest says so in
`counts` rather than in prose. The full export carries 360 IFCWALL, 132
IFCDOOR, 256 IFCCOLUMN, 116 IFCSPACE, 80 IFCSLAB and 15 IFCBUILDINGSTOREY;
rvt-rs recovers 0, 0, 0, 18, 64 and 12 respectively. Nine of the thirteen
categories are therefore excluded first-class — eight as `known_gap`, one
(`levels`) as `decoder_baseline` — each carrying its rvt-rs tracking issue:

| Excluded field | Category | Export | rvt-rs | Reason | Tracking |
|---|---|---|---|---|---|
| entity_counts.IFCBUILDINGSTOREY | levels | 15 | 12 | decoder_baseline | rvt-rs#33 (binding #86) |
| entity_counts.IFCWALL | walls | 360 | 0 | known_gap | rvt-rs#30 |
| entity_counts.IFCSLAB | floors | 80 | 64 | known_gap | rvt-rs#31 |
| entity_counts.IFCDOOR | doors | 132 | 0 | known_gap | rvt-rs#32 |
| entity_counts.IFCWINDOW | windows | 6 | 0 | known_gap | rvt-rs#32 |
| entity_counts.IFCSPACE | rooms_spaces | 116 | 18 | known_gap | rvt-rs#33 |
| entity_counts.IFCCOLUMN | columns | 256 | 0 | known_gap | rvt-rs#204 |
| entity_counts.IFCMATERIAL | materials | 10 | 102 | known_gap | rvt-rs#34 |
| entity_counts.IFCPROPERTYSET | property_sets | 0 | 64 | known_gap | rvt-rs#35 |

The claimed semantic surface is four fields — IFCROOF, IFCBEAM,
IFCFLOWTERMINAL and IFCUNITASSIGNMENT — and only IFCUNITASSIGNMENT is
non-zero. **A narrow surface is the honest one here.** Claiming any of the
nine would be claiming an agreement that does not exist. The excluded table
above is the actual deliverable of this artifact: it is a measured gap
between an independent decoder and Revit's own exporter on a real project
schedule, not a promise about one.

Two of the entries run the other way, which is worth saying because
under-count is the failure mode people expect. `materials` is an over-count
(102 recovered against 10 exported, because rvt-rs recovers partition
display-name materials and does not model the export's 150
IfcMaterialConstituentSet / 309 IfcMaterialConstituent), and
`property_sets` is an over-count against zero (the ReferenceView_V1.2 export
carries no IfcPropertySet at all — confirmed independently by both bridge
readers — while rvt-rs emits 64 RvtFloorGeometry sets for plan-loop slab
annotations). Neither side is a subset of the other.

## Three lineages, two of which hash identically

Three witnesses, three implementation lineages (§9.3): rvt-rs reads the
`.rvt`; IfcOpenShell (C++/Python, LGPL-3.0) and IFClite (`ifc-lite-core`
7.1.1, Rust, MPL-2.0, own byte-level STEP scanner) each read the `.ifc`
independently.

**The two bridge observations have the same canonical payload hash,
`882e1e0f…`.** Two unrelated STEP readers — different languages, different
parsing strategies, no shared code — produced byte-identical canonical
payloads for all thirteen entity types on a 1.6 MB, 19,879-instance file.
That is what the hash equality means and all it means: it is corroboration
of the bridge-side reading, not extra evidence about the source side. The
`entity_counts` surface is a shallow one, and two readers agreeing on it does
not imply they would agree about geometry.

## What is NOT recorded

**There is no export recording for this dataset, and there never will be**,
for exactly the reasons set out in
[g-2026-0001/PROVENANCE.md](../g-2026-0001/PROVENANCE.md#what-is-not-recorded):
this project did not perform the export. `source.recording_uri` is `null` and
`bridge.export_settings_hash` is `null`.

What is known about this particular export is more than for the sibling
artifact, because the file's own STEP header states it:

- `FILE_NAME` names `ODA SDAI 23.12` and
  `Autodesk Revit 24.0.20.20 (ENU) - IFC 24.0.20.20`;
- `FILE_DESCRIPTION` declares `ViewDefinition [ReferenceView_V1.2]` and
  `ExchangeRequirement [Architecture]`;
- `FILE_SCHEMA` is `IFC4`.

`export_mode` records those. They are read off the file, not off an export
dialog: the exporter's full option set, the date, and the operator remain
unrecorded, and the pairing of this `.ifc` with that `.rvt` still rests on
the upstream dataset's word. It is **not** a §12.3-conformant provenance
record.

## Verdict id, and why it differs from the manifest id

`verdict.json` and all three files under `observations/` are **verbatim
copies** from `research/witness/magnetar-2024-core-interior-slim/` in
[DrunkOnJava/rvt-rs](https://github.com/DrunkOnJava/rvt-rs), copied unmodified
so the two repositories stay byte-diffable.

They therefore carry `artifact_id: "magnetar-2024-core-interior-slim"` rather
than `g-2026-0002`, handled exactly as for g-2026-0001: `manifest.json`
declares both as `artifact_id` and `alias`, `tools/verdict.py` accepts either
and rejects anything else as `MANIFEST_ERROR`, and `tools/compare-verdict.py`
ignores `artifact_id` and `verdict_hash_sha256` while comparing everything
else for exact equality.

## The manifest keeps `levels`; g-2026-0001's drops it

`corpus/README.md` documents that the upstream `decoder_*` fields are dropped
from umbrella manifests, and that categories existing only as decoder
baselines go with them. `levels` is dropped in g-2026-0001 for that reason —
there, it carries no `source_ifc_type` and so is invisible to any bridge
witness. Here it carries `IFCBUILDINGSTOREY` and both bridge readers count
15 of them, so it is a real cross-witness observation with a real gap behind
it and is retained as a first-class exclusion. Dropping it would have hidden
a measured 15-vs-12 disagreement behind a formatting rule.

## Immutability

Per §8.3 this artifact is immutable now that it is committed with a passing
verdict. Corrections create a new artifact id with a link back and a reason.
Do not edit this directory to fix a mistake in it.

## Replay

```
tools/replay.sh corpus/artifacts/g-2026-0002
```

Fetches the 1.6 MB bridge file, installs the pinned IfcOpenShell, builds the
pinned IFClite glue in `witnesses/ifc-lite`, re-derives both bridge
observations, validates them against the 1.0.0 schema, re-runs the verdict
against the committed observations, and compares the result to
`verdict.json`. Exits non-zero on anything short of a full match.

The source-witness observation is **not** regenerated: the umbrella never
builds a decoder. To regenerate it, run in rvt-rs:

```
rvt-ifc 2024_Core_Interior.rvt -o out.ifc \
  --observation observations/rvt-rs.json \
  --artifact-id magnetar-2024-core-interior-slim
```

and copy the result here. Its committed hash is what the replay checks
against, so a decoder change that alters what rvt-rs sees on this artifact
fails the gate here as well as in rvt-rs.
