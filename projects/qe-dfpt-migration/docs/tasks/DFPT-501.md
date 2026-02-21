# DFPT-501: Create Integration Test Suite

## Objective

Create a comprehensive integration test suite that validates the entire DFPT module against QE PHonon reference results for representative physical systems. Tests cover insulators, metals, polar materials, and electron-phonon coupling, integrated into the abacustest framework for CI/CD.

## Reference Code

### QE Reference Data Generation

**QE test systems** (`/root/q-e/PHonon/examples/`):
- `example01/` — Si phonon dispersion (semiconductor, 2 atoms)
- `example02/` — Al phonon + electron-phonon (simple metal, 1 atom)
- `example03/` — Cu phonon (FCC metal)
- `example04/` — Ni phonon (magnetic metal)
- `example06/` — AlAs phonon (polar semiconductor, LO-TO splitting)
- `example07/` — BN phonon (polar insulator)
- `example12/` — SiC phonon + electron-phonon
- `example14/` — MgB₂ electron-phonon (superconductor)

**Generating QE reference data**:
```bash
# Si phonon at Gamma
cd /root/q-e/PHonon/examples/example01
pw.x < si.scf.in > si.scf.out          # ground-state SCF
ph.x < si.ph.in > si.ph.out            # DFPT phonon
# Extract: phonon frequencies, dynamical matrix, dielectric constant

# Al electron-phonon
cd /root/q-e/PHonon/examples/example02
pw.x < al.scf.in > al.scf.out
ph.x < al.ph.in > al.ph.out
# Extract: phonon frequencies, linewidths, λ
```

### ABACUS Test Infrastructure

**abacustest framework** (`/root/abacus-test/`):
```python
# abacustest provides:
# - Test case management (INPUT, STRU, KPT, pseudopotentials)
# - Result extraction (energy, forces, stress, custom quantities)
# - Comparison with reference data
# - CI/CD integration (GitHub Actions, Jenkins)
```

**Existing ABACUS test structure** (`/root/abacus-dfpt/abacus-develop/tests/`):
```
tests/
├── integrate/
│   ├── 101_PW_Si_scf/          # Ground-state SCF tests
│   ├── 102_PW_Si_nscf/         # NSCF tests
│   └── ...
├── unit/
│   └── ...                      # GoogleTest unit tests
└── CASES.txt                    # Test case registry
```

**DFPT-specific test utilities** (`/root/abacus-dfpt/abacus-develop/source/source_pw/module_pwdft/operator_pw/test/dfpt_test_utils.h`):
```cpp
// Existing utilities:
void create_random_wavefunction(/* ... */);
void create_test_potential(/* ... */);
void compare_complex_arrays(const std::complex<double>* a, const std::complex<double>* b,
                            int n, double tol);
double relative_error(const std::complex<double>* a, const std::complex<double>* b, int n);
```

## Implementation Guide

### Test Case Design

Each integration test case consists of:
```
tests/integrate/dfpt_{system}_{property}/
├── INPUT                    # ABACUS input file
├── STRU                     # Structure file
├── KPT                      # K-point file
├── *.upf                    # Pseudopotential files
├── reference/
│   ├── phonon_freq.dat      # QE reference frequencies (cm⁻¹)
│   ├── dynmat.xml           # QE reference dynamical matrix
│   ├── dielectric.dat       # QE reference ε∞ (if applicable)
│   ├── born_charges.dat     # QE reference Z* (if applicable)
│   ├── elph_lambda.dat      # QE reference λ (if applicable)
│   └── qe_output.log        # Full QE output for reference
├── result_check.py          # Automated comparison script
└── README.md                # Test description and expected results
```

### Test Cases (≥10)

#### 1. Si Gamma Phonon (Basic Insulator)
```
System: Si, diamond structure, 2 atoms
Pseudopotential: Si.pbe-n-rrkjus_psl.1.0.0.UPF (USPP)
K-grid: 8×8×8, Q-point: Gamma only
Cutoff: 30 Ry
Expected: 3 acoustic (0 cm⁻¹) + 3 optical (~520 cm⁻¹)
Tolerance: < 0.1 cm⁻¹ vs QE
```

INPUT:
```
INPUT_PARAMETERS
calculation     dfpt
pseudo_dir      ./
ntype           1
ecutwfc         30
scf_thr         1.0e-10
dfpt_phonon     1
dfpt_nq1        1
dfpt_nq2        1
dfpt_nq3        1
dfpt_conv_thr   1.0e-10
```

#### 2. Si Phonon Dispersion (Full Q-grid)
```
System: Si, 2 atoms
Q-grid: 4×4×4 (8 irreducible q-points)
Expected: Full phonon band structure
Tolerance: < 0.5 cm⁻¹ at all q-points
Post-processing: q2r → matdyn → band structure
```

#### 3. Al Gamma Phonon (Simple Metal)
```
System: Al, FCC, 1 atom
K-grid: 16×16×16 (dense for metal)
Q-point: Gamma
Smearing: Methfessel-Paxton, σ = 0.05 Ry
Expected: 3 acoustic modes (0 cm⁻¹ at Gamma)
Tests: Fermi energy shift handling, metallic screening
```

