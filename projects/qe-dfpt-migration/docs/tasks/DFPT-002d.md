# DFPT-002d: Integration Verification and Example Reports

## Objective

End-to-end verification that the review and migration workflows (DFPT-002b, DFPT-002c) work correctly on real DFPT code. Generate example reports that serve as quality benchmarks for all future reviews.

## Reference Code

### Test Targets

**For 6-agent review** — Use existing ABACUS DFPT code:
- `/root/abacus-dfpt/abacus-develop/source/source_pw/module_pwdft/operator_pw/dfpt/dvloc_pw.cpp` — Local potential derivative operator
- `/root/abacus-dfpt/abacus-develop/source/source_pw/module_pwdft/operator_pw/dfpt/dfpt_adapter.cpp` — Data structure adapter

**For 3-agent migration** — Use QE→ABACUS pair:
- Source: `/root/q-e/LR_Modules/cgsolve_all.f90` (CG solver, ~200 lines)
- Target: `/root/abacus-dfpt/abacus-develop/source/source_hsolver/diago_cg_lr.h` (CG LR solver)

### Expected Findings

**Review findings for `dvloc_pw.cpp`** (expected categories):
- Units: Structure factor phase convention, `tpiba` usage
- Physics: G=0 term handling, periodicity
- Algorithm: FFT operation order, band loop structure
- Style: Template usage, operator inheritance
- Callchain: dvqpsi_cpp integration, adapter usage
- Debug: Array bounds, null pointer checks

**Migration findings for `cgsolve_all.f90`** (expected adaptations):
- `EXTERNAL ch_psi` → `std::function<void(const ct::Tensor&, ct::Tensor&)>` (high)
- `COMPLEX(DP) dpsi(ndmx*npol, nbnd)` → `psi::Psi<T>` (medium)
- `mp_sum(intra_bgrp_comm)` → `Parallel_Reduce::reduce_pool()` (medium)
- `ZDOTC` → `BlasConnector::dotc()` or `ct::Tensor` operations (low)
- Column-major array → row-major or Tensor abstraction (high)
- 1-based indexing → 0-based indexing (low)

## Implementation Guide

### Step 1: Run 6-Agent DFPT Review

Execute all 6 review agents on `dvloc_pw.cpp`:

```bash
# Run each agent sequentially (or in parallel if orchestrator supports it)
for agent in units physics algorithm style callchain debug; do
    claude-review --agent review-dfpt-${agent} \
        --file source/module_dfpt/dvloc_pw.cpp \
        --output examples/dfpt_dvqpsi_review_${agent}.json
done

# Merge into unified report
python merge_review_reports.py examples/dfpt_dvqpsi_review_*.json \
    --output examples/dfpt_dvqpsi_review.md
```

### Step 2: Run 3-Agent Migration Workflow

Execute serial migration workflow:

```bash
# Agent 1: Analyze QE source
claude-review --agent review-migrate-source-dfpt \
    --file /root/q-e/LR_Modules/cgsolve_all.f90 \
    --output examples/migrate_cgsolve_source.json

# Agent 2: Analyze ABACUS target
claude-review --agent review-migrate-target-dfpt \
    --file /root/abacus-dfpt/abacus-develop/source/source_hsolver/diago_cg_lr.h \
    --output examples/migrate_cgsolve_target.json

# Agent 3: Generate adaptation plan
claude-review --agent review-migrate-diff-dfpt \
    --input examples/migrate_cgsolve_source.json examples/migrate_cgsolve_target.json \
    --output examples/dfpt_cgsolve_migration.md
```

### Step 3: Validate Output Quality

**Review report quality checks**:
- Total findings ≥10 across all 6 agents
- At least 1 ERROR-level finding (or documented reason for none)
- At least 3 WARNING-level findings
- At least 5 INFO-level findings
- Each agent contributes at least 1 finding
- All findings have `file`, `message`, and `suggestion` fields

**Migration report quality checks**:
- Total adaptations ≥8
- At least 2 high-severity adaptations
- At least 3 medium-severity adaptations
- At least 3 low-severity adaptations
- Each adaptation has source reference (QE line) and target pattern (ABACUS)

### Step 4: Extend Orchestrator (if needed)

If `orchestrator.py` needs DFPT-specific support:
- Add DFPT agent configuration to agent registry
- Add DFPT-specific output parsing
- Add report merging for 6-agent concurrent review

## TDD Test Plan

### Tests to Write FIRST

1. **JSON schema validation**:
   ```python
   def test_review_output_schema():
       """All review outputs must match finding.schema.json."""
       schema = json.loads(Path("finding.schema.json").read_text())
       for report_file in glob("examples/dfpt_dvqpsi_review_*.json"):
           report = json.loads(Path(report_file).read_text())
           jsonschema.validate(report, schema)

   def test_migration_output_schema():
       """Migration output must have required fields."""
       report = json.loads(Path("examples/migrate_cgsolve_source.json").read_text())
       assert "algorithm" in report
       assert "data_structures" in report
       assert "dependencies" in report
   ```

2. **Finding count validation**:
   ```python
   def test_review_finding_count():
       """Combined review must have ≥10 findings."""
       total = 0
       for report_file in glob("examples/dfpt_dvqpsi_review_*.json"):
           report = json.loads(Path(report_file).read_text())
           total += len(report.get("findings", []))
       assert total >= 10

   def test_migration_adaptation_count():
       """Migration plan must have ≥8 adaptations."""
       report = load_migration_report("examples/dfpt_cgsolve_migration.md")
       assert len(report.adaptations) >= 8
   ```

3. **Severity distribution validation**:
   ```python
   def test_review_severity_distribution():
       findings = collect_all_findings("examples/dfpt_dvqpsi_review_*.json")
       severities = Counter(f["severity"] for f in findings)
       assert severities.get("ERROR", 0) + severities.get("WARNING", 0) >= 3
       assert severities.get("INFO", 0) >= 3
   ```

## Acceptance Criteria

- [ ] 6-agent review on `dvloc_pw.cpp` completes end-to-end, all agents `status=ok`
- [ ] 3-agent migration on `cgsolve_all.f90` → `diago_cg_lr.h` completes end-to-end
- [ ] Review report has ≥10 findings covering ERROR/WARNING/INFO severities
- [ ] Migration report has ≥8 adaptations covering high/medium/low severities
- [ ] All JSON outputs pass envelope schema validation
- [ ] Example reports saved to `examples/` directory
- [ ] Reports are human-readable and serve as quality benchmarks
