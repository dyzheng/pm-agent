# Project Lifecycle Improvements Design

**Date:** 2026-02-19
**Status:** Approved

## Problem

PM-Agent 在规划和风险检测上做得好，但在三个方面有明显短板：
1. 没有 velocity 追踪，无法预测项目是否能按时完成
2. 没有立项章程和结项报告，项目的成败判定是模糊的
3. 没有里程碑回顾机制，scope 变更只能被动处理

## Design

### 1. Velocity Tracking + Burndown

**Data layer:** `Task` dataclass 新增 `started_at` / `completed_at` 字段（ISO 时间戳）。Pipeline 在状态变更时自动填写。

**Compute layer:** `src/velocity.py`
- `compute_velocity(tasks, window_weeks=2)` → tasks/week 滑动窗口
- `compute_burndown(tasks, start_date, deadline)` → 每周剩余任务数序列
- `forecast_completion(tasks, deadline)` → 预测完成日期 + 是否超期

**CLI:** `tools/generate_burndown.py`
- 读取 project state，计算 velocity + burndown
- 输出 `burndown.json` 到项目目录
- Dashboard 新增 Burndown tab 展示数据

### 2. Project Charter + Closure Report

**Data layer:** `ProjectState` 新增 `charter: dict` 和 `closure: dict` 字段。

Charter schema:
```python
{
    "goals": ["..."],
    "success_criteria": ["..."],
    "constraints": {"timeline": "...", "resources": "..."},
    "risks": [{"description": "...", "mitigation": "..."}],
    "created_at": "ISO timestamp"
}
```

Closure schema:
```python
{
    "delivered": ["..."],
    "not_delivered": ["..."],
    "metrics": {"velocity": ..., "total_weeks": ..., "tasks_done": ..., "tasks_total": ...},
    "lessons_learned": ["..."],
    "closed_at": "ISO timestamp"
}
```

**Integration:**
- `ProjectRegistry.create_project()` 扩展：自动生成 `charter.md` 模板
- 新增 `ProjectRegistry.close_project()` 方法：从 state 汇总生成 `closure.md`
- CLI: `python -m tools.project_lifecycle charter <project_dir>` / `close <project_dir>`

### 3. Milestone Review + Re-scope

**Hook:** `hooks.yaml` 新增 `after_milestone` 配置。

**Logic:** `src/milestone.py`
- `check_milestone_gate(state, milestone_id)` → 检查覆盖任务完成情况
- `run_milestone_review(state, deadline)` → velocity 预测 + re-scope 建议
- 输出 `MilestoneReview` dataclass（velocity, forecast_date, on_track, rescope_suggestions）

**Re-scope strategy:** 如果预测超期，按 priority score 从低到高建议 defer 任务，直到预测时间 ≤ deadline。

## File Changes

| File | Change |
|------|--------|
| `src/state.py` | Task 加 started_at/completed_at，ProjectState 加 charter/closure |
| `src/velocity.py` | 新文件：velocity 计算 |
| `src/milestone.py` | 新文件：milestone review + re-scope |
| `src/persistence.py` | ProjectRegistry 加 close_project() |
| `tools/generate_burndown.py` | 新文件：CLI 燃尽图生成 |
| `tools/project_lifecycle.py` | 新文件：charter/close CLI |
| `tools/generate_dashboard.py` | Dashboard 加 Burndown tab |
| `hooks.yaml` | 加 after_milestone hook |
| `tests/test_velocity.py` | velocity 测试 |
| `tests/test_milestone.py` | milestone review 测试 |
| `tests/test_lifecycle.py` | charter/closure 测试 |
