# DFPT-203: Implement Electron-Phonon Coupling Calculation

## Objective

Implement electron-phonon coupling (EPC) matrix element calculation and derived quantities: phonon linewidths γ(q,ν), Eliashberg spectral function α²F(ω), coupling constant λ, and superconducting Tc estimation. This enables prediction of phonon-mediated superconductivity and phonon-limited transport properties.

## Reference Code

### QE Source (Fortran)

**Main EPC driver** (`/root/q-e/PHonon/PH/elphon.f90`):
```fortran
SUBROUTINE elphon()
  ! Calculates electron-phonon matrix elements from converged DFPT potentials
  !
  ! DO irr = 1, nirr
  !   DO ipert = 1, npert(irr)
  !     1. READ dvscfin from file (converged response potential)
  !     2. IF (doublegrid) CALL fft_interpolate()
  !     3. CALL newdq()  — compute int3 for USPP
  !     4. CALL elphel() — calculate ⟨ψ_{k+q,m}|ΔV_ν|ψ_{k,n}⟩
  !   ENDDO
  ! ENDDO
END SUBROUTINE
```

**Matrix element calculation** (`/root/q-e/PHonon/PH/elphel.f90`):
```fortran
SUBROUTINE elphel(npe, imode0, dvscfins)
  ! Computes g_{mn}(k,q,ν) = ⟨ψ_{m}(k+q)|ΔV_{SCF}^{ν}|ψ_{n}(k)⟩
  !
  ! For each k-point:
  !   1. Read ψ(k) and ψ(k+q) from files
  !   2. For each perturbation mode ν:
  !      a. Apply ΔV_SCF to ψ(k): dvpsi = ΔV_SCF · ψ_n(k)
  !      b. Compute overlap: g(m,n) = ⟨ψ_m(k+q)|dvpsi_n⟩
  !      c. Add USPP contribution if needed
  !   3. Store g matrix for this k-point
  !
  ! Output: el_ph_mat(nbnd, nbnd, nks, npe) — EPC matrix elements
END SUBROUTINE
```

**Phonon linewidth** (`/root/q-e/PHonon/PH/elph_tetra_mod.f90`):
```fortran
! γ(q,ν) = 2π·ω(q,ν) · N(ε_F) · Σ_{k,mn} |g_{mn}(k,q,ν)|²
!          × δ(ε_{m,k+q} - ε_F) × δ(ε_{n,k} - ε_F)
!
! Using tetrahedron method or Gaussian smearing for delta functions
```

**Eliashberg function** (`/root/q-e/PHonon/PH/alpha2f.f90`):
```fortran
SUBROUTINE alpha2f(lambda, alpha_2_f, omega_grid, nw)
  ! α²F(ω) = (1/N(ε_F)) Σ_{q,ν} γ(q,ν)/(2π·ω(q,ν)) × δ(ω - ω(q,ν))
  !
  ! λ = 2 ∫ α²F(ω)/ω dω
  ! ω_log = exp[(2/λ) ∫ α²F(ω)/ω × ln(ω) dω]
  ! Tc (McMillan) = (ω_log/1.2) × exp[-1.04(1+λ)/(λ-μ*(1+0.62λ))]
END SUBROUTINE
```

### ABACUS Target — Existing Infrastructure

**Wavefunction access**:
```cpp
// Ground-state wavefunctions at k and k+q
psi::Psi<std::complex<double>>& psi_k;   // from ESolver_KS_PW
psi::Psi<std::complex<double>>& psi_kq;  // recalculated at k+q

// Eigenvalues
double* eigenvalues_k;   // ε_n(k)
double* eigenvalues_kq;  // ε_m(k+q)
```

**K-point infrastructure**:
```cpp
K_Vectors kv;           // k-point grid
// For EPC: need dense k-grid for Fermi surface sampling
// May need separate k-grid from DFPT q-grid
```

### dvqpsi_cpp Reference

