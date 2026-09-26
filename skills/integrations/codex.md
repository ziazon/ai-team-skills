# Codex CLI / Claude Code plugin — learnings

## Invocation — the canonical dispatch form

**Verified 2026-08-21 against codex-cli 0.148.0.** Check `codex --version` before trusting
any flag written down here: the `codex exec` flag surface moves between releases, and
`codex exec --help` is the source of truth, not this file and not memory.

```bash
codex exec -s workspace-write '<brief>' < /dev/null
```

- **`-s, --sandbox`** takes `read-only | workspace-write | danger-full-access`.
  `workspace-write` is the default for implementation briefs; `read-only` for a review or
  audit brief that must not touch the tree.
- **`--full-auto` no longer exists.** On 0.148.0 it fails with
  `error: unexpected argument '--full-auto' found`. Sandbox mode is its own flag, above.
- **Append `< /dev/null`.** Per `codex exec --help`: when a prompt is passed as an argument
  *and* stdin is piped, stdin is appended to the brief as a `<stdin>` block. So an inherited
  pipe that never closes leaves Codex waiting to read it — the symptom is a run that
  produces no output for tens of minutes and reads exactly like a hung model (one such
  stall ran 21 minutes). Redirecting from `/dev/null` costs nothing and rules it out, and
  also stops stray stdin from silently contaminating the brief. Note it does **not** stall
  every time: bare and `-s workspace-write` runs with piped stdin both completed normally
  on 0.148.0 (checked 2026-08-21), so treat the redirect as insurance and a no-output stall
  as the trigger to look here.
- **`-C, --cd <DIR>`** sets the working root; use it when dispatching from outside the target
  repo or worktree. `--add-dir` adds a second writable directory.
- Other flags that exist on 0.148.0: `-m/--model`, `-o/--output-last-message <FILE>`,
  `--json`, `--skip-git-repo-check`, `--approve-for-me`, `--ephemeral`.

### A flag error is not an outage

🚨 **Before concluding Codex is down, run the simplest invocation that could work — bare
`codex exec '<brief>' < /dev/null`.** Four sessions have mistaken a flag problem for an
outage: they read classifier refusals of `--full-auto` /
`--dangerously-bypass-approvals-and-sandbox` as "Codex is blocked" and fell back to doing
the work without Codex while a bare run worked the whole time. A fifth (2026-08-21) hit
the removed-`--full-auto` error above and recovered only by reading `codex exec --help` —
which is why this section exists. **When a failure message names
something you passed, suspect what you passed.** "Retry once" means retrying with FEWER
flags, not the same command again. (The incident record and the rules it cites: `LOCAL.md`
beside this skill, when your copy keeps one — *Flag-error incidents and rulebook
citations*.)

Corollary for readers of a handoff: a note saying "Codex is blocked" is an **unverified
claim about flags** until someone shows the bare invocation failing.

### Two constraints that shape the brief itself

- **One concern per brief.** A brief spanning many files stalls; splitting the same work
  into single-concern briefs turns a 21-minute no-output stall into two sub-minute runs.
- **The sandbox cannot bind network listeners** — HTTP e2e suites (Supertest/NestJS e2e,
  dev servers) fail with `listen EPERM` inside it. Codex self-verifies unit/typecheck/build;
  the orchestrator runs e2e outside the sandbox.

### The sandbox also has NO OUTBOUND network, and cannot write the package caches

**Verified 2026-09-02, codex-cli 0.149.0.** Distinct from the listener limitation above:
`workspace-write` defaults to `network_access = false`, so a brief that installs anything
or fetches anything fails before it starts. And `writable_roots` (set in
`~/.codex/config.toml`) covers the projects root but **not** the package-manager caches, so
even with network on, installs still fail.

The two failures arrive in that order, and the second one lies:

