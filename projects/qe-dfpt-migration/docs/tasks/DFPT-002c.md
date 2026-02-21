# DFPT-002c: Configure DFPT Migration Workflow

## Objective

Configure a 3-agent serial migration workflow that systematically analyzes QE Fortran source code, extracts ABACUS C++ implementation patterns, and generates adaptation plans for each migration unit. This workflow ensures consistent, traceable Fortran→C++ translation across all DFPT components.

## Reference Code

### QE Source — Migration Source Files

The migration workflow must handle these Fortran patterns:

**Fortran module pattern** (`/root/q-e/PHonon/PH/phcom.f90`):
```fortran
MODULE modes
  USE kinds, ONLY : DP
  COMPLEX(DP), ALLOCATABLE :: u(:,:)    ! mode patterns
  INTEGER :: nirr                        ! number of irreps
  INTEGER, ALLOCATABLE :: npert(:)       ! perturbations per irrep
END MODULE modes
```

**Fortran subroutine pattern** (`/root/q-e/LR_Modules/cgsolve_all.f90`):
```fortran
SUBROUTINE cgsolve_all(ch_psi, cg_psi, e, d0psi, dpsi, h_diag, &
                        ndmx, ndim, ethr, ik, kter, conv_root, anorm, nbnd, npol)
  USE kinds, ONLY : DP
  USE mp, ONLY : mp_sum
  IMPLICIT NONE
  EXTERNAL ch_psi, cg_psi              ! function pointers
  COMPLEX(DP) :: d0psi(ndmx*npol, nbnd), dpsi(ndmx*npol, nbnd)
  REAL(DP) :: h_diag(ndmx*npol, nbnd), e(nbnd)
  ...
END SUBROUTINE
```

**Key Fortran→C++ adaptation dimensions**:
1. **Memory layout**: Fortran column-major → C++ row-major (or use Fortran-order containers)
2. **Array indexing**: Fortran 1-based → C++ 0-based
3. **Complex type**: `COMPLEX(DP)` → `std::complex<double>`
4. **Function pointers**: `EXTERNAL` → `std::function<>` or template
5. **Module globals**: `USE module` → class members or dependency injection
6. **MPI calls**: `mp_sum` → `Parallel_Reduce::reduce_pool` (ABACUS pattern)
7. **FFT interface**: `fwfft/invfft` → `PW_Basis::recip2real/real2recip`
8. **BLAS calls**: Same interface, but ABACUS wraps via `BlasConnector`

### ABACUS Target — Implementation Patterns

**Class pattern** (`/root/abacus-dfpt/abacus-develop/source/source_pw/module_pwdft/operator_pw/dfpt/dvloc_pw.h`):
```cpp
template <typename T, typename Device = base_device::DEVICE_CPU>
class DVloc : public OperatorPW<T, Device> {
public:
    DVloc(/* dependencies injected */);
    void act(const int nbands, const int nbasis, const int npol,
             const T* tmpsi_in, T* tmhpsi, const int ngk_ik = 0) const override;
    void set_displacement(const ModuleBase::Vector3<double>& u);
    void set_qpoint(const ModuleBase::Vector3<double>& xq);
};
```

**Adapter pattern** (`/root/abacus-dfpt/abacus-develop/source/source_pw/module_pwdft/operator_pw/dfpt/dfpt_adapter.h`):
```cpp
class DFPTAdapter {
public:
    static dvqpsi::FFTGrid convert_fft_grid(const ModulePW::PW_Basis* pw_basis);
    static dvqpsi::WaveFunction convert_wavefunction(const psi::Psi<std::complex<double>>& psi, int ik);
    static dvqpsi::KPointData convert_kpoint(const K_Vectors& kv, int ik);
    // ... more conversions
};
```

### dvqpsi_cpp Reference

`/root/q-e/PHonon/dvqpsi_cpp/` provides completed migration examples:
- `dvqpsi_us.hpp/cpp` — Successfully migrated from QE's `dvqpsi_us.f90`
- `cg_solver.hpp/cpp` — Migrated from QE's `cgsolve_all.f90`
- `sternheimer_solver.hpp/cpp` — Migrated from QE's `solve_linter.f90` + `response_kernels.f90`

## Implementation Guide

### 3-Agent Serial Workflow

#### Agent 1: `review-migrate-source-dfpt`

**Input**: QE Fortran source file
**Output**: Algorithm characteristics analysis

**Extraction dimensions** (≥6):
1. **Data structures**: All variables with types, dimensions, allocation patterns
2. **Algorithm flow**: Step-by-step pseudocode of the subroutine
3. **Dependencies**: `USE` statements, `EXTERNAL` functions, `CALL` targets
4. **Parallelization**: MPI calls (`mp_sum`, `mp_bcast`), band group operations
5. **I/O operations**: Buffer reads/writes (`get_buffer`, `save_buffer`)
6. **Numerical patterns**: BLAS calls, FFT operations, convergence checks
7. **Physical units**: What units are assumed for inputs/outputs
8. **Edge cases**: Special handling for q=0, metals, ultrasoft, noncollinear

