# Kolang Project Master Operational Directives

> **Repository:** `Kolang` (Open-Source Agent Control Plane & MCP Gateway)  
> **Status:** Binding Master Rules for all AI Agents and Automated Workflows  
> **Authority:** Inviolable. All instructions herein must be followed without exception on every task.

---

## 1. Core Mandate & Project Identity

Kolang is an enterprise-grade infrastructure platform providing secure, governed access to AI tool infrastructure via Model Context Protocol (MCP) and REST APIs.
All contributions must reflect the quality of a world-class European enterprise infrastructure product: quiet, precise, information-rich, accessible, and robust.

---

## 2. The 11 Inviolable Laws of Kolang

Every task executed in this repository MUST comply with these eleven laws:

### 1. 4-Language Multilingual Standard (i18n)
- **Languages:** English (`en` - Default), German (`de`), Russian (`ru`), Chinese Simplified (`zh`).
- **Strict Separation:**
  - Machine/API/Error Handler internals: **English strictly**.
  - All User-Facing UI (labels, buttons, tooltips, dialogs, notifications, placeholders): **Always localized in all 4 languages**.
- **Zero Hardcoded Strings:** NEVER write raw text strings inside UI components. All text must use translation dictionary keys.
- **Directionality:** Support LTR and RTL dynamically via `dir` attribute and CSS logical properties.

### 2. Universal Responsiveness & Accessibility (a11y)
- **Viewport Spectrum:** Verify all layouts on:
  - Mobile (`390px` – `640px`)
  - Tablet (`641px` – `1024px`)
  - Laptop (`1024px` – `1440px`)
  - Desktop (`>1440px`)
- **Shell Dimensions:** Responsive shell: `248px` expanded sidebar, `68px` collapsed sidebar, mobile sheet/drawer (`<768px`), `60px` topbar.
- **CSS Logical Properties:** Use `margin-inline`, `padding-inline`, `inset-inline-*`, `border-inline-*`. Never use physical `left` or `right` CSS positioning.
- **WCAG 2.1 AA:** Visible focus ring (`--k-focus`), full keyboard operability, ARIA labels, semantic HTML, and multi-modal status indicators (never rely on color alone).

### 3. Day-One Dark / Light Mode Cohesion
- Every component must support both **Light** and **Dark** themes from the moment it is written.
- Driven via semantic CSS variables (`:root` / `[data-theme="dark"]`).
- Never hardcode raw hex/rgb values in component files.

