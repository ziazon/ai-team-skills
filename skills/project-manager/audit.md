# Project manager — auditing existing tickets (Mode C)

Find tickets that are already implemented or duplicated, then link and update them —
**report and confirm before mutating anything.** Rewrites that come out of an audit use the
ticket template in [ticket-writing.md](ticket-writing.md).

## Mode C — Audit existing tickets

Goal: find tickets that are **already implemented**, find **duplicates**, then **link
and update** them — but **produce a report and confirm before mutating anything.**

1. **Scope.** Ask or infer: all of the user's open tickets, a project, a label, a date
   range? Default to the user's open (non-done) tickets in the project, newest first.
2. **Fetch** the tickets (Jira: `searchJiraIssuesUsingJql`) with **minimal fields**
   (`summary, status, issuetype, labels, created, updated, assignee`) — including
   `description` in a broad scan blows the token budget on busy projects. Pull full
   detail (description + comments) only for real candidates, with `getJiraIssue`.
3. **Classify each ticket** with evidence:
   - **Already implemented?** Cross-check against the codebase (search for the
     feature/files, check merged PRs, commits, branches, closed related tickets) and
     the app's current behavior. Be rigorous: "looks done" is a candidate, not a
     verdict. Note *why* you think it's implemented (the commit/PR/file/behavior).
   - **Duplicate?** Compare titles + descriptions for the same underlying work. Group
     suspected duplicates; pick a canonical ticket (usually the oldest or most detailed).
   - **Stale / unclear?** Flag tickets too vague for QA to test (→ Mode D candidates).
4. **Report** back in this shape — do NOT change anything yet:

   ```text
   IMPLEMENTED (suggest verify → close/transition):
     PROJ-123 — <title> — evidence: merged in <PR/commit>, visible at <screen>

   DUPLICATES (suggest link + close the redundant one):
     PROJ-140 ⇄ PROJ-118 — same work; canonical: PROJ-118

   NEEDS WORK / UNCLEAR (suggest improve for QA):
     PROJ-150 — too vague to test; missing steps + expected result

   ALL GOOD: <count> tickets look correctly tracked.
   ```

   For anything you're not confident about, say so and **ask** rather than asserting.
5. **On the user's confirmation**, apply the approved changes. Prefer non-destructive
   first:
   - **Link** related/duplicate tickets (`getIssueLinkTypes` then `createIssueLink`;
     use "Duplicate" / "Relates" / "Blocks" as appropriate).
   - **Comment** with the evidence/rationale (`addCommentToJiraIssue`) so the trail is
     visible to QA and others.
   - **Transition/close** only the ones the user OK'd (`getTransitionsForJiraIssue` →
     `transitionJiraIssue`).
   - **Edit** descriptions to QA-ready form where approved (`editJiraIssue`).
   Apply changes one logical group at a time and report what you did.
