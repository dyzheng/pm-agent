## 4. 项目交付标准

本节定义 DFPT-002 整体以及每个子任务的交付标准。分为三个层次：必须满足（MUST）、应当满足（SHOULD）、建议满足（MAY）。

---

### 4.1 DFPT-002 整体交付标准

#### MUST（不满足则不能关闭任务）

| # | 标准 | 验证方法 |
|---|------|----------|
| M1 | `domain-knowledge/abacus-dfpt.md` 存在且被 `load_domain_knowledge()` 正确加载 | `python3 -c "from orchestrator import load_domain_knowledge; dk=load_domain_knowledge(); assert 'DFPT' in dk"` |
| M2 | 6 个 DFPT review agent prompt（`.agent.md`）存在且格式正确 | 每个文件包含 `$RUN_ID`, `$TARGET` 占位符，输出要求为纯 JSON |
| M3 | 3 个 DFPT migrate agent prompt（`.agent.md`）存在且格式正确 | 同上 |
| M4 | 至少 1 次完整的 6-agent DFPT review 运行成功 | `output/<run_id>/run-manifest.json` 中 `agents_pending` 为空 |
| M5 | 至少 1 次完整的 3-agent DFPT migrate 运行成功 | 同上 |
| M6 | 所有 agent JSON 输出通过 envelope schema 验证 | `jsonschema -i output/<run_id>/<agent>.json schemas/envelope.schema.json` |
| M7 | 示例审查报告和迁移报告各 1 份 | `examples/dfpt_*_review.md` 和 `examples/dfpt_*_migration.md` 存在 |

#### SHOULD（不满足需要记录为技术债务）

| # | 标准 | 验证方法 |
|---|------|----------|
| S1 | DFPT 领域知识中每条 checklist 有 `[REF-DFxx]` 代码证据引用 | 人工检查 `abacus-dfpt.md` |
| S2 | 6 个人读版 prompt（`.md`）存在且可作为 Claude Code slash command | `.claude/commands/review-dfpt-*.md` 存在 |
| S3 | 迁移工作流配对表覆盖 ≥10 个 QE→ABACUS 文件对 | 人工检查 `DFPT_MIGRATION_WORKFLOW.md` |
| S4 | 示例审查报告包含 ≥10 条 findings | `jq '.findings | length' output/<run_id>/review-summary.json` |
| S5 | 示例迁移报告包含 ≥8 条 adaptations | `jq '.adaptations | length' output/<run_id>/review-migrate-diff.json` |

#### MAY（改进建议，不阻塞交付）

| # | 标准 |
|---|------|
| N1 | orchestrator.py 增加 `dfpt-review` 子命令，一键运行 DFPT 专用审查 |
| N2 | 创建 CI 脚本自动验证 prompt 格式和 schema 兼容性 |
| N3 | 为 DFPT 审查创建专用的严重程度分级标准文档 |

---

### 4.2 子任务交付标准

#### DFPT-002a: 领域知识文档

**交付物清单：**

```
domain-knowledge/
├── abacus-dfpt.md                    # DFPT 领域知识主文档
└── references/
    ├── ref-dfpt-physics.md           # DFPT 物理代码证据
    └── ref-dfpt-algorithm.md         # DFPT 算法代码证据
```

**验收检查：**

```bash
# 1. 文件存在性
test -f domain-knowledge/abacus-dfpt.md
test -f domain-knowledge/references/ref-dfpt-physics.md
test -f domain-knowledge/references/ref-dfpt-algorithm.md

# 2. 加载测试
python3 -c "
from orchestrator import load_domain_knowledge
dk = load_domain_knowledge()
assert 'DFPT' in dk, 'DFPT keyword not found'
assert 'Sternheimer' in dk, 'Sternheimer not mentioned'
assert 'REF-DF' in dk, 'No DFPT reference markers'
print('OK: domain knowledge loads correctly')
"

# 3. 内容完整性（人工检查）
# - 物理量表 ≥15 个条目
# - QE PHonon 模块映射 ≥20 个文件
# - 6 个审查维度均有 DFPT 专用 checklist
```

