from rich.console import Console, Group
from rich.text import Text

from clicue.fountain import ParsedScript, process_word_emphasis


def append_styled_cue(header_text: Text, cue: str, is_new_cue: bool = False):
    """
    Parses inline markdown syntax (`code`, *italic*, **bold**) in cue strings
    and appends them to header_text with dark grey background (#262626).
    If is_new_cue is True (within 1.0s of cue change), text renders in bright white.
    """
    header_text.append(" 🎬 ", style="bold bright_white on #262626" if is_new_cue else "yellow on #262626")
    cue_words = cue.split()
    in_italic = False
    in_bold = False
    in_code = False

    for i, raw_w in enumerate(cue_words):
        clean_w, style_str, in_italic, in_bold, in_code = process_word_emphasis(raw_w, in_italic, in_bold, in_code)
        
        styles = ["on #262626"]
        if "cyan" in style_str:
            styles.append("bold cyan")
        elif "bold" in style_str:
            styles.append("bold bright_white")
        else:
            styles.append("bold bright_white" if is_new_cue else "bold bright_yellow")

        if "italic" in style_str:
            styles.append("italic")

        header_text.append(clean_w, style=" ".join(styles))
        if i < len(cue_words) - 1:
            header_text.append(" ", style="on #262626")

    header_text.append(" ", style="on #262626")


class TUIScroller:
    def __init__(self, script: ParsedScript, window_size: int = 38, past_size: int = 9, debug: bool = False, perf_logger = None):
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
        self.debug = debug
        self.perf_logger = perf_logger
        self.console = Console()
        self._cached_width = None
        self._cached_lines = None
        self._last_cue = None
        self._cue_change_time = 0.0

    def _build_wrapped_lines(self, width: int):
        """
        Groups script word indices into terminal line rows based on column width
        and paragraph breaks. Memoizes results to eliminate per-frame allocations.
        """
        if self._cached_width == width and self._cached_lines is not None:
            return self._cached_lines

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

        self._cached_width = width
        self._cached_lines = lines
        return lines

    def render(self, current_index: int, is_paused: bool = False) -> Group:
        """
        Renders the TUI layout:
        - Header: Status badge ([CLICUE TRACKING ▶] or [CLICUE PAUSED ⏸]) and active stage cue.
        - Text Body: Line-anchored to display strictly 1 previous row of text at top,
          maximizing upcoming line visibility with zero reflow.
        """
        import time
        current_index = max(0, min(current_index, len(self.script) - 1)) if len(self.script) > 0 else 0
        
        # 1. Header (Status Badge + Stage Cue + Optional Latency Stats)
        header_text = Text()

        if is_paused:
            header_text.append("[CLICUE PAUSED ⏸] ", style="bold black on yellow")
        else:
            header_text.append("[CLICUE TRACKING ▶] ", style="bold white on green")

        if self.debug and self.perf_logger:
            stt_m = f"{self.perf_logger.latest_stt_ms:.0f}ms"
            align_m = f"{self.perf_logger.latest_align_ms:.1f}ms"
            render_m = f"{self.perf_logger.latest_render_ms:.1f}ms"
            header_text.append(f"⚡ STT:{stt_m} Align:{align_m} Render:{render_m} ", style="bold cyan")

        active_cue = self.script.cues[current_index] if len(self.script.cues) > current_index else ""
        if active_cue:
            now = time.perf_counter()
            if active_cue != self._last_cue:
                self._last_cue = active_cue
                self._cue_change_time = now

            is_new_cue = (now - self._cue_change_time) < 1.0
            append_styled_cue(header_text, active_cue, is_new_cue=is_new_cue)
        else:
            header_text.append(" 🎬 ", style="dim yellow on #1c1c1c")
            header_text.append("(no active cue) ", style="dim yellow on #1c1c1c")


        # 2. Line-Anchored Text Body (1 previous row max context)
        width = max(40, self.console.width - 2)
        height = max(10, self.console.height - 2)

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

                # Check if word_idx is the last word of a paragraph
                is_last_word = (
                    word_idx + 1 < len(self.script.words) and
                    self.script.para_starts[word_idx + 1]
                )

                if is_last_word:
                    para_style = "dim cyan" if word_idx < current_index else "cyan"
                    body_text.append(" ¶ ", style=para_style)
                else:
                    body_text.append(" ")


        return Group(
            header_text,
            body_text
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
