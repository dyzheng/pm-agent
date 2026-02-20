# DFPT-002 任务拆分方案

**日期：** 2026-02-20
**基于：** `/root/code-review-agent/` 实际代码架构

## 1. code-review-agent 架构摘要

在拆分之前，先明确 code-review-agent 的实际设计：

### 1.1 核心组件

```
code-review-agent/
├── orchestrator.py          # 单文件 async Python 编排器
├── prompts/
│   ├── review-*.md          # 人读版 prompt（Claude Code slash command 用）
│   ├── review-*.agent.md    # 机读版 prompt（orchestrator 调用，输出纯 JSON）
│   └── review-*.schema.json # 每个 agent 的接口契约
├── schemas/
│   ├── envelope.schema.json # 统一输出信封
│   ├── finding.schema.json  # 审查类 finding 结构
│   ├── checklist-source.schema.json
│   ├── checklist-target.schema.json
│   └── adaptation.schema.json
├── domain-knowledge/
│   ├── abacus.md            # ABACUS 领域知识（单位制、物理量、checklist）
│   └── references/          # 代码证据文件（ref-*.md）
│       ├── ref-constants.md
│       ├── ref-physics.md
│       ├── ref-algorithm.md
│       ├── ref-callchain.md
│       ├── ref-defensive.md
│       └── ref-framework.md
└── output/<run_id>/         # 运行输出
    ├── run-manifest.json
    ├── review-units.json
    ├── ...
    └── review-summary.json
```

### 1.2 两个工作流

**Review 工作流（6 agent 并发）：**
- `review-units` — 单位/量纲一致性
- `review-physics` — 守恒律、物理约束
- `review-algorithm` — 算法-问题匹配、数值稳定性
- `review-style` — 命名语义、代码结构
- `review-callchain` — 物理量流动、状态追踪
- `review-debug` — 防御性编程、范围断言

**Migrate 工作流（3 agent 串行）：**
1. `review-migrate-source` — 提取源代码算法特征 checklist
2. `review-migrate-target` — 提取目标仓库实现范式 checklist
3. `review-migrate-diff` — 对比两份 checklist，生成适配方案

### 1.3 关键设计模式

- **Prompt 双格式：** 每个 agent 有 `.md`（人读）和 `.agent.md`（机读）两个版本，独立维护
- **领域知识注入：** `domain-knowledge/*.md` 自动注入所有 agent 的 system prompt
- **代码证据引用：** checklist 中的 `[REF-xxx]` 标记对应 `references/` 下的具体代码位置
- **统一 JSON 信封：** 所有输出包含 `agent`, `run_id`, `status`, `target`, `summary`, `raw_markdown`
- **Finding ID 规范：** `{agent前缀}-{三位数字}`，如 `units-001`
- **严重程度三级：** ERROR（确定性物理错误）、WARNING（高概率问题）、INFO（改进建议）
- **断点续跑：** manifest 记录已完成/待完成 agent，支持 `--run-id` 恢复

### 1.4 DFPT 迁移中需要适配的部分

现有 code-review-agent 是为 ABACUS **已有代码的审查**设计的。用于 DFPT 迁移需要：

1. **领域知识扩展：** 现有 `abacus.md` 不包含 DFPT 相关的物理量、单位、checklist
2. **Prompt 适配：** 审查维度需要增加 DFPT 特有的检查项（微扰势、Sternheimer 收敛、声子对称性等）
3. **迁移工作流配置：** source 指向 QE PHonon Fortran 代码，target 指向 ABACUS C++ 代码
4. **代码证据补充：** 需要从 QE PHonon 和 dvqpsi_cpp 中提取代码证据

---

## 2. DFPT-002 拆分为 4 个子任务

原始 DFPT-002 定义：
> 基于 /root/code-review-agent/ 建立 DFPT 迁移的代码审核流程

拆分原则：每个子任务有明确的输入、输出和验收标准，可独立交付和验证。

---

### DFPT-002a: 编写 DFPT 领域知识文档

**目标：** 在 `domain-knowledge/` 下创建 DFPT 专用领域知识，供所有 agent 自动注入。

**输入：**
- QE PHonon 源代码 `/root/q-e/PHonon/PH/`
- dvqpsi_cpp 实现 `/root/q-e/PHonon/dvqpsi_cpp/`
- ABACUS 现有模块接口 `/root/abacus-dfpt/abacus-develop/`
- 现有 `domain-knowledge/abacus.md` 作为格式参考

**交付物：**

