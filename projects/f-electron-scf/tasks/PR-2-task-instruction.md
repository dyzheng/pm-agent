# PR-2: DFT+U PW SCF — nspin=1/2/4 全支持

## 任务目标

将 zdy-tmp 中 `cal_occ_pw()` 的 nspin=1/2 支持完整移植到 develop，使 DFT+U PW 基组的 SCF 计算支持 nspin=1、nspin=2、nspin=4 三种自旋模式。

## 背景

当前 develop 的 `dftu_pw.cpp` 中 `cal_occ_pw()` 仅实现了 nspin=4（SOC）路径。zdy-tmp 在此基础上增加了 nspin=1/2 的完整支持，包括占据矩阵计算、有效势构造、能量计算等。本 PR 的目标是将这些功能移植到 develop 的代码框架中。

## 工作环境

- worktree: `/root/abacus-dftu-pw-port`，分支 `feat/dftu-pw-port`
- 参考实现: `/root/abacus-zdy-tmp/source/module_hamilt_lcao/module_dftu/dftu_pw.cpp`
- develop 当前代码: `/root/abacus-dftu-pw-port/source/source_lcao/module_dftu/dftu_pw.cpp`
- API 映射表见 `CLAUDE.md` 中的"API 映射"section

## 功能需求

### R1: nspin=1/2 占据矩阵计算

`cal_occ_pw()` 必须根据 nspin 值选择正确的计算路径：
- nspin=4: 4-component spinor，becp 步长为 `2*nkb`，占据矩阵存储在 `locale[iat][l][0][0]` 的 4 个 spin 分量中
- nspin=1/2: scalar，becp 步长为 `nkb`，占据矩阵存储在 `locale[iat][l][0][is]`（is 由 k-point 的 spin index 决定）

CPU 和 GPU 代码路径必须保持一致。

### R2: spin-dependent 能量和有效势

DFT+U 能量 `energy_u` 和有效势 `eff_pot_pw` 的计算必须使用正确的 nspin-dependent 系数：
- nspin=1: 能量权重 1.0，对角系数 0.5
- nspin=2: 能量权重 0.5，对角系数 0.5，且需要分别计算 spin-up 和 spin-down 的 VU
- nspin=4: 能量权重 0.25，对角系数 1.0，且需要 Pauli→spin 基变换

Pauli→spin 基变换只在 nspin=4 时执行。

### R3: nspin=2 spin-down 有效势

nspin=2 时，spin-down 的有效势存储在 `eff_pot_pw` 的后半段（`eff_pot_pw[size/2 + index]`）。必须为 spin-down 单独构造 VU 矩阵。

### R4: `initialed_locale` 守卫与 `uom_array` 机制

参考 zdy-tmp 的实现，添加 `initialed_locale` 守卫：
- 首次进入时从 becp 投影计算占据矩阵，并保存到 `uom_array`
- 后续迭代（mixing 后）从 `uom_array` 恢复占据矩阵
- 需要在 `Plus_U` 类中添加 `uom_array`、`uom_save` 成员和 `set_locale()` 方法

### R5: `eff_pot_pw` 和 `uom_array` 的正确分配

确认并修正 `init()` 中的内存分配：
- nspin=2 时 `eff_pot_pw` 需要 2 倍空间
- `uom_array` 大小需要考虑 nspin 的 fold 因子
- `locale` 数组的第 4 维需要支持 `is=1` 索引

## 约束

### C1: 不引入 `Charge_Mixing::mix_uom()`

本 PR 使用 develop 现有的 `mix_locale()` 做占据矩阵 mixing。zdy-tmp 的 `Charge_Mixing::mix_uom()` Broyden mixing 策略留给后续 PR-6。

### C2: 不修改 `cal_occ_pw` 函数签名

保持 develop 当前的 `(iter, psi_in, wg_in, cell, mixing_beta)` 签名，不引入 `Charge_Mixing*` 参数。

### C3: 不修改 `esolver_ks_pw.cpp`

