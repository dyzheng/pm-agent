# DFPT-102: Migrate DVQPsiUS Core Kernel

## Objective

Migrate the core DFPT kernel — computation of `dV/dτ · ψ` (perturbation potential applied to wavefunctions) — into the ABACUS module architecture. This includes local potential, nonlocal pseudopotential, and ultrasoft augmentation contributions. The dvqpsi_cpp standalone implementation serves as the primary reference.

## Reference Code

### QE Source (Fortran)

**Core kernel** (`/root/q-e/PHonon/PH/dvqpsi_us.f90`):
```fortran
SUBROUTINE dvqpsi_us(ik, uact, addnlcc, becp1, alphap)
  ! Computes dV_bare/du · psi for one perturbation pattern uact
  ! Three contributions:
  !   1. dV_loc/du · psi  (local potential derivative)
  !   2. dV_nl/du · psi   (nonlocal pseudopotential derivative)
  !   3. dV_nlcc/du · psi (non-linear core correction)
  !
  ! Algorithm for local part:
  !   a. Compute dV_loc(G) = sum_atom V_loc(|q+G|,type) * i*(q+G)·u * e^{i(q+G)·tau}
  !   b. IFFT to real space: dV_loc(r)
  !   c. For each band: FFT(psi) → multiply by dV_loc(r) → IFFT → extract at k+q
  !
  ! Key variables:
  !   dvscfin(dffts%nnr, nspin) — input: induced potential (zero for bare)
  !   dvpsi(npwx, nbnd) — output: dV·psi at k+q
END SUBROUTINE
```

**Nonlocal contribution** (`/root/q-e/PHonon/PH/dvqpsi_us_only.f90`):
```fortran
SUBROUTINE dvqpsi_us_only(ik, uact, becp1, alphap)
  ! Nonlocal pseudopotential derivative:
  !   dV_nl·psi = sum_{ij} [|dβ_i⟩ D_ij ⟨β_j|psi⟩ + |β_i⟩ D_ij ⟨dβ_j|psi⟩]
  ! where dβ/dτ = i*(k+G)·u * β(G)
  !
  ! Uses precomputed:
  !   becp1(ik)%k = ⟨β|psi⟩ at k
  !   alphap(ipol, ik)%k = ⟨dβ/dk_ipol|psi⟩ at k
  !   int1(nhm, nhm, 3, nat, nspin) — ⟨β|dV_loc|β'⟩ integrals
  !   int2(nhm, nhm, 3, nat, nat) — ⟨β|dV_nl|β'⟩ integrals
END SUBROUTINE
```

**Structure factor derivative** (`/root/q-e/PHonon/PH/dvanqq.f90`):
```fortran
! dS/dτ_κα = i*(q+G)_α * S_κ(q+G)
! where S_κ(G) = e^{-iG·τ_κ}
```

### ABACUS Target — Existing Implementation

**DVloc operator** (`/root/abacus-dfpt/abacus-develop/source/source_pw/module_pwdft/operator_pw/dfpt/dvloc_pw.h`):
```cpp
template <typename T, typename Device>
class DVloc : public OperatorPW<T, Device> {
public:
    // Apply dV_loc/dτ · ψ
    void act(const int nbands, const int nbasis, const int npol,
             const T* tmpsi_in, T* tmhpsi, const int ngk_ik = 0) const override;

    void set_displacement(const ModuleBase::Vector3<double>& u);
    void set_qpoint(const ModuleBase::Vector3<double>& xq);
    void init_k(int ik);
};
```

**Algorithm in DVloc::act()**:
```
1. Compute dV_loc(G) for current perturbation:
   dV_loc(G) = V_loc(|q+G|, type) × i(q+G)·u × e^{i(q+G)·τ}
   (sum over atoms of this type)

2. IFFT: dV_loc(G) → dV_loc(r)

3. For each band ib:
   a. IFFT: ψ(G, ik) → ψ(r)
   b. Multiply: aux(r) = dV_loc(r) × ψ(r)
   c. FFT: aux(r) → aux(G)
   d. Extract: dvpsi(G, ik+q) = aux(G) at k+q G-vectors
```

### dvqpsi_cpp Reference

