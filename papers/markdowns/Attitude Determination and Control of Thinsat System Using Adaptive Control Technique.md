Engineering Science
2023; 8(2): 14-22
http://www.sciencepublishinggroup.com/j/es
doi: 10.11648/j.es.20230802.11
ISSN: 2578-9260 (Print); ISSN: 2578-9279 (Online)

Attitude Determination and Control of Thinsat System
Using Adaptive Control Technique

Ukonu Ihuoma Christian, Eneh Innocent Ifeanyichukwu, Ene Princewill Chigozie*

Electrical and Electronics Engineering Department, Enugu State University of Science and Technology (ESUT), Enugu, Nigeria

Email address:

*Corresponding author

To cite this article:
Ukonu Ihuoma Christian, Eneh Innocent Ifeanyichukwu, Ene Princewill Chigozie. Attitude Determination and Control of Thinsat System
Using Adaptive Control Technique. Engineering Science. Vol. 8, No. 2, 2023, pp. 14-22. doi: 10.11648/j.es.20230802.11

Received: March 20, 2023; Accepted: April 20, 2023; Published: June 10, 2023

Abstract:  This  paper  presents  attitude  determination  and  control  of  ThinSat  system  using  an  adaptive  control  technique.
This study aims to reduce the impact of dynamic torque on the angular velocity and orientation of spacecraft while maintaining
a steady position in the axes. This was achieved by collecting the data of Nigeria Sat-2 which was trained with a multi-layered
neural  network  algorithm  employed  to  generate  an  adaptive  control  system  which  was  implemented  on  the  satellite  using
Simulink software. The training performance of the adaptive controller was evaluated and validated using Mean Square Error
(MSE) and regression. The result showed that the average MSE is 0045394Mu and 0.97271 for regression. The implication is
that the neural network correctly learns the spacecraft data collected and was able to detect changes in the angular velocity. The
step  response  of  the  adaptive  controller  was  evaluated  with  the  characterized  Proportional  Integral  Derivative  (PID)  control
system  and  the  result  showed  that  the  total  time  of  the  attitude  determination  and  control  of  the  spacecraft  is  111.24ms  as
against  465ms  with  PID  which  gives  76%  reduction  in  decision  time  to  control  error  due  to  dynamics.  The  comparative
analysis  with  the  characterized  in  the  rate  of  error  minimization  on  the  pitch  angular  velocity  showed  that  the  angle  was
reduced from 13.46mm with the adaptive controller to 9.55mm which gives a percentage improvement of 29%.

Keywords: ThinSat, Adaptive Control, Spacecraft, Nigeria Sat-2, Neural Network

1. Introduction

Since the beginning of the 21st century, the use of low-orbit
satellites  has  increased  with  great  development  in  the
research  of  space  science  and  technology.  These  satellites
vary  from  micro  to  mini  types  and  are  mostly  used  for
weather  forecasting,  telecommunication,  ship  movement
surveillance,  taking  images  of  the  earth,  obtaining  digital
elevation  maps  of  disaster  areas  and  environmental  tracking
of  some  animals  for  scientific  research  [12].  The  satellite
system is classified into three types which are low earth orbit
(LEO),  medium  earth  and  geostationary  earth  orbit  satellite
system [5].

Nigeria  as  the  giant  of  Africa  for  instance  launched  the
NigeriaSat-2, NigeriaSat-X (earth Observation satellites) and
NigComSat-1R  (a  communication  satellite)  to  space  in
August  and  December  2011  respectively.  Nigeria  Sat-2  was

mapping,

infrastructure

launched  in  August  2011.  It  has  high-resolution  satellite
spatial  resolutions  of  2.5m  panchromatic,  5m  multispectral
and with area coverage (swath width) of 20 by 20km and the
capacity  to  rapidly  produce  accurate  mapping  to  update  the
existing  information  and  acquire  new  mapping  information.
The  Nigeria  Sat-2  allows  for  environmental  and  disaster
settlement
management,
classification,  development  of  urban  green  spaces,  service
provision  maps,  access  control  mechanisms
regional
planning,  and  security  [11].  However,  the  capacity  to  take
precise  readings  due  to  the  impact  of  aerodynamic  and
magnetic parameters  has  hindered the effective performance
of  the  system  and  hence  presents  the  need  for  Attitude
Determination and Control System (ADCS) [15].
ADCS  was  developed  for  monitoring

