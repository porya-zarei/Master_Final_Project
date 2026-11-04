# Q&A Brief — the three papers
### Seminar I · Pouria Zarei · University of Tehran

Use this the night before: for each paper you need **one sentence**, **three numbers**, **two weak points**, and **five answers**. Nothing more.

The Persian line under each question is what you actually say out loud.

---

# Paper 1 — Yang, Jin & Rao (2025)
**Reinforcement learning based attitude fault-tolerant control of spacecraft with unknown system model**
*Journal of the Franklin Institute* 362, 107741 · doi:10.1016/j.jfranklin.2025.107741
Shanghai Institute of Spaceflight Control Technology + Beihang University

### خلاصه در یک خط
یک کنترلر وضعیت می‌سازند که بدون دانستن مدل دقیق ماهواره، با یادگیری تقویتی آفلاین آموزش می‌بیند و بعد با یک مشاهده‌گر عصبی و RLS به‌صورت آنلاین خودش را با خرابی عملگر تطبیق می‌دهد.

### What they actually did
1. **Offline:** combine RL with optimal control (policy iteration) to get an approximate optimal policy for the **nominal** system — inertia uncertainty, faults and disturbances are ignored at this stage.
2. **Observer:** a neural-network observer estimates the **input matrix B** (which absorbs multiplicative actuator faults) and the **partial disturbance δ** (additive faults + external torque).
3. **Online:** the offline controller is the *initial* policy; the **critic network weights are updated online by Recursive Least Squares (RLS)** — not by gradient descent. That is the real-time trick.
4. **Feedforward:** the estimated δ is added as feedforward compensation for additive faults and disturbances.
5. **Stability:** Lyapunov proof for the closed loop.

Chain to remember: **offline optimal policy → observer estimates B and δ → RLS updates critic → feedforward kills the additive part.**

### Numbers to have ready
| Item | Value |
|---|---|
| Actual inertia J | [[45.4, 1.5, 1.0], [1.5, 23.3, 1.2], [1.0, 1.2, 32.8]] kg·m² |
| Nominal inertia J₀ | diag(40, 20, 28) kg·m² → ≈ 10–16 % mismatch |
| Actuators | 4 (3-axis + 1 redundant), installation matrix C |
| Fault | at **t = 20 s**, x-axis: effectiveness e₁ = 0.5, additive bias u_c1 = −0.1 N·m |
| Disturbance | ≈ 10⁻⁴ N·m, slow sinusoid |
| Offline convergence | 4–5 policy iterations, 500 random initial states |
| Cost improvement | 8 → 7 (≈ 12.5 %) |
| Online covariance init | P(0) = 10⁶·I₂₁ |

### Strong points (say these if someone attacks it)
- It is **model-free in the sense that matters**: you never need the true inertia or the fault magnitude.
- RLS gives **real-time parameter update** without a training phase online — this is a genuine engineering argument.
- It has a **Lyapunov stability proof**, which pure DRL papers usually lack.
- Additive and multiplicative faults are handled **separately** (feedforward vs. estimated input matrix) — that is a clean decomposition.

### Weak points (concede them calmly — they are also your gap)
- **One scenario, one simulation.** One fault, one time instant, no Monte-Carlo, no statistical claim.
- **No sensor faults.** Only actuator faults; the state is assumed measurable/known.
- **Fault set is fixed at design time** — nothing is said about a fault never seen in the offline data.
- **No hardware, no onboard timing.** "Real-time" is argued by algorithm structure, not measured on a processor.
- The offline stage still needs a **nominal model** to generate the initial admissible policy.

### Likely questions

**Q: Is this really "model-free"?**
A: Not completely. It is free of the *true* model: the nominal model is only used offline to initialise the policy, and the input matrix is estimated online. So the accuracy of the nominal model affects only the starting point, not stability.
> «کاملاً بدون مدل نیست؛ مدل نامی فقط برای شروع آفلاین استفاده می‌شود و ماتریس ورودی به‌صورت آنلاین تخمین زده می‌شود.»

