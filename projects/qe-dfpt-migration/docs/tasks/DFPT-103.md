# DFPT-103: Migrate Sternheimer Solver

## Objective

Implement the Sternheimer equation solver `(H - ε_n + α_pv·P_v)·Δψ_n = -P_c^+·ΔV·ψ_n` in ABACUS, including the preconditioned conjugate gradient (CG) linear system solver, diagonal preconditioning, and orthogonalization to occupied states. This is the computational core of every DFPT iteration.

## Reference Code

### QE Source (Fortran)

**Sternheimer wrapper** (`/root/q-e/LR_Modules/response_kernels.f90`):
```fortran
SUBROUTINE sternheimer_kernel(first_iter, time_reversed, npert, lrdvpsi, &
                               iudvpsi, thresh, dvscfins, all_conv, avg_iter, &
                               drhoout, dbecsum, dbecsum_nc)
  ! For each k-point and perturbation:
  !   1. Read dvpsi (bare perturbation × psi) from buffer
  !   2. If not first iteration: add screening dV_SCF × psi
  !   3. Apply P_c^+ (project out occupied states)
  !   4. Call cgsolve_all() to solve linear system
  !   5. Accumulate charge density response via incdrhoscf()
  !
  ! Key: thresh is adaptive — starts large, decreases as SCF converges
  ! thresh = min(0.1 * dr2, initial_thresh)
END SUBROUTINE
```

**CG solver** (`/root/q-e/LR_Modules/cgsolve_all.f90`):
```fortran
SUBROUTINE cgsolve_all(ch_psi, cg_psi, e, d0psi, dpsi, h_diag, &
                        ndmx, ndim, ethr, ik, kter, conv_root, anorm, nbnd, npol)
  ! Solves: (H - e_n + Q) · dpsi_n = d0psi_n  for all bands simultaneously
  !
  ! Algorithm (preconditioned CG):
  !   r = d0psi - (H-e+Q)·dpsi     (residual)
  !   z = M^{-1} · r                (precondition)
  !   p = z                         (search direction)
  !   Loop:
  !     q = (H-e+Q) · p
  !     alpha = (r^H · z) / (p^H · q)
  !     dpsi += alpha · p
  !     r -= alpha · q
  !     z = M^{-1} · r
  !     beta = (r_new^H · z_new) / (r_old^H · z_old)
  !     p = z + beta · p
  !     Check: ||r_n|| < ethr for each band
  !
  ! ch_psi: applies (H - e + Q) — EXTERNAL function pointer
  ! cg_psi: applies preconditioner M^{-1} — EXTERNAL function pointer
  ! h_diag: diagonal elements for preconditioning
  ! ethr: convergence threshold (per band)
  ! kter: returns number of iterations used
  ! conv_root: returns .TRUE. if all bands converged
  !
  ! Max iterations: maxter = 400
  ! Band-parallel: uses intra_bgrp_comm for reductions
END SUBROUTINE
```

**Hamiltonian application** (`/root/q-e/LR_Modules/ch_psi_all.f90`):
```fortran
SUBROUTINE ch_psi_all(n, h, ah, e, ik, m)
  ! Applies (H - e·S + Q) to h, result in ah
  ! Q = alpha_pv * P_v (projector onto valence states)
  !
  ! Steps:
  !   1. ah = H · h          (apply full Hamiltonian)
  !   2. ah -= e · S · h     (subtract eigenvalue × overlap)
  !   3. spsi = S · h        (overlap for USPP)
  !   4. ps = ⟨psi|spsi⟩    (project onto occupied states)
  !   5. ah += alpha_pv * psi · ps  (add projector term)
END SUBROUTINE
```

**Preconditioning** (`/root/q-e/LR_Modules/cg_psi.f90`):
```fortran
SUBROUTINE cg_psi(lda, n, m, psi, h_diag)
  ! Diagonal preconditioning:
  ! psi(G,n) = psi(G,n) * h_diag(G,n)
  ! where h_diag(G,n) = 1.0 / max(1.0, |k+q+G|^2 - e_n)
  !
  ! Note: uses k+q (not just k) for the kinetic energy
END SUBROUTINE
```

