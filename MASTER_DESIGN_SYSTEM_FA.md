# Kolang — Design System 2027

> سند مرجع طراحی و پیاده‌سازی رابط کاربری Kolang؛ یک Agent Control Plane / MCP Gateway.
>
> **Design direction:** European Technical Editorial — restrained, precise, quietly confident.
>
> **Version:** 1.0 · **Status:** Implementation-ready foundation · **Theme:** Light-first + fully supported dark mode · **Direction:** RTL/LTR

---

## 0. خلاصه تصمیم طراحی

Kolang نباید شبیه یک داشبورد آماده SaaS، پنل مانیتورینگ ارزان یا محصولی با ظاهر «AI-generated» باشد. این محصول یک لایه زیرساختی برای کنترل، اتصال، سیاست‌گذاری و مشاهده‌پذیری عامل‌ها و ابزارهاست؛ بنابراین زبان بصری آن باید حس **اعتماد، کنترل، وضوح عملیاتی و مهندسی** منتقل کند.

### ایده مرکزی: The Control Surface

رابط کاربری مانند یک سطح کنترل مهندسی‌شده طراحی می‌شود: سطوح روشن و خنثی، مرزبندی‌های دقیق، تایپوگرافی محکم، داده‌های خوانا و یک رنگ تأکیدی محدود. جذابیت از تناسب، ریتم، سلسله‌مراتب و جزئیات دقیق می‌آید؛ نه از گرادیان، شیشه‌ای‌بودن، نورهای نئونی یا کارت‌های بیش‌ازحد گرد.

### امضای بصری Kolang

- **رنگ امضا:** Deep Teal / Signal Jade؛ فقط برای اقدام اصلی، وضعیت فعال و نقاط مهم داده.
- **زمینه اصلی:** سفید گرم و خنثی، نه سفید مطلق.
- **سطوح:** لایه‌بندی با اختلاف بسیار کم در روشنایی و border یک‌پیکسلی.
- **تایپوگرافی:** Sans مدرن و کاربردی؛ اعداد tabular برای متریک‌ها و شناسه‌ها.
- **گوشه‌ها:** کنترل‌شده و کاربردی؛ نه همه‌چیز pill و نه همه‌چیز گرد.
- **آیکون‌ها:** خطی، یکدست و کم‌جزئیات؛ بدون ایموجی در UI محصول.
- **داده:** جدول و جزئیات عملیاتی بر نمودارهای تزئینی اولویت دارند.

### آنچه عمداً انجام نمی‌دهیم

1. گرادیان‌های چندرنگ، glow، blur و glassmorphism.
2. کارت‌های سفید شناور با shadow سنگین.
3. استفاده از رنگ accent برای هر عنصر و هر آیکون.
4. نمودارهای بی‌معنا، KPIهای تزئینی و اعداد بزرگ بدون زمینه.
5. گوشه‌های ۲۰ تا ۳۲ پیکسلی در تمام کامپوننت‌ها.
6. تیترهای تبلیغاتی و فضای خالی نامتناسب در صفحات عملیاتی.
7. انیمیشن‌های پیوسته، پس‌زمینه متحرک، mesh و افکت‌های نمایشی.
8. استفاده از لوگوی ماسکات در تمام صفحات؛ ماسکات فقط در نقاط مناسب برندینگ و empty state محدود استفاده شود.

---

## 1. اصول محصول و تجربه

### 1.1 Operational clarity

کاربر باید در هر لحظه بتواند به چهار سؤال پاسخ دهد:

- اکنون چه چیزی در حال اجراست؟
- چه چیزی سالم نیست و شدت مشکل چقدر است؟
- چه کسی/چه چیزی به چه منبعی دسترسی دارد؟
- برای انجام اقدام بعدی چه مجوز یا اطلاعاتی لازم است؟

### 1.2 Density with rhythm

این محصول داده‌محور است. تراکم اطلاعات باید از داشبوردهای عمومی بیشتر باشد، اما نه به قیمت خوانایی. جدول‌ها، فیلترها، شناسه‌ها و متادیتا فضای کافی دارند. از card wrapping بی‌مورد برای هر فیلد خودداری شود.

### 1.3 Progressive disclosure

اطلاعات پایه در سطح اول، جزئیات فنی در پنل جزئیات، drawer یا صفحه مستقل. هیچ صفحه‌ای نباید با نمایش همه پارامترهای فنی از ابتدا کاربر را بمباران کند.

### 1.4 Reversible actions

