# DFPT-201: Implement DFPT Self-Consistent Field Iteration

## Objective

Implement the DFPT SCF loop that iteratively solves for the self-consistent response potential ΔV_SCF. Each iteration: solve Sternheimer → compute Δρ → compute ΔV_SCF (Hartree + XC) → mix → check convergence. This is the outer loop that wraps the Sternheimer solver (DFPT-103) and drives convergence of the linear response.

## Reference Code

### QE Source (Fortran)

**DFPT SCF loop** (`/root/q-e/LR_Modules/dfpt_kernels.f90`):
```fortran
SUBROUTINE dfpt_kernel(code, npert, iter0, lrdvpsi, iudvpsi, dr2, dfpt_data, ...)
  ! Main self-consistent DFPT loop
  !
  ! DO kter = 1, niter_ph
  !   1. Set adaptive threshold: thresh = min(0.1*dr2, initial_thresh)
  !   2. IF (lda_plus_u) CALL dnsq_scf()
  !   3. DO isolv = 1, nsolv  (nsolv=2 for noncollinear magnetic)
  !      a. CALL sternheimer_kernel()  → dpsi, drhos
  !      b. CALL sternheimer_postprocess() → symmetrize drhos, add augmentation
  !   4. IF (lmetq0) CALL ef_shift_new()  → Fermi energy shift for metals
  !   5. CALL psymdvscf()  → symmetrize response potential
  !   6. CALL dv_of_drho()  → compute ΔV_HXC from Δρ
  !   7. CALL mix_potential()  → Broyden mixing
  !   8. CALL dfpt_dvscfp_to_dvscfs()  → FFT interpolate to smooth grid
  !   9. CALL newdq()  → compute int3 for USPP
  !   10. Check convergence: IF (dr2 < tr2_ph) convt = .TRUE.
  ! ENDDO
END SUBROUTINE
```

**Response potential** (`/root/q-e/LR_Modules/dv_of_drho.f90`):
```fortran
SUBROUTINE dv_of_drho(dvscf, drhoc)
  ! Computes ΔV_HXC = ΔV_Hartree + ΔV_XC from Δρ
  !
  ! Hartree (reciprocal space):
  !   ΔV_H(G) = 4π·e² · Δρ(G) / |q+G|²
  !   (G=0 excluded for q≠0; special treatment for q=0)
  !
  ! XC (real space):
  !   ΔV_xc(r) = f_xc(r) · Δρ(r)
  !   where f_xc = d²E_xc/dρ² (XC kernel)
  !   For GGA: additional gradient terms
  !
  ! Core charge correction (NLCC):
  !   Δρ_total = Δρ_valence + Δρ_core
  !   drhoc = core charge derivative
END SUBROUTINE
```

**Charge density response** (`/root/q-e/LR_Modules/incdrhoscf.f90`):
```fortran
SUBROUTINE incdrhoscf(drhoscf, weight, ik, dbecsum, dpsi, ...)
  ! Accumulates charge density response from wavefunction response:
  !   Δρ(r) += w_k · Σ_n f_n · [ψ*_n(k+q,r) · Δψ_n(k,r) + c.c.]
  !
  ! For each band n:
  !   1. IFFT: Δψ_n(G) → Δψ_n(r)
  !   2. IFFT: ψ_n(k+q,G) → ψ_n(k+q,r)
  !   3. Δρ(r) += w_k · f_n · ψ*_n(k+q,r) · Δψ_n(k,r)
  !   4. Δρ(r) += w_k · f_n · Δψ*_n(k,r) · ψ_n(k+q,r)  (c.c. for time-reversal)
  !
  ! For USPP: also accumulates dbecsum
END SUBROUTINE
```

**Potential mixing** (`/root/q-e/Modules/mix_pot.f90`):
```fortran
SUBROUTINE mix_potential(ndim, vout, vin, alpha_mix, dr2, tr2, iter, n_iter, ...)
  ! Broyden mixing of response potential:
  !   v_in(new) = mix(v_out, v_in_history)
  !
  ! dr2 = ||v_out - v_in||² (convergence metric)
  ! alpha_mix = mixing parameter (0.7 typical)
  ! n_iter = number of previous iterations to keep (Broyden history)
  !
  ! For first iteration: simple linear mixing
  ! For subsequent: modified Broyden (Johnson) mixing
END SUBROUTINE
```

