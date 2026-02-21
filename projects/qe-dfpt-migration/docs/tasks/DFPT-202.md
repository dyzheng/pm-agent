# DFPT-202: Implement Dynamical Matrix Calculation

## Objective

Implement the phonon dynamical matrix calculation from converged DFPT charge density responses. This includes the bare dynamical matrix (ionic + electronic), symmetrization, acoustic sum rule enforcement, LO-TO splitting for polar materials, and eigenvalue decomposition to extract phonon frequencies and eigenvectors.

## Reference Code

### QE Source (Fortran)

**Bare dynamical matrix** (`/root/q-e/PHonon/PH/dynmat0.f90`):
```fortran
SUBROUTINE dynmat0_new()
  ! Computes part of dynamical matrix independent of wavefunction response
  !
  ! D_bare(κα, κ'β; q) = D_us + D_ion + D_nlcc + D_hub
  !
  ! 1. CALL dynmat_us()   — electronic contribution ⟨ψ|V''-eS''|ψ⟩
  ! 2. CALL d2ionq()      — ionic (Ewald) contribution
  ! 3. CALL dynmatcc()    — non-linear core correction
  ! 4. IF (lda_plus_u) CALL dynmat_hub_bare()
  ! 5. CALL symdyn_munu_new()  — symmetrize
END SUBROUTINE
```

**Ionic contribution** (`/root/q-e/PHonon/PH/d2ionq.f90`):
```fortran
SUBROUTINE d2ionq(nat, ntyp, ityp, zv, tau, alat, omega, q, at, bg, g, &
                   gg, ngm, gcutm, nmodes, u, dyn)
  ! Ewald contribution to dynamical matrix:
  !   D_ion(κα, κ'β; q) = D_real + D_recip
  !
  ! Real-space sum (short-range):
  !   D_real = Σ_R Z_κ·Z_κ' · d²erfc(η|τ_κ-τ_κ'+R|)/dτ_κα·dτ_κ'β × e^{iq·R}
  !
  ! Reciprocal-space sum (long-range):
  !   D_recip = (4πe²/Ω) Σ_G Z_κ·Z_κ' · (q+G)_α(q+G)_β/|q+G|²
  !             × e^{-|q+G|²/4η²} × e^{i(q+G)·(τ_κ-τ_κ')}
  !
  ! η = Ewald parameter (optimized for convergence)
END SUBROUTINE
```

**Electronic contribution** (`/root/q-e/PHonon/PH/dynmat_us.f90`):
```fortran
SUBROUTINE dynmat_us()
  ! Electronic contribution from second derivative of potential:
  !   D_us(κα, κ'β) = Σ_{k,n} f_n ⟨ψ_n(k)|d²V/dτ_κα·dτ_κ'β|ψ_n(k)⟩
  !                  - Σ_{k,n} f_n ε_n ⟨ψ_n(k)|d²S/dτ_κα·dτ_κ'β|ψ_n(k)⟩
  !
  ! For USPP: includes second derivatives of beta projectors
END SUBROUTINE
```

**Full dynamical matrix assembly** (`/root/q-e/PHonon/PH/dynmatrix.f90`):
```fortran
SUBROUTINE dynmatrix_new(iq_)
  ! Assembles full dynamical matrix from bare + SCF contributions:
  !   D(κα, κ'β; q) = D_bare + D_SCF
  !
  ! where D_SCF comes from converged DFPT:
  !   D_SCF(κα, κ'β) = Σ_k w_k Σ_n f_n ⟨Δψ_n^{κα}(k)|ΔV^{κ'β}|ψ_n(k)⟩
  !                   + Σ_k w_k Σ_n f_n ⟨ψ_n(k+q)|ΔV^{κ'β}|Δψ_n^{κα}(k)⟩
  !
  ! Steps:
  !   1. Set uncomputed elements to zero
  !   2. CALL symdyn_munu_new()  — symmetrize w.r.t. small group of q
  !   3. IF (asr) CALL set_asr_c()  — acoustic sum rule
  !   4. CALL cdiagh()  — diagonalize → ω², eigenvectors
  !   5. Generate star of q
  !   6. Write dynamical matrix to file
END SUBROUTINE
```

