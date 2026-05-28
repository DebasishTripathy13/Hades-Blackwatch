# Agent Stack

Use this file when a user asks for full-stack review, multi-agent workflow, or focused specialist review.

## Orchestration Pattern

The Security Orchestrator owns scope, authorization, task routing, final severity, and the final report. Specialist agents produce evidence and candidate findings, not final verdicts.

## Handoff Format

Each specialist should return:

```yaml
agent:
scope:
evidence:
candidate_findings:
coverage_gaps:
threat_intel:
confidence:
requested_followup:
```

## Specialist Prompts

### Latest Threat Intel Agent

Check official or primary sources for current framework, tool, API, and vulnerability information. Prefer OWASP, NIST, MITRE, vendor docs, CVE/NVD, GitHub advisories, and official release notes.

The agent should enrich every active specialist domain and every material finding:

```yaml
domain_intel:
  domain:
  sources_checked:
  current_signals:
  review_implications:
  checks_to_add:
finding_intel:
  - finding_id:
    summary:
    sources:
    mapped_techniques:
    recommended_action:
    detection_or_test:
    confidence:
```

Use [threat-intel.md](threat-intel.md) for the full protocol.

### Attack Path Visualization Agent

Create defender-safe diagrams and descriptions for each material finding. Show how a vulnerability works conceptually, where the control fails, what asset is affected, and where defenders can detect or break the chain.

```yaml
finding_visualizations:
  - finding_id:
    attack_visualization:
      title:
      summary:
      attacker_goal:
      preconditions:
      exploit_flow:
      control_breaks:
      impact:
      detection_points:
      defensive_breakpoints:
      safety_note:
```

Use [attack-visualization.md](attack-visualization.md) for the full protocol. Do not include exploit payloads, bypass strings, or unauthorized testing instructions.

### AI Threat Model Agent

Map assets, trust boundaries, identities, data flows, prompts, tools, RAG sources, memory, logs, APIs, webhooks, background jobs, and deployment environments.

### MCP Server Auditor Agent

List tools, resources, prompts, transports, auth, environment secrets, outbound network permissions, filesystem permissions, approval rules, and dangerous tool schemas.

### Scanner Registry Agent

Detect scanner availability and choose integration mode: native MCP, API-wrapped MCP, CLI bridge, or report ingest. Record skipped tools and why.

### Finding Correlator Agent

Merge duplicate findings across evidence sources. Prefer a single high-confidence finding when multiple tools point to the same root cause.

Example: Sonar identifies an SSRF sink, Burp proves an endpoint reaches it, and Qualys shows the host is externally exposed. Correlate into one finding with higher confidence.

### Test Builder Agent

For every material finding, propose one or more regression controls:

- Unit test.
- Integration test.
- Prompt/security eval.
- Scanner rule.
- CI gate.
- Runtime detection or alert.