#### 4. MgO Phonon (Polar Insulator, LO-TO)
```
System: MgO, rocksalt, 2 atoms
Q-point: Gamma
Expected: LO-TO splitting (~400 vs ~700 cm⁻¹)
Tests: Dielectric constant ε∞, Born effective charges Z*
Tolerance: ε∞ within 2%, Z* within 1%, frequencies < 1 cm⁻¹
```

#### 5. GaAs Phonon (Polar Semiconductor)
```
System: GaAs, zincblende, 2 atoms
Q-grid: 4×4×4
Expected: LO-TO splitting, correct acoustic/optical branches
Tests: Non-analytic correction, polar material handling
```

#### 6. BaTiO₃ Phonon (Perovskite, 5 atoms)
```
System: BaTiO₃, cubic perovskite, 5 atoms
Q-point: Gamma
Expected: 15 modes (3 acoustic + 12 optical)
Tests: Multi-atom system, larger dynamical matrix (15×15)
Tolerance: < 2 cm⁻¹ vs QE
```

#### 7. Si with NCPP (Norm-Conserving PP)
```
System: Si, 2 atoms
Pseudopotential: Si.pbe-n-kjpaw_psl.1.0.0.UPF (NC)
Tests: Verify NCPP path (no augmentation terms)
Expected: Same frequencies as USPP (within 5 cm⁻¹)
```

#### 8. Al Electron-Phonon Coupling
```
System: Al, 1 atom
Q-grid: 4×4×4, dense K-grid: 24×24×24
Expected: λ ≈ 0.44, Tc ≈ 1.2 K
Tolerance: λ within 10%, Tc within 50%
Tests: EPC matrix elements, linewidths, Eliashberg function
```

#### 9. Si Phonon with MPI Parallelization
```
System: Si, 2 atoms
Run with: 1, 2, 4 MPI ranks
Expected: Identical results regardless of parallelization
Tolerance: < 1e-10 between serial and parallel
Tests: MPI correctness, not performance
```

#### 10. Si Phonon Restart
```
System: Si, 2 atoms, 4×4×4 q-grid
Procedure:
  1. Run first 4 q-points, interrupt
  2. Restart, complete remaining q-points
  3. Compare with uninterrupted run
Expected: Identical results
Tests: Checkpoint/restart mechanism
```

### Comparison Script Template

```python
#!/usr/bin/env python3
"""result_check.py — Compare ABACUS DFPT results with QE reference."""

import numpy as np
import json
import sys

def load_phonon_frequencies(filename):
    """Load phonon frequencies from output file."""
    # Parse ABACUS output format
    freqs = []
    with open(filename) as f:
        for line in f:
            if "cm-1" in line or "cm^-1" in line:
                freq = float(line.split()[-2])  # adjust parsing
                freqs.append(freq)
    return np.array(sorted(freqs))

def load_qe_reference(filename):
    """Load QE reference frequencies."""
    return np.loadtxt(filename)

def compare_frequencies(abacus_freq, qe_freq, tol_cm):
    """Compare phonon frequencies."""
    assert len(abacus_freq) == len(qe_freq), \
        f"Mode count mismatch: {len(abacus_freq)} vs {len(qe_freq)}"

    max_error = 0
    for i, (a, q) in enumerate(zip(abacus_freq, qe_freq)):
        error = abs(a - q)
        max_error = max(max_error, error)
        status = "PASS" if error < tol_cm else "FAIL"
        print(f"  Mode {i+1}: ABACUS={a:.2f} QE={q:.2f} Δ={error:.4f} cm⁻¹ [{status}]")

    return max_error < tol_cm, max_error

def compare_dielectric(abacus_eps, qe_eps, tol_percent):
    """Compare dielectric tensor."""
    rel_error = np.abs(abacus_eps - qe_eps) / np.abs(qe_eps) * 100
    max_rel_error = np.max(rel_error)
    return max_rel_error < tol_percent, max_rel_error

def main():
    test_dir = sys.argv[1] if len(sys.argv) > 1 else "."

    results = {"passed": 0, "failed": 0, "tests": []}

    # Test 1: Phonon frequencies
    abacus_freq = load_phonon_frequencies(f"{test_dir}/phonon_frequencies.dat")
    qe_freq = load_qe_reference(f"{test_dir}/reference/phonon_freq.dat")
    passed, max_err = compare_frequencies(abacus_freq, qe_freq, tol_cm=0.5)
    results["tests"].append({
        "name": "phonon_frequencies",
        "passed": passed,
        "max_error_cm": max_err
    })

    # Test 2: Dielectric constant (if applicable)
    # Test 3: Born effective charges (if applicable)
    # Test 4: EPC lambda (if applicable)

    # Summary
    for t in results["tests"]:
        if t["passed"]:
            results["passed"] += 1
        else:
            results["failed"] += 1

    print(f"\nResults: {results['passed']} passed, {results['failed']} failed")
    with open(f"{test_dir}/test_results.json", "w") as f:
        json.dump(results, f, indent=2)

    return 0 if results["failed"] == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
```