**LO-TO splitting** (`/root/q-e/PHonon/PH/rigid.f90`):
```fortran
SUBROUTINE rgd_blk(nr1, nr2, nr3, nat, dyn, q, tau, epsil, zeu, ...)
  ! Non-analytic correction for polar materials at q→0:
  !   D_NA(κα, κ'β) = (4πe²/Ω) × (q·Z*_κ)_α × (Z*_κ'·q)_β / (q·ε∞·q)
  !
  ! This splits LO and TO modes at Gamma
  ! Applied AFTER Fourier interpolation (in matdyn/q2r)
END SUBROUTINE
```

**Acoustic sum rule** (`/root/q-e/PHonon/PH/set_asr.f90`):
```fortran
SUBROUTINE set_asr_c(asr, axis, nat, dyn)
  ! Enforces acoustic sum rule on dynamical matrix:
  !   Σ_κ' D(κα, κ'β; q=0) = 0  for all κ, α, β
  !
  ! Methods:
  !   'simple' — subtract average diagonal block
  !   'crystal' — project out acoustic modes
  !   'one-dim' — for 1D systems
  !   'zero-dim' — for molecules
END SUBROUTINE
```

**Symmetrization** (`/root/q-e/PHonon/PH/symdynph_gq.f90`):
```fortran
SUBROUTINE symdynph_gq_new(xq, phi, s, invs, rtau, irt, nsymq, nat, ...)
  ! Symmetrizes dynamical matrix w.r.t. small group of q:
  !   D_sym = (1/N_sym) Σ_S S · D · S†
  !
  ! Also handles q ↔ -q+G symmetry (time reversal)
END SUBROUTINE
```

### ABACUS Target — Existing Infrastructure

**Symmetry module** (`/root/abacus-dfpt/abacus-develop/source/source_cell/module_symmetry/symmetry.h`):
```cpp
class Symmetry {
    int nrotk;                          // number of symmetry operations
    ModuleBase::Matrix3 gmatrix[48];    // rotation matrices
    ModuleBase::Vector3<double> gtrans[48]; // fractional translations
    int *invs;                          // inverse symmetry index
    // Methods for symmetry operations on k-points, charge density, etc.
};
```

**Matrix diagonalization** (`/root/abacus-dfpt/abacus-develop/source/source_base/`):
```cpp
// LAPACK wrapper for complex Hermitian eigenvalue problem
void LapackConnector::zheev(const char jobz, const char uplo, const int n,
                            std::complex<double>* a, const int lda,
                            double* w, /* eigenvalues */
                            std::complex<double>* work, const int lwork,
                            double* rwork, int* info);
```

### dvqpsi_cpp Reference

dvqpsi_cpp does NOT implement dynamical matrix calculation — this is new code. However, the `elphon.hpp` module provides `PhononData` structure:
```cpp
struct PhononData {
    RealVec omega;              // phonon frequencies (3*nat)
    ComplexVec eigenvectors;    // eigenvectors (3*nat × 3*nat)
    int nq, nmodes, nat;
};
```

## Implementation Guide

### Architecture

```
DynamicalMatrix class
├── compute_bare()
│   ├── compute_ionic()         — Ewald sum (real + reciprocal space)
│   ├── compute_electronic()    — ⟨ψ|V''-eS''|ψ⟩
│   └── compute_nlcc()          — core charge correction
├── compute_scf()
│   └── accumulate from converged DFPT: ⟨Δψ|ΔV|ψ⟩ + ⟨ψ|ΔV|Δψ⟩
├── symmetrize()
│   └── Apply small group of q symmetry
├── apply_asr()
│   └── Acoustic sum rule enforcement
├── add_loto()
│   └── Non-analytic LO-TO correction (polar materials)
└── diagonalize()
    └── LAPACK zheev → frequencies ω, eigenvectors
```

