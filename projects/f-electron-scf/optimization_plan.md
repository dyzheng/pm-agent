# f-electron-scf 项目任务优化方案

基于 claude-scholar 研究规划能力的智能任务评审结果

## 评审总结

### 整体健康度：良好 (71.5/100)

- **Total Tasks**: 42
- **Average Priority**: 71.5/100
- **High-Risk Tasks**: 0
- **Tasks Needing Research**: 5

### 分布分析

**可行性 (Feasibility)**
- ✅ High: 30 tasks (71.4%) - 大部分任务有清晰路径
- ⚠️ Low: 8 tasks (19.0%) - 主要是deferred的ML任务
- 🚫 Blocked: 2 tasks (4.8%) - 需要外部依赖
- ⚙️ Medium: 2 tasks (4.8%)

**创新性 (Novelty)**
- 🔬 Frontier: 6 tasks (14.3%) - AI/ML前沿技术
- 🚀 Advanced: 7 tasks (16.7%) - 自适应/智能算法
- ⚡ Incremental: 24 tasks (57.1%) - 增量改进
- 🔧 Routine: 5 tasks (11.9%) - 常规工程

**科学价值 (Scientific Value)**
- 🎯 Critical: 12 tasks (28.6%) - 关键路径任务
- ⭐ High: 10 tasks (23.8%) - 核心科学价值
- 📊 Medium: 20 tasks (47.6%) - 支撑性任务

---

## 关键发现

### 1. 创新任务集中在算法层 (31% frontier/advanced)

13个高创新任务需要特别关注：

**Frontier 任务 (前沿研究)**：
- FE-205: constrained DFT 框架 (100/100) ⭐ **最高优先级**
- FE-204: 能量监控 + SCF 自动回退 (91/100)
- FE-D-C2: GNN 占据矩阵模型训练 (已defer)

**Advanced 任务 (先进技术)**：
- FE-200: 自适应 Kerker 预处理 (95/100)
- FE-201: 分通道 mixing_beta (未在Top 10)
- FE-203: 占据矩阵退火策略 (未在Top 10)

**建议：**
- 为frontier任务预留30-50%的探索时间
- 建立快速原型验证机制
- 考虑发表机会（FE-205的约束DFT方法可能有方法学创新）

### 2. 关键路径任务识别 (12 critical tasks)

**Top 5 Critical + High Feasibility** (应立即启动):
1. FE-205: constrained DFT 框架 (100/100)
2. FE-200: 自适应 Kerker 预处理 (95/100)
3. FE-100: onsite_projector nspin=1/2 (90/100)
4. FE-105: mixing_dftu (90/100)
5. FE-302-305: 验证任务组 (90/100)

**Critical + Low Feasibility** (需前置研究):
- FE-D-A3: 新赝势全面验证
  - 触发条件：FE-304 accuracy_below_threshold
  - 建议：提前进行赝势质量预研究

### 3. 阻塞任务需要优先解决

**Blocked 任务**:
- FE-000: 赝势库调研与收集 (47.5/100)
  - **Action**: 立即启动，作为Phase 0的第一步
  - **Risk**: 阻塞FE-302验证任务

**建议立即行动：**
```bash
# Week 1 任务调整
1. FE-000: 赝势库调研（2天）← 立即启动，解除阻塞
2. FE-001: DFT+U代码审计（2-3天）← 并行进行
3. FE-100: onsite_projector扩展（1-2天）← 补充测试后可并行
```

### 4. 延迟任务的研究前置需求

**5个 deferred 任务需要研究pipeline**：

| Task ID | Novelty | 研究需求 | 时间估算 |
|---------|---------|----------|---------|
| FE-D-C1 | routine | ML数据收集框架调研 | 1周 |
| FE-D-C2 | frontier | GNN架构文献综述 + 原型 | 2-3周 |
| FE-D-C3 | advanced | PyABACUS集成接口设计 | 1周 |
| FE-D-A2 | incremental | ONCVPSP参数优化策略 | 1-2周 |
| FE-D-B2 | incremental | Spillage算法调研 | 1周 |

**建议：**
使用 claude-scholar 的 research-ideation skill 为每个任务生成：
- 5W1H 分析
- 文献综述清单
- Gap 分析
- 技术可行性评估

---