عملیات مخرب یا دارای اثر امنیتی، پیش‌نمایش و تأیید واضح دارند. برای موارد قابل برگشت، امکان undo یا rollback در نظر گرفته شود. وضعیت «در حال اعمال» با «اعمال‌شده» اشتباه نشود.

### 1.5 Honest system status

هیچ وضعیت موفقیتی صرفاً بر اساس کلیک کاربر نمایش داده نشود. رابط باید بین `Pending`، `Applying`، `Applied`، `Failed` و `Unknown` تمایز بگذارد.

### 1.6 Native, not decorative

کامپوننت‌ها باید به ماهیت داده وفادار باشند. مثلاً Policy به شکل rule builder، Approval به شکل صف تصمیم‌گیری، Trace به شکل timeline/span tree و Tool به شکل catalog با ورودی/خروجی schema نمایش داده شود؛ نه اینکه همه‌چیز به یک کارت یکسان تبدیل شود.

---

## 2. Design foundations

## 2.1 رنگ‌ها

پالت بر پایه خنثی‌های گرم و سبزآبی عمیق ساخته شده است. رنگ تأکیدی باید کم‌مصرف بماند تا هر جا ظاهر شد، معنا داشته باشد.

### Core palette

| Token | Hex | کاربرد |
|---|---:|---|
| `jade-700` | `#176B5B` | رنگ برند در Light، دکمه اصلی و focus |
| `jade-600` | `#1D806D` | Hover در Light / accent اصلی در بعضی اجزا |
| `jade-500` | `#26977F` | عناصر فعال در Dark |
| `jade-100` | `#DCEFE9` | سطح ملایم منتخب |
| `ink-950` | `#151C1B` | متن اصلی و زمینه عمیق |
| `ink-900` | `#1C2523` | سطح Dark |
| `ink-800` | `#2B3633` | سطح دوم Dark |
| `stone-50` | `#F7F8F6` | canvas روشن |
| `stone-100` | `#EEF1EE` | سطح دوم روشن |
| `stone-200` | `#E2E7E3` | border روشن |
| `stone-500` | `#76817B` | متن ثانویه |
| `stone-700` | `#46514B` | متن میانی |

### Semantic colors

| نقش | Light | Dark | توضیح |
|---|---|---|---|
| Canvas | `#F7F8F6` | `#111816` | زمینه کل اپ |
| Surface | `#FFFFFF` | `#18211F` | سطح اصلی |
| Surface raised | `#FFFFFF` | `#202B28` | پنل باز، menu و popover |
| Surface muted | `#F0F3F0` | `#202A27` | ناحیه خنثی داخل صفحه |
| Text primary | `#17201D` | `#EEF3EF` | محتوای اصلی |
| Text secondary | `#56615B` | `#AAB5AE` | توضیح و متادیتا |
| Text muted | `#7B867F` | `#7F8D85` | placeholder و داده کم‌اهمیت |
| Border subtle | `#E7EBE7` | `#293631` | جداکننده ظریف |
| Border strong | `#D5DDD7` | `#3A4841` | مرز قابل تشخیص |
| Accent | `#176B5B` | `#63C5A8` | عمل و وضعیت فعال |
| Accent subtle | `#E6F2ED` | `#203C33` | پس‌زمینه accent |

### Status palette

رنگ وضعیت فقط همراه متن، آیکون یا نشانه شکل‌دار استفاده شود؛ رنگ به‌تنهایی معنا را منتقل نکند.

| وضعیت | Light foreground | Light background | Dark foreground | Dark background |
|---|---|---|---|---|
| Success | `#176B4B` | `#E7F4EC` | `#78D5A2` | `#1D382B` |
| Warning | `#8A5A12` | `#FBF1DD` | `#F0C36D` | `#3B3020` |
| Danger | `#B33B36` | `#FBEAE8` | `#FF938B` | `#402624` |
| Info | `#315F91` | `#E9F1FA` | `#91BCEB` | `#20354A` |
| Neutral | `#59645E` | `#EEF1EE` | `#B1BCB5` | `#2B3731` |

**قواعد رنگ:**

- رنگ سبزآبی فقط برای primary action، لینک مهم، focus، وضعیت فعال و داده منتخب.
- Success را برای «اتصال سالم» یا «عملیات تکمیل‌شده» نگه دارید؛ برای دکمه عادی استفاده نکنید.
- Warning برای degraded، latency غیرعادی یا نیازمند توجه؛ Danger برای خطا، لغو و اقدام مخرب.
- برای نمودارهای چندسری، از مجموعه رنگی محدود و قابل تمایز استفاده شود؛ رنگ‌های وضعیت مستقیماً به عنوان پالت نمودار استفاده نشوند.
- در حالت Dark، به‌جای سفید خالص از سفید مایل به سبز استفاده شود.

