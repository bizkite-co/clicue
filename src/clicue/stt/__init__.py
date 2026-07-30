from clicue.stt.base import BaseSTTListener
from clicue.stt.vosk_engine import VoskSTTListener
from clicue.stt.whisper_engine import WhisperSTTListener

STT_ENGINES = {
    "vosk": VoskSTTListener,
    "whisper": WhisperSTTListener,
    "faster-whisper": WhisperSTTListener,
}

def get_stt_listener(engine_name: str = "vosk", **kwargs) -> BaseSTTListener:
    """
    Factory function to instantiate STT listener plugins by engine name.
    """
    engine_name = engine_name.lower().strip()
    if engine_name not in STT_ENGINES:
        raise ValueError(f"Unknown STT engine '{engine_name}'. Available engines: {list(STT_ENGINES.keys())}")
    return STT_ENGINES[engine_name](**kwargs)

