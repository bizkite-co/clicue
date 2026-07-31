import argparse
import sys
from rich.live import Live

from clicue.aligner import Aligner
from clicue.scroller import TUIScroller
from clicue.stt import get_stt_listener
from clicue.fountain import parse_fountain, ParsedScript
from clicue.config import load_config
from clicue.models import resolve_model_path

import urllib.request
import json
import pathlib
import re
from importlib.metadata import version as get_meta_version, PackageNotFoundError

def get_running_version() -> str:
    try:
        return get_meta_version("clicue")
    except PackageNotFoundError:
        return get_local_project_version() or "0.1.14"

def get_pypi_version(running_ver: str) -> tuple[str | None, str]:
    try:
        req = urllib.request.Request(
            "https://pypi.org/pypi/clicue/json",
            headers={"User-Agent": "clicue-cli"}
        )
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            data = json.loads(resp.read().decode())
            latest = data.get("info", {}).get("version", "")
            if latest:
                if latest == running_ver:
                    return latest, "up to date"
                else:
                    return latest, f"upgrade available: v{latest}"
    except Exception:
        pass
    return None, "offline"

def get_local_project_version() -> str | None:
    try:
        pyproject_path = pathlib.Path("pyproject.toml")
        if pyproject_path.exists():
            content = pyproject_path.read_text(encoding="utf-8")
            match = re.search(r'^version\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE)
            if match:
                return match.group(1)
    except Exception:
        pass
    return None

get_version = get_running_version

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

from rich.console import Console

def print_version_details():
    console = Console()
    running_ver = get_running_version()
    
    # 1. Running version
    console.print(f"[bold blue]Running version:[/bold blue] {running_ver}")
    
    # 2. PyPI version
    pypi_ver, status = get_pypi_version(running_ver)
    if pypi_ver:
        if status == "up to date":
            status_markup = "[green](up to date)[/green]"
        else:
            status_markup = f"[yellow]({status})[/yellow]"
        console.print(f"[dim]Latest PyPI version:[/dim] {pypi_ver} {status_markup}")
    else:
        console.print("[dim]Latest PyPI version:[/dim] [dim red]unknown (offline)[/dim red]")

    # 3. Local project version
    local_ver = get_local_project_version()
    if local_ver:
        console.print(f"[dim]Local project version:[/dim] {local_ver} (from pyproject.toml)")
import select
import termios
import tty

class KeyboardListener:
    def __enter__(self):
        self.old_settings = None
        if sys.stdin.isatty():
            try:
                self.old_settings = termios.tcgetattr(sys.stdin)
                tty.setcbreak(sys.stdin.fileno())
            except Exception:
                pass
        return self

    def __exit__(self, type, value, traceback):
        if self.old_settings and sys.stdin.isatty():
            try:
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.old_settings)
            except Exception:
                pass

    def get_key(self) -> str | None:
        if not sys.stdin.isatty():
            return None
        dr, _, _ = select.select([sys.stdin], [], [], 0)
        if dr:
            ch = sys.stdin.read(1)
            if ch == '\x1b':
                dr2, _, _ = select.select([sys.stdin], [], [], 0.01)
                if dr2:
                    ch2 = sys.stdin.read(1)
                    if ch2 == '[':
                        dr3, _, _ = select.select([sys.stdin], [], [], 0.01)
                        if dr3:
                            ch3 = sys.stdin.read(1)
                            if ch3 == 'D':
                                return 'LEFT'
                            elif ch3 == 'C':
                                return 'RIGHT'
            return ch
        return None

