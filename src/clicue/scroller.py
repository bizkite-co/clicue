from rich.console import Console
from rich.text import Text
from rich.panel import Panel

class TUIScroller:
    def __init__(self, script_words: list[str], window_size: int = 20):
        self.script_words = script_words
        self.window_size = window_size
        self.console = Console()

    def render_panel(self, current_index: int) -> Panel:
        """
        Renders a Panel containing exactly `window_size` words starting from `current_index`.
        The current word is highlighted.
        """
        end_index = min(current_index + self.window_size, len(self.script_words))
        words_to_display = self.script_words[current_index:end_index]

        text = Text()
        for i, word in enumerate(words_to_display):
            if i == 0:
                # Highlight the current word being spoken
                text.append(word, style="bold green")
            else:
                text.append(word, style="white")
            
            if i < len(words_to_display) - 1:
                text.append(" ")

        return Panel(text, title="clicue - Reading", expand=False)

    def display(self, current_index: int):
        """
        Clears the terminal and displays the rolling text window.
        In a real TUI loop, this would be updated continuously using rich.live.Live.
        """
        self.console.clear()
        self.console.print(self.render_panel(current_index))

if __name__ == "__main__":
    # Quick visual test
    import time
    script = "This is a quick test of the clicue TUI scroller. It should smoothly update and show only twenty words at a time while scrolling through the provided script text. Here are a few more words to ensure it scrolls properly."
    words = script.split()
    scroller = TUIScroller(words, window_size=20)
    for i in range(len(words)):
        scroller.display(i)
        time.sleep(0.5)
