# Report Format

Use this format for final reports and imported finding normalization.

## Executive Summary

- Overall verdict: pass, pass with conditions, request changes, block, or needs more evidence.
- Highest risk path.
- Most important fixes.
- Coverage gaps.

## Finding Schema

```yaml
id:
title:
severity:
confidence:
status:
source_tools:
affected_component:
affected_file:
affected_endpoint:
affected_asset:
evidence:
attack_path:
ai_agent_relevance:
threat_intel:
  as_of:
  summary:
  sources:
  signals:
  mapped_techniques:
  detection_or_test:
  freshness:
  confidence:
attack_visualization:
  title:
  summary:
  attacker_goal:
  preconditions:
  exploit_flow:
    - label:
      description:
      actor:
      control_gap:
      defensive_breakpoint:
  control_breaks:
  impact:
  detection_points:
  defensive_breakpoints:
  diagram_note:
  safety_note:
framework_mappings:
  owasp_llm:
  owasp_agentic:
  mitre_atlas:
  nist_ai_rmf:
  cwe:
  cve:
score:
  system: AIVSS
  value:
  rationale:
recommended_fix:
regression_test:
residual_risk:
```

## Severity Guidance

Critical:
An attacker can cause unauthorized privileged action, cross-tenant data exposure, credential theft, code execution, destructive action, or systemic agent failure.

High:
An attacker can bypass key AI/tool/data controls, exfiltrate sensitive information, trigger unsafe tool paths, or exploit a confirmed appsec vulnerability reachable by the AI workflow.

Medium:
Exploit requires meaningful preconditions or impact is limited, but a real control weakness exists.

Low:
Defense-in-depth gap, weak signal, or low-impact issue.

Informational:
Useful hardening or coverage note.

## Findings-First Rule

Lead with findings. Put methodology, tool coverage, and long framework discussion after the issues.

## Deliverable Formats

When the user asks for a file deliverable, generate both:

- HTML: detailed, styled, navigable, and suitable for sharing or printing.
- PDF: fixed-format executive/audit artifact generated from the same normalized finding data.

Use `scripts/generate_report.py` for repeatable report generation. See [report-generation.md](report-generation.md).