def main(args=None):

    if args is None:
        args = sys.argv[1:]

    # Support positional 'version' or 'v' subcommand
    if args and args[0].lower() in ("version", "v"):
        sub_args = args[1:]
        if not sub_args:
            print_version_details()
            return 0
        else:
            import subprocess
            import shutil
            if shutil.which("uvx"):
                res = subprocess.run(["uvx", "verkit@latest"] + sub_args)
                return res.returncode
            else:
                try:
                    res = subprocess.run(["verkit"] + sub_args)
                    return res.returncode
                except FileNotFoundError:
                    print("Error: 'verkit' command not found. Install it with 'uv tool install verkit'.", file=sys.stderr)
                    return 1




    parser = argparse.ArgumentParser(description="clicue - teleprompter script scroller")
    parser.add_argument(
        "--version",
        "-V",
        action="version",
        version=f"clicue v{get_version()}",
        help="Show clicue version and exit."
    )
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
        help="STT engine plugin to use (e.g. 'vosk', 'whisper'). Default: vosk."
    )
    parser.add_argument(
        "--whisper",
        action="store_true",
        help="Shortcut to use the Faster-Whisper neural STT engine."
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Model name shortcut (e.g. 'vosk-full', 'vosk-small', 'base.en', 'tiny.en') or folder path."
    )
    parser.add_argument(
        "--vosk-full",
        action="store_true",
        help="Shortcut to use the full 1.8GB Vosk model (vosk-full)."
    )
    parser.add_argument(
        "--vosk-small",
        action="store_true",
        help="Shortcut to use the compact Vosk model (vosk-small)."
    )
    parser.add_argument(
        "--model-path",
        default=None,
        help="Legacy option: Path to the model directory."
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
    
    engine_name = "whisper" if parsed_args.whisper else (parsed_args.engine or cfg.get("audio", {}).get("engine", "vosk"))
    window_size = parsed_args.window_size or cfg["scroller"]["window_size"]
    past_size = parsed_args.past_size or cfg["scroller"]["past_size"]
    max_lookahead = parsed_args.max_lookahead or cfg["aligner"]["max_lookahead"]
    threshold = parsed_args.threshold or cfg["aligner"]["threshold"]
    locality_penalty = cfg["aligner"].get("locality_penalty", 1.5)
    perf_log = parsed_args.perf_log or cfg["debug"]["perf_log"]

    # Determine model shortcut / path
    model_input = None
    if parsed_args.whisper:
        model_input = parsed_args.model or "base.en"
    elif parsed_args.vosk_full:
        model_input = "vosk-full"
    elif parsed_args.vosk_small:
        model_input = "vosk-small"
    elif parsed_args.model:
        model_input = parsed_args.model
    elif parsed_args.model_path:
        model_input = parsed_args.model_path
    else:
        model_input = cfg.get("audio", {}).get("model", cfg.get("audio", {}).get("model_path", "vosk-small"))

    if engine_name.lower() in ("whisper", "faster-whisper"):
        model_path = model_input
    else:
        model_path = resolve_model_path(model_input)


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
    is_paused = False

    try:
        with KeyboardListener() as kbd:
            with Live(scroller.render(0, is_paused=False), refresh_per_second=15, auto_refresh=False, screen=True) as live:
                for text in audio_stream:
                    # Check non-blocking hotkey input
                    key = kbd.get_key()
                    if key in (' ', 'p'):
                        is_paused = not is_paused
                        live.update(scroller.render(current_idx, is_paused=is_paused), refresh=True)
                    elif key in ('LEFT', 'b'):
                        current_idx = max(0, current_idx - 5)
                        aligner.current_index = current_idx
                        live.update(scroller.render(current_idx, is_paused=is_paused), refresh=True)
                    elif key in ('RIGHT', 'f'):
                        current_idx = min(len(script.words) - 1, current_idx + 5)
                        aligner.current_index = current_idx
                        live.update(scroller.render(current_idx, is_paused=is_paused), refresh=True)
                    elif key == 'q':
                        break

                    # Advance cursor with STT only if not paused
                    if not is_paused:
                        new_idx = aligner.advance(text)
                        if new_idx != current_idx:
                            current_idx = new_idx
                            live.update(scroller.render(current_idx, is_paused=is_paused), refresh=True)

                    if current_idx >= len(script.words):
                        break
    except KeyboardInterrupt:
        pass

    return 0

if __name__ == "__main__":
    main()

