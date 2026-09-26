# DigitalOcean App Platform + doctl — learnings

App Platform (Dockerfile service + managed Postgres + PRE_DEPLOY jobs), Terraform
(`digitalocean/digitalocean` provider), and `doctl` multi-account gotchas. Dated by entry.

## PRE_DEPLOY migration job: bind DATABASE_URL on the JOB at RUN_TIME (2026-07-12)
- **Symptom:** the PRE_DEPLOY `migrate` job's container exits non-zero (`DeployContainerExitNonZero`),
  which fails the whole deployment; App Platform then **tears the failed app back down** (it 404s),
  so you lose the logs unless you grab them fast.
- **Root cause:** a database bindable var `${db-name.DATABASE_URL}` is **NOT available at build time**,
  and defining it only at the **app level** (esp. with `RUN_AND_BUILD_TIME` scope) does **not reliably
  reach a PRE_DEPLOY job**. The migration CLI then runs with no DB URL, falls back to `localhost`, and
  exits 1.
- **Fix:** bind `DATABASE_URL = ${db-name.DATABASE_URL}` **directly on each component that needs it**
  (the service AND the PRE_DEPLOY job), with **`scope = RUN_TIME`**. Keep only plain values (e.g.
  `NODE_ENV`) at app level. In Terraform HCL, escape the binding as `"$${db-name.DATABASE_URL}"` (the
  `$$` prevents HCL interpolation so the literal `${…}` reaches DO).
- Migrations don't auto-run; the PRE_DEPLOY job runs `node ./node_modules/typeorm/cli.js migration:run
  -d dist/database/data-source.js` (no `nest build` prefix — the Nest CLI isn't in the prod image).
- Grab a failed job's logs before DO cycles the app:
  `doctl apps logs <app-id> migrate --type run --context <ctx>`.

## doctl: DIGITALOCEAN_ACCESS_TOKEN env overrides context AND can misreport the account (2026-07-12)
- With **multiple `doctl` contexts** (`doctl auth list`), exporting `DIGITALOCEAN_ACCESS_TOKEN` makes
  doctl use that token over the selected context — but in this session `doctl account get` with the env
  token **misreported the wrong account** (showed a different context's account than the token actually
  belonged to). Cost a big false-alarm detour ("provisioned into the wrong account").
- **Ground truth for "which account does THIS token belong to":** hit the raw API, which is exactly what
  the Terraform provider does — `curl -s -H "Authorization: Bearer $TOKEN" https://api.digitalocean.com/v2/account`
  → `.account.email` / `.uuid`. Trust this over `doctl account get`.
- **Rules for multi-account doctl:** ALWAYS pass an explicit `--context <name>`; do NOT rely on the
  env-token path; never assume the "current" context. Terraform's `digitalocean` provider reads its own
  `token` (var), independent of doctl context — so the token in your tfvars is what determines the target account.
- App Platform **dev databases** (the in-app `database { production = false }` component) do NOT appear in
  `doctl databases list` (that lists standalone clusters) — they're attached to the app.

## Terraform digitalocean_app + project naming (2026-07-12)
- App Platform **app name** must be lowercase alphanumeric/hyphens (no dots/caps); a DO **project** name
  is free-form. Keep them as separate vars (`app_name` vs `project_name`) if you want e.g. project
  `Acme` + app `acme-api`.
- Remote state on **DO Spaces** works via the s3 backend (partial config): `endpoints = { s3 = "https://<region>.digitaloceanspaces.com" }`,
  `skip_credentials_validation/skip_region_validation/skip_requesting_account_id/skip_metadata_api_check/skip_s3_checksum = true`,
  Spaces keys via `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` env. `terraform init -backend-config=backend.hcl`.
- `github_actions_secret`: use `value` (not the deprecated `plaintext_value`) in `integrations/github` v6.13+.
- The DO GitHub source needs DO's GitHub app authorized for the repo (one-time OAuth; Terraform can't do it).
- **Claude can't run `terraform apply`**: the auto-mode classifier hard-blocks billable IaC applies even
  with an in-chat "yes" — the user must run it, or add a Bash permission rule.

## Cloudflare custom domain on an App Platform app (2026-07-14)
- **Provider is `cloudflare/cloudflare ~> 5`; resource is `cloudflare_dns_record` (NOT the old
  `cloudflare_record`).** v5 renamed it and uses `content` (not `value`); `ttl`, `name`, `type` required.
  When `proxied = true`, **`ttl` MUST be `1`** ("automatic") or Cloudflare rejects the record — gate it:
  `ttl = var.cloudflare_proxied ? 1 : 3600`.
- **Two pieces wire a custom domain:** (a) a `domain { name = ...; type = "PRIMARY" }` block on
  `digitalocean_app` (DO routes the Host + issues a Google-Trust-Services TLS cert; the app's default DO
  ingress hostname stays a working alias); (b) a `cloudflare_dns_record` CNAME → `replace(digitalocean_app.X.default_ingress,"https://","")`
  (self-derived, not hardcoded). Adding the domain block triggers an app **redeploy** (~3m).
- **Proxied (orange-cloud) needs a two-apply bootstrap.** DO's ACME challenge can stall behind the proxy,
  so apply `-var 'cloudflare_proxied=false'` first (grey cloud → DO issues the cert; in practice it went Active
  DURING the step-1 apply, ~seconds), then flip to `true`. Also the **zone SSL/TLS mode must be Full
  (strict)** or proxied serves 525s — it's zone-wide, so leave it OUT of TF (don't clobber sibling records).
- **The flip apply: use `-target=cloudflare_dns_record.app`.** DO returns SECRET env encrypted, so every
  `plan` shows `digitalocean_app` as "1 to change" (a harmless re-set). Targeting the DNS record avoids
  re-triggering the app redeploy for the flip. (`-target` still pulls the app in as a dependency, but the
  re-set is a fast ~24s spec update, not a full rebuild.)
- **Verifying proxied vs grey-cloud is tricky because DO's OWN edge is also Cloudflare** — `server: cloudflare`
  and `cf-ray` headers appear either way, and a local `dig` may be cached under the old grey-cloud TTL 3600.
  Definitive check: query the zone's authoritative NS directly — `dig +noall +answer @<zone-ns> <host>`.
  Proxied ⇒ Cloudflare anycast A records (104.21.x / 172.67.x) with the ondigitalocean CNAME **hidden**;
  grey-cloud ⇒ the CNAME target is visible.
- **Run TF from the MAIN checkout, not a worktree.** Gitignored bootstrap files (`backend.hcl`,
  `secrets.auto.tfvars`, `.terraform/`, `.envrc`) don't carry into a fresh worktree. Load Spaces state
  creds cleanly with `direnv allow <dir>` then `direnv exec <dir> terraform -chdir=<dir> ...` (never
  grep/echo the secret values). (The project this was learned on ran no Terraform in CI — apply was local-only.)
