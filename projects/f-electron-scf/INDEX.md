# f-electron-scf Project Index

**Last Updated**: 2026-02-14
**Project Phase**: Execute
**Status**: Active Development

---

## 🚀 Quick Start

| Resource | Description | Link |
|----------|-------------|------|
| **📊 Dashboard** | Enhanced interactive dashboard with research tracking, change history, and human review checklist | [dashboard.html](./dashboard.html) |
| **📋 Project State** | Current task status and dependencies | [state/project_state.json](./state/project_state.json) |
| **📈 Optimization Plan** | Execution roadmap based on research review | [research/reviews/optimization_plan.md](./research/reviews/optimization_plan.md) |

---

## 📁 Project Structure

### Core Files

```
f-electron-scf/
├── INDEX.md                    ← You are here (Global Navigation)
├── README.md                   Project overview and goals
├── dashboard.html              Enhanced dashboard (Tasks + Research + Reviews)
│
├── state/                      Project state (source of truth)
│   ├── project_state.json      Main state file
│   └── tasks_*.json            Task definitions by phase
│
├── research/                   Research artifacts
│   ├── literature/             Literature review results (JSON)
│   ├── tasks/                  Task-specific research notes
│   └── reviews/                Project-level reviews
│       ├── research_review.md
│       ├── research_review_enhanced.md
│       └── optimization_plan.md
│
├── docs/                       Documentation
│   ├── reports/                Analysis reports
│   └── guides/                 User guides
│
└── plans/                      Historical planning docs
    └── _archive/               Superseded documents
```

---

## 📊 Current Status

### Summary Statistics

- **Total Tasks**: 42
- **Active Tasks**: 34
- **Deferred Tasks**: 8
- **Tasks in Review**: 1
- **Completed**: 0
- **Average Priority**: 71.5/100

### Top Priority Tasks

1. **FE-205** (100/100): 约束DFT框架 ⭐ [Research](./research/tasks/FE-205_research.md)
2. **FE-200** (95/100): 自适应Kerker预处理 [Research](./research/tasks/FE-200_research.md)
3. **FE-204** (91/100): 能量监控 + SCF自动回退
4. **FE-100** (90/100): onsite_projector nspin=1/2支持
5. **FE-105** (90/100): mixing_dftu（占据矩阵mixing）

### Research Status

| Task ID | Literature Review | Status | Papers |
|---------|------------------|--------|--------|
| FE-205 | ✅ Complete | Ready to implement | 9 papers (2024-2025) |
| FE-200 | ✅ Complete | Algorithm ready | 5 papers (2024) |
| FE-204 | ⏳ Pending | - | - |
| FE-D-C2 | ⏳ Pending | - | - |

---

## 🔍 Navigation by Purpose

### For Project Planning

- **Optimization Plan**: [research/reviews/optimization_plan.md](./research/reviews/optimization_plan.md)
  - Week-by-week execution roadmap
  - Priority adjustments based on research
  - Parallelization opportunities

- **Research Review**: [research/reviews/research_review_enhanced.md](./research/reviews/research_review_enhanced.md)
  - 42 tasks assessed (feasibility, novelty, value)
  - Top 10 priority tasks identified
  - Literature-enhanced recommendations

### For Implementation

- **Task State**: [state/project_state.json](./state/project_state.json)
  - Current task definitions
  - Dependencies and acceptance criteria
  - Task status tracking

- **Task Research Notes**:
  - [FE-205: Constrained DFT](./research/tasks/FE-205_research.md) - 9 papers, implementation algorithm
  - [FE-200: Adaptive Kerker](./research/tasks/FE-200_research.md) - 5 papers, 2024 breakthrough

### For Review & Validation

- **Enhanced Dashboard**: [dashboard.html](./dashboard.html) ⭐ NEW FEATURES
  - **Kanban & Timeline**: Task phases with dependency tracking
  - **Research Tab**: Literature review status with links to 9+ papers for FE-205, 5+ for FE-200
  - **Changes Tab**: Before/after comparison of task evolution through research iterations
  - **Review Tab**: Interactive human verification checklist (10 items, persistent state)
  - Full guide: [Enhanced Dashboard Guide](./docs/guides/ENHANCED_DASHBOARD_GUIDE.md)

- **Dependency Graph**: [dependency_graph.svg](./dependency_graph.svg)
  - Visual task dependencies
  - Critical path identification

---

## 📚 Documentation Index

### Recent Reports

| Document | Date | Purpose |
|----------|------|---------|
| [Integration Summary](./docs/reports/INTEGRATION_SUMMARY.md) | 2026-02-14 | claude-scholar integration results |
| [Literature Review Test](./docs/reports/LITERATURE_REVIEW_TEST_REPORT.md) | 2026-02-14 | WebSearch literature findings |
| [Optimization Plan](./research/reviews/optimization_plan.md) | 2026-02-14 | Execution roadmap |

### Guides

| Guide | Purpose |
|-------|---------|
| **[Enhanced Dashboard Guide](./docs/guides/ENHANCED_DASHBOARD_GUIDE.md)** | ⭐ NEW: Research tracking, change history, review checklist |
| [Dashboard Guide](./docs/guides/DASHBOARD_GUIDE.md) | How to use the basic dashboard features |
| [Research Guide](./research/README.md) | How to run literature reviews |

