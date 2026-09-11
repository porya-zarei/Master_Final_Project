Journal of the Franklin Institute 362 (2025) 107741

Contents lists available at ScienceDirect

Journal of the Franklin Institute

journal homepage: www.elsevier.com/locate/fi

Reinforcement learning based attitude fault-tolerant control of
spacecraft with unknown system model

Shaolong Yang a, Lei Jin b,*, Jiaxuan Rao b
a Shanghai Institute of Spaceflight Control Technology, Shanghai 201108, China
b Beihang University, School of Astronautics, Beijing 102206, China

A R T I C L E  I N F O

A B S T R A C T

Keywords:
Spacecraft
Reinforcement learning
Fault-tolerant control
Actuator fault

With the increasing reliability and safety requirements of spacecraft control system, it is urgent to
study effective fault-tolerant control methods to ensure that the control system can still maintain
high control performance when the actuator fails. Considering the uncertainty and suddenness of
faults, it is very important for fault-tolerant control to have strong adaptability and high real-time
performance. Therefore, a fault-tolerant attitude controller based on reinforcement learning for a
spacecraft with unknown system model is proposed in this paper. Firstly, by ignoring the effects of
inertia uncertainty, actuator faults, and external disturbances, the reinforcement learning algo-
rithm is combined with optimal control to design an offline approximate optimal control policy
for the known nominal system. Next, a neural network-based observer is designed to estimate the
system  input  matrix  and  approximate  the  unknown  system  dynamics,  eliminating  the  offline
nominal controller’s dependency on the system model and mitigating the impact of multiplicative
actuator faults on attitude control. Subsequently, the offline nominal controller is employed as the
initial control strategy, and the parameters of the critic network are updated online using the RLS
method. This approach results in an online reinforcement learning controller that enhances the
algorithm’s real-time performance. In addition, by utilizing the partial disturbances estimated by
the  neural  network-based  observer,  a  feedforward  compensation  algorithm  is  incorporated  to
counteract  the  adverse  effects  of  additive  actuator  faults  and  external  disturbance  torques  on
attitude  control  performance,  completing  the  online  fault-tolerant  control  scheme  based  on
reinforcement  learning.  Lastly,  the  stability  of  the  control  system  is  proved  by  the  Lyapunov
method, and the validity of the proposed fault-tolerant control is illustrated through simulations.

1. Introduction

Since the inception of human space exploration, numerous spacecraft failures have been documented in orbit. Notable examples
include the American navigation satellite GPS BII-7, the Japanese X-ray astronomy satellite Astro-H, and the American commercial
remote sensing satellite WorldView-4 [1]. The harsh and unique nature of the space environment poses significant challenges for
in-orbit repairs, which  are  not as  readily achievable as  repairs  to ground-based systems. To  enhance the  safety  and reliability  of
spacecraft, fault-tolerant control strategies have been developed and implemented.

The thoughts of fault-tolerant control originated from the integrity control first proposed by Niederlinski in 1971 [2], and the

* Corresponding author.

E-mail address: jinlei@buaa.edu.cn (L. Jin).

https://doi.org/10.1016/j.jfranklin.2025.107741
Received 13 September 2024; Received in revised form 11 March 2025; Accepted 8 May 2025
Available online 9 May 2025
0016-0032/© 2025 The Franklin Institute. Published by Elsevier Inc. All rights are reserved, including those for text and data mining, AI training,
and similar technologies.

S. Yang et al.

Journal of the Franklin Institute 362 (2025) 107741

concept of fault-tolerant control was officially proposed by the American IEEE Control Systems Society in 1986 [3]. A control system
with the ability to automatically adapt to component faults is called a fault-tolerant control system. According to the different ways of
handling faults, fault-tolerant control can be divided into two categories: passive fault-tolerant control and active fault-tolerant control
[4]. Passive fault-tolerant control uses the robustness of the controller to keep the system stable when preset faults occur. Jin et al. [5]
designed  a  passive  fault-tolerant  controller  using  dynamic  inversion  and  time-delay  control  theory,  thereby  achieving  spacecraft
attitude control in the presence of actuator faults. Zhang et al. [6] introduced the historical control input into the control system and
proposed a fault-tolerant control scheme for online learning, which improved the robustness of the controller. Passive fault-tolerant
control  systems  are  characterized  by  their  simple  structure  and  high  reliability.  However,  they  have  poor  adaptability  and  may
experience  a  significant  degradation  in  control  performance  when  confronted  with  unknown  and  complex  faults.  Unlike  passive
fault-tolerant control, active fault-tolerant control dynamically adapts the control strategy in real-time based on detected faults to
maintain system stability and performance. Zhou et al. [7] designed two fault observers to estimate the magnitudes of additive and
multiplicative faults, respectively, and achieved stability control of spacecraft attitude through a control law and compensation al-
gorithm. Shen et al. [8] utilized both the estimated and measured values of angular velocities for fault detection and estimation, and
combined these with an integral backstepping control method to achieve stable control of spacecraft attitude. Active fault-tolerant
control  provides  high  adaptability  and  performance  by  dynamically  adjusting  to  detected  faults,  but  it  requires  complex  moni-
toring and computational resources, increasing implementation costs and system complexity.

Compared to passive and active fault-tolerant control methods, adaptive control, which does not require precise fault information
and  offers  strong  adaptability  and  robustness,  has also  been  widely  applied in  the  field  of  fault-tolerant control.  Wang  et  al.  [9]
designed an adaptive integral terminal sliding mode fault-tolerant controller to enhance the stability of the spacecraft attitude tracking
control process. Tutsoy et al. [10] combined an adaptive robust reduced-order observer with nonlinear dynamic inversion control to
achieve fault-tolerant control of quad-rotor UAVs. Adaptive technology enhances the adaptability of fault-tolerant control but still
relies heavily on system models. To address this dependency, neural networks are employed to estimate uncertain models. Sanwale
et al. [11] and Zhou et al. [12] used neural networks to estimate the magnitude of faults and applied the adaptive sliding mode control
method  to  achieve  stability  control  of  spacecraft  attitude, which  improved  system  reliability  and  control  performance.  However,
neural networks require substantial computational resources and complex training processes, and they depend on large volumes of
high-quality data.

In recent years, advancements in computer hardware performance and the development of efficient algorithms have significantly
propelled the growth of reinforcement learning. Reinforcement learning enables agents to learn policies that maximize long-term
rewards  through  continuous  interaction  with  their  environment  [13].  Building  on  these  advancements,  reinforcement
learning-based  fault-tolerant control  has emerged  as a  promising  approach, facilitating model-free  control  through  ongoing  envi-
ronmental interaction. Li et al. [14] employed a model-free DDPG reinforcement learning algorithm to train a fault-tolerant control
method for manipulators, resulting in a controller that is highly insensitive to joint faults. Ahmed and Khorasgani [15] proposed a
hierarchical  reinforcement  learning-based  fault-tolerant  controller  which  was  verified  using  a  C-130  aircraft  fuel  tank  model.  To
enhance the adaptability of the controller, Ahmed and Qui˜nones-Grueiro [16] combined online and offline policies to propose an
adaptive reinforcement learning algorithm that allows the controller to be updated in real-time according to system changes. Zhang
and Gao [17] draw on the idea of model reference control and uses reinforcement learning algorithms to track state responses of
non-fault systems regardless of whether faults occur or not. Ren et al. [18] proposed an incremental reinforcement learning strategy for
flight control systems, gradually approximating optimal fault compensation. Zheng et al. [19] combined reinforcement learning with
sliding  mode  observers  for  spacecraft  attitude  hyperagile  tracking  control,  maintaining  high  accuracy  under  uncertainties.  Rein-
forcement learning offers high adaptability and self-learning capabilities, making it suitable for complex and uncertain environments.
However, it faces challenges including low sample efficiency, slow convergence, and difficulty in proving theoretical stability.

To address the challenge of proving theoretical stability in reinforcement learning, current research combines traditional control
theories with reinforcement learning. This integration leverages the stability-guaranteed framework of traditional control and the
adaptability of reinforcement learning to unknown faults and disturbances. The resulting hybrid architecture is particularly effective in
complex scenarios, ensuring theoretical reliability while enhancing autonomous decision-making in uncertain  environments. Hua
et al. [20] proposed a data-driven reinforcement learning control algorithm that achieves fault-tolerant control of DC motors. Li et al.
[21] proposed a data-driven reinforcement learning method to address model-free fault-tolerant control for discrete-time multi-mode
systems with actuator faults, achieving stability control while optimizing energy consumption. Wang et al. [22] proposed a rein-
forcement learning-based optimal fault-tolerant control method that achieves stable control in the presence of actuator faults and
external disturbances by leveraging system data, thereby reducing the controller’s reliance on precise models. Li et al. [23] proposed
an innovative control method for industrial processes that combines offline reinforcement learning and minimax optimization, offering
a model-free, highly fault-tolerant, and robust solution. For tracking control problems of multi-agent systems with actuator faults, Li
et al. [24] combined reinforcement learning with backstepping control to design an adaptive fault-tolerant controller with compen-
sation for the impact of faults through auxiliary signals. Zhao et al. [25] combined reinforcement learning with optimal control to
design a fault-tolerant controller for unknown quadrotors, which improved control performance. Zhang et al. [26] combined rein-
forcement learning with fuzzy control to improve the robustness of the controller and successfully applies it to pitch rate control of F-16
fighters and  robot  arm systems. Liu  et al.  [27] proposed a  fault-tolerant control  method  based on reinforcement  learning, which
achieves stable control of quadrotor UAVs under actuator faults.

