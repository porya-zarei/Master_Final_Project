5
2
0
2

g
u
A
6
2

]

O
R
.
s
c
[

1
v
4
6
1
9
1
.
8
0
5
2
:
v
i
X
r
a

(Preprint) AAS 25-778

REAL-TIME TESTING OF SATELLITE ATTITUDE CONTROL WITH
A REACTION WHEEL HARDWARE-IN-THE-LOOP PLATFORM

Morokot Sakal*, George Nehma*, Camilo Riano-Rios†, and Madhur Tiwari†

ABSTRACT

We propose the Hardware-in-the-Loop (HIL) test of an adaptive satellite attitude control system
with reaction wheel health estimation capabilities. Previous simulations and Software-in-the-Loop
testing have prompted further experiments to explore the validity of the controller with real momen-
tum exchange devices in the loop. This work is a step toward a comprehensive testing framework for
validation of spacecraft attitude control algorithms. The proposed HIL testbed includes brushless
DC motors and drivers that communicate using a CAN bus, an embedded computer that executes
control and adaptation laws, and a satellite simulator that produces simulated sensor data, estimated
attitude states, and responds to actions of the external actuators. We propose methods to artificially
induce failures on the reaction wheels, and present related issues and lessons learned.

INTRODUCTION

Reaction Wheel (RW) arrays are a crucial means for attitude control on many satellites due to
their ability to precisely execute the control actions required for attitude maneuvers via exchange
of angular momentum.1 As such, it is a highly critical subsystem that incorporates levels of redun-
dancy in the case of actuator faults. Extensive research has been made to enhance the capabilities
of attitude controllers so that they minimize the hardware cost and computational load as much
as possible whilst being able to guarantee tracking.2–5 Methods such as Sliding Mode Control
(SMC),6 Model Predictive Control (MPC),7, 8 neural networks9 as well as a variety of adaptive con-
trollers10–14 have been proposed for attitude control, each with varying capabilities and degrees of
success. The advantage of adaptive controllers is their ability to compensate for uncertainties in the
system dynamics, whilst maintaining stability.

In our previous work,15 we proposed a method to simultaneously learn the health of a satellite’s
RWs and attitude tracking under scenarios of failing or degraded RW(s). Our method involves
a Lyapunov-based adaptive controller with an integral concurrent learning (ICL)-based adaptive
update law that ensures convergence of the estimated health of the RWs once a finite excitation
condition is met. This controller was shown to guarantee exponential convergence of error states
and RW health estimates. We demonstrated via MATLAB/Simulink-based numerical simulations
that the controller correctly estimated the health of each RW and performed the alternating attitude
tracking reference required by the mission. We presented simulations with arrays of 4 and 6 RWs,
a varying number of degraded RWs, and varying levels of degradation. A Software-in-the-Loop

*Ph.D. Student, Aerospace, Physics and Space Sciences Department, Florida Institute of Technology
†Assistant Professor, Aerospace, Physics and Space Sciences Department, Florida Institute of Technology

1

(SIL) test of the controller was conducted to test the real-time capability with embedded hardware
(NVIDIA Jetson Nano), achieving comparable results.

The promising SIL experiments have prompted us to continue with a Hardware-in-the-Loop
(HIL) test to validate the adaptive controller in more realistic conditions, including hardware lim-
itations, sensor noise, and communication latency that are difficult to replicate in simulation. In
addition, we aim to use this controller to demonstrate and validate our envisioned modular testbed,
currently under development, at the Space Vehicle and Robotics (SVR) lab at the Florida Institute
of Technology.

HIL testing is a vital aspect in the development of real, flight-ready controllers and actuator-driven
systems, as it is a mission-critical system that can afford little to no failures. The sim-to-real gap is
large and poses a number of issues when developing control systems, the greatest of which is the
ability to model the behavior of the actuating system in simulation as close to the real behavior as
possible. RW dynamics, although can be approximated in simulation, are often hard to be precisely
emulated due to their physical complexity and interaction with motor drivers, sensors, inner control
loops, among others. Hence, the need to verify the health estimation capability of a controller using
real hardware is of great importance.

The contributions of this paper are two-fold:

• We develop a Hardware in the Loop testing architecture to verify the actuator health estima-

tion performance of the adaptive controller with real RWs.

• We highlight the problems encountered during HIL testing of a RW array, and provide solu-

tions and discussion on each.

This paper is organized as follows. First, we provide an overview of the adaptive controller that
is being tested in this HIL setup. Then we present the architecture design of the testbed. The next
sections describe the experimental setup and procedures to integrate each component to realize the
test. Finally, we discussed the results and concluded with future work.

ADAPTIVE ICL CONTROLLER

Since the focus of this paper is to highlight and analyze the HIL testing for this adaptive controller,
this section only briefly overviews the design and architecture of our controller. For further, more
detailed explanation and derivation of the controller and its stability analysis, we refer the reader to
our previous paper.15

The Equations of Motion for the attitude of a spacecraft with N RWs are given as

J ˙ω = −ω × (Jω + JRW GΩ) + GΦu

˙σ =

1
4

(cid:2)(cid:0)1 − σT σ(cid:1) I3 + 2σ× + 2σσT (cid:3) ω,

(1)

(2)

where ω ∈ R3 is the spacecraft angular velocity expressed in the body coordinate system,
σ ∈ R3 is the vector of Modified Rodrigues Parameters (MRP) that represent the orientation of
the spacecraft with respect to the inertial frame, Ω = [Ω1, Ω2, · · · , ΩN ]T ∈ RN is a vector con-
taining the N RW angular velocities, u = −JRW ˙Ω = [u1, u2, · · · , uN ]T ∈ RN is the control input
that represents the torque applied by each RW, J ∈ R3×3 is the total inertia matrix, JRW ∈ R>0

2

· · · , ϕN } ∈ RN ×N is the
is the inertia of the flywheels about their spin axis, Φ = diag{ϕ1, ϕ2,
uncertain RW health matrix, G = {ˆs1, ˆs2, · · · , ˆsN } ∈ R3×N is the RWA configuration matrix,
and ˆsi ∈ R3 is the direction of the ith RW’s spin axis expressed in the body coordinate system. The
matrix Im ∈ Rm×m represents an identity matrix of dimension m × m, and a× ∈ R3×3 is a the
skew-symmetric matrix built with the vector a = [a1, a2, a3]T ∈ R3.

The designed auxiliary control law ud that stabilize the spacecraft attitude is

ud = ω × (Jω + JRW GΩ) + J ˜R ˙ωd − J ˜ω× ˜Rωd + 4JB−1

(cid:20)

−

1
4

˙B ˜ω − α ˙σe − Kr − βσe

(cid:21)

, (3)

where β ∈ R>0 is a constant control gain, α ∈ R3×3 is a symmetric, positive definite control gain
matrix, ˜R ∈ R3×3 is a rotation matrix between the spacecraft desired and body frames, σe ∈ R3 is
the error MRP and r = ˙σe + ασe ∈ R3 is a modified error state.

The torque commands to be sent to the RWs, u, are recovered as

(cid:17)†

(cid:16)

G ˆΦ

u =

ud,

(4)

where (·)† is the Moore-Penrose pseudo-inverse of (·) and ˆΦ can be obtained by numerically inte-
grating the adaptation law given by:

˙ˆθ = proj

(cid:40)

1
4

ΓY T (cid:0)J −1(cid:1)T

BT r + ΓK1

Ns(cid:88)

i=1

(cid:16)

(cid:17)
Jω(t) − Jω(t − ∆t) + Ui − Yi ˆθ

Y T
i

(cid:41)

,

(5)

where ˆθ ∈ RN is the estimate of the vector containing RWs’ health factors θ = [ϕ1, ϕ2, · · · , ϕN ]T ,
Γ, K1, ∈ RN ×N are constant, positive definite adaptation gain matrices, Ui ∈ R3 and Yi ∈ R3×N
are integrals of input-output data terms, and the matrix B ∈ R3×3 is a matrix used in the MRP
kinematics.16

TESTBED ARCHITECTURE DESIGN

Figure 1 illustrates the overall architecture of the HIL testbed developed for the experiment.
This architecture extends the already tested and proven SIL setup15 with ROS2 middleware used as
for communication between computers in a local network.17 The HIL testbed includes a Satellite
Simulator implemented in Matlab/Simulink running on a Linux computer, an NVIDIA Jetson Nano
embedded computer hosting various software and algorithms undertest, and the RW testbed, which
consists of hardware components including four Maxon EC 60 flat brushless motors18 emulating
RWs, each controlled by a digital position controller EPOS4 Compact 50/5CAN19communicating
via USB/CAN bus, and an artificial fault injection mechanism used to simulate various RW fault
scenarios.

As shown in Figure 1, the ROS2 nodes in the HIL test setup utilize the publisher/subscriber model.
Satellite Simulator Node (SatSimNode) runs the simulation of the satellite dynamics, environment,
actuator models, and sensor models. The sensor models, including sun sensors, magnetometers,
and gyroscopes, are modeled by adding noise and realistic sampling rates. The simulated rates are:
gyroscope 10 Hz, magnetometer 2 Hz, and sun sensors 2 Hz. The noisy sensor outputs are processed

3

Figure 1: Overview of Testbed Architecture.

by the attitude determination block, which employs an Extended Kalman Filter (EKF) based on
multiplicative quaternion20 to estimate the attitude states, i.e., satellite inertial angular velocity ω,
and quaternion → MRPs σ. The SatSimNode provides desired attitude states, satellite configuration
parameters, and estimated states data. It also receives the controller outputs and actuator states data,
i.e., RW angular velocity and current measurements back from the testbed.

The embedded computer operates two ROS2 nodes: the ControllerNode and the RwNode, each
designated for a specific function. The ControllerNode is implemented in Python (rclpy) while
the RwNode is implemented in C++ (rclcpp). Using the estimated attitude states, desired space-
craft states, and satellite configuration, the ControllerNode calculates the required torque command.
Depending on the test configuration, the torque command is converted to angular velocity or cur-
rent commands. The ControllerNode publishes this command to the network via a ROS2 topic.
The RwNode then subscribes to this command topic and forwards the commands (using the EPOS
Command Library written in C++) to the digital controller via a USB/CANopen interface. Simul-
taneously, the RwNode acts as a publisher and delivers angular velocity and current measurement
as the actuator states at the rate of 20 Hz back to the network, which is received by both the Con-
trollerNode and SatSimNode. The final step is to create the closed-loop HIL system and ensure
synchronization between the simulation model and the physical hardware.

The testbed is built with a modular design. It is possible to swap in new actuators, sensors, or
embedded computers with minimal changes to the overall architecture. It is flexible to make the
transition between testing modes, from pure simulation, also called Model-in-the-Loop (MIL), to
SIL, or HIL modes. This architecture is scalable to support future upgrades, such as air-bearing
tests, satellite integration and testing campaigns, and comprehensive end-to-end system tests.

EXPERIMENTAL SETUP

Figure 2 shows the experimental setup used to validate the controller and its RW health estima-
tion capability with actual hardware. The NVIDIA Jetson Nano is connected to one digital motor
controller via USB interface, and the remaining motor drivers are interconnected through a CAN
bus, using the CANopen protocol. A dedicated power supply unit is installed to power the elec-

4

HIL Testbed[ROS2 Topic]ConfigurationsDesired statesEstimated statesControllerNode[ROS2 Topic]Parameter estimatesPerformance MetricsExecutiontime per stepCPU loadTracking accuracyEstimation errorsMemory usageRwNodeFailure Injection-Manually-ElectronicallyNVIDIA Jetson Nano[ROS2 Topic]Actuator statesEmbedded Onboard Computer[ROS2 Topic]Control cmdsMiddlewareSatellite Simulator (Matlab/Simulink)PC-LinuxEnvironmentsGuidanceSensors ModelActuators ModelAttitude DeterminationControllerSatSimNodePlotsSatellite EoMsReaction Wheels-EPOS4 Digital Controller-EC60 Brushless MotorControl cmdsActuator statesUSB/CANOpentronics. The Jetson Nano communicates with MATLAB/Simulink wirelessly in a local network and
exchanges data using the ROS2 middleware.

Figure 2: HIL Experimental Setup

Performing a HIL test introduces a number of complexities that are either ignored or not present
in simulation, one of which is the assumption that all states of the RW are available to the controller,
or whether the inner controller loop of the motor controller is closed via current or angular velocity.
These considerations greatly impact the design of the controller and whether a real-time HIL test is
feasible or representative.

As a first proof of concept, we artificially induce failure through manipulation of the control
command being sent to each RW, as is common practice in many recent literature.21–30 Testing full
failure of the RW is simple, the power stage of the failing RW can be disconnected, whilst other
failures can be induced by manipulating the amount of effort that is sent as command to the motor
controller with respect to the effort output by the main attitude controller. This is normally a scaling
factor that is applied to the required control effort.

5

Power Supply UnitNVIDIA Jetson Nano + Wifi-AdapterCAN Bus CablesReaction Wheels (Brushless DC Motor + Digital Motor Controller)Satelite SimulatorROS2 Middleware EXPERIMENTAL PROCEDURE

The process of transferring a completely simulated system to one where the actuators and sensors
are real hardware connected to the integrated, embedded controller and state estimator is a large
jump to complete altogether. As such, we break down the process of implementing the physical
hardware in the loop in multiple steps to ensure accuracy and reliability. The first step, as seen in
our previous work15 included the SIL testing of the controller executed on an embedded computer.
In order to completely verify the HIL tests, the breakdown of how we integrated certain components
is shown in Figure 3. After the SIL test, which verifies that the embedded computer can run the
control algorithm accurately and efficiently as compared to the simulation, we begin by adding the
reaction wheels, with their CAN bus motor drivers and integrated sensors in the loop. The HIL test
was further broken down to three subsequent steps: HIL-a, HIL-b, and HIL-c. The goal of each test
is to compare the behavior of the model in the Satellite Simulator to a hardware implementation.
Once verified, the model in the Satellite Simulator can be gradually removed and replaced with a
hardware implementation.

Figure 3: Experimental Procedures

HIL-a: Testing Reaction Wheel Response

Current Commands
In order to create the most realistic simulated model of the RW and motor
driver set up, control torque commands calculated by the adaptive controller are passed through a
transfer function that is designed to mimic the behavior of the motor driver and RW operating in
closed-loop torque control. As such, the first test is to pass the control commands, converted to
current via the torque constant for the brushless motor,18 from the simulator to the RW and motor
drivers and then observe their behavior in comparison to the simulated RWs. Hence, the simulation
propagates the equations of motion (EOM) and RW dynamics, with the torque commands being fed
in parallel through the ROS2 network to the real RW and motor drivers, but maintaining the control-
loop closed with the simulated RWs. The built-in current sensor reports back the actual current, and
the Hall-effect sensor measures the angular velocity of each RW.

As the simulation runs, we compare the output torques and angular velocities between the simu-
lated and real RWs to assess the differences between them. Parameters of the RW such as inertia,

6

Test ModesHost (Satellite Simulator)Onboard (Jetson Nano)HardwareRWsControllerRW ModelSatSimNodeControllerNodeRwNodeMIL✓✓╳╳╳╳SIL╳✓✓✓╳╳HIL-a✓✓✓╳✓✓HIL-b✓╳✓╳✓✓HIL-c╳╳✓✓✓✓ModelPhysicalLegend: ✓ active ·  ╳ not usedTable 1: Satellite Configuration Parameters (Simulation vs. HIL )

Parameter

Simulation

HIL

m
J

G

Max RW torque
Max Ω



65
diag{0.44, 0.70, 0.70}
0.5774 −0.5774
0.5774
0.5774

20
diag{0.30, 0.42, 0.42}
0.5774 −0.5774
0.5774 −0.5774 −0.5774
0.5774
0.5774
0.5774
50 × 10−3
3.66 × 102

20 × 10−3
1.04 × 103







Units

kg
kg·m2

–

N·m
rad/s

mass and torque constant were taken from the datasheet of the brushless motors and included in the
simulated RWs. Table 1 shows satellite configuration parameters that were adjusted to reflect the
physical hardware specifications used in the HIL test.

The RW motor drivers have two modes of operation: torque (current) command and angular ve-
locity command. In order to reduce complexity and added calculations that may introduce unwanted
behaviors, we decided to control the RW’s based on a given torque command. In order to do this on
the RW hardware, a current command would be delivered to the motor drivers which in turn would
use their internal PID feedback controller to track this command. We derive the current command
from the torque required by the controller

Icmd = Kt · τcmd

(6)

where, Kt is the torque constant of the RW motor, given in the datasheet.

As seen in Figure 4a, the primary issue with this method of control commands is that the RWs
have a current deadband of around 300mA, throughout which any current commanded would result
in no output from the RWs. This is not an uncommon issue31–33 but in our case, because the
desired torque commands were generally small and would eventually converge to zero, a majority
fell within this deadband, as such the RWs were unable to actuate. A common solution to this issue
is to kickstart the RWs when the simulation starts to break through the deadband, and although this
momentarily helped alleviate the deadband issue, the motors quickly became unresponsive. Another
solution that proved unsuccessful was to append the command signal with the sign of the command
multiplied by the deadband region, Icmd = Icmd + sign(Icmd) · 300. As evident in Figures 4b this
resulted in large jumping in the RW angular velocity and did not track the simulated angular velocity
closely. As such, our next solution to this problem was to convert the output torque commands of
the controller into angular velocity commands.

Velocity Commands
In order to convert the torque commands that are output from the adaptive
controller into velocity commands that are acceptable to the RW motor drivers, the following steps
must occur. First, the commanded simulated torque for each RW is saturated by the maximum
torque that is possible by each RW, given in its respective datasheet. Then, the torque command is
divided by the inertia of the wheel to obtain angular acceleration

7

(a) Controller current commands and deadband
adjusted current commands sent to RWs.

(b) Angular Velocity of Simulated RW and real
RW with deadband

Figure 4: Current commands and angular velocity plots showing the deadband issue when generat-
ing torque commands from the adaptive controller.

˙Ωcmd =

τcmd
JRW

,

(7)

and the velocity command obtained using the forward-Euler integration algorithm which proved
to be sufficient. Velocity saturation was also applied to ensure commands within the motor specs.
These velocity commands can be tracked by the RWs and do not suffer from the deadband issue.

To verify the correct operation of the RWs with the velocity commands generated from the sim-
ulator, a similar experiment was performed where the main control loop is still closed with the sim-
ulated RWs that receive torque commands, and the corresponding computed velocity commands
were also sent to the physical RWs. Figure 5 demonstrates that although the measured velocity
signal includes a small amount of noise, its profile closely follows that of the simulated RW.

HIL-b: Adding Physical RWs in the Main Control Loop

Once it was verified that the simulated and real RWs were behaving similarly for given control
commands, the next step in achieving a complete HIL test was to feed the angular velocities and
angular accelerations from the real RWs into the simulation, as required to propagate the EoMs as
in Equation (1). This was a major step in the process as it introduced a number of issues that needed
to be addressed to bridge the sim-to-real gap.

Dealing with noisy measurements from the RWs’ angular velocities and currents, especially ve-
locity measurements near zero speed, a known issue related to Hall-effect sensors,34 added to the
need to compute the corresponding angular accelerations to be able to propagate the EoMs, became
an important issue. We attempted two approaches to compute the angular acceleration (a) by di-
rectly converting the RWs’ current measurements to angular acceleration and (b) through numerical
differentiation of the velocity measurements, then using low-pass filters to smooth out the signals.
For the approach (a), we found a similar issue earlier with the deadband of the current measurement,
which resulted in an incorrect mapping between current and angular acceleration. For approach (b),
it introduced a phase shift (delay) in the signal, which is quite significant to be fed into the EoMs,

8

0100200300400500Time[sec]-400-300-200-1000100200300400Current[mA]RW1RW1adjusted0100200300400500Time[sec]-1000-5000500100015002000+[rad=s]+1measured+1simFigure 5: Comparison of simulated and physical RWs’ angular velocities under angular velocity
command.

resulting in an unstable system.

(a)

(b)

Figure 6: Wheel acceleration from current sensors and numerical derivative

To mitigate the issue with noisy sensor data, we fed the calculated velocities and angular accel-
erations into the satellite’s EoMs instead of actual accelerations obtained from measurements, as
shown in Figure 7. As a result, current measurements were excluded from the setup, and only ve-
locity measurements were used to interface with the simulator. Because the control and adaptation
laws under test only require estimated satellite states and RWs’ angular velocity measurements as
inputs (as shown in Equations (3), and (5)), and EoMs propagation is only required for numerical
simulation and not for real satellite operation, the proposed data exchange remains representative.

However, the disconnection between the measured (experienced) RWs’ angular velocities, and
the calculated angular accelerations being fed into the EoMs, prevented us from physically inducing
RW failures or degradation. In order to physically induce failure on a RW, an angular acceleration

9

050100150200250300350400450500Time[sec]0200400600800100012001400+[RPM]+sim+measured0100200300400500Time[sec]-200-150-100-50050100150_+[rad=s2]_+1sim_+1currentsensor0100200300400500Time[sec]-20-15-10-50510_+[rad=s2]_+1sim_+1num:deriv:Figure 7: Implementation of the calculation blocks to feed RW states to the EoMs

profile consistent with the measurement would be required. The need of angular acceleration is only
present in this specific HIL test that requires EoMs propagation. However, in a more comprehensive
test (e.g., tests involving a spherical air-bearing testbed), no artifacts would be required to construct
RW angular acceleration and the framework proposed here remains fully applicable for physically
induced failures. Finally, to address the increased noise around zero RW speed, RWs were spun-up
to an initial Ω = [100, −100, −100, 100] rad/s. With these adjustments, we achieved a closed-loop
operation between the SatSim and the physical RWs.

HIL-c: Adding Embedded Computer in the Loop

In this stage, we aim to ensure that the controller is on the embedded hardware. This involved two
additional tasks: (a) To check that the controller still provides correct output even when it receives
the noisy velocity measurements, and (b) To ensure that the controller node correctly implements
failure induction logic, i.e., computes the correct RW commands to be sent to the RW.

Up to this point, RWs are still being commanded by the Satellite Simulator. As an intermediate
step we executed the controller block on the Satellite Simulator and, in parallel, on the Jetson Nano
embedded computer to assess their performance. Although the ControllerNode on the Jetson Nano
had already been validated during the SIL stage, the main difference now is the noisy data mea-
surements from the physical RWs, and newly incoporated satellite state estimates from an attitude
determination EKF.

The estimated states from the EKF (computed in Satellite Simulator) and real-time RW angular
velocity measurements were sent to the ControllerNode on the Jetson Nano, and its outputs are
transmitted back to the SatSimNode for comparison and verification. Once validated, we replace
SatSim’s RW commands with the commands calculated on the Jetson Nano to fully execute the
control computations on the embedded computer.

To validate the controller in this final setup, we employed the same test scenario from our pre-
vious work. In this scenario, the satellite begins by aligning itself with the Earth-Centered Inertial
(ECI) frame and then alternates between its initial orientation and nadir-pointing three times. The
simulation scenario lasts for 4000 seconds, during which the satellite switches its orientation every
12 minutes, then maintains nadir-pointing after 2000 seconds. The only changes we made to the
simulation parameters were to increase the degraded wheel factor from 0 to 0.5 to induce a partial
failure instead and reduce KICL gain by an order of magnitude, i.e., KICL = 1. The gain ad-
justment was necessary to avoid demanding torque commands that exceed the limits of the RWs,
which initially caused the simulator and the ControllerNode on the Jetson Nano to stop once the
ICL term was activated. This highlights the gap in sim-to-real, where sometimes control torques

10

SatAttDynCalc Ω,Ω̇Controller𝒖𝛀𝛀̇ RWsΩ̇!Ω!Table 2: Controller Gains (Simulation vs. HIL)

Gain

Simulation

HIL

KICL
K
α
β
γ
¯λ

10
5 × 10−1
3 × 10−2
5 × 10−3
100I4
1 × 10−7

1
1 × 10−2
3 × 10−2
5 × 10−3
100I4
1 × 10−7

that are feasible in simulation do not mean that they can be replicated in a real test. Table 2 shows
the gains that were adjusted to reflect the hardware constraints.

RESULTS

The satellite was able to follow its guidance commands throughout the simulation as evident
in Figure 8a and Figure 8b. Figure 9 shows the RW health estimation performance, i.e., ˆθ. The
lambda λ plot represents the verifiable excitation level due to the input-output data accumulated
by the system.15 Although the lambda λ reached the defined threshold value earlier than in purely
simulated tests, the health estimation ˆθ can be seen to converge to its true value. Because we reduce
the gain KICL to avoid the simulation from stopping, it affects the convergence rates, taking more
time to converge. As the satellite perform more maneuvers, the action of the gradient-based term
(i,e., first term in Equation (5)) helped move it closer to its true value faster.

(a) Error MRP

(b) Body Angular Velocity

Figure 8: Performance of the Attitude Tracking Accuracy.

Two consistent behaviors with prior results were observed. The estimation accuracy for degraded
RW#3 is better than for the non-degraded wheels (steady-state error) and that there was overshoot
on the estimation for RW#3. The steady state error was partly due to the numerical integration errors
from the forward-Euler integration algorithm used to compute the estimated value ˆθ via integration
of Equation (5), as well as the fact that in the development of the controller some parts of the
simulation model, such as attitude perturbations were neglected, leading to a disparity between the

11

05001000150020002500300035004000Time[sec]-1-0.8-0.6-0.4-0.200.20.40.60.8Amplitude<1<2<305001000150020002500300035004000Time[sec]-8-6-4-20246810![deg=s]!1!2!3(a) Lambda

(b) Estimated RW Health

Figure 9: RW Health Estimation with RW hardware in the loop.

two.

Figure 10 shows the angular velocity measurements from the RW. Due to internal low-pass fil-
tering implemented in the digital motor controller, the measurement noise was observed only at
low-speed regions. Despite the measurement noise, it has minimal impact on the performance of
the attitude tracking and estimation of the controller, as seen in earlier plots.

Figure 10: RW Angular Velocity Measurement.

Table 3 reports the performance of the Jetson Nano embedded computer during the HIL test.
The controller executes the loop in 3.86 ± 0.20 ms on average, which is well below the 100 ms
of the control loop limits. To measure the ROS2 nodes CPU load consumption, each node was
assigned to a specific CPU. The ControllerNode, running on CPU2, consumed less than 15%, while
the RWNode, running on CPU3, consumed about 10% of CPU load. The maximum CPU load of
CPU2 and CPU3 reached 100%, which is expected when the nodes are initialized at the start of the
HIL test. The remaining CPU0 and CPU1 handle the operating system and background tasks that,
on average, consume less than 3% of CPU load. For memory usage, it increased to 19.6% with the
controller running if compared to the baseline of 16.6%, which means that only a small amount of

12

05001000150020002500300035004000Time[sec]02468106#10!8Threshold(1e-7)740745750755760Time[sec]567891011#10!805001000150020002500300035004000Time[sec]00.20.40.60.81HealthPercentage[%]RW3TrueHealth^?1^?2^?3^?401000200030004000Time[sec]-4000-2000020004000+[RPM]+1+2+3+4260026502700Time[sec]-1000100Table 3: Jetson Nano Performance Metrics.

Metric

Average Maximum Std. Dev.

Execution Time (ms)
CPU Usage (%)

CPU2 (ControllerNode)
CPU3 (RWNode)
CPU0
CPU1

Memory (RAM %)
Idle (baseline)
HIL

3.86

14.7
10.3
2.7
0.3

16.6
19.6

6.62

100
100
6.90
3.00

16.7
19.8

0.20

4.4
5.0
0.9
0.5

0.01
0.6

memory (3%) is required to execute the control algorithms.

FUTURE WORK

Given the results and lessons learned in this HIL testing, the avenues for future work are highly
promising. The next immediate step in validating the adaptive controller in a simulation setup that
mimics its true mission profile as closely as possible is to transition the RW hardware setup from a
flat test bench array to one where the RWs are placed in the design configuration array inside a mock
satellite on a rotational air bearing. This setup would alleviate the problematic issues caused by the
EoM in the simulation, allowing for a more comprehensive and thorough analysis of the controller.

With this setup, another possibility for future work includes moving the EKF that is currently
hosted on the simulation computer, along with the attitude determination node, onto the embedded
computer, as it would be on a real mission. This testing would ensure all necessary communication
and computations that would be required by the embedded computer would be possible without
causing too much computational burden.

Finally, with the EoM now being omitted from the simulation setup, we would then be able to
physically induce failures to the RW again to an even more realistic scenario to test the learning
capability of the controller. With this component of the HIL test, performed on the air bearing
testbed, full validation of the adaptive controller would be achieved.

CONCLUSION

In this paper, we validated an adaptive satellite attitude controller capable of estimating the health
level of its RWs through the HIL test that includes an embedded computer and physical RW hard-
ware with artificially induced failure. Using the HIL testbed, we demonstrated that the proposed
adaptive controller performed considerably well under hardware constraints, with noisy measure-
ments from the sensor. In addition, through the test, we have established a baseline validation of
our envisioned modular HIL testbed design that is flexible and scalable. Despite several issues en-
countered during the development of the HIL testbed, the lessons learned are valuable as we move
towards the next step involving a full air-bearing testbed experiment and other comprehensive end-
to-end system tests in the future. This work will contribute to advancing the state-of-the-art ground
hardware testing of fault-tolerant spacecraft attitude controllers.

13

ACKNOWLEDGMENT

The authors would like to thank Cole Schumacher for his contribution to the initial tests and

integrations of the RWs to the HIL testbed.

REFERENCES

[1] F. L. Markley, R. G. Reynolds, F. X. Liu, and K. L. Lebsock, “Maximum Torque and Momentum
Envelopes for Reaction Wheel Arrays,” Journal of Guidance, Control, and Dynamics, Vol. 33, No. 5,
2010, pp. 1606–1614, 10.2514/1.47235.

[2] H. Hassrizal and J. Rossiter, “A survey of control strategies for spacecraft attitude and orientation,” 2016

UKACC 11th international conference on control (CONTROL), IEEE, 2016, pp. 1–6.

[3] M. Y. Ovchinnikov and D. Roldugin, “A survey on active magnetic attitude control algo-
rithms for small satellites,” Progress in Aerospace Sciences, Vol. 109, 2019, p. 100546,
https://doi.org/10.1016/j.paerosci.2019.05.006.
and S. Qin,

[4] M. N. Hasan, M. Haris,

“Fault-tolerant

Sciences, Vol.

spacecraft
130,

attitude
2022,

control:
p.

A
100806,

critical
https://doi.org/10.1016/j.paerosci.2022.100806.

assessment,”

Progress

in Aerospace

[5] S. Ahmed khan, Y. Shiyou, A. Ali, S. Rao, S. Fahad, W. Jing, J. Tong, and M. Tahir, “Active atti-
tude control for microspacecraft; A survey and new embedded designs,” Advances in Space Research,
Vol. 69, No. 10, 2022, pp. 3741–3769, https://doi.org/10.1016/j.asr.2022.02.020.

[6] A. Li, M. Liu, X. Cao, and R. Liu, “Adaptive quantized sliding mode attitude tracking control for
flexible spacecraft with input dead-zone via Takagi-Sugeno fuzzy approach,” Inf. Sci., Vol. 587, Mar.
2022, pp. 746–773.

[7] M. Mirshams and M. Khosrojerdi, “Attitude control of an underactuated spacecraft using
tube-based MPC approach,” Aerospace Science and Technology, Vol. 48, 2016, pp. 140–145,
https://doi.org/10.1016/j.ast.2015.09.018.

[8] P. Iannelli, F. Angeletti, and P. Gasbarri, “A model predictive control for attitude stabilization and spin
control of a spacecraft with a flexible rotating payload,” Acta Astronautica, Vol. 199, 2022, pp. 401–411,
https://doi.org/10.1016/j.actaastro.2022.07.024.

[9] S. Mokhtari, A. Abbaspour, K. K. Yen, and A. Sargolzaei, “Neural Network-Based Active Fault-
Tolerant Control Design for Unmanned Helicopter with Additive Faults,” Remote Sensing, Vol. 13,
No. 12, 2021, 10.3390/rs13122396.

[10] C. Riano-Rios, R. Bevilacqua, and W. E. Dixon, “Differential drag-based multiple spacecraft maneuver-
ing and on-line parameter estimation using integral concurrent learning,” Acta Astronautica, Vol. 174,
2020, pp. 189–203, https://doi.org/10.1016/j.actaastro.2020.04.059.

[11] R. Sun, C. Riano-Rios, R. Bevilacqua, N. G. Fitz-Coy, and W. E. Dixon, “CubeSat Adaptive Attitude
Control with Uncertain Drag Coefficient and Atmospheric Density,” Journal of Guidance, Control, and
Dynamics, Vol. 44, No. 2, 2021, pp. 379–388, 10.2514/1.G005515.

[12] X. Xie, T. Sheng, Y. Zhang, J. Wang, and X. Chen, “Adaptive Fault-Tolerant Attitude Control for Rigid
Spacecraft With Disturbances and Uncertainties,” 2023 China Automation Congress (CAC), IEEE, Nov.
2023, pp. 596–600.

[13] S. M. Sadigh, A. Kashaninia, and S. M. M. Dehghan, “Adaptive sliding mode fault-tolerant control for

satellite attitude tracking system,” Adv. Space Res., Vol. 71, Feb. 2023, pp. 1784–1805.

[14] C. Wang, L. Guo, C. Wen, Q. Hu, and J. Qiao, “Event-Triggered Adaptive Attitude Tracking Control for
Spacecraft With Unknown Actuator Faults,” IEEE Trans. Ind. Electron., Vol. 67, Mar. 2020, pp. 2241–
2250.

[15] G. Nehma, C. Riano-Rios, M. Sakal, and M. Tiwari, “Adaptive Controller for Simultaneous
Spacecraft Attitude Tracking and Reaction Wheel Fault Detection,” https://camilori.com/
wp-content/uploads/2025/07/RW_health_estimation___Journal_version.
pdf, 2025. Manuscript under review at Journal of Spacecraft and Rockets.

[16] H. Schaub and J. Junkins, Analytical Mechanics of Space Systems. American Institute of Aeronautics

and Astronautics, 4th ed., 2018.

[17] S. Macenski, T. Foote, B. Gerkey, C. Lalancette, and W. Woodall, “Robot Operating System 2: De-
sign, architecture, and uses in the wild,” Science Robotics, Vol. 7, No. 66, 2022, p. eabm6074,
10.1126/scirobotics.abm6074.

[18] Maxon Motor AG, “EC 60 flat Ø60mm, brushless, 100W (Part No. 647691) Datasheet,” https:
//www.maxongroup.com/maxon/view/product/647691, July 2025. [Online; accessed 25-
Jul-2025].

