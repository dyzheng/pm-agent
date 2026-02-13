# PR-2 Review: DFT+U PW SCF nspin=1/2/4

**Commit:** 7c54a20e4
**Reviewer:** PM
**Date:** 2026-02-12
**Verdict:** CONDITIONAL PASS — 2 issues to fix, 3 observations

---

## 1. Logic Correctness vs zdy-tmp Reference

All 6 critical logic points verified against zdy-tmp:

| Check | Result |
|---|---|
| nspin=1/2 becp index (`ib*nkb`) vs nspin=4 (`ib*2*nkb`) | ✓ Match |
| nspin=2 spin channel via `is = ik >= nk/2 ? 1 : 0` | ✓ Match |
| `initialed_locale==false` → compute+reduce+save; `else` → save only | ✓ Match |
| `mix_locale` called BEFORE energy/VU calculation | ✓ Match |
| `initialed_locale = false` set at END of function | ✓ Match |
| nspin=2 uom_array spin-down offset (`size` / `nr*nc`) | ✓ Match (equivalent values) |
| energy weight: nspin1=1.0, nspin2=0.5, nspin4=0.25 | ✓ Match |
| diag_coeff: nspin4=1.0, else=0.5 | ✓ Match |
| nspin=2 eff_pot_pw spin-down at `size()/2 + index` | ✓ Match |
| Pauli→spin transform (nspin=4 only) | ✓ Match |

## 2. Issues to Fix

### ISSUE-1 (Medium): `set_locale` nspin=1 bug

`dftu_occup.cpp:145-150` — `set_locale()` treats nspin=1 same as nspin=2:

```cpp
else if (PARAM.inp.nspin == 1 || PARAM.inp.nspin == 2)
{
    for(int mm = 0; mm < ...; mm++)
    {
        locale[iat][l][0][0].c[mm] = this->uom_array[...];
        locale[iat][l][0][1].c[mm] = this->uom_array[... + nr*nc];  // ← nspin=1 has no spin=1 channel
    }
}
```

For nspin=1, `locale[iat][l][n]` is still resized to 2 (line 116-117 in dftu.cpp), so this won't segfault. But it reads garbage from `uom_array` into `locale[..][1]` because the spin-down region of `uom_array` is never populated for nspin=1.

**Impact:** Low for now — `locale[..][1]` is not used in the nspin=1 energy/VU path. But it's a latent bug.

**Fix:** Either guard with `if(PARAM.inp.nspin == 2)` for the spin-down copy, or leave as-is with a comment explaining why it's safe.

Note: zdy-tmp has the same bug. This is a faithful port. Recommend fixing anyway.

### ISSUE-2 (Low): Mixing strategy difference from zdy-tmp

zdy-tmp uses `p_chgmix->mix_uom()` (Broyden/Pulay mixing via charge mixing infrastructure), then `set_locale()` to restore.

PR-2 uses `mix_locale()` (simple linear mixing with `mixing_beta`).

This is actually acceptable for initial port because:
- zdy-tmp's `mix_uom` has nspin=2 completely commented out (broken)
- Simple linear mixing is a valid baseline
- Broyden mixing of occupation matrix can be added as a follow-up optimization

**Action:** Add a TODO comment at line 254 noting that Broyden mixing of uom_array is a future optimization.

## 3. Observations (No Action Required)

### OBS-1: `uom_array` / `uom_save` allocated but `uom_save` never written

`dftu.cpp:172` allocates `uom_save` but no code in PR-2 writes to it. In zdy-tmp, `uom_save` is used by `mix_uom`. Since PR-2 uses `mix_locale` instead, `uom_save` is dead memory.

Not a bug — it's pre-allocated for the future Broyden mixing path. Leave as-is.

### OBS-2: `uom_array` save logic in `else` branch may be unnecessary

When `initialed_locale == true`, the `else` branch (lines 230-252) copies locale→uom_array. But since `mix_locale` operates on locale directly (not uom_array), this save is only useful if something else reads `uom_array` later. Currently nothing does.

Again, this is infrastructure for future Broyden mixing. Leave as-is.

### OBS-3: Unit tests are lightweight

The unit tests verify arithmetic constants (energy weights, becp indices, array copy logic) but don't test the actual `cal_occ_pw` function. This is acceptable given the heavy dependency on ABACUS infrastructure — real verification comes from integration tests 815/816.

## 4. Integration Tests

- **815_PW_DFTU_S2**: Fe BCC, nspin=2, d-orbital (orbital_corr=2), U=5.0 eV — good coverage
- **816_PW_DFTU_S1**: Fe BCC, nspin=1, d-orbital (orbital_corr=2), U=5.0 eV — good coverage
- Both use ecutwfc=10 (fast), scf_thr=1e-4, scf_nmax=50
- Missing: nspin=4 integration test (acceptable — nspin=4 path is unchanged from original develop code)

## 5. Code Quality

- Clean API adaptation (GlobalV→PARAM, GlobalC→parameter passing)
- Consistent formatting with develop codebase
- No debug prints or WIP code
- CMakeLists properly wired

## 6. Verdict

**CONDITIONAL PASS** — merge-ready after:
1. Fix or annotate ISSUE-1 (nspin=1 set_locale spin-down copy)
2. Add TODO comment for ISSUE-2 (Broyden mixing future work)

Both are minor. Gate 4 (code review) passes with these conditions.
