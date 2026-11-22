"""Deterministic random seed management and canonical hashing for reproducibility."""

from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass
from typing import Any

import numpy as np


class SeedManager:
    """Hierarchical deterministic RNG spawner based on NumPy SeedSequence.

    Guarantees that independent subsystems (plant, sensors, faults, estimator, policy)
    receive statistically independent yet reproducible streams for a given master seed.
    """

    def __init__(self, master_seed: int) -> None:
        if not isinstance(master_seed, int) or master_seed < 0:
            raise ValueError(f"master_seed must be a non-negative integer, got {master_seed!r}")
        self.master_seed = master_seed
        self._root = np.random.SeedSequence(master_seed)

    def spawn_rng(self, stream_name: str) -> np.random.Generator:
        """Create a deterministic Generator uniquely derived from (master_seed, stream_name)."""
        digest = hashlib.sha256(stream_name.encode("utf-8")).digest()
        stream_key = int.from_bytes(digest[:8], "little")
        seq = np.random.SeedSequence([self.master_seed, stream_key])
        return np.random.default_rng(seq)

    def spawn_int_seed(self, stream_name: str) -> int:
        """Return a deterministic 32-bit unsigned integer seed for external libraries."""
        rng = self.spawn_rng(stream_name)
        return int(rng.integers(0, 2**31 - 1))

    def seed_global_python(self) -> None:
        """Seed Python stdlib `random` and legacy `np.random` (for external libraries)."""
        random.seed(self.master_seed)
        np.random.seed(self.master_seed % (2**32))


def _canonical_default(obj: Any) -> Any:
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def sha256_canonical(data: Any) -> str:
    """Compute a deterministic SHA-256 hex digest of a JSON-serializable structure."""
    encoded = json.dumps(
        data,
        sort_keys=True,
        separators=(",", ":"),
        default=_canonical_default,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class EpisodeSeedBundle:
    """Paired seed set ensuring identical environment realizations across controller arms."""

    episode_seed: int
    initial_state_seed: int
    sensor_noise_seed: int
    fault_seed: int
    disturbance_seed: int
    policy_seed: int

    @classmethod
    def from_episode_seed(cls, episode_seed: int, policy_seed_offset: int = 0) -> EpisodeSeedBundle:
        mgr = SeedManager(episode_seed)
        return cls(
            episode_seed=episode_seed,
            initial_state_seed=mgr.spawn_int_seed("initial_state"),
            sensor_noise_seed=mgr.spawn_int_seed("sensor_noise"),
            fault_seed=mgr.spawn_int_seed("fault"),
            disturbance_seed=mgr.spawn_int_seed("disturbance"),
            policy_seed=SeedManager(episode_seed + policy_seed_offset).spawn_int_seed("policy"),
        )
