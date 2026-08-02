import os
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path


def get_logs_dir() -> Path:
    """Returns the user log directory for clicue (~/.local/share/clicue/logs)."""
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    
    logs_dir = base / "clicue" / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir

def purge_old_logs(max_age_days: int = 7) -> list[str]:
    """
    Purges date-stamped log files (clicue_YYYY-MM-DD_HHMMSS.log) or log folders older than max_age_days.
    Returns list of purged item names.
    """
    logs_dir = get_logs_dir()
    cutoff_date = datetime.now() - timedelta(days=max_age_days)
    purged = []

    if not logs_dir.exists():
        return purged

    for item in list(logs_dir.rglob("*")):
        if item.is_file() and item.suffix == ".log":
            mtime = datetime.fromtimestamp(item.stat().st_mtime)
            if mtime.date() < cutoff_date.date():
                item.unlink()
                purged.append(item.name)
        elif item.is_dir() and item != logs_dir:
            try:
                folder_date = datetime.strptime(item.name, "%Y-%m-%d")
                if folder_date.date() < cutoff_date.date():
                    shutil.rmtree(item)
                    purged.append(item.name)
            except ValueError:
                pass

    return purged

def list_log_sessions() -> list[dict]:
    """Lists all available performance log files in ~/.local/share/clicue/logs/."""
    logs_dir = get_logs_dir()
    sessions = []
    if not logs_dir.exists():
        return sessions

    log_files = sorted(logs_dir.rglob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    for log_file in log_files:
        size_bytes = log_file.stat().st_size
        mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
        sessions.append({
            "date": mtime.strftime("%Y-%m-%d"),
            "filename": log_file.name,
            "path": log_file,
            "size_bytes": size_bytes,
            "mtime": mtime
        })
    return sessions

class PerfLogger:
    def __init__(self, enabled: bool = True, custom_log_path: str = None):
        self.enabled = enabled
        self.log_file = None
        self.stt_latencies = []
        self.align_latencies = []
        self.render_latencies = []
        self.utterances = 0
        self.latest_stt_ms = 0.0
        self.latest_align_ms = 0.0
        self.latest_render_ms = 0.0

        if not self.enabled:
            return

        # Auto-purge log files older than 7 days on startup
        purge_old_logs(max_age_days=7)

        if custom_log_path:
            p = Path(custom_log_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            self.log_path = p
        else:
            now_str = datetime.now().strftime("%Y-%m-%d_%H%M%S")
            self.log_path = get_logs_dir() / f"clicue_{now_str}.log"

        try:
            self.log_file = open(self.log_path, "a", encoding="utf-8")
            self.log("SESSION_START", f"Clicue performance session started at {datetime.now().isoformat()}")
        except Exception as e:
            print(f"Warning: Could not open perf log file '{self.log_path}': {e}", file=sys.stderr)
            self.enabled = False

    def toggle_disk_logging(self) -> bool:
        """
        Dynamically enables or disables logging to disk during a live session.
        Returns True if disk logging is now ACTIVE, False if OFF.
        """
        if self.enabled and self.log_file:
            self.close()
            self.enabled = False
            return False
        else:
            self.enabled = True
            now_str = datetime.now().strftime("%Y-%m-%d_%H%M%S")
            self.log_path = get_logs_dir() / f"clicue_{now_str}.log"
            try:
                self.log_file = open(self.log_path, "a", encoding="utf-8")
                self.log("SESSION_START", f"Clicue performance session started dynamically at {datetime.now().isoformat()}")
                return True
            except Exception as e:
                print(f"Warning: Could not open perf log file '{self.log_path}': {e}", file=sys.stderr)
                self.enabled = False
                return False

    def log(self, event_type: str, details: str):
        if not self.enabled or not self.log_file:
            return
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self.log_file.write(f"[{ts}] [{event_type:<14}] {details}\n")
        self.log_file.flush()

    def record_stt(self, text: str, latency_ms: float):
        self.latest_stt_ms = latency_ms
        self.stt_latencies.append(latency_ms)
        self.utterances += 1
        self.log("STT_EMISSION", f"Latency: {latency_ms:.1f}ms | Text: '{text}'")

    def record_align(self, text: str, new_index: int, latency_ms: float):
        self.latest_align_ms = latency_ms
        self.align_latencies.append(latency_ms)
        self.log("ALIGN_MATCH", f"Latency: {latency_ms:.2f}ms | Target Index: {new_index} | Input: '{text}'")

    def record_render(self, latency_ms: float):
        self.latest_render_ms = latency_ms
        self.render_latencies.append(latency_ms)
        if len(self.render_latencies) % 30 == 0:
            self.log("TUI_RENDER", f"Frame Render Latency: {latency_ms:.2f}ms")

    def close(self):
        if not self.enabled or not self.log_file:
            return
        avg_stt = sum(self.stt_latencies) / len(self.stt_latencies) if self.stt_latencies else 0.0
        peak_stt = max(self.stt_latencies) if self.stt_latencies else 0.0
        avg_align = sum(self.align_latencies) / len(self.align_latencies) if self.align_latencies else 0.0
        peak_align = max(self.align_latencies) if self.align_latencies else 0.0
        avg_render = sum(self.render_latencies) / len(self.render_latencies) if self.render_latencies else 0.0

        summary = (
            f"\n--- SESSION SUMMARY ---\n"
            f"Total Utterances: {self.utterances}\n"
            f"STT Latency   : avg={avg_stt:.1f}ms, peak={peak_stt:.1f}ms\n"
            f"Align Latency : avg={avg_align:.2f}ms, peak={peak_align:.2f}ms\n"
            f"Render Latency: avg={avg_render:.2f}ms\n"
            f"--- END SUMMARY ---\n"
        )
        self.log_file.write(summary)
        self.log_file.close()
        self.log_file = None
