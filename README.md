# OctetProof

A public, license-free protocol for verifying readers of undocumented binary
formats — and the corpus, registry and CI gate that make one instance of it
real today.

This is a meta-repository. **It never parses a byte.** The decoders live in
their own repositories and are only referenced from here.

---

## The thesis

Closed binary formats are not a reverse-engineering problem. They are a
verification-graph problem.

- A **node** is a file format: RVT, DWG, DXF, IFC, glTF, STEP, E57.
- An **edge** is an export path from one node to another, produced once by a
  named **authoring witness** — for RVT today, a licensed Autodesk Revit
  session exporting to IFC or DWG.
- A **witness** is an independently implemented reader of a node: rvt-rs for
  RVT, dwg-rs for DWG, IfcOpenShell for IFC.

For a format with no specification, correctness cannot mean "matches the
spec". There is no spec. It means:

> **N independent witnesses agree across M format boundaries**, on named
> artifacts, within stated tolerances, with every observation hashed, every
> comparison replayable by a stranger, and the whole thing gated in CI.

A single implementation can be wrong in a correlated way and still look
right. In rvt-rs, a checksum-paging bug silently dropped roughly 48% of the
schema on large streams — the decoder reported success and produced
plausible output. Nothing inside that decoder could have caught it. Two
independently implemented readers agreeing is evidence. Agreement across a
format boundary is stronger evidence, because the two witnesses never shared
a codebase or a sample set.

**Provenance is the other half.** Every claim here records which Revit build
authored the file, what export mode produced the bridge file, the SHA-256 of
both, and exactly which witness at which version parsed which bytes. Nothing
is "verified" in the abstract; it is verified on a named artifact by a named
pair.

**A vendor seat is needed once, not forever.** Producing an edge requires the
authoring application. Verifying against that edge, replaying it, and
extending it does not. After the first export, everything in this repository
runs on open tools with no license.

---

## What exists today

**One recorded, gated edge. Two artifacts on it, three independent witnesses.**
It is still one edge, and this section says so precisely.

| | |
|---|---|
| Edge | RVT → IFC, via the Autodesk Revit 2024 exporter |
| Source | `2024_Core_Interior.rvt`, 33,718,272 bytes, MIT, from magnetar-io/revit-test-datasets — the same file behind both artifacts |
| Source witness | rvt-rs 0.1.2 (Apache-2.0, Rust) reading the `.rvt` |
| Bridge witnesses | IfcOpenShell 0.8.5 (LGPL-3.0, C++/Python) and IFClite `ifc-lite-core` 7.1.1 (MPL-2.0, Rust, own STEP scanner), each reading the `.ifc` |
| Independence (§9.3) | satisfied on both artifacts: three lineages, one source reader, two bridge readers, no GPL-only pair, no commercial witness |

| Artifact | Bridge file | Verdict |
|---|---|---|
| `g-2026-0001` (alias `magnetar-2024-core-interior`) | `2024_Core_Interior.ifc`, 20,392 bytes, IFC4 — an element-export fixture | **PASS** — 8 surface fields, 0 diffs, 4 excluded |
| `g-2026-0002` (alias `magnetar-2024-core-interior-slim`) | `2024_Core_Interior_slim.ifc`, 1,665,968 bytes, IFC4, 19,879 entities — the full project export | **PASS** — 4 surface fields, 0 diffs, 9 excluded |

**The two artifacts share the same `.rvt` and the same committed rvt-rs
observation.** Only the Revit-authored bridge file differs, which makes the
pair a direct measurement of how much of the first verdict was real.

**g-2026-0001 is thin, and the second artifact is why we know that.** Its
eight agreeing fields are entity counts for IFCWALL, IFCROOF, IFCDOOR,
IFCWINDOW, IFCCOLUMN, IFCBEAM, IFCFLOWTERMINAL and IFCUNITASSIGNMENT — and
seven of the eight are zero on both sides, because the reference IFC is a
20 KB element-export fixture rather than a project schedule. Three
independent readers agreeing that a file contains no doors is a real
agreement and a weak one. It exercises the whole machine — fetch by hash,
three witnesses, canonical observations, an independence check, a replay, a
fail-closed gate — on a bridge file that carries almost nothing.

Four fields are excluded there first-class, because rvt-rs cannot yet recover
them and says so rather than pretending:

| Excluded field | Category | Reason | Tracking |
|---|---|---|---|
| entity_counts.IFCSHADINGDEVICE | floors | known_gap: floor slab extrusion thickness | rvt-rs#31 |
| entity_counts.IFCSPACE | rooms / spaces | known_gap: typed door/window discrimination and host binding | rvt-rs#33 |
| entity_counts.IFCMATERIAL | materials | known_gap: Revit compound assemblies and WallType widths | rvt-rs#34 |
| entity_counts.IFCPROPERTYSET | property sets | known_gap: typed door/window discrimination and host binding | rvt-rs#35 |

