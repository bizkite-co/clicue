import logging
import os
import queue
import sys
import time
import warnings

# Suppress HuggingFace Hub unauthenticated request warnings
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
logging.getLogger("huggingface_hub").setLevel(logging.ERROR)
warnings.filterwarnings("ignore", module="huggingface_hub")

import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel
from clicue.stt.base import BaseSTTListener


class WhisperSTTListener(BaseSTTListener):
    def __init__(self, model_path="base.en", sample_rate=16000, device=None, compute_type="int8"):
        self.sample_rate = sample_rate
        self.device_id = device
        self.model_name = model_path if model_path and model_path != "model" else "base.en"
        
        try:
            # Load Whisper model (int8 quantization for lightning-fast CPU inference)
            self.model = WhisperModel(self.model_name, device="cpu", compute_type=compute_type)
        except Exception as e:
            print(f"Error loading Faster-Whisper model '{self.model_name}': {e}", file=sys.stderr)
            sys.exit(1)

        self.q = queue.Queue()

    def _audio_callback(self, indata, frames, time, status):
        if status:
            print(status, file=sys.stderr)
        self.q.put(indata.copy())

    def listen_file(self, audio_file_path: str):
        """Processes a WAV audio file with Faster-Whisper."""
        segments, _ = self.model.transcribe(audio_file_path, language="en", beam_size=1)
        for segment in segments:
            text = segment.text.strip()
            if text:
                yield text

    def listen(self, device=None):
        target_device = device if device is not None else self.device_id
        
        # Audio buffer accumulator (stores float32 samples)
        buffer_samples = []
        min_samples = int(self.sample_rate * 0.8) # 800ms minimum speech buffer
        max_samples = int(self.sample_rate * 3.0) # 3.0s rolling max

        try:
            with sd.InputStream(
                samplerate=self.sample_rate,
                blocksize=4000,
                device=target_device,
                dtype='float32',
                channels=1,
                callback=self._audio_callback
            ):
                while True:
                    # Accumulate incoming audio blocks
                    while not self.q.empty():
                        block = self.q.get()
                        buffer_samples.extend(block.flatten())

                    if len(buffer_samples) >= min_samples:
                        audio_data = np.array(buffer_samples, dtype=np.float32)
                        
                        # Transcribe audio buffer
                        segments, _ = self.model.transcribe(
                            audio_data,
                            language="en",
                            beam_size=1,
                            vad_filter=True,
                            vad_parameters=dict(min_silence_duration_ms=300)
                        )
                        
                        full_text = " ".join([seg.text.strip() for seg in segments if seg.text.strip()])
                        if full_text:
                            yield full_text

                        # Maintain rolling buffer overlap
                        if len(buffer_samples) > max_samples:
                            buffer_samples = buffer_samples[-int(self.sample_rate * 0.5):]

                    time.sleep(0.15)

        except sd.PortAudioError as e:
            print(f"\n[Error] Could not open audio input device ({target_device}): {e}", file=sys.stderr)
            raise
