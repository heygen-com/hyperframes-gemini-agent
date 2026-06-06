#!/usr/bin/env python3
"""Validate proposed variable values against a composition's declared schema
and write a clean variables.json for the render.

The source of truth for a composition's variables is the
`data-composition-variables` JSON array on its `<html>` element. This reads
that schema from the composition's index.html, checks each proposed value
against the declared type (and enum options), fills in declared defaults for
anything the caller omitted, and writes the result to an output file.

Catching a wrong type or an out-of-range enum here means the render API never
sees a bad payload — the failure is a clear local message instead of a remote
render error.

Usage:
    python3 customize.py <composition_dir> <proposed_values.json> <output_variables.json>

Exit status is non-zero on a validation failure, with the problems printed to
stderr.
"""

from __future__ import annotations

import json
import os
import re
import sys

# `data-composition-variables='[ ... ]'` on the <html> element. Starters in
# this repo always single-quote the attribute (its value is JSON with double
# quotes), so match a single-quoted value.
_ATTR_RE = re.compile(r"data-composition-variables\s*=\s*'(?P<json>.*?)'", re.DOTALL)

_VALID_TYPES = {"string", "number", "color", "boolean", "enum"}
_HEX_COLOR_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")


def load_schema(composition_dir: str) -> list[dict]:
    index_path = f"{composition_dir.rstrip('/')}/index.html"
    with open(index_path, encoding="utf-8") as fh:
        html = fh.read()
    match = _ATTR_RE.search(html)
    if not match:
        return []
    try:
        parsed = json.loads(match.group("json"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"data-composition-variables is not valid JSON: {exc}")
    if not isinstance(parsed, list):
        raise SystemExit("data-composition-variables must be a JSON array")
    return [v for v in parsed if isinstance(v, dict) and v.get("type") in _VALID_TYPES]


def _validate_one(var: dict, value: object) -> str | None:
    """Return an error string if `value` is invalid for `var`, else None."""
    vtype = var["type"]
    if vtype in ("string", "color") and not isinstance(value, str):
        return f"expected a string, got {type(value).__name__}"
    if vtype == "color" and isinstance(value, str) and not _HEX_COLOR_RE.match(value):
        return f"expected a hex color like #1a2b3c, got {value!r}"
    if vtype == "number" and (isinstance(value, bool) or not isinstance(value, (int, float))):
        return f"expected a number, got {type(value).__name__}"
    if vtype == "boolean" and not isinstance(value, bool):
        return f"expected true/false, got {type(value).__name__}"
    if vtype == "enum":
        options = {opt.get("value") for opt in var.get("options", []) if isinstance(opt, dict)}
        if value not in options:
            return f"expected one of {sorted(options)}, got {value!r}"
    if vtype == "number":
        if "min" in var and value < var["min"]:
            return f"below min {var['min']}"
        if "max" in var and value > var["max"]:
            return f"above max {var['max']}"
    return None


def build_variables(schema: list[dict], proposed: dict) -> dict:
    declared = {v["id"]: v for v in schema if "id" in v}
    errors: list[str] = []

    unknown = set(proposed) - set(declared)
    if unknown:
        errors.append(f"unknown variable(s) not declared by this composition: {sorted(unknown)}")

    resolved: dict = {}
    for var_id, var in declared.items():
        if var_id in proposed:
            err = _validate_one(var, proposed[var_id])
            if err:
                errors.append(f"variable '{var_id}': {err}")
            else:
                resolved[var_id] = proposed[var_id]
        elif "default" in var:
            resolved[var_id] = var["default"]

    if errors:
        raise SystemExit("Variable validation failed:\n  - " + "\n  - ".join(errors))
    return resolved


def main(argv: list[str]) -> int:
    if len(argv) != 4:
        print(__doc__, file=sys.stderr)
        return 2
    composition_dir, proposed_path, output_path = argv[1], argv[2], argv[3]

    schema = load_schema(composition_dir)
    with open(proposed_path) as fh:
        proposed = json.load(fh)
    if not isinstance(proposed, dict):
        raise SystemExit("Proposed values file must be a JSON object of {variable_id: value}")

    resolved = build_variables(schema, proposed)
    parent = os.path.dirname(os.path.abspath(output_path))
    os.makedirs(parent, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(resolved, fh, indent=2)
        fh.write("\n")
    print(output_path)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
