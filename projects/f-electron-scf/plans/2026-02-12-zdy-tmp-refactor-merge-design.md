# zdy-tmp 重构与 develop 合并：细化任务计划

**日期：** 2026-02-12
**策略：** 在 develop 最新分支上重新移植，细粒度 PR

---

## 1. 背景与现状

### zdy-tmp 仓库状态
- 基于 develop 分叉，241 个 commits 的增量
- 功能可用但代码混乱：混杂 debug prints、WIP 代码、试错过程
- 目录结构为旧版（`module_hamilt_lcao/`、`module_esolver/` 等）

### develop 仓库状态（最新 origin/develop）
- 已完成大规模目录重构：
  - `module_hamilt_lcao/` → `source_lcao/`
  - `module_hamilt_pw/` → `source_pw/`
  - `module_esolver/` → `source_esolver/`
  - `module_elecstate/` → `source_estate/`
  - `module_parameter/` → `source_io/module_parameter/`
  - `module_base/` → `source_base/`
- 类名重构：`ModuleDFTU::DFTU` → `Plus_U`（无命名空间）
- 去全局化：`GlobalC::ucell` 引用已大量移除，改为参数传递
- `onsite_projector` 基础设施已存在，但类名不同：
  - develop: `Onsite_Proj_tools` + `onsite_proj_tools.h/cpp`
  - zdy-tmp: `FS_Nonlocal_tools` + `onsite_proj_pw.h/cpp`

### 工作环境
- 新 worktree: `/root/abacus-dftu-pw-port` (分支 `feat/dftu-pw-port`，基于最新 origin/develop)
- 参考代码: `/root/abacus-zdy-tmp` (zdy-tmp 分支，detached HEAD)
- 主仓库: `/root/abacus-develop`

---

## 2. 功能增量清单

从 zdy-tmp 需要移植的功能增量（按依赖排序）：

### Layer 0: onsite_projector 增强
- `cal_occupations()` 增加 `isk_in` 参数（nspin=2 支持）
- `cal_becp()` 增加 `npwx` 参数
- API 适配（zdy-tmp 用 `FS_Nonlocal_tools`，develop 已重构为 `Onsite_Proj_tools`）

### Layer 1: DFT+U PW 基组支持
- `dftu_pw.cpp` 从仅 nspin=4 扩展到 nspin=1/2/4（+135 行）
- `dftu.cpp/h` 添加 PW 相关方法（`cal_occup_m_pw`、`eff_pot_pw` 等）
- `dftu_occup.cpp` 添加 `mixing_dftu` 功能（占据矩阵 mixing）
- `forces_onsite.cpp` DFT+U 力计算
- `stress_func_onsite.cpp` DFT+U 应力计算
- `esolver_ks_pw.cpp` 集成 DFT+U 调用

### Layer 2: DeltaSpin 增强
- `module_deltaspin/` 新增文件：`cal_h_lambda.cpp`、`cal_mw_helper.cpp`、`sc_parse_json.cpp`
- DeltaSpin PW 支持（`esolver_ks_pw.cpp` 集成）
- DeltaSpin + DFTU 联合使用
- `conserve_setting` 参数
- `dspin_lcao.cpp/h` LCAO 算符（develop 已有但可能需要更新）

### Layer 3: 收敛策略增强
- `mixing_dftu`：自动检测占据矩阵震荡并开启 mixing
- `mixing_restart` 与 `mixing_dftu` 协同
- SCF 震荡检测 + 自动回退
- `sc_scf_thr`、`sc_drop_thr` 等参数

---

## 3. 适配工作量评估

### 关键适配点

| 适配项 | 影响范围 | 工作量 |
|---|---|---|
| include 路径替换 | 所有文件 | 低（机械替换） |
| `ModuleDFTU::DFTU` → `Plus_U` | dftu 相关所有文件 | 中（类名+命名空间） |
| `GlobalC::ucell` → 参数传递 | dftu 约 119 处引用 | 高（需理解每处上下文） |
| `GlobalV::NSPIN/NLOCAL` → `PARAM.inp` | dftu 约 142 处引用 | 中（模式化替换） |
| `FS_Nonlocal_tools` → `Onsite_Proj_tools` | onsite_projector 相关 | 中（API 适配） |
| `get_instance()` 单例 → develop 模式 | dftu 调用点 | 中 |
| operator_lcao 文件名变化 | `*_new.cpp` → `*.cpp` | 低 |

