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

    def _build_wrapped_lines(self, width: int):
        """
        Groups script word indices into terminal line rows based on column width
        and paragraph breaks.
        Returns a list of lists of word indices, e.g. [[0, 1, 2], [3, 4], ...]
        """
        lines = []
        current_line = []
        current_length = 0

        for idx, word in enumerate(self.script.words):
            is_para_start = self.script.para_starts[idx]
            word_len = len(word) + 1  # word + trailing space

            # If paragraph start (and not first word of script), start a new paragraph line
            if is_para_start and idx > 0:
                if current_line:
                    lines.append(current_line)
                    current_line = []
                    current_length = 0
                # Add empty line for paragraph spacing
                lines.append([])

            # If adding word exceeds terminal width, wrap to next line
            if current_line and (current_length + word_len > width):
                lines.append(current_line)
                current_line = [idx]
                current_length = word_len
            else:
                current_line.append(idx)
                current_length += word_len

        if current_line:
            lines.append(current_line)

        return lines

    def render(self, current_index: int, is_paused: bool = False) -> Group:
        """
        Renders the TUI layout:
        - Header: Status badge ([CLICUE TRACKING ▶] or [CLICUE PAUSED ⏸]) and active stage cue.
        - Text Body: Line-anchored to display strictly 1 previous row of text at top,
          maximizing upcoming line visibility with zero reflow.
        """
        current_index = max(0, min(current_index, len(self.script) - 1)) if len(self.script) > 0 else 0
        
        # 1. Header (Status Badge + Stage Cue)
        header_text = Text()

        if is_paused:
            header_text.append("[CLICUE PAUSED ⏸] ", style="bold black on yellow")
        else:
            header_text.append("[CLICUE TRACKING ▶] ", style="bold white on green")

        active_cue = self.script.cues[current_index] if len(self.script.cues) > current_index else ""
        if active_cue:
            header_text.append(" 🎬 ", style="yellow")
            header_text.append(active_cue, style="bold yellow")
        else:
            header_text.append(" 🎬 ", style="dim yellow")
            header_text.append("(no active cue)", style="dim yellow")

        # 2. Line-Anchored Text Body (1 previous row max context)
        width = max(40, self.console.width - 2)
        height = max(10, self.console.height - 3)

        lines = self._build_wrapped_lines(width)

        # Find line containing current_index
        active_line_idx = 0
        for l_idx, line in enumerate(lines):
            if current_index in line:
                active_line_idx = l_idx
                break

        # Show exactly 1 previous line of context above active line (if available)
        top_line_idx = max(0, active_line_idx - 1)
        visible_lines = lines[top_line_idx : top_line_idx + height]

        body_text = Text()

        for l_idx, line in enumerate(visible_lines):
            if l_idx > 0:
                body_text.append("\n")

            if not line:
                # Empty line for paragraph spacing
                continue

            for word_idx in line:
                word = self.script.words[word_idx]
                word_style = self.script.styles[word_idx] if hasattr(self.script, "styles") and len(self.script.styles) > word_idx else ""

                if word_idx < current_index:
                    style_str = f"dim white {word_style}".strip()
                elif word_idx == current_index:
                    style_str = f"bold bright_green {word_style}".strip()
                else:
                    style_str = f"white {word_style}".strip()

                body_text.append(word, style=style_str)
                body_text.append(" ")


        return Group(
            Padding(header_text, (0, 0, 1, 0)),
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
