Aerospace Science and Technology 168 (2026) 111238

Contents lists available at ScienceDirect

Aerospace Science and Technology

journal homepage: www.elsevier.com/locate/aescte

Original article
Safe reinforcement learning based agile satellite attitude control for
non-cooperative target tracking with operation constraints and actuator
faults

a, Hongji Zhuang
a,b,∗, Vladimir Y. Razoumny

Wenlong Lu
Shufan Wu
a Shanghai Jiao Tong University, Shanghai, China
b Peoples’ Friendship University of Russia named after Patrice Lumumba(RUDN University), Moscow, Russian Federation

a, Qiang Shen
b, Yury N. Razoumny

a, Ziyao Geng

a, Zhongcheng Mu
b

a,

a r t i c l e   i n f o

a b s t r a c t

Editor: V Kyriakos

Keywords:
Reinforcement learning
Spacecraft attitude control
Non-cooperative target tracking
Fault-tolerant control
Situation awareness

Persistent tracking of space-based non-cooperative targets is a fundamental capability for achieving space sit-
uational awareness and enabling numerous downstream space applications. However, it presents signiﬁcant
challenges, particularly during agile attitude maneuvers, due to the need to respect operational constraints and
handle potential actuator faults. In this work, we divide the agile satellite tracking task into three distinct stages
and formulate it as a constrained spacecraft attitude control problem. To systematically address the complex prac-
tical challenges in agile satellite control–including attitude constraints from forbidden zones, angular velocity
limitations, torque saturation, and potential actuator faults–we formulate the problem as a Constrained Markov
Decision Process (CMDP). To enhance the adaptability and fault-tolerance of the controller, we integrate a data-
driven fault identiﬁcation module capable of estimating both actuator eﬀectiveness loss and additive torque
faults. A safe reinforcement learning framework is further employed to learn fault-tolerant control policies that
ensure continuous and stable tracking performance while minimizing the risk of constraint violations. Extensive
simulation results demonstrate that the proposed approach enables the agile imaging satellite to achieve accu-
rate, persistent tracking under strict operational constraints, while maintaining safe and resilient attitude control
in the presence of actuator anomalies.

1.  Introduction

In non-cooperative target tracking missions, the implementation of
active tracking strategies holds irreplaceable signiﬁcance for achiev-
ing space situational awareness [1,2] and enabling numerous down-
stream space applications. Passive, wait-and-see observation methods
are wholly inadequate for meeting mission requirements, as targets may
exhibit unexpected motions necessitating real-time response capabilities
from the tracking system. These core requirements render active track-
ing the sole viable solution for addressing non-cooperative target ob-
servation challenges. Active tracking of space non-cooperative targets
is a crucial prerequisite for downstream tasks such as attitude estima-
tion [3] and pose tracking [4]. The tracking of non-cooperative space
targets presents unique challenges due to their orbital characteristics.
With severely limited visibility windows per orbit, these targets may
abruptly migrate from detectable ranges to unobserved regions. Un-
like conventional Earth-pointing or wait-and-see observation missions

in aerial target tracking [5], tracking non-cooperative targets in space
requires agile satellites to perform rapid responded large-angle attitude
maneuvers to maintain persistent line-of-sight alignment. These agile
reorientations present signiﬁcant operational challenges, particularly in
protecting sensitive onboard payloads.

During  high-speed  attitude  maneuvers,  inadvertent  exposure  to
bright celestial bodies may cause irreversible damage or permanent
degradation to optical instruments and imaging sensors. To ensure pay-
load safety, the satellite must avoid predeﬁned exclusion zones in the
attitude space–known as forbidden-pointing regions. These constraints
are typically time-varying, requiring careful designation to ensure con-
tinuous safety satisfaction throughout the mission. Moreover, to pre-
serve actuator health and ensure feasible control actions, additional dy-
namic constraints such as angular velocity limits and torque saturation
bounds must be considered. These constraints are often coupled and
jointly restrict the maneuverability of the satellite, especially during ag-
gressive tracking. In addition to operational constraints, another critical

∗ Corresponding author.

E-mail address: shufan.wu@sjtu.edu.cn (S. Wu).

https://doi.org/10.1016/j.ast.2025.111238
Received 3 August 2025; Received in revised form 2 November 2025; Accepted 4 November 2025
Available online 9 November 2025
1270-9638/© 2025 Elsevier Masson SAS. All rights are reserved, including those for text and data mining, AI training, and similar technologies.

W. Lu, H. Zhuang, Z. Geng et al.

Aerospace Science and Technology 168 (2026) 111238

and accurate estimation of both eﬀectiveness loss and additive faults
during on-orbit operations.

• We adopt a safe oﬀ-policy reinforcement learning algorithm–WCSAC
(Worst-case Soft Actor-Critic)–to train fault-tolerant control policies.
Under the specialized reward/penalty structure that accounts for
mission-speciﬁc constraints, the learned policy ensures reliable at-
titude tracking performance under varying operational constraints
and fault scenarios while minimizing the risk of constraint violations.

2.  Related work

2.1.  Active tracking of non-cooperative target

Active tracking of non-cooperative targets for observation satellites
involves a large-angle pre-maneuver phase to align the ﬁeld of view with
the target and a ﬁne-angle post-adjustment phase to optimize observa-
tion accuracy.

Most existing research on active tracking primarily emphasizes com-
puter vision techniques during the ﬁne-angle post-adjustment phase
[8,9], where high-precision tracking is achieved through visual feedback
and ﬁne-grained control. However, limited attention has been given
to the control mechanisms during the large-angle pre-maneuver phase,
particularly in terms of attitude dynamics and payload pointing control.
The challenge lies in accurately following the target’s motion via the
rapid and accurate attitude maneuvers of the imaging satellite. Recent
studies have made signiﬁcant progress in this area by leveraging ad-
vanced control strategies. Cao et al. [5] addressed the dynamic process
of target tracking by modeling it as a Markov state transition, which
takes into consideration the movement of the moving target and the
prediction model of target position. Wu et al. [10] proposed a novel
attitude tracking strategy for hybrid actuators, dividing the tracking
mission into three distinct processes and validating strategy accuracy
through numerical simulations. Building on this work, Wu et al. [11]
achieved high-precision attitude tracking by employing an improved
back-stepping controller. To tackle the uncertainties inherent in tracking
operations, Zheng et al. [12] developed a reinforcement learning-based
sliding mode observer, which eﬀectively estimates and compensates for
these uncertainties. Yu et al. [9] proposed a reinforcement learning-
based action decision strategy for chaser satellites, leveraging extracted
visual object information. Taking safe motion constraints into account,
Lin et al. [13] combined the back-stepping control method and an adap-
tive sliding mode law to achieve robust 6 DOF tracking. Lu et al. [14] uti-
lized reinforcement learning to govern satellite attitude control through
torque outputs, achieving both accurate and stable tracking of moving
targets. Additionally, Lu et al. [15] proposed a satellite constellation
scheduling method for multi-target tracking, extending their reinforce-
ment learning-based attitude controller to complex multi-object scenar-
ios.

While studies such as [8,9] have attempted to integrate visual ob-
ject tracking with chaser spacecraft control, their methods simplify the
action space of chaser spacecraft to coordinate displacements, neglect-
ing the detailed consideration of command torques and attitude dynam-
ics. Moreover, practical considerations such as operational constraints
[16–20] and actuator faults [21] are critical for real-world applications
and require further investigation. In summary, while signiﬁcant progress
has been made in active tracking of non-cooperative targets, there re-
mains a need for more comprehensive approaches that integrate ad-
vanced control strategies with practical operation considerations to en-
hance the robustness and applicability of these systems in real-world
scenarios.

2.2.  Reinforcement learning in spacecraft control

Recent advances in reinforcement learning [22–27] have demon-
strated  promising  potential  for  spacecraft  attitude  control  appli-
cations.  Traditional  control  approaches  have  shown  limitations  in

Fig. 1. The attitude Maneuver capability of the Agile Satellite.

challenge arises from actuator faults, which are frequently encountered
during long-duration autonomous missions in space. Actuator faults can
manifest as eﬀectiveness degradation (modeled as multiplicative atten-
uation) or additive biases in the output torque. If not timely identiﬁed
and compensated, such faults may degrade tracking accuracy or lead to
mission failure. However, most existing studies on spacecraft tracking
and control either ignore faults or rely on ideal assumptions, limiting
their applicability to realistic fault-prone environments.

To address the high-velocity characteristics of non-cooperative tar-
gets, our approach leverages the exceptional attitude control ability of
agile satellites (as demonstrated in Fig. 1): (1) During the initial ac-
quisition phase, the satellite executes rapid large-angle maneuvers to
promptly align its payload ﬁeld-of-view with the target; (2) In the subse-
quent observation/tracking stage, it switches to high-precision attitude
ﬁne-tuning mode to optimize tracking accuracy and observation qual-
ity. Furthermore, to address the complex challenges of non-cooperative
space target tracking, we formulate the active tracking problem as a
constrained attitude control problem under uncertainty. Our approach
explicitly considers both operational constraints and potential actuator
faults. The problem is formally cast as a Constrained Markov Decision
Process (CMDP) [6], which provides a uniﬁed framework for: (i) simul-
taneous handling of multiple operational constraints, (ii) robust perfor-
mance under actuator fault scenarios, and (iii) optimization of long-term
tracking objectives while maintaining safety guarantees.

To this end, we propose a fault-tolerant attitude control framework
that integrates safe reinforcement learning (SRL) [7] with data-driven
fault identiﬁcation, oﬀering a robust solution for real-world tracking
missions in complex space environments. At the technical implementa-
tion level, our approach innovatively integrates spatial satellite-target
position vector information with attitude into a uniﬁed representation
of error quaternions. Concurrently, we innovatively incorporate payload
ﬁeld-of-view angle into the reinforcement learning reward function de-
sign, enhancing the tracking process whilst ensuring the target remains
continuously within the ﬁeld of view. Through careful formulation, our
method ensures reliable tracking performance while minimizing the risk
of constraint violations during critical operations.

Our main contributions are summarized as follows:

• We introduce, to our knowledge, the ﬁrst Constrained Markov Deci-
sion Process framework that systematically addresses the complete
spacecraft attitude control challenge for active non-cooperative tar-
get tracking. The complex tracking task is divided into three sequen-
tial,  interdependent  stages,  which  incorporate  critical  real-world
constraints: (i) forbidden-pointing regions, (ii) angular velocity lim-
its, (iii) torque saturation, and (iv) actuator faults. The proposed for-
mulation establishes safety guarantees throughout all mission phases
while maintaining tracking performance.

• We develop a neural network-based time-series regression method
for spacecraft actuator fault identiﬁcation, which enables eﬃcient

2

W. Lu, H. Zhuang, Z. Geng et al.

Aerospace Science and Technology 168 (2026) 111238

handling complex operation constraints [16–19] and unexpected non-
linear disturbances or faults [21], as well as the control torque saturation
problem [28,29]. In contrast, RL-based methods oﬀer several advan-
tages, including adaptability to uncertain environments and the ability
to learn optimal control policies through interaction with the environ-
ment. In addressing rapid attitude transitions during complex orbital
maneuvers, Ma et al. [30] developed a deep reinforcement learning
approach that achieved signiﬁcantly better stabilization performance
than conventional proportional-derivative control methods. Elkins et al.
[22,23] proposed an innovative adaptive control architecture using deep
reinforcement learning, speciﬁcally designed for large-angle reorienta-
tion tasks while maintaining precise pointing accuracy. The study not
only validated the controller’s ability to meet stringent industry accu-
racy requirements but also introduced methodological improvements
through reward function optimization. Liu et al. [31] proposed a re-
inforcement learning-based attitude tracking control strategy for com-
bined spacecraft takeover maneuvers subject to completely unknown
dynamics. Lu et al. [32] introduced a RL-based fault-tolerant control
framework for the spacecraft attitude control problem, incorporating
carefully designed state representations and a hybrid reward mecha-
nism. The proposed framework ensures both rapid response and stable
fault recovery, improving overall control robustness. Recent advances
in safe reinforcement learning [33] have shown signiﬁcant promise for
addressing critical spacecraft control challenges, which provide a prin-
cipled framework for developing controllers that can satisfy stringent
safety requirements while maintaining operational eﬀectiveness. Mu et
al. [34] formulated the spacecraft collision avoidance maneuver prob-
lem as a constrained Markov decision process, incorporating safety con-
straints directly into the learning process. This approach achieved au-
tonomous collision avoidance in simulation scenarios, addressing a key
challenge in applying RL to safety-critical systems. Taking contingent
on obstacle warnings and collision avoidance constraints into account,
Sharma et al. [35] established a safety reinforcement learning frame-
work for devising spacecraft rendezvous guidance strategies.