## 优化建议

### A. 任务优先级调整

#### 当前执行顺序（原计划）:
```
Week 1: FE-100 + FE-107
Week 2: FE-101
Week 3: FE-102 + FE-103
...
```

#### 建议优化顺序（基于 priority score）:

**Phase 0 强化（前2周）**:
```
Week 1-2: 基础设施准备
  Day 1-2:   FE-000 赝势库调研 (blocked → 解除阻塞)
  Day 3-5:   FE-001 代码审计 (并行)
  Day 6-8:   FE-002 回归测试套件
  Day 9-10:  FE-205 前置研究：约束DFT文献综述
```

**Phase 1 并行化（第3-4周）**:
```
Week 3: 关键代码移植
  FE-100 (补测试) + FE-101 (nspin=4) 串行
  FE-107 deltaspin移植（并行独立分支）

Week 4: 扩展与验证
  FE-102 + FE-103 并行
  FE-200 前置研究：Kerker预处理调研
```

**Phase 2 前置（第5-6周）**:
```
Week 5-6: 算法创新任务启动
  FE-200: 自适应Kerker（高优先级，95分）
  FE-205: 约束DFT框架（最高优先级，100分）
  FE-204: 能量监控（依赖FE-200/201/203）
```

### B. 研究前置机制

**为高创新任务增加研究阶段**：

| 任务 | 前置研究内容 | 时间 | 产出 |
|-----|-------------|------|------|
| FE-205 | 约束DFT方法综述，VASP/QE实现调研 | 3天 | 技术方案文档 |
| FE-200 | Kerker预处理文献，参数敏感性分析 | 2天 | 参数候选集 |
| FE-D-C2 | GNN占据矩阵预测可行性分析 | 1周 | 原型代码 |

**研究工具链（整合claude-scholar）**：
```bash
# 使用 research-ideation skill
/research-init "Constrained DFT for f-electron occupation control"

# 使用 architecture-design skill
/plan  # 生成技术实现方案

# 使用 results-analysis skill
/analyze-results  # 分析预研究数据
```

### C. 里程碑调整

#### 原计划里程碑:
- M1 (Month 1): Architecture ready + basic convergence
- M2 (Month 2): Occupation strategies working
- ...

#### 建议调整:

**M0 (Week 2): 研究基础完成**
- ✅ 赝势库调研完成
- ✅ 代码审计完成
- ✅ 高优先级任务的前置研究完成
- 📚 研究文档库建立

**M1 (Month 1): 核心功能 + 研究验证**
- ✅ onsite_projector扩展
- ✅ DFT+U PW基本功能
- ✅ FE-200/FE-205 原型验证
- 📊 技术可行性报告

**M2 (Month 2): 算法创新 + 初步验证**
- ✅ 自适应算法全部实现
- ✅ 约束DFT框架
- ✅ CeO2基线验证
- 📈 收敛性能对比报告

### D. 并行化机会识别

**当前并行机会（已识别）**:
```
FE-000 || FE-001 || FE-002
FE-100 || FE-107
FE-200 || FE-201 || FE-202
```

**新增并行机会（基于依赖分析）**:

1. **研究任务并行**:
   ```
   FE-200研究 || FE-205研究 || FE-D-C2前期调研
   ```

2. **验证任务并行**:
   ```
   FE-302 (CeO2) || FE-303 (GdN) || FE-304 (VASP对比)
   ```

3. **工作流任务并行**:
   ```
   FE-400 (参数选择) || FE-401 (失败诊断) || FE-402 (abacustest集成)
   ```

### E. 风险管理

**当前风险识别（基于review）**:
1. ❌ **零高风险任务** - 这是好消息
2. ⚠️ **8个低可行性任务** - 主要是deferred任务，风险可控
3. 🚫 **2个blocked任务** - FE-000和FE-001，需要立即解决

**建议增加的风险缓解措施**:

| 风险 | 影响 | 缓解策略 |
|------|------|----------|
| 前沿任务失败 (FE-205/FE-D-C2) | 高 | 早期原型验证 + fallback方案 |
| 赝势质量不达标 | 中 | 提前触发FE-D-A1/A2 |
| VASP对比差异大 | 中 | 增加中间checkpoint验证 |
| ML模型精度不足 | 低 | 先用rule-based替代 |

