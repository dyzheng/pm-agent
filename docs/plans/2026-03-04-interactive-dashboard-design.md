# Interactive Dashboard Design

**Date:** 2026-03-04
**Status:** Approved

## Problem

The current dashboard (`tools/generate_dashboard.py`) is a static HTML generator that embeds task data as JSON. It has no backend server, no real-time updates, no task dispatching, and no optimization controls. Users must manually re-run the generator to see updated state.

## Requirements

1. **Real-time monitoring** — Task status changes pushed to browser via WebSocket
2. **Task dispatching** — Trigger specialist agent execution from the dashboard
3. **Task optimization** — Run optimizer analysis and apply actions from the dashboard
4. **Human-in-the-loop** — When execution reaches a human review point (plan approval, gate failure, brainstorm decision), the dashboard attracts attention with yellow pulsing cards + notification badges, and provides an inline approval modal
5. **Task lifecycle management** — Defer, split, terminate, restore tasks from the UI

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Browser (Frontend)                 │
│  Existing dashboard.html + interactive enhancements  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐              │
│  │ Monitoring│ │ Dispatch │ │ Optimize │              │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘              │
│       │ WebSocket   │ REST API   │ REST API            │
└───────┼─────────────┼────────────┼───────────────────┘
        │             │            │
┌───────┴─────────────┴────────────┴───────────────────┐
│              FastAPI Server (Backend)                  │
│  ┌──────────────┐ ┌──────────────┐ ┌───────────────┐ │
│  │ WebSocket Hub│ │ REST Routes  │ │ Event Bus     │ │
│  │ (push state) │ │ (CRUD/ops)   │ │ (internal)    │ │
│  └──────┬───────┘ └──────┬───────┘ └───────┬───────┘ │
│         │                │                  │         │
│  ┌──────┴────────────────┴──────────────────┴──────┐ │
│  │              StateManager (state layer)          │ │
│  │  ProjectState <-> JSON file (auto-persist)       │ │
│  └──────────────────────┬──────────────────────────┘ │
│                         │                             │
│  ┌──────────┐ ┌─────────┴──┐ ┌──────────────┐       │
│  │Scheduler │ │Specialist  │ │Optimizer     │       │
│  │          │ │            │ │              │       │
│  └──────────┘ └────────────┘ └──────────────┘       │
└──────────────────────────────────────────────────────┘
```

### Tech Stack

- **Backend:** FastAPI + uvicorn + websockets
- **Frontend:** Vanilla JS (enhance existing HTML template, no build toolchain)
- **Deployment:** Local dev server (`python -m tools.serve`)

## Core Components

### 1. StateManager (`src/server/state_manager.py`)

Thread-safe wrapper around `ProjectState` with change notification.

- `get_state() -> ProjectState` — Read current state
- `update_task(task_id, **changes)` — Modify task + emit event
- `dispatch_tasks(task_ids, mode)` — Start specialist execution in background thread
- `submit_approval(approval_id, decision, feedback)` — Resolve pending approval
- Auto-saves to JSON on every state change
- Uses `threading.Lock` for write serialization

### 2. Event Bus (`src/server/event_bus.py`)

Simple publish-subscribe for internal events.

- `subscribe(event_type, callback)`
- `publish(event_type, payload)`
- Event types: `task_updated`, `approval_needed`, `approval_resolved`, `dispatch_started`, `dispatch_completed`, `optimize_result`, `state_reloaded`

### 3. WebSocket Hub (`src/server/websocket_hub.py`)

Manages browser connections and broadcasts events.

- `connect(websocket)` / `disconnect(websocket)`
- `broadcast(event)` — Send to all connected clients
- Subscribes to Event Bus and forwards all events

### 4. PendingApproval (`src/server/models.py`)

```python
@dataclass
class PendingApproval:
    id: str
    type: str          # "phase_review" | "task_review" | "brainstorm" | "gate_retry"
    task_id: str | None
    title: str
    context: dict      # AI review results, draft preview, etc.
    options: list[str]  # ["approve", "revise", "reject"]
    created_at: float
    resolved: bool = False
    response: str | None = None
    feedback: str | None = None
```

The execution engine's `input_fn` parameter is replaced with an async waiter that creates a `PendingApproval`, broadcasts `approval_needed` via WebSocket, and blocks until the REST API receives a response.

## REST API

```
GET    /api/projects                        # List all projects
GET    /api/projects/{id}                   # Project details + tasks
GET    /api/projects/{id}/tasks             # Task list (?status= filter)
GET    /api/projects/{id}/tasks/{task_id}   # Single task details

PATCH  /api/projects/{id}/tasks/{task_id}   # Modify task status
       body: {"status": "deferred", "defer_trigger": "FE-101:done"}

