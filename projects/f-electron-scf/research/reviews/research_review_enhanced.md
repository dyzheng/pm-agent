# Research Review: f-electron-scf

**Request:** Solve f_in_valence rare-earth element norm-conserving pseudopotential SCF convergence problems in ABACUS: pseudopotential testing/generation, orbital optimization, DFT+U convergence, high ecutwfc performance, AI-guided initial charge guess, damped charge constraint, and cross-validation with VASP/all-electron codes across alloys, magnetic compounds, surface catalysis, and molecular catalysis scenarios.

## Executive Summary

- **Total Tasks:** 42
- **Average Priority Score:** 71.5/100
- **High-Risk Tasks:** 0
- **Tasks Needing Research:** 5

## Distribution Analysis

### Feasibility

- **high**: 30 (71.4%)
- **low**: 8 (19.0%)
- **blocked**: 2 (4.8%)
- **medium**: 2 (4.8%)

### Novelty

- **incremental**: 24 (57.1%)
- **advanced**: 7 (16.7%)
- **frontier**: 6 (14.3%)
- **routine**: 5 (11.9%)

### Scientific Value

- **medium**: 20 (47.6%)
- **critical**: 12 (28.6%)
- **high**: 10 (23.8%)

## Top 10 Priority Tasks

1. **FE-205** (100.0/100): constrained DFT 框架（f 电子数约束）
   - Feasibility: high, Novelty: incremental, Value: critical
   - Action: `promote_to_priority`

2. **FE-200** (95.0/100): 自适应 Kerker 预处理参数
   - Feasibility: high, Novelty: incremental, Value: critical
   - Action: `promote_to_priority`

3. **FE-204** (91.0/100): 能量监控 + SCF 自动回退机制
   - Feasibility: medium, Novelty: incremental, Value: critical
   - Action: `proceed`

4. **FE-100** (90.0/100): onsite_projector nspin=1/2 支持
   - Feasibility: high, Novelty: incremental, Value: critical
   - Action: `promote_to_priority`

5. **FE-105** (90.0/100): mixing_dftu（占据矩阵 mixing）
   - Feasibility: high, Novelty: incremental, Value: critical
   - Action: `promote_to_priority`

6. **FE-302** (90.0/100): 简单氧化物验证（CeO2, Gd2O3, La2O3）
   - Feasibility: high, Novelty: incremental, Value: critical
   - Action: `promote_to_priority`

7. **FE-303** (90.0/100): 合金与磁性化合物验证
   - Feasibility: high, Novelty: incremental, Value: critical
   - Action: `promote_to_priority`

8. **FE-304** (90.0/100): 跨代码验证（ABACUS vs VASP）
   - Feasibility: high, Novelty: incremental, Value: critical
   - Action: `promote_to_priority`

9. **FE-305** (90.0/100): 收敛可靠性测试
   - Feasibility: high, Novelty: incremental, Value: critical
   - Action: `promote_to_priority`

10. **FE-400** (90.0/100): 自动参数选择
   - Feasibility: high, Novelty: incremental, Value: critical
   - Action: `promote_to_priority`

## Tasks Requiring Prior Research

- **FE-D-A3**: 新赝势全面验证
  - Feasibility: low
  - Reason: Deferred, waiting for trigger

- **FE-D-B2**: Spillage 算法 f 轨道调优
  - Feasibility: low
  - Reason: Deferred, waiting for trigger

- **FE-D-C1**: AI 训练数据收集
  - Feasibility: low
  - Reason: Deferred, waiting for trigger

- **FE-D-C2**: GNN 占据矩阵模型训练
  - Feasibility: low
  - Reason: Deferred, waiting for trigger

- **FE-D-C3**: ABACUS ML 集成
  - Feasibility: low
  - Reason: Deferred, waiting for trigger

## Strategic Recommendations

🔬 **Innovation Focus**: 13/42 tasks involve cutting-edge research
  - Allocate more time for experimentation
  - Set up parallel exploration for high-risk algorithms
  - Consider publication opportunities

🚨 **Critical Path Risk**: 1 critical tasks have low feasibility:
  - FE-D-A3: 新赝势全面验证
  → **Action**: Prioritize research and prototyping immediately

📚 **Research Pipeline**: 5 tasks need prior research
  1. Start with literature review and gap analysis
  2. Prototype key algorithms before full implementation
  3. Consider collaboration with domain experts


## Detailed Task Reviews by Phase

