Contents lists available at ScienceDirect

Measurement

journal homepage: www.elsevier.com/locate/measurement

On-orbit performance analysis of spinning spacecraft magnetic control laws.
Application to the UPMSat-2 mission
Angel Porras-Hermoso a,b,∗, Javier Piqueras a,b, Javier Cubas a,b, Elena Roibás-Millán a,b
a Universidad Politécnica de Madrid, Pza. del Cardenal Cisneros 3, Madrid, 28040, Spain
b Instituto Universitario de Microgravedad ’Ignacio Da Riva’ (IDR/UPM), Pza. del Cardenal Cisneros 3, Madrid, 28040, Spain

A R T I C L E I N F O

A B S T R A C T

Keywords:
Attitude control
Magnetic control
ADCS
Attitude determination

1. Introduction

This paper studies the performance of a new magnetic attitude control law developed for the UPMSat-2
satellite. The UPMSat-2 control law, which is a modification of the B-dot, allows the satellite to align one
axis with the normal to the orbital plane and achieve a target angular velocity, without requiring attitude
determination. The study evaluates the control law’s effectiveness using the first housekeeping data received
since the satellite’s launch in September 2020. To verify the control’s on-orbit performance, data from sun
sensors and magnetometers, along with thermal analysis of the satellite external temperatures, are used to
confirm that the satellite remains at its design attitude and angular velocity. The study concludes that the
proposed control law is a simple and effective alternative for small satellite attitude control.

Attitude control systems have a key role in spacecraft operations
since they provide an essential feature to achieve mission goals and
even ensure the survival of the spacecraft. There are a high number
of approaches to be able to control the attitude dynamics [1], and
many more are being developed in recent years with a focus on small-
size satellites [2]. In that case, and for satellites operating in Low
Earth Orbits (LEO), a particularly effective form of attitude control is
based on the measurement and interaction with the Earth’s magnetic
field. Electromagnetic actuators provide a simple solution able to gen-
erate torques onboard the spacecraft by the interaction between three
orthogonal magnetic coils and the Earth’s magnetic field.

The first satellite using passive magnetic control systems was Transit
1B [3], followed by Tiros II [4] that incorporated an active magnetic
control, both launched in 1960. Attitude reconstruction using measure-
ments of the Earth’s magnetic field was first performed with Sputnik-3
satellite, launched in 1958 [5]. Despite the widespread use of magnetic
control systems, they usually play a secondary role, being almost exclu-
sively oriented to perform specific tasks such as detumbling, reaction
wheel desaturation or to provide attitude control in safe modes due
to its simplicity and low failure risks. However, there are notable
exceptions, such as in spin-stabilized satellites, where magnetic control
plays a crucial part [6–8].

In recent years, the use and applications of magnetic control laws
have changed. The increasing interest in micro-, nano- and even smaller
satellites, whose attitude requirements usually have lower demands on

accuracy, have made magnetic control laws an essential component
to meet the weight, power, and low complexity requirements of these
missions [5]. Magnetic actuators present very interesting properties
such as significant savings in overall weight and complexity of the
system, lack of catastrophic failure modes, the possibility to modulate
the control torque and very larger operational life. These factors have
led to an extensive development of purely magnetic control laws.

Magnetic control systems can be classified into passive and active
systems. Passive systems were extremely popular in the first decades of
space exploration. These systems included permanent magnets and/or
hysteresis rods, which were used to detumble and stabilize the satellite
along the local geomagnetic vector. These systems are cheap, simple,
reliable, and do not require computation. However, their accuracy
and maneuverability are poor and limited. Active magnetic systems
are nowadays the preferred systems due to the advance in compo-
nent miniaturization and computer performance. These systems include
magnetorquers, that induce a dipole moment when an electrical current
is applied. The dipole moment interacts with the external geomagnetic
field, producing the control torque.

One of the most widely used algorithms for detumbling is the so-
called B-dot [9]. In its simplest form, the detumbling mode based
on the B-dot law is based on negative feedback of the derivative
of the measured magnetic field vector, obtained by a magnetometer.
This algorithm, although been relatively old, is still used and investi-
gated [10,11]. B-dot is an active purely magnetic law that can achieve

∗ Corresponding author at: Universidad Politécnica de Madrid, Pza. del Cardenal Cisneros 3, Madrid, 28040, Spain.

E-mail address: angel.porras.hermoso@upm.es (A. Porras-Hermoso).

https://doi.org/10.1016/j.measurement.2023.113962
Received 23 April 2023; Received in revised form 9 November 2023; Accepted 28 November 2023

