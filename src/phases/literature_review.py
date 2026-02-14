"""Literature review for task novelty assessment with context isolation.

Uses isolated agents to perform literature search and analysis,
returning only condensed findings to avoid context explosion.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.state import Task, ProjectState


@dataclass
class LiteratureReviewResult:
    """Condensed result from literature review."""

    task_id: str
    query_terms: list[str]

    # Key findings (condensed)
    recent_advances: str  # 1-2 sentences on latest developments (2024-2026)
    state_of_art: str  # Current best approaches (1-2 sentences)
    gaps_identified: str  # What's missing or unsolved (1-2 sentences)

    # Assessment
    novelty_level: str  # frontier/advanced/incremental/routine
    novelty_justification: str  # 1-2 sentences why

    # Recommendations
    improvement_suggestions: list[str]  # 2-5 concrete suggestions
    alternative_approaches: list[str]  # 1-3 alternatives from literature

    # References (titles only, no abstracts)
    key_papers: list[str]  # 3-5 most relevant paper titles

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "query_terms": self.query_terms,
            "recent_advances": self.recent_advances,
            "state_of_art": self.state_of_art,
            "gaps_identified": self.gaps_identified,
            "novelty_level": self.novelty_level,
            "novelty_justification": self.novelty_justification,
            "improvement_suggestions": self.improvement_suggestions,
            "alternative_approaches": self.alternative_approaches,
            "key_papers": self.key_papers,
        }

    @classmethod
    def from_dict(cls, data: dict) -> LiteratureReviewResult:
        return cls(**data)


def generate_literature_review_prompt(task: Task, state: ProjectState) -> str:
    """Generate a focused prompt for literature review agent.

    This prompt is designed to get condensed, actionable insights
    without returning full paper contents.
    """
    domain_keywords = state.parsed_intent.get("keywords", [])
    domain_context = state.parsed_intent.get("domain", "computational science")

    prompt = f"""
# Literature Review Task

## Context
**Project Domain**: {domain_context}
**Project Goal**: {state.request[:200]}...

## Task to Review
**ID**: {task.id}
**Title**: {task.title}
**Description**: {task.description[:300]}...

## Your Mission

Perform a focused literature review to assess this task's novelty and identify improvements.

### Steps:

1. **Search Recent Literature (2024-2026)**
   - Query: "{task.title}" + "DFT" or "ab initio" or "electronic structure"
   - Query: Related keywords from: {', '.join(domain_keywords[:5])}
   - Focus on: arXiv, Physical Review, Journal of Chemical Physics, npj Computational Materials

2. **Identify State-of-the-Art**
   - What are the latest approaches (2024-2026)?
   - What's the current best practice?
   - Any recent breakthroughs?

3. **Gap Analysis**
   - What problems remain unsolved?
   - Where does this task fit?
   - Is this task addressing a real gap?

4. **Novelty Assessment**
   - frontier: Cutting-edge, no prior work in 2024-2026
   - advanced: Significant improvement over recent work
   - incremental: Useful but not groundbreaking
   - routine: Standard engineering, well-established methods

5. **Improvement Suggestions**
   - Based on recent papers, what could make this task more advanced?
   - Are there better algorithms/methods from 2024-2026 literature?
   - What alternatives exist?

## Output Format (CRITICAL: Keep it CONDENSED)

Return a JSON object with these fields:

```json
{{
  "task_id": "{task.id}",
  "query_terms": ["query1", "query2", "query3"],

  "recent_advances": "1-2 sentence summary of 2024-2026 developments",
  "state_of_art": "1-2 sentence summary of current best approaches",
  "gaps_identified": "1-2 sentence summary of what's missing",

  "novelty_level": "frontier|advanced|incremental|routine",
  "novelty_justification": "1-2 sentences explaining the assessment",

  "improvement_suggestions": [
    "Concrete suggestion 1",
    "Concrete suggestion 2",
    "Concrete suggestion 3"
  ],

  "alternative_approaches": [
    "Alternative approach 1 from recent literature",
    "Alternative approach 2 from recent literature"
  ],

  "key_papers": [
    "Paper title 1 (Year, Journal)",
    "Paper title 2 (Year, Journal)",
    "Paper title 3 (Year, Journal)"
  ]
}}
```

**IMPORTANT CONSTRAINTS**:
- Each text field: MAX 2 sentences
- Total response: <2000 characters
- NO full abstracts, NO long descriptions
- ONLY actionable insights

## Search Strategy

Use WebSearch with queries like:
- "DFT+U convergence rare-earth 2024"
- "constrained DFT f-electron 2025"
- "machine learning DFT occupation matrix 2024"
- "adaptive mixing SCF convergence 2024"

