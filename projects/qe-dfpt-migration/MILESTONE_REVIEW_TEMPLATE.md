# Milestone Review Template - QE DFPT Migration

**Milestone ID:** [M1-M6]
**Milestone Name:** [Name]
**Review Date:** [YYYY-MM-DD]
**Reviewers:** [Names]

## Milestone Overview

**Target Date:** [YYYY-MM-DD]
**Actual Completion Date:** [YYYY-MM-DD]
**Status:** [On Track / Delayed / At Risk / Completed]

**Tasks Included:**
- [ ] DFPT-XXX: [Task name]
- [ ] DFPT-XXX: [Task name]
- [ ] DFPT-XXX: [Task name]

## Deliverables Review

### Deliverable 1: [Name]

**Status:** [Complete / Incomplete / Partial]
**Location:** [File path or link]

**Quality Assessment:**
- [ ] Meets acceptance criteria
- [ ] Code review passed
- [ ] Tests passing
- [ ] Documentation complete

**Issues/Concerns:**
- [List any issues]

### Deliverable 2: [Name]

[Repeat for each deliverable]

## Success Criteria Evaluation

### Technical Criteria

| Criterion | Target | Actual | Status | Notes |
|-----------|--------|--------|--------|-------|
| Phonon frequency accuracy | < 0.1 cm⁻¹ | [value] | ✓/✗ | [notes] |
| Performance vs QE | ≥ 0.9× | [value] | ✓/✗ | [notes] |
| Test coverage | > 80% | [value] | ✓/✗ | [notes] |
| Code review pass | 100% | [value] | ✓/✗ | [notes] |

### Quality Criteria

| Criterion | Target | Actual | Status | Notes |
|-----------|--------|--------|--------|-------|
| Unit tests passing | 100% | [value] | ✓/✗ | [notes] |
| Integration tests | All pass | [value] | ✓/✗ | [notes] |
| Compiler warnings | 0 | [value] | ✓/✗ | [notes] |
| Memory leaks | 0 | [value] | ✓/✗ | [notes] |

## QE Comparison Results

### Test Systems

| System | ABACUS Freq (cm⁻¹) | QE Freq (cm⁻¹) | Diff (cm⁻¹) | Status |
|--------|---------------------|----------------|-------------|--------|
| Si (Γ) | [values] | [values] | [values] | ✓/✗ |
| Si (X) | [values] | [values] | [values] | ✓/✗ |
| Al (Γ) | [values] | [values] | [values] | ✓/✗ |

**Summary:**
- Maximum difference: [value] cm⁻¹
- Average difference: [value] cm⁻¹
- Within tolerance: [Yes/No]

### Performance Comparison

| Component | ABACUS (s) | QE (s) | Ratio | Target | Status |
|-----------|------------|--------|-------|--------|--------|
| DVQPsiUS | [value] | [value] | [value] | < 1.2 | ✓/✗ |
| Sternheimer | [value] | [value] | [value] | < 1.2 | ✓/✗ |
| DFPT SCF | [value] | [value] | [value] | < 1.2 | ✓/✗ |
| Total | [value] | [value] | [value] | < 1.2 | ✓/✗ |

## Code Quality Metrics

### Code Review Results

**6-Agent Concurrent Review:**
- [ ] Units consistency: PASS / FAIL
- [ ] Physics conservation laws: PASS / FAIL
- [ ] Algorithm matching: PASS / FAIL
- [ ] Code style: PASS / FAIL
- [ ] Call chain analysis: PASS / FAIL
- [ ] Defensive programming: PASS / FAIL

**Issues Found:** [count]
**Issues Resolved:** [count]
**Outstanding Issues:** [count]

### Test Coverage

```
Overall Coverage: [XX]%
├── module_dfpt/: [XX]%
│   ├── dvqpsi_us.cpp: [XX]%
│   ├── sternheimer_solver.cpp: [XX]%
│   └── dfpt_scf.cpp: [XX]%
```

**Uncovered Lines:** [count]
**Critical Uncovered Code:** [Yes/No - list if yes]

### Static Analysis

**Tool:** clang-tidy, cppcheck

**Warnings:**
- Critical: [count]
- Major: [count]
- Minor: [count]

**Action Items:** [list]

## Risk Assessment

### Risks Materialized

| Risk ID | Description | Impact | Mitigation Taken | Status |
|---------|-------------|--------|------------------|--------|
| R1 | [description] | [H/M/L] | [actions] | [Resolved/Ongoing] |

### New Risks Identified

| Risk ID | Description | Impact | Probability | Mitigation Plan |
|---------|-------------|--------|-------------|-----------------|
| R7 | [description] | [H/M/L] | [H/M/L] | [plan] |

### Risk Trend

- Risks resolved this milestone: [count]
- New risks identified: [count]
- Overall risk level: [Increasing/Stable/Decreasing]