Measurement225(2024)113962Availableonline30November20230263-2241/©2023TheAuthor(s).PublishedbyElsevierLtd.ThisisanopenaccessarticleundertheCCBYlicense(http://creativecommons.org/licenses/by/4.0/).A. Porras-Hermoso et al.

a reasonably good accuracy and almost stop the rotation of the satellite,
as the angular velocity of the satellite tends to shrink around 1.8
times the orbital angular velocity [12]. Regarding its time response,
it depends on both the magnetorquer maximum dipole and the orbit
inclination, as it has been shown in more recent works [13,14].

The main disadvantage of magnetic controlled systems is their
inherent underactuation, as they can only produce a magnetic torque in
the perpendicular direction of the Earth’s magnetic field, making 3-axis
stabilization costly and difficult to achieve. In recent years different
attempts to obtain a purely magnetic (by only employing magnetic
actuators) 3-axis stabilization control law have been proposed. These
algorithms use the periodicity of the Earth’s magnetic field to over-
come the underactuation problem and achieve 3-axis control along
the orbit [15,16]. Nevertheless, most of these methods are theoretical
and have not been proven on a real mission. Moreover, these methods
usually require Earth’s magnetic field models and solving complex
optimization problems that could exceed the computational power of
the on-board computers in small satellites.

A simpler solution to solve the underactuation problem is to com-
plete the magnetic control with other actuators, as an example, the
system can use momentum wheels and magnetorquers to build a bias-
momentum attitude control system [17]. Other approaches use the
disturbances to stabilize the satellite. For example, the torque produced
by the gravity gradient can be used to obtain a 3-axis stabilization
in combination with a magnetic control law [18–20]. Other methods
involve the use of aerodynamic drag to stabilize the satellite. These
methods can only be used in satellites located in LEO and with a
proper mass distribution. With the aerodynamic force the satellite can
be stabilized in 2 axes, and the magnetic control only needs to actuate
in one axis. Good examples of this kind of control laws can be found
in the literature [21–23]. Other interesting magnetic control laws are
the ones used in spinning spacecrafts [24–28]. These algorithms use
the property that spinning around the maximum moment of inertia is
stable. However, small errors and external torques can induce nutation
motion to the satellite, so it is necessary to counteract these terms
with a control torque produced by the magnetorquer. In Ref. [29], a
modification of the B-dot law is proposed which provides an effective
control of the angular rotation of the satellite, enabling the rotation axis
to be aligned with the normal of the orbit without using any reaction
wheel.

This paper analyzes and discusses the on-orbit behavior of the
magnetic control law on board the UPMSat-2. This magnetic control
law (described in Section 2) can be considered an improvement of the
B-dot algorithm for spin-stabilized spacecrafts to include the full control
of the rotation velocity around its main inertia axis. One of the main
advantages of this law is that attitude determination is not required.
Therefore, other attitude sensors, apart from magnetometers, are not
necessary, eliminating potential errors derived from attitude determi-
nation, as the ones happened in Compass-1 mission [30]. Consequently,
it can be said that this control law is purely magnetic concerning its
actuators and sensors. This law was briefly used in Hessi mission [31]
for detumbling purposes, but its use as main control and its effect in the
stabilization and orientation of the spacecraft was not analyzed. Those
aspects were previously studied theoretically [29] and the results are
correlated and verified in this work, using UPMSat-2 flight data.

The UPMSat-2 is a 50 kg-class microsatellite developed by the
Instituto Universitario de Microgravedad ‘‘Ignacio Da Riva’’ (IDR/UPM),1
a research institute integrated in the Universidad Politécnica de Madrid
(UPM), and STRAST2 group. The main purpose of this satellite is to
serve as a technology demonstrator of components and algorithms
designed by IDR/UPM and different partners (Tecnobit, SAFT, Iberespa-
cio, Bartington, etc.). Furthermore, this satellite proved to be a greatly
valuable educational tool for students of the Master in Space Systems

(MUSE Màster Universitario en Sistemas Espaciales) of UPM. The most
relevant characteristics of UPMSat-2 are summarized in Table 1.

This paper is organized as follows. In Section 2, the control law
governing the UPMSat-2 attitude is presented and explained. In Sec-
tion 3, the main problems encountered regarding attitude calculation
are discussed, and a method to obtain the angular velocity of the space-
craft is described. The results obtained are presented and discussed in
Section 4. Finally, in Section 5, the conclusions extracted from this
work are summarized.

2. UPMSat-2 attitude control

The dynamic model of a rigid satellite in the satellite’s body ref-
erence frame, indicated with the superscript 𝑠 (𝐹 𝑠), can be expressed
using the Euler equation [32]:

𝐈 ̇𝝎𝑠 = −𝝎𝑠 × 𝐈𝝎𝑠 + 𝑻 𝑠

𝑐𝑜𝑖𝑙 + 𝑻 𝑠

𝑑𝑖𝑠𝑡

(1)

where 𝐈 is the inertia matrix of the satellite in the body reference frame,
𝝎𝑠 is the angular velocity vector of the satellite relative to the inertial
reference frame, 𝑻 𝑠
𝑑𝑖𝑠𝑡 is the
torque produced by the environment disturbances, both in the body
frame.

𝑐𝑜𝑖𝑙 is the control magnetic torque, and 𝑻 𝑠

The UPMSat-2 is almost axisymmetric around its 𝑧𝑠-axis, so its
inertial matrix in its principal body axes (principal axes of inertia) can
be approximated as:

𝐈 =

𝐼⟂
⎡
0
⎢
⎢
0
⎣

0
𝐼⟂
0

0
0
𝐼∥

⎤
⎥
⎥
⎦

(2)

The control torque is the result of the interaction between the
magnetic dipole moment of the magnetorquers, 𝒎, and the geomagnetic
field 𝑩, and it can be expressed as follows:

𝑻 𝑠

𝑐𝑜𝑖𝑙(𝑡) = 𝒎(𝑡) × 𝑩(𝑡)

(3)

In only magnetic controlled system, the magnetic moment gener-
ated by the magnetorquers is the only controllable actuator of the
system. To regulate this magnetic moment, the following control law is
proposed [33]:
𝒎𝑠 = −𝑘( ̇𝑩𝑠

+ 𝝎𝑠

(4)

𝒅 × 𝑩𝑠)

where 𝑘 is the control gain, 𝑩𝑠 is the Earth’s magnetic field in the
body frame, and 𝝎𝑠
𝑑 is the desired angular rate. In the case of UPMSat-
2, the commanded angular speed of the satellite is parallel to the
axisymmetric principal axis, which corresponds to the axis of minimum
inertia. However, it is important to note that the desired angular
velocity cannot be set arbitrarily, as its magnitude must satisfy the
following condition:

𝜔𝑑 ≫ 𝛺𝑜

where 𝛺𝑜 is the orbital rotation rate.

(5)

Therefore, the control torque can be expressed as:
𝑐𝑜𝑖𝑙(𝑡) = −𝑘( ̇𝑩𝑠
𝑻 𝑠
By introducing Eq. (6) in (1), and neglecting the effects of the

𝑑 × 𝑩𝑠) × 𝑩𝑠

+ 𝝎𝑠

(6)

disturbance torque, the satellite dynamic equation can be written as:
𝐈 ̇𝝎𝑠 = −𝝎𝑠 × 𝐈𝝎𝑠 − 𝑘( ̇𝑩𝑠

+ 𝝎𝑠

𝑑 × 𝑩𝑠) × 𝑩𝑠

(7)

As it is known, the derivative of a quantity, such as the magnetic
field, with regard to moving axes, such as those of the satellite, can be
expressed in the following manner:
̇𝑩𝑠

̇𝑩1 + 𝑩𝑠 × 𝝎𝑠

(8)

= 𝐀𝑠
1

1 https://www.idr.upm.es/
2 https://www.dit.upm.es/∼str/.

Measurement225(2024)1139622A. Porras-Hermoso et al.

Table 1
UPMSat-2 main characteristics.

Orbit

Dimensions

Mass and Moment of inertia

Attitude control

Attitude determination

∙ Sun-synchronous orbit.
∙ Local Time of Descending Node: 10:30 AM.
∙ Altitude at launch: 518 km.

0.5 m × 0.5 m × 0.6 m.

Mass: 50 kg.
Moment of inertia, 𝑧-axis: 1.833 kg m2
Moment of inertia, 𝑥-axis: 2.543 kg m2
Moment of inertia, 𝑦-axis: 2.525 kg m2

Magnetic control:
∙ 3 magnetometers (SSBV and Bartintong).
∙ 3 Magnetorquers (ZARM Technik AG) .
∙ Purely magnetic control law designed by IDR/UPM.
Expected performance:
∙ Satellite’s 𝑧-axis oriented perpendicular to the orbital plane.
∙ Rotation about 𝑧-axis at an angular velocity of 0.1 rad/s.

Attitude determination on ground with received telemetry. Sensors:
∙ Magnetometers.
∙ Solar panels.
∙ Solar sensors designed by IDR/UPM.

Thermal control

Passive for all the satellite excluding the battery (thermostats and heaters).

Power

On board Electronic Box

Communications

Payload

Based on solar photovoltaic panels and batteries:
∙ 5 body-mounted solar panels (Selex Galileo SPVS-5 module with Azur Space 3G28C triple junction solar cells).
∙ 18 A h Li-ion battery designed by Saft.
∙ Direct Energy transfer (DET).

FPGA based (designed by Tecnobit S.L and programmed by STRAST/UPM). Includes:
∙ On-board computer.
∙ Data Handling.
∙ Power supply control.
∙ Power supply distribution.

∙ Half-duplex UHF at 400 MHz and 437 MHz.
∙ Baud rate: 1200 Bd (2-FSK) and 9600 Bd (GMSK).
∙ 4 monopole antenna system with circular polarization.
∙ Ground station located in Madrid, Spain. Software programmed by STRAST; hardware configuration supervised by INTAa

Technological demonstrators:
∙ Magnetometer (Bartington).
∙ Electronic Box (Tecnobit).
∙ Rotation wheel (SSBV).
∙ Thermal microswitch (Iberespacio).
∙ Battery life (Saft).
∙ Solar sensors (IDR/UPM).
∙ Thermal control (IDR/UPM).
Science:
∙ Earth Magnetic Field.

a INTA: Instituto Nacional de Técnica Aeroespacial, Madrid, Spain.

where 𝐀𝑠
1 is the direct cosine matrix between the inertial reference
frame and the moving reference frame. By substituting the aforemen-
tioned expression into Eq. (7), the following equation is derived:

𝐈 ̇𝝎𝑠 = −𝑘𝑩𝑠 × (𝝎𝑠 − 𝝎𝑠

𝑑 ) × 𝑩𝑠 − 𝑘𝐀𝑠

1( ̇𝑩1 × 𝑩1) − 𝝎𝑠 × 𝐈𝝎𝑠

(9)

During the correction phase, when the angular velocity of the
satellite is significant, and given an arbitrary value of the satellite’s
rotation rate different for the target one, it is reasonable to assume the
following condition:

(10)

‖𝜔 − 𝜔𝑑 ‖ ≫ 𝛺𝑜
As a consequence of condition presented in Eq. (10), the order of
magnitude of the second term on the right side of Eq. (9) is negligible
compared with the first term. This is due to the variation of the
Earth’s magnetic field in the inertial reference frame as it changes at an
approximate rate of 2𝛺𝑜. The effect of Earth’s rotation on the magnetic
field can be considered negligible since the change in the direction of
the magnetic field due to the position of the satellite (2.16 ⋅ 10−3 rad/s),
is much greater that the rotation of the Earth (7.27 ⋅ 10−5 rad/s). Hence,
Eq. (9) for the correction phase can be simplified as shows Eq. (11):

𝐈 ̇𝝎𝑠 = −𝑘𝑩𝑠 × (𝝎𝑠 − 𝝎𝑠

𝑑 ) × 𝑩𝑠 − 𝝎𝑠 × 𝐈𝝎𝑠

(11)

Eq. (11) is similar to the one obtained for the B-dot attitude control
and, as it was proven in [29], it is asymptotically stable to the desired

rotation rate using the Lyapunov stability criteria. The selection of
the value of parameter 𝝎𝑠
𝑑 significantly influences the dynamics of
the problem. A larger discrepancy between the target angular velocity
and the initial value leads to a more rapid convergence of the control
towards the desired value and, therefore, the sooner the stabilization
phase will be reached.

Once the angular rotation rate of the satellite approaches to the

target one, that is:

‖𝜔 − 𝜔𝑑 ‖ ∼ 𝛺𝑜

(12)

the second term of Eq. (9) is no longer negligible, and it produces the
following torque:

𝝉 = −𝑘𝐀𝑠

1[ ̇𝑩1 × 𝑩1]

(13)

It has been previously proved that the satellite has a tendency
to align itself with the direction of the torque, 𝝉 [29]. Therefore, a
stabilization time will come when it is assumed that the satellite’s 𝑧-axis
is aligned with the torque direction. In this case, for the stabilization
phase, Eq. (9) can be rewritten as follows:

𝐈 ̇𝝎𝑠 = −𝑘𝑩𝑠 × (𝝎𝑠 − 𝝎𝑠

𝑑 ) × 𝑩𝑠 − 𝑘‖

̇𝑩1(𝑡) × 𝑩1(𝑡)‖𝒆𝒔 − 𝝎𝑠 × 𝐈𝝎𝑠

(14)

Measurement225(2024)1139623A. Porras-Hermoso et al.

where 𝒆𝑠 is the unit vector, which has the same direction as the torque,
𝝉 and can be calculated as follows:
1(𝑡)
1(𝑡)‖

1(𝑡) × 𝑩𝑠
1(𝑡) × 𝑩𝑠

( ̇𝑩𝑠
̇𝑩𝑠

(15)

𝒆 =

)

‖

Introducing the following change of variable:

Table 2
Characteristics of the of selected hardware and parameters for the attitude control of
the UPMSat-2.

Characteristic

Description

Magnetorquer

Linear dipole range: ±15 Am2
Linearity error < 2% at max. linear moment
Residual dipole ≤ 0.5% of max. linear moment

(

‖

𝜔𝑑 +

𝝎∗𝑠

𝒅 =

̇𝑩𝑠

1(𝑡)‖

1(𝑡) × 𝑩𝑠
‖𝑩(𝑡)‖2

)

𝒆𝑠

(16)

Magnetometer (from SSBV)

Error < 25 nT
Noise < 2 nT (RMS)

and substituting it into Eq. (14), it becomes evident that the resulting
equation bears a strong resemblance to the one derived in Eq. (11)

𝐈 ̇𝝎𝑠 = −𝑘𝑩𝑠 × (𝝎𝑠 − 𝝎∗𝑠

𝑑 ) × 𝑩𝑠 − 𝝎𝑠 × 𝐈𝝎𝑠

(17)

This new variable, 𝝎∗𝑠

𝑑 to an average value of 𝜔∗𝑠

𝑑 , represents the equilibrium angular velocity
that varies periodically with time, 𝑡, as the satellite moves along its
orbit. Consequently, the steady solution of Eq. (17) is influenced by the
control gain, 𝑘. For large values of 𝑘, the equilibrium angular velocity
approaches the exact value of 𝜔∗𝑠
𝑑 and exhibits a periodic oscillation
around the commanded angular velocity between 𝜔∗𝑠
𝑑 + 1.5𝛺𝑜 and
𝜔∗𝑠
𝑑 + 3𝛺𝑜. For small values of 𝑘, the variation of that oscillations is
less pronounced, tending 𝜔𝑠
𝑑 , approximately
𝑑 + 1.7𝛺𝑜. Although the average value is slightly higher than 𝜔𝑠
𝜔∗𝑠
𝑑 this
can be easily corrected by commanding a value of 𝜔𝑠
𝑑 that accounts
for that increase. However, the oscillations around the equilibrium
angular velocity cannot be completely eliminated. Nevertheless, they
are a minor compromise given the simplicity of the control. Another
factor to take into account at the stabilization stage is the value of the
parameter 𝜔𝑠
𝑑 (‖𝜔𝑑 ‖ ≫ 𝛺𝑜) the oscillations that
occur will be of little importance compared to the value of the target
angular velocity. Conversely, if this value is low, the oscillations may
approach magnitudes comparable to the target angular velocity, poten-
tially jeopardizing the stability, particularly at lower speeds. Further
details on the theoretical performance of this control law can be found
in the work of Ref. [29].

𝑑 . For high values of 𝜔𝑠

The implementation of this algorithm in UPMSat-2 satellite can be
found in reference [34] and the main characteristics of the hardware
and control parameters are shown in Table 2. The selection of 𝝎𝑑 =
[0, 0, 0.1] rad/s is due to the fact that a high value of the target angular
velocity compared to the initial one accelerates the detumbling phase.
Once the satellite is stabilized, and after commissioning, subsequent
adjustments of the angular velocity via telecommand are possible.
Based on thermal and power studies [35], it is apparent that the
rotation can be lowered to 5.52 ⋅ 10−3 rad/s and the satellite will remain
operationally. However, it is important to note that this value closely
approaches the theoretical lower limit, and it is not recommended to
go below it. Regarding the upper limit of the target angular velocity,
it is given by the sampling rate of the magnetometers, being necessary
that the frequency of change of the measured magnetic field be at most
half the sampling rate of the magnetometers. Therefore, the maximum
rotation frequency of the satellite will be half the sampling rate of
the magnetometers if only two consecutive measurements are used to
obtain the derivative of the magnetic field (𝑓𝑟𝑜𝑡 <

).

𝑓𝑠𝑎𝑚𝑝𝑙𝑖𝑛𝑔
2

One of the primary challenges in implementing this algorithm in
real-world scenarios is the unreliability of magnetometer measurements
while magnetorquers are active. The magnetometer’s readings are in-
fluenced by the magnetorquers’ magnetic field, making it necessary to
ensure that the magnetometer reading and the magnetorquer activation
occurs at different time instants. To accomplish this, a control cycle
was devised (see Fig. 1), with a duration of 2 s, divided into two
separate intervals of one second each. During the first interval, the
magnetometers are sampled with a period of 200 ms. These mea-
surements are averaged, and the derivative of the magnetic field is
calculated. By adopting this approach, the measured magnetic field
derivative becomes more robust to the influence of noise and distur-
bances. Then, these results are fed to the control algorithm, which

Control parameters

Control Gain: 𝑘 = 1 ⋅ 108
Target rotation rate: 𝝎𝑑 = [0, 0, 0.1] rad/s

takes a negligible time to process the control action. In the second
interval, the control action is transmitted to the magnetorquers, which
may take approximately 200–500 ms to complete. The time reserved
for this action is influenced by the time needed for the magnetorquer
to activate and reach the demanded magnetic moment value, which is
usually around 150 to 200 ms. To this time is added another period for
the magnetorquer to remain active, which ultimately culminates in a
maximum total time of 500 ms. Finally, the control cycle is concluded
with a rest period of at least 500 ms. This rest period prevents any
residual magnetic moment in the magnetorquers from interfering with
the magnetometers’ readings.

In Ref. [29], different simulations were done for a satellite with
similar characteristics to the UPMSat-2. These simulations consisted in
a Montecarlo analysis of the attitude control’s behavior once it was
stabilized, for different orbit inclination, with constant control gain, 𝑘,
for each Montecarlo analysis. In Fig. 2 the results for the control gain
implemented in the UPMSat-2 are shown. For this case, the results of
interest correspond to a inclination of 97.4 deg. For this inclination, a
mean deviation around 2.5 deg from the normal direction of the orbit
is expected. In terms of the stabilized rotation rate, the deviation from
the target rotation rate ranges from 1.25 to 3 times the orbital rotation
rate. For the special case of the target rotation rate being 0.1 rad/s, the
expected response and values once the satellite is stabilized are shown
in Fig. 3, giving as a result a rotation rate of 0.1 rad/s plus 1.7 𝛺𝑜 on
the 𝑧-axis, with small periodical variations of less than 𝛺𝑜.

3. UPMSat-2 attitude determination

3.1. The problem of determining UPMSat-2 attitude

UPMSat-2 data is transmitted to the ground station when the satel-
lite has direct access to it. The satellite typically passes over the
ground station four times per day (twice during daylight and twice
at night). During transmission windows that last around 10-15 min,
the satellite’s housekeeping information is sent every minute for fur-
ther analysis. With this information, the attitude of the satellite can
be calculated using two independent sensor measurements, and its
corresponding modeled magnitudes in the reference frame. The result
of this procedure is an ‘‘image’’ of the satellite’s orientation at that
instant, which is independent of the data rate. The estimation of the
angular velocity requires consecutive measurements and the sample
rate shall be equal to or greater than twice the highest frequency of the
movement, as stated by the Nyquist-Shannon sampling theorem [36].
Since UPMSat-2 does not have rate sensors, the estimation of angular
velocity depends on the data rate. It is true that inside the satellite, the
sampling rate of the magnetometers allows to calculate the derivative
of the magnetic field, which in turn will allow to calculate the angular
velocity. However, these data are neither stored nor transmitted. The
only information that is available from the UPMSat-2 is that which is
sent by its commissioning mode. In its commissioning mode the satellite
only sends the current state of the satellite every minute, which does
not include the angular velocity of the satellite. This means that the
received sample rate of the measurements of the satellite is very close to

Measurement225(2024)1139624A. Porras-Hermoso et al.

Fig. 1. Control cycle timing.

Fig. 2. Results of Monte Carlo analysis, carried out to study the situation once the rotation rate is stabilized. Deviation of the pointing direction from the normal of the orbit
(Up). Non-dimensional deviation of the stabilized rotation rate against the target rotation rate (Down). (𝑘′ = 1 ⋅ 106 in the graphs’ legends) [29].

some cases, the attitude can be computed using magnetometers and
solar panels [39]. This approach is interesting for the UPMSat-2 case,
as its solar sensors are part of the payload and the verification of
their in-flight performance depends on the magnetometer results [40].
However, this method can only estimate the spacecraft’s orientation
and not its angular velocity, which is necessary to prove the main
point of the UPMSat-2 attitude control. The work of Ref. [41] pro-
poses a magnetometer-only attitude determination algorithm. With
this method, the algorithm can estimate both the orientation and the
angular velocity using the information of three consecutive measure-
ments from the magnetometer. However, considering the low data
rate received from UPMSat-2 (one data package per minute) and its
expected angular velocity (one revolution per minute), this method is
not suitable for the UPMSat-2 case. Other methods to determine the
attitude of small spinning spacecraft using only magnetometers have
been proposed [42], but the apparent angular velocity calculated with
these algorithms could differ from the true angular velocity of the
spacecraft.

Alternatively, more advanced methods could be considered, which
combine the knowledge of the vehicle’s dynamics and the sensor read-
ings to estimate the full state of the satellite. This is the case of
algorithms like the Kalman filter and its variations. One of the most
popular applications in small satellites is to combine measurements
from magnetometers and solar sensors into a Multiplicative Extended
Kalman Filter (MEKF) [43]. In other algorithms, the spacecraft’s atti-
tude is first determined using single value decomposition (SVD), and
the result is integrated into an Extended Kalman Filter (EKF) to estimate
the angular velocity [44]. More advanced algorithms can estimate the
attitude and angular velocity using a magnetic-only algorithm with a

Fig. 3. Example of
stabilization [29].

the expected oscillations

in 𝑧-axis angular velocity after

the theoretical rotation rate of the satellite. As a result, it is impossible
to directly estimate the spacecraft rotation velocity with consecutive
measurements. Additionally, only 10–12 data packages are received in
each pass above the ground station, making it difficult to follow the
satellite state between passes.

In the available literature, several works related to the analysis of
the attitude control subsystem have been published. In most of them
in-flight data are analyzed to study the performance of the attitude
determination and control subsystems (ADCS) [30,37]. However, the
methods used in these papers are not applicable for the UPMSat-2
case, as the satellite does not include gyroscopes or optical devices.
Other satellites, such as Tian Tuo 1 [38], use an attitude determi-
nation subsystem composed of solar sensors and magnetometers. In

Measurement225(2024)1139625A. Porras-Hermoso et al.

two-step EKF [45]. Once again, the low data rate of measurements from
the satellite makes estimating the angular velocity challenging, even
for Kalman filters. This is due the filter may find it difficult to follow
the true state, as the dynamics of the spacecraft are faster than the
measurement rate. Moreover, the results obtained could heavily depend
on the initial conditions given to the filter. Furthermore, with only 10–
12 data packages per pass, the convergence of the Kalman filter cannot
be guaranteed for that small amount of data.

Recently, a new and interesting approach to the determination
problem has been proposed, where the temperature and absorbed heat
fluxes are used to determine the orientation of the spacecraft [46,47].
Other studies have also explored the idea of obtaining the attitude
from thermal data, such as [48,49]. This approach is particularly
relevant for the UPMSat-2 satellite, which is equipped with temperature
sensors. Furthermore, Gadalla Mohamed et al. [50] have shown that the
rotation of a moving spacecraft can significantly affect the temperature
difference between its surfaces, making it possible to determine the
spacecraft’s rotation rate. Therefore, this approach holds the potential
to distinguish between fast and slow rotation rates of the satellite.

Given the current state of the art and the specific characteristics of
the satellite, this paper adopts a non-traditional approach to solve the
determination problem. Specifically, the angular velocity of the satellite
is determined by using the stroboscopic effect and a transient thermal
analysis.

3.2. Spacecraft attitude determination with stroboscopic effect

In order to determine the attitude of a spacecraft, it is necessary to
first understand the available independent measurements, their uncer-
tainties, and their nature. On the UPMSat-2 satellite, there are multiple
sensors that can be used for attitude determination: 3 magnetome-
ters and 6 photodiodes that estimate the solar direction. Additionally,
housekeeping data such as solar panel currents and temperature mea-
surements are recorded and are also useful for the satellite attitude
determination [51]. Once the data packages are received and correlated
with the satellite clock and TLE data, the orbit position is calculated,
and relevant environmental conditions are determined, such as the
solar direction and Earth’s magnetic field in their respective reference
frames.

Traditional attitude determination methods like TRIAD or q-method
can then be used to calculate the attitude using the sensor mea-
surements and environmental conditions for that specific spacecraft
position. However, for this mission, estimating the angular velocity of
the satellite is challenging due to the similarity between the expected
rotation frequency and the measurement frequency (one revolution per
minute and one measurement per minute). This produces an strobo-
scopic effect in which the apparent angular velocity is not the true
angular velocity, as seen in Fig. 4, where the results of the Sun vector
calculated using the sun sensor and solar panels are plotted. The 𝑥
and 𝑦 components of the solar vector appear to change slowly, while
the 𝑧-component remains almost constant. This behavior implies that
the satellite seems to rotate around its 𝑧-axis very slowly, but this
appearance is due to the stroboscopic effect as it can be clearly seen
when the results are compared to the expected evolution of the Sun
vector. The modeled Sun vector depicted in the graph is obtained by
simulating the satellite’s rotation at a rate of 0.102 rad/s with an initial
phase of 155 degrees. It is worth emphasizing that the simulated Sun
vector evolution closely aligns with the measured data, enhancing the
probability that a stroboscopic effect is indeed in play. Therefore given
the presented results, in order to deduce the true angular velocity, and
assuming that the control law is working as intended, it is necessary to
assume the presence of an stroboscopic effect in the observed angular
velocity.

To begin, let us assume that the spacecraft is rotating around one
of its principal axes while taking measurements of the environment,
such as the direction of the Sun vector or magnetic field. During

short periods of time, each component of the measurements vector
will exhibit a similar behavior to the one illustrated in Fig. 4, where
two components vary, and the one parallel to the angular velocity
remains constant. Let us consider one of the non-constant components
and refer to its measurement as 𝑦. The evolution of this component
can be approximated as a sinusoidal signal with an angular frequency
𝜔𝑐, which is equal to the satellite’s rotation rate, and a phase 𝜑0,
that represents the initial attitude of the spacecraft. Considering the
sampling period of the signal, 𝑇𝑠, consecutive measurements of this
vector component can be expressed mathematically as follows:

𝑦𝑖 = sin(𝜔𝑐𝑡𝑖 + 𝜑0) = sin

(

2𝜋
𝑇𝑐

)

𝑇𝑠𝑖 + 𝜑0

𝑖 ∈ N

(18)

Here, 𝑇𝑐 represents the period of the motion, while 𝑖 is a natural
number indicating the measurement number (1, 2, 3, . . . ), and it is
used as a subscript to identify each of the different measurements taken
from the periodic signal. Usually, the sample frequency is higher than
the frequency of the phenomenon, implying that 𝑇𝑠 ≪ 𝑇𝑐 . In such cases,
there is no stroboscopic effect, and the frequency of the signal can be
determined. However, in the case of UPMSat-2, the satellite rotation
frequency is expected to be similar to the sampling rate, i.e. 𝑇𝑠 ∼ 𝑇𝑐.
Considering that the sampling period is numerically related to the
rotation period, we can express it as follows:

𝑇𝑠 = 𝑘𝑠𝑐 𝑇𝑐

(19)

where 𝑘𝑠𝑐 can be defined as the ratio between the sampling period, 𝑇𝑠,
and the motion period, 𝑇𝑐, and can be also expressed as:

𝑘𝑠𝑐 =

𝑇𝑠
𝑇𝑐

𝑟 = 1 − 𝑘𝑠𝑐 =

= 1 − 𝑟;

𝑇𝑐 − 𝑇𝑠
𝑇𝑐

(20)

where the new variable, 𝑟, has been defined for convenience. The
observed signal can be then written as follows:

𝑦𝑖 = sin

2𝜋𝑘𝑠𝑐 𝑖)
(

;

𝑖 ∈ N

(21)

as 𝜑0 is an arbitrary initial condition, it can be set to zero without losing
generality. Then, substituting 𝑘𝑠𝑐 into expression (21), and using the
definition given by Eq. (20), the observed signal can be expressed as:

𝑦𝑖 = sin (2𝜋 (1 − 𝑟) 𝑖) = sin (2𝜋𝑖) cos (−2𝜋𝑟𝑖) − cos (2𝜋𝑖) sin (2𝜋𝑟𝑖)

= − sin (2𝜋𝑟𝑖)

(22)

From Eq. (22), it is observed that the motion seems to have an
apparent frequency 𝑓𝑎𝑝, with the perception of being moving in the
reverse direction if 𝑇𝑐 > 𝑇𝑠. An apparent cycle is completed after 1∕𝑟
measurements at sample rate 𝑇𝑠. Then, the apparent period, 𝑇𝑎𝑝 can be
calculated as:
)
( 1
𝑟

𝑇𝑎𝑝 =

(23)

𝑇𝑠

Therefore, the apparent frequency, can be expressed in the following

way:

𝑓𝑎𝑝 =

1
𝑇𝑎𝑝

=

1
𝑇𝑠

1
𝑟

=

𝑟
𝑘𝑠𝑐 𝑇𝑐

=

𝑟
1 − 𝑟

𝑓𝑐

(24)

where 𝑓𝑐 is the true frequency of the signal. This expression establishes
a relationship between the apparent frequency and the true frequency
of the motion. By substituting the definition of 𝑟 given by Eq. (20) into
(24) one can determine the true frequency based on the sample and the
apparent frequencies.

𝑓𝑐 =

1 − 𝑟
𝑟

𝑓𝑎𝑝 =

𝑓𝑐 ∕𝑓𝑠
1 − 𝑓𝑐∕𝑓𝑠

𝑓𝑎𝑝 = 𝑓𝑠 − 𝑓𝑎𝑝

which can be finally expressed as:

𝜔𝑐 =

2𝜋
𝑇𝑠

− 𝜔𝑎𝑝

(25)

(26)

Measurement225(2024)1139626A. Porras-Hermoso et al.

Fig. 4. Sun vector components regarding the UPMSat-2, calculated with the solar panels (a) and the Sun sensors (b), during one access to the ground station on September the
4th, 2020 compared to the expected evolution of the solar vector if the satellite rotates at 0.102 rad/s.

where 𝜔𝑎𝑝 is the apparent angular velocity of the signal. With this
expression, the angular velocity can be deduced if the sampling period
and the apparent angular velocity are known. As the sampling period
is fixed and known, the apparent angular velocity shall be calculated.
The Coriolis theorem describes how a magnitude in a moving or
rotating frame is seen in the fixed frame. Mathematically, it is expressed
as follows:

𝑠

𝑠 + 𝝎𝑠

𝑠1 × 𝒗𝑠

1 = ̇𝒗𝑠
̇𝒗𝑠
where 𝒗 represents a generic vector. The subscripts indicate from which
reference frame the variation is seen, and the superscript indicates the
reference frame where the variation is expressed.

(27)

This theorem can be applied to obtain the angular velocity of
a satellite based on any measurement taken in the satellite, taking
into account that the environmental conditions are known in a fixed
reference frame. In the case of UPMSat-2, the satellite is equipped with
a sun sensor and three magnetometers. However, the magnetometers
have a higher accuracy than the sun sensor, and their measurements
can be combined into a single measurement. Consequently, the angular
velocity of the satellite will be calculated using only the magnetometer

data. For the analysis, only the Earth’s magnetic field will be con-
sidered, although the same approach could be applied to any other
measurement that can be expressed as a direction in space. Therefore,
by introducing the magnetic field into Eq. (27), it can be rewritten as
follows:
̇𝑩𝑠
𝑠 − ̇𝑩𝑠
1 = 𝐁𝑠×
where 𝑩𝑠
𝑠 represents the magnetic field measured by the magnetometer,
while 𝑩𝑠
1 represents the modeled magnetic field obtained through the
IRGF magnetic model. Finally 𝐁× denotes the skew-symmetric matrix
of vector 𝑩.

𝑠 𝝎𝑠
𝑠1

(28)

0
𝐵𝑠
𝑧
−𝐵𝑠
𝑦

−𝐵𝑠
𝑧
0
𝐵𝑠
𝑥

𝐵𝑠
𝑦
−𝐵𝑠
𝑥
0

⎤
⎥
⎥
⎦

𝑠 can be calculated as follows.

𝑩𝑠 =

𝐵𝑠
⎡
𝑥
𝐵𝑠
⎢
𝑦
⎢
𝐵𝑠
⎣
𝑧

Then,

̇𝑩𝑠

1,𝑖 =

̇𝑩𝑠

𝑠,𝑖 =

1
𝑇𝑠
1
𝑇𝑠

𝐁𝑠×

𝑠 =

⎤
⎡
⎥
⎢
⎥
⎢
⎦
⎣
1 and ̇𝑩𝑠
̇𝑩𝑠
[
1,𝑖 − 𝑩𝑠
𝑩𝑠

]

1,𝑖−1

[

𝑩𝑠

𝑠,𝑖 − 𝑩𝑠

𝑠,𝑖−1

]

(29)

(30)

(31)

Measurement225(2024)1139627A. Porras-Hermoso et al.

In this expression, 𝑖 denotes the value of the magnitude at a certain
instant. This implies that at least two consecutive magnetic field mea-
surements are required. However, a significant issue with this method
is that the skew-symmetric matrix is not invertible. Therefore, Eq. (28)
does not possess a unique solution a priori. To address this issue, it
is necessary to use the pseudo-inverse matrix to solve the system of
equations [52]. The pseudo-inverse matrix is defined as follows:

𝐖 =

(
𝐁𝑠×
𝑠,𝑖

𝖳𝐁𝑠×
𝑠,𝑖

)−1

𝖳

𝐁𝑠×
𝑠,𝑖

Finally, the apparent angular velocity is calculated as:

𝝎𝑠

𝑠1,𝑖 = 𝐖

[
𝑠,𝑖 − ̇𝑩𝑠
̇𝑩𝑠

1,𝑖

]

(32)

(33)

1,𝑖

]

