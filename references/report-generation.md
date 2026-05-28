# Report Generation

Use this file when creating detailed HTML and PDF deliverables from AI AppSec findings.

## Goals

The report must serve four audiences:

- Leadership: risk posture, top risks, decision needed.
- Security: exploitability, evidence, mappings, residual risk.
- Engineering: affected components, fixes, tests, owners.
- Audit/GRC: methodology, scope, frameworks, evidence sources, assumptions.

## Required Sections

1. Cover page: title, target, date, author, classification, report version.
2. Executive summary: verdict, risk posture, top risks, quick counts, required decisions.
3. Scope and authorization: target, environment, access level, excluded systems, approval status.
4. Methodology: frameworks, agents used, scanner backends, MCP policy, testing constraints.
5. Skill coverage: specialist agents used, why each mattered, coverage notes, and any skipped specialist work.
6. Threat intelligence: dated official sources, target-specific signals, linked findings, and review implications.
7. Personalized recommendations: actions tailored to the target, owners, timeframe, rationale, and linked finding IDs.
8. Risk summary: severity distribution and priority roadmap.
9. Detailed findings: one complete section per finding.
10. AI-specific attack paths: prompt injection, RAG, memory, tool abuse, MCP, agent identity, excessive agency.
11. Framework coverage: OWASP LLM, OWASP Agentic, MITRE ATLAS, NIST AI RMF, AIVSS, CWE/CVE where available.
12. Remediation roadmap: immediate, short-term, medium-term, long-term.
13. Regression test plan: unit, integration, eval, scanner, CI gate, runtime detection.
14. Residual risk and assumptions.
15. Appendices: evidence index, tool versions, skipped checks, raw finding IDs.

## Report Detail Standard

Every material finding must include:

- Severity and confidence.
- Business impact.
- Affected component, file, endpoint, or asset.
- Evidence summary.
- Attack path.
- AI/agent relevance.
- Framework mappings.
- Root cause.
- Recommended fix.
- Verification or regression test.
- Residual risk.

## Generation Script

Use:

```bash
python scripts/generate_report.py examples/report-input.example.json --formats html,pdf --output-dir reports
```

Input may be:

- Output from `scripts/normalize_findings.py`.
- A JSON object with `findings`.
- A full report object with `metadata`, `scope`, `methodology`, and `findings`.

The script uses no external Python dependencies. PDF output is text-focused for portability; HTML is the richer shareable report.

Optional top-level fields:

- `skill_coverage`: Summary plus `specialists` entries with name, status, focus, coverage, and notes.
- `threat_intel`: Dated `summary`, `signals`, and `sources` for current official guidance or observed threat activity.
- `personalized_recommendations`: Tailored actions with priority, owner, timeframe, rationale, and linked findings.
- `findings[].threat_intel`: Per-finding threat intelligence from the Latest Threat Intel Agent, including source links, mapped techniques, detection/test implications, freshness, and confidence.
- `findings[].attack_visualization`: Per-finding defender-safe exploit-flow description, diagram steps, control breaks, detection points, and defensive breakpoints.

If `personalized_recommendations` is not supplied, the generator creates target-specific recommendations from the current findings, severity, affected components, and fixes.
If `attack_visualization` is not supplied, the generator creates a conservative conceptual flow from the finding attack path, affected component, affected asset, fix, and regression test.
