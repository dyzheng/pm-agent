# DFPT-002b: Write DFPT Review Prompts and Schema

## Objective

Create 6 DFPT-specific review agent prompts that enforce physics correctness, algorithm matching, and code quality during the migration. Each prompt produces machine-readable JSON findings that integrate with the existing code-review-agent infrastructure.

## Reference Code

### Existing Review Agent Infrastructure

**Code review agent** (`/root/code-review-agent/` — referenced in project request):
- 6-agent concurrent review system
- Each agent produces JSON output with `findings[]` array
- Finding schema: `{severity, category, file, line, message, suggestion}`
- Severity levels: `ERROR`, `WARNING`, `INFO`

### QE Source — What to Check Against

**Unit consistency** — QE uses Ry atomic units throughout:
- `/root/q-e/Modules/constants.f90`: `e2=2.0`, `fpi=4π`, `tpiba=2π/alat`
- Common mistake: mixing Hartree and Rydberg (factor of 2 errors)
- Common mistake: forgetting `tpiba` or `tpiba2` in G-vector operations

**Physics conservation** — Key invariants:
- `/root/q-e/LR_Modules/response_kernels.f90`: Orthogonality `⟨ψ_m|Δψ_n⟩ = 0`
- `/root/q-e/PHonon/PH/dynmatrix.f90`: Acoustic sum rule enforcement
- `/root/q-e/PHonon/PH/rigid.f90`: LO-TO splitting formula

**Algorithm matching** — QE reference implementations:
- `/root/q-e/LR_Modules/cgsolve_all.f90`: CG algorithm with preconditioning
- `/root/q-e/LR_Modules/dfpt_kernels.f90`: SCF loop with adaptive threshold
- `/root/q-e/LR_Modules/dv_of_drho.f90`: Hartree + XC response potential

### ABACUS Target — Existing Patterns

**Code style** (`/root/abacus-dfpt/abacus-develop/`):
- Template pattern: `template <typename T, typename Device = base_device::DEVICE_CPU>`
- Operator chain: `OperatorPW` base class with `act()` method
- Naming: `snake_case` for functions, `CamelCase` for classes
- Headers: `.h` extension, implementations: `.cpp`

**DFPT-specific patterns**:
- `dvloc_pw.h`: Operator inherits from `OperatorPW`, implements `act()`
- `dfpt_adapter.h`: Conversion functions `convert_*()` and `update_*()`
- `diago_cg_lr.h`: Function types `hpsi_func_type`, `spsi_func_type`

## Implementation Guide

### 6 Review Prompts to Create

Each prompt has two versions:
- `.agent.md` — Machine-readable, produces pure JSON output
- `.md` — Human-readable, usable as Claude Code slash command

#### 1. `review-dfpt-units`

**Purpose**: Check unit consistency in DFPT code

**Check items** (≥5):
- [ ] Energy quantities use Ry (not Hartree, not eV)
- [ ] G-vector operations include `tpiba` / `tpiba2` factors
- [ ] Structure factor uses correct phase convention `e^{i(q+G)·τ}`
- [ ] Hartree potential has correct prefactor `4πe²/|q+G|²` where `e2=2.0`
- [ ] Dynamical matrix elements have correct mass normalization `1/√(M_κ·M_κ')`
- [ ] Phonon frequencies converted correctly: `ω(cm⁻¹) = √(ω²) × RY_TO_CMM1`

**Example finding**:
```json
{
  "severity": "ERROR",
  "category": "unit-consistency",
  "file": "dvloc_pw.cpp",
  "line": 45,
  "message": "Missing tpiba factor in G-vector magnitude calculation",
  "suggestion": "Use g2 = gg[ig] * tpiba2 instead of gg[ig]"
}
```

#### 2. `review-dfpt-physics`

**Purpose**: Check physics conservation laws

**Check items** (≥5):
- [ ] Sternheimer solution orthogonal to occupied states
- [ ] Acoustic sum rule enforced on dynamical matrix
- [ ] Hermiticity of dynamical matrix maintained
- [ ] Charge conservation in response density
- [ ] Correct treatment of q=0 limit (G=0 term excluded in Hartree)
- [ ] Born effective charge sum rule checked

#### 3. `review-dfpt-algorithm`

**Purpose**: Check algorithm correctness vs QE reference

