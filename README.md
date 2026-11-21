<p align="center">
  <img src="Kolang-Logo.svg" alt="Kolang" width="300">
</p>

<h1 align="center">Kolang</h1>

<p align="center">
  <strong>Open-Source Agent Control Plane &amp; MCP Gateway</strong>
  <br />
  <em>Secure, governed access to AI tool infrastructure — self-hosted, cloud-agnostic.</em>
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-Apache_2.0-blue.svg" alt="License"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.11+-3776AB.svg?logo=python&logoColor=white" alt="Python"></a>
  <a href="https://github.com/sepehr-safaeian/Kolang/actions/workflows/ci.yml"><img src="https://github.com/sepehr-safaeian/Kolang/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://github.com/sepehr-safaeian/Kolang/pulls"><img src="https://img.shields.io/badge/PRs-welcome-brightgreen.svg" alt="PRs Welcome"></a>
</p>

---

## What is Kolang?

Kolang is an **open-source infrastructure layer** that sits between AI agents and [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) servers. It provides centralized **authentication, authorization, audit logging, and policy enforcement** — giving organizations the control they need to safely deploy AI agents with tool access in production.

Think of it as an **API Gateway, but purpose-built for the MCP ecosystem**.

---

## Why Kolang?

| | |
|---|---|
| 🔐 **Zero-Trust by Default** | Every tool call is authenticated, authorized, and audited. No implicit trust. |
| 🏛️ **Policy as Code** | Fine-grained access control powered by Open Policy Agent (OPA) and Rego. |
| 🏠 **Self-Hostable** | Deploy on your own infrastructure. No vendor lock-in. No data leaves your network. |
| 👁️ **Full Observability** | OpenTelemetry tracing, structured logging, and Prometheus metrics out of the box. |
| ✅ **Human-in-the-Loop** | Built-in approval workflows for sensitive operations. |
| 🧩 **Modular Architecture** | Clean package boundaries — start as a monolith, scale to services when needed. |

---

## Architecture Overview

Kolang follows a **Modular Monolith** architecture with clear boundaries between the **Control Plane** (policy, identity, registry) and the **Data Plane** (gateway, protocol adapters).

```
┌─────────────────────────────────────────────────────────────────┐
│                        Kolang ACP                               │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │   Identity    │  │    Policy    │  │      Registry        │  │
│  │  (OIDC/JWT)   │  │  (OPA/Rego)  │  │  (Server Catalog)    │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘  │
│         │                 │                      │              │
│  ┌──────▼─────────────────▼──────────────────────▼───────────┐  │
│  │                      Gateway                              │  │
│  │        (Routing · Enforcement · Approval · Audit)         │  │
│  └────────────┬──────────────────────────────┬───────────────┘  │
│               │                              │                  │
└───────────────┼──────────────────────────────┼──────────────────┘
                │                              │
        ┌───────▼───────┐              ┌───────▼───────┐
        │  Downstream   │              │   Upstream    │
        │  (Agents)     │              │ (MCP Servers) │
        └───────────────┘              └───────────────┘
```

> **Design Principles:** Internal policy models are independent of MCP/JSON-RPC wire formats. Upstream and downstream connections use separate interfaces. Every request carries `request_id` and `correlation_id`.

---

## Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Make (optional but recommended)

### Setup

```bash
# Clone the repository
git clone https://github.com/sepehr-safaeian/Kolang.git
cd Kolang

# Install dependencies
make install

# Copy and configure environment
cp .env.example .env

# Start infrastructure (Postgres, Keycloak, OPA, Redis)
make up

# Apply database migrations
make migrate

# Start the development server
make dev
```

The API will be available at `http://localhost:8000/api/docs`.

---

## Project Structure

```
├── apps/
│   ├── api/                    # FastAPI application entrypoint
│   └── web/                    # Next.js admin interface
├── packages/
│   └── acp_core/
│       ├── protocol/           # MCP adapters and internal messages
│       ├── gateway/            # Request routing and enforcement path
│       ├── identity/           # Principals and token validation
│       ├── policy/             # PDP, OPA client, policy models
│       ├── registry/           # MCP server and tool catalog
│       ├── approvals/          # Approval state machine
│       ├── credentials/        # Credential interfaces and encryption
│       ├── audit/              # Audit events and sinks
│       ├── telemetry/          # Tracing, metrics, logging
│       └── common/             # Shared types and errors
├── examples/                   # Demo servers, clients, policies
├── deploy/                     # Docker Compose, Keycloak, OPA, monitoring
├── migrations/                 # Alembic database migrations
├── tests/                      # Unit, integration, contract, security, e2e
├── docs/                       # Product, architecture, security, operations
└── scripts/                    # Utility scripts
```

---

## Tech Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| **Backend** | Python + FastAPI | Strong AI/Identity ecosystem, rapid development |
| **MCP** | Official Python SDK | Reduced risk vs. manual protocol implementation |
| **Validation** | Pydantic v2 | Contract modeling and runtime validation |
| **Database** | PostgreSQL | Relational storage, JSONB, transactions |
| **ORM / Migration** | SQLAlchemy 2 + Alembic | Async-first ORM with controlled migrations |
| **Policy Engine** | OPA + Rego | Industry-standard, avoids building a new DSL |
| **Identity (Dev)** | Keycloak | Self-hosted IdP for OIDC testing |
| **Cache / Rate Limit** | Redis (optional) | Added only when genuinely needed |
| **Admin UI** | Next.js + TypeScript | Developer-friendly admin dashboard |
| **API Docs** | OpenAPI | Auto-generated from FastAPI |
| **Observability** | OpenTelemetry + Prometheus + Grafana | Standard tracing and metrics |
| **Packaging** | Docker Compose | Simple deployment for MVP |
| **Tests** | Pytest + HTTPX + Playwright | Unit, integration, and UI testing |
| **CI** | GitHub Actions | Lint, type check, test, build |

---

## Development

```bash
# Format code
make fmt

# Run linters
make lint

# Run all tests
make test

# Run tests with coverage
make test-cov

# Run security scan
make security

# Run the full CI pipeline locally
make ci
```

---

## Deployment

### Docker Compose (Development)

```bash
make up      # Start all services
make down    # Stop all services
```

This starts: PostgreSQL, Keycloak, OPA, Redis, Prometheus, and Grafana alongside the Kolang API.

### Production

See [docs/operations/](docs/operations/) for production deployment guides.

---

## Documentation

| Topic | Link |
|-------|------|
| Architecture | [docs/architecture/](docs/architecture/) |
| Security Model | [docs/security/](docs/security/) |
| Database & Migrations | [docs/development/database-migrations.md](docs/development/database-migrations.md) |
| Operations | [docs/operations/](docs/operations/) |
| Product | [docs/product/](docs/product/) |
| Research | [docs/research/](docs/research/) |

---

## Contributing

We welcome contributions! Please read our [Contributing Guide](CONTRIBUTING.md) for details on:

- Setting up the development environment
- Branch naming and commit conventions
- Pull request process
- Code style and testing requirements

---

## Security

If you discover a security vulnerability, please follow our [Security Policy](SECURITY.md) for responsible disclosure. **Do not open a public issue.**

---

## License

This project is licensed under the [Apache License 2.0](LICENSE).

---

<p align="center">
  Built with ❤️ by the Kolang community
  <br />
  <sub>Giving organizations the control plane their AI agents deserve.</sub>
</p>
