# Seminar I — Fault-Tolerant Attitude Control of Nanosatellites Using Reinforcement Learning

**Student:** Pouria Zarei  
**M.Sc. Control Engineering — University of Tehran**  
**Supervisor:** Prof. Mohammad Javad Yazdanpanah

---

## Slide 1 — Title

### Fault-Tolerant Attitude Control of Nanosatellites Using Reinforcement Learning

**From spacecraft attitude-control fundamentals to the research gap**

**Visual:** A high-quality real/scientific satellite-in-orbit image or short GIF/video-like visual. Keep the satellite relatively small with negative space for the title.

**Speaker message:** Start from the physical system: what a satellite is, what attitude means, and why attitude control is mission-critical.

**Slide footnote:** Exact image attribution should appear here (e.g. NASA/ESA or the licensed image source).

---

## Slide 2 — Roadmap: From Satellite to Research Question

Use a visual journey rather than a conventional bullet list:

**01 — Satellite & ADCS** → What must a spacecraft control?

**02 — Current ADCS** → How are satellites controlled today?

**03 — My Research Topic** → Why consider reinforcement learning for fault tolerance?

**04 — Related Research** → What have recent studies achieved?

**05 — Research Gap** → What is still missing?

**06 — Conclusion** → Why is this research direction meaningful?

**Key message:** The presentation moves from the engineering problem to the research problem.

---

## Slide 3 — What Is a Satellite? What Is ADCS?

### What is a satellite?

A satellite is a spacecraft placed in orbit to perform missions such as:
- Earth observation
- Communication
- Navigation
- Scientific measurement
- Space-weather monitoring
- Technology demonstration
- Space situational awareness

A satellite must continuously control **where it is pointing** and **how it is rotating**.

### What is ADCS?

**Attitude Determination and Control System (ADCS)** is responsible for:
- Determining spacecraft orientation and angular motion
- Maintaining or changing orientation
- Tracking desired attitudes
- Rejecting disturbances
- Managing angular momentum

### Fundamental closed loop

**Sensors → Attitude Estimation → Controller → Actuators → Spacecraft → Sensors**

**Visual:** Annotated satellite showing gyro/IMU, magnetometer, sun sensor, star tracker, reaction wheels and magnetorquers.

**Key message:** ADCS is a closed-loop control problem in a nonlinear, uncertain and resource-constrained environment.

**Sources:** NASA Small Spacecraft State-of-the-Art — GNC; NASA SSRI ADCS overview.

---

## Slide 4 — Current State of Satellite ADCS: One Size Does NOT Fit All

### Central idea

There is **no single best ADCS architecture** for every satellite.

Controller choice depends mainly on:
- Pointing accuracy
- Slew/agility requirements
- Mission lifetime
- Disturbance environment
- Actuator configuration
- Sensor quality
- Payload requirements
- Computational resources
- Reliability and fault-tolerance requirements

### Mission spectrum

| Mission / spacecraft class | Typical requirement | Typical control philosophy |
|---|---|---|
| Educational / basic CubeSat | Coarse stabilization | Passive stabilization, B-dot, magnetic control, PID/PD |
| Precision CubeSat / SmallSat | Three-axis pointing | PID/PD, LQR, quaternion control |
| Earth-observation / agile SmallSat | Fast slews + precise pointing | LQR, nonlinear control, trajectory optimization, MPC |
| High-performance science / imaging | Very high pointing accuracy | Advanced nonlinear / optimal / model-based control |
| Rendezvous / non-cooperative target | Agile + constrained + autonomous | MPC, nonlinear control, safe/hybrid RL |
| GEO / deep-space / high-value missions | High reliability + long lifetime | Robust/model-based control, redundancy, validated autonomy |

### Important clarification

**Satellite size does not determine controller complexity.**

A small CubeSat can require sophisticated control if its mission requires high pointing accuracy. A larger spacecraft can use a conventional controller if mission requirements are less demanding.

**Speaker line:**  
“Instead of asking which controller a satellite uses, we should ask what the mission requires from the attitude-control system.”

---

## Slide 5 — Controllers, Processors and Sensors

### Controller hierarchy

**Simple / robust**
B-dot → PD/PID

