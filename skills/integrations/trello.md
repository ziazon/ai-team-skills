# Integrations — Trello

Trello REST API integration: key+token auth model, the token-bound-to-key gotcha, REST basics,
membership-as-assignee, and idempotent write-back on shared/guest boards.

## [Trello] REST API integration for a project-tracking workflow

**What we built:** a Trello REST integration for a project-tracking workflow — a
config-driven local helper, reusable across Trello projects, that triages a Trello board
instead of Jira, selected **per project** by a small config file in the project root
(default Jira when absent, so existing Jira projects are untouched). The original setup:
`LOCAL.md` beside this skill, when your copy keeps one — *Trello backend origin*.

- **Auth = key + token, both minted on YOUR account.** Key from the Power-Up admin
  (`trello.com/power-ups/admin` → a Power-Up → API Key tab → 32-hex key). Token from
  `https://trello.com/1/authorize?expiration=never&scope=read,write&response_type=token&key=<KEY>`
  → Allow → copy. The token inherits exactly the web-UI access of the user who approved it, so a
  **guest on someone else's board** works with their own key/token — no owner action, no admin.
- **The token is bound to the key that requested it.** A token minted under key A returns
  `token not found` when queried with key B. Symptom we hit: well-formed 32-hex key + a token,
  but `/members/me` returned **`invalid key`** (misleading!) — root cause was a token generated
  under a different/old key. Fix: open the authorize URL **with the key currently in `.env`**
  (we `open`ed it so the key never printed) and paste the fresh token. Isolation tricks that
  pinpoint it: key alone on a public endpoint → `missing scopes` means **key is valid**;
  `GET /1/tokens/{token}?key={key}` → `token not found` means **token is the problem**. Trello's
  `invalid key` error is unreliable — verify both sides independently.
- **Format sanity checks (no value printing):** key matches `^[0-9a-fA-F]{32}$`; token is a
  long alnum string (newer ones start `ATTA`). Validate format with a regex verdict, never echo
  the value or its length (per secrets rule).
- **REST basics:** base `https://api.trello.com/1`; auth via `key=` + `token=` query params
  (URL-encode them — use `curl -G --data-urlencode`). `GET /members/me` (whoami),
  `GET /boards/{id}/lists`, `GET /boards/{id}/cards/visible`, `GET /cards/{shortLink}` (accepts
  the short code from the card URL `trello.com/c/<shortLink>`; supports `actions=commentCard`,
  `members=true`, `checklists=all` to pull the thread in one call),
  `POST /cards/{id}/actions/comments?text=`, `PUT /cards/{id}?idList=` (move).
- **Card "assignee" = membership.** Filter `cards.idMembers` contains your member id (get it
  from `GET /boards/{id}/members`). No real "created" field — order by `dateLastActivity` (or
  derive a timestamp from the first 8 hex of the card id). Lists have no fixed status semantics;
  map list **names** → ids per board (config knob), don't hardcode ids across boards.
- **Idempotency / write-back:** comments are append-only (a re-run double-comments) so the
  write-back is gated behind a config flag and we state a move before doing it. Moves are
  idempotent (setting idList to the same list is a no-op). On a **shared/guest board**, default
  to least-intrusive (read-only or comment-only) and make list-move targets explicit config.
- **Secrets:** `TRELLO_KEY`/`TRELLO_TOKEN` in the project `.env` (gitignored); the helper
  **sources** the env file and passes them to curl — never echoed. The per-project config file carries only
  non-secret board/list/member ids but is gitignored anyway (per-user member id).
- **No MCP for Trello in this setup** — plain REST from a local bash helper, runs in-session
  where `.env` lives. (A Trello MCP server exists if unattended/cloud runs are ever needed.)
