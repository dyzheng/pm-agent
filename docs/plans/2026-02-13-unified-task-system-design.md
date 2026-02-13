# f-electron-scf 统一任务体系设计

**日期：** 2026-02-13
**目的：** 合并 PR/T/D 和 FE 两套任务 ID 体系为统一的 FE 编号系统

---

## 1. 背景

项目存在两套并行的任务体系：

- **PR/T/D 体系**（project_state.json）：38 个任务，含 14 个细粒度 PR、defer-by-default 策略
- **FE 体系**（f_electron_scf_tasks.json）：20 个任务，系统化编号、详细描述

两套体系覆盖范围不同、ID 不互通、状态不同步，导致看板无法准确反映项目进展。

## 2. 统一方案

以 FE 系统化编号为骨架，吸收 PR/T/D 的细粒度拆分和 defer 策略。

### ID 编号规则

```
FE-0xx   Phase 0: 基础设施与调研
FE-1xx   Phase 1: 代码移植（zdy-tmp → develop）
FE-2xx   Phase 2: SCF 收敛算法改进
FE-3xx   Phase 3: 验证与用户场景
FE-4xx   Phase 4: 生产就绪自动化
FE-D-Axx 延迟: 自定义赝势生成
FE-D-Bxx 延迟: NAO 轨道优化
FE-D-Cxx 延迟: ML 模型
```

### 状态定义

| 状态 | 含义 |
|---|---|
| pending | 未开始 |
| in_progress | 正在执行 |
| in_review | 代码已提交，验收未通过 |
| done | 已完成验收 |
| deferred | 延迟执行，等待触发条件 |
| blocked | 被依赖阻塞 |

## 3. 完整任务清单

### Phase 0: 基础设施与调研（3 个任务）

| ID | 标题 | 依赖 | 状态 |
|---|---|---|---|
| FE-000 | 赝势库调研与收集 | — | pending |
| FE-001 | ABACUS DFT+U 代码深度审计 | — | pending |
| FE-002 | 建立 DFT+U 回归测试套件 | — | pending |

### Phase 1: 代码移植 zdy-tmp → develop（14 个任务）

| ID | 原 PR | 标题 | 依赖 | 状态 |
|---|---|---|---|---|
| FE-100 | PR-1 | onsite_projector nspin=1/2 支持 | — | in_review |
| FE-101 | PR-2 | DFT+U PW SCF（nspin=4） | FE-100 | pending |
| FE-102 | PR-3 | DFT+U PW nspin=1/2 扩展 | FE-100, FE-101 | pending |
| FE-103 | PR-4 | DFT+U PW force | FE-101 | pending |
| FE-104 | PR-5 | DFT+U PW stress | FE-103 | pending |
| FE-105 | PR-6 | mixing_dftu（占据矩阵 mixing） | FE-101 | pending |
| FE-106 | PR-7 | DFT+U PW GPU/DCU 加速适配 | FE-101, FE-102, FE-103, FE-104 | pending |
| FE-107 | PR-8 | module_deltaspin 核心移植 | — | pending |
| FE-108 | PR-9 | DeltaSpin LCAO 算符更新 | FE-107 | pending |
| FE-109 | PR-10 | DeltaSpin PW 支持 | FE-100, FE-107 | pending |
| FE-110 | PR-11 | DeltaSpin force/stress（LCAO + PW） | FE-108, FE-109 | pending |
| FE-111 | PR-12 | DeltaSpin + DFTU 联合 + conserve_setting | FE-105, FE-108 | pending |
| FE-112 | PR-13 | SCF 震荡检测 + 自动回退 | FE-105 | pending |
| FE-113 | PR-14 | mixing_restart 与 mixing_dftu 协同 | FE-105, FE-112 | pending |

### Phase 2: SCF 收敛算法改进（6 个任务）

