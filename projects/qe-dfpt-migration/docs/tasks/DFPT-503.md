# DFPT-503: Write Developer Documentation

## Objective

Write comprehensive developer documentation that enables future contributors to understand, maintain, and extend the DFPT module. This includes architecture deep-dive, algorithm implementation details, code review summary, performance analysis, and extension guidelines.

## Reference Code

### QE Developer Documentation

**QE developer manual** (`/root/q-e/PHonon/Doc/developer_man.pdf`):
- Module organization and dependencies
- Data flow through the phonon calculation
- How to add new perturbation types
- Debugging and testing guidelines

**QE code comments** — Key files with extensive inline documentation:
- `/root/q-e/LR_Modules/dfpt_kernels.f90` — Algorithm flow comments
- `/root/q-e/LR_Modules/response_kernels.f90` — Sternheimer equation derivation
- `/root/q-e/PHonon/PH/phcom.f90` — Data structure documentation

### ABACUS Target — Existing Developer Docs

**ABACUS developer patterns**:
- Template-based device abstraction (`<T, Device>`)
- Operator chain pattern (Hamiltonian composed of operators)
- ESolver hierarchy (ESolver → ESolver_KS → ESolver_KS_PW → ESolver_KS_PW_DFPT)
- Module organization (`source_*` directories)

**Existing DFPT documentation** in the codebase:
- `/root/abacus-dfpt/abacus-develop/DFPT_QUICK_REFERENCE.md`
- `/root/abacus-dfpt/abacus-develop/DFPT_IMPLEMENTATION_COMPLETE.md`
- `/root/abacus-dfpt/abacus-develop/DFPT_TESTING_PLAN.md`

### dvqpsi_cpp Documentation

**Algorithm documentation** (`/root/q-e/PHonon/dvqpsi_cpp/docs/`):
- `algorithm.md` — Mathematical derivation of DFPT equations
- `performance.md` — Performance analysis and optimization
- `elphon.md` — Electron-phonon coupling theory

## Implementation Guide

### Document Structure

#### 1. `docs/DFPT_DEVELOPER_GUIDE.md` — Main Developer Manual

```markdown
# ABACUS DFPT Module Developer Guide

## Architecture Overview
### Module Organization
- Directory structure and file naming conventions
- Dependency graph between DFPT sub-modules
- Integration points with ABACUS core modules

### Class Hierarchy
- ESolver_KS_PW_DFPT: lifecycle, data flow, key methods
- HamiltPW_DFPT: operator chain, perturbation handling
- HSolverPW_DFPT: Sternheimer equation, CG solver
- DiagoCG_LR: linear response CG algorithm

### Data Flow
- Ground-state → DFPT transition
- DFPT SCF loop: dvpsi → Sternheimer → dpsi → drho → dvscf → mix
- Dynamical matrix accumulation
- Post-processing pipeline

## Key Design Decisions
- Why inherit from ESolver_KS_PW (code reuse, ground-state infrastructure)
- Why use operator chain pattern (extensibility, GPU portability)
- Why sequential q-point processing (memory efficiency)
- Why Broyden mixing (faster convergence than plain mixing)
- Why dvqpsi_cpp adapter pattern (leverage existing tested kernel)

## Adding New Features
### Adding a New Perturbation Type
1. Create new operator class inheriting from OperatorPW
2. Implement act() method for the new perturbation
3. Register in HamiltPW_DFPT operator chain
4. Add input parameter for enabling the perturbation
5. Add tests

### Adding a New Post-Processing Tool
1. Create new class in physics/ or postprocess/
2. Implement computation from converged DFPT data
3. Add output file generation
4. Add integration test with QE reference

### Adding GPU Support
1. Specialize template for DEVICE_GPU
2. Use cuBLAS/cuFFT instead of BLAS/FFTW
3. Minimize host-device data transfer
4. Add GPU-specific tests

## Debugging Guide
- Common numerical issues and their causes
- How to enable verbose output for DFPT iterations
- How to compare intermediate quantities with QE
- How to use the 6-agent review system for code quality

## Testing Strategy
- Unit tests: individual components (operators, solvers, adapters)
- Integration tests: full DFPT workflow against QE reference
- Performance tests: timing and memory benchmarks
- Regression tests: prevent regressions in CI/CD
```

#### 2. `docs/DFPT_ALGORITHM_DETAILS.md` — Algorithm Deep-Dive

