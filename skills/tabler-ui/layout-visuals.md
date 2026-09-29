# Tabler UI — grid, badges, icons & visual patterns

Part of the `tabler-ui` skill. Layout, badge/status, icon, and typography patterns on
Tabler. All entries `[Vue 3]` unless tagged otherwise. (This install's stack tag and
component names: `LOCAL.md` beside this skill, when your copy keeps one.)

## Contents

- [Grid: size columns to tile count](#grid-size-columns-to-the-tile-count-so-a-row-fills-its-full-width) · [Table-cell badges & status pills](#table-cell-badges--status-pills)
- [Table/list error state](#tablelist-error-state-empty-state-in-the-body) · [Card/wizard/icon patterns](#card-wizard--icon-patterns-that-worked)
- [Hero eyebrow sizing](#hero-eyebrowsubheader-sizing) · [Custom icons in `.shape` badges](#custom-icon-in-a-shape-badge-must-be-a-square-2424-tabler-style-glyph)

## Grid: size columns to the tile COUNT so a row fills its full width

Tabler's grid is 12-wide, so the `col-lg-*` width must divide 12 by the number of tiles in
that row — otherwise the row leaves a dangling empty slot and reads as broken/misaligned.
**Match the class to the count:** 2 tiles → `col-lg-6`, **3 tiles → `col-lg-4`** (NOT
`col-lg-3`, which is a 4-up grid and leaves the 4th slot empty), 4 tiles → `col-lg-3`, 6 →
`col-lg-2`. Don't reflexively reach for `col-lg-3` on a stat/metric card row — count the
tiles first. (Caught on metric-card dashboards: 3-tile rows were `col-lg-3`, so the
three cards hugged the left with a gap on the right instead of spreading evenly. Origin:
`LOCAL.md` beside this skill, when your copy keeps one — *layout-visuals.md — Grid*.)

- **Why:** an uneven row (3 cards in a 4-slot grid) looks unfinished and off-balance; even
  distribution across the full width is the intended, polished look.
- **How to apply:** when a row's tile count is fixed, hardcode the matching `col-lg-N`
  (12 ÷ count). If the count varies at runtime, compute it (e.g. `col-lg-${12 / tiles.length}`
  — but write the literal class names out for PurgeCSS, per the dynamic-class rule in
  [components-js.md](components-js.md), or cap to the handful of counts you actually use).
  Keep the responsive breakpoints (`col-sm-6`) as-is; only the `-lg-` slot needs to track
  the count.

## Table-cell badges & status pills

- **Status pills in data-table cells are soft badges, not solid ones, built from Bootstrap
  5.3's opaque pair `bg-<color>-subtle` + `text-<color>-emphasis`**, e.g.
  `<span class="badge bg-success-subtle text-success-emphasis">`. Use success (green),
  danger (red), warning (amber) and secondary (grey/neutral). Establish one pattern and
  mirror it: a Yes/No boolean cell uses the success/danger pair, and new status cells
  follow suit (e.g. a job-run status cell: success/failed/partial/skipped). (This
  install's cells: `LOCAL.md` beside this skill, when your copy keeps one —
  *layout-visuals.md — Table-cell badges*.)
  - **Why not Tabler's `-lt` variants** (`bg-success-lt`…), which look the same: measured
    on Tabler 1.5, every `-lt` badge fell between 2.5:1 and 4.4:1 in the light theme,
    under WCAG AA's 4.5:1. They are 10%-alpha tints that aren't redefined for dark mode,
    and inside a `.btn-outline-*` on hover the badge composites to its own text colour
    (1.00:1). The `-subtle`/`-emphasis` pair is opaque and is redefined under
    `[data-bs-theme="dark"]` (primary measured 10.58:1 light, 7.27:1 dark). v1.6 redefined
    colours in `oklch()`, so re-measure before relying on either number.
  - **The pair exists only for the theme colours** (primary, secondary, success, danger,
    warning, info, light, dark). v1.6's `tabler.css` has no `bg-blue-subtle` or
    `bg-cyan-subtle`, so map a palette colour to its theme colour, or define the extended
    pair in the app's own CSS.
  - **`-subtle` sets only the background.** Always pair it with the matching
    `text-*-emphasis`. `-lt` set both, so a blind `-lt` → `-subtle` rename ships grey text.
  - **Write both class names as literals.** PurgeCSS keeps them only while the full name
    appears in source (the dynamic-class rule in [components-js.md](components-js.md)).
- **Mapping an enum value → badge class: key the map by the STRING value, do NOT import the
  enum.** A workspace types package's runtime enum imports can crash Vue SFCs
  (reflect-metadata), so build the value→class lookup off raw string keys instead of the
  enum members.

## Table/list error state (empty state in the body)

When an async list fetch fails, render a Tabler empty-state in the table body — `.empty` >
`.empty-icon.text-danger` (a `@tabler/icons-vue` `IconAlertTriangle`) > `.empty-title`
("Something went wrong") > `.empty-subtitle.text-secondary` > `.empty-action` with a "Try
again" `btn btn-primary`. Wire it as a sibling branch of the loading placeholder inside the
existing `<transition mode="out-in">` (loading → error → table). Put it in the shared
table-list component, driven by an `error` prop + `retry` emit, so every list view gets
it. (This install's files: `LOCAL.md` beside this skill, when your copy keeps one — *layout-visuals.md — Table/list error state*.)

## Card, wizard & icon patterns that worked

- Card header with a right-aligned action: `.card-header` is flex — put the title then a
  `<button class="btn ms-auto">` to push the action right; gate it per step/state with `v-if`.
- Multi-step wizard uses Tabler `.steps.steps-counter.steps-blue` with `.active` on the
  current step; sticky `.card-footer` for Back/Next/Submit.
- Icons: `@tabler/icons-vue` (e.g. `IconPlus`, `IconCar`, `IconSearch`) rather than
  icon-font markup.
- **`@tabler/icons-vue` size/stroke:** in this build `stroke` types as `string`, so pass
  `size="48" stroke="1.5"` as string literals (NOT `:size="48"`) or vue-tsc errors
  "number is not assignable to string".

## Hero eyebrow/subheader sizing

- `tabler-marketing.css` ships a `.hero-subheader` class, but it's an **uppercase, 0.75rem,
  secondary-color** eyebrow — do NOT reuse it for a mixed-case, primary-colored eyebrow; it'll
  look wrong (caps + tiny + gray).
- A subheader `<div>` placed **inside** `h1.hero-title` inherits the title's 3rem/bold, so it
  renders as large as the title. To make a primary-colored eyebrow that's smaller than the title
  with spacing below, put Tabler utilities on the div: `class="text-primary fs-1 fw-semibold mb-3"`
  (`fs-1`≈1.5rem vs the 3rem title — `fs-2`/1.25rem read a touch small; `mb-3` adds the gap).
  (This install's component: `LOCAL.md` beside this skill, when your copy keeps one — *layout-visuals.md — Hero eyebrow*.)

## Custom icon in a `.shape` badge must be a SQUARE 24×24 Tabler-style glyph

`.shape` lives in `tabler-marketing.css`, not `tabler.css`, so a page that loads only the
core stylesheet gets no badge at all. `.shape .icon` forces the icon to a **square** box
(`width:height:var(--tblr-shape-icon-size)`, 1.5rem by default; the `.shape-xxs`…`.shape-xl`
sizes change it). Tabler's own icons are 24×24 so they fill it. A custom **wide** icon (e.g. an old
`IconUserCar`, viewBox `0 0 48 24` — user + car side by side) keeps its aspect ratio and scales to
fit the square's *width*, so it renders at ~half height — visibly smaller than its neighbors.

- **Stopgap that does NOT satisfy:** sizing the wide svg by height only (`style="width:auto;
  height:var(--tblr-shape-icon-size,1.5rem)"` + tightened viewBox). It matches the scale but the
  glyph is wide, so it pushes against the round badge's left/right edges and always reads "too
  tight" no matter how you nudge the internal gap. A wide glyph just doesn't belong in a square badge.
- **Real fix — redesign as a square 24×24 / stroke-2 Tabler composite from the genuine primitives.**
  No native Tabler icon combined people+vehicle. Build one by **transforming the real @tabler `user`
  and `car` path data** (scale+translate) into a square 24×24 grid, keeping stroke-2 — so curves
  match the siblings exactly. Keep it square → `.shape .icon` sizes it like the others, no special CSS.
- **Two-concept icons: balance both parts; don't make one a tiny corner badge.** First attempt used
  Tabler's "primary glyph + corner badge" pattern (`IconUserStar`/`Shield`/`Cog` = `user` base + small
  lower-right badge) with the car as the badge — the user rejected it: the car was too small to read
  as an equal concept. **Winner: balanced side-by-side** — `user` (head + a shoulder *truncated on the
  right*, `…h2`, to clear the overlap) on the LEFT beside a comparably-sized `car` on the RIGHT, both
  ~0.75–0.82 scale, content kept within ~x1–22 so badge padding matches the siblings.
  (This install's icon file: `LOCAL.md` beside this skill, when your copy keeps one — *layout-visuals.md — Two-concept icons*.) Lesson: corner-badge is for a small *modifier* (a star/plus/shield ON a thing);
  when both nouns are first-class ("members & vehicles"), size them evenly side-by-side.
- **Don't hand-guess composite geometry — render and compare.** `rsvg-convert` (installed) → PNG,
  `magick montage` several candidates next to the REAL sibling icons (`IconBuildingStore`,
  `IconLicense`) in the same blue badge, then eyeball the family fit AND let the user pick from the
  montage. Pull canonical path data from `node_modules/.pnpm/@tabler+icons-vue@*/.../dist/esm/icons/
  <Name>.mjs`. A tiny scratch transformer (scale rx/ry + endpoints for `a`, scale deltas for rel
  `h/v/l/c/m`, scale+translate for abs `M`) is enough to reposition real Tabler paths. A car shrunk
  below ~0.5 scale needs wheel radius ≥~1.3 — at r1 + stroke-2 the wheel hole closes and it blobs.