## 2.2 تایپوگرافی

### Font stack

- Latin primary: `Inter` یا `Geist Sans` (یکی انتخاب و در کل محصول ثابت شود).
- Persian primary: `Vazirmatn`.
- Monospace: `Geist Mono` یا `IBM Plex Mono` برای ID، key، endpoint، code و log.
- Fallback: `Arial, sans-serif` و برای monospace، `ui-monospace, SFMono-Regular, Consolas, monospace`.

فونت‌ها به‌صورت self-hosted و با وزن‌های مورد استفاده در پروژه عرضه شوند. از بارگذاری وزن‌های غیرضروری خودداری شود. برای فارسی، line-height به‌صورت مستقل تست شود.

### Type scale

| Token | Size / line-height | Weight | کاربرد |
|---|---|---:|---|
| `display` | 36 / 44 px | 600 | فقط معرفی سطح محصول یا صفحه خالی خاص |
| `h1` | 28 / 36 px | 600 | عنوان صفحه |
| `h2` | 22 / 30 px | 600 | عنوان بخش مهم |
| `h3` | 17 / 24 px | 600 | عنوان پنل و کارت |
| `title-sm` | 15 / 22 px | 600 | عنوان ردیف و زیرپنل |
| `body` | 14 / 22 px | 400 | متن استاندارد |
| `body-sm` | 13 / 20 px | 400 | متن فشرده و راهنما |
| `label` | 12 / 16 px | 550 | label فرم و جدول |
| `caption` | 11 / 16 px | 450 | متادیتا و timestamp |
| `metric` | 30 / 36 px | 600 | KPI با اعداد tabular |
| `code` | 12 / 18 px | 450 | کد و شناسه |

### قواعد تایپوگرافی

- وزن 700 را به‌ندرت استفاده کنید؛ وزن 600 برای تیتر کافی است.
- متن بدنه در دسکتاپ کمتر از 13px نشود؛ caption فقط برای اطلاعات واقعاً ثانویه.
- همه timestamp، metric و شناسه‌های عددی از `font-variant-numeric: tabular-nums` استفاده کنند.
- در محیط فارسی، کد، URL، token، UUID و شناسه‌ها با `dir="ltr"` و فونت monospace رندر شوند.
- برای تیتر فارسی از letter-spacing منفی استفاده نکنید.
- متن‌های دو زبانه در یک خط باید با کنترل جهت نمایش داده شوند؛ به الگوریتم bidi مرورگر به‌تنهایی تکیه نکنید.

## 2.3 فاصله‌گذاری

پایه سیستم 4px است. فاصله‌های نامنظم فقط در صورت ضرورت و با token جدید مجازند.

| Token | Value |
|---|---:|
| `space-0` | 0px |
| `space-1` | 4px |
| `space-2` | 8px |
| `space-3` | 12px |
| `space-4` | 16px |
| `space-5` | 20px |
| `space-6` | 24px |
| `space-8` | 32px |
| `space-10` | 40px |
| `space-12` | 48px |
| `space-16` | 64px |
| `space-20` | 80px |

الگوی کاربرد:

- فاصله داخل input/button: 12px افقی، 8px عمودی.
- فاصله بین کنترل‌های یک گروه: 8px.
- فاصله بین گروه‌های فرم: 20–24px.
- padding اصلی صفحه: 28px در عرض دسکتاپ، 20px در تبلت، 16px در موبایل.
- padding پنل/کارت: 20px؛ در جدول و پنل‌های پرتراکم 16px.

## 2.4 Radius

| Token | Value | کاربرد |
|---|---:|---|
| `radius-xs` | 4px | tag کوچک، code chip |
| `radius-sm` | 6px | input، button، dropdown item |
| `radius-md` | 9px | panel کوچک، card |
| `radius-lg` | 12px | dialog، drawer، panel بزرگ |
| `radius-xl` | 16px | فقط ناحیه‌های اصلی محدود |
| `radius-full` | 999px | avatar، status dot، badge کاملاً گرد |

از `radius-xl` به‌عنوان مقدار پیش‌فرض کارت استفاده نشود.

## 2.5 Border و elevation

