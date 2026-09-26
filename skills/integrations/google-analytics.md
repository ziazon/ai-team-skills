# Google Analytics (GA4) / Tag Manager

## Id types are not interchangeable — verify the prefix before deploying (2026-07-21)

- **GA4 measurement ids start `G-`; Google Tag Manager container ids start `GTM-`.** A
  gtag.js integration (`gtag/js?id=<id>` + `gtag('config', id)`) only works with a `G-` id.
  Fed a `GTM-` id it fails **silently**: Google's endpoint still returns 200 and serves a
  script, no console error — events just never reach any GA4 property. Worse than a crash.
- Users conflate them: one user supplied a `GTM-` id when asked for the GA4 measurement id
  (they had created a Tag Manager account, not a GA4 property). Where the real id lives:
  **GA → Admin → Data streams → (web stream) → Measurement ID**.
- Verify activation END-TO-END, not by deploy success: (1) id present in the shipped JS
  bundle (grep the built asset — `VITE_*` vars are inlined at build time, so the deploy
  pipeline needs a build-arg path); (2) pre-consent: zero googletagmanager requests and
  `window.gtag === undefined`; (3) post-consent click: gtag script src carries the right id,
  dataLayer populated, consent flag stored; (4) final hop = GA4 Realtime shows the hit
  (only the property owner can see this — hand it to the user as the closing check).
- A public analytics id is a repo **variable**, not a secret (`vars.` in Actions, not
  `secrets.`).
