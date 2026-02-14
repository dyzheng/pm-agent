"""Generate dashboard HTML from project state.

Reads project state via state_loader, generates a fully self-contained
dashboard.html with task data embedded inline (no fetch needed, works
with file:// protocol).

Usage:
    python -m tools.generate_dashboard projects/f-electron-scf
    python -m tools.generate_dashboard projects/pybind11-interface
    python -m tools.generate_dashboard --all
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from tools.state_loader import find_project_dirs, load_state


DASHBOARD_TEMPLATE = r'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{PROJECT_NAME}} - Dashboard</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{
  --bg:#0f1117;--surface:#1a1d27;--card:#222639;--border:#2e3348;
  --text:#e2e4ed;--text2:#9498b0;--accent:#6c7aed;--accent2:#8b5cf6;
  --green:#22c55e;--green-bg:rgba(34,197,94,.12);
  --blue:#3b82f6;--blue-bg:rgba(59,130,246,.12);
  --orange:#f59e0b;--orange-bg:rgba(245,158,11,.12);
  --red:#ef4444;--red-bg:rgba(239,68,68,.12);
  --purple:#a78bfa;--purple-bg:rgba(167,139,250,.12);
  --gray:#6b7280;--gray-bg:rgba(107,114,128,.12);
}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Noto Sans SC',sans-serif;background:var(--bg);color:var(--text);line-height:1.6;min-height:100vh}
a{color:var(--accent);text-decoration:none}

.header{padding:32px 40px 24px;border-bottom:1px solid var(--border);background:linear-gradient(135deg,#13151f 0%,#1a1d2e 100%)}
.header h1{font-size:28px;font-weight:700;letter-spacing:-.5px;background:linear-gradient(135deg,var(--accent),var(--accent2));-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.header .subtitle{color:var(--text2);font-size:14px;margin-top:4px}

.stats-bar{display:flex;gap:16px;padding:20px 40px;flex-wrap:wrap}
.stat-card{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:16px 24px;min-width:120px;flex:1}
.stat-card .label{font-size:12px;color:var(--text2);text-transform:uppercase;letter-spacing:.5px;margin-bottom:4px}
.stat-card .value{font-size:28px;font-weight:700}
.stat-card .value.total{color:var(--accent)}
.stat-card .value.pending{color:var(--blue)}
.stat-card .value.progress{color:var(--orange)}
.stat-card .value.review{color:var(--purple)}
.stat-card .value.done{color:var(--green)}
.stat-card .value.deferred{color:var(--gray)}

.tabs{display:flex;gap:4px;padding:0 40px;border-bottom:1px solid var(--border);background:var(--surface)}
.tab{padding:14px 24px;cursor:pointer;font-size:14px;font-weight:500;color:var(--text2);border-bottom:2px solid transparent;transition:all .2s;background:none;border-top:none;border-left:none;border-right:none}
.tab:hover{color:var(--text)}
.tab.active{color:var(--accent);border-bottom-color:var(--accent)}

.content{padding:24px 40px 60px}
.view{display:none}
.view.active{display:block}

/* Kanban */
.kanban{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:20px}
.column{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:16px}
.column-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;padding-bottom:12px;border-bottom:1px solid var(--border)}
.column-header .title{font-weight:600;font-size:15px}
.column-header .count{background:var(--card);padding:2px 10px;border-radius:12px;font-size:12px;color:var(--text2)}

.task-card{background:var(--card);border:1px solid var(--border);border-radius:8px;padding:14px;margin-bottom:10px;cursor:pointer;transition:all .15s;border-left:3px solid var(--blue)}
.task-card:hover{border-color:var(--accent);transform:translateX(3px)}
.task-card.status-pending{border-left-color:var(--blue)}
.task-card.status-in_progress{border-left-color:var(--orange)}
.task-card.status-in_review{border-left-color:var(--purple)}
.task-card.status-done{border-left-color:var(--green)}
.task-card.status-deferred{border-left-color:var(--gray)}
.task-card.status-failed{border-left-color:var(--red)}
.task-card .task-id{font-size:11px;color:var(--text2);margin-bottom:4px;font-family:monospace}
.task-card .task-title{font-weight:500;font-size:14px;margin-bottom:8px;line-height:1.4}
.task-card .task-meta{display:flex;gap:6px;flex-wrap:wrap}

.badge{font-size:10px;padding:2px 8px;border-radius:4px;font-weight:500}
.badge.layer{background:var(--orange-bg);color:var(--orange)}
.badge.risk-low{background:var(--green-bg);color:var(--green)}
.badge.risk-medium{background:var(--orange-bg);color:var(--orange)}
.badge.risk-high{background:var(--red-bg);color:var(--red)}
.badge.type{background:var(--purple-bg);color:var(--purple)}
.badge.batch{background:var(--blue-bg);color:var(--blue)}
.badge.phase{background:var(--accent);background:rgba(108,122,237,.15);color:var(--accent)}

/* Timeline */
.timeline{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:24px}
.phase-section{margin-bottom:28px}
.phase-header{font-size:16px;font-weight:600;margin-bottom:14px;padding:12px 16px;background:var(--card);border-radius:8px;border-left:3px solid var(--accent)}
.phase-tasks{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:10px;margin-left:16px}

/* Graph */
.graph-container{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:24px}
.graph-container h2{margin-bottom:16px;font-size:18px}
#dep-graph-svg{width:100%;min-height:400px;border:1px solid var(--border);border-radius:8px;overflow:auto;background:var(--card);padding:16px}
#dep-graph-svg svg{max-width:100%}
.graph-fallback{padding:40px;text-align:center;color:var(--text2)}
.graph-fallback pre{text-align:left;background:var(--card);padding:16px;border-radius:8px;margin-top:16px;overflow-x:auto;font-size:12px}

/* Deferred */
.deferred-section{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:24px}
.deferred-section h2{margin-bottom:16px;font-size:18px}
.deferred-card{background:var(--card);border:1px solid var(--border);border-left:3px solid var(--orange);border-radius:8px;padding:16px;margin-bottom:12px}
.deferred-card .trigger-info{background:rgba(245,158,11,.08);padding:10px 12px;border-radius:6px;margin-top:10px;font-size:13px}
.deferred-card .trigger-label{font-weight:600;color:var(--orange);margin-bottom:4px;font-size:12px}

/* Modal */
.modal-overlay{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,.6);z-index:1000;align-items:center;justify-content:center}
.modal-overlay.active{display:flex}
.modal{background:var(--surface);border:1px solid var(--border);border-radius:16px;padding:32px;max-width:640px;width:90%;max-height:80vh;overflow-y:auto}
.modal-header{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:20px;padding-bottom:16px;border-bottom:1px solid var(--border)}
.modal-header h3{font-size:18px;font-weight:600}
.modal-close{background:none;border:none;color:var(--text2);font-size:24px;cursor:pointer;padding:4px 8px}
.modal-close:hover{color:var(--text)}
.modal-section{margin-bottom:18px}
.modal-section h4{font-size:12px;text-transform:uppercase;color:var(--text2);letter-spacing:.5px;margin-bottom:8px}
.modal-section p,.modal-section li{font-size:14px;line-height:1.6}
.modal-section ul{padding-left:20px}
.modal-section code{background:var(--card);padding:2px 6px;border-radius:4px;font-size:13px}

.loading{text-align:center;padding:60px;color:var(--text2);font-size:16px}
.error{text-align:center;padding:60px;color:var(--red)}
</style>
</head>
<body>

<div class="header">
  <h1>{{PROJECT_NAME}}</h1>
  <div class="subtitle">{{PROJECT_ID}} &mdash; Generated by pm-agent tools</div>
</div>

<div class="stats-bar" id="stats-bar"></div>

<div class="tabs" id="tabs-bar">
  <button class="tab active" data-view="kanban">Kanban</button>
  <button class="tab" data-view="timeline">Timeline</button>
  <button class="tab" data-view="graph">Dependencies</button>
  <button class="tab" data-view="deferred">Deferred</button>
</div>

<div class="content">
  <div id="kanban-view" class="view active"></div>
  <div id="timeline-view" class="view"></div>
  <div id="graph-view" class="view"></div>
  <div id="deferred-view" class="view"></div>
</div>

<div class="modal-overlay" id="modal-overlay">
  <div class="modal">
    <div class="modal-header">
      <h3 id="modal-title"></h3>
      <button class="modal-close" onclick="closeModal()">&times;</button>
    </div>
    <div id="modal-body"></div>
  </div>
</div>

<script>
// Task data embedded at generation time — no fetch needed, works with file:// protocol
let tasks = {{TASKS_JSON}};

function init() {
  render();
}

function render() {
  renderStats();
  renderKanban();
  renderTimeline();
  renderGraph();
  renderDeferred();
}

function renderStats() {
  const bar = document.getElementById('stats-bar');
  const counts = {
    total: tasks.length,
    pending: tasks.filter(t => t.status === 'pending').length,
    in_progress: tasks.filter(t => t.status === 'in_progress').length,
    in_review: tasks.filter(t => t.status === 'in_review').length,
    done: tasks.filter(t => t.status === 'done').length,
    deferred: tasks.filter(t => t.status === 'deferred').length,
  };
  bar.innerHTML = [
    ['Total', counts.total, 'total'],
    ['Pending', counts.pending, 'pending'],
    ['In Progress', counts.in_progress, 'progress'],
    ['In Review', counts.in_review, 'review'],
    ['Done', counts.done, 'done'],
    ['Deferred', counts.deferred, 'deferred'],
  ].map(([label, val, cls]) =>
    `<div class="stat-card"><div class="label">${label}</div><div class="value ${cls}">${val}</div></div>`
  ).join('');
}

/* --- Kanban --- */
function detectGrouping() {
  // Auto-detect best grouping strategy
  const hasPhase = tasks.some(t => t.phase || (t.id && /^[A-Z]+-\d/.test(t.id)));
  const hasBatch = tasks.some(t => t.batch !== undefined && t.batch !== null);

  if (hasPhase) return 'phase';
  if (hasBatch) return 'batch';
  return 'status';
}

function groupByPhase() {
  // Try to extract phase from task ID pattern (FE-0xx, PB-1xx, SC-0xx)
  const groups = {};
  tasks.forEach(t => {
    let phase = t.phase || '';
    if (!phase && t.id) {
      const m = t.id.match(/^[A-Z]+-(\d)/);
      if (m) phase = 'Phase ' + m[1];
      else if (t.id.match(/^[A-Z]+-D/)) phase = 'Deferred';
    }
    if (!phase) phase = 'Other';
    (groups[phase] = groups[phase] || []).push(t);
  });
  return groups;
}

function groupByBatch() {
  const groups = {};
  tasks.forEach(t => {
    const batch = t.batch !== undefined ? 'Batch ' + t.batch : 'Unassigned';
    (groups[batch] = groups[batch] || []).push(t);
  });
  return groups;
}

function groupByStatus() {
  const order = ['pending', 'in_progress', 'in_review', 'done', 'deferred'];
  const labels = {pending:'Pending',in_progress:'In Progress',in_review:'In Review',done:'Done',deferred:'Deferred'};
  const groups = {};
  order.forEach(s => { groups[labels[s] || s] = []; });
  tasks.forEach(t => {
    const label = labels[t.status] || t.status || 'Pending';
    (groups[label] = groups[label] || []).push(t);
  });
  return groups;
}

function renderKanban() {
  const view = document.getElementById('kanban-view');
  const strategy = detectGrouping();
  let groups;
  if (strategy === 'phase') groups = groupByPhase();
  else if (strategy === 'batch') groups = groupByBatch();
  else groups = groupByStatus();

  let html = '<div class="kanban">';
  for (const [name, items] of Object.entries(groups)) {
    if (items.length === 0) continue;
    html += `<div class="column">
      <div class="column-header">
        <span class="title">${name}</span>
        <span class="count">${items.length}</span>
      </div>`;
    items.forEach(t => { html += taskCard(t); });
    html += '</div>';
  }
  html += '</div>';
  view.innerHTML = html;
  bindCardClicks(view);
}

function taskCard(t) {
  const statusIcon = {pending:'\u23f3',in_progress:'\ud83d\udd04',in_review:'\ud83d\udd0d',done:'\u2705',failed:'\u274c',deferred:'\u23f8\ufe0f'}[t.status] || '';
  let meta = '';
  if (t.layer) meta += `<span class="badge layer">${t.layer}</span>`;
  if (t.type) meta += `<span class="badge type">${t.type}</span>`;
  if (t.risk_level) meta += `<span class="badge risk-${t.risk_level}">${t.risk_level}</span>`;
  if (t.batch !== undefined && t.batch !== null) meta += `<span class="badge batch">B${t.batch}</span>`;
  return `<div class="task-card status-${t.status}" data-id="${t.id}">
    <div class="task-id">${statusIcon} ${t.id}</div>
    <div class="task-title">${esc(t.title)}</div>
    <div class="task-meta">${meta}</div>
  </div>`;
}

/* --- Timeline --- */
function renderTimeline() {
  const view = document.getElementById('timeline-view');
  const groups = groupByPhase();
  let html = '<div class="timeline">';
  for (const [name, items] of Object.entries(groups)) {
    const active = items.filter(t => t.status !== 'deferred');
    if (active.length === 0) continue;
    html += `<div class="phase-section">
      <div class="phase-header">${name} (${active.length})</div>
      <div class="phase-tasks">`;
    active.forEach(t => { html += taskCard(t); });
    html += '</div></div>';
  }
  html += '</div>';
  view.innerHTML = html;
  bindCardClicks(view);
}

/* --- Dependency Graph (text-based) --- */
function renderGraph() {
  const view = document.getElementById('graph-view');
  const withDeps = tasks.filter(t => (t.dependencies && t.dependencies.length > 0) || tasks.some(o => (o.dependencies || []).includes(t.id)));
  if (withDeps.length === 0) {
    view.innerHTML = '<div class="graph-container"><h2>Dependencies</h2><div class="graph-fallback">No dependency information available.</div></div>';
    return;
  }

  // Build adjacency for a simple text-based visualization
  let dot = 'digraph G {\\n  rankdir=LR;\\n';
  const statusColor = {pending:'#3b82f6',in_progress:'#f59e0b',in_review:'#a78bfa',done:'#22c55e',deferred:'#6b7280',failed:'#ef4444'};
  tasks.forEach(t => {
    const c = statusColor[t.status] || '#3b82f6';
    const label = t.id + '\\\\n' + (t.title||'').substring(0,25);
    dot += `  "${t.id}" [label="${label}" fillcolor="${c}" style="filled,rounded" shape=box];\\n`;
  });
  tasks.forEach(t => {
    (t.dependencies || []).forEach(d => { dot += `  "${d}" -> "${t.id}";\\n`; });
    (t.suspended_dependencies || []).forEach(d => { dot += `  "${d}" -> "${t.id}" [style=dashed color=gray];\\n`; });
  });
  dot += '}';

  // Show as text + link to SVG if available
  let html = '<div class="graph-container"><h2>Task Dependencies</h2>';
  html += '<div id="dep-graph-svg">';
  // Inline SVG if embedded at generation time
  const inlineSvg = document.getElementById('embedded-svg');
  if (inlineSvg && inlineSvg.textContent.trim()) {
    html += inlineSvg.textContent;
  } else {
    html += '<div class="graph-fallback">';
    html += '<p>Dependency graph (DOT format). Run <code>python -m tools.generate_graph</code> to generate SVG.</p>';
    html += '<pre>' + dot.replace(/\\n/g, '\n') + '</pre>';
    html += '</div>';
  }
  html += '</div></div>';
  view.innerHTML = html;
}

/* --- Deferred --- */
function renderDeferred() {
  const view = document.getElementById('deferred-view');
  const deferred = tasks.filter(t => t.status === 'deferred');
  let html = '<div class="deferred-section"><h2>Deferred Tasks</h2>';
  if (deferred.length === 0) {
    html += '<div style="text-align:center;padding:40px;color:var(--text2)">No deferred tasks</div>';
  } else {
    deferred.forEach(t => {
      html += `<div class="deferred-card" data-id="${t.id}">
        <div class="task-id">${t.id}</div>
        <div class="task-title" style="font-size:15px;margin:8px 0">${esc(t.title)}</div>
        <div class="task-meta">`;
      if (t.layer) html += `<span class="badge layer">${t.layer}</span>`;
      if (t.risk_level) html += `<span class="badge risk-${t.risk_level}">${t.risk_level}</span>`;
      html += '</div>';
      if (t.defer_trigger) {
        html += `<div class="trigger-info"><div class="trigger-label">Trigger Condition</div><div>${esc(t.defer_trigger)}</div></div>`;
      }
      if (t.description) {
        html += `<div style="margin-top:10px;font-size:13px;color:var(--text2)">${esc(t.description).substring(0,200)}</div>`;
      }
      html += '</div>';
    });
  }
  html += '</div>';
  view.innerHTML = html;
  bindCardClicks(view);
}

/* --- Modal --- */
function showModal(task) {
  const overlay = document.getElementById('modal-overlay');
  document.getElementById('modal-title').textContent = task.id + ': ' + task.title;
  const statusLabels = {pending:'Pending',in_progress:'In Progress',in_review:'In Review',done:'Done',deferred:'Deferred',failed:'Failed'};
  let body = '';
  if (task.description) body += `<div class="modal-section"><h4>Description</h4><p>${esc(task.description)}</p></div>`;
  body += '<div class="modal-section"><h4>Metadata</h4>';
  body += `<p><strong>Status:</strong> ${statusLabels[task.status]||task.status}</p>`;
  if (task.layer) body += `<p><strong>Layer:</strong> ${task.layer}</p>`;
  if (task.type) body += `<p><strong>Type:</strong> ${task.type}</p>`;
  if (task.risk_level) body += `<p><strong>Risk:</strong> ${task.risk_level}</p>`;
  if (task.specialist) body += `<p><strong>Specialist:</strong> ${task.specialist}</p>`;
  if (task.batch !== undefined) body += `<p><strong>Batch:</strong> ${task.batch}</p>`;
  body += '</div>';
  if (task.defer_trigger) body += `<div class="modal-section"><h4>Trigger Condition</h4><p style="background:var(--orange-bg);padding:10px;border-radius:6px">${esc(task.defer_trigger)}</p></div>`;
  const deps = task.dependencies || [];
  if (deps.length) body += `<div class="modal-section"><h4>Dependencies (${deps.length})</h4><ul>${deps.map(d=>'<li>'+d+'</li>').join('')}</ul></div>`;
  const criteria = task.acceptance_criteria || [];
  if (criteria.length) body += `<div class="modal-section"><h4>Acceptance Criteria</h4><ul>${criteria.map(c=>'<li>'+esc(c)+'</li>').join('')}</ul></div>`;
  const files = task.files_to_touch || [];
  if (files.length) body += `<div class="modal-section"><h4>Files</h4><ul>${files.map(f=>'<li><code>'+esc(f)+'</code></li>').join('')}</ul></div>`;
  document.getElementById('modal-body').innerHTML = body;
  overlay.classList.add('active');
}

function closeModal() {
  document.getElementById('modal-overlay').classList.remove('active');
}

document.getElementById('modal-overlay').addEventListener('click', e => {
  if (e.target.id === 'modal-overlay') closeModal();
});

/* --- Tabs --- */
document.querySelectorAll('.tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    tab.classList.add('active');
    document.getElementById(tab.dataset.view + '-view').classList.add('active');
  });
});

/* --- Helpers --- */
function esc(s) { if (!s) return ''; const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }

function bindCardClicks(container) {
  container.querySelectorAll('.task-card, .deferred-card').forEach(card => {
    card.addEventListener('click', () => {
      const id = card.dataset.id;
      const task = tasks.find(t => t.id === id);
      if (task) showModal(task);
    });
  });
}

init();
</script>
<!-- Embedded SVG for dependency graph (avoids file:// CORS issues) -->
<script type="text/plain" id="embedded-svg">{{EMBEDDED_SVG}}</script>
</body>
</html>'''


def generate_dashboard(project_dir: Path) -> bool:
    """Generate dashboard.html for a project.

    Embeds task data and SVG inline so the HTML is fully self-contained
    and works when opened via file:// protocol.

    Returns True if dashboard was generated, False if no tasks found.
    """
    state = load_state(project_dir)
    tasks = state["tasks"]

    if not tasks:
        return False

    # Serialize tasks to JSON for inline embedding
    tasks_json = json.dumps(tasks, ensure_ascii=False)

    # Try to read existing SVG for inline embedding
    svg_path = project_dir / "dependency_graph.svg"
    embedded_svg = ""
    if svg_path.exists():
        try:
            embedded_svg = svg_path.read_text()
        except OSError:
            pass

    html = DASHBOARD_TEMPLATE
    html = html.replace("{{PROJECT_NAME}}", state["name"])
    html = html.replace("{{PROJECT_ID}}", state["project_id"])
    html = html.replace("{{TASKS_JSON}}", tasks_json)
    html = html.replace("{{EMBEDDED_SVG}}", embedded_svg)

    out_path = project_dir / "dashboard.html"
    out_path.write_text(html)
    print(f"  Generated: {out_path}")
    return True


def main() -> None:
    args = sys.argv[1:]

    if not args or args[0] == "--help":
        print("Usage: python -m tools.generate_dashboard <project_dir>")
        print("       python -m tools.generate_dashboard --all")
        sys.exit(0)

    if args[0] == "--all":
        dirs = find_project_dirs()
        if not dirs:
            print("No projects found in projects/")
            sys.exit(1)
        for d in dirs:
            print(f"\n=== {d.name} ===")
            if not generate_dashboard(d):
                print("  No tasks found, skipping")
    else:
        project_dir = Path(args[0])
        if not project_dir.exists():
            print(f"Project directory not found: {project_dir}")
            sys.exit(1)
        print(f"=== {project_dir.name} ===")
        if not generate_dashboard(project_dir):
            print("  No tasks found")


if __name__ == "__main__":
    main()
