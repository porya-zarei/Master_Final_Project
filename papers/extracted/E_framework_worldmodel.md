# Extraction E — Simulation framework (Basilisk), world model (AdaJEPA), and RL fault-resilience methodology

Scope: two framework/world-model sources and two satellite task-scheduling fault papers.
Rule applied throughout: only what the documents state; anything absent is written as `not stated`.
Numbers are quoted exactly as printed in the source markdowns (including source-side unit
inconsistencies, which are flagged).

Source files (in the order read):
1. `markdowns/Basilisk - A Flexible, Scalable and Modular Astrodynamics Simulation Framework.md`
2. `markdowns/AdaJEPA - An Adaptive Latent World Model.md` (full paper)
3. `markdowns/adajepa-paper.md` (reading notes on the same paper — NOT a second version)
4. `markdowns/Enhancing Fault Resilience in RL-Based Satellite Autonomous Task Scheduling.md` (AAS 25-637)
5. `markdowns/Fault Resilience of Reinforcement-Based Satellite Autonomous Task Scheduling.md` (AAS 25-159)

---

## A) Basilisk — simulation-framework philosophy

**Bibliographic identity.** P. W. Kenneally, S. Piggott, H. Schaub (University of Colorado, Boulder;
Smead Aerospace / LASP / AVS Lab). Journal of Aerospace Information Systems, Vol. 17, No. 9,
pp. 496–507, DOI 10.2514/1.I010762 (bibliographic details taken from the reference lists of
documents 4 and 5; the paper markdown itself carries the title, authors and affiliations only).
Distributed under ISC permissive license; hosted on bitbucket at publication time (later
`avslab.github.io/basilisk`, per docs 4–5).

### A.1 Architecture

- **Stated aim:** "strict modular separation and decoupling of modeling concerns" across coupled
  spacecraft dynamics, environment interactions, and flight-software algorithms.
- **Three fundamental building blocks:** Modules, Tasks, Task Groups.
  - **Module** — stand-alone code implementing one model (actuator, sensor, dynamics) or
    self-contained logic (e.g. translating a commanded control torque into a RW command voltage).
    Modules read input messages they subscribe to and publish output messages.
  - **Task** — a grouping of Modules with **one set integration rate** that governs the update rate
    of all its Modules. Rate is settable per Task and **adjustable mid-run** to capture high-frequency
    phases (example given: flexible solar panel / thruster firing during Mars Orbit Insertion at a
    finer rate, longer step during cruise). Tasks can be **enabled/disabled at any time** during a
    run — explicitly motivated by FSW mode changes (safe mode, sun pointing).
  - **Task Group** — highest-level container of Tasks. Resolves messaging dependencies at
    initialization; described as "silos" of Tasks and messages.
  - **Task Group Interface** — a **unidirectional message exchange from one Task Group to another**,
    letting Modules in one group publish to a second group. Motivated explicitly by **distributed
    simulation**: in a SWIL configuration the dynamics/environment Modules run on a desktop while
    the FSW runs "on a separate flight target processor or processor emulator."
- **Only two core system components** are required to start a scenario: the **Basilisk message
  exchange** and the **Basilisk simulation controller**. Three design choices deliver modularity:
  (1) complete decoupling of model and run-loop dependence; (2) message exchange for module I/O and
  inter-module data requirements; (3) a **Dynamics Manager** for the fully coupled rigid-body
  dynamics.
- **Message-passing system** (publisher–subscriber):
  - A message = a unique name + a payload data structure (typically a C/C++ struct); a header holds
    metadata: allowed publishers, subscribers, buffer memory locations, read/write statistics.
  - One **message storage container per Task Group**, allocated and managed as directly managed
    memory. **All messages are double buffered**; a Module may declare additional buffers. Creating a
    new message grows the allocation and moves existing messages (memory layout shown in the paper's
    Fig. 3).
  - API shown: `SystemMessaging::CreateNewMessage(messageName, maxSize, numMessageBuffers,
    messageStruct, moduleID)` — returns a unique message ID used for all subsequent reads/writes.
  - A Module implements `SelfInit()` (internal setup + registers the messages it will publish) and
    `CrossInit()` (subscribes to messages published in the previous stage) — a **two-stage
    initialization**, plus `Reset()` and `UpdateState(uint64_t currentSimNanos)`.
- **Execution flow:** three nested loops — Task Groups (by assigned priority) → Tasks → Modules
  (by priority within their Task). Each Module's `updateState()` is called: read subscribed inputs →
  compute → write published outputs. The special `SpacecraftDynamics` Module implements the Dynamics
  Manager. After each pass the **next call time** for each Task and Task Group is recomputed (Tasks
  may have different steps and be enabled/disabled), letting the sim skip forward according to the
  combined rates. After all Tasks/Modules in a Task Group update, the message logger copies messages
  and Module variables at the user-selected logging frequency.
