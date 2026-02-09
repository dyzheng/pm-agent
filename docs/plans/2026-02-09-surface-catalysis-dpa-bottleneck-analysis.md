# High-Throughput Surface Catalysis DPA Training: Bottleneck Analysis

**Goal:** Use ABACUS to calculate surface/interface catalysis data for many materials, train DPA models with DeePMD-kit. Identify algorithm bottlenecks, data bottlenecks, and improvement tasks.

---

## 1. Algorithm Bottleneck Classification

Each bottleneck is classified by:
- **Universality**: `UNIVERSAL` (all DFT codes face this) vs `ABACUS-SPECIFIC`
- **ROI**: `HIGH` / `MEDIUM` / `LOW` — expected benefit-to-effort ratio
- **Severity**: `CRITICAL` / `HIGH` / `MEDIUM`

### 1.1 SCF Convergence for Metallic Surfaces

| Attribute | Value |
|---|---|
| Universality | **UNIVERSAL** — VASP (AMIX/BMIX), QE (mixing_beta), all PW codes face charge sloshing on metals |
| ROI | **HIGH** — 2-5x fewer SCF iterations for metallic surfaces; affects EVERY metal surface calculation |
| Severity | CRITICAL |

**Problem:** Metallic surfaces exhibit charge sloshing — electrons oscillate between SCF steps instead of converging. Kerker preconditioning mitigates this but ABACUS uses hard-coded cutoff parameters (`mixing_gg0`, `mixing_gg0_min`). Different surface orientations and compositions need different parameters.

**Why high ROI:** In high-throughput, you cannot hand-tune mixing parameters per calculation. An adaptive scheme that auto-adjusts based on the dielectric response would eliminate the #1 cause of failed/slow calculations.

**Files:** `source/source_estate/module_charge/charge_mixing.cpp`, `charge_mixing_preconditioner.cpp`

### 1.2 Vacuum Layer Computational Waste (2D Coulomb Truncation)

| Attribute | Value |
|---|---|
| Universality | **UNIVERSAL** — QE has `assume_isolated='2D'`, VASP has `IDIPOL`/`LDIPOL`, FHI-aims has cluster embedding |
| ROI | **HIGH** — 30-50% speedup on ALL slab calculations; zero approximation error |
| Severity | HIGH |

**Problem:** Slab models require 10-15 Angstrom vacuum. PW basis expands into vacuum. FFT grid covers full cell including empty space. No Coulomb truncation implemented.

**Why high ROI:** Pure algorithmic gain — eliminates waste without any accuracy tradeoff. Every surface calculation benefits. Well-understood theory (Rozzi 2006, Sohier 2017).

**Files:** `source/source_basis/module_pw/pw_basis.cpp`

### 1.3 Davidson Diagonalization Memory

| Attribute | Value |
|---|---|
| Universality | **UNIVERSAL** — all iterative eigensolvers (Davidson, LOBPCG, CheFSI) face this |
| ROI | **MEDIUM** — enables larger systems but can be partially worked around with more nodes |
| Severity | CRITICAL |

**Problem:** Workspace = `david_ndim x nband x npw x 16 bytes`. 500-atom slab → ~100 GB. Some arrays are replicated per MPI rank.

**Files:** `source/source_hsolver/diago_david.cpp`

### 1.4 K-point Load Imbalance

| Attribute | Value |
|---|---|
| Universality | **UNIVERSAL** — all parallel DFT codes with k-point parallelism |
| ROI | **MEDIUM** — typical 10-20% improvement; surfaces have moderate k-point counts |
| Severity | HIGH |

**Problem:** Round-robin k-point distribution ignores per-k-point cost variations. Low-symmetry slabs have many irreducible k-points with varying convergence difficulty.

**Files:** `source/source_cell/parallel_kpoints.cpp`

### 1.5 Non-local Pseudopotential Force Calculation

| Attribute | Value |
|---|---|
| Universality | **UNIVERSAL** — all norm-conserving/PAW PP codes compute Pulay corrections |
| ROI | **MEDIUM** — important for force-heavy workflows (training data generation) but incremental gain |
| Severity | HIGH |

**Problem:** Non-local forces require O(nks x nbands x natom x npw) operations. Code comments suggest current implementation not optimized for large systems.

**Files:** `source/source_pw/module_pwdft/forces_nl.cpp`

### 1.6 Dipole Correction for Asymmetric Slabs

| Attribute | Value |
|---|---|
| Universality | **UNIVERSAL** — QE (`dipfield`), VASP (`LDIPOL`), GPAW all have this |
| ROI | **HIGH** — correctness issue, not just performance; wrong energies without correction for single-sided adsorption |
| Severity | MEDIUM |

**Problem:** Asymmetric slabs (adsorbate on one side) create artificial electric field across periodic images. Without correction, adsorption energies can be off by 0.1-0.5 eV — catastrophic for training data quality.

