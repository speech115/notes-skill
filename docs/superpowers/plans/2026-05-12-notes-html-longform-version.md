# Notes HTML Longform Version Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a rollback-safe `longform` HTML version for `/notes` while preserving the current `classic` HTML output.

**Architecture:** Keep Markdown assembly and Pandoc conversion in `assemble.sh`. Add a theme selector that defaults to `classic`, then introduce separate longform template/CSS files and a deterministic postprocessor that adds semantic classes only in `longform` mode.

**Tech Stack:** Bash, Python standard library, Pandoc standalone HTML, pytest/unittest, local fixture-based smoke checks.

---

## File Structure

- Modify: `/Users/sereja/Projects/products/notes-skill/assemble.sh`
  - Accept optional fifth argument for HTML theme.
  - Select classic or longform template/CSS.
  - Run longform postprocessing only for longform.
- Modify: `/Users/sereja/Projects/products/notes-skill/scripts/notes_runner_lib/parser_runtime.py`
  - Add `--html-theme {classic,longform}` to `notes-runner assemble`.
- Modify: `/Users/sereja/Projects/products/notes-skill/scripts/notes_runner_lib/assemble_shell_runtime.py`
  - Pass selected theme to `assemble.sh`.
  - Include the selected theme in `run.json` state seed.
- Create: `/Users/sereja/Projects/products/notes-skill/template-longform.html`
  - Longform page shell.
- Create: `/Users/sereja/Projects/products/notes-skill/longform-theme.css`
  - Longform typography and semantic class styling.
- Create: `/Users/sereja/Projects/products/notes-skill/scripts/notes_runner_lib/html_theme_runtime.py`
  - Deterministic HTML postprocessor for longform classes.
- Create/modify tests:
  - `/Users/sereja/Projects/products/notes-skill/tests/test_html_theme_runtime.py`
  - `/Users/sereja/Projects/products/notes-skill/tests/test_assemble_shell_runtime.py`
  - `/Users/sereja/Projects/products/notes-skill/tests/test_notes_runner_regressions.py`
  - `/Users/sereja/Projects/products/notes-skill/scripts/test-pipeline.sh`

No commit steps are included because the current repo has unrelated dirty changes. Do not commit until the user explicitly asks and the dirty tree has been handled.

### Task 1: CLI Theme Selection

**Files:**
- Modify: `/Users/sereja/Projects/products/notes-skill/scripts/notes_runner_lib/parser_runtime.py`
- Modify: `/Users/sereja/Projects/products/notes-skill/scripts/notes_runner_lib/assemble_shell_runtime.py`
- Test: `/Users/sereja/Projects/products/notes-skill/tests/test_assemble_shell_runtime.py`

- [ ] **Step 1: Write tests for default and explicit theme routing**

Add tests that build `argparse.Namespace` with and without `html_theme`.

Expected assertions:

```python
self.assertEqual(context.html_theme, "classic")
self.assertIn("--html-theme", help_text)
self.assertEqual(recorded_command[-1], "longform")
```

- [ ] **Step 2: Run the targeted tests and verify they fail**

Run:

```bash
python3 -m pytest tests/test_assemble_shell_runtime.py -q
```

Expected: failures because `AssembleShellContext.html_theme` and command forwarding do not exist yet.

- [ ] **Step 3: Implement theme plumbing**

Add `html_theme: str` to `AssembleShellContext`.

In `prepare_assemble_shell_context`, resolve:

```python
html_theme = str(getattr(args, "html_theme", None) or "classic")
if html_theme not in {"classic", "longform"}:
    raise ValueError(f"Unsupported HTML theme: {html_theme}")
```

Add it to `state_seed`:

```python
"html_theme": html_theme,
```

Pass it to shell:

```python
[
    "bash",
    str(deps.assemble_script),
    str(context.work_dir),
    str(context.output_md),
    str(context.output_html),
    args.title,
    context.html_theme,
]
```

Add parser option:

```python
assemble_parser.add_argument(
    "--html-theme",
    choices=("classic", "longform"),
    default="classic",
    help="HTML rendering theme. Use classic for current output or longform for annotated reader output.",
)
```

- [ ] **Step 4: Run targeted tests**

Run:

```bash
python3 -m pytest tests/test_assemble_shell_runtime.py -q
```

Expected: pass.

### Task 2: Longform Theme Assets and Shell Selection

**Files:**
- Modify: `/Users/sereja/Projects/products/notes-skill/assemble.sh`
- Create: `/Users/sereja/Projects/products/notes-skill/template-longform.html`
- Create: `/Users/sereja/Projects/products/notes-skill/longform-theme.css`
- Test: `/Users/sereja/Projects/products/notes-skill/scripts/test-pipeline.sh`

