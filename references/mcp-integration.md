# MCP Integration

Use this file when reviewing or using MCP servers, MCP clients, tools, resources, prompts, or agent skills that connect to tools.

## MCP Necessity Rule

MCP usage is allowed only in absolute-need cases or when the user explicitly asks for MCP-backed evidence. Agents must prefer these sources first:

1. Local source code and configuration.
2. Existing scanner reports or exported evidence.
3. User-provided architecture, policy, and screenshots.
4. Static scripts bundled with this skill.
5. Read-only public/vendor documentation.

Only after those are insufficient should an agent link to or call an MCP server.

## Necessity Test

Before using MCP, record:

```yaml
mcp_necessity:
  evidence_needed:
  safer_sources_checked:
  why_mcp_is_needed:
  selected_server:
  selected_tool:
  expected_risk_tier:
  approval_required:
```

If this cannot be completed, do not call MCP. Report the missing evidence and recommended follow-up.

## MCP Review Questions

- What servers are connected?
- Which transport is used: local STDIO, HTTP, streamable HTTP, or other?
- What tools, resources, and prompts are exposed?
- Which tools are read-only, state-changing, privileged, or code-executing?
- Where are credentials stored?
- Are OAuth tokens audience-bound to the MCP server?
- Are tool descriptions trusted from an untrusted server?
- Are approvals required for privileged tools?
- Can the server fetch arbitrary URLs or access internal networks?
- Can the server read or write files outside intended roots?
- Can prompt injection influence tool selection or parameters?
- Is every tool call logged with caller, target, inputs, and outcome?

## Risk Tiers

| Tier | Examples | Review Action |
| --- | --- | --- |
| T0 | Public docs, public package metadata | Low risk, still validate source. |
| T1 | Private read-only repo/issues/scanner findings | Check data exposure and logging. |
| T2 | Update issue status, create comments, scoped scan config | Require explicit task reason. |
| T3 | Launch scans, create tickets, mutate security platform state | Require approval or prior authorization. |
| T4 | Shell, filesystem write/delete, cloud admin, credential CRUD, arbitrary browser actions | Disable unless explicitly authorized. |

## Tool Contract Red Flags

- Tool names like `run`, `execute`, `do_anything`, `admin`, `eval`, `shell`, `browser_action`.
- Free-form parameters named `command`, `script`, `url`, `path`, `query`, `payload`, `headers`, or `body` without allowlists.
- Tool descriptions that promise broad authority.
- Missing descriptions or missing input schema.
- Credentials or tokens in tool schemas, examples, logs, or outputs.
- Tools that accept arbitrary URLs and run server-side requests.
- Tools that proxy OAuth tokens to downstream services without audience validation.
- Tools that return raw secrets or full HTTP traffic by default.

## Required Controls

- Explicit outbound host allowlists for scanners and URL fetchers.
- Strong schema validation for all tool inputs.
- Separate read-only and write/action tools.
- Human approval for T3/T4 actions.
- Token audience validation and no token passthrough.
- Redaction for secrets, cookies, authorization headers, and session tokens.
- Structured errors that do not leak internal network or credential details.