- مرزبندی، ابزار اصلی تفکیک سطح است؛ shadow ابزار ثانویه.
- کارت عادی: یک border ظریف، بدون shadow.
- Dropdown و popover: border + shadow بسیار کم.
- Modal: border واضح + shadow متوسط.
- از shadow رنگی یا سایه‌های متعدد استفاده نشود.

## 2.6 Motion

| Token | Duration | کاربرد |
|---|---:|---|
| `instant` | 100ms | hover و رنگ |
| `fast` | 140ms | focus، button، toggle |
| `normal` | 180ms | dropdown، tooltip |
| `panel` | 220ms | drawer و panel |

- Easing استاندارد: `cubic-bezier(0.2, 0, 0, 1)`.
- حرکت فقط برای بازخورد وضعیت یا جابه‌جایی لایه است؛ نه تزئین.
- از parallax، spring اغراق‌شده و animation loop استفاده نشود.
- `prefers-reduced-motion` باید رعایت شود.

---

## 3. Layout system

### Desktop application frame

- حداقل عرض طراحی دسکتاپ: 1280px.
- عرض مرجع: 1440px.
- Sidebar در حالت expanded: 248px؛ collapsed: 68px.
- Top bar: ارتفاع 60px.
- Page content: padding افقی 28px؛ حداکثر عرض لازم نیست به‌زور محدود شود، اما متن‌های طولانی محدود شوند.
- Grid: دوازده ستون با gutter برابر 20px.
- Breakpoints پیشنهادی: 640 / 768 / 1024 / 1280 / 1536px.

### Responsive behavior

- زیر 1024px، sidebar به حالت overlay/collapsible تبدیل شود.
- زیر 768px، جدول‌های عریض به الگوی row-detail یا horizontal scroll کنترل‌شده تبدیل شوند؛ ستون‌های کلیدی حذف نشوند.
- پنل جزئیات در موبایل به صفحه تمام‌عرض یا bottom sheet تبدیل شود.
- کنترل‌های اصلی و فیلترها نباید بدون دلیل به چند ردیف پراکنده تبدیل شوند؛ در صورت نیاز toolbar فشرده یا filter drawer استفاده شود.

### Application shell

1. **Sidebar:** لوگوی تایپوگرافیک Kolang، workspace switcher، navigation groups، user/account area.
2. **Top bar:** breadcrumb، context actions، global search/command menu، theme switch و notification.
3. **Main:** page title + supporting sentence + primary action؛ سپس content.
4. **Inspector/Details:** برای مشاهده جزئیات یک entity بدون خروج از context، در صورت مناسب‌بودن.

### Navigation information architecture

ترتیب پیشنهادی برای محصول:

**Operate**
- Overview
- Gateways
- Agents
- MCP Servers
- Tools

**Govern**
- Policies
- Approvals
- Access & Secrets

**Observe**
- Runs & Traces
- Audit Log

**Manage**
- Workspaces
- Settings

آیتم active باید با یک background خنثی/سبزآبی بسیار ملایم، متن پررنگ و نشانگر باریک مشخص شود؛ نه با نوار رنگی ضخیم یا آیکون بزرگ.

---

## 4. Component system

### 4.1 Buttons

| Variant | کاربرد | مشخصات |
|---|---|---|
| Primary | اقدام اصلی صفحه | زمینه jade، متن سفید، بدون gradient |
| Secondary | اقدام هم‌سطح یا کم‌اهمیت‌تر | سطح شفاف/سفید، border |
| Tertiary | اقدام درون‌خطی | بدون border، hover خنثی |
| Destructive | حذف/قطع دسترسی | زمینه danger فقط در تأیید نهایی؛ در حالت عادی outline/text |
| Icon button | عملیات آیکونی | hit area حداقل 36×36، tooltip لازم |

- ارتفاع استاندارد: 36px؛ compact: 32px؛ large: 40px.
- در هر view فقط یک Primary CTA غالب داشته باشید.
- دکمه disabled باید هم از نظر ظاهری و هم interaction واقعاً disabled باشد.

### 4.2 Inputs

- ارتفاع استاندارد 36px، در فرم‌های بزرگ 40px.
- label همیشه بیرون input باشد؛ placeholder جای label را نمی‌گیرد.
- focus ring دو لایه: یک خط سطحی و یک outline accent با شفافیت قابل‌مشاهده.
- helper/error text دقیقاً زیر فیلد قرار بگیرد.
- خطا با پیام قابل اقدام بیان شود، نه فقط «مقدار نامعتبر».
- فیلدهای secret دارای reveal control، copy و وضعیت rotation باشند.

