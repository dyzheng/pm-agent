# DFPT-302: Performance Optimization and Benchmarking

## Objective

Profile the DFPT module, identify and optimize hotspots, reduce memory footprint, and produce a comprehensive benchmark report comparing ABACUS DFPT performance against QE PHonon for representative systems.

## Reference Code

### QE Performance Characteristics

**Typical QE PHonon timing breakdown** (Si, 2 atoms, 4×4×4 q-grid, 8×8×8 k-grid):
- FFT operations: 40-60% of total runtime
- CG solver (linear algebra): 25-35%
- Charge density accumulation: 5-10%
- Potential mixing: 3-5%
- I/O and communication: 2-5%

**QE memory usage** (Si, 2 atoms):
- Wavefunctions ψ(k): ~50 MB (8 k-points × 10 bands × 1000 PW × 16 bytes)
- Response wavefunctions Δψ: ~50 MB
- Response potential ΔV_SCF: ~4 MB (32³ grid × 16 bytes)
- Charge density response Δρ: ~4 MB
- Workspace: ~20 MB
- Total: ~130 MB

**QE optimization techniques**:
- `/root/q-e/LR_Modules/cgsolve_all.f90`: BLAS-3 operations for band groups
- `/root/q-e/PHonon/PH/solve_linter.f90`: Adaptive CG threshold reduces iterations
- `/root/q-e/Modules/fft_base.f90`: Task-group FFT parallelization
- Buffer I/O: Direct-access files avoid keeping all q-point data in memory

### ABACUS Target — Existing Optimization Infrastructure

**BLAS/LAPACK wrappers** (`/root/abacus-dfpt/abacus-develop/source/source_base/`):
```cpp
class BlasConnector {
    static void gemm(char transa, char transb, int m, int n, int k,
                     std::complex<double> alpha, const std::complex<double>* a, int lda,
                     const std::complex<double>* b, int ldb,
                     std::complex<double> beta, std::complex<double>* c, int ldc);
    static std::complex<double> dotc(int n, const std::complex<double>* x, int incx,
                                      const std::complex<double>* y, int incy);
};
```

**FFT infrastructure** (`/root/abacus-dfpt/abacus-develop/source/source_base/module_fft/`):
- FFTW3 backend for CPU
- cuFFT backend for GPU (future)
- Slab decomposition for MPI parallelization

**Memory management**:
- `psi::Psi<T>` uses contiguous memory allocation
- `ModuleBase::ComplexMatrix` for dense matrices
- No explicit memory pool — relies on allocator

### dvqpsi_cpp Performance Reference

**Timing breakdown** (`/root/q-e/PHonon/dvqpsi_cpp/docs/performance.md`):
- FFT operations: 40-60%
- CG solver: 30-40%
- Charge density: 10-15%
- Mixing: 5-10%

**Memory** (Si, 2 atoms, 32³ grid):
- Wavefunctions: ~50 MB
- Responses: ~30 MB
- Potentials: ~20 MB
- Workspace: ~10 MB
- Total: ~100-150 MB

## Implementation Guide

### Step 1: Profiling

```bash
# Build with profiling support
cmake .. -DCMAKE_BUILD_TYPE=RelWithDebInfo -DENABLE_PROFILING=ON

# Run with perf (Linux)
perf record -g ./abacus < INPUT_dfpt
perf report

# Run with gprof
cmake .. -DCMAKE_CXX_FLAGS="-pg"
./abacus < INPUT_dfpt
gprof abacus gmon.out > profile.txt

# Memory profiling with valgrind/massif
valgrind --tool=massif ./abacus < INPUT_dfpt
ms_print massif.out.* > memory_profile.txt
```

### Step 2: Hotspot Optimization

