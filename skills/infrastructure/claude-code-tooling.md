# Infrastructure — Claude Code tooling & local jobs

Gotchas building Claude Code tooling: custom slash-command arg passing, local scheduled jobs
(launchd), daily-gated SessionStart hooks, and generating Markdown that embeds Markdown.

## [Claude Code] custom slash commands — arg-passing gotchas (personal /todo CLI)

Building a `~/.claude/commands/<x>.md` that shells out to a script (`!`node script $ARGUMENTS``):

- **Quote `$ARGUMENTS` or a leading `#` is eaten as a shell comment.** `/todo #3 done` expanded
  to `node todo.js #3 done` → bash treats `#3 done` as a comment → script runs with **no args**
  and **silently no-ops** (looked like a bug, marked nothing done). Fix: `"$ARGUMENTS"`. This
  also protects `&`, `;`, `*`, etc. Symptom to recognize: a command that "does nothing" when the
  user's args start with or contain `#`.
- **Quoting collapses all args into ONE token** → the script must re-normalize:
  `process.argv.slice(2).flatMap(a => a.split(/\s+/)).filter(Boolean)`. Keep it backward-safe so
  direct argv callers (hooks, cron scripts passing clean tokens) are unaffected — they have no
  whitespace/empties so the flatMap is a no-op for them. An empty `"$ARGUMENTS"` → `[""]` →
  `filter(Boolean)` drops it → bare command still works.
- **Forgive user shorthand** (they will not type canonical syntax): strip a leading `#` from ids
  (`#3`→`3`), accept `<id> <verb>` order not just `<verb> <id>` (reorder when token0 is id-like
  and token1 is a known verb), and accept **multi-id** via commas AND spaces (`done 7,10,14` /
  `done 7 10 14`). Report partial misses cleanly (`No TODO #904, #905`) and skip already-done.
- **Relay preference:** when relaying a LIST back to the user, name **every** item — never
  collapse to a range/count (it read as "items are missing"). Concise is fine for non-list output.

## [Claude Code] local scheduled jobs via launchd (macOS)

For a recurring **local** task (one that must read `~/.claude/*` local state), a **launchd**
LaunchAgent beats Claude Code's cloud `/schedule` routines — cloud agents run remotely and
**cannot see local files**. (See integrations `[pattern] scheduled local reminder → phone push`.)

- Plist at `~/Library/LaunchAgents/com.<you>.<job>.plist`; `StartCalendarInterval` dict with
  `Hour`/`Minute`. **Runs at next wake if the Mac was asleep** at the scheduled time — so pair it
  with an idempotent once-per-day stamp file and an always-available in-session fallback.
- `plutil -lint <plist>` to validate; `launchctl unload <plist>; launchctl load <plist>` to
  (re)register; `launchctl list | grep <label>` to confirm (PID `-` = registered, runs on schedule).
- Make the script robust to a **minimal launchd env**: PATH won't have nvm node — prepend
  `"$HOME/.nvm/versions/node"/*/bin` like any existing PATH-fragile hook must (this
  install's precedent: `LOCAL.md` beside this skill, when your copy keeps one —
  *Hook precedents*).

## [Claude Code] daily-gated SessionStart hook (run once per day, cheaply)

To run a task **once per day** without a clock/launchd, hang it off the existing
`SessionStart` hook list and let the SCRIPT self-guard — it no-ops on every
session after the first of the day. This is the established pattern in
`settings.json` (e.g. a `<your-daily-hook>` entry; this install's precedent is in
`LOCAL.md` beside this skill, when your copy keeps one — *Hook precedents*) and the
cheapest way to keep a local artifact fresh.

- **Wrapper script** detaches so it never delays session start:
  `nohup "$PYTHON" "$SCRIPT" >>"$LOG" 2>&1 & disown; exit 0`. Register it as a
  SECOND object in the `SessionStart` array (each gets its own `{matcher, hooks}`
  entry), `"async": true`, alongside the others — don't nest into an existing one.
