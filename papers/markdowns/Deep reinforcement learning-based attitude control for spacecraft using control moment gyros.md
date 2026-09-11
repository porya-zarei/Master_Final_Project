Available online at www.sciencedirect.com
ScienceDirect

Advances in Space Research 75 (2025) 1129–1144

www.elsevier.com/locate/asr

Deep reinforcement learning-based attitude control for spacecraft
using control moment gyros

Snyoll Oghim a, Junwoo Park a, Hyochoong Bang a,⇑, Henzeh Leeghim b

a Korea Advanced Institute of Science and Technology, Yuseong-gu, Daejeon 34141, Republic of Korea
b Chosun University, Dong-gu, Gwangju 61452, Republic of Korea

Received 11 March 2024; received in revised form 16 June 2024; accepted 29 July 2024
Available online 7 August 2024

Abstract

This paper addresses the development of an attitude control system that steers control moment gyros (CMGs) based on deep rein-
forcement learning (DRL) for agile spacecraft. The proposed DRL-based attitude control system learns CMG steering strategies to
achieve the desired attitude, thus potentially bypassing the singularity issues inherent in the CMG cluster. In particular, it is designed
in two-phases to apply the DRL technique eﬃciently. In the ﬁrst phase, the attitude control is performed based on DRL up to a certain
tolerance, after which it switches to conventional control and steering law for stabilization in the second phase. The rapid pointing capa-
bility of the proposed DRL-based attitude control system is demonstrated for an agile spacecraft equipped with pyramid-type single gim-
bal control moment gyros. Additionally, in realistic scenarios of pointing multiple targets on the ground, the momentum vector recovery
that the CMG system needs to consider is also brieﬂy discussed.
(cid:1) 2024 COSPAR. Published by Elsevier B.V. All rights are reserved, including those for text and data mining, AI training, and similar
technologies.

Keywords: Spacecraft; Attitude control; Control moment gyros; Reinforcement learning

1. Introduction

Attitude control is necessary for spacecraft operations,
especially when large-angle slew or fast maneuvers are
required; the implementation plays an important role con-
sidering future space missions using spacecraft such as mil-
itary surveillance and reconnaissance or deep space
explorations. Over the decades, many researchers have
studied spacecraft attitude control, and various controllers
considering diﬀerent types of actuators have been devel-
oped Wang and Shtessel (1998), Yeh (2010), Petersen
et al. (2017), Bunryo et al. (2021).

⇑ Corresponding author.

E-mail addresses: s.oghim@kaist.ac.kr (S. Oghim), junwoopark@kaist.
ac.kr (J. Park), hcbang@kaist.ac.kr (H. Bang), h.leeghim@controla.re.kr
(H. Leeghim).

Changing the orientation of spacecraft can be classiﬁed
into passive and active methods. Passive methods utilize air
drag, earth gravity, or earth’s magnetic ﬁeld, so the torque
generated is small, and thus is often used in micro-satellites
Sutherland et al. (2018). The active methods perform atti-
tude control by generating torque from thrusters, magnetic
torquers, and reaction devices. These internal reaction
devices include reaction wheels (RWs) or control moment
gyros (CMGs) for reorientation maneuvers.

A Single-Gimbal Control Moment Gyro (SGCMG)
serves as a momentum exchange mechanism in spacecraft
and is employed for attitude control. This system generates
gyroscopic torque by rotating a ﬂywheel mounted within a
gimbal. SGCMGs,
typically in four clusters, provide
redundancy and enable comprehensive 3-axis attitude con-
trol of the spacecraft. Nonetheless, SGCMGs have chal-
lenges due to geometric singularities, in which generating

https://doi.org/10.1016/j.asr.2024.07.078
0273-1177/(cid:1) 2024 COSPAR. Published by Elsevier B.V. All rights are reserved, including those for text and data mining, AI training, and similar
technologies.

S. Oghim et al.

Advances in Space Research 75 (2025) 1129–1144

torque in speciﬁc directions becomes unfeasible. Such sin-
gularity issues arise when the momentum vectors of the
SGCMGs align within the same plane or converge along
a singular line. The singularity problem associated with
the CMG system becomes a signiﬁcant limitation on the
maneuverability of agile spacecraft Leeghim et al. (2018).
Over the past decades, many strategies have been explored
to avoid/escape the singularity problem, aiming to enhance
spacecraft attitude control systems’ operational eﬃciency
and reliability.

The most basic steering law is the pseudo-inverse (PI)
steering law, which provides a minimal two-norm solution
but does not explicitly avoid singularity Davis (1972). A
typical approach to avoid singularities is to add null
motion using gradient vectors to the pseudo-inverse solu-
tion Cornick (1979). These methods work well for certain
SGCMGs but are also considered insuﬃcient
for
pyramid-type SGCMGs.

In addition to the null motion approaches, various
forms of singularity-robust (SR) inverse steering laws have
been employed. These methods attempt to escape singular-
ities by allowing a torque error Bedrossian et al. (1990),
Wie et al. (2000), Wie et al. (2001). Although the SR
method is relatively straightforward, only a speciﬁc class
of singularity can be remedied; it is robust to a particular
situation, yet not universal. For instance, an oﬀ-diagonal
singularity robustness steering law is proposed to handle
a speciﬁc class of saturation singularity by introducing a
time-dependent modulation function into the gimbal rate
construction Wie (2005).

singularity

To improve

avoidance/escape

further,
another study proposed a global singularity avoidance
steering law that employs a switching control strategy to
avoid all types of singularities Paradiso (1992). However,
this method requires high computational cost and is unsuit-
able for real-time applications. In order to relieve the com-
putational burden, research has been conducted to attempt
to geometrically avoid singularities introducing a surface
cost function Takada et al. (2010). In addition, various
other steering methods are being studied, such as steering
law that considers the subsequent step Leeghim et al.
(2009), steering law using artiﬁcial potential functions
Seo et al. (2019), and steering law that applies game theory
Lee et al. (2005), Hua et al. (2023). Research has also been
conducted using Rapidly-exploring Random Tree (RRT),
a representative algorithm used for path planning Mony
and Paranjape (2022).

Recently, studies on ways to utilize machine learning
technique have been attracting attention. Research has
been conducted on adaptive control using basic neural net-
works Leeghim and Kim (2015), and there is research using
machine learning techniques such as deep neural network
and random forest classiﬁer to predict for trajectory to pre-
dict the required null motion Papakonstantinou et al.
(2022). Although it is not a system consisting of several
CMG, in another case, an adaptive radial bias function
neural network is utilized to control the underactuated

1130

CMG Montoya-Cha´irez et al. (2021). Aside from this,
much research is in progress to utilize machine learning
in CMG systems, but most of the research focuses on fault
diagnosis Zhao et al. (2022), Yuandong et al. (2022), Zhang
et al. (2023), and in particular, cases of utilizing reinforce-
ment learning are still insuﬃcient.

