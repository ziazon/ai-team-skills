# Service architecture — general principles

Cross-project architectural patterns and anti-patterns (project-agnostic). This install's
project-specific examples and build conventions: `LOCAL.md` beside this skill, when your
copy keeps one — *general-principles examples*.

## Preferred patterns (general)

- **Smart endpoint / composite auth:** one endpoint serves multiple caller types via a
  single guard that evaluates tiers in a fixed order and short-circuits on the first pass:
  internal admin → partner admin (scoped to a partner that owns the target) → SP
  employee → resource owner (self). Config is per-route allow-list (which tiers + which
  permissions). Build the infra generically; enable only the tiers a given route needs.
  Default-deny; fail safe.
- **Co-locate, don't re-IPC:** once a service absorbs another's module, call it in-process
  via DI. Keep the interservice HTTP client only for still-external services.
- **Own the write, read the view:** route writes through the service that owns the domain
  (add an IPC there if missing); for reads, query the pre-joined read-model views directly.
- **Incremental migration off a legacy engine:** replace the client-facing endpoint
  (new URL + correct auth + docs + tests), keep delegating to the legacy engine under the
  hood when reimplementing it is large/risky, then delete the old endpoint after confirming
  nothing else uses it.
- **Boot-time registration over data migrations** for things like permissions/roles —
  but gate it (advisory lock to serialize instances + content-hash "skip if unchanged")
  so it doesn't write on every boot.
- **Minimize the encrypted surface via key-indirection.** When sensitive data must be both
  protected AND processed (translated, indexed, edited), separate the sensitive
  *association* from the de-associated *content*. Store opaque keys where the sensitive
  linkage lives (encrypted); keep the content — plus its translations — in plaintext keyed
  by those keys. Decrypting then reveals only keys, and the content alone isn't sensitive.
  (E.g. survey answers keyed by opaque IDs in the encrypted file, with the answer text +
  translations in an unencrypted file keyed by those IDs: the respondent↔answer link stays
  secret while the text flows through normal i18n. This install's worked example:
  `LOCAL.md` beside this skill, when your copy keeps one — *general-principles examples*.)
- **Search before you build — the capability is often already there.** Before speccing a
  "missing" feature, grep ALL the repos (legacy + new services). Logic the team believes is
  lost often lives on in the legacy app, or was already ported to a newer service under
  another name; a re-specced feature can turn out to be a different existing flow entirely.
  Discovery beats guessing — and a wrong guess in the plan costs more than the grep. (This
  install's worked example: `LOCAL.md` beside this skill, when your copy keeps one —
  *general-principles examples*.)
- **Derive a classification from an existing FK/column instead of adding a column + migration.**
  `is_active` computed as `deactivated_at IS NULL`, not stored — zero migration, always
  consistent, "every existing row starts active" holds for free. Prefer a derived read-side
  value when the truth already exists in the data. Caveat: derivation breaks if the value
  must ever be set independently of its source — confirm it won't before committing.
  (This install's example: `LOCAL.md` beside this skill, when your copy keeps one —
  *general-principles examples*.)
- **External-API data on list rows → hybrid, never N+1.** When a list needs per-row data from a
  third party (e.g. Stripe balances + payment-method validity across an A/R dashboard): keep a
  **synced read-model** for the sortable/filterable columns and **on-demand refresh of only the
  visible page** for freshness. Don't fan out one external call per row at render time.
- **Same screens, two audiences, gated by tier.** Internal-admin management and self-serve are often
  NOT two separate UIs — they're the SAME permission-gated screens (e.g. one admin route set
  authorized both for a customer's own staff AND, via internal permissions, for your admins).
  Build the screen once; expose/withhold actions by the matched auth tier. Saves a whole
  parallel build, but you MUST verify the lower tier can't reach the privileged actions.
  (This install's example: `LOCAL.md` beside this skill, when your copy keeps one —
  *general-principles examples*.)