**ElPhon class** (`/root/q-e/PHonon/dvqpsi_cpp/include/elphon.hpp`):
```cpp
class ElPhon {
public:
    // Compute g_{mn}(k,q,ν) for all bands at one k-point
    void compute_matrix_elements(
        const WaveFunction& wfc_k,
        const WaveFunction& wfc_kq,
        const ComplexVec& dvscf,        // converged response potential
        const PhononData& phonon,        // frequencies + eigenvectors
        const FFTGrid& grid,
        EPCMatrixElement& g_matrix);

    // Compute phonon linewidth γ(q,ν)
    void compute_linewidth(
        const std::vector<EPCMatrixElement>& g_all_k,
        const std::vector<WaveFunction>& wfc_all_k,
        const PhononData& phonon,
        double ef,                       // Fermi energy
        double sigma,                    // smearing width
        RealVec& gamma);

    // Compute Eliashberg function and λ
    EPCResults compute_eliashberg(
        const std::vector<RealVec>& gamma_all_q,
        const std::vector<PhononData>& phonon_all_q,
        const std::vector<double>& wq,   // q-point weights
        double dos_ef,                    // DOS at Fermi level
        int nw,                           // frequency grid points
        double wmax);                     // max frequency
};
```

**Data structures**:
```cpp
struct EPCMatrixElement {
    ComplexVec g_matrix;    // g_{mn}(k,q,ν): (nbnd × nbnd × nmodes)
    int nk, nq, nbnd, nmodes;
};

struct EPCResults {
    RealVec gamma;          // linewidths γ(q,ν)
    RealVec alpha2F;        // Eliashberg function
    RealVec omega_grid;     // frequency grid
    double lambda;          // EPC constant
    double omega_log;       // logarithmic average frequency
    double Tc_McMillan;     // estimated Tc
};
```

**BZ integration** (`/root/q-e/PHonon/dvqpsi_cpp/include/bz_integration.hpp`):
```cpp
class BZIntegration {
public:
    // Generate uniform k-point grid
    static std::vector<KPointData> generate_grid(int nk1, int nk2, int nk3);

    // Compute Fermi energy
    static double compute_fermi_energy(
        const std::vector<RealVec>& eigenvalues,
        const std::vector<double>& wk,
        int nelec, double sigma);

    // DOS at Fermi level
    static double compute_dos_ef(
        const std::vector<RealVec>& eigenvalues,
        const std::vector<double>& wk,
        double ef, double sigma);
};
```

## Implementation Guide

### Architecture

```
ElPhon class
├── compute_g_matrix()
│   ├── For each k-point:
│   │   ├── Apply ΔV_SCF to ψ(k): dvpsi = ΔV_SCF · ψ_n(k)
│   │   ├── Compute overlap: g(m,n,ν) = ⟨ψ_m(k+q)|dvpsi_n⟩
│   │   └── Transform to mode basis: g_ν = Σ_{κα} e_ν(κα) · g_{κα}
│   └── MPI reduce over k-point pools
├── compute_linewidth()
│   ├── γ(q,ν) = 2πω(q,ν) Σ_{k,mn} |g_{mn}|² δ(ε_m-ε_F) δ(ε_n-ε_F)
│   └── Delta function: Gaussian smearing or tetrahedron method
├── compute_eliashberg()
│   ├── α²F(ω) = (1/N_F) Σ_{q,ν} γ(q,ν)/(2πω(q,ν)) δ(ω-ω(q,ν))
│   ├── λ = 2 ∫ α²F(ω)/ω dω
│   ├── ω_log = exp[(2/λ) ∫ (α²F(ω)/ω) ln(ω) dω]
│   └── Tc = (ω_log/1.2) exp[-1.04(1+λ)/(λ-μ*(1+0.62λ))]
└── output_results()
    ├── Write g matrix to file
    ├── Write linewidths
    └── Write α²F and λ
```

### Key Equations

**EPC matrix element** (perturbation basis):
```
g_{mn}^{κα}(k, q) = ⟨ψ_m(k+q) | ΔV_{SCF}^{κα}(q) | ψ_n(k)⟩
```

**EPC matrix element** (mode basis):
```
g_{mn}^{ν}(k, q) = Σ_{κα} e_ν(κα; q) / √(2·M_κ·ω_{ν,q}) × g_{mn}^{κα}(k, q)
```

**Phonon linewidth**:
```
γ(q, ν) = 2π·ω(q,ν) · Σ_{k,mn} |g_{mn}^{ν}(k,q)|² × δ(ε_{m,k+q} - ε_F) × δ(ε_{n,k} - ε_F) × w_k
```

**Eliashberg spectral function**:
```
α²F(ω) = (1/2π·N(ε_F)) × Σ_{q,ν} w_q × γ(q,ν) / ω(q,ν) × δ(ω - ω(q,ν))
```

