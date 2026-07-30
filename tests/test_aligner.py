import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from clicue.aligner import Aligner

class TestAligner(unittest.TestCase):
    def setUp(self):
        self.script_words = ["The", "quick", "brown", "fox", "jumps", "over", "the", "lazy", "dog."]
        self.aligner = Aligner(self.script_words, window_size=10, threshold=60.0)

    def test_exact_match(self):
        # Starts at 0, "The quick brown" is 3 words
        new_idx = self.aligner.advance("The quick brown")
        self.assertEqual(new_idx, 3)

    def test_fuzzy_match(self):
        self.aligner.current_index = 3
        # Should match "fox jumps" which is from index 3 to 5
        new_idx = self.aligner.advance("fux jump")
        self.assertEqual(new_idx, 5)

    def test_no_match(self):
        new_idx = self.aligner.advance("something completely different")
        # Shouldn't advance
        self.assertEqual(new_idx, 0)

    def test_advance_multiple_chunks(self):
        idx = self.aligner.advance("The qwick brown")
        self.assertEqual(idx, 3)
        idx = self.aligner.advance("fox jumps over")
        self.assertEqual(idx, 6)

if __name__ == '__main__':
    unittest.main()
