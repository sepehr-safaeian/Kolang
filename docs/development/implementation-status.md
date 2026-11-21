# نقشه وضعیت پیاده‌سازی و حسابرسی مخزن (Repository Audit & Implementation Status)

**شناسه سند:** `DOC-ACP-001`  
**تسک مرجع:** `ACP-001 — Audit the Existing Repository and Map the Current Implementation`  
**تاریخ گزارش:** ۲۱ نوامبر ۲۰۲۶ (21 November 2026)  
**نسخه پروژه:** `0.1.0-alpha`  
**هدف:** حسابرسی جامع و دقیق وضعیت فعلی مخزن Kolang ACP پیش از اعمال هرگونه تغییر کد، جهت جلوگیری از بازنویسی کدهای موجود و هدایت دقیق تسک‌های بعدی MVP Backlog.

---

## ۱. خلاصه اجرایی (Executive Summary)

مخزن **Kolang** به عنوان یک **Agent Control Plane (ACP)** و **MCP Gateway** سازمانی با معماری **Modular Monolith** طراحی شده است. بررسی عمیق مخزن نشان می‌دهد که پروژه در فاز استقرار پایه معماری (Foundation / Skeleton) قرار دارد:

1. **پایه ساختار و قراردادهای دامنه (Domain Baseline):** مدل‌های پایه دامنه به صورت شمای Pydantic v2 در بسته‌های `acp_core` (شامل پروتکل داخلی، هویت، سیاست‌گذاری، تأییدیه‌ها و رویدادهای بازرسی) پیاده‌سازی شده و تست‌های واحد آن‌ها با موفقیت کامل پاس می‌شوند.
2. **قابلیت ردیابی و لاگینگ (Telemetry & Context):** میان‌افزار ردیابی کانتکست (`RequestContextMiddleware`) شناسه درخواست (`request_id`) و شناسه همبستگی (`correlation_id`) را در هدرهای HTTP و لاگ‌های ساختاریافته `structlog` ثبت می‌کند.
3. **نبود MCP SDK رسمی در وابستگی‌ها:** پکیج رسمی `mcp` در فایل‌های `pyproject.toml` و `uv.lock` نصب نشده است. کدهای فعلی صرفاً شمای تجریدی داخلی و یک سرور/کلاینت ماک نمایشی دارند.
4. **عدم اتصال و مدل‌های دیتابیس (Persistence Gap):** هیچ مدل دیتابیس SQLAlchemy ORM در مخزن تعریف نشده است؛ دایرکتوری `migrations/versions/` خالی است و تست سلامت `/readyz` برای پایگاه داده دارای کامنت `TODO` بوده و مقدار ساختگی برمی‌گرداند.
5. **عدم پیاده‌سازی موتورهای اجرایی:** اتصال واقعی به OPA (ارزیابی سیاست‌ها)، اعتبارسنجی JWT توکن‌های Keycloak، ماژول رمزنگاری و تزریق کلیدهای محرمانه، و مسیر واقعی فوروارد ابزارها در Gateway هنوز پیاده‌سازی نشده‌اند.
6. **فرانت‌اند:** پوشه `apps/web` خالی بوده و هیچ وابستگی یا پروژه اسکلتی برای Next.js وجود ندارد.

---

## ۲. ساختار واقعی مخزن (Actual Repository Structure)

ساختار واقعی و فعال فایل‌ها و پوشه‌های مخزن به شرح زیر است:

```text
Kolang/
├── .agents/                               # قوانین و دستورالعمل‌های محلی Agent
│   └── rules/                             # ماژول‌های قوانین ۱۱ گانه Kolang
├── .github/                               # پیکربندی گیت‌هاب و خط لوله CI/CD
│   ├── ISSUE_TEMPLATE/                    # الگوهای ایشو (Bug / Feature)
│   ├── workflows/
│   │   ├── ci.yml                         # پایپ‌لاین آزمون، لینت و بیلد داکر
│   │   └── release.yml                    # پایپ‌لاین انتشار ریلیز
│   └── pull_request_template.md           # الگوی PR
├── apps/                                  # برنامه‌های اجرایی (Applications)
│   ├── api/                               # سرویس اصلی FastAPI (Backend Gateway)
│   │   └── app/
│   │       ├── middleware/
│   │       │   └── context.py             # میان‌افزار تزریق Request-ID و Correlation-ID
│   │       ├── routers/
│   │       │   └── health.py              # اندپوینت‌های /healthz و /readyz
│   │       ├── __init__.py
│   │       └── main.py                    # نقطه ورود اصلی اپلیکیشن FastAPI
│   └── web/                               # پوشه رزرو شده برای داشبورد Next.js (در حال حاضر خالی)
├── deploy/                                # فایل‌های استقرار و محیط محلی
│   ├── grafana/provisioning/              # تنظیمات دیتاسورس پرومتئوس در گرافانا
│   ├── keycloak/
│   │   └── kolang-realm.json              # پیکربندی Realm تست Keycloak با نقش‌ها و کلاینت‌ها
│   ├── opa/
│   │   └── kolang/
│   │       └── authz.rego                 # سیاست پایه مجوزدهی در OPA
│   ├── prometheus/
│   │   └── prometheus.yml                 # پیکربندی اسکرپ متریک‌ها در پرومتئوس
│   ├── docker-compose.yml                 # کامپوز توسعه (Postgres, Keycloak, OPA, Redis, Prometheus, Grafana, API)
│   └── Dockerfile                         # بیلد چندمرحله‌ای (Multi-Stage) پایتون ۳.۱۱
├── docs/                                  # مستندات معماری و امنیت
│   ├── architecture/
│   │   └── README.md                      # مستند معماری Modular Monolith و اصول سیستم
│   ├── security/
│   │   └── README.md                      # مستند معماری امنیت Zero-Trust
│   ├── operations/                        # خالی (جهت راهنماهای عملیاتی آینده)
│   ├── product/                           # خالی
│   └── research/                          # خالی
├── examples/                              # نمونه‌ها و ماک‌های نمایشی
│   ├── demo-agent-client/
│   │   └── client.py                      # کلاینت دمو برای ارسال درخواست به Gateway
│   ├── demo-mcp-server/
│   │   └── server.py                      # ماک سرور ابزار MCP در حافظه
│   └── policies/
│       └── default-policy.rego            # نمونه سیاست OPA Rego
├── migrations/                            # تنظیمات مایگریشن Alembic
│   ├── versions/                          # خالی (هیچ فایل بازنگری مایگریشن هنوز ایجاد نشده است)
│   ├── env.py                             # پیکربندی اتصال آسنکرون به دیتابیس
│   └── script.py.mako                     # قالب اسکریپت مایگریشن
├── packages/                              # پکیج‌های دامنه هسته (Modular Monolith)
│   └── acp_core/
│       ├── approvals/
│       │   ├── __init__.py
│       │   └── models.py                  # ماشین حالت تأییدیه‌ها و مدل‌های داده‌ای Pydantic
│       ├── audit/
│       │   ├── __init__.py
│       │   └── models.py                  # مدل‌های رویداد بازرسی (AuditEvent) و پروتکل AuditSink
│       ├── common/
│       │   ├── __init__.py
│       │   ├── context.py                 # متغیرهای کانتکست (contextvars) درخواست
│       │   ├── errors.py                  # سلسله مراتب خطاهای KolangError و ErrorResponse
│       │   ├── settings.py                # تنظیمات برنامه بر پایه Pydantic Settings
│       │   └── types.py                   # NewTypeها و شمارنده‌های دامنه (PrincipalKind و ...)
│       ├── credentials/
│       │   └── __init__.py                # رابط مدیریت کلیدهای محرمانه (فقط داک استرینگ)
│       ├── gateway/
│       │   ├── __init__.py
│       │   └── interfaces.py              # اینترفیس‌های تجریدی Protocol (DownstreamHandler, UpstreamConnector و ...)
│       ├── identity/
│       │   ├── __init__.py
│       │   └── models.py                  # مدل‌های اعتبارسنجی توکن، Principal و کانتکست احراز هویت
│       ├── policy/
│       │   ├── __init__.py
│       │   └── models.py                  # مدل‌های سیاست‌گذاری، ورودی ارزیابی و خروجی تصمیم OPA
│       ├── protocol/
│       │   ├── __init__.py
│       │   └── models.py                  # مدل‌های پیام‌های داخلی ابزارها و دیسکریپتور سرورها
│       ├── registry/
│       │   └── __init__.py                # رابط رجیستری ابزارها و سرورها (فقط داک استرینگ)
│       ├── telemetry/
│       │   ├── __init__.py
│       │   └── setup.py                   # پیکربندی structlog و OpenTelemetry Tracer
│       └── __init__.py
├── scripts/
│   └── generate_key.py                    # اسکریپت تولید کلید رمزنگاری ۲۵۶ بیتی Fernet
├── tests/                                 # سوئیت تست‌های خودکار
│   ├── integration/
│   │   ├── __init__.py
│   │   └── test_health.py                 # تست‌های اندپوینت‌های /healthz و /readyz و ردیابی هدرها
│   ├── unit/
│   │   ├── __init__.py
│   │   ├── test_common.py                 # تست‌های کانتکست، انواع داده و سلسله‌مراتب خطاها
│   │   ├── test_domain_models.py          # تست مدل‌های پروتکل، هویت، ماشین حالت تأیید و بازرسی
│   │   └── test_policy_models.py          # تست مدل‌های تصمیم‌گیری و قوانین سیاست‌گذاری
│   ├── __init__.py
│   └── conftest.py                        # فیکسچرهای تست آسنکرون و کلاینت آزمایشی
├── .dockerignore
├── .editorconfig
├── .env.example                           # متغیرهای محیطی نمونه
├── .gitignore
├── .pre-commit-config.yaml                # هوک‌های گیت (Ruff, Mypy, Bandit)
├── AGENTS.md                              # قوانین عملیاتی Agentها در مخزن
├── AGENT_HANDOFF_PROMPT.md                # سند راهنمای تحویل کار میان Agentها
├── alembic.ini                            # فایل پیکربندی Alembic
├── CODE_OF_CONDUCT.md
├── CONTRIBUTING.md
├── GEMINI.md                              # فرامین حاکمیتی ۱۱ گانه Kolang
├── Kolang-Logo.svg
├── kolang.css                             # توکن‌های استایل دیزاین سیستم
├── LICENSE                                # لایسنس آپاچی ۲.۰
├── Makefile                               # دستورات اتوماسیون بیلد، تست و اجرای پروژه
├── MASTER_DESIGN_SYSTEM_FA.md             # سند مرجع سیستم دیزاین Kolang
├── pyproject.toml                         # پیکربندی وابستگی‌های پایتون و ابزارهای لینت و تست
├── README.md                              # معرفی و راهنمای پروژه
├── SECURITY.md                            # خط‌مشی گزارش آسیب‌پذیری امنیتی
├── tokens.json                            # توکن‌های دیزاین به صورت JSON
├── uv.lock                                # لاگ‌فایل قطعی پکیج‌های پایتون
└── agent-control-plane-mvp-backlog.md      # سند اصلی نیازمندی‌ها و بک‌لاگ تسک‌های MVP (شامل ۶۹ تسک)
```