---

## 具体行动计划

### Week 1-2: 立即启动

```markdown
## Sprint 0: 研究准备 (2周)

### Day 1-2: 解除阻塞
- [ ] FE-000: 赝势库调研 (Priority: 紧急)
  - 收集 La/Ce/Nd/Sm/Eu/Gd/Tb 的 f_in_valence 赝势
  - 建立赝势库索引
  - 产出: `pseudopotentials/rare_earth/README.md`

### Day 3-5: 代码审计
- [ ] FE-001: DFT+U 代码深度审计
  - 绘制数据流图
  - 识别 f 电子处理路径
  - 产出: `projects/f-electron-scf/audit/dftu_audit.md`

### Day 6-8: 回归测试
- [ ] FE-002: DFT+U 回归测试套件
  - CeO2 LCAO baseline
  - GdN LCAO baseline
  - 产出: 自动化测试脚本

### Day 9-14: 前置研究（并行）
- [ ] FE-205 研究: Constrained DFT
  - 使用 /research-init 启动文献综述
  - 调研 VASP/QE/CP2K 实现
  - 设计 ABACUS 实现方案
  - 产出: `FE-205_design.md`

- [ ] FE-200 研究: 自适应 Kerker
  - 分析当前 Kerker 实现
  - 参数敏感性实验
  - 产出: 参数候选集
```

### Week 3-4: 核心移植

```markdown
## Sprint 1: 核心功能 (2周)

### Week 3:
- [ ] FE-100: onsite_projector nspin=1/2 (补测试)
- [ ] FE-101: DFT+U PW nspin=4
- [ ] FE-107: deltaspin 移植（并行分支）

### Week 4:
- [ ] FE-102: DFT+U PW nspin=1/2
- [ ] FE-103: DFT+U PW force
- [ ] FE-105: mixing_dftu 实现
```

### Week 5-8: 算法创新

```markdown
## Sprint 2: 算法创新 (4周)

### Week 5-6: Phase 2 核心算法
- [ ] FE-200: 自适应 Kerker (95/100 priority)
- [ ] FE-201: 分通道 mixing_beta
- [ ] FE-202: 占据矩阵多起点

### Week 7-8: 高级算法
- [ ] FE-203: 占据矩阵退火
- [ ] FE-204: 能量监控 + 自动回退
- [ ] FE-205: 约束 DFT 框架 (100/100 priority) ⭐
```

### Week 9-14: 验证与工作流

```markdown
## Sprint 3: 验证 (4周)

### Week 9-10: 用户需求与体系选择
- [ ] FE-300: 用户需求调研
- [ ] FE-301: 选择验证体系

### Week 11-13: 基准验证
- [ ] FE-302: CeO2/Gd2O3/La2O3 验证
- [ ] FE-303: 合金磁性化合物验证
- [ ] FE-304: ABACUS vs VASP 对比

### Week 14: 可靠性测试
- [ ] FE-305: 收敛可靠性测试（10次随机种子）
```

### Week 15-20: 自动化

```markdown
## Sprint 4: 自动化 (6周)

### Week 15-17: 工具开发
- [ ] FE-400: 自动参数选择
- [ ] FE-401: 失败诊断 + 自动重试
- [ ] FE-402: abacustest 集成

### Week 18-19: 文档与示例
- [ ] FE-403: 用户文档
  - 教程: ABACUS 稀土 DFT+U 计算指南
  - 示例库: 5-10 个收敛体系
  - 故障排除指南

### Week 20: 端到端工作流
- [ ] FE-404: 自动化工作流整合
```

---

## claude-scholar 集成方案

### 工具链映射

| pm-agent 阶段 | claude-scholar skill | 用途 |
|--------------|---------------------|------|
| 前置研究 | research-ideation | 5W1H、Gap分析、先进性评估 |
| 技术设计 | architecture-design | ML项目框架、设计模式 |
| 任务规划 | dev-planner agent | 智能任务拆解 |
| 进度跟踪 | planning-with-files | Markdown规划文档 |
| 结果分析 | results-analysis | 验证数据分析、可视化 |
| 论文准备 | ml-paper-writing | 方法学论文撰写 |

### 具体应用场景

#### 1. FE-205 (约束DFT) 研究工作流