### Key Equations

**Dynamical matrix** (mass-weighted force constant):
```
D(κα, κ'β; q) = (1/√(M_κ·M_κ')) × C(κα, κ'β; q)
```

**Force constant from DFPT**:
```
C(κα, κ'β; q) = C_bare(κα, κ'β; q) + C_SCF(κα, κ'β; q)

C_SCF = Σ_k w_k Σ_n f_n [⟨Δψ_n^{κα}|ΔV^{κ'β}_bare + ΔV^{κ'β}_SCF|ψ_n⟩ + c.c.]
```

**Ewald ionic contribution** (reciprocal space part):
```
C_ion^{recip}(κα, κ'β; q) = (4πe²/Ω) Σ_{G≠0} Z_κ·Z_κ' ×
    (q+G)_α·(q+G)_β / |q+G|² × exp(-|q+G|²/4η²) × exp(i(q+G)·(τ_κ-τ_κ'))
```

**Phonon frequencies**:
```
D(q) · e_ν(q) = ω²_ν(q) · e_ν(q)
ω_ν = √(ω²_ν)  [imaginary if ω² < 0 → unstable mode]
```

**LO-TO splitting** (non-analytic term for q→0 in polar materials):
```
D_NA(κα, κ'β; q̂) = (4πe²/Ω) × Σ_γ q̂_γ·Z*_{κ,γα} × Σ_δ Z*_{κ',δβ}·q̂_δ
                     / (Σ_{γδ} q̂_γ·ε∞_{γδ}·q̂_δ) / √(M_κ·M_κ')
```

### Critical Implementation Details

1. **Ewald parameter η**: Must be optimized for convergence of both real and reciprocal sums. QE uses:
   ```cpp
   double eta = std::sqrt(M_PI) * std::pow(nat, 1.0/6.0) / (alat * std::sqrt(omega));
   ```

2. **Dynamical matrix from DFPT**: The SCF contribution is accumulated during the DFPT SCF loop. After convergence for all perturbations at a q-point:
   ```cpp
   // For perturbation (κ,α) and (κ',β):
   // D_SCF(κα, κ'β) = ∫ Δρ^{κα}(r) · ΔV^{κ'β}_bare(r) dr
   //                 + ∫ Δρ^{κα}(r) · ΔV^{κ'β}_SCF(r) dr
   for (int ir = 0; ir < nrxx; ir++) {
       dyn_scf(ipert1, ipert2) += drho[ipert1][ir] * std::conj(dvscf_bare[ipert2][ir]);
   }
   // MPI reduce over real-space grid distribution
   ```

3. **Symmetrization**: The dynamical matrix must respect the small group of q:
   ```cpp
   // D_sym(κα, κ'β) = (1/N_sym) Σ_S R_S(α,γ) · D(S·κ,γ, S·κ',δ) · R_S(β,δ)
   // where R_S is the rotation matrix and S·κ maps atom κ under symmetry S
   ```

4. **Acoustic sum rule**: For q=0, three eigenvalues must be exactly zero (acoustic modes). Enforce by:
   ```cpp
   // Simple ASR: D(κα, κβ; q=0) -= (1/nat) Σ_κ' D(κα, κ'β; q=0)
   for (int ka = 0; ka < 3*nat; ka++) {
       std::complex<double> sum = 0;
       for (int kb = 0; kb < 3*nat; kb += 3) {
           // sum over κ' for fixed β
       }
       dyn(ka, ka) -= sum;
   }
   ```

