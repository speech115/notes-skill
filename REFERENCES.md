# notes-skill references

## Repo-local

- `AGENTS.md` — короткий рабочий контракт для Codex.
- `CONTEXT.md` — текущая карта repo и workflow.
- `README.md` — install, supported inputs, stable workflow.
- `SKILL.md` — основной user-facing skill contract.
- `ADVANCED.md` — speaker diarization, YouTube fallback transcription, Telegram voice/audio, auto-delivery.
- `OBSERVABILITY.md` — run artifacts, trace files, status/debug commands.
- `TROUBLESHOOTING.md` — known failure modes and triage.
- `RELEASE.md` — release/promote workflow.
- `scripts/release-check.sh` — главный локальный release gate.
- `scripts/notes-runner` — CLI entrypoint.
- `scripts/notes_runner_lib/` — runner implementation.
- `tests/` — regression and contract tests.
- `chatgpt-review-packet/` — packaged review materials and prompt artifacts.

## Vault

- `/Users/sereja/Projects/research/karpathy-kb/wiki/entities/notes-skill.md`
- `/Users/sereja/Projects/research/karpathy-kb/outputs/projects/2026-04-26-notes-skill-digest.md`
- `/Users/sereja/Projects/research/karpathy-kb/wiki/sources/notes-skill-advanced.md`
- `/Users/sereja/Projects/research/karpathy-kb/wiki/sources/notes-skill-agents.md`
- `/Users/sereja/Projects/research/karpathy-kb/wiki/sources/notes-skill-readme.md`
- `/Users/sereja/Projects/research/karpathy-kb/wiki/sources/notes-skill-skill.md`
- `/Users/sereja/Projects/research/karpathy-kb/wiki/sources/notes-skill-troubleshooting.md`

## Live install boundary

Default live targets follow installer resolution:

- `$CODEX_HOME/skills/notes`
- `~/.codex/skills/notes`
- `~/.agents/skills/notes`
- `~/.claude/skills/notes`

Treat those as deployment targets. Use `scripts/dev-link-live.sh` for active local development and `scripts/promote-live.sh` for promotion.
