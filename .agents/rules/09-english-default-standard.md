# Rule 09: English-Default Standard for All Repository Artifacts

> **Mandate:** All code, comments, docstrings, markdown documents, architecture specifications, commits, pull requests, and agent communication must strictly be written in English. Zero Persian or other non-English text is permitted in repository files, with the sole exception of UI translation dictionaries.

---

## 1. Scope of the Standard

The English-default rule applies comprehensively across the entire repository lifecycle:

1. **Source Code & Implementation:**
   - Variable, function, class, and module names.
   - Inline comments, block comments, and `# TODO` / `# FIXME` annotations.
   - Python docstrings (Google/Sphinx style) and TypeScript TSDoc/JSDoc blocks.
   - Internal error codes, exception messages, and machine-readable error reasons.
2. **Documentation & Architecture Artifacts:**
   - All markdown files (`.md`) across `docs/`, `apps/`, `packages/`, and the repository root.
   - Architecture Decision Records (ADRs) and design proposals.
   - Status tracking documents (e.g., `docs/development/implementation-status.md`).
   - Operational runbooks, threat models, and security documentation.
3. **Git Hygiene & Issue Tracking:**
   - Git commit messages (Conventional Commits: `feat:`, `fix:`, `docs:`, etc.).
   - Pull request titles, summaries, test plans, and checklists.
   - GitHub Issue descriptions, labels, and discussion comments.
4. **Agent Output & Interaction:**
   - All summaries, reports, plans, analysis, and execution status updates provided by autonomous agents must be written strictly in English.

---

## 2. Sole Exception: UI Localization (i18n)

The only permitted non-English strings in the entire codebase are **localized user-facing UI copy** stored inside dedicated translation dictionary files:

- Supported UI locales: `en` (Default), `de` (German), `ru` (Russian), `zh` (Simplified Chinese).
- These strings reside strictly within localization bundles (e.g., `locales/*.json` or `i18n/`).
- Code components, logs, backend errors, and internal data structures must NEVER contain hardcoded localized strings.

---

## 3. Verification & Compliance Checklist

Before committing any artifact or concluding any task:
- [ ] Are all newly created or updated `.md` documentation files written strictly in English?
- [ ] Are all docstrings, comments, and commit messages in English?
- [ ] Is there zero Persian/Farsi or unauthorized non-English text anywhere in the changes?
- [ ] If user-facing UI text was added, is it strictly referenced via i18n keys?
