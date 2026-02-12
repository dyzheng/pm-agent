# f-electron-scf Project

**稀土f电子模守恒赝势SCF收敛问题 - Brainstorm优化后的项目计划**

## 项目概述

解决ABACUS中稀土元素（f_in_valence）模守恒赝势的SCF收敛问题，覆盖合金、磁性化合物、表面催化、分子催化等场景。

**优化策略：** 风险驱动的延迟执行（defer-by-default）

## 关键指标

- **总任务数：** 27个
- **活跃任务：** 19个（可立即执行）
- **延迟任务：** 8个（触发条件满足时执行）
- **预计时间：** 5-6个月
- **节省时间：** 40%（相比原计划7-9个月）

## 快速开始

### 查看可视化看板

```bash
python3 -m http.server 8080
# 浏览器打开 http://localhost:8080/dashboard.html
```

### 查看项目状态

```bash
cd state
python3 build_state.py
```

### 生成依赖图

```bash
python3 generate_graph.py
dot -Tsvg dependency_graph.dot -o dependency_graph.svg
```

## 目录结构

```
f-electron-scf/
├── README.md                      # 本文件
├── dashboard.html                 # 交互式可视化看板
├── generate_graph.py              # 依赖图生成器
├── DASHBOARD_GUIDE.md             # 看板使用指南
├── dependency_graph.dot           # 依赖关系图定义
├── project.json                   # 项目元数据
├── plans/                         # 项目计划文档
│   ├── 2026-02-11-f-electron-scf-analysis.md
│   └── 2026-02-11-brainstorm-refined-plan.md
├── state/                         # 项目状态数据
│   ├── project_state.json         # 完整状态（自动生成）
│   ├── project_state_meta.json    # 元数据
│   ├── active_tasks.json          # 活跃任务
│   ├── validation_tasks.json      # 验证任务
│   ├── deferred_tasks.json        # 延迟任务
│   └── build_state.py             # 状态构建脚本
└── annotations/                   # 任务注释

```

## 任务概览

### Phase 0: 代码集成（4个任务）
- T0-1: 合并PW+LCAO DFT+U代码
- T0-2: 重构为可插拔架构
- T0-3: 建立回归测试
- T0-4: 收集现有赝势

### Phase 1: 基础收敛改进（4个任务）
- T1-1: 自适应Kerker预处理器
- T1-2: 分通道mixing_beta
- T1-3: 能量监控+自动回退
- T1-4: 规则启发式占据猜测

### Phase 2: DFT+U策略（3个任务）
- T2-1: 随机占据矩阵初始化
- T2-2: 占据退火策略（触发条件：T2-1验证通过）
- T2-3: Constrained DFT框架（触发条件：T2-1/T2-2不足）

### Phase 3: 用户场景验证（4个任务）
- T3-1: 用户需求调研
- T3-2: 选择验证体系
- T3-3: 跨代码验证（ABACUS vs VASP）
- T3-4: 收敛可靠性测试

### Phase 4: 生产就绪（4个任务）
- T4-1: 自动参数选择
- T4-2: 失败诊断+自动重试
- T4-3: abacustest工作流集成
- T4-4: 文档与示例

### 延迟任务（8个）

**Category A: 自定义赝势生成**
- D-A1: ONCVPSP环境搭建（触发：T3-3精度不足）
- D-A2: 自定义赝势生成（触发：D-A1完成）
- D-A3: 新赝势验证（触发：D-A2完成）

**Category B: NAO优化**
- D-B1: NAO多zeta生成（触发：LCAO偏差>3%）
- D-B2: Spillage算法调优（触发：D-B1发现问题）

**Category C: ML模型**
- D-C1: ML训练数据收集（触发：规则失败率>20%）
- D-C2: GNN模型训练（触发：D-C1完成）
- D-C3: ABACUS ML集成（触发：D-C2完成）

## 里程碑

| 里程碑 | 时间 | 目标 | 门控条件 |
|---|---|---|---|
| M1 | 月1 | 架构就绪 + 基础收敛改进 | CeO2无需手动调参即可收敛 |
| M2 | 月2 | 占据矩阵策略可用 | CeO2+GdN收敛率>80% |
| M3 | 月3 | 用户场景验证通过 | ABACUS vs VASP结构误差<2% |
| M4 | 月5 | 生产就绪 | 非专家用户可成功运行 |
| M5 | 月6 | 发布 | 文档+工作流完成 |

## 风险分布

- 🟢 **低风险：** 15个任务（可立即执行）
- 🟡 **中风险：** 4个任务（需要验证）
- 🔴 **高风险：** 8个任务（已延迟）

## 核心策略

### YAGNI原则
不实现不确定需要的功能，延迟到验证显示必要时再实现。

### 风险驱动
高风险任务后置，低风险任务优先，按需触发延迟任务。

### 增量验证
实现一个功能 → 验证 → 决定下一步，避免过度工程。

### 用户优先
实际需求优先于学术完整性，先调研需求再选择验证场景。

## 相关文档

- **项目计划：** `plans/2026-02-11-brainstorm-refined-plan.md`
- **技术分析：** `plans/2026-02-11-f-electron-scf-analysis.md`
- **看板指南：** `DASHBOARD_GUIDE.md`

## 与PM Agent的关系

本项目使用 [PM Agent](https://github.com/your-org/pm-agent) 的brainstorm hook系统进行任务管理：

- **风险检测：** 自动识别高风险任务
- **任务延迟：** 基于触发条件的延迟执行
- **依赖管理：** 自动处理任务依赖关系
- **可视化：** 交互式看板展示项目状态

## 贡献指南

### 更新任务状态

```bash
cd state
# 编辑对应的JSON文件
vim active_tasks.json

# 重新构建完整状态
python3 build_state.py

# 提交更改
git add .
git commit -m "Update task status: T0-1 completed"
git push
```

### 添加新任务

1. 编辑 `state/active_tasks.json` 或 `state/deferred_tasks.json`
2. 运行 `python3 state/build_state.py`
3. 刷新dashboard查看更新

### 生成依赖图

```bash
python3 generate_graph.py
dot -Tsvg dependency_graph.dot -o dependency_graph.svg
```

## 许可证

本项目遵循与ABACUS相同的许可证。

## 联系方式

- 项目负责人：[待填写]
- 技术讨论：[待填写]
- 问题追踪：GitHub Issues

---

**创建日期：** 2026-02-11
**最后更新：** 2026-02-11
**状态：** 活跃开发中
