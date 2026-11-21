# Kolang Core Laws & Operational Directives

> **Status:** Permanent Mandatory Policy  
> **Target:** All Agents, Developers, Workflows, and Tool Invocations operating in the Kolang repository.  
> **Authority:** Non-negotiable. Must be executed precisely on every task.

---

## The 11 Inviolable Laws of Kolang

Every agent and engineer working on Kolang MUST adhere to these eleven foundational laws:

### Law 1: 4-Language Multilingual Standard (i18n)
- **Supported Languages:**
  1. English (`en`) — Default / Canonical
  2. German (`de`)
  3. Russian (`ru`)
  4. Chinese (`zh`) — Simplified
- **Strict Separation of Concerns:**
  - **Internal / Machine:** Error handlers, API responses, telemetry, server logs, trace IDs, and HTTP status payloads are strictly in English.
  - **User Surface:** Anything rendered to the user (labels, tooltips, dialogs, button texts, error states in UI, notifications, placeholders) MUST ALWAYS be localized across all 4 languages.
- **Zero-Tolerance Rule:** Never define hardcoded strings directly in UI components or templates. All strings must reference centralized translation dictionary keys.
- **Bidirectional Layout:** Components must support both LTR and RTL dynamically via `dir="ltr"` or `dir="rtl"`.

### Law 2: Universal Responsiveness & Accessibility (a11y)
- **Viewport Spectrum:** Verify all screens and components across 4 standard viewports:
  1. Mobile (`390px` to `640px`)
  2. Tablet (`641px` to `1024px`)
  3. Laptop (`1024px` to `1440px`)
  4. Desktop (`>1440px`)
- **Shell Dimensions:** Responsive application shell featuring `248px` expanded sidebar, `68px` collapsed sidebar, mobile slide-over drawer (`<768px`), and `60px` topbar.
- **CSS Logical Properties:** Use logical properties exclusively (`margin-inline`, `padding-inline`, `inset-inline-*`, `border-inline-*`). Never use physical `left` or `right` CSS positioning.
- **Accessibility Standard:** WCAG 2.1 AA compliance:
  - Visible focus indicators (`--k-focus`) on all interactive controls.
  - Full keyboard navigability (Tab, Shift+Tab, Enter, Space, Escape).
  - ARIA attributes, semantic HTML tags, and screen reader announcements.
  - Never convey status or meaning using color alone; pair with icons and accessible text labels.

### Law 3: Day-One Dark / Light Mode Cohesion
- Every component must support both **Light** and **Dark** themes seamlessly from its initial commit.
- Theme switching is driven strictly by semantic tokens bound to `:root` and `[data-theme="dark"]`.
- Never hardcode raw color hex codes or rgb values in individual component styles.

### Law 4: Absolute Adherence to Design Tokens & System
- Master reference files:
  - [`MASTER_DESIGN_SYSTEM_FA.md`](file:///c:/Users/Sepehr/Documents/Kolang/MASTER_DESIGN_SYSTEM_FA.md)
  - [`tokens.json`](file:///c:/Users/Sepehr/Documents/Kolang/tokens.json)
  - [`kolang.css`](file:///c:/Users/Sepehr/Documents/Kolang/kolang.css)
  - [`AGENT_HANDOFF_PROMPT.md`](file:///c:/Users/Sepehr/Documents/Kolang/AGENT_HANDOFF_PROMPT.md)
- **Aesthetic Identity:** "European Technical Editorial / The Control Surface".
  - Warm neutral canvas, deep jade accent (`#176B5B` in Light, `#63C5A8` in Dark).
  - Crisp 1px borders, compact deliberate corner radii (`4px`, `6px`, `9px`, `12px`), high information density, tabular numbers for technical data.
- **Forbidden Visuals:** Gradients, glassmorphism, blur, neon glows, heavy drop shadows, oversized rounded corners (20px-32px), animated mesh backgrounds, decorative non-functional charts.

### Law 5: Shadcn UI Architecture with Token Integration
- Use Shadcn UI (Radix primitives) as the foundational component library.
- Adapt and configure all Shadcn components to inherit Kolang semantic design tokens (`--k-*`).
- Maintain consistent interactive states: hover, focus-visible, active, disabled, loading, and empty.

### Law 6: Comprehensive Documentation for Every Unit of Work
- Every function, class, endpoint, schema, component, and module must include thorough documentation:
  - Python: Structured docstrings (Google/Sphinx format) specifying parameters, returns, and raised exceptions.
  - TypeScript/React: TSDoc comments defining props, interfaces, and accessibility considerations.
  - Architectural Docs: Update `docs/` when introducing new subsystems, patterns, or protocols.

### Law 7: Mandatory Test-Driven Verification
- Zero code merged without corresponding automated tests.
- Backend: `pytest`, `pytest-asyncio`, `pytest-cov` covering unit, domain, integration, and security scenarios.
- Frontend: `vitest`, `@testing-library/react`, and end-to-end checks.
- All test suites must execute and pass cleanly before marking any task complete.

### Law 8: Dual Exposure — REST API & MCP Gateway
- Kolang is an Agent Control Plane and Model Context Protocol (MCP) Gateway.
- Every core feature, resource, or capability MUST be accessible through two distinct interfaces:
  1. **RESTful HTTP API** (FastAPI, OpenAPI schema, structured error handling).
  2. **Model Context Protocol (MCP)** (MCP server tools, resources, and prompt definitions).

### Law 9: Strict Alignment with Provided Design Assets
- All UI layouts, terminology, information architecture, and component catalogs must strictly reflect the specifications provided in `MASTER_DESIGN_SYSTEM_FA.md` and `AGENT_HANDOFF_PROMPT.md`.
- Product IA domains:
  - **Operate:** Overview, Gateways, Agents, MCP Servers, Tools
  - **Govern:** Policies, Approvals, Access & Secrets
  - **Observe:** Runs & Traces, Audit Log
  - **Manage:** Workspaces, Settings

### Law 10: Git Cleanliness, Conventional Commits & Continuous Push
- Maintain an active, spotless, and professional Git history.
- Use Conventional Commits strictly: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `perf:`, `chore:`, `ci:`.
- Commit atomically after each verified milestone and push to remote repository (`origin/main`) to maintain visible, continuous project momentum.

### Law 11: Enterprise CI/CD, DevOps & Automation
- Maintain automated GitHub Actions pipelines for:
  - Code quality (Ruff format, Ruff check, Mypy type validation).
  - Test automation with coverage threshold reporting.
  - Multi-arch Docker container builds (`deploy/Dockerfile`).
  - Security audits (Bandit, vulnerability scanning).
