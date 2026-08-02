import argparse
import json
import os
import pathlib
import re
import sys
import time
import urllib.request
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as get_meta_version

from rich.live import Live

from clicue.aligner import Aligner
from clicue.config import load_config
from clicue.fountain import ParsedScript, parse_fountain
from clicue.models import resolve_model_path
from clicue.scroller import TUIScroller
from clicue.stt import get_stt_listener


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

def get_clicue_data_dir() -> pathlib.Path:
    if sys.platform == "win32":
        base = pathlib.Path(os.environ.get("LOCALAPPDATA", pathlib.Path.home() / "AppData" / "Local"))
    elif sys.platform == "darwin":
        base = pathlib.Path.home() / "Library" / "Application Support"
    else:
        base = pathlib.Path(os.environ.get("XDG_DATA_HOME", pathlib.Path.home() / ".local" / "share"))
    d = base / "clicue"
    d.mkdir(parents=True, exist_ok=True)
    return d

def get_last_script_candidates() -> list[pathlib.Path]:
    d1 = get_clicue_data_dir() / "last_script.txt"
    d2 = get_clicue_data_dir() / "models" / "last_script.txt"
    d3 = pathlib.Path.home() / ".config" / "clicue" / "last_script.txt"
    return [d1, d2, d3]

def save_last_script(path_str: str):
    try:
        if path_str and path_str != "-":
            abs_p = str(pathlib.Path(path_str).resolve())
            for f in get_last_script_candidates():
                try:
                    f.parent.mkdir(parents=True, exist_ok=True)
                    f.write_text(abs_p, encoding="utf-8")
                except Exception:
                    pass
    except Exception:
        pass

def get_last_script() -> str | None:
    for f in get_last_script_candidates():
        try:
            if f.exists():
                content = f.read_text(encoding="utf-8").strip()
                if content and os.path.isfile(content):
                    return content
        except Exception:
            pass
    return None


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