In summary, current spacecraft attitude fault-tolerant control techniques still face several limitations, including insufficient in-
telligence in autonomous decision-making, limited adaptability to handle unknown faults and disturbances, and suboptimal real-time
performance during abrupt actuator faults. These shortcomings highlight the need for more intelligent, adaptive, and computationally

2

S. Yang et al.

Journal of the Franklin Institute 362 (2025) 107741

efficient real-time fault-tolerant control strategies to ensure reliable spacecraft operation in unpredictable space environments.

Therefore, this paper combines reinforcement learning with optimal control method to design an online reinforcement learning-
based fault-tolerant controller for spacecraft with unknown system model. Firstly, by ignoring the influence of inertia uncertainty,
actuator faults and disturbance torques, the nominal systems model can be assumed to be known and an offline nominal controller
based on reinforcement learning is proposed. This controller is an approximation of a nonlinear optimal controller that improves the
intelligence and autonomy of the controller. Then, a neural network-based observer is designed to estimate the real system model
parameters, in which the estimated input matrix containing the multiplicative actuator faults can be used in the offline approximate
optimal control policy. Furthermore, the online reinforcement learning-based controller is developed by using the offline nominal
controller as the initial control strategy and updating the parameters of the critic network online via the Recursive Least Squares (RLS)
algorithm. RLS can update parameters online with good real-time performance and is widely used in system identification, signal
processing, adaptive control, fault diagnosis, and fault-tolerant control, though its application in reinforcement learning is rare. The
online reinforcement learning controller, based on RLS parameter updates, effectively reduces the impact of multiplicative actuator
faults and achieves good real-time performance. Lastly, the observer-based feedforward compensation algorithm is used to eliminate
the adverse effects of actuator additive faults and external disturbances. Based on the above design steps, the online fault-tolerant
control based on reinforcement learning is achieved. In this fault-tolerant control scheme, the reinforcement learning algorithm re-
places  traditional  model-based  control  algorithms,  achieving  spacecraft  attitude  stabilization  control  without  requiring  detailed
system model information and while maintaining good real-time performance.

The main contributions compared to other existing works are stated as follows:

1) By integrating reinforcement learning with optimal control, the stability of the system is guaranteed, while the intelligence, au-

tonomy and adaptability of the controller are improved.

2)  The multiplicative faults of the actuator are treated as unknown model parameters and estimated using a neural network-based
observer. Subsequently, the impact of these multiplicative faults on the spacecraft attitude is indirectly mitigated through the
reinforcement learning algorithm.

3) The  RLS  algorithm  is  utilized  to  update  the  parameters  of  the  critic  network  in  reinforcement  learning,  offering  both  imple-
mentation convenience and enhanced real-time performance. Additionally, the RLS algorithm is initialized with the results from
the offline controller, eliminating the need for an initial data collection phase.

The remainder of the paper is scheduled as follows: Section 2 gives a problem statement where a system model is established
including spacecraft attitude kinematics based on quaternions, spacecraft attitude dynamics and actuator faults models. Section 3
combines reinforcement learning with optimal control theory to design an online fault-tolerant controller. Section 4 presents  the
simulations and comparisons. Section 5 concludes this research.

2. Problem formulation and preliminaries

2.1. Attitude kinematic and dynamic model of spacecraft

To  avoid  computational  singularity,  the  spacecraft  attitude  is  described  using  quaternions.  Therefore,  the  attitude  kinematic

equations of the spacecraft can be expressed as

⎧
⎪⎪⎪⎨
⎪⎪⎪⎩

˙qb0

= (cid:0) 1
2

b ωb
qT

˙qb

= 1
2

(̃qb + qb0I3)ωb

(1)

[

qb0 qT
b

]
T ∈ R × R3denotes the attitude orientation of the spacecraft in the body coordinate system relative to the inertial
where, Qb =
= [q1 q2 q3]T ∈ R3  is the vector component. I3  denotes third-order identity
coordinate system, qb0 ∈ R is the scalar component and qb
]
T ∈ R3  denotes the angular velocity of the spacecraft in the body coordinate system relative to the inertial
matrix. ωb =
coordinate system. Under the action of the attitude kinematic equations, the attitude Qb  is obtained by inputting the attitude angular
velocity ωb. For any 3-dimensional vector x = [x1 x2 x3]T,̃x is a cross product matrix, with

ωx ωy ωz

[

⎡

⎣

̃x =

0
x3
(cid:0) x2

(cid:0) x3
0
x1

⎤

⎦

x2
(cid:0) x1
0

Considering the space environment disturbance, the attitude dynamic equation of a rigid spacecraft is established as

Ib ˙ωb + ̃ωbIbωb = Tc + Td

(2)

where, Ib ∈ R3×3  denotes the actual rotational inertial matrix of the spacecraft, which is usually a positive definite symmetric matrix.
Tc ∈ R3  refers to the control torque acting on the spacecraft, Td ∈ R3  refers to the external disturbance torques.

3

S. Yang et al.

Journal of the Franklin Institute 362 (2025) 107741

Spacecraft will consume fuel during missions such as attitude and orbit maneuvers, which will cause changes in the rotational
inertia of the spacecraft and result in the actual and nominal rotational inertia of the spacecraft not being equal. Taking into account
the impact of uncertainty in rotational inertia, the attitude dynamic equation of a rigid spacecraft can be given by

(Ib0 + ΔIb) ˙ωb + ̃ωb(Ib0 + ΔIb)ωb = Tc + Td

(3)

where, Ib0 ∈ R3×3  denotes the nominal rotational inertial matrix of the spacecraft,  which is  usually a positive definite  symmetric
matrix. ΔIb ∈ R3×3  refers to unknown additional rotational inertia.

Rearranging Eq. (3), the attitude dynamic equation of a rigid spacecraft can be rewritten as

Ib0 ˙ωb + ̃ωbIb0ωb = Tc + Td + TΔ

(4)

where, TΔ = (cid:0) ΔIb

˙ωb (cid:0) ̃ωbΔIbωb  is unknown torque generated by uncertainty in inertia.

2.2. Attitude dynamic model of spacecraft considering actuator faults

The control torque acting on the spacecraft is generated by the actuator. Although there are many types of actuators, the math-

ematical model of actuators can be uniformly expressed as

Tc = Cu

(5)

where, C ∈ R3×nis the actuator effectiveness matrix, u = [u1 u2 ⋯ un]T refers to the control torque vector generated by the actuators, n
refers to the number of the actuators.

Considering the impact of actuator faults, the relationship between the actual control torque generated by the actuator and the

expected control torque can be expressed as

u = (In (cid:0) E)uc + uc

(6)

where, uc = [uc1 uc2 ⋯ ucn]T  refers to the expected control torque, uc = [uc1 uc2 ⋯ ucn]T  refers to the additive faults, E = diag(e1 e2 ⋯
en) is a diagonal matrix composed of actuator fault coefficients, ei represents the fault coefficient of the i th actuator, withei ∈ [0,1]. ei  =
0, means that the actuator is working well; and ei = 1, means the actuator totally loses its effectiveness; and 0 < ei < 1, implies that the
actuator partially loses its effectiveness.

The presence of both additive and multiplicative faults in the actuators causes the actual control torque to deviate from the ex-
pected control torque, thereby affecting the system’s dynamic response. Moreover, these actuator faults introduce additional model
uncertainties, which not only reduce the system’s robustness but also significantly degrade its control performance. In severe cases,
this deviation can lead to system instability.

Substituting Eq. (5) and Eq. (6) into Eq. (4), the attitude dynamic equation considering environmental disturbance, inertia un-

certainty and actuator faults can be expressed as:

Ib0 ˙ωb + ̃ωbIb0ωb = Tcf + Tf + Td + TΔ

(7)

where, Tcf = Cucrefers to the expected control torque generated by the actuators, Tf = (cid:0) CEuc + Cuc  refers to the additional control
torque generated by the actuator faults.

2.3. System state equation

By defining system state variables asx =

[

qT
b ωT
b

]
T

˙x = f(x) + Buc + δ

, based on Eqs.(1), (2), (5) and (6), system state equation is described by

(8)

where, f(x) denotes the nonlinear dynamics of the system and satisfies the Lipschitz condition, B refers to the input matrix, δ refers to
the partial disturbances, which contain additive faults, disturbance torques and a part of rotational inertia effects, with

[

f(x) =

G(qb
(cid:0) 1
b

)ωb
̃ωbIbωb

(cid:0) I

]

[

, B =

03×n
(cid:0) 1
b C(In (cid:0) E)

I

]

[

, δ =

]

03×1

(cid:0) 1
b

I

(Cuc + Td)

(9)

where, G(qb

) = 1
2

(cid:0)

(cid:0)

̃qb

+

1 (cid:0) qT

b qb

)

)
I3

