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
3. **Official MCP SDK Pinned:** The official Python SDK has been pinned as `mcp==2.3.0` in `pyproject.toml` and locked in `uv.lock`. Concrete integration, wire transport adapters, and protocol compatibility validation are pending (ACP-002).
4. **Persistence & ORM Gap:** No SQLAlchemy ORM models exist in the repository; `migrations/versions/` is empty, and the readiness check (`/readyz`) returns a hardcoded mock status with a `TODO` comment for database connectivity.
5. **Execution Engines Pending:** Live integration with Open Policy Agent (OPA HTTP policy evaluation), Keycloak OIDC/JWT signature verification, secret encryption/credential injection, and the actual gateway Streamable HTTP forwarding loop are not yet implemented.
6. **Frontend:** The `apps/web` directory is empty; no Next.js project or frontend package configuration has been initialized yet.

---

## 2. Actual Repository Structure

The active filesystem tree of the repository is structured as follows:

```text
Kolang/
├── .agents/                               # Local agent rules and operational directives
│   └── rules/                             # 12 Inviolable Laws rule modules
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
├── GEMINI.md                              # Master 12 Inviolable Laws of Kolang
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
| **Gateway & Decision Contracts** | `Implemented & Tested` | Canonical internal domain contracts (`Principal`, `RequestContext`, `ToolResource`, `ToolInvocation`, `PolicyInput`, `PolicyDecision`, `GatewayResult`) in `acp_core.contracts` with mandatory tenant scoping, secret leakage guards, and full test suite. |
| **Internal Protocol Models** | `Implemented & Tested` | `ToolCallRequest`, `ToolCallResponse`, `ToolDescriptor`, and `ServerDescriptor` in `acp_core.protocol.models` with comprehensive tests in `test_domain_models.py`. |
| **Request Context & Middleware** | `Implemented & Tested` | `RequestContextMiddleware` generates/extracts `X-Request-ID` and `X-Correlation-ID`, binds them to `structlog.contextvars`, and writes them to response headers. Tested in `test_health.py` and `test_common.py`. |
| **Error Hierarchy** | `Implemented & Tested` | `KolangError` hierarchy with machine-readable codes and HTTP status mappings in `acp_core.common.errors`. Tested in `test_common.py`. |
| **Identity Domain Models** | `Implemented & Tested` | Pydantic models for `Principal`, `TokenClaims`, and `AuthContext` in `acp_core.identity.models`. Tested in `test_domain_models.py`. |
| **Approval State Machine** | `Implemented & Tested` | `ApprovalStatus`, `ApprovalRequest`, and valid transitions via `can_transition()` in `acp_core.approvals.models`. Tested in `test_domain_models.py`. |
| **Policy Domain Models** | `Implemented & Tested` | `PolicyEffect`, `PolicyCondition`, `PolicyDecision`, and `PolicyRule` in `acp_core.policy.models`. Tested in `test_policy_models.py`. |
| **Audit Event Models** | `Implemented & Tested` | `AuditEventType`, `AuditEvent`, and `AuditSink` protocol in `acp_core.audit.models`. Tested in `test_domain_models.py`. |
| **Configuration Management (ACP-004)** | `Implemented & Tested` | Centralized, typed `Settings` model in `acp_core.common.settings` with canonical `ACP_*` variables, backward-compatible aliases, strict production guardrails (OIDC, encryption keys, non-default secrets), secret file resolution (`ACP_ENCRYPTION_KEY_PATH`), credential masking in `safe_dump()`/`__repr__`, updated `.env.example`, and full unit test suite in `test_settings.py`. |
| **Telemetry & Structured Logging (ACP-005)** | `Implemented & Tested` | Centralized redaction utility (`acp_core.common.redaction`), JSON structured logging with request correlation, automatic metadata injection (`service`, `environment`, `component`, `event_name`, `request_id`, `correlation_id`, `workspace_id`, `error_code`), sanitized `X-Request-ID` and `X-Correlation-ID` handling in `RequestContextMiddleware`, fail-safe exception masking in FastAPI exception handlers, and comprehensive unit and integration test coverage (`test_redaction.py`, `test_structured_logging.py`, `test_logging_middleware.py`). |
| **Gateway Protocol Interfaces** | `Partially Implemented` | `Protocol` interfaces (`DownstreamHandler`, `UpstreamConnector`, `PolicyEnforcer`, `ApprovalManager`) defined in `acp_core.gateway.interfaces`, but no concrete router or forwarder classes exist. |
| **Health Check Endpoints** | `Implemented & Tested` | `/healthz` provides liveness monitoring. `/readyz` performs live database ping probing with status 200 (`ok`) or 503 (`degraded`/`unavailable`). |
| **Database Connection & Session Lifecycle (ACP-006)** | `Implemented & Tested` | Centralized `DatabaseManager`, SQLAlchemy 2.0 `DeclarativeBase` with deterministic constraint naming and mixins, robust connection pooling, FastAPI `get_db_session` per-request dependency with guaranteed leak-free cleanup, `transactional_session` service context manager, live readiness probes, and safe public error conversion without schema or credential leaks (`test_database.py`, `test_database_postgres.py`). |
| **OPA Rego Policies** | `Partially Implemented` | Policy rules exist in `deploy/opa/kolang/authz.rego`, but no Python HTTP client for OPA evaluation is implemented. |
| **Official MCP SDK & Wire Protocol** | `Partially Implemented` | Pinned `mcp==2.3.0` in `pyproject.toml` and `uv.lock`. Protocol wire adapters and runtime client/server integration remain pending. |
| **Database ORM Models & Migrations** | `Partially Implemented` | SQLAlchemy 2.0 `Base` and `target_metadata` bound in `migrations/env.py`. Initial versioned migration (`0001_initial_baseline`) created and tested with clean upgrade/downgrade cycles and zero worker auto-migrate guarantee (ACP-007). Concrete domain models (ACP-008 to ACP-014) are pending. |
| **OIDC / JWT Validation Middleware** | `Missing` | Keycloak realm exists, but no FastAPI dependency or middleware validates tokens or resolves principals from JWKS. |
| **Gateway Policy Enforcement Point** | `Missing` | No interception pipeline exists in the request path to evaluate policies against OPA before forwarding calls. |
| **Secure Credential Storage & Injection** | `Missing` | Aside from the standalone `scripts/generate_key.py`, no encryption vault or upstream credential injection exists. |
| **Tool Catalog & Snapshot Models (ACP-010)** | `Implemented & Tested` | Relational models (`Tool`, `ToolSnapshot`), migration `0004`, native PostgreSQL JSONB storage, untrusted schema bounding, deterministic SHA-256 fingerprinting, catalog hashing, multi-dimensional risk labels, and workspace-isolated `ToolService`. |
| **Streamable HTTP Gateway Transport** | `Missing` | Downstream Streamable HTTP MCP endpoint and upstream forwarding transport are not implemented. |
| **Admin Dashboard UI** | `Missing` | `apps/web` directory is empty. |

---

## 6. Backlog Scope Comparison (ACP-001 through ACP-069)

Mapping against the 69 tasks specified in `agent-control-plane-mvp-backlog.md`:

### Group A: Architecture Baseline & Contracts (ACP-001 to ACP-005)
* **ACP-001 (Audit Repository):** `Implemented & Tested` — Fulfilled by this audit document and verification report.
* **ACP-002 (Pin MCP SDK & Protocol Version):** `Implemented & Tested` — `mcp==2.3.0` pinned in dependencies; formal ADR-001 and compatibility verification tests verified.
* **ACP-003 (Internal Gateway & Decision Contracts):** `Implemented & Tested` — Canonical internal domain contracts defined in `acp_core.contracts` and re-exported in `acp_core.gateway`. Comprehensive unit tests verify strict ID and timestamp validation, mandatory workspace scoping, 3 canonical decision outcomes (allow, deny, require_approval), and backend enforcement preventing raw secrets.
* **ACP-004 (Configuration & Environment):** `Implemented & Tested` — `Settings` class and `.env.example` verified.
* **ACP-005 (Structured Logging & Request Correlation):** `Implemented & Tested` — Centralized redaction utility in `acp_core.common.redaction` with re-export in `acp_core.telemetry.redaction`; standardized structlog JSON pipeline with metadata enrichment (`service`, `environment`, `component`, `event_name`, `request_id`, `correlation_id`, `workspace_id`, `error_code`); robust sanitization and correlation in `RequestContextMiddleware`; safe exception handlers in FastAPI preventing credential leaks; and comprehensive automated test suites verifying token absence in logs, upstream secret scrubbing, and fail-safe resilience.

### Group B: Data Models & Persistence (ACP-006 to ACP-014)
* **ACP-006 (PostgreSQL Connection & Session Lifecycle):** `Implemented & Tested` — Centralized `DatabaseManager`, SQLAlchemy 2.0 `Base` (`DeclarativeBase`), connection pool configuration, FastAPI `get_db_session` dependency, service boundary `transactional_session`, live readiness probe in `/readyz`, safe exception handling (`DATABASE_ERROR`), and comprehensive test coverage including Docker PostgreSQL integration tests.
* **ACP-007 (Initial Alembic Migration and Migration Workflow):** `Implemented & Tested` — Alembic `target_metadata` bound to `Base.metadata` with asyncpg NullPool configuration; initial baseline migration `0001_initial_baseline` creating required PostgreSQL extensions (`uuid-ossp`, `pgcrypto`) idempotently; reversible non-destructive downgrade/re-upgrade; standalone runner `scripts/run_migrations.py` with secret redaction and DB readiness polling; decoupling from web workers (zero auto-migration on worker boot); CI migration upgrade step added; comprehensive development guide `docs/development/database-migrations.md`; verified by unit and live Docker PostgreSQL integration tests (`test_migrations.py`).
* **ACP-008 (Workspace Domain Model & Tenant Scoping):** `Implemented & Tested` — Organizational Workspace domain model (`Workspace` ORM & Pydantic DTOs); Alembic revision migration `0002_create_workspaces_table` with unique slug index; `WorkspaceScopedMixin` ensuring tenant consistency across child entities; `workspace_id` added across domain models (`ApprovalRequest`, `AuditEvent`, `PolicyRule`, `ToolCallRequest`, `ServerDescriptor`, `ToolDescriptor`); `TenantContext` resolution from verified Principal in `RequestContext`; body payload tampering detection (`resolve_trusted_workspace_id`) blocking spoofing; `WorkspaceService` lifecycle operations; deterministic demo workspace seeding (`seed_demo_workspace`); Service Layer tenant isolation (`ScopedServerService`, `ScopedPolicyService`) preventing cross-workspace reading, mutation, and IDOR attacks; REST endpoints `/api/v1/workspaces`; verified by 134 unit and live PostgreSQL integration tests.
* **ACP-009 (Create MCP Server Domain Model):** `Implemented & Tested` — Upstream MCP Server domain model (`McpServer` ORM & Pydantic DTOs); Alembic revision migration `0003_create_mcp_servers_table` with foreign key to `workspaces.id` (cascade delete), composite unique constraint on `(workspace_id, slug)`, status indexing, and metadata support; strict URL host parsing, validation, and SSRF protection (`validate_mcp_endpoint_url`) enforcing mandatory HTTPS for remote targets, blocking loopback, link-local, RFC 1918 private subnets, CGNAT, and cloud metadata (169.254.169.254, metadata.google.internal); explicit local demo allowlist controls via `Settings.allow_local_upstreams` and `allowed_upstream_hosts`; `McpServerService` providing workspace-scoped CRUD operations with strict tenant boundary isolation and IDOR protection (returns 404 for cross-workspace lookups without leaking resource existence); FastAPI endpoints at `/api/v1/workspaces/{workspace_id}/servers` and `/api/v1/servers`; verified by 80 unit and live PostgreSQL integration tests (total test suite: 214 tests).
* **ACP-010 (Create Tool and Tool Snapshot Data Models):** `Implemented & Tested` — Tool Catalog and Tool Discovery Snapshot domain models (`Tool`, `ToolSnapshot` SQLAlchemy ORM models, Pydantic schemas, and DTOs); Alembic revision migration `0004_create_tools_and_snapshots_tables` with foreign keys to `workspaces.id` and `mcp_servers.id` (cascade delete), composite unique constraint on `(server_id, name)`, native PostgreSQL `JSONB` storage for input schema, annotations, risk labels, tools data, and metadata; untrusted input handling treating description and input schema as untrusted; strict security bounds enforcing max description length (4096 chars), max JSON schema size (64 KB), and recursion depth limits (10 levels); independent multi-dimensional risk labels (`risk_labels`) replacing ambiguous single risk scores; deterministic SHA-256 fingerprinting (`compute_tool_fingerprint`) and catalog cumulative hashing (`compute_catalog_hash`); `ToolService` domain service enforcing workspace-scoped multi-tenant isolation, server ownership validation, duplicate prevention, and zero cross-workspace data leakage (anti-IDOR); verified by 27 unit and live PostgreSQL integration tests (total test suite: 241 tests).
* **ACP-011 (Create Principal, Agent and MCP Client Identity Models):** `Implemented & Tested` — Domain and persistence models for Agent workloads (`Agent` ORM & Pydantic DTOs), MCP Client Registrations (`McpClientRegistration` ORM & Pydantic DTOs), Workspace Memberships (`WorkspaceMembership` ORM & Pydantic DTOs), and runtime `PrincipalContext`; Alembic revision migration `0005_create_identity_and_agent_tables` establishing relational tables with foreign keys to `workspaces.id` (cascade delete), composite unique constraints on `(workspace_id, slug)`, `(workspace_id, client_id)`, and `(workspace_id, user_id)`, and native PostgreSQL `JSONB` metadata storage; strict discrimination between Human User (`USER`) and Agent Workload (`AGENT`) identity types; runtime execution checks ensuring inactive/revoked agents cannot execute new requests (`check_can_execute`); automatic rejection of unregistered/unknown clients; defense against header-spoofed identity (`X-Agent-ID`, `X-User-ID`) by strictly deriving identity from cryptographic OIDC token claims; demo seed mapping Keycloak service accounts (`kolang-api`) to Agent identities and user clients (`kolang-web`) to human users; verified by 25 unit and live PostgreSQL integration tests (total test suite: 266 tests).
* **ACP-012 to ACP-014:** `Pending` — SQLAlchemy ORM models (`Policy`, `PolicyVersion`, `ApprovalRequest`, `AuditEvent`) and their respective revision migrations.

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