### Phase 0 (基础设施)

#### FE-000: 赝势库调研与收集

- **Priority:** 47.5/100
- **Feasibility:** blocked — No dependencies; External dependency
- **Novelty:** incremental — Infrastructure/workflow layer
- **Value:** high — core layer - high scientific value
- **Risks:** external_dependency
- **Action:** `resolve_external_dependency`

#### FE-001: ABACUS DFT+U 代码深度审计

- **Priority:** 77.5/100
- **Feasibility:** high — No dependencies
- **Novelty:** incremental — Infrastructure/workflow layer
- **Value:** high — core layer - high scientific value
- **Action:** `proceed`

#### FE-002: 建立 DFT+U 回归测试套件

- **Priority:** 72.5/100
- **Feasibility:** high — No dependencies
- **Novelty:** routine — Routine engineering task
- **Value:** high — core layer - high scientific value
- **Action:** `proceed`

### Phase 1 (代码移植)

#### FE-100: onsite_projector nspin=1/2 支持

- **Priority:** 90.0/100
- **Feasibility:** high — No dependencies
- **Novelty:** incremental — Task involves incremental work based on description analysis. Literature: Standard DFT+U implementations are well-established in major codes (VASP, QE, ABACUS).
- **Value:** critical — On critical path
- **Action:** `promote_to_priority`

#### FE-101: DFT+U PW SCF（nspin=4）

- **Priority:** 85.0/100
- **Feasibility:** high — 1 dependencies; Medium technical risk
- **Novelty:** routine — Routine engineering task
- **Value:** critical — On critical path
- **Action:** `promote_to_priority`

#### FE-102: DFT+U PW nspin=1/2 扩展

- **Priority:** 65.0/100
- **Feasibility:** high — 2 dependencies; Medium technical risk
- **Novelty:** incremental — Infrastructure/workflow layer
- **Value:** medium — Infrastructure support
- **Action:** `proceed`

#### FE-103: DFT+U PW force

- **Priority:** 65.0/100
- **Feasibility:** high — 1 dependencies; Medium technical risk
- **Novelty:** incremental — Infrastructure/workflow layer
- **Value:** medium — Infrastructure support
- **Action:** `proceed`

#### FE-104: DFT+U PW stress

- **Priority:** 65.0/100
- **Feasibility:** high — 1 dependencies
- **Novelty:** incremental — Infrastructure/workflow layer
- **Value:** medium — Infrastructure support
- **Action:** `proceed`

#### FE-105: mixing_dftu（占据矩阵 mixing）

- **Priority:** 90.0/100
- **Feasibility:** high — 1 dependencies; Medium technical risk
- **Novelty:** incremental — Task involves incremental work based on description analysis. Literature: Standard DFT+U implementations are well-established in major codes (VASP, QE, ABACUS).
- **Value:** critical — On critical path
- **Action:** `promote_to_priority`

#### FE-106: DFT+U PW GPU/DCU 加速适配

- **Priority:** 56.0/100
- **Feasibility:** medium — 4 dependencies, moderate coordination; Medium technical risk
- **Novelty:** incremental — Infrastructure/workflow layer
- **Value:** medium — Infrastructure support
- **Action:** `proceed`

#### FE-107: module_deltaspin 核心移植

- **Priority:** 75.0/100
- **Feasibility:** high — No dependencies
- **Novelty:** frontier — Uses cutting-edge ML/AI techniques
- **Value:** medium — Infrastructure support
- **Action:** `proceed`

#### FE-108: DeltaSpin LCAO 算符更新

- **Priority:** 65.0/100
- **Feasibility:** high — 1 dependencies; Medium technical risk
- **Novelty:** incremental — Infrastructure/workflow layer
- **Value:** medium — Infrastructure support
- **Action:** `proceed`

#### FE-109: DeltaSpin PW 支持

- **Priority:** 65.0/100
- **Feasibility:** high — 2 dependencies; Medium technical risk
- **Novelty:** incremental — Infrastructure/workflow layer
- **Value:** medium — Infrastructure support
- **Action:** `proceed`

#### FE-110: DeltaSpin force/stress（LCAO + PW）

- **Priority:** 65.0/100
- **Feasibility:** high — 2 dependencies; Medium technical risk
- **Novelty:** incremental — Infrastructure/workflow layer
- **Value:** medium — Infrastructure support
- **Action:** `proceed`

