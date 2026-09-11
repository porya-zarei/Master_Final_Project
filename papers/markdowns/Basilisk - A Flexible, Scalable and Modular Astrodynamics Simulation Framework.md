BASILISK: A FLEXIBLE, SCALABLE AND MODULAR ASTRODYNAMICS SIMULATION
FRAMEWORK

Patrick W. Kenneally ∗, Scott Piggott† and Hanspeter Schaub ‡

University of Colorado, Boulder

ABSTRACT

The Basilisk astrodynamics framework is a spacecraft simu-
lation tool developed with an aim of strict modular separation
and decoupling of modeling concerns in regards to coupled
spacecraft dynamics, environment
interactions and ﬂight
software algorithms. The three core elements of the Basilisk
modular architecture are described. These core elements
are the fundamental functional Basilisk objects of Modules,
Tasks, and Task Groups. The message passing system is a
critical layer which facilitates Module input and output data
routing. Outlines of Basilisk’s data logging and Monte Carlo
simulation functionality are provided. The implementation
of the Basilisk, a Python wrapped C++/C technology stack
is described. Finally, example simulation conﬁgurations and
results are provided to demonstrate the modularity and ﬂexi-
bility of the framework.

Index Terms— simulation, modular, python, dynamics,

1. INTRODUCTION

Spacecraft simulation software tools are an indispensable part
of modern spacecraft design processes. The continual in-
crease in complexity of spacecraft missions and maneuver de-
sign, dynamical and kinematic design veriﬁcation and post-
launch telemetry analysis all heavily rely on software simu-
lation tools. These simulation tools provide engineers with
the ability to increase the quality of design and testing by re-
ducing cost and duration of development. For example, pro-
posed changes to a missions conﬁguration, parameter tuning
or in-ﬂight anomalies may be explored via Monte Carlo simu-
lation. Additionally, hardware in the loop testing (HWIL) al-
lows for veriﬁcation and validation of the spacecraft hardware
and software systems in a controlled laboratory environment.
Such HWIL testing can expose technical faults and system in-
tegration problems saving considerable project ﬁnancial and
personnel resources before launching the system to space.

∗Graduate Research Assistant, Smead Aerospace Engineering Sciences

Department

†ADCS Integrated Simulation Software Lead,Laboratory for Atmo-

spheric and Space Physics

‡Professor, Glenn L. Murphy Endowed Chair, Smead Aerospace Engi-

neering Sciences Department

Basilisk is an astrodynamics framework that simulates
complex spacecraft systems in the space environment. While
many simulation tools possess overlapping features with
Basilisk, none others possess the unique characteristics of
Basilisk. These characteristics are that Basilisk is a highly
modular, Python user-friendly, open-source simulation frame-
work that provides sufﬁciently accurate (ﬁdelity is conﬁg-
urable) coupled vehicle position and attitude dynamics, along
with optional structural ﬂexing, imbalanced momentum ex-
change device, and fuel slosh dynamics, with at least a 365
times speedup (one mission year in one compute time day).
Furthermore, Basilisk is equally well employed during early
mission design phases as it is later on during detailed de-
sign phases and further in post-launch telemetry analysis and
spacecraft command sequence validation.

This paper describes the Basilisk framework in three pri-
mary sections. In Sec. 2 a brief survey of the current state-
of-the-art commercial-off-the-shelf (COTS) and government-
off-the-shelf (GOTS) spacecraft simulation software is given.
Each of these COTS/GOTS systems posses unique feature
sets. These unique feature sets predispose each tool excel
when applied to different classes of spacecraft system anal-
ysis, by different engineering teams.

Section

4 gives a detailed account of the aforemen-
tioned novel Basilisk system architecture, which allows for
the rapid development of a simulation for of a wide vari-
ety of complex spacecraft systems. The key architectural
components discussed are the Basilisk fundamental build-
ing blocks which govern simulation execution, the Basilisk
message system which facilitates data passing between mod-
els, and the Basilisk spacecraft dynamics implementation.
Sec. 5 outlines the simulation execution ﬂow of control and
how the fundamental components of Modules, Tasks, and
Task Groups work together to provide the user with ﬂexible
control over their simulation design, integration rates and
message passing. Section 3 details the software stack used to
develop and build the Basilisk framework. Sections 7 and 6
provide and overview of the Basilisk multi-processing Monte
Carlo tools and the ability to log, process, and analyze large
(multi-gigabyte) data sets. In the ﬁnal section of this paper a
number of archetypal Basilisk simulation conﬁgurations will
be presented from the perspective of the end user engineer to
illustrate the functionality of this design.

