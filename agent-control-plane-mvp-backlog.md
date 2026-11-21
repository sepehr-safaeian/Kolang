# Agent Control Plane / MCP Gateway — MVP Engineering Backlog

**Version:** `0.1.0 MVP Alpha`  
**Document type:** Executable engineering backlog / task specifications  
**Task count:** 69 total (62 P0/P1 release-required or core tasks; 7 P2 polish tasks)  
**Date:** 21 November 2026  
**Language:** توضیحات فارسی؛ نام APIها، کلاس‌ها، فیلدها و اصطلاحات فنی به انگلیسی  
**Target:** Python + FastAPI + official MCP Python SDK + PostgreSQL + SQLAlchemy 2 + Alembic + OPA + Keycloak + Next.js (اختیاری برای دمو) + Docker Compose  
**Delivery model:** یک Developer با کمک AI Coding Agent؛ هر تسک به‌صورت مستقل و قابل واگذاری به Gemini

---

# 0. نحوه استفاده از این Backlog

این سند برای تبدیل مستقیم به Issueهای GitHub نوشته شده است. هر بخش یک Task مستقل است. برای اجرای کار، فقط متن یک Task را به Gemini بده؛ هم‌زمان چند Task را به آن نسپار، مگر اینکه وابستگی‌ها و Scope آن‌ها کاملاً روشن باشد.

## 0.1 دستورالعمل ثابت برای Gemini

این دستورالعمل را همراه هر Task به Gemini بده یا یک بار در فایل `GEMINI.md` یا `AGENTS.md` مخزن قرار بده:

> تو در حال توسعه Agent Control Plane (ACP)، یک MCP Gateway سازمانی هستی. قبل از هر تغییری، Repository، ساختار فعلی، README، فایل‌های معماری، ADRها، قراردادهای API، مدل‌های موجود و تست‌ها را بررسی کن. فرض نکن که ساختار پیشنهادی این سند عیناً با Repository فعلی یکسان است؛ الگوهای موجود را حفظ کن و فقط در صورت نیاز آن‌ها را با کمترین تغییر توسعه بده.
>
> فقط Task مشخص‌شده را اجرا کن. قابلیت‌های خارج از Scope را اضافه نکن، پروژه را بازنویسی نکن، فایل‌های سالم را صرفاً به دلیل سلیقه شخصی جابه‌جا نکن و Dependency جدید را بدون دلیل فنی اضافه نکن. اگر قابلیتی قبلاً پیاده‌سازی شده، ابتدا با کد و تست ثابت کن؛ سپس آن را دوباره نساز و به‌جای آن Gapهای واقعی را تکمیل کن.
>
> قبل از Coding، یک برنامه کوتاه شامل فایل‌های مورد تغییر و ریسک‌ها ارائه کن؛ سپس تغییر را انجام بده. کد باید Type-safe، دارای Error Handling، Logging امن و تست باشد. برای رفتارهای امنیتی فقط به توضیحات یا Prompt اعتماد نکن؛ Enforcement باید در Backend و در مسیر واقعی اجرای درخواست اعمال شود.
>
> از SDK رسمی MCP متناسب با نسخه پروتکل انتخاب‌شده در Repository استفاده کن. JSON-RPC/MCP را دستی از صفر پیاده‌سازی نکن، مگر اینکه یک Adapter کوچک برای یک نیاز مشخص لازم باشد. نسخه Dependency را Pin کن و سازگاری آن را با مستندات رسمی MCP بررسی کن.
>
> هیچ Token، Password، API Key، Cookie یا Secret خامی را در Source Code، Test Fixture عمومی، Log، Trace، Exception، Audit Event یا Screenshot قرار نده. از داده‌های ساختگی استفاده کن.
>
> پس از پایان کار: تست‌های مرتبط را اجرا کن؛ فایل‌های تغییرکرده را فهرست کن؛ دستورهای اجرا و تست را گزارش بده؛ نتیجه Acceptance Criteria را موردبه‌مورد اعلام کن؛ هر محدودیت یا مورد ناقص را صریح بنویس. ادعا نکن تستی اجرا شده که واقعاً اجرا نشده است.

## 0.2 معنی Priority

| Priority | معنی | قاعده اجرا |
|---|---|---|
| **P0 — Blocker** | برای کارکرد واقعی هسته MVP ضروری است | قبل از ادامه قابلیت‌های وابسته باید Done شود |
| **P1 — Required for MVP** | برای انتشار عمومی MVP یا دمو قابل اعتماد لازم است | قبل از Tag کردن `0.1.0` باید Done شود |
| **P2 — MVP Demo Polish** | برای تجربه بهتر دمو مفید است، اما مانع انتشار هسته MVP نیست | فقط بعد از P0 و P1 اجرا شود |

## 0.3 Scope قفل‌شده MVP

MVP باید این سناریو را End-to-End انجام دهد:

1. یک مدیر بتواند حداقل یک Upstream MCP Server را ثبت کند.
2. ACP بتواند به آن Server وصل شود و Toolهایش را با `tools/list` کشف کند.
3. Tool Name، Description، Input Schema و Fingerprint در Catalog ذخیره شوند.
4. یک MCP Client از طریق ACP به Gateway وصل شود.
5. درخواست ورودی دارای هویت معتبر باشد؛ برای Demo از Keycloak/OIDC استفاده شود.
6. درخواست `tools/list` فقط Toolهای قابل مشاهده برای Principal را نشان دهد.
7. درخواست `tools/call` پیش از Forward شدن، با OPA ارزیابی شود.
8. Tool ممنوع حتی با فراخوانی مستقیم و دست‌کاری‌شده اجرا نشود.
9. یک Tool حساس بتواند Approval بخواهد؛ بدون Approval معتبر اجرا نشود.
10. هر تصمیم و نتیجه اجرای Tool در Audit ثبت شود.
11. Credential اتصال Upstream در صورت نیاز، امن ذخیره و بدون افشا استفاده شود.
12. دمو با Docker Compose و داده ساختگی قابل اجرا باشد.

### خارج از MVP

- Resources و Prompts؛ فقط Tools در مسیر اصلی پشتیبانی شوند.
- پشتیبانی از stdio به‌عنوان Transport؛ MVP روی Streamable HTTP متمرکز است. اگر Repository از قبل stdio دارد، آن را نشکن؛ ولی توسعه آن در این Backlog نیست.
- Delegated OAuth / Token Exchange کامل و انتقال مجوز واقعی کاربر به سیستم مقصد.
- یکپارچگی اختصاصی با Odoo، Jira، GitHub یا SAP؛ برای MVP از Demo MCP Server استفاده کن.
- Agent Chat Interface؛ مکالمه در Claude، Cursor یا Agent Host انجام می‌شود.
- کنترل Terminal، Filesystem و ابزارهای داخلی IDE که از مسیر MCP Gateway عبور نمی‌کنند.
- LLM-based security verdict؛ هوش مصنوعی می‌تواند توضیح تولید کند، اما تصمیم Allow/Deny باید قطعی و مبتنی بر Policy باشد.
- Multi-region، Kubernetes، High Availability و Multi-tenant SaaS.
- UI کامل و پرجزئیات؛ برای MVP، API و OpenAPI Docs کافی است. UI محدود در Taskهای P2 تعریف شده است.

## 0.4 تصمیم‌های فنی ثابت MVP

| بخش | تصمیم |
|---|---|
| Backend | Python + FastAPI |
| MCP | Official MCP Python SDK؛ نسخه Pin شده و ثبت‌شده در ADR |
| Transport | Streamable HTTP برای Downstream و Upstream |
| Database | PostgreSQL |
| ORM / Migration | SQLAlchemy 2 + Alembic |
| Validation | Pydantic |
| Policy Engine | Open Policy Agent (OPA) + Rego |
| Demo Identity Provider | Keycloak با OIDC |
| Frontend | در MVP اجباری نیست؛ صفحات محدود در P2 |
| Packaging | Docker Compose |
| Testing | Pytest + HTTPX؛ Playwright فقط در صورت وجود UI |
| CI | GitHub Actions |
| Observability | Structured Logging؛ Metrics پایه P1؛ OpenTelemetry Tracing پیشرفته می‌تواند به 1.0 منتقل شود |

## 0.5 ترتیب اجرا و وابستگی‌ها

ترتیب پیشنهادی اجرای Taskها:

| گروه | Task IDs | خروجی |
|---|---|---|
| A. Repository & Architecture | ACP-001 تا ACP-005 | شناخت Repository و تثبیت Contractها |
| B. Data Model & Persistence | ACP-006 تا ACP-014 | مدل‌های پایدار و Migrationها |
| C. Demo MCP & Gateway | ACP-015 تا ACP-024 | مسیر واقعی MCP Client → ACP → Upstream |
| D. Tool Registry | ACP-025 تا ACP-030 | کشف، نگهداری و مشاهده Toolها |
| E. Identity | ACP-031 تا ACP-037 | هویت قابل اعتماد و Workspace Isolation |
| F. Policy | ACP-038 تا ACP-044 | Allow/Deny واقعی با OPA |
| G. Approval | ACP-045 تا ACP-049 | تأیید یک عملیات معین و یک‌بارمصرف |
| H. Credentials | ACP-050 تا ACP-052 | ذخیره و مصرف امن Credential |
| I. Audit & Operations | ACP-053 تا ACP-057 | Audit، Health، Metrics و Error Semantics |
| J. Tests, Packaging & Release | ACP-058 تا ACP-065 | تست End-to-End، Security، Docker و انتشار |
| K. Optional Demo UI | ACP-066 تا ACP-069 | پنل حداقلی برای نمایش محصول |

> اگر Repository بعضی Taskها را از قبل دارد، Gemini باید با تست و کد آن را اثبات کند و Task را به‌عنوان `Already implemented — verified` گزارش دهد؛ نباید کد موجود را بی‌دلیل بازنویسی کند.

---

# A. Repository, Architecture & Engineering Baseline

## ACP-001 — Audit the Existing Repository and Map the Current Implementation

**Task Summary:** بررسی کامل Repository و تهیه نقشه وضعیت فعلی پروژه پیش از هر تغییر کد.

**Description:**

قبل از توسعه، وضعیت واقعی Repository را شناسایی کن. چون بخشی از پروژه قبلاً ساخته شده، نباید ساختار جدیدی را روی ساختار موجود تحمیل کنی.

کارهای لازم:

1. ساختار پوشه‌ها و فایل‌های اصلی را فهرست کن.
2. زبان‌ها، Frameworkها و Dependencyهای اصلی را از `pyproject.toml`، `package.json`، Lockfileها و Dockerfileها استخراج کن.
3. Entry Pointهای Backend و Frontend را پیدا کن.
4. مدل‌های Database، Migrationها و اتصال Database را بررسی کن.
5. MCP SDK و نحوه استفاده فعلی از آن را شناسایی کن.
6. هرگونه MCP Server، MCP Client، Gateway، Registry یا Proxy موجود را بررسی کن.
7. نحوه فعلی Authentication، Authorization، Logging و Error Handling را پیدا کن.
8. Test Suite و CI Workflow را اجرا یا وضعیت عدم امکان اجرای آن را ثبت کن.
9. قابلیت‌های موجود را با Scope این Backlog مقایسه کن.
10. فایل `docs/development/implementation-status.md` بساز یا به‌روزرسانی کن.

در فایل وضعیت، برای هر حوزه یکی از این وضعیت‌ها را ثبت کن: `Implemented & Tested`، `Implemented but Untested`، `Partially Implemented`، `Missing` یا `Blocked`.

**Acceptance Criteria:**

- هیچ فایل Source Code در این Task تغییر نکند، مگر اصلاح ضروری در مستند وضعیت.
- ساختار واقعی Repository مستند شده باشد.
- دستورات واقعی اجرای Backend، تست‌ها و Frontend ثبت شده باشند.
- نقاطی که با این Backlog تفاوت دارند فهرست شوند.
- Taskهای بعدی بتوانند از این گزارش به‌عنوان Context استفاده کنند.

**Priority:** P0 — Blocker

**Dependencies:** ندارد.

---

## ACP-002 — Verify MCP SDK, Protocol Version and Transport Compatibility

**Task Summary:** تثبیت نسخه MCP و SDK رسمی مورد استفاده در پروژه.

**Description:**

نسخه MCP را حدس نزن و پیاده‌سازی پروتکل را از روی Blog Post یا مثال قدیمی انجام نده. نسخه SDK موجود در Repository را بررسی و آن را با Specification رسمی متناظر تطبیق بده.

کارهای لازم:

1. مستندات رسمی MCP را در `https://modelcontextprotocol.io/specification/` بررسی کن.
2. نسخه رسمی SDK Python موجود در PyPI/GitHub و Release Notes آن را بررسی کن.
3. Transport مورد نیاز MVP یعنی Streamable HTTP را تأیید کن.
4. پشتیبانی SDK از `initialize`، `notifications/initialized`، `ping`، `tools/list`، `tools/call`، Pagination و خطاهای پروتکل را مشخص کن.
5. رفتار HTTP، Content-Type، Accept Header، SSE در صورت استفاده SDK، Origin Validation و Authentication را مستند کن.
6. اگر SDK فعلی با نسخه هدف ناسازگار است، کم‌ریسک‌ترین Upgrade را پیشنهاد بده؛ بدون Upgrade بزرگ و بی‌دلیل.
7. نسخه Dependency را Pin و تصمیم را در `docs/architecture/adr/ADR-00X-mcp-sdk-and-protocol.md` ثبت کن.

**محدودیت Scope:** در MVP فقط Tools لازم‌اند. Resources و Prompts را پیاده‌سازی نکن.

**Acceptance Criteria:**

- نسخه SDK و نسخه Specification در ADR ثبت شده‌اند.
- Dependency در Lockfile Pin شده است.
- دلایل انتخاب و Compatibility Limitations ثبت شده‌اند.
- کد MCP موجود با Upgrade احتمالی نشکسته و تست‌های مرتبط سبز هستند.

**Priority:** P0 — Blocker

**Dependencies:** ACP-001.

---

## ACP-003 — Define Internal Gateway Request and Decision Contracts

**Task Summary:** طراحی مدل‌های داخلی مستقل از MCP برای Request Context، Principal، Resource و Policy Decision.

**Description:**

مدل‌های داخلی ACP را طوری تعریف کن که منطق امنیتی مستقیماً به ساختار JSON-RPC وابسته نباشد. Adapter پروتکل باید پیام MCP را به این مدل‌ها تبدیل کند.

حداقل مدل‌های مفهومی:

- `Principal`: نوع هویت، شناسه، Workspace، نقش‌ها و Attributes معتبر.
- `RequestContext`: Request ID، Correlation ID، زمان، Client ID و Transport.
- `ToolResource`: Server ID، Tool ID، نام Tool و Fingerprint.
- `ToolInvocation`: نام Tool، Arguments و مقصد Upstream.
- `PolicyInput`: Principal، Action، Resource و Context.
- `PolicyDecision`: `allow`، `deny` یا `require_approval`، همراه Reason Code، Policy ID، Version و Obligations.
- `GatewayResult`: نتیجه اجرای Upstream یا خطای استانداردشده.

