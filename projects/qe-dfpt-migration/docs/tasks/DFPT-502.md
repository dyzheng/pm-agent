# DFPT-502: Write User Documentation

## Objective

Write comprehensive user documentation that enables ABACUS users to perform phonon calculations using the new DFPT module, including input parameter reference, step-by-step tutorials, example calculations, FAQ, and a migration guide for users coming from QE PHonon.

## Reference Code

### QE Documentation Reference

**QE PHonon user guide** (`/root/q-e/PHonon/Doc/`):
- `user_guide.pdf` — Comprehensive user manual (~50 pages)
- `INPUT_PH.html` — Complete input parameter reference with defaults and descriptions
- `INPUT_PH.txt` — Plain text version of input reference

**QE PHonon examples** (`/root/q-e/PHonon/examples/`):
- 19 example directories covering various use cases
- Each has `run_example` script and `README`
- Covers: basic phonon, dispersion, metals, polar materials, EPC, Raman, etc.

**QE input parameter structure** (`/root/q-e/PHonon/PH/phq_readin.f90`):
```fortran
! Key parameters users need to know:
NAMELIST /INPUTPH/
  tr2_ph          ! SCF convergence threshold (default 1e-12)
  niter_ph        ! Max DFPT iterations (default 100)
  alpha_mix(1)    ! Mixing parameter (default 0.7)
  nmix_ph         ! Broyden history (default 4)
  ldisp           ! .true. for phonon dispersion on grid
  nq1, nq2, nq3  ! Q-point grid dimensions
  epsil           ! .true. to compute dielectric constant
  zeu             ! .true. to compute Born effective charges
  zue             ! .true. for Z* from phonon perturbation
  elph            ! .true. for electron-phonon coupling
  trans           ! .true. for phonon calculation (default .true.)
  recover         ! .true. to restart interrupted calculation
  fildyn          ! Output dynamical matrix file prefix
  fildvscf        ! Output response potential (for EPC)
  start_q, last_q ! Q-point range (for partial calculations)
  start_irr, last_irr ! Irrep range
```

### ABACUS Target — Existing Documentation Patterns

**ABACUS documentation structure** (`/root/abacus-dfpt/abacus-develop/docs/`):
- Input parameter documentation with type, default, description
- Example calculations with INPUT/STRU/KPT files
- Step-by-step tutorials

**ABACUS DFPT input parameters** (from `input_parameter.h`):
```cpp
bool dfpt_phonon = false;           // Enable DFPT phonon calculation
int dfpt_nq1 = 1;                   // Q-point grid dimension 1
int dfpt_nq2 = 1;                   // Q-point grid dimension 2
int dfpt_nq3 = 1;                   // Q-point grid dimension 3
double dfpt_conv_thr = 1e-8;        // DFPT convergence threshold
int dfpt_max_iter = 100;            // Maximum DFPT iterations
double dfpt_cg_thr = 1e-10;         // CG solver threshold
int dfpt_max_cg_iter = 50;          // Maximum CG iterations
std::string dfpt_mixing = "broyden"; // Mixing scheme
double dfpt_mixing_beta = 0.7;      // Mixing parameter
bool dfpt_epsil = false;            // Compute dielectric constant
bool dfpt_zeu = false;              // Compute Born effective charges
bool dfpt_elph = false;             // Compute electron-phonon coupling
bool dfpt_recover = false;          // Restart from checkpoint
std::string dfpt_fildyn = "dynmat"; // Dynamical matrix output prefix
std::string dfpt_asr = "crystal";   // Acoustic sum rule type
```

## Implementation Guide

### Document Structure

Create the following documentation files:

#### 1. `docs/DFPT_USER_GUIDE.md` — Main User Manual

```markdown
# ABACUS DFPT Phonon Calculation User Guide

## Overview
- What DFPT calculates (phonon frequencies, dynamical matrix, dielectric properties, EPC)
- When to use DFPT vs finite-difference
- Computational cost considerations

## Quick Start
- Minimal example: Si phonon at Gamma
- Step-by-step: prepare input → run → analyze output

## Input Parameters
- Complete parameter reference table
- Grouped by category: basic, convergence, parallelization, output, advanced

## Workflow
### Basic Phonon Calculation
1. Prepare ground-state input (INPUT, STRU, KPT, pseudopotentials)
2. Add DFPT parameters to INPUT
3. Run calculation
4. Analyze output (frequencies, dynamical matrix)

### Phonon Dispersion
1. Choose q-point grid
2. Run DFPT on grid
3. Post-process: q2r → matdyn → band structure plot

### Dielectric Properties (Polar Materials)
1. Enable epsil and zeu
2. Run at Gamma point
3. Extract ε∞ and Z*
4. Use for LO-TO correction in dispersion

### Electron-Phonon Coupling
1. Run DFPT with elph enabled
2. Use dense k-grid
3. Extract λ, α²F, Tc

### Restart/Checkpoint
1. Enable dfpt_recover
2. Interrupted calculation resumes automatically
3. Partial q-point range with start_q/last_q

## Parallelization Guide
- K-point pools: `-nk` flag
- Q-point images: `-ni` flag
- Recommended settings for different system sizes
- Memory considerations

## Output Files
- Dynamical matrix files (format description)
- Phonon frequency output
- Force constant files
- Phonon band structure data
- DOS data

## Troubleshooting / FAQ
- "DFPT SCF not converging" → adjust mixing, threshold
- "Negative frequencies" → check structure optimization, ASR
- "LO-TO splitting missing" → enable epsil/zeu
- "Memory issues" → reduce k-grid, use more pools
- Comparison with QE: parameter mapping table
```