---

## ۳. پشته فنی و وابستگی‌ها (Tech Stack & Dependencies)

### ۳.۱ زبان و فریم‌ورک‌های اصلی
* **پایتون:** نسخه حداقل `>=3.11` بر اساس `pyproject.toml`؛ محیط فعال مجازی محلی روی نسخه `3.12.13` اجرا می‌شود.
* **فریم‌ورک وب:** `FastAPI >=0.115` با وب‌سرور آسنکرون `Uvicorn[standard] >=0.30`.
* **مدل‌سازی و تنظیمات:** `Pydantic >=2.9` و `Pydantic-settings >=2.5`.
* **دیتابیس و ORM:** `SQLAlchemy[asyncio] >=2.0` با درایور آسنکرون `asyncpg >=0.30` و `Alembic >=1.14`.
* **کلاینت شبکه:** `HTTPX >=0.27`.
* **تله‌متری و مشاهده‌پذیری:** `OpenTelemetry API/SDK/OTLP >=1.28`، `structlog >=24.4`.
* **امنیت و کریپتوگرافی:** `python-jose[cryptography] >=3.3`، `cryptography >=43.0`.
* **فرانت‌اند:** هیچ فریم‌ورکی (Next.js/React) در حال حاضر نصب نشده است (`apps/web` خالی است).