**Q: Why RLS instead of gradient descent for the critic?**
A: Speed and no data-collection phase online. RLS updates the weights recursively in closed form, so they avoid the sample-inefficiency of online gradient RL — that is their main claim to real-time feasibility.

**Q: How do they separate multiplicative and additive faults?**
A: Multiplicative goes into the estimated input matrix B̂ (so the policy "sees" reduced authority); additive goes into δ̂ and is cancelled by a feedforward term. Without the feedforward term they show a **steady-state error** after t = 20 s.

**Q: What happens with an unseen fault severity?**
A: Unknown — and that is exactly the hole. The observer extrapolates, but there is no experiment with a severity outside the design case.

**Q: Could you use this on a CubeSat?**
A: The structure is promising — a critic with 21 basis functions and RLS is cheap — but they never quantify it, and the observer gains (K_o = 20·I₆) are tuned in simulation.

---

# Paper 2 — Lu et al. (2026)
**Safe RL based agile satellite attitude control for non-cooperative target tracking with operation constraints and actuator faults**
*Aerospace Science and Technology* 168, 111238 · doi:10.1016/j.ast.2025.111238
Shanghai Jiao Tong University + RUDN University

### خلاصه در یک خط
ردیابی یک هدف غیرهمکار را به یک مسئله کنترل وضعیت **مقید** تبدیل می‌کنند: نواحی ممنوعه، محدودیت نرخ زاویه‌ای، اشباع گشتاور و خرابی عملگر؛ و با یادگیری تقویتی **ایمن** (WCSAC) به‌همراه یک ماژول شناسایی خطا حلش می‌کنند.

### What they actually did
1. **Task decomposition:** the tracking task is split into three stages (large-angle manoeuvre → fine pointing → tracking), inside a ≈540 s imaging window, preceded by a ≈3 s fault-identification window.
2. **CMDP formulation:** reward = tracking quality (target inside payload field of view); **cost** = violation of forbidden zones / rate / torque limits.
3. **Fault model:** u = (I − E)·u_c + u_a — effectiveness loss **and** additive bias, per actuator.
4. **Fault identification:** a neural network estimates ê_l and û_a from the command torque and the state.
5. **WCSAC (worst-case soft actor-critic)** from OmniSafe learns the policy under a reward/penalty structure, explicitly trading reward against constraint cost.

Chain: **fault ID → CMDP → WCSAC → safe, fault-tolerant tracking.**

### Numbers to have ready
| Item | Value |
|---|---|
| Fault ID error (theirs) | MSE **1.92 × 10⁻⁴**, MAE 6.43 × 10⁻³ |
| Fault ID error (prior NN) | MSE 2.35 × 10⁻⁴ |
| Least-squares filter / gradient descent | 4.81 × 10⁻⁴ / 3.98 × 10⁻⁴ |
| Inference time | **7.49 ms** (theirs) vs 3.98 ms (prior NN), 0.44 ms (LS) |
| Compute for training | AMD EPYC 7453 + **RTX 4090**, PyTorch 2.2.2, OmniSafe |
| Training time | "a few hours" |

### Strong points
- Safety is **inside the objective**, not checked afterwards: the CMDP cost makes constraint violation explicit.
- It shows the honest comparison: **vanilla SAC violates the forbidden zones**, a reward-penalty baseline still has high cost in some cases, WCSAC keeps both.
- Fault identification is **data-driven and simultaneous** (effectiveness + bias), and they benchmark it against LS, gradient descent and a prior NN.
- The payload field-of-view angle is in the reward, so "tracking" means "target actually inside the sensor".

### Weak points
- **Training uses the true fault value** (Algorithm 1: ê_l ← e_l, û_a ← u_a during training); the identification network is only used at test time. So the policy is trained under a *perfect* fault estimate and then fed an estimate — an optimistic gap they do not analyse.
- **Simulation only** (they say it themselves), and the fault-ID network **needs pre-trained prior knowledge** and is sensitive to parameter uncertainty.
- **Heavy**: GPU training, a CNN-style identifier, a WCSAC actor-critic. No latency budget for a flight processor.
- Faults come from a designed distribution; no held-out fault types.

