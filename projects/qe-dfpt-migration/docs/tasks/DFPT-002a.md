# DFPT-002a: Write DFPT Domain Knowledge Documentation

## Objective

Create comprehensive DFPT domain knowledge documentation that will be automatically injected into all development and review agents. This ensures every agent working on the migration has consistent understanding of DFPT physics, units, algorithms, and code mappings.

## Reference Code

### QE Source — Physics and Units

**Unit system** (`/root/q-e/Modules/constants.f90`):
- QE uses Rydberg atomic units: energy in Ry, length in Bohr
- Key constants: `e2 = 2.0` (Hartree), `fpi = 4π`, `tpiba = 2π/alat`, `tpiba2 = tpiba²`
- Dynamical matrix units: Ry/Bohr² (converted to cm⁻¹ via `RY_TO_CMM1`)
- Born effective charges: dimensionless (in units of |e|)
- Dielectric tensor: dimensionless

**Physical constraints enforced in QE**:
- Acoustic sum rule: `Σ_κ' C(κα, κ'β; q=0) = 0` — enforced in `q2r.f90`, `dynmat.f90`
- Hermiticity: `D(κα, κ'β; q) = D*(κ'β, κα; -q)` — enforced in `symdynph_gq.f90`
- Charge conservation: `Σ_κ Z*_κ = Z_ion` — checked in `zstar_eu.f90`
- Symmetry: `S·D(q)·S† = D(Sq)` — enforced in `symdyn_munu.f90`

**Key QE subroutines for physics reference**:
- `/root/q-e/PHonon/PH/dynmat0.f90` — Bare dynamical matrix: `dynmat_us + d2ionq + dynmatcc`
- `/root/q-e/PHonon/PH/rigid.f90` — LO-TO splitting: non-analytic term `4πe²/Ω · (q·Z*)(Z*·q) / (q·ε∞·q)`
- `/root/q-e/LR_Modules/dv_of_drho.f90` — Response potential: `ΔV_H(G) = 4πe²·Δρ(G)/|q+G|²`
- `/root/q-e/LR_Modules/cgsolve_all.f90` — CG convergence: `||r|| < ethr` per band

### ABACUS Target — Existing Conventions

**ABACUS unit system** (`/root/abacus-dfpt/abacus-develop/`):
- Energy: Ry (same as QE)
- Length: Bohr (same as QE)
- Wavefunction: normalized in unit cell volume Ω
- Potential: Ry
- Charge density: e/Bohr³

**ABACUS DFPT parameters** (from `input_parameter.h`):
```cpp
bool dfpt_phonon = false;
int dfpt_nq1=1, dfpt_nq2=1, dfpt_nq3=1;
double dfpt_conv_thr = 1e-8;       // Ry²
int dfpt_max_iter = 100;
double dfpt_cg_thr = 1e-10;
int dfpt_max_cg_iter = 50;
std::string dfpt_mixing = "broyden";
double dfpt_mixing_beta = 0.7;
```

### dvqpsi_cpp Reference — Algorithm Patterns

**Algorithm checklist from dvqpsi_cpp** (`/root/q-e/PHonon/dvqpsi_cpp/`):
- `dvqpsi_us.hpp`: Local potential derivative uses structure factor derivative `dS/dτ = i(q+G)·u · S(q+G)`
- `sternheimer_solver.hpp`: Projector parameter `alpha_pv = 0.3` (QE uses adaptive value)
- `preconditioner.hpp`: Diagonal preconditioning `h_diag(G,n) = 1.0 / max(1.0, |k+q+G|² - ε_n)`
- `potential_mixer.hpp`: Broyden mixing with history (QE: `nmix_ph` previous iterations)
- `xc_functional.hpp`: LDA Perdew-Zunger parametrization (GGA not yet implemented)

## Implementation Guide

### Deliverable: `domain-knowledge/abacus-dfpt.md`

The document must cover these 6 dimensions:

#### 1. DFPT Unit System Table (≥15 quantities)