### 4.3 Select / Combobox

- برای گزینه‌های کم، Select ساده.
- برای MCP Server، Tool و Agent با تعداد زیاد، searchable combobox.
- نمایش مقدار انتخاب‌شده باید با نام انسانی و متادیتای ثانویه باشد.
- گزینه disabled دلیل disabled بودن را نشان دهد.

### 4.4 Tables

جدول یکی از مهم‌ترین الگوهای محصول است.

- header ارتفاع 40px، row ارتفاع پایه 48px؛ ردیف با چند خط محتوا حداکثر 64–72px.
- از border افقی ظریف استفاده شود؛ خطوط عمودی به‌صورت پیش‌فرض حذف شوند.
- hover بسیار ملایم؛ selected state مستقل و قابل تشخیص.
- مرتب‌سازی فقط روی ستون‌های واقعی sortable.
- فیلترها به‌صورت toolbar متصل به جدول؛ تعداد فیلتر فعال قابل مشاهده باشد.
- ستون action به‌صورت kebab یا controlهای ضروری؛ از شلوغ‌کردن هر ردیف پرهیز شود.
- empty state، loading skeleton و error state جدا تعریف شوند.
- pagination باید total count و محدوده رکورد فعلی را بیان کند.

### 4.5 Badges و Status

- Badge برای وضعیت کوتاه و ثابت است، نه برای تزئین یا دسته‌بندی دلخواه.
- متن وضعیت همیشه واضح باشد: `Healthy`, `Degraded`, `Offline`, `Pending`, `Blocked`.
- status dot می‌تواند همراه label باشد؛ dot به‌تنهایی در سطح مهم استفاده نشود.
- رنگ‌ها در JSON و CSS از semantic token گرفته شوند.

### 4.6 Tabs

- underline یا segmented tabs کم‌ارتفاع؛ نه tabهای حجیم و گرد.
- انتخاب tab با border پایین/پس‌زمینه خنثی و وزن متن مشخص شود.
- تب‌ها برای جابه‌جایی در یک entity context؛ navigation سطح بالا با tab انجام نشود.

### 4.7 Dialog / Drawer

- Dialog برای تأیید و فرم کوتاه.
- Drawer برای مشاهده/ویرایش جزئیات در context.
- فرم طولانی در صفحه مستقل باشد.
- footer با ترتیب منطقی: Cancel سپس Primary؛ در RTL جایگاه بصری متناسب با الگوی محصول حفظ شود.
- عملیات destructive عنوان صریح و اثر عملیات را شرح دهد.

### 4.8 Toast / Inline feedback

- موفقیت کوتاه و غیرمزاحم؛ خطاهای مهم inline و persistent باشند.
- toast اطلاعات ضروری را در خود داشته باشد و فقط پیام عمومی نباشد.
- برای عملیات asynchronous، toast آغاز عملیات با نتیجه نهایی اشتباه نشود.

### 4.9 Code / JSON / Endpoint blocks

- سطح خنثی با فونت monospace و line-height مناسب.
- copy action در گوشه منطقی block.
- syntax highlight محدود؛ کد نباید به رنگین‌کمان تبدیل شود.
- متن طولانی wrap یا horizontal scroll کنترل‌شده داشته باشد.
- token و secret هرگز به‌صورت پیش‌فرض کامل نمایش داده نشوند.

---

## 5. Kolang-specific patterns

این الگوها تفاوت Kolang با یک داشبورد مدیریتی عمومی را شکل می‌دهند.

### 5.1 Gateway overview

اطلاعات کلیدی:
- Gateway status و endpoint اصلی.
- تعداد requestها در بازه انتخاب‌شده.
- error rate و latency percentile (حداقل p50 و p95، در صورت وجود داده p99).
- تعداد Agentها، Serverهای متصل و Toolهای فعال.
- وضعیت آخرین deployment/config change.

قواعد:
- هر metric باید واحد و بازه زمانی داشته باشد.
- chart بدون timestamp و unit ممنوع.
- تغییرات نسبت به دوره قبل باید با بازه مقایسه صریح نمایش داده شود.

### 5.2 MCP Server catalog

هر ردیف حداقل:
- نام Server و transport.
- endpoint/command به‌صورت secondary.
- connection status.
- تعداد Toolهای کشف‌شده.
- آخرین health check.
- workspace/environment.

جزئیات Server:
- Connection configuration
- Capabilities
- Discovered tools
- Authentication / secret references
- Health history
- Recent activity

