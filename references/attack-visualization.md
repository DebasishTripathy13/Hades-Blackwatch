# Attack Visualization Protocol

Use this reference when the Attack Path Visualization Agent is active or when a report needs defensive diagrams for vulnerabilities.

## Objective

Every material finding should be understandable without forcing the reader to mentally reconstruct the exploit chain. The visualization should answer:

- What does the attacker influence?
- Which component trusts the wrong thing?
- Which control fails?
- What asset or business process is affected?
- Where can defenders detect or break the chain?

## Safety Boundary

Visualizations are for defensive review. They must not include:

- Exploit payloads.
- Step-by-step unauthorized exploitation instructions.
- Credential theft recipes.
- Bypass strings or jailbreak text.
- Tool commands that run active attacks.

Use conceptual descriptions such as "untrusted prompt influences a tool parameter" instead of operational payloads.

## Finding Field

Use this shape inside a finding:

```yaml
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
```

## Recommended Flow

Use five to seven steps:

1. Attacker influence or entry condition.
2. Vulnerable input, prompt, tool, MCP schema, scanner evidence, RAG document, or code path.
3. Failed deterministic control.
4. Propagation through the AI/application workflow.
5. Impacted asset or security outcome.
6. Detection or monitoring point.
7. Defensive breakpoint or remediation gate.

## Diagram Style

Prefer simple left-to-right or top-to-bottom flows that work in HTML and PDF:

```text
Influence -> Trust Boundary -> Control Failure -> Propagation -> Impact -> Detection -> Breakpoint
```

For complex systems, split the diagram into two lanes:

- Attack flow.
- Defensive breakpoints.

Keep labels short. Put longer explanation in the surrounding text.

## Quality Bar

- The diagram must be specific to the affected component and asset.
- The description must be understandable to non-specialists.
- Every visualization should include at least one detection point and one defensive breakpoint.
- If evidence is weak, mark confidence and avoid overstating exploitability.
