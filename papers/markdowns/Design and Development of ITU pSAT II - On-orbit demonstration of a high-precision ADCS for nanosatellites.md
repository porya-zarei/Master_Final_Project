See discussions, stats, and author profiles for this publication at: https://www.researchgate.net/publication/279533161

Design and Development of ITU pSAT II: On orbit demonstration of a high ‐
precision ADCS for nanosatellites

Conference Paper · June 2011

CITATIONS
4

13 authors, including:

Emre Koyuncu

Istanbul Technical University

97 PUBLICATIONS   554 CITATIONS

SEE PROFILE

Nazim Kemal Ure

Istanbul Technical University

56 PUBLICATIONS   1,216 CITATIONS

SEE PROFILE

READS
1,222

Melahat Cihan

University of Samsun

16 PUBLICATIONS   42 CITATIONS

SEE PROFILE

Mehmet Caner Akay

Istanbul Technical University

6 PUBLICATIONS   28 CITATIONS

SEE PROFILE

All content following this page was uploaded by Emre Koyuncu on 02 July 2015.

The user has requested enhancement of the downloaded file.

DESIGN AND DEVELOPMENT OF ITU pSAT II : ON ORBIT DEMONSTRATION
OF A HIGH-PRECISION ADCS FOR NANOSATELLITES

Emre Koyuncu, Melahat Cihan, Kemal Ure, Caner Akay, Elgiz Baskaya, Soner Sarikaya,
Aykut Cetin, Utku Eren,Yigit Kaya, Burak Karadag, Can Kurtulus,
Prof. Dr. Metin Orhan Kaya, Prof. Dr. İbrahim Ozkol and Assoc. Prof. Dr. Gokhan Inalhan1.

1Istanbul Technical University, Faculty of Aeronautics and Astronautics, Istanbul, Turkey.

ABSTRACT

ITU  pSAT  II  is  the  second  student  satellite  project  from  ITU  FAA  Controls  and  Avionics  Laboratory,  which
aims  to  design  and  on-orbit  demonstrate  a  standardized  bus  and  a  novel  ADCS  for  pico  and  nano  sized
satellites  (1-10  kg)  with  multi  objective  applications.  Main  aim  of  this  project  is  to  demonstrate  specific
challenges and solutions for ADCS design for nanosatellites, which require a high precision, fault tolerant and
reconfigurable control system. ITU pSAT II is scheduled for launch on 2012 Q3. In this paper, we review the
ITU  pSAT  II  design  including  the    ADCS  and  the  software/hardware  in  the  loop  test  system  of  ITU  pSAT  II.
ADCS  of  ITU  pSAT  II  consists  of  three  distinct  hardware  layers  integrating  sensors,  actuators,  and  ADCS
computer  over  the  CAN  bus.  The  sensor  layer  embeds  a  set  of  low-cost  inertial  and  magnetic  sensors,  sun
sensors,  a  GPS  receiver  and  an  in-house  developed  multifunctional  camera/star-tracker.  The  actuator  layer
includes  a  redundant  assembly  of  reaction  wheels,  magnetic  torquer  coils  and  an  experimental  set  of
(cid:80)PPTs(micro  pulse-plasma  thrusters).  Embedded  within  the  ADCS  Computer  is  a  filter  which  allows  the
asynchronous  fusion  of  filtered  sensor  data  with  outputs  from  the  orbit  and  attitude  propagation  algorithms.
Propagation  algorithms  simulate  the  spacecrafts  dynamical  response  (including  effects  of  disturbances,  and
uncertainties  in  sensor  and  actuator  models)  and  compare  it  with  actual  sensor  data  to  improve  accuracy  of
determination  of  spacecrafts  attitude  and  orbit  position.  These  filtered  and  fused  state  data  is  fed  to  a  fault-
tolerant  and  reconfigurable  control  layer.  The  control  layer  is  divided  into  different  operation  modes  and
associated control strategies depending not only on the actual spacecraft operation mode (such as de-tumbling
or high-precision attitude control for image capturing) but also depending on the health-status of the individual
sensors  and  the  actuators.  This  paper  presents  development  stages  of  ADCS  of  ITU  pSAT  II,  focusing  on
estimation and control algorithms and hardware implementation suited for high precision attitude control for
small  satellites,  and  development  of  a  testbed  which  simulates  spacecraft  dynamics  and  space  environment.
Specifically,  we  present  a  software  and  a  hardware  in  the  loop  system,  which  integrates  components  of  the
ADCS with an in lab developed air bearing table to simulate attitude dynamics and Helmholtz Coil system to
emulate earth's magnetic field. Overall architecture is suitable for testing under number of possible hardware
failure  scenarios  and  control  modes,  and  compensates  re-design  process  of  the  system,  such  as  improving
reliability of algorithms and re-selection of hardware components.

1.

INTRODUCTION

