# Brainstorm Hook 完整工作流程演示

**日期：** 2026-02-11
**目的：** 展示brainstorm hook从设计到实际应用的完整流程

---

## 工作流程概览

```
用户需求 → Brainstorm对话 → 任务分解 → 风险识别 → 任务延迟 → 触发执行
```

---

## 第一步：用户需求

**原始需求（中文）：**
```
我现在有一个新的算法研究项目需要做，稀土f电子模守恒赝势SCF收敛问题。
需要：赝势生成、轨道优化、DFT+U收敛、AI辅助初猜、约束DFT等。

问题：赝势生成是高风险且不可控的，应该先完成收敛策略优化和测试工作流，
只有在测试精度不足或赝势泛化性不够时才引入赝势生成。
SCF收敛策略应该是高优先级。

能否优化代码规则，引入这种反馈迭代过程，并触发确认任务调整方法？
```

**关键洞察：**
- 赝势生成是高风险任务（external dependency）
- 应该先做收敛算法，后做赝势生成
- 需要反馈驱动的任务调整机制

---

## 第二步：Brainstorm对话

### 问题1：赝势策略

**问题：** 赝势生成作为Phase 1阻塞任务，但你提到这是高风险且不可控。哪种方法更合理？

**选项：**
- A) 使用现有赝势库，按需生成 ✓
- B) Phase 1优先生成自定义赝势
- C) 并行开发

**用户选择：** A

**理由：** 解耦算法开发和赝势不确定性

### 问题2：AI初猜优先级

**问题：** AI辅助初猜在Phase 3，但这创建了长关键路径。你的优先级是？

**选项：**
- A) 完全延迟AI工作
- B) Phase 3保持
- C) 规则启发式先行，ML延迟 ✓

**用户选择：** C

**理由：** 简单规则可能已足够，避免过早ML

### 问题3：NAO轨道优化

**问题：** NAO生成在Phase 1，但需要大量计算测试。如何处理？

**选项：**
- A) 延迟到PW收敛后
- B) Phase 1保持
- C) 使用默认DZP设置 ✓

**用户选择：** C

**理由：** 避免过早优化

### 问题4：DFT+U开发节奏

**问题：** 4个DFT+U功能串行开发。策略？

**选项：**
- A) 全部实现
- B) 增量验证 ✓
- C) 只做最高影响功能

**用户选择：** B

**理由：** 每个功能验证后再开发下一个

### 问题5：验证范围

**问题：** 6个验证场景覆盖全面，但可能过度。策略？

**选项：**
- A) 2-3代表系统
- B) 全6场景
- C) 用户需求驱动 ✓

**用户选择：** C

**理由：** 实际需求优先

### 问题6：时间线

**问题：** 原计划7-9个月。基于延迟策略，目标时间线？

**选项：**
- A) 3-4个月
- B) 5-6个月 ✓
- C) 7-9个月

**用户选择：** B

**理由：** 平衡速度和生产就绪

---

## 第三步：任务分解

### 原始任务列表（21个）

```
Phase 0: 基础设施
  T0-A: 赝势库调研
  T0-B: ONCVPSP环境搭建
  T0-C: DFT+U代码审计

Phase 1: 赝势与轨道
  T1-A: 稀土NC赝势生成 ← 阻塞一切
  T1-B: 赝势质量验证
  T1-C: NAO轨道生成
  T1-D: 轨道质量评估

Phase 2: SCF收敛算法
  T2-A: 自适应Kerker
  T2-B: 分通道mixing
  T2-C: 占据矩阵随机初始化
  T2-D: 占据退火
  T2-E: 能量监控回退
  T2-F: Constrained DFT

Phase 3: AI辅助初猜
  T3-A: 训练数据收集
  T3-B: 模型训练
  T3-C: ABACUS集成

Phase 4: 验证
  T4-A: 简单氧化物
  T4-B: 合金
  T4-C: 磁性化合物
  T4-D: 表面催化
  T4-E: 分子催化
  T4-F: 全场景综合

Phase 5: 工作流
  T5-A: 自动参数选择
  T5-B: 失败诊断
  T5-C: 文档
```

### 优化后任务列表（27个）

**活跃任务（19个）：**