قواعد:

1. از Pydantic Model یا ساختار Domain موجود Repository استفاده کن.
2. تمام IDها و Timestampها نوع مشخص و Validation داشته باشند.
3. Raw Access Token یا Secret را در هیچ Model عمومی قرار نده.
4. `workspace_id` برای تمام Entityهای متعلق به سازمان اجباری باشد.
5. Decision Reason را با Code ماشینی و Message انسانی جدا نگه دار.
6. Modelها نباید به FastAPI Request یا MCP SDK Object وابسته باشند.

**Acceptance Criteria:**

- مدل‌ها در یک محل Domain مشخص تعریف شده‌اند.
- Unit Test برای Validation و Serialization وجود دارد.
- مدل Policy Decision حداقل سه تصمیم Allow/Deny/Require Approval را پشتیبانی می‌کند.
- هیچ Secret یا Token خامی در Serialization Model وجود ندارد.

**Priority:** P0 — Blocker

**Dependencies:** ACP-001، ACP-002.

---

## ACP-004 — Establish Configuration and Environment Variable Management

**Task Summary:** ایجاد Settings مرکزی، اعتبارسنجی Environment Variableها و نمونه تنظیمات امن.

**Description:**

تمام تنظیمات Runtime باید از یک لایه مرکزی و Type-safe خوانده شوند. از خواندن پراکنده `os.environ` در بخش‌های مختلف برنامه جلوگیری کن.

تنظیمات مورد نیاز MVP:

- `ACP_ENV` برای محیط اجرا.
- `ACP_DATABASE_URL` برای PostgreSQL.
- `ACP_OIDC_ISSUER_URL` و `ACP_OIDC_AUDIENCE`.
- `ACP_OIDC_JWKS_URL` در صورت استفاده مستقیم.
- `ACP_OPA_URL`.
- `ACP_ENCRYPTION_KEY` یا مسیر Secret File برای کلید رمزنگاری.
- `ACP_LOG_LEVEL`.
- `ACP_REQUEST_TIMEOUT_SECONDS`.
- `ACP_MAX_REQUEST_BODY_BYTES`.
- `ACP_ALLOWED_UPSTREAM_HOSTS` یا مکانیزم Allowlist معادل.

قواعد:

1. مقدارهای پیش‌فرض Dev را از Production جدا کن.
2. در Production نبودن کلید رمزنگاری یا OIDC تنظیم‌شده را با Error واضح متوقف کن.
3. Secret واقعی را در `.env.example` قرار نده؛ فقط Placeholder مستندشده قرار بده.
4. مقدارهای حساس را هنگام چاپ Settings Mask کن.
5. Config نامعتبر باید در Startup خطای مشخص بدهد، نه اینکه برنامه با مقدار ناامن ادامه دهد.

**Acceptance Criteria:**

- یک Settings Object مرکزی وجود دارد.
- Environment Variableها Type Validation دارند.
- `.env.example` به‌روز است.
- Secretها در Log چاپ نمی‌شوند.
- تست برای Missing/Invalid Configuration وجود دارد.

**Priority:** P0 — Blocker

**Dependencies:** ACP-001.

---

## ACP-005 — Add Structured Logging and Request Correlation

**Task Summary:** پیاده‌سازی Logging ساختاریافته و شناسه‌های قابل ردیابی برای هر درخواست.

**Description:**

برای هر درخواست ورودی Gateway یک `request_id` ایجاد یا شناسه معتبر موجود را طبق سیاست مشخص حفظ کن و یک `correlation_id` برای زنجیره درخواست ایجاد کن. این شناسه باید در لایه‌های Protocol، Identity، Policy، Upstream و Audit قابل دسترسی باشد.

Logها باید Structured JSON باشند و حداقل فیلدهای زیر را برای رخدادهای مناسب داشته باشند:

- timestamp
- level
- service
- environment
- request_id
- correlation_id
- workspace_id در صورت احراز‌شده‌بودن
- component
- event_name
- error_code در صورت خطا

ممنوع:

- Authorization Header کامل.
- Access Token، Refresh Token، API Key، Password یا Cookie.
- کل Payload ابزار به‌صورت پیش‌فرض.
- اطلاعات شخصی یا مالی غیرضروری.

یک Redaction Utility مرکزی بساز و در Logging و Exception Handling استفاده کن.

**Acceptance Criteria:**

- Logهای درخواست‌ها قابل جست‌وجو و Correlate هستند.
- یک تست ثابت می‌کند Token نمونه در Log ظاهر نمی‌شود.
- Exceptionهای Upstream Secret یا Header حساس را افشا نمی‌کنند.
- Logging باعث تغییر رفتار یا Crash برنامه نمی‌شود.

**Priority:** P0 — Blocker

**Dependencies:** ACP-001، ACP-003، ACP-004.

---

# B. Data Model and Persistence

## ACP-006 — Configure PostgreSQL Connection and SQLAlchemy Session Lifecycle

**Task Summary:** ایجاد یا تکمیل لایه Database، Session و Transaction Management.

**Description:**

لایه Database را با SQLAlchemy 2 و PostgreSQL مطابق الگوی موجود Repository تنظیم کن. اگر Repository از قبل ORM یا Database Layer سالم دارد، آن را جایگزین نکن.

الزامات:

1. Database Engine و Session Factory مرکزی باشند.
2. Session در هر Request به شکل صحیح ایجاد و بسته شود.
3. Transactionها در مرزهای مشخص Service مدیریت شوند.
4. Connection Pool دارای تنظیمات معقول و قابل پیکربندی باشد.
5. اتصال ناموفق در Startup/Readiness قابل تشخیص باشد.
6. Unit Testها تا جای ممکن از SQLite استفاده نکنند، اگر رفتارهای PostgreSQL-specific مهم است؛ Integration Test باید PostgreSQL واقعی در Docker داشته باشد.

**Acceptance Criteria:**

- اتصال به PostgreSQL در Docker کار می‌کند.
- Session Leak در تست‌ها مشاهده نمی‌شود.
- Health Check اتصال Database را گزارش می‌کند.
- خطای Database به Response عمومی امن تبدیل می‌شود.

**Priority:** P0 — Blocker

**Dependencies:** ACP-004.

---

## ACP-007 — Create Initial Alembic Migration and Migration Workflow

**Task Summary:** ایجاد یا تکمیل Alembic و روند Migration نسخه‌دار.

**Description:**

Alembic باید منبع رسمی تغییر Schema باشد. هر تغییر مدل Database باید Migration قابل بازبینی داشته باشد.

کارها:

1. Alembic را به Metadata مدل‌ها متصل کن.
2. دستورهای `upgrade` و `downgrade` را در Development Guide مستند کن.
3. Migration اولیه را فقط بر اساس مدل‌های واقعی MVP بساز.
4. اجرای Migration روی Database خالی را تست کن.
5. از اجرای خودکار Migration در هر Worker یا هر Request جلوگیری کن؛ آن را به یک مرحله مشخص Startup/Deployment تبدیل کن.
6. اگر Migration داده را حذف یا تغییر مخرب می‌دهد، آن را صریح علامت‌گذاری و از Scope MVP خارج کن مگر ضرورت اثبات‌شده داشته باشد.

**Acceptance Criteria:**

- نصب تمیز از Database خالی موفق است.
- `alembic upgrade head` کار می‌کند.
- Migrationها در Git Versioned هستند.
- CI حداقل Migration Upgrade را تست می‌کند.

**Priority:** P0 — Blocker

**Dependencies:** ACP-006.

---

## ACP-008 — Implement Workspace Domain Model and Tenant Scoping

**Task Summary:** ایجاد Workspace به‌عنوان مرز مالکیت داده‌های سازمان.

**Description:**

Entity `Workspace` را با فیلدهای حداقل زیر بساز:

- `id` با UUID یا شناسه غیرقابل حدس.
- `name`.
- `slug` یکتا در محدوده محصول، اگر لازم است.
- `status` مانند active/disabled.
- `created_at` و `updated_at`.

تمام Entityهای مربوط به Server، Tool، Agent، Policy، Approval، Credential و Audit باید `workspace_id` داشته باشند، مگر Audit Global که باید دلیل جداگانه داشته باشد.

قواعد:

1. Workspace Scope را از Principal معتبر در Request Context استخراج کن.
2. `workspace_id` ارسالی از Body را به‌تنهایی منبع اعتماد قرار نده.
3. تمام Queryهای مدیریتی باید Workspace-scoped باشند.
4. برای Demo یک Workspace Seed ایجاد کن.
5. تست دسترسی Cross-Workspace بنویس.

**Acceptance Criteria:**

- یک Workspace Demo با Seed Data ساخته می‌شود.
- Query متعلق به Workspace دیگر قابل مشاهده یا تغییر نیست.
- تست IDOR/Cross-Workspace برای Server و Policy وجود دارد.
- Workspace Scope در Service Layer اعمال شده، نه فقط در UI.

**Priority:** P0 — Blocker

**Dependencies:** ACP-003، ACP-006، ACP-007.

---

## ACP-009 — Create MCP Server Domain Model

**Task Summary:** مدل پایدار برای ثبت و مدیریت Upstream MCP Serverها.

**Description:**

Entity مربوط به Upstream MCP Server را ایجاد کن. این Entity حداقل شامل موارد زیر باشد:

- `id`
- `workspace_id`
- `name` و `slug`
- `endpoint_url`
- `transport`؛ در MVP مقدار Streamable HTTP.
- `status`؛ مانند pending، connected، unavailable، error، disabled.
- `auth_profile_id` در صورت نیاز.
- `last_discovered_at`
- `last_health_check_at`
- `created_at` و `updated_at`.

قواعد:

1. URL را Parse و Validate کن.
2. `https` را برای مقصدهای غیرلوکال الزامی کن؛ HTTP فقط برای Demo Local و با تنظیم روشن و مستند مجاز باشد.
3. از URLهای localhost، loopback، private network، link-local و cloud metadata در ورودی سازمانی جلوگیری کن؛ برای Demo Local یک Allowlist صریح داشته باش.
4. Endpoint باید Workspace-scoped باشد.
5. URL و Credential در Log افشا نشوند.

**Acceptance Criteria:**

- CRUD پایه Domain و Migration وجود دارد.
- URL نامعتبر رد می‌شود.
- Server متعلق به Workspace دیگر قابل دسترسی نیست.
- تست SSRF/Host Validation وجود دارد.

**Priority:** P0 — Blocker

**Dependencies:** ACP-006، ACP-007، ACP-008.

---

## ACP-010 — Create Tool and Tool Snapshot Data Models

**Task Summary:** ایجاد مدل Tool Catalog و تاریخچه Snapshotهای Discovery.

**Description:**

دو Entity بساز:

1. `Tool`: تعریف فعلی Tool کشف‌شده از یک Server.
2. `ToolSnapshot`: نسخه تاریخی خروجی Discovery برای مقایسه تغییرات.

حداقل فیلدهای Tool:

- `id`, `workspace_id`, `server_id`
- `name`, `title` اختیاری، `description`
- `input_schema` به‌صورت JSONB
- `annotations` به‌صورت JSONB، اگر توسط SDK/Protocol ارائه شده‌اند
- `fingerprint`
- `classification_status` با مقدار اولیه `unclassified`
- `risk_labels` به‌صورت مجموعه‌ای از برچسب‌های مستقل، نه یک Risk Number مبهم
- `is_enabled`
- `first_discovered_at`, `last_discovered_at`.

Snapshot باید تاریخ، Hash کل Catalog و تعریف کامل هر Tool را نگهداری کند.

قواعد:

- Tool Name در محدوده Server یکتا باشد.
- Description و Schema ورودی غیرقابل اعتماد تلقی شوند.
- JSON Schema فقط به‌عنوان قرارداد ورودی استفاده شود؛ آن را اثبات امنیت رفتار Tool فرض نکن.
- داده حجیم یا Schema غیرمعتبر باید رد یا محدود شود.

**Acceptance Criteria:**

- Migration و Modelها وجود دارند.
- Schema به‌صورت JSONB ذخیره و بازیابی می‌شود.
- Fingerprint در Model قابل ذخیره است.
- Toolها بین Workspaceها نشت نمی‌کنند.

**Priority:** P0 — Blocker

**Dependencies:** ACP-007، ACP-008، ACP-009.

---

## ACP-011 — Create Principal, Agent and MCP Client Identity Models

**Task Summary:** تفکیک هویت Human User، Agent Workload و MCP Client در مدل Domain.

**Description:**

در MVP باید هویت درخواست‌دهنده با یک رشته دلخواه Header اشتباه گرفته نشود. مدل‌های لازم را ایجاد یا مدل موجود را تکمیل کن:

- `Agent`: هویت Workload شامل ID، Workspace، Name، Owner/Team اختیاری و Status.
- `MCPClientRegistration`: شناسه Client مورد انتظار از IdP و وضعیت آن.
- `WorkspaceMembership`: رابطه User و Workspace با Role.
- `PrincipalContext`: مدل Runtime که پس از اعتبارسنجی Token ایجاد می‌شود.

برای Demo، Client ID یا Service Account ثبت‌شده در Keycloak را به Agent Identity متناظر Map کن. اگر Token نماینده Human User هم هست، `sub` و `azp` را طبق Claimهای معتبر و تنظیمات IdP تفسیر کن. از `X-Agent-ID` یا Body به‌عنوان مدرک هویت استفاده نکن.

**Acceptance Criteria:**

- Human User و Agent دو نوع هویت مجزا دارند.
- Agent غیرفعال نمی‌تواند درخواست جدید اجرا کند.
- Client ثبت‌نشده یا ناشناخته رد می‌شود.
- هیچ هویت صرفاً از نام ارسالی در Header پذیرفته نمی‌شود.

**Priority:** P0 — Blocker

**Dependencies:** ACP-008.

---

## ACP-012 — Create Policy and Policy Version Models

**Task Summary:** ذخیره Policyها و نسخه‌های منتشرشده به شکل قابل ردیابی.

**Description:**

مدل‌های `Policy` و `PolicyVersion` را ایجاد کن. Policy Draft با Policy Published نباید یکی باشد.

فیلدهای پیشنهادی:

- Policy: `id`, `workspace_id`, `name`, `description`, `status`, `created_by`, timestamps.
- PolicyVersion: `id`, `policy_id`, `version`, `rego_source` یا `bundle_reference`, `checksum`, `published_at`, `published_by`.

قواعد:

1. Version منتشرشده Immutable باشد؛ ویرایش، نسخه جدید بسازد.
2. هر Decision باید Version دقیق Policy را ثبت کند.
3. Policy Draft تا زمان Publish نباید روی Gateway اعمال شود.
4. Workspace Scope اجباری باشد.

