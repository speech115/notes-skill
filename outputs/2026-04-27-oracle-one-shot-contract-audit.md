# Oracle audit: `/notes` one-shot contract

Date: 2026-04-27

Prompt: `drafts/oracle-prompt-one-shot-contract-audit.md`

Oracle slug: `notes-skill-one-shot-contract-audit`

Files attached: 28 focused repo files covering `SKILL.md`, runner orchestration/status/quality/assemble modules, tests, and release/docs.

Local pre-check:

```bash
python3 -m pytest tests/test_prepare_runtime.py tests/test_prepare_logic_runtime.py tests/test_status_runtime.py tests/test_quality_runtime.py tests/test_assemble_finalize_runtime.py tests/test_assemble_shell_runtime.py tests/test_repo_contracts.py -q
# 58 passed in 0.52s
```

## Short verdict

Oracle found real contract drift, not cosmetic nits. The strongest theme: runner state can mark work as ready/completed in cases where the human-facing `/notes` contract says it is not complete.

Top implementation order:

1. Fix skipped Telegram semantics so `--skip-telegram` cannot poison resume state as normal completion.
2. Harden chunk readiness: completed sentinel, matching fingerprint, block, manifest, summary, declared outputs.
3. Fix assemble readiness: derive from assemble sentinel, bundle outputs, and delivery truth, not stray workdir HTML.
4. Make `single` mean exactly one chunk, or explicitly support one agent processing all chunks.
5. Simplify `SKILL.md`: remove “Telegram is best-effort”, remove unconditional `replace-speakers`, fix speaker-stage values, and clarify/limit batch.

## Findings

### P0 — `--skip-telegram` can poison resume state as if the note were truly complete

Files:

- `SKILL.md`
- `README.md`
- `TROUBLESHOOTING.md`
- `scripts/notes_runner_lib/assemble_finalize_runtime.py`
- `scripts/notes_runner_lib/status_runtime.py`

Mismatch:

Docs say `--skip-telegram` is debug/smoke-only and not normal user-facing completion. But `finalize_assemble_success()` marks assemble completed when `skip_telegram=True` and there are no contract errors. That can write `stage_statuses.assemble = ready`, `completed = true`, and run status `assembled`.

Failure mode:

A future Codex run resumes from a debug/smoke bundle, sees assemble ready, and reports success without real Telegram delivery.

Smallest fix:

Represent skipped delivery as non-final state, such as `delivery-skipped`; keep CLI exit `0` for smoke if needed, but do not let status treat it as normal completion.

### P0 — single mode can legally contain two chunks, but `SKILL.md` tells Codex to extract only one

Files:

- `SKILL.md`
- `scripts/notes-runner`
- `scripts/notes_runner_lib/prepare_runtime.py`
- `scripts/notes_runner_lib/prepare_logic_runtime.py`
- `tests/test_prepare_runtime.py`
- `tests/test_notes_runner_regressions.py`

Mismatch:

Runner can return `execution_plan.mode == "single"` for a short monologue with up to two chunks. `SKILL.md` says to launch one worker using `extract.A` or the only chunk entry.

Failure mode:

Chunk `B` can be lost while assemble still produces a superficially valid note.

Smallest fix:

Prefer the clean invariant: `single` only when `total_chunks == 1`; otherwise use `micro-multi`.

### P0 — extraction readiness can be faked without a block, summary, or completed sentinel

Files:

- `scripts/notes_runner_lib/prepare_runtime.py`
- `SKILL.md`
- `scripts/notes_runner_lib/prepare_logic_runtime.py`
- `tests/test_status_runtime.py`

Mismatch:

Skill and extraction prompts require blocks, manifest, summary, and sentinel. Runner readiness can accept looser states: sentinel outputs with manifest but no block, or block + manifest without summary, and it does not require `sentinel.completed == true`.

Failure mode:

Codex skips extraction on resume because status says ready even though output is incomplete.

Smallest fix:

Chunk ready should require:

- sentinel exists
- `sentinel.completed == true`
- fingerprint matches planned chunk fingerprint
- at least one block file exists
- manifest exists
- summary exists
- all sentinel-declared outputs exist

No sentinel should mean `partial`, not `ready`.

### P0 — assemble readiness is based on `*.html` in `$WORK_DIR`, not real bundle outputs or delivery truth

Files:

- `scripts/notes_runner_lib/prepare_runtime.py`
- `scripts/notes_runner_lib/status_runtime.py`
- `scripts/notes_runner_lib/assemble_finalize_runtime.py`
- `SKILL.md`