### Likely questions

**Q: What is "worst-case" in WCSAC?**
A: The critic estimates a *distribution* over cost-to-go and the policy is optimised against an upper quantile, not the mean — so rare high-cost outcomes are penalised. That is why it dominates a soft reward-penalty approach.

**Q: How do they guarantee safety?**
A: They don't guarantee it in the formal sense. They *penalise* violations through a constrained MDP and show empirically that WCSAC keeps the cost low. "Safe" here means "constraint-aware", not "certified".
> «تضمین رسمی نمی‌دهند؛ قید را در تابع هزینه می‌آورند و تجربی نشان می‌دهند که نقض کم می‌شود.»

**Q: Is the fault estimator used during training?**
A: No — and this is the sharpest question you can be asked. In training they feed the **true** fault; at test they feed the estimate. So performance at test is a lower bound with an extra estimation error.

**Q: Why is their identifier slower than the least-squares filter?**
A: Accuracy. 7.5 ms vs 0.44 ms, but an order of magnitude lower MSE. For a 5 Hz ADCS both are fast enough; for a high-rate inner loop the LS filter wins.

**Q: Can this run on a CubeSat processor?**
A: Not shown. GPU training, no quantisation, no inference measurement on embedded hardware — their own limitation section says the next step is laboratory reaction-wheel testing.

---

# Paper 3 — Nagano & Schaub (2025)
**Enhancing fault resilience in RL-based satellite autonomous task scheduling**
AAS 25-637 · University of Colorado Boulder

### خلاصه در یک خط
یک ماهواره تصویربرداری را در نظر می‌گیرند که با RL زمان‌بندی می‌شود و نشان می‌دهند دوام سیاست در برابر خرابی چرخ واکنشی به **نوع و شدت خطا** بستگی دارد؛ و مهم‌تر: آموزش در محیط معیوب همیشه راه‌حل نیست.

### What they actually did
1. **POMDP**, because the fault state is **not directly observable** — this is the modelling choice that matters.
2. Four RW faults: **complete loss of control**, **power-draw limit**, **increased Coulomb friction**, **encoder fault** (signal off / stuck).
3. **APPO** trained inside **Basilisk** (high-fidelity). Baseline = a **curriculum-learning policy** + a **shield**.
4. Three resilience mechanisms tested: **fault-injected training**, **fault information added to observations**, **recurrent networks** for temporal fault signatures.
5. Metrics: **reward** and **alive ratio** (failure = battery depletion or RW overspeed).

### Findings to remember (this is the gold for your argument)
| Fault severity | What works |
|---|---|
| **Severe** (uncontrollable RW) | Fault-adaptive training **does not help**; **shutting the faulty wheel down** on detection is better |
| **Mild** (small power limit, moderate friction, encoder) | Training inside the fault condition **improves** resilience and reward |
| Encoder fault | Small impact — the ADCS is torque-based and does not rely on RW speed measurement directly |

### Numbers
- 350 trials per configuration; 95-min orbit, 3-orbit episodes.
- Nominal CL policy: 1 failure in 350 (with shield), 3 in 350 (without shield).
- Onset of severe degradation: power limit ≤ **0.01 W**, friction ≈ **×400** nominal.

### Weak points
- It is a **scheduler**, not an attitude controller — no continuous-control stability argument, no pointing accuracy.
- **Simulation only**, and only one satellite model.
- They state it themselves: you **cannot model every real fault**, and when you mix faults in training the policy **over-adapts to the frequent ones and neglects rare but critical ones**. That single sentence is your research gap in the literature's own words.

### Likely questions

**Q: Why is this relevant if it is only a scheduler?**
A: Because it isolates the *learning* question from the control question: does the policy itself degrade under faults, and can training fix it? The answer — "sometimes, and not for severe faults" — transfers to the attitude controller.

**Q: Why a POMDP?**
A: Because in flight you never observe the fault directly; you infer it from behaviour. That is the same reason my policy never receives the true health h.

