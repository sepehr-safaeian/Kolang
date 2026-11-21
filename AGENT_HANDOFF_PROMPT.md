# Prompt for the implementation agent — Kolang UI

You are implementing the production UI for **Kolang**, an Agent Control Plane / MCP Gateway. Your job is to build a coherent, accessible, premium-feeling European enterprise interface — not a generic AI dashboard.

## Read first

1. `MASTER_DESIGN_SYSTEM_FA.md` — product-specific visual and interaction rules.
2. `tokens.json` — canonical machine-readable design tokens.
3. `kolang.css` — ready-to-integrate semantic CSS variables and base primitives.

Do not start coding before reading all three files.

## Visual direction

Use the **European Technical Editorial / The Control Surface** direction:
- Light-first warm neutral canvas, deep jade accent, crisp one-pixel borders.
- Compact, deliberate radius; minimal shadows; no gradients, glows, glassmorphism, neon, mesh backgrounds or ornamental animation.
- Strong typographic hierarchy and calm density. Operational data is the visual content.
- Lucide-style outline icons only, consistent stroke and sizing.
- Use Inter or Geist Sans for Latin, Vazirmatn for Persian, and Geist Mono or IBM Plex Mono for technical identifiers.

## Product IA

Operate: Overview, Gateways, Agents, MCP Servers, Tools.

Govern: Policies, Approvals, Access & Secrets.

Observe: Runs & Traces, Audit Log.

Manage: Workspaces, Settings.

## Required foundation

Implement:
- semantic token integration from `kolang.css`;
- light and dark themes by switching `data-theme`;
- RTL and LTR support from the root `dir` attribute;
- responsive application shell (248px expanded sidebar, 68px collapsed sidebar, 60px topbar);
- reusable PageHeader, Button, Input, Select/Combobox, StatusBadge, DataTable, FilterBar, Metric, CodeBlock, JsonViewer, Dialog, Drawer, Toast and EmptyState;
- consistent loading, empty, error, disabled, focus, hover and selected states.

## First implementation slice

Build the application shell and an Overview page with:
1. Page header and `Add gateway` primary action.
2. Requests, error rate, p95 latency and active gateways metrics, each with a clear time range.
3. Traffic/latency visualization with units, timestamps and useful tooltips.
4. Recent activity table.
5. Needs-attention section for degraded connections, pending approvals, unpublished policies and expiring secrets.

Use mock data only when necessary, and visibly label it `Demo data`.

## Second implementation slice

Build one representative end-to-end screen for each domain pattern:
- MCP Server detail: connection, capabilities, tools, credentials metadata and health history.
- Tool detail: owning server, description, input/output schema and effective permissions.
- Policy builder: scope, subject, conditions, effect, priority, preview/evaluation and publish state.
- Approval review: requester, requested tool/action, context, risk, payload and explicit approve/deny actions.
- Trace inspector: trace summary, span tree/timeline, duration/status and payload inspector.
- Audit log: actor, action, target, timestamp, outcome and correlation ID.

## Non-negotiable implementation constraints

- Never hardcode colors, spacing, radii or typography values in individual components when a token exists.
- Never use left/right CSS positioning in new styles; use logical properties (`margin-inline`, `padding-inline`, `inset-inline-*`).
- Never assume RTL is only right-aligned text. Test layout, order, icons, tables, breadcrumbs and controls in both directions.
- Keep technical strings (URLs, IDs, JSON, IPs, tokens) in LTR containers.
- Never rely on color alone for status; include a text label or accessible name.
- Never show a secret in full by default.
- Do not invent success states before an operation has actually completed.
- No placeholder charts without meaningful axes, units, timestamps and ranges.
- Do not add a new dependency unless the existing stack cannot reasonably support the requirement.
- Do not redesign the brand mascot or invent extra brand colors.

## Review checklist before calling a page complete

- [ ] Light theme
- [ ] Dark theme
- [ ] RTL
- [ ] LTR
- [ ] 1440px desktop
- [ ] 1024px compact desktop/tablet
- [ ] 768px tablet
- [ ] 390px mobile
- [ ] keyboard-only critical flow
- [ ] visible focus state
- [ ] loading / empty / error / disabled / success states
- [ ] no unexplained hardcoded visual values
- [ ] no forbidden visual effects

## Design quality test

The result should look credible in a serious European infrastructure product: quiet, precise, information-rich, legible and unmistakably consistent. Do not optimize for a Dribbble-only hero shot at the expense of real workflows. The interface must remain excellent when populated with dense tables, long IDs, errors, policy rules and trace data.
