import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from clicue.fountain import parse_fountain_words

class TestFountainParser(unittest.TestCase):
    def test_fountain_stripping(self):
        fountain_content = """Title: TASK-AGENT INTRODUCTION
Author: InTEGr8or

[Screen Recording: A clean terminal window.]

NARRATOR
Have you ever stared at a massive codebase?

NARRATOR
I wanted an easy way to look at the next step.
"""
        words = parse_fountain_words(fountain_content)
        expected = [
            "Have", "you", "ever", "stared", "at", "a", "massive", "codebase?",
            "I", "wanted", "an", "easy", "way", "to", "look", "at", "the", "next", "step."
        ]
        self.assertEqual(words, expected)

if __name__ == '__main__':
    unittest.main()
