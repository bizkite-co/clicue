from abc import ABC, abstractmethod
from collections.abc import Iterator


class BaseSTTListener(ABC):
    """
    Abstract base class for all STT listener plugins in clicue.
    """

    @abstractmethod
    def listen(self, device=None) -> Iterator[str]:
        """
        Listens to continuous live audio input and yields recognized text strings.
        """

    def listen_file(self, audio_file_path: str) -> Iterator[str]:
        """
        Optional: Processes a WAV audio file and yields recognized text strings.
        """
        raise NotImplementedError("File streaming is not implemented for this STT engine.")
