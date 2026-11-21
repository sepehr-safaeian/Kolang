# Rule 03: Universal Responsiveness & Accessibility (a11y)

> **Mandate:** Every component, layout, and view must be rigorously responsive across mobile, tablet, laptop, and desktop, meeting WCAG 2.1 AA accessibility standards.

---

## 1. Viewport Spectrum & Breakpoints

Every UI task must be verified across the following 4 tiers:

| Breakpoint Tier | Target Width | Layout Behavior |
|---|---|---|
| **Mobile** | `390px` – `640px` | Single column; drawer navigation; stacked metrics; horizontally scrollable tables or card list view; compact padding (`16px`). |
| **Tablet** | `641px` – `1023px` | Collapsed sidebar (`68px`); 2-column metric grid; dense tables with sticky column headers; medium padding (`20px`). |
| **Laptop** | `1024px` – `1439px` | Expanded sidebar (`248px`); 4-column metrics; full data table density; standard page padding (`28px`). |
| **Desktop** | `≥1440px` | Maximum workspace area; multi-pane inspection view (e.g., trace timeline + JSON payload side-by-side). |

---

## 2. Shell Layout Specifications

- **Topbar:** Fixed height `60px`, border-bottom `1px solid var(--k-border)`, containing breadcrumbs, environment switcher, search trigger, language selector, and theme toggle.
- **Sidebar (Expanded):** Width `248px`, fixed `inset-inline-start: 0`.
- **Sidebar (Collapsed):** Width `68px`, icon-only with accessible hover tooltips.
- **Mobile Navigation:** Hidden sidebar; triggered via hamburger button opening a slide-over sheet / drawer from `inset-inline-start`.

---

## 3. CSS Logical Properties (Mandatory)

Never use physical directional properties (`left`, `right`). Always use CSS logical properties:

```css
/* ❌ FORBIDDEN */
margin-left: 16px;
padding-right: 12px;
left: 0;
border-left: 1px solid var(--k-border);

/* ✅ REQUIRED */
margin-inline-start: 16px;
padding-inline-end: 12px;
inset-inline-start: 0;
border-inline-start: 1px solid var(--k-border);
```

---

## 4. Accessibility (WCAG 2.1 AA) Requirements

1. **Visible Focus Rings:**
   All interactive elements (buttons, inputs, links, tabs, selects) MUST display an unmistakable focus ring on keyboard focus:
   ```css
   :focus-visible {
     outline: 2px solid var(--k-focus);
     outline-offset: 2px;
   }
   ```
2. **Keyboard Navigability:**
   Every user flow must be operable with keyboard only:
   - `Tab` / `Shift+Tab`: Traverse interactive elements in logical DOM order.
   - `Enter` / `Space`: Activate buttons and toggle controls.
   - `Escape`: Close modals, drawers, dropdowns, and tooltips.
   - Arrow keys: Navigate tabs, menus, and combobox option lists.
3. **Multi-Modal Status Badges:**
   Never convey status with color alone. A badge MUST contain:
   - A semantic color token background and foreground (`--k-status-*`).
   - A distinct Lucide icon.
   - Explicit, localized text (e.g., `<StatusBadge status="degraded" icon={AlertTriangle}>Degraded</StatusBadge>`).
4. **Contrast & Typography:**
   - Minimum contrast ratio of 4.5:1 for body text against canvas/surface.
   - Minimum contrast ratio of 3:1 for large text and interactive borders.
   - Respect user preference for reduced motion: `@media (prefers-reduced-motion: reduce)`.
