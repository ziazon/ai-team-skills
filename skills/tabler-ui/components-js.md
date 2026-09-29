# Tabler UI — interactive components, JS & build exceptions

Part of the `tabler-ui` skill. The "don't use Tabler's X — use Y instead, because Z"
exceptions for interactive/JS components in Vue 3, plus stacking and production-build
gotchas. All entries `[Vue 3]` unless tagged otherwise. (This install's stack tag and
component names: `LOCAL.md` beside this skill, when your copy keeps one.)

## Contents

- [Modals](#modals) · [Dropdowns in overflow containers](#dropdowns-inside-scrolloverflow-containers-esp-data-tables) · [Carousel](#carousel) · [Tabler's own JS components](#tablers-own-js-components-datepicker-otp-strength-sortable) · [tabler.min.js](#tablerminjs)
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

Do NOT rely on Tabler/Bootstrap's `data-bs-ride="carousel"` data-api to auto-cycle in an SSR-hydrated SPA — the data-api only inits carousels on the `window.load` event against the server-rendered DOM. It "works" on first load but breaks when Vue re-renders the carousel subtree (e.g. **dark mode**: a theme loader that reads local storage flips `data-bs-theme` before mount → theme-reactive image `src`s make Vue patch the subtree during hydration → the data-api's carousel instance desyncs → cycling stops). Light mode never re-renders, so the bug is dark-mode-only and easy to miss. (This install's case: `LOCAL.md` beside this skill, when your copy keeps one — *components-js.md — Carousel*.) USE explicit lifecycle ownership: construct the carousel in `onMounted` (post-hydration, on Vue-controlled nodes) and `.dispose()` it in `onBeforeUnmount`. Also note `data-interval` is stale BS4 syntax — BS5 wants `data-bs-interval`, or just pass `{ interval }` to the JS ctor.

🚨 **Get `Carousel` (or `Modal`, …) by importing it, never from `window.bootstrap`. Tabler never sets that global.** Its UMD wrapper takes the CommonJS branch under any bundler (`typeof exports === 'object'`), so `import '@tabler/core/dist/js/tabler.min.js'` writes to `exports.bootstrap` and leaves `window` untouched. Loaded as a plain `<script>`, it sets `window.tabler` (with `.bootstrap` inside it), still not `window.bootstrap`. Read the wrapper's `factory(global.tabler = {})` line before trusting any global. The older advice here, `new (window as any).bootstrap.Carousel(...)`, was dead code: a `?.` guard turned the missing global into "never construct", and a spec that set `window.bootstrap` itself stayed green (this install's case: `LOCAL.md` beside this skill, when your copy keeps one — *components-js.md — Carousel*). What to do instead:
- Load `@tabler/core`'s ES-module build (its `module` field, `dist/js/tabler.esm.js`, with types; present since at least 1.5.1) **once** from the client entry, then import named exports from it. Loading the UMD file and the ESM file together puts two Bootstrap copies in the page, and each copy's data-api click handler acts on every click.
- That module calls `EventHandler.on(document, …)` as soon as it is evaluated. A component that also renders on the server must therefore `const { Carousel } = await import('@tabler/core')` inside `onMounted`, and check that it was not unmounted while the import was in flight. `import type { Carousel } from '@tabler/core'` at the top of the file is fine. Pin this with a spec that renders the component with `renderToString` in a node (no-DOM) test environment.

## Tabler's own JS components (datepicker, OTP, strength, sortable…)

v1.6 made Datepicker, OtpInput, Strength, Clipboard, Sparkline, Confetti, Autosize, CountUp,
InputMask, Sortable and SwitchIcon into Bootstrap-style components (`class … extends
BaseComponent`, with `getOrCreateInstance()` and `dispose()`). Do NOT rely on their
`data-bs-*`/`data-tblr-*` auto-init in Vue. Auto-init is a one-shot scan of the DOM
(`initAll`) when the page loads, so an element Vue renders later is never initialized. A
few components, Datepicker among them, also initialize lazily on click or focus through
handlers delegated from `document`. Those appear to work, but nothing disposes the instance
when Vue unmounts or re-renders the element, which is the carousel desync above in another
form. USE a Vue-native equivalent where the app already has one (its date field, for
example). Otherwise own the lifecycle: `Plugin.getOrCreateInstance(el, config)` in
`onMounted`, `.dispose()` in `onBeforeUnmount`, and no `data-*-toggle` on the element.
Check [versions.md](versions.md) first: an app on an older Tabler doesn't have these
components.

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