**DVQPsiUS class** (`/root/q-e/PHonon/dvqpsi_cpp/include/dvqpsi_us.hpp`):
```cpp
class DVQPsiUS {
public:
    DVQPsiUS(const FFTGrid& grid, const GVectorData& gvec);

    // Main computation: dV_bare · psi
    void compute(const SystemGeometry& geom,
                 const WaveFunction& wfc_k,
                 const KPointData& kpt_k,
                 const KPointData& kpt_kq,
                 const std::array<double,3>& uact,
                 int iat,
                 ComplexVec& dvpsi);

    // Individual contributions
    void compute_dvloc(/* ... */);     // Local potential
    void compute_dvnl(/* ... */);      // Nonlocal (beta projectors)
    void compute_dvus(/* ... */);      // Ultrasoft augmentation

private:
    FFTGrid grid_;
    GVectorData gvec_;
    FFTWrapper fft_;
    ComplexVec work_r_, work_g_;       // Workspace arrays
};
```

**Performance**: O(nbnd × nnr × log(nnr)) per perturbation per k-point.

**Existing tests** (`/root/q-e/PHonon/dvqpsi_cpp/tests/test_dvqpsi.cpp`):
- `DVQPsiUS_LocalPotential`: Verifies local contribution against analytic formula
- `DVQPsiUS_StructureFactor`: Verifies e^{iG·τ} computation
- `DVQPsiUS_Symmetry`: Verifies symmetry properties of dvpsi

**ABACUS DFPT tests** (`/root/abacus-dfpt/abacus-develop/source/source_pw/module_pwdft/operator_pw/test/`):
- `nonlocal_pw_dfpt_test.cpp` — 20 tests for nonlocal operator DFPT
- `veff_pw_dfpt_test.cpp` — 13 tests for effective potential DFPT
- `H_Hartree_pw_dfpt_test.cpp` — 18 tests for Hartree potential DFPT
- `pot_local_dfpt_test.cpp` — 17 tests for local potential DFPT
- `dfpt_test_utils.h/cpp` — Test utilities (random wavefunctions, comparison)

## Implementation Guide

### Architecture

```
DVQPsiUS (unified kernel)
├── DVloc (local potential derivative)
│   ├── Compute dV_loc(G) using structure factor derivative
│   ├── IFFT to real space
│   └── Band loop: FFT(ψ) × dV_loc → IFFT → extract at k+q
├── DVnl (nonlocal pseudopotential derivative)
│   ├── Compute dβ/dτ = i(k+G)·u × β(G)
│   ├── Project: ⟨β|ψ⟩ and ⟨dβ|ψ⟩
│   └── Accumulate: |dβ⟩D⟨β|ψ⟩ + |β⟩D⟨dβ|ψ⟩
└── DVus (ultrasoft augmentation)
    ├── Compute dQ/dτ augmentation charge derivative
    └── Add augmentation contribution to dvpsi
```

### Key Equations

**Local potential derivative**:
```
dV_loc(G)/dτ_κα = i(q+G)_α × V_loc(|q+G|, type_κ) × e^{-i(q+G)·τ_κ}
```

**Nonlocal potential derivative** (for atom κ displaced along α):
```
δV_NL|ψ⟩ = Σ_{ij} [|dβ_i^κ/dτ_α⟩ D_ij ⟨β_j^κ|ψ⟩ + |β_i^κ⟩ D_ij ⟨dβ_j^κ/dτ_α|ψ⟩]

where dβ^κ(G)/dτ_α = i(k+q+G)_α × β^κ(G) × e^{-i(k+q+G)·τ_κ}
```

**Ultrasoft augmentation** (additional term for USPP):
```
δV_US|ψ⟩ = Σ_{ij} |β_i⟩ dD_ij/dτ_α ⟨β_j|ψ⟩
           + Σ_{ij} |β_i⟩ D_ij d⟨β_j|ψ⟩/dτ_α
```

### Critical Implementation Details

1. **Structure factor phase convention**: QE uses `e^{-iG·τ}` for structure factor. The derivative is `dS/dτ_α = -i·G_α · S(G)`. Verify sign convention matches between QE and ABACUS.

2. **G-vector at k+q**: The output dvpsi lives at k+q, not k. Must use k+q G-vector set for extraction:
   ```cpp
   // After real-space multiplication, FFT back and extract at k+q points
   for (int ig = 0; ig < npw_kq; ig++) {
       dvpsi[ig + ib * npw_kq] = aux_g[igk_kq[ig]];
   }
   ```

3. **Local potential in reciprocal space**: `V_loc(|q+G|)` must be interpolated from the pseudopotential table. ABACUS stores this in `VL_in_pw` class.

