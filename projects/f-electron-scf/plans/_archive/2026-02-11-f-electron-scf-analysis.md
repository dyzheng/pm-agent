# 稀土f电子模守恒赝势SCF收敛问题：技术分析与任务分解

**目标：** 在ABACUS中实现稀土元素（f_in_valence）模守恒赝势的可靠SCF收敛，覆盖合金、磁性化合物、表面催化、分子催化等场景。

---

## 0. 问题全景

稀土元素的4f电子具有以下特殊性，导致SCF收敛极其困难：
- **极度局域化**：4f轨道径向分布极窄，与5s/5p/5d/6s轨道空间重叠小，导致电荷密度在实空间高度不均匀
- **多重态密集**：4f^n构型的LS耦合态密集，能量差小（~0.01-0.1 eV），SCF容易在多个局域极小值间震荡
- **强关联效应**：4f电子间库仑排斥强，单粒子DFT图像不足，DFT+U是最低成本的修正但引入新的收敛难题
- **赝势挑战**：f_in_valence赝势需要处理4f/5s/5p/5d/6s多个壳层，截断半径选择困难，可迁移性差
- **高截断能**：f轨道的高角动量分量需要更高的平面波截断能（100-200 Ry），计算代价大

---

## 1. 技术难点分层分析

### 1.1 赝势测试与生成

| 属性 | 值 |
|---|---|
| 难度 | HIGH |
| 前置依赖 | 无 |
| 阻塞下游 | 所有后续任务 |

**现状分析：**
- ABACUS支持UPF格式赝势（`read_pp_upf100.cpp`, `read_pp_upf201.cpp`），可读取lmax、lchi、nchi等f轨道信息
- `pseudo.cpp`中的`Pseudo_NC`类处理模守恒赝势，支持任意lmax
- 现有赝势库（SG15、PseudoDojo、PSlibrary）对稀土元素覆盖不完整，f_in_valence版本更少
- VWR格式赝势（`read_pp_vwr.cpp`）只支持到d轨道（S/P/D），不支持f

**需要做的：**
1. 调研现有f_in_valence赝势库：PseudoDojo（Oncvpsp）、PSlibrary（QE）、JTH（ABINIT PAW→NC转换）
2. 用ONCVPSP或APE生成稀土NC赝势，关键参数：
   - 参考构型选择（中性原子 vs 离子化构型）
   - 4f/5s/5p/5d/6s各通道截断半径优化
   - Ghost state检测（对数导数测试）
   - 可迁移性测试（多构型能量差 vs 全电子）
3. 建立赝势质量验证流程：
   - 原子计算对比（ABACUS vs 全电子AE）
   - 简单化合物（CeO2, GdN）晶格常数/体模量对比
   - Delta-test框架适配稀土元素

**关键风险：** f_in_valence赝势的可迁移性是整个项目的基础。如果赝势质量不过关，后续所有工作都建立在错误基础上。

### 1.2 数值原子轨道（NAO）生成与优化

| 属性 | 值 |
|---|---|
| 难度 | MEDIUM-HIGH |
| 前置依赖 | 1.1 赝势 |
| 阻塞下游 | LCAO计算 |

**现状分析：**
- ABACUS的ABACUS-orbitals工具可生成NAO，算法成熟（spillage最小化）
- 轨道文件格式已标准化，`source/source_basis/module_nao/`有完整的读取/处理代码
- 稀土元素的最优轨道组合策略不明确：
  - 基础：需要包含4f/5s/5p/5d/6s通道
  - 极化：是否需要5f/6p/6d极化函数？
  - 每个通道的zeta数（DZP? TZP? QZP?）
  - 截断半径：f轨道极度局域，但化学环境可能需要较大截断

**需要做的：**
1. 系统测试不同轨道组合对稀土化合物性质的影响：
   - 最小基组：[4f,5s,5p,5d,6s] 单zeta
   - DZP：双zeta + 极化
   - TZP：三zeta + 极化
   - 自定义：针对特定应用优化
2. 建立轨道质量评估标准：
   - 与PW基组结果的一致性（能量差、力差、带结构差）
   - 不同化学环境的可迁移性
   - 计算效率（稀疏度、矩阵维度）
3. 考虑是否需要修改spillage优化算法以更好处理f轨道

### 1.3 DFT+U算法与收敛性

| 属性 | 值 |
|---|---|
| 难度 | CRITICAL |
| 前置依赖 | 1.1, 1.2 |
| 阻塞下游 | 所有含f电子的精确计算 |

**ABACUS DFT+U现状（基于代码分析）：**