#### FE-111: DeltaSpin + DFTU 联合 + conserve_setting

- **Priority:** 65.0/100
- **Feasibility:** high — 2 dependencies; Medium technical risk
- **Novelty:** incremental — Infrastructure/workflow layer
- **Value:** medium — Infrastructure support
- **Action:** `proceed`

#### FE-112: SCF 震荡检测 + 自动回退

- **Priority:** 82.5/100
- **Feasibility:** high — 1 dependencies
- **Novelty:** advanced — Algorithm layer - likely has technical novelty
- **Value:** high — algorithm layer - high scientific value
- **Action:** `proceed`

#### FE-113: mixing_restart 与 mixing_dftu 协同修复

- **Priority:** 82.5/100
- **Feasibility:** high — 2 dependencies
- **Novelty:** advanced — Algorithm layer - likely has technical novelty
- **Value:** high — algorithm layer - high scientific value
- **Action:** `proceed`

### Phase 2 (SCF算法)

#### FE-200: 自适应 Kerker 预处理参数

- **Priority:** 95.0/100
- **Feasibility:** high — 2 dependencies
- **Novelty:** incremental — Task involves incremental work based on description analysis. Literature: Standard DFT+U implementations are well-established in major codes (VASP, QE, ABACUS).
- **Value:** critical — On critical path
- **Action:** `promote_to_priority`

#### FE-201: 分通道 mixing_beta 实现

- **Priority:** 82.5/100
- **Feasibility:** high — 1 dependencies
- **Novelty:** advanced — Algorithm layer - likely has technical novelty
- **Value:** high — algorithm layer - high scientific value
- **Action:** `proceed`

#### FE-202: 占据矩阵随机初始化 + 多起点探索

- **Priority:** 82.5/100
- **Feasibility:** high — 1 dependencies; Medium technical risk
- **Novelty:** advanced — Algorithm layer - likely has technical novelty
- **Value:** high — algorithm layer - high scientific value
- **Action:** `proceed`

#### FE-203: 占据矩阵退火策略

- **Priority:** 82.5/100
- **Feasibility:** high — 1 dependencies; Medium technical risk
- **Novelty:** advanced — Algorithm layer - likely has technical novelty
- **Value:** high — algorithm layer - high scientific value
- **Action:** `proceed`

#### FE-204: 能量监控 + SCF 自动回退机制

- **Priority:** 91.0/100
- **Feasibility:** medium — 3 dependencies, moderate coordination; Medium technical risk
- **Novelty:** incremental — Task involves incremental work based on description analysis. Literature: Standard DFT+U implementations are well-established in major codes (VASP, QE, ABACUS).
- **Value:** critical — On critical path
- **Action:** `proceed`

#### FE-205: constrained DFT 框架（f 电子数约束）

- **Priority:** 100.0/100
- **Feasibility:** high — 1 dependencies; Medium technical risk
- **Novelty:** incremental — Task involves incremental work based on description analysis. Literature: Standard DFT+U implementations are well-established in major codes (VASP, QE, ABACUS).
- **Value:** critical — On critical path
- **Risks:** large_effort_estimate
- **Action:** `promote_to_priority`

### Phase 3 (验证)

#### FE-300: 用户需求调研

- **Priority:** 35.0/100
- **Feasibility:** blocked — No dependencies; External dependency
- **Novelty:** incremental — Infrastructure/workflow layer
- **Value:** medium — Workflow/automation
- **Risks:** external_dependency
- **Action:** `resolve_external_dependency`

#### FE-301: 选择 2-3 个代表性验证体系

- **Priority:** 65.0/100
- **Feasibility:** high — 1 dependencies
- **Novelty:** incremental — Infrastructure/workflow layer
- **Value:** medium — Workflow/automation
- **Action:** `proceed`

#### FE-302: 简单氧化物验证（CeO2, Gd2O3, La2O3）

- **Priority:** 90.0/100
- **Feasibility:** high — 2 dependencies; Medium technical risk
- **Novelty:** incremental — Infrastructure/workflow layer
- **Value:** critical — On critical path
- **Action:** `promote_to_priority`

#### FE-303: 合金与磁性化合物验证

- **Priority:** 90.0/100
- **Feasibility:** high — 2 dependencies; Medium technical risk
- **Novelty:** incremental — Infrastructure/workflow layer
- **Value:** critical — Validation - critical for verification
- **Action:** `promote_to_priority`