| Quantity | Symbol | Unit (QE/ABACUS) | Conversion | Ref |
|----------|--------|-------------------|------------|-----|
| Energy | E | Ry | 1 Ry = 13.6057 eV | [REF-DF01] |
| Length | a | Bohr | 1 Bohr = 0.529177 Å | [REF-DF01] |
| Wavefunction | ψ | Ω^(-1/2) | normalized in cell | [REF-DF02] |
| Potential | V | Ry | | [REF-DF02] |
| Charge density | ρ | e/Bohr³ | | [REF-DF02] |
| Force constant | C(κα,κ'β) | Ry/Bohr² | | [REF-DF03] |
| Dynamical matrix | D(κα,κ'β) | Ry/Bohr²/amu | C/(M_κ·M_κ')^(1/2) | [REF-DF03] |
| Phonon frequency | ω | cm⁻¹ | ω² in Ry²·amu⁻¹ | [REF-DF03] |
| Born effective charge | Z* | |e| | dimensionless | [REF-DF04] |
| Dielectric constant | ε∞ | dimensionless | | [REF-DF04] |
| EPC matrix element | g | Ry | | [REF-DF05] |
| EPC constant | λ | dimensionless | | [REF-DF05] |
| Response wavefunction | Δψ | Ω^(-1/2)·Bohr | per displacement | [REF-DF06] |
| Response density | Δρ | e/Bohr³/Bohr | per displacement | [REF-DF06] |
| Response potential | ΔV | Ry/Bohr | per displacement | [REF-DF06] |
| Eliashberg function | α²F(ω) | dimensionless | | [REF-DF05] |

#### 2. Physical Constraints Checklist

Each constraint must have a code evidence reference:

- **[PC-01] Acoustic sum rule**: `Σ_κ' D(κα,κ'β;q=0) = 0`
  - QE: `set_asr_c()` in `dynmatrix.f90`, `q2r.f90`
  - ABACUS: Must enforce after dynamical matrix assembly

- **[PC-02] Hermiticity**: `D(κα,κ'β;q) = D*(κ'β,κα;-q)`
  - QE: `symdynph_gq.f90` line ~120
  - ABACUS: Enforce in symmetrization step

- **[PC-03] Charge neutrality**: `Σ_κ Z*_κ,αβ = Z_total · δ_αβ`
  - QE: Checked in `zstar_eu.f90`

- **[PC-04] ε∞ symmetry**: `ε_αβ = ε_βα`
  - QE: Symmetrized in `dielec.f90`

- **[PC-05] Translational invariance**: Uniform displacement → zero force
  - QE: Enforced via acoustic sum rule

- **[PC-06] Sternheimer orthogonality**: `⟨ψ_m|Δψ_n⟩ = 0` for occupied m
  - QE: `orthogonalize()` in `response_kernels.f90`
  - dvqpsi_cpp: `orthogonalize_to_valence()` in `diago_cg_lr.h`

#### 3. Algorithm Adaptation Checklist

- **[AA-01] Sternheimer convergence**: Adaptive threshold `thresh = min(0.1*dr2, 1e-2)` in QE
- **[AA-02] Preconditioning**: `h_diag(G,n) = 1/max(1.0, |k+q+G|² - ε_n)` — must use k+q, not k
- **[AA-03] SCF mixing**: Broyden with `nmix_ph` history; `alpha_mix` adaptive
- **[AA-04] Metallic systems**: Fermi energy shift `Δε_F` at q=0 (QE: `ef_shift_new`)
- **[AA-05] Ultrasoft PP**: Additional terms `int1..int5` for augmentation charges
- **[AA-06] Noncollinear**: Double solve with time-reversal (`nsolv=2`)

#### 4. QE PHonon Module Mapping (≥20 files)

| QE File | Purpose | ABACUS Equivalent | Priority |
|---------|---------|-------------------|----------|
| `phonon.f90` | Main entry | `esolver_ks_pw_dfpt.cpp` | P0 |
| `solve_linter.f90` | Linear response driver | `dfpt_scf_loop()` | P0 |
| `dfpt_kernels.f90` | DFPT SCF loop | `dfpt_scf_loop()` | P0 |
| `response_kernels.f90` | Sternheimer wrapper | `solve_sternheimer()` | P0 |
| `cgsolve_all.f90` | CG solver | `diago_cg_lr.h` | P0 |
| `dv_of_drho.f90` | Response potential | `compute_dvscf()` | P0 |
| `dvqpsi_us.f90` | dV·ψ kernel | `dvloc_pw.h` + `dvqpsi_cpp` | P0 |
| `phcom.f90` | Data structures | `dfpt_types.h` | P0 |
| `dynmat0.f90` | Bare dynamical matrix | `dynmat.cpp` | P1 |
| `dynmatrix.f90` | Full dynamical matrix | `dynmat.cpp` | P1 |
| `d2ionq.f90` | Ionic contribution | `dynmat.cpp` | P1 |
| `rigid.f90` | LO-TO splitting | `dynmat.cpp` | P1 |
| `elphon.f90` | Electron-phonon | `elphon.cpp` | P2 |
| `set_irr.f90` | Irrep setup | `symmetry_dfpt.cpp` | P2 |
| `symdynph_gq.f90` | Dyn matrix symmetrize | `symmetry_dfpt.cpp` | P2 |
| `q2r.f90` | Q→R transform | `postprocess/q2r.cpp` | P2 |
| `matdyn.f90` | Phonon dispersion | `postprocess/matdyn.cpp` | P2 |
| `phescf.f90` | Electric field response | `esolver_dfpt.cpp` | P2 |
| `dielec.f90` | Dielectric constant | `physics/dielectric.cpp` | P2 |
| `zstar_eu.f90` | Born effective charges | `physics/born_charge.cpp` | P2 |
| `phq_setup.f90` | Phonon setup | `before_dfpt()` | P0 |
| `phq_init.f90` | Phonon init | `before_dfpt()` | P0 |

#### 5. ABACUS DFPT Module Mapping (≥10 files)

| ABACUS File | Class/Function | Status |
|-------------|---------------|--------|
| `esolver_ks_pw_dfpt.h/cpp` | `ESolver_KS_PW_DFPT` | Exists |
| `hsolver_pw_dfpt.h/cpp` | `HSolverPW_DFPT` | Exists |
| `diago_cg_lr.h` | `DiagoCG_LR` | Exists |
| `hamilt_pw_dfpt.h/cpp` | `HamiltPW_DFPT` | Exists |
| `dvloc_pw.h/cpp` | `DVloc` | Exists |
| `dfpt_adapter.h/cpp` | `DFPTAdapter` | Exists |
| `dfpt_test_utils.h/cpp` | Test utilities | Exists |
| `input_parameter.h` | DFPT input params | Exists |
| `pot_xc_dfpt_test.cpp` | XC kernel tests | Exists |
| `nonlocal_pw_dfpt_test.cpp` | Nonlocal tests | Exists |

#### 6. Reference Evidence Codes

Each `[REF-DFxx]` code must point to a specific file and line range in either QE or ABACUS source.

## TDD Test Plan

### Tests to Write FIRST

1. **Domain knowledge loading test**:
   ```python
   def test_load_domain_knowledge():
       """Verify domain knowledge file can be loaded and parsed."""
       path = Path("domain-knowledge/abacus-dfpt.md")
       assert path.exists()
       content = path.read_text()
       # Must contain all 6 sections
       assert "Unit System" in content
       assert "Physical Constraints" in content
       assert "Algorithm Adaptation" in content
       assert "QE PHonon Module Mapping" in content
       assert "ABACUS DFPT Module Mapping" in content
       assert "Reference Evidence" in content
   ```

2. **Completeness validation test**:
   ```python
   def test_unit_table_completeness():
       """Verify unit table has ≥15 entries."""
       content = load_domain_knowledge()
       unit_rows = extract_table_rows(content, "Unit System")
       assert len(unit_rows) >= 15

   def test_qe_mapping_completeness():
       """Verify QE mapping has ≥20 files."""
       content = load_domain_knowledge()
       mapping_rows = extract_table_rows(content, "QE PHonon Module Mapping")
       assert len(mapping_rows) >= 20
   ```

3. **Reference code existence test**:
   ```python
   def test_reference_codes_exist():
       """Verify all [REF-DFxx] codes point to existing files."""
       content = load_domain_knowledge()
       refs = extract_ref_codes(content)
       for ref in refs:
           assert Path(ref.file_path).exists(), f"{ref.code}: {ref.file_path} not found"
   ```

## Acceptance Criteria

- [ ] `domain-knowledge/abacus-dfpt.md` covers all 6 review dimensions
- [ ] Unit system table has ≥15 physical quantities with correct units
- [ ] Physical constraints checklist has ≥6 constraints with `[REF-DFxx]` evidence
- [ ] Algorithm adaptation checklist has ≥6 items
- [ ] QE PHonon module mapping has ≥20 files with purpose and ABACUS equivalent
- [ ] ABACUS DFPT module mapping has ≥10 files with status
- [ ] Every `[REF-DFxx]` code points to a real file path and line range
- [ ] `load_domain_knowledge()` loading test passes
- [ ] Document is valid Markdown and renders correctly
