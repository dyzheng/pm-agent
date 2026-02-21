# DFPT-101: Migrate Data Structure Adapter Layer

## Objective

Create a complete data structure adapter layer that bridges ABACUS native types and the dvqpsi_cpp standalone kernel types. This adapter enables the DFPT module to leverage both the existing dvqpsi_cpp kernel and ABACUS infrastructure without tight coupling.

## Reference Code

### QE Source — Data Structures to Map

**FFT grid** (`/root/q-e/Modules/fft_types.f90`):
```fortran
TYPE fft_type_descriptor
    INTEGER :: nr1, nr2, nr3        ! FFT grid dimensions
    INTEGER :: nnr                  ! total real-space points (local)
    INTEGER :: ngm                  ! number of G-vectors (local)
    INTEGER, ALLOCATABLE :: nl(:)   ! G-vector → FFT index mapping
    INTEGER, ALLOCATABLE :: nlm(:)  ! G-vector → FFT index mapping (-G)
END TYPE
```

**Wavefunctions** (`/root/q-e/Modules/wavefunctions.f90`):
```fortran
COMPLEX(DP), ALLOCATABLE :: evc(:,:)   ! (npwx, nbnd) wavefunctions at k
REAL(DP), ALLOCATABLE :: et(:,:)       ! (nbnd, nks) eigenvalues
```

**K-points** (`/root/q-e/Modules/klist.f90`):
```fortran
REAL(DP), ALLOCATABLE :: xk(:,:)       ! (3, nks) k-point coordinates
INTEGER, ALLOCATABLE :: ngk(:)         ! (nks) number of PW per k
INTEGER, ALLOCATABLE :: igk_k(:,:)     ! (npwx, nks) G-vector indices
REAL(DP), ALLOCATABLE :: wk(:)         ! (nks) k-point weights
```

**Nonlocal PP** (`/root/q-e/Modules/uspp.f90`):
```fortran
COMPLEX(DP), ALLOCATABLE :: vkb(:,:)   ! (npwx, nkb) beta projectors |β⟩
COMPLEX(DP), ALLOCATABLE :: deeq(:,:,:,:) ! (nhm, nhm, nat, nspin) D matrix
REAL(DP), ALLOCATABLE :: qq_at(:,:,:)  ! (nhm, nhm, nat) Q integrals
```

### ABACUS Target — Native Types

**PW Basis** (`/root/abacus-dfpt/abacus-develop/source/source_basis/module_pw/`):
```cpp
class PW_Basis {
    int nx, ny, nz;                    // FFT grid dimensions
    int nrxx;                          // total real-space points (local)
    int npw;                           // number of PW (local)
    int *ig2isz;                       // G-vector → FFT index
    double *gg;                        // |G|² in (2π/a)² units
    double *g;                         // G-vectors (3 × npw)
    // Methods:
    void recip2real(complex<double>* in, complex<double>* out);  // G→R FFT
    void real2recip(complex<double>* in, complex<double>* out);  // R→G FFT
};

class PW_Basis_K : public PW_Basis {
    int *igl2isz_k;                    // k-dependent G→FFT mapping
    int *ngk;                          // PW count per k-point
};
```

**Wavefunction** (`/root/abacus-dfpt/abacus-develop/source/source_psi/psi.h`):
```cpp
template <typename T = std::complex<double>, typename Device = base_device::DEVICE_CPU>
class Psi {
    T* psi;                            // wavefunction data (nk × nbands × nbasis)
    int nk, nbands, nbasis;
    // Methods:
    T* get_pointer(int ik = 0);
    void fix_k(int ik);               // set current k-point
    int get_nbands();
    int get_nbasis();
};
```

**K-vectors** (`/root/abacus-dfpt/abacus-develop/source/source_cell/klist.h`):
```cpp
class K_Vectors {
    std::vector<ModuleBase::Vector3<double>> kvec_c;  // Cartesian coords
    std::vector<ModuleBase::Vector3<double>> kvec_d;  // Direct coords
    std::vector<double> wk;                            // weights
    int *ngk;                                          // PW per k
    int nks;                                           // total k-points
};
```

### dvqpsi_cpp Types — Bridge Target