### 5.3 Tool catalog

Tool را مانند یک API contract نمایش دهید:
- نام tool و متعلق‌بودن به کدام Server.
- Description کوتاه و واضح.
- Input schema و خروجی نمونه.
- Policy/permission مؤثر.
- وضعیت availability و آخرین اجرا.

برای Schema از JSON viewer/editor با validation state استفاده شود؛ نمایش schema در متن پاراگرافی ممنوع.

### 5.4 Policy builder

Policy یک قانون قابل ارزیابی است؛ نه یک فرم معمولی.

ساختار پیشنهادی:
1. Name + description.
2. Scope: workspace / agent / server / tool.
3. Subject / principal.
4. Conditions (field, operator, value).
5. Effect: Allow / Deny / Require approval.
6. Priority / conflict behavior.
7. Preview: نمونه درخواست و نتیجه ارزیابی.
8. Version history و publish status.

تجربه ساخت Policy باید با مثال واقعی، validation و preview همراه باشد. استفاده از rule builder با خطوط اتصال تزئینی ممنوع.

### 5.5 Approval queue

هر approval باید موارد زیر را نشان دهد:
- درخواست‌دهنده (Agent/Principal).
- Tool یا action درخواستی.
- دلیل یا context کوتاه.
- سطح ریسک و اثر احتمالی.
- زمان درخواست و SLA/expiry در صورت وجود.
- decision: approve / deny / request changes.

جزئیات approval باید ورودی‌ها و اثر تصمیم را قبل از تأیید نشان دهد. تأیید نباید صرفاً با یک کلیک مبهم انجام شود.

### 5.6 Runs & Traces

الگوی پیشنهادی:
- trace summary با وضعیت و duration.
- timeline یا span tree برای توالی فراخوانی‌ها.
- هر span: service/agent/tool، start/end، duration، status، parent-child relation.
- request/response payload در inspector جداگانه.
- خطاها با stack/error category و ارتباط به span نمایش داده شوند.
- فیلتر بر اساس trace id، agent، tool، status، time range.

از نمودارهای تزئینی برای trace استفاده نکنید؛ tree/timeline واقعی و قابل پیمایش لازم است.

### 5.7 Audit log

- append-oriented visual language؛ خوانایی و قابلیت جست‌وجو اولویت دارد.
- نمایش actor، action، target، timestamp، outcome و correlation/trace ID.
- جزئیات event شامل diff یا قبل/بعد، در صورت وجود.
- فیلترهای زمانی و actor/type واضح.

### 5.8 Secrets & access

- Secret value به‌صورت masked.
- نمایش metadata مثل name، owner، last rotated، expires، scopes.
- Copy/reveal با کنترل دسترسی و ثبت رویداد audit در صورت نیاز محصول.
- متن خام secret نباید در log یا toast ظاهر شود.

---

## 6. Data visualization

### اصول

- نمودار فقط وقتی استفاده شود که روند، توزیع یا مقایسه را بهتر از عدد/جدول نشان دهد.
- gridline کم‌رنگ، محور و واحد واضح، tooltip کاربردی.
- بدون 3D، gradient fill، glow یا animation پیوسته.
- انتخاب بازه زمانی همیشه قابل مشاهده باشد.
- رنگ هر سری در یک صفحه ثابت بماند.
- برای مقایسه چند محیط یا چند gateway، legend واضح و تعامل خاموش/روشن‌کردن سری‌ها فراهم شود.

### نمودارهای مناسب

| داده | Visualization |
|---|---|
| Request volume over time | Line chart |
| Latency p50/p95/p99 | Multi-line chart |
| Error rate | Line chart یا sparkline همراه مقدار |
| Tool usage by count | Horizontal bar |
| Status distribution | Stacked bar؛ donut فقط در صورت نیاز واقعی |
| Trace execution | Span tree / timeline |

در نمودارهای حساس، مقدار دقیق از tooltip و جدول accessible در دسترس باشد.

---

## 7. Light / Dark mode

### Light mode

- حالت پیش‌فرض محصول.
- canvas سفید گرم `#F7F8F6`.
- سطح‌های اصلی سفید.
- borderها به‌جای shadow برای جداسازی.
- accent تیره‌تر برای حفظ contrast.

### Dark mode

- dark mode واقعی، نه inversion ساده.
- canvas `#111816` و surface `#18211F`.
- متن اصلی `#EEF3EF`.
- accent روشن‌تر برای contrast.
- سطح‌ها با تغییر روشنایی و border تفکیک شوند؛ از black pure استفاده نشود.