14

[19] Maxon Motor AG, “EPOS4 Compact 50/5CAN Digital Position Controller (Part No. 541718)
https://www.maxongroup.com/maxon/view/product/control/

Datasheet,”
Positionierung/EPOS-4/541718, July 2025. [Online; accessed 25-Jul-2025].

[20] J. L. Crassidis and J. L. Junkins, Optimal Estimation of Dynamic Systems. Boca Raton, FL: Chapman

& Hall/CRC, 2 ed., Oct. 26 2011, 10.1201/b11154.

[21] I. Sadeghzadeh and Y. Zhang, A Review on Fault-Tolerant Control for Unmanned Aerial Vehicles

(UAVs), 10.2514/6.2011-1472.

[22] P. R. Yanyachi, A. Mamani-Saico, X. Wang, and B. Espinoza-Garc´ıa, “Development of an Air-Bearing
Testbed for Nanosatellite Attitude Determination and Control Systems,” IEEE Access, Vol. 12, 2024,
pp. 168864–168876, 10.1109/ACCESS.2024.3497722.

[23] M. Post, J. LI, and R. Lee, Nanosatellite Air Bearing Tests of Fault-Tolerant Sliding-Mode Attitude

Control with Unscented Kalman Filter, 10.2514/6.2012-5040.

