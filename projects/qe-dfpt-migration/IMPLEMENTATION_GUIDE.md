# QE DFPT Migration - Implementation Guide

**Version:** 1.0
**Date:** 2026-02-20
**Audience:** Development Team

## Overview

This guide provides practical instructions for implementing the QE PHonon DFPT migration to ABACUS. It covers development workflow, coding standards, testing procedures, and best practices.

## Development Environment Setup

### Prerequisites

**Required Software:**
```bash
# Compilers
gcc/g++ >= 9.0 or clang >= 10.0
gfortran >= 9.0 (for QE comparison)

# Build tools
cmake >= 3.16
make >= 4.0

# Libraries
BLAS/LAPACK (OpenBLAS, MKL, or vendor)
FFTW3 >= 3.3
ScaLAPACK (for MPI builds)
MPI (OpenMPI >= 4.0 or MPICH >= 3.3)

# Testing
GoogleTest >= 1.10
Python >= 3.8 (for test scripts)

# Tools
git >= 2.25
clang-format >= 10.0
clang-tidy >= 10.0
```

**Repository Setup:**
```bash
# Clone repositories
git clone /root/abacus-dfpt/abacus-develop abacus
git clone /root/q-e qe
git clone /root/code-review-agent

# Setup ABACUS build
cd abacus
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Debug \
         -DENABLE_TESTING=ON \
         -DENABLE_COVERAGE=ON
make -j8

# Setup QE for reference
cd ../../qe
./configure --prefix=$PWD/install
make ph -j8
```

### Development Branch Strategy

**Branch Naming Convention:**
```
feature/dfpt-<task-id>-<short-description>

Examples:
feature/dfpt-001-architecture
feature/dfpt-102-dvqpsi-kernel
feature/dfpt-201-scf-loop
```

**Workflow:**
```bash
# Create feature branch
git checkout -b feature/dfpt-XXX-description

# Regular commits
git commit -m "dfpt: implement <component> for DFPT-XXX"

# Push and create PR
git push origin feature/dfpt-XXX-description
```

## Coding Standards

### ABACUS Code Style

**File Organization:**
```cpp
// source/module_dfpt/component_name.h
#ifndef MODULE_DFPT_COMPONENT_NAME_H
#define MODULE_DFPT_COMPONENT_NAME_H

namespace ModuleDFPT {

class ComponentName {
public:
    ComponentName();
    ~ComponentName();

    // Public interface
    void compute();

private:
    // Private members
    double* data_;
};

} // namespace ModuleDFPT

#endif
```

**Naming Conventions:**
```cpp
// Classes: PascalCase
class DvqpsiSolver { };

// Functions: camelCase or snake_case (follow ABACUS convention)
void computeResponse();
void compute_response();  // ABACUS uses this

// Variables: snake_case
double charge_density;
int num_kpoints;

// Constants: UPPER_CASE
const double HARTREE_TO_EV = 27.211386;

// Member variables: trailing underscore
class Foo {
    double data_;
    int count_;
};
```

**Code Formatting:**
```bash
# Use clang-format with ABACUS config
clang-format -i source/module_dfpt/*.cpp

# Check before commit
clang-format --dry-run --Werror source/module_dfpt/*.cpp
```

### Physics Code Best Practices

**1. Units and Dimensions:**
```cpp
// Always document units
class DynamicalMatrix {
    // Phonon frequencies in Ry atomic units
    std::vector<double> frequencies_ry_;

    // Convert to cm^-1 for output
    double to_wavenumber(double freq_ry) const {
        return freq_ry * RY_TO_CMM1;
    }
};

// Use named constants
const double RY_TO_EV = 13.605693;
const double RY_TO_CMM1 = 109737.32;
```

**2. Numerical Precision:**
```cpp
// Use appropriate tolerances
const double CHARGE_TOLERANCE = 1e-10;
const double ENERGY_TOLERANCE = 1e-8;
const double FORCE_TOLERANCE = 1e-6;

// Avoid exact floating-point comparisons
if (std::abs(value - target) < tolerance) {
    // converged
}

// Not: if (value == target)
```

**3. Complex Number Handling:**
```cpp
// Use std::complex consistently
#include <complex>
using std::complex;

// ABACUS uses complex<double> for wavefunctions
complex<double>* psi = new complex<double>[size];

// Prefer std::complex operations
complex<double> z1(1.0, 2.0);
complex<double> z2 = std::conj(z1);
double magnitude = std::abs(z1);
```