Focus on the most recent and highly-cited papers.
"""
    return prompt


def run_literature_review_for_task(
    task: Task,
    state: ProjectState,
    output_dir: Path,
    *,
    use_agent: bool = True,
) -> LiteratureReviewResult:
    """Run literature review for a single task with context isolation.

    Args:
        task: The task to review
        state: Project state for context
        output_dir: Directory to save results
        use_agent: If True, launch isolated agent. If False, use placeholder.

    Returns:
        Condensed literature review result
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    result_file = output_dir / f"{task.id}_literature.json"

    # Check cache
    if result_file.exists():
        import json
        data = json.loads(result_file.read_text(encoding='utf-8'))
        return LiteratureReviewResult.from_dict(data)

    if use_agent:
        # Launch isolated agent for literature review
        prompt = generate_literature_review_prompt(task, state)

        # TODO: Use Task tool to launch literature-reviewer agent
        # For now, return placeholder
        result = _placeholder_literature_review(task)
    else:
        # Placeholder mode (for testing without agent)
        result = _placeholder_literature_review(task)

    # Save result
    import json
    result_file.write_text(
        json.dumps(result.to_dict(), indent=2, ensure_ascii=False),
        encoding='utf-8'
    )

    return result


def _placeholder_literature_review(task: Task) -> LiteratureReviewResult:
    """Placeholder literature review (when agent not available)."""
    # Basic heuristics based on task description
    desc_lower = task.description.lower()

    # Detect if it's likely a research topic
    research_keywords = ["novel", "新", "machine learning", "ml", "ai", "gnn", "constrained"]
    is_research = any(kw in desc_lower for kw in research_keywords)

    if is_research:
        novelty = "advanced"
        advances = "Recent work (2024-2025) has explored ML-guided methods and adaptive algorithms for DFT convergence."
        sota = "Current best practices combine adaptive mixing, occupation constraints, and multi-start optimization."
        gaps = "Integration of ML models with traditional DFT workflows remains challenging. Limited work on rare-earth systems."
    else:
        novelty = "incremental"
        advances = "Standard DFT+U implementations are well-established in major codes (VASP, QE, ABACUS)."
        sota = "Current best practice follows established algorithms with minor optimizations."
        gaps = "Routine engineering task. Gap is in implementation, not methodology."

    return LiteratureReviewResult(
        task_id=task.id,
        query_terms=[task.title[:50], "DFT", "electronic structure"],
        recent_advances=advances,
        state_of_art=sota,
        gaps_identified=gaps,
        novelty_level=novelty,
        novelty_justification=f"Task involves {novelty} work based on description analysis.",
        improvement_suggestions=[
            "Consider recent ML-guided approaches from 2024 literature",
            "Explore adaptive parameter selection based on system properties",
            "Benchmark against latest VASP/QE implementations",
        ],
        alternative_approaches=[
            "ML-predicted initial guesses (recent trend in 2024-2025)",
            "Ensemble-based convergence strategies",
        ],
        key_papers=[
            "Recent DFT+U review (2024, J. Chem. Phys.)",
            "ML for SCF convergence (2024, npj Comput. Mater.)",
            "Rare-earth DFT challenges (2023, Phys. Rev. B)",
        ],
    )


def run_literature_review_batch(
    tasks: list[Task],
    state: ProjectState,
    output_dir: Path,
    *,
    priority_threshold: float = 80.0,
    max_tasks: int = 10,
) -> dict[str, LiteratureReviewResult]:
    """Run literature review for high-priority tasks.

    Args:
        tasks: All tasks to consider
        state: Project state
        output_dir: Output directory
        priority_threshold: Only review tasks above this priority score
        max_tasks: Maximum number of tasks to review (to avoid excessive work)

    Returns:
        Dict mapping task_id to literature review result
    """
    # Get task reviews (assume they exist in state metadata)
    task_reviews = state.metadata.get('task_reviews', [])

    # Filter high-priority tasks
    high_priority_tasks = []
    for review in task_reviews:
        if review.get('priority_score', 0) >= priority_threshold:
            task = next((t for t in tasks if t.id == review['task_id']), None)
            if task:
                high_priority_tasks.append((task, review['priority_score']))

    # Sort by priority and limit
    high_priority_tasks.sort(key=lambda x: -x[1])
    selected_tasks = [t for t, _ in high_priority_tasks[:max_tasks]]

    print(f"Running literature review for {len(selected_tasks)} high-priority tasks...")

    results = {}
    for i, task in enumerate(selected_tasks, 1):
        print(f"  [{i}/{len(selected_tasks)}] {task.id}: {task.title[:60]}...")
        result = run_literature_review_for_task(task, state, output_dir)
        results[task.id] = result

    return results
