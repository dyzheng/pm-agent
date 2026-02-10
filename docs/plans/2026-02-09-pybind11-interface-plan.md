# ABACUS PyBind11 开发计划：接口重构与全局状态解耦

## 问题概述

ABACUS pybind11 开发面临三大架构障碍：

1. **数据接口缺失**：~60% 模块有 Python 绑定，但 ML 训练关键数据（XC 势、DFT+U 占据矩阵、非局域投影算子）完全未暴露
2. **全局状态深度耦合**：`PARAM`（422 文件/4348 引用）、`GlobalV`（322 文件）、`timer`（277 文件）均为全局单例，阻止多实例、并发和状态复用
3. **隐式依赖传播**：`Input_Conv::Convert()` 将 PARAM 值复制到 50+ 类的 static 成员，创建不可见的初始化依赖链

---

## 一、当前 PyABACUS 绑定覆盖分析

### 已有绑定（可用）

| 模块 | Accessor | 数据 | 状态 |
|---|---|---|---|
| 能量 | `EnergyAccessor` | etot, eband, hartree, etxc, ewald, exx, evdw | 完整 |
| 力 | `ForceAccessor` | forces[nat,3] | 完整 |
| 应力 | `StressAccessor` | stress[3,3], voigt[6] | 完整 |
| 电荷密度 | `ChargeAccessor` | rho[nspin,nrxx], rhog[nspin,ngmc], rho_core | 完整 |
| Hamiltonian | `HamiltonianAccessor` | H(k), S(k), H(R), S(R) — 仅 LCAO | 完整 |
| 密度矩阵 | `DensityMatrixAccessor` | DM(k), DM(R) — 仅 LCAO | 完整 |
| 波函数 | `get_psi(ik)` | 系数 psi[nbands,nbasis] | 仅系数 |
| 本征值 | `get_eigenvalues(ik)` | ekb[nbands] per k | 完整 |
| 几何结构 | `get/update_positions/cell` | 读写 | 完整 |
| SCF 控制 | workflow callbacks | before_scf, after_iter, before_after_scf, after_scf | 完整 |

### 缺失绑定（阻塞 ML 训练和高级分析）

| 模块 | C++ 数据位置 | 有 C++ 访问接口? | Python 暴露? | 影响 |
|---|---|---|---|---|
| **有效势 V_eff(r)** | `Potential::v_eff` | `get_eff_v(spin)` 存在 | **NO** | 阻塞 ML 势训练 |
| **XC 势 V_xc(r)** | `Potential` 内部 | 有 getter | **NO** | 物理信息 ML 需要 |
| **Hartree 势** | `Potential` 内部 | 有 getter | **NO** | 同上 |
| **动能密度 tau(r)** | `Charge::kin_r` | public 指针 | **NO** | meta-GGA 分析必需 |
| **密度梯度 nabla_rho** | 计算时产生不存储 | 无 | **NO** | GGA 描述符 |
| **DFT+U 占据矩阵** | `Plus_U::locale[iat][l][n][spin]` | public 成员 | **NO** | 关联体系必需 |
| **非局域投影 <beta\|psi>** | `VNL_in_pw::vkb`, `deeq` | 无简单 getter | **NO** | ML 力场开发 |
| **实空间波函数 psi(r)** | 需 FFT 变换 | 无 | **NO** | 特征工程 |
| **投影态密度 PDOS** | 计算时产生 | 无 Python 接口 | **NO** | 电子结构 ML |
| **能带结构** | 计算时产生 | 无 k-path 接口 | **NO** | 后处理 |
| **力分量分解** | forces.cpp 内部 | 计算但不单独存储 | **NO** | 可解释性 |
| **磁化密度 m(r)** | nspin=4 时在 rho 中 | 无专门接口 | **NO** | 自旋 ML |
| **DeePKS V_delta** | LCAO_deepks 内部 | 有 interface.h | **NO** | ML-DFT 训练 |

---

## 二、全局状态清单

### PARAM — 核心参数单例（最严重）

```
定义: source/source_io/module_parameter/parameter.h
类型: extern Parameter PARAM (全局单例)
影响: 422 个文件, 4348 次引用
内容: ~300+ 输入参数 (PARAM.inp) + ~68 系统参数 (PARAM.globalv)
```

**问题：**
- 无法创建多个 ESolver 实例（共享同一 PARAM）
- 无法从 Python 动态修改参数（必须通过 INPUT 文件）
- 无法在 Python 调用间重置状态

### GlobalV — 全局变量命名空间

```
定义: source/source_base/global_variable.h
类型: namespace GlobalV { extern int NPROC, MY_RANK, ...; extern ofstream ofs_running; }
影响: 322 个文件, 2324 次引用
内容: MPI rank/size, k-point pool 信息, 输出流
```

**问题：**
- `ofs_running` 全局输出流绑定到单一输出目录
- MPI 状态假设一个进程只有一个 rank

### ModuleBase::timer — 全局计时器

```
定义: source/source_base/timer.h
类型: static map<string, map<string, Timer_One>> timer_pool
影响: 277 个文件, 1171 次调用
```

