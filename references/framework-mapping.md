# Framework Mapping

Use this file when translating raw observations into risk categories, scores, and governance controls.

## Primary Mapping Order

1. OWASP LLM Top 10 for LLM application risks.
2. OWASP Agentic Top 10 for autonomous agents, tools, memory, identity, and workflows.
3. OWASP Agentic Skills Top 10 for skills, plugins, local agent config, and MCP-adjacent execution layers.
4. MITRE ATLAS for adversary tactics, techniques, and mitigations.
5. OWASP AIVSS for AI or agentic vulnerability scoring.
6. NIST AI RMF GenAI Profile for governance, monitoring, lifecycle, and accountability.
7. OWASP Web/API Top 10 and CWE/CVSS for conventional appsec issues.

## Common Risk Crosswalk

| Observation | OWASP LLM | Agentic Risk | MITRE ATLAS Theme | Notes |
| --- | --- | --- | --- | --- |
| Prompt injection changes behavior | Prompt Injection | Agent Goal Hijack | Prompt injection / LLM manipulation | Check direct and indirect sources. |
| LLM output reaches shell, SQL, browser, or HTML sink | Insecure Output Handling | Tool Misuse | Execution / impact | Find deterministic validation boundary. |
| Agent can call tools beyond user intent | Excessive Agency | Tool Misuse / Rogue Agent | Execution / impact | Check approval, policy, and least privilege. |
| Tool uses broad OAuth scope or inherited identity | Sensitive Information Disclosure | Identity and Privilege Abuse | Credential access / privilege | Check token audience and scope. |
| Retrieved document contains hidden instructions | Prompt Injection | Memory and Context Poisoning | Data poisoning / evasion | Treat RAG content as untrusted. |
| Cross-tenant retrieval or memory leak | Sensitive Information Disclosure | Identity and Privilege Abuse | Collection / exfiltration | Verify tenant filters are deterministic. |
| MCP server exposes `run_command` or filesystem writes | Insecure Plugin Design | Unexpected Code Execution | Execution / escape | Classify T4 unless constrained. |
| Compromised plugin/skill/server update | Supply Chain Vulnerability | Agentic Supply Chain | Supply chain compromise | Check provenance, pinning, and signatures. |

## Scoring Guidance

Use AIVSS when the exploitability or impact is amplified by autonomy, memory, tool access, or delegated identity. Include conventional severity only as supporting context.

Minimum score inputs to capture:

- Agent autonomy level.
- Tool privilege and blast radius.
- Data sensitivity.
- Persistence through memory, workflow, or scheduled jobs.
- Human approval or review boundary.
- Detectability and auditability.
- Reproducibility of the attack path.

If AIVSS details are unavailable, state a qualitative severity and explain which AIVSS factors would likely raise or lower it.