**From** `/root/q-e/PHonon/dvqpsi_cpp/include/types.hpp`:
```cpp
struct FFTGrid {
    int nr1, nr2, nr3, nnr, ngm;
    IntVec nl;                         // G→FFT index
    std::vector<std::array<int,3>> mill; // Miller indices
};

struct WaveFunction {
    ComplexVec evc;                    // (npw × nbnd) flattened
    RealVec et;                        // eigenvalues
    int npw, nbnd;
};

struct KPointData {
    std::array<double, 3> xk;
    IntVec igk;
    int npw;
};

struct GVectorData {
    std::vector<std::array<double,3>> g;
    RealVec gg;
    int ngm;
};

struct SystemGeometry {
    int nat;
    IntVec ityp;
    std::array<double, 3> xq;
};

struct NonlocalData {
    std::vector<BetaProjector> beta_proj;
    std::vector<ComplexVec> deeq;
    std::vector<ComplexVec> qq_at;
    int ntyp;
    bool ultrasoft;
};
```

### Existing Adapter Reference

**DFPTAdapter** (`/root/abacus-dfpt/abacus-develop/source/source_pw/module_pwdft/operator_pw/dfpt/dfpt_adapter.h`):
```cpp
class DFPTAdapter {
public:
    // ABACUS → dvqpsi conversions
    static dvqpsi::FFTGrid convert_fft_grid(const ModulePW::PW_Basis* pw_basis);
    static dvqpsi::WaveFunction convert_wavefunction(const psi::Psi<std::complex<double>>& psi, int ik);
    static dvqpsi::KPointData convert_kpoint(const K_Vectors& kv, int ik);
    static dvqpsi::GVectorData convert_gvectors(const ModulePW::PW_Basis* pw_basis);
    static dvqpsi::SystemGeometry convert_geometry(const UnitCell& ucell, const ModuleBase::Vector3<double>& xq);
    static dvqpsi::NonlocalData convert_nonlocal(const pseudopot_cell_vnl& vnl, int ik);

    // dvqpsi → ABACUS conversions
    static void update_wavefunction(psi::Psi<std::complex<double>>& psi, const dvqpsi::WaveFunction& wfc, int ik);
    static void update_charge_density(double* rho, const dvqpsi::ComplexVec& drho, int nrxx);

    // Helpers
    static void compute_structure_factors(/* ... */);
    static void verify_conversion(/* ... */);
};
```

## Implementation Guide

### Conversion Matrix

| ABACUS Type | dvqpsi Type | Conversion Notes |
|-------------|-------------|-----------------|
| `PW_Basis::nx,ny,nz` | `FFTGrid::nr1,nr2,nr3` | Direct copy |
| `PW_Basis::nrxx` | `FFTGrid::nnr` | Direct copy |
| `PW_Basis::npw` | `FFTGrid::ngm` | Direct copy |
| `PW_Basis::ig2isz` | `FFTGrid::nl` | Index mapping may differ — verify |
| `PW_Basis::gg` | `GVectorData::gg` | Units: ABACUS uses `(2π/a)²`, dvqpsi may use Bohr⁻² |
| `Psi<T>::psi` | `WaveFunction::evc` | Layout: ABACUS `(nk,nbands,nbasis)` → dvqpsi `(npw*nbnd)` |
| `K_Vectors::kvec_c` | `KPointData::xk` | Cartesian coordinates in 2π/a units |
| `K_Vectors::ngk` | `KPointData::npw` | Per k-point |
| `pseudopot_cell_vnl::deeq` | `NonlocalData::deeq` | D matrix: `(nhm,nhm,nat,nspin)` → per-atom vectors |

### Critical Implementation Details

1. **Memory layout**: ABACUS `Psi` stores wavefunctions as `(nk, nbands, nbasis)` in row-major C++ order. dvqpsi expects `(npw × nbnd)` flattened. The conversion must handle this correctly:
   ```cpp
   // ABACUS → dvqpsi: extract single k-point, transpose if needed
   dvqpsi::WaveFunction convert_wavefunction(const psi::Psi<CT>& psi, int ik) {
       dvqpsi::WaveFunction wfc;
       wfc.npw = psi.get_nbasis();
       wfc.nbnd = psi.get_nbands();
       wfc.evc.resize(wfc.npw * wfc.nbnd);
       // Copy band-by-band (ABACUS stores band-contiguous)
       const CT* src = psi.get_pointer(ik);
       for (int ib = 0; ib < wfc.nbnd; ib++) {
           std::copy(src + ib * wfc.npw, src + (ib+1) * wfc.npw,
                     wfc.evc.begin() + ib * wfc.npw);
       }
       return wfc;
   }
   ```