### ABACUS Target — Existing Implementation

**ESolver DFPT SCF** (`/root/abacus-dfpt/abacus-develop/source/source_esolver/esolver_ks_pw_dfpt.h`):
```cpp
class ESolver_KS_PW_DFPT {
    // SCF loop method
    void dfpt_scf_loop(int iq, int ipert);

    // Individual steps
    void solve_sternheimer();           // → dpsi (from DFPT-103)
    void compute_drho();                // → drho from dpsi
    void compute_dvscf();               // → dvscf from drho (Hartree + XC)
    void mix_dvscf();                   // → mixed dvscf (Broyden)
    bool check_convergence();           // dr2 < threshold?

    // Data members
    std::vector<std::vector<std::vector<std::complex<double>>>> drho_;   // [iq][ipert][ir]
    std::vector<std::vector<std::vector<std::complex<double>>>> dvscf_;  // [iq][ipert][ir]
    double dfpt_conv_thr_;              // convergence threshold (default 1e-8)
    int dfpt_max_iter_;                 // max iterations (default 100)
    std::string dfpt_mixing_;           // "broyden" or "plain"
    double dfpt_mixing_beta_;           // mixing parameter (default 0.7)
};
```

**Charge mixing infrastructure** (`/root/abacus-dfpt/abacus-develop/source/source_base/module_mixing/`):
```cpp
// Broyden mixing (reusable for DFPT)
class Broyden_Mixing {
public:
    void mix(double* vout, double* vin, int ndim, double& dr2);
    void set_mixing_beta(double beta);
    void set_mixing_ndim(int ndim);  // history size
};

// Plain mixing
class Plain_Mixing {
public:
    void mix(double* vout, double* vin, int ndim, double beta, double& dr2);
};
```

**Hartree potential** (`/root/abacus-dfpt/abacus-develop/source/source_estate/module_pot/H_Hartree_pw.h`):
```cpp
class H_Hartree_pw {
public:
    // V_H(G) = 4π·e² · ρ(G) / |G|²
    static void v_hartree(const ModulePW::PW_Basis* rho_basis,
                          const int nspin,
                          const std::complex<double>* rho_g,
                          double& ehart,
                          std::complex<double>* vh_g);
};
```

**XC potential** (`/root/abacus-dfpt/abacus-develop/source/source_estate/module_pot/pot_xc.h`):
```cpp
class Pot_XC {
    // For DFPT: need f_xc = d²E_xc/dρ²
    // Existing: v_xc = dE_xc/dρ (first derivative)
    // Need to add: f_xc computation for response
};
```

### dvqpsi_cpp Reference

**DFPTKernel** (`/root/q-e/PHonon/dvqpsi_cpp/include/dfpt_kernel.hpp`):
```cpp
class DFPTKernel {
public:
    struct Result {
        ComplexVec dpsi;        // converged wavefunction response
        ComplexVec drho;        // converged charge density response
        ComplexVec dvscf;       // converged SCF potential response
        int iterations;
        double final_dr2;
        bool converged;
    };

    Result solve(const WaveFunction& wfc_k,
                 const WaveFunction& wfc_kq,
                 const ComplexVec& dvpsi_bare,
                 double conv_thr, int max_iter);

private:
    SternheimerSolver sternheimer_;
    PotentialMixer mixer_;
    XCFunctional xc_;
    // Hartree: ΔV_H(G) = 4π·e²·Δρ(G)/|q+G|²
    void compute_hartree_response(const ComplexVec& drho_g, ComplexVec& dvh_g);
    // XC: ΔV_xc(r) = f_xc(r)·Δρ(r)
    void compute_xc_response(const ComplexVec& drho_r, ComplexVec& dvxc_r);
};
```