the  navigation
behaviour  of  spacecraft  as  they  orbit  the  earth.  The  ADCS  is
divided into three main areas which are the dynamic modelling,
controller, filtering and estimation of attitude [17]. The dynamics

15

Ukonu Ihuoma Christian et al.:  Attitude Determination and Control of Thinsat System Using Adaptive Control Technique

of  the  system  include  the  environmental  models  and  attitude
mechanics  which  describe  the  translational  and  rotational
behaviour  of  the  satellite.  The  filtering  and  estimation  models
account  for  the  different  hardware  properties  of  the  system
sensors  [16].  Lastly,  the  controller  design  brings  the  control
algorithms together with the dynamics and estimation to ensure
mission performance requirements are met.

Various controllers have been proposed to achieve this aim
such as the Linear Quadratic Regulator, Proportional Integral
Derivative,  pitch  yaw  adjustment  controller,  etc,  [10].
However,  despite  their  success,  the  high  level  of  dynamic
electromagnetic torque which is present in the inner actuators
of the spacecraft presents the need for a control system which
is  adaptive  to  ensure  better  and  faster  control  response  [13-
14].  This  when  achieved  will  reduce  the  error  of  angular
velocity  on  the  momentum  of  the  spacecraft  and  hence
provide a better attitude.

2. Literature Review

Alexandre  et  al  presented  Assurance  and  Control
Framework  for  a  Global  Navigation  Satellite  System-
Reflectometry  (GNSS-R)  Earth  Perception  6U  CubeSat
Mission  [1].  This  work  portrays  the  demeanour  assurance
and  control  framework  Attitude  Determination  and  Control
System (ADCS) of Feline 2 which is a six-unit CubeSat. This
target  controls  the  satellite  in  a  circle  and  satisfies  the
prerequisites fundamental for the satellite framework. Feline
2 is utilized to guide the receiving wires towards the earth to
perform  tests  and  afterwards  situate  the  sun-oriented  boards
towards  the  sun  to  expand  the  force  input  when  the  battery
level is low.

Assaad et al showed the Mentality Assurance and Control
Framework  for  CubeSat  [2].  This  work  centers  around  the
equipment  determination  in  the  space  of  sensors,  actuators
and  processors  of  the  Shape  satellite  framework  which  is
driven  by  NASA  Goddard  Space  Flight  mission.  This
examination  showed  the  Disposition  Assurance  and  Control
Framework (ADCS) utilizing the mathematical codes written
in MATLAB. This examination was produced for exploratory
tests  and  confirmation  of  ADCS.  This  work  builds  the
viability  of  the  control  by  12.5%,  taking  it  from  76%  to
88.5%.  Subsequently,  an  improvement  in  the  adequacy  of
this framework will be fundamental.

Cullen  demonstrated  an  exploration  work  on  Direction,
Route  and  Control  of  Little  Satellite  Demeanor  Utilizing
the  plan,
Miniature  Engines  [8].  This  work  manages
improvement and combination of a Guidance Navigation and
Control  (GNC)  subsystem  into  a  unique  system  that  can  be
executed  on-board  progressively
to  perform  satellite
demeanour  controls  by  telling  the  precise  speed  increase
dependent on a fourth-order polynomial regarding time. The
rate  blunder  rate  distinguished  for  this  examination  was
recorded  to  be  15%  overall.  Thusly,  future  attempts  to
diminish  these  mistake  rates  are  vital  for  a  more  solid
framework.

3. Methodology

The  procedure  of  design  for  this  system  involves  the
development of the model of the attitude control system and
the data of the spacecraft dynamics collected considering the
attributes of navigation such as position and speed. The data
was trained with an adaptive control system to get a reference
point  for  adjustment  and  control  instability.  The  system
developed  was  implemented  with  a  high-level  programming
language  and  integrated  into  the  testbed/test  facility  for
optimization.

