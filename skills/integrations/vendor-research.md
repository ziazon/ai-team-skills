# Integrations — third-party API / vendor research

Scoping external APIs before integrating: the reusable gotchas of researching a vendor
landscape. (A worked domain catalog with access models: `LOCAL.md` beside this skill, when
your copy keeps one — *Automotive vendor API catalog*.)

## [pattern] researching a third-party API / vendor landscape (before integrating) `[seen: 2026-06-29]`

When scoping which external API/vendor to integrate, the research itself has reusable gotchas:

- **Price opacity is the norm — plan an RFQ, not a web search.** Across an entire vendor class (parts-pricing, vehicle-data, estimating APIs), essentially **every serious vendor hides pricing behind "Book a Meeting" / sales** — only free-tier credits + "flexible pricing" appear publicly. So a "which is cheapest / best margin" question is **structurally unanswerable from public data**; the deliverable is a **shortlist + an RFQ**, not a number. Tell the user that up front instead of burning research trying to find prices that aren't published.
- **Marketing FAQ ≠ binding terms.** A vendor product page may say "Yes, consumer-facing use is supported" while the actual **Terms** grant only a generic non-transferable limited license and **bar resale/sublicense/derivative + cap caching** (e.g. Edmunds ToS: commercial OK but single approved app + **purge cache after 24h** + no service-bureau). For anything you'll persist/redistribute (a stored quote), the **license + caching rights must be confirmed in a signed contract**, and you must read the ToS, not the FAQ.
- **When using the `deep-research` workflow for vendor research, it degrades silently under upstream rate-limiting.** A "Server is temporarily limiting requests" storm makes the adversarial-verify votes fail, and those claims come back with **`0-0` votes = "never checked," NOT "refuted."** Always read the `failures` array and the vote counts before trusting a "killed/refuted" list — a degraded run can look like it disproved real vendors when it just never verified them. Re-running may hit the same limit; **targeted first-hand `WebFetch`es of the 2-3 key pages** (a pricing page, a ToS) are a cheaper, more reliable supplement than a full re-scour.
- **Keep scour prompts tight.** A very long, dense multi-part `args` string can fail the workflow's scope-decomposition agent (`StructuredOutput retry cap (5) exceeded`) at agent #1, killing the whole run before any search. If a scour fails at scope, **shorten/flatten the prompt** (fewer nested clauses, plainer enumeration) and relaunch — that fixed it here.
