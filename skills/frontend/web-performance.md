# Frontend — web performance & SEO auditing (Lighthouse)

Part of the `frontend` skill. How to **measure** page performance/SEO with Lighthouse and
the ordered **remediation playbook** for public pages. Target score is **95+ across all
four categories** (Performance / Accessibility / Best Practices / SEO); closer to 100 is
better. Compare against your best-performing reference app. In the worked example below,
an HTML-first reference app scored ~95/96/96/92 while a hydration-heavy SPA's staging
scored **19**/89/77/61 — the gap is structural, explained below. (This install's reference
apps, hosts and scores: `LOCAL.md` beside this skill, when your copy keeps one —
*web-performance.md — Reference apps and target*.)

## Performance triage (where to look before you optimise)

Measure first, then fix the proven bottleneck — general web-perf mechanics that frame the
remediation playbook below:

- **Core Web Vitals "Good" thresholds:** LCP ≤ **2.5s**, INP ≤ **200ms**, CLS ≤ **0.1**. These are
  the pass/fail bar for the Performance-adjacent field metrics.
- **Symptom → where to measure:**
  - *Slow first load* → bundle size / TTFB / render-blocking resources (the worked example's
    killer was a ~1.5 MB render-blocking CSS bundle — see the baseline below).
  - *Sluggish interaction* → long tasks >50ms on the main thread / excess re-renders / layout thrash.
  - *Slow after navigation* → API waterfalls (serialised requests that should be parallel).