4. **Nonlocal projector derivative**: The derivative `dβ/dτ` involves the displacement direction. For atom κ displaced along α:
   ```cpp
   // dβ_κ(G)/dτ_α = i*(k+q+G)_α * β_κ(G) * e^{-i(k+q+G)·τ_κ}
   for (int ig = 0; ig < npw_kq; ig++) {
       double kqg_alpha = (kvec[0] + xq[0] + g[ig][0]) * ucell.lat0;  // in Bohr⁻¹
       dbeta[ig] = std::complex<double>(0, kqg_alpha) * beta[ig] * phase[ig];
   }
   ```

5. **OpenMP parallelization**: The band loop is embarrassingly parallel:
   ```cpp
   #pragma omp parallel for private(work_r, work_g)
   for (int ib = 0; ib < nbands; ib++) {
       // FFT(ψ_ib) → multiply → IFFT → extract
   }
   ```

### Fortran → C++ Adaptation Notes

| QE Pattern | ABACUS Pattern | Notes |
|-----------|---------------|-------|
| `dvpsi(npwx, nbnd)` | `std::vector<T>` or `psi::Psi<T>` | Contiguous memory |
| `CALL cft3s(aux, ..., -1)` | `pw_basis->recip2real(in, out)` | Inverse FFT |
| `CALL cft3s(aux, ..., +1)` | `pw_basis->real2recip(in, out)` | Forward FFT |
| `ZDOTC(npw, vkb, 1, psi, 1)` | `BlasConnector::dotc(npw, vkb, 1, psi, 1)` | BLAS dot product |
| `becp1(ik)%k(jkb, ibnd)` | Precomputed `⟨β\|ψ⟩` matrix | Store in adapter |

## TDD Test Plan

### Unit Tests to Write FIRST

