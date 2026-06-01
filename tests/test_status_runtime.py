import tempfile
import unittest
import json
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
import sys

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from notes_runner_lib.status_runtime import build_status_payload


class StatusRuntimeTests(unittest.TestCase):
    def test_build_status_payload_prefers_observed_stage_statuses_over_stale_prepare_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            work_dir = Path(tmp_dir)
            (work_dir / "chunk_A_block_01.md").write_text("## Block\n", encoding="utf-8")
            (work_dir / "manifest_chunk_A.tsv").write_text(
                "block_file\ttimestamp_start\ttimestamp_end\ttopic\tprimary_claim\tnames\tresources\tcase_title\thas_dialogue\tquote_text\taction_now\taction_check\taction_avoid\tquotes_count\tcases\n",
                encoding="utf-8",
            )
            (work_dir / "summary_chunk_A.md").write_text("1. Test summary\n", encoding="utf-8")
            stage_dir = work_dir / "stages"
            stage_dir.mkdir()
            (stage_dir / "extraction-A.json").write_text(
                json.dumps(
                    {
                        "stage": "extraction",
                        "chunk_id": "A",
                        "completed": True,
                        "expected_outputs": [
                            "manifest_chunk_A.tsv",
                            "summary_chunk_A.md",
                            "stages/extraction-A.json",
                        ],
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            (work_dir / "tldr.md").write_text("1. Test\n", encoding="utf-8")

            prepare_payload = {
                "fingerprint": "abc123",
                "execution_mode": "single",
                "content_mode": "monologue",
                "chunk_plan": [{"id": "A"}],
                "stage_hints": {"speaker_identification": "skip"},
                "stage_statuses": {
                    "speaker_identification": "skipped",
                    "extraction": "missing",
                    "tldr": "missing",
                    "assemble": "failed",
                },
            }

            with (
                mock.patch("notes_runner_lib.status_runtime.load_prepare_payload", return_value=prepare_payload),
                mock.patch("notes_runner_lib.status_runtime.bundle_dir_from_work_dir", return_value=None),
                mock.patch("notes_runner_lib.status_runtime.load_bundle_state", return_value={}),
            ):
                payload = build_status_payload(work_dir)

            self.assertEqual(payload["stages"]["extraction"]["status"], "ready")
            self.assertEqual(payload["stages"]["tldr"]["status"], "ready")
            self.assertEqual(
                payload["stage_statuses"],
                {
                    "speaker_identification": "skipped",
                    "extraction": "ready",
                    "tldr": "ready",
                    "assemble": "failed",
                },
            )

    def test_build_status_payload_marks_chunk_partial_without_completed_sentinel(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            work_dir = Path(tmp_dir)
            (work_dir / "chunk_A_block_01.md").write_text("## Block\n", encoding="utf-8")
            (work_dir / "manifest_chunk_A.tsv").write_text(
                "block_file\ttimestamp_start\ttimestamp_end\ttopic\tprimary_claim\tnames\tresources\tcase_title\thas_dialogue\tquote_text\taction_now\taction_check\taction_avoid\tquotes_count\tcases\n",
                encoding="utf-8",
            )
            (work_dir / "summary_chunk_A.md").write_text("1. Test summary\n", encoding="utf-8")

            prepare_payload = {
                "fingerprint": "abc123",
                "execution_mode": "single",
                "content_mode": "monologue",
                "chunk_plan": [
                    {
                        "id": "A",
                        "stage_sentinel_path": str(work_dir / "stages" / "extraction-A.json"),
                        "expected_outputs": [
                            "manifest_chunk_A.tsv",
                            "summary_chunk_A.md",
                            "stages/extraction-A.json",
                        ],
                    }
                ],
                "stage_hints": {"speaker_identification": "skip"},
            }

            with (
                mock.patch("notes_runner_lib.status_runtime.load_prepare_payload", return_value=prepare_payload),
                mock.patch("notes_runner_lib.status_runtime.bundle_dir_from_work_dir", return_value=None),
                mock.patch("notes_runner_lib.status_runtime.load_bundle_state", return_value={}),
            ):
                payload = build_status_payload(work_dir)

            self.assertEqual(payload["chunk_statuses"]["A"]["status"], "partial")
            self.assertEqual(payload["stages"]["extraction"]["status"], "partial")
            self.assertTrue(payload["execution_plan"]["extraction"]["should_run"])

    def test_build_status_payload_ignores_stray_workdir_html_for_assemble_ready(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            work_dir = Path(tmp_dir) / "work"
            work_dir.mkdir()
            (work_dir / "debug.html").write_text("<html>debug</html>\n", encoding="utf-8")
            (work_dir / "chunk_A_block_01.md").write_text("## Block\n", encoding="utf-8")
            (work_dir / "manifest_chunk_A.tsv").write_text(
                "block_file\ttimestamp_start\ttimestamp_end\ttopic\tprimary_claim\tnames\tresources\tcase_title\thas_dialogue\tquote_text\taction_now\taction_check\taction_avoid\tquotes_count\tcases\n",
                encoding="utf-8",
            )
            (work_dir / "summary_chunk_A.md").write_text("1. Test summary\n", encoding="utf-8")
            (work_dir / "tldr.md").write_text("1. Test\n", encoding="utf-8")
            stage_dir = work_dir / "stages"
            stage_dir.mkdir()
            (stage_dir / "extraction-A.json").write_text(
                json.dumps(
                    {
                        "stage": "extraction",
                        "chunk_id": "A",
                        "completed": True,
                        "expected_outputs": [
                            "manifest_chunk_A.tsv",
                            "summary_chunk_A.md",
                            "stages/extraction-A.json",
                        ],
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )

            prepare_payload = {
                "fingerprint": "abc123",
                "execution_mode": "single",
                "content_mode": "monologue",
                "chunk_plan": [{"id": "A"}],
                "stage_hints": {"speaker_identification": "skip"},
            }

            with (
                mock.patch("notes_runner_lib.status_runtime.load_prepare_payload", return_value=prepare_payload),
                mock.patch("notes_runner_lib.status_runtime.bundle_dir_from_work_dir", return_value=None),
                mock.patch("notes_runner_lib.status_runtime.load_bundle_state", return_value={}),
            ):
                payload = build_status_payload(work_dir)

            self.assertEqual(payload["stages"]["assemble"]["status"], "missing")
            self.assertEqual(payload["stages"]["assemble"]["html_outputs"], [])
            self.assertTrue(payload["execution_plan"]["assemble"]["should_run"])

    def test_build_status_payload_requires_bundle_outputs_and_delivery_for_assemble_ready(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            work_dir = root / "work"
            bundle_dir = root / "bundle"
            work_dir.mkdir()
            bundle_dir.mkdir()
            output_md = bundle_dir / "note.md"
            output_html = bundle_dir / "note.html"
            output_md.write_text("# Note\n", encoding="utf-8")
            output_html.write_text("<html>note</html>\n", encoding="utf-8")
            (work_dir / "chunk_A_block_01.md").write_text("## Block\n", encoding="utf-8")
            (work_dir / "manifest_chunk_A.tsv").write_text(
                "block_file\ttimestamp_start\ttimestamp_end\ttopic\tprimary_claim\tnames\tresources\tcase_title\thas_dialogue\tquote_text\taction_now\taction_check\taction_avoid\tquotes_count\tcases\n",
                encoding="utf-8",
            )
            (work_dir / "summary_chunk_A.md").write_text("1. Test summary\n", encoding="utf-8")
            (work_dir / "tldr.md").write_text("1. Test\n", encoding="utf-8")
            stage_dir = work_dir / "stages"
            stage_dir.mkdir()
            (stage_dir / "extraction-A.json").write_text(
                json.dumps(
                    {
                        "stage": "extraction",
                        "chunk_id": "A",
                        "completed": True,
                        "expected_outputs": [
                            "manifest_chunk_A.tsv",
                            "summary_chunk_A.md",
                            "stages/extraction-A.json",
                        ],
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            (stage_dir / "assemble.json").write_text(
                json.dumps(
                    {
                        "stage": "assemble",
                        "fingerprint": "abc123",
                        "completed": True,
                        "output_md": str(output_md),
                        "output_html": str(output_html),
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            (bundle_dir / "run.json").write_text(
                json.dumps(
                    {
                        "outputs": {
                            "markdown": str(output_md),
                            "html": str(output_html),
                        },
                        "telegram_delivery": {
                            "success": True,
                            "attempted": True,
                            "file_path": str(output_html),
                        },
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )

            prepare_payload = {
                "fingerprint": "abc123",
                "execution_mode": "single",
                "content_mode": "monologue",
                "bundle_dir": str(bundle_dir),
                "chunk_plan": [{"id": "A"}],
                "stage_hints": {"speaker_identification": "skip"},
            }

            with (
                mock.patch("notes_runner_lib.status_runtime.load_prepare_payload", return_value=prepare_payload),
                mock.patch("notes_runner_lib.status_runtime.bundle_dir_from_work_dir", return_value=bundle_dir),
                mock.patch("notes_runner_lib.status_runtime.load_bundle_state", return_value={}),
            ):
                payload = build_status_payload(work_dir)

            self.assertEqual(payload["stages"]["assemble"]["status"], "ready")
            self.assertEqual(payload["stages"]["assemble"]["markdown_outputs"], [str(output_md)])
            self.assertEqual(payload["stages"]["assemble"]["html_outputs"], [str(output_html)])
            self.assertFalse(payload["execution_plan"]["assemble"]["should_run"])

    def test_build_status_payload_reports_external_extraction_timing_from_sentinels(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            work_dir = Path(tmp_dir)
            stage_dir = work_dir / "stages"
            stage_dir.mkdir()
            for chunk_id, started_at, completed_at in (
                ("A", "2026-04-25T07:35:20Z", "2026-04-25T07:36:57Z"),
                ("B", "2026-04-25T07:35:30Z", "2026-04-25T07:36:56Z"),
            ):
                (work_dir / f"chunk_{chunk_id}_block_01.md").write_text("## Block\n", encoding="utf-8")
                (work_dir / f"manifest_chunk_{chunk_id}.tsv").write_text(
                    "block_file\ttimestamp_start\ttimestamp_end\ttopic\tprimary_claim\tnames\tresources\tcase_title\thas_dialogue\tquote_text\taction_now\taction_check\taction_avoid\tquotes_count\tcases\n",
                    encoding="utf-8",
                )
                (work_dir / f"summary_chunk_{chunk_id}.md").write_text("1. Test summary\n", encoding="utf-8")
                (stage_dir / f"extraction-{chunk_id}.json").write_text(
                    json.dumps(
                        {
                            "stage": "extraction",
                            "chunk_id": chunk_id,
                            "completed": True,
                            "expected_outputs": [
                                f"manifest_chunk_{chunk_id}.tsv",
                                f"summary_chunk_{chunk_id}.md",
                                f"stages/extraction-{chunk_id}.json",
                            ],
                            "started_at": started_at,
                            "completed_at": completed_at,
                        },
                        ensure_ascii=False,
                    )
                    + "\n",
                    encoding="utf-8",
                )

            prepare_payload = {
                "fingerprint": "abc123",
                "execution_mode": "micro-multi",
                "content_mode": "monologue",
                "chunk_plan": [{"id": "A"}, {"id": "B"}],
                "stage_hints": {"speaker_identification": "skip"},
            }

            with (
                mock.patch("notes_runner_lib.status_runtime.load_prepare_payload", return_value=prepare_payload),
                mock.patch("notes_runner_lib.status_runtime.bundle_dir_from_work_dir", return_value=None),
                mock.patch("notes_runner_lib.status_runtime.load_bundle_state", return_value={}),
            ):
                payload = build_status_payload(work_dir)

            extraction_timing = payload["telemetry"]["external_stages"]["extraction"]
            self.assertEqual(extraction_timing["started_at"], "2026-04-25T07:35:20Z")
            self.assertEqual(extraction_timing["completed_at"], "2026-04-25T07:36:57Z")
            self.assertEqual(extraction_timing["duration_ms"], 97000)
            self.assertEqual(extraction_timing["chunks"]["A"]["duration_ms"], 97000)
            self.assertEqual(extraction_timing["chunks"]["B"]["duration_ms"], 86000)


if __name__ == "__main__":
    unittest.main()