In this paper, we apply deep reinforcement learning
(DRL) techniques for attitude control of agile spacecraft.
These techniques are utilized to learn the steering strategy
of SGCMGs for achieving the desired attitude. By directly
steering the SGCMGs without relying on their mathemati-
cal models, we present the potential to circumvent the sin-
gularity problem associated with the CMG system
eﬀectively. However, executing the entire spacecraft maneu-
ver solely with DRL techniques is ineﬃcient. This ineﬃ-
ciency becomes more pronounced during the attitude
stabilization phase, where the goal is to achieve the desired
attitude and maintain the spacecraft’s angular rates at zero.
Consequently, the DRL-based attitude control system pro-
posed in this paper is divided into two phases. In the ﬁrst
phase, DRL techniques are employed for large-angle
maneuvers. The system transitions to the second phase once
the attitude error is reduced to within a speciﬁc tolerance. In
this phase, conventional control and steering law are
applied to achieve precise attitude control and stabilization.
The anticipated advantages of this study are as follows.
First, it enables the full utilization of the CMG system’s
performance without the singularity problem, oﬀering a
novel perspective that can surmount the limitations of
existing steering laws. Second, it can be deployed without
additional training, even in the presence of model uncer-
tainties, disturbances, noise, or changes in the CMG sys-
tem’s
superior
versatility of the proposed approach compared to existing
machine learning-based steering laws with speciﬁc applica-
tion ranges. Third, since reinforcement learning learns
through interaction with the environment, the need to cre-
ate a separate training dataset is obviated. This not only
saves time and eﬀort in securing training data but also
enhances the practicality and eﬃciency of our approach.

conﬁguration. This underscores

the

The primary objective of this paper is to present the
validity and advantages of applying DRL techniques to
the attitude control system of agile spacecraft equipped
with SGCMGs. To achieve this, we ﬁrst provide a concise
overview of the spacecraft attitude control problem along-
side an introduction to DRL techniques. Subsequently, we
formulate the problem within the context of the DRL
framework. Lastly, we investigate our proposed attitude
control system through detailed simulation results, demon-
strating its eﬀectiveness in agile spacecraft.

2. Attitude control using SGCMGs

This paper addresses the spacecraft attitude control
problem using SGCMGs. This section brieﬂy introduces
the fundamental principles for spacecraft attitude dynamics

S. Oghim et al.

Advances in Space Research 75 (2025) 1129–1144

and kinematics. First, the spacecraft attitude is expressed
using the quaternion kinematic diﬀerential equations.
_q ¼ 1
2

q (cid:2) X

ð1Þ

i.e.,
where the unit quaternion convention is utilized,
(cid:3)
(cid:1)
T ; (cid:2) is used to represent quaternion multiplica-
q ¼ qw
; qT
v
T are the angular
(cid:3)T , and x ¼ xx; xy; xz
tion, X ¼ 0; xT
velocity vectors of the spacecraft. Moreover, qw and qT
v
denote the scalar and vector components of the quater-
nions, respectively.

(cid:1)

(cid:3)

½

If the desired quaternions are given qd, one can obtain
the attitude error quaternions with the conjugate of the
desired quaternions q(cid:4)

(cid:1)
¼ qwe

qe

(cid:3)

; qT
ve

T ¼ q(cid:4)

d

d as follows,
(cid:2) q

ð2Þ

Then, the attitude error quaternions can be deﬁned such
that
_qe ¼ 1
2

(cid:2) X

ð3Þ

qe

Next, consider Euler’s rotational equations of motion for a
rigid spacecraft described by
_H sc þ x (cid:5) H sc ¼ sext
where H sc is the total angular momentum vector of the
spacecraft, and sext is the external torque. The total angular
momentum of the system consists of the angular momen-
tum of the spacecraft main body and the angular momen-
tum contributed by SGCMGs.
H sc ¼ J x þ H cmg

ð4Þ

ð5Þ

where J is the moment of inertia matrix of the spacecraft,
and H cmg is the angular momentum vector of SGCMGs.
Substituting Eq. 5 into Eq. 4 gives,
(cid:4)
J _x þ _H cmg þ x (cid:5) J x þ H cmg
¼ sext

ð6Þ

(cid:5)

The control torque generated by the SGCMGs is deﬁned as
s ¼ (cid:6) _H cmg (cid:6) x (cid:5) H cmg
ð7Þ
Then substitution of Eq. 6 into Eq. 5 yields
J _x þ x (cid:5) J x ¼ s

ð8Þ

where the external torque is assumed to be zero.

exhibit

slightly diﬀerent

Depending on how SGCMGs are arranged, SGCMG
clusters
characteristics. The
SGCMG cluster considered in this paper is a pyramid-
type cluster, as shown in Fig. 1, with an almost uniform
momentum magnitude in all directions. The total angular
momentum of SGCMGs, each of which is installed having
a skew-angle b and angular momentum h such that

2

H cmg ¼ h

6
4

(cid:6) cos b sin d1 (cid:6) cos d2 þ cos b sin d3 þ cos d4
cos d1 (cid:6) cos b sin d2 (cid:6) cos d3 þ cos b sin d4
sin b sin d1 þ sin b sin d2 þ sin b sin d3 þ sin b sin d4

3

7
5

ð9Þ

1131

Then, the time derivative of H cmg leads to
_H cmg ¼ A dð Þ _d
where d ¼ d1; d2; d3; d4
½
corresponding Jacobian matrix is given by,

2

A dð Þ ¼ h

6
4

(cid:6) cos b cos d1
(cid:6) sin d1
sin b cos d1

sin d2
(cid:6) cos b cos d2
sin b cos d2

cos b cos d3
sin d3
sin b cos d3

(cid:3)T is the gimbal angle vector and the

ð10Þ

3

7
5

(cid:6) sin d4
cos b cos d4
sin b cos d4

ð11Þ

If the desired torque sd is given, the gimbal rates required
can be calculated as follows.
(cid:4)
_d ¼ AT AAT

(cid:5)(cid:6)1sd

ð12Þ

This equation is called the pseudo-inverse steering law.
However, the existence of the pseudo-inverse of the Jaco-
bian cannot be guaranteed since the elements of the Jaco-
bian matrix vary with the gimbal angle. If the angular
momentum vectors of the SGCMGs lie in the same plane,
the Jacobian matrix is not full rank, and the desired gimbal
rates cannot be obtained. This is known as the mathemat-
ical singularity of SGCMGs, which has been addressed in
the introduction. The singularity problem has already been
investigated in many previous studies Wie (2004), Yoon
and Tsiotras (2004), Liang and Xu (2005). In this paper,
we propose a new approach to avoid this singularity issue
using the RL technique.

3. Reinforcement learning

