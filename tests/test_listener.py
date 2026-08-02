import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

# Mock sounddevice and vosk before importing listener
sys.modules['sounddevice'] = MagicMock()
sys.modules['vosk'] = MagicMock()

from clicue.stt.vosk_engine import VoskSTTListener


class TestSTTListener(unittest.TestCase):
    @patch('clicue.stt.vosk_engine.Model')
    @patch('clicue.stt.vosk_engine.KaldiRecognizer')
    def test_listener_init(self, mock_recognizer, mock_model):
        listener = VoskSTTListener(model_path="dummy_model_path")
        mock_model.assert_called_once_with("dummy_model_path")
        mock_recognizer.assert_called_once_with(listener.model, 16000)


if __name__ == '__main__':
    unittest.main()
