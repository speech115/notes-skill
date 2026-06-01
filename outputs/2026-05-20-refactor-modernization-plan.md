# notes-skill modernization plan

Updated after adversarial review on 2026-05-20.

## Confidence verdict

I am confident in the revised strategy, not in the earlier draft.

The earlier draft had four material loopholes:

1. It treated duplicate names between `scripts/notes-runner` and `notes_runner_lib` as likely removable duplication. That is unsafe: many runner functions are compatibility/dependency-injection facades over split runtime modules.
2. It proposed a thin executable entrypoint too early. Tests and the shell harness import `scripts/notes-runner` as a Python module and call functions directly, so that module surface is an internal compatibility contract.
3. It underweighted live install discovery. Codex App discoverability depends on live install shape, including ordinary-file materialization for `SKILL.md` and `agents/openai.yaml`.
4. It did not separate parser/CLI parity from output JSON parity. Both are public behavior for this repo.

The corrected strategy below fixes those loopholes by making compatibility mapping and parity capture the first implementation work, before moving code.

## Scope

Preserve `/notes` behavior and public CLI/skill contracts. Refactor in small passes around the existing release gate:

- `bin/status`
- `python3 -m unittest discover -s tests -p 'test_*.py'`
- `bash scripts/release-check.sh`
- selected CLI parity snapshots for `doctor`, `prepare`, `status`, `assemble --skip-telegram`, and routing commands

## Current findings

- `scripts/notes-runner` is still the largest module at 2174 lines.
- Runtime code has already been partially extracted into `scripts/notes_runner_lib/`, but `scripts/notes-runner` still owns command dispatch, environment resolution, compatibility wrappers, dependency wiring, and several duplicated public functions.
- `prepare_logic_runtime.py` and `prepare_runtime.py` are oversized and mix policy, filesystem state, prompt generation, and stage/status inference.
- `scripts/test-pipeline.sh` is the strongest behavior gate, but it is a large shell harness with repeated fixture/assertion patterns.
- Generated local artifacts appear in the working tree during discovery (`__pycache__`, `.DS_Store`), but tracked generated blobs appear limited to `chatgpt-review-packet.zip`.
- `tests/test_notes_runner_regressions.py` and `scripts/test-pipeline.sh` import `scripts/notes-runner` directly with `importlib`; refactors must preserve or explicitly migrate that module-level compatibility surface.
- The public command set is: `prepare`, `status`, `replace-speakers`, `build-tldr`, `build-header`, `ensure-appendix`, `assemble`, `youtube`, `local`, `audio`, `telegram`, `auto`, `batch`, `doctor`.
- Live install behavior is part of the product surface. `SKILL.md` and `agents/openai.yaml` must remain materialized as ordinary files in the live install for Codex App discoverability.
- Major dependency/framework moves are not required for the first modernization wave and should be split from behavior-preserving refactors.

## Execution status

Foundation passes started on 2026-05-20:

- Added `docs/refactor-parity.md` to make the CLI, runner facade, and live install layout contracts explicit.
- Added repo contract tests for the stable command set and important command flags.
- Added a runner import compatibility test for the module-level facade and patch points used by regression tests and the shell harness.
- Added temp-target live layout tests for `dev-link-live`, `promote-live`, and `install.sh`, without touching the real live install.
- Extracted command dispatch into `scripts/notes_runner_lib/cli_runtime.py` while keeping `scripts/notes-runner` as the importable facade.
- Added parity coverage that keeps `scripts/notes-runner` command handlers aligned with the parser command set and order.
- Added runner-level CLI smoke coverage for `--help`, `doctor --json`, and `status --json` so parity checks exercise the executable surface, not only lower-level runtime modules.
- Strengthened temp-target live install checks to preserve local-only `config.json`, `backups/`, and `.ai/runtime/` state and to verify installed runner executability.
- Replaced brittle literal import-string contract tests with AST-based runner import wiring plus runtime module importability checks, while keeping parser, exact command-handler identity, runner facade, and executable CLI/JSON parity checks as the behavior-preserving guardrail.
- Extracted private dependency factory functions for `local`, `audio`, `prepare`, workdir deterministic commands, `batch`, and `doctor` command wrappers. The public `cmd_*` runner facade functions still exist and resolve dependencies at call time, preserving monkeypatch/dependency-injection behavior.

The runtime code motion so far is limited to command dispatch extraction and
private dependency factory extraction. Command handlers, parser construction,
and command behavior stay owned by the existing runner facade. `cmd_assemble`
is intentionally not split further yet because it mixes shell execution,
quality finalization, and Telegram delivery.

## Refactor passes

### Pass -1: Compatibility map before code motion

Current behavior: `scripts/notes-runner` is both CLI executable and importable module facade used by tests/harness. Several same-named functions delegate into split runtime modules but are still intentionally patchable in tests.

Structural improvement: document the runner module surface as one of three categories: public CLI command, test-supported compatibility facade, or private implementation helper. Do not move or delete a function until it is classified.

Validation: static audit of direct runner imports/calls, unit tests that import `scripts/notes-runner`, and no loss of patch points used by regression tests.

### Pass 0: Baseline and parity harness

