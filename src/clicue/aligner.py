from rapidfuzz import fuzz

class Aligner:
    def __init__(self, script_words, window_size=20, threshold=70.0):
        self.script_words = script_words
        self.current_index = 0
        self.window_size = window_size
        self.threshold = threshold

    def advance(self, stt_text: str) -> int:
        if self.current_index >= len(self.script_words):
            return self.current_index

        # We look ahead in the script within a certain window
        end_index = min(self.current_index + self.window_size, len(self.script_words))
        
        best_ratio = 0
        best_idx = self.current_index

        # We try matching the stt_text against sequences of words in our window
        # To make it robust, we can compare stt_text against a sliding sub-window of script words
        
        stt_words = stt_text.split()
        if not stt_words:
            return self.current_index

        # We slide a window of size roughly equal to the number of words in stt_text
        match_len = len(stt_words)
        
        for i in range(self.current_index, end_index):
            # Form a phrase from the script of similar length
            script_phrase = " ".join(self.script_words[i:i + match_len])
            
            # Compare using rapidfuzz
            ratio = fuzz.ratio(stt_text.lower(), script_phrase.lower())
            
            if ratio > best_ratio:
                best_ratio = ratio
                # The index to advance to would be the end of the matched phrase
                best_idx = i + match_len

        # If the best match is above our confidence threshold, we advance
        if best_ratio >= self.threshold:
            # We don't want to advance past the end of the script
            self.current_index = min(best_idx, len(self.script_words))

        return self.current_index
