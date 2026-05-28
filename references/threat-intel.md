# Threat Intelligence Agent Protocol

Use this reference when the Latest Threat Intel Agent is active or when a report needs per-domain or per-finding threat context.

## Objective

Threat intelligence must help the review become more precise. It should explain why a finding matters now, what attacker pattern it resembles, which sources support that assessment, and what concrete test or mitigation follows.

## Source Order

Prefer sources in this order:

1. Official framework pages and specifications: OWASP GenAI, OWASP Agentic Skills, OWASP AIVSS, MITRE ATLAS, NIST AI RMF GenAI Profile, MCP specification and security guidance.
2. Vendor advisories and documentation: Burp, Qualys, SonarQube, Semgrep, CodeQL, Trivy, Promptfoo, Giskard, Garak, PyRIT, model providers, cloud providers, and MCP server vendors.
3. Vulnerability databases and advisory sources: CVE/NVD, GitHub Security Advisories, OSV, vendor release notes.
4. Primary research from recognized security labs when official guidance is not available.

Avoid unsourced social posts, generic blogs, and stale copies of official pages unless they are clearly marked as background only.

## Domain Matrix

For every active specialist, produce one short domain entry:

```yaml
domain:
sources_checked:
current_signals:
review_implications:
checks_to_add:
confidence:
freshness:
```

Recommended domains:

- `ai-threat-model`: ATLAS tactics, data flows, model/runtime trust boundaries, governance gaps.
- `prompt-injection`: direct and indirect injection, jailbreaks, prompt leakage, tool hijack.
- `agent-tool-security`: excessive agency, delegated authorization, unsafe tool chains, approvals.
- `mcp-server-auditor`: MCP auth, token passthrough, SSRF, local runtime risk, dangerous schemas.
- `rag-data-security`: poisoning, retrieval leakage, tenant isolation, embedding/vector exposure.
- `secure-code-review`: conventional vulnerabilities that become AI exploit paths.
- `scanner-registry`: scanner coverage freshness, connector limitations, imported evidence quality.
- `supply-chain`: dependencies, plugins, skills, MCP servers, models, containers, CI/CD.
- `report`: evidence minimization, source traceability, report distribution, audit readiness.

## Per-Finding Enrichment

Every material finding should get a compact threat-intel block when the threat context changes severity, priority, remediation, test design, or stakeholder explanation:

```yaml
threat_intel:
  as_of:
  summary:
  sources:
    - name:
      url:
      relevance:
  signals:
    - theme:
      relevance:
      recommended_action:
  mapped_techniques:
    mitre_atlas:
    cwe:
    cve:
  detection_or_test:
  freshness:
  confidence:
```

The finding should remain findings-first. Threat intel supports the finding; it does not replace evidence from code, runtime behavior, scanner output, or authorized tests.

## MCP Use

MCP is optional and escalation-only. Use MCP for threat intel only when:

- The user explicitly asks for a connected internal threat-intel source, or
- Required private evidence is unavailable from local files, imported reports, or public official sources.

Before any MCP call, record the MCP necessity decision and classify the tool tier.

## Quality Bar

- Include source dates or access dates when the source is likely to change.
- Link the threat signal to one or more checks, fixes, detections, or tests.
- Keep the report short enough to help decisions.
- Mark confidence clearly when sources conflict or when a signal is emerging.
- Do not include exploit payloads or operational instructions beyond safe defensive validation.