**XCFunctional** (`/root/q-e/PHonon/dvqpsi_cpp/include/xc_functional.hpp`):
```cpp
class XCFunctional {
public:
    // LDA Perdew-Zunger: f_xc = d²ε_xc/dρ²
    double compute_fxc(double rho) const;

    // Apply: ΔV_xc(r) = f_xc(ρ(r)) · Δρ(r)
    void apply_fxc(const RealVec& rho, const ComplexVec& drho,
                   ComplexVec& dvxc, int nrxx);
};
```

**PotentialMixer** (`/root/q-e/PHonon/dvqpsi_cpp/include/potential_mixer.hpp`):
```cpp
class PotentialMixer {
public:
    enum class Method { SIMPLE, BROYDEN };

    // Simple: v_new = (1-α)·v_old + α·v_out
    // Broyden: modified Broyden with history
    double mix(ComplexVec& v_in, const ComplexVec& v_out, int iter);

    double get_dr2() const;  // ||v_out - v_in||²
};
```

## Implementation Guide

### DFPT SCF Loop Algorithm

```
dfpt_scf_loop(iq, ipert):
    Initialize: dvscf = 0, dpsi = 0, dr2 = 1.0

    FOR iter = 1 TO dfpt_max_iter:
        // 1. Adaptive threshold for Sternheimer
        sternheimer_thresh = min(0.1 * dr2, dfpt_cg_thr)

        // 2. Solve Sternheimer for all k-points
        FOR ik = 1 TO nks:
            // Prepare RHS: dvpsi = dV_bare·ψ + dV_SCF·ψ
            compute_rhs(dvpsi_bare[ik], dvscf, psi[ik], rhs)
            // Solve: (H-ε+Q)·Δψ = -P_c^+·rhs
            solve_sternheimer(rhs, dpsi[ik], sternheimer_thresh)

        // 3. Compute charge density response
        drho = 0
        FOR ik = 1 TO nks:
            // Δρ(r) += w_k · Σ_n [ψ*(k+q,r)·Δψ(k,r) + c.c.]
            accumulate_drho(drho, psi_kq[ik], dpsi[ik], wk[ik])

        // 4. Compute response potential
        // Hartree: ΔV_H(G) = 4πe²·Δρ(G)/|q+G|²
        compute_hartree_response(drho, dvscf_out)
        // XC: ΔV_xc(r) = f_xc(ρ₀(r))·Δρ(r)
        compute_xc_response(drho, rho0, dvscf_out)

        // 5. Mix potentials
        dr2 = mix(dvscf, dvscf_out, iter)

        // 6. Check convergence
        IF dr2 < dfpt_conv_thr:
            RETURN converged

    RETURN not_converged
```

### Key Equations

**Charge density response** (accumulated over k-points):
```
Δρ(r) = Σ_k w_k Σ_{n∈occ} [ψ*_n(k+q, r) · Δψ_n(k, r) + Δψ*_n(k, r) · ψ_n(k+q, r)]
```

**Hartree response potential** (reciprocal space):
```
ΔV_H(G) = 4π·e² · Δρ(G) / |q+G|²     for |q+G| ≠ 0
ΔV_H(G=0) = 0                           for q ≠ 0 (neutrality)
```
Note: `e² = 2.0` in Rydberg units.

**XC response potential** (real space, LDA):
```
ΔV_xc(r) = f_xc(ρ₀(r)) · Δρ(r)
where f_xc = d²(ρ·ε_xc(ρ))/dρ² = 2·dε_xc/dρ + ρ·d²ε_xc/dρ²
```

**Convergence metric**:
```
dr2 = (1/Ω) ∫ |ΔV_SCF^{out}(r) - ΔV_SCF^{in}(r)|² dr
    = (1/N_r) Σ_r |ΔV_SCF^{out}(r) - ΔV_SCF^{in}(r)|²
```

### Critical Implementation Details

