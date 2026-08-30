//! Bridge witness: IFClite (`ifc-lite-core`, MPL-2.0, Rust) reads the golden
//! bridge file and emits an OctetProof observation (SPEC.md §6.2).
//!
//! Usage: witness-ifc-lite <manifest.json> <bridge_file>
//!                         --observation observations/ifc-lite.json [--json OUT]
//!
//! **Mirrored from `tools/ci/witness-ifc-lite/` in DrunkOnJava/rvt-rs at commit
//! `dbf23473e1be62cb8ed1a4fb552396c31899df9c` (PR #205).** The only change is
//! the manifest-reading code path: rvt-rs resolves `reference_ifc_file` under a
//! corpus directory and checks `source.reference_ifc_sha256`, while the
//! umbrella is handed the bridge file directly and checks
//! `bridge.file_hash_sha256`, `bridge.bytes` and `bridge.schema` — exactly the
//! contract `tools/witness-ifcopenshell.py` already implements here. Counting,
//! canonicalization, hashing, the manifest-drift check and the observation
//! shape are byte-for-byte the upstream behaviour. Keep the two in sync.
//!
//! **This is glue, not a decoder.** The umbrella parses no format bytes itself;
//! `ifc-lite-core` — a separate, MPL-2.0, out-of-tree crate — does, inside this
//! separate process, and never linked into anything Apache-2.0.
//!
//! The manifest (§6.1) is the only source of truth for what is counted: every
//! `counts` category carrying a `source_ifc_type` is counted, whatever its
//! status. Excluded (`known_gap` / `unsupported` / `decoder_baseline`) types
//! are counted and recorded too — the verdict tool is what refuses to diff them
//! (§7.1 rule 3), not the witness. A witness that silently dropped them would
//! make the exclusion unauditable.
//!
//! Counts use `ifc_lite_core::EntityScanner` (exact STEP keyword, no subtypes —
//! the same semantics as IfcOpenShell's `by_type(..., include_subtypes=False)`)
//! and are compared to `expected` within `tolerance`. Exit 1 on any drift or
//! hash mismatch.
//!
//! This is the third implementation lineage on the RVT → IFC edge: rvt-rs reads
//! the .rvt (source witness), IfcOpenShell and IFClite each read Revit's .ifc
//! (bridge witnesses) with no shared code.

use std::collections::BTreeMap;
use std::fs;
use std::io::{BufReader, Read};
use std::path::{Path, PathBuf};
use std::process::ExitCode;

use ifc_lite_core::EntityScanner;
use serde_json::{json, Map, Value};
use sha2::{Digest, Sha256};

/// Registry id of this witness. Must match the `id` of the `ifc-lite` entry in
/// registry/witnesses.json — tools/verdict.py resolves the lineage and license
/// from there by this key.
const WITNESS_ID: &str = "ifc-lite";

/// Exact pinned version of the reader (OctetProof §9.6). Kept in lockstep with
/// the `ifc-lite-core = "=X.Y.Z"` pin in Cargo.toml, the registry entry's
/// `version`, and every corpus manifest's `version_pin`;
/// tools/check-registry.py fails the build if the four ever drift.
const WITNESS_VERSION: &str = "7.1.1";

fn sha256_of(path: &Path) -> std::io::Result<String> {
    let mut hasher = Sha256::new();
    let mut reader = BufReader::new(fs::File::open(path)?);
    let mut buf = vec![0u8; 1 << 20];
    loop {
        let read = reader.read(&mut buf)?;
        if read == 0 {
            break;
        }
        hasher.update(&buf[..read]);
    }
    Ok(format!("{:x}", hasher.finalize()))
}

/// Canonical JSON per §7.3 / §8.4: sorted keys, no insignificant whitespace,
/// UTF-8. `serde_json` without the `preserve_order` feature stores objects in a
/// `BTreeMap`, so `to_string` already emits sorted keys with no whitespace —
/// byte-identical to Python's `json.dumps(..., sort_keys=True,
/// separators=(",", ":"))` for the integer/string payloads emitted here.
fn canonical_hash(value: &Value) -> String {
    let canonical = serde_json::to_string(value).expect("serialize canonical payload");
    format!("{:x}", Sha256::digest(canonical.as_bytes()))
}

