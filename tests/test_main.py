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

    @patch('clicue.main.get_stt_listener')
    def test_main_with_file_argument(self, mock_get_stt_listener):
        mock_listener = MagicMock()
        mock_listener.listen.return_value = ["mocked text"]
        mock_get_stt_listener.return_value = mock_listener
        
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

    @patch('clicue.main.get_stt_listener')
    @patch('sys.stdin', new_callable=lambda: io.StringIO("stdin input text"))
    def test_main_with_stdin(self, mock_stdin, mock_get_stt_listener):
        mock_listener = MagicMock()
        mock_listener.listen.return_value = [] # Immediately stop
        mock_get_stt_listener.return_value = mock_listener

        with patch('sys.stdout', new=io.StringIO()):
            result = main.main([])
            
        self.assertEqual(result, 0)

    @patch('clicue.main.KeyboardListener.get_key')
    @patch('clicue.main.get_stt_listener')
    def test_hotkey_quit_and_restart(self, mock_get_stt_listener, mock_get_key):
        mock_listener = MagicMock()
        mock_listener.listen.return_value = ["speech"]
        mock_get_stt_listener.return_value = mock_listener

        # Simulate pressing 'r' (restart) then 'q' (quit)
        mock_get_key.side_effect = ['r', 'q']

        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("one two three four five six")
            temp_path = f.name

        try:
            with patch('sys.stdout', new=io.StringIO()):
                res = main.main([temp_path])
            self.assertEqual(res, 0)
        finally:
            os.remove(temp_path)



if __name__ == '__main__':
    unittest.main()
