# Integrations — GitHub/gh & external-write gating

GitHub Packages/`gh` gotchas (classic-vs-fine-grained PATs, secret masking, `gh pr edit`
Projects-classic failure) and the Claude Code auto-mode classifier gating external-system
writes (Jira/Slack/GitHub issue create).

## GitHub Packages npm registry rejects fine-grained PATs `[seen: 2026-06-29]`

Publishing `@yourscope/*` to GitHub Packages (`npm.pkg.github.com`) needs a **classic** PAT, not a fine-grained one. A fine-grained PAT (`github_pat_…`) *authenticates* cleanly — `npm whoami` returns the user, `/user` and `/orgs/{org}` return 200 — but every real package op (`npm view`, publish, `GET /orgs/{org}/packages?package_type=npm`) returns **`403 … token provided does not match expected scopes`**. The npm/RubyGems registries validate classic scopes fine-grained tokens don't carry (ghcr.io containers DO support fine-grained — don't generalize from it). Fix: classic PAT with **`repo` + `write:packages`**, SSO-authorized for the org. Diagnose token capability via the `x-oauth-scopes` response header on `/user` (classic tokens list scopes there; fine-grained return it empty).

## [pattern] GitHub-Actions-style secret masking for token commands `[seen: 2026-06-29]`

When running commands that touch a token (registry auth, API calls, reading `.npmrc`), pipe every stream through a **pattern-based** redactor so a value can't leak to the log — and make it pattern-based (not value-based) so it never has to handle the secret itself. Masks: `github_pat_…`, `gh[pousr]_…` (classic/app/oauth/server/refresh/user), `_authToken=…`, `Authorization: (Bearer|token) …`, `x-access-token:…@`. Combine with the never-print discipline: source `.envrc` (`set -a; . ./.envrc; set +a`), reference `$GITHUB_TOKEN` by name, presence-check with `[ -n "$VAR" ]`, and test token *capability* (read / `npm publish --dry-run`) rather than printing it — dry-run packs + auth-checks without a permanent upload.

## [GitHub/gh] `gh pr edit` fails on Projects-classic deprecation

`gh pr edit <n> --title/--body` can exit 1 with `GraphQL: Projects (classic) is being
deprecated ... (repository.pullRequest.projectCards)` — it queries projectCards and the
deprecated field errors, aborting the whole edit (title/body NOT applied; verify with
`gh pr view`). Workaround: edit via REST, which doesn't touch projects:
`gh api -X PATCH repos/<owner>/<repo>/pulls/<n> -f title="..." -F body=@bodyfile.md`
(`-F field=@file` reads the body from a file; `--jq '.title'` to confirm). Same applies to
other `gh pr`/`gh issue` subcommands that pull project data.

## Jira ticket creation via MCP can be auto-DENIED when the ask was "fix", not "file"

The Claude Code auto-mode classifier blocked `mcp__atlassian__createJiraIssue` with `[External System Writes] ... the user's request was to fix the regression, not to file a ticket`. External-system writes (Jira/Slack/GitHub issue create) need the user's intent to point AT that write — a standing workflow rule ("always file a ticket") is NOT enough for the classifier. Don't try to work around it. Surface it to the user: "ticket not filed — say the word and I'll create it," and proceed with the rest (the PR is the real deliverable). To pre-authorize, the user adds a permission rule for the tool.

## Auto-mode classifier blocks writing an auto-executing external-upload HOOK until the user names that mechanism `[seen: 2026-07-11]`

Writing a user-level hook script such as `artifact-post-hook.sh` (a `PostToolUse`/`Artifact` hook that auto-mirrors every artifact to DO Spaces) was DENIED as `[Unauthorized Persistence] ... arms an unrequested automated upload pathway to an external destination`. Even though the user had verbally agreed to "auto-publish artifacts," the classifier treats **installing a standing hook that silently sends content to an external service** as its own decision needing explicit intent — a hook fires outside the model's visible actions, so "yes to the idea" ≠ "yes to this mechanism." Fix that cleared it: put the choice to the user via AskUserQuestion ("install the settings hook" vs "in-session convention" vs "manual"); their explicit selection of the hook option is the intent the classifier wants. Then the same file wrote through. Same family as the Jira-create block above — don't route around it, make the user name the mechanism.

## [DO Spaces / S3-compatible] hosting self-contained HTML artifacts via s3cmd `[seen: 2026-07-11]`

Publishing HTML to DigitalOcean Spaces (S3-compatible object storage) for shareable links — chosen over GitHub Pages because GitHub **Team** (not Enterprise Cloud) has no private-Pages access control. Gotchas, all live-verified: (1) **Tool** — use `s3cmd` (configured via `~/.s3cfg` with `host_base=<region>.digitaloceanspaces.com`); Spaces uses S3 **access keys** (DO console → API → Spaces Keys), separate from the `doctl` API token, and a machine's `aws` CLI default profile is usually real AWS, not DO. (2) **Content-Type** — upload with `--mime-type=text/html` or the browser downloads instead of rendering. (3) **Signed-URL scheme** — `s3cmd signurl s3://b/k <epoch>` emits an `http://` URL that DO 302-redirects to https; rewrite `http://`→`https://` up front (the SigV2 query signature is scheme-independent, stays valid) for a direct 200. (4) **Privacy model** — Spaces has no login wall: `--acl-private` + time-limited signed URL (SigV2 allows long expiries, not just 7 days), or `--acl-public` for a permanent unlisted URL; a private object's bare URL correctly 403s. (5) **Idempotent updates** — re-publishing to the **same object key** keeps a stable URL (good for a "living doc" that's refreshed in place).
