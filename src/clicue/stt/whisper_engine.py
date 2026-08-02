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
    def __init__(self, model_path="base.en", sample_rate=16000, device=None, compute_type="int8", hf_token=None, perf_logger=None):
        self.sample_rate = sample_rate
        self.device_id = device
        self.model_name = model_path if model_path and model_path != "model" else "base.en"
        self.perf_logger = perf_logger
        token = hf_token or os.environ.get("HF_TOKEN")
        
        try:
            # Load Whisper model (int8 quantization for lightning-fast CPU inference)
            kwargs = {}
            if token:
                kwargs["auth_token"] = token
            self.model = WhisperModel(self.model_name, device="cpu", compute_type=compute_type, **kwargs)
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
        t0 = time.perf_counter()
        segments, _ = self.model.transcribe(audio_file_path, language="en", beam_size=1)
        for segment in segments:
            text = segment.text.strip()
            if text:
                lat_ms = (time.perf_counter() - t0) * 1000.0
                if self.perf_logger:
                    self.perf_logger.record_stt(text, lat_ms)
                yield text
                t0 = time.perf_counter()

    def reset(self):
        """Flushes incoming audio queue and clears accumulated speech buffers."""
        with self.q.mutex:
            self.q.queue.clear()
        self.reset_requested = True

    def listen(self, device=None):
        target_device = device if device is not None else self.device_id
        
        self.buffer_samples = []
        self.reset_requested = False
        min_samples = int(self.sample_rate * 0.5) # 500ms minimum speech buffer for rapid 50ms latency

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
                    if self.reset_requested:
                        self.buffer_samples.clear()
                        with self.q.mutex:
                            self.q.queue.clear()
                        self.reset_requested = False

                    # Accumulate incoming audio blocks
                    while not self.q.empty():
                        block = self.q.get()
                        self.buffer_samples.extend(block.flatten())

                    if len(self.buffer_samples) >= min_samples:
                        audio_data = np.array(self.buffer_samples, dtype=np.float32)
                        
                        # 1. Local RMS Energy Silence Gate (0.001ms check; 0.0005 for quiet/soft voices)
                        rms = np.sqrt(np.mean(audio_data**2))
                        if rms < 0.0005:
                            self.buffer_samples = self.buffer_samples[-int(self.sample_rate * 0.2):]
                            time.sleep(0.05)
                            continue

                        # 2. Peak Audio Normalization for quiet mic inputs
                        max_val = np.max(np.abs(audio_data))
                        if 0.005 < max_val < 0.8:
                            audio_data = (audio_data / max_val) * 0.8

                        t0 = time.perf_counter()
                        # Transcribe audio buffer
                        segments, _ = self.model.transcribe(
                            audio_data,
                            language="en",
                            beam_size=1,
                            vad_filter=True,
                            vad_parameters={"min_silence_duration_ms": 200}
                        )
                        lat_ms = (time.perf_counter() - t0) * 1000.0
                        
                        full_text = " ".join([seg.text.strip() for seg in segments if seg.text.strip()])
                        if full_text and not self.reset_requested:
                            if self.perf_logger:
                                self.perf_logger.record_stt(full_text, lat_ms)
                            # Recognized speech! Trim buffer to 0.2s trailing overlap for next utterance
                            self.buffer_samples = self.buffer_samples[-int(self.sample_rate * 0.2):]
                            yield full_text
                        else:
                            # Mid-phrase or VAD waiting: preserve buffer so complete phrases build naturally.
                            # Only trim if buffer exceeds 3.0s max during long pauses/noise.
                            max_buffer_len = int(self.sample_rate * 3.0)
                            if len(self.buffer_samples) > max_buffer_len:
                                self.buffer_samples = self.buffer_samples[-int(self.sample_rate * 0.5):]

                    time.sleep(0.05)

        except sd.PortAudioError as e:
            print(f"\n[Error] Could not open audio input device ({target_device}): {e}", file=sys.stderr)
            raise
