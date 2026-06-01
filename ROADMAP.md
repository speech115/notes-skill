# Roadmap

## Current bet

Keep `/notes` boring, deterministic, and honest: repo truth first, runner state first, Telegram delivery not faked.

## Near term

- Keep `scripts/release-check.sh` as the release gate.
- Keep quick deterministic checks free of unexpected `SKIP`.
- Improve failures by making runner state and file artifacts easier to inspect.
- Preserve the one-shot contract: prepare, extraction, header, assemble, and delivery should finish without handing manual runner chores back to the user.

## Not now

- No platform rewrite around the skill.
- No hand-edits in live install as normal workflow.
- No broad folder architecture unless the repo actually starts producing those artifacts.
