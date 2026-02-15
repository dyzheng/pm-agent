# Enhanced Dashboard Guide

**Last Updated:** 2026-02-14

## Overview

The f-electron-scf dashboard has been enhanced with three new tabs to address project navigation and tracking requirements:

1. **Research Tab** - Track literature review status and access research documentation
2. **Changes Tab** - View task evolution through research iterations
3. **Review Tab** - Interactive human review checklist with persistent state

## New Features

### 1. Research Status Tab

**Purpose:** Track which tasks have completed literature reviews and access research documentation.

**Features:**
- ✅ Visual indicators for tasks with completed literature reviews
- 📚 Paper count badges showing number of papers reviewed
- 🔗 Direct links to research notes (Markdown) and JSON summaries
- ⏳ Pending research indicators for high-priority tasks

**Data Displayed:**
- **FE-205**: 9 papers reviewed → [Research Notes](../../research/tasks/FE-205_research.md)
- **FE-200**: 5 papers reviewed → [Research Notes](../../research/tasks/FE-200_research.md)
- **FE-100, FE-105, FE-204**: Literature search completed (JSON summaries available)

**Usage:**
1. Open dashboard.html
2. Click "Research" tab
3. Green-bordered cards = completed reviews
4. Gray-bordered cards = pending reviews
5. Click links to view detailed research notes or JSON data

### 2. Changes & Iterations Tab

**Purpose:** Track how tasks evolved after each research iteration, showing before/after comparisons.

**Features:**
- 📊 Side-by-side before/after comparison
- 🔄 Change type indicators (priority_update, status_update, etc.)
- 📅 Timestamp tracking
- 📌 Reason/rationale for each change

**Example Changes Tracked:**
```
FE-205: constrained DFT framework
├─ Before: Priority 85, Novelty: routine, Value: high
├─ After:  Priority 100, Novelty: incremental, Value: critical
└─ Reason: Literature review revealed OS-CDFT method effectiveness

FE-200: Adaptive Kerker
├─ Before: Priority 80, Novelty: routine, Value: high
├─ After:  Priority 95, Novelty: incremental, Value: critical
└─ Reason: 2024 breakthrough with eigenvalue indicator

FE-100: onsite_projector nspin=1/2
├─ Before: Status: pending, Progress: 0%
├─ After:  Status: in_review, Progress: 90%
└─ Reason: Code submitted (d2364165c), awaiting tests
```

**Usage:**
1. Open Changes tab
2. Scroll through change history (chronological order)
3. Review rationale for each change
4. Compare before/after states in highlighted panels

### 3. Human Review Checklist Tab

**Purpose:** Interactive todo list for manual verification and approval tasks.

**Features:**
- ✅ Clickable checkboxes with persistent state (localStorage)
- 📊 Real-time progress statistics
- 📂 Organized by category (Research Validation, Planning, Code Review, etc.)
- 💾 Auto-saves check状态 to browser localStorage

**Review Categories:**

#### Research Validation
- [ ] Review FE-205 constrained DFT research findings
- [ ] Review FE-200 adaptive Kerker research

#### Planning
- [ ] Approve priority changes from research iteration
- [ ] Review optimization plan execution roadmap

#### Code Review
- [ ] Verify FE-100 test coverage

#### Infrastructure
- [ ] Validate FE-000 pseudopotential library survey
- [ ] Approve FE-001 DFT+U code audit

#### Testing
- [ ] Check FE-002 regression test baselines

#### Documentation
- [ ] Review new directory organization

#### Tools
- [ ] Validate dashboard enhancements

**Usage:**
1. Open Review tab
2. View progress stats at top (X/Y completed, Z% progress)
3. Click any item to toggle checkbox
4. State persists across browser sessions (localStorage)
5. Re-opening dashboard restores your previous progress

## Technical Details

### Data Sources

**Research Tab:**
- Reads from `research/literature/*.json` for literature review summaries
- Links to `research/tasks/*_research.md` for detailed notes
- Embedded task list filtered for active (non-deferred) tasks

**Changes Tab:**
- Currently shows simulated change history
- In production, would integrate with version control or state history tracking
- Format ready for real-time updates from pipeline hooks

**Review Tab:**
- Checklist items defined in JavaScript array
- State stored in `localStorage` key: `review_checklist`
- Format: `{ "item_id": true/false }`

### Customization

**Adding New Research Reviews:**

Edit the `litReviews` object in `renderResearch()`:

```javascript
const litReviews = {
  'FE-YOUR-TASK': {
    papers: 5,
    file: 'research/tasks/FE-YOUR-TASK_research.md',
    json: 'research/literature/FE-YOUR-TASK_literature.json'
  }
};
```

**Adding Change History Items:**

Edit the `changes` array in `renderChanges()`:

```javascript
{
  task_id: 'FE-XXX',
  title: 'Task title',
  timestamp: '2026-02-14 12:00',
  type: 'priority_update',
  before: { priority: 80 },
  after: { priority: 95 },
  reason: 'Why this changed'
}
```

**Adding Review Checklist Items:**

Edit the `reviewItems` array in `renderReview()`:

```javascript
{
  id: 'unique_item_id',
  category: 'Category Name',
  title: 'Short title',
  description: 'Detailed description of what to verify'
}
```

## Browser Compatibility

- Modern browsers (Chrome, Firefox, Safari, Edge)
- Requires localStorage support for checklist persistence
- No external dependencies (pure HTML/CSS/JS)

## Accessibility

- Keyboard navigation supported for tabs
- Click handlers on all interactive elements
- Color-coded visual indicators with text fallbacks
- High contrast color scheme (dark theme)

## Performance

- All data embedded in HTML (no external fetches)
- Lazy rendering (only active tab renders)
- Minimal DOM manipulation
- ~100 KB total file size

## Future Enhancements

Planned improvements:
1. **Real-time change tracking** from git history or state snapshots
2. **Bulk actions** for review checklist (check all, uncheck all)
3. **Export functionality** for review status (PDF, Markdown)
4. **Search/filter** for research and changes tabs
5. **Notifications** for new literature reviews or task changes
6. **Team collaboration** - shared checklist state via backend

## Troubleshooting

**Research links not working:**
- Check that files exist in `research/tasks/` and `research/literature/`
- Verify relative paths are correct

**Checklist state not persisting:**
- Check browser localStorage is enabled
- Try clearing localStorage: `localStorage.clear()`
- Verify browser not in private/incognito mode

**Tabs not switching:**
- Check JavaScript console for errors
- Verify all tab buttons have `data-view` attributes
- Ensure corresponding `*-view` divs exist

## Contact

For bugs or feature requests related to dashboard enhancements, see [GitHub Issues](https://github.com/anthropics/claude-code/issues).

---

**Related Documentation:**
- [INDEX.md](../../INDEX.md) - Global project navigation
- [DASHBOARD_GUIDE.md](./DASHBOARD_GUIDE.md) - Original dashboard features
- [Research Review Guide](../../research/README.md) - Literature review process