1. `domain-knowledge/abacus-dfpt.md` — DFPT 领域知识主文档，包含：
   - DFPT 内部单位制（QE 用 Ry，ABACUS 用 Hartree，换算关系）
   - DFPT 核心物理量表（微扰势 ΔV、响应密度 Δρ、响应波函数 Δψ、动力学矩阵 D、EPC 矩阵元 g 等）
   - DFPT 物理约束 checklist（声学和规则、Hermiticity、电荷守恒响应等）
   - DFPT 算法适配 checklist（Sternheimer 收敛、SCF 混合、对称性约化等）
   - QE PHonon 模块-物理映射表（phq_init → 初始化、solve_linter → Sternheimer、dynmatrix → 动力学矩阵等）
   - ABACUS module_dfpt 模块-物理映射表（与 DFPT-001 架构设计对齐）

2. `domain-knowledge/references/ref-dfpt-physics.md` — DFPT 物理代码证据，包含：
   - QE PHonon 中关键物理量的代码位置和变量名
   - dvqpsi_cpp 中已实现的核心 kernel 代码位置
   - ABACUS 中可复用的模块接口代码位置

3. `domain-knowledge/references/ref-dfpt-algorithm.md` — DFPT 算法代码证据，包含：
   - Sternheimer 求解器的 QE 实现位置和关键参数
   - DFPT SCF 循环的 QE 实现位置和收敛判据
   - 动力学矩阵计算的 QE 实现位置

**验收标准：**
- [ ] `abacus-dfpt.md` 覆盖 DFPT 的全部 6 个审查维度（单位、物理、算法、风格、调用链、防御）
- [ ] 每条 checklist 项有 `[REF-DFxx]` 标记，对应 references 中的具体代码位置
- [ ] 物理量表至少包含 15 个 DFPT 核心物理量
- [ ] QE PHonon 模块映射覆盖 PH/ 目录下的主要 Fortran 文件（≥20 个）
- [ ] 用现有 orchestrator 加载测试通过（`load_domain_knowledge()` 能正确读取）

**依赖：** DFPT-001（需要架构设计确定 module_dfpt 的模块结构）

---

### DFPT-002b: 编写 DFPT 审查 Prompt 和 Schema

**目标：** 为 6 个 review agent 创建 DFPT 专用的 prompt 扩展和 schema。

**输入：**
- DFPT-002a 的领域知识文档
- 现有 `prompts/review-*.agent.md` 作为格式参考
- 现有 `schemas/*.schema.json` 作为格式参考

**交付物：**

1. 6 个 DFPT 审查 prompt（机读版），放在 `prompts/` 下：
   - `review-dfpt-units.agent.md` — DFPT 单位检查扩展（Ry/Hartree 混用、微扰势单位、动力学矩阵单位）
   - `review-dfpt-physics.agent.md` — DFPT 物理检查（声学和规则、Hermiticity、电荷响应守恒、LO-TO 劈裂）
   - `review-dfpt-algorithm.agent.md` — DFPT 算法检查（Sternheimer 收敛、预条件器、SCF 混合策略）
   - `review-dfpt-style.agent.md` — DFPT 命名检查（QE→ABACUS 命名映射、DFPT 变量命名规范）
   - `review-dfpt-callchain.agent.md` — DFPT 调用链检查（微扰势传播、响应密度归约、q 点通信）
   - `review-dfpt-debug.agent.md` — DFPT 防御检查（Sternheimer 不收敛处理、负频率检测、对称性破缺检测）

2. 6 个对应的人读版 prompt，放在 `.claude/commands/` 下：
   - `review-dfpt-units.md` 到 `review-dfpt-debug.md`

3. DFPT 专用 schema（如果 finding 结构需要扩展）：
   - `prompts/review-dfpt-units.schema.json` 等（可复用现有 finding.schema.json，仅在 category enum 中增加 dfpt 前缀）

**验收标准：**
- [ ] 6 个 `.agent.md` prompt 均遵循现有格式（输出纯 JSON，包含 findings 数组）
- [ ] 6 个 `.md` prompt 均可作为 Claude Code slash command 使用
- [ ] 每个 prompt 的检查项至少 5 条，且与 DFPT-002a 的 checklist 对应
- [ ] schema 与现有 `finding.schema.json` 兼容（severity/confidence/location 格式一致）
- [ ] 用 dvqpsi_cpp 中的一个文件手动测试每个 prompt，确认输出格式正确

**依赖：** DFPT-002a

---

### DFPT-002c: 配置 DFPT 迁移工作流

**目标：** 配置 3-agent 串行迁移工作流，使其能分析 QE Fortran → ABACUS C++ 的迁移。

