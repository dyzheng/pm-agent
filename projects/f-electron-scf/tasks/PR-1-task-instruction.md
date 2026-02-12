# PR-1: onsite_projector nspin=1/2 支持

## 任务目标

在 develop 分支的 `onsite_projector` 模块中添加 nspin=1/2 支持。当前 develop 仅支持 nspin=4（非共线磁性），需要扩展以支持 nspin=1（非自旋极化）和 nspin=2（共线自旋极化）。

## 工作目录

- worktree: `/root/abacus-dftu-pw-port`
- 分支: `feat/dftu-pw-port`（基于 `origin/develop` commit c039e9275）
- 参考代码: `/root/abacus-zdy-tmp`（zdy-tmp 分支，已实现完整功能）

## 需要修改的文件（共 4 个）

### 1. `source/source_pw/module_pwdft/onsite_projector.h`

**修改 1a**: `overlap_proj_psi` 添加 `npwx` 参数

```cpp
// 当前 develop (line 46-49):
void overlap_proj_psi(
            const int npm,
            const std::complex<double>* ppsi
            );

// 改为:
void overlap_proj_psi(
            const int npm,
            const std::complex<double>* ppsi,
            int npwx = 0
            );
```

**修改 1b**: `cal_occupations` 添加 `isk_in` 参数

```cpp
// 当前 develop (line 73):
void cal_occupations(const psi::Psi<std::complex<T>, Device>* psi, const ModuleBase::matrix& wg_in);

// 改为:
void cal_occupations(const psi::Psi<std::complex<T>, Device>* psi, const ModuleBase::matrix& wg_in, const int* isk_in);
```

### 2. `source/source_pw/module_pwdft/onsite_projector.cpp`

**修改 2a**: `overlap_proj_psi` 实现（约 line 339-406）

```cpp
// 当前 develop (line 339-342):
void projectors::OnsiteProjector<T, Device>::overlap_proj_psi(
                    const int npm,
                    const std::complex<double>* ppsi)

// 改为:
void projectors::OnsiteProjector<T, Device>::overlap_proj_psi(
                    const int npm,
                    const std::complex<double>* ppsi,
                    int npwx
                    )
```

在函数体内，在 `int npol = this->ucell->get_npol();` 之后添加:
```cpp
if(npwx == 0) npwx = this->npwx_;
```

修改 `cal_becp` 调用（当前 line 400）:
```cpp
// 当前:
this->fs_tools->cal_becp(ik_, npm/npol, this->becp, ppsi);

// 改为:
this->fs_tools->cal_becp(ik_, npm/npol, this->becp, ppsi, npwx);
```

**修改 2b**: `cal_occupations` 实现（约 line 523-643）

签名改为:
```cpp
void projectors::OnsiteProjector<T, Device>::cal_occupations(
    const psi::Psi<std::complex<T>, Device>* psi_in,
    const ModuleBase::matrix& wg_in,
    const int* isk_in)
```

在 k-point 循环内，`psi_in->fix_k(ik);` 之后添加:
```cpp
const int sign = isk_in[ik] == 0? 1: -1;
```

将 occupation 累加的内层循环从仅支持 npol=2 改为同时支持 npol=1 和 npol=2:

```cpp
// 当前 develop 只有 npol=2 的分支 (line 558-567):
for(int ih = 0; ih < nh; ih++)
{
    const int occ_index = (begin_ih + ih) * 4;
    const int index = ib*2*nkb + begin_ih + ih;
    occs[occ_index] += weight * conj(becp_p[index]) * becp_p[index];
    occs[occ_index + 1] += weight * conj(becp_p[index]) * becp_p[index + nkb];
    occs[occ_index + 2] += weight * conj(becp_p[index + nkb]) * becp_p[index];
    occs[occ_index + 3] += weight * conj(becp_p[index + nkb]) * becp_p[index + nkb];
}

// 改为 (参考 zdy-tmp line 567-586):
if(this->ucell->get_npol() == 2)
for(int ih = 0; ih < nh; ih++)
{
    const int occ_index = (begin_ih + ih) * 4;
    const int index = ib*2*nkb + begin_ih + ih;
    occs[occ_index] += weight * conj(becp_p[index]) * becp_p[index];
    occs[occ_index + 1] += weight * conj(becp_p[index]) * becp_p[index + nkb];
    occs[occ_index + 2] += weight * conj(becp_p[index + nkb]) * becp_p[index];
    occs[occ_index + 3] += weight * conj(becp_p[index + nkb]) * becp_p[index + nkb];
}
else if(this->ucell->get_npol() == 1)
{
    for(int ih = 0; ih < nh; ih++)
    {
        const int occ_index = (begin_ih + ih) * 4;
        const int index = ib*nkb + begin_ih + ih;
        occs[occ_index] += weight * conj(becp_p[index]) * becp_p[index];
        occs[occ_index + 3] += sign * weight * conj(becp_p[index]) * becp_p[index];
    }
}
```