2. **G-vector index mapping**: ABACUS uses `ig2isz` (G-index → FFT slab index), while dvqpsi uses `nl` (G-index → linear FFT index). These may have different conventions:
   ```cpp
   // Verify: for each G-vector ig, the FFT index must map to the same
   // real-space point after inverse FFT
   void verify_fft_mapping(const PW_Basis* pw, const dvqpsi::FFTGrid& grid) {
       for (int ig = 0; ig < pw->npw; ig++) {
           // ABACUS: ig2isz[ig] encodes (iz * ny + iy) for slab decomposition
           // dvqpsi: nl[ig] is linear index in (nr1 * nr2 * nr3) array
           // Must verify equivalence
       }
   }
   ```

3. **Unit consistency**: Both ABACUS and QE use Rydberg atomic units, but G-vector magnitudes may differ by `tpiba` factor:
   ```cpp
   // ABACUS: gg[ig] is |G|² in (2π/a)² units
   // QE: gg[ig] is |G|² in (2π/a)² units (same)
   // dvqpsi: gg[ig] should also be in (2π/a)² units
   // VERIFY: no tpiba conversion needed if both use same convention
   ```

4. **Zero-copy where possible**: For large arrays (wavefunctions, charge density), avoid unnecessary copies:
   ```cpp
   // If memory layout matches, use pointer view instead of copy
   // Only copy when layout transformation is needed
   ```

### Performance Requirements

- Conversion overhead must be < 5% of total DFPT iteration time
- For Si (2 atoms, 32³ grid, 10 bands, 8 k-points):
  - FFT grid conversion: < 1 μs (metadata only)
  - Wavefunction conversion: < 100 μs per k-point
  - Full adapter setup: < 1 ms

## TDD Test Plan

### Unit Tests to Write FIRST