2. ASTRODYNAMICS SIMULATION TOOLS

Astrodynamics simulation tools can be broadly categorized
into three groups; Commercial off the shelf (COTS), Govern-
ment off the shelf (GOTS) and general open source. A num-
ber of tools had their naissance in the GOTS category and
subsequently moved to the open source category. A list of
popular tools which will subsequently be referred to is given
below.

• Simulink/LabView [1]

• AGI STK [2]

• a.i. FreeFlyer [3]

• NASA General Mission Analysis Tool (GMAT) [4]

• NASA Trick [5]

• OreKit [6]

• DART/Dshell [7]

• NASA 42 [8]

Additionally each tool is developed with a speciﬁc subset
of astrodynamics simulation purposes in mind. For example
the OreKit, GMAT and STK tools were initially developed
with a focus on high ﬁdelity orbit dynamics and estimation,
propagation and trajectory design. As a result these tools in-
clude a range of different propagators, complex multi body,
gravity models, drag, solar radiation pressure and orbit deter-
mination tools. For example the Orekit tool includes 6 op-
tional methods to model atmospheric drag, from simple ex-
ponential models to empirical predictive models such as the
Marshall Solar Activity Future Estimation [9].

When assessing software packages in the context of their
ability to simulate full spacecraft dynamics it is important to
identify how the dynamics are computed and how this im-
pacts the modularity of the implementation. For example
in the subsequent year to their release, tools such as OreKit
and STK have increased their ability to accommodate space-
craft attitude. STK can be paired with the SOLIS plugin, a
commercial plugin to the AGI Systems ToolKit which models
spacecraft translational and attitude dynamics. And while the
SOLIS plugin enhances STK’s spacecraft dynamics, it does
not model disturbances which may alter the spacecraft’s cen-
ter of mass[10]. Similarly, OreKit models the spacecraft as a
rigid body, and the dynamics are primarily focused on deﬁn-
ing perturbations as external forces and torques.

Two tools which do provide increased modularity and
the ability to customize the spacecraft dynamics are the Jet
Propulsion Laboratory Dynamics Algorithms for Real-Time
Simulation (DARTS) software package and NASA’s ”42”
software package [11, 8]. The DARTS tool uses spatial op-
erator algebra for the development of multibody dynamics to

generate a spacecraft system mass matrix in a form that is
efﬁciently solved recursively [12]. Similarly, the simulation
package ”42” allows for spacecraft composed of multiple
rigid or ﬂexible bodies using tree topology to formulate the
dynamics. Both of these formulations allow developers to
add arbitrary models to the simulation without signiﬁcant
change to the code base.

It can be easily agreed upon that it is unreasonable goal
for a simulation tool to accommodate all possible missions
conﬁgurations and spacecraft subtleties out-of-the-box. On
this basis, it is reasoned that extensibility of a simulation tool
via means of scriptability and customization code develop-
ment is needed to allow engineers to adapt the tool to the
particular speciﬁcation and requirements of their mission. It
is then easy to see that all of the tools listed include some
level of scriptability while others enable signiﬁcantly more
customization. For example AGIs STK offers the Connect
and Object Model APIs which facilitate the addition of cus-
tom simulation models excluding the spacecraft dynamics. In
contrast JPLs DARTS tool allows a user to compile and add a
completely custom model to any part of the simulation frame-
work. This may include a model of the ﬂexible dynamics of a
large solar panel boom or the addition of a simulated ground
station.

While it is not surprising that none of the COTS tools use a
version of an open source license, it is interesting to note that
COTS tools are typically not cross platform in so far as they
do not support installation on each of the three big OS variants
of macOS, Windows and Linux (MATLAB excepted).

Finally, a large feature which is not available by default in
most tools is Hardware-in-the-loop and Software-in-the-loop
functionality. Of the tools listed MATLAB/Simulink and the
DARTS/Dshell tools support HWIL and SWIL system. Pro-
viding this functionality now enables the use of the same tool
and ﬂight algorithms through multiple phases of the mission
and in multiple engineering teams across an organization.

3. SOFTWARE STACK AND BUILD

The core Basilisk architectural components and most modules
are written in C++ to allow for object-oriented development
and fast execution speed. However, Basilisk Modules can also
be developed using Python, for easy and rapid prototyping, C
(to allow ﬂight software modules to be easily ported directly
to ﬂight targets) and Fortran (to accommodate legacy space
environment models).

