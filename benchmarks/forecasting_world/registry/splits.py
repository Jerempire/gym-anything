from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, MutableMapping


DEFAULT_SPLITS_ROOT = Path(__file__).resolve().parents[1] / "splits"
DEFAULT_ENVIRONMENTS_ROOT = Path(__file__).resolve().parents[1] / "environments"


def _dedupe_preserve_order(values: Iterable[str]) -> List[str]:
    ordered: List[str] = []
    seen = set()
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def resolve_environment_key(env_ref: str | Path) -> str:
    path = Path(env_ref)
    return path.name if path.parts else str(env_ref)


def resolve_environment_dir(
    env_ref: str | Path,
    environments_root: Path = DEFAULT_ENVIRONMENTS_ROOT,
) -> Path:
    candidate = Path(env_ref)
    if candidate.exists():
        return candidate.resolve()
    return (environments_root / resolve_environment_key(env_ref)).resolve()


def _load_json(path: Path) -> Mapping[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _extract_additional_splits(data: Mapping[str, object]) -> Dict[str, List[str]]:
    additional: Dict[str, List[str]] = {}
    declared = data.get("additional_splits", {})
    if isinstance(declared, dict):
        for split_name, task_ids in declared.items():
            if isinstance(split_name, str) and isinstance(task_ids, list):
                additional[split_name] = _dedupe_preserve_order(str(task_id) for task_id in task_ids)
    return additional


def _load_split_definition(path: Path) -> tuple[str, Dict[str, List[str]]]:
    data = _load_json(path)
    env_folder = data.get("env_folder")
    if not isinstance(env_folder, str) or not env_folder:
        raise ValueError(f"Split file {path} is missing a valid env_folder")

    env_name = Path(env_folder).name
    train_tasks = _dedupe_preserve_order(str(task_id) for task_id in data.get("train_tasks", []) if isinstance(task_id, str))
    test_tasks = _dedupe_preserve_order(str(task_id) for task_id in data.get("test_tasks", []) if isinstance(task_id, str))
    raw_all_tasks = data.get("all_tasks", [])
    if isinstance(raw_all_tasks, list):
        all_tasks = _dedupe_preserve_order(str(task_id) for task_id in raw_all_tasks if isinstance(task_id, str))
    else:
        all_tasks = []
    if not all_tasks:
        all_tasks = _dedupe_preserve_order(train_tasks + test_tasks)

    splits = {
        "all": all_tasks,
        "train": train_tasks,
        "test": test_tasks,
    }
    splits.update(_extract_additional_splits(data))
    return env_name, splits


def _discover_environment_tasks(environments_root: Path) -> Dict[str, List[str]]:
    discovered: Dict[str, List[str]] = {}
    if not environments_root.exists():
        return discovered
    for env_dir in sorted(environments_root.iterdir()):
        if not env_dir.is_dir():
            continue
        tasks_dir = env_dir / "tasks"
        if not tasks_dir.exists():
            continue
        task_ids = sorted(task_dir.name for task_dir in tasks_dir.iterdir() if task_dir.is_dir())
        if task_ids:
            discovered[env_dir.name] = task_ids
    return discovered


def load_environment_task_splits(
    *,
    splits_root: Path = DEFAULT_SPLITS_ROOT,
    environments_root: Path = DEFAULT_ENVIRONMENTS_ROOT,
) -> Dict[str, Dict[str, List[str]]]:
    splits_root = Path(splits_root)
    environments_root = Path(environments_root)

    registry: MutableMapping[str, Dict[str, List[str]]] = {}
    if splits_root.exists():
        for split_path in sorted(splits_root.glob("*_split.json")):
            env_name, split_data = _load_split_definition(split_path)
            registry[env_name] = split_data

    discovered_tasks = _discover_environment_tasks(environments_root)
    for env_name, task_ids in discovered_tasks.items():
        if env_name in registry:
            if not registry[env_name].get("all"):
                registry[env_name]["all"] = list(task_ids)
            continue
        registry[env_name] = {
            "all": list(task_ids),
            "train": list(task_ids),
            "test": [],
        }

    return {env_name: registry[env_name] for env_name in sorted(registry)}


def get_tasks_for_environment(
    env_ref: str | Path,
    *,
    split: str = "all",
    splits_root: Path = DEFAULT_SPLITS_ROOT,
    environments_root: Path = DEFAULT_ENVIRONMENTS_ROOT,
) -> List[str]:
    env_key = resolve_environment_key(env_ref)
    registry = load_environment_task_splits(
        splits_root=splits_root,
        environments_root=environments_root,
    )
    if env_key not in registry:
        raise KeyError(f"Unknown environment key: {env_key}")
    if split not in registry[env_key]:
        available = ", ".join(sorted(registry[env_key]))
        raise KeyError(f"Unknown split '{split}' for {env_key}; available splits: {available}")
    return list(registry[env_key][split])


__all__ = [
    "DEFAULT_ENVIRONMENTS_ROOT",
    "DEFAULT_SPLITS_ROOT",
    "get_tasks_for_environment",
    "load_environment_task_splits",
    "resolve_environment_dir",
    "resolve_environment_key",
]