An excluded field never appears in a disagreement. If it does, the manifest
is wrong, not the witness (SPEC.md §7.1).

### g-2026-0002: the same model against a real project schedule

The full export is where the decoder is actually measured, and the numbers
are not flattering. Both bridge readers count, independently and identically:

| Category | The Revit export has | rvt-rs recovers | Status |
|---|---|---|---|
| walls (IFCWALL) | **360** | 0 | known_gap, rvt-rs#30 |
| doors (IFCDOOR) | **132** | 0 | known_gap, rvt-rs#32 |
| columns (IFCCOLUMN) | **256** | 0 | known_gap, rvt-rs#204 |
| rooms / spaces (IFCSPACE) | **116** | 18 | known_gap, rvt-rs#33 |
| floors (IFCSLAB) | **80** | 64 | known_gap, rvt-rs#31 |
| levels (IFCBUILDINGSTOREY) | **15** | 12 | decoder_baseline, rvt-rs#33 |
| windows (IFCWINDOW) | 6 | 0 | known_gap, rvt-rs#32 |
| materials (IFCMATERIAL) | 10 | 102 | known_gap, rvt-rs#34 — an over-count |
| property sets (IFCPROPERTYSET) | 0 | 64 | known_gap, rvt-rs#35 — an over-count against zero |

So the claimed surface on that artifact is **four fields** — IFCROOF,
IFCBEAM, IFCFLOWTERMINAL and IFCUNITASSIGNMENT — of which only
IFCUNITASSIGNMENT is non-zero. A wider claim would be a false one while 360
walls, 132 doors and 256 columns go unrecovered. **The nine-row table above
is the deliverable, not a footnote to it:** it is a measured gap between an
independent decoder and Revit's own exporter on a real project, each row
carrying its tracking issue, and the gate refuses to diff any of them so that
none can be quietly reclassified as agreement.

### The third witness

IFClite (`ifc-lite-core` 7.1.1, MPL-2.0, Rust) was adopted on 2026-08-30 as a
second, independent reader of the bridge format. It has its own byte-level
STEP scanner and links no IfcOpenShell code; the project *verifies its
geometry kernel against* IfcOpenShell, which is a comparison, not a shared
lineage.

On both artifacts its canonical observation payload hashes **identically** to
IfcOpenShell's (`8cf40465…` on g-2026-0001, `882e1e0f…` on g-2026-0002). Two
unrelated STEP readers, in different languages, produced byte-identical
canonical payloads for every entity type on both files. That is corroboration
of the bridge-side reading and nothing more — it says the two readers agree
about what is in the file, not that `entity_counts` is a deep surface.

It runs in CI through `witnesses/ifc-lite/`, glue mirrored from rvt-rs, built
out of workspace so MPL-2.0 code is never linked into this Apache-2.0 tree.
**The umbrella still parses no format bytes itself** — the witness process
does.

---

## What is pending

- **The RVT → DWG edge.** This is the edge that turns the protocol from one
  lucky dataset into a method, because DWG has three independent readers
  (dwg-rs, ACadSharp, jDwgParser) and no shared lineage with the IFC side.
  It is blocked on exactly one thing: **a single licensed Revit session**
  exporting the owned and redistributable projects to DWG (R2018 and R2013).
  No Revit-exported DWG exists in any public corpus. The 2D plan-view export
  goes first — LINE, LWPOLYLINE, ARC, CIRCLE, TEXT, MTEXT, INSERT, HATCH plus
  the LAYER/LTYPE/BLOCK tables — with 3D ACIS solids deferred.
- **dwg-rs witness mode.** dwg-rs has no `--observation` flag yet, so it
  cannot emit an OctetProof observation. rvt-rs already can.
- **A surface deeper than entity counts.** Three witnesses now agree on
  `entity_counts`, which is a real but shallow claim: it says the readers
  count the same instances of the same types, not that they agree about
  geometry, placement, or property values. §11's faithful-export surface is
  much wider than what any manifest here claims, and the canonicalizer needs
  the full RFC 8785 number rules before a float-bearing surface can be
  trusted at all.
- **Anything that is not this one model.** Both artifacts are exports of the
  same `2024_Core_Interior.rvt`. A second source model would test the decoder
  rather than one file's worth of it.