Whereas Basilisk Modules are developed in a number
of computing languages, Basilisk users interact and develop
simulation scenarios using the Python programming lan-
guage. Each Module is represented by an implementation
C/C++ implementation. Python bindings for these classes/-
ﬁles are available for all Modules and supporting simulation
utilities and core functionality as indicated in Fig. 1. The
Python bindings are auto-generated at build time using the

SWIG tool. At build time, code for Modules, and core func-
tionality and utilities is compiled into individual libraries and
paired with their respective Python wrappers. These Python
wrappers mirror the underlying C++ classes or C ﬁles’ pub-
licly available variables and functions. The Python bindings
allow users to employ the the Modules functionality within
the Python environment.

Fig. 1. An example layout of a complete Basilisk simula-
tion where each element of the system has SWIG generated
Python interfaces available in the Python environment.

With the Python user layer and Basilisks cross-platform
development, (currently developed for macOS, Windows, and
Linux systems) the modularity results in no compile time or
run time dependencies between one module and another. This
modularity provides the engineer with the ability rapidly de-
velop and reconﬁgure their simulation scenario in the Python
language.

4. MODULARITY IN BASILISK

The types of missions, which Basilisk can be used to simu-
late lay on a spectrum with earth orbiting cubesats at one end
and interplanetary probes and spacecraft constellations at the
other. The hallmark of the Basilisk framework is its highly
modular system architecture. Modular design has been the
guiding principle throughout Basilisk’s development. The re-
sult is that Basilisk implements only two core system com-
ponents, the Basilisk message exchange and Basilisk simu-
lation controller. These two components are the only com-
ponents required to begin building a Basilisk simulation sce-
nario. Basilisk’s modular design is achieved by three key de-
sign choices. The ﬁrst is the complete decoupling of model
and run loop dependence. The second design choice is to use
a message exchange approach to managing module input and
output data and inter-module data requirements. Finally, a dy-
namics manager is implemented to manage the fully-coupled

nature of a spacecraft rigid body dynamics.

4.1. Components

Basilisk’s structure is built upon three simulation building
blocks. These buildings blocks are Modules, Tasks and Task
Groups and they are depicted in their relationship to each
other in Fig. 2. A Basilisk Module is a stand-alone code
which typically implements a speciﬁc model (E.g. an actua-
tor, sensor, and dynamics model) or self-contained logic (E.g.
translating a control torque to a RW command voltage). Mod-
ules receive data on which they are dependent from messages
to which they have subscribed and they publish their data as
messages.

Tasks are groupings of modules. A Task has a set inte-
gration rate which directs the update rate of all modules as-
signed to that Task. Each Task has an individually set integra-
tion rate. As a result a simulation may group modules with
different integration rates according to desired ﬁdelity. Fur-
thermore, the set Task integration rate can be adjusted during
a simulation to capture increased resolution for a particular
duration. For example an analyst may increase the integra-
tion rate for the Task containing a set of spacecraft dynam-
ics modules in order to capture the high-frequency dynamics
of ﬂexing solar panels and thruster ﬁrings during Mars Orbit
Insertion (MOI). Yet the integration time step may be kept
to a longer duration during the less active dynamics mission
phases such as cruise.

The execution of a Task and therefore the Modules within
that Task is controlled by either enabling or disabling the
Task. A Task’s enabled status can be toggled any number
of time during a simulation. This feature is particularly use-
ful for enabling or disabling FSW focused Modules in a Task
related to the simulated spacecraft mode e.g. Safe Mode, Sun
Pointing.

Task Groups are the highest level grouping of Basilisk
components. Task Groups act as a container to Tasks and pro-
vides a mechanism for resolving messaging dependencies be-
tween Modules at simulation initialization, which is discussed
in greater detail in Sec. 4.2. Task Groups can be considered
silos of Tasks and the messages published and subscribed to
by Modules.

4.2. Message System

The Basilisk messaging system facilitates the input and output
of data between simulation Modules. The messaging system
decouples the data ﬂow between Modules and Task Groups
and removes explicit inter-Module dependency thus further
supporting the modularity of the Basilisk architecture.

A Basilisk Module reads input messages and writes out-
put messages to the Basilisk messaging system. The message
system acts as a message broker for a Basilisk simulation.

The Basilisk messaging exchange manages the trafﬁck-
ing of messages and employs a publisher-subscriber message

