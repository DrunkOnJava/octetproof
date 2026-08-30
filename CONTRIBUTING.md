# Contributing to OctetProof

Three kinds of contribution, in descending order of how much the project
needs them: **register a witness**, **record an edge**, **improve the tools**.

Everything here is enforced by `.github/workflows/verdict.yml`, which is
fail-closed. A pull request that cannot produce a PASS verdict on every
corpus artifact does not merge.

---

## 1. Registering a witness (SPEC.md §9.1)

A witness is an independently implemented reader of one node (format) that
can parse a golden artifact and emit an observation. Open a pull request
adding an entry to `registry/witnesses.json`.

Your entry must declare:

| Field | Required | What it means |
|---|---|---|
| `id` | yes | lowercase, hyphenated, stable forever |
| `kind` | yes | `reader` or `author` |
| `node` | yes | the format it reads, from `nodes[]` |
| `repo` | yes | public repository, or `null` for a commercial SDK |
| `license` | yes | SPDX identifier, or the exact commercial terms |
| `language` | yes | implementation language |
| `status` | yes | `candidate` on submission; `adopted` only after an agreement uses it |
| `lineage` | if derived | the id of the witness yours is built on |
| `checked` | on verification | ISO date the entry was verified against upstream |
| `notes` | recommended | coverage claims, caveats, version facts |

And, in the pull request body:

- **Coverage declaration.** Which fields of the controlled vocabulary you
  claim. Today that vocabulary is `entity_counts`; `layer_topology`,
  `linework`, `bounding_boxes`, `xdata_fields` and `text_content` are
  specified but not yet exercised. Declaring a field you cannot actually
  parse is a registration violation and grounds for removal.
- **A version pin.** An exact git SHA or release tag, or the exact PyPI /
  crates.io / NuGet specifier the CI gate will install. Floating ranges are
  forbidden. A witness update is a separate pull request that includes the
  new version, a diff of its observation output on the existing corpus, a
  justification for any change in declared coverage, and recomputation of
  every affected verdict. Silent witness upgrades are a protocol violation
  (§9.6).
- **A determinism statement.** Whether your witness produces bit-identical
  canonical observations on identical bytes across two runs, two operating
  systems, and two architectures — and which of those you have actually
  tested. Partial attestation is fine; overclaiming is not.
- **A lineage statement.** If your reader is an FFI binding, a port, a
  wrapper, or was derived from another registered witness's source or notes,
  say so. Independence is counted by lineage, not by repository name.

### Independence (SPEC.md §9.3)

A PASS verdict requires the agreeing witnesses to span at least two distinct
implementation lineages, include at least one bridge-format reader and at
least one source-format reader, and not consist solely of GPL/AGPL readers.
Witnesses derived from the same reverse-engineering notes or the same sample
set are correlated and do not count as independent even if the code differs.

The registry already records several such pairs as one witness: uncad over
LibreDWG, FreeCAD BIM over IfcOpenShell, GDAL's DGN driver over dgnlib,
Ara3D's mesh side over web-ifc.

### Licensing rules

| License | May participate | How |
|---|---|---|
| Apache-2.0, MIT, BSD, MPL-2.0 | yes | preferred |
| LGPL (any version) | yes | separate process only; never linked |
| GPL, AGPL | yes, secondary | separate process only; never the sole agreeing pair |
| Commercial (ODA, DATAKIT, …) | no | excluded from the gate; offline research only |
| No declared license | no | cannot be adopted at all until licensed |

**No GPL linking, ever.** Copyleft witnesses are invoked as isolated
subprocesses that read a file and write JSON. Nothing in `tools/` links,
imports, statically embeds, or vendors copyleft code, and nothing may start.
The gate runs two witnesses today, both at arm's length:

- **IfcOpenShell** (LGPL-3.0) is installed from PyPI at run time and executed
  as a separate Python process, which is stricter than LGPL requires.
- **IFClite** (`ifc-lite-core`, MPL-2.0) is fetched from crates.io at the
  exact pinned version and compiled into `witnesses/ifc-lite`, which is
  **its own Cargo workspace root** and is built by nothing else here. MPL-2.0
  is a file-level copyleft and does link, so the isolation is structural: no
  Apache-2.0 artifact in this repository contains it, and no file of it is
  modified or redistributed.

