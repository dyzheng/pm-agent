# DFPT-402: Implement Q-point Grid and Workflow

## Objective

Implement the complete phonon calculation workflow: q-point grid generation with symmetry reduction, q-point loop driver, restart/checkpoint mechanism, and post-processing tools equivalent to QE's `q2r` (q-to-real-space force constants) and `matdyn` (phonon dispersion interpolation).

## Reference Code

### QE Source (Fortran)

**Q-point grid and symmetry** (`/root/q-e/PHonon/PH/q_points.f90`):
```fortran
SUBROUTINE q_points()
  ! Generates q-point grid and reduces by symmetry
  !
  ! 1. Generate uniform grid: q_i = (i1/nq1, i2/nq2, i3/nq3)
  ! 2. Find small group of q for each q-point
  ! 3. Identify irreducible q-points (star of q)
  ! 4. Compute weights (multiplicity / total)
  !
  ! Output:
  !   nqs     — number of irreducible q-points
  !   x_q(3, nqs) — q-point coordinates
  !   wq(nqs) — weights (sum to nq1*nq2*nq3)
  !   nsymq(nqs) — symmetry operations for each q
END SUBROUTINE
```

**Q-point loop driver** (`/root/q-e/PHonon/PH/do_phonon.f90`):
```fortran
SUBROUTINE do_phonon(auxdyn)
  ! Main q-point loop
  DO iq = 1, nqs
    IF (done(iq)) CYCLE          ! skip completed q-points (restart)
    CALL prepare_q(auxdyn, iq)   ! setup q-specific data
    CALL run_nscf(iq)            ! bands at k+q
    CALL initialize_ph()         ! allocate, setup symmetry
    IF (epsil .OR. zeu) CALL phescf()  ! dielectric, Born charges
    CALL phqscf()                ! main DFPT calculation
    CALL dynmatrix_new(iq)       ! symmetrize, diagonalize
    IF (elph) CALL elphon()      ! electron-phonon (optional)
    CALL save_status(iq)         ! checkpoint
  ENDDO
END SUBROUTINE
```

**Restart mechanism** (`/root/q-e/PHonon/PH/ph_restart.f90`):
```fortran
MODULE ph_restart
  ! Checkpoint/restart infrastructure
  !
  ! Saves:
  !   - Which q-points are completed
  !   - Which irreps within current q-point are done
  !   - Dynamical matrix contributions so far
  !   - Response wavefunctions (optional, for fine-grained restart)
  !
  ! Files:
  !   _ph0/{prefix}.phsave/status_run.xml  — overall status
  !   _ph0/{prefix}.phsave/dynmat.{iq}.xml — dynamical matrix per q
  !   _ph0/{prefix}.phsave/tensors.xml     — dielectric, Born charges
END MODULE
```

**Q-to-R transformation** (`/root/q-e/PHonon/PH/q2r.f90`):
```fortran
PROGRAM q2r
  ! Converts dynamical matrices C(q) to real-space force constants C(R)
  !
  ! Algorithm:
  !   1. Read C(q) for all q-points on the grid
  !   2. Fourier transform: C(R) = (1/Nq) Σ_q C(q) × exp(iq·R)
  !   3. Apply acoustic sum rule (optional)
  !   4. Write force constants to file
  !
  ! Input: fildyn (dynamical matrix files)
  ! Output: flfrc (force constant file)
  !
  ! Key: R-vectors are lattice vectors within the Wigner-Seitz cell
  !      of the q-point superlattice
END PROGRAM
```

**Phonon dispersion interpolation** (`/root/q-e/PHonon/PH/matdyn.f90`):
```fortran
PROGRAM matdyn
  ! Calculates phonon frequencies at arbitrary q-points from force constants
  !
  ! Algorithm:
  !   1. Read force constants C(R) from file
  !   2. For each target q-point:
  !      a. Fourier interpolate: C(q) = Σ_R C(R) × exp(-iq·R)
  !      b. Add non-analytic (LO-TO) correction if polar
  !      c. Diagonalize: C(q)·e = ω²·e
  !   3. Output frequencies along high-symmetry path
  !
  ! Also computes:
  !   - Phonon DOS (tetrahedron method or Gaussian smearing)
  !   - Partial DOS (atom-projected)
  !   - Thermodynamic properties (free energy, entropy, specific heat)
  !
  ! Input: flfrc (force constants), q-path or q-grid
  ! Output: frequencies, DOS, thermodynamics
END PROGRAM
```

