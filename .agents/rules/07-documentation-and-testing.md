# Rule 07: Comprehensive Documentation & Testing Standards

> **Mandate:** Every single function, class, endpoint, and UI component in Kolang MUST have clean documentation and automated test coverage. All documentation, comments, and docstrings must strictly be written in English (zero Persian). Zero undocumented or untested code.

---

## 1. Documentation Requirements (English Strictly)

All documentation, docstrings, code comments, and markdown documents must be authored strictly in English. No Persian or non-English text is permitted in repository files.

### 1.1 Python Code (Backend & SDK)
- Every public function, class, method, and router must include a structured docstring (Google / Sphinx format):
  ```python
  async def evaluate_policy(
      context: PolicyEvaluationContext,
      db_session: AsyncSession,
  ) -> PolicyDecision:
      """Evaluates whether an incoming agent tool execution request is permitted.

      Args:
          context: Rich execution context containing identity, tool, server, and payload.
          db_session: Active asynchronous database transaction session.

      Returns:
          PolicyDecision indicating PERMIT, DENY, or REQUIRES_APPROVAL with audit metadata.

      Raises:
          PolicyEngineError: If the OPA engine evaluation fails or times out.
      """
  ```

### 1.2 TypeScript / React Code (Frontend)
- Every React component, hook, and utility must feature TSDoc comments:
  ```typescript
  interface StatusBadgeProps {
    /** The semantic operational state to display */
    status: 'healthy' | 'degraded' | 'offline' | 'pending';
    /** Optional explicit icon override; defaults to mapped status icon */
    icon?: LucideIcon;
    /** Accessible screen-reader text when visual label differs */
    ariaLabel?: string;
  }

  /**
   * StatusBadge renders an accessible, token-styled operational status pill.
   * Conforms to WCAG 2.1 AA multi-modal visual requirements.
   */
  export const StatusBadge: FC<StatusBadgeProps> = ({ status, icon: Icon, ariaLabel }) => { ... };
  ```

### 1.3 System & Architectural Documentation
- Whenever a new router, package, or subsystem is introduced, update the corresponding markdown file in `docs/architecture/` or `docs/operations/`.

---

## 2. Testing Requirements

### 2.1 Python Backend Testing (`pytest`)
- **Unit Tests (`tests/unit/`):** Pure function logic, domain models, Pydantic validation, utility functions.
- **Integration Tests (`tests/integration/`):** FastAPI endpoints, database persistence, Redis caching, OPA policy evaluation.
- **Contract Tests (`tests/contract/`):** MCP protocol schemas, OpenAPI specification consistency.
- **Security Tests (`tests/security/`):** Token validation, authorization bypass checks, prompt injection sanitization.

### 2.2 Frontend Testing
- **Component Tests (`vitest` + `@testing-library/react`):**
  - Verify render in both Light and Dark mode.
  - Verify all 4 language dictionaries render properly.
  - Verify keyboard accessibility and ARIA roles.
  - Verify loading, empty, and error states.

### 2.3 Definition of Done (DoD) Checklist
Before marking any task complete:
- [ ] Code follows formatting standards (`ruff format`, `eslint`).
- [ ] Linting & Type check passes with 0 errors (`ruff check`, `mypy --strict`, `tsc --noEmit`).
- [ ] Unit & integration tests written for all new functions/components.
- [ ] Test suite executes with 100% pass rate (`pytest`, `vitest`).
- [ ] Docstrings / TSDoc written for all public APIs.