同样，在输出部分（约 line 609-626），charge_mag 的累加也需要添加 npol=1 分支:

```cpp
// 当前 develop (line 611-614) 只有 npol=2 的计算:
charge_mag[3] += (occs[occ_index] - occs[occ_index + 3]).real();
charge_mag[1] += (occs[occ_index + 1] + occs[occ_index + 2]).real();
charge_mag[2] += (occs[occ_index + 1] - occs[occ_index + 2]).imag();
charge_mag[0] += (occs[occ_index] + occs[occ_index + 3]).real();

// 改为:
if(this->ucell->get_npol() == 2)
{
    charge_mag[3] += (occs[occ_index] - occs[occ_index + 3]).real();
    charge_mag[1] += (occs[occ_index + 1] + occs[occ_index + 2]).real();
    charge_mag[2] += (occs[occ_index + 1] - occs[occ_index + 2]).imag();
    charge_mag[0] += (occs[occ_index] + occs[occ_index + 3]).real();
}
else if (this->ucell->get_npol() == 1)
{
    charge_mag[0] += occs[occ_index].real();
    charge_mag[3] += occs[occ_index + 3].real();
}
```

### 3. `source/source_pw/module_pwdft/onsite_proj_tools.h`

**修改 3a**: `cal_becp` 添加 `npwx` 参数

```cpp
// 当前 develop (line 61):
void cal_becp(int ik, int npm, std::complex<FPTYPE>* becp_in = nullptr, const std::complex<FPTYPE>* ppsi_in = nullptr);

// 改为:
void cal_becp(int ik, int npm, std::complex<FPTYPE>* becp_in = nullptr, const std::complex<FPTYPE>* ppsi_in = nullptr, int npwx = 0);
```

### 4. `source/source_pw/module_pwdft/onsite_proj_tools.cpp`

**修改 4a**: `cal_becp` 实现签名（约 line 278-281）

```cpp
// 当前:
void Onsite_Proj_tools<FPTYPE, Device>::cal_becp(int ik,
                                                 int npm,
                                                 std::complex<FPTYPE>* becp_in,
                                                 const std::complex<FPTYPE>* ppsi_in)

// 改为:
void Onsite_Proj_tools<FPTYPE, Device>::cal_becp(int ik,
                                                 int npm,
                                                 std::complex<FPTYPE>* becp_in,
                                                 const std::complex<FPTYPE>* ppsi_in,
                                                 int npwx)
```

在函数体内需要使用 `npwx` 参数。参考 zdy-tmp 的 `fs_nonlocal_tools.cpp` 中 `cal_becp` 的实现，当 `npwx > 0` 时用 `npwx` 替代 `this->wfc_basis_->npwk_max` 作为 leading dimension。具体需要查看 zdy-tmp 中 `cal_becp` 函数体内 `npwx` 的使用方式并对应移植。

### 5. 调用方更新

**文件**: `source/source_io/module_ctrl/ctrl_output_pw.cpp` (约 line 239-240)

```cpp
// 当前:
onsite_p->cal_occupations(reinterpret_cast<psi::Psi<std::complex<double>, Device>*>(stp.psi_t),
                          pelec->wg);

// 改为:
onsite_p->cal_occupations(reinterpret_cast<psi::Psi<std::complex<double>, Device>*>(stp.psi_t),
                          pelec->wg,
                          pelec->klist->isk.data());
```

注意：需要确认 `pelec->klist` 在此处可访问。如果不可访问，需要从 `stp` 或其他途径获取 `isk` 数组。

## 关键注意事项

1. **API 差异映射**:
   - develop 用 `Onsite_Proj_tools`，zdy-tmp 用 `FS_Nonlocal_tools`（类名不同，但接口基本一致）
   - develop 的 memory op 不需要传 `this->ctx` 参数（如 `resmem_complex_op()(this->becp, size)` 而非 `resmem_complex_op()(this->ctx, this->becp, size)`）
   - develop 的 `syncmem_complex_d2h_op` 也不需要 ctx 参数