**Coupling constant**:
```
λ = 2 ∫₀^∞ α²F(ω)/ω dω = Σ_{q,ν} w_q × γ(q,ν) / (π·N(ε_F)·ω²(q,ν))
```

**McMillan Tc formula**:
```
Tc = (ω_log / 1.2) × exp[-1.04(1+λ) / (λ - μ*(1 + 0.62λ))]
where μ* ≈ 0.1-0.15 (Coulomb pseudopotential)
```

### Critical Implementation Details

1. **Mode transformation**: The DFPT gives g in perturbation basis (κα). Must transform to phonon mode basis using eigenvectors from dynamical matrix diagonalization:
   ```cpp
   // g_mode(m,n,nu) = Σ_{kappa,alpha} e(kappa*3+alpha, nu) / sqrt(2*M*omega)
   //                  × g_pert(m, n, kappa*3+alpha)
   for (int nu = 0; nu < nmodes; nu++) {
       for (int m = 0; m < nbnd; m++) {
           for (int n = 0; n < nbnd; n++) {
               std::complex<double> g_nu = 0;
               for (int ipert = 0; ipert < nmodes; ipert++) {
                   int iat = ipert / 3;
                   double mass_factor = 1.0 / std::sqrt(2.0 * mass[ityp[iat]] * AMU_RY * omega[nu]);
                   g_nu += eigvec(ipert, nu) * mass_factor * g_pert(m, n, ipert);
               }
               g_mode(m, n, nu) = g_nu;
           }
       }
   }
   ```

2. **Delta function approximation**: For metallic systems, the delta functions at the Fermi surface are approximated:
   ```cpp
   // Gaussian smearing:
   double delta_gauss(double x, double sigma) {
       return std::exp(-x*x / (2*sigma*sigma)) / (sigma * std::sqrt(2*M_PI));
   }

   // Methfessel-Paxton (better for metals):
   // Or tetrahedron method (most accurate, requires k-mesh topology)
   ```

3. **Dense k-grid**: EPC requires a much denser k-grid than DFPT. Typical: DFPT uses 4×4×4 q-grid, EPC needs 24×24×24 k-grid. The response potential ΔV_SCF is Fourier-interpolated to the dense grid.

4. **Fermi surface sampling**: Only states near ε_F contribute. For efficiency:
   ```cpp
   // Skip bands far from Fermi level
   if (std::abs(eigenvalues_k[n] - ef) > 5*sigma &&
       std::abs(eigenvalues_kq[m] - ef) > 5*sigma) continue;
   ```

5. **Units**: EPC matrix elements in Ry, frequencies in Ry (internal). Convert for output:
   ```cpp
   // γ in Ry → meV: γ_meV = γ_Ry × RY_TO_MEV
   // α²F is dimensionless
   // λ is dimensionless
   // Tc in K: Tc_K = Tc_Ry × RY_TO_K
   ```

## TDD Test Plan

### Unit Tests to Write FIRST