#### 2. `docs/DFPT_INPUT_PARAMETERS.md` — Complete Parameter Reference

For each parameter, document:

| Parameter | Type | Default | Description | QE Equivalent |
|-----------|------|---------|-------------|---------------|
| `dfpt_phonon` | bool | false | Enable DFPT phonon calculation | `trans` |
| `dfpt_nq1` | int | 1 | Q-grid dimension along b1 | `nq1` |
| `dfpt_nq2` | int | 1 | Q-grid dimension along b2 | `nq2` |
| `dfpt_nq3` | int | 1 | Q-grid dimension along b3 | `nq3` |
| `dfpt_conv_thr` | double | 1e-8 | SCF convergence threshold (Ry²) | `tr2_ph` |
| `dfpt_max_iter` | int | 100 | Maximum DFPT SCF iterations | `niter_ph` |
| `dfpt_cg_thr` | double | 1e-10 | CG solver convergence threshold | (internal) |
| `dfpt_max_cg_iter` | int | 50 | Maximum CG iterations per band | (internal) |
| `dfpt_mixing` | string | "broyden" | Mixing scheme: "broyden" or "plain" | (always Broyden in QE) |
| `dfpt_mixing_beta` | double | 0.7 | Mixing parameter | `alpha_mix(1)` |
| `dfpt_epsil` | bool | false | Compute dielectric constant ε∞ | `epsil` |
| `dfpt_zeu` | bool | false | Compute Born effective charges Z* | `zeu` |
| `dfpt_elph` | bool | false | Compute electron-phonon coupling | `elph` |
| `dfpt_recover` | bool | false | Restart from checkpoint | `recover` |
| `dfpt_fildyn` | string | "dynmat" | Dynamical matrix output prefix | `fildyn` |
| `dfpt_asr` | string | "crystal" | Acoustic sum rule: "no", "simple", "crystal" | `asr` (in q2r/matdyn) |
| `dfpt_start_q` | int | 1 | First q-point to compute | `start_q` |
| `dfpt_last_q` | int | 0 | Last q-point (0 = all) | `last_q` |

#### 3. `examples/dfpt_*/` — Example Calculations

Each example directory contains:
```
examples/dfpt_si_gamma/
├── INPUT                    # ABACUS input file
├── STRU                     # Structure file
├── KPT                      # K-point file
├── Si_ONCV_PBE-1.0.upf     # Pseudopotential
├── run.sh                   # Run script
├── expected_output.txt      # Expected frequencies
└── README.md                # Step-by-step explanation
```

**Example 1: Si Gamma phonon** (simplest case)
```
# INPUT
INPUT_PARAMETERS
calculation     dfpt
pseudo_dir      ./
ntype           1
ecutwfc         60
scf_thr         1.0e-10
dfpt_phonon     1
dfpt_nq1        1
dfpt_nq2        1
dfpt_nq3        1
dfpt_conv_thr   1.0e-10
```

**Example 2: Si phonon dispersion** (full workflow)
```
# Step 1: DFPT on 4×4×4 q-grid
# Step 2: q2r to get force constants
# Step 3: matdyn to interpolate along Γ-X-W-L-Γ path
# Step 4: Plot phonon band structure
```

**Example 3: MgO with LO-TO** (polar material)
```
# Enable dielectric constant and Born charges
dfpt_epsil      1
dfpt_zeu        1
```

**Example 4: Al electron-phonon** (metal + EPC)
```
# Dense k-grid for Fermi surface sampling
dfpt_elph       1
# Smearing for metallic system
smearing_method gaussian
smearing_sigma  0.02
```

#### 4. QE → ABACUS Migration Guide

For users migrating from QE PHonon:

```markdown
## QE to ABACUS DFPT Migration Guide

### Input File Mapping

| QE (ph.x input) | ABACUS (INPUT) | Notes |
|-----------------|----------------|-------|
| `tr2_ph = 1.0d-12` | `dfpt_conv_thr 1.0e-12` | Same meaning |
| `niter_ph = 100` | `dfpt_max_iter 100` | Same meaning |
| `alpha_mix(1) = 0.7` | `dfpt_mixing_beta 0.7` | Same meaning |
| `ldisp = .true.` | `dfpt_nq1/2/3 > 1` | Implicit in grid size |
| `nq1=4, nq2=4, nq3=4` | `dfpt_nq1 4` etc. | Same meaning |
| `epsil = .true.` | `dfpt_epsil 1` | Same meaning |
| `zeu = .true.` | `dfpt_zeu 1` | Same meaning |
| `elph = .true.` | `dfpt_elph 1` | Same meaning |
| `recover = .true.` | `dfpt_recover 1` | Same meaning |
| `fildyn = 'dyn'` | `dfpt_fildyn dyn` | Same meaning |

### Workflow Differences
- QE: separate pw.x (SCF) + ph.x (DFPT) executables
- ABACUS: single executable, `calculation = "dfpt"` runs both SCF and DFPT
- QE: q2r.x and matdyn.x are separate programs
- ABACUS: integrated post-processing (or separate tools)

### Expected Differences
- Frequencies should agree within 0.5 cm⁻¹ for same pseudopotential and cutoff
- Iteration counts may differ slightly due to mixing implementation
- Output file formats differ (ABACUS uses XML, QE uses custom format)
```

## TDD Test Plan

### Tests to Write FIRST

```python
# test_documentation.py

def test_user_guide_exists():
    assert Path("docs/DFPT_USER_GUIDE.md").exists()
    content = Path("docs/DFPT_USER_GUIDE.md").read_text()
    assert len(content) > 5000  # substantial document

def test_input_parameters_complete():
    """All DFPT input parameters must be documented."""
    doc = Path("docs/DFPT_INPUT_PARAMETERS.md").read_text()
    required_params = [
        "dfpt_phonon", "dfpt_nq1", "dfpt_nq2", "dfpt_nq3",
        "dfpt_conv_thr", "dfpt_max_iter", "dfpt_mixing",
        "dfpt_epsil", "dfpt_zeu", "dfpt_elph", "dfpt_recover"
    ]
    for param in required_params:
        assert param in doc, f"Parameter {param} not documented"

def test_examples_runnable():
    """Each example must have INPUT, STRU, KPT, and pseudopotential."""
    for example_dir in glob("examples/dfpt_*/"):
        assert os.path.exists(os.path.join(example_dir, "INPUT"))
        assert os.path.exists(os.path.join(example_dir, "STRU"))
        assert os.path.exists(os.path.join(example_dir, "KPT"))
        upf_files = glob(os.path.join(example_dir, "*.upf")) + \
                    glob(os.path.join(example_dir, "*.UPF"))
        assert len(upf_files) > 0, f"No pseudopotential in {example_dir}"

def test_examples_have_readme():
    """Each example must have README with explanation."""
    for example_dir in glob("examples/dfpt_*/"):
        readme = os.path.join(example_dir, "README.md")
        assert os.path.exists(readme), f"Missing README in {example_dir}"
        content = open(readme).read()
        assert len(content) > 200  # non-trivial explanation

def test_qe_migration_guide():
    """Migration guide must map all major QE parameters."""
    doc = Path("docs/DFPT_USER_GUIDE.md").read_text()
    assert "QE" in doc or "Quantum ESPRESSO" in doc
    assert "migration" in doc.lower() or "Migration" in doc

def test_example_calculations_reproducible():
    """Run each example and verify it produces expected output."""
    for example_dir in glob("examples/dfpt_*/"):
        if os.path.exists(os.path.join(example_dir, "run.sh")):
            ret = subprocess.run(["bash", "run.sh"], cwd=example_dir,
                                capture_output=True, timeout=300)
            assert ret.returncode == 0, f"Example {example_dir} failed"
```

## Acceptance Criteria

- [ ] User guide complete (`docs/DFPT_USER_GUIDE.md`, > 5000 words)
- [ ] Input parameter reference complete (all DFPT parameters documented)
- [ ] QE → ABACUS parameter mapping table included
- [ ] At least 4 example calculations with INPUT/STRU/KPT/pseudopotentials
- [ ] Each example has README with step-by-step explanation
- [ ] Example calculations are reproducible (run.sh succeeds)
- [ ] FAQ section covers common issues (convergence, negative frequencies, LO-TO)
- [ ] Parallelization guide with recommended settings
- [ ] Documentation review passes (clarity, completeness, accuracy)