**Model-based**
LQR → quaternion feedback → nonlinear control → sliding-mode/backstepping

**Optimization-based**
MPC → optimal control

**Learning-based**
RL → neural adaptive control → safe/constrained RL

### Is a high-order controller always logical?

**No.**

More sophistication can mean:
- Higher computational cost
- More parameters
- Greater verification difficulty
- More sensitivity to assumptions
- More difficult flight qualification

**Principle:** The controller should be **as sophisticated as the mission requires — not as sophisticated as possible.**

### Onboard computing

| Computing level | Typical role |
|---|---|
| MCU / embedded processor | Basic ADCS, sensor fusion, actuator control |
| Radiation-tolerant CPU | Higher-reliability flight computing |
| FPGA | Deterministic high-rate processing / interfaces |
| SoC / heterogeneous processor | Autonomy, payload processing, AI workloads |
| Ground CPU/GPU | Training and development |

**For this research:** RPi can be used as a **prototype/development target** for computational-feasibility studies; it should not be described as inherently flight-qualified hardware.

---

## Slide 6 — What Sensors Does an ADCS Need?

| Sensor | Main information | Typical role |
|---|---|---|
| Gyroscope / IMU | Angular rate | High-rate propagation |
| Magnetometer | Earth's magnetic-field vector | Coarse attitude / reference |
| Sun sensor | Sun direction | Safe mode / coarse attitude |
| Star tracker | Absolute attitude | High-precision determination |
| GPS/GNSS | Position + time | Orbit knowledge / mission context |
| Earth / horizon sensor | Earth direction | Earth-pointing missions |
| Camera / optical sensor | Relative target direction | Tracking / rendezvous |

### No single sensor is enough

**Gyro:** fast, but drifts  
**Magnetometer / Sun sensor:** absolute references, but limited by environment and accuracy  
**Star tracker:** highly accurate, but more complex and not continuously usable

Therefore:

> **Attitude determination is itself a sensor-fusion problem.**

**Visual:** Sensor icons → estimator → attitude quaternion.

**Source:** NASA 2026 State-of-the-Art Small Spacecraft Technology — GNC.

---

## Slide 7 — My Proposal: Why Fault-Tolerant ADCS With RL?

### The problem

A conventional ADCS is designed around assumptions about:
- Sensors
- Actuators
- Spacecraft dynamics
- Disturbances
- Operating conditions

But real spacecraft can experience:

**Sensor faults**
- Bias
- Dropout
- Incorrect measurements

**Actuator faults**
- Partial effectiveness
- Torque bias
- Reaction-wheel degradation
- Reaction-wheel lock / loss

### Research direction

> **Can reinforcement learning provide adaptive fault-tolerant attitude control for a nanosatellite while maintaining reliable attitude performance?**

### Conceptual chain

**Normal spacecraft → Fault occurs → Available control authority changes → Controller adapts → Attitude performance is maintained**

### Scope of this first seminar

This is **not** a report of completed implementation work.

The focus is:

**Why the problem matters → what researchers have done → what remains missing → why this research direction is meaningful.**

---

## Slide 8 — Three Selected Papers: The Big Picture

| Paper | Main question | Main contribution |
|---|---|---|
| **1. Yang, Jin & Rao (2025)** | Can RL handle spacecraft attitude faults with an unknown system model? | RL-based fault-tolerant attitude control with online adaptation |
| **2. Lu et al. (2026)** | Can RL remain safe during agile tracking with constraints and actuator faults? | Safe RL + fault identification + constrained attitude control |
| **3. Nagano & Schaub (2025)** | Can an RL satellite scheduler remain resilient when reaction wheels fail? | Fault-aware training, fault information and temporal/RNN-based resilience |

### Why these three?

They represent three complementary dimensions:

**Paper 1 → Adaptive attitude control**

**Paper 2 → Safe + constrained attitude control**

**Paper 3 → Fault resilience in satellite autonomy**

### Common question

> **How can learning-based spacecraft autonomy remain useful when the real spacecraft does not behave exactly as expected?**

---

## Slide 9 — Paper 1

# Reinforcement Learning Based Attitude Fault-Tolerant Control of Spacecraft With Unknown System Model

