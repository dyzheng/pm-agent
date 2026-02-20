# QE PHonon DFPT Migration to ABACUS - Project Charter

**Version:** 1.0
**Date:** 2026-02-20
**Project ID:** qe-dfpt-migration

## Executive Summary

### Overview
将 Quantum ESPRESSO PHonon 包中的密度泛函微扰理论（DFPT）功能用 C++ 重新实现并集成到 ABACUS 电子结构计算软件包中。

### Business Value
为 ABACUS 添加完整的声子计算和电声耦合功能，使其成为功能完备的第一性原理计算软件包，支持材料的动力学性质研究。

### Strategic Alignment
支持 deepmodeling 生态系统的完整性，为多尺度材料模拟提供基础能力。

## Objectives

### Primary Objectives
1. 将 QE PHonon 的 DFPT 功能完整迁移到 ABACUS
2. 保持与 QE 相同的物理精度（声子频率误差 < 0.1 cm⁻¹）
3. 性能达到或超过 QE 水平
4. 建立完整的测试和验证体系

### Secondary Objectives
1. 建立代码审核工作流（6-agent 并发 + 3-agent 串行迁移）
2. 创建完整的用户和开发者文档
3. 为未来扩展（如 Raman 光谱、介电常数）奠定基础

## Scope

### In Scope
- 核心 DFPT kernel 迁移（dV/dτ·ψ）
- Sternheimer 求解器实现
- DFPT 自洽场迭代
- 声子动力学矩阵计算
- 电声耦合矩阵元计算
- MPI + OpenMP 并行化
- 与 ABACUS 现有模块集成（module_pw, module_hamilt_pw）
- 单元测试和集成测试
- 用户文档和开发者文档

### Out of Scope
- Raman 光谱计算（未来扩展）
- 介电常数计算（未来扩展）
- GPU 加速（未来优化）
- 非线性声子效应
- QE 的所有后处理工具（仅实现核心功能等效）

### Assumptions
- ABACUS 现有模块（module_pw, module_hamilt_pw）功能稳定
- dvqpsi_cpp 的核心 kernel 实现正确且可复用
- code-review-agent 工具可用且配置正确
- 有足够的计算资源进行性能基准测试

### Constraints
- 必须保持与 QE 的数值一致性
- 必须遵循 ABACUS 的代码风格和架构
- 性能不能显著低于 QE
- 必须通过多维度代码审核

## Milestones

### M1: 基础设施就绪
**Target Date:** 2026-03-31
**Tasks:** DFPT-001, DFPT-002, DFPT-003

**Deliverables:**
- DFPT_ARCHITECTURE.md
- code-review-agent 配置
- module_dfpt 骨架和构建系统

**Success Criteria:**
- 架构设计通过技术评审
- 代码审核工作流测试通过
- 空模块可以成功编译

### M2: 核心 Kernel 迁移完成
**Target Date:** 2026-06-30
**Tasks:** DFPT-101, DFPT-102, DFPT-103

**Deliverables:**
- 数据结构适配器
- DVQPsiUS 核心 kernel
- Sternheimer 求解器

**Success Criteria:**
- 与 dvqpsi_cpp 数值结果一致（误差 < 1e-10）
- 与 QE 参考结果一致
- 单元测试全部通过
- 代码审核通过

### M3: 声子计算功能完成
**Target Date:** 2026-09-30
**Tasks:** DFPT-201, DFPT-202, DFPT-203

**Deliverables:**
- DFPT SCF 循环
- 动力学矩阵计算
- 电声耦合计算

**Success Criteria:**
- 声子频率与 QE 一致（误差 < 0.1 cm⁻¹）
- 支持声学和规范和
- EPC 矩阵元与 QE 一致
- 集成测试通过

### M4: 并行化和性能优化
**Target Date:** 2026-11-30
**Tasks:** DFPT-301, DFPT-302

**Deliverables:**
- MPI 并行实现
- 性能基准报告

**Success Criteria:**
- 并行效率 > 80%（16 进程）
- 性能与 QE 相当或更优
- 负载均衡良好

### M5: 集成和用户接口
**Target Date:** 2027-01-31
**Tasks:** DFPT-401, DFPT-402

**Deliverables:**
- ESolver_DFPT 类
- q 点网格工作流
- 后处理工具

**Success Criteria:**
- 可通过 INPUT 文件调用
- 支持恢复中断的计算
- 端到端测试通过

### M6: 项目交付
**Target Date:** 2027-03-31
**Tasks:** DFPT-501, DFPT-502, DFPT-503

**Deliverables:**
- 集成测试套件（≥10 个测试用例）
- 用户文档
- 开发者文档
- 性能基准报告
- 代码审核报告汇总

**Success Criteria:**
- 所有测试通过
- 与 QE 结果一致性验证完成
- 文档评审通过
- 项目可以正式发布