- **Guard:** a `*.state.json` holding `{"last_run_date": "YYYY-MM-DD"}`; compare to
  `date.today().isoformat()` at the top of the script, `return 0` if equal. Add a
  `--force` flag that bypasses the guard so an on-demand slash command can refresh
  immediately.
- **On-demand twin:** a `~/.claude/commands/<x>.md` that runs the same script
  `--force` then `cp`s the result somewhere downloadable (`~/Downloads/`). Lets the
  user pull the latest without waiting for the daily fire.
- Example shipped: `export-setup` — keeps a shareable "my config" doc
  (`<your-config-doc>.md`) current; `/export-setup` exports it. (This install's doc
  path: `LOCAL.md` beside this skill, when your copy keeps one — *Export-setup doc*.)

## [Claude Code] gotchas when generating Markdown that EMBEDS Markdown

- **Embedding fenced content needs a longer outer fence.** Wrapping text that
  itself contains ```` ``` ```` (e.g. your global `CLAUDE.md` mentions "a fenced
  ```diff block") in a ```` ```markdown ```` fence makes the inner backticks
  close the block early. Open with a fence LONGER than any backtick run inside:
  compute `max(3, longest_backtick_run + 1)` and use that many backticks (a
  4-backtick ````` ````markdown ````` fence handled the CLAUDE.md case).