Deep reinforcement learning focuses on making a series
of optimal decisions to maximize the expected reward.
Especially for a given Markov decision process (MDP),
the DRL approach is a mathematical framework that can
infer the optimal choice of actions, even under a stochastic
environment Franc¸ois-Lavet et al. (2018).

In an MDP, an agent interacts with an environment
over all discrete time steps. At each time step t, the agent
observes the current state, st, and takes an action to take,
at. The environment then transitions to a new state, stþ1,
and the agent receives a reward, rt, based on the transition
and the action taken.
ð13Þ
ð
rt ¼ R st; at; stþ1
where R denotes a reward function. This cyclic process is
repeated until one of the user-deﬁned termination or trun-
cation conditions is met, such as exceeding the maximum
number of steps. One cycle is called an episode. The agent’s
goal
is to maximize the cumulative reward over whole
steps, also known as the return.

Þ

Rt ¼

XT

ci(cid:6)tri

i¼t

ð14Þ

where T is the step at the end of an episode, and c 2 0; 1ð
(cid:3) is
a discount factor, which denotes an attenuation of the
reward based on how far oﬀ it can be obtained in the

S. Oghim et al.

Advances in Space Research 75 (2025) 1129–1144

Fig. 1. Pyramid-type of four single-gimbal CMGs.

future. In other words, the objective in DRL is to ﬁnd a
policy, p, that maximizes the expected return when the
agent acts based on it. Therefore, DRL can be seen as an
optimization problem expressed as follows:
J pð Þ ¼ Ep Rt
p(cid:4) ¼ arg max

(cid:3)
J pð Þ

ð15Þ
ð16Þ

½

p

where p(cid:4) means the optimal policy.

½

DRL algorithms for MDP employ a value function to
make a decision. The value functions are generally catego-
rized into two branches: a state-value function and an
action-value function. The state-value function is used to
estimate the expected return of being in a particular state
while following a given policy. The action-value function,
the Q-function, estimates the expected return of taking a
particular action in a given state and following a given pol-
icy. Each is deﬁned as follows:
ð17Þ
(cid:3)
V p stð Þ ¼ Ep Rtjst
Qp st; at
ð18Þ
½
Þ ¼ Ep Rtjst; at
ð
Accurately calculating a value function in DRL is a chal-
lenging task. Therefore, it is a common practice to estimate
the value function. The value function approximation is
typically carried out via sampling data through interactions
between the agent and the environment. To estimate the
value function, we commonly use the Bellman equations
Sutton and Barto (2018). Bellman equations present the
relationship between the current and subsequent state-
value function(or action-value function). The current value
function can be updated through the Bellman equations
with the sampled data. The Bellman equations for the value
functions are described as follows:

(cid:3)

ð
V p stð Þ ¼ Ep rt þ cV p stþ1
½
½
Þ ¼ Ep rt þ cEp Qp stþ1; atþ1
ð
Qp st; at

(cid:3)
ð

Þ

½

(cid:3)
Þ

(cid:3)

ð19Þ
ð20Þ

This method can be employed with model-based and
model-free algorithms, the two broad categories of DRL
algorithms. Model-based algorithms assume some prior
knowledge of the environment and its behavior, whereas
model-free algorithms learn through trial-and-error inter-
actions with the environment. This paper uses a model-
free DRL approach because the mathematical model of
the SGCMGs cluster has a singularity problem.

The model-free approach consists of two principles for
updating the policy: Policy optimization and Q-leaning.
Q-learning is used to learn the optimal action-value func-
tion for a given environment. This algorithm estimates
the expected Q-value in Eq. 20 and updates it using the
Bellman equations. Many diﬀerent algorithms, such as
Deep Q-Network Mnih et al. (2013), update the policy in
an oﬀ-policy way, and most of them are known to be
sample-eﬃcient.

On the other hand, policy optimization is a technique
used to learn a policy function that maps states to actions.
Unlike Q-learning, which estimates the optimal action-
value function, policy optimization directly learns the pol-
icy that maximizes the expected reward. There are various
algorithms for policy optimization, such as Trust Region
Policy Optimization(TRPO) Schulman et al. (2015) and
Proximal Policy Optimization(PPO) Schulman et al.
(2017). Those algorithms are subject to lower sample eﬃ-
ciency due to using an on-policy way to update the policy.
Yet, they are easy to implement and exhibit a stable learn-
ing curve.

1132

S. Oghim et al.

Advances in Space Research 75 (2025) 1129–1144

Adding the entropy term to Eq. 15, one can deﬁne the new
objective function as Ziebart (2010),
#

"

XT

JðpÞ ¼ Ep

ctðrt þ aHðpð(cid:7)jstÞÞÞ

ð22Þ

t¼0

where a > 0 is a temperature parameter that controls the
trade-oﬀ between expected reward and entropy, and
Hðpð(cid:7)jstÞÞ is the entropy of the policy.

As shown in Algorithm 1, SAC involves ﬁve neural net-
work models: one actor network, two critic networks, and
two target critic networks. The actor network generates
actions based on the policy, while the critic networks esti-
mate the state-action values, representing the expected
rewards for a given state and action. The critic networks
are trained using the error loss between the estimated
state-action values and the actual rewards the agent
receives.

One key feature of SAC incorporates a replay buﬀer,
which stores transitions from the environment for later
training. Using data from the replay buﬀer, SAC can learn
from a broader range of experiences,
leading to more
robust policies. The replay buﬀer also allows for decou-
pling the agent’s exploration from the learning process,
improving training stability.

Overall, SAC is a practical algorithm for learning poli-
cies in continuous action spaces. Its use of a stochastic pol-
icy and replay buﬀer makes it particularly useful for
exploration and robustness. Additionally, its oﬀ-policy nat-
ure and use of two critic networks help to prevent overes-
timation and accelerate training.

Algorithm 1. Soft Actor-Critic

Lastly, some algorithms are a compromise between Q-
learning and policy optimization, taking the strengths
and weaknesses of both techniques. These include Deep
Deterministic Policy Gradient(DDPG) Lillicrap et al.
(2015), Twin Delayed Deep Deterministic Policy Gradi-
ent(TD3) Fujimoto et al. (2018), and Soft Actor-Critic
(SAC) algorithms Haarnoja et al. (2018).

3.1. Soft actor-critic

There are two main challenges to consider when apply-
ing the DRL technique to the attitude control problem
using SGCMGs. First, since the desired attitude is achieved
through gimbal rates, the action, at, and observation, st,
should be deﬁned in continuous
space. Second, as
described in the previous section, the mathematical model
of SGCMGs has a singularity problem. Therefore, infer-
ring from the sampling data without explicitly considering
the model is necessary, which requires high sample eﬃ-
ciency. To tackle these challenges, this paper employs the
soft actor-critic(SAC) algorithm.