### ABACUS Target — Existing Infrastructure

**Symmetry for q-points** (`/root/abacus-dfpt/abacus-develop/source/source_cell/module_symmetry/symmetry.h`):
```cpp
class Symmetry {
    int nrotk;                          // number of point group operations
    ModuleBase::Matrix3 gmatrix[48];    // rotation matrices (Cartesian)
    ModuleBase::Matrix3 kgmatrix[48];   // rotation matrices (reciprocal)
    // Can be used to find small group of q and reduce q-grid
};
```

**K-point grid generation** (`/root/abacus-dfpt/abacus-develop/source/source_cell/klist.h`):
```cpp
class K_Vectors {
    void Monkhorst_Pack(const int* nmp, const double* shift, int& nkstot);
    // Similar logic can be adapted for q-point grid
};
```

## Implementation Guide

### Architecture

```
PhononDriver class
├── generate_qgrid()
│   ├── Monkhorst-Pack q-point grid
│   ├── Symmetry reduction → irreducible q-points
│   └── Compute weights and star of q
├── run_qpoint_loop()
│   └── For each irreducible q-point:
│       ├── check_restart() — skip if already done
│       ├── setup_qpoint() — k+q mapping, NSCF at k+q
│       ├── run_dfpt() — all perturbations at this q
│       ├── compute_dynmat() — assemble dynamical matrix
│       ├── save_checkpoint() — write status and dynmat
│       └── output_qpoint_results()
├── postprocess()
│   ├── q2r() — Fourier transform to real-space force constants
│   ├── matdyn() — interpolate to arbitrary q-points
│   └── compute_thermodynamics() — free energy, entropy, Cv
└── output_final_results()
    ├── Write all dynamical matrices
    ├── Write force constants
    ├── Write phonon band structure
    └── Write phonon DOS
```

### Q-point Grid Generation

```cpp
class QPointGrid {
public:
    struct QPoint {
        ModuleBase::Vector3<double> coord;  // crystal coordinates
        double weight;                       // integration weight
        int star_size;                       // number of equivalent q-points
        std::vector<ModuleBase::Vector3<double>> star;  // equivalent q-points
        int nsymq;                           // symmetry operations preserving q
    };

    // Generate Monkhorst-Pack grid
    void generate(int nq1, int nq2, int nq3,
                  const Symmetry& symm,
                  const ModuleBase::Matrix3& reciprocal_lattice);

    // Access
    int nq_irr() const;                     // number of irreducible q-points
    const QPoint& get_qpoint(int iq) const;
    int nq_full() const;                     // total grid points

private:
    std::vector<QPoint> qpoints_irr_;
    int nq1_, nq2_, nq3_;

    // Find small group of q
    int find_small_group(const ModuleBase::Vector3<double>& q,
                         const Symmetry& symm,
                         std::vector<int>& sym_indices);

    // Check if two q-points are equivalent by symmetry
    bool are_equivalent(const ModuleBase::Vector3<double>& q1,
                        const ModuleBase::Vector3<double>& q2,
                        const Symmetry& symm);
};
```

### Checkpoint/Restart

```cpp
class DFPTCheckpoint {
public:
    // Save status after completing a q-point
    void save(int iq, const std::string& project_dir);

    // Load status on restart
    bool load(const std::string& project_dir);

    // Check if a q-point is already completed
    bool is_completed(int iq) const;

    // Save dynamical matrix for one q-point
    void save_dynmat(int iq, const ModuleBase::ComplexMatrix& dyn,
                     const ModuleBase::Vector3<double>& q);

    // Load dynamical matrix
    ModuleBase::ComplexMatrix load_dynmat(int iq);

private:
    struct Status {
        std::vector<bool> q_completed;
        std::vector<std::vector<bool>> irrep_completed;  // per q-point
        int current_q;
        int current_irrep;
    };
    Status status_;
    std::string checkpoint_dir_;
};
```

### Q-to-R Transformation (q2r equivalent)

