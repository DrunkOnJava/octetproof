# Security Policy

## Reporting a vulnerability

Report privately through **GitHub Security Advisories**:

https://github.com/DrunkOnJava/octetproof/security/advisories/new

Do not open a public issue, pull request, or discussion for a vulnerability.
GitHub advisories give us a private fork to develop and review a fix before
anything is disclosed.

If you cannot use GitHub advisories, email **griffinradcliffe@gmail.com**
with "octetproof security" in the subject.

Expect an acknowledgement within 72 hours and an assessment within 7 days.
Reporters are credited in the advisory unless they ask not to be.

## Supported versions

The `main` branch is the only supported version. There are no maintained
release branches.

## What is in scope

This repository is a metadata and verification layer. It parses no binary
formats, so the classic memory-safety surface of a decoder is not here. The
real attack surface is the integrity of the verification claims:

- **A path to a false PASS.** Anything that makes the gate report agreement
  where none exists: a way to bypass the independence check (§9.3), to make
  a single witness satisfy a two-witness requirement, to have an excluded
  field silently absorb a real disagreement, or to make a non-deterministic
  witness look deterministic.
- **Canonicalization collisions or ambiguity.** Two semantically different
  observations that canonicalize to the same bytes, or one observation that
  canonicalizes differently across platforms or Python versions.
- **Hash-chain weaknesses.** Anything that lets a merged manifest, observation
  or verdict be altered without invalidating `corpus/MANIFEST_INDEX.json`.
- **Provenance forgery.** A way to present a bridge file as having come from
  a source or an authoring witness it did not.
- **Fetch-path issues.** Anything that lets `tools/fetch.py` accept bytes that
  do not hash to the recorded value, or that lets a redirect or a compromised
  origin reach a witness before the hash check.
- **Code execution in the tools or the workflow.** Injection through a
  manifest field, a registry entry, an observation, or a witness's output;
  workflow injection through untrusted event payloads.
- **Supply chain.** An unpinned or spoofable action, or a witness install
  specifier that can resolve to something other than the pinned release.

## What is out of scope

- **Vulnerabilities in a witness.** Report those to that project. If a witness
  bug produces a wrong observation, that is a protocol event, not a security
  issue here — the cross-witness comparison exists precisely so a single bad
  reader cannot produce a false PASS.
- **Vulnerabilities in a decoder.** rvt-rs and dwg-rs have their own security
  policies. Report there.
- **Malicious content in a golden artifact's referenced bytes.** Those files
  are fetched from third-party origins and hash-verified; they are never
  executed here.
- **A colluding set of witnesses.** Explicitly out of the threat model
  (SPEC.md §4.2). The mitigation is diversity of origin, not cryptography.
- **The absence of the Ed25519 chain-root signature** (§12.2) and of
  per-witness container isolation (§10.3). Both are known, documented gaps
  listed in the README, not undisclosed vulnerabilities. Reports that these
  weaken the chain's guarantees are welcome as issues, not advisories.

## Threat model

See SPEC.md §4 for what the protocol defends against and §15 for the security
considerations the design already accounts for.
