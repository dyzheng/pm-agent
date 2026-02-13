# f-electron-scf Project

**稀土f电子模守恒赝势SCF收敛问题 — 统一任务体系**

## 项目概述

解决ABACUS中稀土元素（f_in_valence）模守恒赝势的SCF收敛问题，覆盖合金、磁性化合物、表面催化、分子催化等场景。

**策略：** 风险驱动的延迟执行（defer-by-default）

## 关键指标

- **总任务数：** 42个
- **活跃任务：** 34个
- **延迟任务：** 8个（触发条件满足时执行）
- **预计时间：** 5-6个月

## ID 编号规则

```
FE-0xx   Phase 0: 基础设施与调研
FE-1xx   Phase 1: 代码移植（zdy-tmp → develop，14个PR）
FE-2xx   Phase 2: SCF 收敛算法改进
FE-3xx   Phase 3: 验证与用户场景
FE-4xx   Phase 4: 生产就绪自动化
FE-D-Axx 延迟: 自定义赝势生成
FE-D-Bxx 延迟: NAO 轨道优化
FE-D-Cxx 延迟: ML 模型
```

## 快速开始

### 查看可视化看板

```bash
cd /root/pm-agent/projects/f-electron-scf
python3 -m http.server 8080
# 浏览器打开 http://localhost:8080/dashboard.html
```

### 重建项目状态

```bash
cd state
python3 build_state.py
```

### 更新任务状态

编辑对应的 `state/tasks_phase*.json` 文件，然后运行 `python3 state/build_state.py` 重建。

## 目录结构

```
f-electron-scf/
├── README.md
├── dashboard.html                    # 交互式可视化看板
├── DASHBOARD_GUIDE.md
├── project.json
├── plans/
│   ├── 2026-02-11-f-electron-scf-analysis.md
│   ├── 2026-02-11-brainstorm-refined-plan.md
│   ├── 2026-02-12-zdy-tmp-refactor-merge-design.md
│   ├── review-and-testing-spec.md
│   └── ...
└── state/
    ├── project_state.json            # 完整状态（自动生成，勿手动编辑）
    ├── project_state_meta.json       # 元数据与统计
    ├── build_state.py                # 状态构建脚本
    ├── tasks_phase0.json             # FE-0xx
    ├── tasks_phase1a.json            # FE-100~106
    ├── tasks_phase1b.json            # FE-107~113
    ├── tasks_phase2.json             # FE-2xx
    ├── tasks_phase3.json             # FE-3xx
    ├── tasks_phase4.json             # FE-4xx
    └── tasks_deferred.json           # FE-D-*
```

## 任务概览

### Phase 0: 基础设施与调研（3个任务）
- FE-000: 赝势库调研与收集
- FE-001: ABACUS DFT+U 代码深度审计
- FE-002: 建立 DFT+U 回归测试套件

### Phase 1: 代码移植 zdy-tmp → develop（14个任务）
- FE-100: onsite_projector nspin=1/2 支持 **[🔍 审核中]**
- FE-101: DFT+U PW SCF（nspin=4）
- FE-102: DFT+U PW nspin=1/2 扩展
- FE-103: DFT+U PW force
- FE-104: DFT+U PW stress
- FE-105: mixing_dftu（占据矩阵 mixing）
- FE-106: DFT+U PW GPU/DCU 加速适配
- FE-107: module_deltaspin 核心移植
- FE-108: DeltaSpin LCAO 算符更新
- FE-109: DeltaSpin PW 支持
- FE-110: DeltaSpin force/stress
- FE-111: DeltaSpin + DFTU 联合 + conserve_setting
- FE-112: SCF 震荡检测 + 自动回退
- FE-113: mixing_restart 与 mixing_dftu 协同修复

### Phase 2: SCF 收敛算法改进（6个任务）
- FE-200: 自适应 Kerker 预处理参数
- FE-201: 分通道 mixing_beta 实现
- FE-202: 占据矩阵随机初始化 + 多起点探索
- FE-203: 占据矩阵退火策略
- FE-204: 能量监控 + SCF 自动回退机制
- FE-205: constrained DFT 框架

### Phase 3: 验证与用户场景（6个任务）
- FE-300: 用户需求调研
- FE-301: 选择代表性验证体系
- FE-302: 简单氧化物验证（CeO2, Gd2O3, La2O3）
- FE-303: 合金与磁性化合物验证
- FE-304: 跨代码验证（ABACUS vs VASP）
- FE-305: 收敛可靠性测试

### Phase 4: 生产就绪自动化（5个任务）
- FE-400: 自动参数选择
- FE-401: 失败诊断 + 自动重试
- FE-402: abacustest 工作流集成
- FE-403: 文档与示例
- FE-404: 自动化工作流与参数推荐系统

### 延迟任务（8个）

**Category A: 自定义赝势生成**
- FE-D-A1: ONCVPSP 环境搭建（触发：FE-304 精度不足）
- FE-D-A2: 自定义赝势生成（触发：FE-D-A1 完成）
- FE-D-A3: 新赝势验证（触发：FE-D-A2 完成）

**Category B: NAO 优化**
- FE-D-B1: NAO 多 zeta 生成（触发：LCAO 偏差>3%）
- FE-D-B2: Spillage 算法调优（触发：FE-D-B1 发现问题）

**Category C: ML 模型**
- FE-D-C1: AI 训练数据收集（触发：规则失败率>20%）
- FE-D-C2: GNN 模型训练（触发：FE-D-C1 完成）
- FE-D-C3: ABACUS ML 集成（触发：FE-D-C2 完成）

## 里程碑

| 里程碑 | 时间 | 目标 | 门控条件 |
|---|---|---|---|
| M1 | 月1 | 架构就绪 + 基础收敛改进 | CeO2无需手动调参即可收敛 |
| M2 | 月2 | 占据矩阵策略可用 | CeO2+GdN收敛率>80% |
| M3 | 月3 | 用户场景验证通过 | ABACUS vs VASP结构误差<2% |
| M4 | 月5 | 生产就绪 | 非专家用户可成功运行 |
| M5 | 月6 | 发布 | 文档+工作流完成 |

## 关键路径

```
FE-100 → FE-101 → FE-105 → FE-200/201/202 → FE-204 → FE-205 → FE-302 → FE-304 → FE-400
```

## 执行时间线

```
Week 1:  FE-100(补测试) + FE-107 [可并行]
Week 2:  FE-101 (DFT+U PW nspin=4 SCF)
Week 3:  FE-102 + FE-103 [可并行]
Week 4:  FE-104 + FE-105 [可并行]
Week 5:  FE-108 + FE-109 [可并行]
Week 6:  FE-110 + FE-111
Week 7:  FE-106 + FE-112 + FE-113
Week 8-10:  Phase 2 (FE-200~205)
Week 11-14: Phase 3 (FE-300~305)
Week 15-20: Phase 4 (FE-400~404)
```

## 相关文档

- **统一任务体系设计：** `../../docs/plans/2026-02-13-unified-task-system-design.md`
- **Brainstorm 优化计划：** `plans/2026-02-11-brainstorm-refined-plan.md`
- **zdy-tmp 移植计划：** `plans/2026-02-12-zdy-tmp-refactor-merge-design.md`
- **PR 验收规范：** `plans/review-and-testing-spec.md`
- **看板指南：** `DASHBOARD_GUIDE.md`

---

**创建日期：** 2026-02-11
**最后更新：** 2026-02-13（统一任务体系）
**状态：** 活跃开发中