**Orthogonalization** (`/root/q-e/LR_Modules/orthogonalize.f90`):
```fortran
SUBROUTINE orthogonalize(dpsi, evq, ikk, ikq, dpsi_out, npwq, ...)
  ! Projects dpsi onto conduction band subspace:
  ! dpsi_out = (1 - P_v) · dpsi = dpsi - Σ_m |ψ_m(k+q)⟩⟨ψ_m(k+q)|dpsi⟩
  !
  ! For metals: uses smooth occupation function
  ! For USPP: uses S operator in projection
END SUBROUTINE
```

### ABACUS Target — Existing Implementation

**HSolverPW_DFPT** (`/root/abacus-dfpt/abacus-develop/source/source_hsolver/hsolver_pw_dfpt.h`):
```cpp
template <typename T, typename Device>
class HSolverPW_DFPT {
public:
    void solve_dfpt(hamilt::HamiltPW_DFPT<T, Device>* pHamilt,
                    psi::Psi<T, Device>& psi,        // ground-state ψ
                    psi::Psi<T, Device>& dpsi,       // response Δψ (output)
                    const T* dvpsi,                   // RHS: -P_c^+ ΔV·ψ
                    const double* eigenvalues,
                    int ik, int nbands_occ);

    void compute_dfpt_preconditioner(double* h_diag,
                                      const double* eigenvalues,
                                      int npw, int nbands,
                                      const ModuleBase::Vector3<double>& kq);

private:
    double dfpt_cg_threshold_;
    int dfpt_max_cg_iter_;
    double alpha_pv_;  // default 0.3
};
```

**DiagoCG_LR** (`/root/abacus-dfpt/abacus-develop/source/source_hsolver/diago_cg_lr.h`):
```cpp
template <typename T, typename Device>
class DiagoCG_LR {
public:
    using hpsi_func_type = std::function<void(const ct::Tensor&, ct::Tensor&)>;
    using spsi_func_type = std::function<void(const ct::Tensor&, ct::Tensor&)>;

    void solve(hpsi_func_type hpsi_func,    // (H-e+Q) application
               spsi_func_type spsi_func,    // S application (identity for NC)
               const T* preconditioner,     // diagonal preconditioner
               const T* rhs,               // right-hand side
               T* solution,                // output
               int nbasis, int nbands,
               double conv_thr, int max_iter,
               int& niter, bool& converged);

private:
    void solve_band(/* single band solver */);
    void apply_h_minus_e_plus_q(/* operator application */);
    void orthogonalize_to_valence(/* P_c projection */);
    void apply_preconditioner(/* diagonal preconditioning */);
    void compute_alpha(/* CG step size */);
    void compute_beta(/* CG conjugation */);
    bool check_convergence(/* ||r|| < thr */);
};
```

### dvqpsi_cpp Reference

**SternheimerSolver** (`/root/q-e/PHonon/dvqpsi_cpp/include/sternheimer_solver.hpp`):
```cpp
class SternheimerSolver {
public:
    SternheimerSolver(const FFTGrid& grid, const GVectorData& gvec);

    // Solve Sternheimer equation for all bands at one k-point
    void solve(const WaveFunction& wfc_k,      // ground-state ψ(k)
               const WaveFunction& wfc_kq,     // ground-state ψ(k+q)
               const ComplexVec& dvpsi,         // bare perturbation × ψ
               const ComplexVec& dvscf,         // SCF potential response
               ComplexVec& dpsi,                // output: Δψ
               double conv_thr);

private:
    CGSolver cg_solver_;
    Preconditioner precond_;
    HamiltonianOperator hamilt_op_;
    double alpha_pv_ = 0.3;
};
```

**CGSolver** (`/root/q-e/PHonon/dvqpsi_cpp/include/cg_solver.hpp`):
```cpp
class CGSolver {
public:
    struct Stats {
        int total_iterations;
        int converged_bands;
        double max_residual;
    };

    Stats solve(const std::function<void(const ComplexVec&, ComplexVec&)>& apply_A,
                const RealVec& preconditioner,
                const ComplexVec& rhs,
                ComplexVec& solution,
                int npw, int nbands,
                double conv_thr, int max_iter);
};
```

**Preconditioner** (`/root/q-e/PHonon/dvqpsi_cpp/include/preconditioner.hpp`):
```cpp
class Preconditioner {
public:
    // h_diag(G,n) = 1.0 / max(1.0, |k+q+G|^2 - e_n)
    void compute(RealVec& h_diag,
                 const GVectorData& gvec,
                 const KPointData& kpt_kq,
                 const RealVec& eigenvalues,
                 int npw, int nbands);
};
```

