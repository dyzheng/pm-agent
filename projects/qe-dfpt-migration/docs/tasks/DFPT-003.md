# DFPT-003: Create DFPT Module Skeleton and Build System

## Objective

Create the `module_dfpt` directory structure, CMake build configuration, and test framework integration so that subsequent tasks have a compilable skeleton to build upon.

## Reference Code

### ABACUS Build System

**Existing module CMake pattern** (`/root/abacus-dfpt/abacus-develop/source/`):

Each module follows this pattern:
```cmake
# source/source_pw/module_pwdft/CMakeLists.txt
add_library(module_pwdft OBJECT
    hamilt_pw.cpp
    operator_pw/veff_pw.cpp
    operator_pw/nonlocal_pw.cpp
    operator_pw/dfpt/dvloc_pw.cpp
    operator_pw/dfpt/dfpt_adapter.cpp
)
target_link_libraries(module_pwdft PUBLIC
    module_base
    module_pw
    module_psi
)
```

**Test CMake pattern**:
```cmake
# source/source_pw/module_pwdft/operator_pw/test/CMakeLists.txt
AddTest(
    TARGET test_dvloc_pw
    SOURCES dvloc_pw_test.cpp dfpt_test_utils.cpp
    LIBS module_pwdft module_base
)
```

**Top-level CMake** (`/root/abacus-dfpt/abacus-develop/source/CMakeLists.txt`):
- Lists all `add_subdirectory()` calls
- Links all modules into final executable

### dvqpsi_cpp Build Reference

`/root/q-e/PHonon/dvqpsi_cpp/CMakeLists.txt` (244 lines):
```cmake
cmake_minimum_required(VERSION 3.10)
project(dvqpsi_cpp CXX)
set(CMAKE_CXX_STANDARD 11)

# Optional dependencies
find_package(OpenMP)
find_package(BLAS)
find_package(LAPACK)
find_package(FFTW3)

# Library
add_library(dvqpsi_cpp
    src/types.cpp src/fft_wrapper.cpp src/dvqpsi_us.cpp
    src/nonlocal.cpp src/augmentation.cpp
    src/hamiltonian_operator.cpp src/preconditioner.cpp
    src/cg_solver.cpp src/sternheimer_solver.cpp
    src/potential_mixer.cpp src/xc_functional.cpp
    src/dfpt_kernel.cpp src/elphon.cpp src/bz_integration.cpp
)

# Tests (GoogleTest)
enable_testing()
find_package(GTest REQUIRED)
add_executable(test_dvqpsi tests/test_dvqpsi.cpp)
target_link_libraries(test_dvqpsi dvqpsi_cpp GTest::gtest_main)
add_test(NAME test_dvqpsi COMMAND test_dvqpsi)
```

## Implementation Guide

### Step 1: Create Directory Structure

```bash
mkdir -p source/module_dfpt/{operators,solvers,physics,parallel,io,test}
```

Target layout:
```
source/module_dfpt/
├── CMakeLists.txt              # Module build config
├── dfpt_types.h                # Forward declarations and type aliases
├── operators/
│   └── .gitkeep
├── solvers/
│   └── .gitkeep
├── physics/
│   └── .gitkeep
├── parallel/
│   └── .gitkeep
├── io/
│   └── .gitkeep
└── test/
    ├── CMakeLists.txt          # Test build config
    └── test_dfpt_skeleton.cpp  # Skeleton compilation test
```

### Step 2: Create Module CMakeLists.txt

```cmake
# source/module_dfpt/CMakeLists.txt

# Placeholder source list — each task adds its files here
set(DFPT_SOURCES
    dfpt_types.h
)

# Create object library (empty initially, files added by subsequent tasks)
if(DFPT_SOURCES)
    add_library(module_dfpt OBJECT ${DFPT_SOURCES})
    target_include_directories(module_dfpt PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
    target_link_libraries(module_dfpt PUBLIC
        module_base
        module_pw
        module_psi
        module_hamilt_general
        module_hsolver
        module_elecstate
    )
endif()

# Tests
if(BUILD_TESTING)
    add_subdirectory(test)
endif()
```

