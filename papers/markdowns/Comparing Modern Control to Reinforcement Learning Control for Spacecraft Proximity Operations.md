IFAC PapersOnLine 59-30 (2025) 197–202

Comparing Modern Control to
Comparing Modern Control to
Comparing Modern Control to
Reinforcement Learning Control for
Comparing Modern Control to
Reinforcement Learning Control for
Reinforcement Learning Control for
Spacecraft Proximity Operations ⋆
Spacecraft Proximity Operations ⋆
Reinforcement Learning Control for
Spacecraft Proximity Operations ⋆
Spacecraft Proximity Operations ⋆
Britney Rogers ∗ Kyle Dunlap ∗∗ Zheng Chen ∗∗∗
Britney Rogers ∗ Kyle Dunlap ∗∗ Zheng Chen ∗∗∗
Britney Rogers ∗ Kyle Dunlap ∗∗ Zheng Chen ∗∗∗
Marzia Cescon ∗∗∗ Karolos Grigoriadis ∗∗∗
Marzia Cescon ∗∗∗ Karolos Grigoriadis ∗∗∗
Britney Rogers ∗ Kyle Dunlap ∗∗ Zheng Chen ∗∗∗
Marzia Cescon ∗∗∗ Karolos Grigoriadis ∗∗∗
Kerianne L. Hobbs ∗∗
Kerianne L. Hobbs ∗∗
Marzia Cescon ∗∗∗ Karolos Grigoriadis ∗∗∗
Kerianne L. Hobbs ∗∗
Kerianne L. Hobbs ∗∗
∗ Aerospace Eng. Dept., Texas A & M University, College Station, TX
∗ Aerospace Eng. Dept., Texas A & M University, College Station, TX
∗ Aerospace Eng. Dept., Texas A & M University, College Station, TX
(email: bmrogers@tamu.edu).
(email: bmrogers@tamu.edu).
∗ Aerospace Eng. Dept., Texas A & M University, College Station, TX
(email: bmrogers@tamu.edu).
∗∗ Autonomy Capability Team, Air Force Research Laboratory, Wright
∗∗ Autonomy Capability Team, Air Force Research Laboratory, Wright
(email: bmrogers@tamu.edu).
∗∗ Autonomy Capability Team, Air Force Research Laboratory, Wright
Patterson Air Force Base, OH (email:
Patterson Air Force Base, OH (email:
∗∗ Autonomy Capability Team, Air Force Research Laboratory, Wright
Patterson Air Force Base, OH (email:
kyle.dunlap.5—kerianne.hobbs@us.af.mil)
kyle.dunlap.5—kerianne.hobbs@us.af.mil)
Patterson Air Force Base, OH (email:
kyle.dunlap.5—kerianne.hobbs@us.af.mil)
∗∗∗ Mechanical and Aerospace Eng. Dept., University of Houston,
∗∗∗ Mechanical and Aerospace Eng. Dept., University of Houston,
kyle.dunlap.5—kerianne.hobbs@us.af.mil)
∗∗∗ Mechanical and Aerospace Eng. Dept., University of Houston,
Houston, TX (email: zchen43—mcescon2—mece2hv@central.uh.edu).
Houston, TX (email: zchen43—mcescon2—mece2hv@central.uh.edu).
∗∗∗ Mechanical and Aerospace Eng. Dept., University of Houston,
Houston, TX (email: zchen43—mcescon2—mece2hv@central.uh.edu).
Houston, TX (email: zchen43—mcescon2—mece2hv@central.uh.edu).
Abstract: In-Space or On-orbit Servicing, Assembly, and Manufacturing (ISAM/OSAM) is a
Abstract: In-Space or On-orbit Servicing, Assembly, and Manufacturing (ISAM/OSAM) is a
Abstract: In-Space or On-orbit Servicing, Assembly, and Manufacturing (ISAM/OSAM) is a
growing field in developing space robotics to repair or refuel existing satellites, assemble large
growing field in developing space robotics to repair or refuel existing satellites, assemble large
Abstract: In-Space or On-orbit Servicing, Assembly, and Manufacturing (ISAM/OSAM) is a
growing field in developing space robotics to repair or refuel existing satellites, assemble large
structures, and manufacture components in space. A foundational capability in this domain is
structures, and manufacture components in space. A foundational capability in this domain is
growing field in developing space robotics to repair or refuel existing satellites, assemble large
structures, and manufacture components in space. A foundational capability in this domain is
the development of a control approach for OSAM vehicles to safely egress from the servicing or
the development of a control approach for OSAM vehicles to safely egress from the servicing or
structures, and manufacture components in space. A foundational capability in this domain is
the development of a control approach for OSAM vehicles to safely egress from the servicing or
assembly area. This work compares the performance of model-based optimal control techniques
assembly area. This work compares the performance of model-based optimal control techniques
the development of a control approach for OSAM vehicles to safely egress from the servicing or
assembly area. This work compares the performance of model-based optimal control techniques
to a Reinforcement Learning (RL) approach for the egress problem. Simulation results are
to a Reinforcement Learning (RL) approach for the egress problem. Simulation results are
assembly area. This work compares the performance of model-based optimal control techniques
to a Reinforcement Learning (RL) approach for the egress problem. Simulation results are
presented where control efficiency is used as a primary metric for comparison.
presented where control efficiency is used as a primary metric for comparison.
to a Reinforcement Learning (RL) approach for the egress problem. Simulation results are
presented where control efficiency is used as a primary metric for comparison.
Copyright © 2025 The Authors. This is an open access article under the CC BY-NC-ND license
presented where control efficiency is used as a primary metric for comparison.
Keywords: Optimal Control; Aerospace; Machine Learning.
(https://creativecommons.org/licenses/by-nc-nd/4.0/)
Keywords: Optimal Control; Aerospace; Machine Learning.
Keywords: Optimal Control; Aerospace; Machine Learning.
Keywords: Optimal Control; Aerospace; Machine Learning.

1. INTRODUCTION
1. INTRODUCTION
1. INTRODUCTION
1. INTRODUCTION
In-space and On-Orbit Satellite Servicing, Assembly, and
In-space and On-Orbit Satellite Servicing, Assembly, and
In-space and On-Orbit Satellite Servicing, Assembly, and
Manufacturing (ISAM/OSAM) are growing industries.
Manufacturing (ISAM/OSAM) are growing industries.
In-space and On-Orbit Satellite Servicing, Assembly, and
Manufacturing (ISAM/OSAM) are growing industries.
ISAM covers all servicing, assembly, and manufacturing
ISAM covers all servicing, assembly, and manufacturing
Manufacturing (ISAM/OSAM) are growing industries.
ISAM covers all servicing, assembly, and manufacturing
jobs off-Earth and OSAM is a subsection of ISAM solely
jobs off-Earth and OSAM is a subsection of ISAM solely
ISAM covers all servicing, assembly, and manufacturing
jobs off-Earth and OSAM is a subsection of ISAM solely
for on-orbit purposes, with capabilities such as satellite
for on-orbit purposes, with capabilities such as satellite
jobs off-Earth and OSAM is a subsection of ISAM solely
for on-orbit purposes, with capabilities such as satellite
repairs, maintenance, and part installations (Arney et al.,
repairs, maintenance, and part installations (Arney et al.,
for on-orbit purposes, with capabilities such as satellite
repairs, maintenance, and part installations (Arney et al.,
2021). Past OSAM missions include the on-orbit assembly
2021). Past OSAM missions include the on-orbit assembly
repairs, maintenance, and part installations (Arney et al.,
2021). Past OSAM missions include the on-orbit assembly
of the International Space Station and multiple satel-
of the International Space Station and multiple satel-
2021). Past OSAM missions include the on-orbit assembly
of the International Space Station and multiple satel-
lite servicing missions for the Hubble space telescope.
lite servicing missions for the Hubble space telescope.
of the International Space Station and multiple satel-
lite servicing missions for the Hubble space telescope.
Currently, unmanned spacecraft operate solely on human
Currently, unmanned spacecraft operate solely on human
lite servicing missions for the Hubble space telescope.
Currently, unmanned spacecraft operate solely on human
issued commands, but future missions will require the
issued commands, but future missions will require the
Currently, unmanned spacecraft operate solely on human
issued commands, but future missions will require the
ability to make split second decisions. In these instances,
ability to make split second decisions. In these instances,
issued commands, but future missions will require the
ability to make split second decisions. In these instances,
autonomous and automatic control systems have the po-
autonomous and automatic control systems have the po-
ability to make split second decisions. In these instances,
autonomous and automatic control systems have the po-
tential to maintain vehicle safety and mission assurance.
tential to maintain vehicle safety and mission assurance.
autonomous and automatic control systems have the po-
tential to maintain vehicle safety and mission assurance.
A fundamental capability of any OSAM/ISAM mission
tential to maintain vehicle safety and mission assurance.
A fundamental capability of any OSAM/ISAM mission
A fundamental capability of any OSAM/ISAM mission
is an efficient approach into a servicing or assembly area
is an efficient approach into a servicing or assembly area
A fundamental capability of any OSAM/ISAM mission
is an efficient approach into a servicing or assembly area
(ingress) and an accompanying safe exit away from a ser-
(ingress) and an accompanying safe exit away from a ser-
is an efficient approach into a servicing or assembly area
(ingress) and an accompanying safe exit away from a ser-
vicing area (egress), while maintaining a safe distance from
vicing area (egress), while maintaining a safe distance from
(ingress) and an accompanying safe exit away from a ser-
vicing area (egress), while maintaining a safe distance from
the chief to avoid collisions. An efficient feedback controller
the chief to avoid collisions. An efficient feedback controller
vicing area (egress), while maintaining a safe distance from
the chief to avoid collisions. An efficient feedback controller
that can guarantee safety for the deputy satellite while
that can guarantee safety for the deputy satellite while
the chief to avoid collisions. An efficient feedback controller
that can guarantee safety for the deputy satellite while
that can guarantee safety for the deputy satellite while
⋆ Approved for public release; distribution is unlimited. AFRL-
⋆ Approved for public release; distribution is unlimited. AFRL-
⋆ Approved for public release; distribution is unlimited. AFRL-
2025-3524.This work was supported by the Department of Defense
2025-3524.This work was supported by the Department of Defense
⋆ Approved for public release; distribution is unlimited. AFRL-
(DoD) through the Air Force Research Laboratory (AFRL) Minority
2025-3524.This work was supported by the Department of Defense
(DoD) through the Air Force Research Laboratory (AFRL) Minority
2025-3524.This work was supported by the Department of Defense
Leaders Research Collaboration Program (ML-RCP). The views
(DoD) through the Air Force Research Laboratory (AFRL) Minority
Leaders Research Collaboration Program (ML-RCP). The views
(DoD) through the Air Force Research Laboratory (AFRL) Minority
expressed are those of the authors and do not reflect the official
Leaders Research Collaboration Program (ML-RCP). The views
expressed are those of the authors and do not reflect the official
Leaders Research Collaboration Program (ML-RCP). The views
guidance or position of the United States Government, the Depart-
expressed are those of the authors and do not reflect the official
guidance or position of the United States Government, the Depart-
expressed are those of the authors and do not reflect the official
ment of Defense or of the United States Air Force. B.R. is currently
guidance or position of the United States Government, the Depart-
ment of Defense or of the United States Air Force. B.R. is currently
guidance or position of the United States Government, the Depart-
with Texas A&M University. This work was done when she was at
ment of Defense or of the United States Air Force. B.R. is currently
with Texas A&M University. This work was done when she was at
ment of Defense or of the United States Air Force. B.R. is currently
the University of Houston.
with Texas A&M University. This work was done when she was at
the University of Houston.
with Texas A&M University. This work was done when she was at
the University of Houston.
the University of Houston.

it circumnavigates the chief is, therefore, a crucial tool
it circumnavigates the chief is, therefore, a crucial tool
it circumnavigates the chief is, therefore, a crucial tool
for egress purposes. To this end, this research compares
for egress purposes. To this end, this research compares
it circumnavigates the chief is, therefore, a crucial tool
for egress purposes. To this end, this research compares
model-based optimal control techniques, including Linear
model-based optimal control techniques, including Linear
for egress purposes. To this end, this research compares
model-based optimal control techniques, including Linear
Quadratic Regulation (LQR), Linear Quadratic Integra-
Quadratic Regulation (LQR), Linear Quadratic Integra-
model-based optimal control techniques, including Linear
Quadratic Regulation (LQR), Linear Quadratic Integra-
tion (LQI), and Linear Quadratic Tracking (LQT), against
tion (LQI), and Linear Quadratic Tracking (LQT), against
Quadratic Regulation (LQR), Linear Quadratic Integra-
tion (LQI), and Linear Quadratic Tracking (LQT), against
Reinforcement Learning (RL) for the egress problem.
Reinforcement Learning (RL) for the egress problem.
tion (LQI), and Linear Quadratic Tracking (LQT), against
Reinforcement Learning (RL) for the egress problem.
Previous related work includes utilizing a switching back-
Reinforcement Learning (RL) for the egress problem.
Previous related work includes utilizing a switching back-
Previous related work includes utilizing a switching back-
up controller to safely park a deputy spacecraft in an orbit
up controller to safely park a deputy spacecraft in an orbit
Previous related work includes utilizing a switching back-
up controller to safely park a deputy spacecraft in an orbit
about a chosen chief (Mote et al., 2021). Other inves-
about a chosen chief (Mote et al., 2021). Other inves-
up controller to safely park a deputy spacecraft in an orbit
about a chosen chief (Mote et al., 2021). Other inves-
tigations have utilized nonlinear state-dependent Riccati
tigations have utilized nonlinear state-dependent Riccati
about a chosen chief (Mote et al., 2021). Other inves-
tigations have utilized nonlinear state-dependent Riccati
equation (SDRE) control technique and an LQT control
equation (SDRE) control technique and an LQT control
tigations have utilized nonlinear state-dependent Riccati
equation (SDRE) control technique and an LQT control
technique to follow desired trajectories for translational
technique to follow desired trajectories for translational
equation (SDRE) control technique and an LQT control
technique to follow desired trajectories for translational
maneuvers between spacecraft while also accounting for
maneuvers between spacecraft while also accounting for
technique to follow desired trajectories for translational
maneuvers between spacecraft while also accounting for
attitude (Lee and Pernicka, 2010). This paper investigates
attitude (Lee and Pernicka, 2010). This paper investigates
maneuvers between spacecraft while also accounting for
attitude (Lee and Pernicka, 2010). This paper investigates
if there is a way to solve this problem without implement-
if there is a way to solve this problem without implement-
attitude (Lee and Pernicka, 2010). This paper investigates
if there is a way to solve this problem without implement-
ing a switching back-up controller.
ing a switching back-up controller.
if there is a way to solve this problem without implement-
ing a switching back-up controller.
The contributions of this paper are twofold: first, the
ing a switching back-up controller.
The contributions of this paper are twofold: first, the
The contributions of this paper are twofold: first, the
development of LQR, LQI, LQT, and RL control solutions
development of LQR, LQI, LQT, and RL control solutions
The contributions of this paper are twofold: first, the
development of LQR, LQI, LQT, and RL control solutions
for safe egress from close proximity to a chief spacecraft
for safe egress from close proximity to a chief spacecraft
development of LQR, LQI, LQT, and RL control solutions
for safe egress from close proximity to a chief spacecraft
to a distant elliptical natural motion trajectory (eNMT);
to a distant elliptical natural motion trajectory (eNMT);
for safe egress from close proximity to a chief spacecraft
to a distant elliptical natural motion trajectory (eNMT);
and second, the comparison of performances with respect
and second, the comparison of performances with respect
to a distant elliptical natural motion trajectory (eNMT);
and second, the comparison of performances with respect
to time and largest cumulative variation in velocity.
to time and largest cumulative variation in velocity.
and second, the comparison of performances with respect
to time and largest cumulative variation in velocity.
This remainder of this paper is organized as follows: Sec. 2
to time and largest cumulative variation in velocity.
This remainder of this paper is organized as follows: Sec. 2
This remainder of this paper is organized as follows: Sec. 2
introduces the problem statement, Sec. 3 illustrates an
introduces the problem statement, Sec. 3 illustrates an
This remainder of this paper is organized as follows: Sec. 2
introduces the problem statement, Sec. 3 illustrates an
explanation of the control methods, while Sec. 4 shows the
explanation of the control methods, while Sec. 4 shows the
introduces the problem statement, Sec. 3 illustrates an
explanation of the control methods, while Sec. 4 shows the
simulation results for four different cases of each control
simulation results for four different cases of each control
explanation of the control methods, while Sec. 4 shows the
simulation results for four different cases of each control
method. Finally, conclusions with a discussion of proposed
method. Finally, conclusions with a discussion of proposed
simulation results for four different cases of each control
method. Finally, conclusions with a discussion of proposed
future work are presented in Sec. 5.
future work are presented in Sec. 5.
method. Finally, conclusions with a discussion of proposed
future work are presented in Sec. 5.
future work are presented in Sec. 5.

2405-8963 Copyright © 2025 The Authors. This is an open access article under the CC BY-NC-ND license.
Peer review under responsibility of International Federation of Automatic Control.
10.1016/j.ifacol.2025.12.236

10.1016/j.ifacol.2025.12.236

2405-8963

ScienceDirectScienceDirectAvailable online at www.sciencedirect.com198

Britney Rogers  et al. / IFAC PapersOnLine 59-30 (2025) 197–202

To guarantee the bounded relative orbit assigned to the
deputy will not have linear drift, initial conditions (ICs)
must be placed on ˙y. A similar IC is chosen for y to avoid
any offset conditions. The orbit chosen for this paper is an
in-plane closed eNMT (Alfriend et al., 2010), so the ICs set
on the system are y(0) = (2/n) ˙x(0) and ˙y(0) =
2nx(0).
Note for simulations in this paper, x(0) = 1 and ˙x(0) =
0.001. Commonly referred to as a parking trajectory, this is
a stable orbit where once the directional thrust u = 0, the
deputy will stay on track in the orbit with no extra control
needed (Mote et al., 2021). The shape of the eNMT ICs is
given by

(x2/a2) + (y2/b2) = 1
(5)
where a = 200 m is the length of the major radius, and
b = 100 m is the length of the minor radius. The orbital
rate of the chief satellite is n = 0.001027 and the satellite
mass is m = 12 kg to symbolize a 6-unit CubeSat. When
u = 0, the CW equations are reduced to ˙x = Ax.

−

There are two control limits applied to the systems: a
maximum relative velocity in any direction [vx, vy] equal
to 0.5 m/s, and a maximum value for the control inputs
[ux, uy] set to [
1, 1] N. Each simulation
−
is limited to a maximum of two orbits, for a total chosen
orbital period of 6,117 seconds.

umax, umax] = [

−

3. CONTROL DESIGN

This section describes three methods from classical control
theory namely, LQR, LQI, and LQT (Lewis and Syrmos,
1995) as well as a machine learning method, namely, RL.

3.1 Linear Quadratic Regulation (LQR)

1
2

0

(cid:31)

LQR in an optimal state-feedback controller for a linear
dynamical system that minimizes a quadratic cost on the
states and control inputs to stabilize a closed-loop (CL)
control system Lee and Pernicka (2010). The performance
index to be minimized is:
∞

J =

[xT Qx + uT Ru] dt

(6)

≥

where Q
0 and R > 0 are symmetric matrices. The
transition state weight Q is a general diagonal matrix
selected to provide appropriate weight to limit the states,
and the control weight R is a diagonal matrix that can be
weighted for the position states x and y independently to
limit control. The optimal feedback control of the system
is computed by solving the Algebraic Riccati Equation
). The
(ARE) and the time-invariant Kalman gain (K
resulting control law is:
u =

(7)
∞
where r is the reference trajectory which in our case takes
˙x can be
the form r
found using Eq. 3.

R4. With the optimal control u,

(x

r)

K

−

−

∈

∞

Fig. 1. Hill’s Reference Frame.

2. PROBLEM FORMULATION

The OSAM technique utilized in this work is the egress of
a deputy spacecraft from a chief spacecraft to a relative
parking orbit, where it waits for ingress instructions for
tasks such as repairs, maintenance, or refueling. The orbits
used are described in the linearized Clohessy-Wiltshire
equations, which are derived in Hill’s reference frame.

2.1 Hill’s Reference Frame

The Hill’s reference frame, shown in Fig. 1, centers on the
chief spacecraft, where ˆx pointing outwards from Earth’s
center, ˆz being aligned with the angular momentum vector
of an orbit, and ˆy complete an orthogonal coordinate
system (for a circular orbit, ˆy and the inertial orbital
velocity chief are aligned). Additionally, rh is the position
vector pointing from the chief to the deputy, rc is a vector
from Earth’s center to the chief, and rd is the vector from
Earth’s center to the deputy.

2.2 The Clohessy-Wiltshire Equations

The Clohessy-Wiltshire (CW) equations are the linearized
equations of motion used for a deputy satellite orbiting a
chief satellite (Clohessy and Wiltshire, 1960):

¨x = 2n ˙y + 3n2x + (Fx/m)
(1)
(2)
2n ˙x + (Fy/m)
¨y =
where n is the mean motion of the spacecraft [rad/s] , and
m is the mass of the deputy [kg]. For this problem, out-
of-plane (z-axis) motion is neglected for simplicity. These
equations can be written in state-space form as:

−

˙x = Ax + Bu

(3)

y = Cx

(4)
R4, the control
where the state vector is x = [x, y, ˙x, ˙y]T
umax, umax]2 and A, B and
vector is u = [Fx, Fy]T
−
C matrices are derived from the CW equations converted
to state space. The linearized CW equations are based on
the following assumptions (Petersen et al., 2021):