**Acceptance Criteria:**

- ایجاد Draft و انتشار نسخه جدید قابل تست است.
- نسخه قبلی بعد از انتشار نسخه جدید باقی می‌ماند.
- Checksum نسخه Policy ذخیره می‌شود.
- تست جلوگیری از دسترسی Cross-Workspace وجود دارد.

**Priority:** P0 — Blocker

**Dependencies:** ACP-007، ACP-008.

---

## ACP-013 — Create Approval Request Model and State Machine Fields

**Task Summary:** مدل داده مورد نیاز برای تأیید عملیات حساس.

**Description:**

Entity `ApprovalRequest` را با فیلدهای زیر ایجاد کن:

- `id`
- `workspace_id`
- `request_id`
- `principal_id` یا Snapshot شناسه Principal
- `server_id`, `tool_name`
- `payload_hash`
- `payload_encrypted` فقط در صورت نیاز به اجرای Retry بعد از Approval؛ اگر MVP از Re-submit دقیق استفاده می‌کند، Payload کامل را ذخیره نکن.
- `status`: pending، approved، rejected، expired، consumed، cancelled.
- `requested_at`, `expires_at`, `decided_at`, `consumed_at`
- `decided_by`
- `decision_reason` اختیاری.

State Transitionها باید در Service Layer کنترل شوند؛ تغییر Status آزاد از طریق CRUD عمومی مجاز نیست.

**Acceptance Criteria:**

- Stateهای تعریف‌شده در کد Enum هستند.
- انتقال غیرمجاز State رد می‌شود.
- هر Approval به Workspace، Principal، Tool و Payload Hash متصل است.
- Migration و Unit Test وجود دارد.

**Priority:** P1 — Required for MVP

**Dependencies:** ACP-007، ACP-008، ACP-011.

---

## ACP-014 — Create Audit Event Model and Append-oriented Persistence

**Task Summary:** ایجاد ساختار داده Audit برای ثبت تصمیم و اجرای Tool Call.

**Description:**

Entity `AuditEvent` را برای ذخیره رخدادهای Gateway ایجاد کن. حداقل فیلدها:

- Event ID و Timestamp.
- Workspace ID.
- Request ID و Correlation ID.
- Principal Type و Principal ID.
- MCP Server ID و Tool Name در صورت وجود.
- Action.
- Decision: allow/deny/require_approval.
- Reason Code.
- Policy ID و Policy Version.
- Execution Status: not_forwarded، forwarded، succeeded، failed، pending_approval.
- Duration و Upstream Status Code در صورت وجود.
- Redacted Metadata محدود و کنترل‌شده.

در MVP Audit را Append-oriented طراحی کن: API برای Update/Delete عمومی نداشته باشد. ادعای WORM یا Tamper-proof نکن؛ این قابلیت به نسخه بعد منتقل می‌شود.

**Acceptance Criteria:**

- Audit Event با Migration ساخته می‌شود.
- Eventهای تصمیم و Outcome قابل ذخیره هستند.
- API عمومی برای تغییر یا حذف Event وجود ندارد.
- تست می‌کند Token و Secret در Metadata ثبت نمی‌شود.

**Priority:** P0 — Blocker

**Dependencies:** ACP-007، ACP-008، ACP-003.

---

# C. Demo MCP Server and MCP Gateway Data Plane

## ACP-015 — Build a Reproducible Demo MCP Server

**Task Summary:** ساخت MCP Server نمونه برای تست و نمایش End-to-End پروژه.

**Description:**

یک MCP Server نمونه در پوشه `examples/demo-mcp-server` یا محل معادل موجود بساز. این Server نباید به Odoo یا GitHub واقعی وابسته باشد.

Tools زیر را پیاده‌سازی کن:

- `list_projects`: فقط داده ساختگی بخواند.
- `get_project`: اطلاعات یک پروژه ساختگی را بخواند.
- `list_issues`: Issueها را با فیلتر ساده برگرداند.
- `create_issue`: یک Issue ساختگی جدید ایجاد کند.
- `update_issue_status`: وضعیت Issue ساختگی را تغییر دهد.
- `delete_project`: یک عملیات مخرب نمونه باشد و فقط برای تست Policy استفاده شود.

داده اولیه Seed داشته باش؛ نام‌ها، ایمیل‌ها و اطلاعات مالی واقعی استفاده نکن.

برای هر Tool، Description روشن و JSON Schema معتبر بساز. اگر MCP SDK Annotationهایی برای Read-only، Destructive یا Idempotent ارائه می‌دهد، آن‌ها را مطابق معنی واقعی Tool تنظیم کن؛ این Annotationها را به‌تنهایی مبنای Security Decision قرار نده.

**Acceptance Criteria:**

- Server با دستور مستندشده اجرا می‌شود.
- حداقل ۶ Tool از طریق MCP SDK در دسترس هستند.
- Test برای هر Tool وجود دارد.
- داده Demo بعد از Restart طبق رفتار مستندشده Reset یا Persist می‌شود.
- هیچ داده واقعی یا Secret در مثال نیست.

**Priority:** P0 — Blocker

**Dependencies:** ACP-002، ACP-004.

---

## ACP-016 — Build a Demo MCP Client Smoke-test Script

**Task Summary:** ساخت Client سبک برای تست ارتباط با ACP و اجرای سناریوی Demo.

**Description:**

یک Script یا مثال Python بساز که بتواند به MCP Endpoint خود ACP متصل شود و این مراحل را انجام دهد:

1. اتصال با Bearer Token آزمایشی معتبر.
2. اجرای Initialize و Handshake مورد نیاز SDK.
3. دریافت `tools/list`.
4. انتخاب Tool مجاز مانند `list_projects`.
5. اجرای `tools/call` برای آن Tool.
6. تلاش برای اجرای Tool ممنوع مانند `delete_project`.
7. چاپ خروجی خوانا بدون نمایش Access Token.

Client باید از SDK رسمی استفاده کند و فقط برای Demo/Testing باشد؛ یک Agent یا LLM Chat UI نساز.

**Acceptance Criteria:**

- Script با Docker Demo کار می‌کند.
- Tool مجاز Success و Tool ممنوع Denied دریافت می‌کند.
- Exit Code مناسب برای استفاده در CI دارد.
- README دستور اجرای دقیق را دارد.

**Priority:** P1 — Required for MVP

**Dependencies:** ACP-015، ACP-018، ACP-031.

---

## ACP-017 — Implement Upstream MCP Client Adapter

**Task Summary:** ایجاد Adapter سمت Upstream برای اتصال ACP به MCP Serverهای ثبت‌شده.

**Description:**

یک Interface داخلی برای اتصال Upstream MCP تعریف کن و Implementation مربوط به Streamable HTTP را با SDK رسمی بساز.

الزامات:

- Client به‌ازای Server ثبت‌شده یا با Connection Pool کنترل‌شده ساخته شود.
- Endpoint از Server Registry خوانده شود؛ از ورودی Tool Call مستقیماً URL نساز.
- Transport و Authentication از تنظیمات Server/ Credential Profile خوانده شوند.
- Timeout اتصال و Tool Call قابل تنظیم باشد.
- خطای Connection، Protocol و Timeout به Error Type داخلی تبدیل شود.
- Client پس از استفاده درست بسته یا Reuse شود؛ Connection Leak نداشته باش.
- Redirect به Host غیرمجاز دنبال نشود.

در MVP فقط Streamable HTTP لازم است. اگر SDK فعلی اتصال stdio دارد، آن را حذف نکن؛ ولی Feature جدید برای آن نساز.

**Acceptance Criteria:**

- اتصال به Demo MCP Server موفق است.
- خطای Server در دسترس‌نبودن به شکل کنترل‌شده گزارش می‌شود.
- Timeout کار می‌کند.
- Upstream URL از Request Body قابل override نیست.
- Unit و Integration Test وجود دارد.

**Priority:** P0 — Blocker

**Dependencies:** ACP-002، ACP-004، ACP-009.

---

## ACP-018 — Implement Downstream MCP Streamable HTTP Endpoint

**Task Summary:** ارائه ACP به‌عنوان MCP Server برای Clientها.

**Description:**

یک MCP Endpoint در ACP ایجاد کن که MCP Client بتواند آن را به‌عنوان Server ثبت کند. از MCP SDK برای Protocol Handling استفاده کن.

در MVP این متدها را پشتیبانی کن:

- Initialize و Handshake.
- `ping` در صورت پشتیبانی SDK.
- `tools/list`.
- `tools/call`.
- Notifications لازم پروتکل.

Resources و Prompts را پیاده نکن و Capability آن‌ها را اعلام نکن.

الزامات HTTP:

- فقط Methodهای مجاز Transport را بپذیر.
- Content-Type و Accept را مطابق نسخه MCP انتخاب‌شده اعتبارسنجی کن.
- Origin Header را طبق الزامات Streamable HTTP بررسی کن؛ Origin نامعتبر باید Reject شود.
- HTTP Status و JSON-RPC Error را با SDK سازگار برگردان.
- CORS را فقط برای Originهای صریحاً مجاز فعال کن؛ `*` را همراه Credential مجاز نکن.

**Acceptance Criteria:**

- یک MCP Client استاندارد می‌تواند ACP را Initialize کند.
- `tools/list` و `tools/call` از Endpoint عبور می‌کنند.
- Origin نامعتبر در تست رد می‌شود.
- هیچ Capability خارج از Scope ادعا نمی‌شود.
- Integration Test با Demo Client سبز است.

**Priority:** P0 — Blocker

**Dependencies:** ACP-002، ACP-003، ACP-004، ACP-017.

---

## ACP-019 — Implement MCP Protocol Error Mapping and Compatibility Tests

**Task Summary:** مدیریت خطاهای MCP/JSON-RPC و جلوگیری از پاسخ‌های ناسازگار.

**Description:**

Errorهای داخلی ACP را به پاسخ معتبر MCP تبدیل کن. حداقل دسته‌های زیر را پوشش بده:

- Invalid JSON-RPC Request.
- Unsupported Method.
- Unknown Tool.
- Invalid Tool Arguments.
- Authentication Required/Invalid.
- Authorization Denied.
- Approval Required/Pending.
- Upstream Unavailable.
- Upstream Timeout.
- Internal Error.

متن خطا نباید Stack Trace، Database URL، Token یا Secret را افشا کند. در Audit، Error Code و جزئیات داخلی امن‌تر را ثبت کن.

تست‌ها باید علاوه بر Status Code، JSON-RPC Envelope و `isError`/Error semantics مورد انتظار SDK را بررسی کنند.

**Acceptance Criteria:**

- هر دسته خطا Mapping مستند دارد.
- Errorهای داخلی از Client پنهان می‌مانند ولی در Server Log قابل Debug هستند.
- تست Protocol برای Errorها وجود دارد.

**Priority:** P0 — Blocker

**Dependencies:** ACP-018.

---

## ACP-020 — Implement Request Limits, Timeouts and Cancellation

**Task Summary:** اعمال محدودیت‌های عملیاتی روی درخواست‌های MCP.

**Description:**

برای محافظت در برابر درخواست‌های بسیار بزرگ یا گیرکردن Upstream، محدودیت‌های زیر را اعمال کن:

- Maximum HTTP Body Size.
- Maximum JSON Argument Size.
- Connect Timeout.
- Tool Execution Timeout.
- Response Size Limit.
- Maximum Concurrent Upstream Requests به‌صورت قابل تنظیم.
- Cancellation Propagation، تا حدی که SDK/Transport پشتیبانی می‌کند.

مقادیر پیش‌فرض را در Config مرکزی قرار بده و در README توضیح بده. مقدارهای پیش‌فرض باید محافظه‌کارانه و قابل Override باشند.

برای Toolهای غیرIdempotent Retry خودکار انجام نده. اگر Retry در لایه Transport وجود دارد، آن را خاموش یا برای متدهای امن محدود کن.

**Acceptance Criteria:**

- Request بزرگ قبل از رسیدن به Upstream رد می‌شود.
- Timeout باعث آزاد شدن منابع می‌شود.
- Cancellation در صورت امکان به Upstream منتقل می‌شود.
- عملیات غیرIdempotent به‌صورت خودکار دوباره اجرا نمی‌شود.
- تست برای Payload بزرگ و Upstream کند وجود دارد.

**Priority:** P1 — Required for MVP

**Dependencies:** ACP-017، ACP-018، ACP-004.

---

## ACP-021 — Add Upstream Routing and Tool Namespace Mapping

**Task Summary:** Route کردن Tool Call به Server درست و جلوگیری از برخورد نام Toolها.

**Description:**

چند MCP Server ممکن است Tool هم‌نام داشته باشند. در Gateway باید یک نام Downstream بدون ابهام به Tool و Upstream واقعی Map شود.

برای MVP از Namespace پایدار استفاده کن؛ مثلاً:

- `demo__list_projects`
- `github__list_repositories`
- `odoo__create_ticket`

نام خارجی Tool باید در Tool Registry ذخیره شود و به `(server_id, upstream_tool_name)` Map شود.

قواعد:

1. از نام Tool ارسالی در `tools/call` مستقیماً برای ساخت URL یا انتخاب Host استفاده نکن.
2. ابتدا Tool را در Registry و Workspace جاری پیدا کن.
3. Tool غیرفعال یا حذف‌شده نباید Route شود.
4. Mapping باید در Discovery دوباره پایدار بماند.
5. نام‌های ناسازگار با محدودیت نام‌گذاری MCP باید به شکل deterministic مدیریت شوند.

**Acceptance Criteria:**

- دو Upstream با Tool هم‌نام بدون Collision قابل استفاده‌اند.
- Tool ناشناخته به Upstream ارسال نمی‌شود.
- Route فقط از Registry می‌آید.
- تست Namespace Collision وجود دارد.

**Priority:** P0 — Blocker

**Dependencies:** ACP-010، ACP-017.

---

## ACP-022 — Protect Upstream Registration Against SSRF and Unsafe Network Targets

**Task Summary:** جلوگیری از استفاده ACP به‌عنوان Proxy برای دسترسی به شبکه داخلی غیرمجاز.

**Description:**

چون ACP به URLهای ثبت‌شده متصل می‌شود، Registration یک نقطه حساس SSRF است.

الزامات:

1. فقط Schemeهای مجاز را بپذیر؛ در MVP برای Serverهای غیرلوکال HTTPS الزامی باشد.
2. آدرس‌های Loopback، Private, Link-local، Multicast، Unspecified و Cloud Metadata را رد کن، مگر اینکه Admin به‌صورت صریح در حالت Development آن‌ها را Allow کرده باشد.
3. IP را بعد از DNS Resolution نیز بررسی کن؛ صرف بررسی رشته URL کافی نیست.
4. Redirect را غیرفعال کن یا هر Redirect را از نظر Host و IP مجدداً Validate کن.
5. DNS Rebinding و تغییر IP بین Validation و Connect را تا حد امکان با Resolve و Connect کنترل‌شده کاهش بده.
6. در Docker Demo، فقط سرویس‌های نام‌گذاری‌شده در Network داخلی Demo را با Allowlist قابل تنظیم مجاز کن.
7. URL، Query String و Credential را در Log Mask کن.

