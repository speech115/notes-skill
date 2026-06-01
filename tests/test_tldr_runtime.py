import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from notes_runner_lib.tldr_runtime import read_summary_points


class TldrRuntimeTests(unittest.TestCase):
    def test_read_summary_points_removes_internal_chunk_language(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            summary_path = Path(tmp_dir) / "summary_chunk_A.md"
            summary_path.write_text(
                "\n".join(
                    [
                        "1. Чанк фиксирует старт брейншторма: участники быстро подбирают форматы.",
                        "2. Провокация полезна, но в транскрипте заметен риск байта ради байта.",
                        "3. Главный итог чанка — зафиксировать действия на 24 часа.",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            points = read_summary_points(summary_path)

        joined = "\n".join(points).casefold()
        self.assertNotIn("чанк", joined)
        self.assertNotIn("транскрипт", joined)
        self.assertIn("брейншторма", points[0])
        self.assertIn("в обсуждении заметен риск", points[1])
        self.assertIn("Главный итог обсуждения", points[2])


if __name__ == "__main__":
    unittest.main()
