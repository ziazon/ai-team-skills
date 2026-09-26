# Project manager — QA feedback & release gate

Triage QA testers' comments (**Mode E**) and respect each project's QA/staging release gate.
Not every QA comment is a defect — surface each and let the user decide. Fixes go back through
the release gate before returning to QA.

## Mode E — Triage QA feedback

After QA tests a ticket, the tester leaves **comments** on it. Those comments must be
picked up and acted on in later sessions — but **not every comment is a defect.**
Sometimes the tester is just confirming the work looks good. So:

1. **Find tickets with QA comments.** Look at tickets in the QA/staging status (or that
   the QA tester from pm-config has commented on), newest activity first. Fetch full
   detail incl. comments (Jira: `getJiraIssue`).
2. **Surface each comment in plain terms** — what the tester said, on which ticket, and
   your read of whether it sounds like a defect, a question, or a confirmation.
3. **Prompt the user on how to proceed per comment** — do NOT assume every comment is a
   bug to fix. Offer the options: **fix it** (queue the work) / **no action — it's just
   confirmation** (and, if appropriate, move the ticket forward toward Done) / **needs
   discussion**.
4. For comments the user wants fixed, treat it like Mode A work: do the fix on the
   ticket's branch (per the user's git rules), then it goes back through the release
   gate before returning to QA. Reply on the ticket (`addCommentToJiraIssue`) noting
   what was addressed when the user wants that.
5. Never close or advance a ticket off QA feedback without the user's say-so.

## QA handoff & release gate

Some projects gate QA behind a deploy. Read the QA/staging rules in pm-config and
respect them — **don't move a ticket into the QA/staging status (or hand it to the QA
tester) before its changes are actually live in the QA environment.** If a project's
pm-config defines a release gate (e.g. deploy to staging with the project's release
command, then merge to the staging branch, then move the ticket to **In Staging**),
follow that exact order. (This install's release gates: `LOCAL.md` beside the
project-manager skill, when your copy keeps one.) When a ticket's work is done but not yet
deployed, leave it in its pre-QA status and tell the user what still has to happen
before it's QA-ready — offer to walk the release steps if they want, but don't run a
deploy command on your own without the user asking.

**Notify, don't reassign.** When a ticket reaches QA, the implementer stays the
owner/assignee. Signal the QA tester by adding them as a **watcher** and/or
**@mentioning** them in a comment (per pm-config) — never reassign the ticket to QA.
