2024 年　    8 月
第 50 卷 第 8 期

北  京  航  空  航  天  大  学  学  报

Journal of Beijing University of Aeronautics and Astronautics

August　2024
Vol. 50　No. 8

http://bhxb.buaa.edu.cn　　jbuaa@buaa.edu.cn

DOI: 10.13700/j.bh.1001-5965.2022.0666

基于强化学习的航天器姿态预设性能容错控制

金磊*，杨绍龙

(北京航空航天大学 宇航学院，北京 100191)

摘　　　要：针对惯量不确定性和执行机构故障的航天器姿态控制问题，提出了一种基于强化

学习的预设性能容错控制方法。采用预设性能方法设计航天器的姿态控制器，以保证控制过程的暂

态响应。为在线补偿惯量不确定，在预设性能控制器的基础上引入强化学习算法，使用评判网络近

似代价函数，用于评估系统性能，同时使用动作网络产生前馈补偿控制，用于处理惯量不确定；设

计自适应补偿控制，补偿执行机构故障和外扰动对航天器姿态的影响。基于Lyapunov稳定性理论

证明整个闭环系统的稳定性。仿真结果表明：所提容错控制方法能够实现航天器执行机构故障情况

下的稳定控制。

关　键　词：强化学习；容错控制；预设性能；航天器；姿态控制
中图分类号：V448.22；TP302.8
文献标志码：A　　　　文章编号：1001-5965（2024）08-2404-09

如今人类日常生活与航天器的联系日益紧密，

信息来处理执行机构故障。文献[8-9]借助故障诊

以最基本的出行为例，依赖于导航卫星的定位和气

断技术，设计故障观测器估计故障的大小，通过对

象卫星的天气预报服务，因此，保证在轨航天器的
正常运行变得极其重要[1]。然而，空间环境的复杂
性导致在轨运行航天器发生故障的可能性提高[2-3]，
在轨航天器发生故障的案例也不在少数，如1996年

故障进行补偿实现航天器姿态的容错控制，提高容

错控制的控制性能。但是，常规故障诊断存在故障

估计不准确和时间延迟的问题，而自适应技术具有

适应环境变化的特点，因此，自适应容错控制得以

美国导航卫星GPS BII-7由于反作用轮故障而完全

快速发展。文献[10-11]将自适应技术与快速终端

失效，2019年美国遥感卫星WorldView-4由于控制
力矩陀螺故障而无法获得有效图像[4-5]。空间环境

滑模相结合，使得控制过程具有快速收敛性。文献

[12]设计自适应积分型终端滑模容错控制器，通过

的特殊性使得航天器发生故障时难以像地面系统

设计积分形式的滑模变量使得航天器姿态跟踪控

一样进行维修，因此，研究航天器的容错控制问题，

制过程更加平稳。预设性能方法通过人为规定控

对于提高航天器的安全性和可靠性具有重要意义。

制过程的约束，保证系统的暂态响应，但在容错控

容错控制就是在系统发生故障后，通过采取相

制方面的应用较少。文献[13]通过扩展状态观测

应的措施来保证系统稳定性，并且获得可以接受的
性能水平，从而提高系统的安全性和可靠性[6]。航

器估计故障大小，利用预设性能方法和反步控制设

计航天器姿态容错控制器，同时保证系统的稳态和

天器作为安全至上的系统，针对航天器的容错控制

暂态响应。上述容错控制器有一个共同的不足，即

研究已经有一定的成果。文献[7]利用动态逆和时

对系统模型的依赖性较强，严重影响系统的自主性。

滞控制理论设计容错控制器，通过隐式地引入故障

强化学习通过智能体与环境的不断交互学习

　收 稿 日 期：2022-07-28；录 用 日 期：2022-09-16；网 络 出 版 时 间：2022-10-14 14：06
　网 络 出 版 地 址：link.cnki.net/urlid/11.2625.V.20221014.1054.002
　基 金 项 目：中央高校基本科研业务费专项资金(YWF-22-L-801)
 * 通 信 作 者. E-mail：jinleibuaa@163.com

　引用格式：金磊，杨绍龙. 基于强化学习的航天器姿态预设性能容错控制[J]. 北京航空航天大学学报，2024，50（8）：2404-2412.

JIN L，YANG S L. Fault-tolerant control of spacecraft attitude with prescribed performance based on reinforcement learning[J]. Journal of

Beijing University of Aeronautics and Astronautics，2024，50（8）：2404-2412 （in Chinese）.

第 8 期

金磊，等：基于强化学习的航天器姿态预设性能容错控制

2405

最大化长期收益的策略[14]，具有从环境交互得到的
数据中学习的特点，对于模型精度的要求不高，甚

至在没有模型的情况下也能起到很好的效果。目

前，强化学习在无人驾驶、机器人控制等领域的应

用均取得不错的效果，在容错控制领域也有不少应
用[15-16]。文献[17]针对机械臂的轨迹跟踪控制，在
强化学习的训练过程中同时考虑关节正常和故障

的 情 况，设 计 得 到 对 关 节 故 障 不 敏 感 的 容 错 控 制
器。为提高容错控制的实时性，文献[18]结合在线

一个三维列阵

， 为叉乘矩阵，具体表

达式为

航天器执行任务过程中，由于姿态或轨道机动

发生燃料消耗，会引起航天器转动惯量的改变，导

致 航 天 器 实 际 转 动 惯 量 与 名 义 转 动 惯 量 不 相 等 。

考虑转动惯量不确定性的影响，使用角动量定理建

和离线策略提出自适应强化学习容错控制方法，通

立如下刚性航天器姿态动力学方程：

过在线学习的数据拟合系统模型，同时使用近似策

略优化算法针对拟合模型进行离线训练，得到的控
制器能够根据系统变化进行实时更新。文献[19]

