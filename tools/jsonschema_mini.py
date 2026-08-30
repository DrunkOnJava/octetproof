#!/usr/bin/env python3
"""A deliberately small JSON Schema validator — the subset this repository's
schemas actually use, and nothing else.

Why not `jsonschema`: the protocol's dependency budget is "Python 3.12
standard library, plus the witness itself" (CONTRIBUTING.md). The replay
protocol's whole value is that a stranger can run it years from now with no
package resolution; adding a dependency to check three JSON files would spend
that for nothing.

Implemented keywords: `type` (including union types and `null`), `required`,
`properties`, `additionalProperties` (schema form and `false`), `items`,
`enum`, `const`, `pattern`, `minLength`, `minItems`, `uniqueItems`,
`minimum`. Annotation-only keywords (`$schema`, `$id`, `title`,
`description`) are ignored.

Anything else fails loudly: `check()` reports "schema uses constructs this
validator does not implement" rather than passing silently. A future schema
keyword therefore cannot quietly stop being enforced.

Python 3.12 standard library only.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ANNOTATION = {"$schema", "$id", "title", "description", "$comment", "examples", "default"}
IMPLEMENTED = {
    "type", "required", "properties", "additionalProperties", "items",
    "enum", "const", "pattern", "minLength", "minItems", "uniqueItems", "minimum",
}
SUPPORTED = ANNOTATION | IMPLEMENTED

TYPES = {
    "object": dict, "array": list, "string": str, "integer": int,
    "number": (int, float), "boolean": bool,
}


def _type_ok(node, allowed: list[str]) -> bool:
    if node is None:
        return "null" in allowed
    for name in allowed:
        expected = TYPES.get(name)
        if expected is None:
            continue
        # bool is a subclass of int in Python; integer/number must reject True.
        if isinstance(node, bool) and name in ("integer", "number"):
            continue
        if name == "boolean" and not isinstance(node, bool):
            continue
        if isinstance(node, expected):
            return True
    return False


def check(node, schema, path: str, errors: list[str]) -> None:
    """Validate `node` against `schema`, appending human-readable problems."""
    unsupported = set(schema) - SUPPORTED
    if unsupported:
        errors.append(f"{path}: schema uses constructs this validator does not implement: {sorted(unsupported)}")
        return

    declared = schema.get("type")
    if declared is not None:
        allowed = declared if isinstance(declared, list) else [declared]
        if not _type_ok(node, allowed):
            errors.append(f"{path}: expected {allowed}, got {'null' if node is None else type(node).__name__}")
            return
        if node is None:
            return

    if "const" in schema and node != schema["const"]:
        errors.append(f"{path}: expected const {schema['const']!r}, got {node!r}")
    if "enum" in schema and node not in schema["enum"]:
        errors.append(f"{path}: {node!r} is not one of {schema['enum']}")
    if isinstance(node, str):
        if "pattern" in schema and not re.search(schema["pattern"], node):
            errors.append(f"{path}: {node!r} does not match /{schema['pattern']}/")
        if "minLength" in schema and len(node) < schema["minLength"]:
            errors.append(f"{path}: length {len(node)} < minLength {schema['minLength']}")
    if isinstance(node, int) and not isinstance(node, bool) and "minimum" in schema:
        if node < schema["minimum"]:
            errors.append(f"{path}: {node} < minimum {schema['minimum']}")

    if isinstance(node, dict):
        for key in schema.get("required", []):
            if key not in node:
                errors.append(f"{path}: missing required key {key!r}")
        properties = schema.get("properties", {})
        for key, subschema in properties.items():
            if key in node:
                check(node[key], subschema, f"{path}.{key}", errors)
        extra = schema.get("additionalProperties")
        if extra is not None:
            for key, value in node.items():
                if key in properties:
                    continue
                if extra is False:
                    errors.append(f"{path}: unexpected key {key!r}")
                elif isinstance(extra, dict):
                    check(value, extra, f"{path}.{key}", errors)
    elif isinstance(node, list):
        if "minItems" in schema and len(node) < schema["minItems"]:
            errors.append(f"{path}: {len(node)} items < minItems {schema['minItems']}")
        if schema.get("uniqueItems"):
            seen = [json.dumps(i, sort_keys=True) for i in node]
            if len(set(seen)) != len(seen):
                errors.append(f"{path}: items are not unique")
        item_schema = schema.get("items")
        if item_schema:
            for i, item in enumerate(node):
                check(item, item_schema, f"{path}[{i}]", errors)


def validate(document, schema_path: Path, label: str) -> list[str]:
    """Validate one already-parsed document against a schema file."""
    errors: list[str] = []
    check(document, json.loads(schema_path.read_text()), label, errors)
    return errors


def validate_file(document_path: Path, schema_path: Path) -> list[str]:
    return validate(json.loads(document_path.read_text()), schema_path, document_path.name)