**Why high ROI:** Incorrect forces/energies silently pollute training data. A dipole correction is ~200 lines of code but fixes a systematic error affecting ALL asymmetric slab results.

**Files:** New code needed in `source/source_pw/module_pwdft/`

### 1.7 Subspace Wavefunction Recycling

| Attribute | Value |
|---|---|
| Universality | **UNIVERSAL** — VASP (`ISTART`), QE (`startingwfc='file'`), CP2K (wavefunction extrapolation) |
| ROI | **HIGH** — 2-3x fewer SCF steps for sequential configurations (MD, NEB, relaxation) |
| Severity | MEDIUM |

**Problem:** Each configuration starts SCF from scratch. For MD trajectories or NEB images, consecutive frames are very similar — the converged subspace is an excellent initial guess.

**Why high ROI:** Training data generation = thousands of sequential configurations. 2-3x speedup on the most compute-intensive step is massive for throughput.

**Files:** `source/source_hsolver/diago_david.cpp`, `source/source_pw/module_pwdft/`

### 1.8 LCAO Sparse Hamiltonian for Low-Symmetry Slabs

| Attribute | Value |
|---|---|
| Universality | **ABACUS-SPECIFIC** — HContainer is ABACUS's own sparse storage format |
| ROI | **LOW** — only affects LCAO basis users; PW more common for surfaces |
| Severity | MEDIUM |

**Files:** `source/source_lcao/module_hcontainer/hcontainer.cpp`

---

## 1B. Physical Methodology Bottlenecks

### 1.9 DFT+U Occupation Matrix Metastability

| Attribute | Value |
|---|---|
| Universality | **UNIVERSAL** — VASP/QE/all DFT+U codes face multiple SCF minima on TM oxides |
| ROI | **HIGH** — wrong minimum = wrong energies (0.1-1.0 eV error); silently poisons training data |
| Severity | CRITICAL |

**Problem:** ABACUS implements Dudarev simplified DFT+U with U-ramping and occupation matrix control (omc), BUT lacks systematic metastability avoidance. For transition metal oxide surfaces (NiO, CoO, Fe3O4, mixed-valence Mn), multiple d-electron orderings correspond to different SCF minima. The energy difference between true ground state and metastable state can be 0.1-1.0 eV.

**What ABACUS has:**
- Dudarev simplified scheme (`cal_type=3` hardcoded in `dftu_tools.cpp`)
- U-ramping (`uramping` parameter, `dftu.cpp:394-424`) — helps convergence but doesn't guarantee global minimum
- Occupation matrix control (`omc=0/1/2` in `dftu.cpp:202-230`) — manual initial guess from `initial_onsite.dm`
- Yukawa potential for automatic U/J calculation (`dftu_yukawa.cpp`)
- Occupation matrix mixing (`dftu_occup.cpp:85-124`) — damping, not exploration
- Full force/stress with DFT+U Pulay corrections (`dftu_force.cpp`)

**What ABACUS lacks (critical for high-throughput):**
- No randomized occupation matrix initialization
- No occupation annealing (e.g., start with high temperature smearing, cool down)
- No automatic multi-minimum exploration (run N random initializations, pick lowest E)
- No warning/detection of metastable solutions
- No rotationally invariant formalism (Liechtenstein) — only Dudarev
- No DFT+U+V (inter-site Hubbard) — needed for charge-transfer oxides (CuO)
- No self-consistent U (linear response DFPT / ACBN0) — must use literature values or Yukawa
- No AMF (around mean field) double counting — only FLL
- PW basis: only nspin=4 (SOC) supported, no collinear spin (`read_input_item_exx_dftu.cpp:438-444`)

**Why critical for high-throughput ML training:** You cannot manually inspect occupation matrices for 10,000 oxide surface calculations. Wrong d-electron ordering → systematically biased forces → DPA model learns incorrect PES.

**Files:** `source/source_lcao/module_dftu/dftu.cpp`, `dftu_tools.cpp`, `dftu_occup.cpp`, `dftu_io.cpp`

### 1.10 Functional Selection Bottleneck: r2SCAN / Hybrid Cost-Accuracy Tradeoff

| Attribute | Value |
|---|---|
| Universality | **UNIVERSAL** — all DFT codes face the functional accuracy vs cost tradeoff |
| ROI | **HIGH** — wrong functional = systematic bias in training data; multi-fidelity strategy can cut cost 10-100x |
| Severity | HIGH |

**Problem:** PBE systematically overbinds adsorbates on metal surfaces (~0.2-0.5 eV error). RPBE fixes this but underestimates barriers. r2SCAN is better balanced but 2-3x slower. HSE06 is most accurate for barriers but 20-100x slower. No single functional is optimal for all properties.