---

## 4. PR 拆分与任务细化

### Phase A: 基础设施（PR-1）

#### PR-1: onsite_projector nspin=2 支持
**目标：** 让 onsite_projector 支持 nspin=1/2（当前 develop 仅 nspin=4）

**文件改动：**
- `source/source_pw/module_pwdft/onsite_projector.h` — `cal_occupations()` 增加 `isk_in` 参数
- `source/source_pw/module_pwdft/onsite_projector.cpp` — 实现 nspin=1/2 的占据矩阵计算路径
- `source/source_pw/module_pwdft/onsite_proj_tools.h/cpp` — 适配新接口

**参考代码：** zdy-tmp `onsite_projector.h/cpp` 中的 nspin=2 相关改动

**验收标准：**
- 编译通过
- 现有 nspin=4 测试不受影响
- 新增 nspin=2 单元测试

**预估工作量：** 1-2 天

---

### Phase B: DFT+U PW（PR-2 ~ PR-7）

#### PR-2: DFT+U PW SCF（nspin=4）
**目标：** 在 PW 基组下支持 DFT+U SCF 计算（先 nspin=4）

**文件改动：**
- `source/source_lcao/module_dftu/dftu_pw.cpp` — 移植 zdy-tmp 的 PW 占据矩阵计算
- `source/source_lcao/module_dftu/dftu.h` — 添加 PW 相关成员（`eff_pot_pw`、`cal_occup_m_pw` 等）
- `source/source_lcao/module_dftu/dftu.cpp` — PW 初始化路径
- `source/source_esolver/esolver_ks_pw.cpp` — 集成 DFT+U 调用（占据矩阵计算、能量修正）
- `source/source_io/module_parameter/input_parameter.h` — 确认 PW DFT+U 参数可用

**适配要点：**
- `ModuleDFTU::DFTU` → `Plus_U` 类名适配
- `GlobalC::ucell` → 通过参数传递 `UnitCell&`
- `GlobalV::NSPIN` → `PARAM.inp.nspin`
- `get_instance()` → develop 的实例获取方式

**参考代码：** zdy-tmp `dftu_pw.cpp`（354行）vs develop（219行），增量约 135 行核心逻辑

**验收标准：**
- CeO2 nspin=4 PW DFT+U SCF 可收敛
- 能量与 LCAO DFT+U 定性一致
- 编译通过，现有测试不受影响

**预估工作量：** 3-5 天

#### PR-3: DFT+U PW nspin=1/2 扩展
**目标：** 扩展 PW DFT+U 支持 nspin=1 和 nspin=2

**文件改动：**
- `source/source_lcao/module_dftu/dftu_pw.cpp` — nspin=1/2 分支
- `source/source_esolver/esolver_ks_pw.cpp` — nspin=2 的 isk 处理

**依赖：** PR-1（onsite_projector nspin=2）、PR-2

**参考代码：** zdy-tmp commits `0becd0c54`（nspin2 for DFTU）、`6098fba11`（fix nspin2 energy/force/stress）

**验收标准：**
- NiO nspin=2 PW DFT+U SCF 可收敛
- 能量与 LCAO 一致

**预估工作量：** 2-3 天

#### PR-4: DFT+U PW force
**目标：** PW 基组下 DFT+U 力的计算

**文件改动：**
- `source/source_pw/module_pwdft/forces_onsite.cpp` — 适配 `Plus_U` 接口
- `source/source_pw/module_pwdft/onsite_proj_tools.h/cpp` — `cal_force_dftu()` 方法

**参考代码：** zdy-tmp `forces_onsite.cpp`、`onsite_proj_pw.cpp` 中的 force 部分

**验收标准：**
- CeO2 PW DFT+U 力与 LCAO 一致（误差 < 1 mRy/Bohr）
- 力的对称性正确

**预估工作量：** 2-3 天

#### PR-5: DFT+U PW stress
**目标：** PW 基组下 DFT+U 应力的计算

**文件改动：**
- `source/source_pw/module_pwdft/stress_func_onsite.cpp` — 适配 `Plus_U` 接口
- `source/source_pw/module_pwdft/onsite_proj_tools.h/cpp` — `cal_stress_dftu()` 方法

**依赖：** PR-4

**参考代码：** zdy-tmp `stress_func_onsite.cpp`、commits `c324dfb42`（stress for DFT+U）

