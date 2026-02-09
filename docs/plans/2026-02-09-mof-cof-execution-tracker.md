# MOF/COF 手性模拟 — 执行状态追踪表

> 基于 `mof-cof-chirality-analysis.md` 的 20 个任务，映射到 PM Agent execute/verify 流水线。

---

## 表 1：主控追踪表（Master Tracker）

| ID | 任务 | 层级 | Specialist | 依赖 | 执行波次 | 状态 | 审阅结果 | Gate 结果 | 备注 |
|----|------|------|-----------|------|---------|------|---------|----------|------|
| A-001 | MOF/COF 结构准备工作流 | Workflow | workflow_agent | — | Wave 1 | PENDING | — | — | CIF→STRU 转换 |
| C-001 | CD 谱理论与实现方案调研 | Algorithm | algorithm_agent | — | Wave 1 | PENDING | — | — | **关键决策点** |
| C-005 | 手性判定与描述符 | Workflow | workflow_agent | A-001 | Wave 2 | PENDING | — | — | pymatgen/ASE |
| A-002 | 几何优化（结构弛豫） | Workflow | workflow_agent | A-001 | Wave 2 | PENDING | — | — | relax+cell_relax |
| B-001 | SOC 自洽 + H/S/r 输出 | Infra | infra_agent | A-002 | Wave 3 | PENDING | — | — | nspin=4 可行性 |
| A-003 | 声子稳定性验证 | Workflow | workflow_agent | A-002 | Wave 3 | PENDING | — | — | Phonopy 编排 |
| A-004 | MLP 训练 (DeePMD) | Algorithm | algorithm_agent | A-002 | Wave 3 | PENDING | — | — | DP-GEN 闭环 |
| A-006 | 弹性性质与力学稳定性 | Workflow | workflow_agent | A-002 | Wave 3 | PENDING | — | — | abacustest elastic |
| B-002 | PYATB 拓扑性质计算 | Algorithm | algorithm_agent | B-001 | Wave 4 | PENDING | — | — | Berry/Chern/Wilson |
| B-003 | 光学性质（光电导率） | Algorithm | algorithm_agent | B-001 | Wave 4 | PENDING | — | — | σ(ω) 张量 |
| B-004 | 非线性光学（SHG） | Algorithm | algorithm_agent | B-001 | Wave 4 | PENDING | — | — | 手性 SHG 指标 |
| A-005 | 热力学稳定性 MD | Workflow | workflow_agent | A-004 | Wave 4 | PENDING | — | — | NPT 300/500/800K |
| C-002 | 磁偶极跃迁矩阵元 | Core | core_cpp_agent | C-001 | Wave 4 | PENDING | — | — | **核心开发** |
| D-001 | DeePTB 训练数据准备 | Algorithm | algorithm_agent | B-001 | Wave 4 | PENDING | — | — | dftio 转换 |
| C-003 | 圆二色性谱计算 | Algorithm | algorithm_agent | C-002 | Wave 5 | PENDING | — | — | R_n + Δε(ω) |
| D-002 | DeePTB 模型训练验证 | Algorithm | algorithm_agent | D-001 | Wave 5 | PENDING | — | — | MAE<50meV |
| C-004 | 振动圆二色性 (VCD) | Algorithm | algorithm_agent | A-003, C-002 | Wave 6 | PENDING | — | — | ⚠️ 依赖 DFPT |
| D-003 | DeePTB 加速拓扑/光学 | Workflow | workflow_agent | B-002, B-003, D-002 | Wave 6 | PENDING | — | — | 大体系路径 |
| E-001 | 端到端验证 | Workflow | workflow_agent | A-002, A-003, B-002, B-003 | Wave 7 | PENDING | — | — | MOF-520 基准 |
| E-002 | abacustest 集成 | Workflow | workflow_agent | E-001 | Wave 8 | PENDING | — | — | CI/CD 回归 |

**状态值**: `PENDING` → `IN_PROGRESS` → `DONE` / `FAILED` / `PAUSED`
**审阅结果**: `APPROVE` / `REVISE(n次)` / `REJECT` / `PAUSE`
**Gate 结果**: `ALL_PASS` / `RETRY(n)→PASS` / `FAIL→OVERRIDE` / `FAIL→PAUSE`

---

## 表 2：依赖矩阵（谁阻塞谁）

行 = 被阻塞任务，列 = 阻塞者。`●` = 直接依赖，`○` = 传递依赖。