SAC is a model-free approach that is used for continu-
ous control tasks. It is based on the maximum entropy
DRL framework, which aims to maximize both the
expected reward and the entropy of the policy. In the
SAC algorithm, entropy denotes a quantity that measures
the randomness of the policy. Increasing entropy implies
more exploration that can be interpreted as preventing
the policy from converging to bad local optimum
Haarnoja et al. (2018). The entropy of a random variable
x with the probability distribution function P is deﬁned as
H Pð Þ ¼ EP (cid:6) log P xð Þ
ð21Þ
(cid:3)
½

1133

S. Oghim et al.

Advances in Space Research 75 (2025) 1129–1144

4. Deep reinforcement learning-based attitude control

This section introduces the approach to addressing the
attitude control problem of spacecraft equipped with
SGCMGs within the DRL framework, utilizing the SAC
algorithm. The problem formulation involves deﬁning a
suitable MDP and an appropriate reward function. The
environment in which the agent interacts is characterized
by the rotational equations of motion and quaternion kine-
matics presented in the previous section. Within this envi-
ronment,
the observations available to the agent are
deﬁned as follows:
ð
; x; d
st ¼ qe
Here, the reason for using the attitude error quaternions is
for the consistency of the goals the agent should achieve.
No matter the desired attitude, the state the agent must
(cid:3)T . Attitude error quaternions
reach is always qe
are also helpful in the design of reward functions.

¼ 1; 0; 0; 0

ð23Þ

Þ

½

To achieve the desired attitude of a spacecraft equipped
with SGCMGs, it is necessary to control the gimbal rates
of the SGCMGs to generate the gyroscopic torque. Con-
steering laws utilize the pseudo-inverse of
ventional
SGCMGs, as shown in Eq. 12, to determine the gimbal
rates according to the desired torque derived from the con-
trol law. However, the availability of a pseudo-inverse is
not always guaranteed. Therefore, we propose using
DRL techniques to derive gimbal rates directly from sam-
pled data without calculating the pseudo-inverse. For this
purpose, we deﬁne the agent’s actions as gimbal rates _d,
and the action space is also deﬁned using the maximum
gimbal rates _dmax.

Designing an appropriate reward function is crucial for
formulating a complete MDP for the attitude control prob-
lem, considering the environment, states, and actions. The
reward function forms the foundation of agent training
and signiﬁcantly inﬂuences the policy that dictates the prin-
ciples of action within the DRL framework. It is consid-
ered one of the most critical components in the DRL
framework. Nonetheless, there are no deﬁnitive guidelines
for designing reward functions. The design of the reward
function varies depending on the problem being addressed
and often requires a considerable amount of trial and error.
The reward function proposed in this paper is designed
with three key factors. The ﬁrst is the spacecraft’s agility to
achieve the desired attitude, for which we directly utilized
attitude error as a criterion. The second involves minimiz-
ing the spacecraft’s angular rates once it has achieved the
desired attitude, directly utilizing the spacecraft’s angular
rates to accomplish this. The third and ﬁnal element
ensures that the gimbal angle returns to its initial setting
when the desired attitude is successfully achieved. This con-
sideration is crucial for operational aspects of the CMG
system, especially in real scenarios pointing to multiple tar-
gets. Additionally, there is a potential beneﬁt in mitigating
the risk of falling into singularity issues with SGCMGs

when switching to conventional control and steering for
precise attitude control and stabilization.
rt ¼ r1 þ r2

ð24Þ

Each term is deﬁned such that
(cid:6)k1 log jxj
0;

r1 ¼ (cid:6)kq jqve

r2 ¼

jj;

(cid:6)

ð

j

jj þ jderr
j

jj

Þ þ k2;

if

jj 6 bq

j

jqve
otherwise

where kq; k1, and k2 are positive constants to shape the
reward function.

In Eq. 24, the ﬁrst terms represent the attitude error
quaternions. The second term is related to the angular rates
and the gimbal angles error, derr ¼ d0 (cid:6) dt, where d0 is the
initial gimbal angles of the SGCMGs and dt is its the gim-
bal angles at time step t. Using the logarithm reﬂects a
more signiﬁcant reward as the angular rates and the angle
error decreases. This reward term is only applied when the
spacecraft’s attitude error satisﬁes a speciﬁc tolerance, bq,
which is also the parameter for switching to the second
phase of the proposed DRL-based attitude control system.
In other words, decreasing bq enhances the accuracy of
control but increases the learning time.

The coeﬃcients used in the reward function are summa-
rized in Table 1. k1 and k2 are set to ensure that, upon
achieving the goal, accumulated negative reward value over
the episode is converted into positive value, making it clear
to the agent that the goal has been achieved. bq is set to
0.04, a value determined through Monte-Carlo simulations
to be the level at which the conventional control law and
steering law used in the second phase of the proposed atti-
tude control system can avoid singularity issues.

The process of the agent interacting with the environ-
ment and progressing through an episode can be summa-
rized as follows: At each step, the agent takes an action
deﬁned by the gimbal speed of SGCMGs, as derived from
its policy. The environment calculates the spacecraft’s state
for the next step based on the torque generated from the
agent’s action. The agent repeats this process until the epi-
sode termination or truncation conditions are met. The
entire process is illustrated in Fig. 2.

4.1. Training scenarios

This section introduces the considerations for training
scenario. We assumes that the spacecraft performs a rest-
to-rest (R2R) maneuver. This means that the spacecraft’s
angular momentum must be zero both before starting
and after achieving the desired attitude control. Training
begins with initializing the agent and the environment, dur-
ing which a desired attitude is randomly selected, and the

Table 1
Hyperparameters used to train the agent.

kq

1.0

1134

k1

100

k2

500

bq

0.04

S. Oghim et al.

Advances in Space Research 75 (2025) 1129–1144

Fig. 2. A representation of the DRL single-step process for the CMG system-based attitude control problem.

attitude error quaternion is calculated based on this selec-
tion. The spacecraft’s angular rates is initialized to zero,
and the initial gimbal angles of the SGCMGs are set to a
user-selected conﬁguration that ensures the total angular
momentum of the SGCMGs is zero.

We also consider a maximum time of 30 s for a maneu-
ver and a time step of 0.1 s. Therefore, the maximum num-
ber of steps per episode is 300. This maximum step serves
as the truncation condition for an episode; if the agent
achieves or fails to achieve the set tolerance within 300
steps, the episode terminates. When an episode ends, the
state and reward information constituting that episode
are stored in the replay buﬀer. The episodes stored in the
replay buﬀer are used to update the agent’s policy. By
repeating this process, the agent learns how to steer the
SGCMGs to achieve the desired attitude for the spacecraft.
The detailed conﬁgurations of
spacecraft and
SGCMGs used in training are summarized in Table 2, with
initial gimbal angles referenced from literature Kuhns and
Rodriguez (1995).

the