```markdown
# DFPT Algorithm Implementation Details

## Mathematical Foundation
### Density Functional Perturbation Theory
- First-order perturbation of Kohn-Sham equations
- Self-consistent response: ΔV_SCF = ΔV_H[Δρ] + ΔV_xc[Δρ]
- Sternheimer equation derivation

### Key Equations (with code references)
- Sternheimer: (H-ε+Q)Δψ = -P_c^+ ΔV ψ
  → Code: HSolverPW_DFPT::solve_dfpt()
- Charge response: Δρ = Σ_k w_k Σ_n [ψ*Δψ + c.c.]
  → Code: ESolver_KS_PW_DFPT::compute_drho()
- Hartree response: ΔV_H(G) = 4πe²Δρ(G)/|q+G|²
  → Code: ESolver_KS_PW_DFPT::compute_dvscf()
- XC response: ΔV_xc(r) = f_xc(r)·Δρ(r)
  → Code: ESolver_KS_PW_DFPT::compute_dvscf()
- Dynamical matrix: D = D_bare + D_SCF
  → Code: DynamicalMatrix::compute()

## Algorithm Implementation
### CG Solver (DiagoCG_LR)
- Preconditioned conjugate gradient algorithm
- Per-band convergence tracking
- Adaptive threshold from outer SCF loop
- BLAS-3 optimization for projector

### SCF Mixing
- Broyden mixing with configurable history
- Convergence metric: dr2 = ||ΔV_out - ΔV_in||²
- Adaptive mixing parameter

### Symmetry Operations
- Small group of q determination
- Dynamical matrix symmetrization
- Irreducible representation decomposition
- Star of q generation

### Ewald Summation
- Real-space and reciprocal-space contributions
- Ewald parameter optimization
- Convergence acceleration

## Numerical Considerations
- G=0 singularity in Hartree potential
- Acoustic sum rule enforcement strategies
- Metallic systems: Fermi energy shift
- Ultrasoft PP: augmentation charge terms
- Noncollinear magnetism: double solve with time-reversal

## QE ↔ ABACUS Algorithm Comparison
- Differences in implementation choices
- Convergence behavior comparison
- Numerical precision analysis
```

#### 3. `docs/DFPT_CODE_REVIEW_SUMMARY.md` — Code Review Report

```markdown
# DFPT Code Review Summary

## Review Methodology
- 6-agent concurrent review system
- Dimensions: units, physics, algorithm, style, callchain, debug
- 3-agent migration workflow for Fortran→C++ translation

## Review Results by Component
### DVQPsiUS Core Kernel
- Findings: [list from DFPT-002d review]
- Resolution status

### Sternheimer Solver
- Findings: [list]
- Resolution status

### DFPT SCF Loop
- Findings: [list]
- Resolution status

### Dynamical Matrix
- Findings: [list]
- Resolution status

## Common Issues Found
- Unit consistency issues and fixes
- Physics constraint violations and corrections
- Algorithm deviations from QE and justifications
- Code style improvements

## Recommendations for Future Development
- Areas needing additional review
- Known limitations
- Suggested improvements
```

#### 4. `docs/DFPT_EXTENSION_GUIDE.md` — Extension Guidelines

```markdown
# Extending the DFPT Module

## Adding Support for New Pseudopotential Types
### PAW (Projector Augmented Wave)
- Additional terms in DVQPsiUS
- Augmentation charge handling
- Reference: QE PAW phonon implementation

### Full-Relativistic (Spin-Orbit Coupling)
- 2-component spinor wavefunctions
- Modified Sternheimer equation
- Reference: QE noncollinear phonon

## Adding New Physical Properties
### Raman Tensor
- Second-order response to electric field
- Requires: converged first-order response
- Reference: QE raman_mat.f90

### Piezoelectric Tensor
- Strain perturbation
- Reference: QE stress response

### Thermal Conductivity
- Phonon-phonon scattering (third-order)
- Beyond current DFPT scope

## Performance Extensions
### GPU Acceleration
- cuFFT for FFT operations
- cuBLAS for linear algebra
- Device memory management
- Template specialization for DEVICE_GPU

### Hybrid MPI+OpenMP
- MPI for k-point/q-point distribution
- OpenMP for band-level parallelism
- Thread-safe data structures

## Integration with Other Codes
### Wannier90 Interface
- Electron-phonon coupling on Wannier basis
- EPW-like functionality

### ShengBTE Interface
- Third-order force constants
- Thermal conductivity calculation
```