ITU pSAT II is the second student satellite project from ITU FAA Controls and Avionics Laboratory, which
aims to design and on-orbit demonstrate a standardized bus and a novel ADCS for pico and nano sized satellites
(1-10 kg) with multi objective applications. Main aim of this project is to demonstrate specific challenges and
solutions for ADCS design for nanosatellites, which require a high precision, fault tolerant and reconfigurable
control system. ITU-PSAT I, which was developed and manufactured by the same team, was launched
successfully from India at 23rd of September 2009. Satellite is still known to be functional up to this date. More
on the development process of ITU pSAT I can be found in [1, 5].

Nano-satellites are used and envisioned for a wide range of applications including lower-cost testing and proof-
of-concept demonstration of in-development subsystems [6-9], examining of GPS signals [10], providing low-
cost communication links [11, 12], taking photographs [13], and for scientific purposes such as low earth
radiation measurement [14], plasma density and magnetic field measurements [12]. Beside single satellite
operations it is expected in near future that groups of pico-, nano- and micro-satellites (satellite constellations)
will be working as a group on orbit to perform space science [15] and service missions. Satellite constellations
superiority in risk distributing risk, higher target area visit frequency, distributed measurement capability and
backup ability [16] make it an ideal choice for missions such as measurement of earth's magnetic field

Page 1 of 19

alterations [17] and providing lower-cost global communication services [18]. We refer the reader to [19-29] for
surveys of nano-satellite applications and new nano-satellite technologies.

As indicated in [19-29], one of the bigger challenges in nanosatellite technologies is development of robust
attitude determination and control systems which will allow these satellites’ attitudes to be precisely known and
controlled to obtain high quality mission data on demand. ITU pSAT II ADCS is envisioned to fulfill that
requirement. In this paper we provide a compilation of results from [30-32] and present the design of ITU pSAT
II. Specific focus is given to the ADCS hardware and software implementations suited for high precision
attitude control for small satellite. In addition, we present the development of a testbed which simulates
spacecraft dynamics and space environment. Specifically, the developed software and a hardware in the loop
system integrates in-lab developed air bearing table and a Helmholtz Coil system to simulate attitude dynamics
under on-orbit earth's magnetic field.

In Section 2, we first review the ITU pSAT II design giving insight on the bus and the subsystems. Section 3
focuses on the ADCS. Specifically the ADCS computer, sensors, actuators and the software framework is
detailed. This section also includes the SIL test results from the fault tolerant and reconfigurable ADCS
algorithms. In Section 4, we present an overview of the SIL and HIL that is erected for this project.

ITU PSAT II DESIGN

2.
The design of ITU pSAT II hinges on a modular structure and a data bus system which allows it to be used for
various types of different missions. As seen in Fig. 1, the modular structure includes a 1U (i.e.
10cmx10cmx10cm) unit PC-104 stack which embeds the system bus and a 2U (i.e. 10cmx10cmx20cm)
experimental payload unit. Fig. 2 illustrates the assembly of this modular structure. The modular 3U (i.e.
10cmx10cmx30cm)  structure can open up on all the side faces using hinges. This allows not only easy access to
all the structural side panels, but also straight forward assembly of the payloads and components. The solar
panels are screwed on the top of these side structural panels.

Fig. 1: Conceptual design of the ITUpSAT II

As designed, the ITU pSAT II structure weights less than 450 grams and it is fully compliant with Cubesat
Design Specifications [32]. All the structural components are made of Aluminum 7075 T6 as it provides
cheaper access and easier production in comparison to the other Aluminum grades and metals available for
space usage. The modular structure is reconfigurable towards various different mission scenarios as the internal
payload volume is maximized to 2U units. In addition, the payload components and boards can not only be
placed horizontally but also vertically depending on size and the need for access to the side panels. The total
mass and power budget is given in Table 1. It is important to note that the total power as illustrated is not the
operational maximum power but only a straight power list of the all the components. In the budget, in addition
to all the bus systems and specific payloads (i.e. experimental ADCS unit, the camera and the S-band
transmitter) for ITU pSAT II, there is room for an additional 1000g and 5Watt (%5 duty cycle) payload room
for future projects.

Fig. 2: Assembly of ITU pSAT II

COMPONENTS
Structure (incl.
mechanisms)
Solar Panels
Electrical Power
System (EPS)
On-Board Computer
(OBC)
Communication
ADCS
Camera
Payload

Mass (gr)

Power (mW)

560

660

315

70

160
550
400
1000
3715

0

0

250

250

10000
14000
600
5000
30100

Table 1: Mass and power budget

A.  ITU PSAT II BUS

ITU pSAT II houses a 1U unit PC-104 stack which includes the main backbone bus of the satellite. Within the
bus, an OBC, EPS, a battery board, ADCS board(including a sensor) and a GPS unit is housed. The backbone
bus components are as follows:

(cid:120)  OBC : Aerocon NanoOBC I,
(cid:120)  Communication  : AstroDev Li-1 UHF Transceiver,
(cid:120)  EPS and Battery Board : Aerocon customized Gomspace P31U-S and BP4-S units,
(cid:120)  GPS : SSTL SGR-05U with patch antenna,
(cid:120)  Solar Panels : Aerocon 3U and 1U side panels,
(cid:120)  Structure : AeroconNano 3U STR,
(cid:120)  Mechanisms : Aerocon MagBoom 3U , Aerocon AntBoom 3U, and
(cid:120)  Bus and cable bunde : Aerocon Kiss Bus and Cable Bundle.

