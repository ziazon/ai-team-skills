# Frontend — other stacks

Part of the `frontend` skill (split from `LEARNINGS.md`). Frontend learnings from stacks other
than the primary Vue 3 + Tabler one. (The projects these came from: `LOCAL.md` beside this
skill, when your copy keeps one — *other-stacks.md — Project names*.)

## [Vite + Vue 3 SPA over a CommonJS workspace types package]

Two build/dev pitfalls (each cost a broken build/blank app; **a live DEV smoke caught both — CI's `pnpm build` did not**). Applies to any Vite + Vue 3 app importing a linked CJS workspace package (`tsc`-emitted types/DTOs/enums).

- **Importing a named enum VALUE from a deep subpath of a CJS workspace package breaks `vite build` (Rollup).** The subpath resolves via pnpm symlink to a real path OUTSIDE `node_modules` (e.g. `libs/types/dist/x/enums.js`), so Rollup treats the CJS output as ESM and errors `"<Enum>" is not exported by …/enums.js`. **`vue-tsc` and `vitest` resolve differently and stay green — only the production `vite build` trips it.** Fix in `vite.config.ts`: `optimizeDeps.include` the subpath(s) (dev) + `build.commonjsOptions.include: [/node_modules/, /libs[/\\]types[/\\]dist/]` (build) so the CJS→ESM transform runs on the dist. A Node-`require`-based "browser-runtime guard" test does NOT catch this — it's a rollup/esbuild resolution issue, invisible until the first real deep-subpath enum value-import in the web.
- **A type imported in VALUE position breaks `vite dev` (blank app) while `vite build` only WARNS.** e.g. `import { createRouter, RouteLocationNormalized } from 'vue-router'` (a type). Rollup (build) warns + tree-shakes → CI green; `vite dev` (native ESM) throws `does not provide an export named '<Type>'` at module eval → the module fails → `main.ts` `bootstrap()` throws before `app.mount()` → blank page. Fix: `type` qualifier (`type RouteLocationNormalized`). jsdom unit tests don't run the full ESM graph so they miss it too. **Hardening: ESLint `@typescript-eslint/consistent-type-imports` makes type-as-value imports fail lint.**
- **Lesson (both): CI `pnpm build` passing ≠ the dev server boots.** Run a live dev smoke (boot `vite` + drive the app in a browser) for any web slice. In-app browser gotchas: `read_page` may return viewport 0x0 (empty a11y tree) → drive via `javascript_tool` (native value-setter + `input` event for v-model; RouterLink nav = click the actual `<a>`); full-page navigations reset an access-token-in-memory SPA → navigate WITHIN the SPA via router links to stay authenticated.

## [An R/Shiny SPA]

Server-rendered R/Shiny app (no JS framework). Routing via `shiny.router` (4 routes); template hierarchy layout → pages → components (`R/templates/…`); dynamic sections via `uiOutput()` + `output$page_x` in `R/server.R`. Page bodies translate via local fallback helpers `hp()`/`ap()`/`get_*_label(key, fallback)`; header/footer use `%||%`.

- **i18n "translated-nowhere" bug class (high value).** Translations are per-language JSON loaded whole — `get_lang` has NO per-key English fallback; page bodies fall back to English only via the `hp/ap/get_*_label` helper. So a key referenced in code but MISSING from `en.json` too (never defined anywhere) renders English in *every* language AND passes a cross-language key-parity check (all files are equally missing it). Guard with a test that (a) every fallback-helper key referenced in code exists in `en.json`, and (b) every language file has exactly the `en.json` key set.
- **Key-indirection for sensitive + translatable data.** Store opaque keys (`iv_NNNN`) in the encrypted file; keep the de-associated text + all per-language translations in an UNENCRYPTED file keyed by those keys; resolve at render with English fallback. Encrypts the sensitive *linkage* (which org said what) while the text flows through normal i18n.
- **Stamp each lang pack with its own code** (`translations[[code]]$lang_code <- code` in `R/lang.R`) so the active language is resolvable from the `lang` object (which otherwise holds only strings) — needed for dynamic-content lookups.
- **Translation workflow.** Edit `en.json` first (canonical), then fan out one subagent per language (each writes a JSON file or edits its locale file), merge, and validate: key-parity vs en, no empty values, none identical-to-English (catches untranslated). 12 user-facing langs (`SUPPORTED_LANGUAGES`); `es`/`fr` are fallback sources only, not selectable.