将强化学习与最优控制相结合，利用最优控制理论

来保证强化学习算法的最优性，同时加快了强化学
习算法的收敛速度。文献[20]采用与文献[19]类

似的容错控制器，将其与模糊控制相结合，进一步

提高控制性能。强化学习虽然能够降低容错控制

式中：

为航天器的名义转动惯量，通常为

正定对称矩阵；

为未知转动惯量；

为作用在航天器上的控制力矩；

为干扰力矩。

对式（2）进行整理，航天器姿态动力学方程可

改写为

器 对 系 统 模 型 的 依 赖，但 通 常 存 在 离 线 训 练 的 过

式 中：

为 惯 量 不 确 定 性 产 生

程，导致控制器的实时性较差。

基于以上分析，本文将预设性能方法与强化学

的未知力矩。
1.2　执行机构及其故障模型

习算法相结合，设计基于强化学习的航天器姿态预

实际作用在航天器的控制力矩通过执行机构

设性能容错控制器。首先，忽略故障、系统不确定

产生，虽然执行机构的类型多种多样，但不论具体

性和外干扰，利用预设性能方法设计标称控制器，

形式如何，均可使用如下数学模型进行表示：

保证航天器正常工作情况下的稳定性；然后，设计

强化学习算法的结构和参数更新律，实现惯量不确

定性的实时在线补偿；最后，设计自适应参数更新

律补偿执行机构故障和外干扰，实现航天器姿态的

容错控制。本文方法不仅能够保证控制过程的暂

态响应，还能够保证强化学习算法的实时性，从而

减小控制器对系统模型的依赖，有利于提高容错控

制的控制性能和鲁棒性。

1　系统描述

1.1　航天器姿态控制系统模型

式 中 ：

为 执 行 机 构 的 安 装 矩 阵 ；

为各执行机构产生的控制力矩所构成的

列向量；n为执行机构的个数。

航天器在轨运行过程中面临复杂的空间环境，

执行机构故障、老化的概率大大增加，导致执行机

构 产 生 的 实 际 控 制 力 矩 和 期 望 控 制 力 矩 不 相 等 。

常见的执行机构故障有输出效率降低、产生额外的

控制力矩和卡死。

根据故障特性，执行机构故障可分为突发性故

障、渐变性故障和间歇性故障。相比于渐变性故

采用四元数描述航天器的姿态，以避免大角度

障，突发性故障对于系统带来的冲击更大，处理起

机动可能引发的奇异问题。航天器的姿态运动学

来更加困难；而间歇性故障可以视为不同时刻的突

可表示为

发性或渐变性故障叠加的结果，因此，本文选取具

有代表性的突发性故障进行研究。

考虑执行机构故障的影响，执行机构实际产生

的控制力矩和期望控制力矩之间的关系可表示为

式中：

为航天器本体坐标系相对惯性

坐 标 系 的 四 元 数， 和

分 别 为 四 元

式中：

为各执行机构的指令控制

数 的 标 量 和 矢 量 部 分 ； 为 3阶 单 位 矩 阵 ；

力矩所构成的列向量；

为加性偏

为 航 天 器 本 体 坐 标 系 相 对 惯 性 坐 标 系

差 故 障；

为 执 行 机 构 失 效 系 数

的角速度在本体坐标系中的分量列阵。对于任意

所 构 成 的 对 角 矩 阵， 为 第 个 执 行 机 构 的 失 效 系

8><>:˙qb0=(cid:0)12qTbωb˙qb=12(˜qb+qb0I3)ωb（1）Qb=[qb0;qTb]Tqb0qb=[q1;q2;q3]TI3ωb=[ωx;ωy;ωz]Tx=[x1;x2;x3]T˜x˜x=240(cid:0)x3x2x30(cid:0)x1(cid:0)x2x1035(Ib0+∆Ib)˙ωb+˜ωb(Ib0+∆Ib)ωb=Tc+Td（2）Ib02R3(cid:2)3∆Ib2R3(cid:2)3Tc2R3Td2R3Ib0˙ωb+˜ωbIb0ωb=Tc+Td+T∆（3）T∆=(cid:0)∆Ib˙ωb(cid:0)˜ωb∆IbωbTc=Cu（4）C2R3(cid:2)nu=[u1;u2;(cid:1)(cid:1)(cid:1);un]Tu=(In(cid:0)E)uc+¯uc（5）uc=[uc1;uc2;(cid:1)(cid:1)(cid:1);ucn]Tuc=[uc1;uc2;(cid:1)(cid:1)(cid:1);ucn]TE=diag(e1;e2;(cid:1)(cid:1)(cid:1);en)eii

2406

北  京  航  空  航  天  大  学  学  报

2024 年

数，且有

，当

时，表示执行机构无失效

为带约束的控制问题，将不可避免地导致控制器设

故 障 ， 当

时 ， 表 示 执 行 机 构 完 全 失 效 ， 当

计变得复杂。为简化控制器的设计，引入如下误差

时，表示执行机构部分失效。

转换：

将式（4）、式（5）代入式（3），则考虑惯量不确定和

执行机构故障的航天器姿态动力学方程可表示为

式 中： 为 转 换 误 差； 为 光 滑 连 续 的 误 差 转 换

函 数，且 满 足：① 严 格 单 调 递 增；②

；

式 中：

为 执 行 机 构 输 出 的 期 望 力 矩；

③

,

。

为执行机构故障产生的额外控制力矩。

本文选取如下误差转换函数：

2　预设性能约束

某些航天任务对于控制过程的时间响应具有

一定的要求，如收敛速度、超调量、稳态误差等，因

此，在控制器设计之前，先采用预设性能方法对系

统进行处理，通过人为设定受控系统的性能包络来

保证被控系统的暂态和稳态响应。

定义滑模变量 为