### Step 3: Create Minimal Type Header

```cpp
// source/module_dfpt/dfpt_types.h
#pragma once

#include <complex>
#include <vector>
#include "module_base/vector3.h"
#include "module_base/complexmatrix.h"

namespace ModuleDFPT {

/// Forward declarations for DFPT data types
/// Detailed implementations added by DFPT-101 and later tasks

/// Perturbation type: atomic displacement along Cartesian direction
struct Perturbation {
    int atom_index;     ///< Atom index (0-based)
    int direction;      ///< Cartesian direction (0=x, 1=y, 2=z)
};

/// Q-point specification
struct QPoint {
    ModuleBase::Vector3<double> coord;  ///< Q-point in crystal coordinates
    double weight;                       ///< Integration weight
};

} // namespace ModuleDFPT
```

### Step 4: Create Test Skeleton

```cpp
// source/module_dfpt/test/test_dfpt_skeleton.cpp
#include "gtest/gtest.h"
#include "module_dfpt/dfpt_types.h"

TEST(DFPTSkeleton, TypesCompile) {
    ModuleDFPT::Perturbation pert{0, 2};  // atom 0, z-direction
    EXPECT_EQ(pert.atom_index, 0);
    EXPECT_EQ(pert.direction, 2);
}

TEST(DFPTSkeleton, QPointConstruction) {
    ModuleDFPT::QPoint qpt;
    qpt.coord = {0.5, 0.0, 0.0};
    qpt.weight = 1.0;
    EXPECT_DOUBLE_EQ(qpt.coord.x, 0.5);
}
```

### Step 5: Integrate with Top-Level Build

Add to `source/CMakeLists.txt`:
```cmake
add_subdirectory(module_dfpt)
```

Add to main executable link:
```cmake
target_link_libraries(abacus ... module_dfpt ...)
```

### Key Pitfalls

1. **Circular dependencies**: `module_dfpt` depends on `module_pw`, `module_hamilt_pw`, etc. — ensure no reverse dependency
2. **Template instantiation**: If using `template <typename T, typename Device>`, explicit instantiation may be needed in `.cpp` files
3. **GoogleTest discovery**: Use `gtest_discover_tests()` for automatic test registration
4. **Include paths**: Use `target_include_directories(PUBLIC)` so downstream modules can find headers

## TDD Test Plan

### Tests to Write FIRST (before creating the skeleton)

1. **Build system test** — The skeleton must compile:
   ```bash
   cd /root/abacus-dfpt/abacus-develop/build
   cmake .. -DBUILD_TESTING=ON
   make module_dfpt -j4
   # Must succeed with zero errors
   ```

2. **Test framework test** — GoogleTest must discover tests:
   ```bash
   make test_dfpt_skeleton
   ./test_dfpt_skeleton
   # Must report: 2 tests passed
   ```

3. **Link test** — Module must link with main executable:
   ```bash
   make abacus -j4
   # Must succeed (module_dfpt linked but empty)
   ```

### Verification Commands

```bash
# Full build verification
cd /root/abacus-dfpt/abacus-develop
mkdir -p build && cd build
cmake .. -DBUILD_TESTING=ON -DCMAKE_BUILD_TYPE=Debug
make module_dfpt -j$(nproc)
make test_dfpt_skeleton -j$(nproc)
ctest -R dfpt_skeleton --output-on-failure
```

## Acceptance Criteria

- [ ] `source/module_dfpt/` directory structure created with all subdirectories
- [ ] `CMakeLists.txt` correctly configured for object library
- [ ] `dfpt_types.h` compiles with basic type definitions
- [ ] Test framework integration complete (`test/CMakeLists.txt`)
- [ ] `test_dfpt_skeleton` compiles and passes (2 tests)
- [ ] Module integrates with top-level `CMakeLists.txt`
- [ ] Full ABACUS build succeeds with empty module linked
- [ ] No circular dependency warnings