### 4. Absolute Adherence to Design Tokens & System
- Master references:
  - [`MASTER_DESIGN_SYSTEM_FA.md`](file:///c:/Users/Sepehr/Documents/Kolang/MASTER_DESIGN_SYSTEM_FA.md)
  - [`tokens.json`](file:///c:/Users/Sepehr/Documents/Kolang/tokens.json)
  - [`kolang.css`](file:///c:/Users/Sepehr/Documents/Kolang/kolang.css)
  - [`AGENT_HANDOFF_PROMPT.md`](file:///c:/Users/Sepehr/Documents/Kolang/AGENT_HANDOFF_PROMPT.md)
- **Design Direction:** "European Technical Editorial / The Control Surface".
  - Warm neutral canvas (`#F7F8F6` light / `#111816` dark).
  - Deep Teal / Signal Jade accent (`#176B5B` light / `#63C5A8` dark) used purposefully.
  - Crisp 1px borders, compact radii (`4px`, `6px`, `9px`, `12px`), tabular numbers for technical data.
- **Strictly Forbidden:** Multi-color gradients, neon glow, glassmorphism, blur backgrounds, heavy card drop shadows, giant 20px-32px radii, decorative non-functional charts, and mascot spamming.

### 5. Shadcn UI Architecture with Token Integration
- Use Shadcn UI (Radix primitives) for all UI components.
- Style and configure all Shadcn components to strictly consume Kolang semantic design tokens (`--k-*`).
- Maintain consistent interactive states: default, hover, focus, active, disabled, loading, and empty.

### 6. Comprehensive Documentation
- Every function, method, endpoint, and component must include structured docstrings / TSDoc.
- Document arguments, return values, exceptions, and accessibility behavior.
- Keep `docs/` synchronized with architectural and API additions.

### 7. Mandatory Test-Driven Verification
- Zero untested code. Every new feature, endpoint, or function requires unit and integration tests.
- Backend: `pytest`, `pytest-asyncio`, `pytest-cov`.
- Frontend: `vitest`, `@testing-library/react`.
- All tests must pass cleanly before marking any task complete.

### 8. Dual Architecture: REST API & MCP Gateway
- Kolang is both a REST API and a Model Context Protocol (MCP) Gateway.
- Every core domain capability must be exposed via both:
  1. RESTful HTTP endpoints (FastAPI, OpenAPI 3.1).
  2. Native MCP server tools, resources, and prompts.

### 9. Strict Adherence to Information Architecture
- The product is structured into four primary domains:
  - **Operate:** Overview, Gateways, Agents, MCP Servers, Tools
  - **Govern:** Policies, Approvals, Access & Secrets
  - **Observe:** Runs & Traces, Audit Log
  - **Manage:** Workspaces, Settings

### 10. Clean Git Hygiene, Conventional Commits & Auto-Push
- Maintain a clean, active, and professional Git history.
- Use Conventional Commits strictly (`feat:`, `fix:`, `docs:`, `test:`, `style:`, `refactor:`, `chore:`, `ci:`).
- Commit atomically after each verified milestone and automatically push to remote (`origin/main`) to maintain visible momentum.

### 11. Enterprise CI/CD, DevOps & Automation
- Maintain automated GitHub Actions workflows for linting (Ruff), type checking (Mypy), automated tests with coverage, and multi-arch Docker container builds.
- Keep local developer environment reproducible via `deploy/docker-compose.yml`.

---

## 3. Modular Rule Index

For exhaustive technical specifications, consult the dedicated rule modules:
- [Rule 01: Core Laws](file:///c:/Users/Sepehr/Documents/Kolang/.agents/rules/01-core-laws.md)
- [Rule 02: i18n Multilingual Standard](file:///c:/Users/Sepehr/Documents/Kolang/.agents/rules/02-i18n-multilingual.md)
- [Rule 03: Responsive & Accessibility](file:///c:/Users/Sepehr/Documents/Kolang/.agents/rules/03-responsive-accessibility.md)
- [Rule 04: Design System & Tokens](file:///c:/Users/Sepehr/Documents/Kolang/.agents/rules/04-design-system-and-tokens.md)
- [Rule 05: Shadcn Component Standards](file:///c:/Users/Sepehr/Documents/Kolang/.agents/rules/05-shadcn-component-standards.md)
- [Rule 06: API & MCP Dual Architecture](file:///c:/Users/Sepehr/Documents/Kolang/.agents/rules/06-api-and-mcp-dual-architecture.md)
- [Rule 07: Documentation & Testing](file:///c:/Users/Sepehr/Documents/Kolang/.agents/rules/07-documentation-and-testing.md)
- [Rule 08: Git & CI/CD](file:///c:/Users/Sepehr/Documents/Kolang/.agents/rules/08-git-commit-push-and-cicd.md)

---

## 4. Definition of Done (DoD) Checklist

Before concluding any user request, verify:
- [ ] 4-Language localization applied (no raw strings).
- [ ] Responsive across 390px, 768px, 1024px, 1440px.
- [ ] Tested in both Light and Dark themes.
- [ ] WCAG 2.1 AA checked (visible focus, ARIA, keyboard navigation).
- [ ] Semantic tokens used exclusively (no hardcoded visual styles).
- [ ] Documentation / docstrings written.
- [ ] Automated tests written and passing cleanly.
- [ ] Clean conventional commit created and pushed to remote repository.