= [

∈

∈

•
•
•

•
•

≫

the mass of the satellites,

both satellites are rigid bodies,
the mass of Earth
the mass loss of the spacecraft during maneuvers
≪
the total mass of the spacecraft,
the chief spacecraft is in a circular orbit around Earth,
the distance from the chief spacecraft to the deputy
spacecraft (ˆrh)
the distance from the chief space-
craft to Earth’s center ( ˆrc).

≪

3.2 Linear Quadratic Integration (LQI)

LQI is an extension of the standard LQR framework that
includes integral action to the optimal control design to
eliminate steady-state tracking or regulation errors. In our
case, defining the variable ξ:

ξ =

T

0

(cid:31)

(r

−

y) dt

(8)

where the reference values r

R2, and combining Eq. 3

with Eq. 8, the augmented system equations become:

Over all episodes, the solution RL finds is the optimal

behavior function for the situation and ICs, A = π∗(s),

that maximizes the expected cumulative sum of rewards:

(9)

E[J] = E[

γtrt],

(13)

T

t=0

(cid:28)

˙x

˙ξ

=

A 0

C 0

x

ξ

(cid:31)

(cid:30)

(cid:31)

−

(cid:30) (cid:31)

(cid:30)

(cid:31)

(cid:30)

u +

r

0

I

(cid:31)

(cid:30)

˙¯x = ¯A¯x + ¯B ¯u +

∈

B

0

r

+

0

I

(cid:31)

(cid:30)

The performance index of LQI remains quadratic:

J =

∞

[¯x(t)T ¯Q¯x(t) + ¯u(t)T R¯u(t)]dt.

1

2

0

(cid:29)

The ARE and a time-variant Kalman gain are utilized to

calculate the LQI control law,

The final solution is found with a closed-loop system

¯u =

¯K(t)¯x.

−

(10)

version of Eq. 9.

3.3 Linear Quadratic Tracking (LQT)

Linear Quadratic Tracking (LQT) uses the linear dynamic

system in state space form presented in Eq. 3 to minimize

the performance index:

J(to) =

(Cx(T )

r(T ))T P (Cx(T )

r(T ))

−

−

(11)

[(Cx

r)T Q(Cx

r) +u T Ru] dt.

−

−

1

2

T

+

1

2

to

(cid:29)

The main difference between LQR and LQT is an addi-

tional auxiliary function v. The previously used weights

and a new final state weight P are all assigned to the

model, as well as the final time T

=

. The weight

assumptions are Q, P

0 and R > 0 and all must be

∞

symmetric. The time-variant Kalman gain is used, and

≥

the reference trajectory is applied within v instead of u

as seen previously. Both K(t) and v(t) are used to find

the control input,

u =

K(t)x + R−

1BT v(t).

(12)

−

The control input equation in a continuous system is an

affine state feedback due to the additional term added to

the linear state feedback.

3.4 Reinforcement Learning (RL)

RL is a form of machine learning in which one or more

agents learns to complete a task through trial and error.

During each episode, which is the series of interactions

between an RL agent and the environment, the agent

chooses an action At, based on input observation ot. Once

the chosen action is executed , the environment transitions

to a state st+1, output and observation Ω(ot+1 |

and a reward rt = R(st, At, st+1). Figure 2 gives the

st+1, At),

schematic overview of the method.

The environment can be comprised of any system, from

Atari simulations (Hamilton et al., 2020; Alshiekh et al.,

2018) to complex robotics scenarios (Brockman et al.,

2016; Fisac et al., 2018; Henderson et al., 2018; Mania

et al., 2018; Jang et al., 2019; Bernini et al., 2021). RL

is based on the reward hypothesis that all goals can

be met with the maximization of cumulative rewards

(Silver, 2015), but the values of these rewards must be

experimented with for the best solution. In this research,

the agent receives the full state as an observation ot+1 ∈

O.

where T is a finite-time horizon. When γ = 0, the solution

prioritizes immediate reward and when γ = 1 the solution

prioritizes maximizing the expected sum of future rewards.

In this case, the reward functions cover actions such as

traveling towards the rendezvous orbit, reaching an unsafe

velocity, crashing, and other actions considered beneficial

or detrimental to the mission. Training of the RL agent

concluded once the cumulative change in velocity ∆V

and rendezvous time remained stagnant after a series

of slightly differing values for each reward function, and

the best model’s convergence was utilized. This research

uses a Proximal Policy Optimization (PPO) algorithm

(Schulman et al., 2017).

3.5 Tuning of the Controllers

(14)

(15)

The only values being changed for each case are the ICs

in the format xo = [xo, yo, ˙xo, ˙yo]T , and the matrices Q,

R, and P for the linear quadratic controllers. Bryson’s

Rule was utilized to tune the weight matrices of the LQR

with the objective of limiting control and velocity by

designating a maximum value of the states and control.

In the application under consideration, Q

R4

×

4 and

∈

R2

×

2 are given below:

R

∈

Q = diag[1/Q2

x, 1/Q2

y, 1/Q2

˙x, 1/Q2

˙y]

R = diag[1/R2

x, 1/R2

y]

A representative example of tuning values chosen using

Bryson’s Rule is the case in which the maximum distance

from the origin is 200 m, and the maximum desired

velocity outputs and control inputs are 0.5 m/s and 1

N, respectively. This leads to an initial designation of

Qx,y = 200, Q ˙x, ˙y = 0.5, and Rx,y = 1.0.

LQI is based around reducing the error calculated from

another control method’s solution. For this particular

case, the results of an LQR are considered for use in

Eq. 8. The main difference between LQR and LQI is

the added element of complexity in the latter with the

usage of ξ for terms ¯A, ¯B, ¯Q, ¯S, and ¯K being resized. An

additional scalar multiplier term is added to both the -

C section of ¯A and the Identity matrix used in Eq. 9 as

an additional tuning element, decided to be 0.6 for this

problem. Bryson’s rule is not applicable for tuning LQI,

but the Q matrix is tuned in a very similar way to the

previous method, with the addition of two tunable values

for ξ to make the diagonal matrix shown below to tune

position, velocity, and error:

¯Q = diag[Qx, Qy, Q ˙x, Q ˙y, Q ˙z, Qξx , Qξy ]

(16)

Fig. 2. Agent and Environment Interaction in RL.

̸
Britney Rogers  et al. / IFAC PapersOnLine 59-30 (2025) 197–202

199

where the reference values r
with Eq. 8, the augmented system equations become:

R2, and combining Eq. 3

∈

˙x
˙ξ

(cid:31)

=

A 0
C 0

x
ξ

−

(cid:31)

(cid:30)
(cid:30)
˙¯x = ¯A¯x + ¯B ¯u +

(cid:30) (cid:31)

u +

r

0
I

(cid:31)

(cid:30)

B
0

(cid:31)
r

(cid:30)

(9)

+

0
I

(cid:31)

(cid:30)

The performance index of LQI remains quadratic:

J =

1
2

(cid:29)

[¯x(t)T ¯Q¯x(t) + ¯u(t)T R¯u(t)]dt.

∞

0

The ARE and a time-variant Kalman gain are utilized to
calculate the LQI control law,

(10)
−
The final solution is found with a closed-loop system
version of Eq. 9.

¯u =

¯K(t)¯x.

3.3 Linear Quadratic Tracking (LQT)

Linear Quadratic Tracking (LQT) uses the linear dynamic
system in state space form presented in Eq. 3 to minimize
the performance index:

1
2
T

to

(Cx(T )

−

r(T ))T P (Cx(T )

r(T ))

−

[(Cx

−

r)T Q(Cx

−

r) +u T Ru] dt.

(11)

J(to) =

+

1
2

(cid:29)

The main difference between LQR and LQT is an addi-
tional auxiliary function v. The previously used weights
and a new final state weight P are all assigned to the
model, as well as the final time T
. The weight
∞
assumptions are Q, P
0 and R > 0 and all must be
symmetric. The time-variant Kalman gain is used, and
the reference trajectory is applied within v instead of u
as seen previously. Both K(t) and v(t) are used to find
the control input,

≥

=

u =

K(t)x + R−

(12)
The control input equation in a continuous system is an
affine state feedback due to the additional term added to
the linear state feedback.

−

1BT v(t).

3.4 Reinforcement Learning (RL)

RL is a form of machine learning in which one or more
agents learns to complete a task through trial and error.
During each episode, which is the series of interactions
between an RL agent and the environment, the agent
chooses an action At, based on input observation ot. Once
the chosen action is executed , the environment transitions
to a state st+1, output and observation Ω(ot+1 |
st+1, At),
and a reward rt = R(st, At, st+1). Figure 2 gives the
schematic overview of the method.

The environment can be comprised of any system, from
Atari simulations (Hamilton et al., 2020; Alshiekh et al.,
2018) to complex robotics scenarios (Brockman et al.,
2016; Fisac et al., 2018; Henderson et al., 2018; Mania
et al., 2018; Jang et al., 2019; Bernini et al., 2021). RL
is based on the reward hypothesis that all goals can
be met with the maximization of cumulative rewards
(Silver, 2015), but the values of these rewards must be
experimented with for the best solution. In this research,
the agent receives the full state as an observation ot+1 ∈
O.

Over all episodes, the solution RL finds is the optimal
behavior function for the situation and ICs, A = π∗(s),
that maximizes the expected cumulative sum of rewards:

T

E[J] = E[

γtrt],

(13)

t=0
(cid:28)

where T is a finite-time horizon. When γ = 0, the solution
prioritizes immediate reward and when γ = 1 the solution
prioritizes maximizing the expected sum of future rewards.
In this case, the reward functions cover actions such as
traveling towards the rendezvous orbit, reaching an unsafe
velocity, crashing, and other actions considered beneficial
or detrimental to the mission. Training of the RL agent
concluded once the cumulative change in velocity ∆V
and rendezvous time remained stagnant after a series
of slightly differing values for each reward function, and
the best model’s convergence was utilized. This research
uses a Proximal Policy Optimization (PPO) algorithm
(Schulman et al., 2017).

3.5 Tuning of the Controllers

∈

The only values being changed for each case are the ICs
in the format xo = [xo, yo, ˙xo, ˙yo]T , and the matrices Q,
R, and P for the linear quadratic controllers. Bryson’s
Rule was utilized to tune the weight matrices of the LQR
with the objective of limiting control and velocity by
designating a maximum value of the states and control.
4 and
In the application under consideration, Q
R

R4

×

R2

×

2 are given below:
Q = diag[1/Q2

x, 1/Q2
R = diag[1/R2

∈
y, 1/Q2
˙x, 1/Q2
˙y]
x, 1/R2
y]

(15)
A representative example of tuning values chosen using
Bryson’s Rule is the case in which the maximum distance
from the origin is 200 m, and the maximum desired
velocity outputs and control inputs are 0.5 m/s and 1
N, respectively. This leads to an initial designation of
Qx,y = 200, Q ˙x, ˙y = 0.5, and Rx,y = 1.0.

(14)

LQI is based around reducing the error calculated from
another control method’s solution. For this particular
case, the results of an LQR are considered for use in
Eq. 8. The main difference between LQR and LQI is
the added element of complexity in the latter with the
usage of ξ for terms ¯A, ¯B, ¯Q, ¯S, and ¯K being resized. An
additional scalar multiplier term is added to both the -
C section of ¯A and the Identity matrix used in Eq. 9 as
an additional tuning element, decided to be 0.6 for this
problem. Bryson’s rule is not applicable for tuning LQI,
but the Q matrix is tuned in a very similar way to the
previous method, with the addition of two tunable values
for ξ to make the diagonal matrix shown below to tune
position, velocity, and error:

¯Q = diag[Qx, Qy, Q ˙x, Q ˙y, Q ˙z, Qξx , Qξy ]

(16)

Fig. 2. Agent and Environment Interaction in RL.

̸
200

Britney Rogers  et al. / IFAC PapersOnLine 59-30 (2025) 197–202

The LQT controller is tracking the reference trajectory
as a whole, rather than limiting the error of a moving
trajectory point. The Q used for this isn’t the same size as
2, focused
LQR and LQI and instead reduces to a 2
primarily on the position. R is maintained as a 2
2
matrix, regardless of the changes of Q’s size. P is chosen
0.
to be very small for every case, which is valid for P
Another LQT-only tuning measure is that the output can
also be tuned with changing the final time T , but the
scenario limits defined this as two orbits. The values used
for accurately weighting Q, R, P , and in some cases T are
decided upon by trial and error, similarly to LQI.

×

×

≥

During training, the RL ICs start at a random point
in space and end somewhere along a randomly oriented
eNMT, so that the RL agent can learn generalized behav-
ior. The reward function used in this research penalizes
high relative velocity and acceleration (∆V ), which corre-
sponds to high fuel use. Additional rewards are given for
avoiding crashing and reaching the parking orbit.

3.6 Evaluation

The performance of each controller is compared based on
cumulative change in velocity (∆V ) and the time used
for the deputy to reach rt. The change in velocity was
calculated as

∆V =

ux|

|

+
m

uy|

|

∗

∆t.

(17)

(cid:31)

With discrete control being utilized for RL with a zero or-
der hold on control for a specific time step, the continuous
solutions for LQR, LQI, and LQT are discretized for a ∆t
of 1.0 for comparability. The competing objectives are to
minimize total ∆V as well as total time to rendezvous.

Table 1 lists the sets of ICs for the four cases used to
compare controller results.

Table 1. Initial Positions

Case No.
Case 1
Case 2
Case 3
Case 4

x[m]
0
-100
200
-300

y[m]
100
200
300
400

˙x [m/s]
-0.1
-0.25
0.2
0.1

˙y [m/s]
0.1
-0.1
-0.2
0.25

4. SIMULATION RESULTS

Table 3. Rendezvous Time [s]

Method
LQR
LQI
LQT
RL

4.1 Case 1

Case 1 Case 2 Case 3 Case 4
11226
10996
11308
10186

3760
11195
5404
4904

2993
10373
5862
5331

913
10230
1959
2847

The LQR shows the highest peak in instantaneous control
at the very start.The RL agent exhibits slight chatter
and ends with the highest cumulative ∆V of 3.774 N,
followed by LQR solution ∆V of 3.306 N. The next highest
control belongs to LQI, with a value of 2.747 N. The ∆V
decreases substantially for LQT, at 0.633 N. The LQR and
RL maximum velocities are tied at just about 0.4 m/s, as
shown in Figures 3-4.

Fig. 5. Case 2: Position and Velocity Outputs.

Fig. 7. Case 3: Position and Velocity Outputs.

Fig. 3. Case 1: Position and Velocity Outputs.

Fig. 8. Case 3: Control Inputs.

controller is LQT at 1.262 N. This particular case results

in the RL Agent skimming by the origin, which would be

a risky trajectory.

Fig. 6. Case 2: Control Inputs.

4.3 Case 3

The LQI output shows a close pass of the trajectory to

the origin, where the chief satellite is positioned. Although

the ∆V is not the highest at 1.539 N, it is not enough of

a benefit to declare this particular controller the optimal

selection. Alongside this disadvantage is the very near miss

of the LQI velocity limit that shows that, while it doesn’t

exceed the safe bounds, it will not be the best choice of

trajectory. Interestingly enough, the other three controllers

have very similar trajectories coupled with varying ∆V

outputs. The ∆V values of Case 3 are of the same order of

magnitude as Case 1, as shown in Table 3. Regardless of

the negative reward, the RL agent velocity extends past

the bounds of velocity, in Fig. 7 but also has a ∆V of

4.053 N.

4.4 Case 4

This particular set of ICs results in the highest ∆V s

for most of the control methods, with the RL controller

claiming the highest value of 6.276 N, followed by the LQI

output with 4.971 N. This is trailed by the LQR and LQT

Fig. 9. Case 4: Position and Velocity Outputs.

5. CONCLUSION

In this paper, modern optimal control architectures were

compared with RL on a problem involving safe egress to

a distant eNMT. The simulation configurations covered

LQR, LQI, LQT, and RL using the Clohessy-Wiltshire

models for spacecraft dynamics in 2D. We have compared

controller performances with respect to time and largest

cumulative variation in velocity on four different cases,

each characterized by different ICs.

In Case 2, the RL agent violates the maximum velocity
limit of 0.5 m in the y-direction, reaching a peak of around
0.6 m/s. This violation is signified by the intersection of
the RL agent with the gray tinted region in Fig. 5. The
LQR controller has the a high instantaneous control at the
start. The LQI controller has the highest ∆V at 5.566 N,
followed closely behind by RL at 4.763 N. The next highest
value is 2.072 N, belonging to the LQR, and the lowest

values of ∆V , 3.907 N and 1.423 N. All four controllers are

LQR is the simplest modern control method discussed

within the time limit of two orbits and the three modern

and has the basis of controlling the output to maintain

controllers stay within the limit for velocity.

a desired constant value, usually zero, for x. By including

This section compares results from each controller for each
of four different IC cases. Table 3 summarizes the ∆V in
m/s obtained for each of the simulation scenarios.

Fig. 4. Case 1: Control Inputs.

Table 2. ∆V Results [m/s]

4.2 Case 2

Method
LQR
LQI
LQT
RL

Case 1 Case 2 Case 3 Case 4
3.907
3.306
4.971
2.747
1.423
0.633
6.276
3.774

2.072
5.566
1.262
4.763

1.626
1.539
0.603
4.053

Britney Rogers  et al. / IFAC PapersOnLine 59-30 (2025) 197–202

201

controller is LQT at 1.262 N. This particular case results
in the RL Agent skimming by the origin, which would be
a risky trajectory.

Fig. 5. Case 2: Position and Velocity Outputs.

Fig. 7. Case 3: Position and Velocity Outputs.

Fig. 8. Case 3: Control Inputs.

Fig. 6. Case 2: Control Inputs.

4.3 Case 3

The LQI output shows a close pass of the trajectory to
the origin, where the chief satellite is positioned. Although
the ∆V is not the highest at 1.539 N, it is not enough of
a benefit to declare this particular controller the optimal
selection. Alongside this disadvantage is the very near miss
of the LQI velocity limit that shows that, while it doesn’t
exceed the safe bounds, it will not be the best choice of
trajectory. Interestingly enough, the other three controllers
have very similar trajectories coupled with varying ∆V
outputs. The ∆V values of Case 3 are of the same order of
magnitude as Case 1, as shown in Table 3. Regardless of
the negative reward, the RL agent velocity extends past
the bounds of velocity, in Fig. 7 but also has a ∆V of
4.053 N.

4.4 Case 4

This particular set of ICs results in the highest ∆V s
for most of the control methods, with the RL controller
claiming the highest value of 6.276 N, followed by the LQI
output with 4.971 N. This is trailed by the LQR and LQT
values of ∆V , 3.907 N and 1.423 N. All four controllers are
within the time limit of two orbits and the three modern
controllers stay within the limit for velocity.

Fig. 9. Case 4: Position and Velocity Outputs.

5. CONCLUSION

In this paper, modern optimal control architectures were
compared with RL on a problem involving safe egress to
a distant eNMT. The simulation configurations covered
LQR, LQI, LQT, and RL using the Clohessy-Wiltshire
models for spacecraft dynamics in 2D. We have compared
controller performances with respect to time and largest
cumulative variation in velocity on four different cases,
each characterized by different ICs.

LQR is the simplest modern control method discussed
and has the basis of controlling the output to maintain
a desired constant value, usually zero, for x. By including

202

Britney Rogers  et al. / IFAC PapersOnLine 59-30 (2025) 197–202

learning via shielding. In Thirty-Second AAAI Confer-
ence on Artificial Intelligence, 2669–2678.

Arney, D., Sutherland, R., Mulvaney, J., Steinkoenig, D.,
Stockdale, C., and Farley, M. (2021). On-orbit servicing,
assembly, and manufacturing (osam) state of play.

Bernini, N., Bessa, M., Delmas, R., Gold, A., Goubault,
E., Pennec, R., Putot, S., and Sillion, F. (2021). A few
lessons learned in reinforcement learning for quadcopter
attitude control. In Proceedings of the 24th International
Conference on Hybrid Systems: Computation and Con-
trol, 1–11. Association for Computing Machinery, New
York, NY, USA.

Brockman, G., Cheung, V., Pettersson, L., Schneider, J.,
Schulman, J., Tang, J., and Zaremba, W. (2016). Openai
gym.

Clohessy, W. and Wiltshire, R. (1960). Terminal guidance
system for satellite rendezvous. Journal of the aerospace
sciences, 27(9), 653–658.

Fisac, J.F., Akametalu, A.K., Zeilinger, M.N., Kaynama,
S., Gillula, J., and Tomlin, C.J. (2018). A general
safety framework for learning-based control in uncertain
robotic systems.
IEEE Transactions on Automatic
Control, 64(7), 2737–2752.

Hamilton, N., Schlemmer, L., Menart, C., Waddington,
C., Jenkins, T., and Johnson, T.T. (2020). Sonic to
knuckles: evaluations on transfer reinforcement learning.
In Unmanned Systems Technology XXII, volume 11425,
114250J. International Society for Optics and Photonics.
Henderson, P., Islam, R., Bachman, P., Pineau, J., Precup,
D., and Meger, D. (2018). Deep reinforcement learning
that matters. In Proceedings of the AAAI Conference
on Artificial Intelligence, volume 32, 3207–3214.

Jang, K., Vinitsky, E., Chalaki, B., Remer, B., Beaver,
L., Malikopoulos, A.A., and Bayen, A. (2019). Simula-
tion to scaled city: zero-shot policy transfer for traffic
control via autonomous vehicles. In Proceedings of the
10th ACM/IEEE International Conference on Cyber-
Physical Systems, 291–300.

Lee, D. and Pernicka, H. (2010). Optimal control for prox-
International Journal

imity operations and docking.
Aeronautical and Space Sciences, 11(3), 206–220.

Lewis, F.L. and Syrmos, V.L. (1995). Optimal control,

129–203, 215–229. John Wiley & Sons, 2 edition.

Mania, H., Guy, A., and Recht, B. (2018). Simple random
search of static linear policies is competitive for rein-
forcement learning.
In Proceedings of the 32nd Inter-
national Conference on Neural Information Processing
Systems, 1805–1814.

Mote, M.L., Hays, C.W., Collins, A., Feron, E., and Hobbs,
K.L. (2021). Natural motion-based trajectories for au-
tomatic spacecraft collision avoidance during proxim-
ity operations.
In 2021 IEEE Aerospace Conference
(50100), 1–12. IEEE.

Petersen, C.D., Hobbs, K., Lang, K., and Phillips, S.
(2021). Challenge problem: assured satellite proximity
operations. In 31st AAS/AIAA Space Flight Mechanics
Meeting.

Schulman, J., Wolski, F., Dhariwal, P., Radford, A., and
Klimov, O. (2017). Proximal policy optimization algo-
rithms. arXiv preprint arXiv:1707.06347.

Silver, D. (2015). Lectures on reinforcement learning.

url: https://www.davidsilver.uk/teaching/.

Fig. 10. Case 4: Control Inputs.

the reference trajectory in the calculation of u, LQR is
converted to maintaining the value of zero of (x
r) instead
and following the desired eNMT orbit. This edit works
somewhat well for the purpose and keeps within the safety
limits chosen, but the total ∆V is higher than other control
methods set within the same problem.

−

LQI is excellent for reducing steady state error to zero
for a constant value rather than following a trajectory.
Adding the integral of the error greatly decreases the
steady state error and makes any sort of disturbance, force,
or model uncertainty insignificant. The positive outcome
from converting the LQR to follow a time-based trajectory
instead of simply reducing the x to the desired value is
applied to LQI as well, but the outcome has greater ∆V
and rendezvous time. The integral action and disturbance
rejection of LQI increases the robustness of the model and
would be considered a major benefit, but is not displayed
by the chosen problem.

LQT is used for more complex trajectory tracking in
particular, rather than maintaining a constant value by
reducing x to the desired constant value. Regardless of the
simple trajectory instead of a complex one, the problem
statement of falling into a specific eNMT orbit is best
done by LQT out of all modern control methods. However,
the strict time limit T required the spacecraft navigation
as LQI and LQR can.
solution to end, rather than t

→ ∞

The RL agent’s output is comparable to the modern
control methods, as shown by the ∆V and rendezvous
time comparisons. A better trained model may result
in a better maneuvering, but limited training time and
experience created slight issues that ultimately affected the
final results, such as chattering and exceeding the desired
safety threshold. Even so, there is potential for the future
of RL in spacecraft maneuvering with a more adept model
and environment used, as well as more time to train to
achieve optimal results that stay within the velocity limit
of the structural damage threshold.

REFERENCES

Alfriend, T., Junkins, J., and Vadali, S. (2010). Spacecraft
Formation Flying: Dynamics, Control, and Navigation.
Elsevier.

Alshiekh, M., Bloem, R., Ehlers, R., K¨onighofer, B.,
Niekum, S., and Topcu, U. (2018). Safe reinforcement