- [ ] **Step 1: Add shell fallback tests**

In `scripts/test-pipeline.sh`, extend assemble smoke coverage to run:

```bash
$RUN_CMD assemble "$work_dir" "$classic_md" "$classic_html" "Classic Theme" --html-theme classic --skip-telegram --json
$RUN_CMD assemble "$work_dir" "$longform_md" "$longform_html" "Longform Theme" --html-theme longform --skip-telegram --json
```

Check:

```bash
grep -q '<html' "$classic_html"
! grep -q 'note-page' "$classic_html"
grep -q 'note-page' "$longform_html"
grep -q 'Longform Theme' "$longform_html"
```

- [ ] **Step 2: Run shell smoke and verify longform fails**

Run:

```bash
bash scripts/test-pipeline.sh
```

Expected: failure for the new longform checks because `--html-theme` or longform files do not exist yet.

- [ ] **Step 3: Add longform template and CSS**

Copy the current `template.html` structure into `template-longform.html`, then change body shell to:

```html
<body class="note-page">
<main class="note-shell">
...
</main>
</body>
```

Keep existing timestamp JavaScript behavior.

Create `longform-theme.css` with:

```css
:root {
  --note-bg: #111416;
  --note-paper: #181d20;
  --note-text: #e8e3d8;
  --note-muted: #a8a096;
  --note-line: #30363a;
  --note-accent: #d2a55f;
  --note-link: #8fb7ff;
}
```

Add styles for `.note-shell`, `.note-hero`, `.note-toc`, `.note-chapter`, `.note-time`, `.note-outline`, `.note-case`, `.note-quote`, `.note-margin`, `.note-appendix`, `.note-action-plan`, responsive mobile, and print.

- [ ] **Step 4: Select assets in `assemble.sh`**

At the top:

```bash
HTML_THEME="${5:-${NOTES_HTML_THEME:-classic}}"
case "$HTML_THEME" in
  classic)
    CSS_FILE="$SCRIPT_DIR/dark-theme.css"
    TEMPLATE="$SCRIPT_DIR/template.html"
    ;;
  longform)
    CSS_FILE="$SCRIPT_DIR/longform-theme.css"
    TEMPLATE="$SCRIPT_DIR/template-longform.html"
    ;;
  *)
    echo "ERROR: Unsupported HTML theme: $HTML_THEME (expected classic or longform)" >&2
    exit 2
    ;;
esac
```

Keep classic behavior as the default.

- [ ] **Step 5: Run targeted shell assemble**

Run:

```bash
tmpdir="$(mktemp -d)"
cp -R test-fixtures/multi-chunk "$tmpdir/work"
python3 scripts/notes-runner assemble "$tmpdir/work" "$tmpdir/classic.md" "$tmpdir/classic.html" "Classic Theme" --html-theme classic --skip-telegram --json
python3 scripts/notes-runner assemble "$tmpdir/work" "$tmpdir/longform.md" "$tmpdir/longform.html" "Longform Theme" --html-theme longform --skip-telegram --json
```

Expected: both commands exit 0, both HTML files exist, classic has no `.note-page`, longform has `.note-page`.

### Task 3: Deterministic Longform Postprocessor

**Files:**
- Create: `/Users/sereja/Projects/products/notes-skill/scripts/notes_runner_lib/html_theme_runtime.py`
- Modify: `/Users/sereja/Projects/products/notes-skill/assemble.sh`
- Test: `/Users/sereja/Projects/products/notes-skill/tests/test_html_theme_runtime.py`

- [ ] **Step 1: Write postprocessor tests**

Create tests using small HTML strings.

Assertions:

```python
assert 'class="note-chapter"' in rendered
assert 'class="note-outline"' in rendered
assert 'class="note-case"' in rendered
assert 'class="note-appendix"' in rendered
assert 'class="note-action-plan"' in rendered
```

Also assert conservative fallback:

```python
assert add_longform_semantics("<html><body><p>x</p></body></html>") == original_html
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
python3 -m pytest tests/test_html_theme_runtime.py -q
```

Expected: import failure because module does not exist.

- [ ] **Step 3: Implement postprocessor**

Implement `add_longform_semantics(html: str) -> str` using standard-library `html.parser.HTMLParser` or conservative regexes.

Required behavior:

- add `note-toc` to `nav#TOC`;
- wrap each `h2` section until next `h2` in `<section class="note-chapter">`;
- add `note-outline` to the list following heading text `Тезисы`;
- wrap content following `h3` beginning with `Кейс` until next `h3`/`h2` in `.note-case`;
- add `note-quote` to blockquotes;
- add `note-appendix` to sections starting at `Упомянутые`, `План действий`, or `Ключевые идеи`;
- add `note-action-plan` to the `План действий` section.

Prefer conservative no-op over broken markup.

Expose CLI:

```python
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("html_path")
    args = parser.parse_args(argv)
    path = Path(args.html_path)
    path.write_text(add_longform_semantics(path.read_text(encoding="utf-8")), encoding="utf-8")
    return 0
```

- [ ] **Step 4: Wire postprocessor into `assemble.sh`**

After Pandoc succeeds:

```bash
if [[ "$HTML_THEME" == "longform" ]]; then
  python3 "$SCRIPT_DIR/scripts/notes_runner_lib/html_theme_runtime.py" "$OUTPUT_HTML"
fi
```

- [ ] **Step 5: Run postprocessor tests**

Run:

```bash
python3 -m pytest tests/test_html_theme_runtime.py -q
```

Expected: pass.

### Task 4: Runner Regression and Rollback Proof

**Files:**
- Modify: `/Users/sereja/Projects/products/notes-skill/tests/test_notes_runner_regressions.py`
- Modify: `/Users/sereja/Projects/products/notes-skill/tests/test_assemble_shell_runtime.py`

- [ ] **Step 1: Add regression tests**

Add a regression proving:

- default assemble uses `classic`;
- explicit `--html-theme longform` reaches shell command;
- invalid theme is rejected by argparse;
- run state includes `"html_theme": "longform"`.

- [ ] **Step 2: Run targeted regression tests**

Run:

```bash
python3 -m pytest tests/test_assemble_shell_runtime.py tests/test_notes_runner_regressions.py -q
```

Expected: pass.

- [ ] **Step 3: Run fixture assemble in both modes**

Run:

```bash
tmpdir="$(mktemp -d)"
cp -R test-fixtures/multi-chunk "$tmpdir/work"
python3 scripts/notes-runner assemble "$tmpdir/work" "$tmpdir/classic.md" "$tmpdir/classic.html" "Classic Fixture" --html-theme classic --skip-telegram --json
python3 scripts/notes-runner assemble "$tmpdir/work" "$tmpdir/longform.md" "$tmpdir/longform.html" "Longform Fixture" --html-theme longform --skip-telegram --json
grep -q 'note-page' "$tmpdir/longform.html"
! grep -q 'note-page' "$tmpdir/classic.html"
```

Expected: all commands succeed.

### Task 5: Visual QA

**Files:**
- No required source edits unless QA finds a concrete issue.

- [ ] **Step 1: Open longform fixture in browser**

Use the generated `longform.html`.

Expected: title, TOC, chapters, quotes, case sections, appendix, and action plan are visible and not card-fragmented.

- [ ] **Step 2: Check mobile width**

Use a narrow viewport around 390px.

Expected: no horizontal text overflow, tables scroll or fit, back-to-top button does not cover content.

- [ ] **Step 3: Check classic rollback**

Open generated `classic.html`.

Expected: old visual style still works and does not include longform semantic classes.

### Task 6: Final Verification

**Files:**
- No required source edits unless verification finds a concrete issue.

- [ ] **Step 1: Run unit tests for touched runtime**

Run:

```bash
python3 -m pytest tests/test_html_theme_runtime.py tests/test_assemble_shell_runtime.py tests/test_notes_runner_regressions.py -q
```

Expected: pass.

- [ ] **Step 2: Run repo status command**

Run:

```bash
bin/status
```

Expected: status command exits 0 or reports only known pre-existing dirty files plus the intentional new longform changes.

- [ ] **Step 3: Run release check if runtime tests are green**

Run:

```bash
bash scripts/release-check.sh
```

Expected: pass. If it fails for pre-existing dirty-tree reasons, record exact failure and do not hide it.

## Self-Review

Spec coverage:

- Separate rollback-safe version: covered by Tasks 1, 2, 4, and 5.
- Longform visual shell: covered by Task 2.
- Semantic minimum: covered by Task 3.
- Classic fallback: covered by Tasks 2, 4, and 5.
- Verification: covered by Tasks 4, 5, and 6.

Placeholder scan:

- No TBD/TODO placeholders.
- No unspecified “add tests” steps without expected assertions.

Scope check:

- Single subsystem: HTML rendering path for assembled notes.
- No Telegram, transcription, extraction, or quality-contract changes.
