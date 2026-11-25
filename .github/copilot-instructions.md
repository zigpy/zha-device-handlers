The instructions for all AI agents working in this repository are in `AGENTS.md` at the repository root; follow them. Detailed references for writing and reviewing quirks are in the `zha-quirks` skill (`.claude/skills/zha-quirks/SKILL.md` and the files next to it).

## Code review

When reviewing a pull request, use the `quirk-review` skill (`.claude/skills/quirk-review/SKILL.md`). In short:

- Start with a one-sentence summary, then findings ordered by impact, each with a concrete fix. Comment only where you are confident, and once per issue.
- Check that the title and description match the final diff, that new devices have diagnostics attached as a file, and that existing entities keep their unique IDs.
- Don't comment on formatting (pre-commit handles it), don't ask for tests on declarative quirks or for signature tests, and don't ask to move new attribute IDs into module constants.