Python Interface (SWIG)Message StorageSensor ReadTask Group: FSWCSS DecodeMIRU DecodeStar Tacker AcquireAttitude Nav2 Hz1 HzAtt UKFNav AggregateMed Rate DKERWACSSTask Group: DKETask 3SRPHigh Rate DKE10 Hz100HzFlexible PanelsMessage StoragePython Environment - Simulation Scenario ScriptsFig. 2. Basilisk Task Group, Tasks and Module layout.

passing nomenclature. A single module may read and write
any number of messages. A module that writes output data,
registers the ’publication’ of that message by creating a new
message entry with the message exchange. Conversely, a
module that requires data output from another Module(s) sub-
scribes to a message. The messaging exchange then maintains
the messages read and written by all modules and the network
of publishing and subscribing modules.

A message is deﬁned by a unique message name, a pay-
load data structure (typically a C/C++ struct). The messag-
ing system maintains meta-data in a message header for each
message deﬁnition. The message header meta-data includes a
list of allowed message publishers, subscribers, buffer mem-
ory locations and read and write statistics.

The messaging system implements the message storage
as directly managed memory. As shown in Fig. 3(a) a region
of memory is allocated and managed as the message storage
container. The messaging system manages multiple storage
containers, one for each Task Group. The size of the allo-
cated memory for each storage container is determined by the
combined size of the number of created messages, their as-
sociated header and the number of message buffers allocated
for the message. It is important to note, that all messages are
double buffered in the messaging system. For example, when
a Module writes an updated message to the messaging sys-
tem, the messaging system will alternate writing between the
two buffers. This helps to protect data integrity during mes-
sage writes and facilitates the, albeit rare, use case in which
two modules must write a single message. However, as shown
in Fig. 3(a), a Module can declare to increase the number of
buffers for a speciﬁc message.

A message is created in the message system when a Mod-
ule invokes the call, shown in Listing.
4.2, on the Sys-
temMessaging singleton instance. This function call takes
a unique message name, the maxSize in bytes of the mes-
sage payload struct, the number of buffers into which an entry
of the message may be written, the type of message payload

(a) Message system mem-
ory layout

(b) Message system mem-
ory layout upon new mes-
sage creation

Fig. 3. Basilisk messaging system memory layout and orga-
nization.

struct and the identiﬁer of the module creating the new mes-
sage. As demonstrated by Fig. 3(b), the memory allocated
is increased and the other messages are moved within the al-
located memory to accommodate the new message ‘msg n +
1’.

2

3

1 SystemMessaging::CreateNewMessage(
std::string messageName,
uint64_t maxSize,
uint64_t numMessageBuffers,
std::string messageStruct,
int64_t moduleID)

4

5

6

A Module ’creates’ a message in the message exchange
by passing to the message exchange a message payload type
and a unique name and receives in return a unique message
ID generated by the message exchange. It is this message ID
with which a Module will reference its writing or reading of
an updated message.

A three stage process carried out at simulation initializa-
tion resolves the message subscription and publication pairs.
Simulation initialization and the associated resolving of mes-
sage pub-sub pairs is discussed in greater detail in Sec. 5.
However, the functionality of a Task Group Interface (a uni-
directional message exchange from one Task Group to a sec-
ond Task Group) is described here. The design where each
Task Group has a single associated message storage container
is intentional and seeks to accommodate simulation conﬁg-
urations where the dynamic and environment Modules re-
main wholly separate from the ﬂight software Modules. This
separation, while being useful to organize related Modules
within a simulation, becomes signiﬁcantly useful when op-
erating Basilisk as a distributed simulation across multiple

Task 1module 1module 2Task Group 1Task nmodule nTask 1Task Group nTask nmodule 1module 2module nmsg nbuffer 1Msg Storage 1msg 1buffer nmsg headerMsg Storage 1msg 1msg nmsg n + 1compute resources. For example in a SWIL conﬁguration
the dynamics and environment Module’s execute on a desktop
computer while the FSW executes on a separate ﬂight target
processor or processor emulator. However, there are further
less stereotypical instances in which a simulation developer
would like for messages in one Task Group to be available to
Modules in a second Task Group. To facilitate the exchange
of messages between Task Groups, Task Group Interfaces are
available to make this connection. A Task Group Interface is
a unidirectional message exchange from one Task Group to a
second Task Group. This allows for Modules in a ﬁrst Task
Group to publish messages to a second Task Group and, as
implied, Modules in the second Task Group to subscribe to
messages published in the ﬁrst Task Group.

spacecraft. Examples of Dynamic Effectors include: gravity,
thrusters, solar radiation pressure (SRP) and drag.

