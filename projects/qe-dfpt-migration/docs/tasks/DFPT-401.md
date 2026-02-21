# DFPT-401: Create ESolver_DFPT Class

## Objective

Create the `ESolver_KS_PW_DFPT` class that integrates the DFPT module into ABACUS's main execution flow. This ESolver handles input parameter parsing, driver integration, output file generation, and serves as the user-facing entry point for phonon calculations via `calculation = "dfpt"` in the INPUT file.

## Reference Code

### QE Source (Fortran)

**Main entry** (`/root/q-e/PHonon/PH/phonon.f90`):
```fortran
PROGRAM phonon
  ! 1. CALL phq_readin()     — parse input (namelist &INPUTPH)
  ! 2. CALL check_initial_status()  — setup q-grid, check restart
  ! 3. CALL do_phonon()      — main q-point loop
  !    └── For each q:
  !        ├── prepare_q()    — setup q-specific data
  !        ├── run_nscf()     — recalculate bands at k+q
  !        ├── initialize_ph() — allocate, setup symmetry
  !        ├── phescf()       — electric field response (ε, Z*)
  !        ├── phqscf()       — phonon response (main DFPT)
  !        ├── dynmatrix()    — symmetrize, diagonalize
  !        └── elphon()       — electron-phonon (optional)
END PROGRAM
```

**Input parameters** (`/root/q-e/PHonon/PH/phq_readin.f90`):
```fortran
NAMELIST /INPUTPH/ &
  tr2_ph,        &  ! convergence threshold (default 1e-12)
  niter_ph,      &  ! max DFPT iterations (default 100)
  alpha_mix,     &  ! mixing parameter (default 0.7)
  nmix_ph,       &  ! Broyden history size (default 4)
  ldisp,         &  ! .true. for phonon dispersion
  nq1, nq2, nq3,&  ! q-point grid
  epsil,         &  ! .true. for dielectric constant
  zeu,           &  ! .true. for Born effective charges
  elph,          &  ! .true. for electron-phonon
  trans,         &  ! .true. for phonon calculation
  recover,       &  ! .true. for restart
  fildyn,        &  ! dynamical matrix output file
  fildvscf,      &  ! response potential output file
  fildrho,       &  ! response density output file
  start_q, last_q   ! q-point range
```

**Output files**:
- `{prefix}.dyn{iq}` — Dynamical matrix at each q-point (XML format)
- `{prefix}.dvscf{iq}` — Response potential (for electron-phonon)
- `{prefix}.freq` — Phonon frequencies
- Standard output: iteration convergence, frequencies, symmetry analysis

### ABACUS Target — ESolver Framework

**ESolver base class** (`/root/abacus-dfpt/abacus-develop/source/source_esolver/esolver.h`):
```cpp
class ESolver {
public:
    virtual void before_all_runners(UnitCell& ucell, const Input_para& inp) = 0;
    virtual void runner(UnitCell& ucell, const int istep) = 0;
    virtual void after_all_runners(UnitCell& ucell) = 0;
    virtual double cal_energy() = 0;
    virtual void cal_force(ModuleBase::matrix& force) = 0;
    virtual void cal_stress(ModuleBase::matrix& stress) = 0;
};
```

**ESolver_KS_PW** (`/root/abacus-dfpt/abacus-develop/source/source_esolver/esolver_ks_pw.h`):
```cpp
template <typename T, typename Device = base_device::DEVICE_CPU>
class ESolver_KS_PW : public ESolver_KS<T, Device> {
public:
    void before_all_runners(UnitCell& ucell, const Input_para& inp) override;
    void runner(UnitCell& ucell, const int istep) override;
    // Ground-state SCF infrastructure:
    // - PW_Basis, K_Vectors, Psi, Hamiltonian, HSolver, ElecState, Potential
    // DFPT ESolver inherits all of this
protected:
    ModulePW::PW_Basis_K* pw_wfc;
    psi::Psi<T, Device>* psi;
    hamilt::Hamilt<T, Device>* p_hamilt;
    hsolver::HSolver<T, Device>* phsol;
    elecstate::ElecState* pelec;
};
```