Figure 1. Image of the Test facility (Courtesy: NIGCOMSTAT).

From the test facility in figure 1, the Helmholtz cage was
used  to  provide  a  three-axis  dynamic  magnetic  field  which
will  cancel
the  earth's  magnetic  field  and  create  a
geomagnetic  field-based  environment  similar  to  space  for
satellite  habitation.  The  ADCS  hardware  is  the  satellite
control  system  developed  with  a  Proportional  Integral
Differentiator  (PID)  control  system  which  was  used  to
control  the  attitude  parameters  of  the  spacecraft  towards
desired orientation. The test control system software used is
the  space  mission  control  software  which  can  monitor  the
dynamic  behaviour  of  satellites  and  report  to  a  monitoring
laptop. The motion tracking system is a horn antenna which
is specialized in tracking the torque, and angular velocity of a
satellite,  while  the  sun  simulator  is  used  to  provide  up  to
50,000lux  illumination  and  can  be  adjusted  from  30  to  100
per  cent.  The  air-bearing  platform  is  used  to  introduce
nonlinearity in the environment and then test the controlling
attitude of the satellite system.

3.1. Model of the Attitude Determination and Control

System (ADCS)

This section presents the modelling diagram of the ADCS
under  study  with  the  various  sections  such  as  the  earth
electromagnetic field model, attitude determination algorithm
control algorithm, spacecraft dynamics, and attitude.

Engineering Science 2023; 8(2): 14-22

16

Figure 2. Architecture of the ADCS.

In  figure  2,  the  ADCS  sensors  composed  of  absolute  and
relative sensors collect data on the spacecraft's attitude such as
the speed, sun position, temperature, position, and orientation;
then forward to the Tri-Axial Attitude Determination (TRAID)
determination  algorithm  [7]  which  collected  data  about  the
dynamic nature of the input and feed to the control algorithm
which adjusts the position of the actuator to reject disturbance
and ensure better navigation performance.

3.2. Model of the Problem Formulation for ADCS

Based  on  Euler’s  model  [4],  the  angular  momentum  of  a

static body in the body frame is presented as;

(cid:2)                                    (1)

(cid:1)(cid:2) (cid:3) (cid:4)(cid:5)(cid:6),(cid:2)
Where  (cid:4)	 ∈ (cid:10)(cid:11)(cid:12)(cid:11)  is  the  matrix  of  inertia  and  angular
(cid:2) ∈ (cid:10)(cid:11) which is relative to the frame of inertia.
velocity is (cid:5)(cid:6),(cid:2)
The angular momentum is determined by the frame of inertia
[9]. It is represented;

(cid:6) (cid:1)(cid:2)                                 (2)
(cid:1)(cid:6) (cid:3) 	 (cid:10)(cid:2)
The  rate  of  change  of  angular  momentum  is  equal  to
torque  such  as  (cid:13)(cid:6) (cid:3) 	 (cid:1)(cid:6)  and  differentiating  the  frame  of
inertia in equations 1 and 2 gives [9];

(cid:6) (cid:14)(cid:15)(cid:5)(cid:6),(cid:2)
Equation 3 can be written as [4];

(cid:13)(cid:6) (cid:3) 	 (cid:1)(cid:6) (cid:3) 	 (cid:10)(cid:2)

(cid:2) (cid:16)(cid:1)(cid:2) 	 (cid:17) 	 (cid:10)(cid:2)

(cid:6) (cid:1)(cid:2)                (3)

(cid:2)                         (4)

(cid:2) (cid:17) 	 (cid:4)(cid:5)(cid:6),(cid:2)

(cid:13)(cid:2) (cid:3) (cid:14)(cid:18)(cid:5)(cid:6),(cid:2)

(cid:2) (cid:19)	(cid:4)(cid:5)(cid:6),(cid:2)
Where  the  inertia  matrix  is  kept  constant,  the  torque
(cid:2),
decomposition  into  the  actual  component  is (cid:13)(cid:2) (cid:3) 	 (cid:13)(cid:20)
while  the  dynamics  induces  on  the  spacecraft  due  to
perturbed torque is presented [4];

(cid:2) (cid:17) 	 (cid:13)(cid:21)