Fig. 3: ITU pSAT II Bus – components and data bus perspective

These units are illustrated in Fig. 3. Aerocon designation is used for the in-house and indigineous components
designed under this project.  The electronic system supports two different types of data buses, namely the
indigenous “Kiss Bus” and the “CubeSatKit™ Bus”. This is also illustrated in Fig.3. The “CubeSatKit™ Bus”
has been developed by Pumpkin Inc. and has been widely accepted and used in board level OBC, EPS designs
across various other cubesat OEM suppliers.  In addition to the compatibility to this widely used bus, ITU pSAT
II supports an indigenous “Kiss Bus” which embeds CAN bus and extra regulated power lines, providing
flexibility of data rate and interface to new/payload components.

The OBC design, which is illustrated in Fig.4, implements the dual data bus and the interface to all the operation
required actuators on a PIC processor. Specifically, OBC directly drives the mangetometer boom and the
antenna spring loaded mechanisms. In addition embedded on the OBC unit, there is AstroDev Li-1 UHF
Transceiver module. Depending on the satellite power, the transceiver module can be configured to transmit
across 250mW to 4Ws at 9.6kps. This UHF uplink/downlik provides the main T&TC functionality on the ITU
pSATII. In the bus stack, there is also SSTL’s SGR-05U 12 Channel L1 C/A Code Space GPS Receiver which
provides the satellite’s position and velocity at 10m and 15 cm/s accuracy at %95 confidence interval. The EPS
and the battery board of the bus are customized Gomspace P31U-S and BP4-S units respectively. As configured
the EPS can provide two regulated power buses: 3.3V@5A and 5V@4A. The battery board embedds 10.4 Ah
and approximately 39Wh capacity.

Fig. 4: ITU pSAT II OBC design

As illustrated the bus design of the ITU pSAT II provides a considerable amount of power, flexibility and
capability with regards to carrying various types of payload units. As envisioned ITU pSAT II embeds two
experimental payload units excluding the ADCS system. These units are

(cid:120)  Camera/Star Tracker: Aerocon customized Sony Nex-5 camera unit, and
(cid:120)  S-Band Transmitter: Aerocon customized AstroDev Be-1 S-band transmitter with cap antenna.

The camera system is a customized and space environment modified Sony NEX-5 unit. This compact unit
embeds a 14.2 megapixel image sensor with photograph and video recording capability. The images taken by
this unit are not only used for earth imaging but also star tracking and thus absolute attitude determination. The
S-Band transmitter unit is a customized AstroDev Be-1 S-Band transmitter which allows us to downlink
precious science and image data at speeds up to 600 kbps. This unit can be configured to transmit up to 2 Watts.
In the next section, we review the hardware and the software of the experimental ADCS unit developed for the
ITU pSAT II. A larger set of these results can be obtained from the group’s publications [30-32].

3.

ATTITUDE DETERMINATION AND CONTROL SYSTEM

A.  HARDWARE LAYER

ADCS of ITU pSAT II consists of three distinct hardware layers integrating sensors, actuators, and ADCS
computer over the CAN bus. The sensor layer embeds a set of low-cost inertial and magnetic sensors, sun
sensors, a GPS receiver and an in-house developed multifunctional camera/star-tracker. The actuator layer
includes a redundant assembly of reaction wheels, magnetic torquer coils and an experimental set of
uPPTs(micro pulse-plasma thrusters).

The ADCS computer system design is illustrated in Fig. 5. The design embeds a Blackfin processor and
interfaces to the dual data bus system. In addition the magnetotorquer drivers and the reaction wheel drivers are
implemented on this compact unit. The ADCS computer provides analog and digital data interfaces to the sensor
board and the external magnetometer which is located at the end of the boom mechanism.

Fig. 5: ITU pSAT II ADCS computer design

In addition to the GPS unit which is embedded to the bus system, the ADCS houses the following attitude
determination sensors :

(cid:120)  External Magnetic Field Sensor : Honeywell HMR 3300
(cid:120)
(cid:120)  Sun Sensors : Silonex SLCD-61N8 photodiodes

Inertial Sensor and Internal Magnetic Field Sensor : Analog Devices ADIS 16405

The complete set of sensors provide acceleration, angular velocity, internal and external magnetic field strengths
on the three body axes. In addition, using the photodiodes on each panel, the panel illuminations and thus coarse
sun sensing data(i.e. the sun vector) is obtained after filtering. Current actuator assembly for ADCS system
consists of four magnetic torque generators and four reaction wheels completing a fully redundant set.  An in-
house developed (cid:80)PPT system is also included only for experimental purposes including additional momentum
dumping capability.

Magnetic torquers are embedded inside solar panel PCBs using layered windings. In the current design the
satellite house one magnetic torquer per axis and one more additional torquer(on standard z- axis) for
redundancy. The specifications of the design are given in Table 2.

Effective Area

3.31m2 achieved with 13 windings in 10 layers.

Max. Dipole Moment