**Acceptance Criteria:**

- درخواست به metadata address و private IP بدون Allowlist رد می‌شود.
- Redirect به Host غیرمجاز رد می‌شود.
- تست IPv4، IPv6 و DNS Resolution وجود دارد.
- Demo Local با Allowlist مستند کار می‌کند.

**Priority:** P0 — Blocker

**Dependencies:** ACP-009، ACP-017.

---

## ACP-023 — Implement Gateway Health and Upstream Connectivity Checks

**Task Summary:** ارائه Health Check مستقل برای خود ACP و Upstreamها.

**Description:**

سه وضعیت را از یکدیگر جدا کن:

- `/health/live`: آیا Process زنده است؟ نباید وابسته به همه سرویس‌های خارجی باشد.
- `/health/ready`: آیا ACP برای دریافت ترافیک آماده است؟ Database و Dependencyهای ضروری باید قابل دسترس باشند.
- Upstream Health: وضعیت هر MCP Server ثبت‌شده؛ این وضعیت نباید کل ACP را Unready کند، مگر معماری فعلی دلیل مشخصی داشته باشد.

برای Upstream Check از روش کم‌خطر و پشتیبانی‌شده SDK استفاده کن؛ فقط برای Health Check یک Tool مخرب یا ناشناخته اجرا نکن.

**Acceptance Criteria:**

- Liveness و Readiness جدا هستند.
- سلامت هر Server در Registry قابل مشاهده است.
- قطع یک Upstream باعث Crash کل ACP نمی‌شود.
- Test برای Database unavailable و Upstream unavailable وجود دارد.

**Priority:** P1 — Required for MVP

**Dependencies:** ACP-006، ACP-017.

---

# D. MCP Server Registry and Tool Intelligence

## ACP-024 — Create Admin API to Register and Manage Upstream MCP Servers

**Task Summary:** ارائه REST API مدیریتی برای ثبت، ویرایش، غیرفعال‌سازی و مشاهده MCP Serverها.

**Description:**

Endpointهای مدیریتی Versioned ایجاد کن. حداقل:

- `POST /api/v1/servers`
- `GET /api/v1/servers`
- `GET /api/v1/servers/{server_id}`
- `PATCH /api/v1/servers/{server_id}`
- `POST /api/v1/servers/{server_id}/disable`
- `POST /api/v1/servers/{server_id}/test-connection`

در Create، Name، Endpoint URL، Transport و Authentication Profile (در صورت وجود) دریافت شود. در Update، تغییر Endpoint باید باعث Health Check و Discovery مجدد شود.

قواعد:

- همه Endpointها Authentication مدیریتی داشته باشند.
- Role لازم برای تغییر Server، Admin یا Owner باشد.
- Workspace از Principal گرفته شود.
- خطاهای Validation به شکل یکسان برگردند.
- حذف Hard برای Server با تاریخچه Audit انجام نده؛ در MVP Disable و Soft Delete کافی است.

**Acceptance Criteria:**

- CRUD/Disable API در OpenAPI مستند است.
- کاربر غیرمدیر نمی‌تواند Server اضافه یا تغییر دهد.
- Cross-Workspace دسترسی رد می‌شود.
- Test برای هر Endpoint وجود دارد.

**Priority:** P0 — Blocker

**Dependencies:** ACP-008، ACP-009، ACP-011، ACP-018.

---

## ACP-025 — Implement Tool Discovery with Pagination and Schema Validation

**Task Summary:** کشف کامل Toolهای Upstream و ثبت آن‌ها در Catalog.

**Description:**

برای هر Upstream از `tools/list` استفاده کن و تا پایان Pagination، همه صفحات را دریافت کن. اگر Server Cursor ندهد، Discovery در همان پاسخ تمام شود.

اطلاعاتی که باید استخراج شوند:

- `name`.
- `title` در صورت وجود.
- `description`.
- `inputSchema`.
- Tool Annotations/Metadata در صورت پشتیبانی نسخه MCP/SDK.
- زمان Discovery.

قواعد:

1. JSON Schema را Validate کن و Schema نامعتبر را به‌عنوان Tool فعال منتشر نکن.
2. طول Name و Description و حجم Schema را محدود کن.
3. Tool Description و Metadata را Untrusted Data تلقی کن.
4. Discovery باید Idempotent باشد؛ اجرای دوباره نباید Tool Duplicate بسازد.
5. Tool جدید در اولین Discovery باید `unclassified` و بدون دسترسی گسترده باشد.
6. اگر Discovery نصفه شکست خورد، Catalog قبلی را به شکل ناقص جایگزین نکن؛ Snapshot ناقص را Failed ثبت کن.

**Acceptance Criteria:**

- Pagination کامل پشتیبانی می‌شود.
- Toolها در DB ذخیره می‌شوند.
- Schema نامعتبر یا بیش‌ازحد بزرگ فعال نمی‌شود.
- Discovery مجدد Duplicate تولید نمی‌کند.
- تست Empty List، چندصفحه‌ای، Schema نامعتبر و Upstream Failure وجود دارد.

**Priority:** P0 — Blocker

**Dependencies:** ACP-010، ACP-017، ACP-024.

---

## ACP-026 — Implement Deterministic Tool Fingerprints and Discovery Snapshots

**Task Summary:** محاسبه Fingerprint پایدار و ذخیره Snapshot هر Discovery.

**Description:**

برای هر Tool یک Fingerprint از داده Canonical شده تولید کن. Fingerprint حداقل باید این اجزا را پوشش دهد:

- Tool Name.
- Description.
- Input Schema.
- Annotationهای مرتبط با رفتار Tool.

قبل از Hash کردن JSON را Canonicalize کن: ترتیب Keyها، فاصله‌های غیرضروری و ترتیب غیرمعنایی Objectها نباید Hash را تصادفی تغییر دهند. برای Hash از SHA-256 استفاده کن.

هر بار Discovery موفق:

1. Snapshot جدید بسازد.
2. Toolهای جدید، حذف‌شده و تغییرکرده را تشخیص دهد.
3. Diff را ذخیره کند.
4. Event برای Drift مهم ایجاد کند.
5. مجوز قبلی را به Tool جدید یا تغییرکرده به شکل خودکار توسعه ندهد.

**Acceptance Criteria:**

- JSON معادل با ترتیب Key متفاوت Fingerprint یکسان دارد.
- تغییر Description یا Schema Fingerprint را عوض می‌کند.
- Add/Remove/Modify در Diff تشخیص داده می‌شود.
- تست برای هر نوع Drift وجود دارد.

**Priority:** P1 — Required for MVP

**Dependencies:** ACP-010، ACP-025، ACP-014.

---

## ACP-027 — Implement Safe Tool Classification Metadata

**Task Summary:** فراهم‌کردن طبقه‌بندی اولیه و قابل بازبینی برای Toolها.

**Description:**

برای هر Tool چند Attribute مستقل نگهداری کن؛ از یک Risk Score مبهم استفاده نکن:

- `data_access`: none/read/write/unknown.
- `mutates_state`: true/false/unknown.
- `destructive`: true/false/unknown.
- `sensitive_data`: true/false/unknown.
- `external_effect`: true/false/unknown.
- `reversibility`: reversible/irreversible/unknown.
- `classification_source`: admin/manual/annotation/rule.
- `classification_status`: unclassified/reviewed.

در MVP، Classification باید دستی یا Rule-based ساده باشد. Annotationهای MCP و نام Tool صرفاً Hint هستند، نه حقیقت قطعی.

اگر توضیح AI تولید می‌کنی، آن را فقط برای نمایش و کمک به مدیر استفاده کن و با وضعیت `ai_generated_unverified` ذخیره کن. خروجی LLM نباید Policy را مستقیماً تغییر دهد.

**Acceptance Criteria:**

- Tool جدید با وضعیت Unclassified ایجاد می‌شود.
- مدیر/Seed Admin می‌تواند Classification را تغییر دهد.
- تغییر Classification در Audit ثبت می‌شود.
- Tool Unclassified به‌صورت پیش‌فرض Allow نمی‌شود، مگر Policy صریحی وجود داشته باشد.

**Priority:** P1 — Required for MVP

**Dependencies:** ACP-010، ACP-014.

---

## ACP-028 — Add Tool Catalog Read API

**Task Summary:** ارائه API برای جست‌وجو و مشاهده Toolهای کشف‌شده.

**Description:**

Endpointهای زیر یا معادل سازگار در ساختار Repository ایجاد کن:

- `GET /api/v1/servers/{server_id}/tools`
- `GET /api/v1/tools/{tool_id}`
- `GET /api/v1/tools/{tool_id}/snapshots`

Query Filterهای پایه:

- server_id
- name search
- classification_status
- is_enabled
- destructive
- sensitive_data

در پاسخ، Schema، Description، Fingerprint و Classification را نمایش بده. Secret، Credential یا اطلاعات اتصال حساس نباید در خروجی API باشند.

**Acceptance Criteria:**

- Toolها فقط داخل Workspace مجاز قابل مشاهده‌اند.
- Pagination در Catalog API وجود دارد.
- فیلترها با هم کار می‌کنند.
- Schema خروجی به OpenAPI اضافه شده است.

**Priority:** P1 — Required for MVP

**Dependencies:** ACP-025، ACP-027، ACP-024.

---

## ACP-029 — Add Tool List Filtering Based on Principal Policy

**Task Summary:** نمایش فقط Toolهای مجاز یا قابل درخواست در `tools/list`.

**Description:**

هنگام پردازش `tools/list`، فهرست Toolهای Registry را برای Principal احراز‌شده بررسی کن.

رفتار پیشنهادی:

- Tool با Decision=Allow نمایش داده شود.
- Tool با Decision=Require Approval می‌تواند نمایش داده شود، چون Agent ممکن است آن را پیشنهاد کند؛ اجرای آن همچنان به Approval نیاز دارد.
- Tool با Decision=Deny یا Tool غیرفعال نمایش داده نشود.
- Tool Unclassified به‌صورت پیش‌فرض Deny/Hidden باشد، مگر Policy صریح وجود داشته باشد.

اگر MCP SDK Pagination را در سطح Tools پشتیبانی می‌کند، ابتدا فهرست مجاز را در Scope مشخص محاسبه کن و Pagination را درست اعمال کن؛ `nextCursor` نباید Tool ممنوع را افشا کند.

**Acceptance Criteria:**

- دو Principal با Policy متفاوت فهرست Tool متفاوت دریافت می‌کنند.
- Tool مخفی با فراخوانی مستقیم همچنان در `tools/call` رد می‌شود.
- Cursor/Pagination اطلاعات ممنوع را نشت نمی‌دهد.
- Test برای Allow، Deny، Approval و Unclassified وجود دارد.

**Priority:** P0 — Blocker

**Dependencies:** ACP-038، ACP-041، ACP-018، ACP-025.

---

## ACP-030 — Add Tool Catalog Refresh and Drift Review API

**Task Summary:** امکان Refresh کردن Discovery و مشاهده Drift از طریق API.

**Description:**

یک Endpoint برای Trigger کردن Discovery مجدد و یک Endpoint برای مشاهده Snapshot/Diff فراهم کن:

- `POST /api/v1/servers/{id}/discover`
- `GET /api/v1/servers/{id}/drift`

فقط Admin/Owner بتواند Discovery را Trigger کند. عملیات باید Timeout و وضعیت Started/Completed/Failed داشته باشد.

در صورت تغییر Schema، وضعیت Tool به `review_required` تغییر کند یا حداقل Event قابل مشاهده ایجاد شود. تا زمان Review، مجوز Tool تغییرکرده نباید گسترده‌تر شود.

**Acceptance Criteria:**

- Discovery مجدد از API قابل شروع است.
- نتیجه و زمان آن قابل مشاهده است.
- Drift قابل گزارش است.
- Trigger هم‌زمان چند Discovery غیرضروری را ایجاد نمی‌کند.

**Priority:** P2 — MVP Demo Polish

**Dependencies:** ACP-026، ACP-024.

---

# E. Identity and Access Management

## ACP-031 — Configure Keycloak for Local OIDC Development

**Task Summary:** اضافه‌کردن Keycloak به Docker Compose و ایجاد Realm/Clientهای Demo.

**Description:**

Keycloak را به محیط Local/Demo اضافه کن. تنظیمات Demo باید قابل بازتولید و Versioned باشند، اما Password واقعی در Git قرار نگیرد.

حداقل Seed Config:

- Realm به نام `acp-demo`.
- Client برای Admin API.
- Client/Service Account برای Demo Agent.
- User Demo با Role توسعه‌دهنده.
- User Demo با Role مدیر.
- Audience معتبر برای ACP Resource Server.
- تنظیمات Issuer و JWKS.

Credentials دمو باید صرفاً برای Local Demo باشند و در README صریحاً هشدار داده شود که برای Production مناسب نیستند.

**Acceptance Criteria:**

- Keycloak با Docker Compose اجرا می‌شود.
- Token برای User و Demo Agent قابل دریافت است.
- Claims و Audience مورد انتظار در خروجی قابل مشاهده‌اند.
- Realm قابل Import/Bootstrap از Repository است.

**Priority:** P0 — Blocker

**Dependencies:** ACP-004؛ از Docker Compose foundation موجود استفاده کن. اگر هنوز وجود ندارد، فقط تعریف سرویس Keycloak و Realm را در Compose فعلی اضافه کن؛ برای این Task منتظر ACP-063 نمان.

---

## ACP-032 — Implement OIDC JWT Validation and JWKS Key Rotation

**Task Summary:** اعتبارسنجی امن Access Tokenهای ورودی.

**Description:**

یک JWT Validation Service بساز یا تکمیل کن. حداقل موارد زیر را بررسی کن:

- Signature با Key معتبر از JWKS.
- Allowed Signing Algorithm؛ از `none` یا Algorithmهای ناخواسته جلوگیری کن.
- `iss` برابر Issuer تنظیم‌شده.
- `aud` شامل ACP Resource Audience مورد انتظار.
- `exp` و `nbf` با Clock Skew محدود.
- `iat` در صورت نیاز به Policy.
- `azp` یا Client Identifier مطابق Mapping ثبت‌شده.

JWKS باید با Cache و Refresh کنترل‌شده بارگیری شود. Key Rotation باید پشتیبانی شود؛ Token معتبر با `kid` جدید پس از Refresh قابل اعتبارسنجی باشد.

خطای JWKS/IdP نباید باعث Accept کردن Token نامعتبر شود.

**Acceptance Criteria:**

