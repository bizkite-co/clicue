import unittest
from unittest.mock import patch
import io
import sys
import os

# Adjust import path so we can import the clicue package from src/
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from clicue import main

class TestCLI(unittest.TestCase):
    def test_parse_words_from_file(self):
        fake_file = io.StringIO("This is a test script\nwith some words.")
        words = main.parse_words_from_file(fake_file)
        self.assertEqual(words, ["This", "is", "a", "test", "script", "with", "some", "words."])

    def test_main_with_file_argument(self):
        # Create a temporary file
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("one two three")
            temp_path = f.name
        
        try:
            # Capture output
            with patch('sys.stdout', new=io.StringIO()) as fake_out:
                words = main.main([temp_path])
                
            self.assertEqual(words, ["one", "two", "three"])
            self.assertIn("Parsed 3 words.", fake_out.getvalue())
        finally:
            os.remove(temp_path)

    @patch('sys.stdin', new_callable=lambda: io.StringIO("stdin input text"))
    def test_main_with_stdin(self, mock_stdin):
        with patch('sys.stdout', new=io.StringIO()) as fake_out:
            words = main.main([])
            
        self.assertEqual(words, ["stdin", "input", "text"])
        self.assertIn("Parsed 3 words.", fake_out.getvalue())

if __name__ == '__main__':
    unittest.main()
