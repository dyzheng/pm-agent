# DFPT-301: Implement MPI Parallelization

## Objective

Add MPI parallel support to the DFPT module at three levels: k-point pool parallelization, q-point image parallelization, and irreducible representation parallelization. This enables phonon calculations on large systems to scale across hundreds of MPI ranks.

## Reference Code

### QE Source (Fortran)

**Parallelization levels** (`/root/q-e/PHonon/PH/`):

QE PHonon uses 4 parallelization levels:
1. **Pools** (`-nk`/`-npools`): Distribute k-points across pools
2. **Images** (`-ni`/`-nimage`): Distribute q-points or irreps across images
3. **Band groups** (`-nb`/`-nband_group`): Distribute bands within a k-point
4. **Task groups** (`-nt`/`-ntg`): FFT parallelization

**K-point pool parallelization** (`/root/q-e/Modules/mp_pools.f90`):
```fortran
! Key communicators:
!   inter_pool_comm  — between pool leaders
!   intra_pool_comm  — within a pool
!   npool            — number of pools
!   me_pool          — rank within pool
!
! K-point distribution:
!   nks_start, nks_end = distribute_kpoints(nks, npool, me_pool)
!
! After local computation, reduce across pools:
!   CALL mp_sum(drho, inter_pool_comm)
!   CALL mp_sum(dyn, inter_pool_comm)
```

**Q-point image parallelization** (`/root/q-e/PHonon/PH/check_initial_status.f90`):
```fortran
! Images distribute q-points:
!   DO iq = 1, nqs
!     IF (MOD(iq-1, nimage) /= my_image_id) CYCLE
!     ! Process this q-point
!   ENDDO
!
! Or distribute irreps within a q-point:
!   DO irr = 1, nirr
!     IF (MOD(irr-1, nimage) /= my_image_id) CYCLE
!     CALL solve_linter(irr, ...)
!   ENDDO
```

**Band group parallelization** (`/root/q-e/LR_Modules/cgsolve_all.f90`):
```fortran
! Within CG solver, bands distributed across band groups:
!   ibnd_start, ibnd_end = distribute_bands(nbnd, nbgrp, me_bgrp)
!
! Dot products reduced within band group:
!   rho(ibnd) = ZDOTC(ndim, h(1,ibnd), 1, g(1,ibnd), 1)
!   CALL mp_sum(rho, intra_bgrp_comm)
```

**Key reduction patterns** (`/root/q-e/LR_Modules/response_kernels.f90`):
```fortran
! Charge density response: accumulated over k-points, reduced across pools
CALL incdrhoscf(drhoscf, weight, ik, dbecsum, dpsi)
! ... after k-loop:
CALL mp_sum(drhoscf, inter_pool_comm)

! Dynamical matrix: accumulated over k-points, reduced across pools
CALL drhodv(...)
CALL mp_sum(dyn, inter_pool_comm)
```

### ABACUS Target — Existing MPI Infrastructure

**ABACUS parallel framework** (`/root/abacus-dfpt/abacus-develop/source/`):

```cpp
// source/source_base/parallel_reduce.h
class Parallel_Reduce {
public:
    static void reduce_pool(double* data, int n);           // sum across pool
    static void reduce_pool(std::complex<double>* data, int n);
    static void reduce_all(double* data, int n);            // sum across all
    static void bcast_pool(double* data, int n);            // broadcast in pool
};

// source/source_base/parallel_global.h
namespace Parallel_Global {
    extern int nproc;           // total MPI ranks
    extern int myrank;          // global rank
    extern int nproc_in_pool;   // ranks per pool
    extern int my_pool;         // pool index
    extern int rank_in_pool;    // rank within pool
    extern int npool;           // number of pools
    extern MPI_Comm POOL_WORLD; // pool communicator
    extern MPI_Comm INTER_POOL; // inter-pool communicator
}

// K-point distribution
// source/source_cell/klist.h
class K_Vectors {
    int nks;                    // total k-points
    int nks_pool;               // k-points in this pool
    int startk_pool;            // first k-point index in this pool
    void mpi_k();               // distribute k-points across pools
};
```

