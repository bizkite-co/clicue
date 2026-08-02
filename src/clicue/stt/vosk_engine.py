import queue
import sys
import json
import sounddevice as sd
from vosk import Model, KaldiRecognizer, SetLogLevel

from clicue.stt.base import BaseSTTListener

# Suppress Vosk C++ logs
SetLogLevel(-1)

class VoskSTTListener(BaseSTTListener):
    def __init__(self, model_path="model", sample_rate=16000, device=None, perf_logger=None):
        self.sample_rate = sample_rate
        self.device = device
        self.model_path = model_path
        self.perf_logger = perf_logger
        try:
            self.model = Model(model_path)
        except Exception as e:
            print(f"Error loading Vosk model from '{model_path}': {e}", file=sys.stderr)
            print("Please download a model from https://alphacephei.com/vosk/models and extract it to that path.", file=sys.stderr)
            sys.exit(1)
            
        self.recognizer = KaldiRecognizer(self.model, self.sample_rate)
        self.q = queue.Queue()

    def _audio_callback(self, indata, frames, time, status):
        if status:
            print(status, file=sys.stderr)
        self.q.put(bytes(indata))

    def listen_file(self, audio_file_path: str):
        import wave
        import time

        try:
            wf = wave.open(audio_file_path, "rb")
        except Exception as e:
            print(f"Error opening audio file '{audio_file_path}': {e}", file=sys.stderr)
            return

        rec = KaldiRecognizer(self.model, wf.getframerate())
        chunk_size = 4000

        while True:
            data = wf.readframes(chunk_size)
            if len(data) == 0:
                break
            time.sleep(0.1)
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

        result = json.loads(rec.FinalResult())
        text = result.get("text", "")
        if text:
            yield text

    def listen(self, device=None):
        target_device = device if device is not None else self.device
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
            raise