| 被阻塞 ↓ \ 阻塞者 → | A-001 | C-001 | C-005 | A-002 | B-001 | A-003 | A-004 | A-006 | B-002 | B-003 | B-004 | A-005 | C-002 | D-001 | C-003 | D-002 | C-004 | D-003 | E-001 |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **C-005** | ● | | | | | | | | | | | | | | | | | | |
| **A-002** | ● | | | | | | | | | | | | | | | | | | |
| **B-001** | ○ | | | ● | | | | | | | | | | | | | | | |
| **A-003** | ○ | | | ● | | | | | | | | | | | | | | | |
| **A-004** | ○ | | | ● | | | | | | | | | | | | | | | |
| **A-006** | ○ | | | ● | | | | | | | | | | | | | | | |
| **B-002** | ○ | | | ○ | ● | | | | | | | | | | | | | | |
| **B-003** | ○ | | | ○ | ● | | | | | | | | | | | | | | |
| **B-004** | ○ | | | ○ | ● | | | | | | | | | | | | | | |
| **A-005** | ○ | | | ○ | | | ● | | | | | | | | | | | | |
| **C-002** | | ● | | | | | | | | | | | | | | | | | |
| **D-001** | ○ | | | ○ | ● | | | | | | | | | | | | | | |
| **C-003** | | ○ | | | | | | | | | | | ● | | | | | | |
| **D-002** | ○ | | | ○ | ○ | | | | | | | | | ● | | | | | |
| **C-004** | ○ | ○ | | ● | | ● | | | | | | | ● | | | | | | |
| **D-003** | ○ | | | ○ | ○ | | | | ● | ● | | | | ○ | | ● | | | |
| **E-001** | ○ | | | ● | ○ | ● | | | ● | ● | | | | | | | | | |
| **E-002** | ○ | | | ○ | ○ | ○ | | | ○ | ○ | | | | | | | | | ● |

**关键路径**: A-001 → A-002 → B-001 → B-002/B-003 → E-001 → E-002
**手性关键路径**: C-001 → C-002 → C-003（最长的开发链）

---

## 表 3：波次执行计划（并行度分析）

| 波次 | 并行任务 | 任务数 | Specialist 分配 | 预计瓶颈 |
|------|---------|-------|----------------|---------|
| **Wave 1** | A-001, C-001 | 2 | workflow×1, algorithm×1 | 无（无依赖，可立即启动） |
| **Wave 2** | C-005, A-002 | 2 | workflow×2 | A-002 需要 DFT+U 参数调研 |
| **Wave 3** | B-001, A-003, A-004, A-006 | 4 | infra×1, workflow×2, algorithm×1 | A-004 MLP 训练工作量大 |
| **Wave 4** | B-002, B-003, B-004, A-005, C-002, D-001 | 6 | algorithm×4, workflow×1, core_cpp×1 | **C-002 是核心瓶颈**（4-gate 验证） |
| **Wave 5** | C-003, D-002 | 2 | algorithm×2 | D-002 训练耗时 |
| **Wave 6** | C-004, D-003 | 2 | algorithm×1, workflow×1 | ⚠️ C-004 可能 PAUSE（DFPT 依赖） |
| **Wave 7** | E-001 | 1 | workflow×1 | 全流程跑通，耗时长 |
| **Wave 8** | E-002 | 1 | workflow×1 | CI 集成 |

---

## 表 4：Gate 验证矩阵

| 任务 ID | BUILD | UNIT | LINT | CONTRACT | NUMERIC | Gate 总数 | 预期风险 |
|---------|:-----:|:----:|:----:|:--------:|:-------:|:---------:|---------|
| A-001 | | ○ | ○ | | | 2 | 低 |
| C-001 | | ○ | ○ | | | 2 | 低（纯调研） |
| C-005 | | ○ | ○ | | | 2 | 低 |
| A-002 | | ○ | ○ | | | 2 | 低 |
| B-001 | | ○ | ○ | | | 2 | 中（SOC 参数敏感） |
| A-003 | | ○ | ○ | | | 2 | 中（Phonopy 接口） |
| A-004 | | ○ | ○ | | | 2 | 中（训练收敛） |
| A-006 | | ○ | ○ | | | 2 | 低 |
| B-002 | | ○ | ○ | | | 2 | 低 |
| B-003 | | ○ | ○ | | | 2 | 低 |
| B-004 | | ○ | ○ | | | 2 | 低 |
| A-005 | | ○ | ○ | | | 2 | 中（MD 稳定性） |
| **C-002** | **○** | **○** | **○** | **○** | | **4** | **高（C++ 核心修改）** |
| D-001 | | ○ | ○ | | | 2 | 中（格式兼容） |
| C-003 | | ○ | ○ | | | 2 | 中（数值精度） |
| D-002 | | ○ | ○ | | | 2 | 中（训练收敛） |
| C-004 | | ○ | ○ | | | 2 | **高（DFPT 缺失）** |
| D-003 | | ○ | ○ | | | 2 | 中（精度对齐） |
| **E-001** | | **○** | | | **○** | **2** | **高（全链路集成）** |
| E-002 | | ○ | ○ | | | 2 | 低 |

