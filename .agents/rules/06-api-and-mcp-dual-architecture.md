# Rule 06: Dual Architecture — REST API & MCP (Model Context Protocol)

> **Mandate:** In Kolang, all core capabilities, domains, and operations MUST be accessible through two native protocols: RESTful HTTP API and Model Context Protocol (MCP).

---

## 1. The Dual-Protocol Principle

Kolang is an **Agent Control Plane and MCP Gateway**. AI agents interact with tools through MCP, while administrators, microservices, and frontends interact via REST API. Neither protocol is an afterthought; both are first-class citizens.

```
       ┌──────────────────────────────────────────────────┐
       │                   Domain Core                    │
       │  (acp_core: Policies, Approvals, Registry, etc.) │
       └─────────────────────────┬────────────────────────┘
                                 │
                 ┌───────────────┴───────────────┐
                 ▼                               ▼
       ┌───────────────────┐           ┌───────────────────┐
       │   FastAPI (REST)  │           │   MCP Gateway     │
       │  /api/v1/...      │           │  Tools & Servers  │
       │  OpenAPI 3.1      │           │  SSE / Stdio      │
       └───────────────────┘           └───────────────────┘
```

---

## 2. API Guidelines (FastAPI)

1. **RESTful Resource URIs:**
   - Plural nouns: `/api/v1/gateways`, `/api/v1/mcp-servers`, `/api/v1/policies`, `/api/v1/approvals`.
   - Idempotent verbs: `GET` (retrieve), `POST` (create), `PUT`/`PATCH` (update), `DELETE` (remove).
2. **Standard Error Schema:**
   API errors must always return structured JSON in English:
   ```json
   {
     "error": {
       "code": "POLICY_VIOLATION",
       "message": "Tool execution denied by active policy 'deny-external-network'",
       "details": { "tool": "curl_fetch", "server_id": "srv_123" },
       "trace_id": "018f4a12-..."
     }
   }
   ```
3. **Pydantic Validation:**
   Every request and response body must be validated with strict Pydantic models.

---

## 3. MCP (Model Context Protocol) Guidelines

1. **MCP Tools:**
   Every operational action exposed to agents must be defined as an MCP Tool:
   - Tool name: lowercase snake_case (e.g., `kolang_evaluate_policy`, `kolang_request_approval`, `kolang_list_servers`).
   - Description: Detailed semantic explanation of what the tool does, required arguments, and side-effects.
   - Input Schema: JSON Schema defining parameters with type constraints.
2. **MCP Resources:**
   Expose live state and configuration as inspectable MCP resources:
   - URI scheme: `kolang://servers/{server_id}`, `kolang://policies/{policy_id}`, `kolang://traces/{trace_id}`.
3. **MCP Prompts:**
   Provide reusable system prompts for agent self-governance and approval requests.