5. **Mass normalization**: Convert force constants to dynamical matrix:
   ```cpp
   for (int i = 0; i < 3*nat; i++) {
       int iat_i = i / 3;
       for (int j = 0; j < 3*nat; j++) {
           int iat_j = j / 3;
           dyn(i,j) /= std::sqrt(mass[ityp[iat_i]] * mass[ityp[iat_j]]);
       }
   }
   // mass in atomic mass units (amu), convert to Ry units:
   // M_ry = M_amu × AMU_RY where AMU_RY = 1822.888... (me/amu in Ry system)
   ```

## TDD Test Plan

### Unit Tests to Write FIRST

```cpp
// test/test_dynmat.cpp

// 1. Ewald sum — known result for NaCl
TEST(DynMat, EwaldSumNaCl) {
    // NaCl: 2 atoms, charges +1, -1
    // At Gamma: acoustic modes = 0, optical modes known analytically
    auto system = create_nacl_system();
    auto dyn_ion = compute_ionic_dynmat(system, {0,0,0});

    // Verify: diagonal blocks sum to zero (Newton's third law)
    for (int alpha = 0; alpha < 3; alpha++) {
        for (int beta = 0; beta < 3; beta++) {
            auto sum = dyn_ion(alpha, beta) + dyn_ion(alpha, 3+beta)
                     + dyn_ion(3+alpha, beta) + dyn_ion(3+alpha, 3+beta);
            EXPECT_NEAR(std::abs(sum), 0.0, 1e-10);
        }
    }
}

// 2. Acoustic sum rule enforcement
TEST(DynMat, AcousticSumRule) {
    auto dyn = create_random_dynmat(2);  // 2 atoms
    apply_asr(dyn, 2, "simple");

    // After ASR: Σ_κ' D(κα, κ'β) = 0
    for (int ka = 0; ka < 3; ka++) {
        for (int beta = 0; beta < 3; beta++) {
            std::complex<double> sum = 0;
            for (int kp = 0; kp < 2; kp++) {
                sum += dyn(ka, kp*3 + beta);
            }
            EXPECT_NEAR(std::abs(sum), 0.0, 1e-12);
        }
    }
}

// 3. Hermiticity of dynamical matrix
TEST(DynMat, Hermiticity) {
    auto system = create_si_system();
    auto dyn = compute_full_dynmat(system, {0.5, 0, 0});

    for (int i = 0; i < 6; i++) {
        for (int j = 0; j < 6; j++) {
            EXPECT_NEAR(std::abs(dyn(i,j) - std::conj(dyn(j,i))), 0.0, 1e-12);
        }
    }
}

// 4. Diagonalization — eigenvalues are real
TEST(DynMat, EigenvaluesReal) {
    auto system = create_si_system();
    auto dyn = compute_full_dynmat(system, {0, 0, 0});
    apply_asr(dyn, 2, "simple");

    auto [omega2, eigvec] = diagonalize_dynmat(dyn, 2);

    // All ω² should be real (Hermitian matrix)
    // 3 acoustic modes: ω² ≈ 0
    // 3 optical modes: ω² > 0
    int n_acoustic = 0;
    for (int i = 0; i < 6; i++) {
        if (std::abs(omega2[i]) < 1e-6) n_acoustic++;
    }
    EXPECT_EQ(n_acoustic, 3);
}

// 5. Phonon frequencies vs QE reference
TEST(DynMat, SiPhononFrequenciesVsQE) {
    auto system = load_si_dfpt_converged();
    auto dyn = compute_full_dynmat(system, {0, 0, 0});
    apply_asr(dyn, 2, "crystal");

    auto [omega2, eigvec] = diagonalize_dynmat(dyn, 2);
    auto freq_cm = convert_to_cm_inv(omega2);

    // Si optical phonon at Gamma: ~520 cm⁻¹ (QE reference)
    double qe_optical = 520.0;  // cm⁻¹
    double max_optical = *std::max_element(freq_cm.begin(), freq_cm.end());
    EXPECT_NEAR(max_optical, qe_optical, 0.1);  // < 0.1 cm⁻¹ error
}

// 6. LO-TO splitting for polar material
TEST(DynMat, LOTOSplittingGaAs) {
    // GaAs: polar material with known LO-TO splitting
    auto system = create_gaas_system();
    auto epsilon = load_dielectric_tensor();  // ε∞
    auto zstar = load_born_charges();         // Z*

    auto dyn_no_loto = compute_full_dynmat(system, {0,0,0});
    auto dyn_with_loto = dyn_no_loto;
    add_loto_correction(dyn_with_loto, {0,0,1}, epsilon, zstar, system);

    auto [omega2_no, _1] = diagonalize_dynmat(dyn_no_loto, 2);
    auto [omega2_lo, _2] = diagonalize_dynmat(dyn_with_loto, 2);

    // LO frequency should be higher than TO
    double to_freq = std::sqrt(std::abs(omega2_no[5]));
    double lo_freq = std::sqrt(std::abs(omega2_lo[5]));
    EXPECT_GT(lo_freq, to_freq);
}

// 7. Symmetrization preserves eigenvalues
TEST(DynMat, SymmetrizationPreservesEigenvalues) {
    auto system = create_si_system();
    auto dyn = compute_full_dynmat(system, {0.5, 0, 0});

    auto [omega2_before, _1] = diagonalize_dynmat(dyn, 2);
    symmetrize_dynmat(dyn, system.symmetry, {0.5, 0, 0});
    auto [omega2_after, _2] = diagonalize_dynmat(dyn, 2);

    // Eigenvalues should be preserved (or improved)
    std::sort(omega2_before.begin(), omega2_before.end());
    std::sort(omega2_after.begin(), omega2_after.end());
    for (int i = 0; i < 6; i++) {
        EXPECT_NEAR(omega2_before[i], omega2_after[i], 1e-8);
    }
}
```

