# FE-D-C2: GNN 占据矩阵模型训练

## Objective

[TERMINATED] 训练轻量级模型预测初始占据矩阵：(1) 输入特征：原子类型、近邻环境、氧化态估计，(2) 输出：每个稀土原子的 f 电子占据数和轨道序，(3) 先尝试 MLP/随机森林，再考虑 GNN。

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

- [ ] 设计 GNN 架构（结构→占据矩阵）
- [ ] 训练/验证/测试集划分
- [ ] 模型精度：占据数预测误差<0.5 电子
- [ ] 推理速度<1 秒/结构