### ۳.۲ مدیریت بسته‌ها و ابزارهای کیفیت کد
* **مدیر بسته:** `uv` با فایل قفل `uv.lock` و بیلدسیستم `hatchling`.
* **آزمون:** `pytest >=8.3`، `pytest-asyncio >=0.24`، `pytest-cov >=5.0`، `respx >=0.21`.
* **لینت و فرمت:** `ruff >=0.8` (قوانین سخت‌گیرانه `E, F, W, I, N, UP, S, B, A, C4, DTZ, T20, PT, SIM, TID, RUF`).
* **بررسی نوع (Type Check):** `mypy >=1.13` با تنظیم `strict = true` و پلاگین `pydantic.mypy`.
* **اسکن امنیتی:** `bandit[toml] >=1.8`.
* **هوک‌های گیت:** `pre-commit >=4.0`.

---

## ۴. نقاط ورود، دستورات اجرا و تست (Entry Points & Execution Commands)

### ۴.۱ نقاط ورود (Entry Points)
* **Backend:** ماژول `apps.api.app.main` شیء اصلی `app = create_app()` را تولید می‌کند.
* **Frontend:** در حال حاضر تعریف نشده است (Missing).

### ۴.۲ دستورات واقعی اجرای محیط توسعه (Development Execution)

| عملیات | دستور مستقیم با uv / venv | دستور معادل در Makefile |
|---|---|---|
| **اجرای سرور Backend** | `.\.venv\Scripts\uvicorn.exe apps.api.app.main:app --reload --host 0.0.0.0 --port 8000` یا `uv run uvicorn apps.api.app.main:app --reload` | `make dev` |
| **راه‌اندازی زیرساخت با Docker** | `docker compose -f deploy/docker-compose.yml up -d --build` | `make up` |
| **توقف زیرساخت Docker** | `docker compose -f deploy/docker-compose.yml down` | `make down` |
| **اعمال مایگریشن‌ها** | `.\.venv\Scripts\alembic.exe upgrade head` یا `uv run alembic upgrade head` | `make migrate` |
| **ایجاد مایگریشن جدید** | `.\.venv\Scripts\alembic.exe revision --autogenerate -m "message"` | `make migrate-new` |

### ۴.۳ دستورات واقعی تست، لینت و امنیت (Testing & QA)

تمامی دستورات زیر در محیط محلی ویندوز با موفقیت اجرا و راستی‌آزمایی شدند:

```powershell
# اجرای تست‌های واحد و یکپارچگی با گزارش کامل
.\.venv\Scripts\pytest.exe -v

# اجرای تست‌ها به همراه پوشش کد (Coverage Report)
.\.venv\Scripts\pytest.exe --cov=packages/acp_core --cov-report=term-missing

# اجرای لینتر ruff
.\.venv\Scripts\ruff.exe check .

# اعتبارسنجی فرمت کد با ruff
.\.venv\Scripts\ruff.exe format --check .

# بررسی جامع نوع داده با mypy (Strict Mode)
.\.venv\Scripts\mypy.exe apps packages

# اسکن آسیب‌پذیری‌های امنیتی با bandit
.\.venv\Scripts\bandit.exe -r packages/ -c pyproject.toml
```