[

]

1,𝑖−1

𝑠 𝝎𝑠

= 𝐁𝑠×

𝑠1; 𝐁𝑠×

It is possible to calculate the angular velocity of the spacecraft
using only two consecutive measurements. However, this problem is
ill-conditioned, which can lead to numerical difficulties. To avoid
this issue, it is recommended to use three consecutive measurements
instead.
[ ̇𝑩𝑠

𝑠,𝑖−1 − ̇𝑩𝑠
𝑠,𝑖 − ̇𝑩𝑠
̇𝑩𝑠
By solving the system of equations presented here and following the
steps outlined in Eqs. (32) and (33), a unique and more precise solution
can be obtained. When the sample frequency is twice the frequency of
the motion, these equations provide the true angular velocity of the
spacecraft. However, if the sample frequency is lower, it is only possible
to determine the apparent angular velocity, and the stroboscopic effect
must be considered. In such cases, the obtained results should be
incorporated into Eq. (26) to determine the true angular velocity.

𝐁𝑠×
𝑠,𝑖−1
𝐁𝑠×
𝑠,𝑖

𝑠 =

(34)

4. Results

4.1. Angular velocity results obtained for UPMSat-2

Fig. 5 shows the mean angular velocity obtained for the 𝑥- and
𝑦 axes. The mean angular velocity shows a small component that is
heavily influenced by the instruments noise and process errors. This
suggests that the angular velocity of the 𝑥- and 𝑦 axes is close to 0. Fig. 6
presents the results obtained for the mean angular velocity on the 𝑧-axis
in each illuminated pass, once the stroboscopic effect is considered. The
obtained angular velocity approximates to the target value of 0.1 rad/s.
As previously mentioned, once the satellite is stabilized using this
control, the equilibrium angular velocity exhibits minor variations
around the target velocity. A theoretical analysis was conducted using
a target velocity of 0.1 rad/s and a control gain of 1 ⋅ 108, which
revealed that the expected angular velocity varies between 0.1017–
0.1033 rad/s along the orbit, as depicted in Fig. 3 [29]. As it can be
observed in the results presented in Fig. 6, most part of the results are
in the theoretical range and the maximum deviations are smaller than
3% from the bounds of the theoretical range.

Previous results are only valid if the satellite’s angular velocity
is similar to the sample rate and the stroboscopic effect is present.
Therefore, it is necessary to validate or set lower and upper bounds
to the angular velocity using other measurements that can indirectly
and independently provide another value. To this end, thermal analysis
can be used to determine the uniformity of temperature across the
satellite’s different faces and set a lower limit to the rotating speed [50].
Additionally, the method used to measure the magnetic field in the
satellite allows for setting a preliminary upper limit on the rotation
speed. The magnetometer readings are obtained as an average of five
readings separated by 200 ms each. If the satellite rotates too fast, the
resulting average will not have a physical meaning, and the control
law cannot be applied. For instance, at one revolution per second, the
average of the 5 readings would be zero, resulting in random values due
to instrument noise. Even slower angular velocities can cause control
problems. For example, at 30 revolutions per minute, the average value

of the readings is 90 degrees out of phase with the magnetic field at that
moment. Therefore, one revolution per second (6.283 rad/s) seems like
a reasonable upper limit for the angular velocity.

In order to study the expected thermal behavior of the UPMSat-2 at
different spin rates, a reduced thermal model of the satellite was set-up
based on the detailed thermal model created by IDR/UPM in ESATAN-
TMS (see Fig. 7) [53]). Although the detailed thermal model contains
much more information, its complexity makes unnecessarily compli-
cated the calculation of the transient temperatures along the orbit (see
work of Ref. [35] to observe the expected evolution of solar panel
temperatures using a detailed thermal model). Therefore, a reduced
model will be used. It consists of 7 nodes, 6 of them representing each
panel of the satellite. The last node represents the inner part (trays,
payloads, etc.) and it is conductively coupled with the external panels.
The parameters of the reduced model include thermal capacities,
conductive couplings and the emissivity and absorptivity of the panels.
A good initial estimation of the reduced model parameters can be
obtained from the detailed model itself. Indeed, most of the parameters
of the detailed thermal model were already correlated through the
thermal vacuum testing results [53] and low uncertainty is expected
in their values. However, there are some values that could not be
correlated as, for example, those associated with the solar absorptivity
of the external surfaces (due to lack of equipment for its measurement).
Nevertheless, as the materials and surface treatments are known, it is
possible to define upper and lower limits for the absorptivity.

