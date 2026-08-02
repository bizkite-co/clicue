import os
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path


def list_downloaded_models() -> list[tuple[str, int]]:
    """Lists downloaded model directories and their size in bytes."""
    models_dir = get_data_dir()
    results = []
    if models_dir.exists():
        for item in models_dir.iterdir():
            if item.is_dir():
                size_bytes = sum(f.stat().st_size for f in item.rglob("*") if f.is_file())
                results.append((item.name, size_bytes))
    return results

def purge_models(target: str = "all") -> list[tuple[str, int]]:
    """
    Removes downloaded models from ~/.local/share/clicue/models/.
    Returns list of (removed_model_name, freed_bytes).
    """
    models_dir = get_data_dir()
    removed = []
    
    if not models_dir.exists():
        return removed

    for item in list(models_dir.iterdir()):
        if item.is_dir():
            if target.lower() in ("all", "*") or target.lower() in item.name.lower():
                size_bytes = sum(f.stat().st_size for f in item.rglob("*") if f.is_file())
                shutil.rmtree(item)
                removed.append((item.name, size_bytes))
                
    return removed


VOSK_MODELS = {
    "vosk-small": {
        "url": "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip",
        "folder": "vosk-model-small-en-us-0.15",
        "zip_name": "vosk-model-small-en-us-0.15.zip",
    },
    "vosk-full": {
        "url": "https://alphacephei.com/vosk/models/vosk-model-en-us-0.22.zip",
        "folder": "vosk-model-en-us-0.22",
        "zip_name": "vosk-model-en-us-0.22.zip",
    }
}

def get_data_dir() -> Path:
    """Returns the user data directory for clicue (~/.local/share/clicue/models)."""
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    
    models_dir = base / "clicue" / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    return models_dir

def resolve_model_path(model_input: str) -> str:
    """
    Resolves model input to an absolute path.
    Supports shortcuts: 'vosk-small', 'vosk-full'.
    Downloads and extracts model automatically if missing.
    """
    if not model_input:
        model_input = "vosk-small"

    # If model_input is a valid existing path on disk, use it directly
    if os.path.isdir(model_input):
        return os.path.abspath(model_input)

    # Check shortcuts
    model_key = model_input.lower().strip()
    if model_key in VOSK_MODELS:
        info = VOSK_MODELS[model_key]
        models_dir = get_data_dir()
        target_dir = models_dir / info["folder"]

        if target_dir.is_dir():
            return str(target_dir)

        # Also check fallback local repo dirs if present
        local_repo_fallback = Path("model-full") if model_key == "vosk-full" else Path("model")
        if local_repo_fallback.is_dir():
            return str(local_repo_fallback.resolve())

        # Auto-download model
        print(f"Model '{model_key}' not found locally. Downloading from {info['url']}...", file=sys.stderr)
        zip_path = models_dir / info["zip_name"]
        
        try:
            # Download zip
            def _progress(count, block_size, total_size):
                if total_size > 0:
                    pct = int(count * block_size * 100 / total_size)
                    print(f"\rDownloading model [{pct}%]...", end="", file=sys.stderr)

            urllib.request.urlretrieve(info["url"], zip_path, reporthook=_progress)
            print("\nExtracting model files...", file=sys.stderr)

            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(models_dir)

            if zip_path.exists():
                zip_path.unlink()

            print(f"Model extracted to {target_dir}", file=sys.stderr)
            return str(target_dir)
        except Exception as e:
            print(f"Failed to download model '{model_key}': {e}", file=sys.stderr)
            sys.exit(1)

    # Return input as fallback
    return model_input
