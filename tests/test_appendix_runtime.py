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
    def test_build_deterministic_appendix_rewrites_question_style_action_check_to_check_prompt(self) -> None:
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
                "- [ ] Проверь: Какие свои желания я игнорирую из-за чужих ожиданий?",
                text,
            )
            self.assertNotIn("Ответь себе на вопрос:", text)

    def test_build_deterministic_appendix_prefers_manifest_actions_and_ignores_noisy_people_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            work_dir = Path(tmp_dir)
            (work_dir / "header-seed.json").write_text(
                json.dumps({"author_hint": "KARLO BRANS"}, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            (work_dir / "manifest_chunk_A.tsv").write_text(
                "\n".join(
                    [
                        "block_file\ttimestamp_start\ttimestamp_end\ttopic\tprimary_claim\tnames\tresources\tcase_title\thas_dialogue\tquote_text\taction_now\taction_check\taction_avoid\tquotes_count\tcases",
                        "chunk_A_block_01.md\t00:00\t05:00\tИИ заменяет функцию\tГлавная мысль\tKARLO BRANS, Стив Джобс, Генри Форд\tGPT Chat\t\t0\t\tОпиши свою работу как набор решений\tМогу ли я объяснить критерии качества?\tНе отдавай машине направление\t0\t0",
                        "chunk_A_block_02.md\t05:00\t10:00\tЖивой голос выигрывает\tГлавная мысль\tKARLO BRANS\tSpotify, Reddit\tVelvet Sundown\t0\t\tСобери свои критерии качества\tГде аудитория слышит живой голос?\tНе пытайся побеждать ИИ его же оружием\t0\t1",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            (work_dir / "summary_chunk_A.md").write_text(
                "1. Чем больше машинного шума, тем важнее живой голос.\n",
                encoding="utf-8",
            )
            (work_dir / "chunk_A_block_01.md").write_text(
                "\n".join(
                    [
                        "## ИИ заменяет функцию",
                        "",
                        "### Тезисы:",
                        "1. Автор начинает с разворота против массовой паники. *(00:00)*",
                        "2. Velvet Sundown быстро наскучивает без живого ядра. *(02:00)*",
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
            self.assertIn("- [ ] Опиши свою работу как набор решений", text)
            self.assertIn("- [ ] Собери свои критерии качества", text)
            self.assertNotIn("Автор начинает с разворота против массовой паники", text)
            self.assertNotIn("Velvet Sundown:**", text)
            self.assertNotIn("Генри Форда", text)
            self.assertNotIn("Стива Джобса", text)

    def test_build_deterministic_appendix_keeps_resource_descriptions_concise(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            work_dir = Path(tmp_dir)
            (work_dir / "header-seed.json").write_text("{}", encoding="utf-8")
            (work_dir / "manifest_chunk_A.tsv").write_text(
                "\n".join(
                    [
                        "block_file\ttimestamp_start\ttimestamp_end\ttopic\tprimary_claim\tnames\tresources\tcase_title\thas_dialogue\tquote_text\taction_now\taction_check\taction_avoid\tquotes_count\tcases",
                        "chunk_A_block_01.md\t00:00\t05:00\tФормат важнее подготовки\tФормат важнее красивой подготовки\tАртемий; Casey Neistat\tInstagram; YouTube; Reels\t\t0\t\tЗапусти минимальный формат\tЧто вышло в публикацию?\tНе жди идеального монтажа\t0\t0",
                        "chunk_A_block_02.md\t05:00\t10:00\tРоману нужен проводник в здоровье\tРоману предлагают стать понятным проводником в здоровье через сильный монтаж и широкие темы\tРоман; Александр Дзидзария\tInstagram; YouTube; Corso\t\t0\t\tВыбери одну широкую тему\tСтал ли ролик понятнее?\tНе копируй чужой образ\t0\t0",
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
            people_section = text.split("## Люди", 1)[1].split("## Ресурсы", 1)[0]
            resources_section = text.split("## Ресурсы", 1)[1].split("---", 1)[0]
            self.assertIn("- **Роман:** участник или адресат идеи в обсуждении.", text)
            self.assertIn("- **Casey Neistat:** упоминается как человек, автор или культурный референс.", text)
            self.assertNotIn("Роману предлагают стать понятным проводником", people_section)
            self.assertNotIn("Формат важнее красивой подготовки", people_section)
            self.assertIn("- **Instagram:** площадка или формат распространения контента.", text)
            self.assertIn("- **YouTube:** площадка или формат распространения контента.", text)
            self.assertIn("- **Corso:** контентный референс для формата и подачи.", text)
            self.assertNotIn("Роману предлагают стать понятным проводником", resources_section)
            self.assertNotIn("Формат важнее красивой подготовки", resources_section)


if __name__ == "__main__":
    unittest.main()