**Ground-state SCF parallelization pattern**:
```cpp
// ESolver_KS_PW already handles:
// - K-point distribution across pools
// - FFT grid distribution (slab decomposition)
// - Charge density reduction across pools
// DFPT inherits this infrastructure
```

### dvqpsi_cpp Reference

dvqpsi_cpp uses OpenMP only (no MPI). The ABACUS DFPT module must add MPI on top:
```cpp
// dvqpsi_cpp OpenMP pattern (band-level):
#pragma omp parallel for private(work_r, work_g)
for (int ib = 0; ib < nbands; ib++) {
    // FFT, multiply, IFFT per band
}
```

## Implementation Guide

### Parallelization Architecture

```
MPI Rank Layout (example: 16 ranks, 4 pools, 2 images)

Image 0 (q-points 0,2,4,...):
  Pool 0 (k-points 0-3):  Rank 0, 1
  Pool 1 (k-points 4-7):  Rank 2, 3
  Pool 2 (k-points 8-11): Rank 4, 5
  Pool 3 (k-points 12-15): Rank 6, 7

Image 1 (q-points 1,3,5,...):
  Pool 0 (k-points 0-3):  Rank 8, 9
  Pool 1 (k-points 4-7):  Rank 10, 11
  Pool 2 (k-points 8-11): Rank 12, 13
  Pool 3 (k-points 12-15): Rank 14, 15
```

### Level 1: K-point Pool Parallelization

This is the most important level — inherited from ground-state but needs DFPT-specific reductions.

```cpp
void ESolver_KS_PW_DFPT::dfpt_scf_loop(int iq, int ipert) {
    // K-points already distributed by K_Vectors::mpi_k()
    // Each pool processes its subset of k-points

    for (int iter = 0; iter < max_iter; iter++) {
        // Local charge density response
        std::vector<std::complex<double>> drho_local(nrxx, 0.0);

        // Each pool processes its k-points
        for (int ik_local = 0; ik_local < kv.nks_pool; ik_local++) {
            int ik_global = kv.startk_pool + ik_local;

            solve_sternheimer(ik_global, dpsi[ik_local]);
            accumulate_drho(drho_local, psi_kq[ik_local], dpsi[ik_local], wk[ik_global]);
        }

        // CRITICAL: Reduce charge density across pools
        Parallel_Reduce::reduce_pool(drho_local.data(), nrxx);

        // Compute response potential (all pools have same drho now)
        compute_dvscf(drho_local, dvscf);

        // Mix and check convergence
        double dr2 = mix_dvscf(dvscf);
        if (dr2 < conv_thr) break;
    }
}
```

**Key reduction points**:
- `drho` after k-point loop (sum across pools)
- `dyn_mat` after all perturbations (sum across pools)
- CG dot products within band groups (if band parallelization used)

### Level 2: Q-point Image Parallelization

```cpp
void ESolver_KS_PW_DFPT::run_all_qpoints() {
    // Distribute q-points across images
    // (requires image communicator setup)

    for (int iq = 0; iq < nq_total; iq++) {
        // Skip q-points not assigned to this image
        if (iq % nimage != my_image_id) continue;

        setup_qpoint(iq);

        for (int ipert = 0; ipert < npert; ipert++) {
            dfpt_scf_loop(iq, ipert);
        }

        // Store dynamical matrix for this q-point
        store_dynmat(iq);
    }

    // Collect dynamical matrices from all images
    collect_dynmat_across_images();
}
```

### Level 3: Irreducible Representation Parallelization

```cpp
void ESolver_KS_PW_DFPT::run_qpoint_with_irrep_parallel(int iq) {
    // Group perturbations by irreducible representation
    auto irreps = compute_irreps(iq);

    for (int irr = 0; irr < irreps.size(); irr++) {
        // Distribute irreps across images (if available)
        if (irr % nimage != my_image_id) continue;

        for (int ipert : irreps[irr].perturbations) {
            dfpt_scf_loop(iq, ipert);
        }
    }

    // Collect results from all images
    collect_irrep_results();
}
```