```
source/source_lcao/module_dftu/
├── dftu.cpp          — 主逻辑：U-ramping, omc控制, 占据矩阵计算
├── dftu.h            — DFTU类定义
├── dftu_occup.cpp    — 占据矩阵mixing（阻尼）
├── dftu_hamilt.cpp   — DFT+U哈密顿量贡献
├── dftu_force.cpp    — DFT+U力/应力Pulay修正
├── dftu_yukawa.cpp   — Yukawa势自动U/J计算
├── dftu_tools.cpp    — 工具函数（cal_type=3 Dudarev）
├── dftu_io.cpp       — 占据矩阵I/O
├── dftu_folding.cpp  — k空间折叠
└── dftu_pw.cpp       — PW基组DFT+U（仅nspin=4/SOC）
```

**已有能力：**
- Dudarev简化方案（cal_type=3）
- U-ramping（`uramping`参数）：从小U逐步增大到目标U，帮助收敛
- 占据矩阵控制（omc=0/1/2）：从`initial_onsite.dm`读取初始占据矩阵
- Yukawa势自动U/J计算
- 占据矩阵mixing/阻尼
- 完整的力/应力DFT+U Pulay修正

**缺失能力（对稀土f电子关键）：**
- **无随机占据矩阵初始化**：无法系统探索多个SCF极小值
- **无占据退火**：无法从高温smearing逐步冷却到基态
- **无自动多极小值探索**：无法运行N个随机初始化，选最低能量
- **无亚稳态检测/警告**：用户不知道是否收敛到了正确基态
- **无Liechtenstein旋转不变形式**：只有Dudarev，对f电子精度不足
- **无DFT+U+V（位间Hubbard）**：稀土化合物中f-d杂化需要
- **PW基组限制**：只支持nspin=4（SOC），不支持共线自旋

**需要做的：**
1. **占据矩阵初始化增强**：
   - 实现随机占据矩阵初始化（在`dftu.cpp`中添加）
   - 实现基于化学直觉的初始猜测（根据元素氧化态预设f电子数）
   - 实现多起点并行探索策略
2. **收敛性增强**：
   - 占据矩阵退火（高温→低温smearing）
   - 更强的占据矩阵阻尼（当前`dftu_occup.cpp`的mixing可能不够）
   - U-ramping与占据矩阵控制的联合策略
3. **亚稳态检测**：
   - 监控占据矩阵的本征值分布
   - 检测能量是否在多个SCF循环间震荡
   - 输出警告信息

### 1.4 高截断能性能优化

| 属性 | 值 |
|---|---|
| 难度 | MEDIUM |
| 前置依赖 | 1.1 |
| 阻塞下游 | PW基组大规模计算 |

**问题：** f轨道的高角动量分量需要ecutwfc > 100 Ry（vs 普通元素40-60 Ry），FFT网格和平面波数量大幅增加。

**ABACUS现状：**
- `source/source_basis/module_pw/pw_basis.cpp`：标准FFT网格
- Davidson对角化（`diago_david.cpp`）：内存 ∝ npw × nbands
- 无自适应精度策略

**需要做的：**
1. 评估ecutwfc对稀土计算精度的影响（收敛性测试）
2. 考虑PAW方法作为替代（ABACUS是否有PAW支持？→ 目前无）
3. LCAO基组可以绕过高ecutwfc问题，但需要高质量NAO（回到1.2）
4. 对于必须用PW的场景，评估：
   - 双网格技术（粗网格SCF + 细网格能量）
   - 实空间投影算子（减少非局域势计算量）

### 1.5 SCF算法优化：AI辅助初猜 + 带阻尼电荷约束

| 属性 | 值 |
|---|---|
| 难度 | CRITICAL — 本项目核心创新点 |
| 前置依赖 | 1.1, 1.3 |
| 阻塞下游 | 可靠的自动化计算 |

**问题本质：** 常规Broyden mixing对f电子体系失效的原因：
1. 电荷密度的初始猜测（原子叠加）对f电子分布严重偏离真实基态
2. Kerker预处理假设金属性电荷响应，对局域f电子不适用
3. 多个SCF极小值之间的能量壁垒低，mixing容易在它们之间震荡

**ABACUS charge mixing现状：**
```
source/source_base/module_mixing/
├── mixing.h/cpp           — 基类
├── broyden_mixing.h/cpp   — Broyden mixing
├── pulay_mixing.h/cpp     — Pulay mixing
└── plain_mixing.h/cpp     — 简单线性mixing

source/source_estate/module_charge/
├── charge_mixing.h/cpp              — 主控制
├── charge_mixing_preconditioner.cpp — Kerker预处理（mixing_gg0, mixing_gg0_min）
├── charge_mixing_rho.cpp            — 电荷密度mixing
├── charge_mixing_dmr.cpp            — 密度矩阵mixing（LCAO）
├── charge_mixing_residual.cpp       — 残差计算
└── charge_mixing_uspp.cpp           — USPP相关
```