**Check items** (≥5):
- [ ] CG solver matches `cgsolve_all.f90` algorithm (gradient, preconditioning, line search)
- [ ] Preconditioning formula uses k+q (not just k): `1/max(1, |k+q+G|² - ε_n)`
- [ ] SCF mixing uses correct Broyden update formula
- [ ] Convergence threshold is adaptive: `thresh = min(0.1*dr2, initial_thresh)`
- [ ] Projector `P_c^+` applied before CG solve (not after)
- [ ] Metal systems: Fermi energy shift included at q=0

#### 4. `review-dfpt-style`

**Purpose**: Check DFPT naming conventions and code structure

**Check items** (≥5):
- [ ] DFPT classes follow ABACUS template pattern `<T, Device>`
- [ ] Operators inherit from `OperatorPW` and implement `act()`
- [ ] File naming follows `module_dfpt/` convention
- [ ] Physical quantities named consistently with QE (dvscf, dpsi, drho)
- [ ] No raw pointers where `std::unique_ptr` or `std::vector` suffices

#### 5. `review-dfpt-callchain`

**Purpose**: Track physical quantity flow through call chain

**Check items** (≥5):
- [ ] `dvbare` (bare perturbation) flows correctly: `DVloc::act() → dvpsi`
- [ ] `dvscf` (SCF response) flows: `compute_dvscf() → HamiltPW_DFPT → Sternheimer`
- [ ] `dpsi` (wavefunction response) flows: `Sternheimer → compute_drho()`
- [ ] `drho` (density response) flows: `compute_drho() → compute_dvscf()`
- [ ] Dynamical matrix accumulation: `drho × dvbare → dyn_mat`

#### 6. `review-dfpt-debug`

**Purpose**: Check defensive programming for numerical stability

**Check items** (≥5):
- [ ] Division by `|q+G|²` protected against G=0 singularity
- [ ] CG solver has maximum iteration guard
- [ ] SCF loop has maximum iteration guard with warning
- [ ] Eigenvalue differences `ε_n - ε_m` protected against degeneracy
- [ ] FFT grid dimensions validated before allocation
- [ ] NaN/Inf checks on convergence metric `dr2`

### JSON Output Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "agent": {"type": "string"},
    "status": {"enum": ["ok", "warning", "error"]},
    "findings": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["severity", "category", "file", "message"],
        "properties": {
          "severity": {"enum": ["ERROR", "WARNING", "INFO"]},
          "category": {"type": "string"},
          "file": {"type": "string"},
          "line": {"type": "integer"},
          "message": {"type": "string"},
          "suggestion": {"type": "string"},
          "qe_reference": {"type": "string"}
        }
      }
    }
  }
}
```

## TDD Test Plan

### Tests to Write FIRST

1. **Prompt format validation**:
   ```python
   def test_agent_prompt_format():
       """Each .agent.md must produce valid JSON output."""
       for prompt_file in glob("prompts/review-dfpt-*.agent.md"):
           content = Path(prompt_file).read_text()
           assert "findings" in content
           assert "severity" in content
           assert "JSON" in content

   def test_slash_command_format():
       """Each .md must be usable as slash command."""
       for cmd_file in glob(".claude/commands/review-dfpt-*.md"):
           content = Path(cmd_file).read_text()
           assert len(content) > 100  # Non-trivial content
   ```

2. **Check item count validation**:
   ```python
   def test_minimum_check_items():
       """Each prompt must have ≥5 DFPT-specific checks."""
       for prompt_file in glob("prompts/review-dfpt-*.agent.md"):
           content = Path(prompt_file).read_text()
           checks = re.findall(r'\[[ x]\]', content)
           assert len(checks) >= 5, f"{prompt_file}: only {len(checks)} checks"
   ```

3. **Manual validation with dvqpsi_cpp**:
   ```bash
   # Run review-dfpt-units on a known file
   # Expected: at least 1 finding (INFO or higher)
   claude review-dfpt-units source/module_dfpt/dvloc_pw.cpp
   ```

## Acceptance Criteria

- [ ] 6 `.agent.md` prompts created in `prompts/` directory
- [ ] 6 `.md` slash commands created in `.claude/commands/`
- [ ] Each prompt has ≥5 DFPT-specific check items
- [ ] JSON output schema defined and compatible with `finding.schema.json`
- [ ] Manual test with `dvqpsi_cpp/dvqpsi_us.cpp` produces correct output format
- [ ] All prompts reference specific QE source files as evidence
- [ ] Prompts cover all 6 dimensions: units, physics, algorithm, style, callchain, debug