**输入：**
- DFPT-002a 的领域知识文档
- QE PHonon 源代码（Fortran）
- dvqpsi_cpp 参考实现（C++）
- ABACUS 现有模块代码（C++）

**交付物：**

1. 迁移工作流的 prompt 适配：
   - `prompts/review-migrate-source-dfpt.agent.md` — 扩展源代码分析，增加 Fortran→C++ 特有的检查维度：
     - Fortran COMMON block → C++ 类成员
     - Fortran 数组（1-based, column-major）→ C++ 数组（0-based, row-major）
     - Fortran COMPLEX*16 → std::complex<double>
     - Fortran MPI 调用 → ABACUS Parallel_Reduce 接口
   - `prompts/review-migrate-target-dfpt.agent.md` — 扩展目标范式提取，增加 ABACUS DFPT 模块的特有约束
   - `prompts/review-migrate-diff-dfpt.agent.md` — 扩展差异对比，增加 Fortran→C++ 适配维度

2. 迁移工作流配置文档：
   - `docs/DFPT_MIGRATION_WORKFLOW.md` — 说明如何对每个 DFPT 组件运行迁移工作流，包含：
     - 源文件（QE Fortran）和参考文件（ABACUS C++）的配对表
     - 推荐的迁移顺序
     - 每个组件的预期适配复杂度

**验收标准：**
- [ ] 3 个迁移 prompt 均遵循现有格式（source→checklist, target→checklist, diff→adaptations）
- [ ] Fortran→C++ 适配维度至少覆盖 6 个方面（数组布局、复数类型、内存管理、并行接口、全局状态、I/O）
- [ ] 源文件-参考文件配对表覆盖 DFPT 的全部关键组件（≥10 对）
- [ ] 用 dvqpsi_cpp 的一个文件运行完整迁移工作流（source→target→diff），生成有效的适配方案

**依赖：** DFPT-002a

---

### DFPT-002d: 集成验证和示例报告

**目标：** 端到端验证整个审查和迁移工作流，生成示例报告。

**输入：**
- DFPT-002a/b/c 的全部交付物
- dvqpsi_cpp 中的 `dvqpsi_us.cpp` 作为测试文件
- ABACUS 中的 `diago_cg.cpp` 或类似文件作为参考

**交付物：**

1. Review 工作流验证：
   - 用 dvqpsi_cpp 的 `dvqpsi_us.cpp` 运行 6-agent DFPT 审查
   - 输出保存在 `output/<run_id>/`
   - 生成 `review-summary.json`

2. Migrate 工作流验证：
   - 用 QE PHonon 的一个 Fortran 文件（如 `solve_linter.f90`）作为 source
   - 用 ABACUS 的一个 C++ 文件（如 `diago_cg.cpp`）作为 reference
   - 运行 3-agent 迁移工作流
   - 输出保存在 `output/<run_id>/`

3. 示例报告文档：
   - `examples/dfpt_dvqpsi_review.md` — dvqpsi_us.cpp 的审查报告（从 JSON 输出整理）
   - `examples/dfpt_solve_linter_migration.md` — solve_linter.f90 的迁移适配方案

4. orchestrator.py 的 DFPT 扩展（如需要）：
   - 在 `REVIEW_AGENTS` 列表中增加 DFPT 专用 agent 的支持
   - 或创建 `DFPT_REVIEW_AGENTS` 列表和对应的 `run_dfpt_review()` 函数

**验收标准：**
- [ ] 6-agent DFPT 审查工作流端到端运行成功，所有 agent 输出 status=ok
- [ ] 3-agent 迁移工作流端到端运行成功，生成有效的适配方案
- [ ] 示例审查报告包含至少 10 条 findings（覆盖 ERROR/WARNING/INFO 三个级别）
- [ ] 示例迁移报告包含至少 8 条 adaptations（覆盖 high/medium/low 三个复杂度）
- [ ] 所有 JSON 输出通过 schema 验证
- [ ] orchestrator 支持 `--workflow dfpt-review` 或等效方式调用 DFPT 审查

**依赖：** DFPT-002b, DFPT-002c

---

## 3. 子任务依赖关系

```
DFPT-001 (架构设计)
    │
    ▼
DFPT-002a (领域知识)
    │
    ├──────────────┐
    ▼              ▼
DFPT-002b       DFPT-002c
(审查 prompt)   (迁移工作流)
    │              │
    └──────┬───────┘
           ▼
       DFPT-002d
    (集成验证+示例)
```

DFPT-002b 和 DFPT-002c 可以并行开发。