当前 esolver 中的调用已经正确，本 PR 不需要修改调用方。

### C4: API 适配

所有代码必须使用 develop 的 API 风格：
- `PARAM.inp.nspin` 而非 `GlobalV::NSPIN`
- `PARAM.inp.kpar` 而非 `GlobalV::KPAR`
- `psi_p->get_npol()` 而非 `psi_p->npol`
- `Plus_U::energy_u` 而非 `this->EU`
- 参数传递 `const UnitCell& cell` 而非 `GlobalC::ucell`

### C5: CPU/GPU 一致性

CPU 代码块和 GPU 代码块（`#if defined(__CUDA) || defined(__ROCM)`）中的 nspin 分支逻辑必须完全一致。

## 开发流程要求

### D1: 先读后写

修改任何文件前，必须先完整阅读该文件和 zdy-tmp 中的对应文件。特别注意：
- `dftu.cpp` 中 `eff_pot_pw` 和 `eff_pot_pw_index` 的分配逻辑
- `dftu.cpp` 中 `locale` 数组的分配逻辑（第 4 维是否支持 `is=1`）
- `dftu.h` 中现有的成员变量和方法

### D2: 增量编译

每完成一个逻辑变更后立即编译验证，不要积攒多个变更。

### D3: 遇到问题必须暂停

以下情况必须停下来向用户报告，不要自行假设：
- `locale` 数组维度不支持 nspin=2 的 `is=1` 索引
- `eff_pot_pw` 分配大小不足以容纳 nspin=2 的双倍数据
- 任何与 task instruction 描述不一致的代码结构
- 编译错误重试 2 次仍无法解决

## 测试验收要求（MANDATORY）

**以下所有测试要求必须完成，缺失任何一项则 PR 不接受。**

### Gate 1: 编译

```bash
cd /root/abacus-dftu-pw-port/build
cmake --build . -j$(nproc) 2>&1 | tee /tmp/build.log
```

- 零 `error:` 行
- 生成可执行文件
- 保留编译日志

### Gate 2: 单元测试

必须为以下功能点编写 gtest 单元测试：

1. nspin=1/2/4 的能量权重和对角系数计算
2. nspin=1/2 vs nspin=4 的 becp index 步长差异
3. `set_locale()` 在 nspin=2 和 nspin=4 下的 uom_array→locale 拷贝正确性
4. nspin=2 时 spin-down VU 矩阵的构造

测试文件位置: `source/source_lcao/module_dftu/test/`
运行命令: `ctest --test-dir <build测试目录> -j4 --output-on-failure`
要求: 全部 PASS，0 FAIL

如果依赖链过重无法直接构造对象，将计算逻辑提取为可独立测试的函数。**不允许以依赖链重为由跳过测试。**

### Gate 3: 集成测试

回归测试:
```bash
cd /root/abacus-dftu-pw-port/tests/integrate
bash Autotest.sh -a /root/abacus-dftu-pw-port/build/abacus -n 4 -r "099_PW_DJ_SO"
```

新增测试 case:
- `tests/01_PW/100_PW_DFTU_S2/` — PW DFT+U nspin=2，Fe2 反铁磁体系
- `tests/01_PW/101_PW_DFTU_S1/` — PW DFT+U nspin=1，Fe2 体系

每个 case 必须包含: INPUT, STRU, KPT, result.ref, README。
参考现有 case `099_PW_DJ_SO` 的格式。

### Gate 4: 代码审查

- 修改与 zdy-tmp 参考代码逻辑一致
- API 适配正确（无 GlobalV/GlobalC 残留）
- 无 debug print、无 WIP 代码、无未使用 include

## 验收证据

任务完成后必须提供完整的验收证据报告（格式见 CLAUDE.md）。可使用 `/verify` 命令执行完整验收流程。

## 完成后

- commit 到 worktree，不要 push
- commit message 以 `feat: extend DFT+U PW to support nspin=1/2` 开头
- 等待 PM review 后再 push
