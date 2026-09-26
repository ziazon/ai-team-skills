# ai-team skills

A Claude Code plugin of skills for disciplined software work: planning before
building, test-first implementation, code and security review, git hygiene,
orchestrating sub-agents, and handing a session off cleanly. Each skill is a
`SKILL.md` under [`skills/`](skills/), plus any reference files it links to.

## Install

```bash
claude plugin marketplace add ziazon/ai-team-skills
claude plugin install ai-team@ai-team-skills
```

Skills load on their own when a task matches their description. You can also
name one directly as `ai-team:<skill>`, for example `ai-team:planning`.

## Files a skill may mention that are not here

Some skills point to two optional files that your own copy can keep beside a
`SKILL.md`. Neither ships in this repository:

- **`LEARNINGS.md`** is a journal of lessons from using the skill. A skill that
  asks you to append to it means your copy's journal, when you keep one.
- **`LOCAL.md`** holds conventions for your own projects that override or extend
  the generic body, such as your stack's commands or house rules. A skill names
  it at the point where a local convention would apply.

## How this repository is published

It is exported from a private working repository by a release script. Each
release is a single commit, `Release vX.Y.Z`, and the plugin version in
`.claude-plugin/plugin.json` follows semver. Pull requests would be overwritten
by the next release, so please open an issue instead.

## License

[MIT](LICENSE). Some skills are adapted from other MIT-licensed projects; see
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