Current behavior: release stability is mostly protected by `release-check`, deterministic shell tests, and Python unit tests.

Structural improvement: add a lightweight parity checklist/spec that records expected parser command set, help text shape, JSON shape, and stable outputs for key commands before touching runtime structure.

Validation: `bin/status`, `python3 -m unittest discover -s tests -p 'test_*.py'`, `bash scripts/release-check.sh`, plus saved before/after command list/help output and JSON for `doctor --json`, local `prepare --json`, `status --json`, and `assemble --skip-telegram --json`.

### Pass 1: Repository hygiene

Current behavior: generated cache files are ignored, but local discovery still surfaces them; `chatgpt-review-packet.zip` is tracked as a release/review artifact.

Structural improvement: remove untracked generated files from the local tree and decide whether zipped review packets belong in git or should be regenerated from source materials.

Validation: `git status --short`, `git ls-files` artifact audit, `bin/status`.

### Pass 2: Runner facade extraction, not thin-entrypoint rewrite

Current behavior: `scripts/notes-runner` builds parser, dispatches commands, resolves environment, wires dependencies, and keeps compatibility wrappers.

Structural improvement: extract stable command dispatch and dependency wiring into a small `cli_runtime.py` or `runner_app_runtime.py`, but keep `scripts/notes-runner` as an importable compatibility facade until tests and shell harness are intentionally migrated.

Validation: exact command list/help parity, direct import parity for functions used by tests, `doctor --json`, all command smoke paths, full `release-check`.

### Pass 3: Retire duplicated wrapper functions safely

Current behavior: many functions in `scripts/notes-runner` are thin wrappers around `notes_runner_lib` implementations, kept for transition and command dependency injection.

Structural improvement: group wrappers by boundary: public CLI adapters, dependency providers, and true local helpers. Remove wrappers only when tests prove they are not imported by tests, scripts, or skill docs.

Validation: static `rg` import/call audit, unit tests, `test_repo_contracts.py` updated to assert module ownership rather than string imports only.

### Pass 4: Prepare pipeline separation

Current behavior: prepare code mixes transcript/file metadata, chunk planning, prompt rendering, quality contract writing, stage sentinel writing, and status planning.

Structural improvement: split into narrower modules: `prepare_metadata`, `prepare_chunking`, `prepare_prompts`, `prepare_stage_state`, and keep public functions stable through a facade.

Validation: prepare fixture parity for short/medium/long transcripts, stage JSON parity, `status --json` parity, `release-check`.

### Pass 5: Status and state model normalization

Current behavior: status inference reads multiple historical artifacts and has to tolerate stale sentinel/state combinations.

Structural improvement: introduce typed internal helpers/dataclasses for stage status and chunk status while preserving JSON output shape.

Validation: status regression tests for stale extraction flags, missing manifests, completed bundles, and partial stage completion.

### Pass 6: Assemble/finalization cleanup

Current behavior: assemble is split into shell context, shell execution, finalization, Telegram delivery, and quality checks, with behavior-critical `--skip-telegram` semantics.

Structural improvement: make assemble flow explicit as prepare context -> run shell -> quality contract -> optional Telegram -> run state update.

Validation: assemble fixture parity, quality-check JSON parity, Telegram-disabled and skip-telegram tests, no behavior change to final user-facing `/notes` completion contract.

### Pass 7: Live install/discovery boundary

Current behavior: installer/dev-link/promote choose live targets and preserve local config. Codex App visibility depends on live file shape, including materialized `SKILL.md` and `agents/openai.yaml`.

Structural improvement: treat install/dev-link/promote as a separate boundary. Add a small deterministic live-layout check that can run against a temporary target and assert ordinary files/symlinks exactly where expected.

Validation: temp-target install/dev-link/promote smoke, `SKILL.md` ordinary file, `agents/openai.yaml` ordinary file, runner executable bit, config preservation, no manual edits in live install.

### Pass 8: Test harness modernization

Current behavior: `scripts/test-pipeline.sh` is broad and effective, but large and repetitive.

Structural improvement: keep shell entrypoint stable, move repeated JSON/assertion/fixture helpers into a small shared script or Python helper only after runtime refactors settle.

Validation: `release-check` still emits zero `SKIP` in quick mode; full deterministic suite remains readable and fails on the same cases.

## Stop rules

- Do not delete or move a runner-level function just because an implementation exists in `notes_runner_lib`.
- Do not make `scripts/notes-runner` only a shell/console wrapper until direct import tests are migrated.
- Do not combine install/dev-link/promote changes with runtime refactors.
- Do not change JSON schema, command names, command defaults, Telegram completion semantics, or `/notes` skill instructions in a behavior-preserving pass.
- Do not treat `assemble --skip-telegram` as user-facing completion; it remains debug/smoke only.

## Separate migration tasks

- Packaging migration to `pyproject.toml`, console scripts, or installed Python package.
- Replacing `argparse` with Click/Typer.
- Dependency upgrades or lockfile policy changes.
- Public CLI flag changes, output JSON schema changes, or `/notes` skill contract changes.
- Replacing shell integration tests with pytest end-to-end tests.
- Reworking Codex App install/discovery conventions beyond this skill's current live layout.

These should not be mixed into behavior-preserving refactor passes.
