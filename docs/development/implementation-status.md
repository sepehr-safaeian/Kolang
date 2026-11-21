# Repository Audit & Implementation Status Map

**Document ID:** `DOC-ACP-001`  
**Reference Task:** `ACP-001 — Audit the Existing Repository and Map the Current Implementation`  
**Report Date:** 21 November 2026  
**Project Version:** `0.1.0-alpha`  
**Purpose:** Comprehensive technical audit and status mapping of the Kolang Agent Control Plane (ACP) codebase prior to code changes, preventing duplicate rewrites and providing actionable context for subsequent MVP backlog tasks.

---

## 1. Executive Summary

**Kolang** is designed as an enterprise-grade **Agent Control Plane (ACP)** and **Model Context Protocol (MCP) Gateway** architected as a **Modular Monolith**. A comprehensive audit of the repository reveals that the project is currently in its architectural foundation/scaffolding phase:

1. **Domain Baseline & Internal Contracts:** Core domain models are defined as Pydantic v2 schemas across `acp_core` packages (internal protocol, identity, policy, approvals, and audit events). All existing unit tests pass cleanly.
2. **Context Propagation & Telemetry:** Request context middleware (`RequestContextMiddleware`) generates and propagates `request_id` and `correlation_id` across HTTP headers and structured `structlog` contextvars.
3. **Official MCP SDK Dependency Missing:** The official `mcp` Python SDK is neither declared in `pyproject.toml` nor locked in `uv.lock`. Current code relies on abstract internal models and mock demo classes.
4. **Persistence & ORM Gap:** No SQLAlchemy ORM models exist in the repository; `migrations/versions/` is empty, and the readiness check (`/readyz`) returns a hardcoded mock status with a `TODO` comment for database connectivity.
5. **Execution Engines Pending:** Live integration with Open Policy Agent (OPA HTTP policy evaluation), Keycloak OIDC/JWT signature verification, secret encryption/credential injection, and the actual gateway Streamable HTTP forwarding loop are not yet implemented.
6. **Frontend:** The `apps/web` directory is empty; no Next.js project or frontend package configuration has been initialized yet.

---

## 2. Actual Repository Structure

The active filesystem tree of the repository is structured as follows:

```text
Kolang/
├── .agents/                               # Local agent rules and operational directives
│   └── rules/                             # 11 Inviolable Laws rule modules
├── .github/                               # CI/CD and repository workflows
│   ├── ISSUE_TEMPLATE/                    # GitHub issue templates
│   ├── workflows/
│   │   ├── ci.yml                         # Lint, test, security, and Docker build pipeline
│   │   └── release.yml                    # Release automation workflow
│   └── pull_request_template.md           # PR template
├── apps/                                  # Application entrypoints
│   ├── api/                               # FastAPI application service (Backend Gateway)
│   │   └── app/
│   │       ├── middleware/
│   │       │   └── context.py             # Request-ID & Correlation-ID injection middleware
│   │       ├── routers/
│   │       │   └── health.py              # /healthz and /readyz probes
│   │       ├── __init__.py
│   │       └── main.py                    # Main FastAPI application factory and entrypoint
│   └── web/                               # Next.js admin dashboard (currently empty placeholder)
├── deploy/                                # Deployment configurations and local dev stack
│   ├── grafana/provisioning/              # Prometheus datasource provisioning for Grafana
│   ├── keycloak/
│   │   └── kolang-realm.json              # Keycloak development realm config (roles, clients)
│   ├── opa/
│   │   └── kolang/
│   │       └── authz.rego                 # Base OPA authorization policy
│   ├── prometheus/
│   │   └── prometheus.yml                 # Prometheus metrics scraping configuration
│   ├── docker-compose.yml                 # Local dev compose stack (Postgres, Keycloak, OPA, Redis, Prometheus, Grafana, API)
│   └── Dockerfile                         # Multi-stage Python 3.11 production container build
├── docs/                                  # Architecture, security, and development docs
│   ├── architecture/
│   │   └── README.md                      # Modular Monolith architecture & principles
│   ├── development/
│   │   └── implementation-status.md       # This implementation status report
│   ├── security/
│   │   └── README.md                      # Zero-Trust security architecture specification
│   ├── operations/                        # Reserved for operational runbooks
│   ├── product/                           # Reserved for product specifications
│   └── research/                          # Reserved for research notes
├── examples/                              # Reference examples and smoke tests
│   ├── demo-agent-client/
│   │   └── client.py                      # Demo agent client script
│   ├── demo-mcp-server/
│   │   └── server.py                      # In-memory mock MCP tool server
│   └── policies/
│       └── default-policy.rego            # Reference Rego policy rules
├── migrations/                            # Alembic database migration environment
│   ├── versions/                          # Empty (no migration revisions generated yet)
│   ├── env.py                             # Async database migration configuration
│   └── script.py.mako                     # Migration script template
├── packages/                              # Modular monolith core packages
│   └── acp_core/
│       ├── approvals/
│       │   ├── __init__.py
│       │   └── models.py                  # Approval state machine & Pydantic domain models
│       ├── audit/
│       │   ├── __init__.py
│       │   └── models.py                  # AuditEvent schema & AuditSink protocol
│       ├── common/
│       │   ├── __init__.py
│       │   ├── context.py                 # Request context contextvars
│       │   ├── errors.py                  # KolangError hierarchy & standardized ErrorResponse
│       │   ├── settings.py                # Pydantic Settings configuration loader
│       │   └── types.py                   # Domain NewTypes and enums (PrincipalKind, etc.)
│       ├── credentials/
│       │   └── __init__.py                # Credential management interface docstring
│       ├── gateway/
│       │   ├── __init__.py
│       │   └── interfaces.py              # Protocol interfaces (DownstreamHandler, UpstreamConnector, etc.)
│       ├── identity/
│       │   ├── __init__.py
│       │   └── models.py                  # Principal, TokenClaims, and AuthContext models
│       ├── policy/
│       │   ├── __init__.py
│       │   └── models.py                  # Policy models, evaluation input, and decision types
│       ├── protocol/
│       │   ├── __init__.py
│       │   └── models.py                  # Internal tool call messages & server descriptors
│       ├── registry/
│       │   └── __init__.py                # Server/tool registry interface docstring
│       ├── telemetry/
│       │   ├── __init__.py
│       │   └── setup.py                   # structlog and OpenTelemetry Tracer configuration
│       └── __init__.py
├── scripts/
│   └── generate_key.py                    # 256-bit Fernet encryption key generation script
├── tests/                                 # Automated test suite
│   ├── integration/
│   │   ├── __init__.py
│   │   └── test_health.py                 # Health and readiness probe integration tests
│   ├── unit/
│   │   ├── __init__.py
│   │   ├── test_common.py                 # Context, types, and error hierarchy unit tests
│   │   ├── test_domain_models.py          # Protocol, identity, approval, and audit unit tests
│   │   └── test_policy_models.py          # Policy decision and rule model unit tests
│   ├── __init__.py
│   └── conftest.py                        # Async test fixtures and test client setup
├── .dockerignore
├── .editorconfig
├── .env.example                           # Example environment variables
├── .gitignore
├── .pre-commit-config.yaml                # Git hooks (Ruff, Mypy, Bandit)
├── AGENTS.md                              # Repository operational rules for AI agents
├── AGENT_HANDOFF_PROMPT.md                # Agent handoff guidelines
├── alembic.ini                            # Alembic configuration file
├── CODE_OF_CONDUCT.md
├── CONTRIBUTING.md
├── GEMINI.md                              # Master 11 Inviolable Laws of Kolang
├── Kolang-Logo.svg
├── kolang.css                             # Semantic CSS design tokens
├── LICENSE                                # Apache 2.0 License
├── Makefile                               # Automation targets for build, lint, test, run
├── MASTER_DESIGN_SYSTEM_FA.md             # Master design system specification
├── pyproject.toml                         # Python package metadata, dependencies, tool configs
├── README.md                              # Project overview and quick start guide
├── SECURITY.md                            # Security policy and vulnerability disclosure
├── tokens.json                            # JSON design tokens
├── uv.lock                                # Deterministic Python package lockfile
└── agent-control-plane-mvp-backlog.md      # Full 69-task MVP engineering backlog
```

---

## 3. Tech Stack & Dependencies

### 3.1 Core Language & Frameworks
* **Python:** Requires `>=3.11` (Current local virtual environment: `3.12.13`).
* **Web Framework:** `FastAPI >=0.115` with `Uvicorn[standard] >=0.30`.
* **Data Validation & Settings:** `Pydantic >=2.9` and `Pydantic-settings >=2.5`.
* **Database & ORM:** `SQLAlchemy[asyncio] >=2.0`, `asyncpg >=0.30`, and `Alembic >=1.14`.
* **HTTP Client:** `HTTPX >=0.27`.
* **Observability:** `OpenTelemetry API/SDK/OTLP >=1.28`, `structlog >=24.4`.
* **Cryptography & Security:** `python-jose[cryptography] >=3.3`, `cryptography >=43.0`.
* **Frontend:** None initialized (`apps/web` is empty; no Node.js runtime or `package.json` present).

