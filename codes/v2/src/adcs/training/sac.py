"""Self-contained deterministic PyTorch Soft Actor-Critic (SAC) trainer.

Produces lightweight MLP policies (30 -> 64 -> 64 -> 3) exportable to pure-NumPy checkpoints
with SHA-256 hashes, config snapshots, learning curves, and full seed reproducibility.
"""

from __future__ import annotations

import json
import math
import os
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

# Ensure PyTorch inductor/dynamo never tries to create cache dirs in restricted home folders
os.environ["TORCH_COMPILE_DISABLE"] = "1"
os.environ["TORCHINDUCTOR_CACHE_DIR"] = os.path.join(
    tempfile.gettempdir(), "torchinductor_adcs"
)

import torch
import torch.nn as nn
import torch.nn.functional as F

from adcs.control.residual_rl.policy import (
    ACTION_DIM,
    OBS_DIM,
    NumpyMLPWeights,
    TorchMLPResidualPolicy,
)
from adcs.training.env import ADCSResidualEnv
from adcs.utils.logging import capture_run_metadata, write_jsonl
from adcs.utils.seeding import sha256_canonical


@dataclass(frozen=True)
class SACConfig:
    """Hyperparameters for deterministic SAC training."""

    total_steps: int = 12_000
    warmup_steps: int = 1_000
    batch_size: int = 128
    buffer_size: int = 50_000
    gamma: float = 0.99
    tau_polyak: float = 0.005
    actor_lr: float = 3e-4
    critic_lr: float = 3e-4
    alpha_lr: float = 3e-4
    hidden_dim: int = 64
    critic_hidden_dim: int = 128
    updates_per_step: int = 1
    seed: int = 42
    cosine_lr_decay: bool = True