**○** = 该 gate 启用

---

## 表 5：Specialist 任务分发表

### workflow_agent（10 任务）

| 优先级 | 任务 ID | 任务 | 输入 Brief 要点 | 预期产出 | Gates |
|:------:|---------|------|----------------|---------|-------|
| 1 | A-001 | 结构准备工作流 | CIF 解析能力审计 | `workflows/mof_prep.py` | UNIT+LINT |
| 2 | C-005 | 手性判定描述符 | A-001 的 STRU 解析代码 | `chirality/detector.py` | UNIT+LINT |
| 3 | A-002 | 几何优化工作流 | A-001 的结构文件 | `workflows/relax.py` | UNIT+LINT |
| 4 | A-003 | 声子稳定性 | A-002 的优化结构 | `workflows/phonon.py` | UNIT+LINT |
| 5 | A-006 | 弹性性质 | A-002 的优化结构 | `workflows/elastic.py` | UNIT+LINT |
| 6 | A-005 | MD 热力学稳定性 | A-004 的 DP 势 | `workflows/md_stability.py` | UNIT+LINT |
| 7 | D-003 | DeePTB→PYATB 计算 | B-002+B-003+D-002 产出 | `workflows/deeptb_pyatb.py` | UNIT+LINT |
| 8 | E-001 | 端到端验证 | 全链路产出 | 验证报告 + 对比数据 | UNIT+NUMERIC |
| 9 | E-002 | abacustest 集成 | E-001 的参考值 | abacustest 配置 | UNIT+LINT |

### algorithm_agent（8 任务）

| 优先级 | 任务 ID | 任务 | 输入 Brief 要点 | 预期产出 | Gates |
|:------:|---------|------|----------------|---------|-------|
| 1 | C-001 | CD 谱调研 | ABACUS LR-TDDFT 源码分析 | 技术路线报告 | UNIT+LINT |
| 2 | A-004 | MLP 训练 | A-002 的弛豫轨迹 | DP-GEN 工作流 + DP 势 | UNIT+LINT |
| 3 | B-002 | 拓扑性质 | B-001 的 H(R)/S(R) | PYATB 配置 + 计算脚本 | UNIT+LINT |
| 4 | B-003 | 光学性质 | B-001 的 H(R)/S(R) | σ(ω) 计算脚本 | UNIT+LINT |
| 5 | B-004 | SHG 非线性光学 | B-001 的 H(R)/S(R) | SHG 张量计算 | UNIT+LINT |
| 6 | D-001 | DeePTB 数据准备 | B-001 的 SCF 输出 | dftio 转换脚本 | UNIT+LINT |
| 7 | C-003 | CD 谱计算 | C-002 的磁偶极代码 | R_n + Δε(ω) 计算 | UNIT+LINT |
| 8 | D-002 | DeePTB 训练 | D-001 的训练数据 | 训练后模型 + 验证 | UNIT+LINT |
| 9 | C-004 | VCD 振动 CD | A-003 声子 + C-002 磁偶极 | VCD 可行性/实现 | UNIT+LINT |

### core_cpp_agent（1 任务，**最高风险**）

| 优先级 | 任务 ID | 任务 | 输入 Brief 要点 | 预期产出 | Gates |
|:------:|---------|------|----------------|---------|-------|
| 1 | C-002 | 磁偶极跃迁矩阵元 | C-001 调研结论 + velocity_op 源码 | `velocity_op.cpp` 修改 + `lr_spectrum.h` 扩展 | BUILD+UNIT+LINT+CONTRACT |

### infra_agent（1 任务）

| 优先级 | 任务 ID | 任务 | 输入 Brief 要点 | 预期产出 | Gates |
|:------:|---------|------|----------------|---------|-------|
| 1 | B-001 | SOC 自洽计算 | A-002 的优化结构 | INPUT 模板 + 输出验证脚本 | UNIT+LINT |

---

