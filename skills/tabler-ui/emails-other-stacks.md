# Tabler UI — transactional emails & non-Vue stacks

Part of the `tabler-ui` skill. Tabler outside a Vue SPA: email templates and
server-rendered (R/Shiny) usage. (This install's email pipeline and apps: `LOCAL.md`
beside this skill, when your copy keeps one.)

## Tabler transactional emails

Tabler's email templates ship as inlined `compiled.html` bodies; an app that sends them
through an email service keeps those bodies as its templates. Design learnings:

- **Logo imagery = reuse the app's already-public PNG, don't host a new asset.** If the
  app already serves its brand mark as a PNG at a public absolute URL (e.g. the login
  logo), reference that URL directly in the email — no new object-storage upload needed,
  and it's the same mark users already see. The header's text wordmark (`<a …>Acme</a>`)
  becomes `<a …><img src=… alt="Acme" …/></a>`.
- **Email-safe `<img>`:** explicit `width`/`height` HTML attrs **and** inline `style` (`display:
  block; width/height; max-width; border:0; outline:none; line-height:100%`). Size at an **exact
  integer fraction of the source** (160px source → display **80×80** = clean 2× retina).
- **Email clients don't render SVG reliably** — if the white/transparent logo variant for
  dark backgrounds only exists as an SVG, a dark-mode swap needs a hosted white *PNG*; defer
  unless asked. The dark logo on the light page bg is the common-case win.
- **Previewing an email HTML locally — on macOS use `qlmanage`, not headless Chrome.**
  Chrome `--headless` can get sandbox-killed inside a sandboxed agent session (exit 137 /
  "Mach rendezvous failed"). `qlmanage -t -s 700 -o . preview.html` reliably produces
  `preview.html.png` you can Read. **QuickLook renders OFFLINE** → a remote `<img src>` shows
  a broken-image box; to verify the actual logo, `sed` the remote URL to a **local copy** of
  the image first, then render. Substitute template variables (e.g. Liquid
  `{{ confirm_url }}`) with a dummy so links resolve.

(This install's template paths, brand asset URLs and publish flow: `LOCAL.md` beside this
skill, when your copy keeps one — *emails-other-stacks.md — Tabler transactional emails*.)

## R/Shiny + Tabler (htmltools, not Vue)

Tabler used as plain CSS over server-rendered htmltools tags (`div()`, `tags$…`); no reactive-JS-component conflicts here, but htmltools/text gotchas instead.

- **htmltools inserts whitespace between sibling tags → the browser renders it as a visible space.** `tagList(tags$strong("C"), "hallenging")` shows "C hallenging" (the source newline collapses to a space). For inline letter/word emphasis *inside* a word, build ONE HTML string and wrap with `HTML(...)`; escape the surrounding (translated) text with `htmltools::htmlEscape()` and swap only the known literal. Do NOT assemble inline runs as separate `tagList` children.
- **Tabler marketing type scale** (from `tabler-marketing.css`; available when the app's stylesheet `@import`s the Tabler bundles): `.hero-title` 3rem/black weight (responsive 2rem ≤768px); `.hero-description` = h2 (1.25rem), centered, `margin:0 auto; max-width:45rem` (`.hero-description-wide` = 61.875rem); `.section-title` = h1 (1.5rem/bold); `.section-description` = h3 (1rem). Utilities: `.fs-1`=1.5rem, `.fs-2`=1.25rem, `.fs-3`=1rem. **To make a section's header+body match the hero, use `.hero-title` + `.fs-2`.**
- **Beat Tabler's `img` rules with inline `style`** — logos size via inline `style="max-width:NNpx;height:auto"`; Tabler's `img` CSS otherwise wins.
- **Progressive enhancement from R:** emit a `div` carrying `data-*` attributes (e.g. a comma-joined list of labels to show) and let a page JS module enhance it; gating a card on data = just omit the `div` in the R `if`.

(This install's app and its interactive-widget specifics: `LOCAL.md` beside this skill,
when your copy keeps one — *emails-other-stacks.md — R/Shiny + Tabler*.)
