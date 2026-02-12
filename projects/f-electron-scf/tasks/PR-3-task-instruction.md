# PR-3: DeltaSpin 缺失文件移植

## 任务目标

将 zdy-tmp 中 3 个 DeltaSpin 实现文件移植到 develop，补全 DeltaSpin 模块的核心功能。

## 背景

develop 的 `module_deltaspin` 已有大部分文件（basic_funcs, cal_mw, cal_mw_from_lambda, init_sc, lambda_loop, lambda_loop_helper, spin_constrain 等），但缺少 3 个实现文件和对应的测试。这些文件在 zdy-tmp 中存在，需要移植并适配 develop 的 API 风格。

## 工作环境

- worktree: `/root/abacus-dftu-pw-port`，分支 `feat/dftu-pw-port`
- 参考实现: `/root/abacus-zdy-tmp/source/module_hamilt_lcao/module_deltaspin/`
- develop 当前代码: `/root/abacus-dftu-pw-port/source/source_lcao/module_deltaspin/`

## 前置依赖

无。本 PR 独立于 PR-1 和 PR-2。

## 功能需求

### R1: 移植 `cal_h_lambda.cpp`

计算 H_lambda 算符（LCAO 下的自旋约束哈密顿量贡献）。

zdy-tmp 文件: `module_hamilt_lcao/module_deltaspin/cal_h_lambda.cpp`（约 107 行）

### R2: 移植 `cal_mw_helper.cpp`

磁矩计算的辅助函数。

zdy-tmp 文件: `module_hamilt_lcao/module_deltaspin/cal_mw_helper.cpp`（约 167 行）

### R3: 移植 `sc_parse_json.cpp`

自旋约束配置的 JSON 解析。

zdy-tmp 文件: `module_hamilt_lcao/module_deltaspin/sc_parse_json.cpp`（约 3 行，可能只是 stub）

### R4: 移植对应的测试文件

zdy-tmp 中存在但 develop 缺失的测试:
- `cal_h_lambda_test.cpp`
- `cal_mw_helper_test.cpp`
- `init_sc_test.cpp`

## 约束

### C1: API 适配

zdy-tmp 和 develop 之间有以下关键差异，移植时必须适配：

- 命名空间: zdy-tmp 无命名空间 → develop 使用 `namespace spinconstrain`
- 方法名: `cal_MW()` → `cal_mi_lcao()`，`cal_Mi_pw()` → `cal_mi_pw()`
- 目录路径: `module_hamilt_lcao/module_deltaspin/` → `source/source_lcao/module_deltaspin/`
- 全局变量: `GlobalC::ucell` → 参数传递，`GlobalV::NSPIN` → `PARAM.inp.nspin`

### C2: 与现有代码一致

新增文件的代码风格、include 路径、类接口必须与 develop 中已有的 deltaspin 文件一致。先阅读 develop 的 `spin_constrain.h` 了解当前类定义。

### C3: CMakeLists.txt 更新

新增的 .cpp 文件必须加入 `source/source_lcao/module_deltaspin/CMakeLists.txt`。测试文件加入对应的 test/CMakeLists.txt。

## 开发流程要求

### D1: 先读后写

移植前必须完整阅读：
- develop 的 `spin_constrain.h`（了解当前类定义和命名空间）
- develop 中已有的 deltaspin 文件（了解代码风格和 API 模式）
- zdy-tmp 的 3 个源文件和 3 个测试文件

### D2: 逐文件移植

每移植一个文件后立即编译验证，不要一次性移植所有文件。

### D3: 遇到问题必须暂停

以下情况停下来报告：
- zdy-tmp 文件引用了 develop 中不存在的类或方法
- 命名空间适配导致编译错误重试 2 次仍无法解决
- 测试文件依赖 develop 中不存在的 test fixture

## 测试验收要求（MANDATORY）

### Gate 1: 编译

```bash
cd /root/abacus-dftu-pw-port/build
cmake --build . -j$(nproc) 2>&1 | tee /tmp/build.log
```

- 零 error
- 保留编译日志

### Gate 2: 单元测试

移植的 3 个测试文件必须全部通过：
- `cal_h_lambda_test.cpp` 中所有 test case PASS
- `cal_mw_helper_test.cpp` 中所有 test case PASS
- `init_sc_test.cpp` 中所有 test case PASS

如果 zdy-tmp 的测试依赖不存在的 fixture，需要适配或重写测试，但不允许跳过。

运行命令: `ctest --test-dir <build测试目录> -j4 --output-on-failure`

### Gate 3: 集成测试

运行现有 deltaspin 相关集成测试的回归验证（如果存在）。

### Gate 4: 代码审查

- API 适配正确（命名空间、方法名、参数传递）
- 无 GlobalC/GlobalV 残留
- 无 debug print
- include 路径正确

## 完成后

- commit 到 worktree，不要 push
- commit message 以 `feat: port missing deltaspin files (cal_h_lambda, cal_mw_helper, sc_parse_json)` 开头
- 等待 PM review