1. `pnpm install` / `npm view` → `ENOTFOUND registry.npmjs.org`.
2. Network on, but → `EPERM` on `~/.npm/_cacache` or the pnpm store. 🚨 **npm misreports
   this as "Your cache folder contains root-owned files… run `sudo chown -R`".** That
   diagnosis is wrong — it is the sandbox denying the write. **Do not run the suggested
   `chown`**; it "fixes" nothing and touches permissions outside the sandbox.

Fix per invocation, without editing the global config:

```bash
codex exec -s workspace-write -C <worktree> \
  -c sandbox_workspace_write.network_access=true \
  -c 'sandbox_workspace_write.writable_roots=["<HOME>/projects","<HOME>/.npm","<HOME>/Library/pnpm","<HOME>/Library/Caches/pnpm"]' \
  "$(cat brief.md)" < /dev/null
```

(`<HOME>` is your absolute home directory, written out: the value is single-quoted, so
`$HOME` would not expand.)

**Read the cache paths, never assume them** — they move between majors:
`pnpm store path` (was `~/Library/pnpm/store/v11`) and `npm config get cache` (`~/.npm`).

**Related trap — tools that write config outside the workspace.** Astro's telemetry cannot
create `~/Library/Preferences/astro`, so a bare `astro build` / `astro check` dies in the
sandbox while the identical command works in your own shell. Put
`ASTRO_TELEMETRY_DISABLED=1` in the project's package.json scripts and tell Codex to invoke
`pnpm build` / `pnpm check`, never the bare binary. Expect the same shape from any CLI with
opt-out telemetry or a global config dir.

🔑 **Why this belongs next to the flag rules above:** the first failure reads exactly like
"Codex is down" and invites a wrongful fallback to implementing without Codex. It is a
sandbox-config problem, not an outage — the same misdiagnosis class as the flag
errors, and the same remedy: **when a failure names something in your invocation's
environment, suspect the invocation.**


## Claude Desktop hooks can run the OLDEST node (2026-07-10, live-verified)

Relevant to any Node-based Codex plugin hook run from the Claude desktop app:

- **Hooks see the APP process env, not your shell's.** They run `/bin/sh -c`; shell profiles
  (`.zshenv`/`.zprofile`) never apply. Diagnose with `/bin/sh -c 'node --version'` — a plain
  `node --version` (or any zsh probe) can lie because profile fixes mask the app env.
- **Two compounding desktop-app behaviors** (decompiled from app.asar 1.20186.0). (1) The app
  probes the login shell for PATH via `$SHELL -l -i -c` with a **4s timeout**; an interactive
  zsh can take ~5.5s → the probe times out on EVERY launch (`~/Library/Logs/Claude/main.log`:
  "Shell environment extraction timed out") and the failure is **cached for the app's
  lifetime**. (2) It then falls back to glob additions where `~/.nvm/versions/node/*/bin`
  matches are `.reverse()`d (intent: newest-first) — but the glob yields
  reverse-lexicographic, so the nvm block lands ASCENDING and the OLDEST node wins.
- **Fix:** an early-return guard at the top of `~/.zshrc` on
  `$CLAUDE_DESKTOP_RESOLVING_ENVIRONMENT` / `$VSCODE_RESOLVING_ENVIRONMENT` (the probe sets
  the former; an escape hatch built into the probe worker). Guarded probe = 0.4s and returns
  the `.zshenv`/`.zprofile` PATH, which the app prepends ahead of the glob block. Diagnose
  regressions: nvm entries in session PATH ascending + the timed-out warn in main.log.
- **A full app relaunch is REQUIRED after any env fix** — the probe result (including
  failure) is memoized in the Electron main process, and each session's env is baked at
  spawn.

The plugin-specific wiring (the companion entry point, flag asymmetry, runtime teardown,
and the stop-review gate's state and test recipe) is in `LOCAL.md` beside this skill, when
your copy keeps one — *Codex plugin verification-loop wiring* and *Codex plugin stop-review
gate*.