**4. Memory Management:**
```cpp
// Prefer RAII and smart pointers
class WaveFunction {
    std::unique_ptr<complex<double>[]> data_;

public:
    WaveFunction(int size)
        : data_(new complex<double>[size]) {}

    // No manual delete needed
};

// For large arrays, consider ABACUS memory pool
// (follow existing ABACUS patterns)
```

**5. Error Handling:**
```cpp
// Use exceptions for unrecoverable errors
if (num_bands <= 0) {
    throw std::invalid_argument("num_bands must be positive");
}

// Use return codes for expected failures
bool converged = solve_sternheimer(max_iter, tolerance);
if (!converged) {
    std::cerr << "Warning: Sternheimer solver did not converge\n";
    return false;
}

// Use assertions for internal consistency
assert(kpoint_index < num_kpoints);
```

## Implementation Workflow

### Phase 2 Example: DFPT-102 (DVQPsiUS Kernel)

**Step 1: Understand QE Implementation**
```bash
# Study QE source
cd qe/PHonon/PH/
grep -r "dvqpsi_us" *.f90

# Study dvqpsi_cpp reference
cd qe/PHonon/dvqpsi_cpp/
cat README.md
less src/dvqpsi_us.cpp
```

**Step 2: Design ABACUS Integration**
```cpp
// Create design document
// source/module_dfpt/docs/dvqpsi_design.md

/**
 * DVQPsiUS: Apply DFPT perturbation to wavefunction
 *
 * Physics:
 *   |Δψ⟩ = (dV/dτ)|ψ⟩
 *
 * Components:
 *   1. Local potential: dV_loc/dτ
 *   2. Nonlocal potential: dV_nl/dτ
 *   3. Ultrasoft augmentation: dQ/dτ
 *
 * ABACUS Integration:
 *   - Input: Psi<complex<double>> (ABACUS wavefunction)
 *   - Output: Psi<complex<double>> (perturbed wavefunction)
 *   - Uses: PW_Basis, Structure_Factor, pseudopot_cell_vnl
 */
```

**Step 3: Implement with Tests**
```cpp
// source/module_dfpt/dvqpsi_us.h
namespace ModuleDFPT {

class DvqpsiUS {
public:
    DvqpsiUS(const PW_Basis* pw_basis,
             const pseudopot_cell_vnl* ppcell);

    // Apply dV/dτ to wavefunction
    void apply(const Psi<complex<double>>& psi_in,
               Psi<complex<double>>& dpsi_out,
               const int ik,
               const ModuleBase::Vector3<double>& q);

private:
    void add_local_contribution(/*...*/);
    void add_nonlocal_contribution(/*...*/);
    void add_ultrasoft_contribution(/*...*/);

    const PW_Basis* pw_basis_;
    const pseudopot_cell_vnl* ppcell_;
};

} // namespace ModuleDFPT
```

**Step 4: Write Unit Tests First (TDD)**
```cpp
// source/module_dfpt/test/test_dvqpsi_us.cpp
#include "gtest/gtest.h"
#include "module_dfpt/dvqpsi_us.h"

class DvqpsiUSTest : public ::testing::Test {
protected:
    void SetUp() override {
        // Setup test system (e.g., Si with 2 atoms)
        setup_silicon_test_system();
    }

    void setup_silicon_test_system() {
        // Initialize PW_Basis, pseudopotentials, etc.
    }
};

TEST_F(DvqpsiUSTest, LocalPotentialContribution) {
    // Test local potential term
    DvqpsiUS dvqpsi(pw_basis, ppcell);

    // Apply to test wavefunction
    dvqpsi.apply(psi_in, dpsi_out, ik, q);

    // Compare with reference (from dvqpsi_cpp or QE)
    double diff = compute_difference(dpsi_out, dpsi_reference);
    EXPECT_LT(diff, 1e-10);
}

TEST_F(DvqpsiUSTest, CompareWithQE) {
    // Load QE reference data
    auto qe_result = load_qe_reference("test_data/si_dvqpsi.dat");

    // Compute with ABACUS
    DvqpsiUS dvqpsi(pw_basis, ppcell);
    dvqpsi.apply(psi_in, dpsi_out, ik, q);

    // Compare
    double max_diff = compare_wavefunctions(dpsi_out, qe_result);
    EXPECT_LT(max_diff, 1e-10);
}
```

