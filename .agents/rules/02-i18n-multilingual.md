# Rule 02: 4-Language Multilingual Standard (i18n)

> **Mandate:** All user-facing interfaces in Kolang MUST support 4 languages without exception. Zero hardcoded strings allowed in UI code.

---

## 1. Supported Languages

| Code | Language | Role | Direction |
|---|---|---|---|
| `en` | English | Canonical / Default language | LTR |
| `de` | German (Deutsch) | Supported language | LTR |
| `ru` | Russian (Русский) | Supported language | LTR |
| `zh` | Chinese Simplified (简体中文) | Supported language | LTR |

*(Note: Persian/Arabic RTL script compatibility is maintained in layout infrastructure via CSS logical properties and dynamic `dir="rtl"` attribute).*

---

## 2. Separation of Concerns (UI vs. System)

### Machine & System Layer (English Only)
- API endpoint URLs, query parameters, and header keys.
- Internal error codes, exception classes, and traceback logs.
- OpenTelemetry span names, trace IDs, audit log action identifiers (`agent.invoke`, `policy.evaluate`).
- Database column names, enum keys (`PENDING`, `APPROVED`, `DENIED`).

### User Presentation Layer (Strictly Multilingual)
- Page titles, headings, navigation links, and breadcrumbs.
- Button labels, form input placeholders, helper texts, and validation tooltips.
- Status badges and human-readable descriptions.
- Modal dialogues, confirmation prompts, toast notifications.
- Empty states, error boundary UI fallback messages.

---

## 3. Implementation Rules

1. **Zero Hardcoded Strings in Component Code:**
   ```tsx
   // ❌ FORBIDDEN:
   <button className="btn-primary">Add Gateway</button>
   <span>No gateways found</span>

   // ✅ REQUIRED:
   <button className="btn-primary">{t('gateways.actions.add')}</button>
   <span>{t('gateways.empty_state.title')}</span>
   ```

2. **Dictionary Synchronization:**
   Whenever a new translation key is added to `en.json`, corresponding keys MUST simultaneously be added to `de.json`, `ru.json`, and `zh.json`.

3. **Technical Identifiers in LTR Containers:**
   Even in RTL context or multi-byte language environments, technical strings (URLs, IPs, JSON keys, UUIDs, Git hashes, MCP tool names) must remain in an isolated LTR container:
   ```tsx
   <code dir="ltr" className="font-mono text-sm">{server.endpointUrl}</code>
   ```

4. **Number and Timestamp Formatting:**
   Always use locale-aware formatting APIs (`Intl.NumberFormat`, `Intl.DateTimeFormat`) for rendering metrics, percentages, latencies, and dates:
   ```typescript
   // Latency formatting: 1,420 ms vs 1.420 ms
   new Intl.NumberFormat(locale, { style: 'unit', unit: 'millisecond' }).format(latency);
   ```