```cpp
class ForceConstants {
public:
    // Compute real-space force constants from dynamical matrices
    // C(R) = (1/Nq) Σ_q C(q) × exp(iq·R)
    void compute_from_dynmat(
        const std::vector<ModuleBase::ComplexMatrix>& dynmat_q,  // C(q) at grid points
        const QPointGrid& qgrid,
        const UnitCell& ucell);

    // Interpolate to arbitrary q-point
    // C(q) = Σ_R C(R) × exp(-iq·R) × weight(R)
    ModuleBase::ComplexMatrix interpolate(
        const ModuleBase::Vector3<double>& q) const;

    // Add LO-TO correction for polar materials
    void add_loto(ModuleBase::ComplexMatrix& dyn,
                  const ModuleBase::Vector3<double>& q,
                  const ModuleBase::matrix& epsilon,
                  const std::vector<ModuleBase::matrix>& zstar) const;

    // Apply acoustic sum rule
    void apply_asr(const std::string& asr_type);

    // Save/load force constants
    void save(const std::string& filename) const;
    void load(const std::string& filename);

private:
    // Force constants C(κα, κ'β; R)
    // Indexed by: R-vector, atom pair, Cartesian directions
    struct FCEntry {
        ModuleBase::Vector3<int> R;     // lattice vector (in units of a1, a2, a3)
        int iat1, iat2;                  // atom indices
        ModuleBase::matrix fc;           // 3×3 force constant matrix
        double weight;                   // Wigner-Seitz weight
    };
    std::vector<FCEntry> fc_data_;
    int nat_;
    ModuleBase::Matrix3 at_;  // lattice vectors
};
```

### Phonon Dispersion (matdyn equivalent)

```cpp
class PhononDispersion {
public:
    struct BandPoint {
        ModuleBase::Vector3<double> q;
        double path_length;              // cumulative path length
        std::vector<double> frequencies;  // cm⁻¹
    };

    // Compute phonon band structure along high-symmetry path
    std::vector<BandPoint> compute_bands(
        const ForceConstants& fc,
        const std::vector<ModuleBase::Vector3<double>>& path_points,
        const std::vector<std::string>& labels,
        int npoints_per_segment);

    // Compute phonon DOS
    struct DOSResult {
        std::vector<double> omega_grid;  // frequency grid (cm⁻¹)
        std::vector<double> dos;         // total DOS
        std::vector<std::vector<double>> pdos;  // partial DOS per atom
    };
    DOSResult compute_dos(
        const ForceConstants& fc,
        int nq1, int nq2, int nq3,       // dense q-grid for DOS
        double sigma,                      // Gaussian smearing (cm⁻¹)
        int nw);                           // number of frequency points

    // Compute thermodynamic properties
    struct ThermoResult {
        std::vector<double> temperature;  // K
        std::vector<double> free_energy;  // eV/cell
        std::vector<double> entropy;      // kB/cell
        std::vector<double> cv;           // kB/cell (specific heat)
    };
    ThermoResult compute_thermodynamics(
        const ForceConstants& fc,
        int nq1, int nq2, int nq3,
        double T_min, double T_max, int nT);

    // Output
    void write_bands(const std::string& filename, const std::vector<BandPoint>& bands);
    void write_dos(const std::string& filename, const DOSResult& dos);
    void write_thermo(const std::string& filename, const ThermoResult& thermo);
};
```

### Key Equations

**Fourier transform (q → R)**:
```
C(κα, κ'β; R) = (1/N_q) Σ_q w_q × C(κα, κ'β; q) × exp(iq·R)
```

**Fourier interpolation (R → q)**:
```
C(κα, κ'β; q) = Σ_R w_WS(R) × C(κα, κ'β; R) × exp(-iq·R)
```
where `w_WS(R)` is the Wigner-Seitz weight (handles boundary R-vectors).

**Wigner-Seitz weights**: For R-vectors on the boundary of the Wigner-Seitz cell, the weight is the fraction of the cell boundary that belongs to this R-vector (typically 1/2, 1/3, 1/4, etc.).

**Phonon DOS** (Gaussian smearing):
```
g(ω) = (1/N_q) Σ_{q,ν} δ_σ(ω - ω_{ν,q})
where δ_σ(x) = (1/σ√(2π)) exp(-x²/2σ²)
```

**Thermodynamic properties** (quantum harmonic approximation):
```
F(T) = Σ_{q,ν} [ℏω/2 + k_B·T·ln(1 - exp(-ℏω/k_B·T))] / N_q
S(T) = -∂F/∂T
C_v(T) = -T·∂²F/∂T²
```

