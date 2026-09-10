\# Reading Notes: AdaJEPA — An Adaptive Latent World Model



> These are notes and a summary, not a reproduction of the paper. For exact

> wording, equations, or table values, use the source directly:

> \*\*arXiv:2606.32026\*\* — https://arxiv.org/abs/2606.32026

> Project page: https://agenticlearning.ai/adajepa

> Code: https://github.com/agentic-learning-ai-lab/adajepa



\*\*Authors:\*\* Ying Wang, Oumayma Bounou, Yann LeCun, Mengye Ren — NYU / AMI Labs

\*\*Posted:\*\* June 30, 2026



\## The problem it addresses



Latent world models (JEPA-style: an encoder that maps observations into a

compact latent space, plus a predictor that forecasts future latent states)

are normally trained once, then frozen, and paired with model-predictive

control (MPC) for planning. The paper's starting observation: a frozen

model's prediction errors compound over a planning horizon, and get much

worse under test-time distribution shift — visual changes (lighting, noise,

color), or physical changes (different object geometry, different mass or

damping). The model doesn't get worse gracefully; planning built on bad

predictions actively picks bad actions.



\## The core idea



Stop treating the world model as frozen after training. AdaJEPA runs a

\*\*plan → execute → adapt → replan\*\* loop inside closed-loop MPC:



1\. Plan a short action sequence with the current model.

2\. Execute the first action, observe the real next state.

3\. Compare the model's prediction for that transition against what actually

&#x20;  happened, and take \*\*one self-supervised gradient step\*\* to reduce that

&#x20;  error — updating only a small subset of parameters (in their default

&#x20;  setup, the predictor's last transformer block plus the encoder's last

&#x20;  stage).

4\. Replan with the now-slightly-updated model.



No reward labels, no expert demonstrations, no separate data-collection

phase — the signal is just "did my last prediction match what actually

happened," which is available for free from ordinary interaction. The

authors motivate this loosely by analogy to biological motor adaptation

(cerebellar recalibration in humans), though the mechanism itself is a

standard self-supervised latent-prediction loss, not anything

biologically-inspired in implementation.



\## Why it's cheap



Because only a handful of layers get one gradient step per planning

iteration, the added latency is small — on the order of hundredths of a

second per replanning step in their measurements, and adaptation often

\*reduces\* total episode time too, since the agent reaches its goal in fewer

replanning iterations when its predictions are more accurate.



\## What they tested it on



Two simulated benchmarks: \*\*PushT\*\* (a pusher agent shoving a block to a

target pose) and \*\*PointMaze\*\* (2D navigation). Within PushT they built a

variant called \*\*PushObj\*\* that swaps the pushed block for different shapes.

They tested four categories of train/test mismatch:



\- \*\*Shape shifts\*\* — trained on a few block shapes, tested on both those and

&#x20; entirely unseen ones.

\- \*\*Visual shifts\*\* — blur, noise, dark lighting, and recolored objects, with

&#x20; training only ever seeing the unmodified visuals.

\- \*\*Dynamics shifts\*\* — changed mass and damping in PointMaze.

\- \*\*Layout shifts\*\* — unseen maze layouts.



\## Headline results



\- Adaptation helps even \*\*in-distribution\*\* (never hurts, sometimes

&#x20; substantially improves a suboptimal frozen model) and helps \*\*a lot\*\*

&#x20; out-of-distribution — on unseen shapes, planning success roughly doubled

&#x20; relative to the frozen model.

\- Gains hold up across two different planners (gradient descent and CEM),

&#x20; across several different underlying JEPA architectures, and across the

&#x20; choice of exactly which layers get adapted — the method isn't fragile to

&#x20; these choices, though which layers matter most is somewhat

&#x20; shift-dependent (encoder layers matter more when the \*observation\* itself

&#x20; looks different; predictor layers matter more when the \*dynamics\* change).

\- It's especially valuable when training data is scarce: a model trained on

&#x20; one shape with very few trajectories, then adapted at test time,

&#x20; outperformed a frozen model trained on substantially more data spread

&#x20; across more shapes. The authors frame this as adaptation being a

&#x20; sample-efficient complement to simply collecting more training data,

&#x20; not a replacement for it — its benefit is bounded by what the pretrained

&#x20; representation can already cover.



\## Where it sits relative to prior work



The paper positions itself against two neighboring lines of work: (1) other

JEPA-style world models, which are all evaluated frozen; and (2) test-time

training/adaptation more broadly (an established idea in image

classification and elsewhere), which as far as the authors could establish

hadn't previously been applied to adapt a world model \*during\* closed-loop

planning specifically — most prior "adaptive" world models require extra

target-domain data collection or an outer retraining loop rather than a

single online gradient step per control cycle.



\## Why this is relevant to fault-tolerant attitude control



A fault (reaction wheel saturation, sensor bias) is structurally the same

thing as the paper's dynamics-shift experiments (changed mass, changed

damping) — the satellite's effective dynamics change to something the

offline-trained model never saw. The pitch for the thesis: pair a

lightweight JEPA-style world model (an MLP encoder is enough, since attitude

state is low-dimensional, not pixels) with MPC for attitude control, then

apply this same test-time adaptation loop so the controller keeps

recalibrating online when a fault occurs — instead of needing to have seen

that exact fault during offline training, the way a frozen model or a

fixed fault-randomized RL policy would.



\## One gap worth being aware of



Nothing in the paper addresses \*safety\* during adaptation — there's no

mechanism to reject a bad update (e.g. one caused by corrupted sensor data

rather than a genuine dynamics shift). For a safety-critical system like a

spacecraft, that's exactly the kind of validation/rollback gate worth adding

as your own contribution on top of their method, as discussed earlier.

