import queue
import sys
import json
import sounddevice as sd
from vosk import Model, KaldiRecognizer

class STTListener:
    def __init__(self, model_path="model", sample_rate=16000):
        """
        Initializes the Vosk STT listener.
        Note: You need to download a Vosk model and place it in the `model_path` directory.
        For example: https://alphacephei.com/vosk/models
        """
        self.sample_rate = sample_rate
        try:
            self.model = Model(model_path)
        except Exception as e:
            print(f"Error loading Vosk model from '{model_path}': {e}", file=sys.stderr)
            print("Please download a model from https://alphacephei.com/vosk/models and extract it to that path.", file=sys.stderr)
            sys.exit(1)
            
        self.recognizer = KaldiRecognizer(self.model, self.sample_rate)
        self.q = queue.Queue()

    def _audio_callback(self, indata, frames, time, status):
        """This is called (from a separate thread) for each audio block."""
        if status:
            print(status, file=sys.stderr)
        self.q.put(bytes(indata))

    def listen(self):
        """
        Starts listening to the microphone and yields recognized text strings continuously.
        """
        print("Starting STT Listener. Speak into your microphone...")
        with sd.RawInputStream(samplerate=self.sample_rate, blocksize=8000, device=None, dtype='int16',
                               channels=1, callback=self._audio_callback):
            while True:
                data = self.q.get()
                if self.recognizer.AcceptWaveform(data):
                    # Full utterance recognized
                    result = json.loads(self.recognizer.Result())
                    text = result.get("text", "")
                    if text:
                        yield text
                else:
                    # Partial utterance recognized
                    result = json.loads(self.recognizer.PartialResult())
                    text = result.get("partial", "")
                    if text:
                        yield text

if __name__ == "__main__":
    # Simple test program to print recognized text
    listener = STTListener()
    try:
        for text in listener.listen():
            print(f"Recognized: {text}")
    except KeyboardInterrupt:
        print("\nStopped listening.")