For a Module to operate as either a State or Dynamic Ef-
fector, the implemented Module class inherits from the Sta-
teEffector or DynamicEffector parent classes. A dynamics
Module developer is responsible for implementing only the
dynamics of the effector model. For a State Effector a devel-
oper must provide a custom implementation of the following
three functions;

• updateEffectorMassProperties() - provide
contributions to the spacecrafts mass and inertia prop-
erties

• updateContributions() - provide coupled con-

tributions to the back-substitution matrices

• computeDerivatives() - compute the Module’s

own state derivatives

For the non-coupled Dynamics Effector the custom imple-
mentations required are less;

• computeBodyForceTorque() -

the
body or inertial frame force and/or torque due to the
Effector.

compute

Fig. 4. A notional messaging system publish and subscribe
map for a message storage container of a single Task Group.

4.3. Dynamics Manager

The third and ﬁnal piece of Basilisk’s modular design is the
implementation of a Dynamics Manager. The spacecraft dy-
namics are modeled as fully coupled multi-body dynamics
with the generalized equations of motion (EOM) being ap-
plicable to a wide range of spacecraft conﬁgurations. The
implementation, as detailed in reference [13], uses a back-
substitution method to modularize the EOMs and leverages
the modularized equations to allow the arbitrary addition of
forces and torques to a central spacecraft hub.

The concept of an “Effector” is used to deﬁne objects that
are attached to a spacecraft and have a effect on the space-
craft’s dynamics. Effectors are determined to belong to one of
two groups; either State Effectors or Dynamic Effectors. State
Effectors are those Modules which have dynamics states to
be integrated and therefore contribute to the coupled dynam-
ics of the spacecraft. Examples of State Effectors are reaction
wheels, ﬂexible solar arrays, variable speed control moment
gyroscopes (VSCMGs) and fuel slosh. In contrast, a Dynamic
Effectors are Modules which implement the phenomena that
result in an external forces or torques being applied to the

The Dynamics Manager transparently organizes and ag-
gregates the various dynamic contribution of each Dynamic
Effector Module in a simulation ensuring all dynamic states
are updated and propagated. The user may select from various
numerical integration schemes to propagate the spacecraft dy-
namics. Moreover, the interface between the Dynamics Man-
ager and the integrator has been generalized to allow other
developers to implement their own desired numerical integra-
tion scheme.

5. EXECUTION CONTROL

A Basilisk simulation executes through a number of distinct
initialization, integration, and shut down phases. The high
level ﬂow of control for a Basilisk simulation is shown in
Fig. 5.

Basilisk Modules, Tasks, Task Groups, and their associ-
ated message storage and linkages are initialized by a two
stage process. Each Basilisk Module inherits and is there-
fore an instance of a Basilisk SysModel class. As shown in
Listing. 5, the SysModel class deﬁnes an interface of four
functions, which a Module must implement. These functions
are called on each Module as part of the overall simulation
ﬂow of control process.

1

2

3

4

virtual void SelfInit();
virtual void CrossInit();
virtual void UpdateState(uint64_t
currentSimNanos);
virtual void Reset(uint64_t
currentSimNanos);

msg 1msg 2Module 1Module 2module 3module 4msg 4msg 3Msg Systemmsg nmsg 1pubsubmodule 6Module 7Module is responsible for initializing the dynamics integra-
tion process and in doing so collects the dynamics contribu-
tion of all Modules which are also Dynamic Effectors.

Following the iteration through each of the Task Group
and Task loops, the next call time for a Task and Task Group
are set. This is required because each Task with in a Task
Group may have a different integration time step and Tasks
may be enabled or disabled at various times during the sim-
ulation. As a result, the next call time for a Task and Task
Group and therefore the modules can change from loop to
loop and updating the next call time allows the simulation to
skip forward in time according to the desired combined inte-
gration rates.

After all Tasks and Modules within a Task Group have
been updated the message logger copies all messages and
Module variables and saves those for that time step. Vari-
ables are logged at the frequency determined by the user prior
to simulation initialization. as would be expected, the high-
est logging frequency is driven by the highest frequency at
which the Task, containing the Module producing the data, is
executed.

6. DATA LOGGING

Data output by Modules through messages or internal Mod-
ule variables (which have a declared public scope in their
C++ class deﬁnition) may be logged. Data to be logged is
determined prior to a simulation run where a user may spec-
ify complete messages, a single variable within a message
or internal simulation variables to be logged and the logging
rate desired for the data. While executing, the simulation
Data Logger reads the requested messages and variables. At
the conclusion of the simulation the analyst can retrieve the
data with each message and variable made available as a time
stamped series of the desired data type or message data. This
returned data format may be directly used in post processing
scripts developed in Python (Numpy, PANDAS).