In the present study, we extend the safe reinforcement learning
methodology to the domain of non-cooperative target tracking. Our for-
mulation treats the space target tracking problem as a specialized in-
stance of attitude control, where the agent must continuously maintain
the target within the payload’s ﬁeld of view while respecting operational
constraints.

3.  Preliminary

3.1.  Task decomposition

The task decomposition for space target tracking is depicted in Fig. 2,
with its operational workﬂow analyzed in the context of an agile imag-
ing satellite mission. The entire process consists of three critical stages:
Fault Identiﬁcation Stage (A-B), Attitude Adjustment Stage (B-C), and
Target Tracking Stage (C-D).

3.1.1.  Fault identiﬁcation stage

The fault identiﬁcation process follows a systematic approach simi-
lar to traditional spacecraft parameter identiﬁcation, which utilizes the
time series of command torques and measured attitude responses (such
as angular velocity and quaternion) to estimate actuator faults through
model-based parameter estimation. By analyzing the discrepancy be-
tween expected and observed dynamics under known torque commands,
both eﬀectiveness loss and additive bias can be determined using opti-
mization techniques or neural networks.

3.1.2.  Attitude adjustment stage

Following successful fault identiﬁcation, the satellite must rapidly
reorient itself from an arbitrary initial state to align its payload’s sight-
line with the space target. This stage accounts for the identiﬁed actuator
faults to ensure reliable maneuver execution. At the beginning of this
stage, the satellite maintains an arbitrary attitude and angular velocity
conﬁguration. Upon command reception, the satellite must initiate pre-
cise attitude maneuvers to ensure target acquisition within the limited
orbital visible time window. The satellite’s maneuverability is demon-
strated through its three-axis (roll, pitch, and yaw) control capability
[14]. This advanced maneuverability enables the satellite to perform
large-angle attitude adjustments, facilitating target acquisition within
the payload’s ﬁeld-of-view [36].

During the attitude adjustment stage, our primary objective is to
align the payload’s sightline with the relative position vector from the
agile satellite to the space target. Following the established methodol-
ogy in [14,37], we adopt the convention that the payload is mounted
along the satellite body’s z-axis. Denote ⃖⃖⃖⃖⃖⃗𝑂𝑇 𝐸𝐶𝐼  and ⃖⃖⃖⃖⃖⃗𝑂𝑆𝐸𝐶𝐼  represent
the ECI position vector of the space target and the agile satellite, re-
spectively. The alignment of 𝑆𝑇𝐸𝐶𝐼  and payload sightline 𝑧𝑏𝑜𝑑𝑦 can be
mathematically expressed as:

𝑧𝑏 =

⃖⃖⃖⃖⃖⃗𝑆𝑇 𝐸𝐶𝐼
|
⃖⃖⃖⃖⃖⃗𝑆𝑇 𝐸𝐶𝐼
|
|

|
|
|

(1)

To ensure the staring attitude where there is no rotation of the z-axis,
the x-axis 𝑥𝑏 and y-axis 𝑦𝑏 vectors in the body frame can be obtained via:

𝑥𝑏 =

𝑧𝑏 × (−𝑦𝑜)
𝑧𝑏 × (−𝑦𝑜)|
|
|
|
𝑦𝑏 = 𝑧𝑏 × 𝑥𝑏

⎧
⎪
⎨
⎪
⎩

(2)

The desired Euler angles under the yaw-pitch-roll (3-2-1) rotation
sequence can be derived by equating the current rotation matrix with
the desired rotation matrix from the orbit frame to the body frame
𝑜𝑟𝑏𝑖𝑡_𝑏𝑜𝑑𝑦 = 𝑅𝑑𝑒𝑠𝑖𝑟𝑒𝑑
𝑅𝑐𝑢𝑟𝑟𝑒𝑛𝑡

𝑜𝑟𝑏𝑖𝑡_𝑏𝑜𝑑𝑦

1:

𝑅𝑐𝑢𝑟𝑟𝑒𝑛𝑡

𝑜𝑟𝑏𝑖𝑡_𝑏𝑜𝑑𝑦 = 𝑅𝑥(𝜑)𝑅𝑦(𝜃)𝑅𝑧(𝜓)

=

⎡
⎢
⎢
⎣

cos 𝜃 cos 𝜓

cos 𝜃 cos 𝜓

− sin 𝜃

− cos 𝜑 sin 𝜓 + sin 𝜑 sin 𝜃 cos 𝜓

cos 𝜑 cos 𝜓 + sin 𝜑 sin 𝜃 sin 𝜓

sin 𝜑 cos 𝜃

sin 𝜑 sin 𝜓 + cos 𝜑 sin 𝜃 cos 𝜓

− sin 𝜑 cos 𝜓 + cos 𝜑 sin 𝜃 sin 𝜓

cos 𝜑 cos 𝜃

(3)

⎤
⎥
⎥
⎦

𝑅𝑑𝑒𝑠𝑖𝑟𝑒𝑑

𝑜𝑟𝑏𝑖𝑡_𝑏𝑜𝑑𝑦 =

𝑥𝑏 ⋅ 𝑥𝑜
⎡
𝑦𝑏 ⋅ 𝑥𝑜
⎢
⎢
𝑧𝑏 ⋅ 𝑥𝑜
⎣

𝑥𝑏 ⋅ 𝑦𝑜
𝑦𝑏 ⋅ 𝑦𝑜
𝑧𝑏 ⋅ 𝑦𝑜

𝑥𝑏 ⋅ 𝑧𝑜
𝑦𝑏 ⋅ 𝑧𝑜
𝑧𝑏 ⋅ 𝑧𝑜

⎤
⎥
⎥
⎦

≜

𝑎11
⎡
𝑎21
⎢
⎢
𝑎31
⎣

𝑎12
𝑎22
𝑎32

𝑎13
𝑎23
𝑎33

⎤
⎥
⎥
⎦

𝜑𝑑 = atan2

𝑦𝑏 ⋅ 𝑧𝑜
𝑧𝑏 ⋅ 𝑧𝑜

𝜃𝑑 = arcsin(−𝑥𝑏 ⋅ 𝑧𝑜)
𝜓𝑑 = 0

⎧
⎪
⎪
⎨
⎪
⎪
⎩

(4)

(5)

Fig. 2. Task decomposition.

1 We refer the reader to the analysis in [37] and [14].

3

W. Lu, H. Zhuang, Z. Geng et al.

Aerospace Science and Technology 168 (2026) 111238

Fig. 3. Field of View of the onboard payload.

Then the corresponding desired quaternion 𝑄𝑑 = [𝑞𝑑
1

be derived via:

, 𝑞𝑑
2

, 𝑞𝑑
3

, 𝑞𝑑

4 ]𝑇  can

𝑞𝑑
4 =

𝑞𝑑
1 =

𝑞𝑑
2 =

𝑞𝑑
3 =

⎧
⎪
⎪
⎪
⎪
⎪
⎨
⎪
⎪
⎪
⎪
⎪
⎩

(1 + 𝑎11 + 𝑎22 + 𝑎33)

1
2

1
2

1
4𝑞𝑑
4
1
4𝑞𝑑
4
1
4𝑞𝑑
4

(𝑎23 − 𝑎32)

(𝑎31 − 𝑎13)

(𝑎12 − 𝑎21)

Finally, the error quaternion 𝑄𝑒 is the quaternion relating the current
, which can be

body frame 𝑄 of the satellite to the desired frames 𝑄𝑑
obtained as follows:

𝑄𝑒 = 𝑄−1

𝑑 ⊗ 𝑄

(7)

1

𝑑 = [−𝑞𝑑

where 𝑄−1
4 ]𝑇  means the inverse or conjugate of the
, −𝑞𝑑
, −𝑞𝑑
2
3
, and ⊗ means the quaternion multiplication op-
desired quaternion 𝑄𝑑
erator of two quaternion.

, 𝑞𝑑

The equation 𝑄𝑒 = [0, 0, 0, 1]𝑇  equals 𝑄 = 𝑄𝑑

, which means the agile
satellite attitude reaches the desired attitude (payload sightline aligns
with ⃖⃖⃖⃖⃖⃗𝑆𝑇 ) via attitude maneuvers.

3.1.3.  Target tracking stage

In the ﬁnal phase, the satellite executes ﬁne attitude maneuvers to
maintain continuous coverage within the limited visible time window,
incorporating fault compensation strategies based on the earlier identi-
ﬁcation results. Following the large-angle attitude adjustment, the agile
satellite successfully acquires the space target within its payload’s ﬁeld
of view, as illustrated in Fig. 3.

Given the orbital dynamics, both the agile satellite and the space
target undergo rapid positional changes, resulting in a time-varying de-
sired quaternion 𝑄𝑑
. During the tracking stage, the satellite is required
to execute ﬁne attitude adjustments, which are crucial for maintaining
continuous FOV coverage. Moreover, maintaining stable tracking is fur-
ther achieved by keeping the angular velocity at a minimal level.

arccos

⃖⃖⃖⃖⃖⃗𝑆𝑇 𝑜𝑟𝑏𝑖𝑡 ⋅ ̂𝑧
|
⃖⃖⃖⃖⃖⃗𝑆𝑇 𝑜𝑟𝑏𝑖𝑡
⋅ | ̂𝑧|
|
|
≤ 𝜔𝑡𝑟𝑎𝑐𝑘𝑖𝑛𝑔, ∀𝜔𝑖 ∈ [𝜔𝑥, 𝜔𝑦, 𝜔𝑧]

< 𝜃𝑡𝑟𝑎𝑐𝑘𝑖𝑛𝑔

|
|
|

𝜔𝑖

⎧
⎪
⎪
⎨
⎪
⎪
⎩

Fig. 4. Attitude Constraints in Ref [18].

3.2.  Operation constraints

(6)

3.2.1.  Attitude constraint

As extensively analyzed in [16–19] and visually represented in Fig. 4,
the satellite’s attitude control is subject to two principal constraint cat-
egories: attitude-forbidden zones and attitude-mandatory zones. The
attitude-forbidden zones encompass both static and dynamic forbidden
zones. The static forbidden zone is primarily associated with bright ce-
lestial bodies, while the dynamic forbidden zone typically corresponds
to the thrust engines of neighboring spacecraft. These zones pose sig-
niﬁcant risks to the onboard payload, particularly imaging observation
instruments, as exposure to intense radiation and brightness levels may
cause irreversible damage or even complete payload system failure. Re-
garding the attitude-mandatory zone, it represents a speciﬁc attitude set
that must be maintained to ensure the space target remains within the
payload’s ﬁeld of view (FOV). This zone is crucial for successful target
acquisition and continuous tracking operations.

𝑠𝑓 , 

𝑓 𝑜𝑟𝑏𝑖𝑑𝑑𝑒𝑛 = {

Attitude-Forbidden Zones: Let 

𝑑𝑓 } represent the
comprehensive set encompassing both static and dynamic forbidden
sources, where 
𝑠𝑓  denotes the collection of static forbidden sources and

𝑑𝑓  represents the set of dynamic forbidden sources. To ensure compli-
ance with the attitude-forbidden constraint, the angular separation be-
tween the payload axis ̂𝑧 and the vectors from the agile satellite to each
forbidden source 𝜁𝑓  must exceed the speciﬁed forbidden sensitive angle
. This constraint can be mathematically expressed as:
𝜃𝑓 𝑜𝑟𝑏𝑖𝑑𝑑𝑒𝑛

arccos

( ⃖⃖⃖⃖⃖⃖⃖⃖⃗𝑆𝜁𝑓 ,𝑖 ⋅ ̂𝑧

)

⃖⃖⃖⃖⃖⃖⃖⃖⃗𝑆𝜁𝑓 ,𝑖‖ ⋅ ‖ ̂𝑧‖
‖

> 𝜃𝑓 𝑜𝑟𝑏𝑖𝑑𝑑𝑒𝑛,

∀𝜁𝑓 ,𝑖 ∈ 

𝑓 𝑜𝑟𝑏𝑖𝑑𝑑𝑒𝑛

(9)

where 𝜁𝑓 ,𝑖 denotes the 𝑖-th attitude-forbidden source in the set 
,
𝑓 𝑜𝑟𝑏𝑖𝑑𝑑𝑒𝑛
𝜃𝑓 𝑜𝑟𝑏𝑖𝑑𝑑𝑒𝑛 represents the minimum acceptable angular separation thresh-
old.