0.33Am2 at 3.3V, 100mA

Table 2: Magnetotorquer specifications

The design of reaction wheels is based on requirement of being able to command the spacecraft for 1.5°/s
rotation per axis. For the reaction wheels Maxon EC 20 motors are used in tetrahedron formations .The
specifications of the designed reaction wheels are given in Table 3.

Angular Momentum Capability

1.05 mN.m.s

Rotor Moment of Inertia

Maximum Torque

6.23E-6 kg.m2

1 mN.m

Table 3: Reaction wheel specifications

Both of the actuators provide not only redundant three axis control but also capability to overcome the estimated
disturbance torques calculated for a nominal 700km sun synchronous orbit. The estimated disturbance torque
values are given in Table 4.

Disturbance

Aerodynamic Drag Induced Torque

Solar Pressure Drag Induced Torque

Residual Magnetic Field Torque

Approximate Value

3.6245E-08 [N.m]

4.9212E-09 [N.m]

1.2800E-07 [N.m]

Factor of Safety

3

Total Disturbance with Factor of Safety

4.9295E-07 [N.m]

Table 4: Approximate disturbance torques at 700km sun synchronous orbit

B.  SOFTWARE LAYER

The software component of the ADCS is illustrated in Fig. 6. In this architecture, the Orbit and Attitude
Propagator simulates full dynamics of the aircraft by integrating standard spacecraft attitude equations and orbit
equations with perturbations. These data along with sensor readings are sent to Estimation and Filtering layer,
where all sensor readings and propagation data is fused to generate an accurate state vector to be fed to Control
layer. These data are also sent back to propagation algorithms to update the current estimated state, so that they
can function more precisely at the next cycle. Finally estimated states are sent to control layer, where it takes the
order of current control mode from mission computer and generates commanded torque based on fault tolerant
architecture. Finally commanded torque is converted into Actuator Commands based on actuator associated with
current control mode and toque is exerted on the spacecraft. This cycle is run in every time step.

Fig. 6: ITU-pSAT II ADCS software architecture

Within the ADCS software architecture, we have used quaternion attitude parameterization for the model and
assumed rigid body dynamics with seven variables in total (four quaternions and three dimensional angular
velocity vector). In addition, the propagator also takes into account of disturbance torques on the spacecraft,
which were modeled as Gaussian white noise. Order of magnitude of total disturbance also gives us a rough
estimate on the necessary torque that has to be provided by actuators. Orbit propagator, simulates the orbital
trajectory of the vehicle based on initial conditions provided by Tracking Location Error (TLE) file. Propagator
integrates the orbital differential equations, which includes perturbation effects such as J2, in order to simulate
satellites position on the orbit. This propagator algorithm also includes an Earth Magnetic Field model
(IGRF11), which allows it to compute the magnetic field vector based on position of the spacecraft on the orbit.
This satellite’s position (and velocity) is estimated using the on-board GPS receiver data. Task of estimation and
filtering layer is to provide noise free and reliable state data to control algorithms, which is achieved via fusion
of various sensors and improvement of estimations by using a Kalman Filter. Since propagation algorithms
simulates nonlinear dynamics, an Extended Kalman Filter algorithm is used in this layer, to improve efficiency
of estimator on operating regions which involve nonlinear dynamics.

OPERATION MODES

Attitude control operation of the spacecraft has two modes:

1.  De-Tumbling Mode: This mode is activated to stabilize the spacecraft’s attitude from an initial high

angular velocity.

2.  Attitude Tracking Mode : This maneuvers the spacecraft's attitude from its initial position to a desired

orientation.

For the “De-tumbling Mode” a nonlinear control technique namely B-Dot algorithm is used.  In this mode the
primary actuators are the magnetotorquers. After satellite’s rotational kinetic energy is deflated, Linear
Quadratic Regulator is used for to carry out the “Attitude Tracking Mode” part. In this mode the primary
actuators are the reaction wheels. Embedded within the “Attitude Tracking Mode” is the momentum
unloading/dumping capability which transfers the excess (and saturating) momentum on the reaction wheels
using the magnetotorquers.

Fig. 7: The duty cycle of the Bdot process for detumbling

Especially after initial launch phase, spacecraft can possibly begin to spin in all directions with relatively high
angular velocity,  therefore have to be stabilized before entering into mission phase. Although reaction wheels
can be used for this purpose, high accuracy is not needed and the wheels are likely to saturate for under high
angular velocities. For this reason we prefer to use a B-dot controller, which extracts the magnetic field vector
as observed from spacecraft frame from magnetometer readings, takes it derivative and feed it to magnetorquers
to generate required torque, which will derive the derivative of magnetic field vector to zero. One important
point on B-Dot control algorithm is obtaining the time derivative of the magnetic field. This process cannot be
done with raw magnetometer data, because differentiating the magnetometer data will also differentiate sensor
noises. To estimate the derivative of the magnetic field a “State Variable Filter” with cut-off frequeny is used.
During stabilization, since magnetic field vectors magnitude can be assumed to be constant in the final phase,
driving its derivative to zero results in driving spacecraft’s angular velocity to zero. This process is illustrated in
Fig. 7. Using the SIL system, which is outlined in the next section, we have tested the detumbling phase of
operations across challenging scenarios. One of these scenarios is given in Table 5. Figure 8 illustrates the
performance of the system under sensor noise and actuator limitations. As it can be seen from Fig. 8, the system
provides stabilization just under five orbits.

