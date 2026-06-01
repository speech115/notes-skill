# Oracle prompt: `/notes` one-shot contract audit

You are reviewing a local Codex skill repo: `/Users/sereja/Projects/products/notes-skill`.

The project is a local `/notes` skill. It routes YouTube/local transcript/audio/video/batch inputs through `scripts/notes-runner`, prepares prompt packs and work state, asks agents to extract blocks, writes a header, assembles final Markdown/HTML, validates quality, and normally delivers the result to Telegram.

I want a hard repo-grounded audit of the central contract: `SKILL.md` tells Codex to continue after prepare and finish extraction/header/assemble/delivery autonomously, while the Python runner owns routing, execution plans, prompt packs, note contracts, status, quality checks, and delivery truth.

Focus on drift between:
- `SKILL.md` user/agent instructions,
- runner reality in `scripts/notes_runner_lib/`,
- tests in `tests/`,
- release/docs promises in `README.md`, `RELEASE.md`, `OBSERVABILITY.md`, and `TROUBLESHOOTING.md`.

Do not give a generic architecture review. Find concrete places where a future Codex run could do the wrong thing, stop too early, rerun unsafe stages, ignore runner state, fake completion, over-compress long content, or treat Telegram/delivery failures incorrectly.

Output format:

1. Findings first, ordered by severity (`P0`, `P1`, `P2`). Each finding must include file paths and the exact contract mismatch.
2. Missing tests: list the smallest regression tests that would catch the risk.
3. Prompt simplification: what should be removed or moved out of `SKILL.md` because runner state should own it.
4. Runner-owned vs agent-owned boundary: a crisp table of what belongs in Python vs the skill prompt.
5. Next 5 patches: the best implementation order, with narrow file targets.

Important local constraints:
- This repo is source of truth; live installs under `~/.codex/skills/notes` or `~/.agents/skills/notes` are deployment targets.
- A normal user-facing `/notes` completion is not truly complete if Telegram delivery failed, unless the user explicitly asked for debug/smoke behavior.
- `--skip-telegram` is only for local/debug smoke.
- `release-check.sh` treating `SKIP` as acceptable was previously fixed; if quick deterministic checks skip unexpectedly, that is a harness bug.
- Do not propose a big platform rewrite. We want surgical, test-backed improvements.