Attitude-Mandatory  Zones:  The  operational  regulation  of  the
attitude-mandatory zone follows the same criterion as the tracking con-
dition deﬁned in Eq. 8. This ensures that the target remains within the
ﬁeld of view coverage of the onboard payload.

(8)

arccos

⃖⃖⃖⃖⃖⃗𝑆𝑇 𝑜𝑟𝑏𝑖𝑡 ⋅ ̂𝑧
|
⃖⃖⃖⃖⃖⃗𝑆𝑇 𝑜𝑟𝑏𝑖𝑡
⋅ | ̂𝑧|
|
|

|
|
|

< 𝜃𝑡𝑟𝑎𝑐𝑘𝑖𝑛𝑔

(10)

where 𝜃𝑡𝑟𝑎𝑐𝑘𝑖𝑛𝑔 denotes the half angle of onboard payload, 𝜔𝑡𝑟𝑎𝑐𝑘𝑖𝑛𝑔 de-
notes the acceptable max angular velocity during tracking, and ̂𝑧 rep-
resents the transformed z-axis of satellite after the body-to-orbit frame
rotation.

3.2.2.  Angular velocity constraint

Considering the limited measurement range of gyroscopes and the
operational requirements of space missions [19], the angular velocity 𝜔

4

W. Lu, H. Zhuang, Z. Geng et al.

Aerospace Science and Technology 168 (2026) 111238

of the agile satellite is subject to the following constraint 2:

4.  Proposed method

𝜔𝑖

≤ 𝜔𝑚𝑎𝑥, ∀𝜔𝑖 ∈ [𝜔𝑥, 𝜔𝑦, 𝜔𝑧]

(11)

where 𝜔max represents the maximum allowable angular velocity magni-
tude to ensure stable and precise attitude control.

3.2.3.  Torque constraint

Actuator saturation is a well-known challenge in traditional satel-
lite attitude control design. This built-in constraint handling enhances
the practicality and safety of the controller in real-world applications.
Speciﬁcally, this design allows the agile satellite agent to make control
torque decisions within a predeﬁned and physically feasible range, in-
herently satisfying the actuator saturation constraint [21,28,29]:

≤ 𝑢𝑚𝑎𝑥

|𝑢𝑐𝑖|
where 𝑢𝑐𝑖 denotes the command torque of any actuator along a given
direction, and 𝑢max is a positive constant.

(12)

3.3.  Actuator faults

The precise attitude control of agile satellites critically depends on
reliable actuator operation, with reaction wheels being particularly vul-
nerable to performance degradation. These high-precision mechanisms
are prone to developing various anomalies across their electrical, me-
chanical, and power delivery subsystems due to prolonged operational
stresses [21]. Empirical observations reveal that the predominant fail-
ure mechanisms stem from cumulative wear eﬀects, including but not
limited to material fatigue, lubrication breakdown, and increasing me-
chanical resistance. These faults manifest as either multiplicative eﬀec-
tiveness loss (𝑒𝑙
), leading to slower response times,
reduced eﬃciency, or even complete failure of the reaction wheel. As
done in previous works [32,38,39], actuator faults are considered in this
study, reﬂecting the complexity and realism of actual tracking scenarios.
The attitude dynamics and kinematics models of the satellite with

) or additive bias (𝑢𝑎

actuator faults are as follows:

𝑞𝑇 𝜔

𝐽 ̇𝜔 = −𝜔×(𝐽 ⋅ 𝜔) + 𝑢 + 𝑑
̇𝑞 = 1
(𝑞× + 𝑞4𝐼3)𝜔
2
̇𝑞4 = − 1
2

⎧
⎪
⎨
⎪
⎩
where 𝐽 is the inertia matrix, 𝜔 is the angular velocity of the agile
satellite, 𝑢 ∈ ℝ𝑛 denotes the actual torque, 𝑑 ∈ ℝ3 denotes the distur-
bance torque, 𝑄 = [𝑞1, 𝑞2, 𝑞3, 𝑞4]𝑇 = [𝑞, 𝑞4]𝑇  denotes the quaternion of
body frame, and the notation × is used to represent the skew-symmetric
cross-product matrix.

(13)

When a fault occurs, the actual torque 𝑢 produced by the actuators
deviates from the command torque 𝑢𝑐 due to eﬀectiveness loss 𝑒𝑙 and
additive bias 𝑢𝑎

.

𝑢 = (𝐼 − 𝐸)𝑢𝑐 + 𝑢𝑎

(14)

where 𝐼 is the identity matrix, 𝐸 = 𝑑𝑖𝑎𝑔(𝑒𝑙1, 𝑒𝑙2, ⋅ ⋅ ⋅, 𝑒ln) represents the ef-
fectiveness loss of each actuator with 𝑒𝑙𝑖 ∈ [0, 1], 𝑢𝑐 = [𝑢𝑐1, 𝑢𝑐2, ⋅ ⋅ ⋅, 𝑢𝑐𝑛]𝑇
is the command torque, and 𝑢𝑎 = [𝑢𝑎1, 𝑢𝑎2, ⋅ ⋅ ⋅, 𝑢𝑎𝑛]𝑇  is the additive bias
fault. Substituting the fault model (Eq. 14) into the dynamics model
(Eq. 13), the attitude dynamics considering the actuator faults can be
written as:
𝐽 ̇𝜔 = −𝜔×(𝐽 ⋅ 𝜔) + (𝐼 − 𝐸)𝑢𝑐 + 𝑢𝑎 + 𝑑

(15)

= −𝜔×(𝐽 ⋅ 𝜔) + 𝑢𝑐 + 𝑓 + 𝑑

This  section  presents  the  proposed  fault-tolerant  and  safety-
aware reinforcement learning framework for agile satellite-based non-
cooperative space target tracking. The method consists of two key com-
ponents: (i) a neural network-based fault identiﬁcation module that
estimates actuator eﬀectiveness loss and additive bias, and (ii) a safe re-
inforcement learning controller based on a worst-case Soft Actor-Critic
algorithm, which generates fault-tolerant attitude commands while en-
suring safety limitations such as forbidden zone avoidance, angular
velocity limits and torque saturation constraints. The overall frame-
work enables intelligent non-cooperative target tracking in uncertain
and fault-prone space environments.

4.1.  Neural network for fault identiﬁcation

(17)

In this paper, fault identiﬁcation based on neural networks is framed
as a time series regression problem. Speciﬁcally, in order to simplify
the neural network’s learning task by precomputing complex matrix op-
erations, we re-analyze the spacecraft dynamics equation (Eq. 13) by
moving the complex computation terms to the left-hand side,
𝐽 ̇𝜔 + 𝜔×(𝐽 ⋅ 𝜔) = (𝐼 − 𝐸)𝑢𝑐 + 𝑢𝑎 + 𝑑
and denote the left-hand side of this equation as the dynamics residuals
Φ:
Φ = 𝐽 ̇𝜔 + 𝜔×(𝐽 ⋅ 𝜔)

(16)

𝑜𝑙𝑑 )

𝑜𝑙𝑑× (𝐽 ⋅ 𝜔𝑚

𝑜𝑙𝑑 )∕𝑑𝑡 + 𝜔𝑚

𝑛𝑒𝑤 − 𝜔𝑚
𝑛𝑒𝑤 and 𝜔𝑚

≈ 𝐽 (𝜔𝑚
where 𝜔𝑚
𝑜𝑙𝑑 represent the measured angular velocity of the
satellite at two consecutive time steps. As illustrated in Fig. 5, the neu-
ral network processes the time series in both the dynamics residuals
and command torques. The input tensor has dimensions 𝐿 × 𝑀, where
𝐿 represents the look-back window size, and 𝑀 = 6 features consist of 3-
axis dynamics residuals Φ and corresponding command torques 𝑢𝑐
. The
network outputs the estimated actuator faults with dimensions 1 × 𝑁,
where 𝑁 = 6 represents the complete fault information vector: 3-axis es-
. As illustrated in
timated eﬀectiveness loss ̂𝑒𝑙 and additive bias faults ̂𝑢𝑎
Fig. 6, we adopt the similar architecture in [32] and enhance the atten-
tion layer with a convolutional block attention module (CBAM) to im-
prove estimation accuracy. Speciﬁcally, in the feature extraction phase,
a bidirectional LSTM structure (implemented by 𝑛𝑛.𝐿𝑆𝑇 𝑀) is adopted,
with an input dimension of 6 (𝑖𝑛𝑝𝑢𝑡_𝑠𝑖𝑧𝑒 = 6) and a hidden layer dimen-
sion set to 128 (ℎ𝑖𝑑𝑑𝑒𝑛_𝑠𝑖𝑧𝑒 = 128). Due to the enabled bidirectional
mode (𝑏𝑖𝑑𝑖𝑟𝑒𝑐𝑡𝑖𝑜𝑛𝑎𝑙 = 𝑇 𝑟𝑢𝑒), the output feature dimension of the LSTM
doubles to 256, forming a time-series feature matrix with the shape
[𝐵, 𝐿, 256], where 𝐵 is the batch size and 𝐿 is the look-back window
size. The attention enhancement layer is the core improvement point of
this model, implementing a lightweight CBAM attention module, and its
workﬂow is divided into two sub-modules: the channel attention mod-
ule and the spatial attention module. This CBAM attention mechanism
eﬀectively identiﬁes critical time steps as well as important spatial and
channel-wise features within the temporal sequences via channel and
spatial attention layers. After dimension conversion and mean opera-
tion, the output of the attention module is concatenated with the output
of the LSTM to form a feature vector of [𝐵, 512]. This design not only
retains the global information of the time series but also incorporates
local key features. In the output phase, the fully connected layer maps
the 512-dimensional features to a 6-dimensional output. These output
features pass through an activation layer, and ﬁnally, they are concate-
nated into an output tensor of [𝐵, 1, 6].

where 𝑓 = −𝐸𝑢𝑐 + 𝑢𝑎 denotes the total eﬀect of actuator faults on the
spacecraft dynamics system.

2 The constraint criterion diﬀers from Eq. 8 (𝜔𝑡𝑟𝑎𝑐𝑘𝑖𝑛𝑔 ≪ 𝜔max

latter is designed to ensure stable tracking.

), because the

4.2.  Safe reinforcement learning for tracking

4.2.1.  Constrained markov decision process

As done in the most safe reinforcement learning applications [40,41],
the interaction between the agile satellite agent and tracking environ-
ment is regarded as a Constraint Markov Decision Process [6]. A tuple

5

W. Lu, H. Zhuang, Z. Geng et al.

Aerospace Science and Technology 168 (2026) 111238

Fig. 5. Input and output of Neural Network.

𝑀 = (𝑆, 𝐴, 𝑝, 𝑟, 𝑐, 𝑑𝑐𝑜𝑠𝑡, 𝛾) denotes a CMDP, where 𝑆 is the state space, 𝐴
is the action space, 𝑝 is the state transition probability: 𝑆 × 𝐴 × 𝑆′ ⟹ 𝑅
represents the transition from state 𝑆 to new state 𝑆′ after executing ac-
tion 𝐴, 𝑟 ∈ [𝑟min, 𝑟max] is the reward after taking action, 𝑐 ∈ [𝑐min, 𝑐max]
is the cost after taking action, 𝑑𝑐𝑜𝑠𝑡 is given safety threshold, deﬁning
the maximum allowable cumulative cost, and 𝛾 ∈ [0, 1) is the discount
factor balancing the trade-oﬀ between immediate and future rewards.

The process unfolds as follows: At each discrete time step, the agent
observes the current state 𝑠 ∈ 𝑆. Based on 𝑆, the agent selects an action
𝑎 ∈ 𝐴. The environment transitions to a new state 𝑆′ ∈ 𝑆 according to
the probability distribution 𝑝. The agent receives a reward 𝑟(𝑆, 𝐴, 𝑆′) and
a cost 𝑐(𝑆, 𝐴, 𝑆′). This process repeats until a terminal state is reached.
In a Constrained Markov Decision Process, the policy optimization ob-
jective and safety constraints are deﬁned as follows:

max
𝜋

𝔼𝜏∼𝜋

s.t. 𝔼𝜏∼𝜋

[ ∞
∑

𝑡=0
[ ∞
∑

𝑡=0

]

𝛾 𝑡𝑟(𝑠𝑡, 𝑎𝑡, 𝑠𝑡+1)

]
𝛾 𝑡𝑐(𝑠𝑡, 𝑎𝑡, 𝑠𝑡+1)

≤ 𝑑𝑐𝑜𝑠𝑡

(18)

4.2.2.  Worst-case SAC

To deal with the randomness in long-term costs, the worst-case soft
actor-critic (WCSAC) algorithm [7] is applied by depicting the long-term
costs with its current cost returns and variance via replacing the origi-
nal single-output safety critic with a distributional-output critic. Specif-
ically, as done in [7,42], the distributional critic is approximated with
a Gaussian distribution.

𝐶𝜋 ∼ 𝑁(𝑄𝑐

𝜋 (𝑠, 𝑎), 𝑉 𝑐

𝜋 (𝑠, 𝑎))

(19)

where 𝑄𝑐

𝜋 and 𝑉 𝑐

𝜋  represents the mean and variance of this distribution:

Fig. 6. Neural Network Architecture.

𝜋 (𝑠, 𝑎) = 𝑐2 − 𝑄𝑐
𝑉 𝑐

𝜋(𝑠, 𝑎)2
∑
𝑝(𝑠′

+ 2𝛾𝑐

𝑠′∈𝑆
+ 𝛾 2 ∑
𝑠′∈𝑆
+ 𝛾 2 ∑
𝑠′∈𝑆

𝑝(𝑠′

𝑝(𝑠′

|𝑠, 𝑎)

|𝑠, 𝑎)

∑

𝑎′∈𝐴
∑

𝑎′∈𝐴
∑

𝑎′∈𝐴

|𝑠, 𝑎)

𝜋(𝑎′

|𝑠′)𝑄𝑐

𝜋 (𝑠′, 𝑎′)

𝜋(𝑎′

|𝑠′)𝑉 𝑐

𝜋 (𝑠′, 𝑎′)

(21)

𝜋(𝑎′

|𝑠′)𝑄𝑐

𝜋(𝑠′, 𝑎′)

𝑄𝑐

𝜋(𝑠, 𝑎) = 𝑐 + 𝛾

∑

𝑠′∈𝑆

𝑝(𝑠′

|𝑠, 𝑎)

∑

𝑎′∈𝐴

𝜋(𝑎′

|𝑠′)𝑄𝑐

𝜋 (𝑠′, 𝑎′)

(20)

Then the parameters of the safety critic network are updated via
gradient descent using the following equation, which incorporates the

6

W. Lu, H. Zhuang, Z. Geng et al.

Temporal Diﬀerence (TD) error:

Aerospace Science and Technology 168 (2026) 111238

where:

2

𝑡𝑟𝑎𝑐𝑒(𝑉

𝐿𝑉 (𝜂) =

𝜋,𝜂(𝑠′, 𝑎′)

𝜋,𝜇(𝑠′, 𝑎′)||

𝑐
𝜋,𝜂(𝑠′, 𝑎′) + 𝑉 𝑐

𝐸
(𝑠𝑡,𝑎𝑡)∼𝑝𝜋
𝐸
(𝑠𝑡,𝑎𝑡)∼𝑝𝜋

𝐿safety  critic(𝜇, 𝜂) = 𝐿𝑄(𝜇) + 𝐿𝑉 (𝜂)
𝑐
𝜋,𝜇(𝑠′, 𝑎′) − 𝑄𝑐
||𝑄
𝐿𝑄(𝜇) =

⎧
⎪
⎪
⎪
⎨
⎪
⎪
⎪
⎩
where 𝐿𝑄(𝜇) and 𝐿𝑉 (𝜂) represent the TD errors loss function for the
safety critic’s mean 𝑄𝑐
, respectively. Here, 𝜇 and
𝜂 denote the trainable parameters of the respective neural networks,
while the overline notation means the target value used in the TD error
computation.

𝑝𝑖,𝜇 and variance 𝑉 𝑐

𝑐
𝜋,𝜂(𝑠′, 𝑎′)𝑉 𝑐

𝜋,𝜂(𝑠′, 𝑎′)

𝜋,𝜂(𝑠′, 𝑎′)

− 2(𝑉 𝑐

(22)

1
2 𝑉

1
2 )

1
2 )

𝑝𝑖,𝜂

As for the actor network, the action is decided by taking the new

safety measure Γ𝜋 (𝑠, 𝑎, 𝛼) into account to ensure safe exploration.
√

Γ𝜋 (𝑠, 𝑎, 𝛼) = 𝑄𝑐

𝜋(𝑠, 𝑎) +

𝜙(Φ(𝛼))

𝑉 𝑐
𝜋 (𝑠, 𝑎)

(23)

1
𝛼

where Γ𝜋(𝑠, 𝑎, 𝛼) is the new safety measure under risk level 𝛼 under the
distribution safety critic. The actor network should decide an action
which satisﬁes the safety requirement Γ𝜋 (𝑠, 𝑎, 𝛼) ≤ 𝑑.

The trainable parameter of the actor network is updated by minimiz-

ing the following equation:

𝛼,𝑘(𝑠𝑡, 𝑎𝑡)]