| ID | 标题 | 依赖 | 状态 |
|---|---|---|---|
| FE-200 | 自适应 Kerker 预处理参数 | FE-001, FE-105 | pending |
| FE-201 | 分通道 mixing_beta 实现 | FE-001 | pending |
| FE-202 | 占据矩阵随机初始化 + 多起点探索 | FE-001 | pending |
| FE-203 | 占据矩阵退火策略 | FE-202 | pending |
| FE-204 | 能量监控 + SCF 自动回退机制 | FE-200, FE-201, FE-203 | pending |
| FE-205 | constrained DFT 框架（f 电子数约束） | FE-204 | pending |

### Phase 3: 验证与用户场景（6 个任务）

| ID | 标题 | 依赖 | 状态 |
|---|---|---|---|
| FE-300 | 用户需求调研 | — | pending |
| FE-301 | 选择 2-3 个代表性验证体系 | FE-300 | pending |
| FE-302 | 简单氧化物验证（CeO2, Gd2O3, La2O3） | FE-000, FE-204 | pending |
| FE-303 | 合金与磁性化合物验证 | FE-302, FE-204 | pending |
| FE-304 | 跨代码验证（ABACUS vs VASP） | FE-302, FE-301 | pending |
| FE-305 | 收敛可靠性测试 | FE-304 | pending |

### Phase 4: 生产就绪自动化（5 个任务）

| ID | 标题 | 依赖 | 状态 |
|---|---|---|---|
| FE-400 | 自动参数选择 | FE-304, FE-305 | pending |
| FE-401 | 失败诊断 + 自动重试 | FE-400 | pending |
| FE-402 | abacustest 工作流集成 | FE-400 | pending |
| FE-403 | 文档与示例 | FE-400 | pending |
| FE-404 | 自动化工作流与参数推荐系统 | FE-401, FE-403 | pending |

### 延迟任务（8 个）

| ID | 标题 | 触发条件 | 状态 |
|---|---|---|---|
| FE-D-A1 | ONCVPSP 赝势生成环境搭建 | FE-304:accuracy_below_threshold | deferred |
| FE-D-A2 | 自定义稀土 NC 赝势生成 | FE-D-A1:completed | deferred |
| FE-D-A3 | 新赝势全面验证 | FE-D-A2:completed | deferred |
| FE-D-B1 | NAO 多 zeta 轨道生成与测试 | FE-304:lcao_divergence_above_3pct | deferred |
| FE-D-B2 | Spillage 算法 f 轨道调优 | FE-D-B1:spillage_issue_detected | deferred |
| FE-D-C1 | AI 训练数据收集 | FE-202:failure_rate_above_20pct | deferred |
| FE-D-C2 | GNN 占据矩阵模型训练 | FE-D-C1:completed | deferred |
| FE-D-C3 | ABACUS ML 集成 | FE-D-C2:completed | deferred |

## 4. 关键路径

```
FE-100 → FE-101 → FE-105 → FE-200/201/202 → FE-204 → FE-205 → FE-302 → FE-304 → FE-400
```

## 5. 并行机会

- FE-000 || FE-001 || FE-002（Phase 0 全部可并行）
- FE-100 || FE-107（onsite_projector 与 deltaspin 核心可并行）
- FE-200 || FE-201 || FE-202（Phase 2 前三个可并行）
- FE-300 || FE-301（用户调研与验证体系选择可提前启动）

## 6. 与旧 ID 的映射表

| 新 ID | PR/T/D ID | 旧 FE ID | 说明 |
|---|---|---|---|
| FE-000 | T0-4 | FE-000 | 赝势收集 |
| FE-001 | — | FE-002 | 代码审计 |
| FE-002 | — | — | 新增：回归测试 |
| FE-100~113 | PR-1~14 | — | 代码移植（新增整段） |
| FE-200~205 | T1-1~T1-4, T2-1~T2-3 | FE-200~205 | SCF 算法（保留 FE 编号） |
| FE-300~305 | T3-1~T3-4 | FE-400~403 | 验证（合并重编号） |
| FE-400~404 | T4-1~T4-4 | FE-500 | 自动化（重编号） |
| FE-D-* | D-A/B/C | FE-001,100~103,300~302 | 延迟任务 |

## 7. 统计

- 总任务数：42
- 活跃任务：34（Phase 0~4）
- 延迟任务：8
- 已有进展：1（FE-100 in_review）
- 预计时间：5-6 个月
