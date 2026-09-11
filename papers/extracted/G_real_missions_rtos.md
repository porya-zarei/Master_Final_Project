# G — How real nanosatellite missions and real-time software papers build, simulate, verify and test ADCS

Extraction performed 2026-09-11 from six markdown conversions in `papers/markdowns/`. All values are quoted
from the sources; `not stated` marks information the documents do not give.

---

## 1. Design and Development of ITU pSAT II — On-orbit demonstration of a high-precision ADCS for nanosatellites
(Koyuncu, Cihan, Ure, Akay, Baskaya, Sarikaya, Cetin, Eren, Kaya, Karadag, Kurtulus, Kaya, Ozkol, Inalhan — ITU FAA Controls & Avionics Laboratory; conference paper, June 2011; ResearchGate upload 2015)

**Mission/platform.** ITU pSAT II, student nanosatellite of the 3U CubeSat class (modular 3U = 10×10×30 cm:
a 1U PC-104 stack carrying the bus plus a 2U experimental payload unit; internal payload volume maximised to 2U).
Structure mass < 450 g (Aluminium 7075 T6). Mass/power budget table totals **3715 g** and **30 100 mW** straight
power list (structure 560 g, solar panels 660 g, EPS 315 g, OBC 70 g, communication 160 g, **ADCS 550 g**,
camera 400 g, payload 1000 g), plus room reserved for an extra 1000 g / 5 W payload. Mission objective: design
and on-orbit demonstrate a standardised bus and a novel high-precision, fault-tolerant, reconfigurable ADCS for
pico/nano satellites (**1–10 kg**) with multi-objective applications. Status at paper time: **scheduled for launch
2012 Q3** (predecessor ITU-pSAT I launched from India 23 September 2009 and still functional).

**ADCS architecture.** Three distinct hardware layers — sensors, actuators, ADCS computer — integrated over the
**CAN bus**.
* Actuators: **4 magnetic torque generators** (one per axis + one extra on the standard z-axis for redundancy;
embedded in solar-panel PCBs as layered windings, effective area 3.31 m² from 13 windings in 10 layers, max
dipole **0.33 Am² at 3.3 V / 100 mA**) and **4 reaction wheels** (Maxon EC 20 motors in **tetrahedron formation**:
angular-momentum capability **1.05 mN·m·s**, rotor inertia **6.23e-6 kg·m²**, max torque **1 mN·m**; sized to
command **1.5 °/s** rotation per axis). An experimental in-house µPPT (micro pulse-plasma thruster) set adds
momentum-dumping capability.
* Sensors: Honeywell **HMR 3300** external magnetic-field sensor on the boom; Analog Devices **ADIS 16405**
inertial + internal magnetic-field sensor (acceleration, angular velocity, internal/external magnetic field on 3
body axes); Silonex **SLCD-61N8 photodiodes** on each panel (panel illumination → coarse **sun vector** after
filtering); **SSTL SGR-05U** 12-channel L1 C/A GPS (**10 m** position, **15 cm/s** velocity at 95 %); in-house
multifunctional **camera/star-tracker** (space-qualified Sony NEX-5, 14.2 MP) used for Earth imaging *and* star
tracking/absolute attitude determination.
* Control laws: **B-dot** for de-tumbling (magnetorquers as primary actuators; control gain C = **-4e4**; a state
variable filter with **variable cut-off frequency 2.0 Hz → 0.6 Hz** switched about **3.5 h** after deployment
produces the field derivative, because differentiating raw magnetometer data would differentiate sensor noise);
**LQR** full-state-feedback attitude tracking (reaction wheels; with the Kalman/EKF estimator the overall scheme
is an **LQG** controller). Large attitude commands are decomposed into a sequence of smaller waypoint commands
(waypoints updated when the spacecraft nears them, i.e. **event-based**, not time-based) to avoid RW saturation.
Momentum unloading/dumping onto the magnetorquers is embedded in attitude-tracking mode. Two operation modes:
(1) De-Tumbling, (2) Attitude Tracking.
* Disturbance budget for a nominal **700 km Sun-synchronous** orbit: aerodynamic drag 3.6245e-8 N·m, solar
pressure 4.9212e-9 N·m, residual magnetic 1.2800e-7 N·m, factor of safety 3 → **total 4.9295e-7 N·m**.
* Pointing requirement/achieved performance: **not stated** as an angle. The reportable quantitative results are
simulated: detumbling scenario ω_sat = [0.54 0.42 0.48] rad/s (Table 5) → **stabilised in just under five orbits**
with sensor noise and actuator limitations; attitude-tracking scenario initial Euler angles [-15 -34 43] deg and
ω = [0.021 0.024 0.018] rad/s → desired [-33 57 -45] deg, stabilised "on the order of **100 seconds**".
Control frequency is described only as "this cycle is run in **every time step**" (number not stated).