[𝛽 log(𝜋𝜃(𝑎𝑡|𝑠𝑡)) − 𝑋𝜋𝜃

𝐿actor(𝜃) =
𝑋𝜋𝜃

𝜋(𝑠, 𝑎) − 𝑘Γ𝜋 (𝑠, 𝑎, 𝛼)
𝜋(𝑠, 𝑎) − 𝑘(𝑄𝑐

𝐸
𝑠∼𝐷,𝑎∼𝜋𝜃
𝛼,𝑘(𝑠𝑡, 𝑎𝑡) = 𝑄𝑟
= 𝑄𝑟

⎧
⎪
⎪
⎨
⎪
1
⎪
𝛼
⎩
where 𝛽 represents the adaptive temperature weight in soft actor critic
[43,44] to balance exploration and exploitation, and 𝑘 represents the
adaptive safety cost weight similar in SACLag [45] and SACPID [46] to
balance safety and cost. Both of the above weight parameters can be
updated via gradient descent to achieve a better balance.

𝑉 𝑐
𝜋 (𝑠, 𝑎))

𝜋 (𝑠, 𝑎) +

𝜙(Φ(𝛼))

(24)

√

∇𝛽 𝐽 (𝛽) = 𝐸(−𝛽(𝑙𝑜𝑔𝜋(𝑎|𝑠) + 𝐻))
∇𝑘𝐽 (𝑘) = 𝐸(𝑘(𝑐𝑡𝑎𝑟𝑔𝑒𝑡 − Γ𝜋(𝑠, 𝑎, 𝛼)))
where 𝑐𝑡𝑎𝑟𝑔𝑒𝑡 denotes the cost target of WCSAC.

(25)

(26)

In a word, the WCSAC algorithm essentially constitutes a specialized
variant of SACLag, wherein the conventional single-output safety critic
network is superseded by a distributional alternative to improve the
estimation accuracy in long-term cost.

4.2.3.  Interaction between RL algorithm and environment

In the context of agile satellite-based space target tracking, the ag-
ile satellite is required to continuously track a moving non-cooperative
space target while ensuring that its attitude maneuver does not violate
forbidden orientation zones. In addition, angular velocity is subject to
operational limitations, and actuator faults may occur during operation.
The interaction loop between the RL agent and the environment is illus-
trated in Fig. 7. At each decision step, the RL agent (based on a worst-
case Soft Actor-Critic algorithm) receives the current state of the sys-
tem, which includes target and forbidden zone orientation quaternion
errors, measured angular velocity, and estimated actuator fault infor-
mation. Based on this input, the agent outputs a command torque as the
action. This action is executed on the satellite dynamics, which consid-
ers both system disturbances and actuator faults, including eﬀectiveness
loss and additive bias. The updated satellite attitude and angular veloc-
ity are used to compute the new state, reward, and cost, which are then
fed back to the RL agent for policy updates.

State Space: The state vector 𝑠 ∈  encompasses a comprehensive
description of the satellite’s current attitude information and actuator
faults, enabling eﬀective policy learning under operation constraints
(attitude and angular velocity constraints) and actuator faults (eﬀec-
tiveness loss and additive bias). The state is deﬁned as:

𝑠 =

[
𝑄𝑇 ,𝑒, 𝑄𝑍1,𝑒, ⋯ , 𝑄𝑍𝑁 ,𝑒, 𝜔𝑚, ̂𝑒𝑙, ̂𝑢𝑎

]

(27)

7

• 𝑄𝑇 ,𝑒 = [𝑞𝑇 ,𝑒
1

, 𝑞𝑇 ,𝑒
2

, 𝑞𝑇 ,𝑒
3

, 𝑞𝑇 ,𝑒
4

]𝑇 : Error quaternion between the current

1

, 𝑞𝑍𝑖,𝑒
3

, 𝑞𝑍𝑖,𝑒
2

• 𝑄𝑍𝑖,𝑒 = [𝑞𝑍𝑖,𝑒

satellite attitude and the target pointing direction.
, 𝑞𝑍𝑖,𝑒
4

]𝑇 : Error quaternions between the satel-
lite attitude and the 𝑖-th forbidden zone orientation, for 𝑖 = 1, … , 𝑁,
where 𝑁 denotes the number of forbidden zones.
• 𝜔𝑚: Measured angular velocity vector of the satellite.
• ̂𝑒𝑙

: Estimated actuator eﬀectiveness loss vector from the fault identi-

• ̂𝑢𝑎

: Estimated actuator additive bias from the fault identiﬁcation

ﬁcation stage.

stage.

Our state representation adopts a uniﬁed error quaternion formu-
lation that inherently encodes the relative geometric relationships be-
tween the spacecraft’s attitude, target positions, and forbidden zones,
enabling the agent to simultaneously optimize tracking performance
while maintaining safety constraints and compensating for actuator
degradation in a generalized manner. This error quaternion-based state
representation fundamentally decouples the control policy from speciﬁc
orbital conﬁgurations and improves generalization capabilities, allow-
ing consistent performance across varying mission scenarios - when tar-
get locations shift due to orbital mechanics, when new forbidden zones
are introduced operationally, or when actuator performance degrades
mid-mission.

Action Space: The action space 𝑎 ∈  is deﬁned as the commanded
control torque applied to the satellite body, subject to actuator con-
straints. That is:
𝑎 = 𝜏𝑐 ∈ ℝ3
where 𝜏𝑐 denotes the 3-axis command torque output by the agent. In
the presence of actuator faults, the actual torque executed by the satel-
lite diﬀers due to loss of eﬀectiveness and additive bias, modeled in the
environment dynamics. In addition, by deﬁning this torque bound in
the RL framework, the control strategy ensures that the resulting con-
trol signals always respect the physical torque constraint (as shown in
Eq. 12).

(28)

Reward Function: The control objective is twofold: to minimize the
attitude error relative to the target–driving the target error quaternion
𝑄𝑇 ,𝑒 toward [0, 0, 0, 1]𝑇 –and to maximize the deviation from forbidden
pointing directions by ensuring the forbidden zone error quaternion
𝑄𝑍𝑖,𝑒 remains suﬃciently far from [0, 0, 0, 1]𝑇 . The reward function is
designed to guide the agent toward achieving accurate and stable target
tracking. It includes multiple components:

𝑟𝑠𝑢𝑚 = 𝑘1 ⋅ 𝑟𝑚𝑎𝑛𝑒𝑢𝑣𝑒𝑟 + 𝑘2 ⋅ 𝑟𝑡𝑟𝑎𝑐𝑘 + 𝑘3 ⋅ 𝑟𝑠𝑡𝑎𝑏𝑖𝑙𝑖𝑡𝑦 + 𝑘4 ⋅ 𝑟𝑠𝑎𝑓 𝑒𝑡𝑦
, and 𝑘4 represent the weights assigned to each individ-
where 𝑘1
ual reward, respectively, and the subscripts denote the speciﬁc reward
components:

, 𝑘2

, 𝑘3

(29)

{

{

𝑟track =

𝑟stability =

𝑟maneuver = 𝑞𝑒
4

if target in the FOV

9,
0, otherwise
{

⎧
⎪
⎪
⎪
⎪
⎪
⎨
⎪
⎪
⎪
⎪
⎪
⎩
• Maneuver Reward (𝑟maneuver): This term uses the scalar part 𝑞𝑒

if𝜔𝑖 > 𝜔𝑡𝑟𝑎𝑐𝑘𝑖𝑛𝑔, ∀𝜔𝑖 ∈ [𝜔𝑥, 𝜔𝑦, 𝜔𝑧]
otherwise

−(|𝜔𝑥| + |𝜔𝑦| + |𝜔𝑧|),
0,

if target in the FOV
otherwise

4 of
the attitude error quaternion 𝑄𝑇 ,𝑒 to encourage alignment between
the satellite’s sightline and the target direction. A larger 𝑞𝑒
4 implies
better alignment, hence a higher reward.

𝑟safety =

−15,

(30)

0,

• Tracking Reward (𝑟track): A discrete reward of 9 is provided when
the target is successfully located within the onboard payload’s ﬁeld-
of-view, thereby indicating the satellite has achieved a valid tracking
status. Otherwise, this term returns zero.

W. Lu, H. Zhuang, Z. Geng et al.

Aerospace Science and Technology 168 (2026) 111238

Fig. 7. Interaction between RL algorithm and Environment.

• Stability Reward (𝑟stability): This penalty term discourages high an-
gular velocity magnitudes during tracking. Excessive rotational rates
may destabilize tracking; hence, the total angular velocity is penal-
ized when the target is being tracked.

• Safety Penalty (𝑟safety): This hard penalty is triggered when any
angular velocity component exceeds a predeﬁned safety threshold,
which could otherwise cause mechanical damage or loss of payload
integrity.

Cost Function: The cost function is designed to quantify safety vi-
olations during the satellite’s tracking maneuvers, particularly in terms
of forbidden zone avoidance and angular velocity constraints. The total
cost 𝑐 at each step is expressed as:

𝑐 = 𝑐attitude + 𝑐𝜔
where the two components are deﬁned as:
𝑐attitude = ∑𝑁
𝑖=1 𝑐𝑎𝑡𝑡𝑖𝑡𝑢𝑑𝑒,𝑖
{
if
1,
‖𝜔‖
0, otherwise

⎧
⎪
⎨
⎪
⎩
The terms are deﬁned as:

≤ 𝜔𝑚𝑎𝑥

𝑐𝜔 =

(31)

(32)

• Attitude Constraint Cost (𝑐attitude): This component penalizes vio-
lations of forbidden orientation zones. For each forbidden zone 𝑖, the
satellite checks whether the zone lies within the payload’s ﬁeld-of-
view, as illustrated in Eq. 9. A discrete cost of 1 is incurred if the 𝑖-th
forbidden zone constraint was violated:

𝑐𝑎𝑡𝑡𝑖𝑡𝑢𝑑𝑒,𝑖 =

1,

if arccos

( ⃖⃖⃖⃖⃖⃖⃗𝑆𝜁𝑓 ,𝑖⋅ ̂𝑧

)

‖⃖⃖⃖⃖⃖⃖⃗𝑆𝜁𝑓 ,𝑖‖⋅‖ ̂𝑧‖

≤ 𝜃𝑓 𝑜𝑟𝑏𝑖𝑑𝑑𝑒𝑛

0, otherwise

⎧
⎪
⎨
⎪
⎩

(33)

• Angular Velocity Cost (𝑐𝜔): A discrete cost of 1 is incurred if any
component of the angular velocity vector exceeds the predeﬁned an-
gular velocity threshold, as illustrated in Eq. 11. A discrete cost of 1
is returned if 𝜔𝑖 > 𝜔max, ∀𝜔𝑖 ∈ [𝜔𝑥, 𝜔𝑦, 𝜔𝑧].

4.3.  Pseudo-code

The learning and deployment process of the proposed safe reinforce-
ment learning framework for non-cooperative space target tracking is

8

summarized in Algorithm 1. The training phase achieves comprehensive
trajectories by randomly generating initial pose conditions and fault sce-
narios. Interaction trajectories are sampled using a replay buﬀer strategy
with a length of 106. During training, the agile satellite agent learns to
track the moving target while respecting safety constraints under vari-
ous actuator fault conditions. The agent receives full fault information
during training to encourage fault-tolerant behavior. In contrast, during
testing, actuator faults are estimated through a pre-trained fault iden-
tiﬁcation network, and the agent makes decisions based on estimated
faults.

At each timestep, the agent observes the current state, which in-
cludes tracking errors, forbidden zone orientation errors, measured an-
gular velocity, and fault information. The agent outputs a control torque
command based on the policy learned using a worst-case Soft Actor-
Critic algorithm. The environment simulates actuator-impaired satellite
dynamics, and returns both a reward signal and a safety cost. These
experience tuples are stored in a replay buﬀer to improve sample eﬃ-
ciency. The actor and critic networks are updated periodically based on
a mini-batch sampled from the buﬀer. Both reward and cost critics are
updated using temporal-diﬀerence learning, and the temperature and
cost weights are also updated via gradient descent, thus ensuring safety
during policy learning.

5.  Experiment

5.1.  Implementation conﬁguration & scenario simulation

The  computational  experiments  were  performed  on  a  high-
performance computing platform featuring an AMD EPYC 7453 CPU and
NVIDIA RTX 4090 GPU, running the Ubuntu 22.04 operating system.
The software environment comprised PyTorch 2.2.2 [47] with CUDA
12.3 acceleration, complemented by Omnisafe reinforcement learning
package [48] and Python 3.11.8 interpreter. Considering the lightweight
requirements for spaceborne missions, both the neural network for WC-
SAC used in safe attitude control and the neural network for fault diag-
nosis and identiﬁcation were trained within a few hours–a reasonable
timeframe for intelligent spacecraft system.

The target tracking simulation environment was developed using
Omnisafe’s Constrained Markov Decision Process interface, providing
a standardized framework for safe reinforcement learning research. In

W. Lu, H. Zhuang, Z. Geng et al.

Aerospace Science and Technology 168 (2026) 111238

Algorithm 1: Safe RL Framework for Target Tracking.
1 if Mode == ’train’ then
2

Randomly initialize the quaternion 𝑄𝑖𝑛𝑖𝑡 and angular
velocity 𝜔𝑖𝑛𝑖𝑡 of the satellite agent;
Randomly initialize the values of actuator faults.;
# No fault estimation in training; true faults are directly
available ;
;
̂𝑒𝑙 ← 𝑒𝑙
̂𝑢𝑎 ← 𝑢𝑎

;

7 else if Mode == ’test’ then
8

Initialize the pre-deﬁned quaternion 𝑄𝑖𝑛𝑖𝑡 and angular
velocity 𝜔𝑖𝑛𝑖𝑡 of the satellite agent based on METADATA;
Initialize the pre-deﬁned values of actuator faults based on
METADATA.;
# Fault Identiﬁcation via pre-trained neural network ;
Apply nominal torque input 𝑢𝑐
( ̂𝑒𝑙, ̂𝑢𝑎) ← Network(Φ, 𝑢𝑐 );

;

13 Receive initial state 𝑠1
14 for 𝑡 = 1 to Terminal timestep do
15

;

Choose action 𝑎𝑡 based on RL algorithm;
Receive reward 𝑟 and cost 𝑐 based on reward and cost
function;
update the attitude of satellite agent based on Eq. (13).;
Collect attitude and fault information to compose a new
state 𝑠𝑡+1
Store (𝑠𝑡, 𝑎𝑡, 𝑟𝑡, 𝑐𝑡, 𝑠𝑡+1) in Replay Buﬀer;
𝑠𝑡 ⟵ 𝑠𝑡+1

;

21 if update interval reached then
22

Randomly select a batch of transitions
{𝑠𝑖, 𝑎𝑖, 𝑟𝑖, 𝑐𝑖, 𝑠𝑖+1}𝑖=1,2,…,𝑁  from Replay Buﬀer.
Update reward critic and cost critic using TD targets;
Update actor network via policy gradient;
Update the temperature weight 𝛽 and safety cost weight 𝑘.

3

4

5

6

9

10

11

12

16

17

18

19

20

23

24

25

Fig. 8. Non-cooperative Space Target Tracking Scenario.

Table 1
Stage duration.
 Stage
 Fault Identiﬁcation
 Attitude Adjustment & Target Tracking  1 Oct 2024 18:50:00.000 - 18:59:00.000 (540s)

 Duration
 1 Oct 2024 18:59:57.000 - 18:50:00.000 (3s)

our approach, the constraints are primarily implemented as soft con-
straints through adjustable penalty terms in the cost function, which
allows the agent policy to learn constraint satisfaction while maintain-
ing reward optimization. As shown in Table 1, each experimental trial
followed a structured timeline: an initial 3-second phase dedicated to
fault identiﬁcation and parameter estimation, followed by a 540-second
operational period for attitude maneuver execution and target track-
ing. The time step for fault identiﬁcation and attitude control is set to
0.1s and 1s, respectively. Fig. 8 illustrates the non-cooperative space
target tracking scenario from 2d and 3d aspects, respectively. The Imag-
ingSat (satellite agent) should continuously track the TargetSat (space
target) while ensuring the operation constraints and compensating actu-
ator faults. The spacecraft attitude dynamics are numerically integrated
using a 4th-order Runge-Kutta (RK4) method. Speciﬁcally, the track-
ing scenario has four forbidden zones for testing attitude constraints,
including one stable forbidden zone (Sun) and three dynamic forbid-
den zones (ForbiddenSat). During each timestep iteration (i.e., at every
step() call of the reinforcement learning environment), the RL environ-
ment performs comprehensive operation constraint checking. All orbital
elements and ephemeris data are computed using professional Systems

Fig. 9. Nominal torques during fault identiﬁcation stage.

Tool Kit software based on their orbital elements. The detailed orbit
elements of satellites in the tracking scenario are shown in Table 2.

Fig. 9 illustrates the detailed nominal torques during the fault iden-
tiﬁcation stage. The layers of the neural network architecture used for
identiﬁcation are implemented by Torch [47]. The spacecraft’s dynam-
ics parameters, including the inertia matrix 𝐽 and total disturbance
torques 𝑑, as well as the measurement noise of angular velocity, are
deﬁned as follows:

𝐽 =

10
0.02
0.01

⎡
⎢
⎢
⎣

0.02
15
−0.01

0.01
−0.01
20

⎤
⎥
⎥
⎦

𝑘𝑔 ⋅ 𝑚2

9

(34)

W. Lu, H. Zhuang, Z. Geng et al.

Aerospace Science and Technology 168 (2026) 111238

Table 2
Orbit elements of satellites.

 Orbit Elements

Satellites

 ImagingSat
 TargetSat
 ForbiddenSat1
 ForbiddenSat2
 ForbiddenSat3

 Semimajor axis(km)
 6900
 6785
 6511
 7321
 6421.1

 Eccentricity
 0
 0.0169
 5.0e-15
 0.013
 4.9e-15

 Inclination(deg)
 96
 150
 35
 62
 77

 Argument of Perigee(deg)
 150
 45
 0
 9.5e-12
 0

 RAAN(deg)
 30
 40
 255
 252
 19

 True Anomaly(deg)
 7
 0
 210
 312
 98

Fig. 10. Episode Curves of WCSAC during Training.

Satellite Agent

WCSAC

Fig. 11. Desired Quaternion Calculated by Eq. 6.

Table 3
Parameter Conﬁguration.
 Parameter

 Value
 command torque range
[−0.5, 0.5] Nm
 eﬀectiveness loss
 rand([0, 1])
 additive bias
 rand([−0.15, 0.15]) Nm
 max angular velocity for tracking
𝜋∕12 rand/s
 max angular velocity for constraint
𝜋∕10 rand/s
 10 deg
 payload half angle for tracking 𝜃𝑡𝑟𝑎𝑐𝑘𝑖𝑛𝑔
 payload half angle for constraint 𝜃𝑓 𝑜𝑟𝑏𝑖𝑑𝑑𝑒𝑛  25 deg
 safety threshold 𝑑𝑐𝑜𝑠𝑡
 discount factor 𝛾
 risk level 𝛼
𝑘1, 𝑘2, 𝑘3, 𝑘4
 initial value of weight 𝛼
 initial value of weight 𝑘
 learning rate
 replay buﬀer size
 total timesteps for training
 optimizer

 5
 0.99
 0.8
1, 1, 10, 1
 0.6931
 0.6931
 0.001
1 × 106
3 × 106
 Adam

𝑑 = 10−5

−10 + 4𝑠𝑖𝑛(3𝜔𝑡) + 3𝑐𝑜𝑠(10𝜔𝑡)
15 + 1.5𝑠𝑖𝑛(2𝜔𝑡) + cos(5𝜔𝑡)
10 + 3𝑠𝑖𝑛(10𝜔𝑡) + 8 sin(4𝜔𝑡)

⎡
⎢
⎢
⎣

𝑁𝑚

⎤
⎥
⎥
⎦

(35)

random signals, both with a mean of zero. The ﬁrst component has a
standard deviation of 0.1 % of the magnitude of 𝜔, while the second
component has a standard deviation of 0.01 % of the magnitude of the
previous 𝜔. Thus, the noise model can be expressed as:

𝜔𝑚 = 𝜔 + 𝜂𝑛𝑜𝑖𝑠𝑒
where the measurement noise component 𝜂𝑛𝑜𝑖𝑠𝑒 is a hybrid noise, similar
to the model presented in Ref. [32,49]. It consists of two independent

(36)

𝜂𝑛𝑜𝑖𝑠𝑒 = 𝜂𝑛𝑜𝑖𝑠𝑒,1 + 𝜂𝑛𝑜𝑖𝑠𝑒,2,
𝜂𝑛𝑜𝑖𝑠𝑒,1 ∼  (𝜇 = 0, 𝜎2 = (0.001|𝜔|)2),
𝜂𝑛𝑜𝑖𝑠𝑒,2 ∼  (𝜇 = 0, 𝜎2 = (0.0001|𝜔old|)2)

⎧
⎪
⎨
⎪
⎩

(37)

10

W. Lu, H. Zhuang, Z. Geng et al.

Aerospace Science and Technology 168 (2026) 111238

Fig. 12. Dynamics responses illustration (Case 1).

Fig. 13. Dynamics responses illustration (Case 2).

Table 4
Initial attitude information and actuator faults in ﬁve testing cases.

Testing Case

 Case 1
 Case 2
 Case 3
 Case 4
 Case 5

 Initial Attitude Information
 Initial Quaternion
[0.4611, 0.2515, 0.2774, 0.8044]𝑇
[0.3003, −0.3849, 0.2489, 0.8364]𝑇
[0.3320, −0.4676, −0.1528, 0.8047]𝑇
[0.3778, 0.2672, −0.3498, 0.8145]𝑇
[0.1584, 0.3066, 0.3303, 0.8784]𝑇

 Initial Angular Velocity(rand/s)
[−0.0290, −0.0268, 0.0231]𝑇
[−0.014, 0.0248, −0.0147]𝑇
[0.0286, −0.0245, −0.0180]𝑇
[0.0222, −0.0134, 0.0216]𝑇
[−0.0132, −0.0158, 0.0112]𝑇

 Initial Actuator Faults
 Eﬀectiveness Loss
[0.51, 0.32, 0.43]𝑇
[0.31, 0.42, 0.63]𝑇
[0.32, 0.38, 0.45]𝑇
[0.61, 0.51, 0.48]𝑇
[0.33, 0.67, 0.63]𝑇

 Additive Bias(Nm)
[0.13, −0.09, 0.04]𝑇
[−0.07, 0.06, 0.14]𝑇
[0.08, 0.12, −0.06]𝑇
[0.09, −0.13, −0.06]𝑇
[−0.04, −0.05, 0.07]𝑇

11

W. Lu, H. Zhuang, Z. Geng et al.

Aerospace Science and Technology 168 (2026) 111238

Fig. 14. Dynamics responses illustration (Case 3).

Fig. 15. Dynamics responses illustration (Case 4).

In addition, simulation parameters in this paper and algorithm pa-

rameters of WCSAC are illustrated in Table 3.

under various actuator fault scenarios and ablation experiments to val-
idate the proposed components.

5.2.  Comparison experiment

To validate the eﬀectiveness and safety of the proposed fault-tolerant
reinforcement learning framework for space target tracking, we conduct
a series of comparison experiments against several baseline algorithms

12

5.2.1.  Comparison methods

Speciﬁcally, we compare our method with the following representa-

tive algorithms:
• SAC [43,44]: The vanilla Soft Actor-Critic algorithm without any
safety mechanism or fault awareness. Serves as a baseline for per-
formance.

W. Lu, H. Zhuang, Z. Geng et al.

Aerospace Science and Technology 168 (2026) 111238

Fig. 16. Dynamics responses illustration (Case 5).

• SACLag  [45]:  SAC  with  a  Lagrangian-based  constraint  handling
mechanism that introduces a cost critic and a cost penalty multiplier
to enforce safety constraints during learning.

• SACPID [46]: Improved version of SACLag, where a proportional-
integral-derivative (PID) controller updates the lagrangian multi-
plier.

• TD3PID [46]: Improved version of TD3Lag, where a proportional-
integral-derivative controller updates the lagrangian multiplier.
• Reward Penalty (RP): A reward-shaping method that introduces
penalties in the reward function when safety violations (e.g., forbid-
den zone violations or excessive angular velocity) occur.

𝑟𝑅𝑃 = 𝑟 − 𝜆𝑅𝑃 ⋅ 𝑐
where 𝑟𝑅𝑃  denotes the returned reward of each timestep after the
reward penalty operation, 𝑟 and 𝑐 represent the original reward and
cost mentioned above, respectively, and 𝜆𝑅𝑃 = 5 is the cost weight.

(38)

Regarding test case selection, ﬁve primary cases were systemat-
ically  chosen  to  cover  the  complete  spectrum  of  anticipated  oper-
ating conditions. These cases aim to represent: 1) arbitrary satellite
attitudes, 2) arbitrary spacecraft angular velocities, and 3) arbitrary ac-
tuator faults (including eﬀectiveness loss 𝑒𝑙 ∈ [0, 1] and additional bias
𝑢𝑎 ∈ [−0.15, 0.15]𝑁𝑚). As listed in Table 4, the selection process consid-
ered all critical operational parameters, including satellite attitude con-
ditions and potential fault combinations. The training and evaluation
hyperparameters are kept consistent across all methods for fair compar-
ison.

5.2.2.  Performance analysis

Fig. 10 illustrates the evolution of episode reward, cost, actor loss
and critic loss during WCSAC training. In each subﬁgure, the light -
colored area represents the range between the maximum and mini-
mum values of the corresponding metric across multiple training pro-
cesses, which are determined by diﬀerent random seeds. Meanwhile, the
dark - colored line denotes the average value of that metric. As shown
in Fig. 10(a), the episode reward experiences a rapid increase in the
early training phase, followed by convergence and stabilization around

a high reward value (>=5000). This indicates that the agent quickly
learns an eﬀective control policy for target tracking under constraints
and begins to consistently achieve high returns. Furthermore, Fig. 10(b)
presents the episode cost curves, which reﬂect the number of speciﬁc
constraint violations as shown in Eq. 31 (e.g., forbidden zone violations,
actuator limit breaches). Initially, the cost values are high and ﬂuctuate
signiﬁcantly, reﬂecting frequent violations of safety constraints during
early attitude control exploration. However, as training progresses, the
episode cost markedly decreases, approaching zero in many episodes.
Although occasional spikes in cost still occur after convergence, these
are sparse and typically correspond to rare constraint violations due to
the balancing operation between eﬀective mission execution and safety
operation. In Fig. 10(c), the average actor loss drops sharply at ﬁrst
and then maintains stability, which implies the actor network gradu-
ally optimizes its policy. In Fig. 10(d), the average critic loss also shows
a decreasing trend and becomes stable eventually, meaning the critic
network accurately evaluates the rewards of actions to support policy
learning.

Fig. 11 illustrates the desired quaternion for tracking calculated by
Eq. 6. We adopt multiple quantitative metrics to evaluate both mission
reward and safety compliance, as well as the tracking performance of
the comparison algorithms:

• Reward: The accumulated reward over one testing trajectory.
• Cost: The accumulated cost over one testing trajectory, including the
cost of violating attitude constraint and angular velocity constraint.
• Reduction: Percentage reduction in constraint violations compared

to baseline method (SAC).

• Tracking Time: The duration of time steps during which the target

remains within the ﬁeld-of-view of the satellite payload.

As shown in Table 5, we recorded all metrics in ﬁve testing cases
with diﬀerent initial conditions and actor faults, as well as the average
performance across all cases. SAC achieves a relatively high average re-
ward, but it incurs a large cost due to the omission of safety constraints,
indicating poor safety compliance. SACLag slightly reduces the cost by
introducing a Lagrangian-based optimization style, but at the expense of
lower tracking reward. SACPID and TD3PID also suﬀer from degraded

13

W. Lu, H. Zhuang, Z. Geng et al.

Aerospace Science and Technology 168 (2026) 111238

Fig. 17. Tracking performance illustration across ﬁve testing cases.

14

W. Lu, H. Zhuang, Z. Geng et al.

Aerospace Science and Technology 168 (2026) 111238

e
m
i
 T

n
o
i
t
c
u
d
e
 R

t
s
o
 C

d
r
a
w
e
 R

e
m
i
 T

n
o
i
t
c
u
d
e
 R

t
s
o
 C

d
r
a
w
e
 R

e
m
i
 T

n
o
i
t
c
u
d
e
 R

t
s
o
 C

d
r
a
w
e
 R

e
m
i
 T

n
o
i
t
c
u
d
e
 R

t
s
o
 C

d
r
a
w
e
 R

e
m
i
 T

n
o
i
t
c
u
d
e
 R

t
s
o
 C

d
r
a
w
e
 R

e
m
i
 T

n
o
i
t
c
u
d
e
 R

t
s
o
 C

d
r
a
w
e
 R

e
g
a
r
e
v
 A

5

e
s
a
 C

4

e
s
a
 C

3

e
s
a
 C

2

e
s
a
 C

1

e
s
a
 C

m
h
t
i
r
o
g
l
A

.
s

m
h
t
i
r
o
g
l
A
n
o
s
i
r
a
p
m
o
C
f
o

e
c
n
a
m
r
o
f
r
e
P

5
e
l
b
a
T

.

.

.

4
3
2
 5

4
3
0
 5

8
6
9
 4

2
8
6
 2

8
3
2
 5

.

.

.

8
3
2
5

%
2
4
1
 9

%
5
9
1
 8

.

.

 6

 9

%
8
4
1
9

.

%

 –

.

2
4
 4

6
 2

.

4
0

.

 –

.

4
9
 6

.

1
9
9
4
2
2
5

.

.

5
6
6
9
1
0
 5

1
8
4
7
8
9
 4

7
0
2
9
6
8
 2

.

.

6
6
9
3
1
2
 5

 –

6
2
 5

8
2
 5

5
1
 5

9
0
 1

2
2
5

8
1
 5

%
2
5
1
 9

%
4
4
6
 8

.

.

 –

 –

%
0
0
 1

%
0
0
1

9
 5

 5

 8

 0

0

3
 8

.

4
0
2
1
5
2
5

.

.

7
4
1
9
4
2
 5

3
7
9
5
5
1
 5

7
6
6
0
7
3
 1

.

.

6
8
2
8
4
1
 5

 –

1
2
 5

2
1
 5

0
2
 5

8
5
 4

1
2
 5

1
2
5

%
8
5
3
 8

%
2
5
5
 9

.

.

%
9
4
 1

.

%
0
0
 1

%
0
0
1

 –

7
 6

1
 1

6
 6

 3

 0

0

.

.

4
7
5
6
0
2
 5

7
6
3
2
0
1
 5

5
9
1
0
0
2
5

.

.

8
1
9
5
8
5
 4

.

7
9
1
7
8
1
 5

 –

0
2
 5

9
3
 4

9
1
 5

3
 7

4
2
 5

7
2
5

%
8
7
0
 6

%
1
1
4
 9

.

.

%
0
0
 1

%
0
0
 1

%
0
0
1

 –

1
 5

0
 2

 0

 3

 0

0

.

.

7
6
6
7
8
1
 5

6
1
0
8
3
4
 4

8
6
7
7
8
1
 5

3
9
0
8
7
1
 1

.

.

 –

.

4
1
1
2
5
2
5

4
2
 5

2
1
 5

4
0
 4

6
2
 2

5
2
 5

7
2
5

%
0
0
 1

%
0
0
 1

%
0
0
 1

%
0
0
 1

%
0
0
1

 –

2
 9

 0

 0

 0

 0

0

.

.

0
6
9
2
2
2
 5

3
5
2
0
8
0
 5

5
3
5
4
3
1
 4

5
2
0
9
4
4
 2

.

.

 –

.

8
5
9
9
3
2
5

6
2
 5

6
2
 5

6
2
 5

5
7
 4

7
2
5

6
2
 5

%
5
0
2
 8

%
5
0
2
 8

%
3
5
1
 1

%
3
3
3
 8

%
3
4
7
9

.

.

.

.

.

 –

8
 7

4
 1

4
 1

9
 6

3
 1

2

.

.

4
5
5
6
5
2
 5

7
4
5
8
2
2
 5

7
3
9
8
5
2
5

.

.

2
3
3
2
6
7
 4

.

6
7
2
2
4
2
 5

 –

y
t
l
a
n
e
P
d
r
a
w
e
 R

g
a
L
C
A
 S

D
I
P
C
A
 S

D
I
P
3
D
 T

C
A
 S

C
A
S
C
 W

Table 6
Fault Identiﬁcation Performance of Comparison Methods.

Fault Identiﬁcation Method

 Least Squares Filter
 Gradient Descend
 Neural Network in [32]
 Neural Network in Fig. 6 (Ours)

 Estimation Error
 MSE
4.81 × 10−4
3.98 × 10−4
2.35 × 10−4
1.92 × 10−4

 MAE
1.26 × 10−2
1.09 × 10−2
7.39 × 10−3
6.43 × 10−3

Inference Time (s)

4.42 × 10−4
7.60 × 10−1
3.98 × 10−3
7.49 × 10−3

reward and unstable cost performance. The reward-penalty approach
achieves a relatively low average cost and high tracking time, but the
cost is still high in some cases 3 In contrast, the proposed WCSAC frame-
work achieves the best trade-oﬀ: it maintains a high average reward
while keeping the lowest average cost, and a stable tracking duration
across diﬀerent cases. This demonstrates that WCSAC eﬀectively bal-
ances safety and tracking performance under actuator faults, enabling
fault-tolerant attitude tracking with minimal manual intervention.

In addition, Figs. 12, 13, 14, 15, 16 and 17 present the dynamics
responses and tracking performance of the WCSAC-based agile satellite
agent under ﬁve representative testing cases, respectively. The curves in-
clude actual torque (inﬂuenced by actuator faults), the angular velocity,
and the current quaternion and error quaternion of the imaging satel-
lite. In all cases, the actual torque output and angular velocity exhibit
sharp transients at the beginning of the episode, reﬂecting the satellite’s
rapid attitude maneuvering toward the desired orientation. Once the
angle falls below the payload’s half angle (𝑎𝑛𝑔𝑙𝑒 < 𝜃𝑡𝑟𝑎𝑐𝑘𝑖𝑛𝑔 as shown in
Fig. 17), the target enters the sensor’s ﬁeld of view, and the satellite
transitions into a ﬁne-tuning phase. During this stage, both torque out-
put and angular velocity gradually stabilize. Minor ﬂuctuations are ob-
served intermittently, corresponding to the agent’s maneuvering actions
to avoid attitude constraints. Moreover, the convergence behavior of the
error quaternion supports this interpretation. Due to the reward func-
tion being designed to encourage tracking rather than strict convergence
to the speciﬁc quaternion [0, 0, 0, 1]𝑇  like traditional attitude control
problem [21,50], a small residual tracking error remains, which aligns
with the behavior shown in the plots. Furthermore, as shown in Fig. 17,
we also compare the tracking performance of vanilla SAC and WCSAC
across ﬁve cases, focusing on the angle between the payload sightline
and the target, as well as the angles to multiple forbidden zones. Tak-
ing Case 2 (subﬁg d,e) as an example, vanilla SAC frequently violates
attitude constraints due to its lack of constraint awareness. In contrast,
WCSAC eﬀectively maintains all forbidden zones outside the forbidden
) while keeping the target within
half-angle threshold (𝑎𝑛𝑔𝑙𝑒 > 𝜃𝑓 𝑜𝑟𝑏𝑖𝑑𝑑𝑒𝑛
the payload half-angle limit (𝑎𝑛𝑔𝑙𝑒 < 𝜃𝑡𝑟𝑎𝑐𝑘𝑖𝑛𝑔
). This ensures safe tracking
and allows the cumulative tracking time to increase steadily throughout
the episode, except during the initial large-angle maneuver and brief
constraint-avoidance events.

The performance illustrations indicate that the agent successfully
maintains continuous tracking performance on the space target across
diverse fault scenarios within LEO operational envelope, demonstrating
both agility and fault tolerance.

5.3.  Ablation experiment

In this subsection, we conduct ablation experiments to illustrate the
eﬀectiveness and eﬃciency of the proposed neural network-based fault
identiﬁcation method. Speciﬁcally, the satellite agent’s initial attitude,
angular velocity, and actuator faults are randomized to simulate di-
verse fault conditions. Three fault identiﬁcation methods–Least Squares
Filter, Gradient Descent, and the proposed Neural Network–are evalu-
ated in terms of estimation accuracy (measured by MSE and MAE) and

3 We don’t evaluate the reward term of reward penalty due to the correction

in Eq. 38.

15

W. Lu, H. Zhuang, Z. Geng et al.

Aerospace Science and Technology 168 (2026) 111238

e
m
i
 T

.

.

.

8
3
2
 5

2
4
0
 5

0
2
9
 2

8
7
8
 3

.

.

0
4
2
5

t
s
o
 C

4
0

.

.

8
2
6
 1

.

8
5
 3

.

8
3
 7

4
0

.

e
g
a
r
e
v
 A

d
r
a
w
e
 R

.

.

6
6
9
3
1
2
 5

0
8
7
6
2
0
 5

5
8
4
6
2
1
 3

8
7
9
8
9
9
 3

5
0
9
5
1
2
5

.

.

.

e
m
i
 T

8
1
5

t
s
o
 C

5

e
s
a
 C

d
r
a
w
e
 R

0

.

6
8
2
8
4
1
5

e
m
i
 T

1
2
5

t
s
o
 C

0

0
8
 4

2
1
 5

3
1
 5

8
1
5

7
 2

1
 3

 4

0

.

.

5
8
7
2
7
7
 4

0
7
1
5
9
0
 5

5
9
0
1
0
1
 5

6
6
6
7
4
1
 5

.

.

3
7
 4

0
6
 1

3
2
 4

2
2
5

 0

 0

 0

0

4

e
s
a
 C

d
r
a
w
e
 R

.

.

7
9
1
7
8
1
 5

8
8
7
9
5
7
 4

9
8
1
8
4
9
 1

1
8
4
7
7
2
 4

9
8
7
6
9
1
5

.

.

.

e
m
i
 T

7
2
5

t
s
o
 C

3

e
s
a
 C

d
r
a
w
e
 R

0

.

4
1
1
2
5
2
5

e
m
i
 T

7
2
5

1
2
 5

3
7
 1

5
2
 1

7
2
5

0
2
 3

7
4
 3

6
 7

0

.

.

8
1
3
4
9
1
 5

1
1
0
2
5
0
 2

8
2
1
0
6
7
 1

3
1
9
1
5
2
 5

.

.

2
2
 5

0
2
 5

6
2
 5

7
2
5

t
s
o
 C

2

e
s
a
 C

d
r
a
w
e
 R

1
4
 2

4
 7

3
 1

0

 0

.

.

8
5
9
9
3
2
 5

0
5
6
9
6
1
 5

0
1
5
0
7
1
 5

5
5
5
4
1
2
 5

3
7
1
0
4
2
5

.

.

.

e
m
i
 T

6
2
5

t
s
o
 C

2

5
2
 5

5
 9

2
5
 3

6
2
5

2
2
 2

 2

 5

2

1

e
s
a
 C

d
r
a
w
e
 R

n
o
i
t
a
m

i
t
s
E

t
n
e
r
e
ﬀ
D

i

.

.

6
7
2
2
4
2
 5

2
6
3
7
3
2
 5

5
4
5
6
6
3
 1

1
3
6
1
4
6
 3

7
8
9
2
4
2
5

.

.

.

 a

 b

 c

 d

 e

.

n
o
i
t
a
m

i
t
s
E

s
t
l
u
a
F

t
n
e
r
e
ﬀ
D

i

f
o

e
c
n
a
m
r
o
f
r
e
P

7
e
l
b
a
T

computational eﬃciency (measured by inference time). This experiment
is repeated over 5000 runs, and the averaged results are reported in Ta-
ble 6. As shown in the table, our proposed neural network architecture
achieves the lowest estimation error and relatively short inference time,
demonstrating both its accuracy and real-time suitability compared with
state-of-the-art FDI methods.

In addition, we further evaluate the impact of fault identiﬁcation
quality on the downstream reinforcement learning-based control in a
satellite tracking scenario. We consider ﬁve estimation conﬁgurations:
[a] neural network estimated faults ( ̂𝑒𝑙, ̂𝑢𝑎
), [b] none eﬀectiveness loss
and random additive bias, [c] random eﬀectiveness loss and non ad-
ditive bias, [d] random eﬀectiveness loss and random additive bias,
). As reported in Table 7, the neural
and [e] truth fault faults (𝑒𝑙, 𝑢𝑎
network-based estimation [a] yields a comparable performance to the
ideal condition [e] in terms of tracking reward, cost, and execution
time. In contrast, the conﬁgurations [b]–[d] relying on random or in-
complete fault assumptions lead to signiﬁcant degradation in control
performance, especially in terms of reward drop and increased maneu-
vering cost. This result conﬁrms that accurate and fast fault identiﬁca-
tion not only improves state estimation but also signiﬁcantly beneﬁts
the decision-making and task execution performance of reinforcement
learning-based control policies.

6.  Conclusion

This paper presents a fault-tolerant attitude control framework for an
agile satellite performing persistent tracking of non-cooperative space
targets under multiple operational constraints and potential actuator
faults. By decomposing the tracking mission into three distinct stages
and formulating the control task as a Constrained Markov Decision Pro-
cess, we systematically address complex real-world challenges, includ-
ing attitude forbidden zones, angular velocity limits, torque saturation,
and actuator faults. A data-driven fault identiﬁcation module is inte-
grated to detect both eﬀectiveness degradation and additive actuator
faults in real time, while a safe reinforcement learning algorithm is em-
ployed to learn robust and adaptive control policies that ensure safe,
continuous tracking. Extensive simulation results demonstrate that the
proposed method enables agile satellites to achieve accurate and stable
tracking performance while satisfying all critical constraints, even in the
presence of actuator anomalies. This work provides a promising foun-
dation for the deployment of intelligent, fault-tolerant tracking systems
in future autonomous space missions.

Regarding the limitations of this study, both fault identiﬁcation and
tracking experiments were conducted using simulation programs rather
than onboard hardware. Furthermore, the neural network requires pre-
trained prior knowledge, making it highly sensitive to system parameter
uncertainties. In future work, we will explore a reliable FDI algorithm
that does not require prior knowledge and test it on reaction wheels in
the laboratory to empower intelligent satellite applications. In addition,
we plan to extend the framework to more complex multi-target track-
ing scenarios and address generalization across varying forbidden zone
counts through network architectural modiﬁcations. Moreover, incorpo-
rating noise-aware decision-making and robust onboard autonomy will
further enhance the system’s resilience in noisy space environments.

CRediT authorship contribution statement

Wenlong Lu: Methodology, Investigation; Hongji Zhuang: Method-
ology, Investigation; Ziyao Geng: Methodology, Investigation; Qiang
Shen: Methodology, Investigation; Zhongcheng Mu: Resources; Shu-
fan Wu: Supervision, Funding acquisition; Vladimir Y. Razoumny:
Funding acquisition; Yury N. Razoumny: Funding acquisition.

Data availability

No data was used for the research described in the article.

16

W. Lu, H. Zhuang, Z. Geng et al.

Declaration of competing interest

The authors declare that they have no known competing ﬁnancial
interests or personal relationships that could have appeared to inﬂuence
the work reported in this paper.

Acknowledgments

This work was supported in part by the National Natural Science
Foundation of China under Grant U24B6014 and U24B20157, in part
by the RUDN University Scientiﬁc Projects Grant System under project
202235-2-000, and in part by the Oﬃce of Military and Civilian Inte-
gration Development Committee of Shanghai under project XTCX-kJ-
2022-24. The authors would like to thank the Associate Editor and re-
viewers for generously devoting their valuable time and eﬀort to review
the manuscript meticulously. Additionally, we sincerely acknowledge
the GPU computing power support provided by the Featurize platform
(https://featurize.cn/).

References

[1] B. Wang, S. Li, J. Mu, X. Hao, W. Zhu, J. Hu, Research advancements in key tech-
nologies for space-based situational awareness, Space: Sci. Technol. (2022).
[2] L.U. Wenlong, G. Ziyao, M.U. Zhongcheng, W.U. Shufan, N.R. Yury, et al., Optimiz-
ing spacecraft collision avoidance maneuvers under risk uncertainty from multiple
space debris, Chin. J. Aeronaut. (2025) 103814.

[3] C. Wang, L. Jiang, M. Li, X. Ren, Z. Wang, Slow-Spinning spacecraft cross-Range
scaling and attitude estimation based on sequential ISAR images, IEEE Trans.
Aerosp. Electron. Syst. 59 (6) (2023) 7469–7485. https://doi.org/10.1109/TAES.
2023.3291337

[4] H. Tang, C. Liu, J. Liu, P. Zhang, W. Hu, Real-time monocular 3D pose tracking
for non-cooperative spacecraft in close range, IEEE Trans. Instrum. Meas. (2025) 1.
https://doi.org/10.1109/TIM.2025.3568937

[5] X. Cao, N. Li, S. Qiu, C. Li, Research on the method of searching and tracking of
the time-sensitive target through the mega-constellation, Aerosp. Sci. Technol. 137
(2023) 108299.

[6] E. Altman, Constrained Markov decision processes, Routledge, 2021.
[7] Q. Yang, T.D. Simão, S.H. Tindemans, M.T.J. Spaan, WCSAC: Worst-case soft actor
critic for safety-constrained reinforcement learning, in: Proceedings of the AAAI
Conference on Artiﬁcial Intelligence, 35, 2021, pp. 10639–10646.

[8] D. Zhou, G. Sun, W. Lei, L. Wu, Space noncooperative object active tracking with
deep reinforcement learning, IEEE Trans. Aerosp. Electron. Syst. 58 (6) (2022)
4902–4916.

[9] Z. Yu, X. Su, G. Sun, Fractional order meta-Reinforcement learning for space non-
cooperative object active visual tracking, IEEE Trans. Aerosp. Electron. Syst. (2024).
[10] Y.-H. Wu, F. Han, M.-H. Zheng, F. Wang, B. Hua, Z.-M. Chen, Y.-H. Cheng, Attitude
tracking control for a space moving target with high dynamic performance using
hybrid actuator, Aerosp. Sci. Technol. 78 (2018) 102–117.

[11] W.U. Yunhua, M. Zheng, H.E. Wei, W. Feng, C. Zhiming, H. Bing, High precision
attitude dynamic tracking control of a moving space target, Chin. J. Aeronaut. 32
(10) (2019) 2324–2336.

[12] M. Zheng, Y. Wu, C. Li, Reinforcement learning strategy for spacecraft attitude
hyperagile tracking control with uncertainties, Aerosp. Sci. Technol. 119 (2021)
107126.

[13] Z. Lin, B. Wu, D. Wang, Speciﬁc tracking control of rotating target spacecraft
under safe motion constraints, IEEE Trans. Aerosp. Electron. Syst. 59 (3) (2023)
2422–2438. https://doi.org/10.1109/TAES.2022.3214799

[14] W. Lu, W. Gao, B. Liu, W. Niu, D. Wang, Y. Li, X. Peng, Z. Yang, Reinforcement
learning driven time-sensitive moving target tracking of intelligent agile satellite,
IEEE Trans. Aerosp. Electron. Syst. (2024).

[15] W. Lu, W. Gao, B. Liu, W. Niu, X. Peng, Z. Yang, Y. Song, Parallel dual adaptive ge-
netic algorithm: a method for satellite constellation task assignment in time-sensitive
target tracking, Adv. Space Res. 74 (10) (2024) 5192–5213.

[16] Y. Tian, Q. Hu, X. Shao, Adaptive fault-tolerant control for attitude reorientation
under complex attitude constraints, Aerosp. Sci. Technol. 121 (2022) 107332.
[17] Q. Hu, Y. Liu, H. Dong, Y. Zhang, Saturated attitude control for rigid spacecraft

under attitude constraints, J. Guid., Control, Dyn. 43 (4) (2020) 790–805.

[18] Z. Kang, Q. Shen, S. Wu, C.J. Damaren, Saturated attitude control of multispacecraft
systems on SO (3) subject to mixed attitude constraints with arbitrary initial attitude,
IEEE Trans. Aerosp. Electron. Syst. 59 (5) (2023) 5158–5173.

[19] S. Wang, Q. Shen, H. Li, R. Niu, Finite-Horizon active fault isolation and identiﬁ-
cation for spacecraft attitude control systems with multiple constraints, IEEE Trans.
Aerosp. Electron. Syst. (2025).

[20] C.R. Mclnnes, Large angle slew maneuvers with autonomous sun vector avoidance,

J. Guid., Control, Dyn. 17 (4) (1994) 875–877.

[21] Q. Shen, C. Yue, C.H. Goh, D. Wang, Active fault-tolerant control system design for
spacecraft attitude maneuvers with actuator saturation and faults, IEEE Trans. Ind.
Electron. 66 (5) (2018) 3763–3772.

Aerospace Science and Technology 168 (2026) 111238

[22] J. Elkins, R. Sood, C. Rumpf, Adaptive continuous control of spacecraft attitude
using deep reinforcement learning, in: 2020 AAS/AIAA Astrodynamics Specialist
Conference, AIAA Reston, VA, 2020, pp. 420–475.

[23] J. Elkins, R. Sood, C. Rumpf, Autonomous spacecraft attitude control using deep
reinforcement learning, in: 71St International Astronautical Congress (IAC),  2020,
2020.

[24] W. Lu, B. Liu, Z. Mu, S. Wu, Y. Song, V.Y. Razoumny, Multi-Satellite scheduling
for stereo tracking of moving targets via parallel island diﬀerential evolutionary
algorithm, IEEE Trans. Aerosp. Electron. Syst. (2025).

[25] H. Zhuang, W. Lu, Q. Shen, S. Wu, V.Y. Razoumny, Y.N. Razoumny, Oﬀ-policy re-
inforcement learning control for space manipulators based on object detection via
convolutional neural networks, Aerosp. Sci. Technol. (2025) 110914.

[26] H. Zhuang, W. Lu, Q. Shen, S. Wu, V.Y. Razoumny, Y.N. Razoumny, Heterogeneous
multi-space manipulator cooperative control in task space via oﬀ-policy reinforce-
ment learning, Acta Astronaut. (2025).

[27] H. Zhuang, J. Hou, Q. Shen, S. Wu, V.Y. Razoumny, Y.N. Razoumny, Event-
Triggered image-Space tracking control of space manipulators using oﬀ-Policy rein-
forcement learning with disturbance observers, IEEE Trans. Aerosp. Electron. Syst.
(2025).

[28] Q. Shen, D. Wang, S. Zhu, K. Poh, Finite-time fault-tolerant attitude stabilization
for spacecraft with actuator saturation, IEEE Trans. Aerosp. Electron. Syst. 51 (3)
(2015) 2390–2405.

[29] C. Yue, T. Huo, M. Lu, Q. Shen, C. Li, X. Chen, X. Cao, A systematic method for
constrained attitude control under input saturation, IEEE Trans. Aerosp. Electron.
Syst. 59 (5) (2023) 6005–6015.

[30] Z. Ma, Y. Wang, Y. Yang, Z. Wang, L. Tang, S. Ackland, Reinforcement learning-
based satellite attitude stabilization method for non-cooperative target capturing,
Sensors 18 (12) (2018) 4331.

[31] Y. Liu, G. Ma, Y. Lyu, P. Wang, Neural network-based reinforcement learning control
for combined spacecraft attitude tracking maneuvers, Neurocomputing 484 (2022)
67–78.

[32] W. Lu, Z. Geng, H. Zhuang, Q. Shen, S. Wu, V.Y. Razoumny, Y.N. Razoumny, Neural
network-Based fault identiﬁcation and reinforcement learning for spacecraft fault-
Tolerant control, IEEE Trans. Instrum. Meas. (2025) 1. https://doi.org/10.1109/
TIM.2025.3597688

[33] U.J. Ravaioli, J. Cunningham, J. McCarroll, V. Gangal, K. Dunlap, K.L. Hobbs, Safe
reinforcement learning benchmark environments for aerospace control systems, in:
2022 IEEE Aerospace Conference (AERO), 2022, pp. 1–20. https://doi.org/10.1109/
AERO53065.2022.9843750

[34] C. Mu, S. Liu, M. Lu, Z. Liu, L. Cui, K. Wang, Autonomous spacecraft collision avoid-
ance with a variable number of space debris based on safe reinforcement learning,
Aerosp. Sci. Technol. 149 (2024) 109131.

[35] K.P. Sharma, I. Kumar, P.P. Singh, K. Anbazhagan, H.M. Albarakati, M.W. Bhatt,
A.A. Ziyadullayevich, A. Rana, et al., Advancing spacecraft rendezvous and docking
through safety reinforcement learning and ubiquitous learning principles, Comput.
Human. Behav. 153 (2024) 108110.

[36] C. Han, Y. Zhang, S. Bai, X. Sun, X. Wang, Novel method to calculate satel-
lite visibility for an arbitrary sensor ﬁeld, Aerosp. Sci. Technol. 112 (2021)
106668.

[37] Y. Lian, Y. Gao, G. Zeng, Staring imaging attitude control of small satellites, J. Guid.,

Control, Dyn. 40 (5) (2017) 1278–1285.

[38] X. Sun, Q. Shen, S. Wu, Partial state feedback MRAC-Based reconﬁgurable fault-
Tolerant control of drag-Free satellite with bounded estimation error, IEEE Trans.
Aerosp. Electron. Syst. 59 (5) (2023) 6570–6586.

[39] X. Sun, Q. Shen, S. Wu, Fuzzy supervised learning-Based model-Free adaptive fault-
Tolerant spacecraft attitude control with deferred asymmetric constraints, IEEE
Trans. Aerosp. Electron. Syst. 59 (6) (2023) 8884–8900.

[40] X. Zhang, H. Zhang, H. Zhou, C. Huang, D. Zhang, C. Ye, J. Zhao, Safe reinforce-
ment learning with dead-ends avoidance and recovery, IEEE Rob. Autom. Lett. 9 (1)
(2023) 491–498.

[41] H. Zhang, G. Solak, G.J.G. Lahr, A. Ajoudani, Srl-vic: a variable stiﬀness-based safe
reinforcement learning for contact-rich robotic tasks, IEEE Rob. Autom. Lett. (2024).
[42] Y.C.  Tang,  J.  Zhang,  R.  Salakhutdinov,  Worst  cases  policy  gradients,

arXiv:1911.03618 (2019).

[43] T. Haarnoja, A. Zhou, P. Abbeel, S. Levine, Soft actor-critic: oﬀ-policy maximum
entropy deep reinforcement learning with a stochastic actor, in: International Con-
ference on Machine Learning, PMLR, 2018, pp. 1861–1870.

[44] T. Haarnoja, A. Zhou, K. Hartikainen, G. Tucker, S. Ha, J. Tan, V. Kumar, H. Zhu,
A. Gupta, P. Abbeel, S. Levine, Soft Actor-Critic Algorithms and Applications, 2019.
arXiv:1812.05905

[45] A. Ray, J. Achiam, D. Amodei, Benchmarking safe exploration in deep reinforcement

learning, arXiv:1910.01708 7 (1) (2019) 2.

[46] A. Stooke, J. Achiam, P. Abbeel, Responsive safety in reinforcement learning by
pid lagrangian methods, in: International Conference on Machine Learning, PMLR,
2020, pp. 9133–9143.

[47] A. Paszke, S. Gross, F. Massa, A. Lerer, J. Bradbury, G. Chanan, T. Killeen, Z. Lin, N.
Gimelshein, L. Antiga, et al., Pytorch: an imperative style, high-performance deep
learning library, Adv. Neural Inf. Process. Syst. 32 (2019).

[48] J. Ji, J. Zhou, B. Zhang, J. Dai, X. Pan, R. Sun, W. Huang, Y. Geng, M. Liu, Y. Yang,
Omnisafe: an infrastructure for accelerating safe reinforcement learning research, J.
Mach. Learn. Res. 25 (285) (2024) 1–6.

[49] W. Chu, S. Wu, Z. Wu, Y. Wang, Least square based ensemble deep learning for in-
ertia tensor identiﬁcation of combined spacecraft, Aerosp. Sci. Technol. 106 (2020)
106189.

[50] S. Zhu, D. Wang, Q. Shen, E.K. Poh, Satellite attitude stabilization control with ac-

tuator faults, J. Guid., Control, Dyn. 40 (5) (2017) 1304–1313.

17

