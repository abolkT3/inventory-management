---
name: saas-ui-redesign
description: Redesign a Vue 3 application's UI into a modern SaaS-style interface with a collapsible vertical sidebar on the left instead of a top nav bar, a consistent spacing scale, and a polished professional look. Use when asked to redesign, modernize, or restyle a Vue 3 UI, add a sidebar navigation, or apply SaaS-style layout and spacing.
---

# SaaS UI Redesign

Convert a Vue 3 app from a top-nav layout to a SaaS-style shell: left sidebar, consistent spacing, clean surfaces. This skill changes presentation only. Routes, data flow, API calls, and component props/events stay as they are.

## Precedence

The project's CLAUDE.md design rules override the defaults below. In this repo that means:

- Palette: slate/gray (`#0f172a`, `#64748b`, `#e2e8f0`)
- Status colors: green / blue / yellow / red
- No emojis anywhere in the UI
- Charts stay custom SVG, layouts stay CSS Grid

If the project defines no design rules, use the defaults in this skill.

## Delegation

- Any time a `.vue` file is created or significantly modified, delegate to the **vue-expert** subagent.
- After the redesign, run the **code-reviewer** subagent over the changes.
- Add no new dependencies (no UI kits, no icon libraries).

## Workflow

Follow these steps in order.

### 1. Audit

Locate and read, before changing anything:

- The app shell (usually `src/App.vue`) and its top navigation markup
- The router definition (`src/main.js` or `src/router/*`) to get the full route list
- Global styles (shell styles often live in `App.vue`; otherwise a global CSS file)
- How nav labels are produced (i18n keys vs. literal strings)
- Other shell-level elements: filter bars, language switcher, profile menu, modals

Record the route list and label source. The sidebar must show exactly the same destinations as the old nav.

### 2. Define design tokens

Put tokens in CSS custom properties on `:root` in the global stylesheet. Reuse existing palette values where the app already has them.

```css
:root {
  /* Spacing: 4px base. Use only these values. */
  --space-1: 4px;  --space-2: 8px;  --space-3: 12px;
  --space-4: 16px; --space-6: 24px; --space-8: 32px;

  /* Surfaces and text */
  --color-bg: #f8fafc;
  --color-surface: #ffffff;
  --color-border: #e2e8f0;
  --color-text: #0f172a;
  --color-text-muted: #64748b;
  --color-accent: #2563eb;

  /* Shape and depth */
  --radius-sm: 6px; --radius-md: 8px;
  --shadow-sm: 0 1px 2px rgba(15, 23, 42, 0.06);

  /* Layout */
  --sidebar-width: 240px;
  --sidebar-width-collapsed: 64px;
  --content-max-width: 1280px;
}
```

### 3. Build the shell

- Root layout is CSS Grid: `grid-template-columns: var(--sidebar-w) 1fr`, where `--sidebar-w` switches between the expanded and collapsed widths.
- The sidebar is `position: sticky; top: 0; height: 100vh` with its own overflow handling.
- The content column scrolls independently and centers its content up to `--content-max-width`.
- Remove the old top-nav header and its styles. Shell-level bars that were under the header (such as filters) move to the top of the content column, not the sidebar.

### 4. Sidebar component

Create a `Sidebar.vue` (via vue-expert) containing:

- Brand block at the top
- Nav list rendered from **one array** of `{ path, labelKey, icon }`, with `v-for` keyed by `path`
- Active state derived from the current route (`router-link` active class or `$route.path`), not tracked by hand
- Footer area for secondary controls (profile, language). Placement of these is up to the app; keeping them in a slim content-area top bar is also fine.
- Labels use the app's existing i18n mechanism. Do not hard-code strings that were translated before.

### 5. Collapse behavior

- A toggle button at the sidebar header or footer switches expanded (240px) and collapsed (64px).
- The button has `aria-expanded` and an `aria-label`.
- The state persists in `localStorage`. Read it once when the component is set up, with a safe default if the key is missing.
- Animate width with a short transition (150-200ms). Respect `prefers-reduced-motion`.
- When collapsed, hide text labels visually and give each item a `title` so the name is available on hover. Keep the accessible name (use a visually-hidden label or `aria-label`).

### 6. Inline SVG icons

- One icon per nav item, 20x20, `viewBox="0 0 24 24"`, `fill="none"`, `stroke="currentColor"`, `stroke-width="1.75"`.
- Mark icons `aria-hidden="true"`; the text label carries the meaning.
- Keep icons in the Sidebar component or a small icon map. Use simple, recognizable shapes (grid for overview, box for inventory, list for orders, chart for reports, and so on).
- No emojis and no icon font or library.

### 7. Normalize the pages

Apply tokens across all views without changing their logic:

- Replace ad hoc `margin`/`padding`/`gap` values with the spacing scale.
- Give every page the same header pattern: title, optional muted description, optional actions on the right.
- Use one card style: `--color-surface` background, 1px `--color-border`, `--radius-md`, `--shadow-sm`, `--space-6` padding.
- Tables: consistent cell padding, muted uppercase header text, subtle row dividers, hover highlight.
- Buttons and inputs: shared height, radius, and a visible focus ring (`outline: 2px solid var(--color-accent); outline-offset: 2px`).
- Keep status colors for badges and indicators only.

## Sidebar spec

| Property | Value |
| --- | --- |
| Width | 240px expanded, 64px collapsed |
| Background | Dark slate (`--color-text`) or white with a right border; pick one and use it consistently |
| Item height | 40px |
| Item padding | `--space-3` horizontal, `--space-2` gap between icon and label |
| Item radius | `--radius-sm` |
| Hover | Subtle background tint |
| Active | Stronger tint plus accent-colored icon/label; do not rely on color alone (add a left bar or weight change) |
| Element | `<nav aria-label="Main">` containing a list of links |

Accessibility requirements:

- Fully keyboard operable, with a logical tab order (toggle, then links)
- Visible focus state on every interactive element
- Text and icon contrast of at least 4.5:1 against the sidebar background
- Active link marked with `aria-current="page"`

## Spacing and polish rules

- Use only the spacing scale. If a value is not in the scale, round to the nearest step.
- Align layout to an 8px rhythm; the 4px step is for tight internal gaps.
- One radius, shadow, and border style per surface type; do not mix.
- Clear type hierarchy: page title, section title, body, muted caption. Define sizes once as tokens or shared classes.
- Do not add decorative gradients, heavy shadows, or animation beyond the sidebar transition.

## Pitfalls

- Do not change routes, route names, API calls, or composable logic.
- Do not duplicate the nav list in markup; render from the array.
- Do not drop translated labels or the language switcher when moving things.
- Unique `v-for` keys (use `path`), never the index.
- Check for fixed `100vh` or `position: fixed` assumptions in existing views that the new shell can break.
- Check that modals still overlay the whole viewport and are not clipped by the sidebar's stacking context.

## Verification checklist

Run the app and check each item. In this repo, drive the browser with the Playwright MCP tools against `http://localhost:3000`.

- [ ] Dev server starts with no build errors and no console errors
- [ ] Every route renders inside the new shell
- [ ] The active nav item highlights correctly on each route and on direct URL load
- [ ] Collapse and expand work, and the state persists after a reload
- [ ] Keyboard navigation reaches every link and the toggle, with visible focus
- [ ] Modals and dropdowns display above the sidebar and content
- [ ] Spacing is consistent across pages (compare screenshots of each route at desktop width)
- [ ] No leftover top-nav markup or unused styles remain
- [ ] code-reviewer subagent run completed and findings addressed