Control Gain [C]

-4e4

Cut-off Frequency [ωc]

Variable : 0.6Hz and 2 Hz

ωsat  = [ωx   ωy   ωz]

[0.54   0.42   0.48]   rad/s

Table 5: Simulation parameters for detumbling scenario

    Figure 8: Simulation Results of the scenario in Table 5.

During simulations, it has been observed that the relatively low cut-off frequencies provide better performance
at relatively low angular speeds region. In comparison, higher cut-off frequencies provide better performance at
relatively high angular velocities. For that reason a variable cut-off frequency state filter is used for magnetic
field rate calculations. In this scenario, reduction in cut-off frequency has been performed about three and a half
hours after deployment. From that moment on, the controller has switched from 2.0 Hz to 0.6 Hz cut-off
frequency. This change in cut-off frequency can be observed in derivative of magnetic field. Consequently,
using two different cut-off frequencies at different phases of the detumbling operation provide high performance
during the whole detumbling process.

When the spacecraft is stabilized around any attitude (via De-Tumbling Mode) then Attitude Tracking mode is
used for high accuracy attitude command. Basically this mode makes use of linearized spacecraft equations and
applies an optimal control method by minimizing a linear quadratic performance index (LQR). Since estimation
layer includes a Kalman Filter, overall control scheme can be considered as a LQG controller. These types of
control algorithms have guaranteed robustness margins and moreover, actuator saturation constraints can be
embedded into performance index to avoid them. This control algorithm uses full state feedback, and makes use
of redundant assembly of reaction wheels to generate desired torque. When used in vicinity of trim point
controller performs well, but actuator saturation becomes harder to handle when large maneuvers are requested.
To avoid the saturation on actuators, large attitude command is decomposed into a sequence of smaller
magnitude attitude commands, and then the spacecraft is derived to final reference by taking each attitude

waypoint at a time. Spacecraft is commanded to translate to desired attitude from its initial position. Instead of
trying to go directly commanded attitude, spacecraft is forced to follow intermediate points between initial and
desired attitude. These waypoints get updated whenever spacecraft gets near to them, thus overall tracking
motion is not time based but event based.  Using the SIL system, which is outlined in the next section, we have
tested the attitude tracking phase of operations across challenging scenarios. One of these scenarios is given in
Table 6. Figure 9 illustrates the performance of the system under sensor noise and actuator limitations. As it can
be seen from Fig. 9, the system provides stabilization just on the order of 100 seconds. First the system is
stabilized to the nominal zero all case and then commanded to track the desired Euler angles.  It is important to
note the periodic momentum dumping from the reaction wheels during the whole attitude tracking maneuver
which allows the system to operate safely using both of the actuators.

Initial Euler Angles

ωsat  = [ωx   ωy   ωz]

[-15   -34   43]  deg

[0.021   0.024   0.018]  rad/s

Desired Euler Angles

[-33  57   -45]  deg

Table 6: Simulation parameters for attitude tracking mode

 Fig. 9: Simulation results for attitude tracking mode

FAILURE DETECTION AND RECONFIGURATION

Given the failure-prone nature of space-tolerance increased COTS and in-house developed hardware elements, it
is essential essential to a) develop on-orbit software which can detect, overcome or provide graceful degradation
of performance across various failures, b) test the ADCS software hardware on ground for a complex set of
hardware and software failure scenarios. ITU-pSAT II bus and ADCS operation architecture embeds a health
monitoring system [30-32] in order to cooperatively detect and successfully handle the highly possible failure
modes (such as sensor, actuator failures and errors). Basically the health monitoring system inspects sensed and
estimated state vector to analyze if there is an error in the sensors (noise and biases in sensors have already been
handled in filtering layer) or if there is a failed actuator. After detection, this system reconfigures the estimation
and the control layer through mode switching to account for the errors and the failures. Reconfiguration of
control architecture in case of actuator failure, performance degradation, and sensor bias has been extensively
studied in terms of adaptive and intelligent spacecraft control. Design of control laws, which take into account
actuator saturation and parametric uncertainty and a more extreme case of controlling spacecraft in under-
actuated situations has also been of interest. On these two lines of research, we refer the readers to [30-32] for a
short survey of related results.

Primary fault scenarios that we deal are actuator and sensor failures due to degradation of performance or
complete shutdown at worst situation. Failure detection algorithms for sensor and actuator works independent of
each other therefore it is possible to deal with a multiple failure scenario where sensor and actuator failure
happens at the same time.

Fig. 10 : Fault tolerant control and health monitoring system

1.  Sensor Failure Detection : Sensor readings, which are degraded by noise, are handled by sensing layer