- Token معتبر پذیرفته می‌شود.
- Signature نامعتبر، Expired، Issuer اشتباه، Audience اشتباه و Algorithm ناامن رد می‌شوند.
- Key Rotation تست شده است.
- Token خام در Log ظاهر نمی‌شود.

**Priority:** P0 — Blocker

**Dependencies:** ACP-031، ACP-004، ACP-003.

---

## ACP-033 — Implement Principal Resolution from Validated OIDC Claims

**Task Summary:** تبدیل Claimهای معتبر Token به Principal Context داخلی.

**Description:**

بعد از JWT Validation، Principal را با Mapping کنترل‌شده بساز.

قواعد:

1. `sub` را به User یا Service Account شناخته‌شده Map کن.
2. `azp`/Client ID را فقط پس از Match با Client Registration معتبر به MCP Client یا Agent Map کن.
3. Role و Workspace را از Membership و Database بخوان؛ برای Permission حیاتی صرفاً به Role دلخواه داخل Token اعتماد نکن، مگر Issuer و Claim Mapping صریحاً تعریف شده باشد.
4. هویت Human و Agent را از هم جدا نگه دار.
5. در MVP Delegated OAuth کامل پیاده نکن؛ Context فقط هویت‌هایی را حمل کند که واقعاً در Token معتبر وجود دارند.
6. اگر Mapping ناقص یا مبهم است، Fail-closed کن.

**Acceptance Criteria:**

- User و Agent Demo به Principalهای متفاوت تبدیل می‌شوند.
- Client ID ناشناخته رد می‌شود.
- Principal دارای Workspace درست است.
- هویت دلخواه از Header پذیرفته نمی‌شود.
- تست برای Tokenهای User و Service Account وجود دارد.

**Priority:** P0 — Blocker

**Dependencies:** ACP-011، ACP-032، ACP-008.

---

## ACP-034 — Implement OIDC-Protected MCP Endpoint Authentication

**Task Summary:** محافظت Endpoint ورودی MCP با Bearer Access Token معتبر و رفتار مناسب Client.

**Description:**

Authentication Middleware را به MCP Endpoint وصل کن. قبل از اجرای متدهای محافظت‌شده، Access Token را Validate و Principal Context را در Request Context قرار بده.

الزامات:

- `Authorization: Bearer` را Parse کن.
- Token ناموجود یا نامعتبر را با پاسخ مناسب HTTP/Protocol رد کن.
- رفتار Challenge/WWW-Authenticate و Protected Resource Metadata را طبق نسخه Authorization Specification انتخاب‌شده و SDK/Clientهای هدف بررسی کن.
- Token را در Query String قبول نکن.
- Token را در Response، Error یا Log بازتاب نده.
- Admin REST API و MCP Endpoint را از نظر Authentication/Authorization به‌صورت مجزا اما سازگار پیاده کن.

**Acceptance Criteria:**

- MCP Request بدون Token معتبر قبل از Tool Routing متوقف می‌شود.
- Token معتبر به Principal Context تبدیل می‌شود.
- Token در Log یا Response ظاهر نمی‌شود.
- رفتار با یک MCP Client واقعی تست شده است.

**Priority:** P0 — Blocker

**Dependencies:** ACP-018، ACP-032، ACP-033.

---

## ACP-035 — Implement Workspace Membership and Admin Role Checks

**Task Summary:** اعمال نقش‌های پایه و محدودیت دسترسی مدیریتی.

**Description:**

در MVP حداقل Roleهای زیر را پشتیبانی کن:

- `owner`: مدیریت کامل Workspace.
- `admin`: مدیریت Server و Agent و تنظیمات پایه.
- `security_admin`: مدیریت Policy و Approval.
- `developer`: استفاده از Gateway و مشاهده Catalog مجاز.
- `auditor`: مشاهده Audit بدون تغییر تنظیمات.

Role Check را در Service/Dependency Layer پیاده کن، نه صرفاً در Frontend. برای هر REST Endpoint نقش لازم را مشخص کن.

در MVP نیازی به Role Builder سفارشی نیست؛ Roleها ثابت و مستند باشند.

**Acceptance Criteria:**

- ماتریس Role/Endpoint مستند است.
- Developer نمی‌تواند Server یا Policy منتشر کند.
- Auditor نمی‌تواند داده را تغییر دهد.
- Security Admin می‌تواند Approval را مدیریت کند، اما دسترسی نامحدود به Credential خام ندارد.
- تست مثبت و منفی برای هر Role وجود دارد.

**Priority:** P1 — Required for MVP

**Dependencies:** ACP-008، ACP-011، ACP-033.

---

## ACP-036 — Add Agent Registration, Disable and Ownership API

**Task Summary:** فراهم‌کردن API مدیریت Agentهای شناخته‌شده.

**Description:**

Endpointهای پایه برای ایجاد، مشاهده، تغییر Metadata و Disable کردن Agent ایجاد کن:

- `POST /api/v1/agents`
- `GET /api/v1/agents`
- `GET /api/v1/agents/{id}`
- `PATCH /api/v1/agents/{id}`
- `POST /api/v1/agents/{id}/disable`

Agent باید Owner/Team اختیاری، Workspace، Status و Client ID مرتبط داشته باشد. Agent Disable شده نباید در Principal Resolution یا Policy Evaluation مجاز شناخته شود.

در MVP Agent را به یک Client Registration مشخص متصل کن؛ Agent خوداظهاری از طریق Header قابل قبول نیست.

**Acceptance Criteria:**

- Admin می‌تواند Agent را ثبت و Disable کند.
- Agent Disable شده هیچ Tool Call جدیدی اجرا نمی‌کند.
- Agentها بین Workspaceها ایزوله هستند.
- تمام تغییرات مدیریتی Audit می‌شوند.

**Priority:** P1 — Required for MVP

**Dependencies:** ACP-011، ACP-033، ACP-035.

---

## ACP-037 — Add Identity and Tenant Isolation Security Test Suite

**Task Summary:** ایجاد تست‌های جامع Authentication، Authorization سطح مدیریتی و Tenant Isolation.

**Description:**

یک Test Suite مستقل برای Identity بساز که حداقل این سناریوها را پوشش دهد:

- Missing Token.
- Invalid Signature.
- Expired Token.
- Wrong Issuer.
- Wrong Audience.
- Unknown Client ID.
- Disabled Agent.
- Disabled User/Membership.
- Developer accessing Admin Endpoint.
- Auditor trying to modify a resource.
- Workspace A reading Workspace B Server/Tool/Policy/Approval.
- Forged `X-Agent-ID` Header.

از Test Fixtureهای واقعی Keycloak در Integration Test استفاده کن؛ صرف Mock کردن JWT Validator برای تست کل جریان کافی نیست.

**Acceptance Criteria:**

- همه تست‌های فوق در CI یا Integration Test Command اجرا می‌شوند.
- هیچ تست امنیتی به‌خاطر Skip شدن خاموش نیست، مگر دلیل و Issue ثبت شده باشد.
- خروجی CI شکست‌ها را واضح نشان می‌دهد.

**Priority:** P0 — Blocker

**Dependencies:** ACP-032 تا ACP-036.

---

# F. Policy Engine and Enforcement

## ACP-038 — Integrate Open Policy Agent as the Policy Decision Point

**Task Summary:** اتصال ACP به OPA و ساخت Client پایدار برای ارزیابی Policy.

**Description:**

OPA را به‌عنوان Policy Decision Point استفاده کن. ACP مسئول Enforcement است و OPA فقط Decision ساختاریافته برمی‌گرداند.

کارها:

1. OPA را به Docker Compose اضافه یا تنظیم موجود را تکمیل کن.
2. OPA Client با Timeout و Error Handling بساز.
3. Policy Input را از Domain Model استاندارد ACP تولید کن.
4. Decision Response را به `PolicyDecision` داخلی تبدیل کن.
5. Response ناقص، نامعتبر یا ناشناخته را Allow فرض نکن.
6. Policy Version و Bundle/Checksum را به Decision متصل کن.
7. Health Check برای OPA اضافه کن.

**Acceptance Criteria:**

- ACP می‌تواند یک Query واقعی به OPA بزند.
- Policy Response به مدل داخلی تبدیل می‌شود.
- OPA Unavailable باعث Allow ناخواسته نمی‌شود.
- Unit و Integration Test وجود دارد.

**Priority:** P0 — Blocker

**Dependencies:** ACP-003، ACP-012؛ سرویس OPA را در Docker Compose فعلی اضافه یا تکمیل کن؛ برای این Task منتظر ACP-063 نمان.

---

## ACP-039 — Create Default-Deny Rego Policy for MCP Tool Calls

**Task Summary:** ساخت Policy پایه OPA با رفتار Default Deny.

**Description:**

یک Policy Rego برای تصمیم‌گیری روی Tool Invocation بساز. Input باید شامل این موارد باشد:

- Workspace ID.
- Principal Type و ID.
- User ID در صورت وجود.
- Agent ID در صورت وجود.
- Roles/Attributes معتبر.
- Server ID.
- Tool ID و Tool Name.
- Classification Attributes.
- Environment/Context.

منطق MVP:

1. Principal ناشناخته یا غیرفعال: Deny.
2. Workspace نامعتبر یا نامنطبق: Deny.
3. Server Disabled: Deny.
4. Tool Disabled یا Unclassified: Deny، مگر Policy صریح.
5. Tool در Allow Rule باشد: Allow.
6. Tool در Require Approval Rule باشد: Require Approval.
7. در بقیه موارد: Deny.

قواعد نمونه را در `examples/policies/` قرار بده و چند Rule روشن برای Demo ایجاد کن. Policy Language یا Rule Builder اختصاصی طراحی نکن.

**Acceptance Criteria:**

- Default Decision همیشه Deny است.
- Allow و Require Approval فقط با Rule صریح رخ می‌دهند.
- Test برای هر حالت وجود دارد.
- Policy از طریق OPA CLI یا Test Runner قابل اجراست.

**Priority:** P0 — Blocker

**Dependencies:** ACP-012، ACP-038.

---

## ACP-040 — Implement Policy Management and Publish API

**Task Summary:** ایجاد API برای ساخت Policy Draft، انتشار نسخه و مشاهده نسخه‌ها.

**Description:**

Endpointهای زیر یا معادل آن‌ها را بساز:

- `POST /api/v1/policies`
- `GET /api/v1/policies`
- `GET /api/v1/policies/{id}`
- `POST /api/v1/policies/{id}/versions`
- `POST /api/v1/policies/{id}/publish`
- `GET /api/v1/policies/{id}/versions`

برای MVP ورودی Policy می‌تواند Rego Source محدود و Versioned باشد؛ اگر Repository از قبل قالب YAML یا JSON برای Policy دارد، آن را بی‌دلیل عوض نکن. Policy باید قبل از Publish از نظر Syntax/Compile در OPA اعتبارسنجی شود.

قواعد:

- فقط Security Admin/Owner اجازه Publish دارد.
- نسخه Published قابل تغییر نیست.
- Rollback یعنی Publish نسخه قبلی به‌عنوان نسخه جدید یا انتخاب یک نسخه فعال با Audit؛ سابقه حذف نشود.
- Policy از Workspace دیگر قابل استفاده یا مشاهده نیست.

**Acceptance Criteria:**

- Draft، Validate، Publish و Version History کار می‌کنند.
- Policy نامعتبر Publish نمی‌شود.
- تغییرات Policy در Audit ثبت می‌شوند.
- تست Role و Workspace وجود دارد.

**Priority:** P1 — Required for MVP

**Dependencies:** ACP-012، ACP-035، ACP-038، ACP-039.

---

## ACP-041 — Enforce Policy on Every tools/call Before Upstream Execution

**Task Summary:** اعمال قطعی Policy در مسیر واقعی اجرای Tool.

**Description:**

این مهم‌ترین Task امنیتی MVP است. تمام درخواست‌های `tools/call` باید از یک Enforcement Pipeline مشترک عبور کنند.

ترتیب پیشنهادی:

1. Validate MCP Request و Tool Name.
2. Resolve Server/Tool از Registry.
3. Resolve و Validate Principal.
4. بررسی Workspace و Status منابع.
5. ساخت Policy Input.
6. ارزیابی OPA.
7. اگر Deny: عدم Forward و ثبت Audit.
8. اگر Require Approval: ایجاد Approval و عدم Forward.
9. اگر Allow: دریافت Credential لازم و ارسال به Upstream.
10. ثبت Outcome نهایی و برگرداندن پاسخ.

هیچ مسیر جایگزین، Debug Endpoint یا Handler دیگری نباید بتواند بدون Policy به Upstream Tool دسترسی پیدا کند. منطق Enforcement را در یک Service مرکزی قرار بده و تمام Tool Invocationها را از همان مسیر عبور بده.

**Acceptance Criteria:**

- Tool مجاز واقعاً به Upstream می‌رسد.
- Tool ممنوع هرگز به Upstream نمی‌رسد.
- Deny با تغییر نام Tool، فراخوانی مستقیم یا حذف از `tools/list` دور زده نمی‌شود.
- Policy Engine Error برای عملیات حساس Fail-closed است.
- Test با Fake Upstream ثابت می‌کند تعداد Callهای Upstream در Deny برابر صفر است.

**Priority:** P0 — Blocker

**Dependencies:** ACP-017، ACP-018، ACP-021، ACP-033، ACP-038، ACP-039.

---

## ACP-042 — Generate and Persist a Decision Receipt for Every Policy Evaluation

**Task Summary:** ذخیره مدرک تصمیم Policy برای هر Tool Call.

**Description:**

برای هر Policy Evaluation یک Decision Receipt بساز که شامل موارد زیر باشد:

- Request ID.
- Principal Type و ID.
- Workspace ID.
- Server ID و Tool Name.
- Decision.
- Reason Code.
- Policy ID و Version.
- زمان Decision.
- Hash مرجع Tool Definition/Fingerprint.
- Approval ID در صورت نیاز.

Receipt نباید شامل Secret یا Raw Token باشد. Receipt باید با Audit Event رابطه قابل جست‌وجو داشته باشد.

**Acceptance Criteria:**

- هر Call به یک Receipt یا یک Audit Decision متصل است.
- Policy Version دقیق ذخیره می‌شود.
- Denied و Allowed هر دو Receipt دارند.
- Receipt قابل تغییر از طریق API عمومی نیست.

**Priority:** P1 — Required for MVP

**Dependencies:** ACP-014، ACP-041.

---

## ACP-043 — Add Policy Simulation/Explain Endpoint for Administrators

**Task Summary:** امکان بررسی نتیجه Policy بدون اجرای Tool.

**Description:**

Endpointی مانند `POST /api/v1/policies/simulate` بساز که Admin/Security Admin بتواند Principal، Server، Tool و Context را وارد کند و نتیجه Policy را ببیند.

این Endpoint نباید Tool را اجرا کند و نباید Credential Upstream را بخواند. خروجی باید Decision، Reason Code، Policy Version و فیلدهای اصلی ارزیابی‌شده را نشان دهد.