**验收标准：**
- CeO2 PW DFT+U 应力与 LCAO 一致
- 应力张量对称性正确

**预估工作量：** 2 天

#### PR-6: mixing_dftu（占据矩阵 mixing）
**目标：** 实现占据矩阵的 Broyden mixing，改善 DFT+U 收敛性

**文件改动：**
- `source/source_lcao/module_dftu/dftu_occup.cpp` — 添加 `mix_locale()` 方法
- `source/source_lcao/module_dftu/dftu.h` — 添加 `mixing_dftu` 相关成员
- `source/source_lcao/module_dftu/dftu.cpp` — mixing 初始化
- `source/source_io/module_parameter/input_parameter.h` — `mixing_dftu` 参数
- `source/source_io/module_parameter/read_input_item_exx_dftu.cpp` — 参数读取

**参考代码：** zdy-tmp commits `d1caf6186`（mixing_dftu for PW）、`7bb6fd666`（auto open mixing_dftu）

**验收标准：**
- `mixing_dftu=true` 时占据矩阵使用 Broyden mixing
- 震荡体系自动开启 mixing_dftu
- 不影响非 DFT+U 计算

**预估工作量：** 3-4 天

#### PR-7: GPU/DCU 加速适配
**目标：** 确保 PW DFT+U 在 GPU/DCU 上正确运行

**文件改动：**
- `source/source_pw/module_pwdft/kernels/` — GPU kernel 适配
- `source/source_pw/module_pwdft/onsite_proj_tools.cpp` — device memory 操作

**依赖：** PR-2 ~ PR-5

**参考代码：** zdy-tmp 中大量 GPU fix commits

**验收标准：**
- CUDA 编译通过
- GPU 结果与 CPU 一致

**预估工作量：** 3-5 天

---

### Phase C: DeltaSpin（PR-8 ~ PR-12）

#### PR-8: module_deltaspin 核心移植
**目标：** 将 zdy-tmp 新增的 deltaspin 文件移植到 develop

**文件改动（新增）：**
- `source/source_lcao/module_deltaspin/cal_h_lambda.cpp` — 计算 h_lambda 算符
- `source/source_lcao/module_deltaspin/cal_mw_helper.cpp` — MW 计算辅助函数
- `source/source_lcao/module_deltaspin/sc_parse_json.cpp` — JSON 配置解析
- `source/source_lcao/module_deltaspin/CMakeLists.txt` — 更新构建
- `source/source_lcao/module_deltaspin/test/` — 新增测试文件

**文件改动（更新）：**
- `source/source_lcao/module_deltaspin/spin_constrain.h/cpp` — 合并 zdy-tmp 的增强

**适配要点：**
- include 路径适配
- `GlobalC::ucell` → 参数传递
- 与 develop 已有的 `spin_constrain.h` 合并（develop 有基础版本，zdy-tmp 有增强版本）

**验收标准：**
- 所有 deltaspin 单元测试通过
- 编译通过

**预估工作量：** 3-4 天

#### PR-9: DeltaSpin LCAO 算符更新
**目标：** 更新 LCAO 下的 DeltaSpin 算符

**文件改动：**
- `source/source_lcao/module_operator_lcao/dspin_lcao.h/cpp` — 合并 zdy-tmp 改动
- `source/source_lcao/module_operator_lcao/dspin_force_stress.hpp` — 力/应力更新
- `source/source_esolver/esolver_ks_lcao.cpp` — DeltaSpin 集成点更新

**依赖：** PR-8

**验收标准：**
- LCAO DeltaSpin SCF 正确
- 力/应力正确

**预估工作量：** 2-3 天

#### PR-10: DeltaSpin PW 支持
**目标：** 在 PW 基组下支持 DeltaSpin

**文件改动：**
- `source/source_esolver/esolver_ks_pw.cpp` — 集成 DeltaSpin lambda loop
- `source/source_lcao/module_deltaspin/spin_constrain.h/cpp` — PW 相关方法（`cal_Mi_pw` 等）

**依赖：** PR-1、PR-8

**参考代码：** zdy-tmp commits `045066ee0`（lambda operator in PW）、`f59fadd89`（nspin2 DeltaSpin PW）

**验收标准：**
- PW DeltaSpin SCF 可运行
- 磁矩约束有效

**预估工作量：** 3-4 天

#### PR-11: DeltaSpin force/stress
**目标：** DeltaSpin 的力和应力计算（LCAO + PW）