/// Value of `FILE_SCHEMA` from the STEP header, e.g. `IFC4`. IfcOpenShell
/// reports the same string as `model.schema`, so the two bridge witnesses'
/// `ifc_schema` fields are directly comparable.
fn file_schema(bytes: &[u8]) -> Option<String> {
    let head = &bytes[..bytes.len().min(64 * 1024)];
    let text = String::from_utf8_lossy(head).to_uppercase();
    let start = text.find("FILE_SCHEMA")? + "FILE_SCHEMA".len();
    let rest = &text[start..];
    let open = rest.find('\'')?;
    let tail = &rest[open + 1..];
    let close = tail.find('\'')?;
    Some(tail[..close].trim().to_string())
}

/// Exact-keyword instance counts for the whole data section, upper-cased so the
/// lookup matches the manifest's `source_ifc_type` spelling regardless of how
/// the exporter cased the keyword.
fn count_by_exact_type(bytes: &[u8]) -> BTreeMap<String, usize> {
    let mut scanner = EntityScanner::new(bytes);
    let mut counts: BTreeMap<String, usize> = BTreeMap::new();
    for (type_name, n) in scanner.count_by_type() {
        *counts.entry(type_name.trim().to_uppercase()).or_insert(0) += n;
    }
    counts
}

struct Args {
    manifest: PathBuf,
    bridge_file: PathBuf,
    json: Option<PathBuf>,
    observation: Option<PathBuf>,
}

fn parse_args() -> Result<Args, String> {
    let mut positional: Vec<PathBuf> = Vec::new();
    let mut json = None;
    let mut observation = None;
    let mut argv = std::env::args().skip(1);
    while let Some(arg) = argv.next() {
        match arg.as_str() {
            "--json" => {
                json = Some(PathBuf::from(
                    argv.next().ok_or("--json needs a path".to_string())?,
                ))
            }
            "--observation" => {
                observation = Some(PathBuf::from(
                    argv.next()
                        .ok_or("--observation needs a path".to_string())?,
                ))
            }
            "-h" | "--help" => {
                println!(
                    "usage: witness-ifc-lite <manifest.json> <bridge_file> \
                     --observation OUT [--json OUT]"
                );
                std::process::exit(0);
            }
            other if other.starts_with('-') => return Err(format!("unknown flag {other}")),
            other => positional.push(PathBuf::from(other)),
        }
    }
    if positional.len() != 2 {
        return Err("usage: witness-ifc-lite <manifest.json> <bridge_file>".to_string());
    }
    let bridge_file = positional.pop().expect("two positionals");
    let manifest = positional.pop().expect("two positionals");
    Ok(Args {
        manifest,
        bridge_file,
        json,
        observation,
    })
}