def print_custom_help():
    console = Console()
    
    console.print("\n[bold cyan]CLICUE[/bold cyan] [dim]– Speech-Driven Live Teleprompter Scroller[/dim]\n")
    
    console.print("[bold yellow]USAGE:[/bold yellow]")
    console.print("  [bold green]clicue[/bold green] [cyan]<script.fountain | script.md>[/cyan] [dim][options][/dim]")
    console.print("  [bold green]clicue[/bold green] [cyan]-c[/cyan] | [cyan]--continue[/cyan] [dim][options][/dim]")
    console.print("  [bold green]cat[/bold green] script.fountain | [bold green]clicue[/bold green] [dim][options][/dim]\n")

    console.print("[bold yellow]EXAMPLES:[/bold yellow]")
    console.print("  [bold green]clicue[/bold green] [cyan]script.fountain[/cyan]                      Open script with default Vosk STT engine")
    console.print("  [bold green]clicue[/bold green] [cyan]script.fountain[/cyan] [magenta]--whisper[/magenta]            Use Faster-Whisper neural STT engine")
    console.print("  [bold green]clicue[/bold green] [cyan]script.fountain.md[/cyan]                   Open Fountain markdown script")
    console.print("  [bold green]clicue[/bold green] [cyan]-c[/cyan]                                   Re-open and continue the last-used script")
    console.print("  [bold green]clicue[/bold green] [cyan]-c[/cyan] [magenta]--whisper[/magenta]                         Continue last script with Faster-Whisper")
    console.print("  [bold green]clicue[/bold green] [cyan]script.fountain[/cyan] [magenta]-d[/magenta]                   Enable real-time latency debug header overlay")
    console.print("  [bold green]clicue[/bold green] [cyan]self-up[/cyan]                               Self-update clicue to latest PyPI version")
    console.print("  [bold green]clicue[/bold green] [cyan]models[/cyan]                                List downloaded speech recognition models")
    console.print("  [bold green]clicue[/bold green] [cyan]logs[/cyan]                                  Inspect performance log sessions\n")

    console.print("[bold yellow]ARGUMENTS & OPTIONS:[/bold yellow]")
    console.print("  [cyan]script[/cyan]                Path to script file (.fountain, .fountain.md, .md, or '-' for stdin).")
    console.print("  [cyan]-c, --continue[/cyan]        Re-open and continue the last-used script file.")
    console.print("  [cyan]--whisper[/cyan]             Shortcut for Faster-Whisper neural STT engine.")
    console.print("  [cyan]--engine[/cyan] <name>        STT engine plugin ('vosk' or 'whisper'). Default: vosk.")
    console.print("  [cyan]--model[/cyan] <name>         Model shortcut ('vosk-small', 'vosk-full', 'base.en', 'tiny.en').")
    console.print("  [cyan]-d, --debug[/cyan]           Display real-time STT, Aligner, and Render latency in header.")
    console.print("  [cyan]--perf-log[/cyan]            Enable date-stamped session performance logging.")
    console.print("  [cyan]--raw[/cyan]                 Read text literally without parsing Fountain syntax.")
    console.print("  [cyan]self-up / self-update[/cyan] Self-update clicue to latest PyPI version.")
    console.print("  [cyan]-h, --help[/cyan]            Show this help message and exit.")
    console.print("  [cyan]-V, --version[/cyan]         Show clicue version details and exit.\n")

    console.print("[bold yellow]LIVE TUI SHORTCUTS:[/bold yellow]")
    console.print("  [bold white]r / 0 / Home[/bold white]       Restart teleprompter from word 0 & flush audio buffers")
    console.print("  [bold white]q / Esc[/bold white]            Quit teleprompter immediately")
    console.print("  [bold white]Space / p[/bold white]          Pause / Resume auto-scrolling")
    console.print("  [bold white]Left / Right[/bold white]        Seek backward / forward 5 words")
    console.print("  [bold white]d[/bold white]                  Toggle live latency debug header overlay\n")

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
                            elif ch3 == 'H':
                                return 'HOME'
                else:
                    return 'ESC'
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
            import shutil
            import subprocess
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

    # Support positional 'self-update', 'self-up', or 'update' subcommands
    if args and args[0].lower() in ("self-update", "self-up", "update"):
        console = Console()
        running_ver = get_running_version()
        console.print(f"[bold cyan]Checking for updates...[/bold cyan] (Current: v{running_ver})")
        
        import shutil
        import subprocess

        if shutil.which("uv"):
            upgrade_cmd = ["uv", "tool", "upgrade", "clicue"]
        elif shutil.which("pipx"):
            upgrade_cmd = ["pipx", "upgrade", "clicue"]
        else:
            upgrade_cmd = [sys.executable, "-m", "pip", "install", "--upgrade", "clicue"]

        console.print(f"[dim]Running:[/dim] {' '.join(upgrade_cmd)}")
        res = subprocess.run(upgrade_cmd)
        if res.returncode == 0:
            console.print("[bold green]clicue update check complete![/bold green]")
        else:
            console.print("[bold red]Failed to update clicue.[/bold red]")
        return res.returncode

    # Support positional 'models' or 'purge-models' subcommands
    if args and args[0].lower() in ("models", "purge-models"):
        from clicue.models import get_data_dir, list_downloaded_models, purge_models
        cmd = args[0].lower()
        sub_args = args[1:]
        
        if cmd == "purge-models" or (sub_args and sub_args[0].lower() == "purge"):
            target = "all"
            if cmd == "purge-models" and sub_args:
                target = sub_args[0]
            elif cmd == "models" and len(sub_args) > 1:
                target = sub_args[1]

            removed = purge_models(target)
            if not removed:
                print("No matching downloaded models found to purge.")
            else:
                total_freed = sum(size for _, size in removed)
                mb_freed = total_freed / (1024 * 1024)
                print(f"Purged {len(removed)} model(s) ({mb_freed:.1f} MB freed):")
                for name, size in removed:
                    print(f"  - {name} ({size / (1024*1024):.1f} MB)")
            return 0

        # Default: list models
        models = list_downloaded_models()
        data_dir = get_data_dir()
        if not models:
            print(f"No downloaded models in {data_dir}")
        else:
            print(f"Downloaded models in {data_dir}:")
            for name, size in models:
                size_str = f"{size / (1024*1024*1024):.2f} GB" if size >= 1024**3 else f"{size / (1024*1024):.1f} MB"
                print(f"  - {name} ({size_str})")
        return 0

    # Support positional 'perf' or 'logs' subcommands
    if args and args[0].lower() in ("perf", "logs", "perf-logs"):
        from clicue.perf import get_logs_dir, list_log_sessions, purge_old_logs
        cmd = args[0].lower()
        sub_args = args[1:]
        
        sub = sub_args[0].lower() if sub_args else "list"

        if sub == "purge":
            days = 7
            if len(sub_args) > 1 and sub_args[1].isdigit():
                days = int(sub_args[1])
            purged = purge_old_logs(max_age_days=days)
            if not purged:
                print(f"No log folders older than {days} days found to purge.")
            else:
                print(f"Purged {len(purged)} log folder(s) older than {days} days:")
                for p_folder in purged:
                    print(f"  - {p_folder}")
            return 0

        if sub == "last":
            sessions = list_log_sessions()
            if not sessions:
                print(f"No performance log sessions found in {get_logs_dir()}")
            else:
                last_session = sessions[0]
                print(f"Latest performance log ({last_session['date']}/{last_session['filename']}):")
                with open(last_session['path'], 'r', encoding='utf-8') as f:
                    print(f.read())
            return 0

        # Default: list log sessions
        sessions = list_log_sessions()
        logs_dir = get_logs_dir()
        if not sessions:
            print(f"No performance log sessions in {logs_dir}")
        else:
            print(f"Performance log sessions in {logs_dir}:")
            for s in sessions[:10]:
                size_str = f"{s['size_bytes'] / 1024:.1f} KB" if s['size_bytes'] >= 1024 else f"{s['size_bytes']} B"
                print(f"  - [{s['date']}] {s['filename']} ({size_str}, {s['mtime'].strftime('%H:%M:%S')})")
        return 0

    parser = argparse.ArgumentParser(description="clicue - teleprompter script scroller", add_help=False)
    parser.add_argument(
        "--help",
        "-h",
        action="store_true",
        help="Show clicue help and exit."
    )
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
        default=None,
        help="Path to the script file (or '-' for stdin).",
    )
    parser.add_argument(
        "--continue",
        "-c",
        action="store_true",
        dest="continue_last",
        help="Re-open and continue the last-used script file."
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
    parser.add_argument(
        "--perf-log",
        action="store_true",
        help="Enable performance logging to date-stamped folders in ~/.local/share/clicue/logs/."
    )
    parser.add_argument(
        "--log-file",
        default=None,
        help="Path to custom performance log file."
    )
    parser.add_argument(
        "--debug",
        "-d",
        action="store_true",
        help="Display real-time STT, Aligner, and Render latency stats in TUI header."
    )
    
    parsed_args = parser.parse_args(args)

    if parsed_args.help:
        print_custom_help()
        return 0

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

    from clicue.perf import PerfLogger
    enable_perf = parsed_args.perf_log or bool(parsed_args.log_file) or parsed_args.debug or cfg.get("debug", {}).get("perf_log", False)
    perf_logger = PerfLogger(enabled=enable_perf, custom_log_path=parsed_args.log_file)

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


    target_file = None
    should_close = False
    active_script_path = None

    if parsed_args.continue_last:
        last_p = get_last_script()
        if last_p:
            active_script_path = last_p
            save_last_script(last_p)
            Console().print(f"[bold cyan]Continuing last script:[/bold cyan] {last_p}")
            target_file = open(last_p, "r", encoding="utf-8")
            should_close = True
        else:
            Console().print("[bold red]Error:[/bold red] No previous script found to continue.")
            print_custom_help()
            return 1
    elif parsed_args.script:
        if parsed_args.script == "-":
            target_file = sys.stdin
        else:
            if not os.path.isfile(parsed_args.script):
                print(f"Error: Script file '{parsed_args.script}' not found.", file=sys.stderr)
                return 1
            active_script_path = str(pathlib.Path(parsed_args.script).resolve())
            save_last_script(parsed_args.script)
            target_file = open(parsed_args.script, "r", encoding="utf-8")
            should_close = True
    elif not sys.stdin.isatty():
        target_file = sys.stdin
    else:
        print_custom_help()
        return 1

    try:
        script = parse_script_from_file(target_file, raw=parsed_args.raw)
    finally:
        if should_close and target_file:
            target_file.close()
    
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
        perf_log=perf_log,
        perf_logger=perf_logger
    )
    scroller = TUIScroller(
        script,
        window_size=window_size,
        past_size=past_size,
        debug=parsed_args.debug,
        perf_logger=perf_logger
    )
    listener = get_stt_listener(
        engine_name=engine_name,
        model_path=model_path,
        device=device_param,
        perf_logger=perf_logger
    )

    
    import queue
    import threading

    audio_stream = listener.listen_file(parsed_args.audio_file) if parsed_args.audio_file else listener.listen()
    audio_queue = queue.Queue()
    stop_event = threading.Event()

    def _audio_worker():
        try:
            for text in audio_stream:
                if stop_event.is_set():
                    break
                audio_queue.put(text)
        except Exception:
            pass

    t = threading.Thread(target=_audio_worker, daemon=True)
    t.start()

    current_idx = 0
    is_paused = False
    was_flashing_cue = False

    try:
        with KeyboardListener() as kbd:
            with Live(scroller.render(0, is_paused=False), refresh_per_second=20, auto_refresh=False, screen=True) as live:
                while True:
                    # 1. Non-blocking keypress handling
                    key = kbd.get_key()
                    if key in ('q', 'Q', 'ESC'):
                        stop_event.set()
                        break
                    elif key in ('r', 'R', '0', 'HOME'):
                        current_idx = 0
                        aligner.current_index = 0

                        # Reload script file from disk if path exists
                        if active_script_path and os.path.isfile(active_script_path):
                            try:
                                with open(active_script_path, "r", encoding="utf-8") as f:
                                    reloaded_script = parse_script_from_file(f, raw=parsed_args.raw)
                                    if reloaded_script and reloaded_script.words:
                                        script = reloaded_script
                                        aligner.script_words = script.words
                                        aligner.lower_words = [w.lower() for w in script.words]
                                        scroller.script = script
                                        scroller._cached_lines = None
                                        if perf_logger:
                                            perf_logger.log("FILE_RELOAD", f"Reloaded script from '{active_script_path}' ({len(script.words)} words)")
                            except Exception as ex:
                                if perf_logger:
                                    perf_logger.log("RELOAD_ERROR", f"Failed to reload script: {ex}")

                        # Flush pending STT queue and reset audio listener state
                        with audio_queue.mutex:
                            audio_queue.queue.clear()
                        if hasattr(listener, 'reset'):
                            listener.reset()

                        if perf_logger:
                            perf_logger.log("RESTART_EVENT", "Teleprompter cursor and audio buffers reset to start (0)")

                        r0 = time.perf_counter()
                        live.update(scroller.render(current_idx, is_paused=is_paused), refresh=True)
                        perf_logger.record_render((time.perf_counter() - r0) * 1000.0)
                    elif key in (' ', 'p', 'P'):
                        is_paused = not is_paused
                        r0 = time.perf_counter()
                        live.update(scroller.render(current_idx, is_paused=is_paused), refresh=True)
                        perf_logger.record_render((time.perf_counter() - r0) * 1000.0)
                    elif key in ('d', 'D'):
                        scroller.debug = not scroller.debug
                        r0 = time.perf_counter()
                        live.update(scroller.render(current_idx, is_paused=is_paused), refresh=True)
                        perf_logger.record_render((time.perf_counter() - r0) * 1000.0)
                    elif key in ('l', 'L'):
                        perf_logger.toggle_disk_logging()
                        scroller.debug = True
                        r0 = time.perf_counter()
                        live.update(scroller.render(current_idx, is_paused=is_paused), refresh=True)
                        perf_logger.record_render((time.perf_counter() - r0) * 1000.0)
                    elif key in ('LEFT', 'b', 'B'):
                        current_idx = max(0, current_idx - 5)
                        aligner.current_index = current_idx
                        r0 = time.perf_counter()
                        live.update(scroller.render(current_idx, is_paused=is_paused), refresh=True)
                        perf_logger.record_render((time.perf_counter() - r0) * 1000.0)
                    elif key in ('RIGHT', 'f', 'F'):
                        current_idx = min(len(script.words) - 1, current_idx + 5)
                        aligner.current_index = current_idx
                        r0 = time.perf_counter()
                        live.update(scroller.render(current_idx, is_paused=is_paused), refresh=True)
                        perf_logger.record_render((time.perf_counter() - r0) * 1000.0)

                    # 2. Non-blocking audio queue processing
                    while not audio_queue.empty():
                        text = audio_queue.get_nowait()
                        if not is_paused:
                            new_idx = aligner.advance(text)
                            if new_idx != current_idx:
                                current_idx = new_idx
                                r0 = time.perf_counter()
                                live.update(scroller.render(current_idx, is_paused=is_paused), refresh=True)
                                perf_logger.record_render((time.perf_counter() - r0) * 1000.0)

                    # Auto-refresh while cue flash highlight is active so it un-flashes on time even during silence
                    if scroller.is_flashing_cue:
                        live.update(scroller.render(current_idx, is_paused=is_paused), refresh=True)
                        was_flashing_cue = True
                    elif was_flashing_cue:
                        live.update(scroller.render(current_idx, is_paused=is_paused), refresh=True)
                        was_flashing_cue = False

                    if current_idx >= len(script.words):
                        break

                    if not t.is_alive() and audio_queue.empty():
                        break

                    time.sleep(0.02)
    except KeyboardInterrupt:
        pass
    finally:
        stop_event.set()
        perf_logger.close()

    return 0

if __name__ == "__main__":
    main()


