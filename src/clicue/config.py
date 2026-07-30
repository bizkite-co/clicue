import os
import sys
if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

DEFAULT_CONFIG = {
    "scroller": {
        "window_size": 38,
        "past_size": 9,
    },
    "aligner": {
        "max_lookahead": 20,
        "threshold": 70.0,
        "locality_penalty": 1.5,
    },
    "audio": {
        "sample_rate": 16000,
        "model_path": "model",
    },
    "debug": {
        "perf_log": False,
    }
}

def load_config(config_path: str = None) -> dict:
    """
    Loads configuration from `.clicue.toml` or `~/.config/clicue/config.toml`.
    Falls back to DEFAULT_CONFIG.
    """
    cfg = {k: dict(v) for k, v in DEFAULT_CONFIG.items()}

    paths_to_check = []
    if config_path:
        paths_to_check.append(config_path)
    paths_to_check.extend([
        ".clicue.toml",
        os.path.expanduser("~/.config/clicue/config.toml"),
    ])

    for path in paths_to_check:
        if os.path.isfile(path):
            try:
                with open(path, "rb") as f:
                    file_cfg = tomllib.load(f)
                    for sec, vals in file_cfg.items():
                        if sec in cfg and isinstance(vals, dict):
                            cfg[sec].update(vals)
                        else:
                            cfg[sec] = vals
                break
            except Exception as e:
                print(f"Warning: Failed to parse config file '{path}': {e}", file=sys.stderr)

    return cfg