**Yang, Jin & Rao — Journal of the Franklin Institute, 2025**

### Problem

Traditional fault-tolerant control often relies on an accurate spacecraft model and assumptions about actuator behavior.

**Question:** Can RL maintain attitude performance when the system model is unknown and actuator faults occur?

### Approach

**Offline**
- RL + optimal control
- Initial nominal control policy

**Online**
- Neural-network observer estimates unknown system/input characteristics
- RLS updates critic-network parameters
- Feedforward compensation addresses additive actuator faults and disturbances

### Main idea

**Offline knowledge + online adaptation = fault-tolerant RL**

### Relevance

- Directly addresses fault-tolerant attitude control
- Considers unknown system characteristics
- Explicitly models actuator faults
- Introduces online adaptation

### Open questions for further research

- Unseen fault conditions
- Sensor faults
- Safety around learned actions
- Embedded computational limits
- Hardware-in-the-loop validation

**Reference:** Yang, S., Jin, L., & Rao, J. (2025). *Journal of the Franklin Institute*, 362, 107741. DOI: 10.1016/j.jfranklin.2025.107741.

---

## Slide 10 — Paper 2

# Safe Reinforcement Learning Based Agile Satellite Attitude Control for Non-Cooperative Target Tracking With Operation Constraints and Actuator Faults

**Lu et al. — Aerospace Science and Technology, 2026**

### Why important?

The question moves from:

> “Can RL control the satellite?”

to:

> **“Can RL control the satellite while respecting safety and operational constraints?”**

### Mission

Agile imaging satellite tracking a non-cooperative target.

Constraints include:
- Forbidden pointing regions
- Angular velocity limits
- Torque saturation
- Actuator faults

### Framework

**Fault identification**

→ estimates actuator effectiveness loss / additive fault

↓

**Constrained Markov Decision Process**

↓

**WCSAC — Worst-case Soft Actor-Critic**

↓

**Fault-tolerant safe attitude control**

### Main contribution

**Fault tolerance + operational constraints + safe RL**

### Relevance

For spacecraft RL:

> **Performance alone is not enough.**

The controller must also consider safety, actuator limits, operational constraints and faults.

### Further opportunity

Make such methods:
- lighter computationally,
- easier to verify,
- robust to faults not represented during training,
- practical for embedded deployment.

**Reference:** Lu, W. et al. (2026). *Aerospace Science and Technology*, 168, 111238. DOI: 10.1016/j.ast.2025.111238.

---

## Slide 11 — Paper 3

# Enhancing Fault Resilience in RL-Based Satellite Autonomous Task Scheduling

**Nagano & Schaub — AAS 25-637, 2025**

### Important distinction

This paper is **not an attitude controller**.

It studies a higher-level satellite autonomy problem:

> **Can an RL policy remain resilient when reaction wheels develop faults during mission operations?**

### Scenario

Agile Earth-observation satellite scheduling.

Reaction-wheel faults can cause:
- Reduced maneuver capability
- Safe-mode transitions
- Missed imaging opportunities

### Faults studied

- Complete loss of control
- Power-draw limitation
- Increased Coulomb friction
- Faulty encoder measurements

### Three resilience approaches

**1. Fault-injected training**

Train policies in environments containing faults.

**2. Fault information**

Add fault-related information to observations.

**3. Recurrent neural networks**

Use temporal history to infer fault signatures.

### Key insight

> **Fault resilience should be designed into the learning process — not added after training.**

### Relevance to this thesis

This supports evaluating:

**Nominal training vs. fault-aware training vs. unseen-fault testing**

It also highlights **partial observability and temporal information**.

**Reference:** Nagano, Y. & Schaub, H. (2025). AAS 25-637, *Enhancing Fault Resilience in RL-Based Satellite Autonomous Task Scheduling*.

---

## Slide 12 — Research Gaps & Possible Ideas

# From “Fault-Tolerant RL” to “Trustworthy Fault-Tolerant RL”

### Gap 1 — Unseen faults

Many approaches evaluate faults represented during training.

**Idea:** Train on one fault distribution and deliberately test on another:
- unseen severity
- unseen timing
- unseen combinations
- partial vs. complete degradation