```cpp
// test/test_dfpt_adapters.cpp

// 1. FFT grid conversion roundtrip
TEST(DFPTAdapter, FFTGridConversion) {
    // Create mock PW_Basis with known dimensions
    auto pw = create_test_pw_basis(32, 32, 32);
    auto grid = DFPTAdapter::convert_fft_grid(pw.get());

    EXPECT_EQ(grid.nr1, 32);
    EXPECT_EQ(grid.nr2, 32);
    EXPECT_EQ(grid.nr3, 32);
    EXPECT_EQ(grid.nnr, pw->nrxx);
    EXPECT_EQ(grid.ngm, pw->npw);
    // Verify nl mapping consistency
    for (int ig = 0; ig < grid.ngm; ig++) {
        EXPECT_GE(grid.nl[ig], 0);
        EXPECT_LT(grid.nl[ig], grid.nnr);
    }
}

// 2. Wavefunction conversion preserves data
TEST(DFPTAdapter, WavefunctionConversion) {
    const int nbands = 4, nbasis = 100;
    auto psi = create_test_psi(1, nbands, nbasis);  // 1 k-point
    // Fill with known pattern
    fill_test_pattern(psi, 0);

    auto wfc = DFPTAdapter::convert_wavefunction(psi, 0);

    EXPECT_EQ(wfc.npw, nbasis);
    EXPECT_EQ(wfc.nbnd, nbands);
    // Verify data integrity
    for (int ib = 0; ib < nbands; ib++) {
        for (int ig = 0; ig < nbasis; ig++) {
            EXPECT_EQ(wfc.evc[ib * nbasis + ig],
                      psi.get_pointer(0)[ib * nbasis + ig]);
        }
    }
}

// 3. Wavefunction roundtrip (convert → update → compare)
TEST(DFPTAdapter, WavefunctionRoundtrip) {
    auto psi_orig = create_test_psi(1, 4, 100);
    fill_random(psi_orig);

    auto wfc = DFPTAdapter::convert_wavefunction(psi_orig, 0);
    auto psi_copy = create_test_psi(1, 4, 100);
    DFPTAdapter::update_wavefunction(psi_copy, wfc, 0);

    compare_psi(psi_orig, psi_copy, 0, 1e-15);
}

// 4. K-point conversion
TEST(DFPTAdapter, KPointConversion) {
    K_Vectors kv;
    setup_test_kpoints(kv, 8);  // 8 k-points

    for (int ik = 0; ik < 8; ik++) {
        auto kpt = DFPTAdapter::convert_kpoint(kv, ik);
        EXPECT_DOUBLE_EQ(kpt.xk[0], kv.kvec_c[ik].x);
        EXPECT_DOUBLE_EQ(kpt.xk[1], kv.kvec_c[ik].y);
        EXPECT_DOUBLE_EQ(kpt.xk[2], kv.kvec_c[ik].z);
        EXPECT_EQ(kpt.npw, kv.ngk[ik]);
    }
}

// 5. G-vector conversion with unit check
TEST(DFPTAdapter, GVectorConversion) {
    auto pw = create_test_pw_basis(32, 32, 32);
    auto gvec = DFPTAdapter::convert_gvectors(pw.get());

    EXPECT_EQ(gvec.ngm, pw->npw);
    // Verify |G|² consistency
    for (int ig = 0; ig < gvec.ngm; ig++) {
        double g2 = gvec.g[ig][0]*gvec.g[ig][0]
                   + gvec.g[ig][1]*gvec.g[ig][1]
                   + gvec.g[ig][2]*gvec.g[ig][2];
        EXPECT_NEAR(gvec.gg[ig], g2, 1e-12);
    }
}

// 6. Nonlocal data conversion
TEST(DFPTAdapter, NonlocalConversion) {
    auto vnl = create_test_vnl(2, 4);  // 2 atoms, 4 projectors each
    auto nldata = DFPTAdapter::convert_nonlocal(vnl, 0);

    EXPECT_EQ(nldata.ntyp, vnl.ntype);
    EXPECT_FALSE(nldata.deeq.empty());
}

// 7. Performance benchmark
TEST(DFPTAdapter, ConversionPerformance) {
    auto pw = create_test_pw_basis(64, 64, 64);
    auto psi = create_test_psi(8, 20, 5000);  // 8 k-points, 20 bands

    auto start = std::chrono::high_resolution_clock::now();
    for (int ik = 0; ik < 8; ik++) {
        auto wfc = DFPTAdapter::convert_wavefunction(psi, ik);
    }
    auto elapsed = std::chrono::high_resolution_clock::now() - start;
    auto ms = std::chrono::duration_cast<std::chrono::microseconds>(elapsed).count();

    // 8 k-points × 20 bands × 5000 PW should convert in < 10 ms
    EXPECT_LT(ms, 10000);
}
```

### Integration Tests

```cpp
// Test with real ABACUS data structures (requires ABACUS test fixtures)
TEST(DFPTAdapterIntegration, SiSystem) {
    // Load Si ground-state from test fixture
    auto [ucell, kv, pw, psi] = load_si_fixture();

    // Convert all data structures
    auto grid = DFPTAdapter::convert_fft_grid(pw);
    auto gvec = DFPTAdapter::convert_gvectors(pw);
    auto geom = DFPTAdapter::convert_geometry(ucell, {0.0, 0.0, 0.0});

    // Verify physical consistency
    EXPECT_EQ(geom.nat, 2);  // Si has 2 atoms
    EXPECT_EQ(grid.nr1 * grid.nr2 * grid.nr3, grid.nnr);
}
```

## Acceptance Criteria

- [ ] All 6 adapter conversion functions implemented and tested
- [ ] Both directions tested: ABACUS→dvqpsi and dvqpsi→ABACUS
- [ ] Wavefunction roundtrip preserves data to machine precision (< 1e-15)
- [ ] G-vector |G|² consistency verified to < 1e-12
- [ ] Performance overhead < 5% (benchmark test passes)
- [ ] No memory leaks (valgrind clean or ASAN clean)
- [ ] Code review passes 6-agent DFPT review (from DFPT-002b)
- [ ] All unit tests pass (≥7 test cases)