If all the variables in Eq. (8) are known, the system model is known. The controller can be designed by traditional methods, such as
sliding mode control, backstepping control and optimal control. However, when the spacecraft has model uncertainty and actuator
faults, the terms Ib, E, uc, and Td  are all unknown, which also leads to uncertainty in termsf(x), B, and δ  in the system equation.
Specifically, the spacecraft’s rotational inertia uncertainty affects f(x), B, and δ, multiplicative actuator faults affects B, and additive
actuator faults and disturbance torques will affect δ.

Therefore, the goal is to design an attitude stabilization controller that is bounded stable even if f (x), B and δ of the system model

4

S. Yang et al.

Journal of the Franklin Institute 362 (2025) 107741

described by Eq. (8) are unknown.

3. Control law design

3.1. Offline nominal controller based on reinforcement learning

3.1.1. Optimal controller for nominal nonlinear systems

Ignoring model uncertainty, actuator faults and external disturbance torques, the state equation of the nominal system can be

expressed as
˙x = f 0

(x) + B0uc

(10)

where, f 0

(x) denotes the internal nonlinear dynamics of the system ignoring model uncertainty, B0  refers to the input matrix, with

[

(x) =

f 0

G(qb
(cid:0) 1
b0

)ωb
̃ωbIb0ωb

(cid:0) I

]

[

]

, B0 =

03×n
(cid:0) 1
b0 C

I

Consider control performance and control consumption, define the reward function as follows

r1(x, uc) = xTQ1x + uT

c R1uc

(11)

(12)

where, Q1  and R1  are positive-definite matrices with appropriate dimensions, representing the weights of control performance and
control input.

Based on Eq. (12), define the cost function as follows

∫ ∞

J1(t) =

r1(τ)dτ

t

(13)

Therefore, the optimal control problem can be stated as how to determine the control policy to minimize the value of the cost

functionJ1(t).

For the nonlinear nominal system described in Eq. (10), a continuous control policy is considered admissible if it results in zero

control output when the state is zero and ensures system stability while keeping the cost function as Eq. (13) bounded.

According to optimal control theory, for any admissible control policy, if the cost function as Eq. (13) is continuously differentiable,

then the Hamilton function of the above optimal control problem can be defined as

H(x, uc, ∇J1) = r1 + (∇J1)T ˙x
)
(cid:0)
= r1 + (∇J1)T
(x) + B0uc

f 0

(14)

where, ∇J1 = ∂J1 /∂x refers to the partial derivative of the cost function with respect to the state variables.

According to the Bellman optimality principle, the optimal cost function J

(cid:0)

min
uc

H

∗
x, uc, ∇J
1

)

= 0

∗
1  satisfies the Hamilton-Jacobi-Bellman (HJB) equation

(15)

Substituting Eq. (12) into Eq. (14) and solving for the partial derivative of H with respect to uc, ∂H/∂uc = 2R1uc + BT
0

∇J1  can be
obtained. Assuming that the minimum value on the left side of the above HJB equation exists and is unique, then ∂H /∂uc  = 0.
Therefore, the optimal control policy for the above optimal control problem can be obtained as

∗
u
c

= (cid:0) 1
R
2

(cid:0) 1
1 BT

0

∗
∇J
1

Substituting the optimal control policy Eq. (16) and Eq. (14) into Eq. (15), the HJB equation can be expressed as

xTQ1x +

)
T

(cid:0)

∗
∇J
1

f 0

(x) (cid:0) 1
4

)
T

(cid:0)

∗
∇J
1

B0R

(cid:0) 1
1 BT

0

∗
∇J
1

∗
= 0, J
1

(0) = 0

(16)

(17)

In order to solve the optimal control policy, it is necessary to solve ∇J

∗
1 through the HJB equation represented by Eq. (17). However,
directly solving the HJB equation is not only extremely challenging but also requires complete system model information, including
f 0

(x) and B0.
When solving the HJB equation, the values of the state variables are computed using the backward induction method. However, as
the dimension of the state variables increases, the computational complexity grows exponentially, leading to what is known as the
"curse of dimensionality." Therefore, in this paper, policy iteration algorithms are employed to solve the HJB equation.

Step 1: Initialization: Select an admissible control policyu0
Step 2: Policy evaluation: Update the estimated value of the cost function

c  as the initial iteration policy

Ji
1

(x(t)) =

∫

t+T

t

(cid:0)

r1

x(τ), ui
c

)
dτ + Ji
(τ)
1

(x(t + T)), Ji
1

(0) = 0

(18)

5

S. Yang et al.

Journal of the Franklin Institute 362 (2025) 107741

where, i is the number of iterations, T is the sampling time interval.

Step 3: Policy improvement: Update control policy
)

(cid:0)

ui+1

c

= min
uc

H

x, uc, ∇Ji
1

or

ui+1

c

= (cid:0) 1
2

(cid:0) 1
1 BT

0

R

∇Ji
1

(19)

(20)

Step 4: End judgment: If the cost function finally converges, it ends; otherwise, go back to Step 2.
The above policy iteration algorithm begins with an initial admissible policy (stable policy) and converges to the optimal control
policy through continuous iteration. The convergence proof of the algorithm can be found in [28]. It is necessary for the initial control
policy to be admissible. If the initial control policy is not admissible, the system may diverge during the control policy update process,
making algorithm convergence very difficult.

Compared to directly solving the optimal control policy through the HJB equation, the policy iteration algorithm is more feasible
and does not require knowledge of the system’s internal dynamic response. Given that the state and action spaces in the control
problem are continuous and the state space has an infinite dimension, it is challenging to evaluate the cost function for all states using
Eq. (18). Therefore, the reinforcement learning algorithm is introduced to approximate the cost functions via critic networks and to
approximate optimal control policies through policy iteration.

3.1.2. Approximate optimal controller based on reinforcement learning

Given the powerful nonlinear approximation capability of neural networks, the critic network is employed to approximate the

optimal cost function J

∗
1  as

∗
J
1

= WT

c1σc1(x) + εc1

(21)

where, x refer to  the inputs of  the critic network, Wc1  refer to  the optimal critic network parameters, σc1  refer  to the activation
functions of the critic network, εc1  is the approximation error of the critic network.

Therefore, the partial derivative of the optimal cost function with respect to the state variables can be expressed as

∗
∇J
1

= (∇σc1(x))TWc1 + ∇εc1

(22)

where, ∇σc1(x) = ∂σc1(x) /∂x and ∇εc1 = ∂εc1 /∂x are the partial derivatives of the activation functions and approximation error of the
critic network with respect to the state variables.

Using a neural network to directly obtain the co-state ∇J

∗
1i s another method to approximate the optimal control law. However, the

convergence rate is slower because the gradient is more sensitive to noise and approximation errors.

According to Eq. (22), the optimal control policy can be expressed by

∗
u
c

= (cid:0) 1
R
2

(cid:0) 1
1 BT

0

(cid:0)

(∇σc1(x))TWc1 + ∇εc1

)

(23)

The optimal critic network parameters and the approximation error of the critic network are unknown, so the estimated value of the

cost function ̂J1  can be expressed as

̂
J1 = ̂
W

T

c1σc1(x)

(24)

where,

̂
Wc1  are the estimated values of the critic network parameters Wc1.

Therefore, the partial derivative of the estimated value of the cost function with respect to the state variables can be expressed as

∇̂

J 1 = (∇σc1(x))T ̂
Wc1

(25)

Using the critic network to approximate the cost function, the policy improvement algorithm as Eq. (18) can be rewritten as

̂
W

i T

c1 σc1(x(t)) =

∫

t+T

t

(cid:0)

r1

x(τ), ui
c

)
(τ)

dτ + ̂
W

i T

c1 σc1(x(t + T))

Since there is an approximation error in the critic network, the temporal difference error is defined as follows

ei
c1

=

∫

t+T

t

(cid:0)

r1

x(τ), ui
c

)
dτ + ̂
(τ)
W

i T

c1

[σc1(x(t + T)) (cid:0) σc1(x(t))]

(26)

(27)

The ultimate goal of the critic network is to approximate the optimal cost function as closely as possible. Ideally, the temporal
difference  error  should  be  zero.  However,  due  to  approximation  errors  in  the  critic  network,  it  is  challenging  to  ensure  that  the
temporal difference error is exactly zero.

Therefore, to optimize and solve for the critic network parameters, the optimization objective can be set as the outer product of the