**وضعیت آخرین اجرای محلی:**
* تست‌های سوئیت: **۱۶ تست از ۱۶ تست پاس شدند** در ۰.۱۰ ثانیه.
* پوشش کد هسته (`packages/acp_core`): **۹۱.۱۱٪** (حداقل پوشش تعیین‌شده در کانفیگ: ۸۰.۰٪).
* لینتر Ruff: بدون هیچ‌گونه خطا یا هشدار.
* تایپ‌چکر Mypy: بدون خطا در ۳۱ فایل منبع.
* اسکن امنیتی Bandit: بدون آسیب‌پذیری (۰ خطا).

---

## ۵. تحلیل وضعیت پیاده‌سازی حوزه‌های مختلف (Domain Status Breakdown)

طبق معیارهای خواسته شده، وضعیت هر حوزه با یکی از این برچسب‌ها مشخص شده است:
* `Implemented & Tested`: کاملاً پیاده‌سازی شده و تست معتبر دارد.
* `Implemented but Untested`: پیاده‌سازی شده ولی فاقد پوشش تست کافی است.
* `Partially Implemented`: بخش‌هایی پیاده‌سازی شده اما ناقص یا انتزاعی است.
* `Missing`: هنوز پیاده‌سازی نشده است.
* `Blocked`: به دلیل وابستگی مسدود است.