(cid:2) 	= -S((cid:5)(cid:6),(cid:2)

(cid:22)(cid:5)(cid:23)(cid:6)(cid:2)

(cid:2) (cid:19)	(cid:4)(cid:5)(cid:6),(cid:2)
(cid:2)	(cid:24)	(cid:10)(cid:11) presents the actuator torques and (cid:13)(cid:21)

(cid:2)	(cid:24)	(cid:10)(cid:11) is
Where (cid:13)(cid:20)
the  dynamic
torque  from  gravity.  The  application  of
quaternion presentation of the satellite attitude relative to the

(cid:2) (cid:17) 	 (cid:13)(cid:20)

(cid:2) (cid:17) 	 (cid:13)(cid:21)

(cid:2)                (5)

inertial frame is presented [4];

(cid:25)(cid:6),(cid:2) (cid:3)

(cid:26)
(cid:27) (cid:28)(cid:15)(cid:25)(cid:6),(cid:2)(cid:16) (cid:29)

0
(cid:2) (cid:31)                           (6)
(cid:5)(cid:6),(cid:2)

Equations  5  and  6  presented  the  attitude  behaviour  of
the  spacecraft  under  dynamics  due  to  the  perturbated
torque.

3.3. Error Dynamics Models

From Euler’s  model, the angular acceleration presents the
relationship  to  the  inertia  frames.  For  control  of  the
dynamics, the angular velocity relative to the orbit frame has
to  be  approximated  and  it  is  presented  as  (cid:5) ,(cid:2)
(cid:2) !
 and differentiated as equation 7;
	(cid:10)(cid:6)

(cid:2) (cid:3) 	 (cid:5)(cid:6),(cid:2)

(cid:6)
(cid:2)(cid:5)(cid:6),

(cid:4)(cid:5) ,(cid:2)

(cid:2) (cid:3) 	 !(cid:14)(cid:15)(cid:5)(cid:6),(cid:2)
(cid:2) (cid:16)(cid:10)(cid:6)
(cid:17)	(cid:4)(cid:14)(cid:15)(cid:5)(cid:6),(cid:2)

(cid:2) (cid:16)(cid:5)(cid:6),(cid:2)
(cid:6)
(cid:2)(cid:5) ,(cid:6)

(cid:2) (cid:17) 	 (cid:13)(cid:20)
	 ! (cid:4)(cid:10)(cid:6)

(cid:2)
(cid:2) 	 (cid:17) 	 (cid:13)(cid:21)
                    (7)
(cid:6)
(cid:2)(cid:5)(cid:6),

Figure  7  presented  the  attitude  dynamics  relative  to  the
orbit  frame.  The  relative  dynamic  error  to  enable  tracking  a
desired  altitude  and  angular  velocity  can  be  represented  as
" 	(cid:24)	∞ using the quaternion and angular velocity

(cid:25) ,"
error [9]. This can be determined as;

" , (cid:5) ,"

, (cid:5) ,"

(cid:25) ,"

, = (cid:25) ,"

, ⊗ (cid:25) ,"

                         (8)

(cid:2) (cid:3) 	 (cid:5) ,(cid:2)

(cid:2) ! 	 (cid:10)"

(cid:5)",(cid:2)

(cid:2)(cid:5) ,"

"                      (9)

With kinematics as;

%",(cid:2)

= !

(cid:26)
(cid:27) (cid:24)",(cid:2)

& (cid:5)",(cid:2)

(cid:2)                        (10)

εd, b	 (cid:3) 	 (cid:18)nd, bI	 (cid:17) 	S	(cid:18)εd, b(cid:19)(cid:19)(cid:5)",(cid:2)

(cid:2)          (11)

The  angular  acceleration  error  in  equation  9  can  be

differentiated as;

(cid:4)(cid:5)",(cid:2)

(cid:2) (cid:3) 	 !(cid:14)	(cid:15)(cid:5)(cid:6),(cid:2)
!(cid:4)(cid:10)(cid:6)

(cid:6)
(cid:2)(cid:5)(cid:6),

(cid:2) (cid:17) 	 (cid:13)(cid:20)
(cid:2) (cid:16)(cid:4)(cid:5)(cid:6),(cid:2)
	 (cid:17) (cid:4)(cid:14)	(cid:15)(cid:5) ,(cid:2)

(cid:2) (cid:16)(cid:10)"

(cid:2) (cid:17) (cid:13)(cid:21)
(cid:2)(cid:5) ,"

(cid:2) (cid:17) 	(cid:4)(cid:14)	(cid:15)(cid:5)(cid:6),(cid:2)
(cid:2)(cid:5) ,"
" ! 	(cid:4)(cid:10)"

(cid:6)
(cid:2)(cid:5) .(cid:6)
(cid:2) (cid:16)(cid:10)(cid:6)
"          (12)

17

Ukonu Ihuoma Christian et al.:  Attitude Determination and Control of Thinsat System Using Adaptive Control Technique

Hence the control objectives can be defined as the making
" (cid:19) 	 → (cid:18)0, 0(cid:19)  which  is  the  desired  position  the

of  ( (cid:25)",(cid:2), (cid:5)",(cid:2)
spacecraft is meant to follow.

3.4. Attitude Determination Algorithm (TRIAD)

The  TRIAD  algorithm  provides  a  fast  and  simple
deterministic  solution  for  the  attitude  of  spacecraft  systems
based on two vector observations generated from two different
coordinate  systems.  TRIAD  only  accommodates  two  vector
observations  at  any  one-time  instance  [3].  Initially,  TRIAD
assumes  that  one  of  the  vector  measurements  is  more  exact
than the other. The vector measurements in the spacecraft body
frame are named (b2 and b2), and the vectors in the reference
frame  (r1  and  r2).  It  is  assumed  that  the  first  vector
measurement  b1  is  the  most  reliable.  Based  on  this,  three
TRIAD are set up respectively [7].

/(cid:26)(cid:2) (cid:3)

(cid:2)0
|(cid:2)0| /(cid:26)2 (cid:3)

                       (13)

20
|20|

/(cid:27)(cid:2) (cid:3)

(cid:2)0	3	(cid:2)4
|(cid:2)03	(cid:2)4| /(cid:27)2 (cid:3)

20	3	24
|203	24|

                 (14)

/(cid:11)(cid:2)5	607	(cid:23)	/(cid:27)(cid:2)/(cid:11)25	/(cid:26)2	(cid:23)	/(cid:27)2

                 (15)

Finally,  equations  13  –  15  were  used  to  develop  the

TRIAD as;

862(cid:6)(cid:20)" (cid:3) 9/(cid:26)(cid:2)	(cid:23)	/(cid:27)(cid:2)	(cid:23)	/(cid:11)(cid:2):	9/(cid:26)(cid:2)	(cid:23)	/(cid:27)(cid:2)	(cid:23)	/(cid:11)(cid:2):&       (16)

3.5. Development of an Adaptive Control System (ACS)

The  development  of  an  adaptive  control  system  was
proposed to solve the dynamics problems experienced by the
spacecraft.  The  adaptive  control  strategy  in  focus  employed
an artificial neural network solution which uses the acquired
data  about  the  spacecraft  dynamics  to  train  and  adjust  the
orientation of the system to the desired point.

The  data  was  collected  for  the  training  of  the  adaptive
control  system  developed  with  a  Multi-Layered  Neural
Network  (MLNN).  The  MLNN  algorithm  by  [6]  was  used.
The MLNN is made of weight, bias, activation function and
training  algorithm.  The  architectural  model  of  the  MLNN
was presented in figure 3.

Figure 3. Architectural model of the Neural Network algorithm.

The  architectural  diagram  of  the  MLNN  comprises  two-
layered  neural  network  models  used  to  train  the  data
collected.  The  number  of  inputs  of  the  neural  network  is
determined using the attributes of the dataset collected, while
the activation function used is the tansig type.

PSEUDOCODE OF THE ACS
1.  Start
2.  Load training set
3.  Divide into training and test set
4.            Configure the MLNN
5.                Activation MLNN
6.                    Select training algorithm
7.                     Set epoch parameters and intervals
8.  Set  performance  evaluation  metrics  (Mean  Square

Error (LSE) and regression)

9.          Train neural network
10. If
11.          LSE is true
12. Then
13.            Generate ACS
14. Else
15.              Back-propagation
16.                   Adjust neurons
17.                     Apply (step 9)
18. Do
19.          Until (Step 11 is true)
20.                     Apply step 13
21. End

Engineering Science 2023; 8(2): 14-22

18

3.6. Development of the Adaptive ADCS

The  ADCS  was  developed  using  the  ACS  algorithm

generated  in  the  previous  section  to  model  an  improved
ADCS  for  optimal  satellite  navigation.  The  ADCS  was
developed using the flow chart in figure 3;

The flow chart  was  used to  show the  workflow of the  adaptive  ADCS developed. The trained  algorithm  was  used to  adjust

intelligently the dynamic attitude of the spacecraft to achieve the desired attitude as shown in the architectural model in figure 5;

Figure 4. The flow chart of the adaptive ADCS.

19

Ukonu Ihuoma Christian et al.:  Attitude Determination and Control of Thinsat System Using Adaptive Control Technique

Figure 5. Architectural diagram of the adaptive ADCS.

Figure  5  presents  the  architectural  diagram  of  the  ADCS
developed with the MLNN control algorithm developed. The
ADCS  sensors  collected  data  of  the  spacecraft  dynamics
introduced  due  to  torque  disturbance  and  fed  to  the  MLNN
algorithm  via  the  attitude  determination  system  for  training
and correction of the error to ensure controlled navigation.

4. System Implementation

The adaptive ADCS was implemented with Simulink. This

was  achieved  with  the  aerospace  toolbox,  control  system
toolbox  and  neural  network  toolbox.  The  neural  network
toolbox  was  used  to  train  the  data  collected  to  generate  the
ACS and then used to configure the control system toolbox to
develop  the  Simulink  block  of  the  ACS.  The  aerospace
toolbox  was  used  to  implement  the  NigeriaSat-2  model  and
then  control  the  dynamics  with  the  adaptive  ACS  model
developed.  The  simulation  parameters  are  all  reported  in
table 1.

Table 1. NigeriaSat-2 Simulation parameters.

Values
1960 kg (launch mass), 2.6 m x 1.5 m x 1.5 m
968.5 kg
1164 W, two 18 Ah Ni-Cd batteries
440 N LAM (Liquid Apogee Motor) and twelve 22 N thrusters with MMH (Mono Methyl Hydrazine) as fuel and MON-3
(Mixed Oxides of Nitrogen) as the oxidizer
0.9 m and 1.0 m
7.7 years
35786km
0.1± 402.75
0.1± 4506.05

This

section  presents

the  attitude
the
determination using the neural network and the result of the
satellite navigation from the system implementation.

result  of

5.1. Result of the Attitude Determination

To  evaluate  the  attitude  of  the  ACS  developed  with  a
neural  network,
the  MSE  and  Regression  were  used
respectively.  The  idea  was  to  measure  the  training  error
achieved in the neurons during the learning process and also

determine  the  ability  of  the  adaptive  ADC  algorithm  to
classify changes  in  the angular  momentum and approximate
to  minimize  the  impact  on  the  angular  velocity.  The  MSE
attitude is presented in figure 6 and the regression results are
in figure 7;

Figures 6 and 7 present the MSE and regression performance
of  the  neural  network-based  ADC  algorithm  developed.  From
the result the MSE recorded is 0.056845Mu which is very good
as it is approximately zero. The Regression also showed that the
average R recorded from the training, test and validation set is
0.99999 which is approximately 1 and also very good.

Parameters
Spacecraft mass, size
Spacecraft dry mass
Power

Propulsion

Antenna size
Mission design life
Distance covered
Uplink frequency
Downlink

5. Results

Engineering Science 2023; 8(2): 14-22

20

Figure 6. MSE result of the ADC.

Figure 7. Regression Result.

21

Ukonu Ihuoma Christian et al.:  Attitude Determination and Control of Thinsat System Using Adaptive Control Technique

5.2. Result of the Satellite Navigation

This  section  discussed  the  attitude  of  the  satellite  when
simulated with the adaptive control system developed as the
attitude  control  system.  The  impact  of  dynamics  due  to
electromagnetic torque acting on the wheels momentum and
the quaternion representation  modelled in equations 5 and  6
is presented in figure 8.

equation 7 which results in an error in the angular velocity as
modelled in equation 12. However, this error was controlled
by  the  adaptive  control  system  developed  and  maintained
stable orientation at 0.08orbit respectively. The implication of
the  result  showed  that  the  dynamic  torque  which  affects  the
stable  orientation  of  the  spacecraft  was  controlled  by  the
adaptive control system developed and was able to maintain
a stable satellite attitude.

6. Conclusion And Recommendation

This  section  presents  the  conclusion  of  the  work  and  the
recommendations  for  future  research  and  improvements
satellite navigation system.

6.1. Conclusion

This paper presents attitude determination and control of a
satellite system using an adaptive controller. The aim was to
control  the  orientation  of  the  spacecraft  during  navigation
and  mitigate  the  impact  of  dynamic  electromagnetic  torque
which resulted in an error in the angular velocity for the axes.
This  problem  was  solved  using  an  artificial  neural  network
which was trained with the data collected from the spacecraft
and  developed  an  adaptive  control  which  adjusts  the
orientation of the satellite to the reference position. The result
when  implemented  showed  that  the  adaptive  controller  was
able  to  reduce  the  error  in  the  angular  velocity  of  the
spacecraft and achieve better control performance.

6.2. Recommendation

in

interested

This  control  system  developed  is  recommended  to  be
integrated with other Nigerian satellites like the NigariaSat-3
system  for  optimized  navigation  performance.  For  future
works,  this  paper  can  serve  as  a  valuable  reference  for
researchers  and  engineers  who  are
the
development and implementation of adaptive control systems
for spacecraft. Based on the findings of this study, it may be
beneficial for future research to investigate the effectiveness
of  the  developed  adaptive  control  system  in  different
scenarios  or  under  varying  conditions.  Additionally,  further
studies  could  focus  on  the  integration  of  other  control
techniques or algorithms to further improve the performance
of  the  adaptive  control  system.  Furthermore,  the  results  of
this study may provide insights into the development of more
efficient  and  effective  control  systems  for  spacecraft  in  the
future.

References
[1]  Alexandre  C.,  David  V.,  Jaume  J.,  Enric  J.,  Roger  O.,  Adrià
A.,  Joan  F.,  Pol  V.,  &Adriano  C.,  (2016).  3CAT-2:  Attitude
Determination  and  Control  System  for  a  GNSS-R  Earth
Observation  6U  CubeSat  Mission,  European  Journal  of
Remote
DOI:
10.5721/EuJRS20164940.

759-776,

Sensing,

49:

1,

Figure 8. Impact of torque on the satellite.

From the result in figure 8, it was observed that nonlinear
torque  affected  the  momentum  of  the  spacecraft  orientation
which was reflected in the unstable orientation of the wheels
based  on  the  Euler  rotational  theorem  but  was  controlled  at
three  orbits.  This  was  due  to  the  impact  of  the  adaptive
control system developed which was able to approximate the
impact  of  the  torque  dynamics  and  stabilize  the  angular
velocity as shown in figure 9.

Figure 9. Result of the angular velocity.

From  the  result,  it  was  observed  that  the  impact  of  the
dynamics  torque  affected  the  Euler  angle  position  as  in

Engineering Science 2023; 8(2): 14-22

22

[2]  Assaad  F.,  Jighjigh  I.,  Ye  L.,  Alan  S.,  (2014).  Attitude
Determination  and  Control  System.  Bachelor  of  Science
Project. (Accessed on July 12th 2022).

[3]  Bak  T.  (1999).  Spacecraft  Attitude  Determination  -  a
Magnetometer  Approach,  Ph.D.  Thesis,  Aalborg  University.
(Accessed on July 15th 2022).

[4]  Barsukow W., Edelmann P., Klingenberg C., Ropke F., (2017).
A low-Mach Roe-type solver for the Euler equations allowing
for gravity source terms. ESAIM Proceedings and Surveys 58:
27-39 DOI: 10.1051/proc/201758027.

[5]  Carlo N., (2020). In-orbit data-driven parameter estimation for
attitude  control  of  satellites.  Automatic.  Université  de
Lorraine. English. ffNNT: 2020LORR0058ff. fftel-02949320f.

[6]  Chen  Z.,  Li  C.,  Sanchez  R.,  (2015).  1684.  Multi-layer  Neural
Network with Deep Belief Network for Gearbox Fault Diagnosis.
©  JVE  International  Ltd.  Journal  of  Vibroengineering.  AUG
2015,  VOLUME
1392-8716
ISSUE
https://core.ac.uk/display/323314109?utm_source=pdf&utm_med
ium=banner&utm_campaign=pdf-decoration-v1

ISSN

17,

5.

[7]  Christopher  D.,  (2003),  Spacecraft  Attitude  Dynamics  and
4.

Control,
http://www.aoe.vt.edu/~cdhall/courses/aoe4140/attde.pdf.
(Accessed on July 15th 2022).

chapter

[8]  Cullen  M.,  (2016).  Guidance,  Navigation,  And  Control  of
Small Satellite Attitude Using Micro-Thrusters. A Dissertation
Submitted  To  The  Graduate  Division  Of  The  University  Of
Hawai‘I  At  Manoa  Master  of  Science  Dessertation  In
Mechanical Engineering. (Accessed on July 13th 2022).

[9]  Espen O., (2018) “Modelling and attitude control of elliptical
DOI:
at

orbits;
10.5772/intechopen.80422;
https://www.intechopen.com/chapters/63931

available

control”

modern

applied

[10]  Sakai S., Fukushima Y., Saito H., (2008). Design and on-orbit

evaluation  of  magnetic  attitude  control  system  for  the
“REIMEI”  microsatellite,  Advanced  motion  Control,  2008.
AMC '08. 10th IEEE International Workshop on, pp. 584-589,
26-28 March 2008.

[11]  Samuel O., (2015). Nigerian Communication Satellite and the
Quest  for  Sustainable  National  development,  American
Journal  of  Social  Science  Research,  1  (1),  2015,  1-8.
Retrieved
from:
http://www.publicscienceframework.org/journal/ajssr

[12]  Yuri  V.  Kim  (2020).  Satellite  Control  System:  Part  I  -
DOI:

Architecture
http://dx.doi.org/10.5772/intechopen.92575

Components

Main

and

[13]  Virgili-Llop  J,  Polat  H.  and  Romano  M  (2019)  Attitude
Stabilization of Spacecraft in Very Low Earth Orbit by Center-
Of-Mass  Shifting.  Front.  Robot.  AI
doi:
10.3389/frobt.2019.00007.

6:

7.

[14]  Tam  N.,  Kerri  C.,  and  Anne  M.,

(2018).  Attitude
Determination for Small Satellites with Infrared Earth Horizon
Sensors.  JOURNAL  OF  SPACECRAFT  AND  ROCKETS
Vol.  55,  No.  6,  November–December  2018.  Downloaded  by
129.205.112.63  on  March  3,  2021  |  http://arc.aiaa.org  |  DOI:
10.2514/1.A34010.

[15]  Reyhanoglu M., Drakunov S. (2018) - Attitude Stabilization of
Small Satellites Using Only Magnetic Actuation. Proceedings
of  IEEE  Industrial  Electronics  Society,  pp.  103-107.  doi:
http://dx.doi.org/10.1109/iecon.2008.4757936.

[16]  John  C.  (2018).  Satellite  Attitude  Determination  with  Low-
Cost  Sensors.  Ph.D.  Thesis,  Aerospace  Engineering  in  the
University of Michigan. (Accessed on July 15th 2022).

[17]  Klaus  S.,

(2018).  Mission  Analyses

for  Low-Earth-
Observation  Missions  with  Spacecraft  Formations.  Chair
Robotics
Julius-Maximilians-University
Würzburg  Am  Hubland  D-97074  Würzburg  GERMANY.
RTO-EN-SCI-231

and  Telematics

