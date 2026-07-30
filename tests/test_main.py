import unittest
from unittest.mock import patch, MagicMock
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

    @patch('clicue.main.STTListener')
    def test_main_with_file_argument(self, mock_listener_class):
        mock_listener = MagicMock()
        mock_listener.listen.return_value = ["mocked text"]
        mock_listener_class.return_value = mock_listener
        
        # Create a temporary file
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("one two three")
            temp_path = f.name
        
        try:
            # Capture output to avoid rich clearing the screen
            with patch('sys.stdout', new=io.StringIO()):
                result = main.main([temp_path])
                
            self.assertEqual(result, 0)
        finally:
            os.remove(temp_path)

    @patch('clicue.main.STTListener')
    @patch('sys.stdin', new_callable=lambda: io.StringIO("stdin input text"))
    def test_main_with_stdin(self, mock_stdin, mock_listener_class):
        mock_listener = MagicMock()
        mock_listener.listen.return_value = [] # Immediately stop
        mock_listener_class.return_value = mock_listener

        with patch('sys.stdout', new=io.StringIO()):
            result = main.main([])
            
        self.assertEqual(result, 0)


if __name__ == '__main__':
    unittest.main()