There is a concern when using DRL for spacecraft atti-
tude control, especially when trying to maintain a target
attitude by reducing the spacecraft’s angular rates to zero.
The issue arises when the agent opts for abrupt maneuvers
instead of halting to maintain the attitude. Although this
problem can be mitigated by incorporating an energy-

Table 2
Speciﬁcation of Spacecraft equipped with SGCMGs used to train the
agent Wie et al. (2002).

Parameter

Moment of inertia, J
Initial quaternions, q
Initial angular rates, x
Skew-angle, b
Angular momentum of ﬂywheel, h
Initial gimbal angle, d0
Maximum gimbal rate, _dmax,

(cid:3)T

Value
diag 21400; 20100; 5500
Þ
ð
1; 0; 0; 0
½
(cid:3)T
½
0; 0; 0
53.13
1000
½
45; (cid:6)45; 45; (cid:6)45
1.0

(cid:3)T

Unit
kg(cid:7)m2
-
deg/s
deg
Nm
deg
rad/s

1135

minimizing term into the reward function,
it adversely
aﬀects the spacecraft’s maneuverability and extends the
training duration.

The proposed DRL-based attitude control system dis-
tinguishes precision attitude control and stabilization
phases from an overall attitude control scheme to solve
that consideration and eﬃciently utilize the DRL tech-
nique. The ﬁrst phase involves controlling the attitude for
large-angle maneuvers through DRL. Once the attitude
error has reached a speciﬁc tolerance, the system transi-
tions to the second phase, where conventional attitude con-
trol and steering law are employed for precise attitude
control and stabilization.

The conventional attitude control law used in the second

phase is referenced in Wie et al. (2001).
þ 1
T

(cid:6)
sc ¼ (cid:6)J 2ksat
Li

þ cx

qe

qe

(cid:9)

(cid:7)

(cid:8)

Z

ð25Þ

The variable limiter and the saturation function is deﬁned
as
(cid:10) (cid:11)
Li ¼ c
2k

ﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃﬃ
(cid:13)
(cid:13)
(cid:13)
(cid:13)
(cid:13)
(cid:13)
4ai qe;i

; xi
j

j
max

r

(cid:6)

(cid:9)

min
8
><

eð Þ ¼

sat
L

>:

L if
e
if
(cid:6)L if

e P L
ej j < L
e 6 (cid:6)L

where k and c are controller gain to be properly
determined.

The spacecraft must maintain consistent maneuverabil-
ity throughout the entire mission duration. Since the gim-
bal angle positions of the CMG system are closely related
to the spacecraft’s rotational maneuverability, to keep the
spacecraft’s maneuverability consistent, the gimbal angles
of the CMG system must always be the same at the start
and end of every maneuver. In the ﬁrst phase of the pro-
posed attitude control system, the reward function is
designed to ensure that the gimbal angles of the SGCMGs

S. Oghim et al.

Advances in Space Research 75 (2025) 1129–1144

Fig. 3. Conceptual ﬂowchart of the DRL-based Attitude Control System.

Fig. 4. Training curves on attitude control for spacecraft using CMGs.

return to their initial angles when the phase ends. Consid-
ering this aspect, the second phase also employs a momen-
tum recovery steering law Leeghim et al. (2020).
_d ¼ Aþsc þ g AþA (cid:6) I 4(cid:5)4
ð
(cid:5)(cid:6)1
Aþ ¼ AT AAT

ð26Þ

Þg

(cid:4)

where g is a positive constant and the gradient vector
g ¼ d (cid:6) d0
Þ=Dt forces the gimbal angles to approach the
ð
initial gimbal angles d0. Note that the second term of Eq.
26 is related to the null motion, which does not generate
the torque. The conceptual ﬂowchart of the DRL-based
attitude control system is presented in Fig. 3.

Fig. 4 displays the training curves resulting from train-
ing with diﬀerent deep reinforcement learning algorithms
(SAC, TD3, PPO) according to the previously described
training scenario. The solid lines represent the moving
average return, and shaded regions represent the standard
deviation with the moving window set to 1000.

1136

As the training curves show, SAC and TD3 converge to
high return values, indicating successful learning. In con-
trast, PPO’s convergence to signiﬁcantly lower return val-
ues suggests a poorer learning performance for this task.
This is likely due to PPO’s lower sample eﬃciency and
more conservative exploration than the other two algo-
rithms. Therefore, using PPO might require appropriate
hyperparameter tuning.

SAC and TD3 stabilize at return values of about 700.
Despite SAC exhibiting slight ﬂuctuation in returns due
to its unique exploration–exploitation trade-oﬀ, it rises fas-
ter than TD3 and converges to similar return values. This
suggests that SAC has better sample eﬃciency and can
eﬀectively learn the attitude control policy. Given the nat-
ure of this study, which aims to achieve a desired attitude
by steering four SGCMGs, high sample eﬃciency, and
exploration performance are crucial, making SAC the most
suitable algorithm.

S. Oghim et al.

Advances in Space Research 75 (2025) 1129–1144

Fig. 5. Time history of the attitude error quaternions for the single-axis attitude control problem.

Fig. 6. Time history of the angular rates for the single-axis attitude control problem.

5. Simulation results

This section explores the eﬀectiveness of the DRL-based
attitude control system through simulation results. The
simulations consider three cases: single-axis attitude con-

trol, three-axis attitude control, and multi-target tracking
scenario. The proposed approach is compared and ana-
lyzed against the conventional approach composed of the
quaternion-error feedback control law in Eq. 25 with the
variable limiter and the generalized singularity robustness

1137

S. Oghim et al.

Advances in Space Research 75 (2025) 1129–1144

Fig. 7. Time history of the gimbal rates for the single-axis attitude control problem.

Fig. 8. Time history of the singularity measures for the single-axis attitude control problem.

inverse (GSRI) steering law. Note that the control law used
in the conventional approach is identical to the one used in
the proposed approach’s second phase. In the subsequent
simulation results, PR indicates the proposed DRL-based
attitude control system, and CNV indicates the conven-
tional approach used for comparison.

The GSRI steering law, used with the control law in Eq.
25, is widely employed as a simple yet eﬀective method for
passing through and escaping internal singularities Wie
et al. (2002), Bailey et al. (2000). The proposed steering
law is mainly intended for general maneuvers except point-
ing or tracking, fully utilizing the available momentum

1138

S. Oghim et al.

Advances in Space Research 75 (2025) 1129–1144

training the agent with the DRL-based attitude control sys-
tem, as listed in Table 2. For the control law of both the
conventional and proposed approaches, the maximum con-
trol acceleration a was chosen as U =J , and the control tor-
que command has a saturation limit of 3000Nm, with the
maximum slew rate, xmax , assumed to be 30 degrees.
Assuming xn ¼ 3rad=s; f ¼ 0:9, and T ¼ 10s, the controller
þ 2fxn=T and
gains can be determined as follows: k ¼ x2
n
c ¼ 2fxn þ 1=T .