### Writing Guidelines

1. **Code references**: Every algorithm description must reference the specific source file and function:
   ```markdown
   The Sternheimer equation is solved in `HSolverPW_DFPT::solve_dfpt()`
   (source/source_hsolver/hsolver_pw_dfpt.cpp:120).
   ```

2. **Equations with code mapping**: Show the mathematical equation and the corresponding code:
   ```markdown
   **Hartree response potential:**
   ΔV_H(G) = 4πe² · Δρ(G) / |q+G|²

   Implementation in `compute_dvscf()`:
   ```cpp
   dvh_g[ig] = e2 * fpi * drho_g[ig] / qpg2;  // e2=2.0 in Ry
   ```

3. **Diagrams**: Use ASCII art or Mermaid for architecture diagrams:
   ```
   ESolver_KS_PW_DFPT
   ├── HamiltPW_DFPT
   │   ├── DVloc (dV_loc/dτ · ψ)
   │   ├── DVnl  (dV_nl/dτ · ψ)
   │   └── DVscf (ΔV_SCF · ψ)
   ├── HSolverPW_DFPT
   │   └── DiagoCG_LR (CG solver)
   └── DynamicalMatrix
       ├── Ewald (ionic)
       └── SCF (electronic)
   ```

4. **Diff with QE**: Where ABACUS implementation differs from QE, explain why:
   ```markdown
   **Difference from QE:** QE uses global modules (phcom.f90) for DFPT data.
   ABACUS encapsulates all data in ESolver_KS_PW_DFPT class members.
   **Rationale:** Avoids global state, enables multiple DFPT instances,
   better suited for C++ object-oriented design.
   ```

## TDD Test Plan

### Tests to Write FIRST

```python
# test_developer_docs.py

def test_developer_guide_exists():
    assert Path("docs/DFPT_DEVELOPER_GUIDE.md").exists()
    content = Path("docs/DFPT_DEVELOPER_GUIDE.md").read_text()
    assert len(content) > 3000

def test_algorithm_details_exists():
    assert Path("docs/DFPT_ALGORITHM_DETAILS.md").exists()
    content = Path("docs/DFPT_ALGORITHM_DETAILS.md").read_text()
    assert len(content) > 3000

def test_code_review_summary_exists():
    assert Path("docs/DFPT_CODE_REVIEW_SUMMARY.md").exists()

def test_extension_guide_exists():
    assert Path("docs/DFPT_EXTENSION_GUIDE.md").exists()

def test_code_references_valid():
    """All file:line references in docs must point to existing code."""
    for doc_file in glob("docs/DFPT_*.md"):
        content = Path(doc_file).read_text()
        # Find patterns like "source/module_dfpt/foo.cpp:123"
        refs = re.findall(r'(source/\S+\.(?:cpp|h)):(\d+)', content)
        for filepath, line in refs:
            full_path = Path("/root/abacus-dfpt/abacus-develop") / filepath
            assert full_path.exists(), f"Referenced file {filepath} not found in {doc_file}"

def test_architecture_diagram_present():
    """Developer guide must contain architecture diagram."""
    content = Path("docs/DFPT_DEVELOPER_GUIDE.md").read_text()
    assert "ESolver" in content
    assert "Hamilt" in content
    assert "HSolver" in content

def test_algorithm_equations_present():
    """Algorithm doc must contain key DFPT equations."""
    content = Path("docs/DFPT_ALGORITHM_DETAILS.md").read_text()
    assert "Sternheimer" in content
    assert "Hartree" in content
    assert "dynamical matrix" in content.lower()
```

## Acceptance Criteria

- [ ] Developer guide complete (`docs/DFPT_DEVELOPER_GUIDE.md`)
- [ ] Algorithm details complete (`docs/DFPT_ALGORITHM_DETAILS.md`)
- [ ] Code review summary complete (`docs/DFPT_CODE_REVIEW_SUMMARY.md`)
- [ ] Extension guide complete (`docs/DFPT_EXTENSION_GUIDE.md`)
- [ ] All code references point to existing files
- [ ] Architecture diagram included (class hierarchy + data flow)
- [ ] Key equations mapped to code locations
- [ ] QE ↔ ABACUS implementation differences documented
- [ ] Extension guidelines cover: PAW, GPU, new properties
- [ ] Documentation review passes (technical accuracy, completeness)