**Existing DFPT ESolver** (`/root/abacus-dfpt/abacus-develop/source/source_esolver/esolver_ks_pw_dfpt.h`):
```cpp
template <typename T, typename Device = base_device::DEVICE_CPU>
class ESolver_KS_PW_DFPT : public ESolver_KS_PW<T, Device> {
public:
    void before_all_runners(UnitCell& ucell, const Input_para& inp) override;
    void runner(UnitCell& ucell, const int istep) override;
    void after_all_runners(UnitCell& ucell) override;

private:
    // DFPT-specific methods
    void before_dfpt();
    void dfpt_scf_loop(int iq, int ipert);
    void solve_sternheimer();
    void compute_drho();
    void compute_dvscf();
    void mix_dvscf();
    void compute_phonon_properties();
    void output_dfpt_results();

    // DFPT data
    int nq1_, nq2_, nq3_, nq_;
    std::vector<ModuleBase::Vector3<double>> xq_list_;
    int npert_;
    hamilt::HamiltPW_DFPT<T, Device>* p_hamilt_dfpt_;
    hsolver::HSolverPW_DFPT<T, Device>* phsol_dfpt_;
    // ... dpsi, drho, dvscf, dyn_mat, omega, eigvec
};
```

**Driver integration** (`/root/abacus-dfpt/abacus-develop/source/driver.cpp`):
```cpp
// ESolver selection based on calculation type
if (inp.calculation == "scf") {
    p_esolver = new ESolver_KS_PW<std::complex<double>>();
} else if (inp.calculation == "dfpt") {
    p_esolver = new ESolver_KS_PW_DFPT<std::complex<double>>();
}
```

**Input parameters** (`/root/abacus-dfpt/abacus-develop/source/source_io/module_parameter/input_parameter.h`):
```cpp
// Already defined:
bool dfpt_phonon = false;
int dfpt_nq1 = 1, dfpt_nq2 = 1, dfpt_nq3 = 1;
double dfpt_conv_thr = 1e-8;
int dfpt_max_iter = 100;
double dfpt_cg_thr = 1e-10;
int dfpt_max_cg_iter = 50;
std::string dfpt_mixing = "broyden";
double dfpt_mixing_beta = 0.7;
```

## Implementation Guide

### ESolver Lifecycle

```
Driver::init()
  └── ESolver_KS_PW_DFPT::before_all_runners()
      ├── Parse DFPT input parameters
      ├── Call parent ESolver_KS_PW::before_all_runners() (setup PW, k-points, etc.)
      └── Validate DFPT-specific parameters

Driver::run()
  └── ESolver_KS_PW_DFPT::runner()
      ├── Step 1: Ground-state SCF (inherited from ESolver_KS_PW)
      │   └── Converge ground-state charge density and wavefunctions
      ├── Step 2: before_dfpt()
      │   ├── Generate q-point grid from (nq1, nq2, nq3)
      │   ├── Apply symmetry reduction to q-points
      │   ├── Allocate DFPT data structures (dpsi, drho, dvscf)
      │   ├── Create HamiltPW_DFPT and HSolverPW_DFPT
      │   └── Initialize perturbation patterns
      ├── Step 3: Q-point loop
      │   └── For each q-point:
      │       ├── Setup k+q mapping
      │       ├── Recalculate bands at k+q (if q ≠ 0)
      │       ├── For each perturbation:
      │       │   ├── Compute dV_bare · ψ (DFPT-102)
      │       │   └── dfpt_scf_loop() (DFPT-201)
      │       └── Compute dynamical matrix for this q (DFPT-202)
      ├── Step 4: compute_phonon_properties()
      │   ├── Apply acoustic sum rule
      │   ├── Diagonalize dynamical matrices
      │   └── Extract frequencies and eigenvectors
      └── Step 5: output_dfpt_results()
          ├── Write dynamical matrix files
          ├── Write phonon frequencies
          └── Print summary to stdout

Driver::finalize()
  └── ESolver_KS_PW_DFPT::after_all_runners()
      ├── Deallocate DFPT data structures
      └── Print timing summary
```

### Input Parameter Integration

New parameters to add to `input_parameter.h` (beyond existing):

```cpp
// Additional DFPT parameters needed:
bool dfpt_epsil = false;          // compute dielectric constant
bool dfpt_zeu = false;            // compute Born effective charges
bool dfpt_elph = false;           // compute electron-phonon coupling
bool dfpt_recover = false;        // restart from checkpoint
std::string dfpt_fildyn = "dynmat";  // dynamical matrix output prefix
std::string dfpt_fildvscf = "";   // response potential output (for elph)
int dfpt_start_q = 1;            // first q-point to compute
int dfpt_last_q = 0;             // last q-point (0 = all)
double dfpt_alpha_pv = 0.0;      // projector parameter (0 = auto)
std::string dfpt_asr = "crystal"; // acoustic sum rule type
```