Mismatch:

Final outputs are in `$BUNDLE_DIR`, but `build_stage_statuses()` checks `work_dir.glob("*.html")`. Telegram success is also part of normal completion, but readiness does not validate it.

Failure mode:

A stray HTML in `$WORK_DIR` can make assemble look ready; real bundle output paths may not be represented correctly.

Smallest fix:

Assemble status should be derived from `work/stages/assemble.json`, `run.json`, actual `output_md` / `output_html` existence under bundle, and normal delivery truth.

### P0 — batch mode has no one-shot continuation contract

Files:

- `SKILL.md`
- `README.md`
- `tests/test_notes_runner_regressions.py`

Mismatch:

`SKILL.md` routes directory input to `batch --prepare --json`, then applies the single-note JSON contract. Batch output is multi-result, and tests do not prove continuation through extraction/header/assemble/delivery for every prepared item.

Failure mode:

Codex can stop after batch prepare or treat multi-result batch payload as one note.

Smallest fix:

Either remove batch from user-facing one-shot skill until runner owns full batch assembly, or define a batch JSON contract over `results[]`.

## P1/P2 highlights

- `SKILL.md` still says Telegram is “best-effort” while runner treats delivery failure as blocking.
- `replace-speakers` is unconditional in the skill, while runner exposes partial flags and lacks a proper replace-speakers stage status.
- Single-mode missing `tldr.md` is not blocked by execution plan.
- README says delivery can be disabled by config, but normal runner completion treats disabled delivery as failed.
- Final quality does not validate planned chunk completeness.
- `SKILL.md` documents stale speaker hint values: `skip`/`identify` vs runner `skip`/`optional`/`required`.
- Tests over-check static text and under-check runtime state-machine behavior.

## Missing tests

1. `test_skip_telegram_does_not_mark_normal_assemble_ready`
2. `test_single_mode_never_has_multiple_pending_chunks`
3. `test_chunk_not_ready_without_block_file_even_with_manifest_and_sentinel`
4. `test_chunk_not_ready_when_sentinel_completed_false`
5. `test_chunk_not_ready_without_summary`
6. `test_stray_workdir_html_does_not_make_assemble_ready`
7. `test_final_quality_fails_missing_planned_chunk`
8. static forbidden phrase: `Telegram is best-effort inside assemble only`
9. batch contract test for directory input
10. black-box release-check test proving `SKIP` exits non-zero

## Prompt simplification

Remove or move out of `SKILL.md`:

- hardcoded extraction schema details that runner prompt packs and `note-contract.json` own
- direct branching on `$SPEAKER_STAGE`
- manual title heuristics that should live in header prompt/seed
- unconditional `replace-speakers`
- batch as if it were a single-note flow
- “Telegram is best-effort”

## Boundary

Python runner owns:

- input routing
- prepare/resume state
- chunking
- prompt pack paths
- note contract
- speaker/TL;DR/header routing
- assemble
- Telegram delivery truth
- completion truth

Skill prompt / Codex owns:

- pass user input into runner
- read JSON state
- launch agents only for planned missing stages
- write requested intermediate artifacts
- run assemble and interpret exit code
- report success only when runner state says normal completion is complete

## Next patches

1. `assemble_finalize_runtime.py` + `status_runtime.py`: skipped Telegram cannot mark normal assemble ready.
2. `prepare_runtime.py`: harden `infer_chunk_status()`.
3. `prepare_runtime.py` + `status_runtime.py`: fix assemble readiness source.
4. `prepare_runtime.py` + `prepare_logic_runtime.py` + tests: make `single` exactly one chunk.
5. `SKILL.md` + `README.md` + `tests/test_repo_contracts.py`: remove contradictory prompt/docs drift and clarify batch.

## Patch progress

### 2026-04-27 — Patch 1 done

Closed the first P0:

- `scripts/notes_runner_lib/assemble_finalize_runtime.py` now records `delivery-skipped` instead of normal `ready/assembled` when `assemble --skip-telegram` succeeds without real delivery.
- Smoke/debug CLI behavior stays usable: JSON mode still exits `0`, but persisted state is not a normal completion state.
- `tests/test_assemble_finalize_runtime.py` now asserts skipped Telegram does not mark assemble ready.

Verification:

```bash
python3 -m pytest tests/test_assemble_finalize_runtime.py -q
# 4 passed

python3 -m pytest tests/test_status_runtime.py tests/test_notes_runner_regressions.py tests/test_assemble_shell_runtime.py -q
# 21 passed

bash scripts/release-check.sh
# PASS: 30  FAIL: 0  SKIP: 0
```

