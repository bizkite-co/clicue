import queue
import sys
import json
import sounddevice as sd
from vosk import Model, KaldiRecognizer, SetLogLevel

# Suppress noisy C++ log outputs from Vosk
SetLogLevel(-1)

class STTListener:
    def __init__(self, model_path="model", sample_rate=16000, device=None):
        """
        Initializes the Vosk STT listener.
        """
        self.sample_rate = sample_rate
        self.device = device
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

    def listen_file(self, audio_file_path: str):
        """
        Reads audio chunks from a WAV file and yields recognized text strings continuously.
        """
        import wave
        import time

        try:
            wf = wave.open(audio_file_path, "rb")
        except Exception as e:
            print(f"Error opening audio file '{audio_file_path}': {e}", file=sys.stderr)
            return

        if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getcomptype() != "NONE":
            print("Audio file must be WAV format mono PCM 16-bit.", file=sys.stderr)

        rec = KaldiRecognizer(self.model, wf.getframerate())
        chunk_size = 4000
        print(f"Streaming audio file: {audio_file_path}...")

        while True:
            data = wf.readframes(chunk_size)
            if len(data) == 0:
                break
            time.sleep(0.1) # Simulate real-time audio playback speed
            if rec.AcceptWaveform(data):
                result = json.loads(rec.Result())
                text = result.get("text", "")
                if text:
                    yield text
            else:
                result = json.loads(rec.PartialResult())
                text = result.get("partial", "")
                if text:
                    yield text

        # Final result
        result = json.loads(rec.FinalResult())
        text = result.get("text", "")
        if text:
            yield text

    def listen(self, device=None):
        """
        Starts listening to the microphone and yields recognized text strings continuously.
        """
        target_device = device if device is not None else self.device
        print("Starting STT Listener. Speak into your microphone...")
        try:
            with sd.RawInputStream(
                samplerate=self.sample_rate,
                blocksize=8000,
                device=target_device,
                dtype='int16',
                channels=1,
                callback=self._audio_callback
            ):
                while True:
                    data = self.q.get()
                    if self.recognizer.AcceptWaveform(data):
                        result = json.loads(self.recognizer.Result())
                        text = result.get("text", "")
                        if text:
                            yield text
                    else:
                        result = json.loads(self.recognizer.PartialResult())
                        text = result.get("partial", "")
                        if text:
                            yield text
        except sd.PortAudioError as e:
            print(f"\n[Error] Could not open audio input device ({target_device}): {e}", file=sys.stderr)
            print("Tip: If you are running on a cloud instance / headless machine without a physical microphone,", file=sys.stderr)
            print("     you can test with a pre-recorded WAV file using: `clicue --audio-file sample.wav <script>`", file=sys.stderr)
            raise

if __name__ == "__main__":
    # Simple test program to print recognized text
    listener = STTListener()
    try:
        for text in listener.listen():
            print(f"Recognized: {text}")
    except KeyboardInterrupt:
        print("\nStopped listening.")