```python
# Phase 0: 代码集成（新增）
Task(id="T0-1", title="合并PW+LCAO DFT+U代码", status=PENDING, risk="low")
Task(id="T0-2", title="重构为可插拔架构", status=PENDING, risk="low")
Task(id="T0-3", title="建立回归测试", status=PENDING, risk="low")
Task(id="T0-4", title="收集现有赝势", status=PENDING, risk="low")

# Phase 1: 基础收敛改进
Task(id="T1-1", title="自适应Kerker", status=PENDING, risk="low")
Task(id="T1-2", title="分通道mixing", status=PENDING, risk="low")
Task(id="T1-3", title="能量监控回退", status=PENDING, risk="low")
Task(id="T1-4", title="规则启发式占据", status=PENDING, risk="low")

# Phase 2: DFT+U策略（增量验证）
Task(id="T2-1", title="随机占据初始化", status=PENDING, risk="medium")
Task(id="T2-2", title="占据退火", status=PENDING, risk="medium",
     defer_trigger="T2-1:validation_passed")
Task(id="T2-3", title="Constrained DFT", status=PENDING, risk="medium",
     defer_trigger="T2-1:insufficient OR T2-2:insufficient")

# Phase 3: 用户场景验证
Task(id="T3-1", title="用户需求调研", status=PENDING, risk="low")
Task(id="T3-2", title="选择验证体系", status=PENDING, risk="low")
Task(id="T3-3", title="跨代码验证", status=PENDING, risk="medium")
Task(id="T3-4", title="收敛可靠性测试", status=PENDING, risk="low")

# Phase 4: 生产自动化
Task(id="T4-1", title="自动参数选择", status=PENDING, risk="low")
Task(id="T4-2", title="失败诊断重试", status=PENDING, risk="medium")
Task(id="T4-3", title="abacustest集成", status=PENDING, risk="low")
Task(id="T4-4", title="文档与示例", status=PENDING, risk="low")
```

**延迟任务（8个）：**

```python
# Category A: 自定义赝势生成
Task(id="D-A1", title="ONCVPSP环境搭建", status=DEFERRED, risk="high",
     defer_trigger="T3-3:accuracy_below_threshold")
Task(id="D-A2", title="自定义赝势生成", status=DEFERRED, risk="high",
     defer_trigger="D-A1:completed")
Task(id="D-A3", title="新赝势验证", status=DEFERRED, risk="high",
     defer_trigger="D-A2:completed")

# Category B: NAO优化
Task(id="D-B1", title="NAO多zeta生成", status=DEFERRED, risk="medium",
     defer_trigger="T3-3:lcao_divergence_above_3pct")
Task(id="D-B2", title="Spillage算法调优", status=DEFERRED, risk="medium",
     defer_trigger="D-B1:spillage_issue_detected")

# Category C: ML模型
Task(id="D-C1", title="ML训练数据收集", status=DEFERRED, risk="high",
     defer_trigger="T1-4:failure_rate_above_20pct")
Task(id="D-C2", title="GNN模型训练", status=DEFERRED, risk="high",
     defer_trigger="D-C1:completed")
Task(id="D-C3", title="ABACUS ML集成", status=DEFERRED, risk="high",
     defer_trigger="D-C2:completed")
```

---

## 第四步：风险识别

### 自动风险检测

```python
from src.brainstorm import flag_risky_tasks

# 运行风险检测
questions = flag_risky_tasks(
    state,
    checks=["external_dependency", "high_uncertainty", "long_critical_path"],
    keywords=["generate", "生成", "optimize", "优化"],
    threshold=3
)

# 结果：8个任务被标记
# - D-A1, D-A2, D-A3: external_dependency (赝势生成)
# - D-B1, D-B2: high_uncertainty (NAO优化)
# - D-C1, D-C2, D-C3: external_dependency + high_uncertainty (ML)
```

### 风险分析

| 任务 | 风险类型 | 风险原因 | 阻塞任务数 |
|---|---|---|---|
| D-A1 | external_dependency | 依赖ONCVPSP工具 | 2 |
| D-A2 | external_dependency | 赝势质量不确定 | 1 |
| D-B1 | high_uncertainty | 不确定是否需要 | 1 |
| D-C1 | external_dependency | 需要大量数据 | 2 |
| D-C2 | high_uncertainty | 模型效果未知 | 1 |

