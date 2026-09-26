# macOS dotfiles & Homebrew — learnings

Setups, conventions, and gotchas for the `~/.env` dotfiles repo and macOS dev-environment
bootstrap. See your dotfiles repo's own README for the repo's current structure.

## Building a "match what I use" Brewfile

- **Use `brew leaves --installed-on-request` as the basis, NOT `brew bundle dump`.**
  `brew bundle dump` re-emits every on-request formula *and* pulls a lot of transitive
  library deps (grpc, harfbuzz, glib, poppler…) plus VS Code extensions — ~460 lines of
  noise. `brew leaves --installed-on-request` gives the ~100 top-level tools the user
  actually asked for. Add back anything that only shows as a dep of another leaf but you
  use directly (e.g. `pyenv` appeared only under `pyenv-virtualenv`).
- Keep language-specific tools OUT of the Brewfile when the repo installs them another way
  (cargo/go/nvm/pyenv) — the Brewfile is for brew+cask only; mixing creates two sources of
  truth.

## Verifying a cask/formula exists — FAST

- `brew search` and `brew info --cask <x>` hit the network + auto-update and routinely
  **hang for minutes** (saw 2-min timeouts). Instead curl the formulae.brew.sh API:
  `curl -fsI https://formulae.brew.sh/api/cask/<name>.json` (HEAD, exit 0 = exists), and
  fetch the `.json` to confirm `name`/`desc` when a name is ambiguous. Sub-second, no hang.
- Note: some CLIs ship as **casks not formulae** — e.g. OpenAI Codex is `cask "codex"`
  (there is no `codex` formula), Claude desktop is `cask "claude"`, `claude-code` is a
  separate cask for the CLI.
- HashiCorp tools (terraform/consul/nomad/vault) left Homebrew core — they live in
  `hashicorp/tap` now (`tap "hashicorp/tap"` + `brew "hashicorp/tap/terraform"`).

## Starship prompt config — three silent failures (verified on starship 1.22.1, 2026-07-16)

Starship does not validate config. A wrong `starship.toml` produces no error, no warning,
and a plausible-looking prompt that is simply wrong. **Never verify a starship edit by
reading it — render it.** (This install's project-specific detail: `LOCAL.md` beside
this skill, when your copy keeps one — *Dotfiles pointers*.)

- **Style strings have no `on` keyword — an invalid word discards the WHOLE style.**
  `style = "bold white on red"` (the natural way to write it) renders with **zero ansi**.
  The grammar is `bg:`/`fg:` → `bold fg:white bg:red`. Any unrecognised word silently
  voids the entire string, so the segment falls back to unstyled rather than erroring.
- **`shell = ["/bin/sh", "-c"]` breaks a custom module completely** (renders nothing):
  starship appends its own `-c`, making it `sh -c -c`. It is also pointless — starship
  already uses `sh`; the per-prompt cost is the fork itself, and pinning the shell gives
  **zero** speedup (measured, interleaved).
- **`command` is required on a `custom` module.** `when` + literal text in `format` with
  no `command` renders nothing.

- **⚠️ The "faster" config is often the broken one.** Both bugs above benchmark *faster*
  precisely because they render nothing. This bit twice in one session: a 30% "win" was
  a broken module, and a false "default shell is zsh, pin sh to fix it" hypothesis was
  built on top of that broken measurement. **Confirm correctness before believing a perf
  win**, and re-check the hypothesis, not just the number.
- **Benchmark against the REAL format, not a stripped one.** A minimal format puts the
  custom-module fork alone on the critical path and exaggerated the cost to +37 ms on a
  41 ms prompt. With the real config in a large real-world repo it was **+28 ms on
  312 ms (~9%)** — git modules dominate and run in parallel. Interleave the runs; serial
  A-then-B drifts upward and flatters whichever ran first.
- **`starship prompt` is not the path your shell uses.** Starship sets `PS1` from a
  `precmd` hook, so `${(%%)PS1}` reads empty. Render through the real init:
  `eval "$(starship init zsh)"; for f in $precmd_functions; do $f; done; print -rn -- "${(%%)PS1}"`
  in a `zsh -f -c`, and `cat -v` the output to read the ansi.
- **`starship config` opens `$EDITOR`** — it does not print the config. Don't put it in a
  scripted verification step; it will launch vim and hang.
- Prefer `${custom.name}` over bare `$custom` in `format`: bare `$custom` renders **all**
  custom modules, so an unrelated one added later lands in that slot.

## Gotchas that cost time

- **`cargo install` can report exit 0 while the build failed.** A stale Rust toolchain
  fails newer crates with `this version of Cargo is older than the 2024 edition` (eza
  needs Rust ≥1.85 / edition 2024). When piped through `| tail`, the failure exit is
  masked. Verify the **binary exists** (`command -v eza`), don't trust the exit code.
  Workaround to unblock: install the Homebrew bottle (`brew install eza`); real fix:
  `rustup update`. Fresh machines get current Rust from rustup so `install.sh` is fine there.
- **You cannot test zsh aliases with `zsh -c '...'`.** Non-interactive `-c` resolves
  aliases at parse time, so chained aliases (`ll`→`ls`→`eza`) don't expand and `ls` falls
  back to the system binary — giving false "it works" output. Verify either interactively
  (`zsh -ic`, but heavy configs with zinit/nvm/iterm-integration can hang) or by running
  the resolved binary + exact flags directly (`eza -g --ignore-glob __pycache__ -la`).
- Arch-independence: derive brew paths from `$(brew --prefix)`, never hardcode
  `/usr/local` (Intel) vs `/opt/homebrew` (Apple Silicon). In `install.sh`, after
  installing brew, `eval "$($(…)/brew shellenv)"` to get it on PATH for that arch.
- Modern shell wiring: `fzf --zsh` replaces the old hardcoded `.fzf.zsh` (fzf ≥0.48);
  the zinit org is `zdharma-continuum` (old `zdharma` is abandoned/hijacked); `git.io`
  short URLs are dead (sunset 2022); `go get -u` for installing binaries was removed in
  Go 1.18 → use `go install <pkg>@latest`.
- An **empty `else` clause is a syntax error** in bash/zsh (`if …; then …; else\n\nfi`).
- **A PATH prepend in `~/.zshenv` does NOT survive login-shell init on macOS:**
  `/etc/zprofile` runs `path_helper` after `.zshenv`, moving system dirs
  (`/usr/local/bin` etc.) back to the front. Anything that must stay first (e.g. the nvm
  default node — see `~/.nvm-default-path.zsh`, sourced from BOTH `.zshenv` and
  `.zprofile`) needs a `.zprofile` re-prepend. Caught live by a Codex adversarial review
  2026-07-10; full 3-environment story in
  [claude-code-tooling.md](claude-code-tooling.md).
