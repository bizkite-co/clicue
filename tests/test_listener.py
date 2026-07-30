import unittest
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

# Mock sounddevice and vosk before importing listener
sys.modules['sounddevice'] = MagicMock()
sys.modules['vosk'] = MagicMock()

from clicue.listener import STTListener

class TestSTTListener(unittest.TestCase):
    @patch('clicue.listener.Model')
    @patch('clicue.listener.KaldiRecognizer')
    def test_listener_init(self, mock_recognizer, mock_model):
        listener = STTListener(model_path="dummy_model_path")
        mock_model.assert_called_once_with("dummy_model_path")
        mock_recognizer.assert_called_once_with(listener.model, 16000)

if __name__ == '__main__':
    unittest.main()
