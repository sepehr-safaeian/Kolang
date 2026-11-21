# Kolang Agent Guidelines & Operational Rules

> This file mirrors the master operational rules defined in [`GEMINI.md`](file:///c:/Users/Sepehr/Documents/Kolang/GEMINI.md).
> All autonomous agents operating in this workspace must adhere to the 12 Inviolable Laws of Kolang:

1. **4-Language Support (i18n):** English (`en` - Default), German (`de`), Russian (`ru`), Chinese (`zh`). UI must never have hardcoded strings; error handlers and API internals remain English.
2. **Universal Responsiveness & Accessibility:** 390px mobile, 768px tablet, 1024px laptop, 1440px desktop. Use CSS logical properties exclusively. WCAG 2.1 AA compliant.
3. **Dark / Light Mode Cohesion:** All components support Light and Dark themes from day one using semantic `--k-*` CSS variables.
4. **Strict Design Tokens Adherence:** "European Technical Editorial / The Control Surface" visual style. Deep jade accent, warm neutral canvas, crisp 1px borders, compact radii, tabular numbers. No gradients, glows, glassmorphism, or heavy drop shadows.
5. **Shadcn UI via Tokens:** Use Shadcn UI (Radix primitives) customized with Kolang design tokens.
6. **Documentation Everywhere:** Comprehensive docstrings (Google/Sphinx) for Python and TSDoc for TypeScript/React.
7. **Test-Driven Verification:** Unit and integration tests for all code. Zero untested code.
8. **Dual Architecture (API & MCP):** Core capabilities must be accessible both as RESTful API endpoints and as Model Context Protocol (MCP) servers/tools.
9. **Strict Product IA:** Adhere to Operate, Govern, Observe, and Manage domain hierarchy.
10. **Clean Git Hygiene & Continuous Auto-Push:** Conventional commits (`feat:`, `fix:`, `docs:`, etc.) and automated push on verified milestones.
11. **DevOps & CI/CD:** Maintain passing GitHub Actions pipelines, security scanning, and multi-stage containerization.
12. **English-Default Repository Standard:** All docs, `.md` files, comments, docstrings, commit messages, and PRs must strictly be in English. Zero Persian or non-English text in code or docs (except UI i18n dictionaries).

For detailed rule specifications, see the [`.agents/rules/`](file:///c:/Users/Sepehr/Documents/Kolang/.agents/rules/) directory.