**FFT optimization** (typically largest hotspot):
```cpp
// Optimization 1: Batch FFT for multiple bands
// Instead of: for each band, FFT individually
// Do: batch FFT for all bands at once (if memory allows)
void batch_fft_bands(const std::complex<double>* psi_g, std::complex<double>* psi_r,
                     int nbands, int npw, int nrxx, PW_Basis* pw) {
    // FFTW plan for batch: fftw_plan_many_dft
    // Reduces FFT plan overhead and improves cache utilization
}

// Optimization 2: In-place FFT where possible
// Avoid allocating temporary arrays for FFT input/output

// Optimization 3: Reuse FFT plans
// Create plans once, reuse for all iterations
```

**CG solver optimization**:
```cpp
// Optimization 1: BLAS-3 for projector computation
// Instead of per-band ZDOTC:
//   for (m) for (n) overlap[m][n] = zdotc(npw, psi+m*npw, dpsi+n*npw)
// Use ZGEMM:
//   overlap = psi^H × dpsi  (nbands_occ × nbands matrix multiply)
BlasConnector::gemm('C', 'N', nbands_occ, nbands, npw,
                    {1.0, 0.0}, psi_kq, npw, dpsi, npw,
                    {0.0, 0.0}, overlap, nbands_occ);

// Optimization 2: Skip converged bands
// Track per-band convergence, skip in operator application

// Optimization 3: Adaptive preconditioning
// Update preconditioner less frequently (every 5 iterations)
```

**Memory optimization**:
```cpp
// Optimization 1: Sequential q-point processing
// Don't store all q-point data simultaneously
// Process one q-point at a time, write results to disk

// Optimization 2: Reuse workspace arrays
// Allocate once, reuse across iterations and perturbations
class DFPTWorkspace {
    std::vector<std::complex<double>> work_r;   // real-space workspace
    std::vector<std::complex<double>> work_g;   // G-space workspace
    std::vector<std::complex<double>> aux;      // auxiliary array
    // Allocated once in before_dfpt(), reused throughout
};

// Optimization 3: Compress response wavefunctions
// Δψ only needed for charge density computation
// Can be computed on-the-fly instead of stored (trade compute for memory)
```

**Communication optimization**:
```cpp
// Optimization 1: Overlap computation and communication
// While reducing drho across pools, start next perturbation's dvpsi computation

// Optimization 2: Non-blocking MPI
MPI_Iallreduce(drho_local, drho_global, nrxx, MPI_DOUBLE_COMPLEX,
               MPI_SUM, POOL_WORLD, &request);
// ... do other work ...
MPI_Wait(&request, &status);

// Optimization 3: Reduce communication volume
// Only communicate drho (small) not dpsi (large)
```

### Step 3: Benchmark Suite

**Test systems**:

| System | Atoms | k-grid | q-grid | PW cutoff | Description |
|--------|-------|--------|--------|-----------|-------------|
| Si | 2 | 8×8×8 | 4×4×4 | 30 Ry | Simple semiconductor |
| Al | 1 | 16×16×16 | 4×4×4 | 30 Ry | Simple metal |
| MgO | 2 | 8×8×8 | 4×4×4 | 60 Ry | Polar insulator |
| BaTiO₃ | 5 | 6×6×6 | 4×4×4 | 60 Ry | Perovskite |
| Si₆₄ | 64 | 2×2×2 | 2×2×2 | 30 Ry | Large supercell |

**Metrics to measure**:
1. Wall time per q-point (single perturbation)
2. Wall time per DFPT SCF iteration
3. CG iterations per Sternheimer solve
4. Peak memory usage
5. MPI scaling efficiency (1, 2, 4, 8, 16 ranks)
6. Comparison with QE for same system and parameters

**Benchmark script**:
```bash
#!/bin/bash
# benchmark_dfpt.sh

SYSTEMS="Si Al MgO BaTiO3 Si64"
NPROCS="1 2 4 8 16"

for sys in $SYSTEMS; do
    for np in $NPROCS; do
        echo "=== $sys, $np ranks ==="
        mpirun -np $np ./abacus < benchmarks/${sys}/INPUT 2>&1 | tee benchmarks/${sys}/output_np${np}.log
        # Extract timing
        grep "DFPT total time" benchmarks/${sys}/output_np${np}.log
        grep "Peak memory" benchmarks/${sys}/output_np${np}.log
    done
done
```

