import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from notes_runner_lib.header_runtime import build_deterministic_header


def _load_prepare_payload(work_dir: Path) -> dict:
    return json.loads((work_dir / "prepare_state.json").read_text(encoding="utf-8"))


def _load_json_if_exists(path: Path) -> dict | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def _write_stage_sentinel(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _update_prepare_state_fields(work_dir: Path, updates: dict) -> None:
    path = work_dir / "prepare_state.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(payload.get(key), dict):
            payload[key].update(value)
        else:
            payload[key] = value
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _read_summary_points(path: Path) -> list[str]:
    points: list[str] = []
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line[:2].isdigit() and line[2:4] == ". ":
            points.append(line[4:].strip())
    return points


class HeaderRuntimeTests(unittest.TestCase):
    def test_build_deterministic_header_creates_micro_multi_header_from_local_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            work_dir = Path(tmp_dir)
            (work_dir / "prepare_state.json").write_text(
                json.dumps(
                    {
                        "execution_mode": "micro-multi",
                        "content_mode": "conversation",
                        "total_chunks": 4,
                        "telemetry": {"duration_seconds": 7080},
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            (work_dir / "header-seed.json").write_text(
                json.dumps(
                    {
                        "topic_hint": "сырой заголовок из первой строки",
                        "duration_estimate": "01:58:00",
                        "source_files": ["transcript.md"],
                        "source_identity": {"source_kind": "audio", "duration_seconds": 7080},
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            (work_dir / "note-contract.json").write_text(
                json.dumps(
                    {
                        "content_mode": "conversation",
                        "header": {"format_label": "интервью"},
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            (work_dir / "prescan_context.txt").write_text(
                "Меня зовут Евгений.\nСегодня поговорим о деньгах и мышлении.\n",
                encoding="utf-8",
            )
            (work_dir / "tldr.md").write_text(
                "\n".join(
                    [
                        "1. Деньги растут, когда мышление сильнее страха и старых убеждений.",
                        "2. Дисциплина важнее мотивации, когда человек собирает длинную траекторию.",
                        "3. Личные решения и ежедневный язык собирают реальность быстрее внешних обстоятельств.",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            (work_dir / "summary_chunk_A.md").write_text(
                "1. Деньги, мышление и дисциплина постоянно переплетены.\n",
                encoding="utf-8",
            )
            (work_dir / "manifest_chunk_A.tsv").write_text(
                "\n".join(
                    [
                        "block_file\ttimestamp_start\ttimestamp_end\ttopic\tprimary_claim\tnames\tresources\tcase_title\thas_dialogue\tquote_text\taction_now\taction_check\taction_avoid\tquotes_count\tcases",
                        "chunk_A_block_01.md\t00:00\t10:00\tДеньги растут, когда мышление сильнее страха\tГлавная мысль\tЕвгений\t\t\t0\t\t\t\t\t0\t0",
                        "chunk_A_block_02.md\t10:00\t20:00\tДисциплина и мышление важнее случайной мотивации\tВторая мысль\tЕвгений\t\t\t0\t\t\t\t\t0\t0",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            payload = build_deterministic_header(
                work_dir,
                load_prepare_payload=_load_prepare_payload,
                load_json_if_exists=_load_json_if_exists,
                write_text=_write_text,
                write_stage_sentinel=_write_stage_sentinel,
                stage_sentinel_path=lambda work_dir, stage_name: work_dir / "stages" / f"{stage_name}.json",
                update_prepare_state_fields=_update_prepare_state_fields,
                execution_mode_for_plan=lambda total_chunks, *, content_mode, duration_seconds=0: "micro-multi",
                read_summary_points_fn=_read_summary_points,
            )

            self.assertTrue(payload["generated"])
            text = (work_dir / "header.md").read_text(encoding="utf-8")
            self.assertIn("# Евгений — Деньги, мышление и дисциплина", text)
            self.assertIn("> Большой разговор, в центре которого деньги, мышление и дисциплина.", text)
            self.assertIn("**Формат:** интервью", text)
            self.assertIn("**Тема:** Деньги, мышление и дисциплина", text)
            self.assertIn("**Длительность:** 01:58:00", text)
            self.assertIn("**Источник:** transcript.md", text)
            self.assertIn("## Главная рамка автора", text)
            self.assertTrue((work_dir / "stages" / "header.json").is_file())

    def test_build_deterministic_header_skips_multi_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            work_dir = Path(tmp_dir)
            (work_dir / "prepare_state.json").write_text(
                json.dumps(
                    {
                        "execution_mode": "multi",
                        "content_mode": "conversation",
                        "total_chunks": 6,
                        "telemetry": {"duration_seconds": 7200},
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )

            payload = build_deterministic_header(
                work_dir,
                load_prepare_payload=_load_prepare_payload,
                load_json_if_exists=_load_json_if_exists,
                write_text=_write_text,
                write_stage_sentinel=_write_stage_sentinel,
                stage_sentinel_path=lambda work_dir, stage_name: work_dir / "stages" / f"{stage_name}.json",
                update_prepare_state_fields=_update_prepare_state_fields,
                execution_mode_for_plan=lambda total_chunks, *, content_mode, duration_seconds=0: "multi",
                read_summary_points_fn=_read_summary_points,
            )

            self.assertTrue(payload["skipped"])
            self.assertEqual(payload["reason"], "deterministic header is enabled only for micro-multi")
            self.assertFalse((work_dir / "header.md").exists())


if __name__ == "__main__":
    unittest.main()