6

S. Yang et al.

Journal of the Franklin Institute 362 (2025) 107741

Fig. 1. Offline-based reinforcement learning-based approximate optimal controller.

temporal difference errors as follows

1
c1 ei
ei T
2

c1

min
ˆW

i
c1

(28)

Since the temporal difference error ei

c1 is a scalar, a set of data can only construct one equation through Eq. (27). However, in order
to reduce the approximation error of the critic network, the dimension of parameters of the critic network is usually relatively large. In
this way, optimizing and solving according to Eq. (28) will result in non-uniqueness of estimated values of critic network parameters.
To address the aforementioned issue, we first generate numerous distinct state trajectories using different initial states for the same
iteration process in an offline manner. By calculating the initial and terminal states of each trajectory, as well as the accumulated
reward values, we obtain multiple different temporal difference errors through Eq. (27). Provided that there is a sufficient amount of
data, optimization and solving based on Eq. (28) can ensure the uniqueness of the critic network parameters.
t+T
t

)
(τ)
dτ, the temporal difference error can be expressed as

Defining φ = [σc1(x(t + T)) (cid:0) σc1(x(t))], yi = (cid:0)

x(τ), ui
c

r1

∫

(cid:0)

ei
c1

= ̂
W

i T

c1 φ (cid:0) yi = φT ̂
W

i

c1

(cid:0) yi

(29)

The analytical solution of the optimization problem, as formulated in Eq. (28), can be obtained using the least squares algorithm.

Therefore, in the i th iteration process, the estimated values of the critic network parameters

̂
W

i
c1can be updated by the follows

̂
W

i

c1

=

(cid:0)

ΦΦT

)(cid:0) 1Φyi

(30)

where, Φ = [ φ1 φ2 ⋯ φk
collecting control inputs, system states and reward data, the critic network parameters are updated through Eq. (30).

(i = 1⋯k) is the result of the φ in the i th iteration. yi  is the column vector composed of yi. By

], and φi

Based on the estimation of the critic network parameters, a new control policy is updated according to policy improvement

ui+1

c

= (cid:0) 1
2

(cid:0) 1
1 BT

0

R

(∇σc1(x))T ̂
W

i

c1

(31)

It is worth mentioning that although the control policy (31) is an explicit expression, it can still be regarded as an action network,
where the activation function of the action network is the partial derivative of the activation function of the critic network with respect
to state variables. However, under the framework of optimal control, if the reward function is in the form shown in Eq. (12), then the
update of the action network has the above analytical solution and does not need to be solved by optimization.

Fig. 1 shows  the  designing  process  of  offline-based reinforcement  learning-based  approximate  optimal  controller.  The control

policy is used to generate training data, and the least squares algorithm is used to update the evaluation network parameters
to update the control policy ui+1
converge, and the approximate optimal control policy is obtained.

i
c1, so as
. Then the new control policy is used to repeat the above steps until the evaluation network parameters

̂
W

c

Since the reinforcement learning algorithm described above is essentially a policy iteration algorithm, the selection of the initial

7

S. Yang et al.

Journal of the Franklin Institute 362 (2025) 107741

Fig. 2. The structure of an online fault-tolerant control system based on reinforcement learning.

Fig. 3. The flow of the fault-tolerant controller.

policy is critical. Specifically, the initial control policy must be admissible to ensure that subsequent iterative control policies are also
admissible and can gradually converge to the optimal control policy. In practical applications, an initial admissible policy can be
chosen as a PID control policy or a feedback control policy.

8

S. Yang et al.

Journal of the Franklin Institute 362 (2025) 107741

3.2. Online fault-tolerant controller based on reinforcement learning

The  online  fault-tolerant  control  system  based  on  reinforcement  learning  consists  of  three  parts:  (1)  a  neural  network-based
observer;  (2)  an  online  reinforcement  learning  controller;  (3)  a  feedforward  compensation  algorithm.  The  neural  network-based
observer estimates unknown input matrix Band partial disturbancesδ which include additive faults, disturbance torques and a part
of rotational inertia effects. Using the estimated input matrix and the critic network parameters updated by the least squares algorithm,
an attitude stabilization controller based on reinforcement learning is developed, which is easily implementable online. Finally, a
feedforward compensation algorithm based on the neural network is incorporated into the reinforcement learning controller to address
the partial disturbances and achieve online fault-tolerant control. Fig. 2 shows the structure of the entire online fault-tolerant control
system based on reinforcement learning.

Fig. 3 shows the flow of the fault-tolerant controller. The entire process can be described as follows: First, the initial control policy is
used to generate control inputs that act on the system, and then data such as the system’s states and rewards are collected. Next, an
observer is employed to estimate the system model, thereby updating the reinforcement learning and feedforward control strategies. If
the system achieves stable results, the process concludes; otherwise, a new control policy is used to generate new control inputs, and
the above steps are repeated.

3.2.1. Neural network-based observer

When the  spacecraft is  subject  to rotational  inertia  uncertainty, actuator  faults, and  unknown external  disturbances, both  the
system input matrix B and the partial disturbances δ will change. Since the update of the control policy relies on the information of the
input matrix B and cannot handle the adverse effects of the partial disturbances δ, a neural network-based observer has been designed.
The neural network is employed to approximate the unknown system dynamics f(x). Meanwhile, the observer provides data to update
the network parameters for a more accurate approximation, while estimating the input matrix B and the partial disturbances δ.

Using neural networks to approximate nonlinear functions

f(x) = WTσ(x) + ε

(32)

where, Wis the ideal weight, σ(x)refers to a properly constructed activation function, εrefers to the neural network approximation
error, and its norm has an upper bound ε, that is‖ ε ‖< ε.

Therefore, Eq. (8) can be expressed as

˙x = WTσ(x) + Buc + δ + ε

In order to obtain the system input matrix B and the partial disturbances δ, an observer is constructed as follows

˙̂x = ̂W

Tσ(̂x) + ̂Buc + ̂δ + Ko(x (cid:0) ̂x)

where,  ̂x is the estimated values of statex,
estimated value of the partial disturbances, Ko  is a positive definite observation gain matrix.

̂
W  is the estimated value of W,

̂
B is the estimated value of the input matrix B,

The update laws for the above parameters are

˙̂
W = (cid:0) αw

(cid:0)

σ(̂x)̃x

T + kw

̂
W

)

(cid:0)

˙̂
B = (cid:0) αb

)

̃xu

T
c

+ kb

̂
B

˙̂δ = (cid:0) αδ(̃x + kδ

̂δ)

where, ̃x = ̂x (cid:0) x denoted the observer estimation error, αw, αb, αδ, kw, kb, kδare all constants greater than zero.

Based on Eq. (33) and Eq. (34), the state equation of the observer error can be expressed as

˙̃x = (cid:0) Ko

̃x + WTσ(̂x) + ̃

Bu + ̃δ + WT̃σ(x, ̂x) (cid:0) ε

(33)

(34)

̂δ  is the

(35)

(36)

(37)

(38)

W = ̂
̃

where,
observation error.

W (cid:0) W,

B = ̂
̃

B (cid:0) Band

̃δ = ̂δ (cid:0) δare parameter estimation errors, ̃σ(x, ̂x) = σ(̂x) (cid:0) σ(x) denotes the activation function

Theorem 1: For the unknown nonlinear system described in Eq. (8), using a neural network-based observer defined in Eq. (34) and

the parameter update laws given in Eqs. (35) ~ (37), it can be guaranteed that the estimation error is bounded.

Proof: Define the following Lyapunov function

V1 = 1
̃x
2

T̃x + 1
2αw

(cid:0)
tr

̃
W

T ̃
W

)

(cid:0)

)
T ̃
B

̃
B

tr

+ 1
2αb

+ 1
2αδ

T̃δ
̃δ

Taking the time derivative of V1  and substituting Eqs. (34)-(37) into

˙
V1,

˙
V1can be derived as

(39)

9

S. Yang et al.

Journal of the Franklin Institute 362 (2025) 107741

˙V1 = ̃x
(cid:0)

T ˙̃x + 1
αw
̃x + ̃
W

T

= ̃x

(cid:0)
(cid:0) tr

(cid:0) Ko
Tσ(̂x)̃x

̃
W

(cid:0)
tr

)

̃W

T ˙̃W

+ 1
αb

(cid:0)
tr

)
T ˙̃B
̃B

T ˙̃δ
̃δ

+ 1
αδ

)

Bu + ̃δ + WT̃σ(x, ̂x) (cid:0) ε
Tσ(̂x) + ̃
)
)
T ̂
T̃xu
T ̂
̃
̃
W
B
B
W
T̃x + kδ
̃δ

tr
)

+ kb

T ̂δ
̃δ

̃
B

T
c

(cid:0)

(cid:0)

(cid:0)

T + kw
(cid:0)

since tr(AB) = tr(BA), and when BA is a scalar, tr(AB) = tr(BA) = BA holds. Therefore, Eq. (40) can be simplified as