**Step 5: Implement Incrementally**
```cpp
// Implement one component at a time
// 1. Local potential (simplest)
void DvqpsiUS::add_local_contribution(/*...*/) {
    // FFT to real space
    // Apply dV_loc/dτ
    // FFT back to reciprocal space
}

// Test immediately
// Run: ctest -R DvqpsiUS.LocalPotential

// 2. Nonlocal potential
void DvqpsiUS::add_nonlocal_contribution(/*...*/) {
    // Project onto beta functions
    // Apply dV_nl/dτ
    // Add to result
}

// Test immediately
// Run: ctest -R DvqpsiUS.NonlocalPotential

// 3. Ultrasoft augmentation
void DvqpsiUS::add_ultrasoft_contribution(/*...*/) {
    // Compute augmentation charges
    // Apply dQ/dτ
    // Add to result
}

// Test immediately
// Run: ctest -R DvqpsiUS.UltrasoftAugmentation
```

**Step 6: Integration Testing**
```bash
# Run all unit tests
ctest -R DvqpsiUS

# Run integration test with QE comparison
python test/integration/compare_with_qe.py \
    --test dvqpsi \
    --system Si \
    --qpoint 0.0 0.0 0.0

# Check performance
python test/benchmark/benchmark_dvqpsi.py
```

**Step 7: Code Review**
```bash
# Self-review checklist
- [ ] All unit tests pass
- [ ] QE comparison within tolerance
- [ ] Performance acceptable (within 2x of dvqpsi_cpp)
- [ ] Code formatted (clang-format)
- [ ] No compiler warnings
- [ ] Documentation complete
- [ ] Memory leaks checked (valgrind)

# Submit for review
git push origin feature/dfpt-102-dvqpsi-kernel

# code-review-agent review
cd /root/code-review-agent
python review.py --file ../abacus/source/module_dfpt/dvqpsi_us.cpp \
                 --checks physics,algorithm,units,style
```

## Testing Strategy

### Unit Testing

**Test Structure:**
```
source/module_dfpt/test/
├── test_adapters.cpp          # Data structure adapters
├── test_dvqpsi_us.cpp         # DVQPsiUS kernel
├── test_sternheimer.cpp       # Sternheimer solver
├── test_dfpt_scf.cpp          # DFPT SCF loop
├── test_dynmat.cpp            # Dynamical matrix
└── test_data/                 # Reference data
    ├── si_dvqpsi.dat
    ├── si_phonon.dat
    └── ...
```

**Test Data Generation:**
```bash
# Generate reference data from QE
cd test/reference_data/
./generate_qe_reference.sh Si

# This runs QE and saves:
# - Wavefunctions
# - Perturbed wavefunctions
# - Phonon frequencies
# - Dynamical matrices
```

**Running Tests:**
```bash
# All tests
ctest

# Specific test
ctest -R DvqpsiUS

# Verbose output
ctest -V -R DvqpsiUS

# With coverage
ctest --coverage
lcov --capture --directory . --output-file coverage.info
genhtml coverage.info --output-directory coverage_html
```

### Integration Testing

**Test Systems:**
```
test/integration/systems/
├── Si/              # Simple semiconductor
├── Al/              # Simple metal
├── GaAs/            # Polar semiconductor (LO-TO)
├── MgB2/            # Electron-phonon coupling
└── Fe/              # Magnetic system
```

**Integration Test Script:**
```python
# test/integration/test_phonon.py
import subprocess
import numpy as np

def test_silicon_phonon():
    """Compare ABACUS phonon with QE reference"""

    # Run ABACUS
    subprocess.run(['mpirun', '-np', '4', 'abacus'])

    # Load results
    abacus_freq = np.loadtxt('OUT.ABACUS/phonon_freq.dat')
    qe_freq = np.loadtxt('reference/qe_phonon_freq.dat')

    # Compare
    diff = np.abs(abacus_freq - qe_freq)
    max_diff = np.max(diff)

    # Tolerance: 0.1 cm^-1
    assert max_diff < 0.1, f"Max difference: {max_diff} cm^-1"

    print(f"✓ Silicon phonon test passed (max diff: {max_diff:.4f} cm^-1)")
```

**Running Integration Tests:**
```bash
# All integration tests
python test/integration/run_all.py

# Specific system
python test/integration/test_phonon.py --system Si

# With QE comparison
python test/integration/test_phonon.py --system Si --compare-qe
```

### Performance Testing

**Benchmark Suite:**
```bash
# Run benchmarks
cd test/benchmark
./run_benchmarks.sh

# Compare with QE
./compare_performance.sh

# Generate report
python generate_report.py > performance_report.md
```

