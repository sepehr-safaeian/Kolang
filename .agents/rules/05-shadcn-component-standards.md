# Rule 05: Shadcn UI & Component Architecture

> **Mandate:** All frontend components must be built on top of Shadcn UI / Radix primitives and customized exclusively to consume Kolang semantic design tokens.

---

## 1. Required Foundational Primitives

All screens must be composed from this standardized component catalog:

1. **`Button`:**
   - Variants: `primary` (Jade background, white text), `secondary` (Surface background, 1px border), `ghost` (transparent), `danger` (Red subtle background, red text).
   - Supports `loading` spinner state with `aria-busy="true"`.
2. **`Input` & `Textarea`:**
   - 1px border (`var(--k-border)`), focus ring (`var(--k-focus)`), disabled state with `opacity: 0.6`.
3. **`Select` / `Combobox`:**
   - Searchable, keyboard-driven popover menu matching `--k-surface-raised`.
4. **`StatusBadge`:**
   - Compact pill with icon + label, strictly mapped to semantic status tokens (success, warning, danger, info, neutral).
5. **`DataTable`:**
   - High information density, tabular numbers, sortable headers, selectable rows with `--k-surface-selected`, sticky header capability.
6. **`FilterBar`:**
   - Search input, faceted filter dropdowns, active filter pills, and "Clear filters" action.
7. **`MetricCard`:**
   - Large numeric metric (`--k-text-metric`), trend indicator (with delta percentage and timeframe), and contextual caption.
8. **`CodeBlock` & `JsonViewer`:**
   - Monospace font (`var(--k-font-mono)`), syntax highlighting, copy-to-clipboard action, strictly LTR container.
9. **`Dialog` & `Drawer`:**
   - Modal dialogs for focused critical actions (with `--k-shadow-dialog`); sliding drawer for inspect panels (server detail, trace details).
10. **`Toast`:**
    - Ephemeral notification with status styling and accessible dismiss action.
11. **`EmptyState`:**
    - Clean illustration/icon, clear title, explanatory paragraph, and primary CTA (e.g. "Register MCP Server").

---

## 2. Product Information Architecture (IA)

All navigation links and page structures must strictly adhere to the defined 4 domains:

```
├── Operate
│   ├── Overview
│   ├── Gateways
│   ├── Agents
│   ├── MCP Servers
│   └── Tools
├── Govern
│   ├── Policies
│   ├── Approvals
│   └── Access & Secrets
├── Observe
│   ├── Runs & Traces
│   └── Audit Log
└── Manage
    ├── Workspaces
    └── Settings
```

---

## 3. Component State Contract

Every component must handle and visually reflect all 7 states:
1. **Default:** Clean, unactivated appearance.
2. **Hover:** Subtle luminance shift (`--k-accent-hover` or `--k-surface-muted`).
3. **Focus:** Unmistakable 2px focus ring (`--k-focus`).
4. **Active / Pressed:** Visual depression / darkened background.
5. **Disabled:** Reduced opacity, `cursor: not-allowed`, inert event handling.
6. **Loading / Busy:** Skeleton loader or spinner, screen reader `aria-busy="true"`.
7. **Empty:** Dedicated empty state layout explaining what's missing and next steps.