and estimation layer, as well as biased readings. These kinds of biases are likely to happen in
accelerometers and gyros, which must be handled online in order to avoid sending false state data to
the control algorithms. Filtering and estimation layer achieves bias estimation, by comparing sensed
state data and state data estimated by estimation layer. It generates an initial bias estimation then
updates this estimate based on difference between state vectors generated by sensor data and estimation
layer. Another possible scenario is failure of sensors (either turning off or giving highly erroneous data)
during mission, rendering some of the sensor useless. Sensor failure detection layer in Fig. 10 identifies
the failed sensor, and isolates it from the estimation layer such that output of the failed sensor doesn’t
affect the performance of the estimation layer.

Fig. 11 : Multiple Failure Model and failure identification

2.  Actuator Failure Detection : Actuator failure is possible to detect using Multiple Model Switching

Scheme. This failure detection process is shown in Fig. 11. Principle of this detection algorithm is to
generate state data based on all possible actuator failure scenarios (very similar to attitude
propagation), and compare it with the current state data, to generate a performance index (which is
integrated over time). When performance index associated with that mode is small compared to others,
actual model is more likely to be in that failure mode. When minimum is taken over all possible failure
data, the argument, which minimizes the performance index, indicated the failure mode of the actual
system. If nominal model appears to minimize it, system continues to perform in full configuration.
Whenever a failure mode minimizes the index, failure is detected and redundancy management is
informed. Since an under-actuated spacecraft is very difficult to control precisely, redundant numbers
of actuators are usually found in spacecrafts to take caution against actuator failures. Since all control
algorithms in Fig. 11, generate a 3 dimensional commanded torque Redundancy management
(sometimes referred as control allocation layer) have to distribute them among redundant actuators.

Using the failure detection, we have tested the algorithm across actuator failure scenarios at both the detumbling
and the attitude tracking modes. In the detumbling mode, we assume the failure of y-axis magnetotorquer using
using the identical nominal scenario as given in Table 5. In Fig. 12, the simulation results show that, even if one
of magnetorquer is disabled, the satellite’s  angular velocity converges to zero eventhough the settling takes
more time.

Fig. 12: Simulation Results for y-axis magnetotorquer failure while performing detumbling

For the attitude tracking mode, we assume that one of the reaction wheels fail during the attitude tracking
maneuver scenario as given in Table 6. In Fig. 13 the simulation results show a robust performance given the
the tetrahedron reaction wheel structure which provides inherent redundancy. In the next section, following [30-
32], we review the HIL and SIL system developed for this project. For extended results on the SIL/HIL, we
refer the readers to [30-32].

Fig. 13: Simulation Results for one reaction wheel failure while performing attitude tracking

