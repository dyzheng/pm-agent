# dyzheng-issues 项目总结

## 项目概述

**来源**: GitHub `deepmodeling/abacus-develop` 仓库中 assign 给 dyzheng 的 6 个 open issues
**创建时间**: 2026-02-22
**任务总数**: 10 个（6 个 issues 拆解为 10 个可执行任务）

## Issue → Task 映射

| GitHub Issue | 标题 | 对应任务 | 优先级 |
|--------------|------|----------|--------|
| [#5021](https://github.com/deepmodeling/abacus-develop/issues/5021) | nspin=4 noncolin=0 磁矩解析错误 | DZ-001, DZ-005 | P0, P1 |
| [#6768](https://github.com/deepmodeling/abacus-develop/issues/6768) | 单精度 PW 计算 CUDA 错误 | DZ-002, DZ-007 | P0, P1 |
| [#6195](https://github.com/deepmodeling/abacus-develop/issues/6195) | OpenMPI v4 toolchain 编译问题 | DZ-003, DZ-010 | P0, P2 |
| [#6974](https://github.com/deepmodeling/abacus-develop/issues/6974) | nspin=2 需要 init_chg=dm | DZ-004, DZ-005 | P1, P1 |
| [#6377](https://github.com/deepmodeling/abacus-develop/issues/6377) | SOC 开启时内存过大 | DZ-006 | P1 |
| [#6824](https://github.com/deepmodeling/abacus-develop/issues/6824) | NO 配体电荷/磁性控制 | DZ-008, DZ-009 | P2, P2 |

## 任务分类

### P0 — 紧急 Bug 修复（3 个任务，可并行）

- **DZ-001**: 修复 nspin=4 noncolin=0 时磁矩解析错误
  - 核心文件: `source/source_cell/read_atoms_helper.cpp:302-309`
  - 工作量: 2-3 天

- **DZ-002**: 修复单精度 PW 计算 CUDA 运行时错误
  - 核心文件: `source/source_base/module_device/cuda/memory_op.cu:87`
  - 工作量: 3-5 天

- **DZ-003**: 诊断并修复 OpenMPI v4 toolchain 编译问题
  - 核心文件: `toolchain/scripts/stage1/install_openmpi.sh`
  - 工作量: 1-2 天

### P1 — 功能增强（4 个任务，部分依赖 P0）

- **DZ-004**: 实现 nspin=2 时 init_chg=dm 功能
  - 核心文件: `source/source_esolver/esolver_ks_lcao.cpp:176-181`
  - 工作量: 1-2 周
  - 依赖: 无（可与 P0 并行）

- **DZ-005**: 审查并改进非共线磁性初始化流程
  - 核心文件: 参数组合合法性矩阵
  - 工作量: 3-5 天
  - 依赖: DZ-001 + DZ-004

- **DZ-006**: 优化 SOC 开启时的内存占用
  - 核心文件: `source/source_estate/module_dm/density_matrix.cpp:30-41`
  - 工作量: 1-2 周
  - 依赖: 无（可独立推进）

- **DZ-007**: 单精度 PW 全面测试与加固
  - 核心文件: 7 组测试矩阵 (precision×nspin×backend)
  - 工作量: 3-5 天
  - 依赖: DZ-002 + DZ-004

### P2 — 用户支持与文档（3 个任务，互相独立）

- **DZ-008**: 回复 NO 配体电荷/磁性控制问题并提供工作流建议
  - 核心文件: `source/source_lcao/module_deltaspin/` (DeltaSpin 已实现)
  - 工作量: 1-2 天

- **DZ-009**: 评估并规划 constrained DFT / 局域磁矩约束功能
  - 核心文件: DeltaSpin vs VASP/QE 功能对比
  - 工作量: 3-5 天
  - 依赖: DZ-008

- **DZ-010**: 更新 toolchain 文档：InfiniBand/OFI 环境编译指南
  - 核心文件: `docs/advanced/install.md`
  - 工作量: 1 天
  - 依赖: DZ-003

## 依赖关系图

```
DZ-001 ──┐
          ├──→ DZ-005 (磁性初始化整体审查)
DZ-004 ──┘
          ├──→ DZ-007 (单精度全面测试)
DZ-002 ──┘

DZ-003 ──→ DZ-010 (编译文档)
DZ-008 ──→ DZ-009 (constrained DFT 评估)

DZ-006 (独立，SOC 内存优化)
```

## 执行建议

### 第一周（6 个无依赖任务并行启动）
- DZ-001 (nspin=4 磁矩 bug)
- DZ-002 (单精度 CUDA 错误)
- DZ-003 (OpenMPI 编译诊断)
- DZ-004 (init_chg=dm nspin=2)
- DZ-006 (SOC 内存优化)
- DZ-008 (NO 配体用户支持)

### 第二周（依赖任务启动）
- DZ-001/DZ-004 完成后 → DZ-005 (磁性初始化审查)
- DZ-002 完成后 → DZ-007 (单精度测试)
- DZ-003 完成后 → DZ-010 (编译文档)

### 第三周（收尾）
- DZ-008 完成后 → DZ-009 (constrained DFT 评估)
- 收尾 DZ-005, DZ-006, DZ-007

## Spec Doc 特色

每个任务的 spec doc 包含：

1. **Reference Code** — 从 ABACUS 源码中实际查找的文件路径、函数名、行号
2. **Implementation Guide** — 架构决策、数据结构映射、关键实现细节
3. **TDD Test Plan** — 具体的测试代码示例（C++ GoogleTest / Python pytest）
4. **Acceptance Criteria** — 可量化的验收标准

### 示例：DZ-001 (磁矩解析 bug)

```cpp
// Reference Code
source/source_cell/read_atoms_helper.cpp:302-309
  process_magnetization() — nspin==4 时的磁矩处理逻辑

// TDD Test
TEST_F(ReadAtomsTest, Nspin4NoncolinFalse_PreservesXYZ) {
    setup_nspin(4);
    setup_noncolin(false);
    set_atom_mag(0, 1.0, 1.0, 1.0);
    process_magnetization();
    EXPECT_NEAR(atom.m_loc_[0].x, 1.0, 1e-10);  // 不应被置零
}
```

### 示例：DZ-006 (SOC 内存优化)

内存热点分析（100 原子, 1000 基函数, 10 k 点）:

| 数据结构 | nspin=2 | nspin=4 | 增长倍数 |
|----------|---------|---------|---------|
| DMK | 80 MB | 640 MB | **8x** |
| HR | nnr×8 | nnr×16 | 2x |
| SOC sparse | 0 | 50-200 MB | ∞ |

优化方案：DMK 延迟分配 + 及时释放，预期收益 20%+

## 项目文件结构

```
projects/dyzheng-issues/
├── state/
│   └── project_state.json          # 项目状态（10 个任务）
├── docs/
│   └── tasks/
│       ├── DZ-001.md               # 磁矩解析 bug spec
│       ├── DZ-002.md               # 单精度 CUDA spec
│       ├── DZ-003.md               # OpenMPI 编译 spec
│       ├── DZ-004.md               # init_chg=dm nspin=2 spec
│       ├── DZ-005.md               # 磁性初始化审查 spec
│       ├── DZ-006.md               # SOC 内存优化 spec
│       ├── DZ-007.md               # 单精度测试 spec
│       ├── DZ-008.md               # NO 配体用户支持 spec
│       ├── DZ-009.md               # constrained DFT 评估 spec
│       └── DZ-010.md               # InfiniBand 编译文档 spec
├── dashboard.html                  # 任务看板
├── dependency_graph.dot            # 依赖图 (Graphviz)
└── dependency_graph.svg            # 依赖图 (SVG)
```

## 关键技术点

### 1. 磁性初始化 (DZ-001, DZ-005)
- nspin=4 时 noncolin 参数的正确处理
- 参数组合合法性矩阵（9 种组合）

### 2. 单精度计算 (DZ-002, DZ-007)
- CUDA memory_op 模板实例化
- float vs double 精度偏差标准 (<1e-4 Ry)

### 3. 密度矩阵初始化 (DZ-004)
- nspin=2 时 DMR[0] (spin-up) + DMR[1] (spin-down)
- CSR 文件格式读取

### 4. SOC 内存 (DZ-006)
- DMK: 4x 增长（spinor doubling + complex）
- 三层嵌套 map 的内存开销

### 5. 约束磁性 (DZ-008, DZ-009)
- DeltaSpin 已实现 Lagrange 乘子法
- 功能对比：ABACUS vs VASP vs QE

### 6. MPI 编译 (DZ-003, DZ-010)
- OpenMPI OFI/UCX 传输层配置
- InfiniBand 环境的三种解决方案

## 总工作量估算

- P0 (紧急): 6-10 天
- P1 (功能): 3-5 周
- P2 (支持): 5-12 天

**总计**: 约 6-8 周（假设串行执行）
**并行优化**: 约 3-4 周（充分利用并行机会）

## 下一步

1. 按优先级启动 P0 任务（DZ-001, DZ-002, DZ-003）
2. 同步启动无依赖的 P1 任务（DZ-004, DZ-006）
3. 完成 P0 后启动依赖任务（DZ-005, DZ-007, DZ-010）
4. 最后处理 P2 用户支持任务（DZ-008, DZ-009）