### Milestone 3 Smoke Test

```cpp
TEST(M3SmokeTest, SiFullDFPTPhonon) {
    // Complete: ground-state → DFPT SCF → dynamical matrix → frequencies
    auto gs = run_ground_state_si();
    auto dfpt = run_dfpt_scf_all_perturbations(gs, {0,0,0});
    auto dyn = compute_full_dynmat(gs, dfpt, {0,0,0});
    apply_asr(dyn, 2, "crystal");
    auto [omega2, eigvec] = diagonalize_dynmat(dyn, 2);
    auto freq_cm = convert_to_cm_inv(omega2);

    // Si Gamma phonon: 3 acoustic (0) + 3 optical (~520 cm⁻¹)
    EXPECT_NEAR(freq_cm[0], 0.0, 0.1);
    EXPECT_NEAR(freq_cm[1], 0.0, 0.1);
    EXPECT_NEAR(freq_cm[2], 0.0, 0.1);
    EXPECT_NEAR(freq_cm[3], 520.0, 0.1);  // deviation from QE < 0.1 cm⁻¹
    EXPECT_NEAR(freq_cm[4], 520.0, 0.1);
    EXPECT_NEAR(freq_cm[5], 520.0, 0.1);
}
```

## Acceptance Criteria

- [ ] Dynamical matrix calculation correct (ionic + electronic + SCF contributions)
- [ ] Ewald sum converges and satisfies Newton's third law
- [ ] Acoustic sum rule enforced (3 zero modes at Gamma)
- [ ] Hermiticity maintained (D(i,j) = D*(j,i))
- [ ] Phonon frequencies match QE reference (error < 0.1 cm⁻¹ for Si)
- [ ] LO-TO splitting implemented for polar materials
- [ ] Symmetrization preserves eigenvalues
- [ ] M3 Smoke Test passes: Si complete DFPT → phonon frequencies
- [ ] All unit tests pass (≥7 test cases)
- [ ] Code review passes 6-agent DFPT review
