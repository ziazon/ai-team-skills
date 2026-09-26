# Tabler UI — interactive components, JS & build exceptions

Part of the `tabler-ui` skill. The "don't use Tabler's X — use Y instead, because Z"
exceptions for interactive/JS components in Vue 3, plus stacking and production-build
gotchas. All entries `[Vue 3]` unless tagged otherwise. (This install's stack tag and
component names: `LOCAL.md` beside this skill, when your copy keeps one.)

## Contents

- [Modals](#modals) · [Dropdowns in overflow containers](#dropdowns-inside-scrolloverflow-containers-esp-data-tables) · [Carousel](#carousel) · [tabler.min.js](#tablerminjs)
- [PurgeCSS strips dynamically-composed class names](#dynamiccomposed-tabler-class-names-in-production-builds-purgecss)
- [Stacking / z-index](#stacking--z-index-gotchas-tabler--vue-final-modal) · [Confirmation dialogs](#confirmation-dialogs) · [Action-item conditions](#action-menu-condition-filtering) · [Theme toggle placement](#theme-toggle-responsive-gotcha)

## Modals

Do NOT use Tabler/Bootstrap's vanilla modal JS (`data-bs-*`, `bootstrap.Modal`) — it fights
Vue 3 reactivity. USE `vue-final-modal` behind one app-level modal wrapper component
(this install's: `LOCAL.md` beside this skill, when your copy keeps one — *components-js.md — Modals*). Open imperatively with
`useModal({ component: shallowRef(MyModal), attrs })`.

- **Edit/manage flows = the vue-final-modal wrapper, not inline page swaps.** A row-action
  "Manage X" should open the modal wrapper via `useModal`, never `router.push` to a full-page
  view that replaces the list with no close button. (The frontend skill has the
  modal-vs-page heuristic.)
- **Modal focus management (a11y):** on open, move focus into the dialog; trap focus inside it
  while it's open (Tab must not escape to the page behind); and return focus to the trigger
  element on close. Without this, keyboard/screen-reader users land nowhere on open and lose
  their place on close.

## Dropdowns inside scroll/overflow containers (esp. data tables)

Do NOT use Tabler/Bootstrap's vanilla dropdown (`data-bs-toggle="dropdown"`) for a menu rendered inside `.table-responsive` (or any `overflow: auto/hidden` ancestor). The menu is a DOM child of the cell, so the overflow ancestor **clips** it; the tempting "fix" of forcing `position: relative` drops the menu into normal flow and **stretches the row open** to fit the whole menu. USE a teleported dropdown component: it `<Teleport>`s the menu to `<body>` (escaping the overflow ancestor) and positions it `fixed` to the trigger via `@vueuse/core` `useElementBounding` + `useWindowSize` (no popper/floating-ui needed), with outside-click/Escape dismissal and capture-phase scroll re-pinning. A workable API: slots `#trigger` (`{ toggle, open }`) + default (`{ close }`); prop `align: 'start' | 'end'`. Build it once and reuse it for every in-table/in-card menu (row action menus, pagination menus). (This install's component and history: `LOCAL.md` beside this skill, when your copy keeps one — *components-js.md — Dropdowns*.)

## Carousel

Do NOT rely on Tabler/Bootstrap's `data-bs-ride="carousel"` data-api to auto-cycle in an SSR-hydrated SPA — the data-api only inits carousels on the `window.load` event against the server-rendered DOM. It "works" on first load but breaks when Vue re-renders the carousel subtree (e.g. **dark mode**: a theme loader that reads local storage flips `data-bs-theme` before mount → theme-reactive image `src`s make Vue patch the subtree during hydration → the data-api's carousel instance desyncs → cycling stops). Light mode never re-renders, so the bug is dark-mode-only and easy to miss. (This install's case: `LOCAL.md` beside this skill, when your copy keeps one — *components-js.md — Carousel*.) USE explicit lifecycle ownership: construct `new (window as any).bootstrap.Carousel(el, { interval: 4000, ride: 'carousel' })` in `onMounted` (post-hydration, on Vue-controlled nodes) and `.dispose()` in `onBeforeUnmount`. Also note `data-interval` is stale BS4 syntax — BS5 wants `data-bs-interval`, or just pass `{ interval }` to the JS ctor. (`window.bootstrap` is exposed by tabler.min.js — `t.bootstrap = vo`, with `Carousel`, `Modal`, etc.)

## tabler.min.js

`tabler.min.js` is still imported for some non-interactive behaviors/styles; prefer
Vue-native wrappers for anything stateful.

## Dynamic/composed Tabler class names in production builds (PurgeCSS)

Do NOT compose Tabler utility/brand class names at runtime (e.g. ``:class="`btn-${network}`"`` for `btn-facebook`/`btn-x`/`btn-linkedin`) when your production build runs **PurgeCSS** (e.g. a Vite plugin) — it only keeps selectors whose literal names appear in source, so composed classes get **stripped from the shipped CSS**. Dev mode and unit tests both pass (full CSS present / no CSS at all), so the breakage is production-only — buttons render unstyled. USE a literal class-name map (`{ facebook: 'btn-facebook', ... }`) or write the full class in the template. Caught only by running the BUILT SSR output (footer social buttons); assume the same for any `bg-${color}`/`text-${status}` composition. (This install's build: `LOCAL.md` beside this skill, when your copy keeps one — *components-js.md — PurgeCSS*.)

## Stacking / z-index gotchas (Tabler + vue-final-modal)

- vue-final-modal's first modal mounts at **z-index 1000** (`1000 + 2*index`). Tabler/Bootstrap `.sticky-top` = **1020**, `.modal` = 1055. A sticky footer/header raised above the sticky column can therefore end up ABOVE a vue-final-modal modal.
- Fix pattern: keep app sticky elements below 1000 (e.g. sticky footer ~995, sticky side column ~990) so modals overlay them; scope the overrides to the component. Scoped Vue styles beat Bootstrap utility classes on specificity (the `[data-v-*]` attribute), so you can override `.sticky-top`'s z-index without `!important`.

## Confirmation dialogs

Give the shared confirmation modal a `type` prop that drives the styling: `type: 'warning'`
→ danger (`btn-danger`) confirm button + alert-triangle icon (use for destructive confirms);
`type: 'info'` → `btn-primary` + alert-circle. (This install's component: `LOCAL.md` beside this skill, when your copy keeps one —
*components-js.md — Confirmation dialogs*.)

## Action-menu condition filtering

Table cells that feed a row action-menu component's `:items` build an array of `{ label, action, condition }` and
filter it to decide which actions show. The condition is (usually) a function — you MUST call
it: `.filter((item) => item.condition())`. Filtering on the bare reference
(`.filter((item) => item.condition)`) is always truthy → every action shows regardless of
permission/status (a real permission-bypass bug class, easy to repeat). When items mix
function conditions with literal `true`, use the guard
`typeof item.condition === 'function' ? item.condition() : item.condition`.

## Theme toggle responsive gotcha

When the top header is `d-none d-lg-flex` (whole header hidden below `lg`), a theme
toggle placed only there vanishes on mobile. Put the mobile toggle in the *side nav*
(its footer, gated `d-lg-none`) so it complements the desktop header toggle without
doubling. Keep the theme-switcher component itself visibility-neutral (`d-flex`, no
`d-none d-md-flex`) and let each parent decide where it shows. (This install's component
names: `LOCAL.md` beside this skill, when your copy keeps one — *components-js.md — Theme toggle*.)