˙V1 = (cid:0) ̃x

T

Ko

̃x + ̃x

T

wσ (cid:0) kwtr

(cid:0)

)

̃W

T ̂W

(cid:0) kbtr

(cid:0)

)

T ̂B
̃B

(cid:0) kδ

T ̂δ
̃δ

where, wσ = WT̃σ(x, ̂x) (cid:0) ε.

Applying Young’s inequality yields

˙
V1 ≤ (cid:0) λmin(Ko)̃x

T̃x + 1
̃x
2
)
(cid:0)
T ̃
B
kbtr

̃
B

σ wσ (cid:0) 1
T̃x + 1
wT
2
2
)
(cid:0) 1
BTB
2

+ 1
2

kbtr

(cid:0)

(cid:0) 1
2

kδ

T̃δ + 1
̃δ
kδδTδ
2

kwtr

(cid:0)

)

̃
W

T ̃
W

(cid:0)

+ 1
2

kwtr

)

WTW

By combining the same coefficients, Eq. (42) can be rewritten as

˙V1 ≤ λ1V1 + μ1

where

λ1 = min{2λmin(Ko) (cid:0) 1, αwkw, αbkb, αdkd}

μ1

= 1
2

σ wσ + 1
wT
2

(cid:0)

kwtr

WTW

)

+ 1
2

(cid:0)

)
BTB

kbtr

+ 1
kδδTδ
2

Integrating Eq. (43) yields

V1(t) ≤

μ1
λ1

(

+

V1(0) (cid:0)

)

μ1
λ1

(cid:0) λ1 t

e

(40)

(41)

(42)

(43)

(44)

(45)

(46)

where, V1(0)is the initial value of Lyapunov function V1.

From Eq. (46), it can be seen that the Lyapunov function V1  is bounded. Furthermore, according to theorem 1, it follows that the

observer estimation error ̃x and the parameter estimation errors  ̃W, ̃B, ̃δ are all bounded. This completes the proof.

When  kw,kb  and  kδare  determined,  μ1  has  an  upper  bound.  From  Eq.  (46),  it  can  be  seen  that  the  upper  bound  of  Lyapunov
/λ1. By increasing the values of Ko, αw, αb, and αδ, the value of λ1 can be increased, thereby reducing the upper

functionV1 depends onμ1
bound of V1  and, consequently, decreasing the estimation error of the observer.

In particular, when the parameters kw,kb  and kδ  are set to zero, the following inequality holds

˙
V1 ≤ (cid:0) λmin(Ko)̃x

T̃x + 1
̃x
2

T̃x + 1
wT
2

σ wσ

Observer estimation error converges to setG1

{

G1 =

̃x|‖ ̃x ‖ ≤

}

‖ wσ ‖
2λmin(Ko) (cid:0) 1

Therefore, if λmin(Ko) > 0.5 holds, the observer estimation error is bounded.

(47)

3.2.2. Online controller based on reinforcement learning

To achieve stable attitude control of the spacecraft in the presence of model uncertainties and actuator faults, a fault-tolerant
controller  is  designed  using  the  reinforcement  learning  method.  Similar  to  the  above  offline  reinforcement  learning  algorithm,
define the following reward function

r2(x, ucn) = xTQ2x + uT

cnR2ucn

(48)

where, Q2  and R2  are positive-definite matrices with appropriate dimensions, representing the weights of control performance and
control input, ucn  is the control policy by online reinforcement learning.

Define the following cost function

∫ ∞

J2(t) =

r2(τ)dτ

t

10

(49)

S. Yang et al.

Journal of the Franklin Institute 362 (2025) 107741

Using the critic network to approximate the optimal cost function as follows

∗
J
2

= WT

c2σc2(x) + εc2

(50)

where, x refer to  the inputs of  the critic network, Wc2  refer to  the optimal critic network parameters, σc2  refer  to the activation
functions of the critic network, εc2  is the approximation error of the critic network.

The optimal critic network parameters and the approximation error of the critic network are unknown, so the estimated value of the

cost function

̂
J2  can be expressed as

̂
J2 = ̂
W

T

c2σc2(x)

where,

̂
Wc2  are the estimated values of the critic network parameters Wc2.

Define the temporal difference error in the same form as Eq. (27)

ec2 =

∫

t+T

t

r2(x(τ), ucn(τ))dτ + ̂
W

T

c2

[σc2(x(t + T)) (cid:0) σc2(x(t))]

(51)

(52)

Due to the real-time requirements of online fault-tolerant control, the RLS method is employed to update the parameters of the

critic network.
Letting φc2

= σc2(x(t + T)) (cid:0) σc2(x(t)), yc2 = (cid:0)

∫

t+T
t

̂
Wc2(k + 1) = ̂

[
yc2(k + 1) (cid:0) φT
W c2(k) + K(k + 1)
c2

r2(x(τ), ucn(τ))dτ, then
]
W c2(k)

/ [

K(k + 1) = P(k)φc2

(k + 1)

P(k + 1) =

[
I6 (cid:0) K(k + 1)φT
c2

(k + 1)P(k)φc2
1 + φT
c2
]
(k + 1)

P(k)

(k + 1)̂
]
(k + 1)

̂
Wc2  can be updated by RLS method

(53)

(54)

(55)

where, k refers to the sequence number of the collected data, Pis the covariance matrix. By collecting control inputs, system states, and
reward data, the parameters are updated using Eq. (53).

After determining the initial values of

̂
Wc2  and P, the critic network parameters can be updated based on φc2  and yc2collected.
̂
There are two methods for selecting the initial values: One method is to set P(0) as a sufficiently large unit matrix and select
Wc2(0) as a
sufficiently small real vector or a zero vector; the other method involves using an offline nominal controller based on offline rein-

forcement learning, where the trained
admissible, the second method is adopted in this study.

̂
Wc2 and corresponding P are used as the initial values. To ensure that the initial control policy is

Compared  to  the  least  squares  algorithm,  the  RLS  method  offers  several  advantages  for  updating  critic  network  parameters.
Specifically, RLS allows for parameter updates at each sampling time without needing to wait for sufficient data accumulation. This
feature enhances real-time performance and is more suitable for online implementation. Additionally, the shorter update intervals
result in smoother parameter changes and reduce the likelihood of abrupt variations in control inputs. Moreover, RLS avoids matrix
inversion, thereby effectively reducing computational complexity.

Based on the above analysis, the optimal online reinforcement learning control policy can be expressed by

∗
u
cn

= (cid:0) 1
(cid:0) 1
2 BT(∇σc2(x))TWc2
R
2

(56)

Since the actual values of B and Wc2  are unknown,

̂
B and

̂
Wc2  are used for approximation. Therefore, the online reinforcement

learning approximate optimal controller can be expressed as

̂ucn = (cid:0) 1
(cid:0) 1
R
2
2

̂
B

T(∇σc2(x))T ̂
W c2

(57)

It can be seen from Eq. (9) that B is affected by the multiplicative actuator faults. By using the observer based on neural network to
estimate B and combining reinforcement learning method to design the controller, the control objective can be achieved and the
adverse effects due to multiplicative faults can be eliminated.

3.2.3. Feedforward compensation algorithm

When rotational inertia uncertainty, additive actuator faults and disturbance torques exist, the partial disturbances δ in Eq. (8) is
non-zero and independent of the system states. This will make it difficult to ensure that the system states converge to zero using only
the online reinforcement learning controller proposed in Section 3.2.2. Therefore, a feedforward compensation algorithm is added to
the online reinforcement learning controller to deal with the impact of the partial disturbances δ.

The feedforward compensation control law can be given by

̂uδ = (cid:0) ̂
B

+̂δ

where,

̂δ  is given by the neural network-based observer.

11

(58)

S. Yang et al.

Journal of the Franklin Institute 362 (2025) 107741

Finally, the command control torque of the actuator is described by

uc = ̂ucn + ̂uδ

(59)

It can be seen from Eq. (59) that the online fault-tolerant controller based on reinforcement learning can directly calculate the
command control torque of the actuator. The entire fault-tolerant control scheme is divided into three parts. Firstly, a neural network-
based observer is designed to estimate the unknown system parameters, including the input matrix Band the partial disturbancesδ.
Secondly, with the estimated value of the input matrix B, a reinforcement learning based online controller is proposed to achieve
attitude  stabilization  of  spacecraft,  while  reducing  the  impact  of  multiplicative  faults  of  the  actuator.  Finally,  a  feedforward
compensation algorithm is added to the attitude controller to eliminate the adverse effects of additive faults of actuator and external
disturbance torques.

3.2.4. Controller stability analysis

Theorem 2: For the system model with inertia uncertainty, actuator faults, and disturbances as described in Eq. (8), the observer
parameters defined in Eq. (34) are updated according to Eqs. (35)–(37), and the critic network parameters defined in Eq. (51) are
updated  according  to  Eqs.  (53)–(55).  Under  these  conditions,  the  online  reinforcement  learning-based  fault-tolerant  controller,
composed of Eqs. (57) and (58) as shown in Eq. (59), can guarantee the bounded stability of the system state.