### 3.2 Tooling & Quality Assurance
* **Package Management:** `uv` with `uv.lock` lockfile and `hatchling` build backend.
* **Testing:** `pytest >=8.3`, `pytest-asyncio >=0.24`, `pytest-cov >=5.0`, `respx >=0.21`.
* **Linting & Formatting:** `ruff >=0.8` (rules: `E, F, W, I, N, UP, S, B, A, C4, DTZ, T20, PT, SIM, TID, RUF`).
* **Type Checking:** `mypy >=1.13` with `strict = true` and `pydantic.mypy` plugin.
* **Security Scanning:** `bandit[toml] >=1.8`.
* **Pre-commit:** `pre-commit >=4.0`.

---

## 4. Entry Points, Execution Commands, and Testing

### 4.1 Entry Points
* **Backend API Entrypoint:** `apps.api.app.main:app` (instantiated via `create_app()`, configuring telemetry, CORS, `RequestContextMiddleware`, and routes in `health.router` mounted at `/healthz`, `/readyz`, and `/`).
* **Frontend Entrypoint:** None currently (`apps/web` empty placeholder).

### 4.2 Verified Development Execution Commands

| Target | Command | Makefile Equivalent |
|---|---|---|
| **Run Backend Dev Server** | `.\.venv\Scripts\uvicorn.exe apps.api.app.main:app --reload --host 0.0.0.0 --port 8000` | `make dev` |
| **Start Docker Infrastructure** | `docker compose -f deploy/docker-compose.yml up -d --build` | `make up` |
| **Stop Docker Infrastructure** | `docker compose -f deploy/docker-compose.yml down` | `make down` |
| **Apply DB Migrations** | `.\.venv\Scripts\alembic.exe upgrade head` | `make migrate` |
| **Generate New Migration** | `.\.venv\Scripts\alembic.exe revision --autogenerate -m "message"` | `make migrate-new` |

### 4.3 Verified Testing, Quality, and Security Commands

All commands below execute cleanly in the local environment:

```powershell
# Run unit and integration tests with coverage
.\.venv\Scripts\pytest.exe --cov=packages/acp_core --cov-report=term-missing

# Run Ruff linter checks
.\.venv\Scripts\ruff.exe check .

# Check code formatting with Ruff
.\.venv\Scripts\ruff.exe format --check .

# Run strict type checking with Mypy
.\.venv\Scripts\mypy.exe apps packages

# Run static security scan with Bandit
.\.venv\Scripts\bandit.exe -r packages/ -c pyproject.toml
```

**Latest Local Verification Metrics:**
* **Test Suite:** **16 passed in 0.11s**.
* **Code Coverage (`packages/acp_core`):** **91.11%** (exceeds the 80.0% threshold).
* **Ruff:** 0 errors, 0 warnings.
* **Mypy:** 0 issues found across 31 source files.
* **Bandit:** 0 security issues identified.

---

## 5. Domain Implementation Status Breakdown

Every domain is evaluated according to the standard five status classifications:
* `Implemented & Tested`: Fully implemented with verified passing automated tests.
* `Implemented but Untested`: Implemented in code but lacking sufficient test coverage.
* `Partially Implemented`: Abstract contracts or partial features present; incomplete execution logic.
* `Missing`: Not implemented in the codebase.
* `Blocked`: Blocked by unmet prerequisite dependencies.