### Critical Implementation Details

1. **FFT grid distribution**: ABACUS distributes the FFT grid in slabs across ranks within a pool. DFPT operations (real-space multiplication, charge density accumulation) must respect this distribution:
   ```cpp
   // Each rank owns a slab of the FFT grid: [nrxx_start, nrxx_end)
   // drho[ir] is local index, not global
   // After accumulation, mp_sum reduces across pool (not across slabs — slabs are independent)
   ```

2. **K+q point mapping**: For DFPT, each k-point needs its k+q partner. The k+q point may be on a different pool:
   ```cpp
   // Option A: Ensure k and k+q are on the same pool (restrict k-distribution)
   // Option B: Communicate ψ(k+q) between pools (more flexible, more communication)
   // QE uses Option A: k-points distributed so that k and k+q are in the same pool
   ```

3. **Dynamical matrix accumulation**: The dynamical matrix is accumulated over k-points and perturbations. Must reduce correctly:
   ```cpp
   // dyn_mat[ipert1][ipert2] accumulated over k-points in each pool
   // After all k-points: reduce across pools
   Parallel_Reduce::reduce_pool(dyn_mat.data(), npert * npert);
   ```

4. **Load balancing**: Q-points and irreps have different computational costs. Use dynamic scheduling:
   ```cpp
   // Sort q-points by estimated cost (number of irreps × perturbations)
   // Assign heaviest q-points first (greedy load balancing)
   ```

5. **Checkpoint/restart**: For long parallel runs, save intermediate results:
   ```cpp
   // After each q-point completes:
   if (rank_in_pool == 0) {
       save_dynmat_checkpoint(iq, dyn_mat);
   }
   // On restart: skip completed q-points
   ```

### Performance Targets

| System | Ranks | Expected Speedup | Efficiency |
|--------|-------|-----------------|------------|
| Si (2 atoms) | 4 pools | 3.5× | 87% |
| Si (2 atoms) | 8 pools | 6.5× | 81% |
| Si (2 atoms) | 16 pools | 11× | 69% |
| MgO (2 atoms) | 16 pools | 12× | 75% |
| BaTiO₃ (5 atoms) | 16 pools | 13× | 81% |

Efficiency target: > 80% at 16 processes for typical systems.

## TDD Test Plan

### Unit Tests to Write FIRST