### Historical Plans (Archived)

These documents represent earlier planning phases and may be superseded:

- [plans/2026-02-11-brainstorm-refined-plan.md](./plans/2026-02-11-brainstorm-refined-plan.md) - Initial brainstorm
- [plans/2026-02-11-f-electron-scf-analysis.md](./plans/2026-02-11-f-electron-scf-analysis.md) - Early analysis
- [plans/2026-02-12-zdy-tmp-refactor-merge-design.md](./plans/2026-02-12-zdy-tmp-refactor-merge-design.md) - Merge design

**Note**: These are superseded by [optimization_plan.md](./research/reviews/optimization_plan.md)

---

## 🔄 Workflows

### Running a Literature Review

```bash
# For a specific task
python tools/literature_search.py FE-204 --project projects/f-electron-scf

# For top 5 priority tasks
python tools/enhanced_review.py --max-lit-tasks 5
```

**Output**:
- `research/literature/{task_id}_literature.json` - Condensed findings
- `research/tasks/{task_id}_research.md` - Detailed research notes

### Updating the Dashboard

```bash
# Regenerate dashboard with latest state
python -m tools.generate_dashboard projects/f-electron-scf

# Regenerate dependency graph
python -m tools.generate_graph projects/f-electron-scf
```

### Reviewing Project Progress

1. Open [dashboard.html](./dashboard.html)
2. Navigate to tabs:
   - **Tasks**: Kanban board by phase
   - **Research**: Literature review status
   - **Review**: Human review checklist
3. Check task details and research links

---

## 🎯 Milestones

### M0 (Week 2): Research Preparation ← Current Phase
- [x] Capability registry complete
- [x] Research review complete
- [x] Literature review for Top 5 tasks
- [ ] FE-000 pseudopotential survey (IN PROGRESS)

### M1 (Month 1): Core Infrastructure
- [ ] onsite_projector extensions
- [ ] DFT+U PW basic functionality
- [ ] FE-200/FE-205 prototypes validated

### M2 (Month 2): Algorithm Innovation
- [ ] All adaptive algorithms implemented
- [ ] Constrained DFT framework complete
- [ ] CeO2 baseline validation

### M3 (Month 3): Validation
- [ ] Cross-code verification (VASP)
- [ ] Convergence reliability tests
- [ ] Use case demonstrations

### M4-M5 (Month 5-6): Production Ready
- [ ] Automation tools complete
- [ ] Documentation complete
- [ ] Release preparation

---

## 📞 Quick Reference

### Key Directories

| Directory | Purpose | Auto-Generated |
|-----------|---------|---------------|
| `state/` | Task definitions and status | Manual + Tools |
| `research/` | Literature reviews and analysis | Tools + Manual |
| `docs/` | Reports and guides | Manual |
| `plans/` | Historical planning docs | Manual (Archived) |

### Auto-Generated Files

These files are regenerated by tools and should not be edited manually:

- `dashboard.html` - Generated by `tools/generate_dashboard.py`
- `dependency_graph.*` - Generated by `tools/generate_graph.py`
- `research/literature/*.json` - Generated by `tools/enhanced_review.py`

### Manual Files (Edit Freely)

- `state/project_state.json` - Main state (or edit split files in `state/tasks_*.json`)
- `research/tasks/*.md` - Task research notes
- `research/reviews/*.md` - Project-level reviews
- `docs/**/*.md` - Documentation

---

## 🚨 Current Action Items

### Immediate (This Week)

1. ✅ ~~Complete research review~~ (DONE)
2. ✅ ~~Literature review for FE-205, FE-200~~ (DONE)
3. 🔄 **Start FE-000**: Pseudopotential library survey (IN PROGRESS)
4. 📋 **Review optimization plan** with team
5. 🧪 **Prototype FE-200**: Adaptive Kerker eigenvalue indicator

### Near-Term (2 Weeks)

1. Complete Phase 0 infrastructure tasks (FE-000, FE-001, FE-002)
2. Implement FE-200 (adaptive Kerker) - 2024 algorithm ready
3. Begin FE-205 prototyping (constrained DFT)
4. Expand literature review to FE-204, FE-D-C2

---

## 📖 Related Documentation

### pm-agent System Documentation

- [pm-agent CLAUDE.md](../../CLAUDE.md) - System architecture
- [Context Isolation Guide](../../docs/CONTEXT_ISOLATION_LITERATURE_REVIEW.md) - Literature review architecture
- [Implementation Report](../../docs/IMPLEMENTATION_REPORT.md) - Integration details

### External Resources

- [ABACUS Documentation](http://abacus.deepmodeling.com/)
- [deepmodeling Ecosystem](https://github.com/deepmodeling)

---

## 🔧 Maintenance

### Keeping This Index Updated

This file should be updated when:
- Major milestones are reached
- New research is completed
- Directory structure changes
- Key documents are added or archived

**Last Major Update**: 2026-02-14 (Literature review integration)

---

## 💡 Tips

- **Start here** when joining the project
- **Check Dashboard** for daily task status
- **Read Optimization Plan** before implementation
- **Review Task Research** before coding
- **Archive old plans** to `plans/_archive/` when superseded

---

**Navigation**: [↑ Top](#f-electron-scf-project-index) | [Dashboard](./dashboard.html) | [State](./state/project_state.json) | [Research](./research/)