**init_chg选项：** `atomic`, `file`, `wfc`, `auto`, `dm`, `hr`
**init_wfc选项：** `atomic`, `atomic+random`, `random`, `file`, `nao`

**需要做的（分三个层次）：**

**层次A — 改进现有mixing（短期，代码修改量小）：**
1. 自适应Kerker参数：根据体系类型（金属/绝缘体/f电子）自动调整mixing_gg0
2. 分通道mixing：对f电子通道使用更小的mixing_beta（更保守的更新）
3. 能量监控+自动回退：当SCF能量上升时，自动减小mixing_beta并回退

**层次B — 带阻尼的电荷约束（中期，需要新模块）：**
1. 实现constrained DFT（cDFT）框架：约束特定原子的f电子数
2. 约束强度从强到弱逐步释放（类似U-ramping的思路）
3. 与DFT+U的占据矩阵控制协同工作
4. 实现方式：在SCF循环中添加惩罚势 V_constraint = λ(n_f - n_target)

**层次C — AI辅助电子态先验初猜（长期，创新性工作）：**
1. 训练一个轻量级模型（GNN或简单MLP）：
   - 输入：原子结构（元素、坐标、近邻环境）
   - 输出：每个稀土原子的f电子占据数、自旋态、轨道序
2. 用该模型生成初始占据矩阵，替代原子叠加初猜
3. 训练数据来源：已收敛的DFT+U计算结果
4. 与ABACUS的`init_chg`/`omc`接口对接

### 1.6 VASP/全电子对比验证

| 属性 | 值 |
|---|---|
| 难度 | MEDIUM |
| 前置依赖 | 1.1-1.5 |
| 贯穿全程 | 每个阶段都需要验证 |

**验证策略：**
- **参考方法1：** VASP + PAW（f_in_valence PAW数据集成熟，是事实标准）
- **参考方法2：** 全电子方法（FHI-aims / Elk / WIEN2k）作为终极参考
- **参考方法3：** Quantum ESPRESSO + NC赝势（同类方法对比）

**验证场景矩阵：**

| 场景 | 代表体系 | 关键性质 | 难度 |
|---|---|---|---|
| 简单氧化物 | CeO2, Gd2O3 | 晶格常数, 体模量, 带隙 | 入门 |
| 稀土合金 | NdFeB, SmCo5 | 磁矩, 磁各向异性能 | 中等 |
| 磁性化合物 | GdN, EuO, TbMnO3 | 磁序, 交换耦合常数 | 中等 |
| 混合价态 | CeO2→Ce2O3, Eu2+/Eu3+ | 氧化还原能, f电子转移 | 困难 |
| 表面催化 | CeO2(111)+CO, La2O3表面 | 吸附能, 反应路径 | 困难 |
| 分子催化 | 稀土茂金属, 稀土MOF | 配位能, 反应活性 | 困难 |
| Kondo/重费米子 | CeAl3, CeCoIn5 | 电子结构, 费米面 | 极难 |

### 1.7 自动化工作流集成

| 属性 | 值 |
|---|---|
| 难度 | MEDIUM |
| 前置依赖 | 1.1-1.6基本完成 |

**目标：** 将上述所有技术整合为可复用的自动化工作流，使稀土计算不再需要专家手动调参。

---

## 2. 任务分解与依赖关系

```
Phase 0: 基础设施（可并行）
  T0-A: 赝势库调研与收集
  T0-B: ONCVPSP赝势生成环境搭建
  T0-C: ABACUS DFT+U代码审计（详细理解现有实现）

Phase 1: 赝势与轨道（串行依赖）
  T1-A: 稀土NC赝势生成（Ce, Gd, Nd, Sm, Eu, Tb, La）  ← T0-A, T0-B
  T1-B: 赝势质量验证（原子测试 + Delta-test）           ← T1-A
  T1-C: NAO轨道生成（多种zeta组合）                     ← T1-B
  T1-D: 轨道质量评估（PW vs LCAO对比）                  ← T1-C

Phase 2: SCF收敛算法（可部分并行）
  T2-A: 自适应Kerker参数实现                            ← T0-C
  T2-B: 分通道mixing_beta实现                           ← T0-C
  T2-C: 占据矩阵随机初始化 + 多起点探索                 ← T0-C
  T2-D: 占据退火策略实现                                ← T2-C
  T2-E: 能量监控 + 自动回退机制                         ← T2-A, T2-B
  T2-F: constrained DFT框架（f电子数约束）              ← T2-E

Phase 3: AI辅助初猜（依赖Phase 1+2的数据）
  T3-A: 训练数据收集（已收敛计算的占据矩阵）            ← Phase 1, Phase 2
  T3-B: 模型设计与训练（结构→占据矩阵）                 ← T3-A
  T3-C: ABACUS接口集成（模型预测→init_chg/omc）         ← T3-B

Phase 4: 验证（贯穿全程，每个Phase完成后都做）
  T4-A: 简单氧化物验证（CeO2, Gd2O3）                  ← Phase 1
  T4-B: 合金验证（NdFeB, SmCo5）                        ← Phase 2
  T4-C: 磁性化合物验证（GdN, EuO）                      ← Phase 2
  T4-D: 表面催化验证（CeO2(111)+CO）                    ← Phase 2
  T4-E: 分子催化验证（稀土茂金属）                       ← Phase 2
  T4-F: 全场景综合验证                                   ← Phase 3

Phase 5: 工作流自动化
  T5-A: 自动参数选择策略                                 ← Phase 4
  T5-B: 失败自动诊断与重试                               ← T5-A
  T5-C: 工作流文档与示例                                 ← T5-B
```

