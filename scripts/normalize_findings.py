#!/usr/bin/env python3
"""Normalize scanner JSON/SARIF output into the AI AppSec finding schema."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def stable_id(*parts: str) -> str:
    data = "|".join(part or "" for part in parts)
    return "F-" + hashlib.sha1(data.encode("utf-8")).hexdigest()[:10]


def severity_from_level(level: str) -> str:
    normalized = (level or "").lower()
    return {
        "error": "high",
        "warning": "medium",
        "note": "low",
        "critical": "critical",
        "high": "high",
        "medium": "medium",
        "low": "low",
        "info": "informational",
        "informational": "informational",
    }.get(normalized, "medium")


def normalize_sarif(data, source):
    findings = []
    for run in data.get("runs", []):
        tool_name = run.get("tool", {}).get("driver", {}).get("name", source)
        rules = {
            rule.get("id"): rule
            for rule in run.get("tool", {}).get("driver", {}).get("rules", [])
            if isinstance(rule, dict)
        }
        for result in run.get("results", []):
            rule_id = result.get("ruleId", "")
            rule = rules.get(rule_id, {})
            message = result.get("message", {}).get("text", rule.get("shortDescription", {}).get("text", "Scanner finding"))
            location = {}
            locations = result.get("locations") or []
            if locations:
                physical = locations[0].get("physicalLocation", {})
                region = physical.get("region", {})
                location = {
                    "file": physical.get("artifactLocation", {}).get("uri"),
                    "line": region.get("startLine"),
                }
            severity = severity_from_level(result.get("level") or rule.get("defaultConfiguration", {}).get("level", "warning"))
            findings.append(
                {
                    "id": stable_id(tool_name, rule_id, str(location), message),
                    "title": message,
                    "severity": severity,
                    "confidence": "medium",
                    "status": "open",
                    "source_tools": [tool_name],
                    "affected_component": None,
                    "affected_file": location.get("file"),
                    "affected_endpoint": None,
                    "affected_asset": None,
                    "evidence": {"rule_id": rule_id, "location": location, "raw_level": result.get("level")},
                    "attack_path": None,
                    "ai_agent_relevance": None,
                    "framework_mappings": {"cwe": result.get("taxa", [])},
                    "score": None,
                    "recommended_fix": None,
                    "regression_test": None,
                    "residual_risk": None,
                }
            )
    return findings


def normalize_generic(data, source):
    items = data if isinstance(data, list) else data.get("findings") or data.get("results") or data.get("issues") or []
    findings = []
    for item in items:
        if not isinstance(item, dict):
            continue
        title = item.get("title") or item.get("message") or item.get("name") or "Scanner finding"
        severity = severity_from_level(str(item.get("severity") or item.get("level") or item.get("risk") or "medium"))
        file_name = item.get("file") or item.get("path") or item.get("filename")
        endpoint = item.get("url") or item.get("endpoint")
        asset = item.get("asset") or item.get("host") or item.get("image")
        findings.append(
            {
                "id": stable_id(source, str(item.get("id") or item.get("rule_id") or ""), str(file_name), str(endpoint), title),
                "title": title,
                "severity": severity,
                "confidence": str(item.get("confidence") or "medium").lower(),
                "status": str(item.get("status") or "open").lower(),
                "source_tools": [source],
                "affected_component": item.get("component"),
                "affected_file": file_name,
                "affected_endpoint": endpoint,
                "affected_asset": asset,
                "evidence": item,
                "attack_path": None,
                "ai_agent_relevance": None,
                "framework_mappings": {},
                "score": None,
                "recommended_fix": item.get("fix") or item.get("recommendation"),
                "regression_test": None,
                "residual_risk": None,
            }
        )
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="JSON or SARIF file")
    parser.add_argument("--source", default=None, help="Source tool name")
    parser.add_argument("--output", help="Write output JSON to file")
    args = parser.parse_args()

    path = Path(args.input)
    data = json.loads(path.read_text(encoding="utf-8"))
    source = args.source or path.stem
    findings = normalize_sarif(data, source) if data.get("version") and data.get("runs") else normalize_generic(data, source)
    output = {"schema": "hades-blackwatch.findings.v1", "source": source, "findings": findings}
    text = json.dumps(output, indent=2)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