اگر OPA دلیل دقیق Rule را در حالت عادی برنمی‌گرداند، یک Explanation محدود و قابل اعتماد از ساختار Decision تولید کن؛ متن توضیح را به‌عنوان دلیل امنیتی قطعی جا نزن.

**Acceptance Criteria:**

- Simulation هیچ اتصال Tool Call به Upstream ایجاد نمی‌کند.
- فقط Role مجاز می‌تواند آن را اجرا کند.
- خروجی Allow/Deny/Require Approval با اجرای واقعی یکسان است.

**Priority:** P2 — MVP Demo Polish

**Dependencies:** ACP-038 تا ACP-040.

---

## ACP-044 — Add Basic Per-Agent Tool Call Rate Limiting

**Task Summary:** اعمال محدودیت نرخ ساده برای جلوگیری از مصرف یا فراخوانی غیرعادی.

**Description:**

یک Rate Limiter ساده per Workspace و per Agent/Principal پیاده کن. برای MVP می‌توان از Redis استفاده کرد، اگر در Repository وجود دارد یا واقعاً لازم است؛ در غیر این صورت یک Storage Interface بساز و محدودیت تک‌نمونه‌ای را صریحاً مستند کن.

حداقل قابلیت‌ها:

- Maximum Calls per Time Window.
- Configurable Limit.
- Rate Limit Decision در Gateway.
- `429` یا خطای MCP سازگار با رفتار Client.
- Audit Event برای Rate Limit Hit.

محدودیت باید قبل از Forward به Upstream اعمال شود. Rate Limit توزیع‌شده را ادعا نکن اگر Store فقط In-memory است.

**Acceptance Criteria:**

- تعداد Callها از حد تنظیم‌شده عبور نمی‌کند.
- Rate Limit برای Agentهای مختلف مستقل است.
- Reset/Window رفتار مستند و تست‌شده دارد.
- خرابی Store به Fail-open ناخواسته تبدیل نمی‌شود.

**Priority:** P2 — MVP Demo Polish

**Dependencies:** ACP-041، ACP-004.

---

# G. Approval Workflow

## ACP-045 — Create Approval Request When Policy Returns require_approval

**Task Summary:** توقف Tool Call و ایجاد Approval Pending برای عملیات حساس.

**Description:**

وقتی OPA نتیجه `require_approval` برمی‌گرداند، Gateway نباید Tool را به Upstream Forward کند. به‌جای آن:

1. Approval Request بساز.
2. Request ID، Principal، Workspace، Server، Tool و Payload Hash را ذخیره کن.
3. Status را `pending` قرار بده.
4. Expiry مشخص داشته باشد.
5. یک نتیجه استاندارد به MCP Client برگردان که توضیح دهد عملیات هنوز اجرا نشده و نیازمند تأیید است.
6. Approval ID را در Response قابل مشاهده کن، بدون آنکه Client بتواند با دانستن ID به‌تنهایی عملیات را اجرا کند.
7. Audit Event ایجاد کن.

برای جلوگیری از ذخیره داده حساس، MVP باید از Re-submit دقیق Tool Call پس از Approval استفاده کند؛ Payload کامل را در DB ذخیره نکن، مگر اینکه واقعاً برای طراحی اجرایی انتخاب شده و رمزنگاری شده باشد.

**Acceptance Criteria:**

- در حالت Pending تعداد فراخوانی Upstream صفر است.
- Approval ID و Expiry ایجاد می‌شود.
- Pending در Audit ذخیره می‌شود.
- Client پیام واضح دریافت می‌کند که عملیات هنوز انجام نشده است.

**Priority:** P1 — Required for MVP

**Dependencies:** ACP-013، ACP-041.

---

## ACP-046 — Implement Approval Approve and Reject API

**Task Summary:** ایجاد API مدیریت تصمیم Approval توسط انسان مجاز.

**Description:**

Endpointهای زیر را بساز:

- `GET /api/v1/approvals`
- `GET /api/v1/approvals/{approval_id}`
- `POST /api/v1/approvals/{approval_id}/approve`
- `POST /api/v1/approvals/{approval_id}/reject`

فقط Security Admin یا Role مشخص‌شده در Policy اجازه تصمیم دارد. Approver باید اطلاعات زیر را ببیند:

- درخواست‌کننده و Agent.
- Server و Tool.
- پارامترهای Redacted یا Safe Summary.
- Payload Hash.
- دلیل درخواست Approval.
- Expiry.

در MVP اگر Payload حساس یا شامل PII است، فقط Summary امن نشان بده؛ Raw Arguments را بدون نیاز ذخیره نکن.

**Acceptance Criteria:**

- User غیرمجاز نمی‌تواند Approve/Reject کند.
- Approval منقضی قابل Approve نیست.
- تصمیم Approver و Timestamp ثبت می‌شوند.
- هر Approval فقط یک تصمیم نهایی می‌گیرد.

**Priority:** P1 — Required for MVP

**Dependencies:** ACP-013، ACP-035، ACP-045، ACP-014.

---

## ACP-047 — Bind Approval to Exact Payload, Principal and One-time Consumption

**Task Summary:** جلوگیری از تغییر پارامتر و Replay پس از تأیید انسانی.

**Description:**

برای Approval Hash قطعی و Canonical از درخواست بساز. Hash باید حداقل شامل Workspace، Principal، Server، Tool Name و Arguments باشد. ترتیب Keyهای JSON نباید نتیجه Hash را تغییر دهد.

رفتار MVP:

1. Tool Call اول با Require Approval متوقف و Pending ایجاد می‌شود.
2. مدیر Approval را تأیید می‌کند.
3. Agent/Client باید همان Tool Call را با همان Principal و دقیقاً همان Arguments دوباره ارسال کند.
4. Gateway Payload Hash جدید را محاسبه می‌کند.
5. اگر Hash، Principal، Server یا Tool متفاوت است، Approval مصرف نشود و درخواست Deny شود.
6. اگر منطبق و Approval معتبر است، Status در Transaction به `consumed` تغییر کند و فقط همان درخواست اجرا شود.
7. Approval بعد از یک بار مصرف دوباره قابل استفاده نیست.

برای جلوگیری از Race Condition، Consume باید با Transaction و Lock/Conditional Update اتمیک انجام شود.

**Acceptance Criteria:**

- تغییر هر Argument بعد از Approval باعث Deny می‌شود.
- Principal دیگر نمی‌تواند Approval را مصرف کند.
- Approval دو بار مصرف نمی‌شود، حتی با دو Request هم‌زمان.
- Approval Expired/Rejected/Cancelled قابل مصرف نیست.
- تست Concurrency و Replay وجود دارد.

**Priority:** P0 — Blocker

**Dependencies:** ACP-045، ACP-046، ACP-013.

---

## ACP-048 — Implement Approval Expiration, Cancellation and Audit Events

**Task Summary:** تکمیل چرخه عمر Approval و ثبت همه Transitionها.

**Description:**

Expiry و State Transitionهای Approval را پیاده کن. حداقل Transitionها:

- pending → approved
- pending → rejected
- pending → expired
- pending → cancelled
- approved → consumed
- approved → expired

در هر Transition، Actor، Timestamp، Reason و Approval ID ثبت شود. اگر Background Scheduler در Repository وجود ندارد، Expiry را حداقل به‌صورت Lazy Evaluation هنگام Read/Consume انجام بده و این رفتار را مستند کن؛ برای MVP به Queue پیچیده نیاز نیست.

**Acceptance Criteria:**

- Approval بعد از Expiry قابل Approve یا Consume نیست.
- State Transition غیرمجاز رد می‌شود.
- تمام Transitionها Audit Event دارند.
- Race بین Expiry و Consume تست شده است.

**Priority:** P1 — Required for MVP

**Dependencies:** ACP-013، ACP-046، ACP-047، ACP-014.

---

## ACP-049 — Define Safe Approval UX and Developer Retry Semantics

**Task Summary:** تعریف و مستندسازی تعامل Agent/Developer با Approval بدون Chat Interface اختصاصی.

**Description:**

MVP چت‌بات داخلی ندارد. Agent در Claude/Cursor یا Host خودش با کاربر صحبت می‌کند. وقتی Gateway یک Approval Pending می‌سازد، نتیجه Tool باید به شکل قابل فهم به Agent برگردد که:

- عملیات هنوز اجرا نشده است.
- Approval ID چیست.
- وضعیت Pending است.
- کاربر/مدیر باید از کانال مدیریتی ACP آن را تأیید کند.
- پس از تأیید، Agent باید همان Call را با همان Arguments دوباره ارسال کند.

یک مثال MCP Client و راهنمای Developer ایجاد کن که این رفتار را نشان دهد. در صورت نیاز، یک Tool مدیریتی کم‌اختیار برای `get_approval_status` می‌تواند در مثال Client باشد؛ اما آن را بدون Authentication و Policy مناسب در Gateway عمومی منتشر نکن.

**Acceptance Criteria:**

- Demo Client پیام Pending را به‌شکل قابل فهم نشان می‌دهد.
- پس از Approve، تکرار دقیق Call موفق می‌شود.
- پس از Reject، Expiry یا تغییر Payload، Call اجرا نمی‌شود.
- Documentation جریان را بدون نیاز به خواندن Source توضیح می‌دهد.

**Priority:** P1 — Required for MVP

**Dependencies:** ACP-045 تا ACP-048، ACP-016.

---

# H. Upstream Credentials

## ACP-050 — Implement Secure Upstream Credential Storage

**Task Summary:** ذخیره Credentialهای Upstream به شکل رمزنگاری‌شده.

**Description:**

در MVP از Credential Profile ساده با پشتیبانی حداقل Bearer Token ثابت استفاده کن. OAuth Delegation و Token Exchange کامل خارج از MVP است.

الزامات:

1. Credential خام فقط هنگام ثبت در حافظه دریافت شود.
2. در Database فقط Ciphertext، Nonce، Key Version و Metadata لازم ذخیره شود.
3. از AES-256-GCM یا کتابخانه معتبر مبتنی بر AEAD استفاده کن.
4. Master Key از Environment یا Secret File خارج از Database دریافت شود.
5. برای هر Secret Nonce یکتا ایجاد شود.
6. تغییر Master Key و Key Version در Data Model قابل تشخیص باشد.
7. APIهای عمومی هرگز Secret خام را در Response برنگردانند.
8. اگر کلید رمزنگاری موجود نیست یا Decryption شکست خورد، Credential قابل استفاده نباشد.

**Acceptance Criteria:**

- Ciphertext در DB قابل مشاهده است ولی Secret خام نیست.
- Decryption فقط در مسیر Connector مجاز انجام می‌شود.
- تغییر Ciphertext یا Nonce باعث Decryption Failure می‌شود.
- Key Material در DB و Git ذخیره نشده است.
- Test برای Encrypt/Decrypt و خطای کلید وجود دارد.

**Priority:** P1 — Required for MVP

**Dependencies:** ACP-004، ACP-007، ACP-009.

---

## ACP-051 — Implement Upstream Credential Profile API and Redacted Views

**Task Summary:** مدیریت Credential Profile بدون افشای مقدار Secret.

**Description:**

APIهای مدیریتی ایجاد کن تا Admin بتواند Credential جدید ثبت، جایگزین یا Revoke کند:

- `POST /api/v1/servers/{id}/credentials`
- `GET /api/v1/servers/{id}/credentials`
- `POST /api/v1/credentials/{id}/rotate`
- `POST /api/v1/credentials/{id}/revoke`

GET فقط Metadata مثل Name، Type، Created At، Updated At، Last Used و Status را برگرداند. مقدار Secret هرگز مجدداً قابل دریافت نباشد.

ثبت Credential باید از طریق HTTPS در Deployment واقعی انجام شود. در Local Demo هشدار روشن بده.

**Acceptance Criteria:**

- Credential قابل ثبت و Revoke است.
- API مقدار Secret را پس از ثبت برنمی‌گرداند.
- Revoke باعث می‌شود Call بعدی با آن Credential انجام نشود.
- عملیات در Audit ثبت می‌شوند.

**Priority:** P1 — Required for MVP

**Dependencies:** ACP-050، ACP-024، ACP-035.

---

## ACP-052 — Inject Upstream Credentials Only at Connector Execution Time

**Task Summary:** استفاده امن از Credential هنگام اتصال به Upstream MCP Server.

**Description:**

Credential Broker را به Upstream Adapter متصل کن. Router نباید Secret را به MCP Client یا Tool Arguments منتقل کند.

رفتار مورد انتظار:

1. پس از Allow شدن Policy، Connector Credential Profile متصل به Server را دریافت کند.
2. Secret در حافظه Decrypt شود.
3. Header یا مکانیزم Authentication مورد پشتیبانی Connector ساخته شود.
4. درخواست به Upstream ارسال شود.
5. Secret در پایان تا حد امکان از Referenceهای غیرضروری آزاد شود.
6. Headerهای حساس از Log و Exception حذف شوند.

در MVP از Bearer Header برای Demo Upstream محافظت‌شده پشتیبانی کن. Token ورودی Client را بدون Audience/Resource بررسی به Upstream Forward نکن.

**Acceptance Criteria:**

- Upstream محافظت‌شده با Credential Profile معتبر قابل فراخوانی است.
- Credential نامعتبر یا Revoked باعث عدم اتصال می‌شود.
- Secret به Agent یا MCP Client بازنمی‌گردد.
- Test با Fake Upstream وجود دارد که Header را دریافت می‌کند، اما Test Report آن را Mask می‌کند.

**Priority:** P0 — Blocker

**Dependencies:** ACP-017، ACP-050، ACP-051، ACP-041.

---

# I. Audit, Health and Observability

## ACP-053 — Record Audit Events for Every Gateway Decision and Outcome

**Task Summary:** اتصال Audit به تمام مسیرهای Gateway.

**Description:**

تمام مسیرهای زیر باید Audit تولید کنند:

- Authentication Failed.
- `tools/list` filtered/allowed.
- Tool Call Allowed.
- Tool Call Denied.
- Approval Requested.
- Approval Approved/Rejected/Expired/Consumed.
- Upstream Success/Failure/Timeout.
- Credential Revoked/Used.
- Tool Discovery/Drift.

Audit باید Reason Code، Request ID، Principal، Workspace، Tool، Decision و Outcome را ثبت کند. Raw Arguments به‌صورت پیش‌فرض ذخیره نشوند. اگر ذخیره خلاصه لازم است، Redaction و Data Minimization انجام بده.

**Acceptance Criteria:**

- هر مسیر مهم حداقل یک Event دارد.
- Deny قبل از Forward با `execution_status=not_forwarded` ثبت می‌شود.
- Outcome نهایی Call جدا از Decision اولیه قابل مشاهده است.
- تست می‌کند Secret و PII آزمایشی در Audit ظاهر نمی‌شوند.

