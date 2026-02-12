import json
import os
from pathlib import Path
from typing import Any, Dict, Optional


def get_runtime_config_path() -> Path:
    path = os.getenv("RUNTIME_CONFIG_PATH")
    if path:
        return Path(path)
    return Path(__file__).resolve().parent / "config" / "runtime.json"


def get_default_runtime_config() -> Dict[str, Any]:
    return {
        "version": 1,
        "logging": {
            "level": "normal",
            "print_final_report": False,
        },
        "search": {
            "engine_type": "searxng",
            "mode": "quick",
            "max_loop_count": 1,
            "timeout": 10,
            "max_results": 30,
            "content_extract_length": 2000,
            "max_concurrent_evaluations": 3,
            "early_stop_on_satisfaction": True,
        },
        "agents": {},
        "providers": {},
    }


def load_runtime_config() -> Dict[str, Any]:
    path = get_runtime_config_path()
    if not path.exists():
        return get_default_runtime_config()
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else get_default_runtime_config()
    except Exception:
        return get_default_runtime_config()


def save_runtime_config(config_data: Dict[str, Any]) -> bool:
    path = get_runtime_config_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(config_data, f, ensure_ascii=False, indent=2)
            f.write("\n")
        return True
    except Exception:
        return False


def get_nested(config_data: Dict[str, Any], keys: list, default: Any = None) -> Any:
    cur: Any = config_data
    for k in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(k)
        if cur is None:
            return default
    return cur


def parse_bool(value: Optional[str], default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}

