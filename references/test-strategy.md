# Test Strategy

Use this file when running or designing AI security tests.

## Tools

| Tool | Use |
| --- | --- |
| Garak | Broad LLM vulnerability scanning and unwanted behavior discovery. |
| PyRIT | Automated AI red-team orchestration, attack generation, converters, scoring. |
| Promptfoo | LLM app and agent red-team tests, CI/CD evals, custom policies, RBAC/BOLA/BFLA, prompt injection. |
| Giskard | Agent/RAG vulnerability scanning, OWASP LLM category coverage, knowledge-base-aware probes. |

## Test Categories

- Direct prompt injection.
- Indirect prompt injection from web pages, docs, emails, tickets, issues, and RAG chunks.
- System prompt extraction.
- Context poisoning and memory poisoning.
- Tool misuse and unsafe chaining.
- Excessive agency and missing approval.
- Broken object/function level authorization.
- Cross-session, cross-tenant, and memory leakage.
- SSRF, SQL injection, shell injection, XSS, and insecure output handling.
- Denial of wallet or model/resource exhaustion.
- Unsafe fallback and exception handling.

## Testing Safety

- Only test authorized targets.
- Prefer non-destructive probes.
- Do not launch active scans against production without explicit approval.
- Disable state-changing tools during adversarial tests unless the objective requires them and approval is recorded.
- Use canary resources instead of real secrets or customer data.

## Regression Test Pattern

Each test should include:

```yaml
name:
risk:
preconditions:
input:
expected_control:
forbidden_outcome:
assertion:
framework_mapping:
```