| حوزه / دامنه | وضعیت | توضیحات و وضعیت فعلی در کد |
|---|---|---|
| **مدل‌های پیام داخلی و پروتکل (Internal Protocol Models)** | `Implemented & Tested` | مدل‌های `ToolCallRequest`، `ToolCallResponse`، `ToolDescriptor`، `ServerDescriptor` در `acp_core.protocol.models` با تست‌های کامل در `test_domain_models.py`. |
| **میان‌افزار کانتکست و ردیابی (Request Context & Middleware)** | `Implemented & Tested` | تولید و استخراج `X-Request-ID` و `X-Correlation-ID`، اتصال به `structlog.contextvars` و هدرهای پاسخ در `apps.api.app.middleware.context` با تست در `test_health.py` و `test_common.py`. |
| **سلسله‌مراتب خطاها (Error Hierarchy)** | `Implemented & Tested` | کلاس پایه `KolangError` و خطاهای فرعی با کدهای ماشین و استاتوس HTTP در `acp_core.common.errors` با تست در `test_common.py`. |
| **مدل‌های داده‌ای هویت (Identity Domain Models)** | `Implemented & Tested` | مدل‌های `Principal`، `TokenClaims`، `AuthContext` در `acp_core.identity.models` با تست در `test_domain_models.py`. |
| **ماشین حالت تأییدیه‌ها (Approval State Machine)** | `Implemented & Tested` | مدل‌های `ApprovalStatus`، `ApprovalRequest`، جدول انتقالات مجاز `can_transition` در `acp_core.approvals.models` با تست در `test_domain_models.py`. |
| **مدل‌های سیاست‌گذاری (Policy Domain Models)** | `Implemented & Tested` | مدل‌های `PolicyEffect`، `PolicyCondition`، `PolicyDecision`، `PolicyRule`، `PolicyEvaluationInput` در `acp_core.policy.models` با تست در `test_policy_models.py`. |
| **مدل‌های رویداد بازرسی (Audit Models)** | `Implemented & Tested` | انواع رویداد `AuditEventType`، مدل `AuditEvent` و پروتکل `AuditSink` در `acp_core.audit.models` با تست در `test_domain_models.py`. |
| **تنظیمات برنامه (Application Settings)** | `Implemented & Tested` | بارگذاری از متغیرهای محیطی و `.env` با اعتبارسنجی در `acp_core.common.settings`. |
| **تله‌متری و لاگینگ ساختاریافته (Telemetry & Tracing)** | `Partially Implemented` | متدهای `setup_structlog` و `setup_telemetry` با خروجی OTLP در `acp_core.telemetry.setup` وجود دارند؛ تست مستقیم صادرکننده OTLP و تجمیع متریک‌ها کامل نیست. |
| **اینترفیس‌های Gateway (Gateway Interfaces)** | `Partially Implemented` | قراردادهای `Protocol` برای `DownstreamHandler`, `UpstreamConnector`, `PolicyEnforcer`, `ApprovalManager` در `acp_core.gateway.interfaces` تعریف شده‌اند اما پیاده‌سازی واقعی کلاسی وجود ندارد. |
| **سلامت سرویس (Health Check Endpoints)** | `Partially Implemented` | اندپوینت `/healthz` سالم است، اما اندپوینت `/readyz` اتصال واقعی به دیتابیس ندارد و دارای کامنت `TODO` است. |
| **قالب‌های سیاست Rego (OPA Rego Policies)** | `Partially Implemented` | فایل `deploy/opa/kolang/authz.rego` آماده است، اما کلاینت فراخوانی OPA از داخل پایتون هنوز ساخته نشده است. |
| **بسته رسمی MCP SDK و نسخه پروتکل (MCP SDK & Protocol)** | `Missing` | پکیج رسمی `mcp` در `pyproject.toml` و `uv.lock` نصب نشده و هیچ استفاده‌ای از SDK در کد وجود ندارد. |
| **مدل‌های دیتابیس ORM و مایگریشن‌ها (SQLAlchemy ORM & Alembic)** | `Missing` | هیچ کلاس مدل دیتابیسی وجود ندارد؛ دایرکتوری `migrations/versions/` خالی است و `target_metadata` در `env.py` برابر `None` است. |
| **احراز هویت و اعتبارسنجی توکن OIDC/JWT** | `Missing` | هیچ میان‌افزار یا Dependency برای اعتبارسنجی توکن با کلیدهای عمومی Keycloak و استخراج Principal در روت‌ها پیاده‌سازی نشده است. |
| **اجرای سیاست‌ها در Gateway (PEP Engine)** | `Missing` | ماژول اجرای سیاست‌ها قبل از فراخوانی ابزار و مسدودسازی ابزارهای ممنوعه در Gateway وجود ندارد. |
| **مدیریت و تزریق محرمانه (Credentials Vault/Storage)** | `Missing` | به جز اسکریپت ساده `generate_key.py`، ماژول ذخیره امن و تزریق هدر/کلید به Upstream پیاده‌سازی نشده است. |
| **رجیستری و کشف ابزارها (Tool Discovery & Registry)** | `Missing` | ماژول‌های اسکن ابزارهای سرور Upstream، فینگرپرینت، و کاتالوگ ابزارها پیاده‌سازی نشده‌اند. |
| **مسیر کامل Streamable HTTP Gateway (MCP Data Plane)** | `Missing` | اندپوینت پردازش درخواست‌های MCP روی HTTP Streamable برای کلاینت‌ها و فوروارد به سرورهای Upstream پیاده‌سازی نشده است. |
| **داشبورد ادمین فرانت‌اند (Admin UI)** | `Missing` | پوشه `apps/web` خالی است. |

---

## ۶. مقایسه وضعیت موجود با تسک‌های MVP Backlog (تسک‌های ACP-001 تا ACP-069)

جدول زیر تطابق وضعیت فعلی مخزن با فازها و تسک‌های ۶۹‌گانه سند `agent-control-plane-mvp-backlog.md` را مشخص می‌کند:

### گروه A: معماری، مخزن و قراردادهای مهندسی (ACP-001 تا ACP-005)
* **ACP-001 (حسابرسی مخزن):** `In Progress` — همین گزارش حسابرسی و نقشه پیاده‌سازی در حال تکمیل آن است.
* **ACP-002 (تثبیت نسخه MCP SDK و پروتکل):** `Missing` — SDK رسمی هنوز پین و اضافه نشده است.
* **ACP-003 (تعریف قراردادهای داخلی درخواست و تصمیم):** `Partially Implemented` — مدل‌های داده‌ای در `protocol/models.py` و `gateway/interfaces.py` ساخته شده و تست شده‌اند، اما نیاز به تکمیل جزئیات فیلدهای استاندارد دارند.
* **ACP-004 (مدیریت تنظیمات و محیط):** `Implemented & Tested` — کلاس `Settings` با استفاده از `pydantic-settings` و فایل نمونه `.env.example` پیاده‌سازی شده و تست شده است.
* **ACP-005 (لاگینگ ساختاریافته و همبستگی درخواست):** `Implemented & Tested` — از طریق `structlog` و `RequestContextMiddleware` به همراه تست کامل فعال است.

### گروه B: مدل داده و ماندگاری (ACP-006 تا ACP-014)
* **ACP-006 تا ACP-014:** `Missing` — هیچ‌یک از مدل‌های دیتابیس (Workspace, McpServer, Tool, ToolSnapshot, Principal, Agent, Policy, PolicyVersion, ApprovalRequest, AuditEvent) در قالب مدل‌های SQLAlchemy 2 پیاده‌سازی نشده‌اند و دیتابیس مایگریشن ندارد.

### گروه C: سرور دمو و درگاه MCP (ACP-015 تا ACP-024)
* **ACP-015 تا ACP-016:** `Partially Implemented` — فایل‌های دمو در `examples/` وجود دارند اما صرفاً اسکریپت ساده با کلاس‌های ماک هستند و با پروتکل رسمی کار نمی‌کنند.
* **ACP-017 تا ACP-024:** `Missing` — آداپتور کلاینت Upstream، اندپوینت Downstream، مپینگ خطاها، محدودیت‌ها و روتینگ و چک سلامت ابزارها پیاده نشده‌اند.

### گروه D: رجیستری ابزارها (ACP-025 تا ACP-030)
* **ACP-025 تا ACP-030:** `Missing` — کشف ابزار، فینگرپرینت، دسته‌بندی امن، API مشاهده کاتالوگ و رفرش هنوز وجود ندارند.

### گروه E: هویت، کلاینت‌ها و چندمستأجری (ACP-031 تا ACP-037)
* **ACP-031:** `Partially Implemented` — فایل Realm در `deploy/keycloak/kolang-realm.json` موجود است.
* **ACP-032 تا ACP-037:** `Missing` — اعتبارسنجی JWT، استخراج هویت، جداسازی فضای کاری و تست‌های امنیتی هنوز ساخته نشده‌اند.

### گروه F: سیاست‌گذاری و OPA (ACP-038 تا ACP-044)
* **ACP-038 تا ACP-044:** `Missing` — به جز فایل Rego خام در `deploy/opa/kolang/authz.rego` و مدل Pydantic، هیچ کلاینت فراخوانی OPA، انطباق سیاست قبل از اجرا، رسید تصمیم یا Rate Limit پیاده نشده است.

### گروه G: مدیریت تأییدیه‌ها (ACP-045 تا ACP-049)
* **ACP-045 تا ACP-049:** `Partially Implemented` — منطق انتقال وضعیت ماشین حالت در حافظه پیاده‌سازی و تست شده (`can_transition`)، اما ذخیره‌سازی، API تأیید/رد و مصرف یک‌بارمصرف آن پیاده نشده است.

### گروه H: مدیریت کلیدهای محرمانه و دسترسی (ACP-050 تا ACP-052)
* **ACP-050 تا ACP-052:** `Missing` — فقط اسکریپت ساده `generate_key.py` وجود دارد؛ هیچ ماژول نگهداری امن یا تزریق Credential ساخته نشده است.

### گروه I: بازرسی و مانیتورینگ (ACP-053 تا ACP-057)
* **ACP-053 تا ACP-057:** `Partially Implemented` — مدل رویداد بازرسی آماده است، تله‌متری اولیه فعال است، اما مخزن ماندگار ذخیره رویدادها، API جستجوی لاگ، متریک‌های پایه و بررسی وابستگی‌ها پیاده نشده‌اند.