## Implementation Guide

### Architecture

```
HSolverPW_DFPT::solve_dfpt()
├── 1. Compute preconditioner h_diag
│   └── h_diag(G,n) = 1/max(1.0, |k+q+G|² - ε_n)
├── 2. Prepare RHS
│   ├── rhs = dvpsi (bare perturbation × ψ)
│   ├── If not first iter: rhs += dvscf × ψ (screening)
│   └── rhs = -P_c^+ · rhs (project out occupied states)
├── 3. Setup operator (H - ε + α_pv·P_v)
│   ├── H application via HamiltPW_DFPT
│   ├── Eigenvalue subtraction
│   └── Valence projector P_v = Σ_m |ψ_m⟩⟨ψ_m|
└── 4. Call DiagoCG_LR::solve()
    └── Preconditioned CG iteration
        ├── r = rhs - A·x
        ├── z = M^{-1}·r
        ├── p = z
        └── Loop: α, update x, update r, β, update p
```

### Key Equations

**Sternheimer equation**:
```
(H_{k+q} - ε_{n,k} · S + α_pv · P_v) |Δψ_{n,k}⟩ = -P_c^+ · (ΔV_bare + ΔV_SCF) |ψ_{n,k}⟩
```

**Projector onto conduction states**:
```
P_c^+ = 1 - Σ_{m∈occ} |ψ_m(k+q)⟩⟨ψ_m(k+q)|S
```
For norm-conserving PP: S = 1. For USPP: S includes augmentation.

**Diagonal preconditioner**:
```
M^{-1}(G,n) = 1 / max(1.0, |k+q+G|² - ε_n)
```
where `|k+q+G|²` is in Ry units (includes `tpiba²` factor).

**Adaptive threshold** (from QE `dfpt_kernels.f90`):
```
thresh = min(0.1 × dr2, initial_thresh)
```
where `dr2` is the SCF convergence metric from the previous iteration.

### Critical Implementation Details

1. **Operator application `(H - ε + Q)`**: This is the most performance-critical function. For each CG iteration, it applies:
   ```cpp
   void apply_A(const T* x, T* Ax, int nbands, int npw, int ik) {
       // Step 1: Ax = H · x (full Hamiltonian at k+q)
       hamilt_dfpt->ops->act(nbands, npw, 1, x, Ax);

       // Step 2: Ax -= ε_n · x (subtract eigenvalue)
       for (int ib = 0; ib < nbands; ib++) {
           for (int ig = 0; ig < npw; ig++) {
               Ax[ib*npw + ig] -= eigenvalues[ib] * x[ib*npw + ig];
           }
       }

       // Step 3: Ax += α_pv · P_v · x (valence projector)
       // P_v · x = Σ_m |ψ_m⟩ ⟨ψ_m|x⟩
       // Compute overlap: ps[m] = ⟨ψ_m|x⟩ for all occupied m
       // Ax += α_pv · Σ_m ps[m] · ψ_m
       compute_projector(x, Ax, psi_occ, nbands_occ, npw, alpha_pv);
   }
   ```

2. **Orthogonalization P_c^+**: Must be applied to the RHS before CG solve:
   ```cpp
   void orthogonalize_to_valence(T* dpsi, const T* psi_kq, int nbands, int nbands_occ, int npw) {
       // For each response band n:
       //   dpsi_n -= Σ_{m∈occ} |ψ_m(k+q)⟩ ⟨ψ_m(k+q)|dpsi_n⟩
       std::vector<T> overlap(nbands_occ);
       for (int n = 0; n < nbands; n++) {
           // Compute overlaps
           for (int m = 0; m < nbands_occ; m++) {
               overlap[m] = BlasConnector::dotc(npw,
                   psi_kq + m*npw, 1, dpsi + n*npw, 1);
           }
           // MPI reduce overlaps across processors
           Parallel_Reduce::reduce_pool(overlap.data(), nbands_occ);
           // Subtract projections
           for (int m = 0; m < nbands_occ; m++) {
               BlasConnector::axpy(npw, -overlap[m],
                   psi_kq + m*npw, 1, dpsi + n*npw, 1);
           }
       }
   }
   ```