### Critical Implementation Details

1. **Wigner-Seitz cell construction**: The R-vectors for force constants must be within the Wigner-Seitz cell of the q-point superlattice. This requires:
   ```cpp
   // Superlattice vectors: A_i = nq_i × a_i
   // WS cell: set of R closest to origin
   // For boundary R: weight = 1/(number of equivalent R)
   std::vector<WSPoint> construct_ws_cell(int nq1, int nq2, int nq3,
                                           const ModuleBase::Matrix3& at) {
       // Check all R = n1*a1 + n2*a2 + n3*a3 with |n_i| ≤ 2*nq_i
       // For each R, check if it's inside WS cell
       // For boundary R, compute degeneracy
   }
   ```

2. **Symmetry of force constants**: Real-space force constants must satisfy:
   - Translational invariance: `Σ_R C(κα, κ'β; R) = 0` for κ=κ' (ASR)
   - Permutation symmetry: `C(κα, κ'β; R) = C(κ'β, κα; -R)`
   - Point group symmetry: `S·C(q)·S† = C(Sq)`

3. **LO-TO correction in interpolation**: For polar materials, the non-analytic term must be added during interpolation (not in the force constants):
   ```cpp
   // At each interpolated q-point (q ≠ 0):
   // C_total(q) = C_short_range(q) + C_non_analytic(q̂)
   // C_NA depends on direction q̂ = q/|q|, not magnitude
   ```

4. **Checkpoint file format**: Use JSON or XML for portability:
   ```json
   {
     "nq_irr": 8,
     "completed": [true, true, true, false, false, false, false, false],
     "current_q": 3,
     "dynmat_files": ["dynmat_q1.xml", "dynmat_q2.xml", "dynmat_q3.xml"]
   }
   ```

## TDD Test Plan

### Unit Tests to Write FIRST