**内容规范：**

`abacus-dfpt.md` 必须包含以下章节：

| 章节 | 内容要求 | 最低条目数 |
|------|----------|-----------|
| DFPT 单位制 | Ry/Hartree 换算、微扰势单位、动力学矩阵单位 | 8 |
| DFPT 核心物理量 | 变量名、量纲、内部单位、典型值范围 | 15 |
| DFPT 物理约束 checklist | 声学和规则、Hermiticity、电荷响应守恒等 | 10 |
| DFPT 算法适配 checklist | Sternheimer 收敛、预条件器、SCF 混合等 | 8 |
| QE PHonon 模块映射 | Fortran 文件 → 物理功能 → 关键变量 | 20 |
| ABACUS DFPT 模块映射 | C++ 文件 → 物理功能 → 接口定义 | 10 |
| 严重程度分级 | ERROR/WARNING/INFO 的 DFPT 专用判定标准 | 各 3 条 |

---

#### DFPT-002b: 审查 Prompt 和 Schema

**交付物清单：**

```
prompts/
├── review-dfpt-units.agent.md
├── review-dfpt-physics.agent.md
├── review-dfpt-algorithm.agent.md
├── review-dfpt-style.agent.md
├── review-dfpt-callchain.agent.md
├── review-dfpt-debug.agent.md
├── review-dfpt-units.schema.json      # 可选，如复用 finding.schema.json
├── ...
.claude/commands/
├── review-dfpt-units.md
├── review-dfpt-physics.md
├── review-dfpt-algorithm.md
├── review-dfpt-style.md
├── review-dfpt-callchain.md
└── review-dfpt-debug.md
```

**验收检查：**

```bash
# 1. 文件存在性
for agent in units physics algorithm style callchain debug; do
  test -f "prompts/review-dfpt-${agent}.agent.md" || echo "MISSING: review-dfpt-${agent}.agent.md"
  test -f ".claude/commands/review-dfpt-${agent}.md" || echo "MISSING: review-dfpt-${agent}.md"
done

# 2. 格式验证（每个 .agent.md 必须包含占位符和 JSON 输出模板）
for f in prompts/review-dfpt-*.agent.md; do
  grep -q '\$RUN_ID' "$f" || echo "MISSING \$RUN_ID in $f"
  grep -q '\$TARGET' "$f" || echo "MISSING \$TARGET in $f"
  grep -q '"findings"' "$f" || echo "MISSING findings in $f"
done

# 3. 手动测试（用 dvqpsi_cpp 文件）
python3 orchestrator.py review /root/q-e/PHonon/dvqpsi_cpp/src/dvqpsi_us.cpp
# 检查输出 JSON 格式正确
```

**Prompt 内容规范：**

每个 `.agent.md` 必须包含：

| 元素 | 要求 |
|------|------|
| 角色定义 | 第一行声明 agent 专长 |
| 任务说明 | 明确审查目标 |
| 检查项 | ≥5 条 DFPT 专用检查项，每条有编号 |
| 输出格式 | 纯 JSON，包含 `agent`, `run_id`, `status`, `target`, `findings`, `summary`, `raw_markdown` |
| 占位符 | `$RUN_ID`, `$TARGET` |
| severity 约束 | 只能是 ERROR / WARNING / INFO |
| confidence 约束 | 只能是 high / medium / low |
| finding ID 格式 | `dfpt-{agent前缀}-{三位数字}`，如 `dfpt-units-001` |

---

#### DFPT-002c: 迁移工作流配置

**交付物清单：**

```
prompts/
├── review-migrate-source-dfpt.agent.md
├── review-migrate-target-dfpt.agent.md
└── review-migrate-diff-dfpt.agent.md
docs/
└── DFPT_MIGRATION_WORKFLOW.md
```