**问题：**
- 无 reset() 方法 — 计时累积跨 Python 调用
- 非线程安全（static map 无锁）

### ModuleBase::Memory — 全局内存追踪

```
定义: source/source_base/memory.h
类型: static double total; static string* name; ...
影响: 28 个文件, 112 次调用
```

### Input_Conv::Convert() — 隐式状态传播

```
定义: source/source_io/input_conv.cpp
效果: 将 PARAM 值复制到 50+ 类的 static 成员
```

**被影响的类示例：**
- `ModuleSymmetry::Symmetry::symm_flag`
- `Plus_U::Yukawa`, `Plus_U::U`, `Plus_U::orbital_corr`
- `BFGS_Basic::relax_bfgs_w1`
- `elecstate::Efield::efield_dir`
- `TD_info::out_current`
- 等 40+ 个 static 成员

### 初始化顺序依赖链

```
MPI_Init()
  → PARAM.set_pal_param(rank, nproc, nthread)
    → GlobalV::MY_RANK = rank, GlobalV::NPROC = nproc
      → ReadInput.read_parameters(PARAM, "INPUT")
        → ReadInput.create_directory(PARAM)    [opens GlobalV::ofs_running]
          → Input_Conv::Convert()              [propagates to 50+ statics]
            → timer::start()
              → Parallel_Global::init_pools()  [sets MY_POOL, etc.]
                → UnitCell.setup()
                  → ESolver::init()            [reads PARAM everywhere]
```

任何模块在此链完成前使用都会 segfault 或产生垃圾结果。

---

## 三、开发计划

### Phase 1: 数据接口补全（不动全局状态，纯增量）

优先级排序：按 ML 训练工作流的阻塞程度

#### P1-1: PotentialAccessor — V_eff, V_xc, V_Hartree

```
新文件: python/pyabacus/src/ModuleESolver/py_potential_accessor.hpp
修改:   python/pyabacus/src/ModuleESolver/py_esolver_bindings.cpp

方案: 包装 elecstate::Potential 的现有 getter:
  - get_eff_v(spin) → double* 已存在
  - 需要找到 V_xc 和 V_Hartree 的单独存储

暴露 API:
  esolver.get_potential() → PotentialAccessor
    .get_veff(spin) → np.array[nrxx]
    .get_vofk(spin) → np.array[nrxx]  # meta-GGA kinetic potential
    .get_fixed_v() → np.array[nrxx]    # local ionic + Hartree + ...
```

#### P1-2: DFT+U OccupationAccessor

```
新文件: python/pyabacus/src/ModuleESolver/py_dftu_accessor.hpp
修改:   python/pyabacus/src/ModuleESolver/py_esolver_bindings.cpp

方案: 包装 Plus_U::locale (public 成员)

暴露 API:
  esolver.get_dftu() → DFTUAccessor
    .get_occupation_matrix(iat, l, n, spin) → np.array[2l+1, 2l+1]
    .get_U_values() → dict[atom_type → float]
    .get_orbital_corr() → list[int]
    .is_converged() → bool
```

#### P1-3: ChargeAccessor 扩展 — tau(r)

```
修改: python/pyabacus/src/ModuleESolver/py_charge_accessor.hpp

方案: Charge::kin_r 是 public 指针，meta-GGA 时已计算

新增 API:
  charge_accessor.get_tau(spin) → np.array[nrxx]   # 动能密度
  charge_accessor.get_nhat(spin) → np.array[nrxx]  # PAW 增强电荷（如有）
```

#### P1-4: ProjectorAccessor — <beta|psi>

```
新文件: python/pyabacus/src/ModuleESolver/py_projector_accessor.hpp

方案: 包装 OnsiteProjector 或 VNL_in_pw

暴露 API:
  esolver.get_projectors() → ProjectorAccessor
    .get_becp(ik) → np.array[nkb, nbands]   # <beta|psi> 投影
    .get_deeq() → np.array[ntype, nhm, nhm, nspin]  # D_ij 系数
    .nkb, lmaxkb properties
```

#### P1-5: 力分量分解

```
修改: python/pyabacus/src/ModuleESolver/py_force_accessor.hpp

方案: forces.cpp 内部已分别计算各分量，但求和后丢弃。
      需在 C++ 侧保存各分量到 ESolver 成员。

暴露 API:
  force_accessor.get_force_components() → dict
    {"local": array, "nonlocal": array, "ewald": array,
     "xc": array, "hartree": array, "vdw": array, "dftu": array}
```

#### P1-6: 实空间波函数 + 网格信息

```
方案A (Python 侧): 用 get_psi(ik) 系数 + FFT 网格信息做 Python FFT
方案B (C++ 侧): 在 C++ 做 FFT 后返回 psi(r)

推荐方案A — 更灵活，需暴露:
  esolver.get_fft_dims() → (nx, ny, nz)
  esolver.get_gvec(ik) → np.array[npw, 3]  # G-向量索引
```

### Phase 2: 全局状态最小化解耦

不做大规模重构（影响 400+ 文件），而是做**最小侵入性修复**。

#### P2-1: Timer/Memory 添加 reset() 和 disable()