1. **Hartree G=0 singularity**: For q≠0, the G=0 term of the Hartree potential is excluded (charge neutrality). For q=0, special treatment is needed:
   ```cpp
   void compute_hartree_response(const std::complex<double>* drho_g,
                                  std::complex<double>* dvh_g,
                                  const ModuleBase::Vector3<double>& xq,
                                  const ModulePW::PW_Basis* pw) {
       const double e2 = 2.0;  // Rydberg units
       const double fpi = 4.0 * M_PI;
       const double tpiba2 = pw->tpiba2;

       for (int ig = 0; ig < pw->npw; ig++) {
           double qpg2 = (xq + pw->getg(ig)).norm2() * tpiba2;
           if (qpg2 > 1e-12) {
               dvh_g[ig] = e2 * fpi * drho_g[ig] / qpg2;
           } else {
               dvh_g[ig] = 0.0;  // G=0 excluded
           }
       }
   }
   ```

2. **XC kernel f_xc**: Must implement second derivative of XC energy. For LDA (Perdew-Zunger):
   ```cpp
   double compute_fxc_lda(double rho) {
       if (rho < 1e-10) return 0.0;
       double rs = std::pow(3.0 / (4.0 * M_PI * rho), 1.0/3.0);
       // Perdew-Zunger parametrization
       // f_xc = d²(ρ·ε_xc)/dρ² = exchange part + correlation part
       double fxc_x = -(2.0/9.0) * (6.0/M_PI) * std::pow(3.0*M_PI*M_PI, 1.0/3.0)
                      * std::pow(rho, -2.0/3.0) / 3.0;
       double fxc_c = /* correlation second derivative */;
       return fxc_x + fxc_c;
   }
   ```

3. **Broyden mixing for complex arrays**: ABACUS's existing `Broyden_Mixing` works with real arrays. For DFPT, the response potential is complex. Options:
   - Treat real and imaginary parts separately (2× ndim)
   - Implement complex Broyden mixing
   - Use dvqpsi_cpp's `PotentialMixer` as reference

4. **K-point summation with MPI**: Charge density response is accumulated over k-points distributed across MPI pools:
   ```cpp
   // Each pool handles a subset of k-points
   // After local accumulation, reduce across pools
   compute_drho_local(drho_local, dpsi, psi_kq, wk, my_kpoints);
   Parallel_Reduce::reduce_pool(drho_local.data(), nrxx);
   ```

5. **Spin handling**: For spin-polarized systems, drho and dvscf have spin index:
   ```cpp
   // drho[ispin][ir], dvscf[ispin][ir]
   // Hartree: uses total Δρ = Δρ_up + Δρ_down
   // XC: uses spin-dependent f_xc kernel
   ```

## TDD Test Plan

### Unit Tests to Write FIRST