式中：

。

由 于 误 差 转 换 函 数 严 格 单 调 递 增，存 在 逆 函

数，则转换误差 可表示为

式中：

。

从 式（11）可 以 看 出，当 趋于0时，转 换 误 差

也趋于0；并且当被控量处于不等式约束之内时，

转化误差满足

。因此，后续进行控制

滑模变量包含姿态四元数和姿态角速度信息，

器设计时，只需保证转换误差 有界即可实现对滑

对滑模变量进行约束能够在一定程度上同时约束

模变量的不等式约束。

姿态四元数和姿态角速度。假设滑模变量的各个

分量

满足如下不等式约束：

3　控制器设计

式 中： 和 为 正 常 数，表 示 超 调 抑 制 参 数；

图1为基于强化学习的航天器姿态预设性能

容错控制系统结构示意图。可以看出，容错控制器

为光滑连续、单调递减的预设性

由标称控制器、强化学习补偿算法和自适应补偿算

能函数，且有

，

。

法3部分构成。标称控制器通过预设性能方法设

值得注意的是，为保证不等式恒成立，参数的

计得到，用于保证无惯量不确定和执行机构故障情

选取需要满足不等式约束：

。

况下姿态控制的暂态和稳态响应。评判网络用于

由式（8）可知，滑模变量的变化受到预设性能

评估闭环系统的控制性能，动作网络则根据评判网

函数的限制，其时间响应可以通过预设性能函数和

络进行更新，用于生成补偿惯量不确定性的前馈控

超调抑制参数进行调整，从而获得期望的暂态和稳

制力矩。设计自适应律补偿执行机构故障和外扰

态性能。其中，参数 主要保证稳态误差， 保证

收敛速度， 和 调整超调量。

动对航天器姿态的影响。
3.1　标称控制器设计

在引入控制约束后，原来的无约束控制问题变

在设计标称控制器时，忽略惯量不确定性、干

Fig. 1    Structure of fault-tolerant control system of spacecraft attitude with prescribed performance based on reinforcement learning

图 1    基于强化学习的航天器姿态预设性能容错控制系统结构示意图

