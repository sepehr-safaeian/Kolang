# Kolang Architecture

## Overview

Kolang is engineered as a **Modular Monolith** for an Agent Control Plane and Model Context Protocol (MCP) Gateway.

```
┌─────────────────────────────────────────────────────────────┐
│                        Control Plane                        │
│   Identity (OIDC)   ·   Policy (OPA)   ·   Registry (MCP)   │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│                         Data Plane                          │
│                      Gateway Router                         │
│       - Context Propagation (request_id, correlation_id)     │
│       - Policy Enforcement Point (PEP)                      │
│       - Approval Workflow State Machine                     │
│       - Upstream & Downstream Protocol Abstraction          │
└─────────────────────────────────────────────────────────────┘
```

## Key Architectural Principles

1. **Modular Monolith First**: Explicit package boundaries and domain interfaces without premature microservice fragmentation.
2. **Protocol Independence**: The policy engine and internal domain models are completely decoupled from JSON-RPC and wire-level MCP transport details.
3. **Decoupled Interfaces**: Downstream agent consumers and upstream MCP tool providers connect via isolated protocols (`DownstreamHandler` and `UpstreamConnector`).
4. **Context Propagation**: Every operation enforces `request_id` and `correlation_id` through `contextvars` and telemetry spans.
5. **Robust Networking**: All upstream calls apply strict timeout enforcement, cancellation tokens, and payload size bounds.