### Output Format

**Standard output** (during calculation):
```
 ============================================================
  ABACUS DFPT Phonon Calculation
  Q-point grid: 4 x 4 x 4
  Number of q-points: 8 (after symmetry reduction)
  Number of perturbations per q: 6 (2 atoms × 3 directions)
 ============================================================

  Q-point   1 / 8:  ( 0.0000  0.0000  0.0000 )  weight = 0.0156
    Perturbation  1 / 6:  atom 1, direction x
      DFPT SCF iteration   1:  dr2 = 1.234e-02
      DFPT SCF iteration   2:  dr2 = 3.456e-04
      ...
      DFPT SCF converged in 12 iterations, dr2 = 8.765e-11

  Phonon frequencies at q = ( 0.0000  0.0000  0.0000 ):
    Mode   1:    0.00 cm-1  (acoustic)
    Mode   2:    0.00 cm-1  (acoustic)
    Mode   3:    0.00 cm-1  (acoustic)
    Mode   4:  519.87 cm-1
    Mode   5:  519.87 cm-1
    Mode   6:  519.87 cm-1
```

**Dynamical matrix file** (`dynmat_q{iq}.xml`):
```xml
<dynamical_matrix>
  <header>
    <ntyp>1</ntyp>
    <nat>2</nat>
    <ibrav>2</ibrav>
    <celldm>10.2</celldm>
    <qpoint>0.0 0.0 0.0</qpoint>
  </header>
  <matrix>
    <!-- 6×6 complex matrix -->
    <row i="1">
      (0.123456, 0.000000) (0.023456, 0.001234) ...
    </row>
    ...
  </matrix>
  <frequencies>
    0.00 0.00 0.00 519.87 519.87 519.87
  </frequencies>
</dynamical_matrix>
```

### Critical Implementation Details

1. **Ground-state to DFPT transition**: After ground-state SCF converges, the DFPT ESolver must preserve all ground-state data (wavefunctions, charge density, potential) and create DFPT-specific objects on top:
   ```cpp
   void ESolver_KS_PW_DFPT::runner(UnitCell& ucell, const int istep) {
       // Step 1: Run ground-state SCF (parent class)
       ESolver_KS_PW<T, Device>::runner(ucell, istep);

       // Step 2: Transition to DFPT
       // Ground-state data is now available: this->psi, this->pelec, etc.
       this->before_dfpt();

       // Step 3: DFPT calculation
       this->run_dfpt();
   }
   ```

2. **K+q band recalculation**: For q ≠ 0, wavefunctions at k+q are needed. These must be computed by running a non-self-consistent (NSCF) calculation at k+q points:
   ```cpp
   void ESolver_KS_PW_DFPT::setup_kplusq(int iq) {
       // Generate k+q point list
       auto kq_list = generate_kplusq_points(this->kv, xq_list_[iq]);
       // Run NSCF at k+q points using ground-state potential
       run_nscf_at_kplusq(kq_list);
       // Store ψ(k+q) and ε(k+q)
   }
   ```

3. **Q-point symmetry reduction**: Use crystal symmetry to reduce the number of independent q-points:
   ```cpp
   void generate_qpoint_grid() {
       // Generate full grid
       for (int i = 0; i < nq1_; i++)
           for (int j = 0; j < nq2_; j++)
               for (int k = 0; k < nq3_; k++)
                   qpoints_full.push_back({(double)i/nq1_, (double)j/nq2_, (double)k/nq3_});

       // Reduce by symmetry
       qpoints_irr = reduce_by_symmetry(qpoints_full, ucell.symm);
       // Store weights
   }
   ```

4. **Calculation type registration**: Register `"dfpt"` as a valid calculation type in ABACUS's input parser and ESolver factory.

## TDD Test Plan

### Unit Tests to Write FIRST