Fig. 5 and 6 show the simulation results of

two
approaches for a yaw attitude command of 70 degrees.
Both approaches achieve the desired attitude when examin-
ing the attitude error quaternions and angular rates results.
However, looking at the gimbal rates results, Fig. 7, when
using the conventional approach, it can be seen that chat-
tering starts to occur in 4 s. This phenomenon appears
when the CMG system falls into a singularity, and it is
essential to note that gimbal rates cannot be calculated
when operating an actual CMG system in such a condition.
To explore whether the CMG system has fallen into a sin-
gularity, the singularity measures, m ¼ detðAAT Þ, is used
(when the CMG system is in a singularity, m becomes 0).
The graph for the singularity measures also approaches a
value of 0 around 4 s, indicating that the CMG system
has fallen into a singularity. In contrast, the DRL-based
attitude control system achieves the desired attitude with-
out the chattering of gimbal rates associated with singular-
ities. These results imply that the proposed approach
potentially circumvents the singularity problem in the
CMG system. (see Fig. 8).

5.2. Three-axis attitude control

This section extends the single-axis attitude control
problem to a three-axis attitude control problem, describ-
ing a typical spacecraft operation. The attitude commands
are arbitrarily selected as ½50; (cid:6)83; 29(cid:3) degrees, assuming
large-angle maneuvers.

The time histories of attitude angles and angular rates
for both the conventional and proposed approaches are
displayed in Fig. 9 and 10. Both approaches achieve the
desired attitude in a similar amount of time. In Fig. 11,
however, the conventional approach produces extreme
chattering around 2 and 7 s, with the singularity measures
approaching zero in Fig. 12. The DRL-based attitude con-
trol system produces no chattering at the gimbal rates
despite the singularity measures approaching zero around
5 and 10 s.

Fig. 9. The time histories of attitude angles for the three-axis atittutide
control problem.

Fig. 10. The time histories of angular rates for the three-axis atittutide
control problem.

space of the CMG system even though singularities are pre-
sent. The GSRI steering law is as follows.
(cid:1)
_d ¼ AT AAT þ kE
(cid:1)
k ¼ 0:01 exp (cid:6)10 det AAT

(cid:3)(cid:6)1sc

ð27Þ

(cid:4)

(cid:5)

(cid:3)

2

6
4

E ¼

3

7
5

1
e3
e2

e3
1
e1

e2
e1
1

where the oﬀ-diagonal elements (cid:2)i ¼ 0:01 sin 0:5pt þ /i
with /2

¼ p=2, and /3

¼ p.

ð

Þ

5.3. Multi-target attitude control

5.1. Single-Axis Attitude Control

The ﬁrst simulation considers a single-axis attitude con-
trol problem for a rigid spacecraft. The parameters of the
spacecraft are assumed to be the same as those used in

1139

This section presents a simulation study for multi-target
attitude control, suitable for realistic missions. Each atti-
tude command is generated every 30 s resulting in 8 atti-
tude reorientations. Table 3 summarizes the randomly
selected attitudes for this simulation.

S. Oghim et al.

Advances in Space Research 75 (2025) 1129–1144

Fig. 11. The time histories of gimbal rates for the three-axis atittutide control problem.

Table 3
Desired Euler angles for multi-target scenario.

Target Number

1
2
3
4
5
6
7
8

Desired Attitude [yaw, pitch, roll]
½14; (cid:6)1; (cid:6)11(cid:3) (deg)
½(cid:6)67; (cid:6)50; 5(cid:3) (deg)
½3; 57; 73(cid:3) (deg)
½(cid:6)4; (cid:6)52; (cid:6)18(cid:3) (deg)
½40; 5; (cid:6)85(cid:3) (deg)
½(cid:6)84; (cid:6)45; (cid:6)39(cid:3) (deg)
½25; 42; 12(cid:3) (deg)
½(cid:6)51; 61; (cid:6)61(cid:3) (deg)

tialized gimbal angles after successive attitude control.
These results have important implications for the CMG
system, as the initial position of the gimbal aﬀects its per-
formance. Fig. 16 and 17 also show that similar to the
results for the three-axis attitude control problem, the tra-
ditional method results in extreme chattering due to the
singularity problem.

5.4. Robustness analysis

The ﬁnal aspect to examine is the robustness of the pro-
posed approach. The DRL-based attitude control system
deﬁnes the agent’s state using attitude error, angular veloc-
ity, and gimbal angles. This means attitude control can be
performed without relearning, even if the model parame-
ters change. To demonstrate this, we use diﬀerent model
parameters from those used in the training and consider
the external disturbances. We also added white Gaussian
in the angular
noise to assume measurement errors
momentum, angular velocity, and gimbal angles of the

Fig. 12. The time histories of singularity measures for the three-axis
atittutide control problem.

Figs. 13 and 14 show the time histories of the attitude
angles for the multi-target scenario. The DRL-based atti-
tude control system (PR) and the conventional approach
(CNV) perform well for the eight attitude commands.
Fig. 15 shows the time history of the gimbal angles of the
CMG system steered by each approach. Since the proposed
approach includes momentum recovery driving, we can see
that after achieving each command, the CMG system’s
gimbal angles return to the initial set angles. On the other
hand, the conventional approach does not include this con-
sideration, resulting in a signiﬁcant deviation from the ini-

1140

S. Oghim et al.

Advances in Space Research 75 (2025) 1129–1144

Fig. 13. The time histories of the attitude angles for multi-target scenario.

Fig. 16. The time histories of the gimbal angles for multi-target scenario.

Fig. 14. The time histories of the angular rates for the multi-target
scenario.

Fig. 17. The time histories of the singularity measures for the multi-target
scenario.

the

SGCMGs. Furthermore,
the
SGCMGs cluster is changed from a pyramid-type to a
roof-type for the simulations. Table 4 summarizes the
changed model parameters and noise, and the external dis-
turbance is chosen as

conﬁguration

of

2

sext ¼

6
4

3

ð

Þ
5 sin 0:01t þ 0:25p
Þ
(cid:6)5 sin 0:01t þ 0:5p
Þ
10 sin 0:01t þ 0:7p

ð

ð

7
5

ð28Þ

Fig. 15. The time histories of the gimbal angles for the multi-target
scenario.

Aroof ¼

6
4

1141

The Jacobian matrix of the roof-type SGCMG cluster is as
follows:
2

sin d1

sin d2

(cid:6) cos br cos d1 (cid:6) cos br cos d2
sin br cos d2
sin br cos d1

(cid:6) sin d3
cos br cos d3
sin br cos d3

(cid:6) sin d4
cos br cos d4
sin br cos d4

3

7
5

ð29Þ

S. Oghim et al.