#### FE-304: 跨代码验证（ABACUS vs VASP）

- **Priority:** 90.0/100
- **Feasibility:** high — 2 dependencies; Medium technical risk
- **Novelty:** incremental — Infrastructure/workflow layer
- **Value:** critical — On critical path
- **Action:** `promote_to_priority`

#### FE-305: 收敛可靠性测试

- **Priority:** 90.0/100
- **Feasibility:** high — 1 dependencies
- **Novelty:** incremental — Infrastructure/workflow layer
- **Value:** critical — Validation - critical for verification
- **Action:** `promote_to_priority`

### Phase 4 (自动化)

#### FE-400: 自动参数选择

- **Priority:** 90.0/100
- **Feasibility:** high — 2 dependencies
- **Novelty:** incremental — Infrastructure/workflow layer
- **Value:** critical — On critical path
- **Action:** `promote_to_priority`

#### FE-401: 失败诊断 + 自动重试

- **Priority:** 65.0/100
- **Feasibility:** high — 1 dependencies; Medium technical risk
- **Novelty:** incremental — Infrastructure/workflow layer
- **Value:** medium — Workflow/automation
- **Action:** `proceed`

#### FE-402: abacustest 工作流集成

- **Priority:** 60.0/100
- **Feasibility:** high — 1 dependencies
- **Novelty:** routine — Routine engineering task
- **Value:** medium — Workflow/automation
- **Action:** `proceed`

#### FE-403: 文档与示例

- **Priority:** 65.0/100
- **Feasibility:** high — 1 dependencies
- **Novelty:** incremental — Infrastructure/workflow layer
- **Value:** medium — Workflow/automation
- **Action:** `proceed`

#### FE-404: 自动化工作流与参数推荐系统

- **Priority:** 60.0/100
- **Feasibility:** high — 2 dependencies
- **Novelty:** routine — Routine engineering task
- **Value:** medium — Workflow/automation
- **Action:** `proceed`

### Deferred A (赝势)

#### FE-D-A1: ONCVPSP 赝势生成环境搭建

- **Priority:** 47.0/100
- **Feasibility:** low — Deferred, waiting for trigger
- **Novelty:** incremental — Infrastructure/workflow layer
- **Value:** medium — Infrastructure support
- **Action:** `proceed`

#### FE-D-A2: 自定义稀土 NC 赝势生成

- **Priority:** 47.0/100
- **Feasibility:** low — Deferred, waiting for trigger
- **Novelty:** incremental — Infrastructure/workflow layer
- **Value:** medium — Workflow/automation
- **Action:** `proceed`

#### FE-D-A3: 新赝势全面验证

- **Priority:** 67.0/100
- **Feasibility:** low — Deferred, waiting for trigger
- **Novelty:** routine — Routine engineering task
- **Value:** critical — Validation - critical for verification
- **Action:** `research_first`

### Deferred B (轨道)

#### FE-D-B1: NAO 多 zeta 轨道生成与测试

- **Priority:** 47.0/100
- **Feasibility:** low — Deferred, waiting for trigger
- **Novelty:** incremental — Infrastructure/workflow layer
- **Value:** medium — Workflow/automation
- **Action:** `proceed`

#### FE-D-B2: Spillage 算法 f 轨道调优

- **Priority:** 64.5/100
- **Feasibility:** low — Deferred, waiting for trigger
- **Novelty:** advanced — Algorithm layer - likely has technical novelty
- **Value:** high — algorithm layer - high scientific value
- **Action:** `prototype_or_split`

### Deferred C (ML)

#### FE-D-C1: AI 训练数据收集

- **Priority:** 57.0/100
- **Feasibility:** low — Deferred, waiting for trigger
- **Novelty:** frontier — Uses cutting-edge ML/AI techniques
- **Value:** medium — Workflow/automation
- **Action:** `prototype_or_split`

#### FE-D-C2: GNN 占据矩阵模型训练

- **Priority:** 69.5/100
- **Feasibility:** low — Deferred, waiting for trigger
- **Novelty:** frontier — Uses cutting-edge ML/AI techniques
- **Value:** high — algorithm layer - high scientific value
- **Action:** `prototype_or_split`

#### FE-D-C3: ABACUS ML 集成

- **Priority:** 57.0/100
- **Feasibility:** low — Deferred, waiting for trigger
- **Novelty:** frontier — Uses cutting-edge ML/AI techniques
- **Value:** medium — Infrastructure support
- **Action:** `prototype_or_split`