- **markdownlint will fail the doc on structure auto-fix can't repair** — keep
  `~/.claude` docs lint-clean (shared `.markdownlint.json`): give every code fence
  a language (`MD040` — even an ASCII tree → ```` ```text ````); use real
  `###` headings not whole-line **bold** (`MD036`); headings increment by one
  level (`MD001` — under `##` use `###`, not `####`); avoid aligned tables with a
  wildly long cell (`MD060` — a bullet list is simpler and lint-safe).
- **Auto-generate only a delimited block.** Regenerate strictly between
  `<!-- AUTO:BEGIN -->`/`<!-- AUTO:END -->` markers via a regex replace so the
  hand-curated prose around it is never clobbered by the daily refresh.
- **Scrub privacy when the source is "live."** Pulling skill/command descriptions
  verbatim leaks real names/company/tracker into a doc meant to be published. Run
  pulled text through a user-editable substring→replacement map
  (`setup/export-redactions.json`, longest-key-first) before writing.
- **YAML block-scalar leak:** a frontmatter `description: >` folded value parses
  with a leading `>`/`|` token — strip `^[>|][+-]?\s*` from the captured value.

## Node version: Claude Code's THREE environments ≠ your shell (nvm)

(Reworked 2026-07-10 after the full fix landed — supersedes the earlier version of this
section.) There are three distinct environments, each needing its own lever:

1. **Your terminals (interactive zsh):** `.zshrc` `nvm use` after `nvm.sh` loads. Fine.
2. **Bash tool + snapshots (non-interactive zsh):** the tool sources a per-session
   snapshot; snapshot CREATION sources `~/.zshenv`. **Durable fix = a dynamic prepend in
   `~/.zshenv`** that resolves `~/.nvm/alias/default` and prepends that version's bin
   (see `~/.nvm-default-path.zsh` — glob `(N/On)`, no `nvm.sh` load, follows future
   `nvm alias default` changes). Two gotchas: (a) macOS `/etc/zprofile` runs
   `path_helper` AFTER `.zshenv` and pushes system dirs ahead — so ALSO source the same
   snippet from `~/.zprofile`; (b) an already-running session keeps its stale snapshot
   (its `export PATH="$__path:$PATH"` re-prepends over `.zshenv`) — fix lands at the
   NEXT session; prepend per-command in the current one.
3. **Hooks (incl. plugin Stop/SessionStart hooks):** run via **`/bin/sh -c` with the
   Claude Code APP PROCESS env** — profiles and snapshots NEVER apply
   (code.claude.com/docs/en/hooks.md; verified live: codex gate hook crashed on v12
   while `zsh -c` gave v22). Levers: restart the desktop app from a fixed environment,
   an absolute node path in the hook command, or `settings.json` `env.PATH` (full
   override — risky for MCP servers). A modern-syntax `.mjs` hook under old node dies
   with a SyntaxError and Stop hooks fail SILENTLY — always live-test a gate hook.

Do NOT trust `zsh -c 'source ~/.zshrc; node -v'` as a proxy for any of these — it lies
green. Test each environment directly (fresh Bash call, `env -i zsh -lc`, real hook fire).

## [Claude Code] gating a generated-doc export on markdown lint

Pattern (from the `/export-setup` flow): a generator script that emits Markdown should
lint its output against the shared `~/.claude/.markdownlint.json` before the doc is
shipped, so drift is caught at the source.

- **Where to put the gate:** inside the *already-permitted* generator script, not in the
  slash-command's inline `!`command``. Auto-mode BLOCKS editing a command's `allowed-tools`
  to add a new `Bash(...)` rule (counts as self-modification / permission-widening). Having
  the script `subprocess.run` the linter and `exit 1` on failure lets the command's existing
  `&& cp …` chain short-circuit with no permission change.
- **Gate only the interactive path** (`--force`), not a silent daily SessionStart refresh —
  keep session start fast.
- **Reusable linter helper** `<your-scripts-dir>/lint-md.sh`: resolves the newest node
  ≥18 itself (default Bash-tool `node` is nvm v12, too old for markdownlint-cli2 — see the
  nvm section above), caches the linter under `<your-tools-dir>` via a one-time
  `npm install --prefix`, and is best-effort (missing node/script → exit 0, never blocks;
  lint violations → exit 1). (This install's paths: `LOCAL.md` beside this skill, when
  your copy keeps one — *Markdown lint helper*.)
- **GOTCHA — config discovery:** `markdownlint-cli2` does NOT walk up to find
  `~/.claude/.markdownlint.json` from a subdir. Pass `--config <path>` explicitly or it lints
  with defaults (e.g. MD013 line-length fires even though the shared config disables it).
- **GOTCHA — MD049 emphasis-style is *consistency*-based**, not "always asterisk": a lone
  `_underscore_` span passes if it's the only emphasis in the file, but fails when the
  document elsewhere uses `*asterisks*`. Fix generated emphasis at the source (the generator
  string), not the output file.
## Capability-aware shared tooling installers (2026-07-10)

- A shared AI-tool bootstrap must derive its repository root from the installer
  path, create tool config parents on a clean machine, and support explicit tool
  selection in addition to command/directory auto-detection.
- Optional session hooks need capability preflight before mutation and must
  detach stdin (`</dev/null`) when backgrounded; otherwise a host hook can hang
  even though the launched process uses `nohup`.
- Backups must be lazy, collision-safe, separated by destination tool, and
  idempotent. Verification should accept partial tool installations and check
  exact nonbroken targets rather than merely testing that a path is a symlink.

## [Claude Code] launchd self-updater for a locally built app (2026-09-29)

This covers a LaunchAgent that rebuilds and installs a desktop app into `/Applications` whenever `origin/main` changes it.
- **Fingerprint the inputs, not the checkout:** `git rev-parse origin/main:<subdir>` is the tree hash of
  everything the build reads. Journal commits on main don't trigger it. First confirm that no `include_str!`,
  path dependency or build config escapes the subdirectory.
- **The agent runs the main checkout's working-tree script, which lags.** Re-exec `origin/main`'s copy when its
  blob differs from `git hash-object "$0"`, with an env guard against a loop. The installer resolves the main
  checkout through `git rev-parse --git-common-dir` and refuses when the target script doesn't exist (otherwise it exits 127 every interval).
- **Build from `git archive` into a persistent directory.** Rsync with `-rlp --checksum --delete` and no `-t`, so unchanged files keep
  their mtimes and cargo stays incremental. Exclude `target/` and `node_modules/`, which `--delete` then protects.
- **Swap under `set -e`:** put every `mv` in an `if` so a failure cannot skip the rollback. Under the lock, a repair
  loop restores an orphaned `.old.*` when the app is missing. Record a failed tree once and don't retry it every interval.
- Under launchd, `git fetch` over SSH worked (macOS gives GUI agents `SSH_AUTH_SOCK`). Prepend cargo, pnpm and Homebrew to PATH.