Proof: Define the following Lyapunov function

V2 = 1
2

xTx + J

∗
2

Taking the time derivative of the above equation and substituting Eqs.(8) and (59) yields

(cid:0)

)T ˙x

˙
∗
V2 = xT ˙x +
∇J
2
= xT(f(x) + B(̂ucn + ̂uδ) + δ) +
∗
= xT(f(x) + B(̂ucn + ̃uδ)) +
∇J
2

(cid:0)

(cid:0)

)
T(f(x) + B(̂ucn + ̂uδ) + δ)

∗
∇J
2
)
T(f(x) + B(̂ucn + ̃uδ))

where, ̃uδ = ̂uδ + B

+δis the feedforward compensation error.

According to Eq. (59), it yields

)

T

(cid:0)

∗
∇J
2

B = WT
c2

∇σc2(x)B = (cid:0) 2u

∗T
cn R2

Due to

xTQ2x + u

∗
∗T
cn R2u
cn

+

(cid:0)

)

T

(cid:0)

∗
∇J
2

f(x) + Bu

∗
cn

)

= 0

Eq. (61) can be expressed as

(cid:0)

)

T

∗
∇J
2

˙
V2 = xT(f(x) + B(̂ucn + ̃uδ)) +

f(x) +
∗T
= xT(f(x) + B(̂ucn + ̃uδ)) (cid:0) xTQ2x (cid:0) u
cn R2u
)T
(cid:0)
∗
∗
B̃uδ
∇J
∇J
+
2
2
∗
∗T
(cid:0) 2u
cn R2u
cn
T
T
cnR2̃ucn (cid:0) ̂u

B̂ucn +
= xT(f(x) + B(̂ucn + ̃uδ)) (cid:0) xTQ2x + u
= xT(f(x) + B(̂ucn + ̃uδ)) (cid:0) xTQ2x + ̃u

)T

(cid:0)

(cid:0)

)
T

(cid:0)

B(̂ucn + ̃uδ)
∗
∇J
2

Bu

)
T

∗
cn

∗
∇J
2
∗
(cid:0)
cn

∗T
∗T
cn R2̃uδ
cn R2 ̂ucn (cid:0) 2u
∗T
cn R2̃uδ
cnR2 ̂ucn (cid:0) 2u

∗
where, ̃ucn = ̂ucn (cid:0) u
cn  is the estimation error of the optimal control policy.
Since  (cid:0) 2u

˙
V2  satisfies the following inequality

T
δ R2̃uδ,

∗T
cn R2̃uδ ≤ u

∗T
cn R2u

+ ̃u

∗
cn

˙
V2 = xT(f(x) + B(̂ucn + ̃uδ)) (cid:0) xTQ2x + ̃u
T
≤ xT(f(x) + B(̂ucn + ̃uδ)) (cid:0) xTQ2x + ̃u
cnR2

T
cnR2
̃ucn (cid:0) ̂u

̃ucn (cid:0) ̂u

T
cnR2

T
cnR2
̂ucn + u

̂ucn (cid:0) 2u
∗T
cn R2u

∗T
cn R2
∗
cn

̃uδ
+ ̃u

T
δ R2

̃uδ

(60)

(61)

(62)

(63)

(64)

(65)

Since f(x) satisfies Lipschitz conditions, there is ‖ f(x) ‖≤ Df ‖ x ‖, whereDf  is a positive real number. Combining with Young’s

inequality, the following inequality holds

̂ucn + u

∗
∗T
cn R2u
cn

+ ̃u

T
δ R2

̃uδ

˙
V2 ≤ xT(f(x) + B(̂ucn + ̃uδ)) (cid:0) xTQ2x + ̃u
≤ Df xTx + 1
xTx + 1
2
2
T
̃ucn (cid:0) ̂u
(cid:0) xTQ2x + ̃u
cnR2
)
λmin(Q2) (cid:0) Df (cid:0) 1
(cid:0)
T
δ

+0.5λmax

xTx (cid:0)

BTB

)
̃u

≤ (cid:0)

̂u

(cid:0)

T

̃ucn (cid:0) ̂u

T
T
cnR2
cnR2
xTx + 1
cnBTB̂ucn + 1
̃u
2
2
∗T
̂ucn + u
+ ̃u
cn R2u
(cid:0)

T
cnR2
(cid:0)

∗
cn

T

(cid:0)
̃uδ + λmax(R2)

λmin(R2) (cid:0) 0.5λmax
∗
cn

̃ucn + u

∗T
cn u

T
cn

̃u

δ BTB̃uδ

T
δ R2

BTB

̃uδ
))
T
̂u
cn
)

+ ̃u

T
δ

̃uδ

̂ucn

(66)

The Eq. (66) can be rewritten as

12

S. Yang et al.

Journal of the Franklin Institute 362 (2025) 107741

(67)

(68)

(69)

˙
V2 ≤ (cid:0) λxxTx (cid:0) λcn

̂u

T
cn

̂ucn + μ2

where, λx,λcn  and μ2are respectively expressed by

λx = λmin(Q2) (cid:0) Df (cid:0) 1

λcn = λmin(R2) (cid:0) 0.5λmax

(cid:0)

)
BTB

μ2

= 0.5λmax

(cid:0)

)
̃u
BTB

T
δ

(cid:0)
̃uδ + λmax(R2)

̃u

T
cn

)

When λmin(Q2) > Df + 1 and λmin(R2) > 0.5λmax
the system state variables x are bounded and stable. In practical applications, the upper limits of Df  and λmax
by considering the constraints imposed on the system, and then Q2  and R2  can be set accordingly.

̃ucn + u
(cid:0)

T
δ

∗
cn

̃uδ

+ ̃u

∗T
cn u
)
BTB
, both λx and λcn are greater than zero. According to Lyapunov Stability Theorem,
can be determined

BTB

(70)

)

(cid:0)

This completes the proof.
Define the setG2

{

G2 =

x|‖ x ‖ ≤

}

μ2
λx

Under the premise of selecting appropriate parameters to ensure that λx  and λcn  are both greater than zero, if x does not belong to
˙
V2 < 0 holds. In this case, the value of the Lyapunov function will gradually decrease, and x will eventually converge to
the set G2, then
the set G2. Therefore, to reduce the control error of the system state variables, one can appropriately increase parameter λx  or decrease
)
parameter  μ2.  Specifically,  while  ensuring  λmin(Q2) > Df + 1  andλmin(R2) > 0.5λmax
BTB
,  the  eigenvalues  of  matrix  Q2  can  be
increased appropriately or the eigenvalues of matrix R2  can be decreased appropriately.

(cid:0)

4. Simulation results

In this section, a simulation example is carried out to illustrate the controller design procedures and verify the effectiveness of the

proposed controller based on reinforcement learning.

The actual and nominal moments of inertia of the spacecraft are given respectively as
⎡

⎡

⎣

Ib =

45.4
1.5
1

1.5
23.3
1.2

1
1.2
32.8

⎤
⎦kg ⋅ m2, Ib0 =

⎤
⎦kg ⋅ m2

⎣

40
0
0

0
20
0

0
0
28

⎡

The installation matrix of the actuator is given as
/ ̅̅̅
√
3
/ ̅̅̅
√
3
/ ̅̅̅
√
3

0 1 0 1

1 0 0 1

0 0 1 1

C =

⎣

⎤

⎦

The initial attitude quaternion and angular velocity of the spacecraft are set by

Qb(0) = [0.9531 0.1 0.15 (cid:0) 0.12]T and ωb(0) = [ 0.4 (cid:0) 0.2 0.3 ]T o/s.

The disturbance torque acting on the spacecraft is given as

⎡

⎣

Td =

3cos(0.001t)
cos(0.001t) + 1
(cid:0) 4sin(0.001t)

⎤
⎦ × 10

(cid:0) 4 N ⋅ m

The actuator faults are set as: the x-axis actuator simultaneously fails at the 20th second, where the fault coefficient is e1  = 0.5, and

the additive fault is uc1 = (cid:0) 0.1 N ⋅ m.

The control parameters in this paper are categorized into four groups: neural network structure, observer parameters, reinforce-
ment learning parameters, and RLS parameters. The neural network structure employs nonlinear functions, drawing on research re-
sults such as those in [26]. The observer parameters, which are used to adjust the convergence rate of the observer, are selected based
on experience and fine-tuned through experimentation. For reinforcement learning, the parameters are chosen to satisfy the stability
conditions derived in this paper, assuming that the system inputs and states have upper bounds. The initial values of the RLS pa-
rameters are selected from the offline controller to enhance real-time performance and convergence.