**文件改动：**
- `source/source_pw/module_pwdft/forces_onsite.cpp` — DeltaSpin 力
- `source/source_pw/module_pwdft/stress_func_onsite.cpp` — DeltaSpin 应力

**依赖：** PR-9、PR-10

**参考代码：** zdy-tmp commits `cef4b8312`（force）、`c324dfb42`（stress）

**验收标准：**
- DeltaSpin 力/应力与数值微分一致

**预估工作量：** 2-3 天

#### PR-12: DeltaSpin + DFTU 联合 + conserve_setting
**目标：** 支持 DeltaSpin 和 DFT+U 同时使用

**文件改动：**
- `source/source_esolver/esolver_ks_pw.cpp` — 联合使用逻辑
- `source/source_esolver/esolver_ks_lcao.cpp` — 联合使用逻辑
- `source/source_io/module_parameter/input_parameter.h` — `conserve_setting` 参数

**依赖：** PR-6、PR-9

**参考代码：** zdy-tmp commit `a9d881c95`（conserve_setting for DFTU with DeltaSpin）

**验收标准：**
- DeltaSpin + DFT+U 联合计算正确
- conserve_setting 参数生效

**预估工作量：** 2-3 天

---

### Phase D: 收敛策略增强（PR-13 ~ PR-14）

#### PR-13: SCF 震荡检测 + 自动回退
**目标：** 检测 SCF 能量震荡并自动调整策略

**文件改动：**
- `source/source_estate/module_charge/charge_mixing.cpp` — 震荡检测逻辑
- `source/source_esolver/esolver_ks.cpp` — 自动回退机制

**依赖：** PR-6

**参考代码：** zdy-tmp commits `f506ae37f`、`7bb6fd666`

**验收标准：**
- 震荡体系自动检测并调整 mixing 参数
- 不影响正常收敛体系

**预估工作量：** 2-3 天

#### PR-14: mixing_restart 与 mixing_dftu 协同
**目标：** 修复 mixing_restart 与 mixing_dftu 的兼容性问题

**文件改动：**
- `source/source_estate/module_charge/charge_mixing.cpp` — restart 逻辑修复

**依赖：** PR-6、PR-13

**参考代码：** zdy-tmp commits `96f72ca00`、`caf450953`

**验收标准：**
- mixing_restart 后 mixing_dftu 状态正确
- kpar > 1 时 mixing_dftu 正确

**预估工作量：** 1-2 天

---

## 5. 执行时间线

```
Week 1:  PR-1 (onsite_projector) + PR-8 (deltaspin core) [可并行]
Week 2:  PR-2 (DFT+U PW nspin=4 SCF)
Week 3:  PR-3 (nspin=1/2) + PR-4 (force) [可并行]
Week 4:  PR-5 (stress) + PR-6 (mixing_dftu) [可并行]
Week 5:  PR-9 (dspin LCAO) + PR-10 (dspin PW) [可并行]
Week 6:  PR-11 (dspin force/stress) + PR-12 (联合使用)
Week 7:  PR-7 (GPU) + PR-13 (震荡检测) + PR-14 (mixing_restart)
```

总计约 7 周，14 个 PR。

---

## 6. 风险与缓解

| 风险 | 概率 | 缓解 |
|---|---|---|
| develop 持续更新导致冲突 | HIGH | 每周 rebase，小 PR 快速合入 |
| Plus_U 类 API 与 zdy-tmp 差异大 | MEDIUM | PR-2 先做最小适配，后续 PR 逐步完善 |
| GPU kernel 适配困难 | MEDIUM | PR-7 放最后，先确保 CPU 正确 |
| 测试覆盖不足 | LOW | 每个 PR 附带单元测试 + 集成测试 |

---

## 7. 与 f-electron-scf 项目的关系

本计划对应 f-electron-scf 项目的 Phase 0（代码集成与架构），具体映射：

| 原任务 | 新任务 |
|---|---|
| T0-1 合并PW+LCAO DFT+U代码 | PR-1 ~ PR-7 |
| T0-2 重构DFT+U架构为可插拔策略 | 移植过程中自然完成适配 |
| T0-3 建立回归测试套件 | 每个 PR 附带测试 |

Phase 0 完成后，Phase 1（收敛改进）和 Phase 2（占据矩阵策略）的任务可以直接在 develop 上开发。