---

## 第五步：任务延迟

### 延迟操作

```python
from src.brainstorm import defer_task

# 延迟赝势生成任务
deferred = defer_task(
    state,
    task_id="D-A1",
    trigger="T3-3:accuracy_below_threshold"
)
# 返回: ["D-A1"]（D-A2, D-A3通过依赖链自动延迟）

# 延迟ML任务
deferred = defer_task(
    state,
    task_id="D-C1",
    trigger="T1-4:failure_rate_above_20pct"
)
# 返回: ["D-C1"]
```

### 依赖处理

```python
# 原始依赖
T3-3.dependencies = ["T1-1", "T1-2", "T1-3", "T1-4", "T2-1", "T3-2"]

# 延迟D-A1后（假设T3-3依赖D-A1）
# T3-3.dependencies = ["T1-1", "T1-2", "T1-3", "T1-4", "T2-1", "T3-2"]
# T3-3.suspended_dependencies = []  # D-A1不在依赖中
# T3-3.original_dependencies = []

# 实际上D-A1是独立的，不影响T3-3
# T3-3可以使用现有赝势运行
```

---

## 第六步：执行与触发

### 执行流程

```python
from src.phases.execute import run_execute_verify
from src.brainstorm import check_deferred_triggers

# 1. 执行Phase 0-1任务
for task in ["T0-1", "T0-2", "T0-3", "T0-4", "T1-1", "T1-2", "T1-3", "T1-4"]:
    # 执行任务...
    task.status = TaskStatus.DONE

    # 检查触发
    promoted = check_deferred_triggers(state, task.id)
    if promoted:
        print(f"Promoted: {promoted}")

# 2. 执行Phase 2任务（增量验证）
# T2-1: 随机占据初始化
execute_task(state, "T2-1")
validate_task(state, "T2-1")
# 如果验证通过，T2-2自动从PENDING变为可执行

# 3. 执行Phase 3验证
execute_task(state, "T3-3")  # 跨代码验证

# 检查精度
if accuracy < 0.95:  # 假设精度不足
    # 触发赝势生成
    promoted = check_deferred_triggers(state, "T3-3")
    # 返回: ["D-A1", "D-A2", "D-A3"]

    # D-A1, D-A2, D-A3现在变为PENDING
    # 可以开始执行
```

### 触发场景

**场景1：验证精度不足**
```python
# T3-3完成，精度<95%
promoted = check_deferred_triggers(state, "T3-3")
# 触发: D-A1 (赝势生成)
# 原因: T3-3:accuracy_below_threshold
```

**场景2：规则启发式失败率高**
```python
# T1-4完成，失败率>20%
promoted = check_deferred_triggers(state, "T1-4")
# 触发: D-C1 (ML数据收集)
# 原因: T1-4:failure_rate_above_20pct
```

**场景3：LCAO偏差大**
```python
# T3-3完成，LCAO vs PW偏差>3%
promoted = check_deferred_triggers(state, "T3-3")
# 触发: D-B1 (NAO优化)
# 原因: T3-3:lcao_divergence_above_3pct
```

---

## 第七步：结果对比

### 时间线对比

| 阶段 | 原计划 | 优化后 | 节省 |
|---|---|---|---|
| Phase 0 | - | 2周 | - |
| Phase 1 | 2个月 | 6周 | 2周 |
| Phase 2 | 2个月 | 6周 | 2周 |
| Phase 3 | 2个月 | 4周 | 4周 |
| Phase 4 | 1个月 | 8周 | - |
| **总计** | **7-9个月** | **5-6个月** | **~3个月** |

### 任务数对比

| 类别 | 原计划 | 优化后 |
|---|---|---|
| 活跃任务 | 21 | 19 |
| 延迟任务 | 0 | 8 |
| 总任务数 | 21 | 27 |

### 风险对比

| 风险 | 原计划 | 优化后 |
|---|---|---|
| 赝势质量不足 | 前期阻塞 | 后期按需 |
| AI模型效果差 | 后期发现 | 规则先行 |
| 过度工程 | 全部实现 | 增量验证 |
| 验证不足 | 学术完整 | 需求驱动 |

---

## 第八步：审计追踪

### BrainstormResult记录