### گروه J: آزمون‌های یکپارچگی، پکیجینگ و انتشار (ACP-058 تا ACP-065)
* **ACP-063 (داکر کامپوز محلی):** `Implemented but Untested` — فایل کامپوز کامل وجود دارد اما اجرای End-to-End کل استک ارزیابی نشده است.
* **ACP-064 (خط لوله CI):** `Implemented & Tested` — ورک‌فلوهای گیت‌هاب در `.github/workflows/` کامل و فعال هستند.
* **ACP-058 تا ACP-062 و ACP-065:** `Missing` — تست‌های سناریوهای کامل امنیتی، تست قراردادهای SDK و ران‌بوک نهایی دمو هنوز توسعه داده نشده‌اند.

### گروه K: رابط کاربری نمایشی ادمین (ACP-066 تا ACP-069)
* **ACP-066 تا ACP-069:** `Missing` — پوشه `apps/web` خالی است و رابط کاربری وجود ندارد.

---

## ۷. نیازمندی‌ها، ریسک‌ها و راهنمای تسک‌های بعدی (Context for Next Tasks)

1. **حفظ استقلال مدل‌های داخلی از فرمت فیزیکی پروتکل (Protocol Independence):**
   * مدل‌های پکیج `acp_core.protocol.models` نباید مستقیماً با شمای JSON-RPC درهم‌آمیخته شوند. آداپتورهای تبدیل سیم (Wire Adapters) باید در مرز پروتکل قرار گیرند.
2. **عدم بازنویسی ساختار موجود:**
   * ماژولار بودن بسته‌ها در `packages/acp_core` باید حفظ شود.
   * افزودن کد نباید تست‌های سبز موجود (۱۶ تست جاری) را بشکند.
3. **گام اول بلافاصله پس از این گزارش (تسک ACP-002):**
   * بررسی پکیج رسمی Python MCP SDK (`mcp`)، انتخاب نسخه سازگار و پین کردن آن در `pyproject.toml` و `uv.lock`.
   * ثبت نسخه انتخاب‌شده در ADR یا سند معماری پروژه.
4. **گام‌های فاز دیتا (تسک ACP-006 به بعد):**
   * اضافه کردن مدل‌های پایگاه داده با استفاده از SQLAlchemy 2.0 (همان‌طور که در وابستگی‌ها وجود دارد) با الگوی `DeclarativeBase` و همگام‌سازی آن در `migrations/env.py` روی `target_metadata`.

---

## ۸. چک‌لیست معیار پذیرش (Acceptance Criteria Verification)

- [x] **عدم تغییر در سورس کد:** هیچ فایل پایتون یا سورس کدی در این تسک ویرایش یا اضافه نشد؛ تنها سند گزارش حسابرسی در `docs/development/implementation-status.md` ایجاد گردید.
- [x] **مستندسازی ساختار واقعی مخزن:** تمامی دایرکتوری‌ها، فایل‌های پیکربندی و پکیج‌ها به طور کامل استخراج و در بخش ۲ نگاشت شدند.
- [x] **ثبت دستورات واقعی اجرا و تست:** دستورات واقعی برای بک‌اند، کامپوز داکر، مایگریشن‌ها، ruff، mypy، bandit و pytest به همراه آخرین وضعیت اجرای موفق مستند شدند.
- [x] **فهرست مغایرت‌ها با Scope بک‌لاگ:** تمامی ۶۹ تسک بک‌لاگ بررسی و شکاف‌های واقعی بین مدل‌های فعلی و پیاده‌سازی‌های مورد انتظار معین شدند.
- [x] **ایجاد کانتکست برای تسک‌های بعدی:** این سند مرجع مستند و رسمی برای راهنمای تسک‌های بعدی (از ACP-002 به بعد) آماده است.