POST   /api/projects/{id}/dispatch          # Dispatch tasks
       body: {"task_ids": ["FE-205"], "mode": "parallel"}

POST   /api/projects/{id}/optimize          # Trigger optimization
       body: {"optimizations": ["all"]}

POST   /api/approvals/{id}                  # Submit review decision
       body: {"decision": "approve", "feedback": "looks good"}

GET    /api/approvals/pending               # List pending approvals

POST   /api/projects/{id}/brainstorm        # Trigger brainstorm
       body: {"checks": ["novelty_gap", "low_roi"]}
```

## WebSocket Events (`ws://localhost:8000/ws`)

Server -> Browser:
```
{type: "task_updated",       payload: {task_id, old_status, new_status, task}}
{type: "approval_needed",   payload: {id, type, task_id, title, context, options}}
{type: "approval_resolved", payload: {id, decision}}
{type: "dispatch_started",  payload: {task_ids, mode}}
{type: "dispatch_progress", payload: {task_id, stage, message}}
{type: "dispatch_completed",payload: {task_id, success, draft}}
{type: "optimize_result",   payload: {plan_summary, findings_count}}
{type: "state_reloaded",    payload: {tasks, stats}}
```

## Human-in-the-Loop Flow

```
Execution engine hits review point
       │
       ▼
  Creates PendingApproval
       │
       ▼
  Event Bus publishes "approval_needed"
       │
       ▼
  WebSocket Hub broadcasts to browser
       │
       ▼
  Frontend:
  1. Task card turns yellow with pulse animation
  2. Notification badge appears in header (count incremented)
  3. Browser title updates: "(1) PM Dashboard"
  4. Click card → approval modal with:
     - AI review summary
     - Draft/plan content preview
     - File change list
     - Feedback text input
     - [Approve] [Revise] [Reject] buttons
       │
       ▼
  User clicks decision button
       │
       ▼
  POST /api/approvals/{id} {decision, feedback}
       │
       ▼
  StateManager resolves approval → execution continues
```

## Frontend Enhancements

All changes within existing `generate_dashboard.py` HTML template.

### New Visual Elements

| Location | Element | Function |
|----------|---------|----------|
| Header right | Notification bell + badge | Pending approval count, click to expand list |
| Stats bar | "Awaiting" count card | Yellow, shows awaiting-review count |
| Kanban cards | Action buttons (on hover) | Dispatch / Defer / Split shortcuts |
| Task modal | Actions section | Status change, dispatch, view execution log |
| New "Actions" tab | Operations panel | Batch dispatch, optimize trigger, brainstorm |
| Approval modal | Dedicated modal | Review context + approve/revise/reject |

### New Task Visual State: AWAITING_REVIEW

- Yellow pulse animation (distinct from orange in_progress)
- Yellow left border accent
- Bell icon in card header

### WebSocket Client

- Auto-connect on page load
- Exponential backoff reconnect (1s/2s/4s/8s, max 30s)
- On reconnect: request full state sync via `state_reloaded`
- DOM updates applied incrementally (update single card, not full re-render)

## File Structure

```
src/
└── server/
    ├── __init__.py
    ├── app.py              # FastAPI app + route registration
    ├── state_manager.py    # Thread-safe ProjectState wrapper
    ├── event_bus.py        # Publish-subscribe event bus
    ├── websocket_hub.py    # WebSocket connection management
    ├── routes/
    │   ├── __init__.py
    │   ├── projects.py     # Project + task CRUD
    │   ├── dispatch.py     # Task dispatch
    │   ├── optimize.py     # Optimization trigger
    │   └── approvals.py    # Human review
    └── models.py           # Pydantic request/response models

tools/
└── serve.py                # Entry point: python -m tools.serve
```

## Error Handling

| Scenario | Handling |
|----------|----------|
| WebSocket disconnect | Frontend auto-reconnects with exponential backoff; on reconnect, server sends full `state_reloaded` |
| Task execution failure | Mark FAILED, push `task_updated`, frontend shows red + error details |
| Approval timeout | No timeout; pending approvals persist; survive server restart |
| Concurrent writes | `threading.Lock` protects all StateManager writes |
| Server restart | Reload state from JSON; incomplete dispatches marked FAILED |

## Testing

- `tests/test_server/test_state_manager.py` — State read/write + event notification
- `tests/test_server/test_routes.py` — REST API endpoints (httpx TestClient)
- `tests/test_server/test_websocket.py` — WebSocket connection + event push
- `tests/test_server/test_approvals.py` — End-to-end approval flow

## Entry Point

```bash
# Start interactive dashboard
python -m tools.serve projects/f-electron-scf --port 8000

# Opens browser at http://localhost:8000
```