7. MONTE CARLO

A key beneﬁt of Basilisk’s Python interface is the abil-
ity to take any simulation script and with minimal code
changes turn that script in a Monte Carlo simulation fash-
ion. Basilisk’s Monte Carlo functionality includes at run
time generated variable dispersions, logging and saving of
simulation dispersed initial conditions, logging and saving
of simulation data in the portable Dataframes data structure
from the Python module named PANDAS, and multi-process
execution of simulation runs.

Variable dispersions are built upon base Python imple-
mentations of scalar, vector, and tensor variable type disper-
sion classes. Currently Basilisk maintains, uniform and nor-
mal dispersion for both, Cartesian variable, Euler angle, and
MRP descriptions. However, each of these individual base

Fig. 5. Basilisk high level ﬂow of control for simulation exe-
cution.

The two stages of simulation initialization are self initial-
ization and cross initialization. During self initialization each
Module’s selfInit() function is called allowing a Mod-
ule to perform any internal setup and register the messages
it intends to publish with the messaging system. Next, dur-
ing cross initialization each Module’s crossInit() func-
tion is called allowing a Module to subscribe to messages that
were made available as published messages in the previous
Self Initialization stage.

The simulation ﬂow of control is governed by three loop
iterations. The outermost loop iterates through each of the
instantiated Task Groups according to each Task Group’s as-
signed priority level. Within each Task Group, each Task is
looped through. Subsequently within each Task, all Modules
within a task are iterated through according to their priority
within their Task. For each Module in a Task the Module’s
updateState() function is called. The logic contained in
the updateState() function is custom to each Module.
However, a common sequence of any updateState()
function is to read subscribed input message, perform a com-
putation deﬁned by the Module and then write published
output messages for use by other Modules. Of particular
importance is the special SpacecraftDynamics Module
which implements the aforementioned Dynamics Manager.
The updateState() of the SpacecraftDynamics

update next task call timeupdate next taskgroup call timelog msgs and variablesstartend after sim timeself/cross inittask groupstasksmodulesupdateState/intergratedispersion can be inherited by a user’s custom dispersion im-
plementation allowing users to generate dispersions for of
variables with different physical bounds, variances and spe-
ciﬁc statistical distributions.

The initial conditions, including the dispersed variables
and random number seeds are saved in a JSON ﬁle format
for each Monte Carlo run. This allows a user to rerun and
examine closer, one or more, particular runs of interest from
a Monte Carlo simulation, with bit-for-bit repeatability.

Multiprocess capability is a key beneﬁt of the Monte
Carlo tools. The Monte Carlo controller uses the Python
module named Multiprocessing to spawn and manage as
many Python Basilisk simulation processes as the user or host
machine allows. For example a computer with a 4 core CPU,
each with two virtual cores will be used by the Monte Carlo
controller as a machine with 8 processors. The controller
will launch 8 simulations at once and continue to provide
simulations to the worker pool of processes until all work
is done. Each simulation execution is handled individually
with data logging, initial conditions and failures all logged
for later analysis. Post processing of Monte Carlo data makes
use of the convenient PANDAS statistical and data manip-
ulation functions. While single simulation plotting is done
with the more traditional Matplolib package, plotting of large
multi-gigabyte data sets is achieved using the DataShaders
plugin to the Bokeh plotting library. This module employs a
rasterized plotting approach allowing for the generation plots
of extremely large data set in a matter of seconds.

8. DEVELOPMENT APPROACH - OPEN SOURCE

Basilisk’s naissance is in the support of the design and devel-
opment of the attitude determination and control system for
an interplanetary spacecraft. The intention was to use Basilisk
as an early mission Phase A/B design and analysis tool, a ﬂght
algorithm veriﬁcation and validation tool duing latter Phase
C, and ﬁnally as the space environment and dynamics simula-
tor for HWIL and SWIL testing during Phase D. Basilisk has
been utilized in all these mission phases and its continually
increasing utility prompted the original development team at
the LASP and the AVS Lab to make the project available
as an open source project. Basilisk uses an Internet System
Consortium (ISC) License which is a permissive software li-
cense simply requiring attribution and relinquishing the cre-
ator of liability [14]. It is anticipated that such a permissive
license will help to encourage experimentation and contribu-
tion back to the main Basilisk project. Basilisk is available
for download from bitbucket. The project employs a gitﬂow
[15] development process where decisions about architecture
changes and release cycles occur within the combined AVS
Lab and LASP team.

