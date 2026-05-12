import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from notes_runner_lib.html_theme_runtime import add_longform_semantics, main


class HtmlThemeRuntimeTests(unittest.TestCase):
    def test_add_longform_semantics_marks_known_note_sections(self) -> None:
        html = """<html><body><main class="note-shell">
<nav id="TOC"><ul><li>one</li></ul></nav>
<h2>Manus AI: что это такое (00:00-05:30)</h2>
<h3>Тезисы:</h3>
<ol><li>Первый тезис.</li></ol>
<h3>Кейс: Стефани</h3>
<p>Контекст кейса.</p>
<blockquote><p>Only the paranoid survive</p></blockquote>
<h1>Упомянутые люди и ресурсы</h1>
<table><tr><td>Manus</td></tr></table>
<h1>План действий</h1>
<ul><li>Сделать шаг.</li></ul>
</main></body></html>"""

        rendered = add_longform_semantics(html)

        self.assertIn('class="note-toc"', rendered)
        self.assertIn('class="note-chapter"', rendered)
        self.assertIn('class="note-outline"', rendered)
        self.assertIn('class="note-case"', rendered)
        self.assertIn('class="note-quote"', rendered)
        self.assertIn('class="note-appendix"', rendered)
        self.assertIn("note-action-plan", rendered)

    def test_add_longform_semantics_leaves_plain_html_unchanged(self) -> None:
        html = "<html><body><p>x</p></body></html>"

        self.assertEqual(add_longform_semantics(html), html)

    def test_main_rewrites_html_file_in_place(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "note.html"
            path.write_text("<html><body><nav id=\"TOC\"></nav></body></html>", encoding="utf-8")

            exit_code = main([str(path)])

            self.assertEqual(exit_code, 0)
            self.assertIn('class="note-toc"', path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
