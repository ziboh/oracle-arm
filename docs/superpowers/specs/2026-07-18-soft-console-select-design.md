# Soft Console Select Styling Design

**Date:** 2026-07-18  
**Status:** Approved (design direction A)  
**Scope:** Visual styling of language switch and form `<select>` controls

## Problem

Language switch selects (topbar / login) and form selects (new task / notification editor) still feel like OS chrome: system arrows, uneven density, and weak alignment with the console theme (steel ink, signal focus, ghost controls). Users asked to restyle both so they match the overall UI.

## Decision

**Direction A — Soft Console** (chosen over Steel Inset and Signal Outline):

- Keep native `<select>` elements (no custom dropdown panel).
- Hide the system caret with `appearance: none` and draw a shared CSS chevron.
- Align form selects with text inputs (height, radius, border, hover, focus).
- Treat the language control as a compact ghost-button sibling in the topbar.
- Prefer CSS-only changes; allow minimal HTML wrappers only if required for chevrons.

## Goals

1. Language select and form selects share one visual language (chevron, border, focus).
2. Form selects sit flush with adjacent inputs in new-task fields.
3. No change to i18n submit behavior, OCI resource loading, or option data.
4. Responsive topbar language control remains usable at existing breakpoints.

## Non-goals

- Replacing native option popups with a custom listbox component.
- Theming OS-rendered option menus (browser limitation).
- Changing notification channel picker business logic (the hidden `#notification-channel-picker` stays a data source; visible channel UI is already custom cards).
- Dark mode or new color tokens beyond existing CSS variables.

## Surfaces in scope

| Surface | Location | Notes |
|---------|----------|--------|
| Language switch | `templates/_lang_switch.html` (topbar + login) | Already has `.lang-select-wrap` + `.lang-select` |
| New task form selects | `templates/dashboard.html` connection/instance fields | Compartment, AD, subnet, OS family, image |
| Other visible form selects | e.g. notification editor SMTP security | Same form select rules |
| Global form control base | `static/app.css` input/select rules | Single source of truth |

Out of visual restyle: `[hidden]` selects used only as data pickers.

## Visual specification

### Shared tokens (existing)

Use current theme variables only:

- Borders: `var(--line-strong)` rest, hover toward `#8da0aa` / `#8fa1ab`
- Focus: border `var(--signal)`, ring `rgba(40, 127, 141, .22)` or `.16` consistent with nearby controls
- Text: `var(--ink)`; muted chevron: `var(--muted)`
- Surfaces: white / translucent white matching ghost buttons

### Form select (default)

| Property | Value |
|----------|--------|
| Height | `42px` (match inputs) |
| Border radius | `8px` |
| Background | `#fff` |
| Border | `1px solid var(--line-strong)` |
| Font | inherit; weight 600; size aligned with form body (~12px if needed for long OCI labels) |
| Padding | left ~11px; right ~34px for chevron clearance |
| Hover | border `#8da0aa`; background optional `#fbfdfe` |
| Focus / focus-visible | signal border + soft signal outline/ring; no default browser outline |
| Disabled | existing disabled input styles (`#eef2f4`, muted text) |
| Chevron | CSS triangle via wrapper `::after`, non-interactive |

### Language select (compact)

| Property | Value |
|----------|--------|
| Min height | `34px` (compact / ghost control family) |
| Border radius | `9px` |
| Background | translucent white (~`.5`–`.72`) matching ghost |
| Border | `1px solid var(--line-strong)` |
| Min width | keep existing responsive mins (`7.5rem` desktop, smaller at 580/440) |
| Label | topbar: visually hidden (sr-only) as today; login: visible mono label unless narrow breakpoint hides it |
| Focus | same signal family as form selects |
| Chevron | same triangle language as form selects |

### Chevron pattern

1. `select { appearance: none; -webkit-appearance: none; }`
2. Wrapper (`.lang-select-wrap` or form `.select-wrap`) positions a CSS caret on the right.
3. Pointer-events none on the caret pseudo-element.
4. Do not rely on background SVG that breaks on high-contrast OS themes unless tested; CSS borders triangle is preferred for consistency with current language switch.

## Implementation approach

### Preferred path (CSS-first)

1. Extend global `select` rules in `app.css` to match Soft Console form spec (appearance, padding-right, hover/focus parity with inputs).
2. Introduce a reusable form wrapper class only if global `select` cannot host a reliable caret without a parent (e.g. `label` may work via `label:has(> select)` / `label > select` sibling patterns — pick one approach and use it everywhere).
3. Refine `.lang-select` / `.lang-select-wrap` so focus ring and hover match form selects while remaining compact.
4. Bump `app.css` cache query on `templates/base.html` (`?v=`).

### HTML changes (only if required)

- New-task / editor selects: wrap each visible `<select>` in `<span class="select-wrap">…</span>` **or** rely on existing `<label>` structure without extra nodes if CSS can target `label:has(> select)::after` carefully without colliding with other label contents.
- Prefer the option that avoids double carets and does not break `label > small` / unit suffixes.
- Language switch already has a wrap; keep that structure.

### Explicit non-changes

- No new JS for select UI.
- No changes to `onchange` language submit or cookie mirroring in `base.html`.
- No tests for pixel UI; existing web tests remain green. Manual visual check only.

## Accessibility

- Keep real `<select>` and native keyboard/option behavior.
- Preserve `aria-label` / associated labels on language and form fields.
- Focus ring must remain visible (`:focus-visible` or equivalent that works when tabbing).
- Do not remove the language label text from the accessibility tree in topbar (continue sr-only pattern).

## Responsive

Respect existing breakpoints in `app.css` (580px / 440px) for language min-width and padding. Form selects remain full width of their grid cells.

## Acceptance criteria

1. Topbar language select uses custom chevron (no dual system + CSS caret).
2. New-task selects (compartment, AD, subnet, OS, image) match Soft Console form rules and sit level with nearby inputs.
3. Notification editor visible selects (e.g. SMTP security) pick up the same form rules without a one-off theme.
4. Hover/focus states use steel/signal language, not browser default blue only.
5. Language switching still submits and sets preference as before.
6. Narrow viewports do not clip the language caret or overflow the topbar actions row.

## Risks and mitigations

| Risk | Mitigation |
|------|------------|
| Double caret if both OS arrow and CSS chevron show | Always set `appearance: none` and pad-right |
| Wrapper CSS breaks labels with multiple children | Prefer wrap on select only, or carefully scoped `label:has(> select:only-of-type)` |
| Cache shows old CSS | Bump `?v=` on stylesheet link |
| Long OCI option text | Keep ellipsis-friendly width; do not force fixed select width in forms |

## File touch list (expected)

- `oracle_arm_console/static/app.css` — primary styling
- `oracle_arm_console/templates/base.html` — CSS version query
- Optionally `oracle_arm_console/templates/dashboard.html` and other templates with bare `<select>` if wrappers are required
- `oracle_arm_console/templates/_lang_switch.html` — only if class names need alignment

## Open decisions resolved

- Style direction: **A Soft Console**
- Custom dropdown component: **No**
- Scope: **All visible selects including new task + language**