## Risk Management

### R1: 物理正确性验证困难
**Category:** Technical
**Impact:** High | **Probability:** Medium

**Mitigation:**
- 与 QE 详细对比每个中间结果
- 使用多个测试体系验证
- 建立自动化验证流程
- 咨询 QE 和 ABACUS 领域专家

### R2: 性能无法达到 QE 水平
**Category:** Technical
**Impact:** High | **Probability:** Medium

**Mitigation:**
- 参考 dvqpsi_cpp 的优化经验
- 使用性能分析工具识别热点
- 优化关键循环和数据访问模式
- 考虑使用更高效的数学库

### R3: MPI 并行化复杂度高
**Category:** Technical
**Impact:** Medium | **Probability:** High

**Mitigation:**
- 参考 QE 和 ABACUS 现有并行方案
- 先实现简单的 k 点并行
- 逐步添加 q 点和不可约表示并行
- 充分测试并行正确性和效率

### R4: 对称性操作实现错误
**Category:** Technical
**Impact:** High | **Probability:** Medium

**Mitigation:**
- 复用 ABACUS 现有对称性模块
- 与 QE 对称性处理逐步对比
- 使用高对称性体系测试
- 代码审核重点关注对称性部分

### R5: 开发时间超出预期
**Category:** Resource
**Impact:** Medium | **Probability:** Medium

**Mitigation:**
- 优先实现核心功能
- 将非关键功能标记为未来扩展
- 定期评估进度并调整计划
- 必要时增加开发资源

### R6: ABACUS 模块接口变化
**Category:** Integration
**Impact:** Medium | **Probability:** Low

**Mitigation:**
- 与 ABACUS 核心开发团队保持沟通
- 使用稳定的 ABACUS 版本
- 设计适配层隔离接口变化
- 及时跟踪 ABACUS 更新

## Success Criteria

### Technical Criteria
- 声子频率与 QE 一致（误差 < 0.1 cm⁻¹）
- EPC 矩阵元与 QE 一致
- 性能与 QE 相当或更优
- MPI 并行效率 > 80%（16 进程）
- 所有单元测试和集成测试通过
- 代码审核通过（6 个维度）

### Quality Criteria
- 代码覆盖率 > 80%
- 无已知的严重 bug
- 代码风格符合 ABACUS 规范
- 文档完整且准确

### Deliverables
- 集成到 ABACUS 的 module_dfpt 模块
- ≥10 个集成测试用例
- 用户手册和开发者文档
- 性能基准报告
- 代码审核报告汇总

## Resources

### Team
| Role | Allocation | Duration |
|------|-----------|----------|
| Architect | 20% | 1 month |
| Physics Developer | 100% | 9 months |
| Algorithm Developer | 100% | 6 months |
| C++ Developer | 50% | 4 months |
| HPC Developer | 100% | 3 months |
| Test Engineer | 50% | 6 months |
| Technical Writer | 30% | 2 months |

### Infrastructure
- HPC 集群（用于性能测试和基准对比）
- code-review-agent 工具
- CI/CD 系统（自动化测试）
- QE 和 ABACUS 开发环境

### External Dependencies
- QE PHonon 源代码（/root/q-e/PHonon/）
- dvqpsi_cpp 参考实现（/root/q-e/PHonon/dvqpsi_cpp/）
- ABACUS 代码库（/root/abacus-dfpt/abacus-develop/）
- code-review-agent（/root/code-review-agent/）

## Timeline

**Start Date:** 2026-02-20
**Target End Date:** 2027-03-31
**Total Duration:** 13 months

| Phase | Name | Duration | Tasks |
|-------|------|----------|-------|
| Phase 1 | 基础设施和架构设计 | 1.5 months | 3 |
| Phase 2 | 核心 DFPT Kernel 迁移 | 3 months | 3 |
| Phase 3 | 自洽场和声子计算 | 3 months | 3 |
| Phase 4 | 并行化和优化 | 2 months | 2 |
| Phase 5 | ESolver 集成和用户接口 | 2 months | 2 |
| Phase 6 | 测试和文档 | 1.5 months | 3 |

## Governance

### Review Frequency
Bi-weekly progress reviews

### Stakeholders
| Stakeholder | Role | Involvement |
|------------|------|-------------|
| ABACUS Core Team | Technical Review | High |
| QE PHonon Experts | Domain Consultation | Medium |
| deepmodeling Community | User Feedback | Low |

### Decision Authority
ABACUS Core Team

### Escalation Path
Project Lead → ABACUS Core Team → deepmodeling Steering Committee

## Approval

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Project Sponsor | | | |
| Technical Lead | | | |
| ABACUS Core Team | | | |

---

**Document Control:**
- Version: 1.0
- Last Updated: 2026-02-20
- Next Review: 2026-03-06
