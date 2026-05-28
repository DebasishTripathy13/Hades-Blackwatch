#!/usr/bin/env python3
"""Generate detailed Hades Blackwatch reports in HTML and PDF formats."""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
import textwrap
from pathlib import Path
from typing import Any


SEVERITY_ORDER = {
    "critical": 0,
    "high": 1,
    "medium": 2,
    "low": 3,
    "informational": 4,
    "info": 4,
}

SEVERITY_LABELS = ["critical", "high", "medium", "low", "informational"]

SEVERITY_STYLES = {
    "critical": {"label": "Critical", "hex": "#991B1B", "rgb": (0.60, 0.11, 0.11), "soft": "#FEE2E2"},
    "high": {"label": "High", "hex": "#B45309", "rgb": (0.71, 0.33, 0.04), "soft": "#FEF3C7"},
    "medium": {"label": "Medium", "hex": "#A16207", "rgb": (0.63, 0.38, 0.03), "soft": "#FEF3C7"},
    "low": {"label": "Low", "hex": "#047857", "rgb": (0.02, 0.47, 0.34), "soft": "#D1FAE5"},
    "informational": {"label": "Informational", "hex": "#475569", "rgb": (0.28, 0.33, 0.41), "soft": "#E2E8F0"},
}

COLORS = {
    "ink": (0.07, 0.09, 0.15),
    "muted": (0.36, 0.39, 0.45),
    "line": (0.83, 0.86, 0.90),
    "panel": (0.97, 0.98, 0.99),
    "blue": (0.10, 0.30, 0.75),
    "blue_dark": (0.06, 0.13, 0.25),
    "teal": (0.05, 0.46, 0.43),
    "white": (1.0, 1.0, 1.0),
}


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, indent=2, ensure_ascii=False)
    return str(value)


def short_text(value: Any, limit: int = 160) -> str:
    text = re.sub(r"\s+", " ", clean_text(value)).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "..."