```cpp
// test/test_dvqpsi_us.cpp

// 1. Local potential derivative — analytic test
TEST(DVQPsiUS, LocalPotentialSingleAtom) {
    // Single atom at origin, uniform displacement along z
    // dV_loc(G)/dτ_z = i*G_z * V_loc(|G|) * 1 (S=1 for atom at origin)
    auto [grid, gvec, geom] = create_single_atom_system();
    DVQPsiUS kernel(grid, gvec);

    // Create test wavefunction: single plane wave e^{ikr}
    auto wfc = create_plane_wave(grid, {0, 0, 1});
    auto kpt_k = create_kpoint({0, 0, 0});
    auto kpt_kq = create_kpoint({0, 0, 0});  // q=0

    ComplexVec dvpsi(wfc.npw * wfc.nbnd);
    kernel.compute(geom, wfc, kpt_k, kpt_kq, {0, 0, 1.0}, 0, dvpsi);

    // Verify: dvpsi should be proportional to i*G_z * V_loc * psi
    // (analytic formula for single atom at origin)
    verify_local_potential_analytic(dvpsi, grid, gvec, wfc);
}

// 2. Translational invariance
TEST(DVQPsiUS, TranslationalInvariance) {
    // Sum of dvpsi over all atoms should be zero for q=0
    // (uniform translation produces no force)
    auto [grid, gvec, geom] = create_si_system();
    DVQPsiUS kernel(grid, gvec);
    auto wfc = create_random_wavefunction(grid, 4);

    ComplexVec dvpsi_total(wfc.npw * wfc.nbnd, 0.0);
    for (int iat = 0; iat < geom.nat; iat++) {
        ComplexVec dvpsi_atom(wfc.npw * wfc.nbnd);
        kernel.compute(geom, wfc, kpt, kpt, {1, 0, 0}, iat, dvpsi_atom);
        for (size_t i = 0; i < dvpsi_total.size(); i++) {
            dvpsi_total[i] += dvpsi_atom[i];
        }
    }
    // Sum should be zero (translational invariance)
    double norm = compute_norm(dvpsi_total);
    EXPECT_LT(norm, 1e-10);
}

// 3. Hermiticity check
TEST(DVQPsiUS, HermiticityProperty) {
    // ⟨ψ_m(k+q)|dV|ψ_n(k)⟩ = ⟨ψ_n(-k)|dV†|ψ_m(-k-q)⟩*
    // For q=0: matrix should be Hermitian
    auto [grid, gvec, geom] = create_si_system();
    DVQPsiUS kernel(grid, gvec);
    auto wfc = create_random_wavefunction(grid, 4);

    // Compute ⟨ψ_m|dV|ψ_n⟩ matrix
    auto dvpsi = compute_dvpsi_matrix(kernel, geom, wfc);
    // Check Hermiticity
    for (int m = 0; m < 4; m++) {
        for (int n = 0; n < 4; n++) {
            EXPECT_NEAR(std::abs(dvpsi(m,n) - std::conj(dvpsi(n,m))), 0.0, 1e-10);
        }
    }
}

// 4. Nonlocal contribution — beta projector derivative
TEST(DVQPsiUS, NonlocalBetaDerivative) {
    // dβ/dτ_z = i*(k+q+G)_z * β(G)
    auto beta = create_test_beta_projector(100);  // 100 G-vectors
    auto dbeta = compute_dbeta(beta, {0,0,1}, kpt_kq);

    for (int ig = 0; ig < 100; ig++) {
        auto expected = std::complex<double>(0, kqg_z[ig]) * beta[ig];
        EXPECT_NEAR(std::abs(dbeta[ig] - expected), 0.0, 1e-14);
    }
}

// 5. Numerical vs analytic comparison for simple system
TEST(DVQPsiUS, NumericalVsAnalytic) {
    // Compare DFPT result with finite-difference:
    // dV/dτ ≈ [V(τ+δ) - V(τ-δ)] / (2δ)
    auto system = create_simple_system();
    double delta = 1e-4;  // Bohr

    auto dvpsi_dfpt = compute_dvpsi_dfpt(system);
    auto dvpsi_fd = compute_dvpsi_finite_diff(system, delta);

    compare_complex_arrays(dvpsi_dfpt, dvpsi_fd, 1e-6);  // FD has O(δ²) error
}

// 6. Consistency with dvqpsi_cpp standalone
TEST(DVQPsiUS, ConsistencyWithStandalone) {
    // Run same calculation with dvqpsi_cpp and ABACUS DVloc
    // Results must match to machine precision
    auto [abacus_data, dvqpsi_data] = create_matched_test_data();

    auto dvpsi_abacus = run_abacus_dvloc(abacus_data);
    auto dvpsi_standalone = run_dvqpsi_cpp(dvqpsi_data);

    compare_complex_arrays(dvpsi_abacus, dvpsi_standalone, 1e-12);
}

// 7. Performance benchmark
TEST(DVQPsiUS, PerformanceBenchmark) {
    // Si system: 32³ grid, 10 bands, 8 k-points
    auto system = create_si_benchmark_system();
    auto start = high_resolution_clock::now();

    for (int ik = 0; ik < 8; ik++) {
        for (int ipert = 0; ipert < 6; ipert++) {
            compute_dvpsi(system, ik, ipert);
        }
    }

    auto elapsed_ms = duration_cast<milliseconds>(
        high_resolution_clock::now() - start).count();
    // 8 k-points × 6 perturbations should complete in < 5 seconds
    EXPECT_LT(elapsed_ms, 5000);
}
```

### Integration Tests

```cpp
// Compare with QE reference data for Si
TEST(DVQPsiUS_Integration, SiReferenceComparison) {
    // Load QE reference dvpsi from file
    auto qe_ref = load_qe_reference("test_data/si_dvpsi_qe.dat");
    auto abacus_result = run_abacus_dvpsi_si();

    // Phonon-relevant quantity: force constant contribution
    // Error must be < 1e-10 Ry/Bohr²
    for (int i = 0; i < qe_ref.size(); i++) {
        EXPECT_NEAR(std::abs(abacus_result[i] - qe_ref[i]), 0.0, 1e-10);
    }
}
```

## Acceptance Criteria

- [ ] `DVQPsiUS` class fully implemented with local + nonlocal + ultrasoft contributions
- [ ] Numerical results match dvqpsi_cpp standalone to < 1e-12
- [ ] Numerical results match QE reference to < 1e-10
- [ ] Translational invariance test passes (sum over atoms = 0 for q=0)
- [ ] Hermiticity test passes for q=0
- [ ] Finite-difference validation passes (DFPT vs FD agreement to O(δ²))
- [ ] Performance comparable to dvqpsi_cpp (within 20%)
- [ ] All unit tests pass (≥7 test cases)
- [ ] Code review passes 6-agent DFPT review
- [ ] OpenMP parallelization over bands implemented