[24] N. P. Nguyen and S. K. Hong, “Sliding Mode Thau Observer for Actuator Fault Diagnosis of Quad-

copter UAVs,” Applied Sciences, Vol. 8, No. 10, 2018, 10.3390/app8101893.

[25] B. Ghalamchi, Z. Jia, and M. W. Mueller, “Real-Time Vibration-Based Propeller Fault Diagnosis
for Multicopters,” IEEE/ASME Transactions on Mechatronics, Vol. 25, No. 1, 2020, pp. 395–405,
10.1109/TMECH.2019.2947250.

[26] D. Vey and J. Lunze, “Experimental evaluation of an active fault-tolerant control scheme for multiro-
tor UAVs,” 2016 3rd Conference on Control and Fault-Tolerant Systems (SysTol), 2016, pp. 125–132,
10.1109/SYSTOL.2016.7739739.

[27] N. P. Nguyen, N. Xuan Mung, and S. K. Hong, “Actuator Fault Detection and Fault-Tolerant Control

for Hexacopter,” Sensors, Vol. 19, No. 21, 2019, 10.3390/s19214721.

[28] M. Saied, B. Lussier, I. Fantoni, C. Francis, H. Shraim, and G. Sanahuja, “Fault diagnosis and fault-
tolerant control strategy for rotor failure in an octorotor,” 2015 IEEE International Conference on
Robotics and Automation (ICRA), 2015, pp. 5266–5271, 10.1109/ICRA.2015.7139933.