**Design and analysis tools / simulation.** MATLAB/**Simulink** implements the ADCS software model (propagation,
filtering, control) and the sensor/bus emulation; **AGI Satellite Toolkit (STK)** is inserted as the **"truth model"**
of the spacecraft and environment because its mathematical models are far more complex than the on-board
propagators and include disturbances/perturbations the on-board model does not. Rationale given explicitly: using
the on-board attitude/orbit propagator as truth model would be pointless ("indifference between estimated and
actual states other than disturbance"). On-board model fidelity: quaternion parameterisation, rigid-body dynamics
with **seven states** (4 quaternions + 3 angular rates), disturbance torques as **Gaussian white noise**, orbit
propagator integrating the orbital differential equations **including J2 perturbation** from initial conditions
supplied by a **TLE** file, and the **IGRF11** Earth magnetic field model for the field vector along the orbit.
The estimator is an **Extended Kalman Filter** (nonlinear dynamics) fusing all sensor readings with propagation
output to produce the state vector, which is fed back to update the propagators for the next cycle. Model
validation: estimator outputs compared against STK-extracted actual state.

**Verification and testing.** Two staged testbeds, **SIL then HIL**, both described as in-house.
* SIL: ADCS software (a MATLAB/Simulink model, or any external ADCS software through an interface) receives the
state update from STK over a **UDP channel**; sensor emulation applies noisy readings, magnetometer calibration
errors and gyro biases to the state vector to synthesise realistic sensor data; the ADCS software computes
commanded torques and returns them (via CAN bus in the interface rack, via UDP for outside sources) to STK, whose
spacecraft model responds; synchronisation between the two Simulink models is handled by the STK-side model; STK
opens a 3-D visualisation window (projected). STK serves as truth model and lets the team measure how well the
estimation layer performs.
* HIL: the **actual hardware** (sensor package, actuators, mission computer) is integrated with the simulation
environment. The computer rack has **two rack PCs** (plus optional monitor): the rack PCs simulate the S/C,
environment, orbit and attitude propagation; an **interface rack** running a MATLAB/Simulink model generates the
data/bus and sensor emulations; an **STK rack** generates position and magnetic-field values. Real hardware in the
loop = **sensor package + actuators + mission computer**; simulated = spacecraft dynamics, environment, orbit and
magnetic field. Two physical facilities: an **in-lab frictionless air-bearing table** to simulate spacecraft
attitude dynamics (three-axis micro-g motion) and a **Helmholtz coil system** producing a homogeneous magnetic
field on the orbit to emulate Earth's field. The spacecraft should stabilise itself on the air-bearing table using
its own reaction wheels and magnetorquers.
* Test scenarios and pass/fail evidence: (a) detumbling under sensor noise and actuator limitations (Table 5
scenario); (b) **y-axis magnetotorquer failure** during de-tumbling — angular velocity still converges to zero,
settling takes longer; (c) **one reaction wheel failure** during attitude tracking — robust performance thanks to
the tetrahedron RW arrangement's inherent redundancy. The stated purpose of the testbed is to test "a complex set
of hardware and software failure scenarios" and to compensate re-design (algorithm reliability, hardware
re-selection). On-orbit commissioning: **not stated** (not yet launched).

**On-board software.** ADCS computer embeds a **Blackfin processor**, interfaces to the dual data bus, and hosts
the magnetotorquer drivers and reaction-wheel drivers plus analog/digital data interfaces to the sensor board and
to the boom magnetometer. Bus electronics support two bus types: the **CubeSatKit™ bus** and an indigenous
**"Kiss Bus"** which **embeds CAN plus extra regulated power lines**. EPS: two regulated buses 3.3 V @ 5 A and
5 V @ 4 A, battery ~10.4 Ah / ~39 Wh; UHF AstroDev Li-1 transceiver 250 mW–4 W at 9.6 kbps; S-band downlink up
to 600 kbps / 2 W. Software architecture (explicit layered data flow): Orbit & Attitude **Propagator** →
**Estimation & Filtering** (asynchronous fusion of filtered sensor data with propagator outputs; EKF) → **Control
layer** (takes the current control mode from the mission computer, generates commanded torque under the
fault-tolerant architecture) → **Actuator Commands** (torque converted per current mode) → spacecraft; the loop
runs every time step, and filtered/fused state is fed back to the propagators. Modes: de-tumbling, attitude
tracking (see above). FDIR: a **health monitoring system** inspects the sensed and estimated state vectors to
decide whether a sensor is in error or an actuator has failed and then **reconfigures the estimation and control
layers through mode switching**. *Sensor* failure detection: bias estimation for accelerometers/gyros online by
comparing sensed vs estimated state, and identification + **isolation of a failed sensor** so its output no longer
affects the estimator. *Actuator* failure detection: **Multiple Model Switching Scheme** — state data are
generated for every possible actuator-failure scenario and compared with the current state, producing a
performance index integrated over time; the argument minimising the index indicates the failure mode (if the
nominal model minimises it, the system continues in full configuration). **Redundancy management (control
allocation layer)** then distributes the 3-D commanded torque among the redundant actuators. Sensor and actuator
detection run **independently**, so simultaneous multiple failures can be handled. Watchdog/safe-mode logic: not
stated (no watchdog, no explicit safe mode beyond mode switching).

**Real-time / timing.** No WCET analysis, no execution-time measurements, no processor clock, memory size or RTOS
are given; timing correctness is asserted only by "the cycle is run in every time step" and by the SIL/HIL
execution. Not stated.

**Fault tolerance.** Redundant actuator sets (4 MTQ / 4 RW with tetrahedron geometry), sensor-failure
identification and isolation from the estimator, actuator-failure identification by multiple-model performance
index, redundancy management/control allocation, mode switching that reconfigures both estimator and controller,
explicit design requirement of "high precision, fault tolerant and reconfigurable" ADCS, and a ground testbed
specifically built for hardware failure scenarios.

**Key quantitative results.** Mass budget total 3715 g (ADCS 550 g); power list 30.1 W; MTQ max dipole 0.33 Am²
at 3.3 V/100 mA, effective area 3.31 m² (13 windings, 10 layers); RW: 1.05 mN·m·s, 6.23e-6 kg·m², 1 mN·m, sized
for 1.5 °/s; disturbance total 4.9295e-7 N·m (FoS 3) at 700 km SSO; B-dot gain -4e4, cut-off 2.0 → 0.6 Hz
(≈3.5 h after deployment); detumbling from [0.54 0.42 0.48] rad/s in < 5 orbits; attitude tracking to
[-33 57 -45] deg in order 100 s; GPS 10 m / 15 cm/s; µPPT and 4th MTQ/RW as redundancy.

**Directly reusable for a 24U nanosat RL-ADCS thesis with an ESP32-S3 HIL stage.** The exact SIL→HIL ladder with a
high-fidelity external truth model, real computer in the loop, and explicit failure-injection scenarios
(magnetorquer loss, reaction-wheel loss) is the template to copy — plus their health-monitoring/control-allocation
separation (detect → isolate → reconfigure) and mode logic (B-dot de-tumble → LQR tracking) as the classical
baseline around an RL policy; the air-bearing + Helmholtz-coil facility is the gold HIL standard an ESP32-S3 bench
cannot reach.

---
## 2. The Design and Implementation of the UPMSAT-2 Attitude Control System
(Zamorano, Garrido (IPT), Cubas (IDR), Alonso, de la Puente — Universidad Politécnica de Madrid; 20th IFAC World Congress, Toulouse, July 2017; IFAC-PapersOnLine 50-1 (2017) 11245–11250, DOI 10.1016/j.ifacol.2017.08.1607)

**Mission/platform.** UPMSat-2 **micro-satellite** developed at IDR-UPM (with the STRAST group for on-board and
ground software). Envelope **0.50 × 0.50 × 0.60 m**, approximate mass **50 kg**. Orbit: **noon/midnight
Sun-synchronous, 700 km altitude, period 98 min, eclipse 36 min**. Mission objective: fly a set of experiments
demonstrating new technologies for space use — **there are no cameras or other payload requiring accurate attitude
control**; the driving requirements are antenna visibility from the ground station at all times (kept by
maintaining the antenna normal to the orbital plane), balancing solar radiation received by the side panels, and
keeping the temperature distribution as uniform as possible. These are met by a **slow rotation around the
tangential direction of the orbit**. Status at paper time (2017): **under development**.

**ADCS architecture.** Deliberately **pure magnetic attitude control** ("simple, reliable and cost-effective …
often used in small satellites on LEO").
* Sensors: a **redundant set of two identical fluxgate magnetometers** as the main control sensor, plus a **third
magnetometer from a different manufacturer** as an additional data source. Each magnetometer yields **three analog
voltage signals** (one per body-axis field component), acquired by the OBC through a **12-bit ADC**; conversion to
engineering units (nT) and signal filtering are done in software. Attitude determination from magnetometer data
requires an Earth-field model, and the chosen control law avoids it.
* Actuators: **three single-axis magnetorquers** generating the three components of the commanded magnetic moment;
commanded by **software-controlled PWM**, with an **H-bridge driven by two digital outputs** per magnetorquer to
allow both signs. Control torque **Tc = m × b**, i.e. always perpendicular to the local field; because the field
direction changes along a Sun-synchronous orbit, torques in any direction are possible at least on average over the
orbital period.
* Control law: the new law of **Cubas et al. (2015), m = −k(ḃ + ω_d × b)** with ω_d = [0 0 ω_r]ᵀ in the body frame.
After detumbling the angular velocity converges to ω = ω_d and the spin rotation vector aligns towards the
direction of ḃ × b, which on high-inclination Sun-synchronous orbits stays close to the orbital Z₀ axis. Three
stages: (1) detumbling — X and Y rates → 0, Z → desired value, angle between Z and Z₀ not controlled; (2)
alignment of the spin axis with Z₀; (3) nominal maintenance of ω_d and alignment. **The control law needs no
on-board attitude computation** — only magnetic measurements; attitude angles are computed on the ground from the
magnetometer (and solar-cell) data downlinked in telemetry. **No reaction wheels, thrusters, star trackers or gyros
are used.**
* Sizing/tuning from the model-in-the-loop phase: **nominal sampling period 2 s** and **gain k = 1 × 10⁸** for a
**reference angular velocity 0.1 rad/s on the Z axis**.
* Performance (simulated, Fig. 9): a **≈30 000 s (five orbits)** run with ω_ref = [0 0 0.1]ᵀ rad/s shows the three
stages: detumbling ends at about **t = 4000 s**, alignment lasts until **t = 25 000 s**, after which the Z axis is
stabilised. In-flight pointing results are reported in the companion on-orbit paper (source #3).

**Design and analysis tools / simulation.** **Simulink** is used both as design tool and as the validation
environment: a comprehensive **environment model** (variations of the Earth's magnetic field, spacecraft dynamics
and a number of disturbances) plus models of sensors and actuators; the **ACS itself is modelled in Simulink**,
with the controller model having inputs B_b_T (magnetometer readings from the Sensor task), B_dot, telecommand-
adjustable parameters (k_pb, k_pe), and outputs MT; blocks = magnetic field calculation, control law, "if fail
recalculate", limitation, discretization (PWM duty cycle), and a PD-control discretization block. Signal
conditioning and the control algorithm are Simulink models; **C code for the controller and sensor algorithms is
automatically generated with the Simulink code generator**; the rest of the on-board software is hand-written in
Ada (or generated from other model-oriented languages) and linked to the generated C through the Ada–C interface
facilities (ARM05), producing a mixed-code system. Model validation is done by the incremental MIL→PIL→HIL ladder
below; the control law itself was validated through extensive simulation (and published separately by Cubas et al.,
JGCD 2015).

**Verification and testing.** An explicit **incremental validation approach**: the ACS is first simulated together
with the environment model (MIL), then the software is run on the OBC hardware interfacing with the simulation
model (PIL), and in the final stage the full satellite hardware is tested against the environment model (HIL). The
ultimate purpose is a **Technology Readiness Level of "flight qualified" (TRL 8 for ESA)**.
* **MIL** (Fig. 8): model of the ACS + models of the space environment and spacecraft dynamics ("Environment" →
  Spacecraft / "Perturbations", Controller inside the model) used to assess the validity of the control law and the
  design parameters; this is where the 2 s period and 1e8 gain were selected. Validates functional requirements.
* **PIL**: a **software validation facility (SVF)** with an **auxiliary computer linked to the OBC by a serial
  line** runs the simulation model of the Earth's magnetic field and satellite dynamics; the control-law component
  is replaced by **the actual software running on the OBC**. Values of control variables are exchanged directly in
  engineering units between model and computer, **without** sensor/actuator models (deferred to the next step).
  This setup tests the functional behaviour of the software implementation **and its temporal behaviour** (cited:
  Garrido et al. 2012, "Analysis of WCET in an experimental satellite software development"), but it does **not**
  let TRL exceed **level 4**.
* **HIL**: models of the **actual magnetometers and magnetorquers** are added and their inputs/outputs are connected
  to the **OBC hardware by its analog and digital I/O lines**; the refined model includes the magnetometer
  **calibration data** and the **three-step control cycle**; the SVF is extended with analog and digital interfaces.
  The magnetic-field part of the model now simulates **magnetometer output voltages** fed to the computer via ADC
  lines, and the actuator model takes as input the **digital PWM signals** output by the OBC, driving the H-bridges
  of the simulated magnetorquers. Real = OBC hardware (with its ADC/digital lines); simulated = magnetometers,
  magnetorquers, environment, dynamics. Result obtained: the operation of input/output devices and of signal
  conditioning hardware/software was validated and **noise in the ADC channels was characterised, which allowed the
  engineers to improve the OBC interface hardware design**.
* **Full HIL** (not yet done in this paper) would require **real magnetometers and magnetorquers and ultimately the
  whole satellite structure** in a setup where the spacecraft attitude evolves freely — i.e. **air-bearing testbeds**
  (cited Schwartz, Peck & Hall 2003), stated as future work.
* On-orbit commissioning: not stated here (covered by source #3).

**On-board software.** OBC: **LEON3 single-core SPARC V8 processor at 20 MHz**, **4 MB SRAM** and **2 MB EEPROM**;
**64 analog input channels** and **112 digital I/O signals**, plus an **RS422 serial interface** for the radio.
Software architecture: several subsystems, one of which is the ACS subsystem; the ACS high-level design is **three
concurrent tasks** — **Sensor** (samples magnetometer analog inputs on the control-cycle schedule, converts to
engineering units with per-magnetometer off-line calibration data, stores into a shared Measurements data object),
**Controller** (implements eq. 5 and computes the control action) and **Actuator** (activates the PWM bridge per
magnetorquer) — communicating through **two shared data objects**. Development is **model-driven (MDE)**: Simulink
models → auto-generated C + hand-written Ada. Real-time profile: the whole on-board software has **hard real-time
requirements**; the ACS activities must be synchronised so the control-cycle steps execute in sequence and never
overlap (e.g. magnetometer measurements must not start before the specified delay after magnetorquer actuation
ends), and **the sampling interval must be implemented with high precision so the field derivative is accurate**.
The software uses the **restricted Ada Ravenscar tasking profile** on the **ORK+ real-time kernel** (fully supports
Ravenscar) to make real-time behaviour predictable and analysable, and an **extended form of schedulability
analysis** (Zamorano & Garrido 2015, "Schedulability analysis of PWM tasks for the UPMSat-2 ADCS") is used to verify
that the real-time behaviour complies with requirements. Fault handling in the controller model: an **"if fail
recalculate" block outputs a degraded control action when one or two magnetorquers fail**, plus saturation
limitation and PWM discretisation blocks. Watchdogs and explicit safe modes: not stated.

**Real-time / timing.** Timing correctness is established by (a) the Ravenscar profile + ORK+ kernel, (b) extended
**schedulability analysis** of the PWM/control tasks, and (c) **WCET analysis of the on-board software**, reported in
the group's papers (Garrido, Brosnan, de la Puente, Alonso & Zamorano, "Analysis of WCET in an experimental
satellite software development", 12th Int. Workshop on WCET Analysis, 2012; Garrido, Zamorano & de la Puente,
"Static analysis of WCET in a satellite software subsystem", 13th Int. Workshop on WCET, 2013). The PIL stage
explicitly allows analysing the software's temporal behaviour on the real processor. **No numerical WCET or
execution-time values are given in this paper**; the control algorithm is said to take "a negligible time" to
compute the control action, and the actuation interval is measured (200–500 ms), not computed.

**Fault tolerance.** A **redundant set of two identical fluxgate magnetometers** plus a third, different
magnetometer as an extra data source; a controller path that **recomputes a degraded control action when one or two
magnetorquers fail** (magnetic-only actuation, so a failure leaves an under-actuated system that must still be
handled); saturation limiting; hard-real-time synchronisation to prevent sensor/actuator interference.

**Key quantitative results.** 50 kg, 0.50×0.50×0.60 m, 700 km noon/midnight SSO, 98 min period, 36 min eclipse;
LEON3 @ **20 MHz**, 4 MB SRAM / 2 MB EEPROM, 64 analog in, 112 digital I/O, RS422; 12-bit ADC magnetometer
acquisition; control cycle **2 s** = 1 s sampling at **200 ms** intervals (5 readings averaged) + actuation
**200–500 ms** + idle **≥ 500 ms**; gain **k = 1e8**, ω_d = **0.1 rad/s**, detumbling ends ≈ **4000 s**, Z axis
stabilised by ≈ **25 000 s** in a 5-orbit (30000 s) simulation; PWM H-bridge drive; TRL 4 after PIL, TRL 8
("flight qualified") as target.

**Directly reusable for a 24U nanosat RL-ADCS thesis with an ESP32-S3 HIL stage.** This is the closest published
template for the thesis's HIL architecture: MIL (ACS model) → **PIL where the real OBC runs the controller against
a host-PC environment model over a serial link** → HIL where the OBC's own ADC/digital I/O lines talk to simulated
magnetometer voltages and simulated PWM-driven H-bridges — precisely how an ESP32-S3 can be made "real" while the
plant stays simulated; plus the lesson that the real-time argument rests on Ravenscar-style static tasks +
schedulability + WCET analysis, not on measured averages.

---
## 3. On-orbit performance analysis of spinning spacecraft magnetic control laws. Application to the UPMSat-2 mission
(Porras-Hermoso, Piqueras, Cubas, Roibás-Millán — IDR/UPM, Universidad Politécnica de Madrid; *Measurement* 225 (2024) 113962, DOI 10.1016/j.measurement.2023.113962; received 23 Apr 2023, accepted 28 Nov 2023, online 30 Nov 2023, CC-BY)

**Mission/platform.** UPMSat-2, **50 kg-class microsatellite**, 0.5 × 0.5 × 0.6 m, built by IDR/UPM with the
STRAST group; **technology demonstrator** of components and algorithms from IDR/UPM and partners (Tecnobit, SAFT,
Iberespacio, **Bartington**, SSBV, ZARM Technik) and an educational asset for the UPM MUSE master's programme.
**Launched September 2020**; this paper analyses the **first housekeeping data received since launch** (i.e. in-flight
validation, not simulation). Orbit: **Sun-synchronous, Local Time of Descending Node 10:30 AM, altitude at launch
518 km**, inclination 97.4° is the case analysed. Inertia (paper's Table 1): **I_zz = 1.833 kg m²**, **I_xx = 2.543
kg m²**, **I_yy = 2.525 kg m²** (almost axisymmetric about z — the minimum-inertia axis). Power: five body-mounted
Selex Galileo SPVS-5 panels with Azur Space 3G28C triple-junction cells, 18 A·h SAFT Li-ion battery, direct energy
transfer. Comms: half-duplex UHF 400/437 MHz, 1200 Bd 2-FSK and 9600 Bd GMSK, four monopole antennas, ground station
in Madrid. On-board electronic box: **FPGA-based, designed by Tecnobit and programmed by STRAST/UPM**, containing the
on-board computer, data handling, power supply control and distribution. Payload/technology demonstrators:
Bartington magnetometer, Tecnobit electronic box, **SSBV rotation wheel** (a technology demonstrator, *not* part of
the ADCS), Iberespacio thermal microswitch, SAFT battery-life experiment, IDR/UPM solar sensors and thermal control;
science objective: Earth magnetic field measurement.

**ADCS architecture.** **Purely magnetic, purely sensor-magnetometer** control — there are **no gyroscopes and no
optical attitude sensors** on board; **no reaction wheels** in the control loop.
* Sensors: **3 magnetometers (SSBV and Bartington)** for control; **6 photodiodes** (IDR/UPM solar sensors) and
solar-panel currents plus temperature sensors are used for ground-based attitude determination. SSBV magnetometer
specification: **error < 25 nT, noise < 2 nT RMS**.
* Actuators: **3 magnetorquers (ZARM Technik AG)**; linear dipole range **±15 A·m²**, linearity error **< 2 % at
  maximum linear moment**, residual dipole **≤ 0.5 % of the max linear moment**.
* Control law: the IDR/UPM "modified B-dot", **mˢ = −k(Ḃˢ + ω_dˢ × Bˢ)** with **k = 1 × 10⁸** and **ω_d = [0, 0, 0.1]
  rad/s**. Structure: the control torque is T = −k(Ḃˢ + ω_d × Bˢ) × Bˢ (the actuator cannot produce torque along B,
  so the nominal m is projected); the closed-loop dynamics reduce during the correction phase to
  I ω̇ˢ = −k Bˢ × (ωˢ − ω_dˢ) × Bˢ − ωˢ × I ωˢ, i.e. the classical B-dot form, proved **asymptotically stable to the
  desired rotation rate via Lyapunov stability criteria** (the earlier theory paper, ref. [29]). The residual term
  −k A₁ˢ(Ḃ₁ × B₁) persists once ‖ω − ω_d‖ ~ Ω_o and produces a torque τ = −kA₁ˢ[Ḃ₁ × B₁]; **the satellite tends to
  align itself with the direction of that torque**, so the z axis (minimum inertia) settles normal to the orbital
  plane. Because the gravity gradient and the rotating field make the exact equilibrium rate wobble, the achieved
  rate oscillates: for **large k the equilibrium rate oscillates between ω_d* + 1.5 Ω_o and ω_d* + 3 Ω_o**, for small
  k the oscillation is milder and the mean tends to **ω_d* + 1.7 Ω_o**; both theory and Monte Carlo show the
  **average stabilised rate is 0.1 rad/s + 1.7 Ω_o on the z axis**, with periodic variations < Ω_o. The
  simplification is justified numerically: the field direction changes at **2.16 × 10⁻³ rad/s** because of the
  satellite's motion, far above Earth rotation (**7.27 × 10⁻⁵ rad/s**). **The law needs no attitude determination
  on board**; a design rule is ‖ω_d‖ ≫ Ω_o.
* Rate limits: the **upper** target angular velocity is set by the magnetometer sampling (need the field's rate of
  change < half the sampling frequency ⇒ **f_rot < f_sampling/2** if only two consecutive measurements are used for
  the derivative); the **lower** limit comes from thermal/power studies — the rotation **can be lowered to
  5.52 × 10⁻³ rad/s** and the satellite remains operational, but staying slightly above that lower limit is advised.
  Telecommanded rate changes are possible after commissioning.
* **Control cycle (Fig. 1): period 2 s, two 1-s intervals.** First second: magnetometers sampled **every 200 ms**
  (5 readings, averaged) and the field derivative computed; "these results are fed to the control algorithm, which
  takes a **negligible time** to process the control action." Second interval: the control action is transmitted to
  the magnetorquers, taking **≈200–500 ms** (actuation/reaching the demanded moment usually **150–200 ms**, plus a
  hold period, total max **500 ms**), followed by a **rest period of at least 500 ms** so that residual magnetorquer
  moment does not corrupt the magnetometer readings. This sequencing is the practical remedy for the fact that
  **magnetometer measurements are unreliable while the magnetorquers are active**.
* Pointing requirement: satellite **z axis perpendicular to the orbital plane** and **rotation about z at 0.1 rad/s**
  ("expected performance" in Table 1).

**DESIGN AND ANALYSIS TOOLS / SIMULATION.** Two model families are used, and both are then confronted with flight
data:
* **Monte Carlo simulation of the control law** (the theory paper, ref. [29]) — for a satellite with similar
  characteristics, for different orbit inclinations and a constant gain k per run, studying the behaviour **once
  stabilised**. At the 97.4° inclination of UPMSat-2 and the flown gain, the predicted **mean deviation from the
  orbit normal is ≈2.5°** (later compared with flight: see below) and the stabilised-rate deviation "ranges from
  **1.25 to 3 times the orbital rotation rate**" (Fig. 2, whose legend uses k′ = 1 × 10⁶). The expected response at
  ω_d = 0.1 rad/s is 0.1 rad/s + 1.7 Ω_o on z with variations < Ω_o (Fig. 3).
* **ESATAN-TMS orbital thermal analysis** with a **detailed geometrical mathematical model (GMM)** (7-node reduced
  thermal model), used to predict external-surface temperatures so they can be correlated with flight data and,
  through them, with the achieved attitude/rotation (Section 4).
* **Orbit/environment reconstruction on the ground** from TLEs and the satellite clock: position, solar direction and
  Earth's magnetic field in the appropriate frames, plus modelled Sun-vector and magnetic-field histories to compare
  to the measured ones.
* Attitude determination itself is done **on the ground** with the received telemetry: TRIAD or the q-method with
  magnetometer + solar-sensor (photodiode) measurements and the modelled reference vectors, plus solar-panel
  currents and temperature measurements as additional observables.

**VERIFICATION AND TESTING (the heart of this paper — in-flight verification).** The satellite has **no rate
sensors**, it transmits in **commissioning mode only one data package per minute**, and it is designed to spin at
about **one revolution per minute** — so the expected rotation frequency and the measurement frequency are
**identical and the apparent (aliased) rotation is a stroboscopic effect**. This is documented explicitly: the
measured Sun vector's x and y components appear to change slowly while z stays almost constant, whereas the modelled
Sun vector for a **rotation at 0.102 rad/s with an initial phase of 155°** matches the measurements closely.
Consequences drawn: classical magnetometer-only determination such as the three-consecutive-measurement method is
**not suitable** (10–12 packages per pass, 4 passes/day, 10–15 min windows), solar-sensor+three-magnetometer methods
give attitude but not rate, and **MEKF / SVD+EKF / two-step EKF** approaches are ruled out because the state
dynamics are faster than the measurement rate, filter convergence cannot be guaranteed with 10–12 packages per pass
and results depend heavily on initial conditions. The verification strategy therefore combines:
1. **Magnetometer-based attitude reconstruction on the ground** with the modelled field, to check the z-axis
   orientation against the orbit normal.
2. **Solar-vector measurements from the 6 IDR/UPM photodiodes plus solar-panel currents**, compared against the
   modelled Sun-vector evolution (including the stroboscopic-effect hypothesis test above).
3. **Transient thermal analysis of the satellite's external temperatures** as an independent rotation-rate sensor:
   the rotation modifies the temperature differences between surfaces, so a transient thermal model fitted to
   flight temperature data recovers the true spin rate; housekeeping temperatures (with the ESATAN-TMS model) are
   used for this, and the paper uses **4004 temperature data points** in the fit. (Literature backing cited:
   temperature/absorbed-heat-flux attitude determination refs. [46–50].)
4. Also used as cross-checks: solar-panel currents and the fact that the IDR/UPM solar sensors are themselves a
   payload whose in-flight performance verification depends on the magnetometer result.
* On-orbit commissioning / test procedure outcome: the combined evidence is used to confirm that the satellite
  "**remains at its design attitude and angular velocity**".
* Ground test facilities (air-bearing table, thermal vacuum, HIL): **not stated in this paper** — the control law's
  design/validation process is covered in the companion papers (sources #2 for the software/HIL ladder; ref. [33/34]
  for the implementation).

**ON-BOARD SOFTWARE.** Not the subject of this paper. What is stated: the **electronic box is FPGA-based (Tecnobit
hardware, STRAST-programmed)** and contains the OBC, data handling and power control; the magnetorquer command,
magnetometer sampling and the 2-s/200-ms control cycle above are implemented in that on-board software; the
magnetometer derivative is computed **on board** but **is neither stored nor transmitted**, so rate reconstruction
must be done on the ground (this is an explicit lesson on telemetry design). RTOS, watchdogs, FDIR and processor
clock: **not stated**. Interfaces: UHF radio links at 1200 Bd (2-FSK) / 9600 Bd (GMSK); internal ADC/digital lines
for the magnetometers and magnetorquers (from source #2: LEON3 @ 20 MHz, 4 MB SRAM, 2 MB EEPROM, 12-bit ADC,
PWM/H-bridge drive).

**REAL-TIME / TIMING.** No WCET analysis in this paper; timing enters through (a) the fixed **2 s control cycle**
with its 1 s/1 s split, 200 ms sampling and ≥500 ms guard interval, (b) the **Nyquist constraint tying the
magnetometer sampling rate to the maximum controllable spin rate** (f_rot < f_sampling/2), and (c) the one-sample-
per-minute telemetry that aliases the 1 rev/min rotation. Timing correctness is asserted operationally (the cycle is
fixed and the control computation is "negligible"), not by static analysis.

**Fault tolerance.** The paper argues the *rationale* rather than a scheme: purely magnetic actuators have "**lack of
catastrophic failure modes**", very long operational life, and magnetic control is normally relegated to detumbling,
wheel desaturation or **safe modes** because of its "simplicity and low failure risks". The system also carries 3
magnetometers (SSBV + Bartington, i.e. mixed suppliers giving redundancy/diversity) and 6 photodiodes. Explicit
FDIR logic, safing and redundancy management: **not stated**. Fault handling in the controller (one or two
magnetorquers lost → degraded action) is described in source #2.

**Key quantitative results (in flight).** 50 kg, 0.5 × 0.5 × 0.6 m, SSO 10:30 LTDN, 518 km at launch, i = 97.4°;
I = (2.543, 2.525, 1.833) kg m²; launch September 2020; gain k = **1 × 10⁸**, ω_d = **0.1 rad/s**, control cycle
**2 s** (1 s sampling at 200 ms ×5, actuation 200–500 ms, idle ≥500 ms); magnetorquer ±15 A·m², linearity <2 %,
residual ≤0.5 %; magnetometer error <25 nT, noise <2 nT RMS; Monte-Carlo prediction **≈2.5° mean deviation** from
the orbit normal with 1.25–3 Ω_o rate deviation; measured Sun-vector behaviour reproduced by a **0.102 rad/s**
rotation with **155° initial phase**; mean Sun-vector deviation from the 6-photodiode measurement **2.2°** vs
**2.5°** predicted; average z-axis illumination/incident angle between the Sun vector and the z axis **112.9° ±
2.5°**; the theoretical spin-rate band for the observed temperature behaviour **0.1017–0.1033 rad/s** (mean
0.1025 rad/s); **4004 temperature data points** fitted; thermal-model vs flight discrepancy **±3 °C**; local minima
of the thermal cost function at **0.052, 0.10, 0.21 rad/s** with the global minimum near **1 rpm**; the stroboscopic
aliasing follows directly from the 1 rev/min spin vs 1 sample/min; maximum controllable spin f_rot < f_sampling/2
and minimum operational spin **5.52 × 10⁻³ rad/s**.

**Directly reusable for a 24U nanosat RL-ADCS thesis with an ESP32-S3 HIL stage.** The model of a **credible
in-flight performance claim without a star tracker or rate gyro**: reconstruct attitude from the sensors you have,
cross-check with an independent physical channel (here transient thermal analysis of 4004 points), and state the
achieved numbers (2.2° mean deviation vs 2.5° predicted, 112.9° ± 2.5° illumination angle, spin 0.1025 rad/s) —
this is the standard against which the thesis's "achieved pointing after fault" must be reported, and the
2 s-cycle/200 ms-sampling timing budget with a guard interval is a realistic skeleton for the ESP32-S3 task loop.

---
### 3b. Additional method/results detail (same paper)

**Ground-based attitude and rate reconstruction (Section 3).** Because the satellite carries no rate sensors and the
telemetry rate (one package per minute, 10–12 packages per pass, 4 passes/day, 10–15 min windows) is comparable to
the motion (≈1 rev/min), the paper develops an explicit **stroboscopic-effect correction**. With sampling period T_s
and motion period T_c, T_s = k_sc·T_c and r = 1 − k_sc = (T_c − T_s)/T_c, a sampled sinusoidal component y_i =
sin(ω_c t_i + φ₀) is observed as **y_i = −sin(2π r i)**: the apparent motion is reversed and has apparent period
T_ap = (1/r)·T_s and apparent frequency f_ap = (1−r)/(k_sc T_c)·f_c, giving the recovery relation
**ω_c = ω_s − ω_ap (Eq. 26)** — the true rate is the sampling rate minus the apparent rate.
The true angular velocity is then obtained from the magnetometers alone via the Coriolis theorem,
**Ḃ₁ˢ = Ḃˢ − ωˢ × Bˢ**, using the measured field Bˢ and the geomagnetic reference model B₁ˢ (plus the finite-difference
expressions for Ḃ), solved with the **pseudo-inverse W = (B^×ᵀ B^×)⁻¹ B^×ᵀ** because B^× is singular. Two
consecutive measurements give an **ill-conditioned** solution; **three consecutive measurements** are recommended.
Caveat stated: when the sampling frequency is below the motion frequency only the *apparent* rate is recovered and
the stroboscopic correction must be applied. Where the sampling frequency is at least twice the motion frequency the
equations give the true rate directly.

**Rate results.** The mean angular velocity on **x and y is ≈ 0** (residual dominated by instrument noise and process
errors, only illuminated passes with >5 consecutive data points used). The **z-axis** mean angular velocity per
pass, after the stroboscopic correction, **approximates the 0.1 rad/s target**; the theoretical range at ω_d = 0.1
rad/s and k = 1 × 10⁸ is **0.1017–0.1033 rad/s**; **most results fall inside that range and the maximum deviations
are smaller than 3 % from the bounds**. Independent upper bound argued from the averaging itself: the magnetometer
reading is the average of **5 samples 200 ms apart**; at **1 rev/s** the five-sample average would be zero (random
values from noise) and at **30 rpm** the average is **90° out of phase** with the field, so **1 rev/s (6.283 rad/s)
is taken as a reasonable upper limit** (also the Nyquist-type constraint f_rot < f_sampling/2).

**Thermal model and its use as an independent rate sensor.** The **detailed GMM built in ESATAN-TMS** (Fig. 7) was
reduced to a **7-node model** — six nodes for the six panels plus one internal node (trays, payloads) conductively
coupled to the panels — with thermal capacities, conductive couplings and panel emissivity/absorptivity as
parameters. Most detailed-model parameters had already been **correlated through thermal-vacuum testing**, so they
carry low uncertainty; the exception is the **solar absorptivity of the external surfaces, which could not be
measured (no equipment)** and was therefore bounded between upper and lower limits from the known materials and
surface treatments. Fine-tuning uses **flight data from September 2020** at the IDR/UPM ground station. Two
correlation strategies: (i) case-by-case with three free parameters (initial condition, spin rate and thermal
parameters) — **computationally expensive**, used only to **reject an apparent rate of 0.0031 rad/s**, whose
correlated thermal capacity/absorptivity/emissivity fall outside physically meaningful ranges; (ii) the **infinite
spin-rate assumption** (no initial-condition effect, rate known), fit the thermal parameters to the mean
temperature trend, then **optimise the spin rate**, justified because the spin-induced oscillation about the global
trend is only **≈1 °C or less**. With the high-spin model the **maximum discrepancy between flight data and model is
≈±3 °C**, attributed mainly to per-orbit initial-temperature differences (small operational differences such as
solar-panel operating point, electronics and heater dissipation), not to the spin. Per-pass optimisation then varies
the **initial temperature (mean ± 5 °C) and the initial rotation angle (0–2π)** to minimise the residual sum of
squares using a **non-linear least-squares quasi-Newton algorithm**; the deviation metric is ε_T = sqrt(ΣΣ(T_m,ij −
T_data,ij)²/(N−1)) over **N = 4004 temperature data points** across all passes. Result (Fig. 10/11): high rates
(≥0.2 rad/s) cannot reproduce the observed small oscillations and low rates (≤0.03 rad/s) oscillate too strongly;
ε_T decreases with spin rate and shows **three local minima at 0.052, 0.10 and 0.21 rad/s** (interpreted as
half/double spin artefacts), with the **global minimum near 1 rpm ≈ 0.1 rad/s** — the most plausible in-flight rate,
consistent with the stroboscopic magnetometer result. Rates **below 0.052 rad/s are ruled out**.

**Pointing result (Section 4.2).** In the 10:30 SSO the Sun incidence angle on the orbit normal stays nearly
constant — **mean 110.7° over September** — so the Sun incidence angle with respect to the −z face is used as the
pointing metric. The histogram of the **z-axis illumination angle is fitted by a normal distribution with mean
112.9° and standard deviation 2.5°**; the theoretical mean for perfect z-to-orbit-normal alignment is shown as the
reference line, and the **average difference between the orbit-normal direction and the actual z-axis pointing
direction is 2.2°**, in good agreement with the ≈2.5° predicted for this inclination. Flight data used: pass of
**4 September 2020** shown in Fig. 4, i.e. within weeks of the September 2020 launch. The paper's conclusion: after
correcting the stroboscopic effect the magnetometer data agree with expectations; the thermal analysis rules out
rates below 0.052 rad/s and favours ≈0.1 rad/s; the control law keeps the z-axis aligned with the orbit normal to
within a **mean 2.2°** deviation, consistent with theory. Acknowledgment of funding: Comunidad de Madrid "Sinérgicos
2020" project OAPES and the **EU Horizon 2020 IOD/IOV programme, which funded the UPMSat-2 launch**.

---
## 4. Attitude Determination and Control of Thinsat System Using Adaptive Control Technique
(Ukonu Ihuoma Christian, Eneh Innocent Ifeanyichukwu, Ene Princewill Chigozie — Electrical & Electronics Eng., Enugu
State University of Science and Technology (ESUT), Enugu, Nigeria; *Engineering Science* 2023, 8(2): 14–22,
DOI 10.11648/j.es.20230802.11, sciencepublishinggroup.com; received 20 March 2023, accepted 20 April 2023,
published 10 June 2023)

**Mission/platform.** The stated subject is a **ThinSat ("thinsat") system** — a thin, very small satellite class —
but **no Thinsat mission, mass, orbit or launch is characterised anywhere in the paper**. The work is a
**simulation study**: the attitude data used to train the controller is taken from **NigeriaSat-2**, Nigeria's Earth
observation satellite (launched **August 2011**, 2.5 m panchromatic / 5 m multispectral, 20 × 20 km swath; the paper
also mentions NigeriaSat-X and NigComSat-1R, Dec 2011). Table 1 ("NigeriaSat-2 Simulation parameters", values as
printed, several OCR-corrupted): **launch mass 1960 kg**, **dry mass 968.5 kg**, **2.6 m × 1.5 m × 1.5 m**, power
**1164 W with two 18 A·h Ni-Cd batteries**, propulsion **440 N liquid apogee motor + twelve 22 N thrusters (MMH fuel,
MON-3 oxidiser)**, antenna sizes **0.9 m and 1.0 m**, **mission design life 7.7 years**, distance **35 786 km**,
uplink **0.1 ± 402.75**, downlink **0.1 ± 4506.05** (units lost in conversion). Note the inconsistency: **35 786 km is
a geostationary altitude, whereas the real NigeriaSat-2 flies in LEO (~700 km)** — the model in this paper is
therefore a large GEO-class spacecraft, not a nanosatellite, and no launch/status is claimed for the adaptive ADCS
itself.

**ADCS architecture.** Described at block-diagram level only (Fig. 2): **absolute and relative sensors** collect
spacecraft attitude data — speed, Sun position, temperature, position and orientation — feeding the **TRIAD
(Tri-Axial Attitude Determination)** algorithm, which is stated to accept only **two vector observations per
instant**, the first assumed more accurate than the second; TRIAD builds the orthonormal triads from b₁/B₁ and
b₂/B₂ and the attitude matrix as the product of the two triad matrices (Eqs. 13–16). The determined attitude goes
to the **control algorithm**, which adjusts the actuator position "to reject disturbance". Actuators are implied
rather than specified: **reaction/momentum wheels** (the paper discusses "the impact of nonlinear torque on the
momentum of the wheels") and **electromagnetic torque from the inner actuators**, with thrusters available in the
NigeriaSat-2 model. Plant model: Euler's rigid-body equation with constant inertia,
**T = −S(ω)Jω + τ_act + τ_dist**, plus the **quaternion kinematic equation** q̇ = ½(q× + q₀I)ω; error dynamics
formulated on the quaternion and angular-velocity error relative to the orbit frame (Eqs. 7–12), with the control
objective (q_e, ω_e) → (0, 0). Control law: **adaptive control built from a Multi-Layer Neural Network (MLNN)** with
**tansig activation function**, weights/biases and a training algorithm, trained by **back-propagation**, with the
pseudocode: load training set → split train/test → configure MLNN → activate → select training algorithm → set epoch
parameters → set metrics (MSE and regression) → train → if MSE criterion true generate the ACS, else back-propagate
and adjust neurons. Classical baselines mentioned as prior art: **LQR, PID** and a pitch–yaw adjustment controller.
**Control frequency, pointing requirement in degrees/arcsec: not stated.** Achieved "performance" is simulation-only
(see numbers below).

**DESIGN AND ANALYSIS TOOLS / SIMULATION.** Explicit: **MATLAB/Simulink** — "The adaptive ADCS was implemented with
Simulink… achieved with the **aerospace toolbox, control system toolbox and neural network toolbox**"; the **neural
network toolbox** trains the collected data and generates the ACS block, the **control system toolbox** builds that
Simulink block, and the **aerospace toolbox** implements the **NigeriaSat-2 6-DOF model** whose dynamics are then
controlled by the adaptive ACS (Table 1 gives the simulation parameters). The paper also refers to an earlier
MATLAB-based ADCS developed "for experimental tests and verification of ADCS" and to implementation of the system
"with a high-level programming language … integrated into the testbed/test facility for optimization". **Model
fidelity:** rigid-body Euler + quaternion, environmental/perturbation torque lumped as a dynamic gravity/torque
term; **no orbit propagator, no magnetic-field model, no sensor noise model and no actuator dynamics are
quantified**; validation of the trained controller is by **MSE and regression on the training/test/validation
sets**, not by physical accuracy metrics. The abstract states the average **MSE = 0.0045394** and **regression =
0.97271**, while Section 5.1 states "the MSE recorded is **0.056845**" and "the average R recorded from the
training, test and validation set is **0.99999**" — the paper is internally inconsistent and both pairs are
reported here as printed. Figure 7 caption/values aside, the only fidelity claim is that the network "correctly
learns the spacecraft data collected and was able to detect changes in the angular velocity".

**VERIFICATION AND TESTING.** A **hardware test facility is described (Fig. 1, "Courtesy: NIGCOMSTAT")**, explicitly
as the environment in which the ADCS is to be integrated and optimised, comprising:
* a **Helmholtz cage** providing a **three-axis dynamic magnetic field** that **cancels the Earth's field** and
  creates a geomagnetic-field environment "similar to space";
* **ADCS hardware = the satellite control system developed with a PID control system**, used to control the
  attitude parameters toward the desired orientation (i.e. **the facility's reference controller is PID**);
* **space mission control software** that monitors the dynamic behaviour of the satellite and reports to a
  **monitoring laptop**;
* a **motion tracking system = a horn antenna** "specialized in tracking the torque and angular velocity of a
  satellite";
* a **sun simulator** providing up to **50 000 lux**, adjustable from **30 % to 100 %**;
* an **air-bearing platform** used "to introduce nonlinearity in the environment and then test the controlling
  attitude of the satellite system".
**What is real vs simulated:** the facility hardware (cage, air bearing, sun simulator, PID ADCS unit, mission
control software) is real, but **the adaptive controller itself is never reported as being run in this facility** —
the results presented (Figs. 6–9) are the **Simulink/MATLAB simulation** results; HIL of the adaptive controller,
unit tests, thermal/vacuum tests, and on-orbit commissioning are **not stated**. **Test procedures and pass/fail
criteria** are reducible to the training metrics (MSE small, R ≈ 1) and a comparative step response against PID;
no formal procedure or acceptance threshold is given. This paper is therefore useful as a **cautionary example**:
the facility inventory is realistic, the verification chain is not (no HIL run, no numerical fidelity bound, no
sensor/actuator characterisation).

**ON-BOARD SOFTWARE.** **Not stated** — no processor/MCU model, no clock frequency, no memory, no RTOS or bare-metal
description, no scheduling, no I²C/SPI/CAN/UART interfaces, no FDIR, no watchdogs and no mode/safe-mode logic. The
only software statements are that the controller was implemented in **MATLAB/Simulink (with the three toolboxes
above)** and again "with a high-level programming language" and integrated into the test facility.

**REAL-TIME / TIMING.** No WCET analysis, no static timing analysis, no RTOS. The single timing claim is
comparative and simulation-derived: "the total time of the attitude determination and control of the spacecraft is
**111.24 ms** as against **465 ms** with PID which gives **76 % reduction in decision time**". Because no processor,
clock or software architecture is specified, this figure **cannot be treated as an execution-time or real-time
evidence** — it is the only number in the paper that invites the "real-time feasibility" question, and it does not
answer it (the thesis should not cite it as proof that an NN controller meets a control period; only WCET/measured
execution on a defined MCU does that).

**Fault tolerance.** **Not stated.** No fault detection, isolation or recovery, no redundancy management, no
degraded modes. The motivation is disturbance rejection (dynamic electromagnetic torque on the wheels affecting
angular velocity and orientation), not fault tolerance.

**Key quantitative results (simulation).** NigeriaSat-2 model: 1960 kg launch / 968.5 kg dry, 2.6×1.5×1.5 m,
1164 W, two 18 A·h Ni-Cd, 440 N LAM + 12 × 22 N thrusters, 7.7-year design life, 35 786 km (as printed); controller:
MLNN with tansig activation, back-propagation training; **MSE 0.0045394 (abstract) / 0.056845 (Section 5.1)**;
**regression 0.97271 (abstract) / R ≈ 0.99999 (Section 5.1)**; **ADCS decision time 111.24 ms vs PID 465 ms = 76 %
reduction**; **pitch angular-velocity error 13.46 → 9.55 (as printed, units garbled: "mm") = 29 % improvement**;
with the adaptive controller the satellite "maintained stable orientation at **0.08 orbit**" while the wheel
momentum was affected by nonlinear torque and the orientation was "controlled at **three orbits**"; sun simulator
**50 000 lux, 30–100 %**; Helmholtz cage three-axis field, air-bearing platform for nonlinearity.

**Directly reusable for a 24U nanosat RL-ADCS thesis with an ESP32-S3 HIL stage.** Two things transfer directly:
(i) the **structure of the RL-vs-classical comparison** — train an ML controller on flight-like dynamics data,
report **MSE/regression** for the learning and **step-response/decision-time and error-reduction percentages**
against the classical baseline (here PID, for the thesis LQR) — and (ii) the **inventory of a real lab test
facility** (Helmholtz cage with 3-axis field cancellation, air-bearing platform, sun simulator 50 000 lux, motion
tracking by antenna, mission-control monitoring software) which is what a university ADCS laboratory actually
contains. It is equally reusable as a **negative example**: a simulation-only ML controller with no processor, no
WCET, no HIL run and no fault handling is exactly the gap that a "From Simulation to Hardware-in-the-Loop"
thesis is expected to close.

---
## 5. Model-Driven Design of Real-Time Software for an Experimental Satellite
(Juan A. de la Puente, Jorge Garrido, Juan Zamorano, Alejandro Alonso — Universidad Politécnica de Madrid (UPM), `str@dit.upm.es`; 19th IFAC World Congress, Cape Town, 24–29 Aug 2014, pp. 1592–1598; work supported by Spanish R&D&I plan project HI-PARTES, TIN2011-28567-C03-01)

**Mission/platform.** UPMSat-2 **micro-satellite, mass ≈50 kg, cubic envelope 0.5 × 0.5 × 0.6 m**, **polar Sun-synchronous
orbit at 600 km altitude, period ≈97 min** (as stated in this 2014 paper; the later papers in this collection give
700 km/98 min and 518 km at launch — the orbit was still being finalised), **launch planned 2015**, expected life
**two years**. Mission aim: technology demonstrator + educational platform for university researchers and partner
companies; payload = experiments proposed by research groups and industry, including sensors and actuators to be
tested in the space environment. Power from solar panels covering **five sides**; two UHF **400 MHz** radio links
with **maximum data transfer rate 9600 b/s**; a single **on-board computer (OBC)** performs all data handling,
supervision and control of the platform and experiments. Status at paper time: software system and software
validation facility "scheduled to be completed by mid 2014"; ground-station software planned afterwards.

**ADCS architecture.** Attitude = orientation between a body reference frame and an orbit reference frame,
represented as a rotation matrix or (preferred) the **quaternion** between the two frames (de Ruiter et al. 2012).
The ACS must keep **the Z_B axis normal to the orbit so the radio antenna is always visible from Earth**, and the
body must **rotate slowly about that axis to provide spin stabilisation**. The control algorithm is "based on
estimates of the **Earth magnetic field vector and its derivative**" (Farrahi, Cubas & Sanz 2013, IDR technical
report) and **computes actuation signals fed to three magnetorquers**. Sensors in the loop: **magnetic sensors**
(magnetometers) only; "other configurations are included as experiments". So: **actuators = 3 magnetorquers,
sensors = magnetometers, no reaction wheels in the baseline**. Control frequency: **the attitude controller is a
periodic thread with Period = 1000 ms and Deadline = 100 ms** (AADL listing 3) — this is the only period stated and
it is a *design* attribute of the real-time thread, superposed on the 2 s magnetometer/magnetorquer sequence of the
later flight papers. Pointing requirement: **Z_B normal to the orbit** (no numerical degree/arcsec requirement in
this paper); achieved in-flight performance: not stated (pre-launch).

**DESIGN AND ANALYSIS TOOLS / SIMULATION (this is the paper's core).** A full **model-driven engineering (MDE)
chain** with an explicit model ladder and named tools:
* **PIM (platform-independent model)**: *data view* in **ASN.1** (ITU-T X.680–683), *functional view* in
  **Simulink** (continuous-time functions such as attitude control) and **SDL** (ITU-T Z.100; state-driven
  components such as the payload manager and the TM/TC controller), *interface view* in **AADL** (SAE AS5506B).
  The interface view shows all OBC software components as AADL subsystems with data-flow interfaces and includes an
  extra **orchestrator** component that coordinates the satellite's operating modes.
* **Simulink top-level model of the attitude dynamics (Fig. 6)**: the model includes **the different torques that
  affect attitude — the Earth's magnetic field, the controlling torque and some disturbances — input to a model of
  the spacecraft rotational dynamics**, which outputs **attitude (both in quaternion and rotation-matrix forms) and
  the angular speed vector**; the block labelled **controller** contains the control algorithm with the sensors and
  actuators **also modelled**; "several kinds of control laws and different parameter values have been used in order
  to select the best control performance with the available sensors and actuators" — i.e. the Simulink model is the
  control-design and parameter-tuning environment.
* **PSM (platform-specific model)** in **AADL**: *deployment view* (processors, memory, interconnect buses and
  networks, operating systems; trivial here because the OBC has only a processor board) and *concurrency view*
  (concurrent tasks with real-time attributes, shared data objects), generated from the interface + deployment
  views.
* **Tool chain: TASTE** (Perrotin et al. 2012) — graphical and textual **AADL and ASN.1 editors**, automatic
  building of the concurrency view and **automatic Ada code generation**. ASN.1 types are given **ACN encoding
  rules**, e.g. `MagnetometerType[size32, encoding IEEE754-1985-32]`; the ADC data model defines
  `MagnetometerType ::= REAL(0.0..5.0)` and `MagnetorquerAxisType ::= SEQUENCE { x Boolean, y Boolean, z Boolean }`
  — i.e. **three analogue magnetometer channels 0–5 V and three on/off magnetorquer commands**.
* **Model validation**: "Models are validated through simulation, when possible, or by inspection when not"; the
  attitude-controller design and its parameters were validated using the Simulink model; **static analysis tools**
  validate timing properties (see below).

**VERIFICATION AND TESTING.** Explicitly structured by model level:
* **Functional design** → validated by **Simulink simulation** (attitude controller) and by inspection otherwise.
* **Timing** → **MAST** (Modeling and Analysis Suite for Real-Time applications; González Harbour et al. 2001) for
  **real-time (schedulability/response-time) analysis** plus **RapiTime** (Bernat, Burns & Newby 2005, probabilistic
  timing analysis using copulas) for **execution-time analysis**; **both integrated with the TASTE concurrency
  view** (Pérez et al. 2008) and together they "provide **accurate estimates of worst-case response times of every
  real-time task**, which can be used to validate real-time requirements". So the WCET/response-time validation
  chain is: executable code → RapiTime measures/derives execution times → MAST response-time analysis → compare with
  the AADL deadlines.
* **Implementation code** → tested on an **engineering version of the computer board, built with commercial hardware
  that is not protected against radiation, in order to reduce costs** (the flight board is a radiation-hardened
  FPGA).
* **Dynamic HIL facility (Fig. 8, "ADCS test configuration")**: "the spacecraft dynamics and its environment are
  **simulated on the simulation computer**, while the **control software runs on the engineering board**". The
  rationale is explicit: "**Embedded systems should be validated with respect to their real physical environment.
  However, the environment of space systems is not available for testing, and therefore it has to be simulated.**"
  The HIL configuration "has also been used to **estimate execution-time data that are fed back to the
  response-time analysis tools**" (Garrido et al. 2012) — i.e. **measurement on the board feeds the WCET/response-time
  model**, a closed loop between measurement and static analysis.
* **Planned next steps**: testing with **real sensors and actuators** and with **radio communication links instead of
  the serial line** currently connecting the satellite board to the software validation facility.
* **What is real vs simulated in HIL**: real = the OBC engineering board and the on-board control software; simulated
  = spacecraft rotational dynamics, environment (magnetic field, disturbances); connection = serial line (later radio).
  Thermal/vacuum and on-orbit commissioning: not stated (pre-launch paper).

**ON-BOARD SOFTWARE.** OBC = **LEON3 SPARC V8 32-bit processor implemented on a radiation-hardened FPGA
(system-on-chip) with 4 MB SRAM, 1 MB EEPROM, timers, analog inputs and digital I/O**. Note the EEPROM figure is
**1 MB here**, while the 2017 ACS paper (source #2) says **2 MB EEPROM** — an evolution between the papers.
Software functions: **ADC** (attitude determination and control), **platform monitoring/housekeeping** (periodic
temperature and voltage measurement; **deviations from nominal ranges may cause switching to an error mode and
sending error messages to the ground station** — this is the paper's main FDIR/mode statement),
**OBDH** (execution of telecommands from the ground, generation of telemetry), **experiment management**; plus the
**orchestrator** coordinating operating modes.
* **Language and runtime**: **Ada 2005 (ISO/IEC 8652:1995 with TC1 and Amendment 1) with the Ravenscar profile
  restrictions for tasking**, on a dedicated runtime based on the **PolyORB-HI middleware** and the **GNAT/ORK+
  kernel for bare LEON computers** (de la Puente et al. 2008, "The ASSERT Virtual Machine: a predictable platform
  for real-time systems").
* **Scheduling / concurrency**: the concurrency view is a set of **threads and shared data objects**; an extract
  shows `THREAD ControllerCyclicFV` with `DispatchProtocol => Periodic`, **`Period => 1000 ms`, `Deadline => 100 ms`**,
  features `Magnetometer: REQUIRES DATA ACCESS` and `Magnetorquer: REQUIRES DATA ACCESS`, and calls
  `getMagnetometerValues` / `setMagnetorquers`. Task and shared-data **skeletons are generated from the concurrency
  view by the TASTE code generator**, while functional code comes from Simulink code generation; the Ada body shows
  `pragma Import(C, Control, "Controller")` and `pragma Import(C, getMagnetometerValues, ...)`, with
  `executeControl` declaring aliased ASN.1-typed Magnetometers/Magnetorquers, exporting them to C (`pragma
  Export(C, Magnetometers, "controlU")`), calling `Control`, then `setMagnetorquers` — i.e. **Ada (Ravenscar tasks)
  hosting auto-generated C control code** with an ASN.1-defined interface.
* Interfaces modelled: analog inputs and digital I/O of the SoC to the sensors/actuators; UHF 400 MHz radio links
  (9600 b/s) to the ground; serial line to the HIL facility during testing. Watchdogs: not stated. Safe modes: the
  **error mode** entered on out-of-range housekeeping values, plus the orchestrator's operating-mode coordination.

**REAL-TIME / TIMING (the most transferable part of this paper).** Timing correctness is established by
**(1) modelling real-time attributes in AADL** (periodic threads with periods and deadlines — the controller is
1000 ms/100 ms), **(2) worst-case response-time analysis with MAST**, **(3) execution-time analysis with RapiTime**,
both integrated with the TASTE concurrency view, and **(4) feeding measured execution times from the HIL engineering
board back into the response-time tools** (Garrido et al. 2012, "Analysis of WCET in an experimental satellite
software development", 12th Int. Workshop on WCET Analysis, OASIcs vol. 23, pp. 81–90). The claim is that these
tools "together provide accurate estimates of **worst-case response times of every real-time task**". Measured
execution times themselves are **not tabulated** in this paper. (Note the naming: RapiTime is a
*measurement/hybrid* execution-time analysis tool, referenced here through Bernat, Burns & Newby's **probabilistic
timing analysis** paper — relevant to the thesis's discussion of how measurement complements static WCET analysis.)

**Fault tolerance.** Two mechanisms only: (a) **platform monitoring with error mode** — out-of-nominal temperatures
and voltages detected by periodic housekeeping cause a **switch to an error mode and error messages to the ground**;
(b) the **engineering board is explicitly non-radiation-hardened** for cost reasons while the flight board is a
radiation-hardened FPGA SoC (i.e. radiation tolerance is handled in hardware, not software). No redundancy
management, no sensor/actuator fault detection, no reconfiguration logic is described here (that appears in the
complementary papers: the ACS paper's "if fail recalculate" block and the 2011 ITU paper's multiple-model actuator
FDIR).

**Key quantitative results.** 50 kg; 0.5 × 0.5 × 0.6 m; 600 km polar SSO, ~97 min period, 2-year design life,
launch planned 2015; LEON3 SPARC V8 in radiation-hardened FPGA SoC with **4 MB SRAM, 1 MB EEPROM**, timers, analog
inputs and digital I/O; **three magnetorquers** and **three magnetometer channels 0–5 V** (ASN.1 `REAL(0.0..5.0)`,
ACN `IEEE754-1985-32`) with Boolean per-axis magnetorquer commands; **controller thread period 1000 ms, deadline
100 ms**; UHF 400 MHz, **9600 b/s**; the attitude Simulink model outputs quaternion + rotation matrix + angular
speed from Earth-field, control and disturbance torques; validation = Simulink + MAST + RapiTime + HIL on an
engineering board.

**Directly reusable for a 24U nanosat RL-ADCS thesis with an ESP32-S3 HIL stage.** This is the single best
architectural template for the thesis's on-board software chapter: **a periodic control thread with an explicit
period and deadline (1000 ms / 100 ms), a Ravenscar-style static task set on a small kernel, auto-generated code
from the design model, and an HIL where "the plant runs on the simulation computer while the control software runs
on the real board"** — exactly the ESP32-S3 arrangement — plus the crucial argument technique that **measured
execution times from the HIL board are fed back into the worst-case response-time analysis** so that real-time
feasibility is *claimed against a WCET/response-time bound*, not against an average. The TASTE/ASN.1/AADL tool
chain is heavier than a thesis needs, but the task-per-period + shared-data-object + explicit-deadline pattern is
directly portable (e.g. an ESP32-S3 FreeRTOS task with a fixed period, deadline and instrumented worst-case
timing).

---
## 6. OTAWA: An Open Toolbox for Adaptive WCET Analysis
(Clément Ballabriga, Hugues Cassé, Christine Rochange, Pascal Sainrat — Institut de Recherche en Informatique de Toulouse (IRIT), University of Toulouse, France; **SEUS 2010**, LNCS 6399, pp. 35–46, © IFIP 2010)

**Mission/platform.** *Not applicable* — OTAWA is **not a satellite paper**; it is the **WCET-analysis tooling
reference** for this collection. It must be read for what it can and cannot do when a thesis claims real-time
feasibility of an on-board controller.

**What it analyses (the object of study).** The **Worst-Case Execution Time (WCET) of a task**, motivated by the
first sentence: "The analysis of worst-case execution times has become mandatory in the design of hard real-time
systems: it is absolutely necessary to know an upper bound of the execution time of each task to determine a task
schedule that insures that deadlines will all be met." The paper's framing of WCET analysis has **three steps**:
**(a) flow analysis** — identifying (in)feasible paths and bounding loops; **(b) low-level analysis** — determining
the global effects of the target architecture on execution times and deriving the worst-case execution times of
code snippets; **(c) combination** of flow and low-level results into the overall WCET. It also explains why pure
measurement is insufficient: execution time depends on input data and initial hardware state, and (a) covering all
execution paths is hard (especially with floating-point inputs), (b) the number of paths is too large for
exhaustive measurement, (c) the hardware state cannot always be initialised as required — hence **decomposition
into code snippets (generally basic blocks)** with per-unit measurement/estimation and recomposition. Method
families it distinguishes: measurement-based timing (on the real target hardware or on a simulator) vs **hardware
model-based computation**; and, for combining unit times, AST/analytical-formula approaches (poor fit with
compiler-optimised code) vs **Control Flow Graph** approaches using path-based calculation or **Integer Linear
Programming (IPET)**. Hardware mechanisms whose behaviour must be modelled: **processor pipelines** (scalar →
superscalar → dynamic instruction scheduling), **instruction and data caches and multi-level memory hierarchies**,
**dynamic branch predictors**, and mechanisms such as the **memory row buffer**.

**What OTAWA is, and what inputs it needs.** "OTAWA is **not a tool but a toolbox**: it comes as a **C++ library**
that can be used to develop WCET analysis tools"; development started in **2004**; it is released **under the LGPL
licence from www.otawa.fr**; example tools are distributed with the library (an earlier survey of the ARTIST
network's WCET tools, Wilhelm et al. 2008, is cited as the motivation for building an open framework). Inputs:
* **the binary under analysis: an ELF object file**, loaded through the ISA abstraction layer ("a representation
  of the binary (.elf) code under analysis");
* **an XML description of the target hardware** ("from the user side, the hardware parameters can be specified with
  an **XML file**"), covering **processor** (width and length of the pipeline, number of functional units and their
  latencies, the binding of instruction categories to functional units, specification of instruction queues —
  location, capacity), **caches** (capacity, line width, organization in sets/ways, replacement policy, write
  policy), and **memories** (DRAM, scratchpad, each with specific access latencies and buffering policies, added in
  the French MORE project);
* **ISA support modules** for **PowerPC, ARM, TriCore, HCS12 and Sparc**, generated with their **GLISS** tool from
  **SimNML** ISA specifications (the loader modules are built from these instruction-set simulators, which
  decode/disassemble/emulate);
* **flow facts, in particular loop bounds**, obtained with the companion tool **oRange**, which works on the **C
  source code** using flow analysis + abstract interpretation to derive **contextual loop bounds** (a loop can have
  different bounds for different calls), the results being mapped to machine-level instructions through the
  compiler's debug information;
* **user-supplied branch targets for indirect branches** (e.g. switch statements) when the CFG cannot be built
  automatically;
* for the IPET step, the generated integer linear programs are solved by invoking the **lp_solve** tool.

**What it outputs.** Annotations ("properties") attached to any object, and from them a **WCET estimate** — but the
outputs are richer than a single number: (i) the **CFG representation of every function** (basic blocks plus edges,
as a set of interconnected CFGs for the program); (ii) analysis annotations such as **instruction-cache hit/miss
per instruction** and **basic-block worst-case execution times**; (iii) the **IPET integer linear programs**, built
by a structural-constraints builder and a cache-related-constraints builder and solved by an ILP solver; (iv) **dump
facilities** that print program representations and annotations, "as useful to the WCET tool developer … as well as
to the real-time application developer" — the latter "can get a better understanding of the program behavior and
locate program regions that break the deadlines"; (v) an **Eclipse integration** whose graphical program
representation **colours source code and CFGs to highlight the critical paths** (darker regions are those
responsible for the larger part of the total WCET), so "time-faulty program regions can be easily identified and
fixed"; and (vi) at least one WCET tool can be run by **invoking only the final "WCET computation" code processor**
— missing prerequisite data are then generated automatically by default code processors (dependency handling
through "features"). The canonical analysis order shown is: **object code loader → flow facts loader → CFG builder →
loop analyzer → instruction cache analyzer → basic block timing analyzer → structural constraints builder (IPET) →
cache-related constraints builder (IPET) → WCET computation (call to ILP solver)**.

**Analyses implemented in the toolbox (what it can actually do).** All analyses are **Code Processors**
(functions that consume and produce annotations): CG builders; a **CFG virtualiser that inlines functions to allow
call-contextual analyses**; a **loop analyzer** (loop headers, dominance relationships); Abstract Interpretation
facilities; an **instruction-cache analysis** based on abstract interpretation, close to Ferdinand's method with
improvements for accurate **persistence analysis of loop nests** in set-associative caches; a **pipeline analysis**
that computes worst-case basic-block execution times from **execution graphs with an analytical calculus** using a
**parametric view of the processor state at basic-block entry** — contrasted with **aiT** (abstract interpretation
over processor states, "likely to be time consuming") and **Chronos** (worst-case processor state); **experiments
are claimed to give more accurate results at comparable computation times**; and a **dynamic branch predictor
analysis** that formulates "whether a branch will be always/sometimes/never well predicted" as an ILP — "experiments
have shown that the complexity of this program is significant". It also embeds a **cycle-level simulator generated
on top of SystemC**, matching the XML architecture description, which "makes it possible to observe the execution
times related to given input values and then to get an **empirical insight into the range of WCET overestimation**".

**Limitations (explicit and implicit — important for the thesis).** (1) It is a **research toolbox, not a
push-button commercial tool**; the user is expected to develop analyses for their processor. (2) The **XML hardware
format is deliberately limited to "standard architectures"**: "Taking into account **real-life processors still
requires specific developments by the user**", although the library classes make this easier. (3) **Indirect
branches may need manual user input** of possible targets before the CFG is sound. (4) Modelling a dynamic branch
predictor via ILP has **significant complexity**. (5) The ISA plugins shipped/generated cover **PowerPC, ARM,
TriCore, HCS12 and Sparc** — **no Xtensa/ESP32 target is mentioned**, so OTAWA cannot be pointed at an ESP32-S3
binary out of the box; an ARM-based board would be the natural OTAWA-compatible alternative. (6) **No numerical
WCET results are reported in this paper at all** — it is a tools paper; the validation evidence is the list of
projects (below).

**Examples of use (the paper's "results").** *MasCotTE* (French ANR): OTAWA + GLISS modelled two automotive
processors — the **Freescale 16-bit Star12X** and the **high-performance Freescale MPC5554** — to test whether WCET
analysis scales to off-the-shelf processors of different complexity. *MERASA* (EU FP7 grant 216415, mixed-criticality
multicore): **two WCET approaches compared on the same platform — measurement-based with the RapiTime tool and
static analysis with OTAWA**; abstractions of the MERASA multicore and the **TriCore ISA** were developed, plus
models of a **dynamic instruction scratchpad**, a **data scratchpad for stack data** and a **predictable bus and
memory controller**; OTAWA analysed the WCET of a **parallel 3D multigrid solver** as pilot study, contributing
(a) analysis of **synchronisations between parallel threads** and (b) tight evaluation of **synchronisation-related
waiting times**, exploiting OTAWA's ability to analyse the WCET of **specified partial execution paths**.
*MORE* (French ANR ANR-06-ARFU-002): a framework for **code transformations** evaluated for code size, energy and
WCET; OTAWA is used to build **transformation emulators** — e.g. for code compression the profiling data are
collected with **OTAWA's cycle-level simulator**, the instructions to compress are chosen, each instruction is
**annotated with the address it would occupy in the compressed code**, and the WCET is analysed using those
addresses (they feed the instruction-cache analysis), so the impact of a compression algorithm can be estimated
**without generating the real compressed code or a new code loader**.

**Key quantitative/qualitative facts to quote.** Toolbox since **2004**; C++ library; **LGPL**, www.otawa.fr;
SEUS 2010, LNCS 6399, pp. 35–46; ISAs: **PowerPC, ARM, TriCore, HCS12, Sparc**; hardware model via **XML**
(pipeline width/length, functional units and latencies, instruction queues; cache capacity/line/ways/replacement/
write policy; DRAM and scratchpad latencies); three-step WCET method (flow analysis, low-level analysis, combination);
analysis order with **IPET** and **lp_solve**; **SystemC** cycle-level simulator for overestimation ranges;
**Eclipse** plugin with WCET-coloured code/CFG; companion tools **GLISS** and **oRange**; projects MasCotTE
(Star12X, MPC5554), MERASA (RapiTime vs OTAWA, TriCore, 3D multigrid solver, partial-path WCET), MORE (code
compression emulation).

**Directly reusable for a 24U nanosat RL-ADCS thesis with an ESP32-S3 HIL stage.** Use OTAWA as the **definition of
what "WCET analysis" means** in the real-time chapter: three steps (flow analysis → low-level/architecture analysis →
combination), the requirement of an **object-file input plus an architectural model**, the distinction between
**measurement-based** and **static/hardware-model-based** timing (the MERASA project used **RapiTime and OTAWA side
by side on the same multicore** — exactly the honest framing for an ESP32-S3, where *measurement* is feasible but
*static WCET* is not), and the output form to report: **a bound per task compared against its deadline, plus a
coloured/annotated view of the critical path**. Critically, the **Xtensa ESP32-S3 is not among OTAWA's supported
ISAs (PowerPC/ARM/TriCore/HCS12/Sparc) and the XML model is restricted to standard architectures**, so a thesis
that wants a static WCET bound should either (i) argue measurement-based worst-case timing on the target with
instrumentation and stress inputs, or (ii) present such a bound for an ARM-class MCU as a cross-check — and must
never claim OTAWA-verified WCET on an ESP32-S3.

---
# Cross-cutting patterns — what a credible ADCS verification and HIL chapter looks like in real missions

1. **Every real mission publishes an explicit model ladder, and names the tool at each rung.** UPMSat-2 runs
   MIL (Simulink ACS + environment model, used to pick the 2 s period and k = 1e8) → PIL (real OBC software on a
   LEON3 board joined by a serial line to a host running the environment model; TRL 4) → HIL (the OBC's own ADC and
   digital I/O lines to simulated magnetometer voltages and PWM-driven H-bridge models; TRL 8 target) (source #2);
   the same group's MDE paper calls the last rung a **"dynamic hardware-in-the-loop (HIL) facility"** in which "the
   spacecraft dynamics and its environment are **simulated on the simulation computer**, while the **control
   software runs on the engineering board**", and explicitly justifies it — "the environment of space systems is not
   available for testing, and therefore it has to be simulated" (source #5); ITU-pSAT II separates an **SIL stage
   (Simulink ADCS over UDP to an STK truth model)** from an **HIL stage (real sensors, actuators and mission
   computer on an air-bearing table inside Helmholtz coils)** (source #1). A thesis HIL chapter is only credible if
   it states, rung by rung, **what hardware is real and what is simulated**, exactly as these papers do.

2. **A separate "truth model" or high-fidelity environment, distinct from the control model, is used to catch
   estimator/model errors.** ITU-pSAT II uses **AGI STK as the truth model** (disturbances/perturbations, orbit
   propagation with J2 from TLEs, IGRF11 field) while the ADCS software model in Simulink commands torques back over
   UDP; the emulated sensors inject **noise, magnetometer calibration errors and gyro biases** (source #1). UPMSat-2
   validates the control law with a **Monte Carlo campaign across orbit inclinations** (at the flown 97.4°
   inclination, a mean deviation of **≈2.5°** from the orbit normal) and then checks the flight result against it
   (source #3). Both patterns say: **simulate with credibility, then verify against a bound you predicted in
   advance.**

3. **Verification is layered and each layer has a named pass/fail quantity: functional (does the loop close),
   temporal (does it meet the deadline), environmental (does it survive and behave), and in-flight (did the number
   match).** Functional: Simulink model of torques → rotational dynamics → quaternion/rotation matrix + angular
   speed, controller block including sensor and actuator models (source #5). Temporal: **MAST** response-time
   analysis + **RapiTime** execution-time analysis integrated with the AADL concurrency view, giving "accurate
   estimates of worst-case response times of every real-time task", with the controller as a periodic thread
   **Period 1000 ms, Deadline 100 ms** (source #5); Ravenscar profile + ORK+ kernel + extended schedulability
   analysis of the PWM tasks (source #2); OTAWA's three-step method (flow analysis → low-level architecture
   analysis → combination via IPET/ILP) and the MERASA precedent of running **measurement-based (RapiTime) and
   static (OTAWA) timing analysis side by side on the same multicore** (source #6). Environmental: thermal-vacuum
   testing correlated the thermal model parameters (source #3). In-flight: measured 2.2° vs predicted 2.5°, spin
   0.1025 rad/s (source #3).

4. **The honest, quantitative way to claim pointing performance is a distribution, not a maximum, and it must be
   measured by an independent channel.** UPMSat-2 reports the Sun-incidence/illumination angle on the z axis as a
   **normal distribution with mean 112.9° and σ = 2.5°**, against a theoretical mean of 110.7° for the month, giving
   a **mean pointing deviation of 2.2°** (sources #3); the same paper refuses to trust a single sensor: the
   magnetometer-derived spin rate is **cross-validated by a transient thermal analysis of 4004 temperature points**,
   which rules out rates below **0.052 rad/s** and independently favours **≈0.1 rad/s** within a theoretical band of
   **0.1017–0.1033 rad/s**. A thesis with a star tracker, a sun sensor and a gyro has strictly more observability
   than this and should therefore cross-check the RL controller's attitude error with at least two independent
   sensor channels and report mean ± σ and worst case — not one number.

5. **HIL in real programmes is designed around a specific physical nuisance, and that nuisance shapes the
   software.** For magnetic control the nuisance is that **the magnetometers cannot be read while the magnetorquers
   are energised**, so UPMSat-2 built a **2 s control cycle: 1 s of magnetometer sampling at 200 ms intervals (five
   readings averaged) → 200–500 ms of magnetorquer actuation → ≥500 ms of rest** to let the residual dipole decay
   (sources #2 and #3). ITU-pSAT II's HIL nuisance is the opposite: it must inject a **homogeneous field from
   Helmholtz coils** and let an **air-bearing table** reproduce 3-axis micro-gravity dynamics, and it tests the
   scenarios that matter for FDIR — **y-axis magnetorquer failure** and **one reaction-wheel failure during
   tracking** (source #1). The chapter's HIL section should therefore be organised around *the artefacts of the
   specific hardware* (wheel torques, magnetic disturbances, sensor timing) rather than around a generic data flow.

6. **Fault tolerance is designed as detection + reconfiguration, and it is tested explicitly, not assumed.**
   ITU-pSAT II detects sensor failures by bias estimation and isolation from the estimator, detects actuator
   failures with a **multiple-model switching scheme** (generate the state trajectory for every possible actuator
   failure, integrate a performance index over time, take the minimum as the identified failure), and manages
   redundancy by **control allocation across 4 wheels in a tetrahedron and 4 magnetorquers** — then validates it in
   HIL with the failed-actuator scenarios above (source #1). UPMSat-2's controller model contains an **"if fail
   recalculate"** block that produces a degraded action when one or two magnetorquers fail (source #2), and its
   platform software switches to an **error mode** reporting to the ground when housekeeping values leave their
   nominal ranges (source #5). For a thesis whose faults are "one RW fully dead" and "one RW limited to 50 %
   torque", this is the established template: detection logic, isolation/reconfiguration rule, a **degraded
   performance number for each fault case**, and the fault injected in HIL.

7. **On-board software architecture in flight-realistic systems is small, static and analysable: one processor,
   hard real-time task set, generated code, explicit interfaces — and the interfaces are quantised early.** UPMSat-2
   flies a **LEON3 @ 20 MHz with 4 MB SRAM / 1–2 MB EEPROM, 12-bit ADC, PWM + H-bridge drive, RS422**, three
   concurrent tasks (Sensor, Controller, Actuator) over two shared data objects, Ada Ravenscar on ORK+ with C code
   auto-generated from Simulink (sources #2, #5); the MDE paper defines the ADC data model in ASN.1 as
   `MagnetometerType ::= REAL(0.0..5.0)` with IEEE-754-32 ACN encoding and per-axis Boolean magnetorquer commands,
   and the controller as a periodic AADL thread **1000 ms / 100 ms** (source #5). ITU-pSAT II keeps a layered
   architecture — propagator → estimation/filtering (EKF) → mode-dependent control → actuator commands — with an
   explicit mode logic of de-tumbling (B-dot) and attitude tracking (LQR + momentum dumping) (source #1). An
   ESP32-S3 chapter should mirror this: **a fixed-period task set, one shared state object per direction, a mode
   table (detumble / acquire / nadir-point / safe), and no dynamic allocation in the loop.**

8. **The real-time claim is always made against a WCET or response-time bound — never against average runtime —
   and the tool's scope is stated honestly.** The UPMSat-2 group has two dedicated WCET papers on exactly this
   subsystem (Garrido et al., 12th and 13th Int. Workshops on WCET Analysis, 2012 and 2013) and uses the PIL/HIL
   board to **estimate execution times that are fed back into the response-time analysis tools** (sources #2, #5);
   OTAWA is the reference for what a WCET analysis requires (ELF binary + XML architectural model, three-step flow/
   low-level/combination method, IPET+lp_solve) and, crucially, for its limits (toolbox not tool; XML restricted to
   standard architectures; **no Xtensa/ESP32 support**; ILP branch-predictor modelling is expensive) (source #6).
   Conversely, source #4's "111.24 ms vs 465 ms with PID, 76 % reduction in decision time" is precisely the kind of
   number that must **not** be presented as real-time evidence, because no processor, clock, memory layout or
   analysis is given for it.

9. **The verification chain ends in flight, and the paper is willing to publish the discrepancy.** UPMSat-2's
   in-flight analysis required inventing a method — **stroboscopic-effect correction with ω_c = ω_s − ω_ap** —
   because the 1-sample-per-minute telemetry aliased the 1 rev/min spin, plus thermal-model fitting to break the
   ambiguity (source #3); the paper documents the ±3 °C thermal-model discrepancy and attributes it to per-orbit
   initial conditions rather than hiding it (source #3). A thesis that reaches only HIL should say so explicitly and
   state which parts of the verification chain remain unflown — that transparency is itself the pattern followed by
   the credible papers here (source #5: "plans for the near future include testing with real sensors and actuators …
   instead of the serial line connections that are being currently used").

---

## Realistic HIL expectations for a 24U nanosat with an ESP32-S3

* **What the ESP32-S3 HIL can genuinely prove.** (i) **Software-in-the-loop equivalence on real silicon**: that the
  identical controller binary/source that will fly runs at the commanded rate and produces the commanded actuator
  words from real sensor inputs — the UPMSat-2 PIL/HIL arrangement ("plant simulated on the host, control software
  on the real board", sources #2 and #5) with the ESP32-S3 playing the role of the LEON3 board. (ii) **End-to-end
  timing, measured not assumed**: per-cycle execution time of the RL policy forward pass plus estimation and mode
  logic, with a stated **worst case over stress inputs** (adversarial states, saturation, fault branches) and a
  margin against the control period — the honest analogue of the 1000 ms/100 ms AADL thread (source #5), because a
  static WCET bound for Xtensa is not available from OTAWA (source #6). (iii) **Fault-handling logic**: injection of
  "RW-1 dead" and "RW-2 at 50 % torque" and demonstration that detection, reconfiguration and the safe fallback
  execute in bounded time — the type of scenario ITU-pSAT II actually ran in HIL (source #1). (iv) **Interface and
  numerics integrity**: fixed-point/floating-point behaviour, ADC quantisation (12-bit-like), PWM/discrete
  actuation, and the sensor-sampling-versus-actuation exclusion window that magnetic designs must respect (2 s cycle
  with a ≥500 ms guard, sources #2/#3) — for the thesis, the equivalent of "do not read the star tracker / gyro
  while the wheels are slewing".

* **What it cannot prove and must not be claimed for it.** (i) **Physical actuator and sensor dynamics**: an ESP32
  driving a simulated wheel model proves nothing about real wheel friction, torque ripple, saturation below the
  commanded 50 %, tachometer noise or star-tracker/gyro bias and latency — those require an air-bearing table with
  real hardware, a Helmholtz-cage magnetic environment, or vendor data sheets with margins (testbed inventory in
  source #4; air-bearing + coil HIL in source #1). (ii) **Disturbance environment**: aerodynamic drag, solar
  pressure, residual dipole and gravity-gradient torque cannot be generated in a lab HIL; they enter only through
  the model, so the thesis's disturbance rejection claim is only as good as its model (sources #1, #3). (iii) **A
  static WCET guarantee**: one cannot obtain a safe WCET upper bound for the ESP32-S3 with the tools described here
  (OTAWA supports PowerPC/ARM/TriCore/HCS12/Sparc, not Xtensa; source #6), so the claim must be explicitly
  **measurement-based worst case on the target under worst-case inputs**, ideally cross-checked against a model or
  an ARM-class MCU run, and worded as such.

* **Three concrete requirements to make the HIL stage defensible.** (1) **Fix the loop period and deadline before
  the experiment** and report, for every cycle: state estimates in, action out, actuation time, execution time, and
  the measured maximum against the deadline (the AADL thread with Period/Deadline is the model to imitate, source
  #5). (2) **Instrument the fault cases as first-class scenarios with pass/fail criteria** — e.g. "RW-1 dead at
  t = X: attitude error must return below θ within T s, wheel-3 speed must stay below ω_max, and no NaN/unbounded
  action appears" — and, like ITU-pSAT II, run them in HIL, not only in simulation (source #1). (3) **Report
  attitude performance as mean ± σ plus worst case against a predicted bound** (the 2.2° measured vs 2.5° predicted
  norm of source #3), separately for the nominal RL/LQR comparison and for each fault case, with the achieved
  numbers in degrees and the pointing requirement stated in the same units.

* **Where the honest limit line is.** The ESP32-S3 HIL can establish that the **software** of the RL-ADCS is
  correct, timely and graceful under injected faults on the real processor; it cannot establish that the
  **spacecraft** points as intended, because the plant, the sensors and the actuators are simulated. In the
  literature surveyed here, exactly two hardware HIL elements do that job and neither is an ESP32: an
  **air-bearing table** (free rotational dynamics of the real structure) and a **Helmholtz cage with a sun
  simulator** (real magnetic and illumination environment), with the real magnetometers, wheels and torquers
  mounted on the structure (sources #1, #3, #4). The thesis should therefore present the ESP32-S3 stage as
  **"software and timing HIL"** and state that physical-fidelity validation (air bearing, magnetic cage, thermal
  vacuum) remains future work, in the same way the UPMSat-2 papers declare their pending steps (source #5).