**Q: Why did shutting the wheel down beat fault-adaptive training?**
A: A dead wheel removes authority that no policy can recover; the best action is to reconfigure (three wheels + magnetorquers) rather than to keep chasing performance. Training cannot manufacture torque.
> «چرخی که از کار افتاده، اختیار کنترلی را از بین می‌برد؛ بهترین کار خاموش کردن آن و بازآرایی است، نه یادگیری جبران.»

**Q: What is the "over-adaptation" problem?**
A: With a mixed fault distribution, the policy optimises for the statistically frequent fault and becomes worse on rare, severe ones — the exact failure mode a naive fault-randomised training would have.

---

# Cross-paper questions (they will ask these)

**"Which of the three is closest to your work?"**
Yang — same problem (unknown model + actuator faults + attitude), but no deployment and no unseen-fault test. Lu gives the safety argument; Nagano gives the training-split argument.

**"All three are simulation-only. Isn't that a weakness of the field?"**
Yes, and it is the most honest thing you can say. None of them reports inference time on flight hardware or a hardware-in-the-loop run; Lu reports 7.5 ms measured on a workstation GPU, not on an MCU. That is why my plan puts MIL → SIL → HIL on the critical path.

**"Do any of them test faults outside the training distribution?"**
No. Nagano *discusses* it and warns about over-adaptation, but does not hold out a fault family. That is the gap my evaluation matrix targets (dead wheel never seen in training).

**"Are the fault models the same across papers?"**
Yang: multiplicative + additive, one axis. Lu: per-actuator effectiveness loss + bias, several actuators. Nagano: four physically distinct RW failures, including encoder faults. Mine uses the continuous health h ∈ [0,1] per wheel — a superset of Yang's and Lu's binary/partial cases.

---

# Questions aimed at *you* (prepare these too)

**Q: Why RL and not MPC or a robust controller?**
A: Because the fault changes the plant in a way I cannot model at design time. A model-based controller is only as good as its fault model; RL can absorb the mismatch. But I keep LQR as the baseline and the fallback — I am not claiming RL replaces it.

**Q: How do you guarantee safety?**
A: I don't claim a formal guarantee. I use a **physics-based governor + LQR fallback** — the network is never the last line of defence. That is a deliberate design choice, not a theorem.

**Q: Why not let the network see the true health h?**
A: In flight h is not measurable; only an estimate ĥ exists. Training with the true value would create a policy that depends on information it will never have.

**Q: What happens with a fully dead wheel?**
A: Control authority drops; the allocator redistributes to the remaining wheels and magnetorquers. If the configuration becomes uncontrollable, the honest answer is that no controller recovers it — the governor hands over to the fallback and the mission degrades safely.

**Q: Is a 24U / 35 kg platform a "nanosatellite"?**
A: It is the upper end. The method is platform-agnostic; the inertia only scales the torque budget.

**Q: Your results were invalidated by a frame-convention bug — how do you answer that?**
A: Straight. The bug was in the pointing metric (`quat_to_dcm` returned C_NB while callers assumed C_BN); it is fixed and pinned by 12 frame tests including a momentum-conservation test. That is also why this seminar reports no numbers — only the method and the gap.

---

# One-page cheat sheet

| | Yang 2025 | Lu 2026 | Nagano 2025 |
|---|---|---|---|
| Problem | attitude FTC, unknown model | agile tracking, constrained | mission scheduling |
| Method | RL + NN observer + **RLS** | **CMDP + WCSAC** + fault ID | **APPO** in Basilisk, POMDP |
| Faults | 1 actuator, e=0.5 + bias | effectiveness + bias, several | 4 RW fault types |
| Safety | Lyapunov | constraint cost (empirical) | shield + alive ratio |
| Evidence | 1 simulation | 5 cases, ablations | 350 trials × configs |
| Deployment | none | none (GPU only) | none |
| Unseen faults | ✗ | ✗ | discussed, not tested |
| Use in my talk | "closest problem" | "safety argument" | "training-split argument" |