- **Synthetic vs RUM:** use Lighthouse / DevTools for reproducible lab runs and isolating a specific
  regression; use a `web-vitals`-style RUM library to validate the fix actually helped real users
  (lab numbers can improve while field metrics don't, and vice-versa).
- **Perf budgets in CI** (bundlesize / Lighthouse CI) catch silent regressions. A
  PurgeCSS-safelist gotcha (a theme-variant purge shipped a bloated/broken bundle) is the kind of
  bundle regression that makes this a live concern, not a hypothetical one — see the Regression
  gate section. (This install's instance: `LOCAL.md` beside this skill, when your copy keeps
  one — *web-performance.md — Performance triage, project examples*.)

## Running Lighthouse (the DevTools panel is a GUI over a CLI)

The Chrome DevTools "Lighthouse" tab runs the **Lighthouse engine**, which also ships as a
Node CLI — so audits are fully runnable headlessly, no GUI needed. Use the helper:

```bash
scripts/lh-audit.sh <url> [desktop|mobile|both] [outdir]
# e.g. scripts/lh-audit.sh https://staging.example.com/ both ./.lighthouse
```

It runs a locally installed `lighthouse` CLI (it never downloads one) with a **pinned config**, saves timestamped JSON+HTML per form-factor,
and prints category scores, Core Web Vitals, and the top failing audits ranked by estimated
savings. Parse the `.report.json` for detail; open the `.report.html` for the full panel view.

**Comparability rules — get these wrong and the numbers lie (both were wrong in the worked
example's first screenshots; this install's specifics: `LOCAL.md` beside this skill, when
your copy keeps one — *web-performance.md — Running Lighthouse, project framing*):**

- **Disable extensions.** A dirty Chrome profile can cost 40+ perf points; Lighthouse warns
  "Chrome extensions negatively affected this page's load performance." The helper passes
  `--no-extensions --headless=new`. The worked example's staging **19** was partly an
  extensions artifact — the clean-profile number is higher (but still far from 95).
  **Incognito is not the same thing as a clean Lighthouse profile**: extensions can be allowed
  in incognito, localStorage/theme state can persist or be recreated differently, DevTools may
  use a different Lighthouse version/config, and a cached/stale deploy can still be audited.
  When a user screenshot shows a category mismatch (e.g. Accessibility 96 while clean CLI
  reports 100), ask for the expanded failing audit ID and DOM node; the category score alone
  is not actionable.
- **Match the form-factor.** `--preset=desktop` = desktop viewport, **no throttling**. Default
  (no preset) = **mobile**: ~4× CPU throttle + slow-4G. In the worked example the reference
  app's run was **desktop** and the staging run was **mobile** (the phone mockup). Never
  compare desktop-vs-mobile — the helper runs `both` so you diff like-for-like.
- **Separate app-cost from infra-cost.** Audit **staging (deployed)** *and* a **local
  production-SSR build** and diff them. Local prod-SSR isolates the bundle/app from staging
  network latency; a big staging-vs-local gap = infra (TTFB, no CDN, a cold container/scheduler
  start), a small gap = the app itself.
- Run 2–3× and take the median — Lighthouse lab numbers have run-to-run variance. One homepage
  run after a release showed desktop Performance vary from 99 to 96 with similar FCP/LCP but a
  transient TBT spike, while Accessibility/Best Practices stayed at 100.

## Why an HTML-first app beats a hydration-heavy SPA (a worked example)

This install's original case study, with its app names, hosts, dates and asset names, is in
`LOCAL.md` beside this skill, when your copy keeps one — *web-performance.md — The structural
finding and measured baseline*. Anonymized:

Reference A (the ~95 scorer) is really two sibling repos, both **HTML-first, JS-minimal** —
the page arrives as real HTML and ships little-to-no client framework:

- One is Go + **`a-h/templ`** — server-rendered HTML components, **nothing to hydrate**.
  Near-zero client JS ⇒ Total Blocking Time ≈ 0.
- The other is server-rendered `.tpl.html` templates + **Alpine.js** islands (~15KB) bundled
  by Vite (single small `main.ts`, `@rollup/plugin-html` multi-page). Progressive enhancement,
  not a SPA — tiny JS sprinkled onto static HTML.

**Reference B is a Vue 3 SSR app.** Its public pages SSR real HTML (good for LCP/SEO/content),
but ship a huge **render-blocking payload**. The public landing page transitively imports the
whole app's CSS and much of its JS. **A public marketing page must not pay to boot the admin
app** — but the specific symptom is *transfer size / render-blocking*, not hydration cost.
Verify with data, don't assume (see the measured baseline below).

### Measured baseline — Reference B's staging `/` (clean profile)

Clean-profile scores were **Perf 60 desktop / 50 mobile** (the DevTools-panel **19** was an
extensions artifact — always audit `--no-extensions`). The bottleneck is **NOT** main-thread /
hydration: **TBT was 0ms desktop / 250ms mobile, JS execution 0.7s, TTFB 370ms** (infra is fine).
It is **render-blocking transfer weight**, LCP 4.3s desktop / **25.7s mobile**, 4.2 MB total:

| Culprit | Transfer | Note |
| --- | --- | --- |
| **The single app CSS bundle** | **~1.46 MB** (one file) | render-blocking; ~1.66 MB reported "unused" — unpurged Tabler/FontAwesome. **The #1 fix.** |
| Unused JS: the forms, main index, stores and Vue runtime chunks | ~1.0 MB unused | the form-builder/admin chunks shipped to a landing page — code-split them off public routes |
| 3× hero SVGs | ~538 KiB | heavy LCP element |
| A variable web font (`.woff2`) | ~345 KiB | subset + preload |

**Lesson: hydration TBT was a red herring for this app; the killer was a ~1.5 MB render-blocking
CSS bundle + ~1 MB of unused JS.** Measure before prescribing — image tuning can't fix a
render-blocking 1.5 MB stylesheet, and neither can partial hydration (TBT was already ~0).

## Remediation playbook (ordered by MEASURED impact, each tied to its Lighthouse audit)

Do these **top-down** — in the worked example steps 1–2 were ~90% of the gap (LCP/FCP), the
rest polish. The order comes from that baseline; re-audit after each step to confirm movement,
and re-order if your own baseline says otherwise. (This install's playbook, with its route,
component, asset and release names: `LOCAL.md` beside this skill, when your copy keeps one —
*web-performance.md — Remediation playbook*.)

1. **Purge the CSS bundle** *(fixes: "Reduce unused CSS", Render-blocking, LCP/FCP — the dominant
   lever when a large stylesheet is render-blocking).* An unpurged component-library + icon-font
   payload (e.g. Tabler + FontAwesome) can be well over a megabyte, most of it unused.
   Tree-shake/purge to just what's used (PurgeCSS/Tailwind-style content scan, or import only
   the library partials + the specific icons in use, not the whole packs). Consider inlining
   critical CSS and loading the rest non-blocking. In the worked example this one change was
   expected to move FCP (3.5s→~1s desktop) and LCP more than everything else combined.

