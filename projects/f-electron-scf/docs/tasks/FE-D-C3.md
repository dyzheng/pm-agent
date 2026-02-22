# FE-D-C3: ABACUS ML 集成

## Objective

[TERMINATED] 将训练好的模型集成到 ABACUS 工作流：(1) Python 脚本：读取 STRU 文件→模型预测→生成 initial_onsite.dm，(2) 或通过 PyABACUS 接口直接注入，(3) 新增 init_chg='ai' 选项（长期目标）。

终止原因：见 plans/2026-02-16-critical-review.md

## Reference Code

### Source Code (to migrate from)

<!-- List specific source files with paths and key functions/subroutines.
     Every path must be verified to exist. Example:
     **`/root/q-e/PHonon/PH/solve_linter.f90`** — Main DFPT SCF loop
     - `solve_linter()`: outer SCF iteration
     - `dvqpsi_us()`: compute dV/dtau * psi
-->

TODO: Add reference source code paths and key functions.

### Target Code (to integrate with)

<!-- List ABACUS target files, classes, and patterns. Example:
     **`/root/abacus-dfpt/abacus-develop/source/source_esolver/`**
     - `ESolver_KS_PW` — base class to extend
     - `esolver_ks_pw.cpp:120` — `before_scf()` lifecycle hook
-->

TODO: Add target code paths and integration points.

### Prior Art / Related Implementations

<!-- List any existing implementations to reference. Example:
     **`/root/q-e/PHonon/dvqpsi_cpp/`** — Standalone C++ DFPT kernel
     - `DVQPsiUS` class — core dV*psi operator
-->

TODO: Add prior art references if applicable.

## Implementation Guide

### Architecture Decisions

<!-- Key design choices and rationale. -->

TODO: Document architecture decisions.

### Data Structure Mapping

<!-- Fortran-to-C++ or source-to-target variable/type correspondence.
     Use a table format:

     | Source (QE/Fortran) | Target (ABACUS/C++) | Notes |
     |---------------------|---------------------|-------|
     | `evc(npwx, nbnd)`  | `psi::Psi<T>`      | Band wavefunctions |
-->

TODO: Add data structure mapping table.

### Critical Implementation Details

<!-- Pitfalls, numerical considerations, edge cases. -->

TODO: Document critical details.

## TDD Test Plan

### Tests to Write FIRST

```cpp
// TODO: Add concrete test code with expected values and tolerances.
// Example:
// TEST_F(DFPTTest, SiGammaPhononFrequencies) {
//     // Expected: 3 acoustic (0 cm-1) + 3 optical (~520 cm-1)
//     run_dfpt("Si_gamma");
//     auto freqs = read_frequencies("dynmat.out");
//     EXPECT_NEAR(freqs[3], 520.0, 0.5);  // first optical mode
// }
```

## Acceptance Criteria

- [ ] 模型推理接口集成到 ABACUS
- [ ] 添加 init_chg=ml 选项
- [ ] 自动从结构预测占据矩阵
- [ ] 与现有 omc 模式兼容
- [ ] 性能开销<5%