### Step 4: Performance Report

Generate `docs/DFPT_PERFORMANCE.md` with:
1. Profiling results (hotspot breakdown)
2. Optimization changes and their impact
3. Benchmark results table
4. Scaling plots (speedup vs ranks)
5. Memory usage analysis
6. Comparison with QE PHonon
7. Recommendations for users (optimal parallelization settings)

## TDD Test Plan

### Tests to Write FIRST

```cpp
// test/test_dfpt_performance.cpp

// 1. Single q-point timing within budget
TEST(DFPTPerformance, SingleQPointTiming) {
    auto system = create_si_benchmark();
    auto start = high_resolution_clock::now();

    run_dfpt_single_qpoint(system, {0.5, 0, 0}, /*ipert=*/0);

    auto elapsed = duration_cast<seconds>(high_resolution_clock::now() - start);
    // Si single q-point, single perturbation: should complete in < 60s on 1 core
    EXPECT_LT(elapsed.count(), 60);
}

// 2. Computation time ratio vs QE
TEST(DFPTPerformance, TimingVsQE) {
    auto system = create_si_benchmark();

    double abacus_time = measure_dfpt_time(system);
    double qe_time = load_qe_benchmark_time("Si");  // from reference file

    // ABACUS should be within 1.2× of QE
    EXPECT_LE(abacus_time / qe_time, 1.2);
}

// 3. Memory usage within budget
TEST(DFPTPerformance, MemoryUsage) {
    auto system = create_si_benchmark();
    size_t mem_before = get_current_memory_usage();

    run_dfpt_single_qpoint(system, {0.5, 0, 0}, /*ipert=*/0);

    size_t mem_peak = get_peak_memory_usage();
    size_t mem_dfpt = mem_peak - mem_before;

    // Si DFPT memory: should be < 1.5× QE reference
    size_t qe_mem = load_qe_benchmark_memory("Si");
    EXPECT_LE(mem_dfpt, qe_mem * 1.5);
}

// 4. CG iteration count reasonable
TEST(DFPTPerformance, CGIterationCount) {
    auto system = create_si_benchmark();
    auto stats = run_dfpt_with_stats(system);

    // Average CG iterations per band should be < 50
    EXPECT_LT(stats.avg_cg_iterations, 50);
    // SCF iterations should be < 20
    EXPECT_LT(stats.scf_iterations, 20);
}

// 5. BLAS-3 optimization effective
TEST(DFPTPerformance, BLAS3Projector) {
    // Compare projector computation: per-band ZDOTC vs ZGEMM
    int npw = 5000, nbands = 20, nbands_occ = 10;
    auto psi = create_random_matrix(npw, nbands_occ);
    auto dpsi = create_random_matrix(npw, nbands);

    auto t_blas1 = measure_time([&]() {
        projector_blas1(psi, dpsi, npw, nbands, nbands_occ);
    });
    auto t_blas3 = measure_time([&]() {
        projector_blas3(psi, dpsi, npw, nbands, nbands_occ);
    });

    // BLAS-3 should be faster
    EXPECT_LT(t_blas3, t_blas1);
}
```

## Acceptance Criteria

- [ ] Profiling completed with hotspot breakdown documented
- [ ] FFT optimization implemented (batch FFT or plan reuse)
- [ ] CG solver uses BLAS-3 for projector computation
- [ ] Memory optimization: sequential q-point processing, workspace reuse
- [ ] Single q-point computation time ≤ 1.2× QE for Si system
- [ ] Memory peak ≤ 1.5× QE for Si system
- [ ] Performance benchmark report complete (`docs/DFPT_PERFORMANCE.md`)
- [ ] Benchmark covers ≥3 test systems (Si, Al, MgO)
- [ ] Scaling data collected for 1-16 MPI ranks
- [ ] All performance tests pass
