# QE PHonon DFPT Migration to ABACUS

将 Quantum ESPRESSO PHonon 包中的 DFPT 功能迁移到 ABACUS C++ 代码库。

**项目状态：** ✓ 规划完成 - 准备执行

**开始日期：** 2026-02-20
**目标完成日期：** 2027-03-31 (13个月)
**当前阶段：** Phase 1 准备中

## 快速导航

📋 **规划文档**
- [项目章程](PROJECT_CHARTER.md) - 目标、范围、里程碑、风险
- [项目总结](PROJECT_SUMMARY.md) - 完整项目概览和状态
- [任务分解](manual_plan.json) - 16个任务的详细定义

📊 **可视化**
- [项目仪表板](dashboard.html) - 交互式看板、时间线、依赖图
- [依赖关系图](dependency_graph.svg) - 任务依赖可视化

🔬 **分析文档**
- [项目分析](research/project_analysis.md) - 可行性、风险、资源评估
- [优化建议](optimization/optimization_recommendations.md) - 任务拆分和并行化策略

🛠️ **实施指南**
- [实施指南](IMPLEMENTATION_GUIDE.md) - 开发流程、编码规范、测试策略
- [里程碑评审模板](MILESTONE_REVIEW_TEMPLATE.md) - 里程碑评审流程

## 项目概述

**目标：** 将 QE PHonon 的密度泛函微扰理论（DFPT）功能用 C++ 重新实现并集成到 ABACUS 电子结构计算软件包中。

**源代码：**
- QE PHonon: `/root/q-e/PHonon/` (183个Fortran文件)
- 已有C++实现: `/root/q-e/PHonon/dvqpsi_cpp/` (独立的核心kernel实现)

**目标代码库：**
- ABACUS: `/root/abacus-dfpt/abacus-develop/`

**代码审核参考：**
- Code Review Agent: `/root/code-review-agent/` (6-agent并发审核 + 3-agent串行迁移工作流)

## 核心需求

1. **物理正确性：** 保持与 QE 相同的物理精度和数值结果
2. **架构集成：** 利用 ABACUS 现有模块（module_pw, module_hamilt_pw, module_elecstate）
3. **性能达标：** 性能与 QE 相当或更优
4. **代码质量：** 通过多维度代码审核（物理、算法、数值稳定性）
5. **完整测试：** 单元测试 + 集成测试 + 与 QE 对比验证

## 技术栈

| 组件 | 技术 |
|------|------|
| 源语言 | Fortran 90/95 (QE PHonon) |
| 目标语言 | C++11/14 (ABACUS) |
| 构建系统 | CMake |
| 测试框架 | GoogleTest (单元测试) + abacustest (集成测试) |
| 并行 | MPI + OpenMP |
| 数学库 | BLAS/LAPACK, FFTW3, ScaLAPACK |

## 关键组件（按优先级）

1. **核心 DFPT kernel** (dV/dτ·ψ) - 已在 dvqpsi_cpp 中实现
2. **Sternheimer 求解器** (H-ε)·Δψ = -ΔV·ψ
3. **自洽场迭代** (SCF loop for DFPT)
4. **声子动力学矩阵计算**
5. **电声耦合矩阵元**
6. **对称性操作和约化**
7. **并行化**（k点、q点、不可约表示）

## 项目阶段

### Phase 1: 基础设施和架构设计 (3 tasks)
- DFPT-001: 设计 ABACUS DFPT 模块架构
- DFPT-002: 建立代码审核工作流
- DFPT-003: 创建 DFPT 模块骨架和构建系统

### Phase 2: 核心 DFPT Kernel 迁移 (3 tasks)
- DFPT-101: 迁移数据结构适配层
- DFPT-102: 迁移 DVQPsiUS 核心 kernel
- DFPT-103: 迁移 Sternheimer 求解器

### Phase 3: 自洽场和声子计算 (3 tasks)
- DFPT-201: 实现 DFPT 自洽场迭代
- DFPT-202: 实现动力学矩阵计算
- DFPT-203: 实现电声耦合计算

### Phase 4: 并行化和优化 (2 tasks)
- DFPT-301: 实现 MPI 并行化
- DFPT-302: 性能优化和基准测试

