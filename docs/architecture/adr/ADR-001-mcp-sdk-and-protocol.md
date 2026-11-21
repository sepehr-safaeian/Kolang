# ADR-001: Verification and Standardization of MCP SDK, Protocol Version, and Transport

- **Status:** Accepted
- **Date:** 2026-11-21
- **Deciders:** Kolang Architecture & Core Engineering Team
- **Task ID:** ACP-002
- **Related ADRs / Docs:**
  - `docs/architecture/README.md`
  - `docs/development/implementation-status.md`
  - `agent-control-plane-mvp-backlog.md` (ACP-001, ACP-002)

---

## 1. Context and Problem Statement

Kolang operates as an enterprise-grade Agent Control Plane (ACP) and Model Context Protocol (MCP) Gateway. In this role, Kolang acts as an intermediary (gateway/reverse-proxy/policy enforcement point) between downstream AI agents/clients and upstream MCP tool providers.

Prior to this decision:
1. The repository did not include the official MCP Python SDK in `pyproject.toml` or `uv.lock`.
2. Existing codebase contained abstract internal models (`acp_core.protocol.models`) and mock demo servers/clients without direct dependency on the official specification wire types.
3. The MCP specification has evolved significantly:
   - Initial stable release: `2024-11-05`
   - Iterative revisions: `2025-03-26`, `2025-06-18`, `2025-11-25` (handshake-based session era)
   - Modern specification revision: `2026-07-28` (stateless per-request envelope era)
4. Kolang requires a definitive, pinned SDK dependency and an explicit architectural contract covering protocol versions, transports, HTTP semantics, security protections, pagination, and error handling.

---

## 2. Decision

We standardize on and pin the official Python MCP SDK:
```toml
mcp = "2.3.0"
```
pinned explicitly in `pyproject.toml` and resolved into `uv.lock`.

### 2.1 Protocol Version Standards

Kolang adopts the **dual-era capability model** supported by `mcp==2.3.0` and the official MCP Specification (`https://modelcontextprotocol.io/specification/`):

1. **Latest Protocol Version (Modern Era):** `2026-07-28`
   - Characterized by stateless per-request message envelopes.
   - Eliminates mandatory initialization handshake overhead for remote HTTP requests.
   - Request metadata is embedded within the `_meta` object using key `io.modelcontextprotocol/protocolVersion` and mirrored into HTTP headers (`mcp-protocol-version`).
2. **Handshake Protocol Versions (Legacy / Compatibility Era):**
   - Latest Handshake Version: `2025-11-25`
   - Revisions: `2025-06-18`, `2025-03-26`, `2024-11-05` (oldest supported)
   - Full backward compatibility is maintained for upstream MCP servers or legacy clients using the `initialize` -> `notifications/initialized` handshake.
3. **Default Negotiated Version:** `2025-03-26` (used as baseline fallback when older handshake clients do not negotiate a higher revision).
4. **JSON-RPC Standard:** Strictly `2.0`.

### 2.2 Transport Standard: Streamable HTTP

For the Kolang MVP, **Streamable HTTP** (`TransportType.STREAMABLE_HTTP`) is the primary, required transport:
- **Downstream Agents / Clients:** Connect to Kolang Gateway via Streamable HTTP.
- **Upstream MCP Tool Servers:** Kolang Gateway connects to remote tool servers via Streamable HTTP. Local tool subprocesses may optionally use `stdio` through internal adapters.
- **Legacy SSE Transport:** Supported as fallback where standalone SSE endpoint pairing is mandated by older third-party servers.

---

## 3. Wire Protocol & HTTP Transport Specifications

### 3.1 HTTP Endpoints and Methods
- **Endpoint Pattern:** Single canonical endpoint (e.g., `/mcp` or `/api/v1/gateway/mcp`).
- **HTTP POST:** Used by clients for sending all JSON-RPC requests (`tools/list`, `tools/call`, `ping`, `initialize`) and notifications.
- **HTTP GET:** Used when opening a Server-Sent Events (SSE) stream for streaming asynchronous responses, notifications, or keep-alive pings.

### 3.2 Headers, Media Types & Negotiation
1. **Content-Type:**
   - JSON-RPC requests & responses: `application/json` (`CONTENT_TYPE_JSON`).
   - Streaming responses: `text/event-stream` (`CONTENT_TYPE_SSE`).
2. **Accept Header Handling:**
   - Inspected via `check_accept_headers(request)`.
   - Adheres to RFC 7231 wildcard parsing: `*/*`, `application/*`, `text/*`, `application/json`, `text/event-stream`.
3. **MCP-Specific Headers:**
   - `mcp-protocol-version`: Mirrors the protocol version declared in the message envelope. If header and body diverge, standard error `HEADER_MISMATCH` (`-32020`) is emitted.
   - `mcp-session-id`: Optional session correlation header for stateful or session-bound upstream connections.
   - `last-event-id`: Resumption header for interrupted SSE event streams.

### 3.3 Security, Origin Validation & DNS Rebinding Protection
Kolang enforces transport-level security on all incoming Streamable HTTP connections:
1. **Origin Header Validation:** Incoming requests with `Origin` headers must match configured allowed origins (`allowed_origins`). Cross-origin requests from unauthorized web domains are rejected with `403 Forbidden`.
2. **Host Header Validation:** Prevents DNS rebinding attacks by validating the `Host` header against `allowed_hosts`.
3. **Request Body Size Limits:** Default maximum body size is enforced (4 MiB) to prevent denial-of-service via memory exhaustion.
4. **Authentication:**
   - Downstream: HTTP `Authorization: Bearer <token>` carrying OAuth 2.0 / OIDC JWTs.
   - Upstream: Pinned credential injection (API keys, bearer tokens) managed securely by Kolang's Credential Manager without exposing credentials to clients or logs.

