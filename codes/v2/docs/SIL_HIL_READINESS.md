# SIL/HIL Readiness & Candidate C/C99 Deployment Boundary

**Status:** Architecture & Interface Readiness Assessment (pre-embedded implementation)  
**Target Control Rate:** `5.0 Hz` (`200 ms` deterministic cycle budget per `spacecraft_config.yaml`)

---

## 1. Candidate C/C99 Onboard Control Boundary

All flight-candidate modules (`B1 MEKF`, `B2 Symptoms`, `B3 Online Capability / AMS`, `B4/B8 Supervisor`, `B5 Classical Backbone`, `B6 MLP Policy`, `B7 Deterministic Authority Gate`, `B9 Allocator`) are completely decoupled from simulator internals (both `FastSimulatorBackend` and `BasiliskBackend`) and use fixed-size arrays with zero dynamic memory allocation requirements in C99.

### Static C99 Interface Contract (Fixed-Size Structs)

```c
/* Fixed-size onboard ADCS cycle structs (SI units, double or float32) */
typedef struct {
    double time_s;
    double gyro_rad_s[3];
    uint8_t gyro_valid;
    double star_tracker_q_ib[4];   /* scalar-first [q0, q1, q2, q3] */
    uint8_t star_tracker_valid;
    double star_tracker_age_s;
    double mag_body_t[3];
    uint8_t mag_valid;
    double rw_speed_rad_s[3];
    uint8_t rw_speed_valid[3];
} adcs_sensor_in_t;

typedef struct {
    double rw_torque_cmd_nm[3];    /* body reaction torque command */
    double mtq_dipole_cmd_am2[3];  /* dipole command */
    uint8_t supervisor_mode;       /* 0=M0..4=M4 */
    uint8_t rl_enabled;            /* 0/1 */
    double rho;
    double alpha;
    double dir_gain[3];
    uint16_t fault_flags;          /* bitmask: invalid/stale/NaN/policy-fault */
} adcs_actuator_out_t;
```

### Static Policy Footprint (`B6`)
- Architecture: `30 -> 64 (ReLU) -> 64 (ReLU) -> 3 (tanh)`
- Total parameters: `30*64 + 64 + 64*64 + 64 + 64*3 + 3 = 6,339` parameters
- Static Flash/ROM weight footprint: **`24.76 KB`** (`float32`) or **`49.52 KB`** (`float64`)
- Static RAM scratch buffer: `< 1 KB` (two 64-element hidden vectors)
- Multiply-accumulate operations (MACs) per inference: `~6,208` FLOPs (`< 0.1 ms` even on a Cortex-M7 @ 200 MHz with hardware FPU)

---

## 2. Deterministic Watchdog & Fallback Architecture

1. **Inference timeout / NaN / checksum guard:** If `B6` inference exceeds a configured sub-budget (e.g. `5 ms`), returns non-finite values, or fails weight CRC-32 check at boot, `policy_valid = 0` is asserted.
2. **Zero-delay fallback (`M3_UNKNOWN_INVALID_UNSAFE`):** `B4/B8` transitions immediately to `M3`, `B7` forces `alpha = 0`, `tau_rl_gated = 0`, and `B5` + `B9` emit a valid deterministic classical control command without skipping a control cycle.
3. **Hard hardware limits:** `B9` box-constrained Gauss-Seidel allocator (`<= 30` fixed iterations, bounded WCET) enforces RW torque, RW momentum-wall headroom, and MTQ dipole saturation strictly downstream of `B7`.

---

## 3. SIL / HIL Integration & Test Plan

### Timing & I/O Assumptions
- **Plant / Truth simulator rate:** `100 Hz` (`10 ms` RK4 integration substep, or Basilisk truth host once installed).
- **Flight software / OBC loop rate:** `5 Hz` (`200 ms` period, synchronized over CAN/UART/Ethernet packet framing with sequence counter + monotonic timestamp + CRC-16).
- **Sensor transport latency budget:** `<= 20 ms` gyro/tachometer, `<= 100 ms` star tracker (`star_tracker_age_s` passed explicitly to `B1` MEKF).