2. **Code-split JS off public routes** *(fixes: "Reduce unused JavaScript").* A landing page
   should not pull form-builder, store, or admin chunks it doesn't need. **Route-level
   code-split** so a public page pulls only its own chunk, never the admin SPA (admin routes,
   data tables, editors, map/rich-text libraries, form builders). Verify the public entry chunk
   in `dist` excludes admin/vendor code (analyze the Rollup output). Lazy
   `defineAsyncComponent`/dynamic `import()` below-the-fold; analytics (GTM/Segment/Hotjar)
   **`async`/deferred**. (NB: hydration TBT was ~0 in the worked example — this is about
   *transfer size*, not main-thread; don't bother with partial hydration until TBT actually
   shows up.)

3. **Trim the LCP path** *(fixes: LCP, "Preload LCP image", "Serve next-gen formats").* Heavy
   hero SVGs — optimize/simplify them (SVGO) or rasterize to sized WebP where they're
   photographic; **preload the LCP hero** + `fetchpriority="high"`, eager (never lazy-load the LCP
   element), `loading="lazy"` for the rest. **Subset + preload the web font** and
   `font-display: swap`.

   For public components, use this image-loading contract:
   - LCP/first hero image: `fetchpriority="high"` and `loading="eager"`.
   - Secondary carousel images, logo strips, cards, map popups, galleries, and below-the-fold
     section artwork: `loading="lazy"`.
   - All public `<img>` tags: `decoding="async"`.
   - Add/keep a static public-image contract test that scans public component files and fails
     when a public `<img>` lacks an explicit loading strategy or async decoding. In the worked
     example it caught nine missing attributes across the header, content sections, cards,
     popups and gallery views before a release.

4. **Kill layout shift** *(fixes: Cumulative Layout Shift — already low at ~0.01 in the worked
   example; keep it there).* Explicit dimensions on images/embeds, reserved space for async
   content, `font-display: swap`.

5. **Edge/caching & transfer** *(fixes: TTFB, "Enable text compression", "Efficient cache policy").*
   Lower priority when TTFB is already fine (it was 370ms in the worked example) — but ensure
   `compression()` gzip/brotli on the SSR HTML + assets, long-lived immutable cache headers on
   hashed assets, and short-TTL/CDN caching of anonymous SSR HTML.

6. **SEO category** *(fixes: SEO score).* An SSR foundation should give each public route a
   dynamic `<title>`/description, canonical, and **JSON-LD** structured data (e.g. breadcrumb
   lists) from one SEO utility. Audit each public route for: unique title + meta description,
   canonical, Open Graph/Twitter tags, valid structured data, crawlable links, and
   `robots`/sitemap coverage. SEO ≠ Performance — a page can be fast and still lose SEO points
   on missing meta.

7. **Accessibility & Best Practices** *(fixes those two categories).* Contrast, form labels, alt
   text, heading order, `lang`, no console errors, HTTPS, no deprecated APIs. Mostly mechanical —
   Lighthouse lists each failing element with the DOM node.

## Regression gate — run it after a staging release

Scores rot silently. Wire the audit into whatever gate runs **after a staging release, against
the deployed host**, and only when the released commits touched public-page paths. (This
install's wiring, its release step, host and baseline log: `LOCAL.md` beside this skill, when
your copy keeps one — *web-performance.md — Regression gate*.)

- **Trigger:** `git diff --name-only <prev-tag>..<new-tag>` over the public path set (public
  views, public layout components, public content sections, the public layout, the SSR entry,
  the server, the bundler config, global CSS, `package.json`) returns anything.
- **Run:** `lh-audit.sh https://staging.example.com/ both` — median of 3.
- **Compare + record:** against a baseline log kept in your project docs, which carries the
  current numbers, the floors, and the standing caveats. Append a block per release (the
  helper prints a `ROW|` line for this).
- **Outcome:** a tripped floor or a newly-failing insight is investigated before the ticket
  moves to Staging. It is a signal, not an automatic block — and **SEO is not gated on
  staging** when staging is served non-crawlable (`is-crawlable` always fails there; measure
  SEO on prod).

Why here and not on every PR: it fires only when something actually shipped, it measures the
real deployed artifact rather than a preview build, and it costs nothing on the many PRs that
never touch a public page.

**Open option:** **Lighthouse CI** (`@lhci/cli autorun`) with assertion budgets against a
preview build in CI, which would catch a bundle-bloating PR *before* merge rather than after
release. Start in `warn` mode to calibrate budgets, then flip to `error`.

**Structural guards worth having** in lint / unit tests → CI (no score): a public-entry-imports
test (the public entry must not import admin code), a public-image-attributes test (explicit
loading strategy + `decoding="async"`), a production purge-CSS test, a main-CSS test, and a
dependency-cruiser `no-public-to-private` rule.
