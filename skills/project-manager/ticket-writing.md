# Project manager — writing & fixing tickets

How to draft a QA-ready ticket (**Mode B**, the ticket template) and how to bring a
thin/technical ticket up to that bar (**Mode D**). Both use the **plain-language** skill for
all prose. Mode A ([SKILL.md](SKILL.md)) routes here when work needs a new/better ticket.

## Mode B — Draft a QA-ready ticket (the ticket template)

Write every ticket so a **non-technical QA/UX tester** can pick it up and verify it with
zero code knowledge. Use the **plain-language** skill for all prose. Draft it, show the
user, and **only create it after they approve** (adjust on feedback).

Gather: what changed/should change, where in the app it shows up, which user roles can
reach it, and what "working" looks like. If you don't know the user-facing surface, ask
or inspect the app — don't hand-wave the test steps.

**Ticket title** — a plain-language headline of the user-facing outcome (see
plain-language "Titles"). No file paths or internal codenames.

**Description body** — use these sections:

```markdown
**What this is**
1–3 plain sentences: what changed (or needs to change) and why it matters to a user.

**Where to find it**
How a tester navigates to it: the exact page/menu/button path, and which kind of
account/role they need to be signed in as.

**How to test — happy path**
Numbered, click-by-click steps a non-technical tester can follow exactly.
1. Sign in as <role>.
2. Go to <page>.
3. Do <action>.
4. ...

**What you should see**
The expected result for the happy path, in plain terms (the message, the saved value,
the screen that appears).

**Also check**
Bullets for the important non-happy-path cases that matter here, e.g.:
- Different user types: if more than one role can reach this, list each role and what
  they should / should NOT be able to do.
- Security/permissions: if multiple user types can use it, explicitly call out that a
  lower-privilege user must NOT be able to do/see the privileged thing. (The user cares
  about this — internal-only controls must not be exercisable by lower tiers.)
- Empty / error states: what should happen with no data, bad input, or a failure.
- Edge cases specific to this change.

**Out of scope / known limitations**
Anything intentionally not covered, so QA doesn't file it as a bug.

**Technical notes** (optional, for engineers — kept separate from the tester-facing copy)
Branch/PR, affected services, migration notes, etc.
```

Set sensible fields: issue type (Bug/Story/Task), the project key from pm-config,
labels per convention, and **assign QA / add the QA tester** if pm-config names one.
Confirm field choices with the user when unsure.

Decide security depth by reach: if the feature is usable by only one role, a light
"Also check" is fine; if **multiple user types** can use it, the security/permission
bullets are **mandatory**.

---

## Mode D — Make a specific ticket QA-ready

Take a thin/technical ticket and rewrite it into the Mode B template using the
plain-language skill: clear title, "where to find it," numbered happy-path steps,
expected results, the "Also check" (with security/role bullets if multiple user types),
and out-of-scope. Show the before→after and **confirm before editing** the ticket.