Although the described initial thermal reduced model predicts the
general thermal behavior of the UPMSat-2, a fine-tuning process is
performed using the flight data received by the IDR/UPM’s ground
station during September 2020. A monotonic temperature increasing
trend is observed despite of the flight data are distributed along many
orbits. This is because the temperature data are plotted as a function
of the time, starting at the eclipse exit instant, so the satellite is
illuminated by the Sun (colored dots in Fig. 8).

The fine-tuning correlation can be performed on a case-by-case
basis by estimating the initial condition, the spin rate, and the thermal
parameters (thermal capacity, absorptivity, and emissivity) at the same
time. The Sun vector and the angular velocity direction are also re-
quired, but they can be estimated through the onboard magnetometers
and sun sensors [40]. Then, for each correlation, a better approximation
between the data and the correlated model is obtained.

It should be taken into account that this correlation process is
computationally expensive, so following this approach for every initial
condition and spin rate is inefficient. Therefore it will be used to dis-
card, before any further analysis, values of apparent angular velocities
of around 0.0031 rad/s. In fact, trying to correlate a low spin rate model
against the flight data, such as the one with apparent angular velocity of
0.0031 rad/s, yields to a thermal model whose parameters do not have
a physical meaning. That is, the thermal capacity, the absorptivity and
the emissivity of the panels acquire values outside the expected ranges.
Another approach for the fine-tuning correlation is to assume an
infinite spin rate. By doing so, the correlation is simpler (the initial
conditions do not have an effect and the angular velocity is known).
Then, the thermal parameters can be adjusted so the model predicts
the global averaged temperature trend. With this approach, the thermal
parameters can be set, and a subsequent optimization process can
be followed to find the spin rate that better match the data. This
assumption works well if the temperature oscillation due to the spin is
small compared to the secular variation. By looking at the temperature
data of each individual pass (for example the pass depicted in Figs 9
and 10), it is possible to see that temperature oscillation around the
global trend is small (around 1 ◦C or less). Therefore, the high-spin
rate model should work well in this case.

