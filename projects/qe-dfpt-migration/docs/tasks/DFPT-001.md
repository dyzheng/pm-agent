# DFPT-001: Design ABACUS DFPT Module Architecture

## Objective

Design the overall architecture of the DFPT module in ABACUS, defining module structure, class hierarchy, data flow, and integration points with existing ABACUS infrastructure. This document serves as the blueprint for all subsequent implementation tasks.

## Reference Code

### QE Source (Fortran)

The QE PHonon package provides the reference architecture to study:

**Top-level workflow** (`/root/q-e/PHonon/PH/`):
- `phonon.f90` — Main entry point: `phq_readin → check_initial_status → do_phonon`
- `do_phonon.f90` — Q-point loop: `prepare_q → run_nscf → initialize_ph → phqscf → dynmatrix`
- `phqscf.f90` — Irrep loop: calls `solve_linter` for each irreducible representation
- `phescf.f90` — Electric field response: `solve_e → dielec → zstar_eu`

**Linear response infrastructure** (`/root/q-e/LR_Modules/`):
- `dfpt_kernels.f90` — Self-consistent DFPT loop orchestrator
- `response_kernels.f90` — Sternheimer equation solver wrapper
- `cgsolve_all.f90` — Conjugate gradient linear system solver
- `dv_of_drho.f90` — Response potential (Hartree + XC) from response density
- `dfpt_type.f90` — `dfpt_data_type`: drhos, drhop, dvscfs, dvscfp, dbecsum, def

**Data structures** (`/root/q-e/PHonon/PH/phcom.f90`):
- `modes` module: `u(3*nat,3*nat)`, `nirr`, `npert(nirr)`, `t`, `tmq`
- `dynmat` module: `dyn(3*nat,3*nat)`, `dyn00`, `dyn_rec`, `w2(3*nat)`
- `efield_mod`: `epsilon(3,3)`, `zstareu(3,3,nat)`, `zstarue(3,nat,3)`
- `phus`: `int1..int5`, `alphasum`, `becsum_nc`

### ABACUS Target (C++)

Existing DFPT implementation in `/root/abacus-dfpt/abacus-develop/`:

**ESolver hierarchy**:
- `source/source_esolver/esolver_ks_pw_dfpt.h` — DFPT ESolver (inherits `ESolver_KS_PW`)
  - Key methods: `runner()`, `before_dfpt()`, `dfpt_scf_loop()`, `solve_sternheimer()`, `compute_drho()`, `compute_dvscf()`, `mix_dvscf()`, `compute_phonon_properties()`
  - Data: `dpsi_[iq][ipert][ik]`, `drho_[iq][ipert][ir]`, `dvscf_[iq][ipert][ir]`, `dyn_mat_`, `omega_`

**Hamiltonian**:
- `source/source_pw/module_pwdft/hamilt_pw_dfpt.h` — DFPT Hamiltonian extending `HamiltPW`
  - Methods: `apply_dvbare()`, `apply_dvscf()`, `set_perturbation()`
  - Operator chain pattern: `DVloc → Nonlocal → Veff`

**Solver**:
- `source/source_hsolver/hsolver_pw_dfpt.h` — Sternheimer solver
- `source/source_hsolver/diago_cg_lr.h` — CG linear response solver

**Operators**:
- `source/source_pw/module_pwdft/operator_pw/dfpt/dvloc_pw.h` — Local potential derivative
- `source/source_pw/module_pwdft/operator_pw/dfpt/dfpt_adapter.h` — Data structure bridge

**Key ABACUS infrastructure to integrate with**:
- `source/source_basis/module_pw/pw_basis_k.h` — PW basis per k-point
- `source/source_psi/psi.h` — `psi::Psi<T, Device>` wavefunction container
- `source/source_cell/klist.h` — `K_Vectors` k-point management
- `source/source_cell/module_symmetry/symmetry.h` — Symmetry operations
- `source/source_estate/module_charge/charge_mixing.h` — Broyden/plain mixing
- `source/source_base/module_mixing/broyden_mixing.h` — Broyden mixing implementation
- `source/source_io/module_parameter/input_parameter.h` — Input parameters

### dvqpsi_cpp Reference

`/root/q-e/PHonon/dvqpsi_cpp/` — Standalone C++ DFPT kernel (15 classes, ~12k lines):
- Architecture: `types.hpp` → `dvqpsi_us.hpp` → `sternheimer_solver.hpp` → `dfpt_kernel.hpp` → `elphon.hpp`
- Data types: `FFTGrid`, `WaveFunction`, `KPointData`, `GVectorData`, `SystemGeometry`, `NonlocalData`
- Build: CMake with optional OpenMP, BLAS, FFTW3

## Implementation Guide

### Deliverables

1. **Architecture Design Document** (`docs/DFPT_ARCHITECTURE.md`) covering:
   - Module directory layout under `source/module_dfpt/`
   - Class hierarchy diagram (ESolver → Hamiltonian → Operators → Solver)
   - Data flow diagram (ground-state → DFPT init → q-loop → perturbation-loop → SCF → properties)
   - Memory management strategy (sequential q-point processing with checkpointing)
   - Parallelization strategy (MPI pools for k-points, images for q-points)

2. **Interface Specification** defining:
   - `ESolver_KS_PW_DFPT<T, Device>` public API
   - `HamiltPW_DFPT<T, Device>` operator interface
   - `HSolverPW_DFPT<T, Device>` solver interface
   - Data structure mappings (QE Fortran → ABACUS C++)