**ABACUS functional support status:**
- PBE, RPBE (native, `xc_funct_exch_gga.cpp` — RPBE via `REVPBE` shorthand): Full, production-ready
- r2SCAN (via LibXC 7.0, `dft_functional MGGA_X_R2SCAN+MGGA_C_R2SCAN`): Supported, stress tensor works (`stress_mgga.cpp`), GPU kernels available
- HSE06 (via LibXC + EXX, `dft_functional hse`): Tested, LCAO with RI-LRI method, PW with ACE acceleration (`op_pw_exx_ace.cpp`), but PW still "under active development"
- BEEF-vdW: **NOT supported** — no ensemble error estimation for ML uncertainty quantification
- SCAN+rVV10: **NOT supported** — nonlocal correlation explicitly rejected (`xc_functional_libxc.cpp:35-61`)

**Key gap:** No automated multi-fidelity workflow. The optimal strategy is:
1. PBE for exploration (10,000 configs)
2. r2SCAN for intermediate fidelity (1,000 configs)
3. HSE06 for critical points only (100 configs)
4. Delta-learning: train DPA on PBE, learn PBE→HSE06 correction

But this workflow must be manually orchestrated — no tool support exists.

**Files:** `source/source_hamilt/module_xc/xc_functional.cpp`, `xc_functional_libxc.cpp`, `source/source_pw/module_pwdft/stress_mgga.cpp`, `op_pw_exx_ace.cpp`

### 1.11 van der Waals Correction Algorithm Limitations

| Attribute | Value |
|---|---|
| Universality | **UNIVERSAL** — vdW treatment for surfaces is a universal challenge; but nonlocal methods are standard in QE/VASP |
| ROI | **HIGH** — missing vdW-DF/rVV10 means ABACUS cannot match VASP/QE accuracy for physisorbed systems |
| Severity | HIGH |

**Problem:** ABACUS only has pair-wise DFT-D corrections (D2, D3(0), D3(BJ)). No nonlocal correlation functionals (vdW-DF, vdW-DF2, rVV10, SCAN+rVV10). For surface catalysis involving physisorption (flat-lying molecules, vdW-bound intermediates), pair-wise D3 can have 50-100 meV/molecule errors vs nonlocal methods.

**What ABACUS has:**
- D2 (`vdwd2.cpp`): Simple C6/r6, obsolete
- D3(0) and D3(BJ) (`vdwd3.cpp`, 1539 lines): Coordination-dependent C6, optional three-body ATM term (`vdw_abc 1`), full forces/stress
- Auto-parameter for most functionals (`vdwd3_autoset_xcparam.cpp`) including r2SCAN+D3

**What ABACUS lacks:**
- DFT-D4 (charge-dependent C6 — significant improvement over D3 for metals)
- Tkatchenko-Scheffler (TS) / Many-Body Dispersion (MBD) — density-dependent, much better for surfaces
- **vdW-DF / vdW-DF2 / rVV10** — nonlocal correlation, gold standard for physisorption
- SCAN+rVV10 — explicitly rejected by code (`xc_functional_libxc.cpp:35-61`)

