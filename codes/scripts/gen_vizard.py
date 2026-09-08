"""Generate a Basilisk Vizard .bin file from the Earth-observing env.

Run from `codes/`:
    python scripts/gen_vizard.py [steps] [max_step_duration] [n_targets]

The .bin lands in viz_output/ and is opened with the Vizard app
(D:\\Vizard\\Vizard\\Vizard.exe --loadFile viz_output\\<file>.bin).
More steps / longer max_step_duration = more orbit covered in the replay.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from simulation.envs.eo_imaging_env import make_eo_env


def main(steps: int = 40, max_step_duration: float = 120.0, n_targets: int = 40):
    out_dir = Path("viz_output")
    out_dir.mkdir(exist_ok=True)
    env = make_eo_env(
        max_step_duration=max_step_duration,
        n_targets=n_targets,
        vizard_dir=str(out_dir),
    )
    env.reset(seed=1)
    for i in range(steps):
        env.step(env.action_space.sample())
    env.close()
    files = sorted(out_dir.glob("*.bin"))
    print(f"wrote {len(files)} viz file(s) in {out_dir.resolve()}:")
    for f in files:
        print("  ", f.name, f.stat().st_size // 1024, "KB")


if __name__ == "__main__":
    st = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    dt = float(sys.argv[2]) if len(sys.argv) > 2 else 120.0
    nt = int(sys.argv[3]) if len(sys.argv) > 3 else 40
    main(st, dt, nt)
