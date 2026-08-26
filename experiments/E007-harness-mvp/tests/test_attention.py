import importlib.util
import unittest
from pathlib import Path


CLIENT = Path(__file__).parents[3] / "site" / "experiments" / "E007" / "attention-node-v0.1.py"
spec = importlib.util.spec_from_file_location("attention_node", CLIENT)
attention = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(attention)


class AttentionScoreTests(unittest.TestCase):
    def test_question_is_not_rewritten(self):
        question = "Не могу решить CV-задачу с маленькими объектами. Claude и Codex не помогли."
        self.assertEqual(attention.normalize(question), question.lower())

    def test_relevant_card_ranks_above_unrelated_card(self):
        question = "Не могу решить CV-задачу с маленькими объектами. Claude и Codex не помогли."
        relevant = "computer vision CV, small objects; компьютерное зрение, маленькие объекты"
        unrelated = "beekeeping, hive, honey; пчеловодство, улей, мед"
        self.assertGreater(
            attention.whole_text_vector_score(question, relevant),
            attention.whole_text_vector_score(question, unrelated),
        )
        self.assertGreater(
            attention.exact_term_score(question, relevant)[0],
            attention.exact_term_score(question, unrelated)[0],
        )

    def test_scores_are_bounded(self):
        for score in (
            attention.whole_text_vector_score("same text", "same text"),
            attention.exact_term_score("same text", "same text")[0],
        ):
            self.assertGreaterEqual(score, 0)
            self.assertLessEqual(score, 1)


if __name__ == "__main__":
    unittest.main()
