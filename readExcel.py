# readExcel.py
# Purpose: Read an Excel task table (Task, Duration, Predecessors) into a normalized dict,
#          then validate basic integrity (missing predecessors, duplicates, invalid durations, etc.).

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import pandas as pd

@dataclass(frozen=True)
class TaskInfo:
    duration: int
    preds: List[str]

def norm_col(df: pd.DataFrame) -> pd.DataFrame:
    """
    Strips whitespace from header names and normalizes common variants to:
      - task
      - duration
      - preds
    """
    df = df.copy()
    df.columns = df.columns.astype(str).str.strip()

    # Map a few common header variants
    rename_map = {}
    for c in df.columns:
        c_stripped = str(c).strip()
        c_lower = c_stripped.lower()

        if c_lower == "task":
            rename_map[c] = "task"
        elif c_lower in {"duration", "duration (days)", "duration(days)", "duration_days", "duration day", "days"}:
            rename_map[c] = "duration"
        elif c_lower in {"predecessors", "predecessor", "preds", "dependencies", "depends on"}:
            rename_map[c] = "preds"

    df = df.rename(columns=rename_map)
    return df

def _parse_preds(x) -> List[str]:
    """
    Parse predecessors cell into a list of task ids/names.
    Accepts comma-separated values. Blank/NaN -> [].
    """
    if pd.isna(x):
        return []
    s = str(x).strip()
    if not s:
        return []
    return [p.strip() for p in s.split(",") if p.strip()]


def read_tasks_from_excel(
    filepath: str,
    sheet_name: str = "Sheet1",
) -> Dict[str, TaskInfo]:
    """
    Reads tasks from Excel and returns:
      tasks = { "A": TaskInfo(duration=5, preds=["B","C"]), ... }
    """
    df = pd.read_excel(filepath, sheet_name=sheet_name)
    df = norm_col(df)

    required = {"task", "duration", "preds"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(
            f"Missing required columns: {sorted(missing)}. "
            f"Found: {df.columns.tolist()}"
        )

    # Clean up values
    df["task"] = df["task"].astype(str).str.strip()

    # Convert durations to numeric, fail loudly if not possible
    df["duration"] = pd.to_numeric(df["duration"], errors="raise")

    # Parse predecessors
    df["preds"] = df["preds"].apply(_parse_preds)

    # Build dict keyed by task name
    tasks: Dict[str, TaskInfo] = {}
    for _, row in df.iterrows():
        task = row["task"]
        if task in tasks:
            # Duplicate task rows are usually data errors
            raise ValueError(f"Duplicate task name found in Excel: '{task}'")

        duration_val = int(row["duration"])
        preds_val = list(row["preds"])

        tasks[task] = TaskInfo(duration=duration_val, preds=preds_val)

    return tasks


def validate_tasks(tasks: Dict[str, TaskInfo]) -> List[str]:
    """
    Basic validation:
      - non-empty task names
      - duration is an integer >= 0
      - all predecessor references exist
      - no self-dependencies
      - no duplicate predecessor entries per task
    """
    errors: List[str] = []

    # Quick set for membership tests
    task_names = set(tasks.keys())

    for task, info in tasks.items():
        # Task name check
        if not str(task).strip():
            errors.append("Found an empty task name.")

        # Duration check
        if not isinstance(info.duration, int):
            errors.append(f"Task '{task}' has non-integer duration: {info.duration!r}")
        elif info.duration < 0:
            errors.append(f"Task '{task}' has negative duration: {info.duration}")

        # Predecessor check
        seen = set()
        for pred in info.preds:
            if pred == task:
                errors.append(f"Task '{task}' lists itself as a predecessor.")
                continue

            if pred in seen:
                errors.append(f"Task '{task}' has duplicate predecessor '{pred}'.")
                continue
            seen.add(pred)

            if pred not in task_names:
                errors.append(f"Task '{task}' references missing predecessor '{pred}'.")

    return errors


def read_and_validate_tasks(
    filepath: str,
    sheet_name: str = "Sheet1",
) -> Dict[str, TaskInfo]:
    """
    Read tasks from Excel, validate them, and raise if invalid.
    """
    tasks = read_tasks_from_excel(filepath, sheet_name=sheet_name)
    errors = validate_tasks(tasks)
    if errors:
        msg = "Invalid task table:\n" + "\n".join(f"- {e}" for e in errors)
        raise ValueError(msg)
    return tasks