**验收检查：**

```bash
# 1. 文件存在性
test -f prompts/review-migrate-source-dfpt.agent.md
test -f prompts/review-migrate-target-dfpt.agent.md
test -f prompts/review-migrate-diff-dfpt.agent.md
test -f docs/DFPT_MIGRATION_WORKFLOW.md

# 2. 迁移工作流端到端测试
python3 orchestrator.py migrate \
  /root/q-e/PHonon/PH/solve_linter.f90 \
  --ref /root/abacus-dfpt/abacus-develop/source/source_hsolver/diago_cg.cpp

# 3. 检查输出
jq '.adaptations | length' output/<run_id>/review-migrate-diff.json
# 期望 ≥8
```

**迁移 Prompt 内容规范：**

`review-migrate-source-dfpt.agent.md` 必须额外覆盖：

| 维度 | Fortran→C++ 特有检查 |
|------|---------------------|
| 数组布局 | 1-based column-major → 0-based row-major |
| 复数类型 | COMPLEX*16 → std::complex<double> |
| 全局状态 | COMMON block / MODULE 变量 → 类成员 / 参数传递 |
| 并行接口 | MPI_Allreduce → Parallel_Reduce::reduce_pool |
| 内存管理 | ALLOCATE/DEALLOCATE → new/delete / RAII |
| I/O 模式 | Fortran WRITE → ABACUS 日志框架 |

`DFPT_MIGRATION_WORKFLOW.md` 必须包含：

| 内容 | 要求 |
|------|------|
| 源文件-参考文件配对表 | ≥10 对，覆盖 Phase 2-3 的全部关键组件 |
| 推荐迁移顺序 | 与 manual_plan.json 的任务顺序一致 |
| 每个组件的预期适配复杂度 | high/medium/low 标注 |
| 运行命令示例 | 每个组件的 orchestrator 调用命令 |

---

#### DFPT-002d: 集成验证和示例报告

**交付物清单：**

```
output/<review-run-id>/
├── run-manifest.json
├── review-dfpt-units.json
├── review-dfpt-physics.json
├── review-dfpt-algorithm.json
├── review-dfpt-style.json
├── review-dfpt-callchain.json
├── review-dfpt-debug.json
└── review-summary.json

output/<migrate-run-id>/
├── run-manifest.json
├── review-migrate-source-dfpt.json
├── review-migrate-target-dfpt.json
├── review-migrate-diff-dfpt.json
└── migrate-summary.json

examples/
├── dfpt_dvqpsi_review.md
└── dfpt_solve_linter_migration.md
```

**验收检查：**

```bash
# 1. Review 工作流验证
REVIEW_RUN=$(ls -t output/ | head -1)
jq '.agents_pending | length' "output/$REVIEW_RUN/run-manifest.json"
# 期望: 0（所有 agent 完成）

for agent in review-dfpt-units review-dfpt-physics review-dfpt-algorithm \
             review-dfpt-style review-dfpt-callchain review-dfpt-debug; do
  STATUS=$(jq -r '.status' "output/$REVIEW_RUN/${agent}.json")
  [ "$STATUS" = "ok" ] || echo "FAIL: $agent status=$STATUS"
done

# 2. Migrate 工作流验证
MIGRATE_RUN=$(ls -t output/ | sed -n '2p')
jq '.agents_pending | length' "output/$MIGRATE_RUN/run-manifest.json"
# 期望: 0

# 3. Schema 验证
pip install jsonschema 2>/dev/null
for f in output/$REVIEW_RUN/review-dfpt-*.json; do
  python3 -c "
import json, jsonschema
with open('schemas/envelope.schema.json') as s:
    schema = json.load(s)
with open('$f') as d:
    data = json.load(d)
jsonschema.validate(data, schema)
print('OK: $(basename $f)')
"
done

# 4. 示例报告存在性
test -f examples/dfpt_dvqpsi_review.md
test -f examples/dfpt_solve_linter_migration.md
```