3. SOFTWARE AND HARDWARE IN THE LOOP SYSTEM
To test the actual behavior of the control system elements during execution of real mission of the spacecraft
including failure scenarios, we have developed a software and hardware-in-the-loop test system. The software
and hardware-in-the-loop system consists of an in-house developed air bearing table (to simulate attitude
dynamics) and Helmholtz Coil system (to emulate Earth's magnetic field) in addition to the computer rack
which provides high-precision orbit, attitude and environment “truth-model” propagation with 3D orbit and
attitude visualization. Overall architecture is suitable for testing under number of possible hardware failure
scenarios and control modes, and greatly aids the development process of the ADCS and bus components.
Particular difficulty with this situation is how to make a develop a “truth model” which will act as the actual
state of the spacecraft in the space, and will be tried to estimate as good as possible by filtering layer and sensor
emulations. It is pointless to use models in attitude and orbit propagators as truth models, since this situation
will not present any interesting results due to indifference between estimated and actual states other than
disturbance. For this purpose we incorporate a commercial space mission simulator “Satellite Toolkit” (STK)
developed by Analytical Graphics Inc. into our simulation setup. Satellite Tool Kit is widely used software for
developing and analyzing virtual space missions. STK can be used for calculating contact time between ground
and satellite, determining critical vectors such as magnetic field vector and determining other attitude
information rapidly by communicating with a MATLAB/Simulink model. STK serves as a truth model since it
takes into account disturbances and perturbations from large number of sources and uses mathematical models
far more complex than the ones we used in propagation algorithms. In addition since it is possible to extract the
actual state data from STK we can see how well estimation layer works.

A.  SOFTWARE-IN-THE-LOOP SYSTEM ARCHITECTURE

Components of SIL simulator are shown on Fig. 14. A cycle of simulation can be explained as follows: ADCS
software (including propagation, filtering and control algorithms) is provided either by an interface in STK
Rack (INT) or by some outside source, such that anyone with an ACDS software can connect to simulation
setup and test his/her algorithms. Software receives state update from STK over UDP channel, sensor emulation
(such as noisy readings, magnetometer calibration errors, gyro biases) are applied to state vector to simulate
actual sensor reading during mission. Based on these data ADCS software applies the filtering and control
architecture detailed in second section to generate commanded torques to spacecraft and sent (via CAN Bus in
INT, via UDP in outside source) to STK software to simulate its effect on spacecraft model. Communication
between ADCS software (which is modeled in MATLAB Simulink) and STK is achieved through another
Simulink model in STK computer, which also adjusts the synchronicity between the software. Finally STK open
a special 3D visualization window to observe attitude and orbit of the test spacecraft and this visualization is
displayed via a projector.  In in Fig. 14, a STK screenshot from an SIL simulation is also displayed.

Fig. 14: SIL System and STK Visualization

Our experience on SIL simulations with iterative design resulted on control estimation and health management
algorithms which are suitable for a nano sized satellite with three-axis precise attitude control.

B.  HARDWARE-IN-THE-LOOP SYSTEM ARCHITECTURE

As the last step, actual hardware (sensor package, actuators and mission computer) is planned to be integrated
into simulation environment along with experimental platforms. The main aim here is to test the integrated
performance of the system under a realistic space environment (i.e. magnetic field and three axis micro-g
motion).  Towards this goal we have designed a HIL system. The computer rack system of the HIL consists of
two rack PCs and one optional monitor which displays satellite simulation visual. The rack PCs not only
simulate the S/C, environment, orbit and attitude propagation but also provide emulations of bus and sensor,
retrieved by interface rack running MATLAB Simulink model. Interface Rack generates data updated by
satellite hardware simulation system and STK Rack generates position and magnetic field values as in SIL
(using another MATLAB Simulink model) as response and also displays satellites movements.

For simulating space environment, two primary components were integrated into simulation. First one is an in-
lab-built frictionless air-bearing table to simulate spacecrafts attitude dynamics. The seconds one is a Helmholtz
Coil system for simulating Earth’s magnetic field on the orbit of the spacecraft. These coils are able to provide a
homogenous magnetic field around spacecraft. When combined with air- bearing table, spacecraft should be
able stabilize itself on the air bearing table via exerting torque with reaction wheels and magnetotorquers. The
complete setup is illustrated in Fig. 15.

Fig. 15: HIL system diagram and hardware :  integrated air bearing table and helmholtz coil platform

4. CONCLUSION

ITU pSAT II is the second student satellite project from ITU FAA Controls and Avionics Laboratory, which
aims to design and on-orbit demonstrate a standardized bus and a novel ADCS for pico and nano sized satellites
(1-10 kg) with multi objective applications. Main aim of this project is to demonstrate specific challenges and
solutions for ADCS design for nanosatellites, which require a high precision, fault tolerant and reconfigurable
control system. One of the bigger challenges in nanosatellite technologies is development of robust attitude
determination and control systems which will allow these satellites’ attitudes to be precisely known and
controlled to obtain high quality mission data on demand. ITU pSAT II ADCS is envisioned to fulfill that
requirement. ITU pSAT II is scheduled for launch on 2012 Q3.

In this paper, we presented the development stages of ITU pSAT II, focusing on the ADCS hardware and
software implementations suited for high precision attitude control for small satellite. In addition, we presented
the  development of a SIL/HIL testbed which emulates the spacecraft dynamics and space environment.

This work is supported under TUBITAK 108M523 Project.

5. REFERENCES

[1]  Can Kurtuluş, Taşkın  Baltacı, Barış Toktamış, İlke Akbulut, O. Oğuz Haktanır, Gökhan İnalhan, , M.Fevzi Ünal ve A
Rüstem  Aslan,  “İTÜ  pSAT  I:  Getting  Ready  For  Launch,”  Proc.  of  International  Workshop  on  Small  Satellites,
Istanbul, Turkey, 2008.

[2]  Can Kurtuluş ve Gökhan İnalhan, “Analysis of İTÜ NXG I Next Generation Technology Demonstrator from a Controls
Perspective”, Proc. Of  7th International ESA Conference on Guidance, Navigation & Control Systems, Tralee, Ireland,
2008.

[3]  Can  Kurtuluş,  Taşkın  Baltacı  ve  Gökhan  İnalhan,  “A  Next  Generation  Test-Bed  for  Large  Aperture  Imaging

Applications”, Proc. of 21st Annual Conference on Small Satellites, Logan, ABD, 2007.

[4]  Can  Kurtuluş,  S.M.  İmre,  G.  Yüksel  ve  Gökhan  İnalhan,  “Technology  Drivers  and  Challenges  For  Next  Generation
Distributed  Spacecraft  Systems”,  3rd  International  Conference  on  Recent  Advances  in  Space  Technologies,  İstanbul,
Türkiye, 2007.

[5]  Can Kurtuluş, Taşkın  Baltacı, M. Ulusoy, B. T. Aydın, B. Tutkun, Gökhan İnalhan, N.L.O. Çetiner-Yıldırım, Turgut
Berat  Karyot,  Cuma  Yarım,F.O.  Edis,  C.  Haciyev,  A.R.  Aslan  ve  M.F.  Ünal,  “İTÜ-pSAT  I:  Istanbul  Technical
University Student Pico-Satellite Program”, 3rd  International Conference on Recent Advances in Space Technologies,
Istanbul, Turkey, 2007.
[6]  http://polysat.calpoly.edu/
[7]  http://courses.ece.uiuc.edu/cubesat/mission.htm
[8]  http://www.und.nodak.edu/org/zamboni/
[9]  http://www.conolley.com/cubesat/
[10]  http://www.mae.cornell.edu/cubesat/
[11]  http://space.auburn.edu
[12]  http://www.css.tayloru.edu/~physics/picosat/indexes/purpose.htm
[13]  http://www.space.t.u-tokyo.ac.jp/cubesat/index-e.html
[14]  http://www.ssel.montana.edu/merope/mission/goals.html
[15]  Jaime  Esper,  Peter  V.  Panetta  ,  Dr.  Michael  Ryschkewitsch  ,  Dr.  Warren  Wiscombe  and  Steven  Neeck,  2nd  IAA
International  Symposium  on  Small  Satellites  for  Earth  Observation  NASA-GSFC  nanosatellite  technology  for  Earth
science missions Acta Astronautica Volume 46, Issues 2-6 , January-March 2000, pp. 287-296

[16]  Space Technology Guide, FY 2000-01, Department of Defense
[17]  Hendrik  Lübberstedta,  David  Koebela,  Flemming  Hansenb  and  Peter  Brauerc,  4th  IAA  International  Symposium  on
Small Satellites for Earth Observation MAGNAS-Magnetic Nanoprobe SWARM, Acta Astronautica Volume 56, Issues
1-2 , January 2005, pp. 209-212

[18]  Robert  Schulte,  TUBSAT-N,  an  ultra  low  cost  global  communication  nanosatellite  system,  Air  &  Space  Europe,

Volume 2, Issue 5, September-October 2000, pp. 80-83

[19]  N.R. Gans, W.E Dixon, R. Lind and A. Kurdila, “Hardware in the loop simulation platform for vision based control of

unmanned air vehicles”, Mechatronics, 19, pp.1043-1056. 2009

[20]  S.  Rainer,  K.  Brieß  and  M.  D'Ericco  “  Small  satellites  for  global  coverage:  Potential  and  limits”,  ISPRS  Journal  of

Photogrammetry and Remote Sensing, 2010

[21]  Shiokawa,  K.  et  al.”  ERG  –  A  small-satellite  mission  to  investigate  the  dynamics  of  the  inner  magnetosphere”.

Advances in Space Research, 38, pp. 1861-1869, 2006.

[22]  Analytical

Graphics
modules/stk-integration

STK/Integration.

http://www.stk.com/products/by-producttype/applications/stk/add-on-

[23]  H.  Helvajian  The  generation  after  next:  satellites  as  an  assembly  of  mass-producible  functionalized  modules.  In  H.

Helvajian & S. Jason (Eds.), Small satellites: past, present, and future . Aerospace Press. 2009

[24]  Laurent Marchand, John Hopkins, Fabien Filhol, Micro and Nano Industry Space Days, ESA/ESTEC, 30 May 2006
[25]  Neil Barbour and George Schmidt, Inertial Sensor Technology Trends, IEEE Sensors Journal, Vol. 1, No. 4, December

2001

[26]  Peter  Rossoni,  Peter  V.  Panetta, Developments  in  Nano-Satellite  Structural  Subsystem  Design  at  NASAGSFC,  13  th

AIAA/USU Conference on Small Satellites

[27]  V.J.  Lappas  ,  WH  Steyn  ,  C.I.  Underwood,  Attitude  control  for  small  satellites  using  control  moment  gyros,  Acta

Astronautica, Volume 51, Issues 1-9, July-November 2002, pp. 101-111

[28]  Demoz Gebre-Egziabher, Gabriel H. Elkaim, J. D. Powell and Bradford W. Parkinson, A Gyro-Free Quaternion-Based
Attitude  Determination  System  Suitable  for  Implementation  Using  Low  Cost  Sensors,  Position  Location  and
Navigation Symposium, IEEE 2000

[29]  M.L. Prydderch, N.J. Waltham , R. Turchetta , M.J. French , R. Holt , A. Marshall, D. Burt , R. Bell , P. Pool , C. Eyles
,  H.  Mapson-Menard,  A  512512  CMOS  Monolithic  Active  Pixel  Sensor  with  integrated  ADCs  for  space  science,
Nuclear Instruments and Methods in Physics Research A 512 (2003) pp. 358-367

[30]  N.  K.  Ure,  Y.  B.  Kaya,  G.  Inalhan,  The  Development  of  a  Software  and  Hardware-in-the-Loop  Test  System  for  a
Reconfigurable  and  Fault-Tolerant  Nano-Satellite  Attitude  Determination  and  Control  System:  ITU-PSAT  II  ADCS,
2011 IEEE Aerospace Conference, March 5–12 2011, Big Sky, Montana, 2011

[31]  U.  Eren,  Attitude  Determination  and  Control  System  Design  for  Nanosatellites,  B.Sc.  Thesis,  Istanbul  Technical

University, Faculty of Aeronautics and Astronautics, 2011

[32]  E.  Koyuncu  et.  al.,  ITU-pSAT  II  :  5th  High  precision  Nanosatellite  ADCS  Development  Project,  International

Conference on Recent Advances in Space Technologies, 2011,Istanbul,Turkey
[33]  The Cubesat Program, Cal Poly SLO, Cubesat Design Specifications Rev.12, 2011

View publication stats

