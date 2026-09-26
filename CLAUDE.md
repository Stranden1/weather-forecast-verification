# Claude instructions

Follow `AGENTS.md`. It is the shared working agreement for all assistants
(ChatGPT/Codex and Claude) on this project.

Before starting, read `AGENTS.md`, `WORK_STATUS.md`, `PROJECT_STATUS.md`,
`NEXT_STEPS.md`, `DECISIONS.md` and the latest `REVIEW_*.md`.

- More than one assistant works here. Check `git status` first, and never
  overwrite uncommitted work you did not make.
- Update the handoff .md files at the end of each substantial task, as
  `AGENTS.md` describes. Read `CHANGELOG.md` only when you need past details.
- `data/weather.db` is authoritative. Open it read-only unless the task
  explicitly requires writes.
- Commit in validated steps. Do not push unless asked.

## Model routing
- If this session runs on **Sonnet**: do routine, clearly specified work yourself. For hard
  problems (see the `deep-thinker` description), consult the `deep-thinker` subagent (Opus)
  first, then carry out its plan yourself.
- If this session runs on **Opus**: never call `deep-thinker`; handle hard problems directly.
- Either way: one task per session, run the tests before committing, and never push without
  the user's OK.
