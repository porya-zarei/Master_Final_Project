# adaptive/ — Phase 3: AdaJEPA-style test-time adaptation + safety gate

**The thesis contribution.** Plan–execute–adapt–replan: after each real
transition, take a single self-supervised gradient step (predicted vs. actual
next latent state) on a small parameter subset, then replan with MPC. Evaluated
on faults **not seen** during offline training (novel severities/combinations).

Our addition over the base AdaJEPA paper: a **safety/validation gate** that
rejects an adaptation step if it would increase predicted cost or drift
parameters too far — plus a bridge to classical adaptive control (STR / MRAC).

_Scaffolding — nothing implemented yet._
