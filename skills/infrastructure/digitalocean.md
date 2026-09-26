# DigitalOcean (learned 2026-07-13)

## Managed database lockdown
- **No "disable public endpoint" exists.** The only mechanism is the trusted-sources
  firewall (`digitalocean_database_firewall`): once ≥1 rule exists, ALL other traffic is
  denied. Rule types: `app`, `droplet`, `tag`, `ip_addr`, `k8s`.
- **The TF firewall resource is authoritative** (PUT replaces the whole list). DO auto-adds
  an app with a `database` block as a trusted source — declare that `app` rule explicitly
  in TF or the next apply strips it and the service + PRE_DEPLOY jobs lose DB access.
- `database_cluster.private_network_uuid` is **ForceNew** (changing = destroy+recreate).
  A cluster created without it sits in the region's DEFAULT VPC (attribute is computed —
  re-declaring the same value later is a no-op). `data "digitalocean_vpc"` with only
  `region` returns that default VPC.
- App Platform VPC integration exists (`spec.vpc`), but metro regions map to ONE
  datacenter (nyc→nyc1) and DB bindings resolve the PUBLIC hostname regardless — the
  `app` trusted-source rule is the designed mechanism; don't reach for spec.vpc for DB access.

## Tag race (droplet + cloud firewall)
- A `digitalocean_firewall` whose `tags` reference a bare string can race the droplet
  whose creation implicitly creates that tag → `422 tag does not exist` on first apply.
  Always declare an explicit `digitalocean_tag` and reference `.name` from both.

## Bastion/droplet hardening (Ubuntu 24.04)
- fail2ban sshd jail needs `backend = systemd` + `python3-systemd` package — noble cloud
  images have no rsyslog/auth.log; default backend errors at service start.
- sshd drop-ins: `sshd_config.d` is included at the TOP of sshd_config and sshd takes the
  FIRST occurrence of a keyword → a hardening drop-in must sort BEFORE cloud-init's
  `50-cloud-init.conf` (name it `00-…`). Validate fragments with `sshd -t -f %s`.
- Playbook ordering is a safety property: users/keys/sudoers BEFORE the sshd lockdown, so
  a mid-run failure can't disable root with no admin user in place.

## Terraform workflow
- Offline validate/schema in a worktree without backend creds:
  `terraform init -backend=false -plugin-dir <main-checkout>/.terraform/providers`.
  `terraform providers schema -json` on that init answers provider-capability questions
  authoritatively (block names, optional/computed) without web research.
- State creds load by sourcing the Terraform dir's `.envrc` (`set -a; . <dir>/.envrc;
  set +a`, never print). Don't trust the currently-selected doctl context — pass
  `--context <name>` explicitly and confirm with `doctl auth list` first. (This install's
  paths and context names: `LOCAL.md` beside this skill, when your copy keeps one —
  *DigitalOcean accounts and contexts*.)