```python
# 延迟赝势生成
BrainstormResult(
    hook_name="after_decompose",
    task_id="D-A1",
    question="High risk: external dependency (ONCVPSP tool)",
    options=["defer", "keep", "split", "drop"],
    answer="defer",
    action_taken="deferred 1 task: ['D-A1']",
    timestamp="2026-02-11T15:30:00"
)

# 延迟ML模型
BrainstormResult(
    hook_name="after_decompose",
    task_id="D-C1",
    question="High risk: external dependency + high uncertainty",
    options=["defer", "keep", "split", "drop"],
    answer="defer",
    action_taken="deferred 1 task: ['D-C1']",
    timestamp="2026-02-11T15:31:00"
)

# 提升赝势生成（假设触发）
BrainstormResult(
    hook_name="after_task_complete",
    task_id="T3-3",
    question="Validation accuracy below threshold?",
    options=["promote", "keep_deferred"],
    answer="promote",
    action_taken="promoted 3 tasks: ['D-A1', 'D-A2', 'D-A3']",
    timestamp="2026-03-15T10:30:00"
)
```

---

## 完整代码示例

### 1. 初始化项目

```python
from src.state import ProjectState, Phase

# 创建项目状态
state = ProjectState(
    request="Solve f_in_valence rare-earth SCF convergence...",
    project_id="f-electron-scf",
    phase=Phase.INTAKE
)
```

### 2. 运行Pipeline（含Brainstorm）

```python
from src.pipeline import run_pipeline
from src.hooks import HookConfig

# 加载hook配置
hook_config = HookConfig.load("hooks.yaml")

# 运行pipeline
state = run_pipeline(
    state,
    hook_config=hook_config,
    input_fn=input  # Interactive模式
)

# Brainstorm会在after_decompose自动触发
# 用户交互式决策：defer/keep/split/drop
```

### 3. 执行任务

```python
from src.phases.execute import run_execute_verify
from src.specialist import WorktreeSpecialist
from src.phases.verify import GateRegistry
from src.review import MockReviewer

# 执行任务
state = run_execute_verify(
    state,
    specialist=WorktreeSpecialist(...),
    gate_registry=GateRegistry(...),
    reviewer=MockReviewer(),
    integration_runner=...,
    worktree_mgr=...,
    hook_config=hook_config
)

# 自动检查延迟触发
# 自动提升满足条件的延迟任务
```

### 4. 保存状态

```python
# 保存完整状态
state.save("projects/f-electron-scf/state/project_state.json")

# 查看brainstorm结果
for result in state.brainstorm_results:
    print(f"{result.task_id}: {result.action_taken}")
```

---

## 关键收获

### 1. YAGNI原则的威力

**不要实现你不确定需要的功能**

- 赝势生成：可能现有库已足够
- NAO优化：可能默认设置已足够
- AI模型：可能规则启发式已足够

**策略：** 延迟到验证显示确实需要时再实现

### 2. 风险驱动的价值

**高风险任务特征：**
- 依赖外部工具/数据
- 结果不确定
- 阻塞大量下游任务

**策略：** 延迟高风险任务，优先低风险任务

### 3. 增量验证的重要性

**传统：** 实现所有功能 → 一次性验证
**增量：** 实现一个 → 验证 → 决定下一步

**优势：**
- 早期发现问题
- 避免无效工作
- 保持灵活性

### 4. 用户需求优先

**学术陷阱：** 覆盖所有可能场景
**实际需求：** 只覆盖用户真正需要的

**策略：** 先调研需求，再选择验证

---

## 总结

Brainstorm hook系统通过风险驱动的任务延迟策略，成功将f-electron-scf项目从7-9个月优化到5-6个月，节省约40%时间。

**核心流程：**
1. 用户需求 → 识别高风险任务
2. Brainstorm对话 → 确定延迟策略
3. 任务分解 → 活跃任务 + 延迟任务
4. 风险检测 → 自动标记风险任务
5. 任务延迟 → 设置触发条件
6. 执行验证 → 检查触发条件
7. 动态提升 → 按需执行延迟任务
8. 审计追踪 → 记录所有决策

**关键价值：**
- 降低项目风险
- 缩短交付时间
- 提高决策质量
- 保持计划灵活性

**准备就绪：** 可以在更多项目中推广使用。