1) Simulation of offline reinforcement learning nominal controller
In the cost function, the weight coefficients are set as Q1 = 50I6, R1 = 0.1I4. The neural network structure similar to that in the ref
[28]. is adopted. The output of the activation function of the critic network is 21-dimensional, and the specific form of the activation
function is given as

13

S. Yang et al.

Journal of the Franklin Institute 362 (2025) 107741

Fig. 4. Quaternions obtained by the initial control policy.

Fig. 5. Attitude angular velocity obtained by the initial control policy.

Fig. 6. Command control torque obtained by the initial control policy.

[

σc1(x) =

x2
1

, x2
2

, x2
3

, x2
4

, x2
5

, x2
6

, x1x2, x1x3, x1x4, x1x5, x1x6, x2x3,

x2x4, x2x5, x2x6, x3x4, x3x5, x3x6, x4x5, x4x6, x5x6]T

Since the algorithm needs to start iterating from an initial admissible policy, the initial values of the critic network parameters was

obtained by fitting through a PID control law with

0

= [0, 0, 0, 75.4, 18.9, 37.0, 0, 0, 85.3, (cid:0) 8.5, (cid:0) 11.9, 0, (cid:0) 8.5,

̂
W
c1
21.3, (cid:0) 6.0, (cid:0) 11.9, (cid:0) 6.0, 41.8, (cid:0) 15.1, (cid:0) 21.1, (cid:0) 10.6]T

Using the initial control policy to control the nominal system, the simulation results are shown in Fig. 4-Fig. 6.

14

S. Yang et al.

Journal of the Franklin Institute 362 (2025) 107741

Fig. 7. The norm of critic network parameter vector obtained by offline RL algorithm.

Fig. 8. The cost function obtained by offline RL algorithm.

Fig. 9. Quaternions obtained by the final control policy.

From Fig. 4–Fig. 5, it can be seen the spacecraft attitude and attitude angular velocity converge eventually, but there is some
overshoot and oscillation in the convergence process. Fig. 6 shows the command control torque over time, which is also convergent.
Based on the initial control policy, the nominal controller based on reinforcement learning is trained offline. The data required for
iteration is obtained by state trajectories generated by 500 random initial states. Fig. 7 shows the norm of the evaluation network
parameter vector under different iteration times, which converges after 4 or 5 iterations, indicating that the offline reinforcement
learning algorithm has good convergence properties. Fig. 8 shows the cost function of the offline algorithm. It can be seen that the cost
function continuously decreases as the number of iterations increases, and it essentially converges when the number of iterations
reaches 4 to 5.

The critic network parameter vector for the final iteration is given as

15

S. Yang et al.

Journal of the Franklin Institute 362 (2025) 107741

Fig. 10. Attitude angular velocity obtained by the final control policy.

Fig. 11. Command control torque obtained by the final control policy.

Fig. 12. Cost function obtained by the initial and final control policy.

̂
W c3 = [165.2, 137.7, 149.6, 128.2, 51.8, 80.2, (cid:0) 8.9, (cid:0) 9.1, 161.8, (cid:0) 10.5, (cid:0) 14.3,
(cid:0) 7.2, (cid:0) 11.8, 80.4, (cid:0) 10.0, (cid:0) 13.8, (cid:0) 11.7, 112.6, (cid:0) 20.4, (cid:0) 27.9, (cid:0) 17.9]T

and the simulation results using the parameters from the final iteration are shown in Fig. 9-Fig. 11.

By  comparing  Figs.4  and  5  with  Figs.  9 and  10,  it  is  evident  that  the  spacecraft  attitude  control  performance  is  significantly
improved  after applying the  reinforcement  learning algorithm. The attitude  convergence  time is  reduced, and  there is  almost no
overshoot or oscillation during the convergence process. Fig. 11 illustrates the time-varying curve of the commanded control torque,
indicating that the final control policy requires a larger control torque compared to the initial control policy.

In order to illustrate the effect of reinforcement learning algorithm more intuitively, the cost function curve is shown in Fig. 12. As
can be seen from the simulation results, under the initial control policy, the cost function eventually stabilizes around 8. In contrast,

16

S. Yang et al.

Journal of the Franklin Institute 362 (2025) 107741

Fig. 13. Quaternions obtained by the co-state approximation-based final control policy.

Fig. 14. Attitude angular velocity obtained by the co-state approximation-based final control policy.

Fig. 15. The norm of critic network parameter vector obtained by offline co-state approximation-based RL algorithm.

In Section 3.1.2, we mentioned that in addition to using neural networks to approximate the optimal value function J

after incorporating the offline reinforcement learning algorithm, the cost function corresponding to the final control policy decreases
to around 7. This represents a reduction of approximately 12.5 %, indicating that the reinforcement learning algorithm is effective.
∗
1, it is also
∗
possible to approximate the co-state ∇J
1  using neural networks and then obtain the approximate optimal controller through policy
iteration. To compare these two methods, the numerical simulation results based on neural network approximation of the co-state are
presented in Fig. 13-Fig. 16. Figs. 13 and 14 present the curves of quaternions and angular velocity over time under the final control
policy obtained by using neural networks to approximate the co-state and through policy iteration. Comparison reveals that the final
control performance of the two approximation methods is essentially the same. Figs. 15 and 16 illustrate the convergence of the norm
of the neural network parameter vector and the  cost function during  the policy iteration process when  using neural networks to
approximate the co-state. It is observed that the convergence is relatively slow, requiring approximately 10 iterations to stabilize.

17

S. Yang et al.

Journal of the Franklin Institute 362 (2025) 107741

Fig. 16. The cost function obtained by offline co-state approximation-based RL algorithm.

Fig. 17. Quaternions obtained by online algorithm without feedforward compensation.

Fig. 18. Attitude angular velocity obtained by online algorithm without feedforward compensation.

2) Simulation of online fault-tolerant controller based on reinforcement learning
The initial parameters of neural network-based observer are given as follows. ̂x0 is equal to the initial states,

̂
B0 is equal to the input
̂δ0 is zero, ̂W0 is randomly selected in [(cid:0) 0.5,0.5]. The activation function in observer is σ(x) = [ x σc2(x) ]T,

matrix of nominal system,
the gain matrix is given as Ko = 20I6and various parameters in update law are αw = 10, αb = 10, αδ = 100,kw = kb  = kδ  = 0.

The weight coefficients in the cost function and the activation function of the critic network in online reinforcement learning
algorithm are kept consistent with the offline algorithm, which are Q2 = 50I6, R2 = 0.1I4, σc2(x) = σc1(x). The initial values of critic
network parameters are consistent with the parameters when offline algorithm converges, and the initial covariance matrix is P(0) =
106I21.

Before  verifying  the  effectiveness  of  the  online  fault-tolerant  controller  based  on  reinforcement  learning,  the  necessity  of  the

18

S. Yang et al.

Journal of the Franklin Institute 362 (2025) 107741

Fig. 19. Command control torque obtained by online algorithm without feedforward compensation.

Fig. 20. Actual control torque obtained by online algorithm without feedforward compensation.

Fig. 21. Estimation errors of quaternions.

feedforward compensation algorithm is verified. The output of the feedforward compensation algorithm as ̂uδ  is set to zero, and only
the observer and the online reinforcement learning algorithm are used to generate the command control torque. The simulation results
are shown in Fig. 17-Fig. 20.

From Fig. 17 and Fig. 18, it can be seen that after the actuator faults occur at the 20th second, the quaternions eventually converge
to non-zero values, which indicates that there is a steady-state control error if the feedforward compensation is not applied. From
Fig. 19 and Fig. 20, it can be seen that when the actuator faults occur at the 20th second, there is a sudden change in the actual control
torque, as well as a sudden change in quaternions and angular velocity, resulting in a change in the command control torque.

When  applying  the  feedforward  compensation  algorithm,  the  simulation  of  the  online  fault-tolerant  control  scheme  based  on

reinforcement learning is carried out, and the simulation results are shown in Fig. 21-Fig. 26.

19

S. Yang et al.

Journal of the Franklin Institute 362 (2025) 107741

Fig. 22. Estimation errors of attitude angular velocity.

Fig. 23. Quaternions obtained by online algorithm.

Fig. 24. Attitude angular velocity obtained by online algorithm.

From Fig. 21 and Fig. 22, it can be seen that the estimation errors of attitude quaternions and attitude angular velocity converge to

zero, which indicates that the observe-based neural network can estimate the input matrix B and partial disturbances δ exactly.

From Fig. 23 and Fig. 24, it can be seen that due to the use of the feedforward compensation algorithm, the spacecraft attitude and
attitude  angular  velocity  can  still  converge  after  the  faults  occur,  which  indicates  that  the  online  fault-tolerant  control  based  on
reinforcement learning can effectively achieve attitude stabilization of spacecraft with inertia uncertainty, actuator faults and external
disturbances.

Fig. 25 illustrates that the commanded control torque experiences a continuous deviation after 20 s to compensate for actuator
faults. Due to this torque compensation, the attitude deviation and attitude angular velocity deviation that occur at the 20th second
converge rapidly. Correspondingly, the actual control torque oscillates initially and then quickly converges, as shown in Fig. 26.