```
修改: source/source_base/timer.h/.cpp

新增:
  static void reset() { timer_pool.clear(); n_now = 0; }
  static void disable() { disabled = true; }
  static void enable() { disabled = false; }

修改: source/source_base/memory.h/.cpp

新增:
  static void reset() { total = 0; n_now = 0; }
```

在 PyABACUS ESolver 的 `cleanup()` 中调用 reset。

#### P2-2: PARAM 支持 Python 字典初始化（绕过 INPUT 文件）

```
新文件: python/pyabacus/src/utils/py_param_init.hpp

方案: 增加一个 init_from_dict(py::dict) 方法:
  PARAM.inp.ecutwfc = dict["ecutwfc"].cast<double>();
  PARAM.inp.basis_type = dict["basis_type"].cast<string>();
  ...
  Input_Conv::Convert();  // 仍需调用

效果: Python 可以不依赖 INPUT 文件:
  esolver = ESolverLCAO()
  esolver.initialize_from_dict({
      "ecutwfc": 100, "basis_type": "lcao",
      "nspin": 2, "gamma_only": True, ...
  })
```

#### P2-3: ESolver 状态 cleanup 增强

```
修改: python/pyabacus/src/ModuleESolver/py_esolver_*.cpp

在 cleanup() 中增加:
  - ModuleBase::timer::reset()
  - ModuleBase::Memory::reset()
  - 关闭并重新打开 GlobalV::ofs_running
  - 重置 Input_Conv::Convert() 设置的 static 成员（列表式）
```

#### P2-4: 全局输出流重定向

```
方案: ESolver 实例拥有自己的输出流
  - esolver->ofs_running_ (实例成员)
  - 初始化时 redirect GlobalV::ofs_running 到 esolver->ofs_running_
  - cleanup 时恢复

效果: 不同 ESolver 实例输出到不同目录
```

### Phase 3: 长期架构重构（可选，高影响高风险）

#### P3-1: PARAM 实例化

```
目标: extern Parameter PARAM → ESolver 构造函数参数
影响: 422 文件, ~4348 处修改
方案:
  1. 在 ESolver 添加 Parameter* param_ 成员
  2. 逐模块替换 PARAM. → param_->
  3. 保留 extern PARAM 作为兼容层（指向当前活跃 ESolver 的 param）
  4. 分 10+ PR 完成
```

#### P3-2: Input_Conv::Convert() 消除

```
目标: 消除 50+ 类的 static 成员隐式传播
方案:
  1. 将 static 成员转为实例成员
  2. 通过构造函数或 init() 参数传入
  3. 逐类迁移
```

#### P3-3: GlobalV 命名空间清理

```
目标: MPI 信息和输出流从全局变量变为上下文参数
方案:
  1. 定义 ParallelContext struct { rank, nproc, pool_id, ... }
  2. 定义 OutputContext struct { ofs_running, ofs_warning }
  3. ESolver 持有两个 context
  4. 逐模块传递
```

---

## 四、优先级与依赖关系

```
Phase 1 (纯增量，可并行):
  P1-1 PotentialAccessor ──────┐
  P1-2 DFTUAccessor ───────────┤
  P1-3 ChargeAccessor扩展 ─────┤── 全部独立，可并行开发
  P1-4 ProjectorAccessor ──────┤
  P1-5 力分量分解 ─────────────┤
  P1-6 FFT网格信息 ────────────┘

Phase 2 (最小侵入):
  P2-1 Timer/Memory reset ─────→ P2-3 ESolver cleanup 增强
  P2-2 Python dict 初始化 ─────→ P2-4 输出流重定向

Phase 3 (长期):
  P3-1 PARAM实例化 ── depends on → P3-2 Convert消除 ── depends on → P3-3 GlobalV清理
```

### 建议执行顺序

1. **立即开始**: P1-1 (PotentialAccessor) + P2-1 (Timer reset) — 解除最大阻塞
2. **第二批**: P1-2 (DFT+U) + P1-3 (tau) + P2-2 (dict init) — ML 训练数据补全
3. **第三批**: P1-4 (Projectors) + P1-5 (力分量) + P2-3 (cleanup) — 高级分析
4. **第四批**: P1-6 (FFT grid) + P2-4 (输出流) — 完善
5. **长期**: Phase 3 PARAM 重构 — 需要团队协作

---

## 五、分支管理策略

所有开发在 branches.yaml 中登记，合并后更新 capabilities.yaml。

```yaml
# branches.yaml 新增
pyabacus:
  - branch: feature/potential-accessor
    repo: /root/abacus-develop
    target_capabilities: [veff_access, vxc_access, vhartree_access]
    created_by: human
    task_id: PB-001
    status: in_progress

  - branch: feature/dftu-accessor
    repo: /root/abacus-develop
    target_capabilities: [dftu_occupation_access, dftu_u_values_access]
    created_by: human
    task_id: PB-002
    status: in_progress

  - branch: feature/timer-reset
    repo: /root/abacus-develop
    target_capabilities: [timer_reset, memory_reset, multi_instance]
    created_by: human
    task_id: PB-007
    status: in_progress
```