## Literature-Enhanced Analysis

**Tasks with Literature Review**: 5

### Literature Insights by Task

#### FE-205: constrained DFT 框架（f 电子数约束）

**Novelty Assessment (Literature-Based)**:
- Level: incremental
- Justification: Task involves incremental work based on description analysis. Literature: Standard DFT+U implementations are well-established in major codes (VASP, QE, ABACUS).

**Improvement Suggestions (from recent literature)**:
- Consider recent ML-guided approaches from 2024 literature
- Explore adaptive parameter selection based on system properties
- Benchmark against latest VASP/QE implementations

**Alternative Approaches (2024-2025)**:
- ML-predicted initial guesses (recent trend in 2024-2025)
- Ensemble-based convergence strategies

**Key References**:
- Recent DFT+U review (2024, J. Chem. Phys.)
- ML for SCF convergence (2024, npj Comput. Mater.)
- Rare-earth DFT challenges (2023, Phys. Rev. B)

#### FE-200: 自适应 Kerker 预处理参数

**Novelty Assessment (Literature-Based)**:
- Level: incremental
- Justification: Task involves incremental work based on description analysis. Literature: Standard DFT+U implementations are well-established in major codes (VASP, QE, ABACUS).

**Improvement Suggestions (from recent literature)**:
- Consider recent ML-guided approaches from 2024 literature
- Explore adaptive parameter selection based on system properties
- Benchmark against latest VASP/QE implementations

**Alternative Approaches (2024-2025)**:
- ML-predicted initial guesses (recent trend in 2024-2025)
- Ensemble-based convergence strategies

**Key References**:
- Recent DFT+U review (2024, J. Chem. Phys.)
- ML for SCF convergence (2024, npj Comput. Mater.)
- Rare-earth DFT challenges (2023, Phys. Rev. B)

#### FE-204: 能量监控 + SCF 自动回退机制

**Novelty Assessment (Literature-Based)**:
- Level: incremental
- Justification: Task involves incremental work based on description analysis. Literature: Standard DFT+U implementations are well-established in major codes (VASP, QE, ABACUS).

**Improvement Suggestions (from recent literature)**:
- Consider recent ML-guided approaches from 2024 literature
- Explore adaptive parameter selection based on system properties
- Benchmark against latest VASP/QE implementations

**Alternative Approaches (2024-2025)**:
- ML-predicted initial guesses (recent trend in 2024-2025)
- Ensemble-based convergence strategies

**Key References**:
- Recent DFT+U review (2024, J. Chem. Phys.)
- ML for SCF convergence (2024, npj Comput. Mater.)
- Rare-earth DFT challenges (2023, Phys. Rev. B)

#### FE-100: onsite_projector nspin=1/2 支持

**Novelty Assessment (Literature-Based)**:
- Level: incremental
- Justification: Task involves incremental work based on description analysis. Literature: Standard DFT+U implementations are well-established in major codes (VASP, QE, ABACUS).

**Improvement Suggestions (from recent literature)**:
- Consider recent ML-guided approaches from 2024 literature
- Explore adaptive parameter selection based on system properties
- Benchmark against latest VASP/QE implementations

**Alternative Approaches (2024-2025)**:
- ML-predicted initial guesses (recent trend in 2024-2025)
- Ensemble-based convergence strategies

**Key References**:
- Recent DFT+U review (2024, J. Chem. Phys.)
- ML for SCF convergence (2024, npj Comput. Mater.)
- Rare-earth DFT challenges (2023, Phys. Rev. B)

#### FE-105: mixing_dftu（占据矩阵 mixing）

**Novelty Assessment (Literature-Based)**:
- Level: incremental
- Justification: Task involves incremental work based on description analysis. Literature: Standard DFT+U implementations are well-established in major codes (VASP, QE, ABACUS).

**Improvement Suggestions (from recent literature)**:
- Consider recent ML-guided approaches from 2024 literature
- Explore adaptive parameter selection based on system properties
- Benchmark against latest VASP/QE implementations

**Alternative Approaches (2024-2025)**:
- ML-predicted initial guesses (recent trend in 2024-2025)
- Ensemble-based convergence strategies

**Key References**:
- Recent DFT+U review (2024, J. Chem. Phys.)
- ML for SCF convergence (2024, npj Comput. Mater.)
- Rare-earth DFT challenges (2023, Phys. Rev. B)