## Schedule Performance

### Milestone Timeline

**Planned:**
- Start: [YYYY-MM-DD]
- End: [YYYY-MM-DD]
- Duration: [X weeks]

**Actual:**
- Start: [YYYY-MM-DD]
- End: [YYYY-MM-DD]
- Duration: [X weeks]

**Variance:** [+/- X weeks]

### Task Completion

| Task ID | Planned Duration | Actual Duration | Variance | Status |
|---------|------------------|-----------------|----------|--------|
| DFPT-XXX | [X weeks] | [X weeks] | [+/- X] | ✓/✗ |
| DFPT-XXX | [X weeks] | [X weeks] | [+/- X] | ✓/✗ |

**On-time completion rate:** [XX]%

### Schedule Impact

**Impact on next milestone:** [None / Minor / Significant]
**Recommended adjustments:** [list]

## Resource Utilization

### Team Effort

| Role | Planned (person-weeks) | Actual (person-weeks) | Variance |
|------|------------------------|----------------------|----------|
| Physics Developer | [X] | [X] | [+/- X] |
| Algorithm Developer | [X] | [X] | [+/- X] |
| C++ Developer | [X] | [X] | [+/- X] |

**Total effort variance:** [+/- X person-weeks]

### Infrastructure Usage

- HPC cluster hours: [X hours]
- CI/CD builds: [X builds]
- Code review sessions: [X sessions]

## Lessons Learned

### What Went Well

1. [Item 1]
2. [Item 2]
3. [Item 3]

### What Could Be Improved

1. [Item 1]
   - Root cause: [description]
   - Recommendation: [action]

2. [Item 2]
   - Root cause: [description]
   - Recommendation: [action]

### Process Improvements

1. [Improvement 1]
   - Implementation: [how]
   - Expected benefit: [what]

2. [Improvement 2]
   - Implementation: [how]
   - Expected benefit: [what]

## Technical Debt

### Debt Incurred

| Item | Description | Impact | Planned Resolution |
|------|-------------|--------|-------------------|
| TD-1 | [description] | [H/M/L] | [milestone] |

### Debt Resolved

| Item | Description | Resolution |
|------|-------------|------------|
| TD-X | [description] | [how resolved] |

**Net technical debt:** [Increasing/Stable/Decreasing]

## Action Items

### Critical (Must address before next milestone)

1. [ ] [Action item 1]
   - Owner: [name]
   - Due date: [YYYY-MM-DD]
   - Status: [Not started/In progress/Blocked]

2. [ ] [Action item 2]
   - Owner: [name]
   - Due date: [YYYY-MM-DD]
   - Status: [Not started/In progress/Blocked]

### Important (Should address soon)

1. [ ] [Action item 3]
   - Owner: [name]
   - Due date: [YYYY-MM-DD]

### Nice to Have (Can defer if needed)

1. [ ] [Action item 4]
   - Owner: [name]
   - Due date: [YYYY-MM-DD]

## Next Milestone Preview

**Next Milestone:** [MX: Name]
**Target Date:** [YYYY-MM-DD]
**Key Objectives:**
1. [Objective 1]
2. [Objective 2]
3. [Objective 3]

**Dependencies from this milestone:**
- [Dependency 1]
- [Dependency 2]

**Readiness Assessment:**
- [ ] All blockers resolved
- [ ] Team resources confirmed
- [ ] Infrastructure ready
- [ ] Dependencies satisfied

**Confidence Level:** [High/Medium/Low]

## Stakeholder Feedback

### ABACUS Core Team

**Feedback:**
- [Feedback item 1]
- [Feedback item 2]

**Action Items:**
- [Action based on feedback]

### QE PHonon Experts

**Feedback:**
- [Feedback item 1]
- [Feedback item 2]

**Action Items:**
- [Action based on feedback]

### User Community

**Feedback:**
- [Feedback item 1]
- [Feedback item 2]

**Action Items:**
- [Action based on feedback]

## Milestone Decision

### Recommendation

**Status:** [Approve / Conditional Approve / Reject]

**Rationale:**
[Explanation of recommendation]

**Conditions (if conditional):**
1. [Condition 1]
2. [Condition 2]

### Approvals

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Project Lead | | | |
| Technical Lead | | | |
| ABACUS Core Team | | | |
| Sponsor | | | |

## Appendices

### A. Detailed Test Results

[Link to detailed test report]

### B. Code Review Reports

[Link to code review reports]

### C. Performance Benchmarks

[Link to benchmark results]

### D. QE Comparison Data

[Link to comparison data]

---

**Document Control:**
- Template Version: 1.0
- Review Date: [YYYY-MM-DD]
- Next Review: [YYYY-MM-DD]
- Distribution: Project team, stakeholders
