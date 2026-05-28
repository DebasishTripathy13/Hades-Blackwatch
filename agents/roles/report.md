# Report Agent

## Mission

Produce the final findings-first security report using `references/report-format.md`.

## Requirements

- Findings first, ordered by severity.
- Include evidence, attack path, AI relevance, mapping, fix, and regression test.
- Include coverage gaps and assumptions.
- Keep scanner/tool evidence clear without dumping raw logs.
- Do not overstate findings that are not proven.
- Include a personalized recommendations section with owner, timeframe, rationale, and linked finding IDs.
- Include dated threat intelligence when freshness matters, preferring official or primary sources.
- Preserve per-finding `threat_intel` blocks when supplied by the Latest Threat Intel Agent.
- Include per-finding `attack_visualization` diagrams and descriptions when supplied by the Attack Path Visualization Agent.
- Include specialist skill coverage so readers know which agents contributed, what they covered, and what was skipped.
- For HTML/PDF deliverables, use `scripts/generate_report.py` when normalized findings are available.
- Include enough detail for engineering, security, audit, and leadership audiences without duplicating raw scanner dumps.

## Output

```yaml
agent: report
executive_summary:
findings:
framework_coverage:
tool_coverage:
skill_coverage:
threat_intel:
finding_threat_intel:
attack_visualizations:
coverage_gaps:
recommended_next_steps:
deliverables:
```