### 2026-04-27 — Patch 2 done

Closed the chunk-readiness P0:

- `scripts/notes_runner_lib/prepare_runtime.py` now treats a planned chunk as `ready` only when it has a completed extraction sentinel, matching chunk fingerprint when one is planned, at least one block file, `manifest_chunk_[id].tsv`, `summary_chunk_[id].md`, and all declared sentinel outputs.
- Planned chunks with block/manifest/summary but no sentinel are now `partial`, not `ready`.
- `summary_chunk_*.md` participates in chunk discovery and status payloads now expose a `summary` path.
- `scripts/test-pipeline.sh` now creates extraction sentinels for copied local fixtures in temp dirs, so release checks do not depend on ignored local fixture files.
- `tests/test_prepare_runtime.py` and `tests/test_status_runtime.py` cover missing/completed sentinel, missing summary, fingerprint mismatch, and no-sentinel partial status.

Verification:

```bash
python3 -m pytest tests/test_prepare_runtime.py tests/test_status_runtime.py -q
# 10 passed

bash scripts/test-pipeline.sh --quick
# PASS: 30  FAIL: 0  SKIP: 0

bash scripts/release-check.sh
# PASS: 30  FAIL: 0  SKIP: 0
```

### 2026-04-27 — Patch 3 done

Closed the assemble-readiness P0:

- `scripts/notes_runner_lib/prepare_runtime.py` no longer treats stray `*.html` files in `$WORK_DIR` as assemble completion.
- Assemble readiness now comes from `work/stages/assemble.json`, real bundle output paths from the sentinel / `run.json` / suggested output paths, and Telegram delivery truth from bundle `run.json`.
- Completed assemble with missing bundle outputs becomes `partial`; fingerprint mismatch or stale upstream stages become `stale`; skipped delivery becomes `delivery-skipped`; missing successful delivery becomes `failed`.
- Output path lists are deduplicated before status reporting.
- `tests/test_status_runtime.py` now covers stray workdir HTML and successful bundle-output + delivery readiness.

Verification:

```bash
python3 -m pytest tests/test_status_runtime.py tests/test_prepare_runtime.py -q
# 12 passed

python3 -m pytest tests/test_notes_runner_regressions.py tests/test_assemble_finalize_runtime.py tests/test_assemble_shell_runtime.py -q
# 23 passed

bash scripts/test-pipeline.sh --quick
# PASS: 30  FAIL: 0  SKIP: 0

bash scripts/release-check.sh
# PASS: 30  FAIL: 0  SKIP: 0
```

### 2026-04-27 — Patch 4 done

Closed the `single`-mode multi-chunk P0:

- `scripts/notes_runner_lib/prepare_runtime.py` now makes `single` mean exactly one chunk.
- Short monologues with two chunks now route to `micro-multi`, so Codex will process all chunks through the parallel chunk contract instead of only `extract.A`.
- `tests/test_prepare_runtime.py` now locks the invariant: `execution_mode_for_plan(1, ...) == "single"` and `execution_mode_for_plan(2, ...) == "micro-multi"`.

Verification:

```bash
python3 -m pytest tests/test_prepare_runtime.py tests/test_prepare_logic_runtime.py tests/test_status_runtime.py tests/test_notes_runner_regressions.py -q
# 35 passed

bash scripts/test-pipeline.sh --quick
# PASS: 30  FAIL: 0  SKIP: 0

bash scripts/release-check.sh
# PASS: 30  FAIL: 0  SKIP: 0
```

### 2026-04-27 — Patch 5 done

Closed the batch contract P0 by making the current boundary explicit:

- `SKILL.md` now says batch JSON is not a single-note payload and must not be fed into the single-note continuation flow.
- Batch mode now reports `results`, `index`, `ok`, and `failed`; it must not claim final notes, final HTML, or Telegram delivery unless the runner result explicitly includes final artifacts for each item.
- `README.md` and `ADVANCED.md` now describe batch as prepare/index mode, not completed per-item `/notes` delivery.
- `tests/test_repo_contracts.py` locks this contract and forbids the old README promise.

Verification:

```bash
python3 -m pytest tests/test_repo_contracts.py tests/test_notes_runner_regressions.py -q
# 59 passed

bash scripts/test-pipeline.sh --quick
# PASS: 30  FAIL: 0  SKIP: 0

bash scripts/release-check.sh
# PASS: 30  FAIL: 0  SKIP: 0
```