**Performance Metrics:**
```
Benchmark Results (Si, 64 atoms, 4x4x4 q-grid):
┌─────────────────────┬──────────┬──────────┬────────┐
│ Component           │ ABACUS   │ QE       │ Ratio  │
├─────────────────────┼──────────┼──────────┼────────┤
│ DVQPsiUS            │ 2.3 s    │ 2.1 s    │ 1.10   │
│ Sternheimer solver  │ 45.2 s   │ 43.8 s   │ 1.03   │
│ DFPT SCF (1 iter)   │ 52.1 s   │ 50.3 s   │ 1.04   │
│ Dynamical matrix    │ 1.2 s    │ 1.1 s    │ 1.09   │
│ Total (1 q-point)   │ 156.3 s  │ 151.2 s  │ 1.03   │
└─────────────────────┴──────────┴──────────┴────────┘

Target: Ratio < 1.2 for all components
Status: ✓ PASS
```

## QE Comparison Workflow

### Setting Up QE Reference

**QE Input File (Si example):**
```fortran
&control
    calculation = 'scf'
    prefix = 'si'
    outdir = './tmp'
/
&system
    ibrav = 2
    celldm(1) = 10.26
    nat = 2
    ntyp = 1
    ecutwfc = 30.0
/
&electrons
    conv_thr = 1.0d-10
/
ATOMIC_SPECIES
 Si 28.086 Si.pbe-n-rrkjus_psl.1.0.0.UPF
ATOMIC_POSITIONS crystal
 Si 0.00 0.00 0.00
 Si 0.25 0.25 0.25
K_POINTS automatic
 4 4 4 0 0 0
```

**QE Phonon Calculation:**
```bash
# SCF calculation
mpirun -np 4 pw.x < si.scf.in > si.scf.out

# Phonon calculation
mpirun -np 4 ph.x < si.ph.in > si.ph.out

# Extract results
python extract_qe_results.py si.ph.out
```

### Automated Comparison

**Comparison Script:**
```python
# test/compare_qe.py
def compare_phonon_frequencies(abacus_file, qe_file, tolerance=0.1):
    """
    Compare phonon frequencies between ABACUS and QE

    Args:
        abacus_file: ABACUS phonon output
        qe_file: QE phonon output
        tolerance: Maximum allowed difference (cm^-1)

    Returns:
        bool: True if within tolerance
    """
    abacus_freq = parse_abacus_phonon(abacus_file)
    qe_freq = parse_qe_phonon(qe_file)

    # Match q-points
    for q in abacus_freq.keys():
        if q not in qe_freq:
            print(f"Warning: q-point {q} not in QE results")
            continue

        diff = np.abs(abacus_freq[q] - qe_freq[q])
        max_diff = np.max(diff)

        if max_diff > tolerance:
            print(f"✗ q={q}: max diff = {max_diff:.4f} cm^-1 (> {tolerance})")
            return False
        else:
            print(f"✓ q={q}: max diff = {max_diff:.4f} cm^-1")

    return True
```

## Debugging Tips

### Common Issues

**1. Numerical Differences with QE:**
```cpp
// Check intermediate results
void DvqpsiUS::apply(/*...*/) {
    add_local_contribution(/*...*/);

    // Debug output
    #ifdef DEBUG_DFPT
    double norm = compute_norm(dpsi_out);
    std::cout << "After local: norm = " << norm << std::endl;
    #endif

    add_nonlocal_contribution(/*...*/);

    #ifdef DEBUG_DFPT
    norm = compute_norm(dpsi_out);
    std::cout << "After nonlocal: norm = " << norm << std::endl;
    #endif
}

// Compare with QE at each step
```

**2. Convergence Issues:**
```cpp
// Add detailed convergence output
bool SternheimerSolver::solve(/*...*/) {
    for (int iter = 0; iter < max_iter; ++iter) {
        double residual = compute_residual();

        if (GlobalV::MY_RANK == 0) {
            std::cout << "Iter " << iter
                      << ": residual = " << residual << std::endl;
        }

        if (residual < tolerance) {
            return true;
        }

        // ... CG iteration
    }

    return false;
}
```

**3. Memory Issues:**
```bash
# Check for memory leaks
valgrind --leak-check=full --show-leak-kinds=all \
         ./abacus < INPUT

# Check memory usage
/usr/bin/time -v ./abacus < INPUT
```

**4. MPI Issues:**
```bash
# Run with MPI debugging
mpirun -np 4 xterm -e gdb ./abacus

# Check MPI communication
export MPICH_DBG=1
mpirun -np 4 ./abacus < INPUT
```

### Debugging Tools

**GDB for C++:**
```bash
# Compile with debug symbols
cmake .. -DCMAKE_BUILD_TYPE=Debug

# Run with GDB
gdb --args ./abacus
(gdb) break DvqpsiUS::apply
(gdb) run < INPUT
(gdb) print dpsi_out[0]
(gdb) continue
```

**Valgrind for Memory:**
```bash
# Memory leak detection
valgrind --leak-check=full ./abacus < INPUT

# Memory error detection
valgrind --tool=memcheck ./abacus < INPUT
```

