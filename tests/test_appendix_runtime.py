import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from notes_runner_lib.appendix_runtime import build_deterministic_appendix


def _load_json_if_exists(path: Path) -> dict | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _read_summary_points(path: Path) -> list[str]:
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines()
        if line.strip()
    ]


def _read_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


class AppendixRuntimeTests(unittest.TestCase):
    def test_build_deterministic_appendix_rewrites_question_style_action_check(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            work_dir = Path(tmp_dir)
            (work_dir / "header-seed.json").write_text("{}", encoding="utf-8")
            (work_dir / "manifest_chunk_A.tsv").write_text(
                "\n".join(
                    [
                        "block_file\ttimestamp_start\ttimestamp_end\ttopic\tprimary_claim\tnames\tresources\tcase_title\thas_dialogue\tquote_text\taction_now\taction_check\taction_avoid\tquotes_count\tcases",
                        "chunk_A_block_01.md\t00:00\t01:00\tЖелания\tГлавная мысль\t\t\t\t0\t\t\tКакие свои желания я игнорирую из-за чужих ожиданий?\t\t0\t0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            appendix_path = build_deterministic_appendix(
                work_dir,
                header_seed_filename="header-seed.json",
                load_json_if_exists=_load_json_if_exists,
                read_summary_points=_read_summary_points,
                read_text_file=_read_text_file,
                write_text=_write_text,
            )

            text = appendix_path.read_text(encoding="utf-8")
            self.assertIn(
                "- [ ] Ответь себе на вопрос: Какие свои желания я игнорирую из-за чужих ожиданий?",
                text,
            )


if __name__ == "__main__":
    unittest.main()