### Gap 2 — Safety of the learned controller

A neural policy can produce actions outside its trusted region.

**Idea: Safety layer / fallback**

**RL policy → Safety check → RL action OR verified baseline controller**

### Gap 3 — Detection and control are often separated

A complete fault-tolerant system is:

**Fault → Observation → Detection/Estimation → Adaptation → Control**

### Gap 4 — Deployment constraints

A policy working on a GPU workstation is not automatically suitable for a spacecraft processor.

Evaluate:
- Inference latency
- Memory footprint
- Quantization
- Model size
- CPU utilization
- RPi prototype execution
- HIL behavior

### Central research opportunity

> **A learning-based attitude controller that is generalizable, safe, fault-tolerant and computationally practical.**

---

## Slide 13 — Conclusion

### Five takeaways

**1 — ADCS is mission-critical**  
The spacecraft must know and control its orientation continuously.

**2 — Controller complexity is mission-dependent**  
Not every satellite needs a high-order controller.

**3 — Modern ADCS is increasingly autonomous**  
Advanced sensors, onboard computing and algorithms enable more capable spacecraft.

**4 — RL offers adaptability**  
It can learn behavior for nonlinear, uncertain and fault-affected systems.

**5 — RL also creates new questions**  
Can it generalize? Can it remain safe? Can it handle unseen faults? Can it run under embedded constraints?

### Final research statement

> **The goal is not simply to replace a classical controller with RL.**

> **The goal is to investigate whether learning can make spacecraft attitude control more adaptive and fault-tolerant — without sacrificing safety, reliability and practical deployability.**

---

## Slide 14 — Thank You

# Thank You for Your Attention

### Questions & Discussion

**Pouria Zarei**  
M.Sc. Control Engineering — University of Tehran

**Supervisor:**  
Prof. Mohammad Javad Yazdanpanah

**Visual:** Clean satellite–Earth image with substantial negative space.

No technical content on this slide.

---

# References

1. Yang, S., Jin, L., & Rao, J. (2025). *Reinforcement learning based attitude fault-tolerant control of spacecraft with unknown system model.* Journal of the Franklin Institute, 362, 107741. DOI: `10.1016/j.jfranklin.2025.107741`
2. Lu, W., Zhuang, H., Geng, Z., Shen, Q., Mu, Z., Wu, S., Razoumny, V. Y., & Razoumny, Y. N. (2026). *Safe reinforcement learning based agile satellite attitude control for non-cooperative target tracking with operation constraints and actuator faults.* Aerospace Science and Technology, 168, 111238. DOI: `10.1016/j.ast.2025.111238`
3. Nagano, Y. & Schaub, H. (2025). *Enhancing Fault Resilience in RL-Based Satellite Autonomous Task Scheduling.* AAS 25-637.
4. NASA Small Spacecraft Systems Virtual Institute (2026). *State-of-the-Art of Small Spacecraft Technology — Guidance, Navigation, and Control.*
5. NASA Small Spacecraft Systems Virtual Institute (2026). *State-of-the-Art of Small Spacecraft Technology — Small Spacecraft Avionics.*
6. NASA SSRI Knowledge Base. *Attitude Determination and Control — Small Satellite Systems Engineering.*
7. Blue Canyon Technologies. *Attitude Determination & Control Systems — XACT / FleXcore.*
8. AAC Clyde Space. *iADCS200 — Integrated Attitude Determination & Control System.*

---

# Presentation Design Notes

- Academic aerospace/control-engineering visual language.
- Light background with University-of-Tehran-inspired blue.
- Navy for headings, red for faults, purple for RL, green for desired/safe behavior, gold for constraints/hardware.
- Target sizes: title 30–34 pt, main statements 24–28 pt, body 18–22 pt, tables 15–18 pt, footnotes 8–10 pt.
- Use animation to reveal logic rather than decorate.
- Suggested animations: ADCS loop sequentially; satellite classes progressively; controller hierarchy progressively; fault chain Normal → Fault → Degraded → Adaptation; papers Problem → Method → Contribution → Open Question; gaps one by one.
- Prefer Fade, Wipe and restrained Morph-style transitions. Avoid bouncing, spinning and letter-by-letter text.