ei2[0;1]ei=0ei=10<ei<1Ib0˙ωb+˜ωbIb0ωb=Tcf+Tf+Td+T∆（6）Tcf=CucTf=(cid:0)CEuc+C¯ucss=ωb+k0qb（7）k0>0si(i=1;2;3)(cid:0)(cid:14)i(cid:26)i(t)<si(t)<¯(cid:14)i(cid:26)i(t)（8）(cid:14)i¯(cid:14)i(cid:26)i(t)=((cid:26)i0(cid:0)(cid:26)i1)e(cid:0)(cid:21)it+(cid:26)i1(cid:26)i0>(cid:26)i1>0(cid:21)i>0(cid:0)(cid:14)i(cid:26)i0<si0<¯(cid:14)i(cid:26)i0(cid:26)i1(cid:21)i(cid:14)i¯(cid:14)isi(t)=(cid:26)i(t)S("i)（9）"iS((cid:1))(cid:0)(cid:14)i<S("i)<¯(cid:14)ilim"i!(cid:0)1S("i)=(cid:0)(cid:14)ilim"i!+1S("i)=¯(cid:14)iS(")=¯(cid:14)(cid:14)(e"(cid:0)e(cid:0)")(cid:14)e"+¯(cid:14)e(cid:0)"（10）"i"i=S(cid:0)1(li)=12ln((cid:14)i+li¯(cid:14)i(cid:0)li)(cid:0)12ln((cid:14)i¯(cid:14)i)（11）li=si(t)/(cid:26)i(t)li"i"i2((cid:0)1;+1)"i标称控制器执行机构故障自适应律−−航天器qb, ωb误差转换(预设性能)动作网络评判网络erˆdˆTΔ+TcTw

第 8 期

金磊，等：基于强化学习的航天器姿态预设性能容错控制

2407

扰力矩和执行机构的影响，因此，航天器的姿态动

最优的评判网络参数和网络近似误差通常是

力学方程可简化为

未知的，因此，代价函数的估计值 可表示为

通过预设性能方法来保证控制过程的暂态响

式中： 为 的估计值。

应。对式（11）求导，可得转换误差的动力学方程为

为评估代价函数的近似误差，定义如下评判网

式中： 为正数，具体表达式为

为便于描述，将转换误差改写成矩阵形式。令

，则有

式中：

；

。

对式（7）求导，并代入式（1）、式（12），可得

由于 为正定矩阵，借助反馈控制的思想，令转

换误差满足等式

，即可得到标称控制器为

式中：

为控制参数。

式（16）中的

项用于保证收敛速度，其余

各项均为前馈控制项，用于保证控制精度。
3.2　评判网络和动作网络设计

航天器姿态控制的目标是保证姿态四元数矢

部和姿态角速度趋于0，由此定义如下代价函数：

络估计误差：

式中：

导数，

为

的

，

。

定义评判网络的优化目标为

评判网络的参数根据式（23）进行更新：

式中：

为评判网络的学习率；

为设计参数。

网络参数更新分为2部分：

通过极小化

目标函数 获得，修正项

用于增强参数的

鲁棒性。

动作网络用于补偿航天器惯量不确定性带来

的 影 响 。 假 设 由 惯 量 不 确 定 性 产 生 的 干 扰 力 矩

可用神经网络近似为

式中：

为动作网络的输入；

为动

作网络激活函数； 为最优的动作网络参数； 为

动作网络近似误差。

由惯量不确定性产生的干扰力矩为

，即 为 的多项式函数。本文使用多项

式作为动作网络的激活函数，相比于单层前馈神经

网络，使用多项式的动作网络对惯量不确定性的拟

合能力更强。激活函数具体选为

式中：

为折扣因子；

为即

。

时 代 价 函 数 ，

为 航 天 器 的 状 态 变 量 ，

同理，最优的动作网络参数和网络近似误差通

和 为待定的正定矩阵。

常是未知的，因此，惯量不确定性的估计值 可表

对 式（17）求 导，得 到 代 价 函 数 满 足 的 等 式 约

示为

束为

使用评判网络近似代价函数，借助神经网络强

动作网络的目标为：①动作网络的近似误差尽

大的函数拟合能力，代价函数可以表示为

可能小；②代价函数的估计值与代价函数的期望值

式中： 为 的估计值。

式 中 ：

为 评 判 网 络 的 输 入 ；

为评判网络激活函数，采用单层前馈神经

之间的误差尽可能小；③转换误差 尽可能小。

定义如下动作网络估计误差：

网络来实现， 为双曲正切函数， 为加权矩阵；

式中：

，且有

； 为代

为最优的评判网络参数； 为评判网络近似误差。

价函数的期望值，不失一般性，将其设置为0。

Ib0˙ωb+˜ωbIb0ωb=Tc（12）˙"i=ri(˙si(cid:0)˙(cid:26)i(cid:26)isi)（13）riri=12(cid:26)i(1(cid:14)i+li+1¯(cid:14)i(cid:0)li)e=["1"2"3]T˙e=R(˙s(cid:0)Ps)（14）R=diag(r1;r2;r3)P=diag(˙(cid:26)1=(cid:26)1;˙(cid:26)2=(cid:26)2;˙(cid:26)3=(cid:26)3)˙s=˙ωb+k0˙qb=I(cid:0)1b0(Tc(cid:0)˜ωbIb0Ib)+12k0(˜qb+qb0I3)ωb（15）R˙e=(cid:0)kReTc0=(cid:0)kIb0e+Ib0Ps+˜ωbIb0ωb(cid:0)12k0Ib0(˜qb+qb0I3)ωb（16）k>0(cid:0)kIb0eJ(t)=w1te(cid:0)(cid:13)c((cid:28)(cid:0)t)r((cid:28))d(cid:28)（17）(cid:13)c⩾0r(t)=xTbQrxb+TTcfRrTcfxb=[qTb;ωTb]TQrRr˙J(t)=(cid:13)cJ(t)(cid:0)r(t)（18）J(t)=WTcφc(xc)+"c（19）xc=[qTb;ωTb]Tφc(xc)=fc(VTcxc)fc((cid:1))VcWc"cˆJ(t)ˆJ(t)=ˆWTcφc(xc)（20）ˆWcWcec(t)=r(t)(cid:0)(cid:13)cˆJ(t)+˙ˆJ(t)=r(t)+ˆWTc(cid:3)c(xc;˙xc)（21）(cid:3)c(xc;˙xc)=˙φc(xc)(cid:0)(cid:13)cφc(xc)˙φc(xc)φc(xc)˙φc(xc)=(@φc(xc)/@xc)˙xcEc=12e2c（22）˙ˆWc=(cid:0)(cid:11)cec(cid:3)c(cid:0)(cid:11)ckcˆWc（23）(cid:11)c>0kc>0(cid:11)cec(cid:3)cEc(cid:0)(cid:11)ckcˆWcT∆T∆=WTaφa(xa)+"a（24）xa=[ωTb;˙ωTb]Tφa(xa)Wa"aT∆=(cid:0)∆Ib˙ωb(cid:0)˜ωb∆IbωbT∆xaφa(xa)=[x21;x22;x23;x1x2;x1x3;x2x3;5x4;3x5;4x6]ˆT∆ˆT∆=ˆWTaφa(xa)（25）ˆWaWaeea=ˆWTaφa(xa)+e+Kf(ˆJ(cid:0)Jd)（26）Kf=[kf1;kf2;kf3]Tkfi>0;i=1;2;3Jd
2408

北  京  航  空  航  天  大  学  学  报

2024 年

定义动作网络的优化目标为

动作网络的参数通过式（28）进行更新：

由式（18）和式（19）可得

式中：

。

式中：

为动作网络的学习率；

为设计参数。

由式（21）、式（23）、式（35）和杨氏不等式可得

从式（23）和式（28）可以看出，评判网络和动作

网络的参数都是实时更新的，因此，本文提出的强

化学习算法能够在线对惯量不确定性进行补偿，更

有利于实际应用。

3.3　自适应补偿控制器设计

考虑到执行机构故障的突发性，在短时间内使

用强化学习进行在线识别具有一定的难度，因此，

式中：

。

设计自适应律补偿执行机构故障和干扰力矩。

由式（26）、式（28）和杨氏不等式可得

将干扰力矩和执行机构故障产生的额外控制

力矩之和定义为外扰动 ：

假设外扰动 的估计值为 ，设计如下自适应律：

式中：

、

为设计参数。

综上所述，基于强化学习的预设性能容错控制

器为

式中： 为期望控制力矩。

执行机构的指令控制力矩 通过伪逆操纵律

获得：

式中：

。

由式（30）和杨氏不等式可得

式中：C+为矩阵C的伪逆。

4　稳定性分析

定理1    针对式（1）、式（6）描述的考虑惯量不

确定性和执行机构故障的航天器模型，如果评判网

络和动作网络分别选为式（19）和式（24），网络参数

更新律由式（23）和式（28）确定，则由式（16）、式（25）

和式（30）构成的基于强化学习的预设性能容错控

制器式（31）可以保证航天器姿态一致有界，同时能

保证姿态控制的暂态和稳态性能。

证明    定义如下Lyapunov函数：

由 于

，结 合 式（14）、

式（16）、式（31）和杨氏不等式可得

式中：

。

将式（36）～式（39）代入式（34）可得

式中：

；

；

。

对式（33）求时间导数，有

式中：

Ea=12eTaea（27）˙ˆWa=(cid:0)(cid:11)aφaeTa(cid:0)(cid:11)akaˆWa（28）(cid:11)a>0ka>0dd=Td+Tf（29）dˆd˙ˆd=(cid:11)d(I(cid:0)1b0Re(cid:0)kdˆd)（30）(cid:11)d>0kd>0Tw=Tc0(cid:0)ˆT∆(cid:0)ˆd（31）Twucuc=C+Tw=CT(CCT)(cid:0)1Tw（32）V=12eTe+12(cid:11)ctr(˜WTc˜Wc)+12(cid:11)atr(˜WTa˜Wa)+12(cid:11)d˜dT˜d（33）˜Wc=ˆWc(cid:0)Wc˜Wa=ˆWa(cid:0)Wa˜d=ˆd(cid:0)d˙V=eT˙e+1(cid:11)ctr(˜WTc˙˜Wc)+1(cid:11)atr(˜WTa˙˜Wa)+1(cid:11)d˜dT˙˜d（34）r(t)=(cid:13)cJ(t)(cid:0)˙J(t)=(cid:0)WTc(cid:3)c(cid:0)(cid:3)("c)（35）(cid:3)("c)=˙"c(cid:0)(cid:13)c"c1(cid:11)ctr(˜WTc˙˜Wc)=(cid:0)tr(˜WTc(cid:3)c((cid:3)Tc˜Wc+(cid:3)("c)))(cid:0)kctr(˜WTcˆWc)⩽(cid:0)(cid:21)min((cid:3)c(cid:3)Tc)tr(˜WTc˜Wc)+(cid:12)1(cid:21)max((cid:3)c(cid:3)Tc)tr(˜WTc˜Wc)+14(cid:12)1(cid:3)2("c)(cid:0)kc2tr(˜WTc˜Wc)+kc2tr(WTcWc)（36）(cid:12)1>01(cid:11)atr(˜WTa˙˜Wa)=(cid:0)tr(˜WTaφa(φTaˆWa+eT+KTfφTcˆWc))(cid:0)katr(˜WTaˆWa)⩽(cid:12)2eTe+(cid:21)max(φaφTa)4(cid:12)2tr(˜WTa˜Wa)+(cid:21)max(φaφTa)tr(˜WTa˜Wa)+(cid:12)3tr(WTaWa)+(cid:21)max(φaφTaφaφTa)4(cid:12)3tr(˜WTa˜Wa)+(cid:12)4tr(˜WTc˜Wc)+(cid:21)max(φaKTfφTcφcKfφTa)4(cid:12)4tr(˜WTa˜Wa)+(cid:12)5tr(WTcWc)+(cid:21)max(φaKTfφTcφcKfφTa)4(cid:12)5tr(˜WTa˜Wa)(cid:0)ka2tr(˜WTa˜Wa)+ka2tr(WTaWa)（37）(cid:12)2;(cid:12)3;(cid:12)4;(cid:12)5>01(cid:11)d˜dT˙˜d=˜dTI(cid:0)1b0Re(cid:0)kd˜dTˆd⩽˜dTI(cid:0)1b0Re(cid:0)kd2˜dT˜d+kd2dTd（38）˜T∆=ˆT∆(cid:0)T∆=˜WTaφa(xa)(cid:0)"aeT˙e=(cid:0)keTRe(cid:0)eTRI(cid:0)1b0˜d(cid:0)eTRI(cid:0)1b0˜WTaφa+eTRI(cid:0)1b0"a⩽(cid:0)k(cid:21)min(R)eTe(cid:0)eTRI(cid:0)1b0˜d+(cid:12)6(cid:21)max(RI(cid:0)1b0I(cid:0)Tb0RT)eTe+(cid:21)max(φaφTa)4(cid:12)6tr(˜WTa˜Wa)+(cid:12)7(cid:21)max(RI(cid:0)1b0I(cid:0)Tb0RT)eTe+14(cid:12)7"Ta"a（39）(cid:12)6;(cid:12)7>0˙V⩽(cid:0)(cid:21)eeTe(cid:0)(cid:21)ctr(˜WTc˜Wc)(cid:0)(cid:21)atr(˜WTa˜Wa)(cid:0)(cid:21)d˜dT˜d+(cid:22)（40）(cid:21)e=k(cid:21)min(R)(cid:0)(cid:12)2(cid:0)((cid:12)6+(cid:12)7)(cid:21)max(RI(cid:0)1b0I(cid:0)Tb0RT)

第 8 期

金磊，等：基于强化学习的航天器姿态预设性能容错控制

2409

评判网络激活函数的输出为10维，前馈神经网络

的参数在
之间随机选取并保持不变，评判网
络 的 初 始 参 数 为 0； 动 作 网 络 的 初 始 参 数 为

。 强 化 学 习 算 法 参 数 为 ：

,

,

,

,

,

,

,

。自适应参数为：

,

。

考虑到本文的重点在于提出一种新的容错控

制方法，仿真主要验证控制方法的有效性，因此，并
未引入敏感器，量测误差为0；执行机构选用可输出

连续力矩的飞轮或陀螺，其控制周期与仿真步长保
持一致。仿真结果如图2～图9所示。

从图2和图3可以看出，航天器姿态四元数和

姿态角速度在10 s左右基本收敛；当20 s发生执行

定义

，则有

机构故障后，姿态四元数和姿态角速度发生不同程

对式（41）积分可得

式中： 为Lyapunov函数的初值。

因 此 ， Lyapunov函 数

始 终 小 于 ， 即

Lyapunov函数有界。为获得更好的控制效果，可通

过增大参数

的值来实现。根据Lyapunov

稳 定 性 判 定 定 理 可 知，转 换 误 差 和 估 计 误 差 、

都是一致有界的。由于转换误差 有界，即对

， 有界，滑模变量 一致有界，并且控制

过程的暂态和稳态响应都不超过规定的预设性能

约 束 。 进 而 由 于 滑 模 变 量 有 界，姿 态 四 元 数 矢 部

和姿态角速度 均一致有界，其上界由预设性能

函数决定。

5　仿真验证

证毕

本节通过数值仿真验证控制器的有效性。航天

器的实际转动惯量 和名义转动惯量 分别为：

 kg·m2，

m2；执行机构的安装矩阵为：

 kg·

；

航 天 器 初 始 姿 态 四 元 数 和 姿 态 角 速 度 分 别 为

和

。

航天器的干扰力矩为：

。执行机构故障为：20 s时，x轴执行机构同时发

生失效和偏差故障，其中，失效系数为

，偏差

故 障 为

。 控 制 参 数 为 ：

,

,

,

,

,

,

。

度的波动，其中，姿态四元数变化量不超过

，

姿态角速度变化量不超过

，但是均能在

5 s之内收敛到0附近，表明本文提出的容错控制方

图 2    姿态四元数

Fig. 2    Attitude quaternion

图 3    姿态角速度

Fig. 3    Attitude angular velocity

图 4    滑模变量

Fig. 4    Sliding mode variable

(cid:21)c=kc2+(cid:21)min((cid:3)c(cid:3)Tc)(cid:0)(cid:12)1(cid:21)max((cid:3)c(cid:3)Tc)(cid:0)(cid:12)4(cid:21)a=ka2(cid:0)(1+14(cid:12)2+14(cid:12)6)(cid:21)max(φaφTa)(cid:0)(cid:21)max(φaφTaφaφTa)4(cid:12)3(cid:0)(14(cid:12)4+14(cid:12)5)(cid:21)max(φaKTfφTcφcKfφTa)(cid:21)d=kd2(cid:22)=14(cid:12)1(cid:3)2("c)+((cid:12)5+kc2)tr(WTcWc)+((cid:12)3+ka2)tr(WTaWa)+kd2dTd+14(cid:12)7"Ta"a(cid:21)=minf2(cid:21)e;2(cid:11)c(cid:21)c;2(cid:11)a(cid:21)a;2(cid:11)d(cid:21)dg˙V⩽(cid:0)(cid:21)V+(cid:22)（41）V(t)⩽(cid:22)(cid:21)+(V0(cid:0)(cid:22)(cid:21))e(cid:0)(cid:21)t（42）V0V(t)(cid:22)/(cid:21)k、(cid:11)c、(cid:11)a、(cid:11)de˜Wc˜Wa、˜de8i=1;2;3"isqbωbIbIb0Ib=2445:41:511:523:31:211:232:835Ib0=2440000200002835C=241001=p30101=p30011=p335[0:9531;0:1;0:15;(cid:0)0:12]T[0:4;(cid:0)0:2;0:3]T(°)/sTd=243cos(0:001t)cos(0:001t)+1(cid:0)4sin(0:001t)35(cid:2)10(cid:0)4N(cid:1)me1=0:5u1=(cid:0)0:2N·mk0=2k=0:1(cid:21)i=0:2(cid:14)i=¯(cid:14)i=1(cid:26)i0=0:4(cid:26)i1=10(cid:0)3i=1;2;3[(cid:0)1;1][03(cid:2)6(cid:0)I3]T(cid:13)c=0(cid:11)c=2(cid:11)a=5kc=0:001ka=0:0001Qr=100I6Rr=I3Kf=[1;1;1]T(cid:11)d=10kd=0:0014(cid:2)10(cid:0)52(cid:2)10(cid:0)2(°)/s010203040时间/s−0.100.1姿态四元数q1q2q3203040−4×10−5−2×10−50010203040时间/s−6−4−2024姿态角速度/((°)·s−1)ωxωyωz203040−2×10−2−1×10−20010203040时间/s−0.4−0.200.20.4滑模变量203040−0.0100.01s1s2s3δρδρ

2410

北  京  航  空  航  天  大  学  学  报

2024 年

图 5    期望控制力矩

Fig. 5    Expected control moment

图 9    动作网络权重

Fig. 9    Weight of actor network

制力矩不为0，用于抵消执行机构故障的影响。

图6和图7分别为惯量不确定性和外扰动的估

计误差，可以看出，发生故障后，估计误差都能快速

收敛到0附近，表明设计的强化学习和自适应算法

能 够 较 好 地 处 理 惯 量 不 确 定 性 和 执 行 机 构 故 障 。

评判网络和动作网络的参数变化曲线如图8和图9

所示，参数在姿态稳定前基本收敛，表明强化学习

算法的收敛性较好。

图 6    惯量不确定性估计误差

下面通过对比仿真验证本文提出的容错控制

Fig. 6    Estimation error of inertia uncertainty

方 法 的 优 势 。 选 取 如 下 自 适 应 滑 模 容 错 控 制 器：

中，k1为 控 制 参 数，

， 其

，用 于 估 计 外

干扰和模型不确定性。为便于对比分析，尽可能保

证控制器的参数一致，其中，

,

,

,

。仿真结果如图10～图13所示。

从图10可以看出，航天器姿态四元数并不能

很好地收敛到0附近，控制精度仅为

，表明

自适应滑模容错控制方法在执行机构故障和惯量

不 确 定 情 况 下 的 控 制 性 能 较 差 。 从图11可 以 看

图 7    外扰动估计误差

Fig. 7    Estimation error of external disturbance

出，姿态角速度能够收敛到0附近，但发生执行机

构 故 障 后 的 波 动 更 大，达 到

。 并 且 从图12

的滑模变量变化曲线可以看出，10 s之后滑模变量

并不能始终在预设性能函数范围之内，尤其在发生

执行机构故障后，滑模变量甚至不能收敛到0，控制

过程的暂态响应更差。

通过上述对比可以看出，本文提出的基于强化

图 8    评判网络权重

Fig. 8    Weight of critic network

法能够较好地处理执行机构故障。从图4可以看

出，整个控制过程中，滑模变量始终在预设性能函

数的约束范围内，表明设计好的容错控制器能使航

天器姿态获得预先设定好的暂态和稳态性能。图5

给出了期望控制力矩的曲线，其中，20 s后期望控

图 10    姿态四元数仿真结果

Fig. 10    Results of attitude quaternion

Tw=(cid:0)k1Ib0s(cid:0)0:5k0Ib0(˜qb+qb0I3)ωb+˜ωbIb0ωb(cid:0)ˆd˙ˆd=(cid:11)d(I(cid:0)1b0s(cid:0)kdˆd)k0=2k1=0:4(cid:11)d=10kd=0:00110(cid:2)10(cid:0)30:2(°)/s010203040时间/s−6−4−2024期望控制力矩/(N·m)Tw1Tw2Tw320304000.20.4010203040时间/s−0.3−0.2−0.100.10.2惯量不确定性估计误差/(N·m)203040−4×10−3−2×10−302×10−3TΔ3~TΔ2~TΔ1~010203040时间/s−2−1012外扰动估计误差/(N·m)20304000.10.2d1~d2~d3~010203040时间/s24681012评判网络权重010203040时间/s1.52.02.5动作网络权重010203040时间/s−0.100.1姿态四元数q1q2q3203040−10×10−3−5×10−305×10−3

第 8 期

金磊，等：基于强化学习的航天器姿态预设性能容错控制

2411

图 11    姿态角速度仿真结果

Fig. 11    Results of attitude angular velocity

在未来研究中，将进一步考虑执行机构输出受

限的影响，使得该容错控制方法能够更好地应用到

实际航天器中。

参考文献（References）

[  1  ]

 王亚坤, 杨凯飞, 张婕, 等. 卫星在轨故障案例与人工智能故障诊

断[J]. 中国空间科学技术, 2022, 42(1): 16-29.

WANG Y K, YANG K F, ZHANG J, et al. Case study of in-orbit

satellite failures and artificial intelligence based failure detection[J].

Chinese Space Science and Technology, 2022, 42(1): 16-29(in Chi-

nese).

[  2  ]

 姜斌, 张柯, 杨浩, 等. 卫星姿态控制系统容错控制综述[J]. 航空

学报, 2021, 42(11): 524662.

JIANG  B,  ZHANG  K,  YANG  H,  et  al.  Fault-tolerant  control  of

satellite  attitude  control  systems:  Review[J].  Acta  Aeronautica  et

Astronautica Sinica, 2021, 42(11): 524662(in Chinese).

[  3  ]

 沈毅, 李利亮, 王振华. 航天器故障诊断与容错控制技术研究综

述[J]. 宇航学报, 2020, 41(6): 647-656.

SHEN  Y,  LI  L  L,  WANG  Z  H.  A  review  of  fault  diagnosis  and

fault-tolerant control techniques for spacecraft[J]. Journal of Astro-

图 12    滑模变量仿真结果

nautics, 2020, 41(6): 647-656(in Chinese).

Fig. 12    Results of sliding mode variable

[  4  ]

 陈雪芹, 孙瑞, 宋道喆, 等. 航天器姿态控制系统单机故障分析

[C]//第三届中国指挥控制大会. 北京: 国防工业出版社, 2015:

275-280.

CHEN X Q, SUN R, SONG D Z, et al. Failure analysis of compo-

nents  in  spacecraft  attitude  control  system[C]//Proceedings  of  the

3rd China Conference on Command and Control. Beijing: National

Defense Industry Press, 2015: 275-280(in Chinese).

[  5  ]

 林来兴. 最近十年航天器制导、导航与控制(GNC)系统故障分

析研究[J]. 控制工程, 2004(1): 1-8.

LIN L X. Fault analysis of spacecraft guidance, navigation and con-

trol  (GNC)  systems  in  the  last  decade[J].  Control  Engineering  of

图 13    期望控制力矩仿真结果

China, 2004(1): 1-8(in Chinese).

Fig. 13    Results of expected control moment

[  6  ]

 EDWARDS  C,  LOMBAERTS  T,  SMAILI  H.  Fault  tolerant  flight

学习的预设性能容错控制方法能够更好地补偿惯

量不确定和执行机构故障，从而提高航天器姿态控

control: A benchmark challenge[M]. Berlin: Springer, 2010.

[  7  ]

 JIN  J,  KO  S,  RYOO  C  K.  Fault  tolerant  control  for  satellites  with

four reaction wheels[J]. Control Engineering Practice, 2008, 16(10):

制的精度。此外，本文提出的控制方法借助了预设

1250-1258.

性能方法，在实现容错控制的基础上能够保证控制

过程的暂态响应，这是常规容错控制方法所不具有

的优势。

6　结　论

1） 针对存在惯量不确定和执行机构故障的航

天器，结合强化学习和预设性能方法提出一种新型

[  8  ]

 ZHOU  J,  LI  X,  LIU  R,  et  al.  Active  fault-tolerant  satellite  attitude

control based on fault effect classification[J]. Proceedings of the In-

stitution of Mechanical Engineers, Part G: Journal of Aerospace En-

gineering, 2017, 231: 1917-1934.

[  9  ]

 SHEN  Q,  YUE  C  F,  GOHC  H,  et  al.  Active  fault-tolerant  control

system design for spacecraft attitude maneuvers with actuator satur-

ation  and  faults[J].  IEEE  Transactions  on  Industrial  Electronics,

2019, 66(5): 3763-3772.

[10]

 闫鑫. 基于滑模的航天器执行机构故障诊断与容错控制研究[D].

容错控制方法，实现了航天器姿态的稳定控制。

哈尔滨: 哈尔滨工程大学, 2012.

2） 该容错控制方法能较为准确地补偿惯量不

YAN  X.  Research  on  sliding  mode  based  spacecraft  actuator  fault

确定和故障的影响，并且对强化学习中的神经网络

结构进行改进后，收敛性较好。

diagnosis and fault-tolerant control[D]. Harbin: Harbin Engineering

University, 2012(in Chinese).

[11]

 苏伟伟. 深空探测器高精度姿态容错控制研究[D]. 南京: 南京航

3） 相比于自适应滑模容错控制器，该容错控制

空航天大学, 2018.

方法的控制精度更高，并且有更好的暂态响应。

SU W W. Research on high precision fault-tolerant attitude control

010203040时间/s−4−2024姿态角速度/((°)·s−1)ωxωyωz203040−0.2−0.10010203040时间/s−0.4−0.200.20.4滑模变量203040−0.02−0.0100.01s1s2s3δρδρ010203040时间/s−4−2024期望控制力矩/(N·m)Tw1Tw2Tw320304000.20.4

2412

北  京  航  空  航  天  大  学  学  报

2024 年

for deep space probe[D]. Nanjing: Nanjing University of Aeronau-

of  deep  reinforcement  learning  in  intelligent  manufacturing[J].

tics and Astronautics, 2018(in Chinese).

Computer Engineering and Applications, 2021, 57(2): 49-59(in Chi-

[12]

 WANG  Z,  LI  Q,  LI  S  R.  Adaptive  integral-type  terminal  sliding

nese).

mode fault tolerant control for spacecraft attitude tracking[J]. IEEE

[17]

 李铭浩, 张华, 刘满禄, 等. 基于深度强化学习的机械臂容错控制

Access, 2019, 7: 35195-35207.

方法[J]. 传感器与微系统, 2020, 39(1): 53-55.

[13]

 HUANG X W, DUAN G R. Fault-tolerant attitude tracking control

LI M H, ZHANG H, LIU M L, et al. Fault tolerant control method

of combined spacecraft with reaction wheels under prescribed per-

of  manipulator  based  on  deep  reinforcement  learning[J].  Transdu-

formance[J]. ISA Transactions, 2020, 98: 161-172.

cer and Microsystem Technologies, 2020, 39(1): 53-55(in Chinese).

[14]

 RICHARD S S, ANDREW G B. Reinforcement learning: An intro-

[18]

 AHMED I, QUIÑONES-GRUEIRO M, BISWAS G. Fault-tolerant

duction[M]. 2nd ed. Cambridge: MIT Press, 2017: 1-18.

control of degrading systems with on-policy reinforcement learning

[15]

 李茹杨, 彭慧民, 李仁刚, 等. 强化学习算法与应用综述[J]. 计算

[J]. IFAC-Papers OnLine, 2020, 53(2): 13733-13738.

机系统应用, 2020, 29(12): 13-25.

[19]

 ZHAO W B, LIU H, LEWIS F. Fault-tolerant control for the forma-

LI R Y, PENG H M, LI R G, et al. Overview on algorithms and app-

tion  of  multiple  unknown  nonlinear  quadrotors  via  reinforcement

lications  for  reinforcement  learning[J].  Computer  Systems  &  App-

learning[J]. IFAC-Papers OnLine, 2020, 53(2): 2465-2470.

lications, 2020, 29(12): 13-25(in Chinese).

[20]

 ZHANG  H  G,  ZHANG  K,  CAI  Y  L,  et  al.  Adaptive  fuzzy  fault-

[16]

 孔松涛, 刘池池, 史勇, 等. 深度强化学习在智能制造中的应用展

tolerant tracking control for partially unknown systems with actuator

望综述[J]. 计算机工程与应用, 2021, 57(2): 49-59.

faults via integral reinforcement learning method[J]. IEEE Transac-

KONG S T, LIU C C, SHI Y, et al. Review of application prospect

tions on Fuzzy Systems, 2019, 27(10): 1986-1998.

Fault-tolerant control of spacecraft attitude with prescribed performance
based on reinforcement learning

JIN Lei*，YANG Shaolong

(School of Astronautics，Beihang University，Beijing 100191，China)

Abstract： A  fault-tolerant  control  method  with  prescribed  performance  based  on  reinforcement  learning  was
proposed for spacecraft attitude control with inertia uncertainties and actuator faults. In order to ensure the transient

response  of  the  control  process,  the  attitude  controller  of  the  spacecraft  was  designed  by  using  the  prescribed

performance  method.  A  reinforcement  learning  algorithm  was  introduced  based  on  the  prescribed  performance

controller  to  compensate  for  the  inertia  uncertainty  online.The  critic  network  was  used  to  approximate  the  cost

function  to  evaluate  the  performance  of  the  system,  and  the  actor  network  was  used  to  generate  feedforward

compensation control and deal with the inertia uncertainty. Then, an adaptive compensation control law was designed

to compensate for the effect of actuator faults and external disturbance on spacecraft attitude. According to Lyapunov

stability  theory,  the  stability  of  the  whole  closed-loop  system  was  proved.  The  simulation  results  show  that  the

proposed fault-tolerant control method can realize the stability control of spacecraft with actuator faults.

Keywords： reinforcement learning；fault-tolerant control；prescribed performance；spacecraft；attitude control

　Received：2022-07-28；Accepted：2022-09-16；Published Online：2022-10-14 14：06

　URL：link.cnki.net/urlid/11.2625.V.20221014.1054.002

　Foundation item：The Fundamental Research Funds for the Central Universities (YWF-22-L-801)

 * Corresponding author. E-mail：jinleibuaa@163.com

