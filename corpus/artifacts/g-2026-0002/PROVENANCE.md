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
| Witness set (`W_set`) | rvt-rs 0.1.2 → `70f8df9dd188b7e42947bfa167b2810333b3d0dc4398019ea40570b7fcb87c24`; IfcOpenShell 0.8.5 → `5a101408488d591d4e7d15fe39969f1ee295c282dfe53c1f093468ae3e5cb2d0`; IFClite 7.1.1 → `5a101408488d591d4e7d15fe39969f1ee295c282dfe53c1f093468ae3e5cb2d0` |
| Verdict (`V`) | PASS — 13 surface fields, 0 diffs, 3 excluded, independence satisfied across three lineages |
| Protocol | OctetProof 1.1.0 (`manifest.json`'s `octetproof_version`) |
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
what a thin reference can support and what only a real project schedule can.

## The thirteen surface fields

Three agreement classes are claimed here — counts, one relation pair set, one
storey set — and all three come out exact at tolerance 0.

| Field | Class | Agreed value |
|---|---|---|
| `entity_counts.IFCBUILDINGSTOREY` | count | 15 |
| `entity_counts.IFCWALL` | count | 360 |
| `entity_counts.IFCSLAB` | count | 80 |
| `entity_counts.IFCROOF` | count | 0 |
| `entity_counts.IFCDOOR` | count | 132 |
| `entity_counts.IFCWINDOW` | count | 6 |
| `entity_counts.IFCCOLUMN` | count | 256 |
| `entity_counts.IFCBEAM` | count | 0 |
| `entity_counts.IFCFLOWTERMINAL` | count | 0 |
| `entity_counts.IFCUNITASSIGNMENT` | count | 1 |
| `entity_counts.IFCSHADINGDEVICE` | count | 20 |
| `relations.IFCRELFILLSELEMENT` | relation pair set (§7.2, 1.1.0) | 138 `[host Tag, filling Tag]` pairs |
| `storeys.IFCBUILDINGSTOREY` | storey set (§7.2, 1.1.0) | 15 `[name, elevation]` pairs |

The last two are stronger claims than any count, and they are stronger in
different directions:

- **The relation pair set is about topology.** Two witnesses can agree on 138
  `IfcRelFillsElement` instances while disagreeing about every wall those
  openings belong to. Agreement on the pair set means the decoder put every
  one of the 132 doors and 6 windows into the *same host wall* Revit did —
  138 of 138, no wrong host, no missing pair, no extra pair. The pairs are
  ElementIds, so this gates identity recovery rather than cardinality
  (rvt-rs#222).
- **The storey set is about labels and units.** It carries the same fifteen
  pairs the thin sibling does, `Basement 2` at −40 ft through `Level 13` at
  185.5 ft, with each witness resolving its own file's declared `LENGTHUNIT`
  before emitting. Revit's export declares `FOOT`; rvt-rs writes `METRE`. The
  raw `Elevation` numbers of the two faithful sides differ by 3.28, so the
  field would be undiffable without the normalisation — which makes unit
  handling part of the claimed surface instead of an implementation detail
  (rvt-rs#218).

## What is excluded, and why

Three categories, all `known_gap`, all first-class exclusions carrying their
rvt-rs tracking issue, none ever diffed:

| Excluded field | Category | Export | rvt-rs | Reason | Tracking |
|---|---|---|---|---|---|
| entity_counts.IFCSPACE | rooms_spaces | 116 | 18 | known_gap | rvt-rs#33 |
| entity_counts.IFCMATERIAL | materials | 10 | 102 | known_gap | rvt-rs#34 |
| entity_counts.IFCPROPERTYSET | property_sets | 0 | 854 | known_gap | rvt-rs#35 |

Two of the three run the *other* way, which is worth saying because
under-count is the failure mode people expect. `materials` is an over-count —
102 recovered against 10 exported, because rvt-rs recovers partition
display-name materials and does not model the export's 150
`IfcMaterialConstituentSet` / 309 `IfcMaterialConstituent`. `property_sets`
is an over-count against zero: the ReferenceView_V1.2 export carries no
`IfcPropertySet` at all — confirmed independently by both bridge readers —
while rvt-rs emits 854 `RvtElementRecordGeometry` sets, one per element it
recovered from a partition element record. Neither side is a subset of the
other, and no rvt-rs set carries a Revit element parameter yet.

**Three exclusions is the honest count, and it used to be nine.** The walls,
doors, windows, columns, slabs and shading devices that sat in this table as
measured gaps were closed by rvt-rs #211, #212, #204 and #212 respectively,
and `levels` by #218; each is now an exact id-set match inside the surface
above. The remaining three are the real, still-open gap between an
independent decoder and Revit's own exporter on a real project schedule. The
gate refuses to diff them so that none can be quietly reclassified as
agreement.

## Three lineages, two of which hash identically

Three witnesses, three implementation lineages (§9.3): rvt-rs reads the
`.rvt`; IfcOpenShell (C++/Python, LGPL-3.0) and IFClite (`ifc-lite-core`
7.1.1, Rust, MPL-2.0, own byte-level STEP scanner) each read the `.ifc`
independently.

**The two bridge observations have the same canonical payload hash,
`5a101408488d591d4e7d15fe39969f1ee295c282dfe53c1f093468ae3e5cb2d0`.** Two
unrelated STEP readers — different languages, different parsing strategies,
no shared code — produced byte-identical canonical payloads for all fourteen
entity types, all 138 relation pairs and all 15 storey pairs on a 1.6 MB,
19,879-instance file. On the storey set that includes the unit resolution:
IfcOpenShell reached feet through `ifcopenshell.util.unit.calculate_unit_scale`
and IFClite through `ifc_lite_core::extract_length_unit_scale`, and the two
rendered the same six-decimal strings.

That is corroboration of the bridge-side reading, not extra evidence about
the source side. It says the two readers agree about what is in the file.

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

## Where the two artifacts' manifests differ

Both now carry all three normative blocks — `counts`, `relations` and
`storeys` — mirrored from the rvt-rs project-count fixture under the drop
rules in `corpus/README.md`. They differ on one row, and the difference is
the whole argument for keeping both artifacts:

| Block | Here | g-2026-0001 |
|---|---|---|
| `relations.IFCRELFILLSELEMENT` | `known` — 138 pairs inside the surface | `decoder_baseline` — the 20 KB fixture carries no `IfcRelFillsElement`, so the two sides are not comparable |
| `storeys.IFCBUILDINGSTOREY` | `known` — 15 pairs | `known` — the same 15 pairs |

A thin artifact supports a thin surface, except where it does not: Revit
writes the complete spatial hierarchy into even a one-element export, so the
storey set is as strong on the fixture as it is here, while the relation set
is available only here. SPEC.md §20.1 and §20.2 record the same split.

## Immutability

Per §8.3 this artifact is immutable in the sense that matters: the bytes it
names, the edge it records and the id it carries do not change, and a
correction to any of those creates a new artifact id with a link back and a
reason. Do not edit this directory to fix a mistake in it. Re-recording the
verdict when a witness is added or the decoder recovers more is not such a
correction.

## Replay

```
tools/replay.sh corpus/artifacts/g-2026-0002
```

Fetches the 1.6 MB bridge file, installs the pinned IfcOpenShell, builds the
pinned IFClite glue in `witnesses/ifc-lite`, re-derives both bridge
observations, validates them against the 1.1.0 schemas, re-runs the verdict
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