```cpp
// test/test_dfpt_parallel.cpp

// 1. K-point distribution correctness
TEST(DFPTParallel, KPointDistribution) {
    // Verify all k-points are covered exactly once across pools
    int nks = 16, npool = 4;
    auto distribution = distribute_kpoints(nks, npool);

    std::set<int> all_k;
    for (int pool = 0; pool < npool; pool++) {
        for (int ik : distribution[pool]) {
            EXPECT_TRUE(all_k.insert(ik).second);  // no duplicates
        }
    }
    EXPECT_EQ(all_k.size(), nks);  // all covered
}

// 2. K and K+q on same pool
TEST(DFPTParallel, KplusQSamePool) {
    // For DFPT: k and k+q must be on the same pool
    auto kv = create_test_kpoints(16);
    auto xq = ModuleBase::Vector3<double>(0.5, 0.0, 0.0);
    auto distribution = distribute_kpoints_dfpt(kv, xq, 4);

    for (int pool = 0; pool < 4; pool++) {
        for (int ik : distribution[pool]) {
            int ikq = find_kplusq(kv, ik, xq);
            // k+q must be in the same pool
            EXPECT_TRUE(std::find(distribution[pool].begin(),
                                  distribution[pool].end(), ikq)
                        != distribution[pool].end());
        }
    }
}

// 3. Charge density reduction correctness
TEST(DFPTParallel, DrhoReduction) {
    // Simulate: each pool computes partial drho, reduce should give total
    int nrxx = 1000;
    int npool = 4;

    // Each pool contributes drho from its k-points
    std::vector<std::complex<double>> drho_total_expected(nrxx, 0.0);
    std::vector<std::vector<std::complex<double>>> drho_per_pool(npool);

    for (int pool = 0; pool < npool; pool++) {
        drho_per_pool[pool].resize(nrxx);
        fill_random(drho_per_pool[pool]);
        for (int ir = 0; ir < nrxx; ir++) {
            drho_total_expected[ir] += drho_per_pool[pool][ir];
        }
    }

    // Simulate MPI_Allreduce
    auto drho_reduced = simulate_allreduce(drho_per_pool);
    compare_complex_arrays(drho_reduced, drho_total_expected, 1e-15);
}

// 4. Parallel vs serial consistency
TEST(DFPTParallel, ParallelVsSerial) {
    // Run DFPT with 1 pool and 4 pools — results must match
    auto system = create_si_system();

    auto result_serial = run_dfpt_serial(system);
    auto result_parallel = run_dfpt_parallel(system, /*npool=*/4);

    // Dynamical matrix must match
    compare_complex_matrices(result_serial.dyn_mat, result_parallel.dyn_mat, 1e-12);
    // Phonon frequencies must match
    compare_real_arrays(result_serial.omega, result_parallel.omega, 1e-10);
}

// 5. Parallel efficiency benchmark
TEST(DFPTParallel, ScalingEfficiency) {
    auto system = create_benchmark_system();

    auto t1 = measure_time([&]() { run_dfpt_parallel(system, 1); });
    auto t4 = measure_time([&]() { run_dfpt_parallel(system, 4); });
    auto t8 = measure_time([&]() { run_dfpt_parallel(system, 8); });
    auto t16 = measure_time([&]() { run_dfpt_parallel(system, 16); });

    double eff_4 = t1 / (4 * t4);
    double eff_8 = t1 / (8 * t8);
    double eff_16 = t1 / (16 * t16);

    EXPECT_GT(eff_4, 0.85);   // > 85% at 4 ranks
    EXPECT_GT(eff_8, 0.80);   // > 80% at 8 ranks
    EXPECT_GT(eff_16, 0.70);  // > 70% at 16 ranks
}

// 6. Q-point image distribution
TEST(DFPTParallel, QPointImageDistribution) {
    int nq = 10, nimage = 3;
    auto distribution = distribute_qpoints(nq, nimage);

    // All q-points covered
    std::set<int> all_q;
    int total = 0;
    for (int img = 0; img < nimage; img++) {
        total += distribution[img].size();
        for (int iq : distribution[img]) {
            all_q.insert(iq);
        }
    }
    EXPECT_EQ(all_q.size(), nq);
    EXPECT_EQ(total, nq);

    // Load balance: max - min ≤ 1
    int max_load = 0, min_load = nq;
    for (int img = 0; img < nimage; img++) {
        max_load = std::max(max_load, (int)distribution[img].size());
        min_load = std::min(min_load, (int)distribution[img].size());
    }
    EXPECT_LE(max_load - min_load, 1);
}
```

### Integration Tests (require MPI environment)

```bash
# Run with 4 MPI ranks, 2 pools
mpirun -np 4 abacus_dfpt_test --gtest_filter="DFPTParallel*" --npool 2

# Run with 8 MPI ranks, 4 pools
mpirun -np 8 abacus_dfpt_test --gtest_filter="DFPTParallel*" --npool 4

# Scaling test
for np in 1 2 4 8 16; do
    mpirun -np $np abacus_dfpt_benchmark --system Si --npool $np
done
```

## Acceptance Criteria

- [ ] K-point pool parallelization implemented and tested
- [ ] Q-point image parallelization implemented
- [ ] Irreducible representation parallelization implemented
- [ ] K and K+q guaranteed on same pool
- [ ] Parallel results match serial to machine precision (< 1e-12)
- [ ] Parallel efficiency > 80% at 16 processes for Si system
- [ ] Load balancing implemented for q-point distribution
- [ ] Checkpoint/restart mechanism for long parallel runs
- [ ] All parallel tests pass (≥6 test cases)
- [ ] Code review passes 6-agent DFPT review