Basilisk has undergone an internal veriﬁcation and vali-
dation effort within LASP and the AVS Lab and by compari-
son to ﬂight data from previous missions. As an open source

project, Basilisk will beneﬁt from strong community and en-
gaged users. The community shall provide further validation,
bug ﬁxes and functionality additions. In the short time that
Basilisk has been openly available a number of ﬁxes and func-
tionality additions have been made.

9. EXAMPLE BASILISK SIMULATION
CONFIGURATIONS

Constructing a Basilisk simulation scenario requires the cre-
ation of Task Groups, assigning Tasks to these Task Groups,
and the instantiation of desired Modules within the desired
Task.

The following example demonstrates the important Basilisk

function calls which conﬁgures a simple Earth orbiting space-
craft with multiple gravity bodies and interacting with a
SPICE interface governing the bodies positions and the space-
craft’s initial state. The spacecraft initial position and velocity
are extracted from the SPICE ephemeris ﬁle for the Hubble
Space Telescope. A conceptual simulation conﬁguration is
presented in Fig. 6 showing the Modules, Task, and Task
Group conﬁguration.

Fig. 6. Concept diagram of simple multi body gravity orbiter
Basilisk simulation conﬁguration.

The ﬁrst function call sets up a new Basilisk simulation.

1 scSim = SimulationBaseClass.SimBaseClass

()

Following this at least a single Task Group and Task must
be created and linked. This is done by creating a Task Group
also referred to as a Process and then adding a Task to this
Task Group. The Task integration rate is set to 5 seconds.

Task @ 0.2 HzSpacecraft DynamicsTask GroupGravity Effectorearth, mars barycenter sun, moon, jupiter barycenter SPICEHowever, in Basilisk, the base time scale is nano seconds and
so the sec2nanos() utility is used for this conversion.

1 dynProcess = scSim.CreateNewProcess(

simProcessName)

2 dynProcess.addTask(scSim.CreateNewTask(

simTaskName, sec2nanos(5)))

Now the core Basilisk structures are instantiated and one
begins to populate the simulation with various Basilisk Mod-
ules. The ﬁrst Module here is the SpacecraftPlus Module
which instantiates the rigid body hub to which other stateEf-
fectors and dynamicEffectors can be associated. The Space-
craftPlus() object is added to the single Task.

1 scObject = spacecraftPlus.SpacecraftPlus

()

2 scSim.AddModelToTask(simTaskName,

scObject, None, 1)

A number of gravity bodies (dynamicEffectors) are in-

stantiated and added to the scObjects gravBodies list.

1 gravBodies = gravFactory.createBodies([’

earth’, ’mars barycenter’, ’sun’, ’
moon’, ’jupiter barycenter’])

2 scObject.gravField.gravBodies =

spacecraftPlus.GravBodyVector(
gravFactory.gravBodies.values())

Finally, a SPICE Module is created using the convenience
function available in the gravity body factory class. This
SPICE Module is also added to the Task.

1 gravFactory.createSpiceInterface(bskPath
+’/supportData/EphemerisData/’,

timeInitString)

2 scSim.AddModelToTask(simTaskName,

gravFactory.spiceObject, None, -1)

To begin the simulation three function calls are required.
The ﬁrst initializes the Task Groups, Tasks and Modules
added to the simulation calling the selfInit, crossInit, resetInit
functions. Following this, the stop time is set and then the
simulation is launched.

1 scSim.InitializeSimulation()
2 scSim.ConfigureStopTime(simulationTime)
3 scSim.ExecuteSimulation()

Simulations can be executed for a speciﬁed duration af-
ter which conﬁguration changes are made and the simula-
tion continued further. This can be useful to simulate speciﬁc
spacecraft sequence instruction sets. Additionally, Events ob-
jects are available and can be set to trigger a custom user pro-
vided function. This custom user provided function means
that that the developer can trigger and change any variable/s-
tate in the simulation that is available through the Python in-
terface of each Basilisk Module.

1 scSim.ConfigureStopTime(sec2nanos(20))
2 scSim.ExecuteSimulation()
3 # Command the FSW to go into safe mode

and advance to ˜ periapsis
4 scSim.modeRequest = ’safeMode’
5 scSim.ConfigureStopTime(sec2nanos(60))
6 scSim.ExecuteSimulation()
7 # Command the FSW to go into Nav only

mode

8 scSim.ConfigureStopTime(sec2nanos(60 *

11 * 1 + 30)))

9 scSim.modeRequest = ’navOnly’
10 scSim.ExecuteSimulation()