**Performance Profiling:**
```bash
# CPU profiling with gprof
cmake .. -DCMAKE_CXX_FLAGS="-pg"
./abacus < INPUT
gprof ./abacus gmon.out > profile.txt

# Or use perf
perf record ./abacus < INPUT
perf report
```

## Documentation Requirements

### Code Documentation

**Header Documentation:**
```cpp
/**
 * @file dvqpsi_us.h
 * @brief DFPT perturbation operator for ultrasoft pseudopotentials
 *
 * This file implements the application of the DFPT perturbation
 * operator dV/dτ to wavefunctions, including local potential,
 * nonlocal pseudopotential, and ultrasoft augmentation contributions.
 *
 * Physics reference:
 *   S. Baroni et al., Rev. Mod. Phys. 73, 515 (2001)
 *   Eq. (47)-(49)
 *
 * @author DFPT Migration Team
 * @date 2026-02-20
 */
```

**Function Documentation:**
```cpp
/**
 * @brief Apply DFPT perturbation to wavefunction
 *
 * Computes |Δψ⟩ = (dV/dτ)|ψ⟩ where dV/dτ is the derivative
 * of the potential with respect to atomic displacement τ.
 *
 * @param[in] psi_in Input wavefunction |ψ⟩
 * @param[out] dpsi_out Output perturbed wavefunction |Δψ⟩
 * @param[in] ik K-point index
 * @param[in] q Phonon wavevector
 *
 * @note Units: Ry atomic units
 * @note psi_in and dpsi_out must have same dimensions
 *
 * @throws std::invalid_argument if dimensions mismatch
 */
void apply(const Psi<complex<double>>& psi_in,
           Psi<complex<double>>& dpsi_out,
           const int ik,
           const ModuleBase::Vector3<double>& q);
```

### User Documentation

**User Guide Structure:**
```
docs/DFPT_USER_GUIDE.md
├── 1. Introduction
├── 2. Installation
├── 3. Input Parameters
├── 4. Running Phonon Calculations
├── 5. Output Files
├── 6. Examples
├── 7. Troubleshooting
└── 8. FAQ
```

**Example Section:**
```markdown
## 4. Running Phonon Calculations

### Basic Phonon Calculation

1. Prepare INPUT file:
```
INPUT_PARAMETERS
calculation     phonon
basis_type      pw
ecutwfc         50
scf_thr         1e-8
ph_thr          1e-10
```

2. Run ABACUS:
```bash
mpirun -np 4 abacus
```

3. Check output:
```bash
cat OUT.ABACUS/phonon_freq.dat
```

### Advanced: Electron-Phonon Coupling

[...]
```

### Developer Documentation

**Developer Guide Structure:**
```
docs/DFPT_DEVELOPER_GUIDE.md
├── 1. Architecture Overview
├── 2. Module Structure
├── 3. Data Flow
├── 4. Key Algorithms
├── 5. Integration Points
├── 6. Testing Framework
├── 7. Performance Optimization
└── 8. Future Extensions
```

## Best Practices Summary

### Do's ✓

1. **Write tests first** (TDD approach)
2. **Compare with QE continuously** (automated regression)
3. **Document units and physics** (inline comments)
4. **Commit frequently** (small, logical commits)
5. **Profile early** (performance monitoring from Phase 2)
6. **Review thoroughly** (use code-review-agent)
7. **Communicate issues** (don't hide problems)

### Don'ts ✗

1. **Don't skip tests** (even for "simple" code)
2. **Don't optimize prematurely** (correctness first)
3. **Don't ignore warnings** (fix all compiler warnings)
4. **Don't hardcode values** (use named constants)
5. **Don't commit commented code** (use git history)
6. **Don't mix refactoring and features** (separate commits)
7. **Don't assume QE is always right** (verify physics)

## Getting Help

### Resources

**Documentation:**
- ABACUS: `/root/abacus-develop/CLAUDE.md`
- QE PHonon: `/root/q-e/PHonon/CLAUDE.md`
- dvqpsi_cpp: `/root/q-e/PHonon/dvqpsi_cpp/README.md`

**Code Review:**
- code-review-agent: `/root/code-review-agent/CLAUDE.md`

**Community:**
- ABACUS GitHub: https://github.com/deepmodeling/abacus-develop
- QE Forum: https://www.quantum-espresso.org/forum

### Contact

**Project Lead:** [TBD]
**Technical Lead:** [TBD]
**ABACUS Team:** [TBD]

---

**Document Version:** 1.0
**Last Updated:** 2026-02-20
**Next Review:** 2026-03-06
