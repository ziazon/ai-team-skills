# git-sync — re-stacking mechanics & stacked-PR topology

Read this when: a branch's **base was amended/rebased/squash-merged**, or you're
running a **multi-PR program** (stacked or parallel branches off one worktree).
The everyday sync workflow lives in [SKILL.md](SKILL.md).

## Re-stacking after a base branch's history is rewritten (amend / rebase / it merges)

Use `--onto` so you replay ONLY the branch's own commits — a plain `git rebase
<newbase>` re-applies the *old* base commits too and conflicts against their
rewritten twins.

```sh
# PR_B branches off PR_A. PR_A's tip was OLD_A, now NEW_A (amended/rebased).
git rebase --onto PR_A OLD_A PR_B        # replay PR_B's own commits onto new PR_A
git push --force-with-lease origin PR_B
```

When the whole stack **merges to main** (rebase-merge gives the commits NEW SHAs),
rebase each surviving branch onto main and drop the now-duplicated merged commits:

```sh
git fetch origin && git rebase --onto origin/main <my-last-merged-commit> <branch>
```

This is the mechanics behind SKILL.md invariant 3 ("rebase back onto main and drop
the dep"). Verify with `git log --oneline origin/main..HEAD` → should show only
your unmerged commits.

## Base commit was AMENDED (content changed) — plain sequential rebase makes a DUPLICATE

Plain rebase only auto-drops the old base commit when its content is UNCHANGED
(base merely rebased). An amended base has a different patch-id, so git replays
the old base commit on top of the new one → duplicate base commits in every child.
Deterministic fix — rebuild the stack bottom-up with reset + cherry-pick of each
branch's OWN (top) commit:

```sh
P2=$(git rev-parse <child2>); P3=...   # capture each child's own top commit FIRST
git checkout <base> && git rebase origin/main          # (or amend here)
git checkout <child2> && git reset --hard <base> && git cherry-pick $P2
git checkout <child3> && git reset --hard <child2> && git cherry-pick $P3
# …repeat up the stack
```

Verify per branch: `git rev-list --count origin/main..<branch>` (expect 1,2,3,…)
and `git diff --name-only <parent> <branch>` = only that branch's own files. Then
force-push-with-lease each.

**Squash-merged parent:** the parent's commits are NOT ancestors of main (a new
squashed commit is), so plain `git rebase origin/main` replays them and may
conflict. Use `git rebase --onto origin/main <old-parent-tip>` to carry only your
own commits.

## Stacked PRs & worktree topology (multi-PR programs)

For a program that ships as many small dependent/independent PRs off one worktree:

- **Move an INDEPENDENT slice onto its own main-based branch** (don't pile it onto
  the current feature branch): `git stash push -u` → `git checkout -b <new> origin/main`
  → `git stash pop` → commit. Keeps each PR independent + reviewable. Use this when the
  next slice doesn't actually depend on the current branch's commits.
- **A stacked PR auto-heals when its base merges.** Branch B based on branch A (a PR);
  A merges to main and its remote branch is deleted. `gh pr create --base A` then fails
  with "Base ref must be a branch / Head sha / Base sha can't be blank" — that error IS
  the signal A merged. Recover: `git fetch origin main` → `git rebase origin/main`
  (rebase auto-drops A's already-merged commits — "skipped previously applied commit")
  → `git push --force-with-lease` → open the PR against `main`.
- **After rebasing onto a moved main, re-verify before force-pushing.** The rebase can
  silently fold in a concurrent session's changes to the same files — re-run build +
  tests on the rebased tree; "rebase clean" ≠ "still correct."
- **Identical wiring edits on parallel branches merge without conflict.** If two
  independent branches each need the SAME one-line change (e.g. register the same
  provider), make the edit byte-identical on both — git's 3-way merge treats identical
  additions as already-applied. After rebasing the second one onto the merged first,
  confirm the redundant hunk dropped (`git diff origin/main..HEAD` shouldn't list that file).
