# Gemini CLI as a team-member (reader/reviewer role)

Reusable lessons from wiring `gemini-cli` (Homebrew `gemini`, v0.46) into the agent team as a
headless reader/researcher/independent-reviewer. Tagged **[gemini-cli]**. Read before adding or
debugging a Gemini integration. Companion to [codex.md](codex.md) (the other agent CLI).

## Auth-path reality check (the load-bearing gotcha)
- **A vendor's consumer subscription is NOT API/headless access — verify the billing surface
  before assuming a subscription wires up a CLI.** Google **AI Pro** ($4.99/mo Google One) grants
  Gemini in the *app / web / Antigravity*, not the API. The API is a **separate metered
  pay-as-you-go** surface — you need an **AI Studio API key**, billed independently of the sub.
- **gemini-cli OAuth "Login with Google" for individuals is being shut off** (cutoff
  ~2026-06-18; Google routes those users to Antigravity). Error text: *"This client is no longer
  supported for Gemini Code Assist for individuals… migrate to Antigravity."* This is a
  deliberate deprecation, **not a version bug** — upgrading the CLI does not fix it. The escape
  hatch that keeps the CLI headless is the **API key** (`GEMINI_API_KEY`) or Vertex.

## Secrets & config placement
- **`~/.gemini/.env`** is the CLI's **global** env home (loaded for every project, not scoped to
  a repo). Put `GEMINI_API_KEY=...` there, `chmod 600`. Write it with no-echo
  `read -rs "k?…"` so the value never hits screen or shell history.
- **List models without leaking the key:** `curl -H "x-goog-api-key: $GEMINI_API_KEY"
  https://generativelanguage.googleapis.com/v1beta/models` — key in a **header, never the
  `?key=` URL param** (never secrets in URLs). Source the env file into the process, don't echo.
- `settings.json`: default model = `model.name`; auth mode = `security.auth.selectedType`
  (`"gemini-api-key"`). Global context file = `~/.gemini/GEMINI.md` (loads in `-p` headless too).

## Model-id volatility → prefer the alias
- **`-preview` model ids retire fast and 404 out from under you** (e.g. `gemini-3-pro-preview`
  shut down 2026-03-09, replaced by `gemini-3.1-pro-preview`, which will itself age out).
- Default to the **`gemini-pro-latest` alias** — it always resolves to Google's current stable
  pro and **never 404s**. Tradeoff: it auto-tracks whatever Google marks "latest pro," so
  behavior/cost can shift on a new release — but it won't break. Pin a versioned id only when
  reproducibility matters, and add a **404 → `-latest` → fall back to primary agent** recovery.

## Workspace sandbox + trust (headless gotchas)
- gemini **sandboxes file/tool access to the cwd workspace** (+ its temp dir): it can't read
  files outside the dir you launch it from, and `run_shell_command` is blocked for the review
  agent. **Run it from the repo dir** you want it to read; pull files in with `@path`, `@dir/`,
  or `--all-files`.
- **A cross-boundary `@import` in `GEMINI.md` is refused** ("resolves outside allowed
  workspace") — e.g. importing a shared rules file from outside the workspace. Keep the context
  file **self-contained**; inline the rules the agent needs instead of importing across the
  sandbox boundary.
- **Headless in an untrusted dir needs `--skip-trust`** (or `GEMINI_CLI_TRUST_WORKSPACE=true`).
  A dir already in `~/.gemini/trustedFolders.json` works without it; a fresh worktree won't.
- `~/.gemini/state.json` does **not** record the active model — don't rely on it to confirm
  which model ran. Transient `503 UNAVAILABLE` happens; retry.

## Pattern: second-model CLI as a non-overlapping teammate
- Give the second model a **lane that doesn't overlap the code-writer** — reader / researcher /
  independent reviewer, **never** a code-writer or git-actor — declared in its context file
  (`GEMINI.md`). This is what stops two agents fighting over the same diff.
- Add a **fallback-to-primary rule** for when the metered key is exhausted (429
  RESOURCE_EXHAUSTED / billing error): the orchestrator does the work directly, flags it inline,
  and stops re-hammering the dead key for the session. Mirrors the fallback for any other
  delegated agent CLI that becomes unavailable.
- Its value is **independent failure modes** (different model family) for adversarial review —
  prompt it to reason from first principles, not defer to the other agents' conclusions.
