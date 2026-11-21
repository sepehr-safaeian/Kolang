# Rule 08: Git Hygiene, Commit & Push Automation, and CI/CD

> **Mandate:** Maintain a spotless, active, and professional Git history using Conventional Commits. Commit and push automatically on every verified milestone. Keep CI/CD pipelines green at all times.

---

## 1. Git Commit Protocol (Conventional Commits)

Every commit message MUST follow the Conventional Commits specification:

```
<type>(<scope>): <short imperative description>

[optional body explaining why and what changed]

[optional footer(s)]
```

### Commit Types
| Type | Purpose | Example |
|---|---|---|
| `feat` | New feature or capability | `feat(gateway): add streaming SSE support for MCP tool execution` |
| `fix` | Bug fix or error resolution | `fix(policy): prevent unhandled null pointer during role lookup` |
| `docs` | Documentation additions or edits | `docs(readme): document multi-language and design system setup` |
| `style` | Formatting, CSS variables, tokens | `style(tokens): align semantic surface colors with jade-700` |
| `refactor`| Code restructuring without feature change | `refactor(auth): isolate JWT validation into reusable dependency` |
| `test` | Adding or updating tests | `test(approvals): add unit tests for pending approval transitions` |
| `chore` | Dependency bumps, configs, build scripts | `chore(deps): update ruff to 0.8.2` |
| `ci` | CI/CD workflow updates | `ci(github): add frontend lint and type-check steps` |

---

## 2. Milestone Automation & Push Policy

1. **Atomic & Frequent Commits:**
   Do not accumulate massive uncommitted diffs. Once a discrete unit of work (e.g., a function + test + docstring, or a component + token styling) is complete and verified, commit it immediately.
2. **Auto-Push on Verified Milestones:**
   After tests pass and the milestone is cleanly committed, push to the remote repository (`git push origin <branch>`). This ensures the GitHub activity graph reflects steady, professional momentum and all progress is safely backed up.
3. **Clean Working Tree:**
   Keep the working tree clean. Never commit temporary files, credentials, local environment files (`.env`), or untracked build artifacts.

---

## 3. Enterprise CI/CD & DevOps Standards

1. **GitHub Actions Workflows (`.github/workflows/`):**
   - **`ci.yml`:** Runs on every push and PR to `main` / `develop`:
     - Python: Ruff lint, Ruff format check, Mypy strict type check, Pytest with coverage XML upload.
     - Node/Frontend: ESLint check, Prettier check, TypeScript compilation (`tsc --noEmit`), Vitest suite.
   - **`release.yml`:** Triggered on tag `v*`, builds multi-arch Docker image, publishes to GitHub Container Registry (`ghcr.io`), generates changelog and release notes.
2. **Containerization Standards (`deploy/Dockerfile`):**
   - Multi-stage Docker builds to keep final production image small and secure.
   - Non-root user execution (`USER nonroot`).
   - Healthcheck directives included.
3. **Infrastructure as Code:**
   - Maintain `deploy/docker-compose.yml` for instant zero-dependency local reproduction (FastAPI + PostgreSQL + Redis + OPA + Keycloak + Prometheus + Grafana).