Advances in Space Research 75 (2025) 1129–1144

Table 4
Changed model parameters and noise levels to demonstrate the robustness
of the proposed approach.

Parameter

Moment of inertia, J
Angular momentum of SGCMG, H cmg
Std. of angular momentum, rh
Std. of angular velocity noise, rx
Std. of gimbal angle noise, rd

Value
Unit
diagð22470; 21105; 5250Þ kg(cid:7)m2
800
1.0
0.005
0.01

N(cid:7)m
N(cid:7)m
rad/s
rad

where br denotes the skew-angle of the roof-type conﬁgura-
tion and is set to 45 degree.

The simulation results, presented in Fig. 18–21, high-
the adaptability and versatility of our proposed
light
approach. The blue dashed line represents the results with-
out disturbances and noise, and the orange solid line repre-

Fig. 20. Time histories of gimbal angles for pyramid types and scenario
taking into account model uncertainties, external disturbance, and noise.

Fig. 18. Time histories of Euler angles for pyramid types and scenario
taking into account model uncertainties, external disturbance, and noise.

Fig. 19. Time histories of angular rates for pyramid types and scenario
taking into account model uncertainties, external disturbance, and noise.

1142

Fig. 21. Time histories of gimbal rates for pyramid types and scenario
taking into account model uncertainties, external disturbance, and noise.

sents these factors considered. Although there is a slight
the proposed
delay due to disturbances and noise,
approach achieves the desired attitude. These results show
the eﬀectiveness of the proposed approach to diﬀerent
model parameters and various type conﬁgurations, demon-
strating its versatility and reassuring its potential in diverse
scenarios.

However, starting at about 23 s in Fig. 20, the gimbal
angle shows that it is slightly biased and does not recover
the initial gimbal angle. This section, which begins the sec-
ond phase of precise postural control and momentum vec-
tor recovery, uses a conventional approach. The results
mean that the second phase still requires considering uncer-
tainties, perturbations, and noise, unlike the ﬁrst phase,
which uses DRL-based attitude control.

S. Oghim et al.

6. Conclusion

The attitude control problem of a rigid spacecraft using
the CMG system is a well-known research topic. While var-
ious steering laws have been studied to address the singu-
larity problem of the CMG system, a steering law that
can fully utilize their performance while avoiding/escaping
singularities has yet to be developed. In this study, we pro-
pose a DRL-based attitude control system to overcome the
singularity problem of single-gimbal control moment gyros
(SGCMGs) and achieve the desired attitude.

We deﬁned the observation of the agent as the attitude
error quaternions, the angular rates of the spacecraft,
and the gimbal angles of the SGCMGs. The agent’s action
is deﬁned as the gimbal rates of the SGCMGs. In addition,
the reward function is designed considering the characteris-
tics of
the spacecraft attitude control problem using
SGCMGs. DRL techniques are used to solve the Markov
decision process(MDP) deﬁned in this way, and among
them, SAC algorithms specialized in control tasks are used.
Since the SGCMGs are steered based on sampling data
through the DRL techniques, they can bypass the singular-
ity problem.

However, achieving high precision in attitude control
and maintaining a steady state using only DRL techniques
takes much work. Therefore, we divide the attitude control
system into two phases. The ﬁrst phase is based on the
DRL, and the second is based on a conventional approach.
The conventional approach comprises the quaternion error
feedback control and the momentum recovery steering law.
Once the DRL technique performs the attitude control to a
certain level, the conventional approach performs precise
control.

Finally, we explored the validity of

the proposed
approach in various simulations. Simulation results have
shown that the desired attitude is achieved by steering
SGCMGs well without any singularity problem, and it is
noteworthy that attitude control is performed similarly to
the conventional approach. In practical cases, the perfor-
mance and versatility of the proposed approach are further
highlighted by the fact that the conventional approach can-
not achieve the same level of performance as the simulation
results due to issues such as model uncertainty, distur-
bances, noise, and the singularity problem of CMG
systems.

Previous studies applying machine learning techniques
have often used them as auxiliary means alongside other
methodologies. In contrast, this study demonstrated that
reinforcement
learning can directly steer actuators to
achieve attitude control in an end-to-end manner. This sug-
gests that data-driven control approaches like reinforce-
ment learning have recently gained signiﬁcant attention
and can be crucial in addressing the singularity problem.
These results can provide valuable insights for future
research in attitude control using the CMG system.

We presented a novel approach to overcome the singu-
larity problem of SGCMGs, but some limitations still need

Advances in Space Research 75 (2025) 1129–1144

to be addressed in future research. The proposed approach
deﬁnes the satellite’s attitude error, angular velocity, and
SGCMG gimbal angle as the agent’s state. Therefore, atti-
tude control can be performed well without retraining,
even if the model parameters change. However, new train-
ing is required if the state space or action space is changed,
for example, when using a triple-parallel conﬁguration or a
variable-speed CMGs cluster. The second limitation is the
inherent reliability issue of reinforcement learning. Since
control is performed through deep neural networks, theo-
retical analysis such as stability assessment, which is used
in control theory, is diﬃcult. We indirectly addressed these
issues by combining reinforcement learning with tradi-
tional control methods, and explainable AI, which is
actively researched in machine learning, can also help ana-
lyze and explain the reliability of reinforcement learning-
based controllers. However, the reliability of reinforcement
learning-based attitude controllers remains an issue that
needs to be resolved.

Declaration of Competing Interest

The authors declare that they have no known competing
ﬁnancial interests or personal relationships that could have
appeared to inﬂuence the work reported in this paper.

Acknowledgments

This work was supported by the ’Space Pioneer Pro-
gram’ grant funded by the Ministry of Science and ICT,
Republic of Korea. (2021M1A3B9094394)

References

Bailey, D.A., Heiberg, C.J., Wie, B., 2000. Continuous attitude control

that avoids cmg array singularities. US Patent 6,131,056.

Bedrossian, N.S., Paradise, J., Bergmann, E.V., et al., 1990. Steering law
design for redundant single-gimbal control moment gyroscopes. J.
Guid., Control, Dynam. 13 (6), 1083–1089.

Bunryo, Y., Satoh, S., Shoji, Y., et al., 2021. Feedback attitude control of
spacecraft using two single gimbal control moment gyros. Adv. Space
Res. 68 (7), 2713–2726.

Cornick, D., 1979. Singularity avoidance control laws for single gimbal
control moment gyros. In: Guidance and Control Conference (p.
1698).

Davis, B., 1972. A Comparison of CMG Steering Laws for High Energy
Astronomy Observatories (HEAOS). Technical Report Marhall Space
Flight Center.

Franc¸ois-Lavet, V., Henderson, P., Islam, R., et al., 2018. An introduction
to deep reinforcement learning. Found. Trends Mach. Learn. 11 (3–4),
219–354.