An example plot generated from Basilisk data using the
Python post-processing tools is shown in Fig. 7 shows the
evolution of the spacecraft inertial position. Additionally,
Fig. 8 demonstrates visually the replication of the Hubble
SPICE trajectory overlayed with the Basilisk integrated tra-
jectory. Finally, Fig. 9 demonstrates the difference and there-
fore close agreement of the RK4 integrated trajectory and the
Hubble SPICE trajectory.

Fig. 7. Inertial position of the Hubble spacecraft simulation.

10. CONCLUSION

The Basilisk astrodynamics framework provides a new open
source alternative for fully coupled spacecraft dynamics mis-
sion simulation. Among the suite of other available simu-
lation tools, Basilisk provides an enabling mix of usability,
extensibility and computational speed. Basilisk is able to
achieve the usability though generated Python user interface
for each Basilisk component, allowing user to leverage the
depth of the Python math and data analysis package ecosys-
tems. Basilisk’s modular architecture of Modules, Tasks,
Task Groups, and the Messaging system supports the extensi-
bility and allows users to conﬁgure simulation scenarios from
the very simple early feasibility analysis to complex mission
veriﬁcation and validation.

[6] CS Syst`emes d’Information, “Orekit: An accurate and
efﬁcient core layer for space ﬂight dynamics applica-
tions,” https://www.orekit.org, Accessed 15 Oct 2018.

[7] Jet Propulsion Lab DARTS Lab, “Darts shell (dshell),”
https://dartslab.jpl.nasa.gov, Accessed 1 Oct 2018.

[8] NASA Goddard Space Flight Center,

“42: A com-
prehensive general-purpose simulation of attitude and
trajectory dynamics and control of multiple space-
craft composed of multiple rigid or ﬂexible bod-
ies,” https://software.nasa.gov/software/GSC-16720-1,
Oct 2018, Accessed 2018-10-1.

[9] Marshall Space Flight Center, “Marshall solar activity
future estimation,” https://sail.msfc.nasa.gov, Accessed
1 Oct 2018.

[10] Advanced Solutions,

“Stk solis: Commercial plug-
in to the analytical graphics, inc (agi) systems toolkit
(stk),” http://www.go-asi.com/solutions/stk-solis/, Oct
2018, Accessed 1 Oct 2018.

[11] A. Jain C. Lim,

“Dshell++: A component based,
reusable space system simulation framework,” in IEEE
International Conference on Space Mission Challenges
for Information Technology (SMC-IT 2009), Pasadena,
CA, July 19 - 23 2009, IEEE.

[12] A. Jain and G. Rodriguez, “Recursive ﬂexible multibody
system dynamics using spatial operators,” Journal of
Guidance, Control, and Dynamics, vol. 15, no. 6, pp.
1453–1466, Nov 1992.

[13] Cody Allard, Manuel Diaz Ramos, Hanspeter Schaub,
Patrick Kenneally, and Scott Piggott, “Modular Soft-
ware Architecture for Fully Coupled Spacecraft Simu-
lations,” Journal of Aerospace Information Systems, pp.
1–14, oct 2018.

[14] Open Source

Initiative,

“Isc

license

(isc),”

https://opensource.org/faq, Accessed 15 Oct 2018.

[15] Vincent Driessen, “A successful git branching model,”
https://nvie.com/posts/a-successful-git-branching-
model/, January 2010, Accessed 27 Oct 2018.

Fig. 8. Overlay of the Hubble SPICE trajectory with the
Basilisk rk4 integrated trajectory.

Fig. 9. The difference in inertial position between the Hubble
SPICE trajectory with the Basilisk trajectory.

11. REFERENCES

[1] MathWorks,

“Matlab/simulink,”

https://www.mathworks.com/products/matlab.html,
Accessed 23 Oct 2018.

[2] Analytic Graphics Inc (AGI), “Systems tool kit (stk),”
https://www.agi.com/products/engineering-tools, Ac-
cessed 20 Oct 2018.

[3] a.i.

Solutions,

“Freeﬂyer,”

https://ai-

solutions.com/freeﬂyer/, Accessed 21 Oct 2018.

[4] NASA

Goddard
mission

Space
analysis

Flight
tool

Center,
(gmat),”

“General
https://software.nasa.gov/software/GSC-17177-1,
Accessed 27 Oct 2018.

[5] NASA Johnson Space Center, “Trick simulation envi-
ronment,” https://github.com/nasa/trick/wiki/FAQ, Ac-
cessed 20 Oct 2018.

