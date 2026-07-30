from rich.console import Console
from rich.text import Text
from rich.console import Group
from rich.padding import Padding
from clicue.fountain import ParsedScript

class TUIScroller:
    def __init__(self, script: ParsedScript, window_size: int = 38, past_size: int = 9):
        if isinstance(script, ParsedScript):
            self.script = script
        else:
            self.script = ParsedScript(
                words=script,
                cues=[""] * len(script),
                para_starts=[i == 0 for i in range(len(script))]
            )

        self.window_size = window_size
        self.past_size = past_size
        self.console = Console()

        # Precompute paragraph start word indices
        self.para_starts_indices = [
            i for i, is_start in enumerate(self.script.para_starts) if is_start
        ]
        if not self.para_starts_indices:
            self.para_starts_indices = [0]

    def _get_current_para_index(self, current_index: int) -> int:
        """Finds the paragraph index containing current_index."""
        for p_idx in range(len(self.para_starts_indices) - 1, -1, -1):
            if self.para_starts_indices[p_idx] <= current_index:
                return p_idx
        return 0

    def render(self, current_index: int) -> Group:
        """
        Renders the TUI layout without reflow:
        - Header: Clean yellow stage cue description (no redundant CUE: [Screen Recording:)
        - Body: Anchored at paragraph boundaries to prevent word-wrapping reflow while reading.
        """
        current_index = max(0, min(current_index, len(self.script) - 1)) if len(self.script) > 0 else 0
        
        # 1. Clean Cue Status Bar (in yellow, no redundant labels or trailing brackets)
        active_cue = self.script.cues[current_index] if len(self.script.cues) > current_index else ""
        
        header_text = Text()
        if active_cue:
            header_text.append("🎬 ", style="yellow")
            header_text.append(active_cue, style="bold yellow")
        else:
            header_text.append("🎬 ", style="dim yellow")
            header_text.append("(no active cue)", style="dim yellow")

        # 2. Text Body with Paragraph-Anchored Stationary Layout
        p_idx = self._get_current_para_index(current_index)

        # Anchor start_index at the beginning of the previous paragraph (or current paragraph if at start)
        # This keeps start_index FIXED while reading through the current paragraph!
        prev_p_idx = max(0, p_idx - 1)
        start_index = self.para_starts_indices[prev_p_idx]

        # End index covers current paragraph + upcoming paragraphs (up to window_size)
        end_index = min(start_index + max(self.window_size + self.past_size, current_index - start_index + self.window_size), len(self.script.words))

        body_text = Text()

        for idx in range(start_index, end_index):
            word = self.script.words[idx]

            # Paragraph break spacing
            if idx > start_index and self.script.para_starts[idx]:
                body_text.append("\n\n")

            if idx < current_index:
                # Read past words (dimmed 50% style)
                body_text.append(word, style="dim white")
            elif idx == current_index:
                # Active current word
                body_text.append(word, style="bold bright_green")
            else:
                # Upcoming words
                body_text.append(word, style="white")

            body_text.append(" ")

        return Group(
            Padding(header_text, (0, 0, 1, 0)),
            Padding(body_text, (0, 0, 0, 0))
        )

    def render_text(self, current_index: int):
        return self.render(current_index)

    def display(self, current_index: int):
        self.console.clear()
        self.console.print(self.render(current_index))

if __name__ == "__main__":
    import time
    words = ["Hello", "world", "this", "is", "a", "test"]
    script = ParsedScript(words=words, cues=["Screen recording"]*6, para_starts=[True, False, False, True, False, False])
    scroller = TUIScroller(script)
    for i in range(len(words)):
        scroller.display(i)
        time.sleep(0.3)