### قوانین مشترک

- تمام کامپوننت‌ها باید هر دو theme را پوشش دهند.
- theme از semantic token استفاده کند؛ hex مستقیم در کامپوننت ممنوع.
- نمودارها در هر دو theme بررسی شوند.
- ترجیح کاربر ذخیره شود و initial theme به سیستم عامل احترام بگذارد؛ در محصول در صورت نیاز default روی Light باشد.

---

## 8. RTL / LTR and localization

Kolang باید از ابتدا دوزبانه‌پذیر طراحی شود؛ RTL صرفاً با `text-align: right` حل نمی‌شود.

- از CSS logical properties مثل `margin-inline-start`، `padding-inline`، `inset-inline-end` استفاده شود.
- آیکون‌های جهت‌دار (chevron/back/forward) بر اساس direction mirror شوند؛ آیکون‌های معنایی مانند shield، database، key و gear mirror نشوند.
- جدول‌ها، breadcrumb، sidebar و toolbar در RTL از ابتدا تست شوند.
- کد، URL، IP، UUID و schema در container مستقل LTR نمایش داده شوند.
- ترکیب اعداد فارسی و انگلیسی در متریک‌ها طبق locale تعیین شود؛ شناسه‌های فنی به اعداد لاتین باقی بمانند.
- تاریخ و ساعت از locale formatter استفاده کنند؛ timestamp فنی در جزئیات می‌تواند ISO-like باشد.
- متن فارسی نباید با فونت لاتین یا line-height لاتین رندر شود.

---

## 9. Accessibility & quality bar

- هدف: WCAG 2.2 AA برای جریان‌های اصلی.
- تمام کنترل‌ها keyboard accessible.
- focus ring در هر دو theme قابل مشاهده.
- رنگ تنها وسیله انتقال وضعیت نباشد.
- متن بدنه contrast حداقل 4.5:1؛ متن بزرگ حداقل 3:1.
- hit target کنترل‌های مهم حداقل 36×36px؛ تعامل لمسی در موبایل ترجیحاً 44×44px.
- جدول‌های پیچیده باید heading و row/column semantics درست داشته باشند.
- آیکون بدون label یا accessible name نباشد.
- برای نمودارها خلاصه متنی و داده قابل دسترس فراهم شود.
- reduced motion رعایت شود.

---

## 10. Iconography & brand usage

- کتابخانه پیشنهادی: Lucide؛ stroke استاندارد 1.75px، اندازه پایه 16 یا 18px.
- آیکون‌ها نباید ترکیبی از سبک‌های filled، outline و emoji باشند.
- برای navigation اندازه 18px؛ برای controlهای درون‌خطی 16px.
- از icon-only action فقط با tooltip و accessible label استفاده شود.
- نماد موش کور Kolang یک دارایی برند است؛ در sidebar فقط در اندازه کوچک و در login/empty state با کنترل مصرف شود.
- لوگو نباید در کنار هر عنوان صفحه تکرار شود.

---

## 11. Content design / microcopy

لحن رابط: دقیق، کوتاه، بی‌طرف و عملیاتی. از لحن تبلیغاتی، شوخی مداوم و عبارت‌های مبهم پرهیز شود.

| بد | بهتر |
|---|---|
| Something went wrong | Connection failed · Check endpoint and credentials |
| Great job! | Policy published |
| No data found | No traces in this time range |
| Are you sure? | Disconnect `production-gateway`? Active requests may fail. |
| Invalid input | Enter a valid HTTPS endpoint |

- وضعیت‌ها با واژگان ثابت نوشته شوند.
- فعل دکمه دقیق باشد: `Create gateway`, `Publish policy`, `Rotate secret`.
- از `Submit` و `OK` تا حد امکان استفاده نشود.
- خطاها علت، اثر و قدم بعدی را مشخص کنند.

---

## 12. Page blueprint — Overview

ترتیب پیشنهادی صفحه Overview:

1. **Page header:** `Overview` + توضیح کوتاه workspace/environment + primary action `Add gateway`.
2. **Operational summary:** چهار metric کوچک و هم‌تراز: Requests، Error rate، p95 latency، Active gateways. هر metric با timeframe.
3. **Traffic & latency:** نمودار خطی اصلی در عرض 8 ستون؛ سلامت gateway یا distribution در پنل 4 ستونی.
4. **Recent activity:** جدول آخرین رخدادها با actor، event، target، time و outcome.
5. **Needs attention:** اتصال‌های degraded، approvalهای باز، policyهای منتشرنشده یا secretهای نزدیک انقضا.
6. **Quick access:** فقط در صورت نیاز و برای ایجاد مسیر سریع به gateway/server/tool؛ از میانبرهای بی‌هدف اجتناب شود.

