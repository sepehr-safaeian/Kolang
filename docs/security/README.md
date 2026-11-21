# Kolang Security Architecture

## Security Model

Kolang operates under a **Zero-Trust** security architecture for AI agent tool interactions.

### Authentication & Principals
- Supports OpenID Connect (OIDC) tokens with Keycloak as a reference identity provider.
- Principals are categorized into `user`, `service`, and `agent` types with distinct trust tiers.

### Authorization & Policy as Code
- Open Policy Agent (OPA) evaluates requests against declarative Rego rules.
- Supported effects: `allow`, `deny`, and `conditional` (requiring human-in-the-loop approval).

### Credential Protection
- Credentials for upstream servers are encrypted at rest using AES-GCM / 256-bit Fernet keys.
- Decrypted secrets are kept only in ephemeral process memory during upstream invocations.

### Audit & Forensics
- All authorization decisions, tool invocations, and approval transitions emit structured immutable audit events.