[29] R. Avram, X. Zhang, and J. Muse, “Quadrotor Sensor Fault Diagnosis with Experimental Results,”

Journal of Intelligent & Robotic Systems, Vol. 86, 04 2017, 10.1007/s10846-016-0425-1.

[30] Z. Cen, H. Noura, T. Susilo, and Y. Younes, “Robust Fault Diagnosis for Quadrotor UAVs Using Adap-
tive Thau Observer,” Journal of Intelligent & Robotic Systems, Vol. 73, 01 2014, 10.1007/s10846-013-
9921-8.

[31] J. R. Wertz, Spacecraft attitude determination and control, Vol. 73. Springer Science & Business Media,

2012.

[32] V. Carrara, R. H. Siqueira, and D. Oliveira, “Speed and current control mode strategy comparison in
satellite attitude control with reaction wheels,” Proceedings of the 21st Brazilian Congress of Mechani-
cal Engineering (COBEM’11), 2011.

[33] V. Carrara and H. K. Kuga, “Torque and speed control loops of a reaction wheel,” 11th International

Conference on Vibration Problems, 2013.

[34] S. Shigeto, S. Mitani, N. Tanishima, and M. Goto, “Development and Evaluation of the 1/30U Small-
Sized 3 Axis Attitude Control Module, and its Application for the JEM Internal Ball Camera Robot,”
2018.

15