---

### 4.3 质量门禁（Quality Gate）

DFPT-002 关闭前必须通过以下质量门禁：

```
┌─────────────────────────────────────────────────────────┐
│                    DFPT-002 Quality Gate                 │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Gate 1: 文件完整性                                      │
│  ├─ domain-knowledge/abacus-dfpt.md          ✓/✗       │
│  ├─ 6 × review-dfpt-*.agent.md               ✓/✗       │
│  ├─ 6 × review-dfpt-*.md (slash commands)    ✓/✗       │
│  ├─ 3 × review-migrate-*-dfpt.agent.md       ✓/✗       │
│  ├─ docs/DFPT_MIGRATION_WORKFLOW.md          ✓/✗       │
│  └─ 2 × examples/dfpt_*.md                  ✓/✗       │
│                                                         │
│  Gate 2: 格式正确性                                      │
│  ├─ 所有 .agent.md 包含 $RUN_ID/$TARGET      ✓/✗       │
│  ├─ 所有 JSON 输出通过 envelope schema        ✓/✗       │
│  └─ finding ID 格式符合规范                    ✓/✗       │
│                                                         │
│  Gate 3: 功能验证                                        │
│  ├─ 6-agent review 端到端成功                  ✓/✗       │
│  ├─ 3-agent migrate 端到端成功                 ✓/✗       │
│  └─ load_domain_knowledge() 加载成功           ✓/✗       │
│                                                         │
│  Gate 4: 内容质量                                        │
│  ├─ 领域知识物理量 ≥15 条                      ✓/✗       │
│  ├─ 审查 findings ≥10 条                      ✓/✗       │
│  ├─ 迁移 adaptations ≥8 条                    ✓/✗       │
│  └─ 代码证据引用 [REF-DFxx] 完整              ✓/✗       │
│                                                         │
│  Result: ALL PASS → DFPT-002 可关闭                     │
│          ANY FAIL → 修复后重新验证                       │
└─────────────────────────────────────────────────────────┘
```

---

## 5. 工作量估算和并行策略

| 子任务 | 估算工作量 | 角色 | 可并行 |
|--------|-----------|------|--------|
| DFPT-002a | 3-5 天 | 物理开发者 + DevOps | 否（其他子任务的前置） |
| DFPT-002b | 3-4 天 | DevOps | 是（与 002c 并行） |
| DFPT-002c | 3-4 天 | DevOps | 是（与 002b 并行） |
| DFPT-002d | 2-3 天 | DevOps | 否（需要 002b + 002c 完成） |

**最优路径：** 002a → (002b ∥ 002c) → 002d

**总工期：** 8-12 天（串行 11-16 天，并行节省 3-4 天）

---

## 6. 与其他任务的接口

### 上游依赖

| 任务 | 提供什么 | DFPT-002 如何使用 |
|------|----------|------------------|
| DFPT-001 | module_dfpt 架构设计 | 002a 中的 ABACUS DFPT 模块映射表 |

### 下游消费

| 任务 | 消费什么 | 如何使用 |
|------|----------|---------|
| DFPT-102 | 6-agent review + migrate workflow | 迁移 DVQPsiUS kernel 后运行审查 |
| DFPT-103 | 6-agent review + migrate workflow | 迁移 Sternheimer 后运行审查 |
| DFPT-201 | 6-agent review | DFPT SCF 实现后运行审查 |
| DFPT-202 | 6-agent review | 动力学矩阵实现后运行审查 |
| DFPT-203 | 6-agent review | EPC 实现后运行审查 |
| DFPT-301 | review-callchain | MPI 并行化后检查通信正确性 |

每个下游任务的验收标准中都包含"代码审核通过"，具体含义是：
- 运行 6-agent DFPT review，所有 agent status=ok
- 无 ERROR 级别 finding（或已修复）
- WARNING 级别 finding 已评估并记录处理决定