def slug(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return value or "report"


def normalize_severity(value: Any) -> str:
    severity = str(value or "medium").strip().lower()
    if severity == "info":
        return "informational"
    return severity if severity in SEVERITY_ORDER else "medium"


def load_report(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if "findings" in data:
        findings = data["findings"]
    elif "results" in data:
        findings = data["results"]
    else:
        findings = []

    metadata = data.get("metadata", {})
    scope = data.get("scope", {})
    methodology = data.get("methodology", {})

    if "schema" in data and "source" in data:
        methodology.setdefault("scanner_backends", [data["source"]])

    return {
        "metadata": metadata,
        "scope": scope,
        "methodology": methodology,
        "findings": [f for f in findings if isinstance(f, dict)],
        "raw": data,
    }


def sort_findings(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        findings,
        key=lambda f: (
            SEVERITY_ORDER.get(normalize_severity(f.get("severity")), 2),
            str(f.get("title") or ""),
        ),
    )


def severity_counts(findings: list[dict[str, Any]]) -> dict[str, int]:
    counts = {severity: 0 for severity in SEVERITY_LABELS}
    for finding in findings:
        counts[normalize_severity(finding.get("severity"))] += 1
    return counts


def verdict_from_counts(counts: dict[str, int]) -> str:
    if counts["critical"]:
        return "Block: critical AI/application security risk requires remediation."
    if counts["high"]:
        return "Request changes: high-risk issues require remediation before approval."
    if counts["medium"]:
        return "Pass with conditions: medium-risk issues need tracked remediation."
    if counts["low"] or counts["informational"]:
        return "Pass with hardening recommendations."
    return "Pass: no material findings in the provided evidence."


def risk_posture(counts: dict[str, int]) -> str:
    score = counts["critical"] * 10 + counts["high"] * 6 + counts["medium"] * 3 + counts["low"]
    if score >= 10:
        return "Elevated"
    if score >= 4:
        return "Moderate"
    if score > 0:
        return "Low"
    return "No material risk identified"


def html_list(items: Any) -> str:
    values = [clean_text(item) for item in as_list(items) if clean_text(item)]
    if not values:
        return '<p class="empty">Not provided.</p>'
    return "<ul>" + "".join(f"<li>{html.escape(item)}</li>" for item in values) + "</ul>"


def html_block(value: Any) -> str:
    text = clean_text(value)
    if not text:
        return '<p class="empty">Not provided.</p>'
    if "\n" in text or text.strip().startswith("{") or text.strip().startswith("["):
        return f"<pre>{html.escape(text)}</pre>"
    return f"<p>{html.escape(text)}</p>"


def html_badge(severity: str) -> str:
    style = SEVERITY_STYLES[severity]
    return f'<span class="badge {severity}">{html.escape(style["label"])}</span>'


def html_finding_nav(findings: list[dict[str, Any]]) -> str:
    if not findings:
        return '<p class="empty">No findings.</p>'
    items = []
    for index, finding in enumerate(findings, 1):
        fid = clean_text(finding.get("id") or f"F-{index:03d}")
        severity = normalize_severity(finding.get("severity"))
        title = clean_text(finding.get("title") or "Untitled finding")
        items.append(
            f'<a class="risk-link" href="#{html.escape(slug(fid))}">'
            f"<span>{html.escape(fid)}</span>"
            f"<strong>{html.escape(title)}</strong>"
            f"{html_badge(severity)}"
            "</a>"
        )
    return "".join(items)


def dict_or_empty(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def get_skill_coverage(report: dict[str, Any]) -> dict[str, Any]:
    raw = dict_or_empty(report.get("raw"))
    value = (
        raw.get("skill_coverage")
        or raw.get("skills_coverage")
        or raw.get("specialist_coverage")
        or dict_or_empty(report.get("methodology")).get("skill_coverage")
    )
    if isinstance(value, dict):
        return value
    if value:
        return {"specialists": as_list(value)}
    return {}


def get_threat_intel(report: dict[str, Any]) -> dict[str, Any]:
    raw = dict_or_empty(report.get("raw"))
    value = raw.get("threat_intel") or dict_or_empty(report.get("methodology")).get("threat_intel")
    if isinstance(value, dict):
        return value
    if value:
        return {"summary": value}
    return {}


def specialist_records(skill_coverage: dict[str, Any], methodology: dict[str, Any]) -> list[dict[str, str]]:
    specialists = (
        as_list(skill_coverage.get("specialists"))
        or as_list(skill_coverage.get("agents"))
        or as_list(skill_coverage.get("skills"))
    )
    if not specialists:
        specialists = [
            {
                "name": clean_text(agent),
                "status": "Used",
                "focus": "Declared in methodology",
                "coverage": "No dedicated specialist note was supplied.",
                "notes": "",
            }
            for agent in as_list(methodology.get("agents_used"))
            if clean_text(agent)
        ]

    records: list[dict[str, str]] = []
    for index, specialist in enumerate(specialists, 1):
        if isinstance(specialist, dict):
            records.append(
                {
                    "name": clean_text(specialist.get("name") or specialist.get("agent") or f"Specialist {index}"),
                    "status": clean_text(specialist.get("status") or specialist.get("used") or "Used"),
                    "focus": clean_text(specialist.get("focus") or specialist.get("responsibility") or ""),
                    "coverage": clean_text(specialist.get("coverage") or specialist.get("evidence") or ""),
                    "notes": clean_text(specialist.get("notes") or specialist.get("recommendation") or ""),
                }
            )
        else:
            records.append(
                {
                    "name": clean_text(specialist),
                    "status": "Used",
                    "focus": "",
                    "coverage": "",
                    "notes": "",
                }
            )
    return records


def threat_signal_records(threat_intel: dict[str, Any]) -> list[dict[str, str]]:
    signals = as_list(threat_intel.get("signals")) or as_list(threat_intel.get("items"))
    records: list[dict[str, str]] = []
    for index, signal in enumerate(signals, 1):
        if isinstance(signal, dict):
            linked = signal.get("linked_findings") or signal.get("finding_ids") or signal.get("findings")
            records.append(
                {
                    "theme": clean_text(signal.get("theme") or signal.get("name") or f"Signal {index}"),
                    "relevance": clean_text(signal.get("relevance") or signal.get("why_it_matters") or ""),
                    "recommended_action": clean_text(signal.get("recommended_action") or signal.get("action") or ""),
                    "linked_findings": ", ".join(clean_text(item) for item in as_list(linked) if clean_text(item)),
                }
            )
        elif clean_text(signal):
            records.append(
                {
                    "theme": f"Signal {index}",
                    "relevance": clean_text(signal),
                    "recommended_action": "",
                    "linked_findings": "",
                }
            )
    return records


def threat_source_records(threat_intel: dict[str, Any]) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    for index, source in enumerate(as_list(threat_intel.get("sources")), 1):
        if isinstance(source, dict):
            records.append(
                {
                    "name": clean_text(source.get("name") or source.get("title") or f"Source {index}"),
                    "url": clean_text(source.get("url") or source.get("link") or ""),
                    "relevance": clean_text(source.get("relevance") or source.get("notes") or ""),
                }
            )
        elif clean_text(source):
            records.append({"name": clean_text(source), "url": "", "relevance": ""})
    return records


def recommendation_owner(finding: dict[str, Any]) -> str:
    text = " ".join(
        clean_text(finding.get(key))
        for key in ("title", "affected_component", "affected_file", "recommended_fix", "ai_agent_relevance")
    ).lower()
    if "mcp" in text or "tool" in text:
        return "Agent platform / MCP owner"
    if "report" in text or "evidence" in text or "redact" in text or "scanner" in text:
        return "Security tooling owner"
    if "doc" in text or "readme" in text:
        return "Documentation owner"
    if "test" in text or "ci" in text or "regression" in text:
        return "Engineering quality owner"
    if "dependency" in text or "supply" in text or "package" in text:
        return "Supply chain owner"
    return "Application security owner"


def recommendation_timeframe(severity: str) -> str:
    return {
        "critical": "Immediate",
        "high": "0-7 days",
        "medium": "1-2 sprints",
        "low": "Next hardening cycle",
        "informational": "Backlog",
    }.get(normalize_severity(severity), "1-2 sprints")


def normalize_recommendation(value: Any, index: int) -> dict[str, str]:
    if isinstance(value, dict):
        linked = value.get("linked_findings") or value.get("finding_ids") or value.get("findings")
        return {
            "priority": clean_text(value.get("priority") or value.get("severity") or f"Priority {index}"),
            "recommendation": clean_text(value.get("recommendation") or value.get("title") or value.get("action")),
            "why": clean_text(value.get("why") or value.get("rationale") or value.get("reason")),
            "owner": clean_text(value.get("owner") or value.get("team") or "Application security owner"),
            "timeframe": clean_text(value.get("timeframe") or value.get("sla") or ""),
            "linked_findings": ", ".join(clean_text(item) for item in as_list(linked) if clean_text(item)),
        }
    return {
        "priority": f"Priority {index}",
        "recommendation": clean_text(value),
        "why": "",
        "owner": "Application security owner",
        "timeframe": "",
        "linked_findings": "",
    }


def personalized_recommendations(
    report: dict[str, Any], findings: list[dict[str, Any]], target: str
) -> list[dict[str, str]]:
    raw = dict_or_empty(report.get("raw"))
    explicit = raw.get("personalized_recommendations") or raw.get("recommendations")
    if explicit:
        return [normalize_recommendation(item, index) for index, item in enumerate(as_list(explicit), 1)]

    recommendations: list[dict[str, str]] = []
    for finding in sort_findings(findings)[:6]:
        fid = clean_text(finding.get("id") or "Finding")
        severity = normalize_severity(finding.get("severity"))
        component = clean_text(finding.get("affected_component") or finding.get("affected_asset") or "the reviewed target")
        fix = clean_text(finding.get("recommended_fix")) or "Add a concrete mitigation and verification path."
        why_source = clean_text(finding.get("attack_path") or finding.get("ai_agent_relevance") or finding.get("evidence"))
        why = short_text(
            f"For {target}, prioritize this because the affected area is {component}. {why_source}",
            limit=260,
        )
        recommendations.append(
            {
                "priority": SEVERITY_STYLES[severity]["label"],
                "recommendation": f"Resolve {fid} in {component}: {fix}",
                "why": why,
                "owner": recommendation_owner(finding),
                "timeframe": recommendation_timeframe(severity),
                "linked_findings": fid,
            }
        )

    if not recommendations:
        recommendations.append(
            {
                "priority": "Maintain",
                "recommendation": f"Keep {target} under recurring AI security review as prompts, tools, MCP servers, models, and scanner evidence change.",
                "why": "No material findings were supplied, so the priority is preserving coverage and avoiding stale assurance.",
                "owner": "Application security owner",
                "timeframe": "Next review cycle",
                "linked_findings": "",
            }
        )
    return recommendations


def render_skill_coverage_html(skill_coverage: dict[str, Any], methodology: dict[str, Any]) -> str:
    summary = clean_text(skill_coverage.get("summary"))
    specialists = specialist_records(skill_coverage, methodology)
    if not specialists:
        return '<p class="empty">No specialist coverage was provided.</p>'

    cards = []
    for specialist in specialists:
        notes = specialist["notes"]
        notes_html = f"<p>{html.escape(notes)}</p>" if notes else ""
        cards.append(
            f"""
            <article class="insight-card">
              <div class="insight-head">
                <h3>{html.escape(specialist["name"])}</h3>
                <span class="status-pill">{html.escape(specialist["status"])}</span>
              </div>
              <h4>Focus</h4>
              {html_block(specialist["focus"])}
              <h4>Coverage</h4>
              {html_block(specialist["coverage"])}
              {notes_html}
            </article>
            """
        )
    summary_html = f"<p>{html.escape(summary)}</p>" if summary else ""
    return summary_html + f'<div class="insight-grid">{"".join(cards)}</div>'


def render_threat_intel_html(threat_intel: dict[str, Any]) -> str:
    if not threat_intel:
        return '<p class="empty">No threat intelligence section was provided for this report input.</p>'

    as_of = clean_text(threat_intel.get("as_of") or threat_intel.get("date"))
    summary = clean_text(threat_intel.get("summary"))
    signals = threat_signal_records(threat_intel)
    sources = threat_source_records(threat_intel)
    header = []
    if as_of:
        header.append(f'<p class="kicker">As of {html.escape(as_of)}</p>')
    if summary:
        header.append(f"<p>{html.escape(summary)}</p>")

    signal_cards = []
    for signal in signals:
        linked = signal["linked_findings"]
        linked_html = f'<p class="tag-list"><span class="tag">Linked: {html.escape(linked)}</span></p>' if linked else ""
        signal_cards.append(
            f"""
            <article class="insight-card threat">
              <h3>{html.escape(signal["theme"])}</h3>
              <h4>Why It Matters</h4>
              {html_block(signal["relevance"])}
              <h4>Recommended Action</h4>
              {html_block(signal["recommended_action"])}
              {linked_html}
            </article>
            """
        )

    source_items = []
    for source in sources:
        name = html.escape(source["name"])
        if source["url"]:
            name = f'<a href="{html.escape(source["url"])}">{name}</a>'
        relevance = f' - {html.escape(source["relevance"])}' if source["relevance"] else ""
        source_items.append(f"<li>{name}{relevance}</li>")
    source_html = f'<h3>Sources</h3><ul class="source-list">{"".join(source_items)}</ul>' if source_items else ""
    signals_html = f'<div class="insight-grid">{"".join(signal_cards)}</div>' if signal_cards else ""
    return "".join(header) + signals_html + source_html


def render_finding_threat_intel_html(finding: dict[str, Any]) -> str:
    threat_intel = finding.get("threat_intel") or finding.get("threat_intelligence")
    if not threat_intel:
        return ""
    if not isinstance(threat_intel, dict):
        return f'<section class="wide threat-note"><h4>Threat Intelligence</h4>{html_block(threat_intel)}</section>'

    parts: list[str] = []
    as_of = clean_text(threat_intel.get("as_of") or threat_intel.get("date"))
    summary = clean_text(threat_intel.get("summary"))
    if as_of:
        parts.append(f'<p class="kicker">As of {html.escape(as_of)}</p>')
    if summary:
        parts.append(f"<p>{html.escape(summary)}</p>")

    signals = threat_signal_records(threat_intel)
    if signals:
        parts.append("<ul>")
        for signal in signals:
            action = f" Action: {signal['recommended_action']}" if signal["recommended_action"] else ""
            parts.append(
                f"<li><strong>{html.escape(signal['theme'])}:</strong> "
                f"{html.escape(signal['relevance'])}{html.escape(action)}</li>"
            )
        parts.append("</ul>")

    mapped = threat_intel.get("mapped_techniques") or threat_intel.get("techniques")
    if mapped:
        parts.append("<h4>Mapped Techniques</h4>")
        parts.append(html_block(mapped))

    detection = threat_intel.get("detection_or_test") or threat_intel.get("detection") or threat_intel.get("test")
    if detection:
        parts.append("<h4>Detection / Test Impact</h4>")
        parts.append(html_block(detection))

    sources = threat_source_records(threat_intel)
    if sources:
        items = []
        for source in sources:
            name = html.escape(source["name"])
            if source["url"]:
                name = f'<a href="{html.escape(source["url"])}">{name}</a>'
            relevance = f' - {html.escape(source["relevance"])}' if source["relevance"] else ""
            items.append(f"<li>{name}{relevance}</li>")
        parts.append("<h4>Sources</h4>")
        parts.append(f'<ul class="source-list">{"".join(items)}</ul>')

    meta = []
    for key in ("freshness", "confidence"):
        value = clean_text(threat_intel.get(key))
        if value:
            meta.append(f'<span class="tag">{html.escape(key.title())}: {html.escape(value)}</span>')
    if meta:
        parts.append(f'<div class="meta-row">{"".join(meta)}</div>')

    body = "".join(parts) or html_block(threat_intel)
    return f'<section class="wide threat-note"><h4>Threat Intelligence</h4>{body}</section>'


def normalize_visual_step(value: Any, index: int) -> dict[str, str]:
    if isinstance(value, dict):
        return {
            "label": clean_text(value.get("label") or value.get("title") or f"Step {index}"),
            "description": clean_text(value.get("description") or value.get("detail") or value.get("summary")),
            "actor": clean_text(value.get("actor") or ""),
            "control_gap": clean_text(value.get("control_gap") or value.get("failed_control") or ""),
            "defensive_breakpoint": clean_text(
                value.get("defensive_breakpoint") or value.get("breakpoint") or value.get("mitigation")
            ),
        }
    return {
        "label": f"Step {index}",
        "description": clean_text(value),
        "actor": "",
        "control_gap": "",
        "defensive_breakpoint": "",
    }


def attack_visualization_record(finding: dict[str, Any], target: str) -> dict[str, Any]:
    explicit = finding.get("attack_visualization") or finding.get("visualization") or finding.get("exploit_visualization")
    if isinstance(explicit, dict):
        steps = as_list(explicit.get("exploit_flow") or explicit.get("steps") or explicit.get("flow"))
        return {
            "title": clean_text(explicit.get("title") or "How This Vulnerability Works"),
            "summary": clean_text(explicit.get("summary") or explicit.get("description") or finding.get("attack_path")),
            "attacker_goal": clean_text(explicit.get("attacker_goal") or ""),
            "preconditions": clean_text(explicit.get("preconditions") or ""),
            "exploit_flow": [normalize_visual_step(step, index) for index, step in enumerate(steps, 1) if clean_text(step)],
            "control_breaks": clean_text(explicit.get("control_breaks") or explicit.get("control_break")),
            "impact": clean_text(explicit.get("impact") or finding.get("affected_asset")),
            "detection_points": clean_text(explicit.get("detection_points") or explicit.get("detection")),
            "defensive_breakpoints": clean_text(
                explicit.get("defensive_breakpoints") or explicit.get("defensive_breakpoint") or finding.get("recommended_fix")
            ),
            "diagram_note": clean_text(explicit.get("diagram_note") or ""),
            "safety_note": clean_text(
                explicit.get("safety_note")
                or "Conceptual defensive flow only. No exploit payloads or unauthorized testing steps are provided."
            ),
        }

    fid = clean_text(finding.get("id") or "Finding")
    component = clean_text(finding.get("affected_component") or "the affected component")
    asset = clean_text(finding.get("affected_asset") or "the protected asset")
    attack_path = clean_text(finding.get("attack_path") or "A weakness allows untrusted influence to cross a trust boundary.")
    fix = clean_text(finding.get("recommended_fix") or "Apply deterministic validation and monitoring at the trust boundary.")
    test = clean_text(finding.get("regression_test") or "Add a regression test that proves the unsafe flow is blocked.")
    ai_relevance = clean_text(finding.get("ai_agent_relevance") or "")
    title = clean_text(finding.get("title") or fid)

    return {
        "title": "How This Vulnerability Works",
        "summary": short_text(
            f"For {target}, {title} can be understood as a control failure where untrusted influence reaches {component} and can affect {asset}. {attack_path}",
            limit=420,
        ),
        "attacker_goal": f"Influence {component} so the workflow reaches {asset} in an unintended way.",
        "preconditions": short_text(
            ai_relevance
            or "An attacker can influence an input, prompt, retrieved document, tool parameter, scanner artifact, or configuration used by the reviewed workflow.",
            limit=260,
        ),
        "exploit_flow": [
            {
                "label": "Influence",
                "description": "Untrusted input or context reaches the reviewed workflow.",
                "actor": "Attacker-controlled input",
                "control_gap": "Input is treated as more trusted than it should be.",
                "defensive_breakpoint": "Classify the source as untrusted and constrain it early.",
            },
            {
                "label": "Trust Boundary",
                "description": f"The workflow passes data into {component}.",
                "actor": "Application or agent runtime",
                "control_gap": "A deterministic policy check is missing or incomplete.",
                "defensive_breakpoint": "Validate before the data crosses the boundary.",
            },
            {
                "label": "Control Failure",
                "description": short_text(attack_path, limit=210),
                "actor": "Vulnerable component",
                "control_gap": "Authorization, validation, isolation, or evidence minimization does not fully hold.",
                "defensive_breakpoint": short_text(fix, limit=190),
            },
            {
                "label": "Impact",
                "description": f"The unsafe path can affect {asset}.",
                "actor": "Impacted asset",
                "control_gap": "Blast radius is not contained.",
                "defensive_breakpoint": "Limit privileges, scope, data exposure, and egress.",
            },
            {
                "label": "Detect / Break",
                "description": short_text(test, limit=210),
                "actor": "Security control",
                "control_gap": "Regression coverage or monitoring may be missing.",
                "defensive_breakpoint": "Turn the regression test and detection point into a release gate.",
            },
        ],
        "control_breaks": "Missing or incomplete deterministic enforcement at the trust boundary.",
        "impact": asset,
        "detection_points": short_text(test, limit=260),
        "defensive_breakpoints": short_text(fix, limit=320),
        "diagram_note": "Generated from the finding evidence, attack path, affected component, affected asset, fix, and regression test.",
        "safety_note": "Conceptual defensive flow only. No exploit payloads or unauthorized testing steps are provided.",
    }


def render_attack_visualization_html(finding: dict[str, Any], target: str) -> str:
    visualization = attack_visualization_record(finding, target)
    steps = visualization.get("exploit_flow") or []
    if not steps:
        return ""

    step_cards = []
    for index, step in enumerate(steps, 1):
        detail_bits = []
        if step.get("actor"):
            detail_bits.append(f'<span class="tag">Actor: {html.escape(step["actor"])}</span>')
        if step.get("control_gap"):
            detail_bits.append(f'<span class="tag danger">Gap: {html.escape(step["control_gap"])}</span>')
        if step.get("defensive_breakpoint"):
            detail_bits.append(f'<span class="tag">Break: {html.escape(step["defensive_breakpoint"])}</span>')
        step_cards.append(
            f"""
            <div class="flow-step">
              <span class="step-number">{index}</span>
              <strong>{html.escape(step.get("label") or f"Step {index}")}</strong>
              <p>{html.escape(step.get("description") or "No description provided.")}</p>
              <div class="meta-row">{"".join(detail_bits)}</div>
            </div>
            """
        )

    facts = [
        ("Attacker Goal", visualization.get("attacker_goal")),
        ("Preconditions", visualization.get("preconditions")),
        ("Control Breaks", visualization.get("control_breaks")),
        ("Impact", visualization.get("impact")),
        ("Detection Points", visualization.get("detection_points")),
        ("Defensive Breakpoints", visualization.get("defensive_breakpoints")),
    ]
    fact_cards = "".join(
        f"<section><h4>{html.escape(label)}</h4>{html_block(value)}</section>" for label, value in facts if clean_text(value)
    )
    note = clean_text(visualization.get("diagram_note"))
    safety = clean_text(visualization.get("safety_note"))
    note_html = f"<p>{html.escape(note)}</p>" if note else ""
    safety_html = f'<p class="safe-note">{html.escape(safety)}</p>' if safety else ""

    return f"""
    <section class="wide attack-visual">
      <h4>Attack Path Visualization</h4>
      <h3>{html.escape(visualization.get("title") or "How This Vulnerability Works")}</h3>
      {html_block(visualization.get("summary"))}
      <div class="flow-diagram">{"".join(step_cards)}</div>
      <div class="mini-grid">{fact_cards}</div>
      {note_html}
      {safety_html}
    </section>
    """


def render_recommendations_html(recommendations: list[dict[str, str]]) -> str:
    cards = []
    for recommendation in recommendations:
        linked = recommendation["linked_findings"]
        linked_html = f'<span class="tag">Findings: {html.escape(linked)}</span>' if linked else ""
        cards.append(
            f"""
            <article class="recommendation-card">
              <div class="insight-head">
                <span class="priority">{html.escape(recommendation["priority"])}</span>
                <span class="status-pill">{html.escape(recommendation["timeframe"] or "Track")}</span>
              </div>
              <h3>{html.escape(recommendation["recommendation"] or "Recommended action")}</h3>
              <p>{html.escape(recommendation["why"] or "Prioritized from the current evidence set.")}</p>
              <div class="meta-row">
                <span class="tag">Owner: {html.escape(recommendation["owner"])}</span>
                {linked_html}
              </div>
            </article>
            """
        )
    return f'<div class="recommendation-grid">{"".join(cards)}</div>'


def render_html(report: dict[str, Any]) -> str:
    metadata = report["metadata"]
    scope = report["scope"]
    methodology = report["methodology"]
    findings = sort_findings(report["findings"])
    counts = severity_counts(findings)
    title = metadata.get("title") or "Hades Blackwatch Security Report"
    target = metadata.get("target") or "Unspecified target"
    date = metadata.get("date") or dt.date.today().isoformat()
    author = metadata.get("author") or "Hades Blackwatch"
    classification = metadata.get("classification") or "Internal"
    version = metadata.get("version") or "1.0"
    verdict = verdict_from_counts(counts)
    posture = risk_posture(counts)
    skill_coverage = get_skill_coverage(report)
    threat_intel = get_threat_intel(report)
    recommendations = personalized_recommendations(report, findings, target)

    finding_sections = []
    remediation_rows = []
    test_rows = []
    coverage_rows = []

    for index, finding in enumerate(findings, 1):
        fid = clean_text(finding.get("id") or f"F-{index:03d}")
        severity = normalize_severity(finding.get("severity"))
        confidence = clean_text(finding.get("confidence") or "medium")
        title_text = clean_text(finding.get("title") or "Untitled finding")
        mappings = finding.get("framework_mappings") or {}
        score = finding.get("score")
        source_tools = ", ".join(clean_text(x) for x in as_list(finding.get("source_tools")) if clean_text(x)) or "Not provided"
        finding_threat_intel_html = render_finding_threat_intel_html(finding)
        attack_visualization_html = render_attack_visualization_html(finding, target)

        remediation_rows.append(
            "<tr>"
            f"<td><a href=\"#{html.escape(slug(fid))}\">{html.escape(fid)}</a></td>"
            f"<td>{html_badge(severity)}</td>"
            f"<td>{html.escape(title_text)}</td>"
            f"<td>{html.escape(clean_text(finding.get('recommended_fix')) or 'Not provided')}</td>"
            "</tr>"
        )
        test_rows.append(
            "<tr>"
            f"<td><a href=\"#{html.escape(slug(fid))}\">{html.escape(fid)}</a></td>"
            f"<td>{html.escape(clean_text(finding.get('regression_test')) or 'Not provided')}</td>"
            "</tr>"
        )

        for key, value in (mappings.items() if isinstance(mappings, dict) else []):
            if value:
                coverage_rows.append(
                    "<tr>"
                    f"<td><a href=\"#{html.escape(slug(fid))}\">{html.escape(fid)}</a></td>"
                    f"<td>{html.escape(str(key))}</td>"
                    f"<td>{html.escape(clean_text(value))}</td>"
                    "</tr>"
                )

        finding_sections.append(
            f"""
            <article class="finding {severity}" id="{html.escape(slug(fid))}">
              <div class="finding-head">
                <div>
                  <p class="kicker">{html.escape(fid)} - {html.escape(source_tools)}</p>
                  <h3>{index}. {html.escape(title_text)}</h3>
                </div>
                <div class="finding-badges">
                  {html_badge(severity)}
                  <span class="badge confidence">Confidence: {html.escape(confidence)}</span>
                </div>
              </div>
              <div class="mini-grid">
                <section><h4>Affected Component</h4>{html_block(finding.get("affected_component"))}</section>
                <section><h4>Affected File</h4>{html_block(finding.get("affected_file"))}</section>
                <section><h4>Affected Endpoint</h4>{html_block(finding.get("affected_endpoint"))}</section>
                <section><h4>Affected Asset</h4>{html_block(finding.get("affected_asset"))}</section>
              </div>
              <div class="finding-body">
                <section class="wide"><h4>Evidence</h4>{html_block(finding.get("evidence"))}</section>
                <section><h4>Attack Path</h4>{html_block(finding.get("attack_path"))}</section>
                <section><h4>AI / Agent Relevance</h4>{html_block(finding.get("ai_agent_relevance"))}</section>
                {finding_threat_intel_html}
                {attack_visualization_html}
                <section><h4>Framework Mappings</h4>{html_block(mappings)}</section>
                <section><h4>Score</h4>{html_block(score)}</section>
                <section class="wide fix"><h4>Recommended Fix</h4>{html_block(finding.get("recommended_fix"))}</section>
                <section class="wide"><h4>Regression Test</h4>{html_block(finding.get("regression_test"))}</section>
                <section class="wide"><h4>Residual Risk</h4>{html_block(finding.get("residual_risk"))}</section>
              </div>
            </article>
            """
        )

    count_cards = "".join(
        f"""
        <div class="score-card {severity}">
          <span>{html.escape(SEVERITY_STYLES[severity]["label"])}</span>
          <strong>{counts[severity]}</strong>
        </div>
        """
        for severity in SEVERITY_LABELS
    )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>
    :root {{
      --ink: #101828;
      --muted: #667085;
      --soft: #f8fafc;
      --panel: #ffffff;
      --line: #d9dee8;
      --blue: #1d4ed8;
      --blue-dark: #101828;
      --teal: #0f766e;
      --critical: #991b1b;
      --critical-soft: #fee2e2;
      --high: #b45309;
      --high-soft: #fef3c7;
      --medium: #a16207;
      --medium-soft: #fef3c7;
      --low: #047857;
      --low-soft: #d1fae5;
      --informational: #475569;
      --informational-soft: #e2e8f0;
      --shadow: 0 18px 42px rgba(15, 23, 42, 0.08);
    }}
    * {{ box-sizing: border-box; }}
    html {{ scroll-behavior: smooth; }}
    body {{ margin: 0; color: var(--ink); background: #eef2f7; font: 14px/1.6 Arial, Helvetica, sans-serif; }}
    a {{ color: var(--blue); text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    .layout {{ display: grid; grid-template-columns: 292px minmax(0, 1fr); min-height: 100vh; }}
    .sidebar {{ position: sticky; top: 0; height: 100vh; overflow: auto; padding: 26px 20px; background: var(--blue-dark); color: #e5e7eb; }}
    .mark {{ width: 44px; height: 44px; display: grid; place-items: center; border-radius: 8px; background: linear-gradient(135deg, #2563eb, #0f766e); color: #fff; font-weight: 800; margin-bottom: 12px; }}
    .sidebar h1 {{ margin: 0; font-size: 22px; }}
    .sidebar p {{ color: #aab3c2; margin: 6px 0 22px; }}
    .nav-title {{ margin: 22px 0 8px; color: #aab3c2; text-transform: uppercase; font-size: 12px; letter-spacing: 0.04em; }}
    .risk-link {{ display: grid; grid-template-columns: 58px minmax(0, 1fr); gap: 8px; align-items: start; padding: 10px; border-radius: 8px; color: #e5e7eb; border: 1px solid transparent; }}
    .risk-link:hover {{ background: #1d2939; text-decoration: none; border-color: #344054; }}
    .risk-link span {{ color: #aab3c2; font-size: 12px; }}
    .risk-link strong {{ font-size: 13px; line-height: 1.35; }}
    .risk-link .badge {{ grid-column: 2; width: fit-content; }}
    .section-nav {{ display: grid; gap: 6px; }}
    .quick-link {{ color: #dbeafe; padding: 7px 10px; border-radius: 8px; font-size: 13px; }}
    .quick-link:hover {{ background: #1d2939; text-decoration: none; }}
    .content {{ min-width: 0; }}
    .hero {{ padding: 44px 56px 34px; color: #fff; background: radial-gradient(circle at top right, rgba(15,118,110,0.55), transparent 32%), linear-gradient(135deg, #111827, #172554 62%, #0f766e); }}
    .hero-inner {{ max-width: 1180px; margin: 0 auto; }}
    .eyebrow {{ margin: 0 0 10px; color: #bfdbfe; text-transform: uppercase; font-weight: 800; font-size: 12px; letter-spacing: 0.06em; }}
    .hero h2 {{ margin: 0; max-width: 920px; font-size: 38px; line-height: 1.12; }}
    .hero p {{ max-width: 900px; color: #dbeafe; font-size: 17px; }}
    .hero-meta {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin-top: 26px; }}
    .hero-meta div {{ border: 1px solid rgba(255,255,255,0.2); background: rgba(255,255,255,0.09); border-radius: 8px; padding: 12px; }}
    .hero-meta span {{ display: block; color: #bfdbfe; font-size: 12px; text-transform: uppercase; }}
    .hero-meta strong {{ display: block; margin-top: 4px; font-size: 14px; }}
    main {{ max-width: 1180px; margin: 0 auto; padding: 32px 56px 72px; }}
    section {{ scroll-margin-top: 24px; }}
    h2 {{ font-size: 25px; margin: 34px 0 14px; }}
    h3 {{ font-size: 20px; margin: 0; }}
    h4 {{ font-size: 12px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.04em; margin: 18px 0 6px; }}
    p {{ margin: 7px 0 12px; }}
    ul {{ margin: 8px 0 14px; padding-left: 20px; }}
    pre {{ margin: 8px 0 14px; white-space: pre-wrap; overflow-wrap: anywhere; background: #111827; color: #e5e7eb; border-radius: 8px; padding: 14px; font-size: 12px; line-height: 1.55; }}
    table {{ width: 100%; border-collapse: collapse; margin: 14px 0 28px; background: #fff; border: 1px solid var(--line); border-radius: 8px; overflow: hidden; box-shadow: 0 8px 24px rgba(15,23,42,0.04); }}
    th, td {{ padding: 11px 12px; border-bottom: 1px solid var(--line); text-align: left; vertical-align: top; }}
    th {{ background: #eef2f7; color: #344054; font-size: 12px; text-transform: uppercase; letter-spacing: 0.04em; }}
    tr:last-child td {{ border-bottom: 0; }}
    .summary {{ display: grid; grid-template-columns: minmax(0, 1.3fr) minmax(300px, 0.7fr); gap: 18px; }}
    .panel {{ background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 20px; box-shadow: var(--shadow); }}
    .insight-grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; margin: 14px 0 24px; }}
    .insight-card, .recommendation-card {{ background: #fff; border: 1px solid var(--line); border-radius: 8px; padding: 16px; box-shadow: 0 8px 24px rgba(15,23,42,0.04); }}
    .insight-card.threat {{ border-left: 5px solid var(--teal); }}
    .insight-head {{ display: flex; justify-content: space-between; gap: 12px; align-items: flex-start; margin-bottom: 8px; }}
    .insight-head h3 {{ font-size: 17px; }}
    .status-pill, .tag, .priority {{ display: inline-flex; align-items: center; min-height: 24px; border-radius: 999px; padding: 3px 9px; background: #eef2ff; color: #1e3a8a; font-size: 12px; font-weight: 800; }}
    .priority {{ background: #ecfdf5; color: #065f46; }}
    .tag-list, .meta-row {{ display: flex; flex-wrap: wrap; gap: 7px; margin-top: 12px; }}
    .source-list a {{ font-weight: 800; }}
    .recommendation-grid {{ display: grid; gap: 14px; margin: 14px 0 26px; }}
    .recommendation-card {{ border-left: 5px solid var(--blue); }}
    .recommendation-card h3 {{ margin-top: 10px; font-size: 17px; line-height: 1.35; }}
    .score-grid {{ display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 12px; margin-top: 16px; }}
    .score-card {{ background: #fff; border: 1px solid var(--line); border-top: 5px solid var(--informational); border-radius: 8px; padding: 14px; }}
    .score-card span {{ display: block; color: var(--muted); }}
    .score-card strong {{ display: block; font-size: 30px; line-height: 1; margin-top: 8px; }}
    .score-card.critical {{ border-top-color: var(--critical); }}
    .score-card.high {{ border-top-color: var(--high); }}
    .score-card.medium {{ border-top-color: var(--medium); }}
    .score-card.low {{ border-top-color: var(--low); }}
    .mini-grid {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin-top: 16px; }}
    .mini-grid section, .finding-body section {{ background: #f8fafc; border: 1px solid var(--line); border-radius: 8px; padding: 12px; }}
    .finding {{ background: #fff; border: 1px solid var(--line); border-left: 7px solid var(--informational); border-radius: 8px; padding: 18px; margin: 18px 0 28px; box-shadow: var(--shadow); }}
    .finding.critical {{ border-left-color: var(--critical); }}
    .finding.high {{ border-left-color: var(--high); }}
    .finding.medium {{ border-left-color: var(--medium); }}
    .finding.low {{ border-left-color: var(--low); }}
    .finding-head {{ display: flex; justify-content: space-between; gap: 18px; border-bottom: 1px solid var(--line); padding-bottom: 14px; }}
    .finding-badges {{ text-align: right; min-width: 190px; }}
    .finding-body {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; margin-top: 12px; }}
    .finding-body .wide {{ grid-column: 1 / -1; }}
    .finding-body .fix {{ background: #ecfdf5; border-color: #a7f3d0; }}
    .finding-body .threat-note {{ background: #f0fdfa; border-color: #99f6e4; }}
    .finding-body .attack-visual {{ background: #fff7ed; border-color: #fed7aa; }}
    .flow-diagram {{ display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 10px; margin: 14px 0; counter-reset: flow; }}
    .flow-step {{ position: relative; min-height: 190px; border: 1px solid #fed7aa; border-radius: 8px; background: #fffaf5; padding: 13px; }}
    .flow-step::after {{ content: ""; position: absolute; top: 28px; right: -10px; width: 10px; height: 2px; background: #f97316; }}
    .flow-step:last-child::after {{ display: none; }}
    .flow-step strong {{ display: block; margin: 7px 0 5px; color: #9a3412; }}
    .flow-step p {{ font-size: 13px; line-height: 1.45; }}
    .step-number {{ display: inline-grid; place-items: center; width: 25px; height: 25px; border-radius: 50%; background: #f97316; color: #fff; font-size: 12px; font-weight: 800; }}
    .tag.danger {{ background: #fef2f2; color: #991b1b; }}
    .safe-note {{ color: #7c2d12; font-weight: 700; }}
    .badge {{ display: inline-flex; align-items: center; min-height: 24px; border-radius: 999px; padding: 3px 9px; color: #fff; background: var(--informational); font-size: 12px; font-weight: 800; }}
    .badge.critical {{ background: var(--critical); }}
    .badge.high {{ background: var(--high); }}
    .badge.medium {{ background: var(--medium); }}
    .badge.low {{ background: var(--low); }}
    .badge.informational {{ background: var(--informational); }}
    .badge.confidence {{ background: #344054; margin-left: 4px; }}
    .kicker {{ color: var(--muted); text-transform: uppercase; font-size: 12px; margin: 0 0 5px; font-weight: 700; }}
    .empty {{ color: var(--muted); font-style: italic; }}
    @media (max-width: 1100px) {{
      .layout {{ grid-template-columns: 1fr; }}
      .sidebar {{ position: static; height: auto; }}
      .hero, main {{ padding-left: 24px; padding-right: 24px; }}
      .hero-meta, .score-grid, .summary, .mini-grid, .finding-body, .insight-grid, .flow-diagram {{ grid-template-columns: 1fr; }}
      .finding-body .wide {{ grid-column: auto; }}
      .flow-step::after {{ display: none; }}
    }}
    @media print {{
      body {{ background: #fff; }}
      .layout {{ display: block; }}
      .sidebar {{ display: none; }}
      .hero {{ color: #111827; background: #fff; border-bottom: 1px solid var(--line); }}
      .hero p, .eyebrow {{ color: #475569; }}
      main, .hero {{ padding: 24px 32px; }}
      .panel, .finding, table {{ box-shadow: none; }}
      .finding {{ break-inside: avoid; }}
    }}
  </style>
</head>
<body>
  <div class="layout">
    <aside class="sidebar">
      <div class="mark">HB</div>
      <h1>Hades Blackwatch</h1>
      <p>Security review report</p>
      <div class="nav-title">Sections</div>
      <nav class="section-nav">
        <a class="quick-link" href="#summary">Executive summary</a>
        <a class="quick-link" href="#scope">Scope</a>
        <a class="quick-link" href="#methodology">Methodology</a>
        <a class="quick-link" href="#skills">Skill coverage</a>
        <a class="quick-link" href="#threat-intel">Threat intel</a>
        <a class="quick-link" href="#recommendations">Recommendations</a>
        <a class="quick-link" href="#findings">Detailed findings</a>
        <a class="quick-link" href="#roadmap">Roadmap</a>
      </nav>
      <div class="nav-title">Top Risks</div>
      {html_finding_nav(findings[:8])}
    </aside>
    <div class="content">
      <header class="hero">
        <div class="hero-inner">
          <p class="eyebrow">{html.escape(classification)} - Version {html.escape(version)}</p>
          <h2>{html.escape(title)}</h2>
          <p>{html.escape(verdict)}</p>
          <div class="hero-meta">
            <div><span>Target</span><strong>{html.escape(target)}</strong></div>
            <div><span>Date</span><strong>{html.escape(date)}</strong></div>
            <div><span>Author</span><strong>{html.escape(author)}</strong></div>
            <div><span>Risk Posture</span><strong>{html.escape(posture)}</strong></div>
          </div>
        </div>
      </header>
      <main>
        <section class="summary" id="summary">
          <div class="panel">
            <h2>Executive Summary</h2>
            <p><strong>Verdict:</strong> {html.escape(verdict)}</p>
            <p><strong>Risk posture:</strong> {html.escape(posture)} based on {len(findings)} normalized finding(s).</p>
          </div>
          <div class="panel">
            <h2>Severity</h2>
            <div class="score-grid">{count_cards}</div>
          </div>
        </section>

        <section id="scope">
          <h2>Scope and Authorization</h2>
          <div class="mini-grid">
            <section><h4>Environment</h4>{html_block(scope.get("environment"))}</section>
            <section><h4>Access Level</h4>{html_block(scope.get("access_level"))}</section>
            <section><h4>Authorized</h4>{html_block(scope.get("authorized"))}</section>
            <section><h4>Excluded</h4>{html_list(scope.get("excluded"))}</section>
          </div>
          <div class="panel"><h4>Included</h4>{html_list(scope.get("included"))}</div>
        </section>

        <section id="methodology">
          <h2>Methodology</h2>
          <div class="mini-grid">
            <section><h4>Frameworks</h4>{html_list(methodology.get("frameworks"))}</section>
            <section><h4>Agents Used</h4>{html_list(methodology.get("agents_used"))}</section>
            <section><h4>Evidence Sources</h4>{html_list(methodology.get("scanner_backends"))}</section>
            <section><h4>MCP Policy</h4>{html_block(methodology.get("mcp_policy"))}</section>
          </div>
        </section>

        <section id="skills">
          <h2>Skill Coverage and Specialist Notes</h2>
          {render_skill_coverage_html(skill_coverage, methodology)}
        </section>

        <section id="threat-intel">
          <h2>Threat Intelligence</h2>
          {render_threat_intel_html(threat_intel)}
        </section>

        <section id="recommendations">
          <h2>Personalized Recommendations for {html.escape(target)}</h2>
          <p>These actions are tailored to the target, authorization model, actual evidence sources, and the current finding set.</p>
          {render_recommendations_html(recommendations)}
        </section>

        <section id="findings">
          <h2>Detailed Findings</h2>
          {''.join(finding_sections) if finding_sections else '<p>No material findings were provided.</p>'}
        </section>

        <section id="roadmap">
          <h2>Personalized Remediation Roadmap</h2>
          <table><thead><tr><th>ID</th><th>Severity</th><th>Finding</th><th>Recommended Fix</th></tr></thead><tbody>{''.join(remediation_rows) or '<tr><td colspan="4">No remediation items.</td></tr>'}</tbody></table>
        </section>

        <section id="tests">
          <h2>Regression Test Plan</h2>
          <table><thead><tr><th>ID</th><th>Test / Control</th></tr></thead><tbody>{''.join(test_rows) or '<tr><td colspan="2">No regression tests provided.</td></tr>'}</tbody></table>
        </section>

        <section id="framework">
          <h2>Framework Coverage</h2>
          <table><thead><tr><th>ID</th><th>Framework</th><th>Mapping</th></tr></thead><tbody>{''.join(coverage_rows) or '<tr><td colspan="3">No framework mappings provided.</td></tr>'}</tbody></table>
        </section>

        <section class="panel" id="residual">
          <h2>Residual Risk and Assumptions</h2>
          <p>Residual risk depends on complete remediation, regression test adoption, scanner coverage, evidence redaction, and continued enforcement of deterministic authorization around model-driven actions.</p>
        </section>
      </main>
    </div>
  </div>
</body>
</html>
"""


def pdf_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def pdf_color(rgb: tuple[float, float, float], operator: str = "rg") -> str:
    return f"{rgb[0]:.3f} {rgb[1]:.3f} {rgb[2]:.3f} {operator}"


class PdfReport:
    width = 612
    height = 792
    margin = 48
    bottom = 54

    def __init__(self) -> None:
        self.pages: list[str] = []
        self.commands: list[str] = []
        self.page_number = 0
        self.y = 0.0
        self.new_page()

    def new_page(self) -> None:
        if self.commands:
            self.footer()
            self.pages.append("\n".join(self.commands))
        self.page_number += 1
        self.commands = []
        self.y = self.height - self.margin

    def footer(self) -> None:
        self.line(self.margin, 38, self.width - self.margin, 38, COLORS["line"])
        self.text("Hades Blackwatch Security Report", self.margin, 24, 8, "regular", COLORS["muted"])
        self.text(f"Page {self.page_number}", self.width - self.margin - 40, 24, 8, "regular", COLORS["muted"])

    def finish(self) -> list[str]:
        self.footer()
        self.pages.append("\n".join(self.commands))
        self.commands = []
        return self.pages

    def ensure_space(self, amount: float) -> None:
        if self.y - amount < self.bottom:
            self.new_page()

    def rect(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        fill: tuple[float, float, float] | None = None,
        stroke: tuple[float, float, float] | None = None,
    ) -> None:
        if fill:
            self.commands.append(f"q {pdf_color(fill, 'rg')} {x:.2f} {y:.2f} {w:.2f} {h:.2f} re f Q")
        if stroke:
            self.commands.append(f"q {pdf_color(stroke, 'RG')} {x:.2f} {y:.2f} {w:.2f} {h:.2f} re S Q")

    def line(self, x1: float, y1: float, x2: float, y2: float, color: tuple[float, float, float]) -> None:
        self.commands.append(f"q {pdf_color(color, 'RG')} {x1:.2f} {y1:.2f} m {x2:.2f} {y2:.2f} l S Q")

    def text(
        self,
        value: str,
        x: float,
        y: float,
        size: float,
        font: str = "regular",
        color: tuple[float, float, float] = COLORS["ink"],
    ) -> None:
        font_name = {"regular": "F1", "bold": "F2", "mono": "F3"}[font]
        safe = pdf_escape(value)
        self.commands.append(f"BT /{font_name} {size:.1f} Tf {pdf_color(color, 'rg')} {x:.2f} {y:.2f} Td ({safe}) Tj ET")

    def wrap(self, text: str, max_width: float, size: float, font: str = "regular") -> list[str]:
        factor = 0.58 if font == "mono" else 0.50
        max_chars = max(18, int(max_width / (size * factor)))
        lines: list[str] = []
        for raw in clean_text(text).splitlines() or [""]:
            if not raw.strip():
                lines.append("")
                continue
            lines.extend(textwrap.wrap(raw, width=max_chars, break_long_words=True, replace_whitespace=False))
        return lines

    def paragraph(
        self,
        text: Any,
        *,
        x: float | None = None,
        width: float | None = None,
        size: float = 10,
        font: str = "regular",
        color: tuple[float, float, float] = COLORS["ink"],
        leading: float | None = None,
        after: float = 8,
    ) -> None:
        x = self.margin if x is None else x
        width = self.width - self.margin * 2 if width is None else width
        leading = size + 4 if leading is None else leading
        lines = self.wrap(clean_text(text), width, size, font)
        self.ensure_space(len(lines) * leading + after)
        for line in lines:
            if line:
                self.text(line, x, self.y, size, font, color)
            self.y -= leading
        self.y -= after

    def heading(self, text: str, level: int = 1) -> None:
        if level == 1:
            self.ensure_space(42)
            self.y -= 8
            self.text(text, self.margin, self.y, 18, "bold", COLORS["blue_dark"])
            self.y -= 10
            self.line(self.margin, self.y, self.width - self.margin, self.y, COLORS["line"])
            self.y -= 16
        else:
            self.ensure_space(28)
            self.text(text, self.margin, self.y, 13, "bold", COLORS["blue_dark"])
            self.y -= 18

    def label_value(self, label: str, value: Any) -> None:
        self.ensure_space(28)
        self.text(label.upper(), self.margin, self.y, 8, "bold", COLORS["muted"])
        self.y -= 11
        self.paragraph(clean_text(value) or "Not provided", size=9.5, after=4)

    def severity_chip(self, severity: str, x: float, y: float) -> None:
        sev = normalize_severity(severity)
        rgb = SEVERITY_STYLES[sev]["rgb"]
        self.rect(x, y - 3, 72, 16, fill=rgb)
        self.text(SEVERITY_STYLES[sev]["label"], x + 7, y + 2, 8, "bold", COLORS["white"])

    def cover(self, report: dict[str, Any]) -> None:
        metadata = report["metadata"]
        findings = sort_findings(report["findings"])
        counts = severity_counts(findings)
        title = metadata.get("title") or "Hades Blackwatch Security Report"
        target = metadata.get("target") or "Unspecified target"
        date = metadata.get("date") or dt.date.today().isoformat()
        classification = metadata.get("classification") or "Internal"
        version = metadata.get("version") or "1.0"

        self.rect(0, 0, self.width, self.height, fill=(0.97, 0.98, 0.99))
        self.rect(0, self.height - 190, self.width, 190, fill=COLORS["blue_dark"])
        self.rect(self.margin, self.height - 104, 46, 46, fill=COLORS["blue"])
        self.text("HB", self.margin + 12, self.height - 86, 16, "bold", COLORS["white"])
        self.text("HADES BLACKWATCH", self.margin + 62, self.height - 70, 11, "bold", (0.75, 0.86, 1.0))
        self.paragraph(title, x=self.margin, width=490, size=24, font="bold", color=COLORS["white"], leading=29, after=8)
        self.text(f"{classification} - Version {version}", self.margin, self.height - 168, 10, "regular", (0.75, 0.86, 1.0))

        self.y = self.height - 236
        self.heading("Executive Summary", 1)
        self.paragraph(f"Target: {target}", size=12, font="bold", after=4)
        self.paragraph(f"Date: {date}", size=10, color=COLORS["muted"], after=10)
        self.paragraph(verdict_from_counts(counts), size=12, font="bold", color=COLORS["blue_dark"], after=16)

        card_w = 94
        card_h = 58
        start_x = self.margin
        start_y = self.y - card_h
        for idx, sev in enumerate(SEVERITY_LABELS):
            x = start_x + idx * (card_w + 8)
            self.rect(x, start_y, card_w, card_h, fill=COLORS["white"], stroke=COLORS["line"])
            self.rect(x, start_y + card_h - 6, card_w, 6, fill=SEVERITY_STYLES[sev]["rgb"])
            self.text(SEVERITY_STYLES[sev]["label"], x + 9, start_y + 34, 8, "bold", COLORS["muted"])
            self.text(str(counts[sev]), x + 9, start_y + 13, 20, "bold", COLORS["ink"])
        self.y = start_y - 34
        self.paragraph(
            f"Risk posture: {risk_posture(counts)}. This report contains {len(findings)} normalized finding(s), ordered by severity and supported by local source review and generated evidence.",
            size=10,
            color=COLORS["muted"],
        )

    def key_values(self, title: str, data: dict[str, Any], keys: list[str]) -> None:
        self.heading(title, 1)
        for key in keys:
            self.label_value(key.replace("_", " "), data.get(key))

    def finding(self, index: int, finding: dict[str, Any], target: str = "Unspecified target") -> None:
        fid = clean_text(finding.get("id") or f"F-{index:03d}")
        sev = normalize_severity(finding.get("severity"))
        title = clean_text(finding.get("title") or "Untitled finding")
        confidence = clean_text(finding.get("confidence") or "medium")

        self.new_page()
        self.text(fid, self.margin, self.y, 10, "bold", COLORS["muted"])
        self.severity_chip(sev, self.width - self.margin - 78, self.y - 1)
        self.y -= 24
        self.paragraph(f"{index}. {title}", size=17, font="bold", color=COLORS["blue_dark"], leading=22, after=8)
        self.paragraph(f"Confidence: {confidence}", size=9.5, font="bold", color=COLORS["muted"], after=8)

        for label, key in (
            ("Affected component", "affected_component"),
            ("Affected file", "affected_file"),
            ("Affected endpoint", "affected_endpoint"),
            ("Affected asset", "affected_asset"),
        ):
            value = clean_text(finding.get(key)) or "Not provided"
            self.paragraph(f"{label}: {value}", size=9.5, color=COLORS["ink"], after=2)

        sections = [
            ("Evidence", finding.get("evidence"), "mono"),
            ("Attack Path", finding.get("attack_path"), "regular"),
            ("AI / Agent Relevance", finding.get("ai_agent_relevance"), "regular"),
            ("Threat Intelligence", finding.get("threat_intel") or finding.get("threat_intelligence"), "regular"),
            ("Framework Mappings", finding.get("framework_mappings"), "mono"),
            ("Score", finding.get("score"), "mono"),
            ("Recommended Fix", finding.get("recommended_fix"), "regular"),
            ("Regression Test", finding.get("regression_test"), "regular"),
            ("Residual Risk", finding.get("residual_risk"), "regular"),
        ]
        for heading, value, font in sections:
            if heading == "Threat Intelligence" and not value:
                continue
            self.heading(heading, 2)
            self.paragraph(clean_text(value) or "Not provided", size=8.8 if font == "mono" else 9.5, font=font, after=10)

        visualization = attack_visualization_record(finding, target)
        steps = visualization.get("exploit_flow") or []
        if steps:
            self.heading("Attack Path Visualization", 2)
            self.paragraph(visualization.get("summary") or "Not provided", size=9.5, after=6)
            for step_index, step in enumerate(steps, 1):
                label = clean_text(step.get("label") or f"Step {step_index}")
                description = clean_text(step.get("description") or "No description provided.")
                self.paragraph(f"{step_index}. {label}: {description}", size=9.2, font="bold", after=2)
                if step.get("control_gap"):
                    self.paragraph(f"Control gap: {step['control_gap']}", size=8.8, color=COLORS["muted"], after=2)
                if step.get("defensive_breakpoint"):
                    self.paragraph(f"Defensive breakpoint: {step['defensive_breakpoint']}", size=8.8, color=COLORS["teal"], after=4)
            for label, key in (
                ("Attacker goal", "attacker_goal"),
                ("Preconditions", "preconditions"),
                ("Control breaks", "control_breaks"),
                ("Impact", "impact"),
                ("Detection points", "detection_points"),
                ("Defensive breakpoints", "defensive_breakpoints"),
                ("Safety note", "safety_note"),
            ):
                value = clean_text(visualization.get(key))
                if value:
                    self.paragraph(f"{label}: {value}", size=8.8, after=3)


def build_pdf_pages(report: dict[str, Any]) -> list[str]:
    pdf = PdfReport()
    metadata = report["metadata"]
    scope = report["scope"]
    methodology = report["methodology"]
    findings = sort_findings(report["findings"])
    counts = severity_counts(findings)
    target = metadata.get("target") or "Unspecified target"
    skill_coverage = get_skill_coverage(report)
    threat_intel = get_threat_intel(report)
    recommendations = personalized_recommendations(report, findings, target)

    pdf.cover(report)
    pdf.new_page()
    pdf.heading("Scope and Authorization", 1)
    for key in ("environment", "access_level", "authorized", "included", "excluded"):
        pdf.label_value(key.replace("_", " "), scope.get(key))

    pdf.heading("Methodology", 1)
    for key in ("frameworks", "agents_used", "scanner_backends", "mcp_policy"):
        pdf.label_value(key.replace("_", " "), methodology.get(key))

    pdf.heading("Skill Coverage and Specialist Notes", 1)
    pdf.paragraph(
        clean_text(skill_coverage.get("summary"))
        or "Specialist coverage is derived from the agents used in the methodology.",
        size=10,
    )
    specialists = specialist_records(skill_coverage, methodology)
    if specialists:
        for specialist in specialists[:12]:
            pdf.heading(specialist["name"], 2)
            pdf.paragraph(f"Status: {specialist['status']}", size=9.5, font="bold", after=3)
            pdf.paragraph(f"Focus: {specialist['focus'] or 'Not provided'}", size=9.5, after=3)
            pdf.paragraph(f"Coverage: {specialist['coverage'] or 'Not provided'}", size=9.5, after=3)
            if specialist["notes"]:
                pdf.paragraph(f"Notes: {specialist['notes']}", size=9.5, after=6)
    else:
        pdf.paragraph("No specialist coverage was provided.", size=9.5)

    pdf.heading("Threat Intelligence", 1)
    if threat_intel:
        if threat_intel.get("as_of") or threat_intel.get("date"):
            pdf.paragraph(f"As of: {clean_text(threat_intel.get('as_of') or threat_intel.get('date'))}", size=9.5, font="bold")
        pdf.paragraph(clean_text(threat_intel.get("summary")) or "No threat intelligence summary was provided.", size=10)
        for signal in threat_signal_records(threat_intel):
            pdf.heading(signal["theme"], 2)
            pdf.paragraph(f"Why it matters: {signal['relevance'] or 'Not provided'}", size=9.5, after=3)
            pdf.paragraph(f"Recommended action: {signal['recommended_action'] or 'Not provided'}", size=9.5, after=3)
            if signal["linked_findings"]:
                pdf.paragraph(f"Linked findings: {signal['linked_findings']}", size=9, font="bold", color=COLORS["muted"])
        sources = threat_source_records(threat_intel)
        if sources:
            pdf.heading("Threat Intel Sources", 2)
            for source in sources:
                source_line = source["name"]
                if source["url"]:
                    source_line += f" - {source['url']}"
                if source["relevance"]:
                    source_line += f" - {source['relevance']}"
                pdf.paragraph(source_line, size=8.8, color=COLORS["muted"], after=3)
    else:
        pdf.paragraph("No threat intelligence section was provided for this report input.", size=9.5)

    pdf.heading("Personalized Recommendations", 1)
    pdf.paragraph(
        f"These actions are tailored to {target}, the authorization model, actual evidence sources, and the current finding set.",
        size=10,
        color=COLORS["muted"],
    )
    for recommendation in recommendations:
        pdf.heading(recommendation["priority"], 2)
        pdf.paragraph(recommendation["recommendation"] or "Recommended action", size=10, font="bold", after=4)
        pdf.paragraph(f"Why: {recommendation['why'] or 'Prioritized from the current evidence set.'}", size=9.5, after=3)
        pdf.paragraph(f"Owner: {recommendation['owner']}", size=9.5, after=3)
        if recommendation["timeframe"]:
            pdf.paragraph(f"Timeframe: {recommendation['timeframe']}", size=9.5, after=3)
        if recommendation["linked_findings"]:
            pdf.paragraph(f"Linked findings: {recommendation['linked_findings']}", size=9, font="bold", color=COLORS["muted"])

    pdf.heading("Findings Index", 1)
    if findings:
        for index, finding in enumerate(findings, 1):
            fid = clean_text(finding.get("id") or f"F-{index:03d}")
            sev = normalize_severity(finding.get("severity"))
            title = clean_text(finding.get("title") or "Untitled finding")
            pdf.ensure_space(34)
            pdf.severity_chip(sev, pdf.margin, pdf.y - 2)
            pdf.paragraph(f"{fid}: {title}", x=pdf.margin + 84, width=410, size=9.5, font="bold", after=3)
    else:
        pdf.paragraph("No material findings were provided.")

    for index, finding in enumerate(findings, 1):
        pdf.finding(index, finding, target)

    pdf.new_page()
    pdf.heading("Personalized Remediation Roadmap", 1)
    for index, finding in enumerate(findings, 1):
        fid = clean_text(finding.get("id") or f"F-{index:03d}")
        pdf.heading(fid, 2)
        pdf.paragraph(clean_text(finding.get("recommended_fix")) or "Not provided", size=9.5)

    pdf.heading("Regression Test Plan", 1)
    for index, finding in enumerate(findings, 1):
        fid = clean_text(finding.get("id") or f"F-{index:03d}")
        pdf.heading(fid, 2)
        pdf.paragraph(clean_text(finding.get("regression_test")) or "Not provided", size=9.5)

    pdf.heading("Residual Risk and Assumptions", 1)
    pdf.paragraph(
        "Residual risk depends on complete remediation, regression test adoption, scanner coverage, evidence redaction, and continued enforcement of deterministic authorization around model-driven actions.",
        size=10,
    )
    pdf.paragraph(f"Overall verdict: {verdict_from_counts(counts)}", size=10, font="bold")
    pdf.paragraph(f"Report title: {metadata.get('title') or 'Hades Blackwatch Security Report'}", size=9, color=COLORS["muted"])
    return pdf.finish()


def make_pdf(report: dict[str, Any]) -> bytes:
    pages = build_pdf_pages(report)
    objects: list[bytes] = []

    def add_object(content: bytes) -> int:
        objects.append(content)
        return len(objects)

    font_regular = add_object(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    font_bold = add_object(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>")
    font_mono = add_object(b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>")

    content_refs = []
    for commands in pages:
        stream = commands.encode("latin-1", errors="replace")
        content = b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream"
        content_refs.append(add_object(content))

    pages_obj_placeholder = len(objects) + len(content_refs) + 1
    page_refs = []
    for content_ref in content_refs:
        page_refs.append(
            add_object(
                f"<< /Type /Page /Parent {pages_obj_placeholder} 0 R /MediaBox [0 0 612 792] "
                f"/Resources << /Font << /F1 {font_regular} 0 R /F2 {font_bold} 0 R /F3 {font_mono} 0 R >> >> "
                f"/Contents {content_ref} 0 R >>".encode("ascii")
            )
        )

    kids = " ".join(f"{ref} 0 R" for ref in page_refs)
    pages_obj = add_object(f"<< /Type /Pages /Kids [{kids}] /Count {len(page_refs)} >>".encode("ascii"))
    catalog_obj = add_object(f"<< /Type /Catalog /Pages {pages_obj} 0 R >>".encode("ascii"))

    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, 1):
        offsets.append(len(out))
        out.extend(f"{index} 0 obj\n".encode("ascii"))
        out.extend(obj)
        out.extend(b"\nendobj\n")
    xref = len(out)
    out.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    out.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        out.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    out.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root {catalog_obj} 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode("ascii")
    )
    return bytes(out)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="Normalized findings JSON or full report JSON")
    parser.add_argument("--output-dir", default="reports", help="Output directory")
    parser.add_argument("--formats", default="html,pdf", help="Comma-separated: html,pdf")
    parser.add_argument("--title", help="Override report title")
    parser.add_argument("--target", help="Override target name")
    args = parser.parse_args()

    report = load_report(Path(args.input))
    if args.title:
        report["metadata"]["title"] = args.title
    if args.target:
        report["metadata"]["target"] = args.target

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    title = report["metadata"].get("title") or "Hades Blackwatch Security Report"
    target = report["metadata"].get("target") or "target"
    base = slug(f"{target}-{title}")
    requested = {fmt.strip().lower() for fmt in args.formats.split(",") if fmt.strip()}
    outputs = []

    if "html" in requested:
        html_path = output_dir / f"{base}.html"
        html_path.write_text(render_html(report), encoding="utf-8")
        outputs.append(str(html_path))

    if "pdf" in requested:
        pdf_path = output_dir / f"{base}.pdf"
        pdf_path.write_bytes(make_pdf(report))
        outputs.append(str(pdf_path))

    print(json.dumps({"outputs": outputs}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
