"""satellite_adcs — configuration-driven nonlinear ADCS simulator.

Phase 1 (M0/M1): post-release detumble + nadir/LVLH acquisition from random
initial conditions, validated with LQR + MEKF. Built Gymnasium-compatible so
RL (PPO/SAC) becomes the final controller on the same simulator.
"""
