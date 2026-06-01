# Refactor parity contract

This document defines the behavior-preserving checks that must stay green while
modernizing `notes-skill`.

## Public CLI surface

`scripts/notes-runner` must keep these commands unless a separate migration
explicitly changes the public API:

- `prepare`
- `status`
- `replace-speakers`
- `build-tldr`
- `build-header`
- `ensure-appendix`
- `assemble`
- `youtube`
- `local`
- `audio`
- `telegram`
- `auto`
- `batch`
- `doctor`

Command names, required positional arguments, default values, and JSON output
shape are behavior. Refactors may move implementation code, but command behavior
must be proven with parser parity, JSON parity, unit tests, and
`scripts/release-check.sh`.

## Runner module facade

`scripts/notes-runner` is not only an executable. Current regression tests and
the deterministic shell harness import it as a Python module and patch selected
functions. That importable facade is an internal compatibility contract until
the tests and harness are intentionally migrated to `notes_runner_lib`.

Do not delete or rename runner-level functions just because a same-named
implementation exists under `scripts/notes_runner_lib/`. Many of those functions
are dependency-injection boundaries or compatibility wrappers.

## Live install layout

The live skill directory is a deployment target. Refactors must not require
manual edits in `~/.codex/skills/notes`, `~/.agents/skills/notes`, or
`~/.claude/skills/notes`.

For Codex App discoverability, these files must be materialized as ordinary
files in a dev-linked live target:

- `SKILL.md`
- `agents/openai.yaml`

Other managed files may be symlinked during local development if the install
scripts preserve local-only paths such as `config.json`, `backups/`, and `.ai/`.

## Required gates

Before and after runtime refactors:

```bash
bin/status
python3 -m unittest discover -s tests -p 'test_*.py'
bash scripts/release-check.sh
```

For changes that touch install, dev-link, promote, or skill discovery, also run
a temp-target live layout check rather than touching the real live install.

Temp-target checks should cover:

- `scripts/dev-link-live.sh`
- `scripts/promote-live.sh`
- `install.sh` with isolated `HOME`, `CODEX_HOME`, and `NOTES_SKILL_TARGET_DIR`

Those checks prove file layout, not real Codex App indexing. If the app does not
see the skill after a layout-safe change, inspect the app index/cache separately.