Fig. 27 illustrates the norm of the critic network parameter vector throughout the entire control process. It can be observed that the

20

S. Yang et al.

Journal of the Franklin Institute 362 (2025) 107741

Fig. 25. Command control torque obtained by online algorithm.

Fig. 26. Actual control torque obtained by online algorithm.

Fig. 27. The norm of critic network parameter vector obtained by online algorithm.

norm of the critic network parameter vector essentially converges before the attitude stabilization is achieved, indicating that the
online reinforcement learning algorithm exhibits good convergence properties.

5. Conclusion

In  this  paper,  a  reinforcement  learning-based  fault-tolerant  control  method  under  the  condition  of  unknown  system  model  is
proposed, aiming to address the attitude stabilization control problem of spacecraft in the presence of inertia uncertainty, actuator
faults and external disturbances. First, an offline nominal controller based on reinforcement learning is designed. This controller serves
as an approximation of the nonlinear optimal controller, thereby enhancing the intelligence and autonomy of the control system.
Subsequently, an observer based on neural network is designed to estimate the system input matrix, addressing the dependency of the

21

S. Yang et al.

Journal of the Franklin Institute 362 (2025) 107741

offline nominal controller on the system model. The offline nominal controller is then employed as the initial control strategy, and the
parameters of the critic network are updated online using the RLS method, resulting in an online reinforcement learning controller that
improves the real-time performance of the algorithm. Finally, to eliminate the adverse effects of actuator additive faults and external
disturbance torques on attitude control performance, a feedforward compensation algorithm based on the partial disturbances esti-
mated  by  the  neural  network  observer  is  designed,  thereby  achieving  a  complete  online  fault-tolerant  control  scheme  based  on
reinforcement learning. Numerical simulation results demonstrate the effectiveness of the proposed fault-tolerant control scheme,
providing a feasible solution for spacecraft attitude control.

CRediT authorship contribution statement

Shaolong  Yang:  Writing  –  original  draft,  Visualization,  Validation,  Software,  Resources,  Methodology,  Investigation,  Formal
analysis,  Data  curation,  Conceptualization.  Lei  Jin:  Writing  –  review  &  editing,  Validation,  Supervision,  Project  administration,
Methodology, Funding acquisition, Conceptualization. Jiaxuan Rao: Writing – review & editing, Writing – original draft, Software,
Resources, Investigation, Formal analysis, Data curation.

Declaration of competing interest

The authors declare that they have no known competing financial interests or personal relationships that could have appeared to

influence the work reported in this paper.

References

[1] M. Tafazoli, A study of on-orbit spacecraft failures[J], Acta Astronaut. 64 (2-3) (2009) 195–205.
[2] A. Niederlinski, A heuristic approach to the design of linear multivariable interacting control systems[J], Automatica 7 (6) (1971) 691–701.
[3] A. Levis, Challenges to control: a collective view–Report of the workshop held at the University of Santa Clara on September 18-19, 1986[J], IEEe Trans.

Automat. Contr. 32 (4) (1987) 275–285.

[4] J.S. Eterno, J.L. Weiss, D.P. Looze, et al., Design issues for fault tolerant-restructurable aircraft control[A], in: 1985 24th IEEE Conference on Decision and

Control[C], IEEE, Fort Lauderdale, 1985, pp. 900–905.

[5] J. Jin, S. Ko, C.K Ryoo, Fault tolerant control for satellites with four reaction wheels[J], Control Engineering Practice 16 (10) (2008) 1250–1258.
[6] C. Zhang, B. Xiao, J. Wu, et al., On low-complexity control design to spacecraft attitude stabilization: An online-learning approach[J], Aerosp. Sci. Technol. 110

(2021) 106441.

[7] J. Zhou, X. Li, R. Liu, et al., Active fault-tolerant satellite attitude control based on fault effect classification[J], Proceedings of the Institution of Mechanical

Engineers, Part G: Journal of Aerospace Engineering 231 (10) (2017) 1917–1934.

[8] Q. Shen, C. Yue, C.H. Goh, et al., Active fault-tolerant control system design for spacecraft attitude maneuvers with actuator saturation and faults[J], IEEE

Transactions on Industrial Electronics 66 (5) (2018) 3763–3772.

[9] Z. Wang, Q. Li, S. Li, Adaptive integral-type terminal sliding mode fault tolerant control for spacecraft attitude tracking[J], IEEe Access. 7 (2019) 35195–35207.
[10] O. Tutsoy, D. Asadi, K. Ahmadi, et al., Robust reduced order thau observer with the adaptive fault estimator for the unmanned air vehicles[J], IEEe Trans. Veh.

Technol. 72 (2) (2023) 1601–1610.

[11] J. Sanwale, S. Salahudden, D.K Giri, Neuro-Adaptive Fault-Tolerant Sliding Mode Controller for Spacecraft Attitude Stabilization[J], J. Spacecr. Rockets. 58 (6)

(2021) 1924–1929.

[12] N. Zhou, Y. Kawano, M. Cao, Neural network-based adaptive control for spacecraft under actuator failures and input saturations[J], IEEe Trans. Neural Netw.

Learn. Syst. 31 (9) (2019) 3696–3710.

[13] R.S. Sutton, A.G. Barto, Reinforcement learning: An introduction[M], MIT press, 2018, pp. 1–18.
[14] M.H. Li, H. Zhang, M.L. Liu, et al., Fault tolerant control method of manipulator based on deep reinforcement learning[J], Transducer and Microsystem

Technologies 39 (1) (2020) 53–55.

[15] I. Ahmed, H. Khorasgani, G. Biswas, Comparison of model predictive and reinforcement learning methods for fault tolerant control[J], IFAC-PapersOnLine 51

(24) (2018) 233–240.

[16] I. Ahmed, M. Qui˜nones-Grueiro, G. Biswas, Fault-Tolerant Control of Degrading Systems with On-Policy Reinforcement Learning[J], IFAC-PapersOnLine 53 (2)

(2020) 13733–13738.

[17] D. Zhang, Z. Gao, Fault tolerant control using reinforcement learning and particle swarm optimization[J], IEEe Access. 8 (2020) 168802–168811.
[18] J. Ren, J.W. Liu, P. Yang, Fault-tolerant tracking control for continuous flight control system based on reinforcement learning algorithm with incremental

strategy[J], Control Theory and Technology 37 (7) (2020) 1429–1438.

[19] M.H. Zheng, Y.H. Wu, C.Y Li, Reinforcement learning strategy for spacecraft attitude hyperagile tracking control with uncertainties[J], Aerosp. Sci. Technol.

119 (2021) 107126.

[20] C. Hua, S.X. Ding, Y.A .W Shardt, A New Method for Fault Tolerant Control through Q-Learning[J], IFAC-PapersOnLine 51 (24) (2018) 38–45.
[21] T.S. Li, W.W. Bai, Q. Liu, et al., Distributed Fault-Tolerant Containment Control Protocols for the Discrete-Time Multiagent Systems via Reinforcement Learning

Method[J], IEEe Trans. Neural Netw. Learn. Syst. 34 (8) (2023) 3979–3991.

[22] L.M. Wang, X.Y. Li, F.R. Gao, et al., Reinforcement Learning-Based Optimal Fault-Tolerant Tracking Control of Industrial Processes[J], Ind. Eng. Chem. Res. 62

(39) (2023) 16014–16024.

[23] X.Y. Li, Q.W. Luo, L.M Wang, et al., Off-policy reinforcement learning-based novel model-free minmax fault-tolerant tracking control for industrial processes[J],

J. Process. Control 115 (2022) 145–156.

[24] H. Li, Y. Wu, M. Chen, Adaptive fault-tolerant tracking control for discrete-time multiagent systems via reinforcement learning algorithm[J], IEEe Trans.

Cybern. 51 (3) (2020) 1163–1174.

[25] W. Zhao, H. Liu, F.L Lewis, Fault-Tolerant Control for the Formation of Multiple Unknown Nonlinear Quadrotors via Reinforcement Learning[J], IFAC-

PapersOnLine 53 (2) (2020) 2465–2470.

[26] H. Zhang, K. Zhang, Y. Cai, et al., Adaptive fuzzy fault-tolerant tracking control for partially unknown systems with actuator faults via integral reinforcement

learning method[J], IEEE Transactions on Fuzzy Systems 27 (10) (2019) 1986–1998.

[27] Liu X., Yuan Z., Gao Z., et al. Reinforcement Learning-Based Fault-Tolerant Control for Quadrotor UAVs Under Actuator Fault[J]. 2024, 20(12): 13926–13935.
[28] D. Vrabie, F. Lewis, Neural network approach to continuous-time direct adaptive optimal control for partially unknown nonlinear systems[J], Neural Networks

22 (3) (2009) 237–246.

22

