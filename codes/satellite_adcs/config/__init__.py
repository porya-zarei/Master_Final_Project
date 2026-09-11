"""Config loading for the ADCS simulator (YAML, config-driven)."""
from __future__ import annotations
import os
import yaml

CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))


def _load(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_config(overrides: dict | None = None) -> dict:
    """Load all core config files; apply optional nested overrides."""
    cfg = {
        "satellite": _load(os.path.join(CONFIG_DIR, "satellite.yaml"))["satellite"],
        "orbit": _load(os.path.join(CONFIG_DIR, "orbit.yaml"))["orbit"],
        "actuators": _load(os.path.join(CONFIG_DIR, "actuators.yaml")),
        "sensors": _load(os.path.join(CONFIG_DIR, "sensors.yaml")),
        "disturbances": _load(os.path.join(CONFIG_DIR, "disturbances.yaml")),
        "simulation": _load(os.path.join(CONFIG_DIR, "simulation.yaml"))["simulation"],
        "rl": _load(os.path.join(CONFIG_DIR, "rl.yaml"))["rl"],
    }
    if overrides:
        _merge(cfg, overrides)
    return cfg


def _merge(base: dict, update: dict) -> None:
    for k, v in update.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _merge(base[k], v)
        else:
            base[k] = v