| Domain / Capability | Status | Implementation Details & Current State |
|---|---|---|
| **Internal Protocol Models** | `Implemented & Tested` | `ToolCallRequest`, `ToolCallResponse`, `ToolDescriptor`, and `ServerDescriptor` in `acp_core.protocol.models` with comprehensive tests in `test_domain_models.py`. |
| **Request Context & Middleware** | `Implemented & Tested` | `RequestContextMiddleware` generates/extracts `X-Request-ID` and `X-Correlation-ID`, binds them to `structlog.contextvars`, and writes them to response headers. Tested in `test_health.py` and `test_common.py`. |
| **Error Hierarchy** | `Implemented & Tested` | `KolangError` hierarchy with machine-readable codes and HTTP status mappings in `acp_core.common.errors`. Tested in `test_common.py`. |
| **Identity Domain Models** | `Implemented & Tested` | Pydantic models for `Principal`, `TokenClaims`, and `AuthContext` in `acp_core.identity.models`. Tested in `test_domain_models.py`. |
| **Approval State Machine** | `Implemented & Tested` | `ApprovalStatus`, `ApprovalRequest`, and valid transitions via `can_transition()` in `acp_core.approvals.models`. Tested in `test_domain_models.py`. |
| **Policy Domain Models** | `Implemented & Tested` | `PolicyEffect`, `PolicyCondition`, `PolicyDecision`, and `PolicyRule` in `acp_core.policy.models`. Tested in `test_policy_models.py`. |
| **Audit Event Models** | `Implemented & Tested` | `AuditEventType`, `AuditEvent`, and `AuditSink` protocol in `acp_core.audit.models`. Tested in `test_domain_models.py`. |
| **Configuration Management** | `Implemented & Tested` | Typed `Settings` class loading from environment variables and `.env` in `acp_core.common.settings`. |
| **Telemetry & Structured Logging** | `Partially Implemented` | `setup_structlog()` and `setup_telemetry()` with OTLP exporter in `acp_core.telemetry.setup`. Base tracing is initialized; live collector export and metric aggregations are unverified. |
| **Gateway Protocol Interfaces** | `Partially Implemented` | `Protocol` interfaces (`DownstreamHandler`, `UpstreamConnector`, `PolicyEnforcer`, `ApprovalManager`) defined in `acp_core.gateway.interfaces`, but no concrete router or forwarder classes exist. |
| **Health Check Endpoints** | `Partially Implemented` | `/healthz` is functional. `/readyz` returns a mock `"ok"` response with a `# TODO` comment for real database ping. |
| **OPA Rego Policies** | `Partially Implemented` | Policy rules exist in `deploy/opa/kolang/authz.rego`, but no Python HTTP client for OPA evaluation is implemented. |
| **Official MCP SDK & Wire Protocol** | `Missing` | The official `mcp` package is not declared in `pyproject.toml` or `uv.lock`. No protocol wire adapters exist. |
| **Database ORM Models & Migrations** | `Missing` | No SQLAlchemy 2.0 ORM models exist; `migrations/versions/` is empty; `target_metadata` in `migrations/env.py` is `None`. |
| **OIDC / JWT Validation Middleware** | `Missing` | Keycloak realm exists, but no FastAPI dependency or middleware validates tokens or resolves principals from JWKS. |
| **Gateway Policy Enforcement Point** | `Missing` | No interception pipeline exists in the request path to evaluate policies against OPA before forwarding calls. |
| **Secure Credential Storage & Injection** | `Missing` | Aside from the standalone `scripts/generate_key.py`, no encryption vault or upstream credential injection exists. |
| **Tool Registry & Discovery** | `Missing` | Tool scanning, deterministic SHA-256 fingerprinting, tool snapshotting, and catalog APIs are not implemented. |
| **Streamable HTTP Gateway Transport** | `Missing` | Downstream Streamable HTTP MCP endpoint and upstream forwarding transport are not implemented. |
| **Admin Dashboard UI** | `Missing` | `apps/web` directory is empty. |

---

## 6. Backlog Scope Comparison (ACP-001 through ACP-069)

Mapping against the 69 tasks specified in `agent-control-plane-mvp-backlog.md`:

### Group A: Architecture Baseline & Contracts (ACP-001 to ACP-005)
* **ACP-001 (Audit Repository):** `Implemented & Tested` — Fulfilled by this audit document and verification report.
* **ACP-002 (Pin MCP SDK & Protocol Version):** `Missing` — SDK must be selected, pinned, and documented in an ADR.
* **ACP-003 (Internal Gateway & Decision Contracts):** `Partially Implemented` — Domain schemas exist in `protocol/models.py` and `gateway/interfaces.py`, needing contract hardening.
* **ACP-004 (Configuration & Environment):** `Implemented & Tested` — `Settings` class and `.env.example` verified.
* **ACP-005 (Structured Logging & Request Correlation):** `Implemented & Tested` — `structlog` and `RequestContextMiddleware` verified with automated tests.

### Group B: Data Models & Persistence (ACP-006 to ACP-014)
* **ACP-006 to ACP-014:** `Missing` — Database session lifecycle, Alembic initial migration, and SQLAlchemy ORM models (`Workspace`, `McpServer`, `Tool`, `ToolSnapshot`, `Principal`, `Agent`, `Policy`, `PolicyVersion`, `ApprovalRequest`, `AuditEvent`) are not implemented.

