import unittest

from scripts.notes_runner_lib.media_transcribe_runtime import normalize_transcript_text


class MediaTranscribeRuntimeTests(unittest.TestCase):
    def test_normalize_transcript_text_merges_fragmented_timestamp_lines(self) -> None:
        raw = (
            "*00:00* Я немножко не успел до дома дойти, потому что у меня самокат вырубился на полдороги, и мне пришлось...\n"
            "*00:05* Бывает.\n"
            "*00:06* Бежать, так сказать, все равно я чуть не успел.\n"
            "*00:09* Ну, в общем, да.\n"
        )

        normalized = normalize_transcript_text(raw)

        self.assertEqual(
            normalized,
            "*00:00* Я немножко не успел до дома дойти, потому что у меня самокат вырубился на полдороги, и мне пришлось... Бывает.\n"
            "*00:06* Бежать, так сказать, все равно я чуть не успел. Ну, в общем, да.\n",
        )

    def test_normalize_transcript_text_keeps_question_and_answer_separate(self) -> None:
        raw = (
            "*01:20* Можете пока представиться, может быть, для участников, если считаете это нужным?\n"
            "*01:28* Да, слушайте, меня зовут Евгений.\n"
        )

        normalized = normalize_transcript_text(raw)

        self.assertEqual(
            normalized,
            "*01:20* Можете пока представиться, может быть, для участников, если считаете это нужным?\n"
            "*01:28* Да, слушайте, меня зовут Евгений.\n",
        )


if __name__ == "__main__":
    unittest.main()
