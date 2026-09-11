5
2
0
2

l
u
J

1
1

]

O
R
.
s
c
[

1
v
6
6
3
8
0
.
7
0
5
2
:
v
i
X
r
a

Intelligent Control of Spacecraft Reaction Wheel
Attitude Using Deep Reinforcement Learning

Ghaith El-Dalahmeha,∗, Mohammad Reza Jabbarpoura, Bao Quoc Voa,
Ryszard Kowalczykb,c

aSwinburne University of Technology, John St,
Hawthorn, Melbourne, 3122, VIC, Australia
bUniversity of South Australia, Adelaide, 5000, SA, Australia
cSystems Research Institute Polish Academy of Sciences, Warsaw, 00-901, Poland

Abstract

Reliable satellite attitude control is essential for the success of space missions,
particularly as satellites increasingly operate autonomously in dynamic and
uncertain environments. Reaction wheels (RWs) play a pivotal role in at-
titude control, and maintaining control resilience during RW faults is crit-
ical to preserving mission objectives and system stability. However, tradi-
tional Proportional-Derivative (PD) controllers and existing deep reinforce-
ment learning (DRL) algorithms—such as TD3, PPO, and A2C—often fall
short in providing the real-time adaptability and fault tolerance required for
autonomous satellite operations. This study introduces a DRL-based con-
trol strategy designed to improve satellite resilience and adaptability under
fault conditions. Specifically, the proposed method integrates Twin Delayed
Deep Deterministic Policy Gradient (TD3) with Hindsight Experience Re-
play (HER) and Dimension-Wise Clipping (DWC) referred to as TD3-HD
to enhance learning in sparse reward environments and maintain satellite
stability during RW failures.

The proposed approach is benchmarked against PD control and leading
DRL algorithms. Experimental results show that TD3-HD achieves signif-
icantly lower attitude error, improved angular velocity regulation, and en-

∗Corresponding author: geldalahmeh@swin.edu.au
Email addresses: geldalahmeh@swin.edu.au (Ghaith El-Dalahmeh),

rjabbarpoursattari@swin.edu.au (Mohammad Reza Jabbarpour), bvo@swin.edu.au
(Bao Quoc Vo), Ryszard.Kowalczyk@unisa.edu.au (Ryszard Kowalczyk)

Preprint submitted to Elsevier

July 14, 2025

hanced stability under fault conditions. These findings underscore the pro-
posed method’s potential as a powerful, fault-tolerant, on-board AI solution
for autonomous satellite attitude control.

Keywords: Deep Reinforcement Learning, Twin-Delayed Deep
Deterministic Policy Gradient, Hindsight Experience Replay, Attitude
Control, Reaction Wheels, Spacecraft Autonomy

Nomenclature

Attitude Determination and Control System
ADCS
A2C
Advantage Actor-Critic
Dimension-Wise Clipping
DWC
Deep Reinforcement Learning
DRL
Hindsight Experience Replay
HER
Low Earth Orbit
LEO
Markov Decision Process
MDP
Modified Rodrigues Parameters
MRP
Proportional-Derivative
PD
Proximal Policy Optimization
PPO
Reinforcement Learning
RL
Reaction Wheel
RW
Soft Actor-Critic
SAC
TD3
Twin Delayed Deep Deterministic Policy Gradient
TD3-HD TD3 with Hindsight Experience Replay and DWC
IS

Importance Sampling

1. Introduction

The increasing demand for small satellites in low Earth orbit (LEO) for
applications such as Earth observation, telecommunications, scientific re-
search, and defense has underscored the importance of precise and resilient
attitude control systems. In these missions, accurate orientation control is
critical to ensure that the satellite’s payload can perform optimally, collect-
ing high-quality data, or maintaining stable communication links with ground
stations [1]. As small satellites operate in environments with frequent dis-
turbances and limited resources, achieving high-performance attitude con-
trol has become a challenge. Traditional approaches, such as Proportional-
Derivative (PD) controllers and their variants, have served as reliable solu-

2

tions for standard attitude control tasks by correcting errors through simple
proportional and derivative gains. However, these methods can be sensitive
to changes in system dynamics, particularly in scenarios where hardware
components, such as reaction wheels (RWs), fail or experience degradation
[2]. When such faults occur, traditional control strategies often lack the
adaptability to compensate effectively, which can compromise overall mission
success and, in severe cases, may render the satellite incapable of performing
its intended functions.

RWs, key components of Attitude Determination and Control System
(ADCS), provide fine-grained control over satellite orientation by adjusting
the angular momentum. However, RWs are susceptible to wear, saturation,
and degradation over time, which increases the likelihood of failures that can
significantly compromise the stability of the ADCS [3]. Such failures may re-
sult in reduced pointing accuracy, increased oscillations, and, in severe cases,
complete loss of attitude control [1]. Addressing these issues requires robust,
fault-tolerant control mechanisms capable of adapting to RW performance
degradation and potential failures.
In scenarios involving unresponsive or
degraded RWs, the limitations of conventional control strategies become ev-
ident as they struggle to adapt dynamically to compensate for these hard-
ware issues. Recent advancements in artificial intelligence (AI) and, more
specifically, reinforcement learning (RL), have introduced new possibilities
for overcoming these challenges by offering adaptive, data-driven solutions
that can respond to changing system states in real-time. RL-based methods
are particularly suited for autonomous control applications, as they learn
to make optimal decisions through trial and error, enabling them to handle
unforeseen system changes, such as RW failures, in ways that traditional con-
trol systems cannot. This capability positions RL as a promising approach
for enhancing spacecraft resilience and ensuring mission continuity despite
component faults or operational uncertainties [4].

In light of these developments, this paper introduces a novel approach to
attitude control for small satellites based on the Twin-Delayed Deep Deter-
ministic Policy Gradient [5] with Hindsight Experience Replay [6] (TD3-HD)
algorithm. The TD3-HD method leverages the strengths of twin-delayed
gradients for stability in training and HER to efficiently handle sparse or
challenging reward scenarios, making it well-suited for complex control tasks
under dynamic fault conditions. Dimension-Wise Clipping (DWC) [7] is also
integrated into the approach to further stabilize control by independently
managing torque adjustments for each RW, preventing overcorrections or

3

undercorrections that could destabilize the system in cases of partial actua-
tor failures. The goal of this study is to assess the feasibility and benefits of
applying TD3-HD in the context of ADCS, aiming to improve the resilience,
adaptability, and control precision of the system under both normal oper-
ations and failure scenarios, such as when RWs become unresponsive. The
key contributions of this paper are as follows.

• Presenting an in-depth overview of existing control methods and RL-
based approaches to assess their strengths and weaknesses in the con-
text of spacecraft attitude control.

• Introducing TD3-HD as an advanced deep reinforcement learning (DRL)
algorithm specifically tailored to address fault-tolerant attitude control
in spacecraft, offering a robust alternative to traditional PD and DRL-
based controllers.

• Providing extensive comparison between TD3-HD with other DRL al-
gorithms, including Proximal Policy Optimization (PPO), Advantage
Actor-Critic (A2C), and Twin-Delayed Deep Deterministic Policy Gra-
dient (TD3), to assess their control performance under both nominal
and failure scenarios.

This paper is organized as follows: Section 2 reviews related work on tradi-
tional and recent DRL methods for spacecraft attitude control, emphasizing
fault tolerance and the limitations of DRL algorithms. Section 3 formu-
lates the satellite attitude control problem in the context of an unresponsive
RW, defining control objectives and fault-tolerant strategies. Section 4 intro-
duces our proposed TD3-HD with DWC methodology, detailing the reward
function design and objective function to manage RW faults. Section 5 de-
scribes the experimental setup using the Basilisk simulation framework to
evaluate TD3-HD’s fault-tolerance in unresponsive RW scenarios. Section
6 presents the results, comparing TD3-HD with PD, PPO, A2C, and stan-
dard TD3, demonstrating its superior stability and accuracy in maintaining
control under fault conditions. Section 7 summarizes the findings, highlight-
ing TD3-HD’s advantages in adaptability and precision over traditional and
DRL-based approaches. Section 8 conclusion and future work.

4

2. Related Works

This section reviews the current state-of-the-art in spacecraft attitude
control, focusing on traditional methods and recent advancements in RL-
based control systems. An Overview of studied approaches is represented
in Figure 1. Relevant research on spacecraft control and autonomy is also
discussed.

Figure 1: Overview of studied approaches

2.1. Background

Various advanced control methods have been applied to spacecraft atti-
tude control, alongside traditional methods like Proportional (P) controllers.
These include Sliding Mode Control (SMC) for robustness, adaptive control
for handling system variability, fuzzy logic for managing imprecise data, and
neural networks for learning complex, and nonlinear dynamics. Each ap-
proach has shown significant promise, contributing to ongoing advancements
in spacecraft resilience and autonomy.

• Proportional controllers: Proportional-Derivative (PD) and Proportional-
Integral-Derivative (PID) controllers have been widely used for space-
craft attitude control due to their simplicity and ability to achieve high
pointing accuracy under stable conditions. However, as shown in Ta-
ble 1, their performance is significantly constrained in the presence of

5

disturbances, rapidly changing environmental conditions, or uncertain-
ties in system parameters [8]. These limitations arise from the use of
fixed gains, which reduce their adaptability to nonlinearities and time-
varying dynamics inherent in spacecraft operations [9, 10].

Method
P Control

PI Control

PD Control

PID Control

errors,

Eliminates
state
precision
Reduces
fast response
Simple
widely applied

Advantages
Simple,
response

low cost, fast

Disadvantages
Cannot
steady-state errors

eliminate

steady-
higher

Slow response to rapid
changes

Comments
Combine with PI or
PD for better perfor-
mance.
Adaptive PI can re-
duce manual tuning.

Ref.
[11,
12]

[12,
10]

overshoot,

structure,

Cannot handle steady-
state errors
Requires tuning, not
robust to disturbances

Hybridize with PID or
fuzzy logic.
Adaptive
proves robustness.

PID im-

[9]

[12,
13]

Table 1: Comparison of Proportional controllers

• Sliding Mode Control: Sliding Mode Control (SMC) provides a robust
solution to spacecraft attitude control, overcoming the limitations of
traditional PID controllers by handling disturbances and uncertainties,
such as actuator faults. As summarized in Table 2, various SMC vari-
ants have been developed to mitigate chattering and enhance control
performance. Adaptive SMC [14] enhances system flexibility by es-
timating disturbances in real-time. However, despite its effectiveness,
SMC suffers from chattering and high computational demands, limiting
its applicability in systems with constrained resources.To mitigate these
drawbacks, several enhancements have been introduced. Fuzzy Sliding
Mode Control (FSMC), for instance, integrates fuzzy logic to reduce the
chattering effect, as demonstrated in [15]. This integration improves
control smoothness, although it increases computational complexity
due to the need for precise tuning of fuzzy parameters. In a similar ef-
fort, Minimum Sliding Mode Error Feedback Control (MSMEFC) [16]
enhances control precision by minimizing sliding mode error. While this
approach improves accuracy, it comes with the trade-off of increased
computational load and heightened sensitivity to parameter tuning. In
addition to these improvements, Adaptive Non-Singular Terminal Slid-
ing Mode Control (ANSTSMC) [17] tackles the chattering issue through
adaptive tuning while avoiding singularities. Though ANSTSMC offers

6

smoother control and finite-time convergence, its complexity restricts
its real-time applicability in resource-constrained environments. Like-
wise, Adaptive Fuzzy Sliding Mode Control (AFSMC) [18] combines
fuzzy logic with adaptive SMC, dynamically adjusting control laws to
enhance tracking accuracy. Despite these improvements, the increased
computational burden poses a challenge for systems with limited pro-
cessing power. Furthermore, Integral Sliding Mode Control (ISMC)
[19] incorporates integral action into the SMC framework to improve
steady-state accuracy in the presence of persistent disturbances. While
this method demonstrates strong performance in managing uncertain-
ties and actuator faults, its complexity and high processing require-
ments make real-time implementation difficult for systems with limited
resources. In [20] a study that addressed the challenge of mitigating
reaction wheel assembly (RWA) jitter in micro-satellites, which can
significantly degrade attitude control accuracy due to their small mo-
ments of inertia. the authors proposed a combined approach using a
Sliding Mode Controller (SMC) and an adaptive moment distribution
algorithm to reduce jitter effects. The SMC ensures robust control un-
der bounded disturbances, while the adaptive algorithm dynamically
redistributes control torques based on wheel speeds, imposing limits
to reduce vibration-induced disturbances. Simulation results demon-
strate that this combination achieves high precision, reducing attitude
errors to as low as 0.001°, a marked improvement over traditional PD
controllers. However, the method relies on simplified jitter models, and
requires careful tuning to balance speed limits and actuator saturation.

In summary, although these advancements in SMC significantly im-
prove robustness, control precision, and disturbance rejection capabili-
ties, they introduce trade-offs in terms of complexity and computational
demands. As a result, further optimization is necessary to make these
methods more practical for real-time spacecraft applications, particu-
larly in systems with constrained resources.

7

Method
SMC

FSMC

ISMC

distur-
low computa-

Advantages
Robust
to
bances,
tional cost
Handles uncertainties,
reduces chattering
Effective in magnetic
attitude control

Disadvantages
Causes chattering, ac-
tuator wear

computational

High
cost
Cannot fully neutralize
disturbances

ANSTSMC

Fast
strong robustness

convergence,

Computationally
manding

de-

Comments
FSMC,
AFSMC,
ISMC reduce chatter-
ing.
Hybrid methods opti-
mize performance.
Non-linear
dynamics
improve output con-
trol.
Suitable where preci-
sion outweighs cost.

Ref.
[14]

[15]

[19]

[17]

Table 2: Comparison of Sliding Mode Control Variants

• Backstepping controller: The researchers in [21], introduced Backstep-
ping as a solution for nonlinear control systems, particularly effective
for ensuring stability by dividing the system into smaller subsystems.
This step-by-step approach improves trajectory tracking and system ro-
bustness. In space manipulators, Backstepping works alongside sliding
mode control to maintain performance despite uncertainties and distur-
bances. As summarized in Table 3, several variations of Backstepping
have been proposed to address these challenges. For instance, [22] used
Backstepping with the Modified Rodrigues Parameters (MRP) model
and an extended state observer for satellite attitude control under dis-
turbances. While effective, it increases computational complexity and
introduces chattering. Similarly, [23] proposed an adaptive Backstep-
ping fault-tolerant control (FTC) for handling actuator faults, though
it faces issues with chattering and computational intensity. Lastly,
[24] applied Backstepping to microsatellites with inertia uncertainties,
showing good results but requiring fine-tuning and posing computa-
tional challenges for real-time use in resource-limited systems.

Despite its benefits, Backstepping can lead to high computational de-
mands and the chattering effect, both of which hinder real-time imple-
mentation, especially in systems with limited processing power. Addi-
tionally, the need for precise tuning makes it challenging for adaptive
and dynamic environments

8

Method
Backstepping

Adaptive Back-
stepping

Advantages
Handles nonlinearities,
Lyapunov stability
Adapts to uncertain-
ties, high precision

Disadvantages
Computationally
pensive
High complexity, tun-
ing required

ex-

techniques

Comments
Adaptive
enhance flexibility.
ML/fuzzy systems im-
prove real-time use.

Ref.
[22]

[24]

Table 3: Comparison of Backstepping-Based Methods

• H∞ controller:

In [25], researchers developed the H∞ control tech-
nique as a robust solution to handle uncertainties, disturbances, and
noise in control systems. It ensures system stability even when exact
models of environmental conditions are unavailable, making it highly
suitable for managing complex space systems. H∞ control optimizes
worst-case disturbance rejection, providing strong resilience in unpre-
dictable environments. As outlined in Table 4, various implementations
of H∞ control have been proposed to enhance spacecraft resilience. For
instance, [26] addressed attitude control in spacecraft with actuator
misalignments and external disturbances using a nonlinear H∞ con-
troller, which ensures stability by solving the Hamilton–Jacobi–Isaacs
(HJI) equation through the Chebyshev–Galerkin method. While ef-
fective, this approach’s mathematical complexity can lead to conser-
[27] applied
vative performance under nominal conditions.Similarly,
a backstepping-based nonlinear H∞ controller to flexible spacecraft,
achieving vibration suppression and finite-time stability during large-
angle maneuvers. However, the method’s intricate calculations and
extensive parameter tuning present challenges for real-time implemen-
tation, especially in systems with limited resources.

Despite its robustness, H∞ control’s complexity leads to high compu-
tational demands and conservative performance in typical scenarios.
These trade-offs highlight the need for further research to improve ef-
ficiency and adaptability for real-world satellite missions.

Method
H-infinity

backstepping-
based H∞

Advantages
High robustness, per-
formance bounds
Energy-efficient, fault-
resilient

Disadvantages
Complex design, ma-
trix equation solving
Limited
handling

maneuver

Comments
Efficient
computa-
tional techniques help.
Extend for orbital dy-
namics.

Ref.
[26]

[27]

Table 4: Comparison of H∞ Control Techniques

9

However, although these control techniques provide some level of resilience,
they do so inefficiently due to their complexity and computational burdens.
This inefficiency limits their practical use in real-time applications, particu-
larly in small satellite systems. Further research is required to optimize these
methods, making them both resilient and efficient for real-world, resource-
constrained spacecraft missions. By addressing these limitations, future de-
velopments can aim to produce control solutions that are not only robust
but also scalable and practical for real-time satellite operations. In recent
years, RL has garnered substantial attention for its potential in spacecraft
attitude control. Consequently, the following section provides a comprehen-
sive overview of its application to spacecraft RW control, highlighting key
methodologies, benefits, and challenges associated with this approach.

2.2. RL in Spacecraft Attitude Control

Artificial Intelligence (AI) has been acknowledged for its capability to
address complex, real-world problems for many years [28]. While founda-
tional deep learning techniques like backpropagation were developed in the
1990s [29], their broader adoption was delayed until advancements in hard-
ware and the availability of large datasets made them more feasible. Early
attempts to apply AI to satellite control, such as those conducted at INPE
[30], demonstrated promise but were limited by the technological capabilities
of the time. As AI and ML evolved, these technologies rekindled interest in in-
telligent control systems. RL, which shares a strong connection with optimal
control theory [31], enables agents to learn behaviours through interaction
with their environments, eliminating the necessity for precise mathematical
models. As detailed in Table 5, various RL algorithms such as SAC, PPO,
TD3, and A2C have been explored for their adaptability, robustness, and po-
tential to handle nonlinearities and actuator faults. Major advancements in
RL, such as the introduction of Deep Q Networks [32], significantly expanded
its applicability to large state spaces by using neural networks to approxi-
mate the state-action value function, Q(s, a). Building on this foundation,
the Deep Deterministic Policy Gradient (DDPG) algorithm [33] was intro-
duced to handle continuous action spaces. Later advancements, including
Twin-Delayed DDPG (TD3) [5] and Soft Actor-Critic (SAC) [34], addressed
challenges like overestimation bias in DDPG, leading to enhanced training
stability and efficiency. Furthermore, policy gradient methods such as Prox-
imal Policy Optimization (PPO) [35] and Trust Region Policy Optimization
(TRPO) [36] became widely adopted due to their reliable and robust per-

10

[37] addresses the challenge of spacecraft attitude control under
formance.
nonlinear dynamics, external disturbances, and model uncertainties, where
traditional optimal control methods are limited by high computational de-
It proposes an analytical predic-
mands and sensitivity to local minima.
tive controller based on Sequential Action Control (SAC), which calculates
closed-form control actions within a receding horizon, eliminating the need
for iterative optimization. The method is fast, robust to disturbances and
model mismatches, easy to implement for jet thrusters or flywheels, and
shows low sensitivity to initial conditions. However, the reliance on line
search for action duration, which can be computationally inefficient. RL has
seen extensive success in robotics, with notable applications in legged robots
[38] and robotic hand manipulation [39]. More recently, RL has been uti-
lized in the aerospace domain. For instance, [40] combined RL for high-level
guidance with a PD controller for spacecraft attitude control during dock-
ing maneuvers. The DRL approach may struggle with robustness against
specific faults and often requires retuning of the PD controller to maintain
stability. Sparse rewards can slow learning, requiring many interactions, and
the method is computationally intensive, limiting real-time applicability. To
address spacecraft attitude control during post-capture maneuvers with un-
known dynamics, a Q-learning-based RL controller was proposed [41], lever-
aging system input/output data to develop a model-free control strategy
and eliminating the need for dynamic model identification. However, the Q-
learning approach may struggle with robustness in uncertain environments
due to the lack of a system dynamics model. Additionally, it is computation-
ally intensive and slowed by sparse rewards, requiring numerous interactions
to achieve reliable control in high-uncertainty settings. In [42] authors pro-
posed an adaptive fault-tolerant control (FTC) method for spacecraft using a
Stackelberg game model integrated with Advantage Actor-Critic (A2C) RL.
The approach addresses the challenge of maintaining spacecraft stability and
efficiency under fault conditions by structuring FTC as a dynamic interac-
tion between two players: a Fault-Tolerant Control (FTC) unit and a Fault
Detection Observer (FDO). The A2C framework enables these units to adapt
in real-time, improving resilience against faults. While promising, the solu-
tion requires high computational resources and may face scalability issues in
multi-agent or complex environments, which the authors suggest as a focus
for future research. Addressing the problem of control during debris removal
missions is investigated in [43], where changes in mass distribution after
debris capture render traditional PID controllers insufficient due to their re-

11

liance on fixed system parameters. To overcome this, the authors proposed a
Deep Reinforcement Learning (DRL)-based adaptive control approach using
algorithms like Soft Actor-Critic (SAC) and Proximal Policy Optimization
(PPO) with a novel stacked observations technique. This method enables
the system to infer dynamic properties, such as mass, indirectly from his-
torical states and actions, improving adaptability across a wide mass range
(10–1,000 kg). Simulations in the Basilisk framework demonstrate superior
adaptability and robustness of the DRL-based system compared to PID con-
trollers. However, still there is instability in extreme mass cases. A recent
study [44] addresses a key challenge in RL-based spacecraft control by intro-
ducing a reward-shaping mechanism that guides agents using outputs similar
to those of traditional PID controllers. This technique, termed expert-guided
exploration (EGE), improves fault tolerance by efficiently directing the RL
agent’s actions, particularly in environments with actuator or sensor mal-
functions. By comparing RL and PID-like control outputs, EGE reduces the
time needed to reach optimal policies, mitigating the risk of local minima and
improving control robustness under uncertain conditions.While effective, the
EGE approach’s reliance on predefined similarity metrics may limit its full
autonomy, as it necessitates expert input for optimal tuning and control vec-
tor adjustments. However [44] also note that its computational complexity
may impact real-time application feasibility for spacecraft with constrained
onboard resources. A DRL-based approach for six degrees-of-freedom plan-
etary landing, particularly for Mars exploration missions, was presented in
[45]. The system employed PPO to map the estimated state of the lander
directly to thrust commands, achieving both high accuracy and fuel-efficient
trajectories. While the system showed robustness in simulations, The pri-
mary challenages of PPO include a high demand for samples, which makes
training resource-intensive and time-consuming, and a sensitivity to hyperpa-
rameter tuning, impacting performance stability. While clipping aids stabil-
ity, it can restrict exploration, sometimes trapping the agent in local optima.
PPO also typically relies on multiple parallel environments for optimal re-
sults, adding to the computational load in complex applications. Recent
advances in DRL have highlighted the potential of model-free approaches
to enhance satellite attitude control, particularly in RW management. For
instance, [46] presents a model-free attitude control solution for spacecraft
using a PID-guided Twin-Delayed Deep Deterministic Policy Gradient (TD3)
algorithm. This method seeks to address control challenges, such as external
disturbances and control torque saturation, by employing RL techniques that

12

enhance convergence speed and control stability. The incorporation of a PID
guide for TD3 accelerates learning, potentially overcoming the slow training
associated with TD3 in environments lacking prior knowledge. This study
contributes to the growing application of RL in spacecraft control, demon-
strating improved accuracy and adaptability under conditions of unknown
dynamic parameters. However, as the authors noted that the deployment of
the proposed solution in real-time space environments remains challenging
due to the computational demands of pretraining and fine-tuning processes.
In [47], a Twin Delayed Deep Deterministic Policy Gradient with Priori-
tized Experience Replay (TD3-PER) was applied to the Diwata microsatel-
lite, demonstrating significant improvements in sample efficiency and control
stability. By leveraging prioritized experience replay, the study effectively
reduced training time while maintaining precise attitude control, which is
crucial for microsatellites operating under limited computational resources.
However, TD3 with Prioritized Experience Replay (TD3-PER) is limited in
handling partial actuator failures, such as an unresponsive RW, as it was
designed for systems that face only environmental disturbances, not internal
control failures, and lacks adaptive mechanisms for fault tolerance, leading
to degraded control performance under fault conditions. Motivated by the
success of DRL in satellite attitude control, this study explores its applica-
tion to address the critical challenge of unresponsive RW—a gap not fully
covered in previous works. Managing unresponsive RWs is essential for main-
taining satellite stability, and this research seeks to develop advanced control
strategies to address such faults effectively. Standard TD3 has limitations
in these scenarios, struggling with fewer successful outcomes, slow learning
from failure cases, and limited exploration, which makes it less effective for
controlling satellites with failed RWs. Building on these insights, the present
study integrates HER with TD3, creating TD3-HD to enhance fault tolerance
specifically in cases of unresponsive RWs. TD3-HD accelerates adaptation by
enabling the agent to learn from unsuccessful attempts, addressing the short-
comings of standard TD3. Furthermore, DWC is incorporated to stabilize
control by independently managing torque adjustments for each RW, pre-
venting excessive or insufficient responses that could destabilize the system.
This combined approach offers a novel solution to autonomously manage
RW faults, providing a robust alternative to traditional methods such as PD
control in the dynamic environment of low-Earth orbit.

13

Method
SAC

PPO

TD3

DDPG

Q-learning

Advantages
Adaptable to distur-
bances

Stable learning,
able control
Stable, low energy use Hyperparameter-

reli-

Disadvantages
High
computation,
needs stacked observa-
tions
Computationally
manding

de-

sensitive
Prone to instability

Computationally
in-
tensive, sparse rewards

computational
scalability

High
resources,
issues
Adapts dynamically to
mass variations

Learns complex poli-
cies efficiently
Model-free, adaptable
to unknown dynamics

A2C

Real-time adaptability,
fault-tolerant

PPO stacked

overall perfor-

Best
mance

SAC stacked

More generalized ap-
proach

Adapts dynamically to
mass variations

EGE

Guided
fault-tolerant

exploration,

TD3-PER

PPO

High sample efficiency,
stable control
High accuracy,
efficient trajectories

fuel-

on

expert
computa-

Reliance
knowledge,
tional overhead
Reward function tun-
ing challenges
High sample demand,
hyperparameter sensi-
tivity

Comments
Stacking improves per-
formance.

Ref.
[37]

Combine with other
RL methods.
Delayed updates stabi-
lize control.
Actor-Critic improves
learning.
Suitable
uncertainty
ments.
Promising for multi-
agent systems.

high-
environ-

for

consistent

Slightly better at lower
masses More
robust
than PID but less con-
sistent
at
More
higher masses More
robust than PID but
never fully settles
Balances guidance and
exploration.

[47]

[46]

[46]

[41]

[42]

[43]

[43]

[44]

resource-

Optimizes
constrained systems.
Robust for planetary
landings.

[47]

[45]

Table 5: Comparison of RL Methods

3. Problem Formulation

The spacecraft’s attitude is defined by how its body-fixed coordinate sys-
tem aligns with the orbital coordinate system. The attitude describes the
orientation of its body-fixed frame relative to the orbital frame. There are
five common ways to describe attitude: Euler angles, Rotation Matrices,
Quaternions, Rodrigues Parameters (RP), and Modified Rodrigues Param-
eters (MRP). These methods can be converted into one another, with their

14

details available in references [48], [49]. In this study, the body’s orientation
relative to the inertial frame is expressed using MRPs because they smoothly
represent eigenaxis rotations up to 360 degrees without ambiguities or dis-
continuities [50]

3.1. Spacecraft Attitude Kinematics and Dynamics

In the context of spacecraft kinematics and dynamics, satellite kinematics
is the study of how a satellite’s orientation changes over time, focusing on its
rotation without considering forces [51]. The kinematic equation in terms of
MRPs is given by [52]:

˙ρ = Gρω

(1)
where ω ∈ R3×1 is the angular velocity vector relative to the inertial
frame, and Gρ represents a kinematic transformation matrix that relates the
time derivative of the MRPs, ˙ρ, to the spacecraft’s angular velocity vector ω
and calculated as follows:

Gρ =

1
2

(cid:18)

I − S(ρ) + ρρT −

(cid:19)

,

ρT ρI

1
2

(2)

where I is the identity matrix of appropriate dimensions, S(·) represents a
skew-symmetric matrix. The MRPs are defined as ρi = qi/(1+q0), where ¯q =
[q0, qT ]T ∈ R × R3 represents the spacecraft quaternions, and q = [q1, q2, q3]T .
Thus, MRPs are ρ = [ρ1, ρ2, ρ3]T .

While satellite dynamics focuses on a satellite’s motion, including orien-
tation changes (kinematics) and the effects of forces to ensure stability and
control in space [51], the rotational motion of a rigid spacecraft with fully
functioning actuators is governed by the following dynamics equation [52, 53]:

J ˙ωt − S(ωt)Jωt = ut

(3)

In this equation, J ∈ R3×3 is the spacecraft’s moment of inertia matrix, which
is symmetric and positive-definite, reflecting how the mass is distributed
about its three principal axes. The term ωt ∈ R3 represents the spacecraft’s
angular velocity vector at time t, and ˙ωt is its time derivative—i.e., the
angular acceleration.

The term S(ωt)Jωt accounts for gyroscopic torques (Coriolis effects),
where S(ωt) is the skew-symmetric matrix that performs the cross product

15

operation with ωt. This captures the nonlinear coupling between rotational
axes during angular motion.

The right-hand side, ut = [u1, u2, u3, u4] ∈ R4, represents the total con-
trol torque generated by four reaction wheels (RWs). Each RW contributes
torque about a specific axis by changing its spin rate. The wheels operate
within a rotational speed range of [−1500, 1500] revolutions per minute and
have a moment of inertia of 4.67 × 10−4 kg·m2, enabling fine-grained control
of the spacecraft’s angular momentum.

The control system aims to align the spacecraft’s current orientation rep-
resented using Modified Rodrigues Parameters (MRP)—with a desired target
orientation. The difference between the current and target orientation is de-
noted as the attitude error MRPerror, which is favored for its compactness
and ability to avoid singularities.

To formally model and solve the spacecraft attitude control problem,
a Markov Decision Process (MDP) formulation is introduced in the next
section.

3.2. Markov Decision Process Formulation

Spacecraft attitude control is framed as a Markov Decision Process (MDP).
This formulation enables the application of Deep Reinforcement Learning
(DRL) to develop optimal control strategies for maintaining the spacecraft’s
orientation. Within this context, the spacecraft is modeled as an intelligent
agent that interacts with its environment, adapting its actions to ensure sta-
bility and control even under challenging conditions, such as an RW failure.

The MDP is defined as:

M DP = (S, A, T, P, r)

(4)

A Markov Decision Process (MDP) is defined as a tuple (S, A, T, P, r),
where: The state space S represents all potential configurations of the system.
The action space A encompasses all possible decisions the agent can make.
The set T , which is a subset of N, represents a sequence of time steps during
which the agent interacts with the environment. The transition function
P (s′|s, a) defines the probability of transitioning to a state s′ given the current
state s and action a. The reward function r(s, a) specifies the immediate
reward obtained by the agent when it takes action a in state s.

16

The state space at time t, denoted as st, includes key parameters rep-

resenting the spacecraft’s attitude error and angular velocity:

st = {MRPerror, ω}

(5)

where:

• MRPerror represents the Modified Rodrigues Parameters that quan-
tify the orientation error between the current and desired orientations.
This choice enables the state vector to describe the attitude error rel-
ative to the target orientation in a simple, compact form, avoiding the
complexity and potential singularities associated with other represen-
tations, such as Euler angles. By using MRPs, we can maintain a
consistent, relative frame for error calculation, streamlining real-world
implementation by removing any reliance on an arbitrary inertial ref-
erence frame [54].

• ω is the angular velocity of the spacecraft relative to an inertial frame,
a parameter crucial for tracking the spacecraft’s rotational dynamics.
Specifically, ω provides information on the instantaneous rotation rate
of the spacecraft’s body with respect to a fixed external reference. This
velocity measurement allows the control system to make corrections
that stabilize and adjust the spacecraft’s attitude as it seeks the target
orientation. Including ω in the state vector is essential for capturing
the spacecraft’s current motion state, enabling the agent to understand
both the direction and magnitude of rotations. This, in turn, supports
effective control strategies for damping oscillations and precisely orient-
ing the spacecraft, particularly under conditions where reaction wheel
limitations may impact stability

The action space at includes the control commands applied to the RWs:

at = {τ1, τ2, τ3, τ4}

(6)

where τi is the torque applied to the RW. In case of a fault where a RW be-
comes unresponsive, the control system must redistribute torque across the
remaining functional wheels and activate a backup RW to maintain control
and stability. The goal of the control policy π(st) is to minimize attitude er-
ror and regulate angular velocity. To achieve this, we employ the TD3 (Twin
Delayed Deep Deterministic Policy Gradient) with HER and DWC, which

17

stabilizes learning by clipping control inputs, especially in fault conditions
that could destabilize the spacecraft.

To train the DRL agent and simulate the spacecraft’s environment, we use
the Basilisk simulation framework. Basilisk provides a high-fidelity environ-
ment to simulate spacecraft dynamics and control subsystems, allowing for
robust training of the DRL agent under dynamic and fault-prone conditions
[55]. By simulating real-time spacecraft operations, including RW faults,
As illustrated in Figure 2, Basilisk enables the agent to interact with the
spacecraft’s control system, adapt its actions, and maintain stability. Using
Basilisk as the simulation environment, this approach allows the spacecraft
to autonomously manage faults, adapt control actions, and maintain attitude
control in unpredictable space environments.

Figure 2: Interaction of Agent with Environment via Basilisk

4. Proposed Approach:

In this section, we propose a TD3-HD approach to address the problem
of spacecraft attitude control under unresponsive RW. When an RW becomes
unresponsive, the proposed algorithm dynamically redistributes the torque
to functional RWs and enables backup RW to compensate. The algorithm
incorporates Dimension-Wise Clipping (DWC) to ensure stable action
updates and Hindsight Experience Replay (HER) to improve learning
efficiency in sparse reward environments.

18

4.1. Twin-delayed deep deterministic policy gradient (TD3):

TD3 is an off-policy, actor-critic, policy gradient algorithm that builds
on Deep Deterministic Policy Gradient (DDPG) [33], a popular method for
continuous control tasks. However, DDPG often experiences instability and
is highly sensitive to hyperparameter settings, primarily due to overestimated
Q-values in the critic network. This overestimation can accumulate over time,
leading the agent to converge to suboptimal solutions. TD3 addresses these
challenges by introducing three major enhancements: (1) utilizing two critic
networks, (2) delaying actor network updates, and (3) applying action noise
regularization [5].

4.2. Hindsight Experience Replay (HER):

HER effectively tackles the well-known challenge of sparse rewards in
reinforcement learning by transforming unsuccessful episodes into valuable
learning experiences [56].
In spacecraft attitude control tasks—especially
under actuator faults such as unresponsive reaction wheels—the agent may
receive minimal feedback if the reward is only granted upon full stabilization.
This severely limits the agent’s ability to learn effective control strategies
early in training. HER overcomes this by retrospectively redefining the goals
within each trajectory to match outcomes the agent actually achieved (e.g.,
intermediate attitude states), thereby converting failure into simulated suc-
cess. This significantly increase the reward space, accelerating convergence
and improving the agent’s adaptability to fault scenarios.

Compared to other sparse reward mitigation techniques, HER stands out
for its simplicity, generality, and effectiveness in goal-conditioned environ-
ments [57]. Alternatives like intrinsic motivation methods such as curiosity-
driven exploration can promote broader state-space exploration but often
lack task specific focus [58]. Curriculum learning, where agents progress
from easy to hard tasks, also shows promise but requires careful manual tun-
ing and domain expertise to define appropriate training progressions [59]. In
contrast, HER provides a plug-and-play solution that dynamically leverages
the agent’s own experience to improve learning efficiency without requiring
manual reward engineering or additional exploratory incentives. This makes
HER particularly well suited for space applications, where stability and ro-
bustness under fault conditions are critical.

19

4.3. Dimension-Wise Clipping (DWC):

To address the problem of maintaining stability during updates in com-
plex environments, the algorithm restricts updates within a defined range to
prevent excessively large changes that could destabilize the system. However,
this restriction can lead to zero-gradient problem [60]. This issue becomes
particularly problematic in high-dimensional action spaces, such as those re-
quired to control multiple reaction wheels, as it hinders effective learning
[61]. To overcome this limitation, TD3-HD integrates Dimension-Wise Clip-
ping (DWC), a technique introduced by [62].

In DWC, the policy gradient updates are clipped independently for each

dimension of the action space. Specifically:

• Parameters clipped: DWC applies independent clipping to each di-
mension of the policy gradient ∇θJ(θ), where each dimension corre-
sponds to an individual reaction wheel’s torque adjustment.

• Clipping mechanism: For each dimension i, the gradient component
∇θJ(θ)i is clipped to a range [−ci, ci], where ci is the clipping threshold
for that dimension. This means each component is restricted to its own
specific range, rather than applying a uniform clipping to the entire
gradient vector.

• Threshold determination: The clipping thresholds ci are deter-

mined based on:

– Adaptive thresholds calibrated to the historical variance of gradi-

ents in each dimension

– Physical constraints of each reaction wheel, including maximum

torque capacity

– Expected operational ranges for different control scenarios, includ-

ing fault conditions

DWC independently clips the torque adjustments for each RW, thereby
preventing destabilizing updates without causing zero-gradient issues in unaf-
fected dimensions. This preservation of learning signals in stable dimensions
allows training to proceed efficiently even when some reaction wheels require
significant adjustment while others need only minor corrections. This method
significantly enhances the sample efficiency of TD3-HD by maintaining sta-
bility and responsiveness, even in the presence of faults. As a result, TD3-HD

20

becomes highly effective for robust satellite attitude control, particularly in
scenarios involving reaction wheel failures.

4.4. Torque Redistribution

When an RW becomes unresponsive, TD3-HD clips the corresponding
action dimension, preventing further updates to that RW. The remaining
active RWs receive updated actions based on the redistributed torque. The
backup RW is activated only when necessary to ensure continuous control of
the spacecraft’s attitude.

The total control torque T applied to the satellite is calculated as:

T =

3
(cid:88)

i=0

λiRWi

(7)

where RWi is the torque applied by each RW, and λi is the policy parameter
for each RW.

The parameter λi acts as a weighting factor that governs the contribution
of each RW to the net control torque. These weights are dynamically adapted
only for the currently active wheels.
In nominal conditions, all active λi
values are equal, assuming symmetric contribution. If an RW becomes faulty,
its corresponding λi is set to zero, effectively excluding it from the control
torque calculation. The remaining λi values are renormalized over the set
of operational RWs to preserve control authority. When the backup RW
is activated, it is assigned a non-zero λi and included in the redistribution
scheme, ensuring seamless fault recovery and attitude control.

4.5. Reward Function

A reward function serves as a fundamental tool in reinforcement learning,
guiding an agent’s behavior toward achieving specific objectives [63]. It pro-
vides feedback by assigning a numerical value, or ”reward,” to each action or
state, reflecting how well the agent’s behavior aligns with the desired goals.
The reward function plays a critical role in defining the learning objective
and encouraging the agent to make decisions that optimize long-term out-
comes. It effectively balances competing priorities, driving the agent toward
desirable behavior while penalizing undesirable actions [63]. Our reward
function is specifically designed to minimize attitude error while penalizing
large angular velocities, comprising three components:

21

• Attitude Error Reduction Reward:

The reward function for attitude error reduction is defined as:

r1 = eprevious − ecurrent

(8)

where:

– eprevious represents the attitude error at the previous time step.
This reflects the difference between the spacecraft’s desired and
actual orientations at that earlier moment. It serves as a reference
to determine if the attitude error is decreasing over time.

– ecurrent represents the attitude error at the current time step, calcu-
lated similarly to eprevious. It reflects the current difference between
the desired and actual orientations.

• Penalty for High Angular Velocities:

r2 =

(cid:40)

−10,
0,

if |ω| > 1
otherwise

(9)

where ω is the angular velocity. High angular velocities are penalized
to prevent instability and ensure safe control actions.

• Accuracy Incentive:

r3 =

(cid:40)

if ecurrent < 0.25

0.01,
−0.01, otherwise

(10)

This component encourages precise attitude control by rewarding low
attitude errors. The threshold value of 0.25 degrees was selected based
on industry standards for high-precision satellite pointing requirements
[64]. This value represents a balance between achievable physical per-
formance given the hardware constraints of typical reaction wheel sys-
tems and mission requirements for Earth observation and scientific in-
struments. Experimental validation confirmed this threshold as opti-
mal - lower values (e.g., 0.1 degrees) led to excessive control effort and
oscillatory behavior without meaningful improvement in steady-state
accuracy, while higher thresholds (e.g., 0.5 degrees) resulted in insuffi-
cient pointing precision for typical mission requirements. Additionally,

22

the 0.25-degree threshold aligns with the capabilities of modern star
trackers and inertial measurement units, ensuring the control system
operates within the reliable detection range of the attitude determina-
tion systems [65].

The overall reward function is:

reward = r1 + r2 + r3

(11)

This function ensures that the spacecraft is rewarded for reducing attitude
error, penalized for unsafe angular velocities, and incentivized to maintain
accurate control.

The TD3 algorithm, known for its stable learning and capability of han-
dling continuous control problems [66], is enhanced with Dimension-Wise
Clipping (DWC), which independently limits action updates for each reac-
tion wheel (RW). This mechanism helps mitigate large and unstable updates
in the presence of faults [62]. Additionally, Hindsight Experience Replay
(HER) addresses the issue of sparse rewards by reinterpreting failed actions
as successes with modified goals [67], enabling the agent to learn effectively
even in scenarios involving unresponsive RWs. The pseudo-code for the pro-
posed method is outlined in Algorithm 1, and the network structure of the
TD3-HD with DWC system is illustrated in Figure 3. The system inte-
grates two primary neural networks: an actor network and a critic network.
The actor network, consisting of four sub-networks parameterized by λi (for
i = 1, 2, 3, 4), generates torque values for each RW by outputting Gaussian
parameters µi and σi, which are sampled to produce normalized torque ac-
tions ai (for i = 1, 2, 3, 4). These actions are applied to the satellite’s RWs
to adjust its attitude. During training, the satellite’s state, represented as
[MRPerror, ω] (where MRPerror denotes the Modified Rodrigues Parameters
for attitude error and ω represents the angular velocity vector), is stored in
the HER buffer E, which modifies failed trajectories by replacing goals with
future goals. The TD3-HD method uses batch training, where the actor net-
work updates its policy based on sampled transitions from E and then copies
its parameters to an ”old” network to ensure stability. DWC is applied to the
output of the old network, limiting large updates for each RW independently.
Additionally, Importance Sampling (IS) weights ρt are computed to correct
for mismatches between the behavior policy and target policy, feeding into

23

the TD3 operation. The critic network evaluates the generated torque ac-
tions by calculating an advantage value A1, which reflects the quality of the
actions. This advantage value, along with the IS weights and policy loss JIS,
is passed to the TD3 operation to finalize updates to the actor network. The
system ensures efficient and stable training, resulting in updated Gaussian
parameters µi and σi for torque actions ai, which are applied to the satellite’s
RWs to maintain and adjust its attitude.

24

Algorithm 1 TD3-HD with DWC

1: Input: Maximum iterations L, epochs K, HER goal sampling strategy,

DWC bounds.
2: Initialization:
3: Initialize actor network weights λi for i = 1, 2, 3, 4 (corresponding to each

RW).

4: Initialize Q-value critic networks for TD3.
5: Initialize Importance Sampling (IS) weighting factors αIS = 1, learning

rate ζ, and dimension-wise clipping thresholds for DWC.
state

storing

replay

6: Initialize

for

buffer
{(MRPerror, ω), a, r, (MRP′

E
error, ω′)}.

transitions

7: Load the satellite dynamics model, including RW faults or unresponsive

scenarios.

8: Main Loop: Interaction Phase
9: for iteration = 1 to L do
10:
11:
12:

Initialize the satellite’s states [MRPerror, ω]T , including RW faults.
Load the desired target states (goal orientation and angular velocity).
Store current actor network parameters λi ← λ (to retain a stable
policy reference).
Apply the actor policy πλi to sample actions a = [a1, a2, a3, a4].
Store state transitions (st, at, rt, st+1) in the replay buffer E, apply-
ing the HER strategy to modify episodes by sampling future goals as
desired goals.
Compute advantage estimates ˆAt using transitions from the HER
buffer E.

13:
14:

15:

16: end for
17: Training Loop
18: for epoch = 1 to K do
19:
20:
21:

for each gradient step do

Sample a mini-batch of size M from the replay buffer E.
Apply dimension-wise clipping (DWC) to action updates λi for each
RW, limiting large and unstable updates.
Update actor network weights:

λ ← λ + ζ∇λJIS(λ)

where JIS is the IS-weighted policy loss based on KL divergence.

end for
Update the IS weighting factor αIS adaptively to balance replay im-
portance.

25

25: end for

22:

23:
24:

Figure 3: Proposed TD3-HD structure.

5. Experimental Setup

The Basilisk Astrodynamics Simulation Framework [55] provides a high-
fidelity simulation environment for modeling the kinematics and dynamics
of a small satellite in Low Earth Orbit (LEO). Hence, this simulator is used
as simulation environment in our experiments The satellite’s orientation is
represented by Modified Rodrigues Parameters (MRPs) and controlled using
four Honeywell HR16 RWs arranged in a pyramid configuration. These RWs
deliver torque adjustments to maintain the desired attitude of the satellite.
To evaluate the fault tolerance of various control strategies, an RW failure
is simulated by disabling one of the wheels at 3000th second. Key telemetry
data, including MRP, angular velocity, and RW torque, are recorded over a
8000-second period.

This study evaluates advanced DRL algorithms for CubeSat attitude con-
trol, focusing on the proposed TD3-HD algorithm. TD3-HD enhances control
performance under actuator faults by integrating HER for improved learning
in sparse reward environments. Additionally, Proximal Policy Optimization
(PPO) [68], known for its robustness in complex tasks and stable policy up-
dates, is assessed alongside Advantage Actor-Critic (A2C) and the standard
Twin Delayed Deep Deterministic Policy Gradient (TD3), which serves as a
baseline for reliable CubeSat attitude control [47].

This comprehensive evaluation provides a comparative analysis of each

26

algorithm’s strengths and suitability for autonomous CubeSat attitude con-
trol.

All DRL algorithms in this study are implemented using the Stable-
Baselines3 library [69], an open-source toolkit built on PyTorch that facili-
tates efficient and reliable model development for DRL research. For training
the neural networks, a custom simulation environment is created in Python,
adhering to the OpenAI Gym standards [70]. This standardization ensures
a flexible interface for simulating interactions and enables seamless integra-
tion of the DRL algorithms. Figure 4 provides an overview of the simulation
configuration.

Figure 4: Simulation configuration used for satellite attitude control.

The following table outlines the training parameters used for the TD3-HD
algorithm. These parameters are used for optimizing the spacecraft attitude
control system and ensuring effective learning under dynamic conditions.
TD3-HD exhibited stable and reliable performance using standard hyperpa-
rameter settings in (Table 6) without the need for extensive tuning. The
integration of HER and DWC contributes to this robustness by improving
learning stability and mitigating the effects of sparse rewards. These char-
acteristics make TD3-HD a practical and resilient choice for autonomous
fault-tolerant satellite control.

27

Table 6: Training parameters for the TD3-HD algorithm.

Parameter

Learning Rate (ζ)
Replay Buffer Size
Batch Size (M )
Target Update Interval
Clipping Thresholds (DWC)
Hidden Units
Importance Sampling (αIS)
Trajectory Size (N )
Actor Sub-networks (λi)

Value

3 × 10−4
1,000,000
128
2
0.2
256
1
100
4

6. Experimental Results

This section presents and analyzes the results of applying DRL to address
the satellite attitude control problem. The performance of the control system
was evaluated based on the pointing error between the satellite’s body-fixed
and inertial frames, measuring the precision of orientation alignment.

Additionally, the performance of each approach was tested under a chal-
lenging actuator failure scenario (e.g., unresponsive RW). The findings demon-
strate that, among the DRL algorithms, the proposed TD3-HD displayed
a notably robust response, handling the critical failure scenario effectively
and outperforming traditional methods in maintaining control accuracy and
adaptability.

6.1. Proportional-Derivative (PD) Controller: Analysis

The results demonstrate the limitations of a PD controller in managing
satellite attitude control following a RW failure. Initially, the PD controller
effectively tracks the desired attitude, as shown by the ”Desired vs. Ac-
tual Attitude” plot. However, following a fault in RW0 at 3000th second,
the PD controller fails to adapt autonomously, resulting in substantial de-
viations from the target attitude. The ”Error History” and ”Angle Error”
plots (Figure 5) illustrate a sharp increase in attitude error after fault, with
persistent oscillations of the angular velocity indicating that the controller’s
parameters would require manual adjustment to restore stability. This lack of
adaptability highlights a significant shortcoming of the PD controller under
fault conditions.

28

Figure 5: PD Controller Error Metrics for Attitude Control with RW Fault at 3000 seconds

Additionally, the torque plots (Figure 6) reveal that RW0 becomes unre-
sponsive after the fault, leaving the remaining wheels to compensate without
activating the backup wheel, which would require telecommand (ground in-
tervention) to retune the parameters. This limitation further destabilizes the
system, highlighting the PD controller’s inability to effectively manage fault
recovery under such conditions.

Figure 6: Torque History of RWs under PD Control with RW0 Fault

These findings highlight the need for advanced, fault-tolerant control
mechanisms, such as RL, which can autonomously adapt to actuator fail-

29

ures. Unlike traditional controllers, RL algorithms are capable of learning
optimal control policies through experience, enabling real-time adjustments
in response to faults and ensuring mission success without requiring manual
intervention.

6.2. A Comparative Analysis of RL-based approaches

This section provides a comprehensive comparison of three DLR algo-

rithms, A2C, PPO, and TD3, to address the unresponsive RW problem.

• PPO Performance Analysis: The PPO algorithm shows effective
adaptation following a fault in RW0 at 3000th second. As illustrated in Figure
7, the ”Desired vs Actual Attitude” subplot, PPO successfully aligns the
satellite’s actual attitude with the desired orientation, minimizing deviations
in a relatively short time. The ”Attitude Error” subplot indicates that PPO
maintains low error levels across all axes, even after the fault, demonstrating
stable control. The ”Angular Velocity” subplot reveals PPO’s capability to
reduce the oscillations, achieving alignment of actual velocities with desired
values. However, PPO required more time to stabilize and experienced slight
control variations due to exploration in rapidly changing conditions

Figure 7: PPO Error Metrics for Attitude Control with Fault at 3000 seconds

In terms of torque distribution, PPO dynamically redistributes torque
among RW1, RW2, and RW3 after the RW0 fault, as shown in Figure 8.
RW0’s torque drops to zero, while the other wheels exhibit increased torque

30

fluctuations to compensate. This adaptive redistribution highlights the re-
silience of PPO in maintaining control and stability under fault conditions.

Figure 8: PPO Torque History for RW0, RW1, RW2, and RW3

• A2C Performance Analysis: The A2C algorithm also performs well
following a fault in RW0 at 3000th second. As shown in Figure 9, in the
”Desired vs Actual Attitude” subplot, A2C gradually minimizes deviations
between the actual and desired attitudes, showing robust adaptability. The
”Attitude Error” subplot indicates a rapid reduction in initial errors, par-
ticularly along the x-axis, with stable low error levels maintained post-fault.
A2C effectively stabilizes angular velocities, as seen in the ”Angular Veloc-
ity” subplot. However, a limitation of PPO is that it requires more time
to align with the desired attitude in highly dynamic environments, where it
may struggle to respond quickly to changes in spacecraft orientation

31

Figure 9: A2C Error Metrics for Attitude Control with Fault at 3000 seconds

In the ”Torque History” plots (Figure 10), A2C redistributes torque ef-
fectively among RW1, RW2, and RW3 to compensate for RW0’s inactivity.

Figure 10: A2C Torque History for RW0, RW1, RW2, and RW3

• TD3 Performance Analysis: The TD3 algorithm demonstrates the
strongest performance among the three, particularly in handling the RW0
fault introduced at 3000th second. As illustrated in Figure 11, the ”Desired vs
Actual Attitude” subplot reveals rapid alignment with the desired trajectory,
In the ”Attitude Error” subplot, TD3 achieves
with minimal deviations.

32

the quickest reduction in errors across all axes, maintaining near-zero error
levels post-fault. The ”Angular Velocity” subplot shows stable control with
minimal oscillations, reflecting TD3’s high precision in managing angular
velocities.

Figure 11: TD3 Error Metrics for Attitude Control with Fault at 3000 seconds

TD3 achieves smooth torque redistribution in RW1, RW2 and RW3 after
RW0 fault, as shown in Figure 12. This adaptive torque redistribution show-
cases the robustness of TD3 in ensuring control and stability during fault
conditions. However, the gradual convergence observed, particularly in the
”Error Angle” subplot, reflects the challenges posed by sparse rewards, as
the algorithm requires more iterations to achieve stable control.

33

Figure 12: TD3 Torque History for RW0, RW1, RW2, and RW3

• Comparative Summary: All three algorithms, PPO, A2C, and TD3,
demonstrate effective fault tolerance in satellite attitude control, but each has
limitations. PPO provides moderate adaptability, but can introduce oscilla-
tory behaviors in persistent faults. A2C offers resilience and flexible torque
redistribution, but has slower convergence and higher fluctuations. TD3
excels in precision and stability in both attitude control and torque distribu-
tion, though it requires higher computational resources and may be sensitive
to over-adjustment. Overall, TD3 presents the most robust control solution,
suitable for fault-tolerant applications, but the gradual convergence observed
is attributed to the challenges posed by sparse rewards, which require more
time for the algorithm to achieve stable control. These comparisons under-
score the need for an advanced control mechanism that can overcome the
issues mentioned above. The effectiveness of our proposed algorithm, TD3-
HD, in addressing these challenges is evaluated and discussed in the following
section.

6.3. Performance of the Proposed TD3-HD

Figures 13 and 14 display the performance of the proposed TD3-HD algo-
rithm, incorporating HER and DWC. This enhanced TD3 variant addresses
the limitations of standard TD3 and demonstrates superior performance in
satellite attitude control. HER enables TD3-HD to learn effectively from
sparse rewards, while DWC refines control precision by limiting torque ad-
justments dimensionally. These enhancements significantly boost resilience

34

and adaptability under challenging conditions, such as the RW fault intro-
duced at 3000th second (RW0).

Figure 13: TD3-HD Error Metrics for Attitude Control with Fault at 3000 seconds

In the ”Desired vs Actual Attitude” subplot, TD3-HD rapidly aligns the
actual attitude with the target orientation, maintaining stability and preci-
sion throughout the simulation. The ”Attitude Error” subplot reveals that
TD3-HD minimizes deviations along all axes, achieving consistently low er-
ror levels post-fault, reflecting enhanced control accuracy. The ”Angular
Velocity” subplot demonstrates that TD3-HD effectively damps oscillations,
achieving near-immediate alignment of actual and desired angular velocities.
The ”Error Angle” subplot further emphasizes the control precision of TD3-
HD, with the attitude error angle quickly converging and remaining stable,
underscoring the robustness of the algorithm in fault scenarios (Figure 13).
The torque history plots (Figure 14) highlight TD3-HD’s efficient torque
management. In ”Torque History RW0,” torque drops to zero following the
fault, while the remaining wheels (RW1, RW2, and RW3) adjust smoothly
and dynamically. DWC ensures dimensionally restricted torque outputs, pre-
venting overcompensation and enabling balanced control. This approach pro-
viding smoother control than PPO, A2C, and standard TD3, as reflected in
the consistent torque responses of RW1, RW2, and RW3.

35

Figure 14: TD3-HD Torque History for RW0, RW1, RW2, and RW3

Overall, the proposed TD3-HD algorithm, which integrates HER and
DWC, offers exceptional adaptability and precision, effectively overcoming
the limitations of existing DRL algorithms. TD3-HD establishes itself as a
robust, efficient solution for satellite attitude control under fault conditions,
achieving optimal torque distribution and attitude stability, surpassing the
performance of PPO, A2C, and standard TD3.

7. Findings

The key findings of the research are summarized as follows:

• PD Controller Limitations: The PD controller, though effective in
maintaining the attitude of the satellite under nominal conditions, fails
to adapt autonomously following a RW fault. After the failure of RW0
at 3000th second, the PD controller exhibits substantial deviations from
the target attitude and prolonged instability in angular velocity, neces-
sitating manual tuning for stability restoration. This result highlights
the PD controller’s limitations in scenarios requiring fault-tolerant ca-
pabilities.

• Comparative Analysis of PPO, A2C, and TD3: The PPO and
A2C algorithms provide satisfactory fault tolerance but exhibit certain

36

limitations in control smoothness and convergence speed. PPO demon-
strates moderate adaptability, but introduces oscillations in torque dis-
tribution under fault conditions. A2C offers flexible torque manage-
ment, but shows slower convergence. TD3 excels in precision and sta-
bility, achieving rapid alignment with target orientations, although it
requires higher computational resources and can be sensitive to over-
adjustments in dynamic environments. Overall, TD3 proves to be the
most robust of these three algorithms, though it still falls short of the
proposed TD3-HD in terms of fault tolerance and efficiency.

• The Proposed TD3-HD’s Enhanced Fault-Tolerance: The pro-
posed TD3-HD algorithm demonstrates superior fault tolerance and
adaptability for satellite attitude control compared to other DRL al-
gorithms such as PPO, A2C and TD3. Enhanced by HER, TD3-HD
efficiently learns from sparse rewards, while DWC optimizes torque
adjustments, minimizing fluctuations. This results in stable attitude
alignment and low error levels even under RW fault conditions, effec-
tively redistributing the torque without excessive oscillations. Over-
all, TD3-HD outperforms traditional and other DRL methods, making
it the most effective autonomous solution for fault-tolerant control in
satellites.

• Implications for Autonomous Satellite Control: This study un-
derscores the potential of DRL, particularly the proposed TD3-HD, in
enhancing satellite autonomy by adapting to actuator failures without
manual intervention. This capability is essential for mission continu-
ity, where reliability and adaptability are crucial for mission success
in the face of unanticipated faults. The proposed TD3-HD’s ability to
maintain control precision in challenging scenarios demonstrates its ap-
plicability for advanced space missions, require resilient and adaptive
control solutions.

8. Conclusion and Future Work

This study introduced a DRL approach, called TD3-HD with DWC, to
enhance satellite attitude control and address unresponsive RW faults in
autonomous, fault-tolerant systems. TD3-HD’s combination of HER for im-
proved learning from sparse rewards and DWC for stable individual torque

37

adjustment, makes it well-suited for dynamic space environments. Simula-
tions in the Basilisk environment showed that TD3-HD achieved lower at-
titude errors, better angular velocity control, and greater stability in RW
fault scenarios compared to traditional PD control and other DRL methods
(standard TD3, PPO, and A2C). This highlights the potential of TD3-HD
as a robust, fault-tolerant, on-board AI solution for satellites, effectively en-
abling autonomous fault management and improving satellite resilience as an
advanced autonomous system. Future work will extend TD3-HD to satellite
constellations, focusing on coordinated, fault-tolerant control across multiple
satellites. Developing distributed DRL frameworks will support autonomous
attitude management and adaptability to shared faults, advancing scalable,
resilient operations for multi-satellite environments.

ACKNOWLEDGEMENTS

This work has been supported by the SmartSat CRC, whose activities are
funded by the Australian Government’s CRC Program. We also acknowledge
the collaborative contributions of the research team (James Barr, Travis
Bessell) from Saab Australia.

38

References

[1] J. R. Mansell, Deep learning fault protection applied to spacecraft atti-
tude determination and control, Ph.D. thesis, Purdue University (2020).

[2] J. R. Mansell, D. A. Spencer, Deep learning fault diagnosis for spacecraft
attitude determination and control, Journal of Aerospace Information
Systems 18 (3) (2021) 102–115.

[3] A. Mahfouz, D. Pritykin, J. Biggs, Hybrid attitude control for nano-
spacecraft: Reaction wheel failure and singularity handling, Journal of
Guidance, Control, and Dynamics 44 (3) (2021) 548–558.

[4] P. Miralles, K. Thangavel, A. F. Scannapieco, N. Jagadam, P. Baranwal,
B. Faldu, R. Abhang, S. Bhatia, S. Bonnart, I. Bhatnagar, et al., A
critical review on the state-of-the-art and future prospects of machine
learning for earth observation operations, Advances in Space Research
71 (12) (2023) 4959–4986.

[5] S. Fujimoto, H. Hoof, D. Meger, Addressing function approximation
error in actor-critic methods, in: International conference on machine
learning, PMLR, 2018, pp. 1587–1596.

[6] M. Andrychowicz, F. Wolski, A. Ray, J. Schneider, R. Fong, P. Welin-
der, B. McGrew, J. Tobin, O. Pieter Abbeel, W. Zaremba, Hindsight
experience replay, Advances in neural information processing systems
30 (2017).

[7] H. Wu, H. Ye, W. Xue, X. Yang, Improved reinforcement learning using
stability augmentation with application to quadrotor attitude control,
IEEE Access 10 (2022) 67590–67604.

[8] H. Henna, H. Toubakh, M. R. Kafi, M. Sayed-Mouchaweh, Towards
fault-tolerant strategy in satellite attitude control systems: A review,
in: Annual Conference of the PHM Society, Vol. 12, 2020, pp. 14–14.

[9] M. F. Mehrjardi, H. Sanusi, M. A. M. Ali, M. A. Taher, Pd controller for
three-axis satellite attitude control using discrete kalman filter, in: 2014
International Conference on Computer, Communications, and Control
Technology (I4CT), IEEE, 2014, pp. 83–85.

39

[10] K. M. Mohan, U. Anitha, K. Anbumani, Cubesat attitude control by
implementation of pid controller using python, in: 2023 12th Interna-
tional Conference on Advanced Computing (ICoAC), IEEE, 2023, pp.
1–5.

[11] M. L. Orozco, B. S. Giraldo, Attitude determination and control in small
satellites: A review, IEEE Journal on Miniaturization for Air and Space
Systems (2024).

[12] T. Wu, C. Zhou, Z. Yan, H. Peng, L. Wu, Application of pid opti-
mization control strategy based on particle swarm optimization (pso)
for battery charging system, International Journal of Low-Carbon Tech-
nologies 15 (4) (2020) 528–535.

[13] A. K. Parsai, J. S. Qureishi, G. Raju, K. Ratnakara, Model based pid
tuning of antenna control system for tracking of spacecraft, in: 2019 3rd
International conference on Electronics, Communication and Aerospace
Technology (ICECA), IEEE, 2019, pp. 906–913.

[14] Z. Zhu, Y. Xia, M. Fu, Adaptive sliding mode control for attitude sta-
bilization with actuator saturation, IEEE Transactions on Industrial
Electronics 58 (10) (2011) 4898–4907.

[15] B. Wang, S. Li, Q. Zhang, M. Xin, Combined fuzzy sliding-mode atti-
tude stabilization and energy storage for small satellite, IEEE Transac-
tions on Aerospace and Electronic Systems (2023).

[16] L. Cao, X. Chen, A. K. Misra, Minimum sliding mode error feedback
control for fault tolerant reconfigurable satellite formations with j2 per-
turbations, Acta Astronautica 96 (2014) 201–216.

[17] A. Modirrousta, M. Khodabandeh, Adaptive non-singular terminal slid-
ing mode controller: new design for full control of the quadrotor with
external disturbances, Transactions of the Institute of Measurement and
Control 39 (3) (2017) 371–383.

[18] W. Xin, Z. Shasha, Z. Xingwang, Adaptive fuzzy sliding mode controller
for attitude coordinated control in spacecraft formation, GSTF Journal
on Aviation Technology (JAT) 1 (2015) 1–7.

40

[19] S. Jia, J. Shan, Continuous integral sliding mode control for space ma-
nipulator with actuator uncertainties, Aerospace Science and Technol-
ogy 106 (2020) 106192.

[20] H. Wang, L. Chen, Z. Jin, J. L. Crassidis, Adaptive momentum dis-
tribution jitter control for microsatellite, Journal of Guidance, Control,
and Dynamics 42 (3) (2019) 632–641.

[21] R. A. Freeman, P. Kokotovi´c, Backstepping design of robust controllers
for a class of nonlinear systems, in: Nonlinear Control Systems Design
1992, Elsevier, 1993, pp. 431–436.

[22] S. Babaei Faramarz, A. Akbarzadeh Kalat, An output feedback back-
stepping attitude control for rigid satellite, Transactions of the Institute
of Measurement and Control 45 (11) (2023) 2182–2191.

[23] K. Yan, Q. Wu, C. Yang, M. Chen, Backstepping-based adaptive fault-
tolerant control design for satellite attitude system, in: 2020 Interna-
tional Conference on Unmanned Aircraft Systems (ICUAS), IEEE, 2020,
pp. 176–181.

[24] H. Boussadia, A. S. Mohammed, N. Boughanmi, A. Bellar, Adaptive
backstepping control for microsatellite under inertia uncertainties, in:
2017 8th International Conference on Recent Advances in Space Tech-
nologies (RAST), IEEE, 2017, pp. 67–72.

[25] Feedback and optimal sensitivity: Model reference transformations, mul-
tiplicative seminorms, and approximate inverses, IEEE Transactions on
automatic control 26 (2) (1981) 301–320.

[26] Z. Wang, Y. Li, Rigid spacecraft nonlinear robust h∞ attitude controller
design under actuator misalignments, Nonlinear Dynamics 111 (16)
(2023) 15037–15054.

[27] S. M. Esmaeilzadeh, M. S. Zeyghami, Nonlinear finite time attitude con-
trol of flexible spacecraft based on a novel output redefinition method,
Chinese Journal of Aeronautics 36 (11) (2023) 373–385.

[28] T. H. Davenport, R. Ronanki, et al., Artificial intelligence for the real

world, Harvard business review 96 (1) (2018) 108–116.

41

[29] P. J. Werbos, Backpropagation through time: what it does and how to

do it, Proceedings of the IEEE 78 (10) (1990) 1550–1560.

[30] A. Carrara, A. R. Neto, Satellite attitude acquisition using a neural
network controller, Advances in space dynamics; Advances in Space Dy-
namics (2000) 272–282.

[31] R. Bellman, The theory of dynamic programming, Bulletin of the Amer-

ican Mathematical Society 60 (6) (1954) 503–515.

[32] V. Mnih, K. Kavukcuoglu, D. Silver, A. A. Rusu, J. Veness, M. G.
Bellemare, A. Graves, M. Riedmiller, A. K. Fidjeland, G. Ostrovski,
et al., Human-level control through deep reinforcement learning, nature
518 (7540) (2015) 529–533.

[33] T. Lillicrap, Continuous control with deep reinforcement learning, arXiv

preprint arXiv:1509.02971 (2015).

[34] T. Haarnoja, A. Zhou, P. Abbeel, S. Levine, Soft actor-critic: Off-policy
maximum entropy deep reinforcement learning with a stochastic ac-
tor, in: International conference on machine learning, PMLR, 2018, pp.
1861–1870.

[35] J. Schulman, F. Wolski, P. Dhariwal, A. Radford, O. Klimov, Proximal
policy optimization algorithms, arXiv preprint arXiv:1707.06347 (2017).

[36] J. Schulman, Trust

region policy optimization,

arXiv preprint

arXiv:1502.05477 (2015).

[37] Y. Chai, J. Luo, N. Han, Spacecraft attitude analytical predictive control
based on sequential action control, in: 2018 IEEE CSAA Guidance,
Navigation and Control Conference (CGNCC), IEEE, 2018, pp. 1–7.

[38] Y. Yang, K. Caluwaerts, A. Iscen, T. Zhang, J. Tan, V. Sindhwani,
Data efficient reinforcement learning for legged robots, in: Conference
on Robot Learning, PMLR, 2020, pp. 1–10.

[39] X. He, C. Lv, Robotic control in adversarial and sparse reward envi-
ronments: A robust goal-conditioned reinforcement learning approach,
IEEE Transactions on Artificial Intelligence 5 (1) (2023) 244–253.

42

[40] K. Hovell, S. Ulrich, On deep reinforcement learning for spacecraft guid-

ance, in: AIAA Scitech 2020 forum, 2020, p. 1600.

[41] Y. Liu, G. Ma, Y. Lyu, P. Wang, Neural network-based reinforcement
learning control for combined spacecraft attitude tracking maneuvers,
Neurocomputing 484 (2022) 67–78.

[42] Y. Meng, C. Liu, Y. Liu, L. Tan, Adaptive fault-tolerant control for
spacecraft: A dynamic stackelberg game approach with a2c reinforce-
ment learning, Available at SSRN 4683974.

[43] W. Retagne, J. Dauer, G. Waxenegger-Wilfing, Adaptive satellite atti-
tude control for varying masses using deep reinforcement learning, Fron-
tiers in Robotics and AI 11 (2024) 1402846.

[44] H. Henna, Attitude fault-tolerant control applied to microsatellite,
Ph.D. thesis, UNIVERSITY OF KASDI MERBAH OUARGLA (2024).

[45] B. Gaudet, R. Linares, R. Furfaro, Deep reinforcement learning for six
degree-of-freedom planetary landing, Advances in Space Research 65 (7)
(2020) 1723–1741.

[46] Z. Zhang, X. Li, J. An, W. Man, G. Zhang, Model-free attitude control
of spacecraft based on pid-guide td3 algorithm, International Journal of
Aerospace Engineering 2020 (1) (2020) 8874619.

[47] J.-A. R. Sarmiento, V. H. Tan, M. C. R. Talampas, P. C. Naval Jr,
Sample efficient deep reinforcement learning for diwata microsatellite
reaction wheel attitude control, Aerospace Systems 6 (1) (2023) 61–69.

[48] N. A. Chaturvedi, A. K. Sanyal, N. H. McClamroch, Rigid-body attitude

control, IEEE control systems magazine 31 (3) (2011) 30–51.

[49] S. Bandyopadhyay, S.-J. Chung, F. Hadaegh, Attitude control and sta-
bilization of spacecraft with a captured asteroid, in: AIAA Guidance,
Navigation, and Control Conference, 2015, p. 0596.

[50] R. Calaon, H. Schaub, Constrained attitude maneuvering via modified-
rodrigues-parameter-based motion planning algorithms, Journal of
Spacecraft and Rockets 59 (4) (2022) 1342–1356.

43

[51] F. L. Markley, J. L. Crassidis, Attitude kinematics and dynamics,
in: Fundamentals of Spacecraft Attitude Determination and Control,
Springer, 2014, pp. 67–122.

[52] Y. Su, C. Zheng, Globally asymptotic stabilization of spacecraft with
simple saturated proportional-derivative control, Journal of Guidance,
Control, and Dynamics 34 (6) (2011) 1932–1936.

[53] P. C. Hughes, Spacecraft attitude dynamics, Courier Corporation, 2012.

[54] J. Elkins, R. Sood, C. Rumpf, Adaptive continuous control of spacecraft
attitude using deep reinforcement learning, in: Proceedings of, 2020, pp.
420–475.

[55] P. W. Kenneally, S. Piggott, H. Schaub, Basilisk: A flexible, scalable
and modular astrodynamics simulation framework, Journal of aerospace
information systems 17 (9) (2020) 496–507.

[56] M. Fang, C. Zhou, B. Shi, B. Gong, J. Xu, T. Zhang, Dher: Hindsight
experience replay for dynamic goals, in: International Conference on
Learning Representations, 2018.

[57] R. Liu, F. Nageotte, P. Zanne, M. de Mathelin, B. Dresp-Langley, Deep
reinforcement learning for the control of robotic manipulation: a fo-
cussed mini-review, Robotics 10 (1) (2021) 22.

[58] R. Creus-Castanyer, Intrinsic exploration for reinforcement learning be-

yond rewards (2024).

[59] S. Narvekar, B. Peng, M. Leonetti, J. Sinapov, M. E. Taylor, P. Stone,
Curriculum learning for reinforcement learning domains: A framework
and survey, Journal of Machine Learning Research 21 (181) (2020) 1–50.

[60] H. Zhang, Gradient-norm constrained algorithm on offline and online

learning, Available at SSRN 4663051.

[61] Y. Zhang, J. Sun, G. Wang, J. Chen, Addressing high-dimensional con-
tinuous action space via decomposed discrete policy-critic (2022).

[62] S. Han, Y. Sung, Dimension-wise importance sampling weight clipping
for sample-efficient reinforcement learning, in: International Conference
on Machine Learning, PMLR, 2019, pp. 2586–2595.

44

[63] K. Arulkumaran, M. P. Deisenroth, M. Brundage, A. A. Bharath, Deep
reinforcement learning: A brief survey, IEEE Signal Processing Maga-
zine 34 (6) (2017) 26–38.

[64] H. Sawada, T. Hashimoto, K. Ninomiya, High-stability attitude con-
trol of satellites by magnetic bearing wheels, Transactions of the Japan
Society for Aeronautical and Space Sciences 44 (145) (2001) 133–141.

[65] J. R. Forbes, Fundamentals of spacecraft attitude determination and
control [bookshelf], IEEE Control Systems Magazine 35 (4) (2015) 56–
58.

[66] A. A. Al-Atawi, Genetically optimized td3 algorithm for efficient access
control in the internet of vehicles, Wireless Networks (2024) 1–21.

[67] W. Xiao, L. Yuan, T. Ran, L. He, J. Zhang, J. Cui, Multimodal fusion
for autonomous navigation via deep reinforcement learning with sparse
rewards and hindsight experience replay, Displays 78 (2023) 102440.

[68] V. Tan, J. L. Labrador, M. C. Talampas, Mata-rl: continuous reaction
wheel attitude control using the mata simulation software and reinforce-
ment learning (2021).

[69] A. Raffin, A. Hill, A. Gleave, A. Kanervisto, M. Ernestus, N. Dor-
mann, Stable-baselines3: Reliable reinforcement learning implementa-
tions, Journal of Machine Learning Research 22 (268) (2021) 1–8.

[70] G. Brockman, V. Cheung, L. Pettersson, J. Schneider, J. Schulman,
J. Tang, W. Zaremba, Openai gym (2016). arXiv:arXiv:1606.01540.

45

