# Tabler UI — forms, field widgets & filter UIs

Part of the `tabler-ui` skill. How form inputs, validation, and filter controls are built
on Tabler. All entries `[Vue 3]`. (This install's stack tag and component names: `LOCAL.md` beside this skill, when your copy keeps one.)

## Contents

- [Forms/validation exception](#formsvalidation-use-shared-field-components) · [Shared form-field widgets](#shared-form-field-widgets--reuse-dont-hand-roll)
- [Currency/money input](#currencymoney-input) · [Removable form-row control](#removable-form-row-control--subtle-btn-close-grouped-by-the-label)
- [Filter chip bar](#filter-chip-bar--a-teleported-popover-per-chip) · [Date/datetime display](#datedatetime-display)

## Forms/validation: use shared field components

Use a shared set of field components (text, select, number…) wired to vuelidate, not raw
Tabler inputs — they render Bootstrap `is-invalid` + `.invalid-feedback` automatically.
(This install's components: `LOCAL.md` beside this skill, when your copy keeps one — *forms-filters.md — Forms/validation*.)

- Validation error display: per-field uses Tabler's red `.invalid-feedback`; an aggregated
  error list should carry `text-danger` to render red (a plain `<ul>` won't).
- **HTTP 422 is always inline, never a toast.** Attach field-addressable validation
  messages to the matching shared field via Vuelidate external results. When a 422
  expresses a cross-field or form-wide invariant and has no field path, render its
  message in a form-level `.invalid-feedback.d-block` region beside the relevant
  controls. Reserve toasts for network failures and non-validation responses. Prevent
  known cross-field invariants in the UI as well; server validation remains the safety net.

## Shared form-field widgets — reuse, don't hand-roll

Keep one set of generic, vuelidate-wired form-field components (behind a barrel
`index.ts`) and import from there instead of writing raw Tabler
`form-control`/`form-select`/`form-switch` inputs — they render the Bootstrap
`is-invalid` + `.invalid-feedback` plumbing for you. The same set can build a filter UI
(operator picker + per-field value widgets). A useful set: text, number, date, date
range, select, multi-select and toggle fields, plus currency / password / rich-text.
(This install's components and their props: `LOCAL.md` beside this skill, when your copy keeps one —
*forms-filters.md — Generic form-field widgets*.)

- **Select field** — single value from `{label, value}[]` options. Good for an operator
  picker (equals / contains / between …).
- **Multi-select field wrapping `vue-multiselect`** — its model is an array of the
  selected **option OBJECTS** (`{label, value}[]`), NOT raw values (`trackBy: 'value'`,
  `optionLabel: 'label'`). To recover raw values, map the selected options' `.value`.
  Pass `:allow-empty="true"` so users can clear the selection. Use for multi-select
  enum/status filters.
- **Toggle field** — a Tabler `.form-switch`; make its model **`boolean | null`
  (tri-state)** — `null` is a real "untouched/unset" value, ideal so a toggle can mean
  "no filter" until the user interacts with it. When an external label already exists,
  give the field a way to suppress its own label text so it isn't duplicated.
- **Date field** — single date via `@vuepic/vue-datepicker`; model is a `yyyy-MM-dd`
  string in UTC, with a separate date-range field for from/to. (Distinct from the
  read-only date display below, which is for rendering, not input.)
- **Widget-by-type pattern** — drive the right widget off a field's declared type:
  enum → multi-select, boolean → toggle, date → date field, number → number field,
  text → text field. Keeps a generic builder (e.g. a filter panel) data-driven instead
  of a switch of bespoke markup.
- **Don't import a workspace types package's runtime enum VALUES into these SFCs /
  eagerly-loaded modules** when that package depends on reflect-metadata — it crashes.
  Key option lists by their string value (or use a locally-redefined enum) when
  populating `options`. (Same rule as the badge-class mapping in layout-visuals.md;
  applies to building select/multi-select option arrays too.)

## Currency/money input

Wrap the input in a Tabler `.input-group` with a leading
`<span class="input-group-text">$</span>` prefix; the `<input class="form-control">` edits
whole dollars. Put the `.invalid-feedback` **inside** the `.input-group`, after the input, so
Bootstrap's adjacency rule (`.is-invalid ~ .invalid-feedback`) still renders the red error.
Have the currency field v-model cents while it edits dollars, and mirror the number
field for the label/validation wiring; just add the input-group wrapper. (This install's
files: `LOCAL.md` beside this skill, when your copy keeps one — *forms-filters.md — Currency/money input*.)

## Removable form-row control — subtle `btn-close`, grouped by the label

For a "remove this row" affordance on a filter/form row, do NOT use a bordered
`btn btn-icon` with an `IconX` pinned to the cell corner (`position-absolute end-0`):
it reads as a heavy floating box, and in a fixed-width grid cell it floats **far from
a narrow control** (e.g. a boolean toggle) — visually disconnected from the field it
removes (user rejected exactly this). USE Tabler/Bootstrap's `btn-close` (a borderless,
theme-aware × via CSS mask — auto-inverts under `data-bs-theme="dark"`, no
`btn-close-white` needed), placed **inline right after the field label** in a
`d-flex align-items-center gap-2` wrapper, so it's clean and clearly grouped with its
field for every control type. Reference: the Tabler bundle's dashboard
`form-elements.html` page (`btn-close`; label-side secondary content uses
`form-label-description`). Make it opt-in on the reusable row component (a `removable`
prop + `remove` emit) so standalone uses stay unaffected. (This install's reference line
and files: `LOCAL.md` beside this skill, when your copy keeps one — *forms-filters.md — Removable form-row control*.)

## Filter chip bar — a teleported popover per chip

Airtable/Linear-style filter bar: applied filters as removable `bg-blue-lt` badge
**chips** + a dashed "+ Add filter" button, each opening a popover. (This install's
component names and ticket: `LOCAL.md` beside this skill, when your copy keeps one — *forms-filters.md — Filter chip bar*.)

- **Anchor each popover with its own teleported dropdown** (see the dropdowns entry in
  [components-js.md](components-js.md)) — wrap the chip (and the add button) in the
  dropdown's `#trigger="{ toggle }"` slot and put the editor in its `#default="{ close }"`
  slot. The teleported menu escapes the card/`.table-responsive` overflow and pins to that
  specific trigger. Multiple chips in a `d-flex flex-wrap` each become a flex item (the
  `.dropdown` wrapper divs lay out horizontally). Reuse the popover for **edit** (seed the
  editor from the chip's clause; the menu remounts on each open so it re-seeds) — no
  separate edit modal needed.
- **Chip remove ✕ must `@click.stop`** so it emits `remove` without also toggling the
  popover open (the body button is the edit affordance).
- **Operator picker as a Tabler `.form-check` radio list** (not a `<select>`) reads
  best in a roomy popover and matches the reference; hide it for single-operator types
  (enum/boolean). Keep a draft + explicit "Apply Filter" so it commits on confirm only.
- **Restyled table header chrome:** grow the table search full-width (a block mode →
  `d-block` + drop `form-control-sm`) in a `row > col`, with column-visibility + CSV as
  `btn btn-icon` (title tooltips) in a `col-auto .btn-list`.

## Date/datetime display

Use one shared date/datetime display directive (or helper), NOT manual per-view
formatting: a full-datetime form plus a date-only form with timezone-from-string parsing.
Give tables matching date / datetime cell components and reuse them. (This install's
directive and cells: `LOCAL.md` beside this skill, when your copy keeps one — *forms-filters.md — Date/datetime display*.)