3. **Integration Point Analysis** documenting:
   - How DFPT ESolver inherits from ground-state `ESolver_KS_PW`
   - How DFPT Hamiltonian extends `HamiltPW` operator chain
   - How DFPT uses existing `Charge_Mixing` infrastructure
   - How DFPT input parameters integrate with `Input_para`

### Key Design Decisions

| Decision | QE Approach | Recommended ABACUS Approach | Rationale |
|----------|-------------|----------------------------|-----------|
| Module organization | Flat file structure in PH/ | Hierarchical `module_dfpt/` with subdirs | C++ namespace/class organization |
| Data flow | Global modules (phcom.f90) | Encapsulated in ESolver members | Avoid global state |
| Perturbation loop | Irrep-based (solve_linter per irrep) | Perturbation-based initially, irrep later | Simpler first, optimize with symmetry |
| Buffer I/O | Direct-access Fortran files | In-memory with optional checkpoint | Modern C++ memory management |
| Mixing | Custom mix_potential | Reuse ABACUS `Charge_Mixing` | Avoid code duplication |

### QE → ABACUS Data Structure Mapping

| QE (Fortran) | ABACUS (C++) | Notes |
|-------------|-------------|-------|
| `dffts%nnr`, `dfftp%nnr` | `PW_Basis::nrxx` | FFT grid sizes |
| `evc(npwx, nbnd)` | `psi::Psi<T>` | Wavefunctions |
| `xk(3, nks)` | `K_Vectors::kvec_c` | K-point coordinates |
| `ngk(nks)` | `K_Vectors::ngk` | PW count per k |
| `igk_k(npwx, nks)` | `PW_Basis_K::igl2isz_k` | G-vector index mapping |
| `dvscf(dffts%nnr, nspin, npert)` | `std::vector<std::vector<std::complex<double>>>` | Response potential |
| `dpsi(npwx, nbnd)` | `psi::Psi<T>` | Response wavefunction |
| `dyn(3*nat, 3*nat)` | `ModuleBase::ComplexMatrix` | Dynamical matrix |

### Proposed Directory Structure

```
source/module_dfpt/
├── CMakeLists.txt
├── dfpt_types.h              # DFPT-specific data types
├── esolver_dfpt.h/cpp        # ESolver_KS_PW_DFPT
├── hamilt_dfpt.h/cpp         # HamiltPW_DFPT
├── hsolver_dfpt.h/cpp        # HSolverPW_DFPT
├── operators/
│   ├── dvloc.h/cpp           # Local potential derivative
│   ├── dvnl.h/cpp            # Nonlocal potential derivative
│   └── dvscf.h/cpp           # SCF potential response
├── solvers/
│   ├── cg_lr.h/cpp           # CG linear response solver
│   └── sternheimer.h/cpp     # Sternheimer equation driver
├── physics/
│   ├── drho.h/cpp            # Charge density response
│   ├── dvscf_calc.h/cpp      # Potential response (Hartree + XC)
│   ├── dynmat.h/cpp          # Dynamical matrix
│   ├── elphon.h/cpp          # Electron-phonon coupling
│   └── symmetry_dfpt.h/cpp   # DFPT symmetry operations
├── parallel/
│   ├── qpoint_pool.h/cpp     # Q-point parallelization
│   └── irrep_parallel.h/cpp  # Irrep parallelization
├── io/
│   ├── dfpt_input.h/cpp      # Input parameter handling
│   ├── dfpt_output.h/cpp     # Output file generation
│   └── checkpoint.h/cpp      # Restart/checkpoint
└── test/
    ├── CMakeLists.txt
    └── test_*.cpp
```

## TDD Test Plan

### Tests to Write FIRST (before implementation)

1. **Architecture validation tests** (`test_dfpt_types.cpp`):
   ```cpp
   // Test that DFPT data types can be constructed and serialized
   TEST(DFPTTypes, PerturbationDataConstruction) {
       DFPTData data(nat=2, nq={2,2,2}, npert=6);
       EXPECT_EQ(data.npert(), 6);
       EXPECT_EQ(data.nq_total(), 8);
   }
   ```

2. **ESolver interface tests** (`test_esolver_dfpt_interface.cpp`):
   ```cpp
   // Test that ESolver_KS_PW_DFPT can be instantiated
   TEST(ESolverDFPT, Instantiation) {
       // Verify inheritance from ESolver_KS_PW
       auto solver = std::make_unique<ESolver_KS_PW_DFPT<std::complex<double>>>();
       EXPECT_NE(solver, nullptr);
   }
   ```

3. **Input parameter tests** (`test_dfpt_input.cpp`):
   ```cpp
   // Test DFPT input parameter parsing
   TEST(DFPTInput, DefaultParameters) {
       Input_para inp;
       EXPECT_FALSE(inp.dfpt_phonon);
       EXPECT_EQ(inp.dfpt_nq1, 1);
       EXPECT_DOUBLE_EQ(inp.dfpt_conv_thr, 1e-8);
   }
   ```

### Integration Tests

- Verify that the module skeleton compiles and links with ABACUS
- Verify that `ESolver_KS_PW_DFPT` can be selected via input parameter `calculation = "dfpt"`

## Acceptance Criteria

- [ ] Architecture document covers all 5 deliverable sections
- [ ] Class hierarchy diagram is complete and consistent
- [ ] Data flow diagram traces full phonon calculation path
- [ ] All QE → ABACUS data structure mappings documented (≥15 mappings)
- [ ] Integration points with existing ABACUS modules identified (≥8 modules)
- [ ] Directory structure proposal reviewed and approved
- [ ] Design document passes technical review by at least one domain expert
