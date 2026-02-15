# PR 验收与测试规范

**适用范围：** f-electron-scf 所有 PR（PR-1 ~ PR-14）

通用的 4-Gate 验收规则、执行者行为约束、验收证据模板已写入 worktree 的 `CLAUDE.md`，此处不再重复。本文档仅记录教训和各 PR 的具体测试要求。

---

## 教训记录

### PR-1 验收失败

PR-1 声称"编译通过、已推送"，实际验收发现：零单元测试、零集成测试、无编译日志。

根因：task instruction 中测试要求是"建议"而非"强制"。

对策：所有 task instruction 的测试 section 标记为 MANDATORY，CLAUDE.md 中写入强制 4-Gate 规则。

---

## 各 PR 测试要求

每个 PR 的 task instruction 中已包含具体的 Gate 2/3 要求。以下为补充说明。

### 通用要求（所有 PR）

- 每个新增/修改的 public 方法至少一个 test case
- 每个新增的代码分支至少一个 test case
- 依赖链重时提取 static/free function 做单元测试，不允许跳过
- 新增功能如果需要后续 PR 才能端到端运行，集成测试 case 可以只建骨架（不含 result.ref），但必须运行现有 case 的回归测试

### PR-1: onsite_projector nspin=1/2

状态：代码已提交 (d2364165c)，验收未通过，需补充测试。

单元测试覆盖点：
- npol=1 spin-up/spin-down 的 occupation 累加（sign=±1）
- npol=2 回归（4 个 occ 分量不变）
- npol=1 的 charge_mag 计算

集成测试：回归 `099_PW_DJ_SO`，新增 case 骨架（待 PR-2 后生成 result.ref）。

### PR-2: DFT+U PW SCF nspin=1/2/4

单元测试覆盖点：
- nspin=1/2/4 的能量权重和对角系数
- nspin=1/2 vs nspin=4 的 becp index 步长
- set_locale() 的 uom_array→locale 拷贝
- nspin=2 spin-down VU 矩阵构造

集成测试：回归 `099_PW_DJ_SO`，新增 `100_PW_DFTU_S2`（nspin=2）和 `101_PW_DFTU_S1`（nspin=1）。

### PR-3 ~ PR-14

具体测试要求在各自的 task instruction 中定义。通用要求见上。
