# Rule 04: Design System & Design Tokens

> **Mandate:** All visual styling must derive strictly from canonical tokens defined in `tokens.json` and `kolang.css`. Direct hardcoding of visual properties is strictly prohibited.

---

## 1. Aesthetic Direction: European Technical Editorial

Kolang is an **Agent Control Plane / MCP Gateway** enterprise infrastructure platform.
- **The Core Metaphor:** *The Control Surface* — engineered, quiet, precise, high-density, informative.
- **Visual Signature:**
  - Deep Teal / Signal Jade accent (`#176B5B` in Light, `#63C5A8` in Dark) reserved strictly for primary actions, active state, and key metrics.
  - Warm neutral canvas (`#F7F8F6` in Light, `#111816` in Dark).
  - 1px crisp borders separating subtle surface luminance levels.
  - Tabular numbers for all metrics, IDs, latency values, and timestamps.
  - Crisp outline Lucide icons with consistent 1.5px/1.75px stroke.

---

## 2. Core Token Mappings

### 2.1 Colors (`tokens.json` & `kolang.css`)

| Semantic Token | Light Mode Value | Dark Mode Value | Purpose |
|---|---|---|---|
| `--k-canvas` | `#F7F8F6` | `#111816` | Main application background |
| `--k-surface` | `#FFFFFF` | `#18211F` | Default card and panel surface |
| `--k-surface-raised` | `#FFFFFF` | `#202B28` | Elevated surfaces (dialogs, popovers) |
| `--k-surface-muted` | `#F0F3F0` | `#202A27` | Table header, subtle backgrounds |
| `--k-surface-selected`| `#E6F2ED` | `#203C33` | Active/selected row or item |
| `--k-text-primary` | `#17201D` | `#EEF3EF` | High-contrast body and title text |
| `--k-text-secondary`| `#56615B` | `#AAB5AE` | Supporting labels, descriptions |
| `--k-text-muted` | `#7B867F` | `#7F8D85` | Placeholders, inactive icons |
| `--k-border-subtle` | `#E7EBE7` | `#293631` | Dividers, subtle inner borders |
| `--k-border` | `#E2E7E3` | `#34413B` | Default component and table borders |
| `--k-border-strong` | `#D5DDD7` | `#3A4841` | High-emphasis borders, active inputs |
| `--k-accent` | `#176B5B` | `#63C5A8` | Primary CTA, focus ring, selected tab |
| `--k-accent-hover` | `#125647` | `#82D7BD` | Primary button hover |
| `--k-focus` | `#6CBBA4` | `#63C5A8` | Keyboard focus ring |

### 2.2 Status Colors

| Status | Light (FG / BG) | Dark (FG / BG) | Semantic Usage |
|---|---|---|---|
| **Success** | `#176B4B` / `#E7F4EC` | `#78D5A2` / `#1D382B` | Healthy, Applied, Approved, 2xx |
| **Warning** | `#8A5A12` / `#FBF1DD` | `#F0C36D` / `#3B3020` | Degraded, Pending, Expiring, 4xx |
| **Danger** | `#B33B36` / `#FBEAE8` | `#FF938B` / `#402624` | Offline, Denied, Error, Failed, 5xx |
| **Info** | `#315F91` / `#E9F1FA` | `#91BCEB` / `#20354A` | Informational notes, connecting |
| **Neutral** | `#59645E` / `#EEF1EE` | `#B1BCB5` / `#2B3731` | Inactive, draft, unregistered |

### 2.3 Typography Scale

- **Display:** `36px` / `line-height: 44px` (Overview headlines)
- **H1:** `28px` / `line-height: 36px` (Page headers)
- **H2:** `22px` / `line-height: 30px` (Section titles)
- **H3:** `17px` / `line-height: 24px` (Card titles)
- **Body:** `14px` / `line-height: 22px` (Standard text, forms, tables)
- **Body-sm:** `13px` / `line-height: 20px` (Secondary descriptions)
- **Label:** `12px` / `line-height: 16px` (Status badges, metadata headers)
- **Metric:** `30px` / `line-height: 36px` (Key performance metrics)

### 2.4 Corner Radii

- `--k-radius-xs`: `4px` (Badges, tags, small code chips)
- `--k-radius-sm`: `6px` (Buttons, inputs, dropdown items)
- `--k-radius-md`: `9px` (Cards, panels, modal dialogs)
- `--k-radius-lg`: `12px` (Outer containers, large drawers)
- `--k-radius-full`: `999px` (Pills, circular avatars)

---

## 3. Explicit Forbidden Patterns

1. ❌ **NO Multi-color gradients or radial glows:** Keep surfaces solid and flat.
2. ❌ **NO Glassmorphism or background blurs:** Enterprise operational UI requires crisp readability.
3. ❌ **NO Floating cards with heavy shadows:** Use clean 1px border separation (`var(--k-border)`).
4. ❌ **NO Giant 20px-32px border radii:** Stay within `--k-radius-xs` to `--k-radius-lg`.
5. ❌ **NO Meaningless decorative charts:** Every chart must have labeled axes, units, time ranges, and tooltips.
6. ❌ **NO Mascot spamming:** Kolang mascot is only for authentication hero or empty states.