این صفحه نباید شبیه صفحه بازاریابی باشد. داده واقعی و وضعیت عملیاتی باید محور باشد.

---

## 13. Definition of Done برای هر صفحه

یک صفحه فقط وقتی با این Design System منطبق محسوب می‌شود که:

- [ ] از semantic tokens استفاده کند و رنگ/فاصله/radius مستقیم در کامپوننت hardcode نشده باشد.
- [ ] در Light و Dark درست کار کند.
- [ ] در RTL و LTR قابل استفاده باشد.
- [ ] loading، empty، error، success و disabled state داشته باشد.
- [ ] focus، hover، active و selected state طراحی شده باشند.
- [ ] keyboard navigation برای جریان اصلی کار کند.
- [ ] داده فنی LTR و قابل کپی باشد.
- [ ] در viewportهای 1440، 1024، 768 و 390 پیکسل بررسی شده باشد.
- [ ] متن‌ها، statusها و واحدها دقیق و سازگار باشند.
- [ ] هیچ gradient، glow، glassmorphism یا shadow تزئینی ناخواسته نداشته باشد.

---

## 14. Implementation rules for the coding agent

1. قبل از نوشتن UI، تمام فایل‌های این پکیج را بخوان؛ `tokens.json` منبع حقیقت tokenها و `kolang.css` پیاده‌سازی پایه CSS است.
2. از token موجود استفاده کن. اگر token جدید لازم شد، اول در JSON و CSS تعریفش کن؛ مقدار inline نساز.
3. کامپوننت‌ها را بر اساس وظیفه بساز: `DataTable`، `StatusBadge`، `PageHeader`، `FilterBar`، `CodeBlock`، `JsonViewer`، `Metric`، `ApprovalReview`، `TraceTree`.
4. ساختار componentها را از رنگ/تم جدا نگه دار. theme باید با تغییر `data-theme` عوض شود، نه با شرط‌های پراکنده در JSX.
5. جهت را از `dir` ریشه بگیر. از `left/right` در CSS جدید استفاده نکن؛ logical properties به‌کار ببر.
6. اطلاعات و statusهای نمونه را به‌عنوان داده ساختگی قطعی نمایش نده. برای mock data برچسب واضح `Demo data` بگذار.
7. نمودار را با charting library موجود پروژه بساز؛ کتابخانه جدید را فقط در صورت نیاز واقعی اضافه کن.
8. اولویت با عملکرد، خوانایی، دسترسی‌پذیری و consistency است؛ از افکت‌های بصری غیرضروری دوری کن.
9. از icon library واحد استفاده کن. آیکون‌های متفرقه و emoji ممنوع.
10. هیچ‌وقت اطلاعات حساس را در UI، log، toast یا screenshot تست افشا نکن.

### خروجی مورد انتظار از agent

- global theme + tokens integrated.
- application shell responsive.
- reusable primitives and components.
- Overview page با ساختار بخش 12.
- حداقل یک نمونه کامل از هر الگوی تخصصی (Server detail، Policy builder، Approval review، Trace inspector).
- Storybook یا صفحه داخلی component showcase، در صورت وجود زیرساخت پروژه.
- تست بصری Light/Dark و RTL/LTR.

---

## 15. تصمیم‌های نهایی برند

| موضوع | تصمیم |
|---|---|
| Personality | Calm, capable, precise, quietly distinctive |
| Visual metaphor | Engineered control surface |
| Primary color | Deep Jade `#176B5B` |
| Dark accent | Soft Jade `#63C5A8` |
| Base typography | Inter/Geist Sans + Vazirmatn |
| Technical typography | Geist Mono / IBM Plex Mono |
| Shape language | Compact radii, crisp borders |
| Density | Medium-high, operational |
| Motion | Functional, restrained |
| Illustration | Rare, purposeful, brand mascot only in selected states |
| Default theme | Light |
| Localization | RTL and LTR first-class |

**اصل نهایی:** Kolang باید شبیه ابزاری باشد که یک تیم زیرساخت اروپایی با وسواس مهندسی ساخته است؛ نه محصولی که صرفاً می‌خواهد در اسکرین‌شات زیبا به نظر برسد.
