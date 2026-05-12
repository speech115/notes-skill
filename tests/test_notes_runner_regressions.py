import argparse
import contextlib
import importlib.machinery
import importlib.util
import json
import shutil
import sys
import tempfile
import types
import unittest
from io import StringIO
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = REPO_ROOT / "scripts" / "notes-runner"
FIXTURES_DIR = REPO_ROOT / "test-fixtures"


def load_runner_module() -> types.ModuleType:
    loader = importlib.machinery.SourceFileLoader("notes_runner_test", str(RUNNER_PATH))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    if spec is None:
        raise RuntimeError("Failed to build import spec for notes-runner")
    module = importlib.util.module_from_spec(spec)
    sys.modules[loader.name] = module
    loader.exec_module(module)
    return module


class NotesRunnerRegressionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runner = load_runner_module()

    def test_run_mlx_whisper_wrapper_matches_runtime_signature(self) -> None:
        captured: dict[str, object] = {}

        def fake_impl(audio_path: Path, output_dir: Path, *, model: str, language: str | None) -> Path:
            captured["audio_path"] = audio_path
            captured["output_dir"] = output_dir
            captured["model"] = model
            captured["language"] = language
            return output_dir / "sample.json"

        with tempfile.TemporaryDirectory() as tmp_dir:
            audio_path = Path(tmp_dir) / "sample.ogg"
            audio_path.write_bytes(b"audio")
            output_dir = Path(tmp_dir) / "out"
            output_dir.mkdir()
            with mock.patch.object(self.runner, "run_mlx_whisper_impl", side_effect=fake_impl):
                result = self.runner.run_mlx_whisper(
                    audio_path,
                    output_dir,
                    model="mlx-community/whisper-large-v3-turbo",
                    language="ru",
                )

        self.assertEqual(result, output_dir / "sample.json")
        self.assertEqual(captured["audio_path"], audio_path)
        self.assertEqual(captured["output_dir"], output_dir)
        self.assertEqual(captured["model"], "mlx-community/whisper-large-v3-turbo")
        self.assertEqual(captured["language"], "ru")

    def test_run_whisperx_diarize_wrapper_matches_runtime_signature(self) -> None:
        captured: dict[str, object] = {}

        def fake_impl(audio_path: Path, output_dir: Path, *, model: str, language: str | None) -> Path:
            captured["audio_path"] = audio_path
            captured["output_dir"] = output_dir
            captured["model"] = model
            captured["language"] = language
            return output_dir / "sample.json"

        with tempfile.TemporaryDirectory() as tmp_dir:
            audio_path = Path(tmp_dir) / "sample.ogg"
            audio_path.write_bytes(b"audio")
            output_dir = Path(tmp_dir) / "out"
            output_dir.mkdir()
            with mock.patch.object(self.runner, "run_whisperx_diarize_impl", side_effect=fake_impl):
                result = self.runner.run_whisperx_diarize(
                    audio_path,
                    output_dir,
                    model="large-v3",
                    language="ru",
                )

        self.assertEqual(result, output_dir / "sample.json")
        self.assertEqual(captured["audio_path"], audio_path)
        self.assertEqual(captured["output_dir"], output_dir)
        self.assertEqual(captured["model"], "large-v3")
        self.assertEqual(captured["language"], "ru")

    def test_call_parakeet_transcribe_uses_macwhisper_cli(self) -> None:
        captured: dict[str, object] = {}

        def fake_run_checked(command: list[str], *, label: str) -> object:
            captured["command"] = command
            captured["label"] = label
            md_out = Path(command[command.index("--md-out") + 1])
            json_out = Path(command[command.index("--json-out") + 1])
            md_out.write_text("*00:00* тест\n", encoding="utf-8")
            json_out.write_text("{}", encoding="utf-8")
            return types.SimpleNamespace(stdout="", stderr="")

        with tempfile.TemporaryDirectory() as tmp_dir:
            audio_path = Path(tmp_dir) / "sample.mp3"
            audio_path.write_bytes(b"audio")
            json_out = Path(tmp_dir) / "out.json"
            with mock.patch.object(self.runner.shutil, "which", return_value="/usr/local/bin/mw"):
                with mock.patch.object(self.runner, "run_checked", side_effect=fake_run_checked):
                    result = self.runner.call_parakeet_transcribe(
                        audio_path,
                        language="ru",
                        json_output_path=json_out,
                    )
            self.assertTrue(json_out.is_file())

        command = captured["command"]
        self.assertEqual(result, "*00:00* тест\n")
        self.assertEqual(captured["label"], "MacWhisper Parakeet transcription")
        self.assertIn("parakeet-pro:nvidia_parakeet-v3", command)
        self.assertIn("--quiet", command)

    def test_call_parakeet_transcribe_normalizes_ogg_before_macwhisper(self) -> None:
        captured: dict[str, object] = {}

        def fake_ffmpeg_run(command: list[str], **_: object) -> object:
            captured["ffmpeg_command"] = command
            output_path = Path(command[-1])
            output_path.write_bytes(b"m4a")
            return types.SimpleNamespace(stdout="", stderr="")

        def fake_run_checked(command: list[str], *, label: str) -> object:
            captured["mw_command"] = command
            captured["label"] = label
            transcribed_path = Path(command[2])
            captured["transcribed_suffix"] = transcribed_path.suffix
            captured["transcribed_exists"] = transcribed_path.exists()
            md_out = Path(command[command.index("--md-out") + 1])
            json_out = Path(command[command.index("--json-out") + 1])
            md_out.write_text("*00:00* тест\n", encoding="utf-8")
            json_out.write_text("{}", encoding="utf-8")
            return types.SimpleNamespace(stdout="", stderr="")

        with tempfile.TemporaryDirectory() as tmp_dir:
            audio_path = Path(tmp_dir) / "sample.ogg"
            audio_path.write_bytes(b"ogg")
            json_out = Path(tmp_dir) / "out.json"
            with mock.patch.object(self.runner.shutil, "which", return_value="/usr/local/bin/mw"):
                with mock.patch.object(self.runner.subprocess, "run", side_effect=fake_ffmpeg_run):
                    with mock.patch.object(self.runner, "run_checked", side_effect=fake_run_checked):
                        result = self.runner.call_parakeet_transcribe(
                            audio_path,
                            language="ru",
                            json_output_path=json_out,
                        )

        self.assertEqual(result, "*00:00* тест\n")
        self.assertEqual(captured["label"], "MacWhisper Parakeet transcription")
        self.assertEqual(captured["transcribed_suffix"], ".m4a")
        self.assertTrue(captured["transcribed_exists"])
        self.assertIn("-c:a", captured["ffmpeg_command"])
        self.assertIn("aac", captured["ffmpeg_command"])
        self.assertNotEqual(Path(captured["mw_command"][2]), audio_path)

    def test_groq_preflight_skips_audio_at_hourly_audio_limit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            audio_path = Path(tmp_dir) / "long.mp3"
            audio_path.write_bytes(b"audio")
            raw_output_path = Path(tmp_dir) / "groq.json"
            with mock.patch.dict(self.runner.os.environ, {"GROQ_API_KEY": "test-key"}, clear=True):
                with mock.patch.object(self.runner, "probe_media_duration_seconds", return_value=7200):
                    with mock.patch.object(self.runner, "_groq_transcribe_single") as groq_call:
                        with self.assertRaises(self.runner.RateLimitError) as exc:
                            self.runner.call_groq_transcribe(audio_path, raw_output_path, language="ru")

        groq_call.assert_not_called()
        details = exc.exception.details
        self.assertEqual(details["scope"], "hourly")
        self.assertEqual(details["daily_limit_status"], "not_checked")
        self.assertEqual(details["hourly_limit_status"], "exhausted")
        self.assertEqual(details["preflight"]["duration_seconds"], 7200)
        self.assertEqual(details["preflight"]["hourly_limit_seconds"], 7200)

    def test_groq_rate_limit_error_records_daily_headers(self) -> None:
        def fake_run(command: list[str], **_: object) -> object:
            headers_path = Path(command[command.index("-D") + 1])
            headers_path.write_text(
                "\n".join(
                    [
                        "HTTP/2 429",
                        "retry-after: 7320",
                        "x-ratelimit-limit-audio-seconds: 28800",
                        "x-ratelimit-remaining-audio-seconds: 0",
                    ]
                ),
                encoding="utf-8",
            )
            return types.SimpleNamespace(
                returncode=0,
                stdout=json.dumps(
                    {
                        "error": {
                            "code": "rate_limit_exceeded",
                            "message": "ASD limit exceeded for audio per day. Please try again later.",
                        }
                    }
                ),
                stderr="",
            )

        with tempfile.TemporaryDirectory() as tmp_dir:
            audio_path = Path(tmp_dir) / "sample.mp3"
            audio_path.write_bytes(b"audio")
            with mock.patch.object(self.runner.subprocess, "run", side_effect=fake_run):
                with self.assertRaises(self.runner.RateLimitError) as exc:
                    self.runner._groq_transcribe_single(audio_path, api_key="test-key", language="ru")

        details = exc.exception.details
        self.assertEqual(details["scope"], "daily")
        self.assertEqual(details["daily_limit_status"], "exhausted")
        self.assertEqual(details["retry_after_seconds"], 7320)
        self.assertEqual(details["headers"]["x-ratelimit-remaining-audio-seconds"], "0")

    def test_whisper_json_wrapper_matches_runtime_signature(self) -> None:
        captured: dict[str, object] = {}

        def fake_impl(whisper_json_path: Path) -> str:
            captured["whisper_json_path"] = whisper_json_path
            return "*00:00* тест\n"

        with tempfile.TemporaryDirectory() as tmp_dir:
            whisper_json_path = Path(tmp_dir) / "sample.json"
            whisper_json_path.write_text("{}", encoding="utf-8")
            with mock.patch.object(self.runner, "whisper_json_to_transcript_markdown_impl", side_effect=fake_impl):
                result = self.runner.whisper_json_to_transcript_markdown(whisper_json_path)

        self.assertEqual(result, "*00:00* тест\n")
        self.assertEqual(captured["whisper_json_path"], whisper_json_path)

    def test_whisperx_json_wrapper_matches_runtime_signature(self) -> None:
        captured: dict[str, object] = {}

        def fake_impl(whisperx_json_path: Path) -> str:
            captured["whisperx_json_path"] = whisperx_json_path
            return "**Speaker 1**: тест\n"

        with tempfile.TemporaryDirectory() as tmp_dir:
            whisperx_json_path = Path(tmp_dir) / "sample.json"
            whisperx_json_path.write_text("{}", encoding="utf-8")
            with mock.patch.object(self.runner, "whisperx_json_to_transcript_markdown_impl", side_effect=fake_impl):
                result = self.runner.whisperx_json_to_transcript_markdown(whisperx_json_path)

        self.assertEqual(result, "**Speaker 1**: тест\n")
        self.assertEqual(captured["whisperx_json_path"], whisperx_json_path)

    def test_enrich_work_dir_with_source_hints_passes_bound_prepare_prompt_helpers(self) -> None:
        captured: dict[str, object] = {}

        def fake_impl(work_dir: Path, source_hints: dict | None, **kwargs: object) -> None:
            captured["work_dir"] = work_dir
            captured["source_hints"] = source_hints
            captured.update(kwargs)

        with tempfile.TemporaryDirectory() as tmp_dir:
            work_dir = Path(tmp_dir)
            with mock.patch.object(self.runner, "enrich_work_dir_with_source_hints_impl", side_effect=fake_impl):
                self.runner.enrich_work_dir_with_source_hints(work_dir, {"kind": "youtube"})

        self.assertEqual(captured["work_dir"], work_dir)
        self.assertEqual(captured["source_hints"], {"kind": "youtube"})
        self.assertTrue(callable(captured["render_speaker_prompt"]))
        self.assertTrue(callable(captured["render_header_prompt"]))
        self.assertTrue(callable(captured["render_extraction_prompt"]))

    def test_local_bundle_records_timeline_and_snapshot_with_codex_thread(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            source_path = Path(tmp_dir) / "source.md"
            source_path.write_text("# Test note\n\nhello world\n", encoding="utf-8")

            args = argparse.Namespace(
                path=str(source_path),
                output_root=tmp_dir,
                title=None,
                prepare=False,
                refresh=False,
                json=True,
            )

            stdout = StringIO()
            with mock.patch.dict(self.runner.os.environ, {"CODEX_THREAD_ID": "019da067-e065-7890-a37d-043253389e12"}, clear=False):
                with contextlib.redirect_stdout(stdout):
                    exit_code = self.runner.cmd_local(args)

            self.assertEqual(exit_code, 0)
            payload = json.loads(stdout.getvalue())
            bundle_dir = Path(payload["bundle_dir"])

            state = json.loads((bundle_dir / "run.json").read_text(encoding="utf-8"))
            self.assertIn("note_id", state)
            self.assertIn("latest_run_id", state)
            self.assertEqual(state["latest_status"], "source-ready")
            self.assertEqual(state["timeline_path"], str(bundle_dir / "timeline.jsonl"))

            timeline_path = bundle_dir / "timeline.jsonl"
            self.assertTrue(timeline_path.is_file())
            timeline_entries = [json.loads(line) for line in timeline_path.read_text(encoding="utf-8").splitlines() if line.strip()]
            self.assertEqual(len(timeline_entries), 1)
            entry = timeline_entries[0]
            self.assertEqual(entry["note_id"], state["note_id"])
            self.assertEqual(entry["run_id"], state["latest_run_id"])
            self.assertEqual(entry["command"], "local")
            self.assertEqual(entry["status"], "source-ready")
            self.assertIn("codex:thread:019da067-e065-7890-a37d-043253389e12", entry["external_refs"])
            self.assertEqual(entry["hashes"]["transcript"], self.runner.compute_file_sha256(bundle_dir / "transcript.md"))
            self.assertIsNone(entry["hashes"]["markdown"])
            self.assertIsNone(entry["hashes"]["html"])

            snapshot_path = Path(state["latest_run_snapshot"])
            self.assertTrue(snapshot_path.is_file())
            snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
            self.assertEqual(snapshot["run_id"], state["latest_run_id"])
            self.assertEqual(snapshot["note_id"], state["note_id"])
            self.assertEqual(snapshot["status"], "source-ready")
            self.assertEqual(snapshot["hashes"]["transcript"], entry["hashes"]["transcript"])
            self.assertIn("codex:thread:019da067-e065-7890-a37d-043253389e12", snapshot["external_refs"])

            trace_entries = [
                json.loads(line)
                for line in (bundle_dir / "trace.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            run_events = [item for item in trace_entries if item["event"] in {"run.started", "run.finished"}]
            self.assertEqual([item["event"] for item in run_events], ["run.started", "run.finished"])
            self.assertTrue(all(item.get("run_id") == state["latest_run_id"] for item in run_events))

    def test_build_run_snapshot_marks_changes_against_previous_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            bundle_dir = Path(tmp_dir) / "bundle"
            bundle_dir.mkdir()

            transcript_path = bundle_dir / "transcript.md"
            transcript_path.write_text("same transcript\n", encoding="utf-8")
            output_md = bundle_dir / "конспект.md"
            output_md.write_text("# New version\n", encoding="utf-8")
            output_html = bundle_dir / "конспект.html"
            output_html.write_text("<html>new</html>\n", encoding="utf-8")

            runs_dir = bundle_dir / "runs"
            runs_dir.mkdir()
            previous_snapshot_path = runs_dir / "old-run.json"
            self.runner.write_json(
                previous_snapshot_path,
                {
                    "run_id": "old-run",
                    "note_id": "file:test",
                    "hashes": {
                        "transcript": self.runner.compute_file_sha256(transcript_path),
                        "markdown": "old-md-hash",
                        "html": "old-html-hash",
                    },
                    "quality": {
                        "contract_errors": [],
                        "summary": {"tldr_count": 2, "header_complete": True},
                    },
                    "telegram_delivery": {
                        "attempted": False,
                        "success": False,
                        "reason": "disabled",
                    },
                },
            )

            self.runner.write_json(
                bundle_dir / "run.json",
                {
                    "note_id": "file:test",
                    "title": "History test",
                    "source_kind": "local",
                    "source_path": "/tmp/source.md",
                    "transcript_path": str(transcript_path),
                    "outputs": {
                        "markdown": str(output_md),
                        "html": str(output_html),
                    },
                    "latest_run_snapshot": str(previous_snapshot_path),
                },
            )

            snapshot = self.runner.build_run_snapshot(
                bundle_dir,
                {
                    "run_id": "new-run",
                    "note_id": "file:test",
                    "command": "assemble",
                    "started_at": "2026-04-18T15:00:00+04:00",
                    "external_refs": ["codex:thread:019da067-e065-7890-a37d-043253389e12"],
                },
                status="assembled",
                contract_errors=[],
                quality_payload={
                    "final": {
                        "header_complete": True,
                        "tldr_count": 4,
                    }
                },
                telegram_delivery={
                    "enabled": True,
                    "attempted": True,
                    "success": True,
                    "reason": "sent",
                    "file_path": str(output_html),
                },
            )

            self.assertEqual(snapshot["status"], "assembled")
            self.assertFalse(snapshot["change_flags"]["input_changed"])
            self.assertTrue(snapshot["change_flags"]["output_changed"])
            self.assertTrue(snapshot["change_flags"]["quality_changed"])
            self.assertTrue(snapshot["change_flags"]["delivery_changed"])
            self.assertFalse(snapshot["change_flags"]["only_resume"])

    def test_auto_routes_video_extensions_to_audio_handler_without_overwriting_language(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            video_path = Path(tmp_dir) / "sample.mp4"
            video_path.write_bytes(b"\x00\x00\x00\x18ftypisom")

            called: list[str] = []

            def fake_audio(args: argparse.Namespace) -> int:
                called.append("audio")
                return 17

            def fake_local(args: argparse.Namespace) -> int:
                called.append("local")
                return 23

            self.runner.cmd_audio = fake_audio
            self.runner.cmd_local = fake_local

            args = argparse.Namespace(
                input=str(video_path),
                output_root=tmp_dir,
                model="mlx-community/whisper-large-v3-turbo",
                language="auto",
                transcribe_backend="auto",
                prepare=False,
                refresh=False,
                diarize=False,
                json=True,
            )

            result = self.runner.cmd_auto(args)

            self.assertEqual(result, 17)
            self.assertEqual(called, ["audio"])
            self.assertEqual(args.command, "audio")
            self.assertEqual(args.path, str(video_path.resolve()))
            self.assertEqual(args.language, "auto")

    def test_local_backend_language_omits_auto_for_local_transcribers(self) -> None:
        self.assertIsNone(self.runner.local_backend_language("auto"))
        self.assertIsNone(self.runner.local_backend_language(" AUTO "))
        self.assertEqual(self.runner.local_backend_language("ru"), "ru")

    def test_choose_transcribe_backend_ignores_elevenlabs_env(self) -> None:
        with mock.patch.dict(self.runner.os.environ, {"ELEVENLABS_API_KEY": "test-key"}, clear=True):
            with mock.patch.object(self.runner, "is_macos", return_value=False):
                with self.assertRaises(ValueError) as exc:
                    self.runner.choose_transcribe_backend("auto")

        self.assertIn("GROQ_API_KEY", str(exc.exception))
        self.assertNotIn("ELEVENLABS", str(exc.exception))

    def test_choose_transcribe_backend_uses_macwhisper_parakeet_on_macos(self) -> None:
        with mock.patch.dict(self.runner.os.environ, {}, clear=True):
            with mock.patch.object(self.runner, "is_macos", return_value=True):
                with mock.patch.object(self.runner, "parakeet_available", return_value=True):
                    self.assertEqual(self.runner.choose_transcribe_backend("auto"), "parakeet")

    def test_execution_mode_routes_five_chunk_conversation_to_micro_multi(self) -> None:
        self.assertEqual(
            self.runner.execution_mode_for_plan(5, content_mode="conversation", duration_seconds=7080),
            "micro-multi",
        )

    def test_parser_supports_build_header_command(self) -> None:
        parser = self.runner.build_parser()
        args = parser.parse_args(["build-header", "/tmp/work"])
        self.assertEqual(args.command, "build-header")
        self.assertEqual(args.work_dir, "/tmp/work")

    def test_parser_accepts_parakeet_backend(self) -> None:
        parser = self.runner.build_parser()
        args = parser.parse_args(["audio", "/tmp/a.mp3", "--transcribe-backend", "parakeet"])
        self.assertEqual(args.transcribe_backend, "parakeet")

    def test_batch_binary_markdown_writes_index_and_trace_instead_of_crashing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_dir = Path(tmp_dir) / "input"
            input_dir.mkdir()
            bad_markdown = input_dir / "broken.md"
            bad_markdown.write_bytes(b"\x00\x01\x02not-text")
            output_root = Path(tmp_dir) / "out"

            args = argparse.Namespace(
                directory=str(input_dir),
                output_root=str(output_root),
                model="mlx-community/whisper-large-v3-turbo",
                language="auto",
                transcribe_backend="auto",
                prepare=False,
                refresh=False,
                json=True,
            )

            stdout = StringIO()
            stderr = StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                exit_code = self.runner.cmd_batch(args)

            self.assertEqual(exit_code, 1)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["ok"], 0)
            self.assertEqual(payload["failed"], 1)
            self.assertTrue((output_root / "batch-index.json").is_file())
            self.assertTrue((output_root / "trace.jsonl").is_file())
            self.assertEqual(payload["results"][0]["status"], "error")
            self.assertIn("binary", payload["results"][0]["error"].lower())

            trace_lines = (output_root / "trace.jsonl").read_text(encoding="utf-8").splitlines()
            self.assertTrue(any('"event": "batch.file.failed"' in line for line in trace_lines))

    def test_assemble_shell_failure_writes_failed_sentinel_and_trace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            work_dir = Path(tmp_dir) / "work"
            shutil.copytree(FIXTURES_DIR / "single-chunk", work_dir)
            output_dir = Path(tmp_dir) / "bundle"
            output_md = output_dir / "Broken assemble.md"
            output_html = output_dir / "Broken assemble.html"

            def fake_run(*args: object, **kwargs: object) -> types.SimpleNamespace:
                return types.SimpleNamespace(returncode=9, stdout="", stderr="pandoc boom")

            args = argparse.Namespace(
                work_dir=str(work_dir),
                output_md=str(output_md),
                output_html=str(output_html),
                title="Broken assemble",
                send_to=None,
                skip_telegram=True,
                force_telegram_resend=False,
                json=True,
            )

            stdout = StringIO()
            stderr = StringIO()
            with mock.patch.object(self.runner.subprocess, "run", side_effect=fake_run):
                with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                    exit_code = self.runner.cmd_assemble(args)

            self.assertEqual(exit_code, 9)
            self.assertIn("pandoc boom", stderr.getvalue())

            sentinel = json.loads((work_dir / "stages" / "assemble.json").read_text(encoding="utf-8"))
            self.assertFalse(sentinel["completed"])
            self.assertEqual(sentinel["returncode"], 9)
            self.assertIn("pandoc boom", sentinel["error"])

            prepare_state = json.loads((work_dir / "prepare_state.json").read_text(encoding="utf-8"))
            self.assertEqual(prepare_state["stage_statuses"]["assemble"], "failed")

            trace_path = output_dir / "trace.jsonl"
            self.assertTrue(trace_path.is_file())
            trace_lines = trace_path.read_text(encoding="utf-8").splitlines()
            self.assertTrue(any('"event": "assemble.shell_failed"' in line for line in trace_lines))

    def test_missing_tldr_fails_when_contract_requires_items(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            work_dir = Path(tmp_dir) / "work"
            shutil.copytree(FIXTURES_DIR / "single-chunk", work_dir)
            (work_dir / "tldr.md").unlink(missing_ok=True)
            self.runner.write_json(
                self.runner.note_contract_path(work_dir),
                {
                    "enforce_on_assemble": True,
                    "content_mode": "monologue",
                    "header": {"required_metadata": list(self.runner.HEADER_METADATA_LABELS)},
                    "tldr": {"min_items": 3, "max_items": 6},
                    "blocks": {},
                },
            )

            output_md = Path(tmp_dir) / "note.md"
            output_md.write_text(
                "\n".join(
                    [
                        "# Тестовая заметка",
                        "> Короткий абстракт.",
                        "**Формат:** Конспект",
                        "**Источник:** Локальный файл",
                        "**Автор:** Тест",
                        "**Длительность:** 00:10:00",
                        "",
                        "## Главная рамка автора",
                        "Главная идея достаточно конкретна.",
                        "",
                        "# План действий",
                        "- [ ] Проверить TL;DR",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            quality = self.runner.compute_final_quality_checks(work_dir, output_md)
            self.assertFalse(quality["final"]["tldr_length_ok"])
            self.assertEqual(quality["final"]["tldr_count"], 0)

    def test_update_bundle_run_state_replaces_stale_telegram_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            bundle_dir = Path(tmp_dir) / "bundle"
            bundle_dir.mkdir()
            output_md = bundle_dir / "note.md"
            output_html = bundle_dir / "note.html"
            output_md.write_text("# note\n", encoding="utf-8")
            output_html.write_text("<html></html>\n", encoding="utf-8")
            self.runner.write_json(
                bundle_dir / "run.json",
                {
                    "telegram_delivery": {
                        "success": True,
                        "chat": "@old",
                        "result": {"message_id": 123},
                    }
                },
            )

            self.runner.update_bundle_run_state(
                output_md,
                output_html,
                title="Fresh state",
                telegram_delivery={
                    "enabled": False,
                    "attempted": False,
                    "success": False,
                    "reason": "skipped-by-request",
                },
            )

            payload = json.loads((bundle_dir / "run.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["telegram_delivery"]["reason"], "skipped-by-request")
            self.assertNotIn("chat", payload["telegram_delivery"])
            self.assertNotIn("result", payload["telegram_delivery"])

    def test_local_rejects_binary_input_even_if_file_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            binary_path = Path(tmp_dir) / "garbage.mp4"
            binary_path.write_bytes(b"\x00\x00\x00\x18ftypisom\x00\x00\x00\x08free\x00\x00mdat")

            args = argparse.Namespace(
                path=str(binary_path),
                output_root=tmp_dir,
                title=None,
                prepare=False,
                refresh=False,
                json=True,
            )

            with self.assertRaises(ValueError) as exc:
                self.runner.cmd_local(args)

            message = str(exc.exception).lower()
            self.assertIn("text", message)
            self.assertTrue("binary" in message or "media file" in message)


if __name__ == "__main__":
    unittest.main()