### 3.4 Supported Lifecycle & Tool Call Primitives

The SDK (`mcp==2.3.0`) provides full type-safe models for all MVP operations:

| Protocol Method | Direction | SDK Type Model | Description |
|---|---|---|---|
| `initialize` | Client -> Server | `InitializeRequest` / `InitializeResult` | Handshake negotiation for legacy (<=2025-11-25) connections |
| `notifications/initialized` | Client -> Server | `InitializedNotification` | Signals client readiness following initialization |
| `ping` | Bidirectional | `PingRequest` / Empty Result | Liveness probe verifying network & server responsiveness |
| `tools/list` | Client -> Server | `ListToolsRequest` / `ListToolsResult` | Tool discovery with cursor-based pagination |
| `tools/call` | Client -> Server | `CallToolRequest` / `CallToolResult` | Tool execution with structured arguments & output blocks |

### 3.5 Pagination Specification
- `ListToolsRequest` accepts optional pagination parameters via `params.cursor`.
- `ListToolsResult` returns `tools: list[Tool]` and an optional `next_cursor: str | None`.
- When `next_cursor` is present and non-empty, further items exist; subsequent pages are retrieved by passing `cursor=next_cursor`.
- An absent or `None` `next_cursor` indicates the end of the tool list.

### 3.6 Error Handling Architecture

Kolang enforces a strict distinction between **Protocol Errors** and **Tool Execution Failures**:

1. **Protocol Errors (JSON-RPC Error Responses):**
   Returned when request framing, routing, gateway policies, or protocol semantics fail:
   - `-32700` (`PARSE_ERROR`): Invalid JSON received.
   - `-32600` (`INVALID_REQUEST`): Malformed JSON-RPC structure.
   - `-32601` (`METHOD_NOT_FOUND`): Unrecognized MCP method.
   - `-32602` (`INVALID_PARAMS`): Parameters failed schema validation.
   - `-32603` (`INTERNAL_ERROR`): Unexpected gateway or upstream failure.
   - `-32000` (`CONNECTION_CLOSED`): Upstream connection terminated prematurely.
   - `-32001` (`REQUEST_TIMEOUT`): Upstream timeout threshold exceeded.
   - `-32020` (`HEADER_MISMATCH`): `mcp-protocol-version` header does not match body metadata.
   - `-32021` (`MISSING_REQUIRED_CLIENT_CAPABILITY`): Missing client feature declaration.
   - `-32022` (`UNSUPPORTED_PROTOCOL_VERSION`): Requested version cannot be negotiated.
   - `-32042` (`URL_ELICITATION_REQUIRED`): Elicitation challenge required.

2. **Tool Execution Failures (Application Level):**
   When a tool is validly invoked by an authorized principal but the tool itself returns an operational error, MCP protocol dictates returning a successful JSON-RPC response with:
   ```json
   {
     "jsonrpc": "2.0",
     "id": 1,
     "result": {
       "content": [
         {
           "type": "text",
           "text": "Detailed error message from upstream tool"
         }
       ],
       "is_error": true
     }
   }
   ```
   This ensures LLM agent runtimes can inspect and recover from tool execution errors without breaking the JSON-RPC communication channel.

---

## 4. Scope Boundaries for MVP

As mandated by backlog directives:
- **Included in MVP Scope:** Tools ONLY (`tools/list`, `tools/call`, tool pagination, tool parameter schema validation, policy checks, approval gates).
- **Excluded from MVP Scope:**
  - `resources/*` (Resources, resource templates, subscriptions).
  - `prompts/*` (Server-defined prompt templates).
  - `sampling/*` (Server-initiated LLM sampling).
  - `roots/*` (Workspace roots notification).
  
Deferred capabilities will be designed in subsequent post-MVP phases (ACP-070+).

---

## 5. Compatibility Limitations & Consequences

### 5.1 Benefits
- **Zero Handshake Latency:** Support for `2026-07-28` enables stateless per-request execution, crucial for horizontal scaling of the Kolang Gateway behind cloud load balancers.
- **Broad Compatibility:** Dual-era negotiation ensures upstream tools built on older SDK versions (`1.x`, `2024-11-05` to `2025-11-25`) continue to work seamlessly without modification.
- **Enterprise Security:** Built-in support for DNS rebinding protection, Host/Origin validation, and Bearer token authentication aligns with Kolang's security mandate.
- **Decoupled Architecture:** Kolang's internal protocol representation (`acp_core.protocol.models`) remains independent of the wire format, with official SDK types serving as the adapter boundary.

### 5.2 Limitations & Mitigations
1. **Dependency on `httpx2`:** The MCP SDK v2 requires `httpx2>=2.10.0` for client transport with OS-native trust store verification (`truststore`). Kolang maintains both `httpx>=0.27` (for internal HTTP clients) and `httpx2` without naming or binary collision.
2. **Strict Tool Header Annotation Validation:** In v2.3.0, tool registration strictly validates `x-mcp-header` annotations. Tools declaring invalid types or unparseable headers fail at registration. Kolang's tool catalog registry must validate schemas during tool onboarding.
3. **Empty Parameter Stripping:** On `2025-11-25` legacy connections, empty `_meta` and `params` fields are omitted. Kolang's downstream and upstream adapters must treat absent params as `None` / empty dict interchangeably.
