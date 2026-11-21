# Contributing to Kolang

First off, **thank you** for considering a contribution to Kolang! 🎉

This document provides guidelines and information to make the contribution process smooth and effective.

---

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Setup](#development-setup)
- [Branch Naming Convention](#branch-naming-convention)
- [Commit Message Format](#commit-message-format)
- [Pull Request Process](#pull-request-process)
- [Code Style](#code-style)
- [Testing Guidelines](#testing-guidelines)
- [Architecture Decisions](#architecture-decisions)
- [Security Vulnerabilities](#security-vulnerabilities)
- [License](#license)

---

## Code of Conduct

This project adheres to the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code. Please report unacceptable behavior to [conduct@kolang.dev](mailto:conduct@kolang.dev).

---

## How Can I Contribute?

### 🐛 Reporting Bugs

- Check [existing issues](https://github.com/sepehr-safaeian/Kolang/issues) first to avoid duplicates
- Use the [Bug Report template](https://github.com/sepehr-safaeian/Kolang/issues/new?template=bug_report.yml)
- Include reproduction steps, expected behavior, and environment details

### 💡 Suggesting Features

- Use the [Feature Request template](https://github.com/sepehr-safaeian/Kolang/issues/new?template=feature_request.yml)
- Explain the use case and why the feature matters

### 🔧 Code Contributions

1. Fork the repository
2. Create a feature branch
3. Write your code and tests
4. Submit a pull request

---

## Development Setup

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Git
- Make (recommended)

### Fork & Clone

```bash
git clone https://github.com/<your-username>/Kolang.git
cd Kolang
git remote add upstream https://github.com/sepehr-safaeian/Kolang.git
```

### Install Dependencies

```bash
make install
```

This installs the project in editable mode with dev dependencies and sets up pre-commit hooks.

### Start Infrastructure

```bash
cp .env.example .env
make up
make migrate
```

### Verify Setup

```bash
make ci
```

---

## Branch Naming Convention

Use the following prefixes:

| Prefix | Purpose |
|--------|---------|
| `feat/` | New feature |
| `fix/` | Bug fix |
| `docs/` | Documentation only |
| `refactor/` | Code refactoring (no behavior change) |
| `test/` | Adding or updating tests |
| `chore/` | Maintenance tasks (CI, deps, tooling) |

**Example:** `feat/add-approval-webhook` or `fix/token-validation-edge-case`

---

## Commit Message Format

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <short description>

[optional body]

[optional footer(s)]
```

### Types

| Type | Description |
|------|-------------|
| `feat` | A new feature |
| `fix` | A bug fix |
| `docs` | Documentation changes |
| `style` | Formatting (no logic change) |
| `refactor` | Code change that neither fixes a bug nor adds a feature |
| `test` | Adding or updating tests |
| `chore` | Build process, CI, or auxiliary tool changes |
| `perf` | Performance improvement |

### Examples

```
feat(policy): add wildcard matching for tool patterns
fix(identity): handle expired OIDC tokens gracefully
docs(architecture): add data flow diagram
test(audit): add unit tests for event serialization
```

---

## Pull Request Process

1. **Update your branch** with the latest `main`:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Ensure all checks pass:**
   ```bash
   make ci
   ```

3. **Fill in the PR template** completely

4. **Review Checklist:**
   - [ ] Code follows the project's style guidelines
   - [ ] Tests added/updated for the changes
   - [ ] Documentation updated if needed
   - [ ] No secrets or credentials committed
   - [ ] Linting and type checks pass
   - [ ] All tests pass with ≥80% coverage

5. PRs require **at least one review** before merging

---

## Code Style

- **Formatter & Linter:** [Ruff](https://docs.astral.sh/ruff/) — `make fmt` to auto-format, `make lint` to check
- **Type Checker:** [mypy](https://mypy-lang.org/) in strict mode
- **Line Length:** 99 characters
- **Docstrings:** Google style
- **Imports:** Sorted by isort (via Ruff)

```bash
make fmt     # Auto-format
make lint    # Lint + type check
```

---

## Testing Guidelines

| Directory | Purpose | Run |
|-----------|---------|-----|
| `tests/unit/` | Pure logic tests, no I/O | `make test-unit` |
| `tests/integration/` | Tests with database/services | `make test-integration` |
| `tests/contract/` | API contract verification | `make test` |
| `tests/security/` | Security-focused tests | `make test` |
| `tests/e2e/` | Full end-to-end flows | `make test-e2e` |

### Requirements

- Minimum **80% code coverage** (enforced in CI)
- Use `pytest` with `pytest-asyncio` for async tests
- Use `httpx.AsyncClient` for API tests
- Mock external services; don't depend on running infrastructure for unit tests

---

## Architecture Decisions

Significant design decisions are documented as Architecture Decision Records (ADRs) in [`docs/architecture/`](docs/architecture/).

When proposing a change that affects the architecture, please include an ADR or update an existing one.

---

## Security Vulnerabilities

**Do not open a public issue for security vulnerabilities.**

Please follow our [Security Policy](SECURITY.md) for responsible disclosure.

---

## License

By contributing to Kolang, you agree that your contributions will be licensed under the [Apache License 2.0](LICENSE).

---

Thank you for helping make Kolang better! 🚀