3. **CG convergence per band**: Each band converges independently. Track convergence flags:
   ```cpp
   std::vector<bool> converged(nbands, false);
   for (int iter = 0; iter < max_iter; iter++) {
       for (int ib = 0; ib < nbands; ib++) {
           if (converged[ib]) continue;
           double residual = compute_residual_norm(ib);
           if (residual < conv_thr) {
               converged[ib] = true;
           }
       }
       if (std::all_of(converged.begin(), converged.end(), [](bool c){return c;}))
           break;
   }
   ```

4. **alpha_pv parameter**: QE computes this adaptively as `alpha_pv = max(eigenvalue) + 1.0`. dvqpsi_cpp uses fixed `0.3`. The ABACUS implementation should support both:
   ```cpp
   // Adaptive: alpha_pv = max(et[nbands_occ-1]) - min(et[0]) + 1.0
   // Fixed: alpha_pv = 0.3 (simpler, works for insulators)
   ```

5. **Metal systems**: For metals, the occupation function is smooth (Fermi-Dirac or Gaussian smearing). The projector must use fractional occupations:
   ```cpp
   // P_v = Σ_m f_m |ψ_m⟩⟨ψ_m|  where f_m is occupation
   // For insulators: f_m = 1 for m ≤ nbands_occ, 0 otherwise
   // For metals: f_m = fermi_dirac(ε_m, ε_F, σ)
   ```

### Performance Considerations

- CG iteration is O(nbands × npw × nbands_occ) per iteration (dominated by projector)
- Typical: 20-50 CG iterations per band
- Total per k-point per perturbation: O(cg_iter × nbands × npw × nbands_occ)
- BLAS-3 optimization: batch projector computation using ZGEMM instead of per-band ZDOTC

## TDD Test Plan

### Unit Tests to Write FIRST