### Fault Injection Points (HIL Harness)
1. **Sensor bus injection (Host -> OBC):** packet drop (star-tracker dropout), stale timestamp freeze, single-frame quaternion corruption (glitch), gyro bias/noise perturbation, magnetometer bias.
2. **Actuator plant injection (Host simulator):** RW gain attenuation, RW lock, RW stuck torque, RW torque bias/Coulomb/stiction friction, MTQ dropout/polarity reversal.
3. **OBC internal fault injection:** disable/corrupt `B6` MLP weight CRC, inject synthetic inference delay to trigger watchdog fallback (`M3`).

### Staged Verification Plan
1. **MIL -> SIL bit-exact parity:** Cross-compile C99 `B1–B9` library, wrap via `ctypes`, replay recorded `E001` Python traces, assert `max |tau_cmd_C - tau_cmd_Py| < 1e-10`.
2. **WCET profiling on target MCU (e.g. STM32H7 / Cortex-M7):** Measure `B1`, `B3`, `B6`, `B7`, `B9` cycle counts with DWT cycle counter; confirm total `< 10%` of `200 ms` budget (`< 20 ms`).
3. **Closed-loop SIL/HIL fault campaign:** Re-run `S0`, `S1`, `S2`, `S4`, `S6`, `S8` with real-time packet I/O and verify zero missed deadlines and safe `M3` fallback under injected policy faults.

---

## 4. Measured Host CPU Profiling Summary

Measured over `500` consecutive control cycles (`5 Hz` = `200.0 ms` budget) via `adcs.evaluation.profiling.profile_control_stack_cpu` on Windows 11 x86_64 (Python 3.14.6, pure NumPy deployment path, `E001_ccr_v2_benchmark`):

| Component | Mean (ms) | p50 (ms) | p95 (ms) | p99 (ms) | Max (ms) |
|---|---:|---:|---:|---:|---:|
| `B1_MEKF` | 0.734 | 0.647 | 1.220 | 1.435 | 1.835 |
| `B3_OnlineCapability` | 1.525 | 1.342 | 2.376 | 2.608 | 2.775 |
| `B6_PolicyInference_NumPy` | **0.034** | 0.028 | 0.061 | **0.094** | 0.143 |
| `CCR_v2_Controller_Step` (B2+B4/B8+B5+B6+B7+B9) | 1.508 | 1.316 | 2.396 | 2.728 | 3.141 |
| `A3_StrongClassical_Step` (for comparison) | 0.912 | 0.786 | 1.545 | 1.778 | 1.969 |
| **Total Onboard (`B1 + B3 + CCR v2`)** | **3.767** | **3.361** | **5.615** | **6.231** | **6.775** |
| `FastSimulator_RK4_Step` (plant only, off-board) | 37.183 | 35.603 | 46.502 | 60.120 | 61.884 |

- **Control-cycle budget utilization (`200 ms` @ `5 Hz`):** **`1.884%` mean**, **`3.115%` p99**, **`3.388%` max** — leaving `> 96.5%` timing margin even in interpreted Python/NumPy.
- **Memory footprint:** `6,339` MLP parameters (`24.76 KB` in `float32`); Python `tracemalloc` peak traced allocation `145.34 KB` (`130.94 KB` steady).
- **Bottleneck identification:** In Python, `B3_OnlineCapability` (`1.525 ms`) and `CCR_v2_Controller_Step` (`1.508 ms`, dominated by Python object creation and box-LSQ loop) account for `~80%` of onboard cycle time; `B6` neural inference is negligible (`0.034 ms`, `< 1%` of onboard compute). Porting `B1/B3/B7/B9` to static C99 structs will reduce cycle time by 10–50x.