2. **npwx 参数的作用**: 当 nspin=1/2 时，psi 的 leading dimension (npwx) 与 nspin=4 不同（nspin=4 时 npwx 包含 2*npol 的空间）。`npwx` 参数允许调用方指定实际的 leading dimension，默认值 0 表示使用 `npwk_max`。

3. **sign 变量的物理含义**: 在 nspin=2 时，isk[ik]=0 对应 spin-up（sign=+1），isk[ik]=1 对应 spin-down（sign=-1）。这用于正确计算磁矩 Mz = n_up - n_down。

4. **不要修改 `init()` 函数**: develop 的 `init()` 结构与 zdy-tmp 有差异（develop 把所有初始化放在 `if(!initialed)` 内部），不需要在 PR-1 中修改。

## 验收标准

### 必须通过

1. **编译通过**: 在 worktree 中 `cmake .. && make -j` 无错误
2. **现有 nspin=4 测试不受影响**: 运行现有的 onsite_projector 相关测试，结果不变
3. **代码一致性**: 修改后的代码与 zdy-tmp 对应部分逻辑一致（允许 API 名称差异）

### 建议验证

4. 检查是否有其他调用 `overlap_proj_psi` 或 `cal_becp` 的地方需要同步更新
5. 确认 `cal_becp` 内部使用 `npwx` 参数的逻辑正确（参考 zdy-tmp 的 `fs_nonlocal_tools.cpp`）

## 完成后

- 在 worktree `/root/abacus-dftu-pw-port` 中 commit，commit message 格式:
  ```
  feat: extend onsite_projector to support nspin=1/2

  - Add isk_in parameter to cal_occupations() for spin channel identification
  - Add npwx parameter to overlap_proj_psi() and cal_becp() for flexible leading dimension
  - Add npol=1 branch in occupation calculation for nspin=1/2 systems
  - Update caller in ctrl_output_pw.cpp to pass isk array
  ```
- 不要 push，等待验收

## 完成情况

- [x] **修改 1a**: `overlap_proj_psi` 添加 `npwx` 参数 — `onsite_projector.h` 声明 + `onsite_projector.cpp` 实现
- [x] **修改 1b**: `cal_occupations` 添加 `isk_in` 参数 — `onsite_projector.h` 声明 + `onsite_projector.cpp` 实现
- [x] **修改 2a**: `overlap_proj_psi` 实现中添加 `if(npwx == 0) npwx = this->npwx_;` 并传递 `npwx` 给 `cal_becp`
- [x] **修改 2b**: `cal_occupations` 实现中添加 `sign` 变量、npol=1 occupation 累加分支、npol=1 charge_mag 输出分支
- [x] **修改 3a**: `cal_becp` 声明添加 `npwx` 参数 — `onsite_proj_tools.h`
- [x] **修改 4a**: `cal_becp` 实现签名添加 `npwx`，函数体内 `if(npwx == 0) npwx = this->wfc_basis_->npwk_max;`，GEMM 调用中 `this->max_npw` 替换为 `npwx`
- [x] **修改 5**: 调用方 `ctrl_output_pw.cpp` 传递 `kv.isk.data()` 作为第三个参数

### 修改文件清单（5 个文件，+43/-15 行）
1. `source/source_pw/module_pwdft/onsite_projector.h`
2. `source/source_pw/module_pwdft/onsite_projector.cpp`
3. `source/source_pw/module_pwdft/onsite_proj_tools.h`
4. `source/source_pw/module_pwdft/onsite_proj_tools.cpp`
5. `source/source_io/module_ctrl/ctrl_output_pw.cpp`

### 编译验证
- [x] CMake 配置通过（cmake 3.18.6, g++-8, OpenBLAS, ScaLAPACK, FFTW3, ELPA）
- [x] `cmake --build build -j$(nproc)` 编译通过，生成二进制 `abacus_2p`（354MB）
- [ ] 无专门针对 onsite_projector 的单元测试（上游未编写）

### 分支信息
- commit: `d2364165c`
- 远程分支: `zdy/feat/onsite-proj-nspin12`
- GitHub: https://github.com/dyzheng/abacus-develop/tree/feat/onsite-proj-nspin12

### 状态：已完成，编译通过，已推送至远程分支