### Phase 5: ESolver 集成和用户接口 (2 tasks)
- DFPT-401: 创建 ESolver_DFPT 类
- DFPT-402: 实现 q 点网格和工作流

### Phase 6: 测试和文档 (3 tasks)
- DFPT-501: 创建集成测试套件
- DFPT-502: 编写用户文档
- DFPT-503: 编写开发者文档

## 质量保证

### 代码审核流程

使用 code-review-agent 的多维度审核：

**6-agent 并发审核：**
1. **单位一致性** (review-units): 检查物理单位和量纲
2. **物理守恒律** (review-physics): 验证能量守恒、电荷守恒等
3. **算法匹配** (review-algorithm): 确保算法与物理问题匹配
4. **代码风格** (review-style): 检查命名语义和代码结构
5. **调用链分析** (review-callchain): 追踪物理量流动
6. **防御性编程** (review-debug): 检查边界条件和错误处理

**3-agent 串行迁移工作流：**
1. **源代码分析** (review-migrate-source): 提取 QE 算法特征
2. **目标代码模式** (review-migrate-target): 提取 ABACUS 实现模式
3. **差异对比** (review-migrate-diff): 生成适配计划

### 验证策略

1. **数值验证：** 与 QE 参考结果对比（声子频率误差 < 0.1 cm⁻¹）
2. **物理验证：** 检查声学和规范、LO-TO 劈裂等物理约束
3. **性能验证：** 与 QE 性能对比，确保相当或更优
4. **并行验证：** 测试 MPI 并行效率（> 80% @ 16进程）

## 项目文件

- **项目规划：** `manual_plan.json` - 完整的任务分解和依赖关系
- **项目状态：** `state/project_state.json` - 当前执行状态
- **依赖图：** `dependency_graph.svg` - 任务依赖关系可视化
- **项目看板：** `dashboard.html` - 交互式项目仪表板

## 查看项目进度

```bash
# 在浏览器中打开项目看板
open projects/qe-dfpt-migration/dashboard.html

# 查看依赖关系图
open projects/qe-dfpt-migration/dependency_graph.svg

# 查看项目状态
cat projects/qe-dfpt-migration/state/project_state.json | jq '.tasks[] | {id, title, status}'
```

## 关键风险

1. **物理正确性验证：** 需要与 QE 详细对比，确保所有物理量计算正确
2. **性能达标：** 需要优化到与 QE 性能相当的水平
3. **MPI 并行化复杂度：** k点、q点、不可约表示的并行分布需要仔细设计
4. **对称性操作：** 对称性约化和对称化操作的正确性至关重要

## 预估时间线

- **总任务数：** 16 tasks
- **预估工期：** 6-9 个月
- **关键路径：** DFPT-001 → DFPT-003 → DFPT-101 → DFPT-102 → DFPT-103 → DFPT-201 → DFPT-202 → DFPT-203 → DFPT-301 → DFPT-302 → DFPT-401 → DFPT-402 → DFPT-501

## 交付物

1. **代码：** 集成到 ABACUS 的 module_dfpt 模块
2. **测试：** 单元测试 + 集成测试套件（≥10个测试用例）
3. **文档：**
   - 用户手册（DFPT_USER_GUIDE.md）
   - 开发者文档（DFPT_DEVELOPER_GUIDE.md）
   - 算法细节（DFPT_ALGORITHM_DETAILS.md）
4. **报告：**
   - 性能基准报告（DFPT_PERFORMANCE.md）
   - 代码审核报告汇总（DFPT_CODE_REVIEW_SUMMARY.md）

## 参考资源

- **QE PHonon 文档：** `/root/q-e/PHonon/CLAUDE.md`
- **ABACUS 文档：** `/root/abacus-dfpt/abacus-develop/CLAUDE.md`
- **dvqpsi_cpp 实现：** `/root/q-e/PHonon/dvqpsi_cpp/README.md`
- **Code Review Agent：** `/root/code-review-agent/CLAUDE.md`
- **DFPT 理论：** S. Baroni et al., Rev. Mod. Phys. 73, 515 (2001)

## 联系方式

项目管理工具：PM Agent (pm-agent)
- 项目目录：`/root/pm-agent/projects/qe-dfpt-migration/`
- 工具文档：`/root/pm-agent/CLAUDE.md`
