import argparse
import sys
from rich.live import Live

from clicue.aligner import Aligner
from clicue.scroller import TUIScroller
from clicue.stt import get_stt_listener
from clicue.fountain import parse_fountain, ParsedScript
from clicue.config import load_config


def parse_script_from_file(file_obj, raw=False) -> ParsedScript:
    content = file_obj.read()
    if raw:
        words = content.split()
        return ParsedScript(
            words=words,
            cues=[""] * len(words),
            para_starts=[i == 0 for i in range(len(words))]
        )
    return parse_fountain(content)

def parse_words_from_file(file_obj, raw=False):
    return parse_script_from_file(file_obj, raw).words

def main(args=None):
    parser = argparse.ArgumentParser(description="clicue - teleprompter script scroller")
    parser.add_argument(
        "script",
        nargs="?",
        type=argparse.FileType("r"),
        default=sys.stdin,
        help="Path to the script file (or '-' for stdin). If omitted, reads from stdin.",
    )
    parser.add_argument(
        "--config",
        default=None,
        help="Path to a TOML configuration file."
    )
    parser.add_argument(
        "--window-size",
        type=int,
        default=None,
        help="Number of upcoming words to display in look-ahead."
    )
    parser.add_argument(
        "--past-size",
        type=int,
        default=None,
        help="Number of past words to display in look-behind."
    )
    parser.add_argument(
        "--max-lookahead",
        type=int,
        default=None,
        help="Maximum word distance to search ahead for alignment."
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=None,
        help="Fuzzy match confidence threshold (0.0 - 100.0)."
    )
    parser.add_argument(
        "--perf-log",
        action="store_true",
        help="Log performance metrics to stderr."
    )
    parser.add_argument(
        "--engine",
        default="vosk",
        help="STT engine plugin to use (default: vosk)."
    )
    parser.add_argument(
        "--model-path",
        default=None,
        help="Path to the model directory."
    )
    parser.add_argument(
        "--device",
        default=None,
        help="Audio input device ID or name."
    )
    parser.add_argument(
        "--audio-file",
        default=None,
        help="Path to a pre-recorded WAV audio file to use instead of live microphone input."
    )
    parser.add_argument(
        "--raw",
        action="store_true",
        help="Do not parse Fountain syntax; read all text literally."
    )
    parser.add_argument(
        "--list-devices",
        action="store_true",
        help="List available audio input devices and exit."
    )
    
    parsed_args = parser.parse_args(args)

    if parsed_args.list_devices:
        import sounddevice as sd
        print("Available Audio Devices:")
        print(sd.query_devices())
        return

    # Load TOML config and merge with CLI arguments
    cfg = load_config(parsed_args.config)
    
    engine_name = parsed_args.engine or cfg.get("audio", {}).get("engine", "vosk")
    window_size = parsed_args.window_size or cfg["scroller"]["window_size"]
    past_size = parsed_args.past_size or cfg["scroller"]["past_size"]
    max_lookahead = parsed_args.max_lookahead or cfg["aligner"]["max_lookahead"]
    threshold = parsed_args.threshold or cfg["aligner"]["threshold"]
    locality_penalty = cfg["aligner"].get("locality_penalty", 1.5)
    model_path = parsed_args.model_path or cfg["audio"]["model_path"]
    perf_log = parsed_args.perf_log or cfg["debug"]["perf_log"]

    script = parse_script_from_file(parsed_args.script, raw=parsed_args.raw)
    
    if not script.words:
        print("Script is empty.")
        return 0
        
    device_param = parsed_args.device
    if device_param is not None and device_param.isdigit():
        device_param = int(device_param)

    aligner = Aligner(
        script.words,
        max_lookahead=max_lookahead,
        threshold=threshold,
        locality_penalty=locality_penalty,
        perf_log=perf_log
    )
    scroller = TUIScroller(script, window_size=window_size, past_size=past_size)
    listener = get_stt_listener(engine_name=engine_name, model_path=model_path, device=device_param)

    
    audio_stream = listener.listen_file(parsed_args.audio_file) if parsed_args.audio_file else listener.listen()

    current_idx = 0
    try:
        with Live(scroller.render(0), refresh_per_second=15, auto_refresh=False, screen=True) as live:
            for text in audio_stream:
                new_idx = aligner.advance(text)
                if new_idx != current_idx:
                    current_idx = new_idx
                    live.update(scroller.render(current_idx), refresh=True)
                if current_idx >= len(script.words):
                    break
    except KeyboardInterrupt:
        pass

    return 0




if __name__ == "__main__":
    main()