A witness whose driver cannot be written in the standard library goes in
`witnesses/<id>/`, not in `tools/`, and its manifest entry declares
`runner_kind`. `tools/check-registry.py` will refuse the build unless the
registry version, the package-manager pin, the manifest `version_pin` and the
version constant the binary stamps into its observations are one number
(§9.6).

**Clean-room rule.** Contributions to a *decoder* that participates as a
witness must be clean-room with respect to the format it decodes: derived
from observation of bytes, published specifications, and your own analysis —
never from decompiled vendor binaries, leaked internal documentation, or
copy-pasted code from a copyleft or commercial reader. Consulting another
reader's comments or issue threads for a factual disambiguation is allowed
and must be recorded in that repository's clean-room log with the exact
source. Reading another reader's implementation and reproducing its logic is
not allowed. This repository will not accept an artifact, observation, or
verdict produced by a decoder whose provenance is unclear on this point.

---

## 2. Recording an edge

An edge is an export path from one node to another, produced by a named
authoring witness. Recording one is the highest-value contribution, and the
only step that needs a licensed seat of the authoring application.

1. **Export once.** Open the source file in the authoring application and
   export to the bridge format. Record the exact build string, the export
   mode, and every setting. Per §12.3, the first artifact of each
   export-mode class should carry a screen recording or structured event log
   showing the file open, the export dialog with settings visible, the
   export, and the resulting hash. Recordings may be redacted for sensitive
   geometry; the settings panel and the hash must remain legible.
2. **Publish the bytes somewhere durable and fetchable, under a license that
   permits it.** This repository does not redistribute source or bridge
   files. It records their SHA-256, byte length, license and origin URL. If
   the bytes cannot be made publicly fetchable, the artifact cannot be
   replayed by a stranger, and it does not belong in the corpus.
3. **Add the artifact.** Create `corpus/artifacts/<id>/manifest.json` in the
   §6.1 shape — see `g-2026-0001` for a worked example. Assign the next
   `g-YYYY-NNNN` id. State the semantic surface you claim and the fields you
   exclude, each exclusion carrying a reason and a tracking issue.
4. **Commit the observations.** Run each witness, commit the resulting
   observation under `observations/`, and commit the verdict. Write a
   `PROVENANCE.md` saying what is recorded and, more importantly, what is
   not.
5. **Regenerate the chain.** `python3 tools/index.py`, then
   `python3 tools/index.py --check` to confirm.
6. **Replay it.** `tools/replay.sh corpus/artifacts/<id>` must exit 0 before
   you open the pull request.

Artifacts are immutable once merged with a passing verdict (§8.3).
Corrections create a new artifact with a new id, a link to the superseded
one, and a reason. Do not edit a merged manifest to fix a mistake; supersede
it.

---

## 3. Improving the tools

- **Python 3.12 standard library only**, plus the witnesses themselves. This
  is a hard constraint, not a preference: the replay protocol's value is that
  a stranger can run it, and every added dependency is a reason it will not
  run in five years. `tools/check-registry.py` implements the JSON Schema
  subset the registry uses rather than depending on `jsonschema`, for exactly
  this reason. The constraint binds `tools/`; a witness driver under
  `witnesses/` is whatever language its reader needs, with its dependency
  tree pinned by a committed lock file and built with `--locked`.
- **Canonicalization is load-bearing.** Sorted keys, no insignificant
  whitespace, UTF-8, SHA-256. Any change to how a payload is canonicalized
  changes every committed observation hash and is a major version bump of the
  spec (§16.1). Do not touch it casually.
- **The gate stays fail-closed.** A missing witness, an unreachable origin, a
  crashed parser and an empty corpus all fail the build. Never add a code
  path where absence of evidence becomes evidence of agreement.
- **The umbrella never parses a byte.** No decoder source, no format parsing,
  no vendored binaries. If a change would make this repository read a `.rvt`
  or a `.dwg` directly, it belongs in a decoder repository instead. The
  drivers in `witnesses/` are the one adjacent thing that is allowed, and
  only on that condition: they may hash an input, count what a manifest
  names via a third-party reader, and emit an observation. The moment one of
  them contains format-parsing logic of its own it has stopped being glue.

Pull requests are squash-merged. Use conventional commit subjects.

---

## Code of conduct

By participating you agree to the [Code of Conduct](CODE_OF_CONDUCT.md).

## Security

Do not open a public issue for a vulnerability. See [SECURITY.md](SECURITY.md).