After the correlation, the thermal model obtained (see solid curve
in Fig. 8) predicts the evolution of the satellite average temperatures.
The maximum discrepancy between the data and the high spin rate
model is around ±3 ◦C. There are mainly two possible sources for

Measurement225(2024)1139628A. Porras-Hermoso et al.

Fig. 5. UPMSat-2 mean angular velocity results for the 𝑥-axis and 𝑦-axis for each pass above the ground station. (In these results, only those passes that were illuminated and
have more than five consecutive data points were considered).

Fig. 6. UPMSat-2 mean angular velocity results for the 𝑧-axis for each pass above the ground station.

operational mode, such as the solar panels working point or the internal
dissipation of the electronics and the heaters, or differences that are
propagated for several orbits, but cannot be modeled with the available
information. In Fig. 8, the red dashed line represents the correlated
model, simulated at an apparent angular velocity of 0.0031 rad/s. The
plot clearly shows why 0.0031 rad/s or other low rotation spins are
not compatible with the data. Low angular velocities create relatively
extended periods without sun illumination at the faces, resulting in a
temperature decrease out of eclipse that the data does not exhibit.

Summarizing, the general trend of the thermal data received in
each pass can be reproduced in the model assuming an adequate initial
temperature and a fast spin of the satellite. In addition, some cyclical
variations are observed, and those should be explained by adjusting the
model to the exact rate of rotation of the satellite in its orbit.

