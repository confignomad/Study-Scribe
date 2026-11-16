"""Unit tests for app.services.transcript_format (Phase 7). Offline."""

from __future__ import annotations

import unittest

from app.services import transcript_format as tf


class SplitSentencesTests(unittest.TestCase):
    def test_basic_split(self) -> None:
        out = tf.split_sentences("Hello there. How are you? I am fine!")
        self.assertEqual(out, ["Hello there.", "How are you?", "I am fine!"])

    def test_empty(self) -> None:
        self.assertEqual(tf.split_sentences("   "), [])


class ParagraphizeTests(unittest.TestCase):
    def test_groups_into_paragraphs(self) -> None:
        text = "One. Two. Three. Four. Five. Six."
        out = tf.paragraphize(text, sentences_per_para=3, max_chars=10_000)
        self.assertEqual(out, "One. Two. Three.\n\nFour. Five. Six.")

    def test_not_one_big_block(self) -> None:
        text = " ".join(f"Sentence number {i}." for i in range(1, 13))
        out = tf.paragraphize(text, sentences_per_para=3)
        self.assertGreater(out.count("\n\n"), 0)

    def test_preserves_code_fence(self) -> None:
        text = "Intro sentence one. Intro two.\n\n```\nrouter ospf 1\nnetwork 10.0.0.0\n```\n\nAfter one. After two."
        out = tf.paragraphize(text, sentences_per_para=1)
        # The code block must survive verbatim, untouched by reflow.
        self.assertIn("```\nrouter ospf 1\nnetwork 10.0.0.0\n```", out)


class RemoveFillersTests(unittest.TestCase):
    def test_removes_um_uh(self) -> None:
        out = tf.remove_fillers("So um this is uh the answer.")
        self.assertNotIn("um", out.split())
        self.assertNotIn("uh", out.split())
        self.assertIn("this is", out)

    def test_keeps_real_words(self) -> None:
        # 'summer' contains 'um' but must not be touched (word boundaries).
        self.assertIn("summer", tf.remove_fillers("I love summer."))


class TrimIntroOutroTests(unittest.TestCase):
    def test_drops_subscribe_and_goodbye(self) -> None:
        text = (
            "Today we cover OSPF. The RIB holds routes. "
            "If you like the video, please subscribe. Goodbye."
        )
        out = tf.trim_intro_outro(text)
        self.assertIn("The RIB holds routes.", out)
        self.assertNotIn("subscribe", out.lower())
        self.assertNotIn("goodbye", out.lower())


class SpeechifyCleanTests(unittest.TestCase):
    def test_end_to_end(self) -> None:
        text = (
            "Welcome. Um the FIB is fast. It is derived from the RIB. "
            "It is optimized. Please like and subscribe. Goodbye."
        )
        out = tf.speechify_clean(text)
        self.assertNotIn("subscribe", out.lower())
        self.assertNotIn(" um ", f" {out} ")
        self.assertIn("FIB is fast", out)
        self.assertIn("\n\n", out)  # reflowed into paragraphs


if __name__ == "__main__":
    unittest.main()