- **From the spec, not yet implemented here:** container isolation per witness
  (§10.3), the Ed25519 chain-root signature (§12.2 — the hash chain exists,
  the signature does not), the export recording requirement (§12.3, and no
  recording exists for either artifact in the corpus — see their
  PROVENANCE.md files), determinism attestation across operating systems and
  architectures (§9.5, so the `NON_DETERMINISTIC` and `WITNESS_ERROR`
  statuses are in the vocabulary but are never produced), a registry-level
  `ci_eligible` flag and standing coverage declaration (§5.3.1 lists both as
  umbrella scope), and full RFC 8785 number and Unicode rules in the
  canonicalizer — the payloads in scope are integers and ASCII, so the
  JCS-lite implementation is sufficient today and will not be once a geometry
  surface carries floats.

---

## Repository layout

```
SPEC.md                         Layer 1 — the protocol, version 1.0.1 (CC-BY-4.0)
schemas/                          machine-checkable observation + verdict schemas
corpus/                         Layer 2 — golden artifacts
  MANIFEST_INDEX.json             hash chain over every manifest
  artifacts/g-2026-0001/          the element-export fixture
  artifacts/g-2026-0002/          the full project export, same .rvt
    manifest.json                 source + bridge hashes, counts, surface, exclusions
    PROVENANCE.md                 what is and is not recorded
    observations/                 committed witness observations
    verdict.json                  the recorded verdict
registry/                       Layer 3 — the witness registry
  witnesses.json                  nodes, witnesses, artifacts, edges, agreements
  witness-registry.schema.json
tools/                          Layer 4 — the gate (Apache-2.0)
  fetch.py                        fetch a golden file by origin, verify by hash
  witness-ifcopenshell.py         bridge witness → observation
  verdict.py                      diff function, independence, replay, statuses
  compare-verdict.py              fresh verdict vs committed record
  replay.sh                       all of the above, end to end
  validate-corpus.py              observations + verdicts against the schemas
  check-registry.py               registry cross-references + the §9.6 pin chain
  index.py                        rebuild / check the corpus hash chain
  jsonschema_mini.py              the JSON Schema subset the validators use
witnesses/                      witness glue — drivers, not readers (Apache-2.0)
  ifc-lite/                       drives the pinned MPL-2.0 ifc-lite-core crate
.github/workflows/verdict.yml   the CI gate itself
```

**Layer 5 — decoders — is not here.** By design:

| Repository | Node | Witness mode |
|---|---|---|
| [DrunkOnJava/rvt-rs](https://github.com/DrunkOnJava/rvt-rs) | RVT (source) | `rvt-ifc <file.rvt> -o out.ifc --observation PATH --artifact-id ID` |
| [DrunkOnJava/dwg-rs](https://github.com/DrunkOnJava/dwg-rs) | DWG (source) | none yet — pending |
| [IfcOpenShell/IfcOpenShell](https://github.com/IfcOpenShell/IfcOpenShell) | IFC (bridge) | driven here by `tools/witness-ifcopenshell.py` |
| [LTplus-AG/ifc-lite](https://github.com/LTplus-AG/ifc-lite) | IFC (bridge) | driven here by `witnesses/ifc-lite/` (crate `ifc-lite-core`, pinned `=7.1.1`) |

`witnesses/ifc-lite/` is ~300 lines of hashing, counting and JSON that shell
out to a third-party crate; it is mirrored from rvt-rs and is glue, not a
decoder. Every byte of IFC it reports on is parsed by `ifc-lite-core`, in its
own process, from its own workspace root so MPL-2.0 code never links into
this Apache-2.0 tree.

The umbrella consuming decoders as a monorepo would recreate the original
coordination problem at larger scale. Decoders ship independently, emit
observations, and are checked here. They do not self-certify.

---

## The corpus stores hashes, not bytes

No source or bridge file is redistributed. Each manifest records the SHA-256,
the byte length, the license and the public origin URL; the replay fetches
from that origin and refuses anything that does not hash to the recorded
value. That keeps the repository small, keeps redistribution questions out of
it, and makes "the bytes were swapped" a detectable event rather than a
silent one.

---

## Replay it yourself, in two commands

No vendor license, no special hardware, no Revit.

```bash
git clone https://github.com/DrunkOnJava/octetproof && cd octetproof
tools/replay.sh corpus/artifacts/g-2026-0002
```

That fetches the bridge file from its public origin and rejects it unless it
hashes to the recorded value, installs the pinned IfcOpenShell into a venv,
builds the pinned IFClite glue with `cargo build --release --locked`, runs
both bridge witnesses, copies in the committed rvt-rs observation, validates
everything against the 1.0.0 schemas, and prints:

```
g-2026-0002: PASS — witnesses ifc-lite, ifcopenshell, rvt-rs
  surface: 4 fields, excluded: 9, diffs: 0
  replay ifc-lite: match
  replay ifcopenshell: match
  replay rvt-rs: match
verdict matches the committed record (ignored: artifact_id, replay, timestamp, verdict_hash_sha256)
```

It exits 0 only on PASS with every observation replaying byte-for-byte and
the fresh verdict matching the committed one. Omit the argument for
`g-2026-0001`, which prints `surface: 8 fields, excluded: 4, diffs: 0` with
the same three witnesses.

The steps are individually runnable if you would rather see them:

```bash
python3 tools/fetch.py corpus/artifacts/g-2026-0002/manifest.json --which bridge --out _replay/slim.ifc
python3 -m venv .venv && .venv/bin/pip install 'ifcopenshell>=0.8,<0.9'
mkdir -p _replay/observations
.venv/bin/python tools/witness-ifcopenshell.py corpus/artifacts/g-2026-0002/manifest.json _replay/slim.ifc --observation _replay/observations/ifcopenshell.json
cargo build --release --locked --manifest-path witnesses/ifc-lite/Cargo.toml
witnesses/ifc-lite/target/release/witness-ifc-lite corpus/artifacts/g-2026-0002/manifest.json _replay/slim.ifc --observation _replay/observations/ifc-lite.json
cp corpus/artifacts/g-2026-0002/observations/rvt-rs.json _replay/observations/
python3 tools/verdict.py corpus/artifacts/g-2026-0002/manifest.json _replay/observations --out _replay/verdict.json --registry registry/witnesses.json --compare-committed corpus/artifacts/g-2026-0002/observations
```

The source witness observation is copied from the corpus rather than
regenerated, because the umbrella never builds a decoder — to regenerate it,
run the `rvt-ifc` witness command in rvt-rs and copy the result here.

Requirements: Python 3.12, IfcOpenShell, and a Rust toolchain ≥ 1.87 for the
IFClite glue. Everything else is standard library.

---

## Registering a witness

A witness is any independently implemented reader that can parse a node and
emit an observation. Open a pull request against `registry/witnesses.json`
declaring:

- **License and copyleft status.** Apache-2.0 / MIT / BSD / MPL-2.0 are
  preferred; LGPL runs as a separate process; GPL and AGPL may participate
  but never as the sole agreeing pair; commercial SDKs are excluded from the
  gate entirely.
- **Lineage.** If your reader is built on another registered witness — an FFI
  binding, a port, a wrapper — say so in `lineage`. Independence is counted by
  lineage, not by repository. uncad over LibreDWG, FreeCAD BIM over
  IfcOpenShell, GDAL's DGN driver over dgnlib: each pair is one witness.
- **Coverage.** Which fields of the controlled vocabulary you claim
  (`entity_counts` today). Declaring a field you cannot parse is a
  registration violation.
- **An exact version pin.** A git SHA or a release tag. Floating ranges are
  forbidden; silent upgrades are a protocol violation.

A witness not in the registry is not tested. Listing a witness is not a
capability claim, and a coverage figure quoted in a candidate's notes stays
that project's own claim until an agreement recorded here reproduces it.

Full process, including the clean-room rule and the no-GPL-linking rule:
[CONTRIBUTING.md](CONTRIBUTING.md).

---

## Status and licensing

Protocol version **1.0.1**, dated 2026-08-30. `SPEC.md` is the released
specification, not a draft: it supersedes the draft received from the project
owner on 2026-08-30, and its Section 19 lists every correction applied. The
draft, with its reviewer notes, is retained in rvt-rs at
`docs/octetproof-spec-draft.md`.

1.0.1 is a patch release (§19a): it resolves note 4's open `ifc-lite` license
question to MPL-2.0 against the exact upstream, and replaces the "umbrella
repository planned" wording now that this repository exists. **No schema,
diff-function or provenance rule changed**, so every document here still
declares `schema_version: "1.0.0"` and a 1.0.0 implementation remains
conformant. `SPEC.md` is a byte-identical copy of
`docs/octetproof-spec.md` in rvt-rs, the same policy as the registry.

Two of the spec's schemas are machine-checkable and shipped here:
`schemas/witness-observation.schema.json` (§6.2) and
`schemas/witness-verdict.schema.json` (§6.3). Every committed observation and
verdict in this corpus validates against them, and CI enforces it on every
push, including on observations freshly produced during the run.

- Code, tools, workflows, corpus metadata and registry: **Apache-2.0**
  (`LICENSE`).
- `SPEC.md`: **CC-BY-4.0** (`LICENSE-SPEC`), per its own header.
- See [NOTICE](NOTICE) for the split and for third-party attribution.