```cpp
// test/test_sternheimer.cpp

// 1. Preconditioner formula verification
TEST(Sternheimer, PreconditionerFormula) {
    const int npw = 100, nbands = 4;
    auto gvec = create_test_gvectors(npw);
    auto kq = ModuleBase::Vector3<double>(0.25, 0.0, 0.0);
    double eigenvalues[] = {-0.5, -0.3, -0.1, 0.2};  // Ry

    std::vector<double> h_diag(npw * nbands);
    compute_preconditioner(h_diag.data(), eigenvalues, gvec, kq, npw, nbands);

    for (int ib = 0; ib < nbands; ib++) {
        for (int ig = 0; ig < npw; ig++) {
            double kqg2 = compute_kqg_squared(kq, gvec, ig);  // |k+q+G|²
            double expected = 1.0 / std::max(1.0, kqg2 - eigenvalues[ib]);
            EXPECT_NEAR(h_diag[ib*npw + ig], expected, 1e-14);
        }
    }
}

// 2. Orthogonalization completeness
TEST(Sternheimer, OrthogonalizationComplete) {
    const int npw = 200, nbands = 6, nbands_occ = 4;
    auto psi = create_orthonormal_wavefunctions(npw, nbands);
    auto dpsi = create_random_vector(npw * nbands);

    orthogonalize_to_valence(dpsi.data(), psi.data(), nbands, nbands_occ, npw);

    // Verify: ⟨ψ_m|dpsi_n⟩ = 0 for all occupied m
    for (int n = 0; n < nbands; n++) {
        for (int m = 0; m < nbands_occ; m++) {
            auto overlap = zdotc(npw, psi.data() + m*npw, dpsi.data() + n*npw);
            EXPECT_NEAR(std::abs(overlap), 0.0, 1e-13);
        }
    }
}

// 3. CG solver on known linear system
TEST(Sternheimer, CGSolverKnownSystem) {
    // Solve A·x = b where A is a known positive-definite matrix
    const int n = 50;
    auto A = create_spd_matrix(n);  // symmetric positive definite
    auto b = create_random_vector(n);
    auto x = std::vector<std::complex<double>>(n, 0.0);

    auto apply_A = [&](const auto& in, auto& out) {
        matvec(A, in, out, n);
    };
    auto precond = compute_diagonal_preconditioner(A, n);

    int niter;
    bool converged;
    cg_solve(apply_A, precond, b, x, n, 1, 1e-12, 200, niter, converged);

    EXPECT_TRUE(converged);
    // Verify: A·x ≈ b
    auto Ax = std::vector<std::complex<double>>(n);
    matvec(A, x, Ax, n);
    for (int i = 0; i < n; i++) {
        EXPECT_NEAR(std::abs(Ax[i] - b[i]), 0.0, 1e-10);
    }
}

// 4. Sternheimer solution orthogonal to occupied states
TEST(Sternheimer, SolutionOrthogonality) {
    auto system = create_test_dfpt_system();
    auto dpsi = solve_sternheimer(system);

    // Δψ must be orthogonal to all occupied states
    for (int n = 0; n < system.nbands; n++) {
        for (int m = 0; m < system.nbands_occ; m++) {
            auto overlap = zdotc(system.npw,
                system.psi_kq + m*system.npw,
                dpsi.data() + n*system.npw);
            EXPECT_NEAR(std::abs(overlap), 0.0, 1e-12);
        }
    }
}

// 5. Convergence rate test
TEST(Sternheimer, ConvergenceRate) {
    auto system = create_test_dfpt_system();
    std::vector<double> residuals;

    auto dpsi = solve_sternheimer_with_history(system, residuals);

    // CG should converge monotonically
    for (size_t i = 1; i < residuals.size(); i++) {
        EXPECT_LE(residuals[i], residuals[i-1] * 1.01);  // allow small fluctuation
    }
    // Should converge in reasonable iterations
    EXPECT_LT(residuals.size(), 100);
}

// 6. Consistency with dvqpsi_cpp Sternheimer
TEST(Sternheimer, ConsistencyWithStandalone) {
    auto [abacus_data, dvqpsi_data] = create_matched_sternheimer_data();

    auto dpsi_abacus = solve_sternheimer_abacus(abacus_data);
    auto dpsi_standalone = solve_sternheimer_dvqpsi(dvqpsi_data);

    compare_complex_arrays(dpsi_abacus, dpsi_standalone, 1e-10);
}

// 7. Component-wise comparison with QE cgsolve_all
TEST(Sternheimer, CGSolveVsQEReference) {
    // Load QE reference: dpsi from cgsolve_all for Si system
    auto qe_ref = load_qe_reference("test_data/si_dpsi_qe.dat");
    auto abacus_result = run_abacus_sternheimer_si();

    // Per-band comparison
    for (int ib = 0; ib < qe_ref.nbands; ib++) {
        double error = compute_band_error(abacus_result, qe_ref, ib);
        EXPECT_LT(error, 1e-8);
    }
}
```

### Milestone 2 Smoke Test

```cpp
// End-to-end: DVQPsiUS + Sternheimer data flow
TEST(M2SmokeTest, SiDVQPsiPlusSternheimer) {
    // 1. Run ground-state SCF for Si
    auto gs = run_ground_state_si();

    // 2. Compute dvpsi = dV_bare · ψ (from DFPT-102)
    auto dvpsi = compute_dvpsi(gs, /*iq=*/0, /*ipert=*/0);

    // 3. Solve Sternheimer equation
    auto dpsi = solve_sternheimer(gs, dvpsi, /*iq=*/0);

    // 4. Verify solution quality
    EXPECT_TRUE(dpsi.converged);
    EXPECT_LT(dpsi.max_residual, 1e-10);

    // 5. Verify orthogonality
    verify_orthogonality(dpsi, gs.psi_kq, gs.nbands_occ);
}
```

## Acceptance Criteria

- [ ] Sternheimer solver fully implemented with CG, preconditioning, and orthogonalization
- [ ] CG solver converges for test linear systems (known SPD matrix)
- [ ] Preconditioner formula uses k+q (not just k) — verified by unit test
- [ ] Solution orthogonal to occupied states (overlap < 1e-12)
- [ ] Convergence is monotonic (residual decreases each iteration)
- [ ] Component-wise error vs QE `cgsolve_all` < 1e-8
- [ ] Sternheimer residual < 1e-10 for Si test system
- [ ] M2 Smoke Test passes: Si DVQPsiUS + Sternheimer end-to-end
- [ ] Performance: CG iterations ≤ 50 per band for Si system
- [ ] Code review passes 6-agent DFPT review
