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
        for p_idx in range(len(self.para_starts_indices) - 1, -1, -1):
            if self.para_starts_indices[p_idx] <= current_index:
                return p_idx
        return 0

    def render(self, current_index: int, is_paused: bool = False) -> Group:
        """
        Renders the TUI layout with player controls status bar:
        - Top Header: Player state ([TRACKING ▶] or [PAUSED ⏸]), stage cue, and hotkey guide.
        - Text Body: Anchored at paragraph boundaries for zero-reflow teleprompter viewing.
        """
        current_index = max(0, min(current_index, len(self.script) - 1)) if len(self.script) > 0 else 0
        
        # 1. Player Controls & Stage Cue Header
        header_text = Text()

        if is_paused:
            header_text.append("[PAUSED ⏸] ", style="bold black on yellow")
        else:
            header_text.append("[TRACKING ▶] ", style="bold white on green")

        active_cue = self.script.cues[current_index] if len(self.script.cues) > current_index else ""
        if active_cue:
            header_text.append(" 🎬 ", style="yellow")
            header_text.append(active_cue, style="bold yellow")
        else:
            header_text.append(" 🎬 ", style="dim yellow")
            header_text.append("(no active cue)", style="dim yellow")

        # Hotkey Help Bar
        footer_help = Text()
        footer_help.append("[Space]: Pause/Resume  |  [← / b]: Rewind 5w  |  [→ / f]: Skip 5w  |  [q]: Quit", style="dim cyan")

        # 2. Text Body with Paragraph-Anchored Stationary Layout
        p_idx = self._get_current_para_index(current_index)
        prev_p_idx = max(0, p_idx - 1)
        start_index = self.para_starts_indices[prev_p_idx]

        end_index = min(
            start_index + max(self.window_size + self.past_size, current_index - start_index + self.window_size),
            len(self.script.words)
        )

        body_text = Text()

        for idx in range(start_index, end_index):
            word = self.script.words[idx]

            if idx > start_index and self.script.para_starts[idx]:
                body_text.append("\n\n")

            if idx < current_index:
                body_text.append(word, style="dim white")
            elif idx == current_index:
                body_text.append(word, style="bold bright_green")
            else:
                body_text.append(word, style="white")

            body_text.append(" ")

        return Group(
            Padding(header_text, (0, 0, 0, 0)),
            Padding(footer_help, (0, 0, 1, 0)),
            Padding(body_text, (0, 0, 0, 0))
        )

    def render_text(self, current_index: int, is_paused: bool = False):
        return self.render(current_index, is_paused=is_paused)

    def display(self, current_index: int, is_paused: bool = False):
        self.console.clear()
        self.console.print(self.render(current_index, is_paused=is_paused))

if __name__ == "__main__":
    import time
    words = ["Hello", "world", "this", "is", "a", "test"]
    script = ParsedScript(words=words, cues=["Screen recording"]*6, para_starts=[True, False, False, True, False, False])
    scroller = TUIScroller(script)
    for i in range(len(words)):
        scroller.display(i)
        time.sleep(0.3)
