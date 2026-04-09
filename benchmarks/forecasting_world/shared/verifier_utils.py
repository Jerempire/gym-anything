from __future__ import annotations

import json
import os
import tempfile
from typing import Any, Dict


def _copy_json_from_env(copy_from_env, env_path: str) -> Dict[str, Any]:
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
    temp_file.close()
    try:
        copy_from_env(env_path, temp_file.name)
        with open(temp_file.name, "r", encoding="utf-8-sig") as handle:
            return json.load(handle)
    finally:
        if os.path.exists(temp_file.name):
            os.unlink(temp_file.name)


def load_exported_result(copy_from_env, result_path: str = "/tmp/task_result.json") -> Dict[str, Any]:
    return _copy_json_from_env(copy_from_env, result_path)


def load_exported_forecast(copy_from_env, forecast_path: str) -> Dict[str, Any]:
    return _copy_json_from_env(copy_from_env, forecast_path)


def build_feedback(parts: list[str]) -> str:
    return " | ".join(part for part in parts if part)