**Surface-specific issue:** vdW correction applies across vacuum in slab geometries (issue #5401 in code). No automatic vacuum correction — users must manually tune `vdw_cutoff_radius` to prevent inter-slab vdW artifacts.

**Comparison:**
| Method | ABACUS | QE | VASP |
|---|---|---|---|
| D3(BJ) | Yes | Yes | Yes |
| D4 | **No** | Yes (plugin) | Yes |
| TS/MBD | **No** | Yes | Yes |
| vdW-DF | **No** | Yes | Yes |
| rVV10 | **No** | Yes | Yes |
| SCAN+rVV10 | **No** | Yes | Yes |

**Files:** `source/source_hamilt/module_vdw/vdwd3.cpp`, `vdw.cpp`

### 1.12 NEB/过渡态搜索策略优化

| Attribute | Value |
|---|---|
| Universality | **UNIVERSAL** — all DFT-NEB codes face the cost vs accuracy vs path quality tradeoff |
| ROI | **HIGH** — NEB is the single most expensive step in catalysis workflows; ML-accelerated NEB can cut cost 10-50x |
| Severity | HIGH |

**Problem:** ABACUS 没有原生 NEB 实现，依赖 ASE+PyABACUS（`python/pyabacus/tests/ase-neb/`）。当前实现的问题：

1. **无原生并行 image 计算**：ASE NEB 中每个 image 的 DFT 调用是串行的（或需要用户手动并行化）。对于 7-11 个 image 的标准 NEB，这是巨大的性能损失。
2. **无 ML-accelerated NEB**：理想流程是用廉价 DP 模型做初始路径搜索，再用 DFT 精修关键 image。当前无工具链支持。
3. **无 DFT 策略优化**：所有 image 用同一泛函/精度。实际上，路径两端和过渡态附近应该用更高精度（r2SCAN/HSE06），中间 image 可以用 PBE。
4. **无自适应 image 密度**：过渡态附近应该加密 image，远离过渡态的部分可以稀疏。

**ASE NEB 模式：**
- ESolver mode (`neb_esolver.py`): 内存驻留 ABACUS 实例，低开销，但无 image 并行
- Driver mode (`neb_driver.py`): 子进程方式，可并行但启动开销大

**What's missing:**
- 原生 NEB（C++ 层面，image 并行）
- ML-DFT 混合 NEB（DP 粗搜 + DFT 精修）
- 自适应精度 NEB（关键 image 用高精度泛函）
- Dimer method / string method / growing string
- Saddle point search（用于发现未知反应路径）

**Files:** `python/pyabacus/tests/ase-neb/neb_esolver.py`, `neb_driver.py`

### 1.13 DFT+U 采样不一致导致 ML 训练数据偏差

| Attribute | Value |
|---|---|
| Universality | **UNIVERSAL** — all ML potential训练都面临 DFT+U 数据一致性问题 |
| ROI | **HIGH** — 不一致的 U 值或占据矩阵 = 不连续的 PES = ML 模型发散 |
| Severity | CRITICAL |

**Problem:** 当用 DFT+U 生成 ML 训练数据时，存在三个层面的一致性问题：

1. **U 值的可迁移性**：不同表面取向、不同吸附构型、不同氧化态下，最优 U 值可能不同。用固定 U 训练的 DPA 模型可能在某些构型上完全错误。

2. **占据矩阵连续性**：MD 轨迹中，如果某一帧 SCF 收敛到不同的占据矩阵最小值（高自旋 vs 低自旋），能量和力会出现不连续跳变。ML 模型无法拟合不连续的 PES。

3. **自旋态采样**：过渡金属催化剂可能在反应过程中发生自旋翻转（spin crossover）。固定自旋多重度的训练数据无法捕捉这一物理。

**ABACUS 当前状态：**
- 无自旋态自动探索
- 无 U 值自适应调整
- 无占据矩阵连续性监控
- Yukawa 自动 U 可以缓解第一个问题，但不能解决后两个

---

## 2. Data Pipeline Bottlenecks

| # | Bottleneck | Universality | ROI | Severity |
|---|---|---|---|---|
| D1 | DFT 收敛精度不足导致训练数据质量差 (scf_thr, k-points) | UNIVERSAL | HIGH | CRITICAL |
| D2 | ABACUS→DeePMD 格式批量转换无校验 | ABACUS-SPECIFIC | HIGH | HIGH |
| D3 | GPU 显存限制 DPA attention (100-200 原子) | UNIVERSAL | MEDIUM | HIGH |
| D4 | DP-GEN 迭代延迟 (DFT wall-time + HPC queue) | UNIVERSAL | MEDIUM | MEDIUM |
| D5 | 多元素类型覆盖不足 (每种需 10k+ 帧) | UNIVERSAL | MEDIUM | MEDIUM |
| D6 | 百万级 .npy 小文件 I/O | UNIVERSAL | LOW | LOW |

---

## 3. ROI Summary Matrix

```
                  HIGH ROI                         MEDIUM ROI              LOW ROI
CRITICAL    [1]  Adaptive Kerker              [3]  Davidson Memory
            [9]  DFT+U metastability
            [13] DFT+U sampling consistency
            [D1] DFT convergence QC

HIGH        [2]  2D Coulomb truncation        [4]  K-point load balance
            [6]  Dipole correction            [5]  Non-local force opt
            [7]  Subspace recycling           [D3] GPU memory / attention
            [10] Multi-fidelity functional
            [11] vdW nonlocal (rVV10)
            [12] ML-accelerated NEB
            [D2] Batch data conversion

MEDIUM                                        [D4] DP-GEN latency        [8]  LCAO HContainer
                                              [D5] Multi-element          [D6] Small file I/O
```

### Priority order (updated):

**Tier 0 — Correctness (wrong results pollute ALL downstream):**
`[6] Dipole correction > [9] DFT+U metastability > [13] DFT+U sampling consistency`

**Tier 1 — Highest throughput multiplier:**
`[1] Adaptive Kerker > [2] 2D Coulomb > [7] Subspace recycling`

**Tier 2 — Physical accuracy for catalysis:**
`[10] Multi-fidelity functional > [11] vdW nonlocal > [12] ML-NEB`

**Tier 3 — Performance optimization:**
`[3] Davidson memory > [4] K-point LB > [5] NL force opt`

---

## 4. Task List (for PM Agent registration)

See `state/surface_catalysis_dpa.json` for formal task decomposition with dependencies.