```bash
# Step 1: 研究构思
/research-init "Constrained DFT for rare-earth f-electron occupation"
# → 生成: 5W1H分析、文献清单、Gap分析

# Step 2: 技术设计
/plan
# → 生成: 实现方案、API设计、测试策略

# Step 3: 实现

# Step 4: 结果分析
/analyze-results
# → 生成: 收敛性分析、与VASP对比图表

# Step 5: 论文准备（如果有方法学创新）
# 使用 ml-paper-writing skill
```

#### 2. FE-D-C2 (GNN模型) ML开发工作流

遵循 claude-scholar 的 ML 生命周期：

```
1. 研究构思 → /research-init "GNN for DFT+U occupation matrix prediction"
2. ML开发 → architecture-design + tdd
3. 实验分析 → /analyze-results
4. 论文写作 → ml-paper-writing (如果效果好)
```

### 建议新增文件

```
projects/f-electron-scf/
├── research/                      # 新增：研究文档
│   ├── FE-205_constrained_dft_research.md
│   ├── FE-D-C2_gnn_feasibility.md
│   └── literature_review.md
├── design/                        # 新增：技术设计
│   ├── FE-205_implementation_plan.md
│   └── FE-200_adaptive_kerker_design.md
└── results/                       # 新增：实验结果
    ├── convergence_analysis.ipynb
    └── vasp_comparison.md
```

---

## 预期收益

### 任务执行效率提升

| 指标 | 优化前 | 优化后 | 提升 |
|------|--------|--------|------|
| 前期阻塞时间 | 2周+ | 0.5周 | **75%↓** |
| 高风险任务失败率 | 20-30% | <10% | **67%↓** |
| 研究-实现周期 | 不明确 | 明确的前置研究 | **清晰化** |
| 并行度 | 部分并行 | 充分并行 | **30%↑** |

### 科学产出提升

- **方法学创新机会**: FE-205 约束DFT方法可能发表方法学论文
- **工程最佳实践**: 自动化工作流可作为ABACUS稀土计算标准流程
- **技术积累**: ML辅助DFT的经验可推广到其他体系

### 项目管理改进

- ✅ 任务优先级科学化（基于可行性+先进性+价值）
- ✅ 风险识别自动化（5个需前置研究的任务提前标识）
- ✅ 研究-工程平衡（31%创新任务有明确研究规划）
- ✅ 进度可视化（结合dashboard工具）

---

## 下一步行动

### 立即启动（本周）

1. ✅ **运行研究评审** - 已完成
2. 📋 **审阅优化方案** - 本文档
3. 🚀 **启动 FE-000** - 赝势库调研（解除阻塞）
4. 📚 **启动 FE-205 前置研究** - 约束DFT文献综述

### 近期计划（2周内）

1. 完成 Phase 0 基础设施
2. 为 Top 5 创新任务准备研究文档
3. 建立研究文档库结构
4. 集成 claude-scholar 工具链

### 持续优化

1. 每个 Sprint 结束后重新运行评审
2. 根据进展动态调整优先级
3. 定期更新 research_review.md
4. 追踪创新任务的研究进展

---

## 附录: 评审方法论

### 评估维度

本次评审整合了 claude-scholar 的研究规划思想：

1. **Feasibility (可行性)**: 技术成熟度、依赖清晰度、工作量合理性
2. **Novelty (先进性)**: 是否解决前沿问题、是否有创新性
3. **Scientific Value (科学价值)**: 对项目目标的贡献度、关键路径重要性
4. **Risk (风险)**: 技术风险、依赖风险、时间风险

### Priority Score 计算

```
Priority = 0.5 * Value + 0.3 * Feasibility + 0.2 * Novelty

Value: {critical: 100, high: 75, medium: 50, low: 25}
Feasibility: {high: 100, medium: 70, low: 40, blocked: 0}
Novelty: {frontier: 100, advanced: 75, incremental: 50, routine: 25}
```

### 评审工具

- 脚本: `tools/review_f_electron.py`
- 报告: `projects/f-electron-scf/research_review.md`
- 数据: `projects/f-electron-scf/research_review.json`

---

**Generated by**: pm-agent research review (claude-scholar integration)
**Date**: 2026-02-14
**Tool Version**: v0.1.0
