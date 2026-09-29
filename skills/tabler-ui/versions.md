# Tabler UI — versions: bundle vs. app, and what changed in v1.6

Part of the `tabler-ui` skill. Read this when you copy markup from the reference bundle,
when an app upgrades `@tabler/core`, or when a Tabler class or token "does nothing".
(This install's bundle version and each app's pinned version: `LOCAL.md` beside this
skill, when your copy keeps one — *Reference templates*.)

## Contents

- [The bundle can be ahead of the app](#the-bundle-can-be-ahead-of-the-app)
- [v1.6 changes that bite app code](#v16-changes-that-bite-app-code) · [New in v1.6](#new-in-v16)

## The bundle can be ahead of the app

The reference bundle is upgraded in place, but each app pins its own `@tabler/core`.
Markup copied from a newer bundle can use classes, tokens or `data-*` components that the
app's installed Tabler does not have. Nothing errors when that happens: an unknown class
renders unstyled, and an unknown `data-bs-toggle` does nothing.

- **Before copying from the bundle, compare the two versions.** The bundle's version is
  in the header of `tabler-admin/dashboard/dist/css/tabler.css`. The app's version is
  `@tabler/core` in its `package.json`, or better, in the lockfile.
- **If the bundle is newer, grep the app's installed `dist/css/tabler.css` for each class
  you copied** before you trust the render. Upgrading Tabler is a separate change with its
  own review; don't fold it into a feature.
- **Upgrade notes are published one page per release** under the Tabler docs'
  getting-started → upgrade section, and at <https://tabler.io/changelog>.

## v1.6 changes that bite app code

v1.6.0 was released 2026-09-25, with a 1.6.1 patch on 2026-09-28. These changes affect
code written against 1.5 or earlier:

- **`--tblr-*-rgb` tokens are deprecated** (they remain until 2.0). Colors are now defined
  in `oklch()`, and Tabler builds its own tints and hovers with
  `color-mix(in oklab, …)`. For new code, prefer
  `color-mix(in oklab, var(--tblr-secondary) 8%, transparent)` over
  `rgba(var(--tblr-secondary-rgb), 0.08)`. Tabler's own tokens moved the same way: for
  example `--tblr-dropdown-link-hover-bg` is now `var(--tblr-hover-bg)`, not an
  `rgba(var(…-rgb))`. Don't copy an old token definition as your pattern.
- **The focus indicator is now a solid 2px `outline`, not a `box-shadow` halo.** A custom
  control that copied the old `box-shadow` focus ring now looks different from native
  fields. Match the outline instead.
- **The default gray scale is neutral now; the blue tint is gone.** Hard-coded
  blue-gray hex values that used to match Tabler's grays now look off.
- **`.form-hint` is renamed `.form-text`.** The old name is kept as an alias; use
  `.form-text` in new markup.
- **Litepicker is deprecated.** v1.6 ships its own Datepicker, built on Vanilla Calendar
  Pro.
- **The `tabler.tabler` JS namespace is deprecated** (`getColor()`, `hexToRgba()`). Read
  the CSS variable directly instead.
- **A bare `.legend` still renders a dot, but `.legend-dot` is the proper class.**
- **Stricter TypeScript.** Component configs are now fully typed, which can surface type
  errors in loosely typed code that constructs Tabler components.
- **Every toggle attribute also accepts a `data-tblr-*` prefix** (`data-tblr-toggle`
  alongside `data-bs-toggle`). Treat both prefixes the same way under the
  don't-use-vanilla-JS rules in [components-js.md](components-js.md).

## New in v1.6

- **Components:** Datepicker (single, multiple and range), Sparkline (inline SVG charts
  from `data-bs-values`), Legend (`.legend-lg`, optional toggle mode), Signal (stepped
  strength bars), Password Strength (fires `change.bs.strength`), OTP Input, Clipboard,
  and Confetti.
- **Converted to full JS components** (with instances, methods and events): Autosize,
  CountUp, InputMask, Sortable and SwitchIcon. SwitchIcon adds a `switch-icon-loading`
  state.
- **Layout:** `.navbar-floating` and `.offcanvas-floating`. The native `<dialog>` element
  is styled to match modals, and `.modal-blur` blurs the page behind a modal.
- **Demo pages** for each of these are in the bundle: `datepicker.html`, `legend.html`,
  `sparkline.html`, `signal.html`, `password-strength.html`,
  `2-step-verification-code.html` (OTP), `clipboard.html`, `confetti.html` and
  `billing.html`.

Every new component is vanilla JS, so the Vue lifecycle rules in
[components-js.md](components-js.md) apply to all of them.