fn run() -> Result<i32, String> {
    let args = parse_args()?;
    let manifest_text =
        fs::read_to_string(&args.manifest).map_err(|e| format!("read manifest: {e}"))?;
    let manifest: Value =
        serde_json::from_str(&manifest_text).map_err(|e| format!("parse manifest: {e}"))?;
    let bridge = manifest.get("bridge").cloned().unwrap_or(Value::Null);

    if !args.bridge_file.is_file() {
        return Err(format!(
            "bridge file missing at {}",
            args.bridge_file.display()
        ));
    }

    let actual_sha = sha256_of(&args.bridge_file).map_err(|e| format!("hash bridge file: {e}"))?;
    if let Some(expected) = bridge.get("file_hash_sha256").and_then(Value::as_str) {
        if expected != actual_sha {
            return Err(format!(
                "{}: sha256 {actual_sha} != manifest {expected}",
                args.bridge_file.display()
            ));
        }
    }
    let actual_bytes = fs::metadata(&args.bridge_file)
        .map_err(|e| format!("stat bridge file: {e}"))?
        .len();
    if let Some(expected) = bridge.get("bytes").and_then(Value::as_u64) {
        if expected != actual_bytes {
            return Err(format!(
                "{}: {actual_bytes} bytes, manifest says {expected}",
                args.bridge_file.display()
            ));
        }
    }

    let bytes = fs::read(&args.bridge_file).map_err(|e| format!("read bridge file: {e}"))?;
    let schema = file_schema(&bytes).unwrap_or_else(|| "UNKNOWN".to_string());
    if let Some(expected) = bridge.get("schema").and_then(Value::as_str) {
        if expected != schema {
            return Err(format!("schema {schema} != manifest {expected}"));
        }
    }
    let counts = count_by_exact_type(&bytes);

    let empty = Map::new();
    let categories = manifest
        .get("counts")
        .and_then(Value::as_object)
        .unwrap_or(&empty);

    // The umbrella never redistributes the bridge bytes, so the name recorded in
    // the observation is the origin's basename, exactly as
    // tools/witness-ifcopenshell.py records it.
    let origin = bridge.get("origin").and_then(Value::as_str).unwrap_or("");
    let input_file = match origin.rsplit('/').next() {
        Some(name) if !name.is_empty() => name.to_string(),
        _ => args
            .bridge_file
            .file_name()
            .map(|n| n.to_string_lossy().into_owned())
            .unwrap_or_default(),
    };

    let artifact_id = manifest
        .get("artifact_id")
        .and_then(Value::as_str)
        .unwrap_or("");
    println!(
        "{artifact_id}: {input_file} ({schema}, sha256 {}…)",
        &actual_sha[..12]
    );
    println!(
        "{:<16} {:<22} {:>8} {:>8} {:>4}  result",
        "category", "ifc type", "expected", "ifc-lite", "tol"
    );

    let mut drift = 0usize;
    let mut records = Vec::new();
    let mut entity_counts = Map::new();
    for (category, spec) in categories {
        let ifc_type = match spec.get("source_ifc_type").and_then(Value::as_str) {
            Some(t) => t,
            None => continue,
        };
        let expected = spec.get("expected").and_then(Value::as_i64).unwrap_or(0);
        let tolerance = spec.get("tolerance").and_then(Value::as_i64).unwrap_or(0);
        let actual = counts.get(&ifc_type.to_uppercase()).copied().unwrap_or(0) as i64;
        let ok = (actual - expected).abs() <= tolerance;
        if !ok {
            drift += 1;
        }
        records.push(json!({
            "category": category,
            "ifc_type": ifc_type,
            "expected": expected,
            "tolerance": tolerance,
            "ifc_lite": actual,
            "agree": ok,
        }));
        entity_counts.insert(ifc_type.to_string(), json!(actual));
        println!(
            "{category:<16} {ifc_type:<22} {expected:>8} {actual:>8} {tolerance:>4}  {}",
            if ok { "ok" } else { "DRIFT" }
        );
    }
    if entity_counts.is_empty() {
        return Err(
            "no manifest count category carries source_ifc_type — nothing to witness".to_string(),
        );
    }

    if let Some(path) = args.json.as_ref() {
        let record = json!({
            "schema_version": 1,
            "manifest": manifest.get("artifact_id").cloned().unwrap_or(Value::Null),
            "reference_ifc": input_file,
            "reference_ifc_sha256": actual_sha,
            "ifc_schema": schema,
            "witness": format!("{WITNESS_ID} {WITNESS_VERSION}"),
            "categories": records,
            "agree": drift == 0,
        });
        write_json(path, &record)?;
    }

    if let Some(path) = args.observation.as_ref() {
        let payload = json!({
            "entity_counts": Value::Object(entity_counts),
            "ifc_schema": schema,
        });
        let observation = json!({
            "schema_version": "1.0.0",
            "witness_id": WITNESS_ID,
            "witness_version": WITNESS_VERSION,
            "artifact_id": manifest.get("artifact_id").cloned().unwrap_or(Value::Null),
            "input_role": "bridge",
            "input_file": input_file,
            "input_hash_sha256": actual_sha,
            "deterministic": true,
            "semantic_surface_covered": ["entity_counts"],
            "observation": payload,
            "observation_hash_sha256": canonical_hash(&payload),
            "unsupported_entities": [],
            "warnings": [],
        });
        write_json(path, &observation)?;
    }

    if drift > 0 {
        eprintln!(
            "error: {drift} categor{} drifted from the manifest",
            if drift == 1 { "y" } else { "ies" }
        );
        return Ok(1);
    }
    println!("cross-witness: IFClite agrees with the manifest for every source_ifc_type");
    Ok(0)
}

fn write_json(path: &Path, value: &Value) -> Result<(), String> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(|e| format!("create {}: {e}", parent.display()))?;
    }
    let mut text = serde_json::to_string_pretty(value).map_err(|e| format!("serialize: {e}"))?;
    text.push('\n');
    fs::write(path, text).map_err(|e| format!("write {}: {e}", path.display()))
}

fn main() -> ExitCode {
    match run() {
        Ok(0) => ExitCode::SUCCESS,
        Ok(_) => ExitCode::FAILURE,
        Err(message) => {
            eprintln!("error: {message}");
            ExitCode::FAILURE
        }
    }
}