Once the thermal model is set-up, it is possible to start searching
for the spin rate that better fit the data, but each pass needs to be
considered individually. This process is necessary because, as stated
before, the temperature variations with respect to the global trend
produced by the spin are considerably smaller than the variations
produced by the different initial conditions. Therefore, the contribution
of the initial conditions needs to be set individually in each pass, in
order to clearly see the oscillations due to the spin.

The approach followed here is to optimize, for each pass, the initial
temperature and the initial attitude. Because the Sun rays and the spin
direction are known, the attitude is specified only by setting the initial
rotation angle (between 0 and 2𝜋). The initial attitude determines the

Fig. 7. UMPSat-2 detailed Geometrical Mathematical Model (GMM).

that discrepancy: a smaller spin rate that generates some oscillation
around the average temperature, or a different initial temperature
condition for each orbit. As the oscillation around the global trend is
small, the ±3 ◦C discrepancy is mainly due to differences in the initial
condition, which in the end can be explained by small differences in the

Measurement225(2024)1139629A. Porras-Hermoso et al.

Fig. 8. Flight temperature data vs time starting at the satellite eclipse exit for several passes (colored points) and correlated model assuming fast (black solid line) and slow (red
dashed line) spin rates.

phase of the temperature oscillations, and its determination becomes
more important the lower the spin rate is. The initial temperature range
considered is the average shown in Fig. 8 with ±5 ◦C. Once a spin
rate is set, the optimization begins with two free parameters, the initial
temperature, and the rotation angle. The initial conditions have been
calculated as those that minimize the root of the residual sum of the
squares between the data and the model. For this purpose, a non-linear
least squares minimization algorithm based on quasi-Newton steps was
used.

In Fig. 9, the result after the optimization process (green solid line)
is shown for one of the passes at an spin rate of 0.03 rad/s. The red and
blue dotted lines, labeled as Hot IC and Cold IC respectively, represent
a model without optimum initial conditions. The optimization process
starts with some arbitrary initial conditions, for example the Hot IC
or the Cold IC, and iteratively converge to other initial conditions
(Optimum IC) that better fits the data.

In Fig. 10 the same flight data as in Fig. 9 is presented, together
with the correlated model with optimized initial conditions, and for
four different spin rates. It is possible to note that the flight data have in
fact small oscillations that high spin rates (0.2 rad/s or higher) cannot
model. This can also be stated for low spin rates, of around 0.03 rad/s
or lower (see also solid green line of Fig. 9 and slow spin curve of Fig. 8)
as the amplitude of their oscillations in the model are too high and
do not correspond to the flight data. If this analysis is done for other
passes, the plots are similar and same conclusions can be extracted. For
spin rates in between, it is not easy to see directly which one fits better
with the data, but it is possible to numerically compare the goodness
of fit by defining the following deviation between the model and the
data:

√
√
√
√

∑𝑁𝑝
𝑖=1

∑𝑁𝑑
𝑗=1

𝜀𝑇 =

)2

