"""Compatibility wrapper for the forecasting benchmark split registry."""

from .splits import load_environment_task_splits


ENV_TASK_SPLITS = load_environment_task_splits()

__all__ = ["ENV_TASK_SPLITS", "load_environment_task_splits"]
