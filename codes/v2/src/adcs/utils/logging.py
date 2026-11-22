"""Structured logging and experiment metadata capture."""

from __future__ import annotations

import json
import logging
import platform
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import scipy
import yaml

from adcs import __version__ as adcs_version
from adcs.utils.seeding import _canonical_default


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Return a consistently formatted console logger without duplicate handlers."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.setLevel(level)
    return logger


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    """Write a sequence of dictionaries to a JSONL file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, default=_canonical_default) + "\n")


@dataclass(frozen=True)
class RunMetadata:
    """Immutable metadata captured for every simulation or experiment run."""

    timestamp_utc: str
    adcs_version: str
    git_commit: str
    git_dirty: bool
    python_version: str
    platform: str
    numpy_version: str
    scipy_version: str
    pyyaml_version: str
    config_hash: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _git_info(cwd: Path | None = None) -> tuple[str, bool]:
    try:
        commit = (
            subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                cwd=cwd,
                stderr=subprocess.DEVNULL,
                text=True,
            )
            .strip()
        )
        status = subprocess.check_output(
            ["git", "status", "--porcelain"],
            cwd=cwd,
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        return commit, bool(status)
    except Exception:
        return "unknown", True


def capture_run_metadata(config_hash: str, cwd: Path | None = None) -> RunMetadata:
    """Capture software, git, and config metadata for reproducibility."""
    commit, dirty = _git_info(cwd=cwd)
    return RunMetadata(
        timestamp_utc=datetime.now(UTC).isoformat(),
        adcs_version=adcs_version,
        git_commit=commit,
        git_dirty=dirty,
        python_version=sys.version.split()[0],
        platform=platform.platform(),
        numpy_version=np.__version__,
        scipy_version=scipy.__version__,
        pyyaml_version=yaml.__version__,
        config_hash=config_hash,
    )