---

## 3. 优先级排序

**Tier 0 — 必须先做（阻塞一切）：**
`T0-A/B/C → T1-A → T1-B`
没有可靠的赝势，后续一切都是空中楼阁。

**Tier 1 — 核心算法（项目价值所在）：**
`T2-A/B/C → T2-D/E → T2-F`
SCF收敛算法改进是本项目的核心交付物。

**Tier 2 — 轨道优化（LCAO用户必需）：**
`T1-C → T1-D`
如果只用PW基组可以延后，但LCAO是ABACUS的特色。

**Tier 3 — 创新性工作（长期价值）：**
`T3-A → T3-B → T3-C`
AI辅助初猜是最有创新性的部分，但依赖大量已收敛数据。

**Tier 4 — 验证与自动化（持续进行）：**
`T4-A...F → T5-A/B/C`

---

## 4. ABACUS代码修改点汇总

| 文件/模块 | 修改类型 | 任务 |
|---|---|---|
| `source/source_estate/module_charge/charge_mixing_preconditioner.cpp` | 增强 | T2-A: 自适应Kerker |
| `source/source_estate/module_charge/charge_mixing.cpp` | 增强 | T2-B: 分通道mixing |
| `source/source_estate/module_charge/charge_mixing_rho.cpp` | 增强 | T2-E: 能量监控回退 |
| `source/source_lcao/module_dftu/dftu.cpp` | 增强 | T2-C: 随机占据初始化 |
| `source/source_lcao/module_dftu/dftu_occup.cpp` | 增强 | T2-D: 占据退火 |
| `source/source_lcao/module_dftu/dftu_io.cpp` | 增强 | T2-C: 多起点I/O |
| 新模块: `source/source_estate/module_charge/charge_constraint.cpp` | 新建 | T2-F: cDFT |
| `source/source_io/module_parameter/input_parameter.h` | 增强 | 新输入参数 |
| `source/source_io/module_parameter/read_input_item_exx_dftu.cpp` | 增强 | 新输入参数 |

---

## 5. 风险评估

| 风险 | 概率 | 影响 | 缓解措施 |
|---|---|---|---|
| 赝势质量不足，ghost state | HIGH | CRITICAL | 多工具交叉验证，必要时用PAW参考 |
| DFT+U多极小值无法可靠找到基态 | HIGH | CRITICAL | 多起点+退火+约束的组合策略 |
| 高ecutwfc导致计算不可行 | MEDIUM | HIGH | 优先发展LCAO路线 |
| AI模型训练数据不足 | MEDIUM | MEDIUM | 先用规则基方法，AI作为增强 |
| VASP对比发现系统性偏差 | MEDIUM | HIGH | 追溯到赝势/基组层面修正 |
| 代码修改引入回归bug | LOW | HIGH | 完善单元测试，CI集成 |

---

## 6. 里程碑定义

**M1（月1-2）：** 赝势+轨道基础就绪
- 至少3种稀土元素（Ce, Gd, La）的验证赝势
- 对应NAO轨道文件
- CeO2基准测试通过

**M2（月3-4）：** SCF收敛算法v1
- 自适应Kerker + 分通道mixing实现
- 占据矩阵多起点探索实现
- GdN, EuO等磁性体系可收敛

**M3（月5-6）：** 高级收敛策略
- constrained DFT框架
- 占据退火
- 表面催化场景可收敛

**M4（月7-9）：** AI辅助 + 全面验证
- AI初猜模型原型
- 全场景验证完成
- 自动化工作流

---

## 7. 与现有项目的关联

- **surface-catalysis-dpa项目**：本项目的T4-D（表面催化验证）与该项目的DFT+U瓶颈（§1.9, §1.13）直接相关
- **pybind11-interface项目**：自动化工作流（Phase 5）可通过PyABACUS接口暴露
- **ABACUS主线开发**：Phase 2的代码修改需要与ABACUS开发团队协调，避免冲突