## 表 6：风险与阻塞追踪

| 风险 ID | 关联任务 | 类型 | 描述 | 影响范围 | 缓解策略 | 状态 |
|---------|---------|------|------|---------|---------|------|
| R-001 | C-001 | 技术决策 | CD 谱实现：ABACUS C++ vs PYATB Python | C-002, C-003, C-004 | 先完成 C-001 调研再启动后续 | 待调研 |
| R-002 | C-002 | 开发风险 | Core C++ 修改可能破坏 ABACUS 构建 | C-003, C-004 | 4-gate 验证（含 BUILD+CONTRACT） | 待开发 |
| R-003 | B-001 | 性能 | 100+ 原子 SOC 计算可能不可行 | B-002~B-004, D-001 | DeePTB 加速路线（D 系列）作备选 | 待评估 |
| R-004 | A-004 | 适用性 | DP 截断半径对 MOF 孔道相互作用的覆盖度 | A-005 | 测试不同截断半径；对比 AIMD | 待调研 |
| R-005 | C-004 | 外部依赖 | DFPT 模块未合入 ABACUS 主线 | C-004 | 降级为有限差分方案或推迟 | **高风险** |
| R-006 | D-002 | 精度 | DeePTB 多元素 MOF 模型可能不收敛 | D-003 | 对比 DFT 验证；必要时回退全 DFT | 待验证 |
| R-007 | E-001 | 集成 | 全链路首次跑通可能遇到格式/接口问题 | E-002 | 分段验证各接口 | 待集成 |

---

## 表 7：Integration Validation 检查点

| 里程碑 | 触发条件 | 覆盖任务 | 验证内容 | 通过标准 |
|--------|---------|---------|---------|---------|
| M-1: 结构准备 | A-001, A-002 全部 DONE | A-001, A-002 | CIF→弛豫 全流程 | 弛豫收敛（力<0.01 eV/Å） |
| M-2: 稳定性三件套 | A-003, A-005, A-006 全部 DONE | A-001~A-006 | 声子+MD+弹性 一致性 | 三项均确认稳定 |
| M-3: 电子结构 | B-001~B-004 全部 DONE | B-001~B-004 | ABACUS→PYATB 全链路 | 能带/拓扑不变量自洽 |
| M-4: 手性核心 | C-001~C-003 全部 DONE | C-001~C-003 | CD 谱正确性 | 非手性体系 R_n=0；对映体符号相反 |
| M-5: 加速路线 | D-001~D-003 全部 DONE | D-001~D-003 | DeePTB→PYATB 精度 | 能带 MAE<50meV, CD 符号一致 |
| M-FINAL | 全部 20 任务 DONE | ALL | MOF-520 全流程 | 与实验/文献定性一致 |

---

## 表 8：人工审阅决策预案

| 任务 ID | 预期审阅轮次 | 可能的 REVISE 原因 | REJECT 条件 | PAUSE 条件 |
|---------|:-----------:|-------------------|------------|-----------|
| A-001 | 1 | MOF 大胞 CIF 解析异常 | — | — |
| C-001 | 1~2 | 方案对比不充分 | — | — |
| A-002 | 1~2 | DFT+U 参数不当；vdW 校正缺失 | — | — |
| B-001 | 1~2 | SOC 参数错误；输出文件不完整 | 计算量超可行范围 | — |
| A-004 | 2~3 | 训练不收敛；截断半径不足 | — | 多元素训练失败 |
| **C-002** | **2~3** | 单位制错误；厄米性不满足；API 不兼容 | 实现方案不可行 | — |
| C-003 | 1~2 | 数值精度不足；求和规则不满足 | — | — |
| **C-004** | **1** | — | DFPT 完全不可用 | **DFPT 未就绪** |
| E-001 | 2~3 | 接口对接问题；数值偏差 | — | 上游任务质量不足 |

---

## 使用说明

**状态更新流程**:
1. `select_next_task()` 选出下一个任务 → 更新表 1 状态为 `IN_PROGRESS`
2. `specialist.execute(brief)` → 更新表 5 对应行
3. `reviewer.review()` → 更新表 1 审阅结果列 + 表 8 实际轮次
4. `gate_registry.run_all()` → 更新表 4 Gate 状态（`○`→`✅`/`❌`）
5. 任务完成 → 更新表 1 状态为 `DONE`，检查表 2 解除哪些阻塞
6. 波次完成 → 检查表 7 是否触发 Integration Validation
7. 遇到阻塞 → 更新表 6 风险状态
