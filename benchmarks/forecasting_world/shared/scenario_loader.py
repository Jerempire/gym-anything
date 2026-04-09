from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


def load_visible_scenario(task_dir: str | Path) -> Dict[str, Any]:
    path = Path(task_dir) / "scenario.json"
    return json.loads(path.read_text(encoding="utf-8"))