### CI/CD Integration

```yaml
# .github/workflows/dfpt_tests.yml
name: DFPT Integration Tests

on:
  push:
    paths: ['source/module_dfpt/**', 'tests/integrate/dfpt_*/**']
  pull_request:
    paths: ['source/module_dfpt/**']

jobs:
  dfpt-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build ABACUS with DFPT
        run: |
          mkdir build && cd build
          cmake .. -DBUILD_TESTING=ON -DENABLE_DFPT=ON
          make -j$(nproc)

      - name: Run DFPT unit tests
        run: cd build && ctest -R dfpt --output-on-failure

      - name: Run DFPT integration tests
        run: |
          for test_dir in tests/integrate/dfpt_*/; do
            echo "=== Running $(basename $test_dir) ==="
            cd $test_dir
            mpirun -np 2 ../../build/abacus < INPUT
            python result_check.py .
            cd ../..
          done
```

### Generating QE Reference Data

```bash
#!/bin/bash
# generate_qe_references.sh
# Run QE calculations to generate reference data for all test systems

QE_BIN=/root/q-e/bin
PSEUDO_DIR=/root/q-e/pseudo

systems=("si_gamma" "si_dispersion" "al_gamma" "mgo_loto" "gaas" "batio3" "si_ncpp" "al_elph")

for sys in "${systems[@]}"; do
    echo "=== Generating reference for $sys ==="
    cd tests/integrate/dfpt_${sys}/reference/

    # Run QE SCF
    ${QE_BIN}/pw.x < ${sys}.scf.in > ${sys}.scf.out

    # Run QE phonon
    ${QE_BIN}/ph.x < ${sys}.ph.in > ${sys}.ph.out

    # Extract frequencies
    grep "freq" ${sys}.ph.out | awk '{print $NF}' > phonon_freq.dat

    # Extract dielectric constant (if computed)
    grep -A3 "Dielectric constant" ${sys}.ph.out > dielectric.dat 2>/dev/null

    # Extract Born charges (if computed)
    grep -A10 "Effective charges" ${sys}.ph.out > born_charges.dat 2>/dev/null

    cd ../../../..
done
```

## TDD Test Plan

### Tests to Write FIRST

```python
# test_integration_suite.py

def test_all_test_cases_have_reference():
    """Every test case must have QE reference data."""
    for test_dir in glob("tests/integrate/dfpt_*/"):
        ref_dir = os.path.join(test_dir, "reference")
        assert os.path.isdir(ref_dir), f"Missing reference/ in {test_dir}"
        assert os.path.exists(os.path.join(ref_dir, "phonon_freq.dat")), \
            f"Missing phonon_freq.dat in {ref_dir}"

def test_all_test_cases_have_input():
    """Every test case must have valid INPUT file."""
    for test_dir in glob("tests/integrate/dfpt_*/"):
        input_file = os.path.join(test_dir, "INPUT")
        assert os.path.exists(input_file), f"Missing INPUT in {test_dir}"
        content = open(input_file).read()
        assert "dfpt" in content.lower(), f"INPUT doesn't contain dfpt in {test_dir}"

def test_all_test_cases_have_checker():
    """Every test case must have result_check.py."""
    for test_dir in glob("tests/integrate/dfpt_*/"):
        checker = os.path.join(test_dir, "result_check.py")
        assert os.path.exists(checker), f"Missing result_check.py in {test_dir}"

def test_minimum_test_count():
    """Must have at least 10 integration test cases."""
    test_dirs = glob("tests/integrate/dfpt_*/")
    assert len(test_dirs) >= 10, f"Only {len(test_dirs)} test cases, need ≥10"

def test_system_coverage():
    """Must cover: insulator, metal, polar, multi-atom, elph."""
    test_names = [os.path.basename(d.rstrip('/')) for d in glob("tests/integrate/dfpt_*/")]
    categories = {
        "insulator": any("si" in n for n in test_names),
        "metal": any("al" in n for n in test_names),
        "polar": any("mgo" in n or "gaas" in n for n in test_names),
        "multi_atom": any("batio3" in n for n in test_names),
        "elph": any("elph" in n for n in test_names),
    }
    for cat, present in categories.items():
        assert present, f"Missing test category: {cat}"
```

## Acceptance Criteria

- [ ] Integration test suite has ≥10 test cases
- [ ] All test cases have QE reference data, INPUT files, and comparison scripts
- [ ] System coverage: insulator, metal, polar material, multi-atom, electron-phonon
- [ ] Si Gamma phonon: frequency error < 0.1 cm⁻¹ vs QE
- [ ] Si dispersion: frequency error < 0.5 cm⁻¹ at all q-points
- [ ] MgO: LO-TO splitting correct, ε∞ within 2%, Z* within 1%
- [ ] Al EPC: λ within 10% of QE reference
- [ ] MPI parallel test: serial vs parallel results identical (< 1e-10)
- [ ] Restart test: interrupted vs uninterrupted results identical
- [ ] CI/CD integration configured (GitHub Actions or equivalent)
- [ ] Test documentation complete (README per test case)
- [ ] All tests pass in CI environment