Fujimoto, S., Hoof, H., Meger, D., 2018. Addressing function approx-
imation error in actor-critic methods. In: International Conference on
Machine Learning. PMLR, pp. 1587–1596.

Haarnoja, T., Zhou, A., Abbeel, P., et al., 2018. Soft actor-critic: Oﬀ-
policy maximum entropy deep reinforcement learning with a stochastic
actor. In: International Conference on Machine Learning. PMLR, pp.
1861–1870.

Hua, B., Ni, R., Zheng, M., et al., 2023. Cooperative game theory-based
steering law design of a cmg system. J. Syst. Eng. Electron. 34 (1), 185–
196.

1143

S. Oghim et al.

Advances in Space Research 75 (2025) 1129–1144

Kuhns, M.D., Rodriguez, A.A., 1995. A preferred trajectory tracking
steering law for spacecraft with redundant cmgs. In: Proceedings of
1995 American Control Conference-ACC’95 (pp. 3111–3115). IEEE
volume 5.

Lee, J.-S., Bang, H.-C., Lee, H.-J., 2005. Singularity avoidance by game
theory for control moment gyros. In: AIAA Guidance, Navigation,
and Control Conference and Exhibit (p. 5946).

Leeghim, H., Bang, H.-C., Park, J.-O., 2009. Singularity avoidance of
control moment gyros by one-step ahead singularity index. Acta
Astronaut. 64, 935–945.

Leeghim, H., Jin, J., Mok, S.-H., 2018. Feasible angular momentum of
spacecraft installed with control moment gyros. Adv. Space Res. 61
(1), 466–477.

Leeghim, H., Kim, D., 2015. Adaptive neural control of spacecraft using

control moment gyros. Adv. Space Res. 55 (5), 1382–1393.

Leeghim, H., Lee, C.-Y., Jin, J.-H., et al., 2020. A singularity-free steering
law of roof array of control moment gyros for agile spacecraft
maneuver. Int. J. Control Autom. Syst. 18, 1679–1690.

Liang, T., Xu, S.-J., 2005. Geometric analysis of singularity for single-
gimbal control moment gyro systems. Chin. J. Aeronaut. 18 (4), 295–
303.

Lillicrap, T.P., Hunt, J.J., Pritzel, A. et al. (2015). Continuous control with

deep reinforcement learning. arXiv preprint arXiv:1509.02971.

Mnih, V., Kavukcuoglu, K., Silver, D. et al. (2013). Playing atari with

deep reinforcement learning. arXiv preprint arXiv:1312.5602.

Montoya-Cha´irez, J., Rossomando, F.G., Carelli, R., et al., 2021.
Adaptive rbf neural network-based control of an underactuated
control moment gyroscope. Neural Comput. Appl. 33 (12), 6805–6818.
Mony, A., Paranjape, A.A., 2022. Singularity avoidance in spacecraft with
single-gimbal cmgs using rrt-based steering laws. In: AIAA Scitech
2022 Forum (p. 0864).

Papakonstantinou, C., Daramouskas, I., Lappas, V., et al., 2022. A
machine learning approach for global steering control moment
gyroscope clusters. Aerospace 9 (3), 164.

Paradiso, J.A., 1992. Global steering of single gimballed control moment
gyroscopes using a directed search. J. Guid., Control, Dynam. 15 (5),
1236–1244.

Petersen, C.D., Leve, F., Kolmanovsky, I., 2017. Model predictive control
of an underactuated spacecraft with two reaction wheels. J. Guid.,
Control, Dynam. 40 (2), 320–332.

Schulman, J., Levine, S., Abbeel, P., et al., 2015. Trust region policy
optimization. In: International Conference on Machine Learning.
PMLR, pp. 1889–1897.

Schulman, J., Wolski, F., Dhariwal, P. et al., 2017. Proximal policy

optimization algorithms. arXiv preprint arXiv:1707.06347.

Seo, H.-H., Bang, H.-C., Cheon, Y.-J., 2019. Steering law of control
function approach. Acta

moment gyros using artiﬁcial potential
Astronaut. 157, 374–389.

Sutherland, R., Kolmanovsky, I., Girard, A.R., 2018. Attitude control of
a 2u cubesat by magnetic and air drag torques. IEEE Trans. Control
Syst. Technol. 27 (3), 1047–1059.

Sutton, R.S., Barto, A.G., 2018. Reinforcement Learning: An Introduc-

tion. MIT press.

Takada, K., Kojima, H., Matsuda, N., 2010. Control moment gyro
singularity-avoidance steering control based on singular-surface cost
function. J. Guid., Control, Dynam. 33 (5), 1442–1450.

Wang, P., & Shtessel, Y.B. (1998). Satellite attitude control using only
magnetorquers. In Proceedings of the 13th Southeastern Symposium
on System Theory (pp. 500–504).

Wie, B., 2004. Singularity analysis and visualization for single-gimbal
control moment gyro systems. J. Guid., Control, Dynam. 27 (2), 271–
282.

Wie, B., 2005. Singularity escape/avoidance steering logic for control
moment gyro systems. J. Guid., Control, Dynam. 28 (5), 948–956.
Wie, B., Bailey, D., Heiberg, C., 2001. Singularity robust steering logic for
redundant single-gimbal control moment gyros. J. Guid., Control,
Dynam. 24 (5), 865–872.

Wie, B., Bailey, D., Heiberg, C., 2002. Rapid multitarget acquisition and
pointing control of agile spacecraft. J. Guid., Control, Dynam. 25 (1),
96–104.

Wie, B., Bailey, D.A., & Heiberg, C.J.

(2000). Robust singularity

avoidance in satellite attitude control. U.S. Patent 6,039,290.

Yeh, F.-K., 2010. Sliding-mode adaptive attitude controller design for
spacecrafts with thrusters. IET Control Theory Appl. 4 (7), 1254–1264.
Yoon, H.-J., Tsiotras, P., 2004. Singularity analysis of variable speed
control moment gyros. J. Guid., Control, Dynam. 27 (3), 374–386.
Yuandong, L., Qinglei, H., Xiaodong, S., 2022. Neural network-based
fault diagnosis for spacecraft with single-gimbal control moment
gyros. Chin. J. Aeronaut. 35 (7), 261–273.

Zhang, K., Wang, S., Wang, S., et al., 2023. Anomaly detection of control
moment gyroscope based on working condition classiﬁcation and
transfer learning. Appl. Sci. 13 (7), 4259.

Zhao, H., Liu, M., Sun, Y., et al., 2022. Fault diagnosis of control
moment gyroscope based on a new cnn scheme using attention-
enhanced convolutional block. Sci. China Technol. Sci. 65 (11), 2605–
2616.

Ziebart, B.D., 2010. Modeling Purposeful Adaptive Behavior with the
Principle of Maximum Causal Entropy. Carnegie Mellon University.

1144