```cpp
// test/test_esolver_dfpt.cpp

// 1. ESolver instantiation
TEST(ESolverDFPT, Instantiation) {
    auto solver = std::make_unique<ESolver_KS_PW_DFPT<std::complex<double>>>();
    EXPECT_NE(solver, nullptr);
}

// 2. Input parameter parsing
TEST(ESolverDFPT, InputParameterParsing) {
    Input_para inp;
    inp.calculation = "dfpt";
    inp.dfpt_phonon = true;
    inp.dfpt_nq1 = 4; inp.dfpt_nq2 = 4; inp.dfpt_nq3 = 4;
    inp.dfpt_conv_thr = 1e-10;

    auto solver = create_dfpt_solver(inp);
    EXPECT_EQ(solver->get_nq1(), 4);
    EXPECT_DOUBLE_EQ(solver->get_conv_thr(), 1e-10);
}

// 3. Q-point grid generation
TEST(ESolverDFPT, QPointGridGeneration) {
    auto qpoints = generate_qpoint_grid(4, 4, 4);
    EXPECT_EQ(qpoints.size(), 64);  // full grid

    // After symmetry reduction (FCC Si): should be ~8 irreducible q-points
    auto qpoints_irr = reduce_by_symmetry(qpoints, si_symmetry);
    EXPECT_LE(qpoints_irr.size(), 10);
    EXPECT_GE(qpoints_irr.size(), 4);

    // Weights should sum to 1
    double wsum = 0;
    for (auto& qp : qpoints_irr) wsum += qp.weight;
    EXPECT_NEAR(wsum, 1.0, 1e-10);
}

// 4. Calculation type selection
TEST(ESolverDFPT, CalculationTypeSelection) {
    Input_para inp;
    inp.calculation = "dfpt";
    auto solver = ESolver::create(inp);
    EXPECT_NE(dynamic_cast<ESolver_KS_PW_DFPT<std::complex<double>>*>(solver), nullptr);
}

// 5. Output file generation
TEST(ESolverDFPT, OutputFileGeneration) {
    auto system = create_si_test_system();
    run_dfpt_and_output(system);

    // Check output files exist
    EXPECT_TRUE(file_exists("dynmat_q1.xml"));
    EXPECT_TRUE(file_exists("phonon_frequencies.dat"));

    // Check output file content
    auto dyn = parse_dynmat_xml("dynmat_q1.xml");
    EXPECT_EQ(dyn.nat, 2);
    EXPECT_EQ(dyn.nmodes, 6);
}

// 6. INPUT file integration
TEST(ESolverDFPT, INPUTFileIntegration) {
    // Write test INPUT file
    write_test_input("INPUT", {
        {"calculation", "dfpt"},
        {"dfpt_phonon", "1"},
        {"dfpt_nq1", "2"}, {"dfpt_nq2", "2"}, {"dfpt_nq3", "2"},
        {"dfpt_conv_thr", "1e-8"}
    });

    auto inp = parse_input("INPUT");
    EXPECT_EQ(inp.calculation, "dfpt");
    EXPECT_TRUE(inp.dfpt_phonon);
    EXPECT_EQ(inp.dfpt_nq1, 2);
}
```

### Integration Tests

```cpp
// End-to-end: INPUT file → ESolver → phonon frequencies
TEST(ESolverDFPT_Integration, SiEndToEnd) {
    // Requires full ABACUS infrastructure
    setup_si_test_case("test_dfpt_si/");
    int ret = run_abacus("test_dfpt_si/");
    EXPECT_EQ(ret, 0);

    // Check phonon frequencies in output
    auto freq = parse_phonon_output("test_dfpt_si/phonon_frequencies.dat");
    EXPECT_EQ(freq.size(), 6);  // 2 atoms × 3 = 6 modes
    // 3 acoustic modes near zero
    EXPECT_NEAR(freq[0], 0.0, 1.0);
}
```

## Acceptance Criteria

- [ ] `ESolver_KS_PW_DFPT` fully implemented and callable via `calculation = "dfpt"`
- [ ] All DFPT input parameters parsed correctly from INPUT file
- [ ] Q-point grid generation with symmetry reduction working
- [ ] Ground-state → DFPT transition seamless (no data loss)
- [ ] K+q band recalculation implemented for q ≠ 0
- [ ] Output files generated (dynamical matrix XML, frequencies)
- [ ] Standard output shows iteration convergence and final frequencies
- [ ] Integration with ABACUS Driver flow verified
- [ ] All unit tests pass (≥6 test cases)
- [ ] Code review passes