```cpp
// test/test_dfpt_scf.cpp

// 1. Hartree response potential — analytic test
TEST(DFPTSCF, HartreeResponseAnalytic) {
    // For a known Δρ(G) = δ_{G,G0}, verify ΔV_H(G0) = 4πe²/|q+G0|²
    const int ngm = 100;
    auto pw = create_test_pw_basis(32, 32, 32);
    auto xq = ModuleBase::Vector3<double>(0.5, 0.0, 0.0);

    std::vector<std::complex<double>> drho_g(ngm, 0.0);
    drho_g[5] = 1.0;  // single G-vector

    std::vector<std::complex<double>> dvh_g(ngm);
    compute_hartree_response(drho_g.data(), dvh_g.data(), xq, pw.get());

    double qpg2 = (xq + pw->getg(5)).norm2() * pw->tpiba2;
    std::complex<double> expected = 2.0 * 4.0 * M_PI / qpg2;  // e2=2 in Ry
    EXPECT_NEAR(std::abs(dvh_g[5] - expected), 0.0, 1e-14);
    // G=0 should be zero
    EXPECT_NEAR(std::abs(dvh_g[0]), 0.0, 1e-14);
}

// 2. XC kernel f_xc — comparison with numerical derivative
TEST(DFPTSCF, XCKernelNumerical) {
    // f_xc = d²(ρ·ε_xc)/dρ² ≈ [v_xc(ρ+δ) - 2·v_xc(ρ) + v_xc(ρ-δ)] / δ²
    double rho = 0.01;  // typical valence density
    double delta = 1e-5;

    double fxc_analytic = compute_fxc_lda(rho);
    double vxc_plus = compute_vxc_lda(rho + delta);
    double vxc_0 = compute_vxc_lda(rho);
    double vxc_minus = compute_vxc_lda(rho - delta);
    double fxc_numerical = (vxc_plus - 2*vxc_0 + vxc_minus) / (delta * delta);

    EXPECT_NEAR(fxc_analytic, fxc_numerical, 1e-4);  // FD has O(δ²) error
}

// 3. Charge density response — sum rule
TEST(DFPTSCF, ChargeDensityResponseSumRule) {
    // ∫ Δρ(r) dr = 0 (charge conservation for phonon perturbation)
    auto system = create_test_dfpt_system();
    auto dpsi = solve_sternheimer(system);
    auto drho = compute_drho(system, dpsi);

    // Sum in real space (= G=0 component)
    std::complex<double> total = 0.0;
    for (int ir = 0; ir < system.nrxx; ir++) {
        total += drho[ir];
    }
    total /= system.nrxx;
    EXPECT_NEAR(std::abs(total), 0.0, 1e-10);
}

// 4. Broyden mixing convergence
TEST(DFPTSCF, BroydenMixingConvergence) {
    // Test that Broyden mixing converges for a simple fixed-point problem
    const int ndim = 100;
    auto v_in = create_random_complex_vector(ndim);
    double beta = 0.7;

    for (int iter = 0; iter < 50; iter++) {
        auto v_out = apply_simple_operator(v_in);  // known fixed point
        double dr2;
        broyden_mix(v_in, v_out, ndim, beta, iter, dr2);
        if (dr2 < 1e-12) break;
    }
    // Should converge
    auto v_out = apply_simple_operator(v_in);
    double final_dr2 = compute_dr2(v_in, v_out, ndim);
    EXPECT_LT(final_dr2, 1e-10);
}

// 5. Full SCF loop convergence for simple system
TEST(DFPTSCF, FullSCFConvergence) {
    auto system = create_si_dfpt_system();
    auto result = run_dfpt_scf(system, /*conv_thr=*/1e-10, /*max_iter=*/100);

    EXPECT_TRUE(result.converged);
    EXPECT_LT(result.final_dr2, 1e-10);
    EXPECT_LT(result.iterations, 50);  // should converge in reasonable iterations
}

// 6. SCF convergence rate — iteration count vs QE
TEST(DFPTSCF, ConvergenceRateVsQE) {
    auto system = create_si_dfpt_system();
    auto result = run_dfpt_scf(system, /*conv_thr=*/1e-10);

    // QE typically converges Si DFPT in 8-15 iterations
    // ABACUS should be within ±2 iterations
    int qe_iterations = 12;  // reference from QE run
    EXPECT_LE(std::abs(result.iterations - qe_iterations), 2);
}
```

### Integration Tests

```cpp
// Full DFPT SCF with QE comparison
TEST(DFPTSCF_Integration, SiPhononGamma) {
    // Si phonon at Gamma point — compare drho with QE
    auto system = load_si_ground_state();
    auto result = run_dfpt_scf(system, {0,0,0}, /*ipert=*/0);

    auto qe_drho = load_qe_reference("test_data/si_drho_gamma_qe.dat");
    compare_complex_arrays(result.drho, qe_drho, 1e-8);
}
```

## Acceptance Criteria

- [ ] DFPT SCF loop fully implemented with Hartree + XC response
- [ ] Hartree response correct (analytic test passes)
- [ ] XC kernel f_xc matches numerical second derivative (< 1e-4)
- [ ] Charge conservation: ∫Δρ dr = 0 (< 1e-10)
- [ ] Broyden mixing converges for test problem
- [ ] Supports both linear and Broyden mixing schemes
- [ ] DFPT SCF converges to dr2 < 1e-10 for Si system
- [ ] Iteration count deviation from QE ≤ 2 iterations
- [ ] All unit and integration tests pass
- [ ] Code review passes 6-agent DFPT review
