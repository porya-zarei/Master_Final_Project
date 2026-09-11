Available online at www.sciencedirect.com
ScienceDirect

Advances in Space Research 73 (2024) 5741–5755

www.elsevier.com/locate/asr

Deep reinforcement learning spacecraft guidance with state
uncertainty for autonomous shape reconstruction of
uncooperative target

Andrea Brandonisio ⇑, Lorenzo Capra 1, Miche`le Lavagna

Aerospace Department, Politecnico di Milano, 20157 Milan, Italy

Received 15 November 2022; received in revised form 26 June 2023; accepted 3 July 2023
Available online 7 July 2023

Abstract

In recent years, space research has shifted heavily its focus towards enhanced autonomy on-board spacecrafts for on-orbit servicing
activities (OOS). OOS and proximity operations include a variety of activities: the focal point of this work is the autonomous guidance of
a chaser spacecraft for the shape reconstruction of an artiﬁcial uncooperative object. Adaptive guidance depends on the ability of the
system to build a map of the uncertain environment, ﬁguring out its location inside of it and accordingly determining the control
law. Thus, autonomous navigation is framed as an active Simultaneous Localization and Mapping (SLAM) problem and modeled as
a Partially Observable Markov Decision Process (POMDP). A state-of-the-art Deep Reinforcement Learning (DRL) method, Proximal
Policy Optimization (PPO), is investigated to develop an agent capable of cleverly planning the shape reconstruction of the target. Start-
ing from previous research on the topic, this work develops further proposing a continuous action space, such that the agent is no more
forced to choose between a predeﬁned set of possible discrete actions, ﬁxed both in magnitude and direction. In this way any combination
of the three-dimensional thrust vector components is available. The chaser spacecraft is a small satellite mounting an electric propulsion
engine deﬁning the action space range, in linearized eccentric relative motion with the selected uncooperative object. Through a rendered
triangular mesh, the agent capabilities of geometry reconstruction and mapping are evaluated, considering the number of quality pictures
made for each face. Extensive training tests are performed with random initial conditions to verify the generalizing capability of the DRL
agent. The results are then validated in a comprehensive testing campaign, whose primary focus is the introduction of noisy measure-
ments coming from navigation, aﬀecting pose estimation. The sensitivity of the proposed method to this condition is analyzed and
the eﬃciency of a retraining procedure is examined. The applicability of DRL methods and neural networks to support autonomous
guidance in a close proximity scenario is corroborated and the technique employed is vastly tested and veriﬁed.
(cid:1) 2023 COSPAR. Published by Elsevier B.V. This is an open access article under the CC BY license (http://creativecommons.org/licenses/by/4.0/).

Keywords: On-orbit servicing; Relative dynamics; Reinforcement learning; State uncertainty; Shape reconstruction

⇑ Corresponding author.

E-mail addresses: andrea.brandonisio@polimi.it
(L.

(A. Brandonsio),
michelle.lavagna@polimi.it

Capra),

lorenzo.capra@polimi.it
(M. Lavagna).

1 Equal contribution.

1. Introduction

Enhanced autonomy is driving the research of leading
space agencies, as spacecraft independence would allow
for reliable, cost-eﬀective, lower risk services, and for much
more ﬂexibility in future missions planning of a space vehi-
cle. Concerning the application of these studies, on-orbit
servicing (OOS) activities (Joshua et al., 2019) have
recently gained a lot of interest: maintenance, refueling,

https://doi.org/10.1016/j.asr.2023.07.007
0273-1177/(cid:1) 2023 COSPAR. Published by Elsevier B.V.
This is an open access article under the CC BY license (http://creativecommons.org/licenses/by/4.0/).

A. Brandonisio et al.

Advances in Space Research 73 (2024) 5741–5755

debris mitigation, upgrade, repair, assembly, relocation,
orbit modiﬁcation and non-contact support are some of
the operations included in this deﬁnition. An increased
level of autonomy while carrying out these activities would
lead to major beneﬁts. These operations share a similar sce-
nario, in which two objects are in relative motion and inter-
acts in some kind of form, generally with the ﬁrst one,
referred to as the servicer, performing some action on the
second, called client. The work here presented develops
an innovative adaptive guidance algorithm for the path-
planning of a chaser spacecraft trajectory around an unco-
operative artiﬁcial object, aiming to the shape and map
reconstruction of the latter. As speciﬁed, in this scenario
the client is non-cooperative, so it does not interact directly
with the servicer, and it is not able to exchange information
with it. In this context,
the spacecraft autonomously
explores
the surrounding environment, understanding
where it is located inside of it, and consequently choosing
the actions to take according to a certain objective function
to be deﬁned. Thus, the problem falls in the Simultaneous
Localization and Mapping (SLAM) (Durrant-Whyte and
Bailey, 2006) framework, and since the planning operations
is also performed, it is called active. This problem formula-
tion has been widely researched in the last few years, par-
ticularly in the ﬁeld of robotics. An overview on active
SLAM state-of-the-art is given by Placed et al. (2023).
SLAM may be phrased as a Partially Observable Markov
Decision Process (POMDP) (Sutton and Barto, 2018),
which entails an agent interacting with the environment
and exchanging information with it. POMDP derives from
Markov Decision Process (MDP), which is a stochastic
control process, that does not have any memory. Nowa-
days, according to (Silvestrini et al., 2023), Deep Rein-
forcement Learning (DRL) is the most common method
to solve both MDP and POMDP, whose goal is to solve
for the decision-making policy of the agent. Reinforcement
Learning (RL) algorithms are a powerful tool when dealing
with decision-making problems and the combination with
Neural Networks (NN) in DRL allows to improve the gen-
eralizing capabilities of the resulting policy, and to solve
characterized
more
high-
dimensional and continuous
state and action spaces
(Sutton and Barto, 2018). Even if POMDP represents the
ﬁrst step in applying policy models in the real world scenar-
ios, it is worth to underline how it still remains a problem
in RL since directly viewing partial observations as full
states violates the Markov property of state transitions:
this is particularly problematic when the system is strongly
aﬀected by historical
information or large state/action
spaces. The ﬁrst problem is treated in (Xie et al., 2023),
where the addition of long memory ability is proposed;
while the second is handled with alternative Actor-Critic
formulation for a multi-component
in
(Andriotis and Papakonstantinou, 2019).

systems, as

problems

complex

by

Diﬀerent applications of machine learning techniques
have been studied in the last few years in the context of
guidance, navigation and control. Starting from relative

5742

the

and

control

Instead,

motion scenarios, in Silvestrini and Lavagna (2021b) and
Silvestrini and Lavagna (2021a), neural networks are
exploited to help a model predictive control (MPC) guid-
ance and control system in learning the dynamics of the
environment and be able to safely maneuver the spacecraft
or reconﬁgure distributed systems. In Silvestrini et al.
(2022a) and Silvestrini et al. (2022b), a step further is
accomplished using supervised learning trained convolu-
tional networks as embedded navigation system for lunar
lending and relative motion rendezvous scenarios. How-
ever, all these works focus on well-established GNC guid-
ance
ﬁrst
algorithms.
formulation as a POMDP for a spacecraft guidance design
problem was proposed by Pesce et al. (2018) and then
developed further in Chan and Agha-mohammadi (2019)
and Piccinin et al. (2022), who adopted Reinforcement
Learning (RL) to plan the trajectory of a chaser spacecraft
for small-bodies imaging. These works adopted an active
SLAM formulation based on RL algorithms, such as
NFQ (Neural Fitted Q) and DQN (Deep Q Network),
which nowadays have been outperformed by other meth-
ods more suitable for continuous state-action space prob-
lems, like PPO. Major contributions to the application of
RL advanced techniques, as the PPO algorithm, are given
by Gaudet et al. (2020a) and Gaudet et al. (2020b), who
investigates, among others, planetary landing and close
proximity operations. This particular RL approach has
been proved eﬀective in diﬀerent environments as the circu-
lar restricted three-body problem (CR3BP) framework
(Scorsoglio et al., 2023) and compared to cloning tech-
niques, as done by Federici et al. (2021).

This work takes shape from our previous studies
(Brandonisio et al., 2021; Capra et al., 2023), where, for
the ﬁrst time, these tools were exploited for the guidance
and control of a chaser spacecraft aimed at reconstructing
the shape of an artiﬁcial object. The selected target is
VESPA (Vega Secondary Payload Adapter), and the chaser
spacecraft is a small satellite equipped with both visible and
thermal infrared cameras and a single thruster with electric
propulsion. A state-of-the-art Deep Reinforcement Learn-
ing algorithm, Proximal Policy Optimization (PPO)
(Schulman et al., 2017), is investigated to solve for the
chaser decision-making policy, mapping the input observa-
tions to the action to take. An extensive testing campaign is
performed, to verify the results and analyze the model
robustness and sensitivity to several diﬀerent conditions.
In particular, a detailed analysis of the performance in
presence of state uncertainty is presented. Therefore, this
paper, starting from this background, develops the formu-
lation further, removing some limiting assumptions and
testing a more realistic, ﬂexible, and robust architecture.
In particular, we want to analyze two diﬀerent aspects:
the improvement of the action space from a discrete space
to a continuous one, and the study of how the agent
performance are aﬀected by state uncertainty. The aim is
to take a step forward in the autonomous mapping of
uncooperative artiﬁcial space objects, thus conﬁrming the

A. Brandonisio et al.

Advances in Space Research 73 (2024) 5741–5755

applicability of these DRL techniques to support a poten-
tial exploratory mission around VESPA, as currently
explored by the ESA e.Inspector project (Silvestrini et al.,
2020).

2. Problem statement

The development of an autonomous guidance algorithm
depends on the overall architecture, which is described in
Fig. 1. The part of the block diagram that is highlighted
represent what has been developed in this work, while the
other blocks are reported with the intention of giving the
overall picture of the close proximity GNC scenario.

The inputs to the guidance block are the relative motion
between the chaser and the target object (ex. VESPA), and
the relative attitude between the two. These information
may come from diﬀerent sensors sources. In this work,
the inputs have been considered as generated by image
processing and pose estimation tools. A vision-based
navigation system may employ both visible (VIS) and
thermal
infrared (TIR) imaging. In Brandonisio et al.
(2021), only a VIS is considered to generate the input of
the autonomous agent, and to deﬁne the reward model nec-
essary to train it under the mission objectives. A coupled
approach (VIS + TIR) has been proposed by Civardi
et al. (2024), where it demonstrated the eﬀectiveness of
combining imagery from diﬀerent bands to space naviga-
tion purpose in proximity operation scenarios. This allows
to avoid problems of illumination condition typical of
VIS-only systems, as underlined by Brandonisio and
Lavagna (2021).

The implementation of the navigation system is out of
the scope of the presented work, that focuses on the devel-
opment of the guidance algorithm; therefore, the informa-

tion regarding relative motion and target attitude are
assumed to be known at each step during the nominal case.
As anticipated, state uncertainty will be then introduced
and the model will be tested against it to assess its
robustness. The output of the guidance algorithm is the
trajectory that the spacecraft should follow to achieve the
mission objectives, consisting in the target object shape
reconstruction map, which can be retrieved via stereopho-
toclinometry (SPC) methodology developed by Gaskell
(2001).

2.1. Problem dynamics

This section introduces the dynamics models that
express the relative motion between the chaser and the tar-
get. The equations of motion can be linearized under the
assumption of a very low chaser-target relative distance
with respect to the main attractor distance. The linearized
eccentric model here exploited is the one proposed by
Inalhan et al. (2002), selected as a result of a trade-oﬀ
between dynamics accuracy and computational eﬃciency.
The equations are reported in Eq. 1, considering the Local
Vertical Local Horizontal (LVLH) reference frame cen-
tered in the target object center of mass:
8
><

ð1Þ

r3 x þ 2x _y þ x2x
r3 y (cid:2) 2x_x (cid:2) x2y

€x ¼ 2l
€y ¼ (cid:2)l
€z ¼ (cid:2)lz
r3

>:

where r is the radius of the target orbit, l is the primary
attractor gravitational parameter, and x ¼ _f , deﬁned in
Eq. 2, is the time derivative of the target true anomaly,
expressed as follows:
ð
x ¼ _f ¼ n 1 þ e cos f
Þ3
ð
1 þ e2

ð2Þ

Þ2

2

with f being the target true anomaly, e its orbit eccentricity,
and n ¼

the mean motion.

p

ﬃﬃﬃ
l
r3

Concerning the relative target attitude motion, this
work follows
the two main assumptions deﬁned in
Brandonisio et al. (2021), exploited to simplify the already
quite complex problem: target small angles rotation and
chaser camera always pointed toward the target center.
In this way, the spacecraft attitude dynamics control is
completely neglected and the Euler equations for the target
in the LVLH reference frame can be approximated as
expressed in Eq. 3.
8
><

I x

(cid:3)

(cid:4)

_hy þ n2 I z (cid:2) I x
ð
(cid:4)
_hx þ n2 I z (cid:2) I x
ð

Þhx ¼ 0
Þhy ¼ 0

(cid:3)

€hx þ n I z (cid:2) I y (cid:2) I x
€hy þ n I x þ I y (cid:2) I z
€hz ¼ 0

>:

I y

I z

ð3Þ

Fig. 1. Fly-around planning architecture.

5743

with I x; I y; I z being the target object principal components
of inertia, hx; hy; hz being the Euler angles around the three
directions of the LVLH reference frame, and _hi; €hi the cor-
responding ﬁrst and second time derivative.

A. Brandonisio et al.

2.2. Visibility model

At each step of the simulation, a visibility model is nec-
essary to evaluate which parts of the target are observable
by the VIS and/or TIR cameras. The model is based on the
target object shape, that is designed with a triangular mesh.
This makes the deﬁnition of other possible shapes easier,
without changing the visibility framework. As already
introduced, in this work the analysis have been carried
out considering VESPA as target object, and its triangular
mesh is shown in Fig. 2.

Two main parameters aﬀects the visibility model:

(cid:3) The cameras ﬁeld of view (FOV);
(cid:3) The incidence angle between the cameras and each of

the mesh faces.

If only the VIS camera is present on the chaser space-
craft, also the Sun incidence angle becomes greatly impor-
tant to deﬁne the visibility of the object.Knowing the
relative pose between chaser and target, the normal vector
of each faces can be computed, and consequently also the
incidence angle. All the faces inside the camera FOV are
considered visible. The reconstruction of the map is ideally
performed during the image processing step, which, as
already mentioned, is out of the scope of the presented
work. Anyway, the selection of the shape reconstruction
method is important for the formulation of the reward
model. Following the deﬁnition presented in Brandonisio
et al. (2021), the main requirements for a good shape
reconstruction with SPC can be expressed mathematically
by the follow conditions:

(cid:3) minimum of 3 images per face;
(cid:3) incidence angle of 45(cid:4) (with acceptable range between

10(cid:4) (cid:2) 50(cid:4) and limits between 5(cid:4) (cid:2) 60(cid:4))

Advances in Space Research 73 (2024) 5741–5755

There should be also few additional recommendations
on the sun incidence angle conditions, negligible when
the architecture also adopts thermal infrared cameras, as
in this case.

3. Autonomous guidance

The autonomous exploration and trajectory planning in
an unknown environment can be formulated as an active
Simultaneous Localization and Mapping (SLAM) prob-
lem, in which an agent builds a map of its surroundings
while concurrently estimating its positions and planning
the next action to take. This problem can be phrased as a
Partially Observable Markov Decision Process (POMDP).
The next section aims at developing the mathematical tools
necessary to understand the problem and how it is solved.

3.1. Partially observable Markov Decision Process

A POMDP is a Markov Decision Process (MDP) with
state uncertainty, meaning the agent cannot know the true
state, but only a belief state using observations. This for-
mulation is valid whenever the agent senses the environ-
ment via sensors, which inherently introduce errors in
their measurements, or when it may not be able to observe
all the state variables describing the environment.

A POMDP is characterized by a 6-tuple.
(S, A, R, T, X, O):

(cid:3) S is the space of all possible states in the environment;
(cid:3) A is the space of all possible actions that can be taken in

all the states of the environment;

(cid:3) R is the reward function, guiding the action selection to

maximize it;

(cid:3) T s; s0
ð

Þ is the transition function governing the proba-
bility of moving from one state to the next, given the
current state and action;

(cid:3) X is the space of possible observations;
(cid:3) O o0ja; s0
ð

Þ is the probability of making a particular
observation, taking an action that leads to a particular
new state.

This type of problems is quite complex to solve and may
become computationally intractable if not reduced to a
simpler MDP. This can be done including the history h,
that plays the role of an archive of past actions and obser-
vations. The new formulation, known as belief-space
MDP, is described by a 4-tuple (B, A, R, T):

(cid:3) B is the belief space, where the belief is deﬁned as
Þ, so it is the probability of being in a certain

b ¼ p sjhð
state s after the history h.

A, R, and T have the same meaning described before.
The solution to the belief-space MDP is a policy p, which
represents the mapping function from states to actions that
the agent is employing. This decision-making feature is

Fig. 2. Triangular mesh of VESPA.

5744

A. Brandonisio et al.

Advances in Space Research 73 (2024) 5741–5755

optimal if the agent concurrently maximizes the reward
function, thus reaching the goal eﬀectively. In case of an
inﬁnite horizon problem, the optimal policy is deﬁned as
in Eq. 4:

#

p(cid:5) ¼ argmax

p

Ep

ð
ckR ak; bk

Þ

ð4Þ

"

X1

k¼0

(cid:6)

where c 2 0; 1½
introduced as a
is the discount factor,
mechanism to control how myopic or short-sided is the
agent, exponentially decaying the eﬀect of rewards far away
in time. R represents indeed the reward signal, depending
on the action a and belief b at step k.

4. Deep reinforcement learning

Reinforcement Learning is a widely employed tool for
solving MDPs (Sutton and Barto, 2018), and its combina-
tion with Neural Networks for function approximation,
allows to solve many complex problems characterized by
high-dimensionality and partial observability. A state-of-
the-art Deep Reinforcement Learning algorithm for con-
tinuous state and action space problems, called Proximal
Policy Optimization (PPO) (Schulman et al., 2017), is con-
sidered for the optimization of the spacecraft decision-
making policy.

4.1. Proximal policy optimization

PPO is a policy-gradient method, belonging to the
Actor-Critic family (Mnih et al., 2016). It outclasses most
of the other DRL algorithms in many typical benchmark
problems, because of its improved training stability. It
builds up from the Trust Region Policy Optimization
(TRPO) method (Schulman et al., 2015), retaining its reli-
ability and data eﬃciency, but handling the loss function
in a much simpler and well-planned fashion. Starting from
the TRPO loss function, which exploits the probability
ratio, deﬁned in Eq. 5, between the policy at subsequent
timesteps, PPO increases training robustness by clipping
the objective function and limiting the possible update, so
that the policy does not change drastically. This simple
expression is reported in Eq. 6.

pw akjsk
Þ
ð
pw ak(cid:2)1jsk(cid:2)1
ð
½
ð

hð Þ ¼

pk

Þ

ð5Þ

ð

Þ

(cid:6)Ak

ð6Þ

LCLIP wð Þ ¼ bEk min pk wð Þ; clip pk wð Þ; 1 (cid:2) (cid:2); 1 þ (cid:2)
Þ
In both Eq. 5 and Eq. 6, w refers to the networks parame-
ters (i.e. their weights and biases). The parameter (cid:2) indi-
cates the clipping factor (generally selected in the range
½
(cid:2) 2 0; 0:2
Common practice in PPO algorithms is the addition of
an entropy regularization term to the clipping objective
function, as in Eq. 7, to ensure a suﬃcient exploration level
during training:
LPPO wð Þ ¼ LCLIP wð Þ þ c2S pwð

(cid:6)), while Ak is the advantage function at step k.

ð7Þ

Þsk

where S pwð
Þ is the entropy bonus term, that is function of
the current policy, and c2 a scalar multiplying factor that
determines the inﬂuence of the entropy term on the overall
loss function.

From the A2C formulation (Mnih et al., 2016), the
advantage function A is retained, and represents how better
a selected action is compared to all the others at a given
state. It is simply computed as the diﬀerence between the
discounted reward r and the state value function V base-
line, computed by the critic network. This concept is
described in Eq. 8.

#

ð
A sk; ak

Þ ¼

cj(cid:2)kr sk; ak
ð

Þ

(cid:2) V skð Þ

ð8Þ

"

XT

j¼k

The agent stores a number of transitions speciﬁed by the
batch dimension of the experience buﬀer, by interacting
with the environment, and then exploits them to update
the networks via backpropagation. This way the networks
adjust their parameters to better ﬁt the problem objectives.

5. Planning architecture

This work proposes an innovative decision-making pro-
cess to autonomously plan the pseudo-optimal guidance
around the uncooperative space object VESPA, with Deep
Reinforcement Learning. This is coupled with a pre-
processing phase, in which information coming from the
external environment, sensors and the object conditions
are elaborated to estimate the state. Once again, it is high-
lighted that this part is out of the scope of this work, and as
such, the developed analysis starts with this information
given for granted as input. The state is then fed to the
autonomous guidance agent which crafts the control policy
to maximize the reward, aﬀecting the environment and all
the others information providers. In the next sections, a
detailed and critical description of all the architecture com-
ponents is presented, according to the DRL framework.

Environment model. It represents everything surrounding
the agent and, in this context, it is the relative dynamics
model governing the reciprocal motion between the chaser
and the target, the attitude motion of the object and the
visibility model. In particular, the relative motion between
the two objects is directly aﬀected by the agent actions, that
inﬂuence the set of equations. With respect to Brandonisio
et al. (2021), the implementation of a vision-based system,
exploiting also thermal infrared imagery, allows to reduce
the applicability constraints and removes a few assump-
tions: unfavorable illumination conditions are no more
an issue, like an inadequate incidence angle between the
Sun direction and the normal of the mesh faces, or Earth
eclipses and reﬂections. The main part of this work selects
VESPA as target object. VESPA is a space debris (the
upper stage of the VEGA launcher), currently orbiting
around the Earth, and it is of huge interest for several pro-
jects, like the ClearSpace-1 mission or the e.Inspector pro-
ject (Silvestrini et al., 2020), funded by the European Space

5745

A. Brandonisio et al.

Advances in Space Research 73 (2024) 5741–5755

Table 1
Orbital elements of VESPA.
a km½

e

(cid:6)

6878

0.009633

i (cid:4)½ (cid:6)

98

X (cid:4)½ (cid:6)

0

x (cid:4)½ (cid:6)

0

f (cid:4)½ (cid:6)

0

Agency. To simulate both its orbital and rotational
motion, the inertial properties and keplerian parameters
are approximated as reported in Eq. 9 and Table 1.

2

6
4

I ¼

3

0:5208
0

0

0
0:5208
0

0
0
0:6667

7
5kgm2

ð9Þ

State model. The state space models all the information
coming from the environment. Taking inspiration from
Brandonisio et al. (2021), at ﬁrst it is assumed that the
agent has the knowledge of the correct state variables at
each timestep. Obviously, in practice all the input data
derive from sensor measurements, which inherently intro-
duce errors. This uncertainty is studied in the second part
of the paper, where the sensitivity analysis tests have been
performed. In general, the input vector, with which the
agent is trained, should be tailored in such a way that it
contains only essential
the decision-
making process, to build a policy capable of selecting the
appropriate action in every condition the agent may ﬁnd
itself. In this case, the variables are the ones that properly
identify the close proximity scenario and facilitate the
agent learning. Moreover, a key factor to be considered
is the possibility of estimating these quantities by means
of on-board instruments, which is of fundamental impor-
tance for an autonomous spacecraft.

information for

9
>>>=
>>>;

8
>>><
>>>:

p

v
h
_h

¼

S ¼

9

>>>>>>>>>>>>>>>>>>>>>>>>=
>>>>>>>>>>>>>>>>>>>>>>>>;

8

>>>>>>>>>>>>>>>>>>>>>>>><
>>>>>>>>>>>>>>>>>>>>>>>>:

x

y

z
_x
_y
_z
hx
hy
hz
_hx
_hy
_hz

The state in Eq. 10 contains the relative motion (posi-
tion p and velocity v) between the chaser and the target,
together with the attitude information about VESPA, in
terms of Euler angles and angular velocities (h; _h).

Action model. The action space represents all the possi-
ble decisions that the agent could take at each timestep
with its policy. In this work, the agent can interact with
the surrounding environment by means of the acceleration

5746

vector a, representative of the control action, that directly
aﬀects the equations of motion as expressed in Eq. 11. This
kind of action control can easily represent a thrust vector
coming from the thruster.
8
><

ð11Þ

r3 x þ 2x _y þ x2x þ ax
r3 y (cid:2) 2x_x (cid:2) x2y þ ay

>:

€x ¼ 2l
€y ¼ (cid:2)l
€z ¼ (cid:2)lz
r3
(cid:6)
(cid:5)
ax; ay; az

þ az

(cid:6)

(cid:5)

is the control vector given by the thruster.
This section encapsulates one of the main advancement
developed by this work. Current research on the topic
developed in Brandonisio et al. (2021); Brandonisio and
Lavagna (2021) adopts a discrete action space, so that the
action is selected between a set of predeﬁned thrust
impulses ﬁxed both in direction and magnitude, as in Eq.
12.
A ¼ þT x; (cid:2)T x; þT y; (cid:2)T y; þT z; (cid:2)T z; 0
ð12Þ
where, for example, þT x means a thrust action aligned with
the +x direction of the chaser’s body. With a continuous
action space, instead, the control action becomes a tridi-
mensional vector, that ideally is free to point towards the
entire 3D space, without being constrained by some speciﬁc
direction. Moreover, since it is continuous, the magnitude
of the thrust vector can vary inside the limits speciﬁed by
the propulsion system on-board. To deﬁne the action
space, an electric propulsion system with a single thruster
(Martı´nez et al., 2019) is employed. The most notable attri-
bute aﬀecting the formulation is the maximum thrust and
the minimum impulse bit (MIB), since they deﬁne the range
inside which the decision-making policy can select the mag-
nitude of the action. Another important parameter for the
action model is the control interval Dt, that deﬁnes the time
elapsing between one control action and the other. The set-
ting of these parameters entails a trade-oﬀ between ﬁdelity
of the control frequency and computational burden. In the
training section, the resulting analysis on the continuous
action space model will be presented. In the testing section,
instead, a sensitivity analysis comparison between the dis-
crete and continuous models will be described in terms of
state uncertainty.

Reward model. The reward function is one of the main
characters, if not the main one, when talking about Rein-
forcement Learning. It drives the agent policy, aiming at
maximizing it by means of positive and negative scores,
which should incentivize a speciﬁc agent behavior. The
reward here deﬁned phrases the objectives and constraints
of the problem in mathematical form with diﬀerent scores’
formulations:

(cid:3) distance score: in the case of proximity operations, a
general and intuitive idea is that the chaser spacecraft
shall not crash onto the target, nor escape far away from
it. This constraint is formulated adopting a lower and
upper limit in terms of relative distance between the
two objects. In this way it is intrinsically introduced

ð10Þ

A. Brandonisio et al.

Advances in Space Research 73 (2024) 5741–5755

safety in the operations, by incentivizing the agent to
avoid dangerous regions of space, in which the mission
would completely fail. Note that this bounded region
represents also a possible terminal state for the agent:
if the lower or the upper limit are overcome, then the
episode ends and the agent is given a negative reward
signal. The associated mathematical expression and
score are reported in Eq. 13:

in visibility of the camera, and a picture of one of
these faces is said to be of ‘‘good quality” if the
reward signal re associated to that single face is
greater than zero.

M %;k ¼

N q
N p (cid:5) nfaces
8
><

1

if M %;k > M %;k(cid:2)1
if M %;k ¼ 100
otherwise

ð16Þ

ð17Þ

(cid:7)

rd ¼

(cid:2)100
1

if d 6 Dmin or d P Dmax
otherwise

ð13Þ

rm ¼

>:

100
0

where d ¼ kpk is the distance between chaser and target,
with Dmin ¼ 50m and Dmax ¼ 500m.

(cid:3) incidence angle score: regarding the main goal of the pre-
sented work, the agent should maximize a reward func-
tion that enables it to better map the target. This is
strictly connected to the adopted mapping technique,
that, being SPC, requires to assert some speciﬁc condi-
tions in terms of incidence angle and number of quality
images per mesh face, as discussed before. At each time-
step the agent keeps track of the target rotation and re-
computes the normal direction for each of the mesh
faces. First, a screening of the faces that are in the ﬁeld
of view of the spacecraft’s cameras is performed. Then,
the angle, e, between each of the normal directions of the
faces in visibility and the camera vector, assumed as
continuously pointing the target center, is calculated.
A score, reported in Eq. 14, is formulated on the base
of the visibility model deﬁned in Section 2.2:

re ¼

8
>>><
>>>:

1
e (cid:2) 1
1
5
e
6 (cid:2) 1
10
0

if 10(cid:4) 6 e 6 50(cid:4)
if 5(cid:4) 6 e 6 10(cid:4)
if 50(cid:4) 6 e 6 60(cid:4)
otherwise

ð14Þ

The scores retrieved from each mesh face are then
summed together and an average reward signal
is
obtained dividing by the number of faces nfaces, as
reported in Eq. 15.

reavg

¼

P

re
nfaces

ð15Þ

(cid:3) map percentage score: to better reconstruct the target
geometry and shape, a reward on the current level of
the map is necessary. The overall map is fragmented
into a number N p of quality photos for each face con-
stituting the mesh, where quality is to be intended
with respect to the incidence angle e between the cam-
era and the face. At each time step, the map percent-
age can be computed counting the number of quality
pictures (re – 0) available for each face N q up to that
moment and dividing this quantity by N p times the
number of mesh faces nfaces, as in Eq. 16. At each time
step, the algorithm checks which faces of the mesh are

In Eq. 17, note how the agent is rewarded for improving
the map level and it is also given a big bonus for com-
pleting the map reconstruction. The condition in which
the agent has successfully reconstructed the total target
shape is intentionally not deﬁned as a stopping condi-
tion. In this way the agent is rewarded more if it rapidly
completes the map. In general an episode will end only if
the spacecraft escapes the bounded region of space
deﬁned or if the deﬁned simulation time runs out.

After all the reward signals are described, the total
reward received by the agent at each time step is simply
the sum of the three components:
R ¼ rd þ reavg

þ rm

ð18Þ

As anticipated, the following result analysis is diﬀerentiated
into two sections: the ﬁrst describes the process adopted to
train a continuous action space agent to perform the map
reconstruction of VESPA. The second, instead, compares
the already trained discrete (derived from Brandonisio
and Lavagna (2021)) and continuous action space agent,
testing them on the robustness with respect to the state
space uncertainty.

6. Training

In order to perform the training of the DRL agent, the
major algorithm characteristics and some important vari-
ables relative to the problem at hand are critically com-
mented in the following paragraphs.

Initial conditions. Generalization is a key property in this
work because the goal is to obtain an agent that can con-
sistently perform well, whatever the initial conditions of
the state variables are. For this reason, at the start of each
episodic simulation run,
they are randomly generated
inside a certain range, reported in Table 2. The relative ini-

Table 2
Initial condition ranges for all the input state variables.

Variable

d
a
d
v
hi
_hi

5747

Range
2Dmin < d < 0:5Dmax
0(cid:4) < a < 360(cid:4)
(cid:2)90(cid:4) < d < 90(cid:4)
0 m=s
0(cid:4)
(cid:2)0:001rad=s < _h1 < 0:001rad=s

A. Brandonisio et al.

Advances in Space Research 73 (2024) 5741–5755

tial position is formulated with spherical coordinates,
where a and d represent the azimuth and the elevation
angle respectively. The other variables instead have already
been introduced.

Neural Networks design. A simple Multi-Layer Percep-
tron (MLP) neural network is employed for both the actor
and the critic. The size and depth of the network for both
characters are reported in Table 3; they have been deﬁned
from literature review (Gaudet et al. (2020a)), and previous
trade-oﬀ analysis carried out in Brandonisio et al. (2021).
The learning rate and the hidden layers speciﬁcations,
instead, come from a simple grid search analysis (Yang
and Shami, 2020).

Scenario parameters. Some more general parameters (re-
lated to the scenario formulation) that aﬀects the perfor-
mance level obtained are here discussed.

(cid:3) The cameras ﬁeld of view is selected in accordance with
typical values for VIS and TIR cameras: FOV¼ 10(cid:4);
(cid:3) The control timestep determines how frequently the

thruster is ﬁred: Dt ¼ 1s;

(cid:3) The picture timestep, Dtp, represents the time interval
between two subsequent images: Dtp ¼ 10s. This feature
is important because neither a memory or camera state
is inserted in the overall state vector, and therefore it
is needed to limit the smearing eﬀect due to a too short
time elapsing between two subsequent pictures.

(cid:3) The number of quality pictures for each face of the mesh
is set at N p ¼ 20. Recall that in Section 2.2, the mini-
mum number of images requirement was set to 3, so
N p is designed with a large enough margin to have a
more robust method.

Starting from these parameters, the agent is trained for
30000 episodes on an objective function that rewards the
decision-making policy when it
improves the covered
map of the uncooperative target VESPA, and remains in
the safe region of space. The results of this training process
are presented in Fig. 3, Fig. 4.

Few remarks can be highlighted from the plots:

(cid:3) the learning process can be considered successful, as the
curve of the score is stable, and, for the most part,
increases with the number of episodes;

Fig. 3. Average score proﬁle during model training.

Fig. 4. Average map percentage proﬁle during model training.

(cid:3) the trend of the two proﬁles (score and map) is quite
similar and they both grows over time. This can be
thought as a check on the reward function formulation:
the agent improves the average score when it concur-
rently reaches higher level of map reconstruction, mean-
ing that the agent is learning correctly;

(cid:3) at the very beginning of the training, the autonomous
guidance agent seems to behave randomly,
is
because it still needs to learn the most convenient map-
ping between state and action. As highlighted in Capra
et al. (2023), the average map percentage settles down
around 50% with a random acting agent. Therefore this
value can be considered as a benchmark to evaluate the
eﬀectiveness of the agent training;

that

(cid:3) the average map level achieved at the end of the training

Table 3
Actor & Critic Network characteristics.

Layer

Input
1st hidden layer
2nd hidden layer
Output
Learning rate
Activation function

Actor
Neurons

12
256
256
3
10(cid:2)5
Tanh

step is around 95%.

An example of trajectory obtained with the trained
agent and completing 100% of the target object map is
reported in Fig. 5.

The model is tested on 5000 episodes to retrieve some
interesting statistical data on its performance, summarized
in Table 4.

Critic
Neurons

12
256
256
1
5 (cid:7) 10(cid:2)5
Tanh

5748

A. Brandonisio et al.

Advances in Space Research 73 (2024) 5741–5755

a priori and, as such, a deeper analysis is required to verify
the algorithm in higher ﬁdelity
the applicability of
scenarios.

Here the autonomous guidance performance is evalu-
ated in presence of noise, which, as just said, can be a result
of both errors in the sensors measurement and in the math-
ematical formulation of the problem, that is not able to
represent all
its characteristics. Noise is added at each
time-step between the estimated value coming from naviga-
tion and the guidance block. In regard to the problem at
hand, noise is assumed to aﬀect the state input vector in
terms of chaser-target relative position and velocity, as well
of the attitude angles describing the relative target rotation.
As speciﬁed in the previous chapters, the incoming state
vector is considered resulting from an image-based naviga-
tion system. Therefore, much attention has been paid in
order to properly deﬁne the type of errors aﬀecting the nav-
igation outputs. Indeed, most of the time, image-based
navigation systems are not aﬀected by deterministic errors,
but by stochastic errors. For this reason, concerning the
relative position and velocity, a uniformly random error
constrained in predeﬁned ranges is taken into account. Dif-
ferently happen, for the angular position error, where a
Gaussian noise is applied to the input state, as motivated
in Piazza et al. (2022). In Eq. 19 and Eq. 20, the position
and velocity error ranges are deﬁned. These are typical val-
ues for VIS image-based navigation tool, as the one pro-
posed in Silvestrini et al. (2020). In Eq. 21 the standard
deviation considered to describe the angular error is
deﬁned, and it is valid for all the three directions.
(cid:6)m
½
epos ¼ (cid:2)10; þ10
evel ¼ (cid:2)0:1; þ0:1
(cid:6)m=s
½
ra ¼ 2(cid:4)

ð19Þ
ð20Þ
ð21Þ

7.1.1. Discrete agent

In this sub-section the results of the sensitivity analysis
are generated starting from a discrete action space agent,
as the one deﬁned in Brandonisio and Lavagna (2021).
The motivation that drives the comparison between the dis-
crete and continuous agent on this particular analysis, as
will be later shown, is twofold: indeed, both the control
and model robustness performances can be compared.
The following results are focused on a target object shaped
as a simple rectangular, exactly as the one deﬁned in
Brandonisio et al. (2021), and shown in Fig. 17.

The ﬁrst analysis consisted in comparing the perfor-
mance level (in terms of mapping level) of the trained agent
with nominal input state and with noisy input state, testing
it for 5000 episodes. In Fig. 6, the mapping level of the
trained agent with noisy input in terms of relative position
is shown. The histogram shows that the overall agent per-
formance lowers down, but not dramatically, how, instead,
it happens when the navigation errors are applied also to
the relative velocity and attitude position, as shown in
Fig. 7 and Fig. 8 respectively. In Fig. 9, the result derived

Fig. 5. Example ﬂy-around trajectory.

Table 4
Principal model statistics.

n%
(cid:8) 60%

t100% s½ (cid:6)
1595

mprop kg½
(cid:6)
4:56 (cid:7) 10(cid:2)5

These indicators can be interpreted as follows:

(cid:3) n% is the percentage of episodes in which the agent

reconstructs the entire 100% of the map;

(cid:3) t100% is the average time it takes the agent to complete

the map;

(cid:3) mprop is the average propellant mass consumed by the
chaser spacecraft, computed with the Tsiolkovsky’s
rocket equation.

7. Testing

An extensive testing campaign is carried out to assess
the model performance, its robustness to non-nominal con-
ditions, and its sensitivity to some of the parameters previ-
ously selected. Particular emphasis is given to the noise
aﬀecting on board sensors, which in turn causes issues in
the perfect reconstruction of the pose. In the following sec-
tions a detailed analysis of the performance of two diﬀerent
models of the agent is described, together with possible
improvements in the design.

7.1. Navigation uncertainty

A faulty assumption employed during both training and
testing the proposed guidance algorithm is the correct esti-
mation of the relative pose with the target at each time
step. In reality, these estimation is, in most cases, the out-
put of an estimation ﬁlter, which takes as input the model
of the dynamics and the sensor measurements, that are
inherently aﬀected by noise and imperfections. This means
that the assumption of perfectly known state is not satisﬁed

5749

A. Brandonisio et al.

Advances in Space Research 73 (2024) 5741–5755

Fig. 6. Map level comparison between trained discrete agent with nominal
input and with noisy chaser-target position input (rectangular object).

Fig. 9. Map level comparison between trained discrete agent with nominal
input and with overall noisy input (rectangular object).

by testing the trained agent with all the noisy input state
traces the trend of the worst error due to angular position
uncertainty. As it is, the agent is completely useless for a
real image-based navigation system.

To overcome this problem, the agent is re-trained again,
but this time the erratic input information becomes part of
the training simulation. The results can be appreciated in
Fig. 10, where the training architecture model is conﬁrmed
robust
to environment changes. Despite the problem
becoming more complex, the training properties remained
unchanged due to the higher and uncertain information
regarding the state space.

To better understand the robustness properties of this
discrete agent model, this analysis has been performed also
for a diﬀerent target object shape, namely the VESPA deb-
ris. In this way a direct line between the discrete and con-
tinuous action space agents is created.

Fig. 7. Map level comparison between trained discrete agent with nominal
input and with noisy chaser-target velocity input (rectangular object).

Fig. 8. Map level comparison between trained discrete agent with nominal
input and with noisy chaser-target angular position input (rectangular
object).

Fig. 10. Map level comparison between discrete agent with nominal input
and re-trained agent with overall noisy input (rectangular object).

5750

A. Brandonisio et al.

Advances in Space Research 73 (2024) 5741–5755

Fig. 11. Map level comparison between discrete agent with nominal input
and and with overall noisy input (VESPA object).

Fig. 13. Average map percentage obtained adding noise to the relative
position and velocity, and angles measurements to continuous agent.

Similarly to before, in Fig. 11 the comparison between
the trained agent (this time on VESPA) fed by nominal
and noisy inputs is shown. It is notable that, with this
object, the performance really drops down, underlining
how the eﬃciency of agent model is diﬀerent in terms of
objects or state errors sensitivity. Indeed, even if the trained
agent performs better around VESPA than with the rectan-
gular object, it is greatly more sensitive to noisy input. As
observable in Fig. 12, the agent has been re-trained exactly
as the one for the rectangular object, but in this case, the
performance recovery is poorer. This demonstrates that
at least for a discrete space agent the coupling between
object and state uncertainty can not be ignored. A possible
solution to this problem is brieﬂy proposed in the Future
developments section.

7.1.2. Continuous agent

In this sub-section, the state uncertainty sensitivity anal-
ysis for a continuous space agent is presented. Referencing
the results obtained after the training shown in Section 6,
the 95% average map level achieved by the agent is com-
pared to the level reached when the input is aﬀected by
noise. In this case, the performance drops fairly, settling
down at about 69% of average map level, as reported in

Fig. 14. Map level comparison between continuous agent with nominal
input and with overall noisy input (VESPA object).

Table 5
Map percentage comparison applying diﬀerently navigation uncertainty.

Noisy state

Position + Velocity + Angles
Position
Velocity
Angles

5751

Map level
69:22%
84:07%
87:58%
81:71%

Fig. 12. Map level comparison between discrete agent with nominal input
and re-trained agent with overall noisy input (VESPA object).

A. Brandonisio et al.

Advances in Space Research 73 (2024) 5741–5755

Fig. 13. Analogously, in Fig. 14, the results are shown com-
paring the episodic map level in histogram.

The same test is performed applying distinctively the
three uncertainties, ﬁrst on the relative position, then on
the velocity, and ﬁnally on the target attitude angles.
Table 5 summarizes the results of all tests.

The results show how the model performance is depre-
cated, speciﬁcally in the case in which all three measure-
ments are noisy. In particular, errors in the estimation of
the target Euler angles seem to be the ones aﬀecting the
most the average map level, similarly to what happened
for the discrete agent. This could be linked to the way
the algorithm tries to reconstruct the shape of the target:
indeed it needs to know very well how it is oriented to
maneuver towards the faces that it still has to see. The same
workﬂow used in the discrete case is followed also for this
analysis, re-training the agent
to investigate whether
accounting for these errors during the training step leads
to beneﬁts in the overall autonomous guidance perfor-
mance. As such, at each step of every episodic simulation,
noise errors are added to the state with the characteristics
previously deﬁned in Eq. 19, Eq. 20 and Eq. 21. The result
of the new training is reported in Fig. 15 and compared
with the nominal input in Fig. 16.

Some key takeaways from the obtained result are here

described:

(cid:3) when the training starts, the average map level is around
50%, so practically the same as in the previous training
in Fig. 4. Again, at the beginning, the agent selects its
action in a random way;

(cid:3) the proﬁle of the average map percentage is similar to
the one in the previous training, suggesting that, over
the episodes,
is
repeated;

the learning pattern of an agent

(cid:3) the number of training episodes is increased to account
for the additional complexity introduced by the presence

Fig. 16. Map level comparison between continuous agent with nominal
input and re-trained agent with overall noisy input (VESPA object).

Table 6
Map percentage comparison between nominal and retrained model with
state uncertainty.

Nominal training
69:22%

Retraining
(cid:8) 85%

of errors in the state. So, for this case, 40000 episodes
have been simulated during the training;

(cid:3) the average map level achieved at the end of the training
step is around 85%. As expected, the performance level
is lower with respect to the nominal case, but it is of
great interest the fact that it outperformed the nominal
model by about 16% in map percentage. The compar-
ison is explicitly reported in Table 6.

Therefore,

in general,

it seems that the continuous
action space agent is less sensitive to state input uncertainty
or at least more prone to re-training on a diﬀerent environ-
ment to improve its behavior. This is also conﬁrmed by the

Fig. 15. Average map percentage proﬁle during model retraining the
continuous agent with noisy state.

Fig. 17. Triangular mesh of parallelepiped object.

5752

A. Brandonisio et al.

Advances in Space Research 73 (2024) 5741–5755

come, considering the performance level is still quite high.
However, note that the largest drop occurs in correspon-
dence of a failure event along the x-axis. This is not a casu-
alty, since by propagating the free dynamics from random
initial conditions, one discovers that the x-direction is the
most sensitive one.

8. Conclusion

In conclusion, the presented work deals with an adap-
tive guidance algorithm to autonomously reconstruct the
geometry and shape of the selected uncooperative artiﬁcial
object in space. The ﬂy-around and mapping problem has
been mathematically formulated as a Partially Observable
Markov Decision Process and framed as an autonomous
exploration active SLAM task. Relative dynamics and vis-
ibility models dictate the outcome of the simulations,
describing how the chaser moves around the target and
which surfaces are visible from the cameras, under the
assumption that they are always pointing towards the tar-
get. A vision-based architecture is assumed, employing
images both in the visible and infrared band, and process-
ing them to obtain the object map via stereophotoclinom-
etry. This step generates the essential
inputs for the
following guidance block, that have been implemented with
a state-of-the-art Deep Reinforcement Learning algorithm
to design the decision-making policy of the spacecraft
agent. Proximal Policy Optimization in continuous action
space is implemented, advancing from the previous related
works, which exploited a discrete action space. Therefore,
the agent can select any value for the action, under the
form of a thrust vector, which can ideally point in any
direction. The training of the PPO agent is performed, fol-
lowed by an extensive testing campaign to assess the model
robustness and sensitivity. A planning policy is obtained,
capable of reconstructing on average 95% of the map,
starting from random initial conditions. The testing cam-
paign is then carried out, speciﬁcally analyzing the case
of uncertainty in the state and how it aﬀects the perfor-
mance of the algorithm. A retraining procedure is pro-
posed as a possible solution to improve the capabilities of
the autonomous guidance agent in terms of average target
mapping.

8.1. Future development

Several

improvements can be made to the proposed
method, and in this section, some interesting future devel-
opments are discussed. As outlined before, it is important
to deﬁne a stable model capable of facing the state uncer-
tainty problem. Here the retraining procedure is proposed
as ﬁrst step of the analysis, but it is assumed that improving
the deep reinforcement learning model, introducing model-
based network, may be very beneﬁcial to this kind of issue.
Future studies will be carried on in this direction. More-
over, one of the main drawback of the agent, in its current
form, is its inability to consider the chaser attitude, assum-

Fig. 18. Average map level with a rectangular object.

object sensitivity analysis where a simple test is performed
changing the target object and checking how the agent
responds, to evaluate its adaptability. The new target is a
plain parallelepiped, as in the previous discrete case test,
depicted in Fig. 17.

Indeed, the results are quite promising, reaching nearly
90% of average map level, as in Fig. 18. These results con-
ﬁrm the feasibility of having a continuous action space,
representing a strong advancement with respect to previous
works. Indeed, the advancement should not be focused on
the achievement of an higher performance level, but
instead, on the achievement of at least the same perfor-
mance level of a problem that is much more simple, as
the discrete action space’s one, while retaining higher ﬁde-
lity with respect to control thrusting authority.

7.1.3. Failure event

To conclude the testing phase on the agent performance,
a further interesting case has been studied, focused on the
robustness of the model with respect to a failure event.
The test is structured as follows: at a random time step
at the beginning of an episode, one of the 3D thrust vector
components becomes suddenly unavailable and it is set to
zero. For the sake of the simulation, a random time step
in the range 0 (cid:2) 100s is selected, and from there on the
spacecraft is no more able to provide an action in every
possible direction. Testing is performed on all directions
simultaneously and on each axis, to see if one of them
may be more sensitive than the others. The results are
reported in Table 7.

On average the agent seems to lose (cid:8) 7% in mapping
percentage, which can be considered a satisfactory out-

Table 7
Map percentage comparison considering a failure event in each directions.

All directions
88:46%

X
86:01%

Y
89:37%

Z
88:63%

5753

A. Brandonisio et al.

Advances in Space Research 73 (2024) 5741–5755

ing that it is always pointing toward the target. A model of
the chaser attitude dynamics would bring much closer to
reality the discussed method, making sure that the map
level during a single episode increases only when the chaser
is correctly pointing toward the target, and is able to take
pictures of only the faces that are inside the ﬁeld of view of
the cameras. From the RL side, this development could be
managed in diﬀerent ways, as for example:

(cid:3) implementing the attitude dynamics and controlling it
concurrently with the orbital dynamics, so that the same
agent outputs the action vector containing both attitude
and orbital controls;

(cid:3) implementing the attitude dynamics and developing a
multi-agent reinforcement learning methodology. In this
case, one agent would be responsible for the orbital
motion and the other for the attitude, meaning that both
of them have to learn how to cooperate to reach the end
goal of mapping the target object.

Moreover, this research is directed towards the coupling
of AI-based navigation tool, which exploits simulated
images as input to retrieve the pose, together with the here
presented AI-based guidance and trajectory (eventually
also attitude) control policy.

Declaration of Competing Interest

The authors declare that they have no known competing
ﬁnancial interests or personal relationships that could have
appeared to inﬂuence the work reported in this paper.

Acknowledgments

In the person of Andrea Brandonisio, this publication
resulted from research grant supported by Fondazione Fra-
telli Confalonieri, Milano.

References

Andriotis, C., Papakonstantinou, K., 2019. Managing engineering systems
with large state and action spaces through deep reinforcement
learning. Reliab. Eng. Syst. Saf. 191. https://doi.org/10.1016/j.
ress.2019.04.036 106483.

Brandonisio, A., Lavagna, M., 2021. Sensitivity analysis of adaptive
guidance via deep reinforcement learning for uncooperative space
objects imaging. In: 2021 AAS/AIAA Astrodynamics Specialist
Conference, Big Sky, Montana, USA, pp. 1–20.

Brandonisio, A., Lavagna, M., Guzzetti, D., 2021. Reinforcement learning
for uncooperative space objects smart imaging path-planning. J.
Astronaut. Sci. 68 (4), 1145–1169. https://doi.org/10.1007/s40295-021-
00288-7.

Capra, L., Brandonisio, A., Lavagna, M., 2023. Network architecture and
action space analysis for deep reinforcement learning towards space-
craft autonomous guidance. Adv. Space Res. 71 (9), 3787–3802.
https://doi.org/10.1016/j.asr.2022.11.048.

Chan, D.M., Agha-mohammadi, A.-A., 2019. Autonomous imaging and
mapping of small bodies using deep reinforcement learning. In: 2019
IEEE Aerospace Conference, Big Sky, Montana, USA, pp. 1–12,
https://doi.org/10.1109/AERO.2019.8742147.

5754

Civardi, G.L., Bechini, M., Quirino, M., et al., 2024. Generation of fused
visible and thermal-infrared images for uncooperative spacecraft
proximity navigation. Adv. Space Res. 73 (11), 5501–5520. https://
doi.org/10.1016/j.asr.2023.03.022.

Durrant-Whyte, H., Bailey, T., 2006. Simultaneous localization and
mapping: part i. IEEE Robot. Automat. Mag. 13 (2), 99–110. https://
doi.org/10.1109/MRA.2006.1638022.

Federici, L., Benedikter, B., Zavoli, A., 2021. Deep learning techniques for
autonomous spacecraft guidance during proximity operations. J.
Spacecraft Rock. 58 (6), 1774–1785. https://doi.org/10.2514/1.A35076.
Gaskell, R.W., 2001. Automated landmark identiﬁcation for spacecraft

navigation. Adv. Astronaut. Sci. 109, 1749–1756.

Gaudet, B., Linares, R., Furfaro, R., 2020a. Deep reinforcement learning
for six degree-of-freedom planetary landing. Adv. Space Res. 65 (7),
1723–1741. https://doi.org/10.1016/j.asr.2019.12.030.

Gaudet, B., Linares, R., Furfaro, R., 2020b. Terminal adaptive guidance
via reinforcement meta-learning: Applications to autonomous asteroid
close-proximity operations. Acta Astronaut. 171, 1–13. https://doi.
org/10.1016/j.actaastro.2020.02.036.

Inalhan, G., Tillerson, M., How, J., 2002. Relative dynamics and control
of spacecraft formations in eccentric orbits. J. Guidance Control Dyn.
25 (1), 48–59. https://doi.org/10.2514/2.4874.

Joshua P., D., John P., M., Jay P., P., 2019. On-orbit servircing:
Inspection, repair, refuel, upgrade, and assembly of satellites in space.
Aerospace
https://aerospace.org/sites/de-
fault/ﬁles/2019-05/Davis-Mayberry-Penn_OOS_04242019.pdf.

Corporation, URL:

Martı´nez, J., Rafalskyi, D., Aanesland, A., 2019. Development and testing
of the npt30-i2 iodine ion thruster. https://doi.org/10.6084/m9.ﬁg-
share.11931363.

Mnih, V., Badia, A.P., Mirza, M. et al., 2016. Asynchronous methods for
deep reinforcement learning. CoRR, abs/1602.01783. URL: http://
arxiv.org/abs/1602.01783.

Pesce, V., Agha-mohammadi, A.-A., Lavagna, M., 2018. Autonomous
navigation and mapping of small bodies. In: 2018 IEEE Aerospace
Conference, Big Sky, Montana, USA, pp. 1–10, https://doi.org/10.
1109/AERO.2018.8396797.

Piazza, M., Maestrini, M., Di Lizia, P., 2022. Monocular relative pose
estimation pipeline for uncooperative resident space objects. J.
Aerospace Informat. Syst. 19 (9), 613–632. https://doi.org/10.2514/1.
I011064.

Piccinin, M., Lunghi, P., Lavagna, M., 2022. Deep reinforcement
learning-based policy for autonomous imaging planning of small
celestial bodies mapping. Aerosp. Sci. Technol. 120. https://doi.org/
10.1016/j.ast.2021.107224 107224.

Placed, J.A., Strader, J., Carrillo, H. et al., 2023. A survey on active
simultaneous localization and mapping: State of the art and new
frontiers. arXiv:2207.00254.

Schulman, J., Levine, S., Abbeel, P. et al., 2015. Trust region policy
optimization. In: Bach, F., Blei, D. (Eds.), Proceedings of the 32nd
International Conference on Machine Learning, Lille, France:
PMLR vol. 37 of Proceedings of Machine Learning Research,
pp. 1889–1897. URL: https://proceedings.mlr.press/v37/schulman15.
html.

Schulman, J., Wolski, F., Dhariwal, P. et al., 2017. Proximal policy

optimization algorithms. arXiv:1707.06347.

Scorsoglio, A., Furfaro, R., Linares, R., et al., 2023. Relative motion
guidance for near-rectilinear lunar orbits with path constraints via
actor-critic reinforcement learning. Adv. Space Res. 71 (1), 316–335.
https://doi.org/10.1016/j.asr.2022.08.002.

Silvestrini, S., Cassinis, L.P., Hinz, R., et al., 2023. Chapter ﬁfteen -
modern spacecraft gnc. In: Pesce, V., Colagrossi, A., Silvestrini, S.
(Eds.), Modern Spacecraft Guidance, Navigation, and Control.
Elsevier, pp.
819–981. https://doi.org/10.1016/B978-0-323-90916-
7.00015-9.

Silvestrini, S., Lavagna, M., 2021a. Neural-aided gnc reconﬁguration
algorithm for distributed space system: development and pil test. Adv.
https://doi.org/10.1016/j.
1490–1505.
Space Res.
asr.2020.12.014.

(5),

67

A. Brandonisio et al.

Advances in Space Research 73 (2024) 5741–5755

S., Lavagna, M.,
safe autonomous
for

predictive
Silvestrini,
relative maneuvers. J.
control
Guidance Control Dyn. 44, 2303–2310. https://doi.org/10.2514/
1.G005481.

2021b. Neural-based
spacecraft

Silvestrini, S., Piccinin, M., Zanotti, G., et al., 2022a. Optical navigation
for lunar landing based on convolutional neural network crater
123. https://doi.org/10.1016/j.
detector. Aerosp. Sci. Technol.
ast.2022.107503 107503.

Silvestrini, S., Piccinin, M., Zanotti, G., et al., 2022b. Implicit extended
kalman ﬁlter for optical terrain relative navigation using delayed
measurements.
https://doi.org/10.3390/
9
aerospace9090503.

Aerospace

(9).

Silvestrini, S., Prinetto, J., Zanotti, G. et al., 2020. Design of robust
passively safe relative trajectories for uncooperative debris imaging in
preparation to removal. In: 2020 AAS/AIAA Astrodynamics Special-
ist Conference. Lake Tahoe, California, USA.

Sutton, R.S., Barto, A.G., 2018. Reinforcement Learning: An Introduc-

tion, 2nd ed. MIT Press, Cambridge, Massachusetts, USA.

Xie, S., Zhang, Z., Yu, H., et al., 2023. Recurrent prediction model for
partially observable mdps. Inf. Sci. 620, 125–141. https://doi.org/
10.1016/j.ins.2022.11.065.

Yang, L., Shami, A., 2020. On hyperparameter optimization of machine
learning algorithms: Theory and practice. Neurocomputing 415, 295–
316. https://doi.org/10.1016/j.neucom.2020.07.061.

5755