**Priority:** P0 — Blocker

**Dependencies:** ACP-014، ACP-041، ACP-045 تا ACP-052.

---

## ACP-054 — Implement Audit Search and Filter API

**Task Summary:** فراهم‌کردن API فقط‌خواندنی برای جست‌وجوی Audit.

**Description:**

Endpoint `GET /api/v1/audit-events` بساز. فیلترهای حداقل:

- `from`, `to`.
- `principal_id`.
- `server_id`.
- `tool_name`.
- `decision`.
- `execution_status`.
- `request_id`.

Pagination و Sort بر اساس Timestamp داشته باش. محدودیت حداکثر Page Size اعمال کن. فقط Owner/Admin/Security Admin/Auditor مجاز باشند؛ Developer فقط در صورت Policy مشخص، Eventهای متعلق به خودش را ببیند.

**Acceptance Criteria:**

- فیلترها درست ترکیب می‌شوند.
- Cross-Workspace Audit قابل دسترسی نیست.
- Pagination پایدار است.
- API هیچ Secret یا Raw Token برنمی‌گرداند.
- تست Access Control و Query وجود دارد.

**Priority:** P1 — Required for MVP

**Dependencies:** ACP-014، ACP-035، ACP-053.

---

## ACP-055 — Add Base Metrics and Operational Counters

**Task Summary:** ارائه Metrics پایه برای مشاهده عملکرد و تصمیم‌های Gateway.

**Description:**

Metrics Endpoint یا Exporter سازگار با Prometheus اضافه کن. حداقل Metrics:

- تعداد درخواست‌های MCP بر اساس Method و Outcome.
- تعداد Policy Decisionها بر اساس Allow/Deny/Require Approval.
- تعداد Tool Callهای موفق و ناموفق.
- Upstream Latency Histogram.
- Policy Evaluation Duration Histogram.
- تعداد Pending Approval.
- تعداد Authentication Failure.

از Labelهای با Cardinality بالا مثل Request ID، User Email یا Tool Arguments به‌عنوان Metric Label استفاده نکن. این اطلاعات جای Audit/Trace هستند، نه Metric Label.

**Acceptance Criteria:**

- `/metrics` فقط در محیط/شبکه مجاز قابل دسترسی است.
- Metrics اصلی قابل Scrape هستند.
- تست افزایش Counter در سناریوی Allow و Deny وجود دارد.
- Secret و PII در Metric Label نیست.

**Priority:** P1 — Required for MVP

**Dependencies:** ACP-005، ACP-041، ACP-053.

---

## ACP-056 — Implement Readiness, Liveness and Dependency Health Reporting

**Task Summary:** Health Endpointهای عملیاتی قابل استفاده برای Docker و Monitoring.

**Description:**

اگر در Task ACP-023 پیاده‌سازی شده، فقط Gapها را کامل کن. Liveness نباید به اتصال همه Upstreamها وابسته باشد. Readiness باید Database و Dependencyهای حیاتی برای شروع کار را بررسی کند. OPA و Keycloak/ JWKS باید وضعیت قابل فهم داشته باشند.

برای هر Health Check Timeout کوتاه داشته باش. Health Endpoint اطلاعات Secret، Internal IP غیرضروری یا Connection String را افشا نکند.

**Acceptance Criteria:**

- Docker Healthcheckها از Endpoint مناسب استفاده می‌کنند.
- Dependency Down وضعیت درست گزارش می‌شود.
- Upstream Down به‌تنهایی باعث Restart Loop کل ACP نمی‌شود.
- Test برای Ready/Not Ready وجود دارد.

**Priority:** P1 — Required for MVP

**Dependencies:** ACP-023، ACP-038.

---

## ACP-057 — Add Safe Error Reporting and Redaction Tests

**Task Summary:** جلوگیری از نشت اطلاعات در Error Response، Log، Audit و Metrics.

**Description:**

یک مجموعه تست بساز که Secretهای ساختگی را در Authorization Header، Upstream Error، Tool Arguments و Exception Message قرار دهد و ثابت کند هیچ‌کدام در مکان‌های عمومی ظاهر نمی‌شوند.

Redaction باید حداقل این موارد را پوشش دهد:

- Bearer Token.
- API Key Patternهای رایج.
- Password/Client Secret.
- Cookie/Set-Cookie.
- Database DSN با Password.
- Credential داخل URL.

در Error Response به Client فقط Error Code و Message عمومی بده. جزئیات داخلی در Log امن با Request ID ثبت شوند.

**Acceptance Criteria:**

- تست Secret Leakage سبز است.
- Errorها Stack Trace برنمی‌گردانند.
- Request ID برای پشتیبانی در Response وجود دارد.
- هیچ Test Fixture شامل Secret واقعی نیست.

**Priority:** P0 — Blocker

**Dependencies:** ACP-005، ACP-019، ACP-050، ACP-053.

---

# J. Integration Tests, Security, Packaging and Release

## ACP-058 — Build an End-to-End Test for the Full Allowed Tool Call Path

**Task Summary:** تست کامل مسیر Initialize → Authentication → tools/list → tools/call → Upstream → Audit.

**Description:**

یک E2E Test بساز که با PostgreSQL، OPA، Keycloak و Demo MCP Server در Docker یا Test Environment واقعی اجرا شود.

سناریو:

1. Workspace و Agent Demo ایجاد شوند.
2. Demo MCP Server ثبت و Discover شود.
3. Policy برای `list_projects` Allow باشد.
4. MCP Client با Token معتبر به ACP وصل شود.
5. `tools/list` ابزار مجاز را نمایش دهد.
6. `tools/call` اجرا شود.
7. Demo Upstream واقعاً درخواست را دریافت کند.
8. Response به Client برگردد.
9. Audit Event با Outcome موفق ثبت شود.

**Acceptance Criteria:**

- Test بدون Mock کردن Policy Decision و Upstream واقعی Demo اجرا شود.
- کل مسیر با یک Command قابل اجرا باشد.
- Failure در هر Dependency Test را Fail کند، نه اینکه Skip شود.

**Priority:** P0 — Blocker

**Dependencies:** ACP-015 تا ACP-055؛ حداقل قابلیت‌های Core باید آماده باشند.

---

## ACP-059 — Build an End-to-End Test for Denied Tool Calls

**Task Summary:** اثبات اینکه Policy Deny در مسیر واقعی اجرا دور زده نمی‌شود.

**Description:**

سناریوی امنیتی بساز:

- Principal معتبر است.
- Tool `delete_project` در Policy ممنوع است.
- Client ابتدا `tools/list` می‌زند.
- سپس حتی اگر Tool را با نام مستقیم در `tools/call` فراخوانی کند، Gateway باید آن را Deny کند.

Fake Upstream باید Counter داشته باشد تا تعداد Callهای دریافتی را نشان دهد. بعد از Deny این Counter باید صفر بماند.

**Acceptance Criteria:**

- Deny Response قابل مشاهده است.
- Upstream هیچ درخواست مربوط به Tool ممنوع دریافت نمی‌کند.
- Audit Deny با Reason Code وجود دارد.
- تست با دو Principal و دو Policy متفاوت اجرا می‌شود.

**Priority:** P0 — Blocker

**Dependencies:** ACP-041، ACP-053، ACP-058.

---

## ACP-060 — Build End-to-End Approval and Replay Security Tests

**Task Summary:** تست کامل Approval Pending، Approve، Retry دقیق و جلوگیری از Replay.

**Description:**

سناریو:

1. Agent Tool دارای Require Approval را صدا می‌زند.
2. Gateway Pending می‌سازد و Upstream Call صفر است.
3. Security Admin درخواست را Approve می‌کند.
4. Agent همان Tool را با همان Arguments دوباره صدا می‌زند.
5. Gateway Approval را یک بار مصرف و Upstream را اجرا می‌کند.
6. Agent همان درخواست را بار دوم می‌فرستد؛ باید Deny شود.
7. یک Test جداگانه نشان دهد با تغییر Argument، Approval قابل استفاده نیست.
8. Expired و Rejected نیز تست شوند.

**Acceptance Criteria:**

- تمام حالات گفته‌شده تست خودکار دارند.
- هیچ درخواست قبل از Approve به Upstream نمی‌رسد.
- اجرای هم‌زمان برای مصرف یک Approval فقط یک بار موفق می‌شود.

**Priority:** P0 — Blocker

**Dependencies:** ACP-045 تا ACP-049، ACP-053.

---

## ACP-061 — Add Protocol Contract Tests Against the Pinned MCP SDK

**Task Summary:** تست سازگاری Protocol Gateway با MCP SDK و نسخه انتخاب‌شده.

**Description:**

Contract Testها باید Handshake، `tools/list`، Pagination، `tools/call`، Tool Not Found، Invalid Arguments، Notifications لازم، Streamable HTTP Headers و Error Mapping را پوشش دهند.

اگر SDK تست Conformance یا Test Server رسمی دارد، از آن استفاده کن. از ساخت تستی که فقط Implementation خود ACP را تأیید می‌کند اجتناب کن؛ حداقل یک Client مستقل/استاندارد باید به ACP متصل شود.

**Acceptance Criteria:**

- Contract Testها در CI اجرا می‌شوند.
- یک MCP Client مستقل ACP را می‌شناسد.
- رفتار Pagination و Errorها تست شده‌اند.
- نسخه SDK و نسخه Protocol در Test Report ثبت می‌شوند.

**Priority:** P1 — Required for MVP

**Dependencies:** ACP-002، ACP-018، ACP-019.

---

## ACP-062 — Add Security Regression Tests for SSRF, Origin, Tenant and Secret Leakage

**Task Summary:** ایجاد تست‌های امنیتی Regression برای مهم‌ترین Trust Boundaryهای MVP.

**Description:**

مجموعه تست مستقلی بساز که حداقل موارد زیر را پوشش دهد:

- SSRF به localhost، loopback، private IP و metadata IP.
- Redirect به Host غیرمجاز.
- Origin نامعتبر در Streamable HTTP.
- Cross-Workspace IDOR.
- Header جعلی Agent/User.
- Token با Audience اشتباه.
- Secret Leakage در Log/Trace/Error/Audit.
- Tool Call مستقیم برای Tool ممنوع.
- Schema Drift بدون افزایش خودکار Permission.
- Approval Replay و Payload Tampering.

برای هر مورد Test Name و Threat توضیح داده شود.

**Acceptance Criteria:**

- تست‌ها در CI اجرا می‌شوند.
- مورد P0 امنیتی Skip نشده است.
- نتیجه در `docs/security/mvp-security-test-report.md` ثبت می‌شود.

**Priority:** P0 — Blocker

**Dependencies:** ACP-022، ACP-032، ACP-037، ACP-047، ACP-057، ACP-059، ACP-060.

---

## ACP-063 — Create Docker Compose for a Complete Local MVP Demo

**Task Summary:** بسته‌بندی سرویس‌ها برای اجرای دمو با یک دستور.

**Description:**

Docker Compose باید حداقل این سرویس‌ها را اجرا کند:

- ACP API/Gateway.
- PostgreSQL.
- OPA.
- Keycloak.
- Demo MCP Server.

اگر Metrics در MVP فعال است، Prometheus اختیاری می‌تواند Profile جداگانه باشد. سرویس‌های غیرضروری را به Compose اصلی تحمیل نکن.

الزامات:

1. Healthcheck مناسب برای هر سرویس.
2. Volume پایدار برای PostgreSQL.
3. Network داخلی مشخص.
4. Environment Variable از `.env`؛ هیچ Secret واقعی در Compose Commit نشود.
5. Demo Seed/Bootstrap تکرارپذیر.
6. Startup Order با `depends_on` و Health Condition یا Logic Retry در برنامه.
7. Container با Non-root User در صورت سازگاری اجرا شود.
8. Tagهای Image مشخص و قابل بازتولید باشند؛ از `latest` برای Release استفاده نکن.

**Acceptance Criteria:**

- `docker compose up --build` محیط Demo را بالا می‌آورد.
- Healthcheckها سبز می‌شوند.
- Client Demo سناریوی Allow و Deny را اجرا می‌کند.
- Restart باعث Duplicate Seedهای ناخواسته نمی‌شود.
- دستورات Stop و Clean Up مستند هستند.

**Priority:** P0 — Blocker

**Dependencies:** ACP-004، ACP-006، ACP-015، ACP-018، ACP-031، ACP-038.

---

## ACP-064 — Add CI Pipeline for Lint, Type Check, Unit, Integration and Build

**Task Summary:** ساخت GitHub Actions Workflow برای کیفیت و Regression Gate.

**Description:**

برای Pull Request حداقل این مراحل را اجرا کن:

1. Dependency Installation از Lockfile.
2. Formatter Check.
3. Linter.
4. Static Type Check.
5. Unit Tests.
6. Integration Tests با PostgreSQL/OPA/Keycloak/Demo Server در صورت امکان.
7. Build Backend Image.
8. Scan پایه Secret/Dependency.

اگر Integration Environment طولانی است، آن را به Job جدا تقسیم کن ولی Required Status آن را برای Merge مشخص کن.

از چاپ Environment Variables حساس در CI جلوگیری کن. Test Secretها ساختگی باشند.

**Acceptance Criteria:**

- Workflow روی Pull Request اجرا می‌شود.
- شکست Test یا Lint وضعیت CI را Fail می‌کند.
- Lockfile رعایت می‌شود.
- حداقل یک Branch Protection Rule برای Required Checks مستند شده است.

**Priority:** P1 — Required for MVP

**Dependencies:** ACP-001، ACP-063 و Test Taskهای مربوط.

---

## ACP-065 — Write MVP Quick Start, Security Model and Demo Runbook

**Task Summary:** مستندات لازم برای نصب، اتصال Client و اجرای Demo را کامل کن.

**Description:**

مستندات را برای یک توسعه‌دهنده خارجی بنویس که Repository را نمی‌شناسد. حداقل این فایل‌ها را بساز یا تکمیل کن:

- `README.md`: معرفی، Scope، Status، Quick Links.
- `docs/quickstart.md`: نصب Docker و اجرای Demo از صفر.
- `docs/architecture/overview.md`: Data Plane/Control Plane و Componentها.
- `docs/security/security-model.md`: Threat Boundary، Identity، Policy، Credential و محدودیت‌ها.
- `docs/guides/add-mcp-server.md`: ثبت Upstream Server.
- `docs/guides/connect-mcp-client.md`: اتصال Client به ACP.
- `docs/guides/write-policy.md`: ساخت و انتشار Policy.
- `docs/guides/approval-flow.md`: Approval و Retry دقیق.
- `docs/operations/configuration.md`: Environment Variables.
- `docs/operations/troubleshooting.md`: خطاهای متداول.

در مستندات روشن بگو که ACP فقط ترافیکی را کنترل می‌کند که از Gateway عبور می‌کند. کنترل Toolهای Local IDE یا مسیرهای خارج از Gateway در MVP تضمین نمی‌شود.

