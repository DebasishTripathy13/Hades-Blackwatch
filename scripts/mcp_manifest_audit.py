#!/usr/bin/env python3
"""Audit MCP-like tool manifests for risky capability design."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


DANGEROUS_WORDS = {
    "shell": "T4",
    "command": "T4",
    "exec": "T4",
    "eval": "T4",
    "delete": "T4",
    "write": "T3",
    "filesystem": "T4",
    "file": "T3",
    "browser": "T3",
    "admin": "T3",
    "credential": "T4",
    "token": "T3",
    "secret": "T4",
    "iam": "T4",
    "cloud": "T3",
    "scan": "T3",
    "url": "T2",
    "http": "T2",
}

FREEFORM_PARAMS = {"command", "script", "code", "url", "path", "query", "payload", "headers", "body"}


def load_manifest(path: Path):
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".yaml", ".yml"}:
        try:
            import yaml  # type: ignore
        except ImportError as exc:
            raise SystemExit("YAML input requires PyYAML. Use JSON or install PyYAML.") from exc
        return yaml.safe_load(text)
    return json.loads(text)


def find_tools(data):
    if isinstance(data, dict):
        for key in ("tools", "serverTools"):
            if isinstance(data.get(key), list):
                return data[key]
        if isinstance(data.get("server"), dict) and isinstance(data["server"].get("tools"), list):
            return data["server"]["tools"]
    if isinstance(data, list):
        return data
    return []


def risk_from_text(text: str) -> str:
    tier = "T0"
    for word, candidate in DANGEROUS_WORDS.items():
        if re.search(rf"\b{re.escape(word)}\b", text, re.IGNORECASE):
            if candidate > tier:
                tier = candidate
    return tier


def schema_properties(tool):
    schema = tool.get("inputSchema") or tool.get("input_schema") or tool.get("schema") or {}
    if not isinstance(schema, dict):
        return {}
    props = schema.get("properties")
    return props if isinstance(props, dict) else {}


def audit_tool(tool):
    name = str(tool.get("name") or tool.get("id") or "<unnamed>")
    description = str(tool.get("description") or "")
    text = f"{name} {description}"
    tier = risk_from_text(text)
    issues = []

    if name == "<unnamed>":
        issues.append("missing tool name")
    if not description.strip():
        issues.append("missing description")
    if not (tool.get("inputSchema") or tool.get("input_schema") or tool.get("schema")):
        issues.append("missing input schema")

    props = schema_properties(tool)
    for prop_name, prop_schema in props.items():
        prop_text = f"{prop_name} {json.dumps(prop_schema, default=str)}"
        prop_tier = risk_from_text(prop_text)
        if prop_tier > tier:
            tier = prop_tier
        if prop_name.lower() in FREEFORM_PARAMS:
            issues.append(f"free-form sensitive parameter: {prop_name}")
            if tier < "T3":
                tier = "T3"

    if tier in {"T3", "T4"} and not re.search(r"confirm|approval|dry.?run|allow.?list", text, re.IGNORECASE):
        issues.append("high-risk tool has no obvious approval, dry-run, or allowlist language")

    return {"name": name, "risk_tier": tier, "issues": issues}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", help="MCP tool manifest JSON/YAML")
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    args = parser.parse_args()

    data = load_manifest(Path(args.manifest))
    tools = find_tools(data)
    results = [audit_tool(tool) for tool in tools if isinstance(tool, dict)]
    summary = {}
    for result in results:
        summary[result["risk_tier"]] = summary.get(result["risk_tier"], 0) + 1

    output = {"tool_count": len(results), "summary": summary, "tools": results}
    if args.json:
        print(json.dumps(output, indent=2))
    else:
        print(f"Audited {len(results)} tools")
        for tier, count in sorted(summary.items()):
            print(f"- {tier}: {count}")
        for result in results:
            issue_text = "; ".join(result["issues"]) if result["issues"] else "no obvious issues"
            print(f"{result['risk_tier']} {result['name']}: {issue_text}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