```cpp
// test/test_elphon.cpp

// 1. Matrix element symmetry: g(m,n,ν) at q=0 should be Hermitian
TEST(ElPhon, MatrixElementHermiticity) {
    auto system = create_test_metal_system();
    auto g = compute_g_matrix(system, /*iq=*/0);

    // At q=0: g_{mn}^ν = g_{nm}^{ν*}
    for (int nu = 0; nu < system.nmodes; nu++) {
        for (int m = 0; m < system.nbnd; m++) {
            for (int n = 0; n < system.nbnd; n++) {
                EXPECT_NEAR(std::abs(g(m,n,nu) - std::conj(g(n,m,nu))), 0.0, 1e-10);
            }
        }
    }
}

// 2. Acoustic mode coupling vanishes at q=0
TEST(ElPhon, AcousticModeCouplingZero) {
    // g_{mn}^{acoustic}(k, q=0) = 0 (uniform translation doesn't couple)
    auto system = create_test_system();
    auto g = compute_g_matrix_mode_basis(system, /*iq=*/0);

    for (int nu = 0; nu < 3; nu++) {  // 3 acoustic modes
        double max_g = 0;
        for (int m = 0; m < system.nbnd; m++) {
            for (int n = 0; n < system.nbnd; n++) {
                max_g = std::max(max_g, std::abs(g(m, n, nu)));
            }
        }
        EXPECT_LT(max_g, 1e-8);
    }
}

// 3. Linewidth positivity
TEST(ElPhon, LinewidthPositive) {
    auto system = create_al_system();  // Al is a good test metal
    auto gamma = compute_linewidths(system);

    for (int nu = 0; nu < system.nmodes; nu++) {
        EXPECT_GE(gamma[nu], 0.0);
    }
}

// 4. λ sum rule: λ = Σ_{q,ν} λ_{q,ν}
TEST(ElPhon, LambdaSumRule) {
    auto system = create_al_system();
    auto [gamma_all_q, phonon_all_q] = compute_all_linewidths(system);
    auto results = compute_eliashberg(gamma_all_q, phonon_all_q, system);

    // λ from integration of α²F
    double lambda_integral = 2.0 * integrate(results.alpha2F, results.omega_grid,
                                              [](double a2f, double w) { return a2f/w; });
    // λ from sum over q,ν
    double lambda_sum = 0;
    for (int iq = 0; iq < system.nq; iq++) {
        for (int nu = 0; nu < system.nmodes; nu++) {
            double omega = phonon_all_q[iq].omega[nu];
            if (omega > 1e-6) {
                lambda_sum += system.wq[iq] * gamma_all_q[iq][nu]
                            / (M_PI * system.dos_ef * omega * omega);
            }
        }
    }
    EXPECT_NEAR(lambda_integral, lambda_sum, 0.01);
}

// 5. EPC matrix elements vs QE reference
TEST(ElPhon, MatrixElementsVsQE) {
    auto system = load_al_dfpt_converged();
    auto g = compute_g_matrix(system, /*iq=*/0);
    auto g_qe = load_qe_reference("test_data/al_elph_qe.dat");

    // |g| relative error < 1%
    for (int nu = 0; nu < system.nmodes; nu++) {
        for (int m = 0; m < system.nbnd_occ; m++) {
            for (int n = 0; n < system.nbnd_occ; n++) {
                if (std::abs(g_qe(m,n,nu)) > 1e-6) {
                    double rel_err = std::abs(g(m,n,nu) - g_qe(m,n,nu))
                                   / std::abs(g_qe(m,n,nu));
                    EXPECT_LT(rel_err, 0.01);
                }
            }
        }
    }
}

// 6. λ vs QE reference
TEST(ElPhon, LambdaVsQE) {
    auto system = load_al_dfpt_converged();
    auto results = compute_full_epc(system);

    double lambda_qe = 0.44;  // Al reference value
    EXPECT_NEAR(results.lambda, lambda_qe, 0.05 * lambda_qe);  // < 5% error
}

// 7. McMillan Tc formula
TEST(ElPhon, McMillanTcFormula) {
    // Known values: λ=1.0, ω_log=100K, μ*=0.1 → Tc ≈ 5.3K
    double lambda = 1.0;
    double omega_log_K = 100.0;
    double mu_star = 0.1;

    double Tc = mcmillan_tc(lambda, omega_log_K, mu_star);
    EXPECT_NEAR(Tc, 5.3, 0.5);  // approximate
}
```

### Integration Tests

```cpp
// Full EPC workflow for Al
TEST(ElPhon_Integration, AlFullEPC) {
    auto gs = run_ground_state_al();
    auto dfpt = run_dfpt_all_qpoints(gs);
    auto epc = compute_full_epc(gs, dfpt);

    EXPECT_GT(epc.lambda, 0.3);   // Al: λ ≈ 0.44
    EXPECT_LT(epc.lambda, 0.6);
    EXPECT_GT(epc.Tc_McMillan, 0.5);  // Al: Tc ≈ 1.2K
    EXPECT_LT(epc.Tc_McMillan, 3.0);
}
```

## Acceptance Criteria

- [ ] EPC matrix elements g_{mn}(k,q,ν) correctly computed
- [ ] Mode transformation from perturbation to phonon basis implemented
- [ ] Phonon linewidths γ(q,ν) ≥ 0 for all modes
- [ ] Eliashberg function α²F(ω) computed with correct normalization
- [ ] λ sum rule satisfied (integral vs sum agreement < 1%)
- [ ] |g| relative error vs QE < 1%
- [ ] λ relative error vs QE < 5%
- [ ] McMillan Tc formula implemented and validated
- [ ] Supports Gaussian smearing for delta functions
- [ ] All unit tests pass (≥7 test cases)
- [ ] Code review passes 6-agent DFPT review
