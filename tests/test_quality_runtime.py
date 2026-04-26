import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from notes_runner_lib.quality_runtime import compute_final_quality_checks


def _update_prepare_state_fields(work_dir: Path, updates: dict) -> None:
    path = work_dir / "prepare_state.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(payload.get(key), dict):
            payload[key].update(value)
        else:
            payload[key] = value
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class QualityRuntimeTests(unittest.TestCase):
    def test_actionability_accepts_answer_question_prefix_with_question_word(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            work_dir = Path(tmp_dir)
            (work_dir / "prepare_state.json").write_text(
                json.dumps({"telemetry": {"duration_seconds": 0}}, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            (work_dir / "note-contract.json").write_text(
                json.dumps(
                    {
                        "content_mode": "monologue",
                        "header": {"required_metadata": ["Автор", "Формат", "Тема", "Длительность", "Источник"]},
                        "tldr": {"min_items": 1, "max_items": 8},
                        "blocks": {},
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            (work_dir / "quality-checks.json").write_text(
                json.dumps({"schema_version": 1, "content_mode": "monologue", "prepare": {}, "final": {}}, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            (work_dir / "tldr.md").write_text("1. Сомнение считывается раньше аргументов.\n", encoding="utf-8")

            output_md = work_dir / "note.md"
            output_md.write_text(
                "\n".join(
                    [
                        "# Тестовая заметка",
                        "",
                        "> Короткий абстракт.",
                        "",
                        "**Автор:** Тест",
                        "**Формат:** лекция",
                        "**Тема:** Продажи",
                        "**Длительность:** 00:00",
                        "**Источник:** https://example.com",
                        "",
                        "## Главная рамка автора",
                        "- Клиент замечает сомнение раньше объяснений.",
                        "",
                        "# План действий",
                        "",
                        "### На этой неделе",
                        "- [ ] Ответь себе на вопрос: где клиент считывает мое сомнение раньше аргументов?",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            quality = compute_final_quality_checks(
                work_dir,
                output_md,
                update_prepare_state_fields=_update_prepare_state_fields,
            )

            self.assertEqual(quality["final"]["actionability_score"]["items"], 1)
            self.assertEqual(quality["final"]["actionability_score"]["verbish_items"], 1)
            self.assertTrue(quality["final"]["actionability_score"]["ok"])

    def test_actionability_accepts_broader_real_imperatives(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            work_dir = Path(tmp_dir)
            (work_dir / "prepare_state.json").write_text(
                json.dumps({"telemetry": {"duration_seconds": 1385}}, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            (work_dir / "note-contract.json").write_text(
                json.dumps(
                    {
                        "content_mode": "monologue",
                        "header": {"required_metadata": ["Автор", "Формат", "Тема", "Длительность", "Источник"]},
                        "tldr": {"min_items": 1, "max_items": 8},
                        "blocks": {},
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            (work_dir / "quality-checks.json").write_text(
                json.dumps({"schema_version": 1, "content_mode": "monologue", "prepare": {}, "final": {}}, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            (work_dir / "tldr.md").write_text("1. ИИ заменяет исполнителя, а не автора замысла.\n", encoding="utf-8")

            output_md = work_dir / "note.md"
            output_md.write_text(
                "\n".join(
                    [
                        "# Тестовая заметка",
                        "",
                        "> Короткий абстракт.",
                        "",
                        "**Автор:** Тест",
                        "**Формат:** лекция",
                        "**Тема:** ИИ и смысл",
                        "**Длительность:** 23:05",
                        "**Источник:** https://example.com",
                        "",
                        "## Главная рамка автора",
                        "- ИИ давит на функцию.",
                        "- Видение остаётся у человека.",
                        "- Практический вывод нужен сразу.",
                        "",
                        "# План действий",
                        "",
                        "### Прямо сейчас",
                        "- [ ] Опиши свою работу как набор решений, а не операций",
                        "- [ ] Собери критерии качества до делегирования",
                        "- [ ] Усиль один живой канал общения",
                        "- [ ] Оставь себе финальное решение",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            quality = compute_final_quality_checks(
                work_dir,
                output_md,
                update_prepare_state_fields=_update_prepare_state_fields,
            )

            self.assertEqual(quality["final"]["actionability_score"]["items"], 4)
            self.assertEqual(quality["final"]["actionability_score"]["verbish_items"], 4)
            self.assertTrue(quality["final"]["actionability_score"]["ok"])


if __name__ == "__main__":
    unittest.main()
