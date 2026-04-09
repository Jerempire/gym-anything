from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


def load_hidden_outcome(task_dir: str | Path, outcome_ref: str) -> Dict[str, Any]:
    task_path = Path(task_dir).resolve()
    benchmark_root = next(
        (parent for parent in [task_path.parent, *task_path.parents] if parent.name == "forecasting_world"),
        None,
    )
    if benchmark_root is None:
        raise FileNotFoundError("Could not locate forecasting_world benchmark root")
    outcome_path = benchmark_root / "datasets" / outcome_ref
    return json.loads(outcome_path.read_text(encoding="utf-8"))
