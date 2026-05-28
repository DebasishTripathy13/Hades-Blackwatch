#!/usr/bin/env python3
"""Map likely AI application security surfaces in a repository."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


PATTERNS = {
    "model_call": [
        r"\bopenai\b",
        r"\banthropic\b",
        r"\bazureopenai\b",
        r"\bchat\.completions\b",
        r"\bresponses\.create\b",
        r"\bgenerate_content\b",
    ],
    "agent_framework": [
        r"\blangchain\b",
        r"\blanggraph\b",
        r"\bcrewai\b",
        r"\bautogen\b",
        r"\bsemantic_kernel\b",
    ],
    "rag_vector": [
        r"\bchroma\b",
        r"\bpinecone\b",
        r"\bweaviate\b",
        r"\bqdrant\b",
        r"\bfaiss\b",
        r"\bembedding",
        r"\bretriever",
        r"\bvector",
    ],
    "tool_calling": [
        r"\btools?\s*=",
        r"\bfunction_call",
        r"\btool_calls",
        r"\binvoke_tool",
        r"\bexecute_tool",
    ],
    "mcp": [
        r"\bmcp\b",
        r"modelcontextprotocol",
        r"mcpServers",
        r"server\.tools",
    ],
    "dangerous_execution": [
        r"\bsubprocess\.",
        r"\bos\.system",
        r"\beval\(",
        r"\bexec\(",
        r"child_process",
        r"\bshell=True\b",
    ],
    "authz": [
        r"\bauthorization\b",
        r"\bauthentication\b",
        r"\brbac\b",
        r"\btenant",
        r"\bscope",
        r"\boauth",
    ],
    "secrets": [
        r"api[_-]?key",
        r"secret",
        r"token",
        r"password",
        r"credential",
    ],
}

DEFAULT_SKIP_DIRS = {
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    "dist",
    "build",
    ".next",
}


def iter_files(root: Path):
    for path in root.rglob("*"):
        if any(part in DEFAULT_SKIP_DIRS for part in path.parts):
            continue
        if path.is_file() and path.stat().st_size <= 1_000_000:
            yield path


def scan_file(path: Path, root: Path):
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []

    findings = []
    for category, patterns in PATTERNS.items():
        for pattern in patterns:
            regex = re.compile(pattern, re.IGNORECASE)
            for match in regex.finditer(text):
                line = text.count("\n", 0, match.start()) + 1
                findings.append(
                    {
                        "category": category,
                        "file": str(path.relative_to(root)),
                        "line": line,
                        "pattern": pattern,
                        "match": match.group(0)[:120],
                    }
                )
                break
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", default=".", help="Repository path")
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    args = parser.parse_args()

    root = Path(args.path).resolve()
    results = []
    for path in iter_files(root):
        results.extend(scan_file(path, root))

    summary = {}
    for item in results:
        summary[item["category"]] = summary.get(item["category"], 0) + 1

    output = {"root": str(root), "summary": summary, "surfaces": results}
    if args.json:
        print(json.dumps(output, indent=2))
    else:
        print(f"AI appsec surface map for {root}")
        for category, count in sorted(summary.items()):
            print(f"- {category}: {count}")
        for item in results[:100]:
            print(f"{item['category']}: {item['file']}:{item['line']} -> {item['match']}")
        if len(results) > 100:
            print(f"... {len(results) - 100} more")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
