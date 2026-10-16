#!/usr/bin/env bash
# Diagnostic sweep: is the training failure VARIANCE or MECHANISM?
# 3 seeds under the canonical recipe + 1 run with reward normalisation ON.
cd "E:/Education/Master/Final_Project/codes" || exit 1
export PYTHONPATH=.

run () {  # $1 = out dir, rest = extra flags
  local out="$1"; shift
  echo "=== $out : $* ==="
  ./venv/Scripts/python.exe scripts/train_rl.py --algo ppo --steps 2000000 \
      --n_envs 8 --device cpu --reward_shape bonus --out "$out" "$@" 2>&1 \
      | grep -E "first/last mean|saved model" 
}

run results/rl_mekf_s1 --seed 1
run results/rl_mekf_s2 --seed 2
run results/rl_mekf_s3 --seed 3
echo "=== return-scale test: reward normalisation ON ==="
run results/rl_mekf_norm --seed 0 --norm_reward 1
echo "=== SWEEP DONE ==="
