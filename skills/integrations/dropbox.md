# Dropbox — connector + local automation quirks

## The Dropbox MCP connector is CREATE-only — it cannot edit a file in place `[seen: 2026-07-16]`

The connector exposes `create_file` (new file with text content) but its documented contract
explicitly lists "editing or overwriting existing file content in place" as NOT supported. Verified
from the server's own boot instructions, not inferred.

**Design implication:** any "both sides append to a shared document" idea is dead on arrival. The
working pattern is an **append-only inbox**: one small file per event, written by the remote party,
drained and moved aside by the owner's machine. This is not a workaround — it fits the connector's
grain. Related tools that DO exist: `delete` (moves to Deleted files, not permanent), `move`, `copy`,
`create_folder`, `list_folder`, `search`, `fetch` (text extraction, may fail).

**Paths:** output paths are always `ns_path` (`ns:<id>//Folder/file.ext`) — never strip the prefix.
Input accepts `fq_path` (`/Folder/file.ext`) or `ns_path`. Personal account root IS writable; team
root is not. Shared folders appear as `object_type: "mount"` in `list_folder` output, distinct from
`folder`.

## MCP connectors are Claude-side only — launchd/cron cannot use them `[seen: 2026-07-16]`

A recurring local job (launchd, cron, a shell script) has NO access to a Claude MCP connector. If a
design says "Claude reads Dropbox via the connector" and also "a background job on the Mac picks it
up", those are two different transports and only one of them exists. The background side needs either:

1. **The Dropbox desktop app** — the folder syncs to `~/Dropbox` OR `~/Library/CloudStorage/Dropbox`
   (modern macOS uses the latter; DETECT, don't assume). The job then reads plain local files: no API
   token, no polling, and `launchd` `WatchPaths` fires within seconds of a sync. Strongly preferred.
2. **A Dropbox OAuth app + refresh token** — self-contained but adds a credential to manage and a
   poll interval.

Check for the desktop app FIRST (`~/Dropbox`, `~/Library/CloudStorage/Dropbox*`, `/Applications/Dropbox.app`,
a running process) before designing around a token — its absence/presence changes the whole architecture.

## Publishing into a watched folder is a feedback loop — make the write byte-idempotent `[seen: 2026-07-16]`

If a `WatchPaths` job also WRITES into the folder it watches (e.g. publishing a rendered view back for
the other party), an unconditional write re-triggers the watcher forever. Two fixes, use both:

- **Byte-idempotent publish** — read the existing file, compare, and return without writing when
  identical. This is the real guarantee. It also means the rendered file must NOT contain a
  "generated at <timestamp>" line, which would differ on every run and defeat the comparison. Drop
  the timestamp; the content IS the state.
- **Early-exit** the drain when there is nothing new to process.

Note `WatchPaths` on a directory watches its direct entries, not recursively — writing into a
`_out/` subdirectory mostly avoids re-triggering anyway, but do not rely on that alone.

## Claude must not share the folder — that's an access-control change `[seen: 2026-07-16]`

Creating the folder is fine; **sharing it is modifying sharing permissions** and is off-limits. Plan
for the human to do that step, and sequence the work so it isn't blocking until the end. Also note the
remote party needs their OWN Dropbox account + their own Dropbox connector authorized in their Claude
before they can write into a folder shared to them — that dependency chain (their Claude plan → their
Dropbox account → accepted share → connector authorized) is worth confirming with the user BEFORE
building, since none of it is verifiable from the owner's machine.

## Drain hygiene that paid off `[seen: 2026-07-16]`

- **Move, don't delete**, processed files (`_processed/`, bad ones to `_processed/rejected/`) — a
  drain bug must not destroy the other party's input.
- **Dedupe on the filename as an `externalId`** stored on the created record. This makes the drain
  crash-safe: commit the store write, THEN move the file; if it dies in between, the next run re-reads
  the file and the dedupe catches it.
- **Commit before notifying.** Write to the store first, attempt the push second, and never let a
  push failure crash the drain or lose committed items.
- **Filter Dropbox noise**: dotfiles, `desktop.ini`, and anything matching `conflicted copy`.
