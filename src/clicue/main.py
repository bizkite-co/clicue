import argparse
import sys
from rich.live import Live

from clicue.aligner import Aligner
from clicue.scroller import TUIScroller
from clicue.listener import STTListener

def parse_words_from_file(file_obj):
    content = file_obj.read()
    return content.split()

def main(args=None):
    parser = argparse.ArgumentParser(description="clicue - read a script and scroll along with your voice")
    parser.add_argument(
        "script",
        nargs="?",
        type=argparse.FileType("r"),
        default=sys.stdin,
        help="Path to the script file (or '-' for stdin). If omitted, reads from stdin.",
    )
    parser.add_argument(
        "--model-path",
        default="model",
        help="Path to the Vosk model directory."
    )
    
    parsed_args = parser.parse_args(args)
    words = parse_words_from_file(parsed_args.script)
    
    if not words:
        print("Script is empty.")
        return []
        
    aligner = Aligner(words)
    scroller = TUIScroller(words, window_size=20)
    listener = STTListener(model_path=parsed_args.model_path)
    
    try:
        with Live(scroller.render_panel(0), refresh_per_second=10) as live:
            for text in listener.listen():
                new_index = aligner.advance(text)
                live.update(scroller.render_panel(new_index))
                if new_index >= len(words):
                    break
    except KeyboardInterrupt:
        pass
            
    print("Done reading.")
    return words

if __name__ == "__main__":
    main()