**Example output for `cgsolve_all.f90`**:
```json
{
  "file": "LR_Modules/cgsolve_all.f90",
  "algorithm": "Preconditioned conjugate gradient for linear systems",
  "data_structures": [
    {"name": "dpsi", "type": "COMPLEX(DP)", "dims": "(ndmx*npol, nbnd)", "role": "solution"},
    {"name": "d0psi", "type": "COMPLEX(DP)", "dims": "(ndmx*npol, nbnd)", "role": "RHS"},
    {"name": "h_diag", "type": "REAL(DP)", "dims": "(ndmx*npol, nbnd)", "role": "preconditioner"}
  ],
  "dependencies": ["ch_psi (EXTERNAL)", "cg_psi (EXTERNAL)", "mp_sum"],
  "parallelization": ["mp_sum over intra_bgrp_comm for dot products"],
  "numerical_patterns": ["ZDOTC for complex dot product", "DZNRM2 for norm"],
  "convergence": "per-band: sqrt(rho(ibnd)) < ethr"
}
```

#### Agent 2: `review-migrate-target-dfpt`

**Input**: ABACUS C++ target file (or pattern reference)
**Output**: Implementation pattern analysis

**Extraction dimensions**:
1. **Class hierarchy**: Inheritance, template parameters
2. **Memory management**: Smart pointers, RAII, container types
3. **Interface pattern**: Virtual methods, function types, callbacks
4. **Parallelization**: ABACUS MPI wrappers, OpenMP pragmas
5. **FFT interface**: `PW_Basis` methods used
6. **BLAS interface**: `BlasConnector` usage

#### Agent 3: `review-migrate-diff-dfpt`

**Input**: Agent 1 + Agent 2 outputs
**Output**: Adaptation plan

**Adaptation categories**:
- `high`: Fundamental design change (e.g., global module → class member)
- `medium`: Interface adaptation (e.g., Fortran array → C++ container)
- `low`: Syntactic translation (e.g., `COMPLEX(DP)` → `std::complex<double>`)

### Source-Reference File Pairing Table (≥10 pairs)

| QE Source File | ABACUS Target File | Migration Status | Priority |
|---------------|-------------------|-----------------|----------|
| `cgsolve_all.f90` | `diago_cg_lr.h/cpp` | Completed (dvqpsi_cpp) | P0 |
| `dvqpsi_us.f90` | `dvloc_pw.h/cpp` + `dvqpsi_cpp` | Completed | P0 |
| `response_kernels.f90` | `hsolver_pw_dfpt.h/cpp` | Partial | P0 |
| `dfpt_kernels.f90` | `esolver_ks_pw_dfpt.cpp::dfpt_scf_loop()` | Partial | P0 |
| `dv_of_drho.f90` | `compute_dvscf()` (new) | Not started | P1 |
| `dynmat0.f90` | `dynmat.h/cpp` (new) | Not started | P1 |
| `dynmatrix.f90` | `dynmat.h/cpp` (new) | Not started | P1 |
| `d2ionq.f90` | `dynmat.h/cpp` (new) | Not started | P1 |
| `rigid.f90` | `dynmat.h/cpp` (new) | Not started | P1 |
| `elphon.f90` | `elphon.h/cpp` (new) | Not started | P2 |
| `set_irr.f90` | `symmetry_dfpt.h/cpp` (new) | Not started | P2 |
| `symdynph_gq.f90` | `symmetry_dfpt.h/cpp` (new) | Not started | P2 |
| `q2r.f90` | `q2r.cpp` (new) | Not started | P2 |
| `phescf.f90` | `esolver_dfpt.cpp` (new) | Not started | P2 |

### Workflow Document: `DFPT_MIGRATION_WORKFLOW.md`

Must include:
1. Workflow diagram (Agent 1 → Agent 2 → Agent 3)
2. Input/output format specifications for each agent
3. Source-reference pairing table
4. Adaptation severity classification guide
5. Example complete workflow run

## TDD Test Plan

### Tests to Write FIRST

1. **Prompt format validation**:
   ```python
   def test_migration_prompts_exist():
       for name in ["source", "target", "diff"]:
           path = Path(f"prompts/review-migrate-{name}-dfpt.agent.md")
           assert path.exists()
           content = path.read_text()
           assert len(content) > 200
   ```

2. **Pairing table completeness**:
   ```python
   def test_pairing_table():
       doc = Path("docs/DFPT_MIGRATION_WORKFLOW.md").read_text()
       rows = extract_table_rows(doc, "Source-Reference")
       assert len(rows) >= 10
   ```

3. **End-to-end workflow test**:
   ```bash
   # Run Agent 1 on cgsolve_all.f90
   # Run Agent 2 on diago_cg_lr.h
   # Run Agent 3 on combined output
   # Verify adaptation plan has ≥8 items
   ```

## Acceptance Criteria

- [ ] 3 migration prompts created: `review-migrate-{source,target,diff}-dfpt.agent.md`
- [ ] Fortran→C++ adaptation dimensions ≥6 aspects documented
- [ ] Source-reference file pairing table ≥10 pairs
- [ ] `DFPT_MIGRATION_WORKFLOW.md` complete with diagram and examples
- [ ] Complete workflow on `cgsolve_all.f90` → `diago_cg_lr.h` generates valid adaptation plan
- [ ] Adaptation plan has ≥8 items with severity classification
- [ ] All prompts produce valid JSON output