(𝑇𝑚,𝑖𝑗 − 𝑇𝑑𝑎𝑡𝑎,𝑖𝑗
𝑁 − 1

(35)

where 𝑁 is the total amount of temperature data, which is the sum
of the 𝑁𝑑 temperature points available on each pass during a total of
𝑁𝑝 passes. 𝑇𝑑𝑎𝑡𝑎,𝑖𝑗 is the flight data 𝑗 during the pass 𝑖 and corresponds
to the model temperature 𝑇𝑚,𝑖𝑗 . For this analysis a total of 4004 tem-
perature data points were used. In Fig. 11 the temperature deviation,

𝜀𝑇 , between the model and the flight data is plotted for different spin
rates. As expected, when the spin rate increases, the error decreases
reaching a stationary value for high spin rates. There are, however,
three relevant local minimum points in the plot: 0.052 rad/s, 0.10 rad/s
and 0.21 rad/s. This is not a coincidence, but those values are multiple
of the most likely satellite spin rate. However, the global minimum
is around 1 rpm and is the most plausible spin rate for the UPMSat-
2. The local minimum at 0.052 rad/s seems to be caused because the
simulated spin is half the spin rate. However, the differences between
maximum and minimum in the model oscillations (see the dotted blue
curve in Fig. 11) are higher than those in the data. Something similar
but opposite can be said for the 0.21 rad/s spin rate, which doubles
the spin rate, whose oscillations are smaller than those observed in the
data.

The foregoing shows that an angular velocity speed in the vicinity
of 0.10 rad/s is the most likely for the satellite and coincides with
the results obtained in Fig. 6 assuming the stroboscopic effect of the
measurement rate. With this speed of rotation and adequate initial con-
ditions, the thermal model of the satellite can be realistically adjusted
to the thermal data of the passes both in global trend and in amplitude
of the cyclical component. On the other hand, if the apparent angular
speed is taken as good, the results of the attitude control could be
adjusted but the thermal results would not be consistent.

4.2. Results regarding the orientation of the UPMSat-2

To evaluate the performance of the control law, it is necessary
to analyze the error between the actual satellite’s attitude and the
expected one. The UPMSat-2 control law is designed to stabilize the 𝑧-
axis almost perpendicular to the orbital plane, with the −𝑧 face pointing
in the positive direction of the normal to the orbit. Since the satellite is
in a 10:30 Sun-synchronous orbit, the incidence angle of the Sun with
the normal to the orbital plane remains nearly constant throughout
the month of observation, with a mean value of 110.7 degrees for the
month of September. Therefore, the incidence angle of the Sun with
respect to the normal to the −𝑧 face of the satellite serves as a good
indicator of the pointing precision of the control law.

Measurement225(2024)11396210A. Porras-Hermoso et al.

Fig. 9. Optimization of the initial conditions (IC) for each orbit and each spin rate. The plot corresponds to a model with a spin rate of 0.03 rad/s.

Fig. 10. Model temperatures for different spin rates (lines) and flight temperature measurements (dots) for one pass.

To assess the pointing precision, an histogram of the Sun incidence

5. Conclusions

angle with the 𝑧-axis (referred to as the illumination angle from now

on) is plotted in Fig. 12. The distribution of the incidence angle

can be fitted to a normal distribution with a mean of 112.9 degrees

and a standard deviation of 2.5 degrees. The figure also shows the

mean theoretical illumination angle if the 𝑧-axis were perfectly aligned

with the normal direction of the orbital plane (represented by the

vertical dashed line). On average, there is a difference of 2.2 degrees

between the normal direction of the orbit and the pointing direction

of the 𝑧-axis. This behavior is in good agreement with the expected

misalignment for the inclination of the orbit, as shown in Fig. 2 [29].

In this work, the in-orbit performance of the UPMSat-2 attitude
control law was studied. The magnetic control law governing the
UPMSat-2 attitude is derived from the B-dot control law, including an
additional performance: it can stabilize an axis in an orientation almost
perpendicular to the orbital plane, and then control the angular velocity
around this axis to the desired target velocity.

The analysis of the data from the satellite has been challenging
due to the low sampling rate (one data package per minute), being
similar to the expected period of the satellite’s main motion (around
one revolution per minute). This fact causes an stroboscopic effect and

Measurement225(2024)11396211A. Porras-Hermoso et al.

Fig. 11. Variation of the temperature deviation between the flight data and the model as a function of the spin rate.

Fig. 12. Assessment of the pointing control of the UPMSat-2. Histogram of the 𝑧-axis illumination angle compared to the mean value, St, of the theoretical illumination angle.

therefore the reconstruction of the original signal is required to analyze
the satellite in-orbit attitude.

After correcting that stroboscopic effect, the magnetometer data
have shown good agreement with the expected results. In addition, to
verify that the satellite is not rotating at its apparent angular velocity,
a thermal analysis has been conducted. The thermal analysis ruled out
rotation rates under 0.052 rad/s, as they did not match the general
temperature trend of the satellite. The analysis has also shown that
only high rotation rates could fit with the experimental data, and an
spin rate near 0.1 rad/s has the best agreement.

Additionally, the control law has been evaluated using Sun sensors
to determine the alignment of the 𝑧-axis with the normal direction to
the orbital plane. The results demonstrate that the control law maintain
a close alignment with a mean deviation of 2.2 degrees, which is
consistent with the theoretical deviation range.

– original draft, Writing – review & editing. Javier Piqueras: Formal
analysis, Investigation, Methodology, Software, Visualization, Valida-
tion, Writing – original draft. Javier Cubas: Conceptualization, Formal
analysis, Investigation, Methodology, Supervision, Validation, Writing
– original draft, Writing – review & editing. Elena Roibás-Millán: Data
curation, Project administration, Resources, Supervision, Visualization,
Writing – original draft, Writing – review & editing.

Declaration of competing interest

The authors declare that they have no known competing finan-
cial interests or personal relationships that could have appeared to
influence the work reported in this paper.

CRediT authorship contribution statement

Data availability

Angel Porras-Hermoso: Conceptualization, Data curation, Formal
analysis, Investigation, Methodology, Software, Visualization, Writing

Data will be made available on request.

Measurement225(2024)11396212A. Porras-Hermoso et al.

Acknowledgments

This research has been supported by the project 478 Y2020/NMT-
6427 OAPES from the program ‘‘Sinérgicos 2020’’ from Comunidad de
Madrid (Spain). The authors are also indebted to the Horizon 2020
IOD/IOV Programme of the European Union that funded the UPMSat-
2 launch. Authors are grateful to Prof. Ángel Sanz-Andrés for the
fruitful discussions of this work and his constant support regarding
the research program on spacecraft subsystems at Instituto Universi-
tario de Microgravedad ‘‘Ignacio Da Riva’’ (IDR/UPM), from Universidad
Politécnica de Madrid (UPM). Authors are also grateful to Prof. Santiago
Pindado, for providing valuable support for this work, as well as for
their contributions to previous research that have been essential to the
completion of this study. Authors also thank the STRAST group and the
IDR/UPM staff for their collaboration and support.

References

[1] W.E. Frye, E.V.B. Stearns, Stabilization and attitude control of satellite vehicles,

ARS J. 29 (12) (1959) 927–931, http://dx.doi.org/10.2514/8.4945.

[2] A.D. Anderson, J.J. Sellers, Y. Hashida, Attitude determination and control
system simulation and analysis for low-cost micro-satellites, IEEE Aerosp. Conf.
Proc. 5 (2004) 2920–2948, http://dx.doi.org/10.1109/AERO.2004.1368100.
[3] R.E. Fischell, Magnetic damping of the angular motions of earth satellites, ARS

J. 31 (9) (1961) 1210–1217, http://dx.doi.org/10.2514/8.5759.

[4] L.H. Grasshoff, A method for controlling the attitude of a spin-stabilized satellite,

ARS J. 31 (5) (1961) 646–649, http://dx.doi.org/10.2514/8.5589.

[5] M.Y. Ovchinnikov, D.S. Roldugin, A survey on active magnetic attitude con-
(2019)
trol algorithms for small satellites, Prog. Aerosp. Sci. 109 (May)
100546, http://dx.doi.org/10.1016/j.paerosci.2019.05.006, https://linkinghub.
elsevier.com/retrieve/pii/S0376042119300569.

[6] W.R. Bandeen, W.P. Manger, Angular motion of the spin axis of the tiros I
meteorological satellite due to magnetic and gravitational torques, J. Geophys.
Res. 65 (9) (1960) 2992–2995.

[7] M. Shigehara, Geomagnetic attitude control of an axisymmetric spinning satellite,

J. Spacecr. Rockets 9 (6) (1972) 391–398.

[8] K.T. Alfriend, Magnetic attitude control system for dual-spin satellites, AIAA J.

13 (6) (1975) 817–822.

[9] A.C. Stickler, K.T. Alfriend, Elementary magnetic attitude control system, J.

Spacecr. Rockets 13 (5) (1976) 282–287, http://dx.doi.org/10.2514/3.57089.

[10] M.A.A. Desouky, O. Abdelkhalik, Time-optimal magnetic attitude detumbling, J.
Spacecr. Rockets 57 (3) (2020) 549–564, http://dx.doi.org/10.2514/1.A34583.
[11] M.A. Desouky, O. Abdelkhalik, A new variant of the B-dot control for spacecraft
magnetic detumbling, Acta Astronaut. 171 (2020) 14–22, http://dx.doi.org/10.
1016/j.actaastro.2020.02.030.

[12] M.Y. Ovchinnikov, D.S. Roldugin, S.S. Tkachev, V.I. Penkov, B-dot algorithm
steady-state motion performance, Acta Astronaut. 146 (2018) 66–72, http://dx.
doi.org/10.1016/j.actaastro.2018.02.019.

[13] M. Lovera, Magnetic satellite detumbling: The b-dot algorithm revisited,

in:
Proceedings of the American Control Conference, Vol. 2015-July, 2015, pp.
1867–1872, http://dx.doi.org/10.1109/ACC.2015.7171005.

[14] H.C. Chang, W.L. Chiang, Y.Y. Lian, Efficiency investigation of conventional
satellite initial acquisition control with the consideration of orbital motion, in:
Procedia Engineering, vol. 67, Elsevier, 2013, pp. 128–139, http://dx.doi.org/
10.1016/j.proeng.2013.12.012.

[15] G.V. Smirnov, M. Ovchinnikov, F. Miranda, On the magnetic attitude control for
spacecraft via the 𝜖-strategies method, Acta Astronaut. 63 (5–6) (2008) 690–694,
http://dx.doi.org/10.1016/j.actaastro.2008.05.009.

[16] M. Lovera, A. Astolfi, Global magnetic attitude control of spacecraft in the
presence of gravity gradient, IEEE Trans. Aerosp. Electron. Syst. 42 (3) (2006)
796–805, http://dx.doi.org/10.1109/TAES.2006.248214.

[17] Y.H. Jia, S.J. Xu, L. Tang, Bias momentum attitude control system using
energy/momentum wheels, Chin. J. Aeronaut. 17 (4) (2004) 193–199, http:
//dx.doi.org/10.1016/S1000-9361(11)60236-7.

[18] R. Wiśniewski, M. Blanke, Fully magnetic attitude control for spacecraft subject
to gravity gradient, Automatica 35 (7) (1999) 1201–1214, http://dx.doi.org/10.
1016/S0005-1098(99)00021-7.

[19] C. Arduini, P. Baiocco, Active magnetic damping attitude control for gravity
gradient stabilized spacecraft, J. Guid. Control Dyn. 20 (1) (1997) 117–122,
http://dx.doi.org/10.2514/2.4003.

[20] K. Zhou, H. Huang, X. Wang, L. Sun, Magnetic attitude control for earth-pointing
satellites in the presence of gravity gradient, Aerosp. Sci. Technol. 60 (2017)
115–123, http://dx.doi.org/10.1016/j.ast.2016.11.003.

[22] G. Sechi, G. André, D. Andreis, M. Saponara, Magnetic attitude control of the

GOCE satellite, Guid. Navig. Control Syst. 606 (2006).

[23] R. Sutherland, I. Kolmanovsky, A.R. Girard, Attitude control of a 2U cubesat by
magnetic and air drag torques, IEEE Trans. Control Syst. Technol. 27 (3) (2019)
1047–1059, http://dx.doi.org/10.1109/TCST.2018.2791979, arXiv:1707.04959.
satellites using

[24] T.H. Go, R.V. Ramnath, Geomagnetic attitude control of

generalized multiple scales, J. Guid. Control Dyn. 20 (4) (1997) 690–698.
[25] H. You, Y.-W. Jan, J.-R. Tsai, Sun pointing attitude control with magnetic
torquers only, in: 57th International Astronautical Congress, in: International
Astronautical Congress (IAF), American Institute of Aeronautics and Astronautics,
2006, http://dx.doi.org/10.2514/6.IAC-06-C1.2.01.

[26] G. Avanzini, E.L. de Angelis, F. Giulietti, Acquisition of a desired pure-spin
condition for a magnetically actuated spacecraft, J. Guid. Control Dyn. 36 (6)
(2013) 1816–1821, http://dx.doi.org/10.2514/1.59364.

[27] J. Cubas, A. de Ruiter, Magnetic control without attitude determination for
spinning spacecraft, Acta Astronaut. 169 (2020) 108–123, http://dx.doi.org/10.
1016/j.actaastro.2019.12.029.

[28] D.S. Roldugin, M.Y. Ovchinnikov, Wobble of a spin stabilized satellite with
cross products of inertia and magnetic attitude control, Adv. Space Res. (2022)
http://dx.doi.org/10.1016/j.asr.2022.08.073.

[29] J. Cubas, A. Farrahi, S. Pindado, Magnetic attitude control for satellites in polar
or sun-synchronous orbits, J. Guid. Control Dyn. 38 (10) (2015) 1947–1958,
http://dx.doi.org/10.2514/1.G000751, URL http://arc.aiaa.org.

[30] A. Scholz, W. Ley, B. Dachwald, J. Miau, J. Juang, Flight results of the COMPASS-
1 picosatellite mission, Acta Astronaut. 67 (9–10) (2010) 1289–1298, http:
//dx.doi.org/10.1016/j.actaastro.2010.06.040, URL https://linkinghub.elsevier.
com/retrieve/pii/S0094576510002316.

[31] G. Creamer, The HESSI magnetic attitude control system, in: Guidance, Naviga-
tion, and Control Conference and Exhibit, in: Guidance, Navigation, and Control
and Co-located Conferences, American Institute of Aeronautics and Astronautics,
1999, http://dx.doi.org/10.2514/6.1999-3969.

[32] J. Wertz, Spacecraft Attitude Determination and Control, Springer Science &

Business Media., 2012.

[33] K.F. Jensen, K. Vinthhe, Attitude determination and control system for AAUSAT3

(Ph.D. thesis), Aalborg University, 2010.

[34] J. Zamorano, J. Garrido, J. Cubas, A. Alonso, J.A. de la Puente, The Design and
Implementation of the UPMSAT-2 Attitude Control System, IFAC-PapersOnLine
50 (1) (2017) 11245–11250, http://dx.doi.org/10.1016/j.ifacol.2017.08.1607.

[35] A.M. Gomez-San-Juan, J. Cubas, S. Pindado, On the thermo-electrical modeling
of small satellite’s solar panels, IEEE Trans. Aerospace and Electron. Syst. 57 (3)
(2021) 1672–1684, http://dx.doi.org/10.1109/TAES.2020.3048797.

[36] H. Nyquist, Certain topics in telegraph transmission theory, Trans. Am. Inst.
Electr. Eng. 47 (2) (1928) 617–644, http://dx.doi.org/10.1109/T-AIEE.1928.
5055024.

[37] A. Slavinskis, H. Ehrpais, H. Kuuste, I. Sünter, J. Viru, J. Kütt, E. Kulu, M.
Noorma, Flight results of estcube-1 attitude determination system, J. Aerosp.
Eng. 29 (1) (2016) 04015014, http://dx.doi.org/10.1061/(ASCE)AS.1943-5525.
0000504, URL https://ascelibrary.org/doi/abs/10.1061/%28ASCE%29AS.1943-
5525.0000504 http://ascelibrary.org/doi/10.1061/%28ASCE%29AS.1943-5525.
0000504.

[38] D. Ran, T. Sheng, L. Cao, X. Chen, Y. Zhao, Attitude control system design and
on-orbit performance analysis of nano-satellite - "tian tuo 1", Chin. J. Aeronaut.
27 (3) (2014) 593–601, http://dx.doi.org/10.1016/j.cja.2013.11.001.

[39] F. Santoni, F. Bolotti, Attitude determination of small spinning spacecraft using
three axis magnetometer and solar panels data, in: IEEE Aerospace Conference
Proceedings, vol. 7, IEEE, 2000, pp. 127–133, http://dx.doi.org/10.1109/aero.
2000.879282, URL http://ieeexplore.ieee.org/document/879282/.

[40] A. Porras-Hermoso, D. Alfonso-Corcuera, J. Piqueras, E. Roibás-Millán, J. Cubas,
J. Pérez-Álvarez, S. Pindado, Design, ground testing and on-orbit performance
of a sun sensor based on cots photodiodes for the upmsat-2 satellite, Sensors 21
(14) (2021) 4905, http://dx.doi.org/10.3390/s21144905.

[41] S. Carletta, P. Teofilatto, M. Farissi, A magnetometer-only attitude determination
strategy for small satellites: Design of the algorithm and hardware-in-the-loop
testing, Aerospace 7 (1) (2020) 3, http://dx.doi.org/10.3390/aerospace7010003,
URL https://www.mdpi.com/2226-4310/7/1/3.

[42] H.E. Soken, S.-i. Sakai, Magnetometer only attitude estimation for spinning
small satellites, in: 2017 8th International Conference on Recent Advances in
IEEE, 2017, pp. 369–374, http://dx.doi.org/10.
Space Technologies (RAST),
1109/RAST.2017.8002996, URL http://ieeexplore.ieee.org/document/8002996/.
[43] R. Burton, S. Rock, J. Springmann, J. Cutler, Online attitude determination
of a passively magnetically stabilized spacecraft, Acta Astronaut. 133 (Octo-
ber 2015) (2017) 269–281, http://dx.doi.org/10.1016/j.actaastro.2017.01.024,
https://linkinghub.elsevier.com/retrieve/pii/S0094576515301399.

[44] C. Hajiyev, D. Cilden, Y. Somov, Gyro-free attitude and rate estimation
for a small satellite using SVD and EKF, Aerosp. Sci. Technol. 55 (2016)
324–331, http://dx.doi.org/10.1016/j.ast.2016.06.004, URL http://linkinghub.
elsevier.com/retrieve/pii/S1270963816302139.

[21] M.L. Psiaki, Nanosatellite attitude stabilization using passive aerodynamics and
active magnetic torquing, J. Guid. Control Dyn. 27 (3) (2004) 347–355, http:
//dx.doi.org/10.2514/1.1993.

[45] J.D. Searcy, H.J. Pernicka, Magnetometer-only attitude determination using novel
two-step Kalman filter approach, J. Guid. Control Dyn. 35 (6) (2012) 1693–1701,
http://dx.doi.org/10.2514/1.57344, https://arc.aiaa.org/doi/10.2514/1.57344.

Measurement225(2024)11396213A. Porras-Hermoso et al.

[46] A. Labibian, A. Alikhani, S.H. Pourtakdoust, Performance of a novel heat
based model for spacecraft attitude estimation, Aerosp. Sci. Technol. 70 (2017)
317–327, http://dx.doi.org/10.1016/j.ast.2017.08.021.

[50] M. Gadalla, M. Ghommem, G. Bourantas, K. Miller, Modeling and thermal
analysis of a moving spacecraft subject to solar radiation effect, Processes 7
(11) (2019) 1–15, http://dx.doi.org/10.3390/pr7110807.

[47] A. Labibian, S.H. Pourtakdoust, A. Alikhani, H. Fourati, Development of a
radiation based heat model for satellite attitude determination, Aerosp. Sci.
Technol. 82–83 (2018) 479–486, http://dx.doi.org/10.1016/j.ast.2018.09.031.

[48] T. Posielek, J. Reger, A novel attitude representation in view of spacecraft
IFAC-PapersOnLine 54 (14)

attitude reconstruction using temperature data,
(2021) 500–505, http://dx.doi.org/10.1016/j.ifacol.2021.10.404.

[49] T. Posielek, J. Reger, Attitude reconstruction of a spacecraft from temperature
measurements in solar eclipse analysis and observer design for a not globally
observable non-linear system, IEEE Trans. Control Syst. Technol. (2022) 1–15,
http://dx.doi.org/10.1109/TCST.2022.3187916.

[51] A. Porras-Hermoso, J. Cubas, S. Pindado, Use of spacecraft solar panels and sun
sensors for estimation of the sun-pointing direction in the upmsat-2 mission,
Measurement 204 (2022) 112061, http://dx.doi.org/10.1016/J.MEASUREMENT.
2022.112061.

[52] X. Xia, C. Guo, G. Xie, Investigation on magnetic-based attitude de-tumbling
algorithm, Aerosp. Sci. Technol. 84 (2019) 1106–1115, http://dx.doi.org/10.
1016/j.ast.2018.11.035.

[53] A. González-Llana, L. Peinado-Pérez, E. Roibás-Millán, J. Pérez-Álvarez,

I.
Torralbo, A. Gómez-San Juan, Thermal testing campaign of the upmsat-2, in:
Proceeding of the 8th European Conference for Aeronautics and Space Sciences
(EUCASS), 2019, pp. 1–11.

Measurement225(2024)11396214