**Acceptance Criteria:**

- فردی غیر از توسعه‌دهنده بتواند Quick Start را اجرا کند.
- همه دستورها در محیط تمیز تست شده‌اند.
- مثال‌ها Secret واقعی ندارند.
- Limitationها و Supported Features صادقانه فهرست شده‌اند.

**Priority:** P1 — Required for MVP

**Dependencies:** ACP-058 تا ACP-064.

---

# K. Optional Minimal Admin Demo UI

> این گروه برای اثبات تجربه محصول مفید است، اما هسته امنیتی نباید به آن وابسته باشد. اگر زمان محدود است، ابتدا API و Acceptanceهای P0/P1 را کامل کن.

## ACP-066 — Create Minimal Admin Web App Shell and Authentication

**Task Summary:** ساخت پوسته حداقلی Next.js برای ورود مدیر و نمایش محیط Demo.

**Description:**

اگر Frontend در Repository وجود دارد، همان را توسعه بده؛ پروژه جدید نساز. یک Layout ساده و قابل دسترس بساز که Login با OIDC/Keycloak را انجام دهد یا در حالت Demo از جریان موجود Repository استفاده کند.

الزامات:

- Session/Token امن طبق الگوی مناسب Framework؛ Token را در Local Storage به‌صورت پیش‌فرض ذخیره نکن.
- Route Protection برای صفحات مدیریتی.
- نمایش Workspace و User جاری.
- Error State و Loading State.
- API Client مرکزی با Handling برای 401/403.
- UI ساده، بدون Dashboard پیچیده و نمودارهای نمایشی غیرواقعی.

**Acceptance Criteria:**

- مدیر Demo وارد می‌شود.
- User غیرمجاز به صفحات مدیریتی دسترسی نمی‌گیرد.
- UI Token را در Log یا URL قرار نمی‌دهد.
- Build و Lint Frontend سبز هستند.

**Priority:** P2 — MVP Demo Polish

**Dependencies:** ACP-031 تا ACP-035.

---

## ACP-067 — Build Minimal MCP Server and Tool Catalog Screens

**Task Summary:** نمایش Serverهای ثبت‌شده و Tool Catalog در پنل.

**Description:**

دو صفحه بساز:

1. Servers: نام، Endpoint Masked، Transport، Status، Last Discovery.
2. Tool Catalog: نام Tool، Title/Description، Server، Classification Status، Risk Attributes، Fingerprint کوتاه و Last Discovered.

در جزئیات Tool، Input Schema را با JSON Viewer خوانا نمایش بده؛ Schema را به‌عنوان توضیح فنی نشان بده، نه اثبات رفتار واقعی Tool.

Actionها:

- مشاهده Server.
- Trigger Discovery در صورت وجود API.
- مشاهده Tools.
- مشاهده Drift Event.

**Acceptance Criteria:**

- UI داده واقعی Backend را نمایش می‌دهد.
- داده Mock در Production/Preview نمایش داده نمی‌شود.
- Workspace Scope در Backend رعایت می‌شود.
- Error و Empty State وجود دارد.

**Priority:** P2 — MVP Demo Polish

**Dependencies:** ACP-024 تا ACP-030، ACP-066.

---

## ACP-068 — Build Minimal Policy and Approval Screens

**Task Summary:** نمایش Policy و مدیریت درخواست‌های تأیید در پنل.

**Description:**

برای MVP یک رابط ساده ایجاد کن:

- فهرست Policyها و Status/Version.
- جزئیات Policy و Rego Source به‌صورت Read-only یا Editor ساده با Validation.
- دکمه Publish فقط برای Role مجاز.
- فهرست Approvalهای Pending.
- صفحه جزئیات Approval شامل Principal، Tool، Payload Hash، Safe Arguments Summary و Expiry.
- دکمه Approve/Reject با Confirmation.

اگر ویرایشگر Rego باعث Scope Creep شد، Policy را از فایل/Seed/API مدیریت کن و UI را فقط Read-only نگه دار. امنیت Publish باید در Backend اعمال شود.

**Acceptance Criteria:**

- Admin Policy را مشاهده می‌کند.
- Security Admin درخواست Approval را بررسی و تصمیم می‌گیرد.
- Developer نمی‌تواند Approve کند، مگر Role صریحاً اجازه دهد.
- UI هیچ Payload حساس خامی را بدون Redaction نشان نمی‌دهد.

**Priority:** P2 — MVP Demo Polish

**Dependencies:** ACP-040، ACP-045 تا ACP-049، ACP-066.

---

## ACP-069 — Build Minimal Audit Activity Screen

**Task Summary:** نمایش Audit Eventها با Filterهای پایه.

**Description:**

یک صفحه Activity بساز که از Audit API واقعی استفاده کند. ستون‌های پیشنهادی:

- Timestamp.
- Principal.
- Server / Tool.
- Decision.
- Execution Status.
- Reason Code.
- Request ID.

Filterهای پایه: Date Range، Principal، Tool، Decision. جزئیات Event در Drawer/Details View باز شود. Raw Secret/Token یا Arguments حساس نمایش داده نشوند.

**Acceptance Criteria:**

- صفحه از Backend واقعی داده می‌گیرد.
- Pagination و Filter کار می‌کنند.
- نقش Auditor فقط Read دارد.
- هیچ Mock Event در محیط عادی نشان داده نمی‌شود.

**Priority:** P2 — MVP Demo Polish

**Dependencies:** ACP-054، ACP-066.

---

# 1. MVP Release Gate — چک‌لیست نهایی

تا وقتی تمام موارد P0 و P1 زیر Done نشده‌اند، نسخه را `0.1.0` اعلام نکن.

## 1.1 Functional Gate

- [ ] ACP می‌تواند به‌عنوان MCP Server از یک Client مستقل درخواست بگیرد.
- [ ] ACP می‌تواند به یک Upstream MCP Server با Streamable HTTP وصل شود.
- [ ] `initialize`، `tools/list` و `tools/call` کار می‌کنند.
- [ ] Discovery تمام صفحات Tool List را دریافت می‌کند.
- [ ] Tool Catalog، Schema و Fingerprint را ذخیره می‌کند.
- [ ] Tool Namespace Collision مدیریت می‌شود.
- [ ] ابزارهای Deny شده در `tools/list` پنهان می‌شوند.
- [ ] فراخوانی مستقیم Tool ممنوع در `tools/call` نیز رد می‌شود.
- [ ] Tool مجاز واقعاً به Upstream می‌رسد و نتیجه برمی‌گردد.

## 1.2 Identity & Security Gate

- [ ] Keycloak در Demo قابل اجراست.
- [ ] JWT Signature، Issuer، Audience و Expiry بررسی می‌شوند.
- [ ] Agent و User با هویت معتبر Mapping می‌شوند.
- [ ] Workspace Isolation تست شده است.
- [ ] Admin Endpointها Role Check دارند.
- [ ] SSRF و Origin Validation تست شده‌اند.
- [ ] Secret در Log/Response/Audit افشا نمی‌شود.
- [ ] ابزار Unclassified به‌صورت پیش‌فرض مجاز نیست.

## 1.3 Policy & Approval Gate

- [ ] OPA Decision واقعی در مسیر Tool Call اجرا می‌شود.
- [ ] Default Deny فعال است.
- [ ] OPA Unavailable باعث Allow ناخواسته نمی‌شود.
- [ ] Approval قبل از اجرای Tool ساخته می‌شود و Upstream در Pending فراخوانی نمی‌شود.
- [ ] فقط Role مجاز Approve/Reject می‌کند.
- [ ] Approval به Payload Hash و Principal متصل است.
- [ ] Approval یک‌بارمصرف است و Replay رد می‌شود.

## 1.4 Audit & Operations Gate

- [ ] Allow، Deny، Approval و Outcome ثبت می‌شوند.
- [ ] Audit Query با Workspace Scope کار می‌کند.
- [ ] Health و Readiness درست هستند.
- [ ] Metrics پایه قابل Scrape هستند.
- [ ] Request ID در تمام مسیر قابل پیگیری است.
- [ ] Timeout و Payload Limit فعال‌اند.

## 1.5 Release Gate

- [ ] Demo با Docker Compose اجرا می‌شود.
- [ ] E2E Allow Test سبز است.
- [ ] E2E Deny Test سبز است.
- [ ] Approval/Replay Test سبز است.
- [ ] Protocol Contract Test سبز است.
- [ ] Security Regression Test سبز است.
- [ ] CI روی Pull Request اجرا می‌شود.
- [ ] Quick Start توسط شخص دیگری تست شده است.
- [ ] Known Limitations مستند شده‌اند.

---

# 2. سناریوی Demo رسمی MVP

سناریوی اصلی Demo باید کوتاه، تکرارپذیر و قابل فهم باشد.

## داده Demo

یک Demo Workspace به نام `Northstar GmbH` داشته باش:

| Principal | Role | Server | Tool | Policy |
|---|---|---|---|---|
| `agent_developer` | Developer | demo | `list_projects` | Allow |
| `agent_developer` | Developer | demo | `create_issue` | Allow |
| `agent_developer` | Developer | demo | `delete_project` | Deny |
| `agent_support` | Support | demo | `list_issues` | Allow |
| `agent_support` | Support | demo | `create_issue` | Require Approval |

## سناریوی اجرا

1. مدیر Docker Compose را اجرا می‌کند.
2. وارد Keycloak می‌شود و Token Demo Agent را می‌گیرد.
3. Demo MCP Server به ACP ثبت و Discovery می‌شود.
4. مدیر Catalog را مشاهده می‌کند.
5. Developer Client به ACP متصل می‌شود.
6. `list_projects` را اجرا می‌کند و پاسخ موفق می‌گیرد.
7. `delete_project` را مستقیماً فراخوانی می‌کند و Deny می‌شود.
8. Support Agent `create_issue` را فراخوانی می‌کند و Approval Pending می‌گیرد.
9. مدیر در API یا UI درخواست را Approve می‌کند.
10. Agent همان درخواست را با همان Arguments دوباره می‌فرستد و موفق می‌شود.
11. مدیر Audit را بررسی می‌کند و تمام تصمیم‌ها را می‌بیند.

این Demo باید ثابت کند محصول واقعاً در مسیر اجرا قرار دارد؛ فقط UI یا Policy نمایشی نباشد.

---

# 3. خروجی مورد انتظار از Gemini برای هر Task

پس از اجرای هر Task، از Gemini بخواه این قالب را برگرداند:

```text
Task ID: ACP-XXX
Status: Done / Partially Done / Blocked / Already Implemented & Verified

Summary:
- What changed and why.

Files Changed:
- path/to/file — reason

Implementation Notes:
- Key design or behavior decisions.

Tests Executed:
- command — result

Acceptance Criteria:
- [x] criterion 1
- [x] criterion 2
- [ ] criterion 3 — explain why not completed

Security Notes:
- Relevant security checks and remaining risks.

Manual Verification:
- Exact steps to verify the feature.

Follow-up Tasks:
- Any newly discovered dependency or issue. Do not implement out-of-scope work automatically.
```

---

# 4. چیزهایی که نباید به MVP اضافه شوند

برای حفظ تمرکز، اگر Gemini پیشنهاد افزودن موارد زیر را داد، آن‌ها را به Backlog نسخه‌های بعد منتقل کن مگر اینکه مانع اجرای یکی از Acceptance Criteriaهای MVP باشند:

- Agent Chat UI.
- LLM-based automatic Allow/Deny.
- Prompt Injection Detection مبتنی بر مدل زبانی به‌عنوان Security Boundary.
- DLP پیشرفته و PII Classification عمومی.
- Resource/Prompt Proxy کامل.
- Stdio Gateway و Process Supervisor عمومی.
- OAuth Token Exchange و Delegated Authorization کامل.
- Vault/KMS Integration چندگانه.
- Kubernetes Operator و Multi-region.
- Billing، Subscription و SaaS Multi-tenancy.
- Agent Runtime Adapter برای همه Frameworkها.
- ACS/Agent Hooks Integration.
- SIEMهای متعدد و Compliance Dashboard کامل.
- گرافیک و داشبوردهای تزئینی بدون نیاز کاربر.

---

# 5. منابع مرجع رسمی و فنی

این منابع را قبل از تغییر نسخه MCP، SDK، OIDC یا OPA دوباره بررسی کن:

1. MCP Specification: https://modelcontextprotocol.io/specification/
2. MCP Transports: https://modelcontextprotocol.io/specification/2025-11-25/basic/transports
3. MCP Tools: https://modelcontextprotocol.io/specification/2025-11-25/server/tools
4. MCP Authorization: https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization
5. MCP Python SDK: https://github.com/modelcontextprotocol/python-sdk
6. FastAPI Documentation: https://fastapi.tiangolo.com/
7. SQLAlchemy 2 Documentation: https://docs.sqlalchemy.org/en/20/
8. Alembic Documentation: https://alembic.sqlalchemy.org/
9. Open Policy Agent: https://www.openpolicyagent.org/docs/latest/
10. Keycloak Documentation: https://www.keycloak.org/documentation
11. OpenTelemetry Python: https://opentelemetry.io/docs/languages/python/
12. OWASP API Security: https://owasp.org/www-project-api-security/
13. Microsoft MCP Security Gateway Draft (فقط به‌عنوان Reference برای مقایسه و Threat Checklist؛ نه استاندارد رسمی MCP): https://github.com/microsoft/agent-governance-toolkit/blob/main/docs/specs/MCP-SECURITY-GATEWAY-1.0.md

---

# 6. ترتیب پیشنهادی شروع کار

اگر الان می‌خواهی کار را با Gemini Flash شروع کنی، این ترتیب را حفظ کن:

1. ACP-001 — اول وضعیت کد فعلی را بشناس.
2. ACP-002 و ACP-003 — Protocol و Contractها را تثبیت کن.
3. ACP-004 تا ACP-014 — Foundation و مدل‌های داده.
4. ACP-015 تا ACP-023 — یک Gateway واقعی و قابل اتصال بساز.
5. ACP-024 تا ACP-030 — Registry و Tool Catalog.
6. ACP-031 تا ACP-037 — هویت و Tenant Isolation.
7. ACP-038 تا ACP-044 — Policy و Enforcement.
8. ACP-045 تا ACP-049 — Approval.
9. ACP-050 تا ACP-057 — Credential، Audit و Operational Controls.
10. ACP-058 تا ACP-065 — تست، امنیت، Docker و انتشار.
11. ACP-066 تا ACP-069 — فقط در صورت باقی‌ماندن زمان برای Demo UI.

**قاعده نهایی:** هیچ Taskی را صرفاً به این دلیل Done نکن که Gemini کد تولید کرده است. Task وقتی Done است که کد در مسیر واقعی اجرا شود، Acceptance Criteria آن تست شده باشد و محدودیت‌های باقی‌مانده مستند شده باشند.