class _SquashedGaussianActor(nn.Module):
    def __init__(self, obs_dim: int, act_dim: int, hidden: int = 64) -> None:
        super().__init__()
        self.fc1 = nn.Linear(obs_dim, hidden)
        self.fc2 = nn.Linear(hidden, hidden)
        self.mean = nn.Linear(hidden, act_dim)
        self.log_std = nn.Linear(hidden, act_dim)
        # Small final layer init keeps initial residual near zero (safe around classical backbone!)
        nn.init.uniform_(self.mean.weight, -3e-3, 3e-3)
        nn.init.zeros_(self.mean.bias)

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        h = F.relu(self.fc1(x))
        h = F.relu(self.fc2(h))
        mean = self.mean(h)
        log_std = torch.clamp(self.log_std(h), -5.0, 2.0)
        return mean, log_std

    def sample(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        mean, log_std = self.forward(x)
        std = log_std.exp()
        normal = torch.distributions.Normal(mean, std)
        u = normal.rsample()
        a = torch.tanh(u)
        log_prob = normal.log_prob(u) - torch.log(1.0 - a.pow(2) + 1e-6)
        return a, log_prob.sum(dim=-1, keepdim=True)

    def to_numpy_weights(self) -> NumpyMLPWeights:
        return NumpyMLPWeights(
            w1=self.fc1.weight.detach().cpu().numpy().astype(np.float64),
            b1=self.fc1.bias.detach().cpu().numpy().astype(np.float64),
            w2=self.fc2.weight.detach().cpu().numpy().astype(np.float64),
            b2=self.fc2.bias.detach().cpu().numpy().astype(np.float64),
            w_mean=self.mean.weight.detach().cpu().numpy().astype(np.float64),
            b_mean=self.mean.bias.detach().cpu().numpy().astype(np.float64),
        )


class _TwinCritic(nn.Module):
    def __init__(self, obs_dim: int, act_dim: int, hidden: int = 128) -> None:
        super().__init__()
        self.q1 = nn.Sequential(
            nn.Linear(obs_dim + act_dim, hidden),
            nn.ReLU(),
            nn.Linear(hidden, hidden),
            nn.ReLU(),
            nn.Linear(hidden, 1),
        )
        self.q2 = nn.Sequential(
            nn.Linear(obs_dim + act_dim, hidden),
            nn.ReLU(),
            nn.Linear(hidden, hidden),
            nn.ReLU(),
            nn.Linear(hidden, 1),
        )

    def forward(self, obs: torch.Tensor, act: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        xu = torch.cat([obs, act], dim=-1)
        return self.q1(xu), self.q2(xu)


class _ReplayBuffer:
    def __init__(self, capacity: int, obs_dim: int, act_dim: int, seed: int) -> None:
        self.capacity = capacity
        self.obs = np.zeros((capacity, obs_dim), dtype=np.float32)
        self.next_obs = np.zeros((capacity, obs_dim), dtype=np.float32)
        self.act = np.zeros((capacity, act_dim), dtype=np.float32)
        self.rew = np.zeros((capacity, 1), dtype=np.float32)
        self.done = np.zeros((capacity, 1), dtype=np.float32)
        self.ptr = 0
        self.size = 0
        self._rng = np.random.default_rng(seed)

    def add(
        self,
        obs: np.ndarray,
        act: np.ndarray,
        rew: float,
        next_obs: np.ndarray,
        done: bool,
    ) -> None:
        self.obs[self.ptr] = obs
        self.act[self.ptr] = act
        self.rew[self.ptr, 0] = rew
        self.next_obs[self.ptr] = next_obs
        self.done[self.ptr, 0] = 1.0 if done else 0.0
        self.ptr = (self.ptr + 1) % self.capacity
        self.size = min(self.size + 1, self.capacity)

    def sample(self, batch_size: int) -> tuple[torch.Tensor, ...]:
        idx = self._rng.integers(0, self.size, size=batch_size)
        return (
            torch.from_numpy(self.obs[idx]),
            torch.from_numpy(self.act[idx]),
            torch.from_numpy(self.rew[idx]),
            torch.from_numpy(self.next_obs[idx]),
            torch.from_numpy(self.done[idx]),
        )


@dataclass(frozen=True)
class SACTrainResult:
    """Summary returned after training and checkpointing a residual SAC policy."""

    policy: TorchMLPResidualPolicy
    weights_sha256: str
    checkpoint_dir: Path | None
    episode_returns: list[float]
    wall_time_s: float


def train_sac(
    env: ADCSResidualEnv,
    sac_cfg: SACConfig | None = None,
    *,
    checkpoint_dir: str | Path | None = None,
    arm_label: str = "A7_ccr_v2",
) -> SACTrainResult:
    """Train a bounded residual SAC policy deterministically and optionally save checkpoint."""
    cfg = SACConfig() if sac_cfg is None else sac_cfg
    t0 = time.perf_counter()

    torch.manual_seed(cfg.seed)
    np.random.seed(cfg.seed)
    torch.set_num_threads(1)

    actor = _SquashedGaussianActor(OBS_DIM, ACTION_DIM, hidden=cfg.hidden_dim)
    critic = _TwinCritic(OBS_DIM, ACTION_DIM, hidden=cfg.critic_hidden_dim)
    target_critic = _TwinCritic(OBS_DIM, ACTION_DIM, hidden=cfg.critic_hidden_dim)
    target_critic.load_state_dict(critic.state_dict())

    actor_opt = torch.optim.Adam(actor.parameters(), lr=cfg.actor_lr)
    critic_opt = torch.optim.Adam(critic.parameters(), lr=cfg.critic_lr)
    target_entropy = -float(ACTION_DIM)
    log_alpha = torch.tensor(np.log(0.1), dtype=torch.float32, requires_grad=True)
    alpha_opt = torch.optim.Adam([log_alpha], lr=cfg.alpha_lr)

    buf = _ReplayBuffer(cfg.buffer_size, OBS_DIM, ACTION_DIM, seed=cfg.seed + 101)
    act_rng = np.random.default_rng(cfg.seed + 202)

    obs, _ = env.reset(seed=cfg.seed)
    ep_return = 0.0
    ep_len = 0
    ep_idx = 0
    episode_returns: list[float] = []
    curve_records: list[dict[str, Any]] = []

    for step in range(1, cfg.total_steps + 1):
        if step <= cfg.warmup_steps:
            # Small bounded exploration around zero residual (preserves baseline stability)
            act = act_rng.uniform(-0.4, 0.4, size=ACTION_DIM).astype(np.float32)
        else:
            with torch.no_grad():
                obs_t = torch.from_numpy(obs).unsqueeze(0)
                a_t, _ = actor.sample(obs_t)
                act = a_t.squeeze(0).numpy().astype(np.float32)

        next_obs, rew, terminated, truncated, info = env.step(act)
        buf.add(obs, act, rew, next_obs, terminated)
        obs = next_obs
        ep_return += rew
        ep_len += 1

        if step >= cfg.warmup_steps and buf.size >= cfg.batch_size:
            if cfg.cosine_lr_decay:
                denom = max(1, cfg.total_steps - cfg.warmup_steps)
                frac = min(1.0, max(0.0, (step - cfg.warmup_steps) / denom))
                cos_factor = 0.5 * (1.0 + math.cos(math.pi * frac))
                lr_min = 0.15 * cfg.actor_lr
                actor_opt.param_groups[0]["lr"] = lr_min + (cfg.actor_lr - lr_min) * cos_factor
            for _ in range(cfg.updates_per_step):
                b_obs, b_act, b_rew, b_next, b_done = buf.sample(cfg.batch_size)
                alpha_ent = log_alpha.exp().detach()

                with torch.no_grad():
                    next_a, next_lp = actor.sample(b_next)
                    tq1, tq2 = target_critic(b_next, next_a)
                    min_tq = torch.min(tq1, tq2) - alpha_ent * next_lp
                    y = b_rew + cfg.gamma * (1.0 - b_done) * min_tq

                q1, q2 = critic(b_obs, b_act)
                c_loss = F.mse_loss(q1, y) + F.mse_loss(q2, y)
                critic_opt.zero_grad()
                c_loss.backward()
                torch.nn.utils.clip_grad_norm_(critic.parameters(), 5.0)
                critic_opt.step()

                pi_a, pi_lp = actor.sample(b_obs)
                pq1, pq2 = critic(b_obs, pi_a)
                a_loss = (alpha_ent * pi_lp - torch.min(pq1, pq2)).mean()
                actor_opt.zero_grad()
                a_loss.backward()
                torch.nn.utils.clip_grad_norm_(actor.parameters(), 5.0)
                actor_opt.step()

                alpha_loss = -(log_alpha * (pi_lp.detach() + target_entropy)).mean()
                alpha_opt.zero_grad()
                alpha_loss.backward()
                alpha_opt.step()

                with torch.no_grad():
                    for p, tp in zip(critic.parameters(), target_critic.parameters(), strict=True):
                        tp.data.mul_(1.0 - cfg.tau_polyak).add_(cfg.tau_polyak * p.data)

        if terminated or truncated:
            ep_idx += 1
            episode_returns.append(float(ep_return))
            curve_records.append(
                {
                    "episode": ep_idx,
                    "env_step": step,
                    "return": float(ep_return),
                    "length": ep_len,
                    "final_att_err_deg": info.get("att_err_deg", float("nan")),
                }
            )
            obs, _ = env.reset(seed=cfg.seed + ep_idx * 17)
            ep_return = 0.0
            ep_len = 0

    wall_s = time.perf_counter() - t0
    config_hash = sha256_canonical({"sac": asdict(cfg), "arm": arm_label})
    meta = {
        "arm_label": arm_label,
        "sac_config": asdict(cfg),
        "wall_time_s": wall_s,
        "episodes_completed": len(episode_returns),
        "run_metadata": capture_run_metadata(config_hash).to_dict(),
    }
    policy = TorchMLPResidualPolicy(
        actor.to_numpy_weights(),
        action_scale_nm=env._controller._action_scale_nm,
        metadata=meta,
    )

    out_path: Path | None = None
    if checkpoint_dir is not None:
        out_path = Path(checkpoint_dir)
        weights_hash = policy.save(out_path)
        write_jsonl(out_path / "training_curve.jsonl", curve_records)
        (out_path / "train_summary.json").write_text(
            json.dumps(
                {
                    "arm_label": arm_label,
                    "weights_sha256": weights_hash,
                    "wall_time_s": wall_s,
                    "episodes": len(episode_returns),
                    "mean_last5_return": (
                        float(np.mean(episode_returns[-5:])) if episode_returns else float("nan")
                    ),
                },
                indent=2,
            ),
            encoding="utf-8",
        )
    else:
        weights_hash = sha256_canonical({"w1": np.round(policy.weights.w1, 6)})

    return SACTrainResult(
        policy=policy,
        weights_sha256=weights_hash,
        checkpoint_dir=out_path,
        episode_returns=episode_returns,
        wall_time_s=wall_s,
    )
