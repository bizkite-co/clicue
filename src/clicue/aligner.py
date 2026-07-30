import time
import sys
from rapidfuzz import fuzz

class Aligner:
    def __init__(
        self,
        script_words: list[str],
        max_lookahead: int = 20,
        threshold: float = 70.0,
        locality_penalty: float = 1.5,
        window_size: int = None,
        perf_log: bool = False
    ):
        self.script_words = script_words
        self.lower_words = [w.lower() for w in script_words]
        self.current_index = 0
        self.max_lookahead = window_size if window_size is not None else max_lookahead
        self.threshold = threshold
        self.locality_penalty = locality_penalty
        self.perf_log = perf_log
        self.call_count = 0
        self.total_time_ms = 0.0

    def advance(self, stt_text: str) -> int:
        if self.current_index >= len(self.script_words):
            return self.current_index

        start_time = time.perf_counter()

        stt_words = stt_text.lower().split()
        if not stt_words:
            return self.current_index

        clean_stt_text = " ".join(stt_words)
        match_len = len(stt_words)

        # Restrict lookahead based on STT utterance length
        effective_lookahead = min(self.max_lookahead, max(6, match_len * 3))
        end_index = min(self.current_index + effective_lookahead, len(self.script_words))

        best_score = -100.0
        best_next_idx = self.current_index
        best_ratio = 0.0

        for i in range(self.current_index, end_index):
            # Form phrase using pre-lowercased words to eliminate string allocation overhead
            script_phrase = " ".join(self.lower_words[i:i + match_len])
            
            ratio = fuzz.ratio(clean_stt_text, script_phrase)

            # Apply locality penalty for jumping forward
            distance = i - self.current_index
            penalized_score = ratio - (distance * self.locality_penalty)

            if penalized_score > best_score:
                best_score = penalized_score
                best_ratio = ratio
                best_next_idx = i + match_len

        # Check threshold
        if best_ratio >= self.threshold or best_score >= (self.threshold - 10.0):
            self.current_index = min(best_next_idx, len(self.script_words))

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        self.call_count += 1
        self.total_time_ms += elapsed_ms

        if self.perf_log and self.call_count % 10 == 0:
            avg_ms = self.total_time_ms / self.call_count
            print(f"[PERF] Align call #{self.call_count}: {elapsed_ms:.2f}ms (avg: {avg_ms:.2f}ms) | STT: '{clean_stt_text}' -> Index {self.current_index}", file=sys.stderr)

        return self.current_index
