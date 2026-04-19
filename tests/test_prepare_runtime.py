import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from notes_runner_lib.prepare_runtime import build_execution_plan, execution_mode_for_plan


class PrepareRuntimeTests(unittest.TestCase):
    def test_execution_mode_routes_five_chunk_conversation_to_micro_multi(self) -> None:
        self.assertEqual(
            execution_mode_for_plan(5, content_mode="conversation", duration_seconds=7080),
            "micro-multi",
        )

    def test_build_execution_plan_skips_optional_speaker_when_no_placeholders_exist(self) -> None:
        chunk_ids = ["A", "B", "C", "D", "E"]
        payload = {
            "execution_mode": "multi",
            "content_mode": "conversation",
            "total_chunks": len(chunk_ids),
            "chunk_plan": [{"id": chunk_id} for chunk_id in chunk_ids],
            "files": [{"markers": 0, "dialogue_cues": 0, "dialogue_speakers": 0, "intro_cues": 0}],
            "totals": {"speaker_markers": 0},
            "prompt_packs": {"tldr_strategy": "agent", "tldr_agent": "/tmp/tldr-agent.md"},
            "header_seed": {},
            "note_contract": {"tldr": {"strategy": "agent", "min_items": 10, "max_items": 14}},
            "quality_checks": {},
        }
        chunk_statuses = {chunk_id: {"status": "ready"} for chunk_id in chunk_ids}
        stages = {
            "speaker_identification": {"hint": "optional", "status": "missing"},
            "extraction": {"status": "ready"},
            "tldr": {"status": "missing"},
            "assemble": {"status": "missing"},
        }

        plan = build_execution_plan(payload, chunk_statuses, stages)

        self.assertEqual(plan["mode"], "micro-multi")
        self.assertFalse(plan["speaker_identification"]["should_run"])
        self.assertFalse(plan["replace_speakers"]["before_tldr"])
        self.assertFalse(plan["replace_speakers"]["after_tldr"])
        self.assertEqual(plan["tldr"]["strategy"], "deterministic-merge")
        self.assertEqual(plan["prompt_packs"]["tldr_strategy"], "deterministic-merge")
        self.assertIsNone(plan["prompt_packs"]["tldr_agent"])
        self.assertEqual(plan["contract"]["tldr_bounds"]["strategy"], "deterministic-merge")
        self.assertEqual(plan["assemble"]["blocked_by"], ["tldr"])

    def test_build_execution_plan_keeps_required_speaker_stage_even_without_placeholders(self) -> None:
        payload = {
            "execution_mode": "micro-multi",
            "content_mode": "conversation",
            "total_chunks": 4,
            "chunk_plan": [{"id": "A"}],
            "files": [{"markers": 0}],
            "totals": {"speaker_markers": 0},
            "prompt_packs": {},
            "header_seed": {},
            "note_contract": {},
            "quality_checks": {},
        }
        chunk_statuses = {"A": {"status": "ready"}}
        stages = {
            "speaker_identification": {"hint": "required", "status": "missing"},
            "extraction": {"status": "ready"},
            "tldr": {"status": "missing"},
            "assemble": {"status": "missing"},
        }

        plan = build_execution_plan(payload, chunk_statuses, stages)

        self.assertTrue(plan["speaker_identification"]["should_run"])
        self.assertIn("speaker_identification", plan["assemble"]["blocked_by"])


if __name__ == "__main__":
    unittest.main()