### Group C: Demo MCP & Gateway Data Plane (ACP-015 to ACP-024)
* **ACP-015 to ACP-016:** `Partially Implemented` — Standalone demo files in `examples/` provide in-memory mocks, but do not speak standard wire MCP.
* **ACP-017 to ACP-024:** `Missing` — Upstream MCP client adapter, downstream Streamable HTTP endpoint, error mapping, timeouts, SSRF protection, health checks, and server registration APIs are missing.

### Group D: Tool Registry & Discovery (ACP-025 to ACP-030)
* **ACP-025 to ACP-030:** `Missing` — Tool discovery, deterministic fingerprinting, safe classification, catalog read APIs, policy filtering, and drift refresh are missing.

### Group E: Identity, Authentication & Workspace Scoping (ACP-031 to ACP-037)
* **ACP-031:** `Partially Implemented` — Realm configuration in `deploy/keycloak/kolang-realm.json` exists.
* **ACP-032 to ACP-037:** `Missing` — OIDC JWT validation, principal resolution, endpoint auth, workspace tenant isolation, agent management APIs, and security suites are missing.

### Group F: Policy Engine & OPA (ACP-038 to ACP-044)
* **ACP-038 to ACP-044:** `Missing` — OPA client integration, default-deny Rego evaluation, policy publish API, pre-execution enforcement, decision receipts, simulation API, and rate limiting are missing.

### Group G: Approval Workflows (ACP-045 to ACP-049)
* **ACP-045 to ACP-049:** `Partially Implemented` — State machine transition validation (`can_transition()`) is implemented in memory, but approval database persistence, APIs, payload binding, and expiration are missing.

### Group H: Upstream Credentials (ACP-050 to ACP-052)
* **ACP-050 to ACP-052:** `Missing` — Encryption at rest, credential profile APIs, and runtime injection are missing.

### Group I: Audit & Operations (ACP-053 to ACP-057)
* **ACP-053 to ACP-057:** `Partially Implemented` — Audit models exist, basic telemetry is present; persistent audit sink, search API, Prometheus metrics, and live dependency health reporting are missing.

### Group J: End-to-End Tests & Packaging (ACP-058 to ACP-065)
* **ACP-063 (Local Docker Compose):** `Implemented but Untested` — `deploy/docker-compose.yml` is present but full stack E2E lifecycle has not been tested.
* **ACP-064 (CI Pipeline):** `Implemented & Tested` — `.github/workflows/ci.yml` is configured and passes.
* **ACP-058 to ACP-062, ACP-065:** `Missing` — End-to-end tool call tests, approval tests, SDK contract tests, and security regression suites are missing.

### Group K: Optional Admin Dashboard (ACP-066 to ACP-069)
* **ACP-066 to ACP-069:** `Missing` — Frontend dashboard shell and screens are missing.

---

## 7. Actionable Context and Guidance for Next Tasks

1. **Protocol Independence Principle:** Internal domain models in `packages/acp_core/protocol/models.py` must remain decoupled from MCP JSON-RPC transport representations. Adapters must isolate protocol transformations at the edges.
2. **Immediate Next Step (Task ACP-002):**
   * Inspect the official Python MCP SDK (`mcp`).
   * Pin the SDK dependency version in `pyproject.toml` and update `uv.lock`.
   * Create an ADR documenting the protocol version, transport choices, and SDK compatibility guarantees.
3. **Data Layer Phase (Task ACP-006 onwards):**
   * Introduce SQLAlchemy 2.0 `DeclarativeBase` ORM models mirroring existing domain schemas.
   * Bind `target_metadata` in `migrations/env.py` and generate the initial Alembic migration.

---

## 8. Acceptance Criteria Verification

- [x] **No Source Code Changes:** No application or test source files were modified; only this status documentation was added.
- [x] **Actual Repository Structure Documented:** Comprehensive directory hierarchy and component inventory detailed in Section 2.
- [x] **Real Execution Commands Documented:** Backend, Docker Compose, Alembic, Ruff, Mypy, Bandit, and Pytest commands verified and documented in Section 4.
- [x] **Differences vs. Backlog Scope Listed:** Detailed gap analysis across all 69 backlog tasks documented in Section 6.
- [x] **Context Established for Subsequent Tasks:** Implementation foundation and technical guidance for `ACP-002` onwards provided in Section 7.
