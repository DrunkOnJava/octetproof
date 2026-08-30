# Layer 3 — the witness registry

`witnesses.json` is the machine-readable index of every participating reader
and author, the formats they read, the golden artifacts, the recorded edges,
and the agreements that gate them. `witness-registry.schema.json` is its
schema.

**A witness not in this registry is not tested.** The registry is the single
source of truth for what the CI gate runs (SPEC.md §5.3).

## Which copy is canonical

`registry/witnesses.json` here is a **copy** of
`research/witness-registry.json` in
[DrunkOnJava/rvt-rs](https://github.com/DrunkOnJava/rvt-rs).

**The rvt-rs copy is the working copy and remains authoritative for now.**
rvt-rs has `tests/witness_registry.rs`, which keeps the registry internally
consistent and in sync with the project-count manifests that carry the
artifact hashes. That test does not exist here, and duplicating it would mean
duplicating the fixtures it reads.

The two files are deliberately kept **byte-diffable**: identical structure,
identical ids, identical field names, no reordering, no umbrella-only fields.
Changes should be made in rvt-rs and copied here, and

```
diff <(python3 -m json.tool ../rvt-rs/research/witness-registry.json) \
     <(python3 -m json.tool registry/witnesses.json)
```

should be empty.

The umbrella becomes canonical when the second edge (RVT → DWG) is recorded
and gated here — at that point the registry describes witnesses for a node
that rvt-rs does not read, and rvt-rs becomes the consumer. When that
happens, this section is deleted and rvt-rs's copy becomes the mirror.

## Field mapping to the specification

SPEC.md §5.3 illustrates the registry as a `registry.yaml` with a different
field vocabulary. **§5.3.1 is the normative mapping between the two
encodings**, and a conforming implementation may use either. This file uses
the JSON encoding. The correspondence in brief, per §5.3.1:

| Spec field | Here | State |
|---|---|---|
| `id`, `language`, `license` | same names | implemented |
| `copyleft` | derived from `license` | not stored; the gate reads `GPL*`/`AGPL*` as strong copyleft and `commercial` as gate-ineligible |
| repository reference (§9.1) | `repo` as `owner/name`, or `null` | implemented |
| lineage rule (§9.3) | `lineage` | implemented |
| `role: primary_source_witness` | not stored | role is per-verdict, resolved from the observation's `input_role` against the manifest hashes |
| — | `kind`, `node`, `status`, `priority`, `checked`, `notes` | extensions beyond the spec vocabulary |
| `ci_eligible` | see below | implemented **per artifact**, not per witness |
| coverage declaration (§9.4) | see below | still per-run only |

Two of those deserve saying plainly, because §5.3.1 marks both "umbrella
scope" and the umbrella only half-delivers them today:

- **`ci_eligible` is per artifact, not per witness.** An artifact manifest's
  `witnesses.bridge[].mode` is `ci-runnable` or not, and
  `tools/check-registry.py` refuses a `ci-runnable` witness whose registry
  `status` is not `adopted`. That is stricter than a registry boolean in one
  way (it is stated per artifact, where runnability actually varies) and
  weaker in another (a witness cannot declare itself ineligible everywhere at
  once). A registry-level `ci_eligible` field is the right fix and is not
  implemented.
- **There is still no standing coverage declaration.** A witness declares
  `semantic_surface_covered` per run, inside each observation. §9.4 wants that
  declared once in the registry so a manifest can select witnesses by
  coverage. Not implemented.

## What the gate reads from it

`tools/verdict.py --registry` enforces the §9.3 independence set from these
fields:

| Field | Used for |
|---|---|
| `license` | commercial witnesses are dropped from the gate entirely; GPL/AGPL witnesses may not be the sole agreeing pair |
| `lineage` | two witnesses sharing a lineage count as one; absent `lineage` means the witness is its own lineage |
| `status` | only `adopted` witnesses may be `ci-runnable` in an artifact manifest |
| `id` | must match the `witness_id` in every observation |

`tools/check-registry.py` validates the file against the schema and checks
the cross-references the schema cannot express: every node, witness, edge and
agreement referenced anywhere must be declared, and every witness a corpus
manifest names must exist here with the right status. It also enforces §9.6
version pinning for any witness the umbrella builds itself — a bridge witness
declaring `runner_kind: "cargo"` must have its registry `version`, its
runner's exact `crate = "=X.Y.Z"` Cargo pin, a committed `Cargo.lock`, the
manifest's `version_pin` string and the `WITNESS_ID`/`WITNESS_VERSION`
constants in the runner's `src/main.rs` all agree. That mirrors rvt-rs's
`tests/witness_registry.rs::ifc_lite_gate_is_wired_and_version_pinned`, which
cannot be imported here because the umbrella has no Rust test harness. CI
runs the whole check on every push.

## Honesty rules baked into the data

- **Listing is not endorsement.** Most entries are `candidate`, meaning
  "known to exist, not yet used in an agreement". Of 47 entries, five are
  `adopted`: rvt-rs, dwg-rs, autodesk-revit-exporter, ifcopenshell and
  ifc-lite.
- **Claims stay the project's own.** A coverage or pass-rate figure in a
  candidate's `notes` — jDwgParser's "100% entity types, 92% sample pass
  rate", for instance — is that project's claim, not a measurement made here.
  It becomes a fact of this registry only when an agreement reproduces it.
- **`checked` means verified against upstream on that date**, usually via the
  GitHub API. An entry without `checked` was carried from an earlier survey
  and has not been re-verified. Absence of the field is information.
- **Unlicensed projects cannot be adopted.** `reviter` has no license file and
  stays a candidate until it has one, regardless of technical merit.

## Known unresolved entries

None outstanding. The one entry that was listed here — `ifc-lite` — is
resolved.

**`ifc-lite`, resolved 2026-08-30.** It was carried as `license: MIT` against
a bare `ifc-lite` in `repo` rather than an `owner/name`, with no `checked`
date, because neither the license nor the upstream had been verified: the
specification draft said MPL-2.0, the registry said MIT, and a GitHub search
returned candidates that disagreed. SPEC.md §19 note 4 recorded the entry as
gate-ineligible until that was settled.

What it resolved to:

| | |
|---|---|
| Upstream | `LTplus-AG/ifc-lite` — the `repository` field of the crate itself |
| Crate | `ifc-lite-core` **7.1.1**, published 2026-08-27 (crates.io API). A bare `ifc-lite` crate does not exist, which is why the old entry could not be verified |
| License | **MPL-2.0**, read on 2026-08-30 from both the crate metadata and the GitHub API's license object for that repository — so the old `MIT` was wrong, and so was the bare slug |
| Language | Rust, own byte-level STEP scanner plus a nom tokenizer; it links no IfcOpenShell code |
| Lineage | its own. The project *verifies its geometry kernel against* IfcOpenShell, which is a comparison, not a shared lineage — the same distinction that makes FreeCAD BIM and IfcOpenShell one witness and these two |
| Status | `adopted`, `checked: 2026-08-30`, `version: 7.1.1` |

`zahmadsaleem/ifc-lite-headless`, the other candidate the search turned up, is
a different project and is not what is adopted. SPEC.md §5.3, §18 and
§19 note 4 carry the same resolution.

It is now the third witness in the gate, running against both corpus
artifacts through the vendored glue at `witnesses/ifc-lite/` (Apache-2.0,
mirrored from rvt-rs). The §9.6 pin is held to one number —
`ifc-lite-core = "=7.1.1"` in that crate's `Cargo.toml`, the `version` field
here, each manifest's `version_pin`, and the `WITNESS_VERSION` the binary
stamps into every observation — by `tools/check-registry.py`, which fails if
any of the four drifts.

## Registering

See [CONTRIBUTING.md](../CONTRIBUTING.md#1-registering-a-witness-specmd-91).