```cpp
// test/test_qpoint_workflow.cpp

// 1. Q-point grid generation
TEST(QPointGrid, MonkhorstPack) {
    QPointGrid grid;
    grid.generate(4, 4, 4, si_symmetry, si_reciprocal);

    // Full grid: 64 points
    EXPECT_EQ(grid.nq_full(), 64);
    // Irreducible (FCC Si): ~8 points
    EXPECT_LE(grid.nq_irr(), 10);
    EXPECT_GE(grid.nq_irr(), 4);
    // Weights sum to nq_full
    double wsum = 0;
    for (int iq = 0; iq < grid.nq_irr(); iq++) {
        wsum += grid.get_qpoint(iq).weight;
    }
    EXPECT_NEAR(wsum, 64.0, 1e-10);
}

// 2. Q-point symmetry equivalence
TEST(QPointGrid, SymmetryEquivalence) {
    QPointGrid grid;
    grid.generate(4, 4, 4, si_symmetry, si_reciprocal);

    // Gamma point should have full symmetry
    auto gamma = grid.get_qpoint(0);  // assuming Gamma is first
    EXPECT_EQ(gamma.star_size, 1);

    // X point (0.5, 0, 0) should have star_size = 3 (for cubic)
    // (0.5,0,0), (0,0.5,0), (0,0,0.5)
}

// 3. Checkpoint save/load roundtrip
TEST(DFPTCheckpoint, SaveLoadRoundtrip) {
    DFPTCheckpoint ckpt;
    ckpt.mark_completed(0);
    ckpt.mark_completed(1);
    ckpt.save_dynmat(0, create_test_dynmat(2), {0,0,0});
    ckpt.save("/tmp/test_ckpt");

    DFPTCheckpoint ckpt2;
    EXPECT_TRUE(ckpt2.load("/tmp/test_ckpt"));
    EXPECT_TRUE(ckpt2.is_completed(0));
    EXPECT_TRUE(ckpt2.is_completed(1));
    EXPECT_FALSE(ckpt2.is_completed(2));

    auto dyn = ckpt2.load_dynmat(0);
    EXPECT_EQ(dyn.nr, 6);
    EXPECT_EQ(dyn.nc, 6);
}

// 4. Q-to-R Fourier transform roundtrip
TEST(ForceConstants, FourierRoundtrip) {
    // Create test dynamical matrices on a 2×2×2 grid
    auto dynmat_q = create_test_dynmat_grid(2, 2, 2);
    QPointGrid qgrid;
    qgrid.generate(2, 2, 2, no_symmetry, cubic_reciprocal);

    // Q → R
    ForceConstants fc;
    fc.compute_from_dynmat(dynmat_q, qgrid, ucell);

    // R → Q (interpolate back to grid points)
    for (int iq = 0; iq < qgrid.nq_full(); iq++) {
        auto dyn_interp = fc.interpolate(qgrid.get_qpoint(iq).coord);
        compare_complex_matrices(dyn_interp, dynmat_q[iq], 1e-10);
    }
}

// 5. Acoustic sum rule in force constants
TEST(ForceConstants, AcousticSumRule) {
    ForceConstants fc;
    fc.load("test_data/si_fc.dat");
    fc.apply_asr("crystal");

    // Interpolate at Gamma: acoustic modes should be exactly zero
    auto dyn_gamma = fc.interpolate({0, 0, 0});
    auto [omega2, eigvec] = diagonalize(dyn_gamma, 2);

    // 3 acoustic modes: ω² = 0
    std::sort(omega2.begin(), omega2.end());
    EXPECT_NEAR(omega2[0], 0.0, 1e-10);
    EXPECT_NEAR(omega2[1], 0.0, 1e-10);
    EXPECT_NEAR(omega2[2], 0.0, 1e-10);
}

// 6. Phonon DOS normalization
TEST(PhononDispersion, DOSNormalization) {
    ForceConstants fc;
    fc.load("test_data/si_fc.dat");

    auto dos = PhononDispersion::compute_dos(fc, 20, 20, 20, 5.0, 500);

    // DOS integrates to 3*nat = 6 for Si
    double integral = 0;
    double dw = dos.omega_grid[1] - dos.omega_grid[0];
    for (size_t i = 0; i < dos.dos.size(); i++) {
        integral += dos.dos[i] * dw;
    }
    EXPECT_NEAR(integral, 6.0, 0.1);  // 3*nat modes
}

// 7. Thermodynamics — high-T limit
TEST(PhononDispersion, HighTLimit) {
    ForceConstants fc;
    fc.load("test_data/si_fc.dat");

    auto thermo = PhononDispersion::compute_thermodynamics(fc, 10, 10, 10, 10, 5000, 50);

    // At high T: Cv → 3*nat*kB (Dulong-Petit)
    double cv_high_T = thermo.cv.back();
    double dulong_petit = 3 * 2;  // 3*nat in units of kB
    EXPECT_NEAR(cv_high_T, dulong_petit, 0.1);
}

// 8. Restart: interrupted calculation resumes correctly
TEST(QPointWorkflow, RestartResumption) {
    auto system = create_si_system();

    // Run first 3 q-points, then "interrupt"
    run_dfpt_partial(system, /*stop_after_q=*/3);

    // Restart: should skip first 3 and continue from q=4
    auto result = run_dfpt_with_restart(system);

    // Final result should be same as running all at once
    auto result_full = run_dfpt_full(system);
    compare_phonon_results(result, result_full, 1e-12);
}
```

### Integration Tests

```bash
# Full workflow: DFPT → q2r → matdyn → phonon band structure
cd test_si_phonon/
mpirun -np 4 abacus < INPUT          # DFPT calculation
abacus_q2r < q2r.in                  # Force constants
abacus_matdyn < matdyn.in            # Phonon dispersion
# Compare with QE reference
python compare_bands.py si_bands_abacus.dat si_bands_qe.dat --tol 0.1
```

## Acceptance Criteria

- [ ] Q-point grid generation with Monkhorst-Pack and symmetry reduction
- [ ] Q-point loop driver processes all irreducible q-points
- [ ] Checkpoint/restart mechanism saves and resumes correctly
- [ ] Q-to-R Fourier transform (q2r equivalent) implemented
- [ ] Phonon dispersion interpolation (matdyn equivalent) implemented
- [ ] Fourier roundtrip preserves dynamical matrices to < 1e-10
- [ ] Acoustic sum rule enforced in force constants
- [ ] Phonon DOS normalization correct (integrates to 3*nat)
- [ ] Thermodynamic properties correct (Dulong-Petit limit)
- [ ] End-to-end workflow test passes
- [ ] All unit tests pass (≥8 test cases)
- [ ] Code review passes