- **Dynamics Manager / Effectors:** the spacecraft is modeled as **fully coupled multi-body dynamics**
  with generalized equations of motion, modularized by a **back-substitution method** (ref. [13],
  Allard, Diaz Ramos, Schaub, Kenneally, Piggott, "Modular Software Architecture for Fully Coupled
  Spacecraft Simulations," JAIS, Oct 2018) so that arbitrary forces/torques can be added to a central
  spacecraft hub.
  - **State Effectors** have their own integrated states and contribute to the coupled dynamics:
    reaction wheels, **flexible solar arrays, VSCMGs, fuel slosh**.
  - **Dynamic Effectors** apply external forces/torques: **gravity, thrusters, solar radiation
    pressure (SRP), drag**.
  - A State Effector implements `updateEffectorMassProperties()`, `updateContributions()` (coupled
    contributions to the back-substitution matrices), `computeDerivatives()`. A Dynamic Effector
    implements `computeBodyForceTorque()`.
  - Numerical integrator: user-selectable from "various numerical integration schemes"; the interface
    between Dynamics Manager and integrator is generalized so third parties can add their own scheme.
    RK4 is the integrator used in the paper's example.
- **Python/C++ split:** core architecture and most Modules are **C++**; Modules can also be written in
  **Python** (rapid prototyping), **C** ("to allow flight software modules to be easily ported directly
  to flight targets"), and **Fortran** (legacy space-environment models). Users author scenarios in
  **Python** only. Python bindings are **auto-generated at build time with SWIG**, mirroring the C++
  public variables/functions; Modules/core/utilities are compiled into individual libraries paired
  with their Python wrappers. Result: **no compile-time or run-time dependencies between modules**.
  Cross-platform: macOS, Windows, Linux.
- **Scenario definition (example given):**
  1. `scSim = SimulationBaseClass.SimBaseClass()`
  2. `dynProcess = scSim.CreateNewProcess(simProcessName)`; `dynProcess.addTask(scSim.CreateNewTask(
     simTaskName, sec2nanos(5)))` — the example Task runs at 0.2 Hz (5 s) because **the base time
     scale is nanoseconds** and `sec2nanos()` converts.
  3. `scObject = spacecraftPlus.SpacecraftPlus()` (instantiates the rigid-body hub) then
     `scSim.AddModelToTask(simTaskName, scObject, None, 1)` (last arg = priority).
  4. Gravity: `gravFactory.createBodies(['earth','mars barycenter','sun','moon','jupiter barycenter'])`
     assigned to `scObject.gravField.gravBodies`.
  5. SPICE: `gravFactory.createSpiceInterface(bskPath + '/supportData/EphemerisData/', timeInitString)`
     added to the same Task with priority −1.
  6. Run: `scSim.InitializeSimulation()` → `scSim.ConfigureStopTime(simulationTime)` →
     `scSim.ExecuteSimulation()`. The sim can be stopped, reconfigured in Python, and continued
     (the paper's example commands `scSim.modeRequest = 'safeMode'` then `'navOnly'` between
     `ConfigureStopTime` calls) — i.e. **FSW mode changes and any Module variable are drivable from
     Python**. `Events` objects can trigger custom user functions at run time.
- **Fidelity is configurable** — stated as a headline characteristic ("sufficiently accurate
  (fidelity is configurable) coupled vehicle position and attitude dynamics"), with optional
  structural flexing, imbalanced momentum exchange device, and fuel slosh dynamics.

### A.2 Supported dynamics / fidelity (as stated)

- Coupled **orbital (position) and attitude dynamics**; rigid-body hub with arbitrary effector
  attachment; multi-body gravity; SPICE-governed body positions and spacecraft initial state.
- State effectors: **reaction wheels**, flexible solar arrays, VSCMG, fuel slosh.
- Dynamic effectors: gravity, thrusters, SRP, drag.
- Integrator choice; per-Task integration rates (example Task at 0.2 Hz / 5 s; the paper's module-layout
  figure shows a FSW Task Group with CSS decode, MIRU decode, star tracker acquire, attitude nav
  (1 Hz / 2 Hz), attitude UKF nav, and a DKE Task Group with high-rate DKE at 100 Hz, SRP, RW, ACS,
  flexible panels at 10 Hz). These module names appear only as figure labels (OCR-fragmented), not as
  described models.
- **Reaction-wheel model details** (friction, torque limits, speed limits, encoder resolution):
  **not stated** in this paper.
- **Magnetorquer (MTQ) model:** **not stated** — no MTQ Module is named or described anywhere in the
  document.
- Sensor models (star tracker, coarse sun sensor, MIRU/gyro) appear only as module labels in the
  layout figure; their fidelity is **not stated**.
- ADCS control law / estimator details: only module names (attitude nav, UKF nav, ACS); **not stated**.

### A.3 Validation against truth / other tools

- "Basilisk has undergone an **internal verification and validation effort within LASP and the AVS
  Lab and by comparison to flight data from previous missions**." Named missions: **not stated**.
- Open-source community validation is framed as expected/ongoing ("the community shall provide
  further validation, bug fixes and functionality additions").
- Tool-to-tool benchmarking (numerical agreement with STK/GMAT/OreKit/etc.): **not stated**; the
  state-of-the-art survey is qualitative (OreKit/GMAT/STK focus on high-fidelity orbit dynamics;
  STK+SOLIS does not model disturbances shifting the centre of mass; DARTS and NASA "42" are the
  modular/customizable ones; COTS tools are typically not cross-platform, MATLAB excepted; of the
  listed tools only MATLAB/Simulink and DARTS/Dshell support HWIL/SWIL).
- The one quantitative agreement demonstration given is **SPICE**: a Hubble Space Telescope
  ephemeris supplies the initial state; the RK4-integrated Basilisk trajectory is overlaid on the
  Hubble SPICE trajectory (Fig. 8) and the position difference is plotted (Fig. 9). **No numeric
  error values are stated**; the text claims "close agreement."

### A.4 Performance numbers

- **"at least a 365 times speedup (one mission year in one compute time day)"** — the only explicit
  speed claim. No head-to-head runtime table against other tools.
- **Monte Carlo:** any Python scenario script can be turned into a Monte Carlo run with minimal
  changes; run-time-generated variable dispersions (uniform and normal, currently for Cartesian
  variables, Euler angles, MRP; base classes inheritable for custom distributions and bounds);
  dispersed initial conditions and random seeds saved as **JSON for bit-for-bit repeatability**;
  **multiprocessing** via Python `Multiprocessing`, spawning as many sims as the machine allows
  (paper's example: a 4-core CPU with two virtual cores each is used as 8 processors, running 8
  simulations at once from a worker pool). Logging/post-processing in **PANDAS DataFrames**;
  Matplotlib for single runs and the **DataShaders/Bokeh** rasterized approach for multi-gigabyte
  datasets "in a matter of seconds."
- **Real-time capability:** not claimed as a hard real-time guarantee. The framework is designed to
  serve as the space-environment/dynamics simulator for **HWIL and SWIL**; SWIL is described as
  distributed execution (dynamics/environment on a desktop, FSW on a separate flight processor or
  emulator). No real-time factor, no timing budget for a controller, and no embedded-target numbers
  are stated.

### A.5 Use in academia / industry

- Origin: built to support design and development of the **ADCS for an interplanetary spacecraft**,
  intended from the start as a Phase A/B design and analysis tool, a **flight-algorithm V&V tool in
  Phase C**, and the **environment/dynamics simulator for HWIL and SWIL during Phase D**; the paper
  states Basilisk "has been utilized in all these mission phases."
- Developed/maintained by **LASP + the AVS Lab** at CU Boulder with a gitflow process; open-sourced
  under ISC to encourage contribution.
- Downstream ecosystem shown in documents 4–5: **BSK-RL** (Stephenson & Schaub, "BSK-RL: Modular,
  High-Fidelity Reinforcement Learning Environments for Spacecraft Tasking," 75th IAC, Milan, 2024)
  wraps Basilisk in Gymnasium for spacecraft tasking RL; Basilisk "serves as the generative model
  G(s,a)" and is described as fast and **flight-proven**.
- Named industrial or commercial deployments: **not stated**.

### A.6 What adopting it would buy an RL thesis (assessment grounded in the above)

- A citable, flight-heritage, open-source (ISC) 6-DOF environment with a documented Phase A–D
  pedigree — the credibility anchor the thesis currently lacks with a custom NumPy sim.
- A **natural SIL/HIL boundary**: Task Group Interface + the documented SWIL split (dynamics/env Task
  Group on the host, FSW Task Group on the flight target) is the same topology Phase D needs for an
  ESP32-S3: Basilisk on the PC, controller on the MCU. It is the only source in this set with a
  first-class SWIL/HWIL story.
- **Per-Module integration rates** (0.1 Hz-class orbital tasks up to 100 Hz high-rate dynamics) map
  onto an ADCS loop where the plant integrates far faster than the scheduler/policy.
- **Monte Carlo with dispersed ICs, JSON-seeded bit-for-bit repeatability, and process-level
  parallelism** is a direct analogue of the thesis's current 8-parallel-env setup, but with a formal
  dispersion mechanism for random-attitude initialization and fault randomization.
- Ready-made effector vocabulary for exactly this satellite class: reaction wheels as State
  Effectors, gravity/SRP/drag as Dynamic Effectors, SPICE ephemerides for the orbital environment.
- Costs / limits to plan for honestly: the 365× figure is for the C++ core, not a Python RL loop;
  MTQ is absent (magnetorquer torque bars would be custom Dynamic Effectors); sensor fidelity
  (star tracker, sun sensor, gyro) is not documented in this paper; module development may be in
  C++/C/Fortran with a SWIG build chain; no embedded/real-time numbers are promised. Migrating an
  existing tuned NumPy sim mid-thesis is a schedule risk — the low-risk use is citation + a
  validation cross-check, or a later port.

---

## B) AdaJEPA — adaptive latent world model

### B.0 Relationship between the two files (important)

- Document 2 is the **full paper**: "AdaJEPA: An Adaptive Latent World Model", **Ying Wang,
  Oumayma Bounou, Yann LeCun, Mengye Ren** — NYU / AMI Labs; project page
  `agenticlearning.ai/adajepa`; 19 pages of content.
- Document 3 is a **reading-notes summary of the same paper**, not a second version and not an
  independent paper. It adds metadata not printed in the paper markdown — **arXiv:2606.32026,
  posted June 30 2026**, code at `github.com/agentic-learning-ai-lab/adajepa` — and it contains
  the note-taker's own commentary sections ("Why this is relevant to fault-tolerant attitude
  control", "One gap worth being aware of"). Those two sections are **the thesis author's
  interpretation, not claims of the paper**, and are labelled as such below.
- Every technical claim in document 3 is consistent with document 2. Where the notes compress
  (e.g. "hundredths of a second"), the paper gives the exact range: **0.01–0.03 s per MPC replanning
  step**.

### B.1 Problem statement (as stated)

Latent world models are normally **frozen after training** and paired with MPC. Prediction errors
compound over the planning horizon, and MPC then "optimizes the wrong objective": actions that look
good in latent imagination fail under true dynamics. The failure is amplified under test-time
distribution shift — visual changes (noise, lighting, background distractors) misalign the **encoder**,
while physical changes (friction, mass, contact dynamics) misalign the **latent predictor**. The
authors note even high-capacity world models degrade under small test-environment changes
(citing Zhou et al. 2025; Toso et al. 2026). Claimed gap: "we are the first to adapt a JEPA world
model during planning."

### B.2 Architecture

- **JEPA world model:** trajectories of observations `o_t ∈ R^{n_o}` and actions `a_t ∈ R^{n_a}`.
  - **Sensory encoder** `E^s_φ`, **action encoder** `E^a_ψ`, **predictor** `f_θ`:
    `u_t = E^a_ψ(a_t)`, `z_t = E^s_φ(o_t)`, `ẑ_{t+1} = f_θ(z_t, u_t)` (one-step notation; `f_θ` may be
    conditioned on a short history of latent states and action embeddings).
  - Instantiation used in experiments: a **ResNet encoder** producing global features (stages: five
    residual blocks rb1–rb5, an optional pooling head, and a projection head implemented as
    Linear–GELU–Linear–LayerNorm) plus a **transformer-based predictor** (ViT-style stack of
    transformer blocks followed by a final LayerNorm). Action embeddings are **concatenated with
    visual and proprioceptive embeddings** before the predictor.
  - **Latent dimensionality in the reported runs:** `1×384` (global features) and `196×384`
    (spatial/patch features). Number of transformer blocks: **not stated**.
- **Adaptivity mechanism (the core contribution):** a **plan → execute → adapt → replan** loop inside
  closed-loop MPC. At each MPC step: plan with the current model → execute the first action → observe
  `o_{t+1}` → take `U` self-supervised gradient steps on the freshly observed transition →
  replan immediately with the updated model. No reward labels, no expert demonstrations, no separate
  data-collection phase.
  - **Online buffer** `ℬ` stores transitions `(o_t, a_t, o_{t+1})` collected during MPC, capped at a
    fixed size `N`. Two strategies: **recent-N** (keep the most recent N — default in the main
    experiments, "most stable gains") and **hard-N** (keep the N transitions with the largest
    prediction errors).
  - **Adaptation loss** (Eq. 4): `L_ada(ℬ) = (1/|ℬ|) Σ ℓ( f_θ(z_i, E^a_ψ(a_i)), sg(z_{i+1}) )` with
    `z_i = E^s_φ(o_i)`, `sg(·)` = stop-gradient applied on the target branch as the **default
    anti-collapse stabilizer during online adaptation**. For longer histories / action chunks /
    frameskips the same loss is averaged over all valid prediction windows.
  - **Adapted parameters** `Ω ⊆ {φ, ψ, θ}` updated `U` times per MPC step: `Ω ← Ω − η∇_Ω L_ada(ℬ)`.
    In experiments Ω is restricted to a small subset (default: **last transformer block of the
    predictor + last stage of the encoder**), which is what makes it cheap.
  - **Each episode starts from the same pretrained model and keeps its own copy of parameters and
    buffer** — adaptation is per-episode and is not carried across episodes.
- **What "adaptive latent" means precisely (paper's own usage):** the paper never defines an
  adaptive latent *structure* (no growing/shrinking dimension, no latent-space edits). "Adaptive"
  refers to the **model being updated at test time**; the adaptation acts on the **latent prediction
  objective**, using latent targets recomputed by the encoder (`sg(z_{i+1})`). So: a fixed-size latent
  space whose encoder/predictor parameters are continuously recalibrated from the latent prediction
  error of self-generated experience. Any stronger reading (e.g. an adaptive latent manifold) is not
  supported by the text.

### B.3 Training objective and losses

- Pretraining: `L_pred = (1/K) Σ_{k=1}^{K} ℓ(ẑ_{t+k}, z_{t+k})`, latent prediction (MSE-style) over
  **reward-free offline transitions** `D_off = {(o_t, a_t, o_{t+1})}`, predicting future latent targets
  rather than reconstructing pixels.
- Anti-collapse: **stop-gradient on the target branch** (default), or a regularization term
  (VICReg / LeJEPA style) depending on the JEPA instantiation.
- Additional training objective used in the paper's models: **curvature regularization / temporal
  straightening** ("we apply stop-gradient to the target branch in the prediction loss to prevent
  collapse and use curvature regularization to encourage straighter latent trajectories to facilitate
  planning"), following Wang et al. 2026 (Temporal straightening for latent planning, ICML).
- Test-time objective: `L_ada` (Eq. 4 above), the same self-supervised prediction signal as
  pretraining. The paper notes that removing stop-gradient while updating only the last layers for one
  step gives similar planning performance, i.e. the restricted online update already limits collapse.

### B.4 Planning / controller (no RL anywhere)

- **Receding-horizon MPC** only; **no reinforcement learning** is used or proposed.
- Action sequence optimized by minimizing a **latent goal-reaching cost**:
  `a*_{t:t+H-1} = argmin Σ_{k=1}^{H} α_k d(ẑ_{t+k}, z_g)`, where `z_g = E^s_φ(o_g)`, `α_k` are
  temporal weights, `d` is squared Euclidean distance.
- Solvers: **gradient-based (GD, Adam)** and **sampling-based CEM**. Standard MPC executes the first
  action, then replans. Goal is given as a goal **observation** `o_g`.

### B.5 Datasets and environments

- **PushT** (Chi et al. 2025, contact-rich manipulation: circular pusher pushing a T-block to a target
  pose), using the **DINO-WM setup** (Zhou et al. 2025) where the fixed green T is a visual reference,
  and DINO-WM's PushT **validation trajectories** for the cross-model comparison.
- **PushObj** (Zhou et al. 2025 extension): replaces the T with shapes `{L, Z, +, I, smallT, square}`.
  Data construction: start from **N = 18,500 PushT training trajectories**, add a **contact bias**, and
  generate **16,000 training trajectories per shape**. Test trajectories filtered to keep only those
  with **at least one contact**. Subsets used: `PushObj-TLZ+-4k` (train on {T,L,Z,+}, 4k each; 3 epochs)
  and `PushObj-T-16k` (train on T only, 16k; 3 epochs).
- **PointMaze-Medium** (Fu et al. 2021 / D4RL, MuJoCo 2D navigation; action = forces along x and y;
  **26 open grid cells**); uses the pretrained ResNet global-feature checkpoint from
  Wang et al. 2026 for the dynamics-shift experiments. Goals resampled until Euclidean distance
  > 3 cell units.
- **Diverse PointMaze** (following HWM-PLDM, Zhang et al. 2026): 30 environments with random **8×8**
  maze layouts — **25 for training (2,000 trajectories each, 50,000 total)**, **5 held-out** for
  evaluation; test = 50 episodes (10 per layout); start cell uniform over open cells; goal at a
  BFS-computed shortest-path distance of **3–5 cells**; 3 epochs.
- **Distribution shifts evaluated:** shape shifts (train {T,L,Z,+}, test seen + held-out
  **{I, smallT, square}**; goals 25 steps away), visual shifts (Gaussian blur; salt-and-pepper noise;
  dark lighting; colours: moving T light-gray→red, anchor T light-green→red, agent blue→red; trained
  only on original visuals), dynamics shifts (PointMaze-Medium: **low mass ×0.2** → faster under same
  force; **high damping ×20** → faster velocity decay; goals with grid distance > 3), layout shifts
  (5 unseen 8×8 mazes).

### B.6 Key hyperparameters (as printed)

Training (Table 3): encoder lr **1e-5**; predictor lr **5e-4**; action/proprioception encoder lr
**5e-4**; batch size **64**; history frames **3**; frameskip **5**.
Planning (Table 4): subplanner horizon **25**; executed actions **5**; GD optimizer **Adam**; GD action
initialization **zero**; GD lr **0.1**; GD optimization steps **100**; CEM samples **200**; CEM
optimization steps **10**.
Test-time adaptation defaults: **one gradient step per MPC replanning step**; learning rates equal to
the training rates (**η_pred = 5×10⁻⁴, η_enc = 10⁻⁵**); replay buffer = **5 most recent** transitions;
**one** action chunk executed per replan; max MPC steps **20** (extended to **30** in the main
shape/visual-shift figures); results averaged over **3 test-data seeds × 50 episodes per seed**.
Ablated adaptation targets: `predlast+enclast` (default), `predfirst+enclast`,
`predfirstlast+enclast`, `predlast+encfirst`, `predlast+encfrozen` (encoder frozen), and **LoRA**
(rank **8**, α **16**, inserted into every linear layer of predictor and encoder, only adapters
updated).

### B.7 Compute cost

- Stated cost is **inference/latency only, measured on one H200**: adaptation adds **0.01–0.03 s per
  MPC replanning step** across all three world models and both planners, and adaptation often reaches
  the goal in **equal-or-fewer replans**, so total episode time can fall.
- **Training compute, wall-clock training time, model parameter counts, and memory:** **not stated**
  (acknowledgements credit NYU HPC, and one H200 is used for the latency measurements).

### B.8 Reported results vs baselines (exact values as printed)

Baseline throughout: the **same world model kept frozen** ("Frozen"). Note the two head-to-head tables.

- **PushObj training shapes (in-distribution):** adaptation gives the **largest boost, over 20%
  gain**, because the model specialises to the current shape.
- **PointMaze-Medium dynamics + layout shift table** (success %, mean ± sd; ↑/↓ = delta vs frozen):

| Setting | default | low mass | high damping | Unseen layouts |
|---|---|---|---|---|
| Frozen GD | 82.7 ± 6.8 | 77.3 ± 8.2 | 77.3 ± 5.0 | 53.3 ± 8.2 |
| Frozen CEM | 84.0 ± 3.3 | 82.0 ± 2.8 | 76.0 ± 2.8 | 49.3 ± 6.2 |
| `predlast+enclast` GD | 83.3 ± 6.6 (↑0.7) | 80.0 ± 3.3 (↑2.7) | 77.3 ± 10.5 (n/a) | 66.0 ± 7.1 (↑12.7) |
| `predlast+enclast` CEM | 83.3 ± 3.4 (↓0.7) | 86.7 ± 2.5 (↑4.7) | 78.7 ± 3.4 (↑2.7) | 55.3 ± 5.0 (↑6.0) |
| `predfirst+enclast` GD | 84.0 ± 1.6 (↑1.3) | 82.0 ± 1.6 (↑4.7) | 78.7 ± 4.7 (↑1.3) | 78.7 ± 5.0 (↑25.3) |
| `predfirst+enclast` CEM | 84.0 ± 4.3 (n/a) | 82.7 ± 3.4 (↑0.7) | 82.0 ± 3.3 (↑6.0) | 70.7 ± 3.8 (↑21.3) |

- **Unseen PushObj shapes:** frozen performance drops substantially while AdaJEPA **nearly doubles the
  planning success rate**. In-distribution summary: "test-time adaptation is safe to apply
  in-distribution: it yields large gains when the frozen model is suboptimal and does no harm when it
  is already near-optimal."
- **Visual shifts:** clear gains under blur, noise, lighting; **gains are modest under the red-anchor
  and red-block shifts**, attributed to the model relying on colour to distinguish the fixed anchor
  from the manipulated object (may require augmentation or explicit invariance regularization).
- **Dynamics shifts:** the frozen model already performs strongly (attributed to in-context learning
  over the 3-frame history), yet adaptation still adds consistent gains.
- **Layout shifts:** default `predlast+enclast` improves over frozen; **adapting earlier predictor
  layers improves further** (+25.3 / +21.3 with `predfirst+enclast`); adapted trajectories are closer
  to the shortest path.

**Across-model latency/success table (PushT validation trajectories from Zhou et al. 2025; success %,
per-replan time on one H200):**

| World model | Latent dim | Anti-collapse | Frozen GD | Adapt GD | Frozen CEM | Adapt CEM |
|---|---|---|---|---|---|---|
| Temporal Straightening, global feat. (Wang et al. 2026) | 1×384 | stop-grad | 84.0 ± 2.0 @ 3.14 s | 85.3 ± 3.1 (↑1.3) @ 3.17 s (↑0.03) | 74.0 ± 3.5 @ 0.24 s | 81.3 ± 6.4 (↑7.3) @ 0.27 s (↑0.03) |
| Temporal Straightening, spatial feat. (Wang et al. 2026) | 196×384 | stop-grad | 91.3 ± 4.2 @ 3.37 s | 92.0 ± 3.5 (↑0.7) @ 3.38 s (↑0.01) | 89.3 ± 3.1 @ 5.37 s | 93.3 ± 2.3 (↑4.0) @ 5.39 s (↑0.02) |
| DINO-WM, patch/spatial (Zhou et al. 2025) | 196×384 | not stated | 68.0 ± 10.6 @ 3.66 s | 70.0 ± 4.0 (↑2.0) @ 3.68 s (↑0.02) | 86.7 ± 6.1 @ 9.53 s | 90.0 ± 3.5 (↑3.3) @ 9.56 s (↑0.03) |

- **Which parameters to adapt:** all variants beat frozen; `predlast+enclast` is consistently
  competitive; **predictor-only updates are less effective for visual and layout shifts** (the
  mismatch enters through the observation representation); adapting the **first** predictor layer is
  particularly effective for layout shifts (closest to the latent/action inputs, recalibrates local
  transition structure); LoRA improves over frozen but does not consistently beat selected-layer
  updates; the best target is environment-dependent but performance is not highly sensitive.
- **Hyperparameter ablation (seen shape T / unseen shape square):** across the grid, adaptation lifts
  success **from 50% to 88% on T and from 20% to 51% on square**. Learning rate and number of steps are
  coupled: 5× the training rate is effective with one step but overshoots with several; 0.2× is more
  stable but needs more updates (more latency); 1–2× with one or two steps is robust. Replay-buffer
  choices span **81%–87% on T and 35%–44% on square**, and **every buffer variant, including no buffer,
  beats the frozen model**; recent-window is the most stable.
- **Data-scale study (PushObj; K = training shapes ∈ {1,2,4}, N = trajectories/shape ∈
  {1k,2k,4k,8k,16k}):** frozen improves from **28%→54% (seen)** and **20%→38% (unseen)** going from
  (K=1,N=1k) to (K=4,N=16k). **Diversity beats volume:** with a 16k total trajectory budget,
  (K=4,N=4k) reaches **51.9% unseen success with AdaJEPA vs 45.8% for (K=1,N=16k)**; seen 81% vs 77%
  adapted and 51% vs 44% frozen; unseen 52% vs 46% adapted and 36% vs 29% frozen. Adaptation averages
  **> 30% improvement on seen and > 15% on unseen** shapes across scales. Low-data headline:
  a single-shape, 1k-trajectory adapted model reaches **60.8%** (from 28.1% frozen), **surpassing a
  frozen model trained with 16× more trajectories per shape (43.5%)**; on seen shapes it approaches the
  best four-shape frozen model (64k trajectories, 54%).
- **Visualisation/mechanism:** a decoder trained on the pretrained latent space still reconstructs
  rollouts after lightweight adaptation; an unseen **red** PushT block is decoded as **gray**
  (training colour) and an unseen object as a visually similar seen shape — evidence that adaptation
  **recalibrates predictions while staying near the learned latent manifold**. The bottom panels of the
  trajectory figures show AdaJEPA **consistently decreasing the latent prediction loss** where the
  frozen model does not.

### B.9 Stated limitations

- Adaptation gains are **modest for colour shifts** (red anchor / red block) where the model relies on
  colour; augmentation or invariance regularization may be required.
- Because only a **lightweight correction** is applied during planning, effectiveness is **bounded by
  the coverage of the pretrained representation**: when the test environment requires features absent
  from training, adaptation can improve planning but **may not fully close the gap**. Suggested next
  step (stated by the authors): combine lightweight test-time adaptation with **continual and active
  learning**.
- Hyperparameters (learning rate, number of steps, buffer) are environment- and model-dependent;
  the default is described as a practical starting point, not an optimum.
- **No safety mechanism during adaptation is described in the paper** (no rejection/rollback of a bad
  update, e.g. one driven by corrupted sensor data rather than a genuine dynamics shift). This point is
  the **note-taker's observation in document 3**, not a stated paper limitation — but it is accurate as
  a reading of document 2, which contains no safety gate, no update validation, and no constraint
  handling beyond the MPC cost.
- Not applicable to / not evaluated on: continuous-time rigid-body attitude control, actuator faults,
  hardware, embedded targets, real-time guarantees — **not stated** (no such experiments exist in the
  paper).
- Document 3's own framing (thesis commentary, not the paper): a fault is structurally the same object
  as the paper's dynamics-shift experiments, so a low-dimensional (MLP-scale, not pixel-scale) JEPA plus
  MPC plus this adaptation loop is the natural Phase-F pitch; and the missing safety gate is the
  natural contribution to add.

---

## C) The two fault-resilience task-scheduling papers

### C.0 Relationship between them (explicit)

- **Same authors, same institution**: Yumeka Nagano (PhD student) and Hanspeter Schaub
  (Distinguished Professor / Department Chair), Smead Aerospace, University of Colorado Boulder,
  in both papers.
- **Document 5 = the earlier paper**: *"Fault Resilience of Reinforcement-Based Satellite Autonomous
  Task Scheduling"*, **AAS 25-159**, AAS Spaceflight Mechanics Meeting, Kauai, Hawaii, Jan 19–23 2025
  (venue given by reference [18] of document 4). Its design: **train a policy in a fault-free
  environment, then test it under faults** — a diagnostic/characterisation study that maps where
  performance and safety degrade. Its own future work says: "train the policy in environments that
  include fault scenarios ... integrate onboard fault detection capabilities and incorporate fault
  information into the observation space."
- **Document 4 = the follow-up**: *"Enhancing Fault Resilience in RL-Based Satellite Autonomous Task
  Scheduling"*, **AAS 25-637** (venue not stated in the markdown; AAS conference paper). It **cites
  document 5 as reference [18]** — "Previous research assessed fault resilience by testing policies
  trained in nominal environments under faulted conditions, without using CL or incorporating
  fault-specific training. Building on that foundation, this study focuses on evaluating DRL-based
  policies with CL training approach under RW faults" — and then executes exactly the future work
  listed in document 5, adding a **curriculum-learning baseline** and **three mitigation strategies**.
- So: **not** a conference-vs-journal pair, and **not** two independent studies. It is one
  **incremental two-step project**: (1) characterise degradation under faults with a nominal-trained
  policy; (2) evaluate CL + fault-injected training + observation augmentation + fault randomisation.
  Document 4 adds a **fourth** strategy family (Fault-random with varied fault types/severities) and a
  shutdown comparison that document 5 does not contain; document 5 contains a **battery-capacity fault**
  sweep that document 4 does not.
- Shared lineage: both build on ref. [17]/[3] Herrmann & Schaub RL for AEOSSP; the CL method is
  Mantovani & Schaub (AAS 25-055, AAS GNC 2025); the safety shield is Mantovani & Schaub (IWPS
  Toulouse 2025 / ACC 2025); the simulator is BSK-RL on **Basilisk**.

### C.1 Environment / task-scheduling simulation (both papers)

- **Task:** Agile Earth-Observing Satellite Scheduling Problem (AEOSSP), single satellite, scheduling
  point-by-point imaging of Earth targets (strip imaging noted as a possible extension).
- **Formulation:** **POMDP** `(S, A, T, R, O, Z)`.
  - **State** `s_k`: satellite + environment states needed to propagate the sim (position, velocity,
    attitude/orientation, charge level, plus target locations and priorities).
  - **Action space = 34 discrete actions**: 1 charging action, 1 momentum-management (RW desaturation)
    action, 32 imaging actions for the upcoming 32 targets. Charging and momentum-management actions
    have a **fixed 60 s duration**.
  - **Transition:** deterministic, generated by the simulator: `T(G(s_k,a_k) | s_k,a_k) = 1`, with
    `G(s_k,a_k) = s_{k+1}` the generative model supplied by the environment.
  - **Reward:** per target `R_i = ρ_i` if target `i ∈ U_k` (unfulfilled list), else 0; targets move to
    the fulfilled list `F_k` on successful imaging. Cumulative return per episode.
  - **Observation:** deterministic subset of the state, normalized — includes position and velocity
    in the planet frame, instrument orientation, angular velocity, battery charge level, solar panel /
    sun-vector angle, each RW's angular speed, next eclipse start/end times, target position,
    angle-to-target, target priority, simulation time (paper 2 additionally lists `θ_i` and `t`).
    Assumed noiseless and fully available within the observation set.
  - **Terminal conditions:** battery reaches zero, **or** any RW reaches maximum angular speed
    (both = "failure"); otherwise truncated at the episode horizon (3 orbits nominal, 15 orbits in CL
    training).
  - Discount factor: **γ = 0.999 in document 4**; document 5's Table 3 prints **1.0** (and its table
    columns are collapsed in the markdown — see C.4 caveat).
- **Simulator:** **BSK-RL** (open-source Python package, Gymnasium + **Basilisk**),
  `avslab.github.io/bsk_rl`; Basilisk is the generative model `G(s,a)`, "written in C and C++ with a
  Python interface", described as high-fidelity and fast, modelling dynamics, subsystems, maneuver
  times and power constraints.
- **Subsystem models:** RW torques, battery subsystem (baseline 20 W, maneuver power, imaging power,
  passive charging when panels face the Sun outside eclipse, charging rate from solar incidence
  angle), imaging constraints (relative angle limit 28°, relative angular rate limit 0.01 rad/s),
  momentum management (align to inertial frame, fire thrusters to dump RW momentum).
- **Satellite (both, Table 2):** altitude **500 km**, mass **330 kg**, inertia **[121, 98, 82] kg·m²**,
  battery capacity **160 Wh** (document 4's table prints **160 W** — a unit inconsistency in the
  source), base power **20 W**, initial battery charge fraction **[0.4, 1.0]**, angle limit **28°**,
  rate limit **0.01 rad/s**, RW max torque **0.2 Nm**, RW max speed **1500 RPM**, initial RW speed
  **[−900, 900] RPM**, requests **[1000, 10000]**, priority ρ ∈ [0,1], external torque **0.1 mNm**.
  Circular orbit, period **95 min**. 4 RWs (3 body-axis yaw/pitch/roll + 1 redundant tilted at equal
  angles to the others); RW null space used to decelerate wheels without perturbing the spacecraft;
  document 4 adds an encoder model of **1024 counts per revolution**. Targets uniform over the Earth's
  surface; request counts 1,000–10,000 (tested at 1k, 2k, 3k, 4k, 6k, 8k, 10k); external-torque
  direction randomised per episode.
- **RL stack:** **APPO (Asynchronous PPO) from RLlib**; train on CURC (CU Boulder cluster), **32 CPU
  workers**. Policy network **2 hidden layers × 512 neurons**; RLlib defaults for everything else
  (including LSTM settings). Document 4 additionally uses RLlib's native recurrent-policy support
  for its LSTM variants.

### C.2 How faults are injected (weights? observations? actuators? nodes?)

Faults are injected **in the simulated physical subsystem / actuator model, at the start of each
episode** — the policy is never corrupted. Concretely:

- **Placement: start of episode, persistent for the episode** ("All faults are introduced at the
  beginning of each episode", both papers). No mid-episode fault onset, no intermittent faults.
- **Actuator/torque path (both papers):**
  1. **Uncontrollable RW fault** — one RW's power draw limited to **1.0 × 10⁻¹² W**, so it can rotate
     passively but contributes no control torque. (In document 4's training environment, if a fault is
     selected, "one of the four single-RW faults is selected uniformly at random" — i.e. which wheel
     is randomised.)
  2. **Power-limit fault** — the RW's power draw is constrained (reduced speed vs nominal). Document 5
     states no power-draw restriction exists by default, only a torque limit. Tested limits: document
     5 = **0.001, 0.01, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0 W**; document 4 = **0.001, 0.01, 0.1, 1.0,
     10.0 W** (training severity range 0.001–10 W).
  3. **Friction fault** — the RW's **Coulomb friction increased** (constant regardless of speed):
     baseline **0.5 mNm**, scaled by **×10, ×100, ×200, ×300, ×400, ×1000** in testing (document 4's
     training range 10×–1000×).
  4. **Encoder measurement fault** — (a) the RW encoder measurement is **turned off**, or (b) it is
     **stuck at its initial value**. This is a measurement/feedback-path fault, so it degrades the
     controller's knowledge of wheel speed, not the wheel itself.
- **Non-actuator subsystem fault (document 5 only):** **battery capacity fault** — capacity reduced to
  **10%, 20%, 30%, 40%, 50%, 60%, 70%, 80%, 90% of nominal** (explicitly flagged in the paper as not
  an RW-associated fault).
- **Not done anywhere in either paper:** no corruption of policy weights, no gradient/noise injection
  into the neural network, no node/latency/compute faults, no communication faults, no multi-fault
  simultaneous injection, no faults on the sensors feeding the RL observation except through the
  physical encoder model above (document 4's observation augmentation supplies fault *labels*, not
  corrupted observations), and no thruster or solar-array faults (explicitly listed as future work in
  document 5).

### C.3 Fault-tolerant mechanism(s)

- **Fault observability is the pivot of both papers** (motivated by a POMDP formulation: "reflecting
  real-world limitations in fault observability").
- **Document 5 (diagnostic):** no mitigation mechanism is trained. The deployed artefact is a policy
  trained **fault-free** plus a **shield** during testing. Its conclusions map the degradation
  thresholds (C.5).
- **Document 4's baseline:** the **CL (curriculum learning) policy** — trained with no faults, but with
  a curriculum that linearly decreases battery capacity **160 → 64 W** and linearly increases external
  torque **0.01 → 0.4 mNm**, samples initial battery charge from **[0,100]%**, initial RW speeds from
  **[−1500, 1500] RPM**, and extends the episode horizon **3 → 15 orbits**. CL is used because it is
  the best-performing robustness method from ref. [17]; it is the reference for all fault comparisons.
- **Document 4's three mitigation strategies:**
  1. **Training in fault environments** (no fault information given to the agent) — 50% nominal /
     50% uncontrollable-RW episodes, with a **feed-forward policy** (`Fault`) and an **LSTM policy**
     (`Fault-LSTM`) so the agent can infer latent faults from observation history.
  2. **Augmenting the observation space with fault information** (assumes onboard detection and
     identification) — two variants: `Fault-bool` (binary fault presence) and `Fault-num`
     (faulty RW index: 0 = no fault, 1–4 = RW1–RW4 fault).
  3. **Varied fault types and severities during training** — `Fault-random`: 25% nominal / 25% power
     limit / 25% friction / 25% encoder fault, one RW chosen at random, severities randomised; the
     agent is told **which RW** is faulted but **not** the fault type or severity.
- **Model-free heuristic alternative evaluated:** **shut down the identified faulty RW and control with
  the remaining three wheels**, using the CL policy (which never saw faults) — compared directly
  against the fault-aware trained policy at the same fault.
- **Safety mechanism (both papers): a "shield"** adapted from the **Handmade shield** of
  Mantovani & Schaub. Two hard constraints enforced at test time: force a **charging action when
  battery < 25% of maximum capacity**; force a **momentum-management (desaturation) action when any RW
  angular speed > 70% of its maximum**. Applied in **all** testing in document 4 and explicitly
  adopted in document 5 after an ablation.
- **No online adaptation, no model identification, no controller reconfiguration** beyond the
  shutdown case; no test-time learning of the kind AdaJEPA uses.

### C.4 Training setup

**Document 4 (the follow-up; its Table 3 is clean):**
- APPO / RLlib; **32 workers**; **up to 3 × 10⁷ environment steps per policy**; learning rate
  **3 × 10⁻⁵**; training batch size **10,000**; minibatch **250**; **50** SGD iterations; network
  **2 × 512**; discount factor **0.999**; failure penalty **0**; CU Boulder computing cluster (CURC).
- Training environments per policy: `CL` = curriculum, no faults; `Fault` = 50% nominal / 50%
  uncontrollable RW; `Fault-LSTM` = same with LSTM; `Fault-bool` = same + binary fault flag;
  `Fault-num` = same + faulty-RW index; `Fault-random` = 25/25/25/25 nominal/power/friction/encoder.
- Testing: nominal parameters unless a fault is introduced; **50 trials per configuration with
  different random seeds, the same seed set applied across all cases**; request counts
  1,000–10,000. (The text says testing uses "the nominal parameter settings listed in Table 5";
  Table 5 is the CL training table — a source-side cross-reference slip.)

**Document 5 (the earlier paper; Table 3 columns are collapsed in the markdown):**
- APPO / RLlib; **32 workers**; **up to 2 × 10⁷ steps** (narrative text); the printed table reads, in
  order, `32, 10⁶, 5·10⁻⁵, 3·10,000, 250, 50, 2 layers with 512 neurons each, 1.0, 0` — i.e. learning
  rate **5 × 10⁻⁵**, minibatch **250**, **50** SGD iterations, network **2 × 512**, discount factor
  **1.0**, failure penalty **0**, with **training batch size and step count ambiguous due to the
  collapsed column**. Treat document 5's exact step count and batch size as uncertain (the prose says
  "up to 20 million steps").
- Training assumed **no fault scenarios**. Testing: 50 runs per fault scenario per target count with
  different random seeds, the **same seed set shared across all fault cases**; shield thresholds
  battery 25% / RW 70%.

### C.5 Evaluation protocol and key results

**Document 5 — protocol:** every fault scenario compared against the fault-free case; metrics = total
episode reward, alive rate (fraction of episodes not failing), image success rate (successfully imaged
targets / total imaging actions), average battery level, average RW1 speed; plus a table of **ratio of
time spent in eclipse at the end of failed episodes** (power-limit table: no fault 0.67, 0.001 W 0.34,
0.01 W 0.35, 0.1 W 0.65, 0.5 W 0.43, 1.0 W 0.50, 2.0 W 0.44, 3.0 W 0.25, 5.0 W 0.50, 10.0 W 0.33;
friction table: no fault 0.67, ×10 0.67, ×100 0.67, ×200 0.75, ×300 0.57, ×400 0.81, ×1000 0.85;
battery table: no fault 0.67, 10% 1.00, 20% 0.99, 30% 0.99, 40% 0.98, 50% 0.88, 60% 0.85, 70% 0.43,
80% 0.50, 90% 0.50). Notable: battery depletion does **not** strongly correlate with eclipse timing
(no-fault ratio 0.67 vs 10%-capacity 1.00, i.e. failures happen even with ample eclipse margin).

**Document 5 — key results:**
- Any RW becoming uncontrollable degrades performance significantly (most actions fail); faults on
  **RW1 (across-track)** and **RW2 (along-track)** — the wheels used most often — cause the most
  pronounced degradation **and** more failed charging actions, hence worse safety.
- Power limit: performance declines gradually with lower limits; **safety is significantly compromised
  at ≤ 0.01 W** because manoeuvre speed becomes insufficient even for the longer-window charging action.
- Friction: gradual decline, **severe degradation and safety compromise at ≥ 400× nominal** (wheel too
  slow; charging insufficient to support eclipse operations at higher power draw).
- Encoder fault: **minimal impact** on performance and safety, because the control system is
  torque-based rather than speed-based (errors only occasionally block momentum management).
- Battery capacity: gradual decline with capacity; **safety significantly compromised at ≤ 40% of
  nominal**.
- **Stated resilience envelope:** "for less severe faults — such as power limits **above 5.0 W**,
  friction multipliers **below 100×** nominal, and battery capacities **exceeding 90%** of nominal —
  the policy demonstrates resilience, with performance comparable to the fault-free case."
- Also: performance declines further as the number of requests rises, since more targets demand
  quicker manoeuvres.

**Document 4 — protocol:** reward change normalised against either the nominal environment (Eq. 4:
`ΔR = (R_fault,i − R_nominal,i)/R_nominal,mean`) or against the CL policy (Eq. 5), plus relative alive
rate (>100% = more survivable than the reference, <100% = worse). Every policy tested under the fault
class its design targets (CL and one `Fault` variant additionally tested under "All" fault types);
Fault-random tested under power limit, friction, and encoder faults; evaluation of the mild faults
uses **RW1 only** because the individual-RW analysis showed it has the greatest impact (trends
consistent across wheels).

**Document 4 — key results:**
- **Shield ablation (nominal, CL policy):** **1 failure in 350 trials with the shield vs 3 in 350
  without** → shield applied everywhere afterwards.
- **CL policy under fault:** degradation is severe under uncontrollable-RW faults; RW1/RW2 worst with
  more failed charging attempts. Power limit: gradual; **safety significantly compromised at
  ≤ 0.01 W**. Friction: significant at **≥ 400× nominal**; safety compromised at 400×. Encoder: slight
  decline only.
- **Strategy 1 — training in fault environments:** the `Fault` policy **does not improve performance in
  the fault environment** even though it was trained there without fault information (aliveness
  comparable to CL except at low request counts). At low request counts CL is over-conservative
  (prefers charging/desaturation over imaging) while `Fault` takes more imaging actions; the gap closes
  as request counts rise. `Fault-LSTM` "demonstrates limited learning within the training horizon",
  fails to adopt effective charging behaviour, keeps prioritising imaging, and converges "significantly
  slower" — the authors note longer training might help but that extended training would also benefit
  every architecture.
- **Strategy 2 — fault information in the observation:** `Fault-num` (which RW) **outperforms the CL
  policy overall in reward**, or at least matches it; `Fault-bool` (binary flag) performs **worse than
  CL**. Aliveness comparable in both. Mechanism observed: `Fault-bool` shifts towards charging over
  desaturation, while `Fault-num` can prioritise imaging over desaturation because the policies learn
  that desaturation is ineffective when a specific wheel is faulted (the faulty wheel cannot offload
  momentum).
- **Shutdown beats fault-aware training for severe faults:** shutting down the faulty RW and flying the
  CL policy on the remaining three wheels gives **significant improvements in both reward and alive
  rate** compared with the fault-aware trained policy (`Alive/CL alive` rises above 105% in that figure
  vs ~95–105% for the fault-observation policies). The paper therefore pivots to mild faults.
- **Strategy 3 — randomised fault training (`Fault-random`):** consistently **outperforms CL in reward
  across all fault types** (CL stays overly conservative), but **alive rate is worse than CL under
  severe conditions** — power limit **≤ 0.1 W**, and friction multipliers **400× and 1000×**. No
  significant alive-rate difference for the encoder fault. Interpretation given: CL's conservatism is
  advantageous under severe faults but suboptimal under mild ones.
- **Overall conclusion (document 4):** for severe faults, fault-adaptive training is insufficient and
  **shutdown of the faulty RW is more effective**; for milder faults, **training in the fault
  conditions improves resilience and overall performance**.
- **Stated limitations (document 4):** the training environment cannot represent all real-world fault
  conditions (modelling every fault type is impractical); and when exposed to a mixture of fault types
  and severities, the policy **may disproportionately adapt to the more frequently encountered faults**,
  reducing robustness to rarer or more severe ones.

### C.6 What the two papers do NOT evaluate (relevant to the thesis)

- No unseen-fault *type* hold-out protocol of the AdaJEPA kind: document 4's randomised training spans
  power/friction/encoder, and testing uses the same fault families and severity grids. Severity values
  outside the training range (document 5's exact multipliers/limits) are tested, but the evaluation is
  not framed as OOD generalisation and no held-out-fault-family experiment is reported.
- No online adaptation, no world model, no MPC — the controller is a feed-forward or LSTM policy plus
  a handcrafted shield.
- No HIL, no embedded target, no inference-latency measurement; training is on 32 CPU cores, not GPUs.
- No attitude-control-quality metrics (pointing error, settling time, torque saturation); the metrics
  are task/reward and survival (alive rate) only.

---

## Cross-cutting patterns

1. **One lineage, one simulator.** Basilisk (JAIS 2020) → BSK-RL (IAC 2024) → the two AAS 2025 fault
   papers, all from the same group. Basilisk is the shared generative model, and the fault papers
   inherit its satellite parameters (330 kg, 500 km, 4 RWs, 0.2 Nm, 1500 RPM). Citing Basilisk +
   BSK-RL buys the thesis a body of comparable, already-satellite-shaped evidence.
2. **Deployment-time distribution shift is the common enemy.** AdaJEPA names it explicitly (visual vs
   dynamics shift) and attacks it with online self-supervised updates; the fault papers name it as RW
   faults and attack it with domain randomisation, observation augmentation, architecture change, and
   a shutdown heuristic. Nobody in this set attacks it with online adaptation *and* a safety gate.
3. **Fault-blind training barely helps.** The single most transferable negative result: document 4's
   `Fault` policy trained in a 50% fault environment without fault information did **not** improve
   reward in the fault environment, and the LSTM variant failed to converge within the budget. Giving
   the policy the **wheel index** did help; a binary flag did not.
4. **Observation/actuator faults matter less than the control law's structure.** Both papers find
   encoder (tachometer) faults nearly harmless because attitude control is torque-based. Corollary for
   an ADCS thesis: the exposure is in wheel *authority* and *allocation*, not in wheel telemetry.
5. **Fixed seeds + large trial counts + severity sweeps is their evaluation grammar.** 50 runs per
   config, one shared seed set, 7 request counts, ~6–10 severity levels, plus relative-to-baseline
   normalised deltas and an explicit "alive rate" survival metric. AdaJEPA's grammar is the same but
   in success-rate form: 3 seeds × 50 episodes, held-out shapes/mazes, frozen-vs-adapted paired
   comparison.
6. **Both sets of authors report the same ceiling.** AdaJEPA: adaptation is bounded by pretrained
   representation coverage. Document 4: a policy trained on a mixture "may overly adapt to more
   frequent faults, potentially neglecting rare but critical ones." Domain randomisation and online
   adaptation both degrade on the tail, and both papers say so.
7. **Compute scale differs by an order of magnitude in kind, not just size.** The task-scheduling
   policies need **2–3 × 10⁷ env steps on 32 CPU cores**; AdaJEPA's contribution costs **1 gradient
   step per replan (+0.01–0.03 s on an H200)**. The thesis's 2M steps / 8 CPUs sits below the former
   and roughly at the scale of the latter's *inference* budget.
8. **Safety is bolted on, never learned.** In the fault papers it is the two-constraint handcrafted
   shield (battery < 25% → charge; RW speed > 70% → desaturate); in AdaJEPA it is absent. An ADCS
   analogue (wheel-saturation / torque / attitude-error gate) would be both citable and novel in the
   world-model context.

## What this means for an ADCS thesis organised as C-freeze → D-HIL → E-defence → F-optional-world-model

- **Cite Basilisk + BSK-RL as the credibility anchor; do not (yet) adopt them as the plant.** They are
  the only sources in this set with flight-heritage validation and a documented Phase C/D role, and
  BSK-RL proves Basilisk drives RL loops. But the 365× claim is about the C++ core, MTQ support is not
  documented, the sensor models are figure labels only, and the toolchain is C++/SWIG-based. Realistic
  use: a cross-validation run of attitude dynamics against the NumPy model, and a citation for why a
  6-DOF coupled plant is the right level of fidelity — not a mid-thesis migration of a 2M-step PPO
  pipeline.
- **Phase D (HIL/MCU) is where Basilisk's architecture actually pays off, and it is a strong argument
  in the proposal.** The Task Group Interface is a unidirectional message exchange designed exactly for
  the SWIL split "dynamics/environment on the host, FSW on a separate flight target processor or
  emulator". That is the ESP32-S3 topology the thesis needs, described in a published framework rather
  than invented ad hoc — worth one paragraph in the thesis even if the implementation stays custom.
- **Phase E (defence) should copy the fault-arm design, including the negative controls.** The three-arm
  comparison LQR (classical baseline, required by the thesis) vs RL-trained-nominal vs RL-fault-aware
  maps directly onto document 4's CL / Fault / Fault-num structure; use document 5's severity-sweep
  protocol (a dead wheel and a 50% torque wheel are exactly its "uncontrollable" and "power-limit /
  friction" fault analogues) with a fixed seed set and ~50 trials per condition.
- **Phase E should expect the "explicit fault information" result to hold** — and test it rather than
  assume it. The evidence says a fault-blind RL policy trained under faults does not reliably beat a
  well-regularised conservative baseline, whereas a policy told *which wheel* is degraded does. For a
  3-wheel satellite there is no fourth wheel to hide behind and no shutdown option for a dead wheel, so
  "shutdown + 3-wheel control" from document 4 becomes, in this thesis, the fault case itself: the
  interesting design question is re-allocated LQR vs fault-conditioned RL, not accommodate-vs-shutdown.
- **Their shield is the precedent for the thesis's safety gate, and it is a small, honest Phase E
  deliverable.** Two hard constraint checks (battery 25%, wheel speed 70%) cut nominal failures from
  3/350 to 1/350 in a task far less safety-critical than attitude control. The ADCS analogue —
  clamp/fallback when a wheel hits its torque or speed limit or attitude error exceeds a bound — is
  cheap to implement, defensible in the thesis, and it is also exactly the mechanism AdaJEPA's paper
  lacks, which makes it the natural bridge into Phase F.
- **Phase F is genuinely unsupported by any number in this set — frame it as exploratory.** AdaJEPA
  demonstrates online adaptation for pixel-based manipulation and 2D navigation with MPC, at 0.01–0.03 s
  extra latency per replan on an H200; it contains no continuous-control rigid-body result, no actuator
  fault, no safety gate, and no embedded target. Two specific mismatches to write down: (a) its
  "dynamics shift" (mass ×0.2, damping ×20) is a parameter perturbation, whereas a dead wheel changes
  the rank of the control-allocation map — no amount of latent predictor adaptation restores lost
  authority, so Phase F must be scoped to *degraded* (50% torque) wheels or to estimation/shielding,
  not to a dead wheel; (b) its own stated limitation — benefit bounded by pretrained coverage — is
  precisely the regime a rare severe fault sits in.
- **Copy AdaJEPA's defaults verbatim as the Phase F baseline configuration** so the comparison is
  honest and cheap: adapt the last predictor block + last encoder stage, one gradient step per replan,
  replay buffer of the 5 most recent transitions, learning rate = training rate, frozen-versus-adapted
  paired evaluation over multiple seeds. With a low-dimensional attitude state the encoder can be an
  MLP rather than a ResNet, which removes the H200-class compute assumption entirely and makes Phase F
  plausible on the thesis's existing CPU budget.
- **Budget expectations to state in the roadmap:** 2–3 × 10⁷ env steps on 32 CPU cores for a
  discrete-action scheduling policy is the published norm in this literature; the thesis's 2M steps on
  8 CPUs is not comparable in training scale, and the fault papers' results are about *policy* scale,
  not controller bandwidth. Raise the step budget or state the limitation explicitly rather than
  claiming generalisation the training regime cannot support.
