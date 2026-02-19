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


def _load_project_extra(project_dir: Path) -> dict:
    """Load extra project data: meta, milestones, literature, research."""
    extra: dict = {
        "meta": {},
        "milestones": [],
        "literature": [],
        "description": "",
        "timeline": "",
        "critical_path": "",
        "phases": {},
    }

    # Try project_state_meta.json first, then fall back to project_state.json
    def _extract_meta(data: dict) -> None:
        md = data.get("metadata", data)
        if not extra["description"]:
            extra["description"] = data.get("request", "")
        if not extra["timeline"]:
            extra["timeline"] = md.get("timeline", "")
        if not extra["critical_path"]:
            extra["critical_path"] = md.get("critical_path", "")
        if not extra["phases"]:
            extra["phases"] = md.get("phases", {})
        if not extra["milestones"]:
            raw_ms = md.get("milestones", {})
            if isinstance(raw_ms, dict):
                for k, v in raw_ms.items():
                    extra["milestones"].append({"id": k, "description": v})

    for candidate in [
        project_dir / "state" / "project_state_meta.json",
        project_dir / "state" / "project_state.json",
    ]:
        if candidate.exists():
            try:
                data = json.loads(candidate.read_text())
                extra["meta"] = extra["meta"] or data
                _extract_meta(data)
            except (json.JSONDecodeError, OSError):
                pass

    # project.json fallback for description
    pj_path = project_dir / "project.json"
    if pj_path.exists() and not extra["description"]:
        try:
            pj = json.loads(pj_path.read_text())
            extra["description"] = pj.get("request", pj.get("name", ""))
        except (json.JSONDecodeError, OSError):
            pass

    # Literature summary
    lit_path = project_dir / "research" / "literature" / "summary.json"
    if lit_path.exists():
        try:
            lit = json.loads(lit_path.read_text())
            if isinstance(lit, dict):
                for tid, entry in lit.items():
                    extra["literature"].append(entry)
        except (json.JSONDecodeError, OSError):
            pass

    # Individual literature files for richer data
    lit_dir = project_dir / "research" / "literature"
    if lit_dir.exists():
        for f in sorted(lit_dir.glob("*_literature.json")):
            if f.name == "summary.json":
                continue
            try:
                data = json.loads(f.read_text())
                # Merge into existing entry or add new
                tid = data.get("task_id", f.stem.replace("_literature", ""))
                found = False
                for entry in extra["literature"]:
                    if entry.get("task_id") == tid:
                        entry.update(data)
                        found = True
                        break
                if not found:
                    extra["literature"].append(data)
            except (json.JSONDecodeError, OSError):
                pass

    # Research task notes (markdown files)
    research_dir = project_dir / "research" / "tasks"
    if research_dir.exists():
        for f in sorted(research_dir.glob("*_research.md")):
            tid = f.stem.replace("_research", "")
            for entry in extra["literature"]:
                if entry.get("task_id") == tid and "research_notes" not in entry:
                    # Extract references section from markdown
                    text = f.read_text()
                    refs = []
                    in_refs = False
                    for line in text.split("\n"):
                        if line.strip().startswith("## References") or line.strip().startswith("### Primary"):
                            in_refs = True
                            continue
                        if in_refs and line.startswith("## "):
                            break
                        if in_refs and line.strip().startswith(("1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.", "9.")):
                            refs.append(line.strip())
                    if refs:
                        entry["detailed_refs"] = refs

    return extra


DASHBOARD_TEMPLATE = r'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{PROJECT_NAME}} — PM Agent</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;700&family=Crimson+Pro:ital,wght@0,300;0,400;0,600;1,300&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{
  --bg:#06080c;--bg2:#090c12;--surface:#0d1018;
  --card:#111520;--card2:#161b26;
  --border:#1c2235;--border2:#242d42;
  --text:#d4cfc4;--text2:#7a7d8a;--text3:#4a4d5a;
  --amber:#f5a623;--amber2:#e8941a;--amber-dim:#c47d10;
  --amber-bg:rgba(245,166,35,.07);--amber-glow:rgba(245,166,35,.15);
  --green:#4ade80;--green-bg:rgba(74,222,128,.07);
  --blue:#60a5fa;--blue-bg:rgba(96,165,250,.07);
  --orange:#fb923c;--orange-bg:rgba(251,146,60,.07);
  --red:#f87171;--red-bg:rgba(248,113,113,.07);
  --purple:#c084fc;--purple-bg:rgba(192,132,252,.07);
  --gray:#4b5563;--gray-bg:rgba(75,85,99,.07);
  --mono:'JetBrains Mono',monospace;
  --serif:'Crimson Pro',Georgia,serif;
}
body::before{
  content:'';position:fixed;top:0;left:0;width:100%;height:100%;
  background:repeating-linear-gradient(0deg,transparent,transparent 2px,rgba(0,0,0,.06) 2px,rgba(0,0,0,.06) 4px);
  pointer-events:none;z-index:9999;
}
body{
  font-family:var(--mono);background:var(--bg);color:var(--text);
  line-height:1.6;min-height:100vh;
  background-image:radial-gradient(ellipse 80% 50% at 50% -10%,rgba(245,166,35,.04) 0%,transparent 60%);
}

/* ── HEADER ── */
.header{
  padding:28px 48px 22px;border-bottom:1px solid var(--border);
  display:flex;align-items:flex-end;justify-content:space-between;gap:24px;
  position:relative;overflow:hidden;
}
.header::after{content:'';position:absolute;bottom:0;left:0;right:0;height:1px;background:linear-gradient(90deg,transparent,var(--amber-dim),transparent)}
.header-label{font-size:10px;letter-spacing:.2em;color:var(--amber-dim);text-transform:uppercase;margin-bottom:6px;font-weight:500}
.header h1{font-family:var(--serif);font-size:26px;font-weight:300;color:var(--text);letter-spacing:.02em;line-height:1.2}
.header h1 em{font-style:italic;color:var(--amber)}
.header-right{text-align:right;font-size:11px;color:var(--text3);line-height:1.8}
.header-right .proj-id{font-size:13px;color:var(--amber-dim);letter-spacing:.05em}

/* ── STATS BAR ── */
.stats-bar{display:flex;gap:1px;border-bottom:1px solid var(--border);background:var(--border)}
.stat-card{background:var(--surface);padding:18px 28px;flex:1;min-width:100px;position:relative;transition:background .15s}
.stat-card:hover{background:var(--card)}
.stat-card .label{font-size:9px;letter-spacing:.18em;color:var(--text3);text-transform:uppercase;margin-bottom:8px;font-weight:500}
.stat-card .value{font-size:32px;font-weight:300;font-family:var(--mono);line-height:1}
.stat-card .unit{font-size:9px;color:var(--text3);margin-top:4px;letter-spacing:.1em}
.stat-card .value.total{color:var(--amber)}
.stat-card .value.pending{color:var(--blue)}
.stat-card .value.progress{color:var(--orange)}
.stat-card .value.review{color:var(--purple)}
.stat-card .value.done{color:var(--green)}
.stat-card .value.deferred{color:var(--gray)}
.stat-card .value.failed{color:var(--red)}
.stat-bar{position:absolute;bottom:0;left:0;height:2px;background:currentColor;opacity:.4;transition:width .6s cubic-bezier(.4,0,.2,1)}

/* ── TABS ── */
.tabs{display:flex;gap:0;border-bottom:1px solid var(--border);background:var(--bg2);padding:0 48px;overflow-x:auto}
.tab{padding:13px 20px;cursor:pointer;font-size:10px;font-weight:500;letter-spacing:.12em;text-transform:uppercase;color:var(--text3);border:none;background:none;border-bottom:2px solid transparent;transition:all .15s;position:relative;white-space:nowrap}
.tab:hover{color:var(--text2)}
.tab.active{color:var(--amber);border-bottom-color:var(--amber)}

/* ── CONTENT ── */
.content{padding:32px 48px 80px}
.view{display:none}
.view.active{display:block}

/* ── SECTION HEADER ── */
.section-h{font-size:10px;letter-spacing:.2em;text-transform:uppercase;color:var(--amber-dim);margin-bottom:20px;padding-bottom:10px;border-bottom:1px solid var(--border);font-weight:500}

/* ── OVERVIEW ── */
.overview-grid{display:grid;grid-template-columns:1fr 1fr;gap:20px}
@media(max-width:900px){.overview-grid{grid-template-columns:1fr}}
.overview-card{background:var(--surface);border:1px solid var(--border);padding:24px}
.overview-card h3{font-size:10px;letter-spacing:.18em;text-transform:uppercase;color:var(--amber-dim);margin-bottom:14px;font-weight:500}
.overview-card p{font-size:13px;line-height:1.8;color:var(--text2);font-family:var(--serif)}
.overview-card .mono{font-family:var(--mono);font-size:11px;color:var(--text);line-height:2}
.overview-full{grid-column:1/-1}
.critical-path{font-family:var(--mono);font-size:11px;color:var(--text2);background:var(--card);padding:14px 18px;border:1px solid var(--border);overflow-x:auto;white-space:nowrap;line-height:1.8}
.critical-path .arrow{color:var(--amber-dim);margin:0 4px}

/* ── MILESTONES ── */
.milestones{display:grid;gap:0;border:1px solid var(--border)}
.milestone-row{display:grid;grid-template-columns:80px 1fr;border-bottom:1px solid var(--border);transition:background .12s}
.milestone-row:last-child{border-bottom:none}
.milestone-row:hover{background:var(--card)}
.milestone-id{padding:16px 20px;background:var(--surface);border-right:1px solid var(--border);display:flex;align-items:center;justify-content:center}
.milestone-id span{font-size:14px;font-weight:500;color:var(--amber)}
.milestone-body{padding:14px 20px}
.milestone-body .ms-desc{font-size:13px;color:var(--text);font-family:var(--serif);line-height:1.6}
.milestone-body .ms-gate{font-size:11px;color:var(--text3);margin-top:6px}
.milestone-body .ms-gate em{color:var(--text2);font-style:normal}
.ms-progress{height:3px;background:var(--border);margin-top:10px;position:relative}
.ms-progress-fill{height:100%;background:var(--amber);transition:width .6s}

/* ── KANBAN ── */
.kanban{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:16px}
.column{background:var(--surface);border:1px solid var(--border);border-top:2px solid var(--border2)}
.column-header{display:flex;justify-content:space-between;align-items:center;padding:12px 16px;border-bottom:1px solid var(--border);background:var(--card)}
.column-header .title{font-size:10px;letter-spacing:.15em;text-transform:uppercase;color:var(--text2);font-weight:500}
.column-header .count{font-size:11px;color:var(--amber-dim);font-family:var(--mono)}
.column-body{padding:12px}

/* ── TASK CARD ── */
.task-card{background:var(--card);border:1px solid var(--border);padding:12px 14px;margin-bottom:8px;cursor:pointer;transition:border-color .12s,background .12s;position:relative;clip-path:polygon(0 0,calc(100% - 10px) 0,100% 10px,100% 100%,0 100%)}
.task-card::before{content:'';position:absolute;top:0;left:0;right:0;height:1px;background:linear-gradient(90deg,var(--status-color,var(--border2)),transparent);opacity:.6}
.task-card:hover{background:var(--card2);border-color:var(--border2)}
.task-card:hover::before{opacity:1}
.task-card.status-pending{--status-color:var(--blue)}
.task-card.status-in_progress{--status-color:var(--orange)}
.task-card.status-in_review{--status-color:var(--purple)}
.task-card.status-done{--status-color:var(--green)}
.task-card.status-deferred{--status-color:var(--gray)}
.task-card.status-failed,.task-card.status-terminated{--status-color:var(--red)}
.task-card .task-header{display:flex;align-items:center;gap:8px;margin-bottom:7px}
.task-card .task-id{font-size:10px;color:var(--amber-dim);letter-spacing:.06em;font-weight:500}
.status-dot{width:6px;height:6px;border-radius:50%;background:var(--status-color,var(--border2));flex-shrink:0}
.status-dot.pulse{animation:pulse 2s ease-in-out infinite}
@keyframes pulse{0%,100%{opacity:1;box-shadow:0 0 0 0 var(--status-color)}50%{opacity:.7;box-shadow:0 0 0 4px transparent}}
.task-card .task-title{font-size:12px;line-height:1.5;color:var(--text);font-family:var(--serif);font-weight:300;letter-spacing:.01em;margin-bottom:8px}
.task-card .task-meta{display:flex;gap:5px;flex-wrap:wrap}

/* ── BADGES ── */
.badge{font-size:9px;padding:2px 7px;letter-spacing:.08em;text-transform:uppercase;font-weight:500;font-family:var(--mono);border:1px solid currentColor;opacity:.8}
.badge.layer{color:var(--orange);border-color:rgba(251,146,60,.3);background:var(--orange-bg)}
.badge.risk-low{color:var(--green);border-color:rgba(74,222,128,.3);background:var(--green-bg)}
.badge.risk-medium{color:var(--orange);border-color:rgba(251,146,60,.3);background:var(--orange-bg)}
.badge.risk-high{color:var(--red);border-color:rgba(248,113,113,.3);background:var(--red-bg)}
.badge.type{color:var(--purple);border-color:rgba(192,132,252,.3);background:var(--purple-bg)}
.badge.batch{color:var(--blue);border-color:rgba(96,165,250,.3);background:var(--blue-bg)}
.badge.phase{color:var(--amber-dim);border-color:rgba(245,166,35,.3);background:var(--amber-bg)}
.badge.novelty-frontier{color:var(--amber);border-color:rgba(245,166,35,.4);background:var(--amber-bg)}
.badge.novelty-advanced{color:var(--purple);border-color:rgba(192,132,252,.3);background:var(--purple-bg)}
.badge.novelty-incremental{color:var(--text3);border-color:var(--border2);background:var(--gray-bg)}

/* ── TIMELINE ── */
.phase-section{margin-bottom:32px}
.phase-header{font-size:10px;letter-spacing:.2em;text-transform:uppercase;color:var(--amber-dim);font-weight:500;padding:10px 0;border-bottom:1px solid var(--border);margin-bottom:14px;display:flex;align-items:center;gap:12px}
.phase-header::before{content:'';width:20px;height:1px;background:var(--amber-dim)}
.phase-tasks{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:8px;padding-left:32px}

/* ── REFERENCES ── */
.ref-grid{display:grid;gap:16px}
.ref-card{background:var(--surface);border:1px solid var(--border);padding:20px 24px;transition:background .12s}
.ref-card:hover{background:var(--card)}
.ref-card-header{display:flex;align-items:center;gap:10px;margin-bottom:12px}
.ref-card-header .ref-tid{font-size:11px;color:var(--amber);font-weight:500}
.ref-card-header .ref-title{font-size:13px;color:var(--text);font-family:var(--serif)}
.ref-meta{display:flex;gap:8px;margin-bottom:12px;flex-wrap:wrap}
.ref-section{margin-bottom:14px}
.ref-section h5{font-size:9px;letter-spacing:.15em;text-transform:uppercase;color:var(--text3);margin-bottom:6px;font-weight:500}
.ref-section p{font-size:12px;line-height:1.7;color:var(--text2)}
.ref-section ul{padding-left:16px;list-style:none}
.ref-section ul li{font-size:12px;line-height:1.8;color:var(--text2);position:relative;padding-left:12px}
.ref-section ul li::before{content:'';position:absolute;left:0;top:9px;width:4px;height:4px;background:var(--amber-dim);border-radius:50%}
.ref-papers{border-top:1px solid var(--border);padding-top:12px;margin-top:12px}
.ref-papers h5{font-size:9px;letter-spacing:.15em;text-transform:uppercase;color:var(--text3);margin-bottom:8px;font-weight:500}
.ref-paper{font-size:11px;line-height:1.7;color:var(--text2);margin-bottom:4px;padding-left:12px;position:relative}
.ref-paper::before{content:'';position:absolute;left:0;top:8px;width:4px;height:1px;background:var(--amber-dim)}
.ref-paper a{color:var(--blue);text-decoration:none;border-bottom:1px solid rgba(96,165,250,.2)}
.ref-paper a:hover{border-bottom-color:var(--blue)}

/* ── GRAPH ── */
.graph-container h2{font-size:10px;letter-spacing:.2em;text-transform:uppercase;color:var(--amber-dim);margin-bottom:20px;padding-bottom:10px;border-bottom:1px solid var(--border)}
#dep-graph-svg{width:100%;min-height:400px;border:1px solid var(--border);background:var(--surface);padding:20px;overflow:auto}
#dep-graph-svg svg{max-width:100%}
.graph-fallback{padding:48px;text-align:center;color:var(--text3)}
.graph-fallback p{font-size:12px;margin-bottom:16px}
.graph-fallback pre{text-align:left;background:var(--card);padding:16px;border:1px solid var(--border);overflow-x:auto;font-size:11px;color:var(--text2);line-height:1.7}

/* ── DEFERRED ── */
.deferred-card{background:var(--surface);border:1px solid var(--border);border-left:2px solid var(--orange);padding:16px 20px;margin-bottom:10px;cursor:pointer;transition:background .12s;clip-path:polygon(0 0,calc(100% - 12px) 0,100% 12px,100% 100%,0 100%)}
.deferred-card:hover{background:var(--card)}
.deferred-card .task-id{font-size:10px;color:var(--amber-dim);margin-bottom:6px}
.deferred-card .task-title{font-size:14px;font-family:var(--serif);font-weight:300;margin-bottom:10px}
.deferred-card .task-meta{display:flex;gap:5px;flex-wrap:wrap;margin-bottom:10px}
.trigger-info{background:rgba(251,146,60,.05);border:1px solid rgba(251,146,60,.15);padding:10px 14px;font-size:11px}
.trigger-label{font-size:9px;letter-spacing:.15em;text-transform:uppercase;color:var(--orange);margin-bottom:4px;font-weight:500}

/* ── MODAL ── */
.modal-overlay{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,.75);z-index:1000;align-items:center;justify-content:center;backdrop-filter:blur(2px)}
.modal-overlay.active{display:flex}
.modal{background:var(--surface);border:1px solid var(--border2);padding:0;max-width:660px;width:90%;max-height:82vh;overflow-y:auto;position:relative}
.modal::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;background:linear-gradient(90deg,transparent,var(--amber),transparent)}
.modal-header{display:flex;justify-content:space-between;align-items:flex-start;padding:24px 28px 18px;border-bottom:1px solid var(--border)}
.modal-header .modal-id{font-size:10px;color:var(--amber-dim);letter-spacing:.1em;margin-bottom:6px}
.modal-header h3{font-family:var(--serif);font-size:18px;font-weight:300;color:var(--text);line-height:1.3}
.modal-close{background:none;border:1px solid var(--border);color:var(--text3);font-size:16px;cursor:pointer;padding:4px 10px;transition:all .12s;flex-shrink:0;margin-left:16px}
.modal-close:hover{border-color:var(--amber-dim);color:var(--amber)}
.modal-body{padding:20px 28px 28px}
.modal-section{margin-bottom:20px}
.modal-section h4{font-size:9px;letter-spacing:.18em;text-transform:uppercase;color:var(--text3);margin-bottom:8px;font-weight:500}
.modal-section p,.modal-section li{font-size:13px;line-height:1.7;color:var(--text2)}
.modal-section ul{padding-left:18px}
.modal-section code{background:var(--card);border:1px solid var(--border);padding:1px 6px;font-size:11px;color:var(--amber-dim)}
.modal-kv{display:grid;grid-template-columns:auto 1fr;gap:4px 16px}
.modal-kv .k{font-size:11px;color:var(--text3)}
.modal-kv .v{font-size:11px;color:var(--text)}

/* ── SCROLLBAR ── */
::-webkit-scrollbar{width:6px;height:6px}
::-webkit-scrollbar-track{background:var(--bg)}
::-webkit-scrollbar-thumb{background:var(--border2)}
::-webkit-scrollbar-thumb:hover{background:var(--amber-dim)}
.empty{padding:60px;text-align:center;color:var(--text3);font-size:12px;letter-spacing:.1em}
</style>
</head>
<body>
<div class="header">
  <div class="header-left">
    <div class="header-label">PM Agent / Project Dashboard</div>
    <h1>{{PROJECT_NAME}}</h1>
  </div>
  <div class="header-right">
    <div class="proj-id">{{PROJECT_ID}}</div>
    <div>Generated by pm-agent</div>
  </div>
</div>

<div class="stats-bar" id="stats-bar"></div>

<div class="tabs" id="tabs-bar">
  <button class="tab active" data-view="overview">Overview</button>
  <button class="tab" data-view="milestones">Milestones</button>
  <button class="tab" data-view="kanban">Kanban</button>
  <button class="tab" data-view="timeline">Timeline</button>
  <button class="tab" data-view="references">References</button>
  <button class="tab" data-view="graph">Dependencies</button>
  <button class="tab" data-view="deferred">Deferred</button>
</div>

<div class="content">
  <div id="overview-view" class="view active"></div>
  <div id="milestones-view" class="view"></div>
  <div id="kanban-view" class="view"></div>
  <div id="timeline-view" class="view"></div>
  <div id="references-view" class="view"></div>
  <div id="graph-view" class="view"></div>
  <div id="deferred-view" class="view"></div>
</div>

<div class="modal-overlay" id="modal-overlay">
  <div class="modal">
    <div class="modal-header">
      <div>
        <div class="modal-id" id="modal-id"></div>
        <h3 id="modal-title"></h3>
      </div>
      <button class="modal-close" onclick="closeModal()">&#x2715;</button>
    </div>
    <div class="modal-body" id="modal-body"></div>
  </div>
</div>
<script>
let tasks = {{TASKS_JSON}};
let extra = {{EXTRA_JSON}};

/* ── INIT ── */
function init() {
  renderStats();
  renderOverview();
  renderMilestones();
  renderKanban();
  renderTimeline();
  renderReferences();
  renderGraph();
  renderDeferred();
  bindTabs();
}

/* ── STATS ── */
function renderStats() {
  const bar = document.getElementById('stats-bar');
  const total = tasks.length;
  const counts = {
    pending:     tasks.filter(t => t.status === 'pending').length,
    in_progress: tasks.filter(t => t.status === 'in_progress').length,
    in_review:   tasks.filter(t => t.status === 'in_review').length,
    done:        tasks.filter(t => t.status === 'done').length,
    deferred:    tasks.filter(t => t.status === 'deferred').length,
    failed:      tasks.filter(t => t.status === 'failed' || t.status === 'terminated').length,
  };
  const specs = [
    {label:'Total',    val:total,             cls:'total',    pct:1},
    {label:'Pending',  val:counts.pending,    cls:'pending',  pct:total?counts.pending/total:0},
    {label:'Active',   val:counts.in_progress,cls:'progress', pct:total?counts.in_progress/total:0},
    {label:'Review',   val:counts.in_review,  cls:'review',   pct:total?counts.in_review/total:0},
    {label:'Done',     val:counts.done,       cls:'done',     pct:total?counts.done/total:0},
    {label:'Deferred', val:counts.deferred,   cls:'deferred', pct:total?counts.deferred/total:0},
    {label:'Failed',   val:counts.failed,     cls:'failed',   pct:total?counts.failed/total:0},
  ];
  bar.innerHTML = specs.map(s =>
    `<div class="stat-card">
      <div class="label">${s.label}</div>
      <div class="value ${s.cls}">${s.val}</div>
      <div class="unit">tasks</div>
      <div class="stat-bar" style="width:${(s.pct*100).toFixed(1)}%;color:var(--${s.cls==='total'?'amber':s.cls==='progress'?'orange':s.cls==='review'?'purple':s.cls})"></div>
    </div>`
  ).join('');
}

/* ── OVERVIEW ── */
function renderOverview() {
  const view = document.getElementById('overview-view');
  const desc = extra.description || '';
  const timeline = extra.timeline || '';
  const cp = extra.critical_path || '';
  const phases = extra.phases || {};

  let html = '<h2 class="section-h">Project Overview</h2>';
  html += '<div class="overview-grid">';

  // Description card
  html += `<div class="overview-card">
    <h3>Description</h3>
    <p>${esc(desc)}</p>
    ${timeline ? `<div style="margin-top:14px"><span style="color:var(--text3);font-size:10px;letter-spacing:.12em;text-transform:uppercase">Timeline</span><div class="mono" style="margin-top:6px;color:var(--amber)">${esc(timeline)}</div></div>` : ''}
  </div>`;

  // Phase summary card
  html += '<div class="overview-card"><h3>Phase Summary</h3><div class="mono">';
  for (const [pname, tids] of Object.entries(phases)) {
    const ids = Array.isArray(tids) ? tids : [];
    const done = ids.filter(id => {
      const t = tasks.find(x => x.id === id);
      return t && t.status === 'done';
    }).length;
    const pct = ids.length ? Math.round(done / ids.length * 100) : 0;
    html += `<div style="margin-bottom:8px">
      <span style="color:var(--text2)">${esc(pname)}</span>
      <span style="color:var(--text3);margin:0 8px">${ids.length} tasks</span>
      <span style="color:${pct > 0 ? 'var(--green)' : 'var(--text3)'}">${pct}%</span>
    </div>`;
  }
  html += '</div></div>';

  // Deliverables card
  const deliverables = [
    {phase:'Phase 1', items:['DFT+U PW SCF (nspin=1/2/4)', 'DeltaSpin LCAO/PW', 'GPU/DCU acceleration']},
    {phase:'Phase 2', items:['Adaptive Kerker preconditioning', 'Occupation matrix mixing', 'Constrained DFT framework']},
    {phase:'Phase 3', items:['CeO2/Gd2O3/La2O3 benchmarks', 'ABACUS vs VASP cross-validation (<3%)', 'Convergence reliability (>90%)']},
    {phase:'Phase 4', items:['Auto parameter selection', 'abacustest workflow integration', 'Documentation & examples']},
  ];
  html += '<div class="overview-card"><h3>Key Deliverables</h3>';
  deliverables.forEach(d => {
    html += `<div style="margin-bottom:12px">
      <div style="font-size:10px;letter-spacing:.12em;text-transform:uppercase;color:var(--amber-dim);margin-bottom:4px">${d.phase}</div>`;
    d.items.forEach(item => {
      html += `<div style="font-size:12px;color:var(--text2);padding-left:12px;line-height:1.8;position:relative">
        <span style="position:absolute;left:0;top:8px;width:4px;height:4px;background:var(--amber-dim);border-radius:50%"></span>
        ${esc(item)}
      </div>`;
    });
    html += '</div>';
  });
  html += '</div>';

  // Critical path card
  if (cp) {
    html += '<div class="overview-card"><h3>Critical Path</h3>';
    const parts = cp.split(/\s*→\s*/);
    html += '<div class="critical-path">';
    html += parts.map(p => `<span style="color:var(--text)">${esc(p)}</span>`).join('<span class="arrow">→</span>');
    html += '</div></div>';
  }

  html += '</div>';
  view.innerHTML = html;
}

/* ── MILESTONES ── */
function renderMilestones() {
  const view = document.getElementById('milestones-view');
  const milestones = extra.milestones || [];
  const phases = extra.phases || {};

  let html = '<h2 class="section-h">Milestones & Gates</h2>';

  if (milestones.length === 0) {
    html += '<div class="empty">No milestone data available</div>';
    view.innerHTML = html;
    return;
  }

  html += '<div class="milestones">';
  milestones.forEach(ms => {
    // Try to compute progress for this milestone
    let progress = 0;
    let totalTasks = 0;
    let doneTasks = 0;

    // Map milestone to phase tasks
    const msNum = ms.id.replace(/[^0-9]/g, '');
    for (const [pname, tids] of Object.entries(phases)) {
      const phaseNum = pname.match(/Phase\s*(\d)/i);
      if (phaseNum) {
        const pn = parseInt(phaseNum[1]);
        // M1 covers Phase 0+1, M2 covers Phase 2, M3 covers Phase 3, etc.
        let covers = false;
        if (msNum === '1' && pn <= 1) covers = true;
        if (msNum === '2' && pn <= 2) covers = true;
        if (msNum === '3' && pn <= 3) covers = true;
        if (msNum === '4' && pn <= 4) covers = true;
        if (msNum === '5' && pn <= 4) covers = true;
        if (covers) {
          const ids = Array.isArray(tids) ? tids : [];
          totalTasks += ids.length;
          doneTasks += ids.filter(id => {
            const t = tasks.find(x => x.id === id);
            return t && t.status === 'done';
          }).length;
        }
      }
    }
    progress = totalTasks ? Math.round(doneTasks / totalTasks * 100) : 0;

    html += `<div class="milestone-row">
      <div class="milestone-id"><span>${esc(ms.id)}</span></div>
      <div class="milestone-body">
        <div class="ms-desc">${esc(ms.description)}</div>
        <div class="ms-gate">Coverage: <em>${doneTasks}/${totalTasks} tasks</em></div>
        <div class="ms-progress"><div class="ms-progress-fill" style="width:${progress}%"></div></div>
      </div>
    </div>`;
  });
  html += '</div>';
  view.innerHTML = html;
}

/* ── GROUPING ── */
function detectGrouping() {
  const hasPhase = tasks.some(t => t.phase || (t.id && /^[A-Z]+-\d/.test(t.id)));
  const hasBatch = tasks.some(t => t.batch !== undefined && t.batch !== null);
  if (hasPhase) return 'phase';
  if (hasBatch) return 'batch';
  return 'status';
}
function groupByPhase() {
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
  const order = ['pending','in_progress','in_review','done','deferred','failed'];
  const labels = {pending:'Pending',in_progress:'In Progress',in_review:'In Review',done:'Done',deferred:'Deferred',failed:'Failed'};
  const groups = {};
  order.forEach(s => { groups[labels[s]] = []; });
  tasks.forEach(t => {
    const label = labels[t.status] || t.status || 'Pending';
    (groups[label] = groups[label] || []).push(t);
  });
  return groups;
}

/* ── TASK CARD ── */
function statusDot(status) {
  const pulse = status === 'in_progress' || status === 'in_review';
  const colorMap = {pending:'blue',in_progress:'orange',in_review:'purple',done:'green',deferred:'gray'};
  return `<span class="status-dot${pulse?' pulse':''}" style="--status-color:var(--${colorMap[status]||'red'})"></span>`;
}
function taskCard(t) {
  let meta = '';
  if (t.layer)       meta += `<span class="badge layer">${t.layer}</span>`;
  if (t.type)        meta += `<span class="badge type">${t.type}</span>`;
  if (t.risk_level)  meta += `<span class="badge risk-${t.risk_level}">${t.risk_level}</span>`;
  if (t.batch !== undefined && t.batch !== null) meta += `<span class="badge batch">B${t.batch}</span>`;
  return `<div class="task-card status-${t.status}" data-id="${esc(t.id)}">
    <div class="task-header">${statusDot(t.status)}<span class="task-id">${esc(t.id)}</span></div>
    <div class="task-title">${esc(t.title)}</div>
    <div class="task-meta">${meta}</div>
  </div>`;
}

/* ── KANBAN ── */
function renderKanban() {
  const view = document.getElementById('kanban-view');
  const strategy = detectGrouping();
  const groups = strategy === 'phase' ? groupByPhase() : strategy === 'batch' ? groupByBatch() : groupByStatus();
  let html = '<div class="kanban">';
  for (const [name, items] of Object.entries(groups)) {
    if (items.length === 0) continue;
    html += `<div class="column"><div class="column-header"><span class="title">${esc(name)}</span><span class="count">${items.length}</span></div><div class="column-body">`;
    items.forEach(t => { html += taskCard(t); });
    html += '</div></div>';
  }
  html += '</div>';
  view.innerHTML = html;
  bindCardClicks(view);
}

/* ── TIMELINE ── */
function renderTimeline() {
  const view = document.getElementById('timeline-view');
  const groups = groupByPhase();
  let html = '';
  for (const [name, items] of Object.entries(groups)) {
    const active = items.filter(t => t.status !== 'deferred');
    if (active.length === 0) continue;
    html += `<div class="phase-section"><div class="phase-header">${esc(name)} <span style="color:var(--text3)">(${active.length})</span></div><div class="phase-tasks">`;
    active.forEach(t => { html += taskCard(t); });
    html += '</div></div>';
  }
  view.innerHTML = html || '<div class="empty">No tasks</div>';
  bindCardClicks(view);
}

/* ── REFERENCES ── */
function renderReferences() {
  const view = document.getElementById('references-view');
  const lit = extra.literature || [];

  let html = '<h2 class="section-h">Literature & Technical References</h2>';

  if (lit.length === 0) {
    html += '<div class="empty">No literature review data available</div>';
    view.innerHTML = html;
    return;
  }

  html += '<div class="ref-grid">';
  lit.forEach(entry => {
    const tid = entry.task_id || '';
    const task = tasks.find(t => t.id === tid);
    const title = task ? task.title : tid;
    const novelty = entry.novelty_level || '';

    html += '<div class="ref-card">';
    html += `<div class="ref-card-header">
      <span class="ref-tid">${esc(tid)}</span>
      <span class="ref-title">${esc(title)}</span>
    </div>`;

    // Badges
    html += '<div class="ref-meta">';
    if (novelty) html += `<span class="badge novelty-${novelty}">${novelty}</span>`;
    html += '</div>';

    // State of art
    if (entry.state_of_art) {
      html += `<div class="ref-section"><h5>State of the Art</h5><p>${esc(entry.state_of_art)}</p></div>`;
    }
    // Recent advances
    if (entry.recent_advances) {
      html += `<div class="ref-section"><h5>Recent Advances</h5><p>${esc(entry.recent_advances)}</p></div>`;
    }
    // Gaps
    if (entry.gaps_identified) {
      html += `<div class="ref-section"><h5>Gaps Identified</h5><p>${esc(entry.gaps_identified)}</p></div>`;
    }
    // Improvement suggestions
    const suggestions = entry.improvement_suggestions || [];
    if (suggestions.length) {
      html += '<div class="ref-section"><h5>Improvement Suggestions</h5><ul>';
      suggestions.forEach(s => { html += `<li>${esc(s)}</li>`; });
      html += '</ul></div>';
    }
    // Alternative approaches
    const alts = entry.alternative_approaches || [];
    if (alts.length) {
      html += '<div class="ref-section"><h5>Alternative Approaches</h5><ul>';
      alts.forEach(a => { html += `<li>${esc(a)}</li>`; });
      html += '</ul></div>';
    }
    // Key papers
    const papers = entry.key_papers || [];
    const detailedRefs = entry.detailed_refs || [];
    if (papers.length || detailedRefs.length) {
      html += '<div class="ref-papers"><h5>Key Papers</h5>';
      const allRefs = detailedRefs.length ? detailedRefs : papers;
      allRefs.forEach(p => {
        // Try to extract URL from markdown link
        const linkMatch = p.match(/\[([^\]]+)\]\(([^)]+)\)/);
        if (linkMatch) {
          html += `<div class="ref-paper"><a href="${esc(linkMatch[2])}" target="_blank">${esc(linkMatch[1])}</a></div>`;
        } else {
          html += `<div class="ref-paper">${esc(p.replace(/^\d+\.\s*/, ''))}</div>`;
        }
      });
      html += '</div>';
    }
    html += '</div>';
  });
  html += '</div>';
  view.innerHTML = html;
}

/* ── GRAPH ── */
function renderGraph() {
  const view = document.getElementById('graph-view');
  const withDeps = tasks.filter(t => (t.dependencies && t.dependencies.length > 0) || tasks.some(o => (o.dependencies || []).includes(t.id)));
  let dot = 'digraph G {\\n  rankdir=LR;\\n';
  const statusColor = {pending:'#60a5fa',in_progress:'#fb923c',in_review:'#c084fc',done:'#4ade80',deferred:'#4b5563',failed:'#f87171'};
  tasks.forEach(t => {
    const c = statusColor[t.status] || '#60a5fa';
    const label = t.id + '\\\\n' + (t.title||'').substring(0,24);
    dot += `  "${t.id}" [label="${label}" fillcolor="${c}" style="filled,rounded" shape=box fontname="monospace" fontsize=10];\\n`;
  });
  tasks.forEach(t => {
    (t.dependencies||[]).forEach(d => { dot += `  "${d}" -> "${t.id}";\\n`; });
    (t.suspended_dependencies||[]).forEach(d => { dot += `  "${d}" -> "${t.id}" [style=dashed color="#4b5563"];\\n`; });
  });
  dot += '}';
  let html = '<div class="graph-container"><h2>Task Dependencies</h2><div id="dep-graph-svg">';
  const inlineSvg = document.getElementById('embedded-svg');
  if (inlineSvg && inlineSvg.textContent.trim()) {
    html += inlineSvg.textContent;
  } else if (withDeps.length === 0) {
    html += '<div class="graph-fallback"><p>No dependency information available.</p></div>';
  } else {
    html += `<div class="graph-fallback"><p>Run <code>python -m tools.generate_graph</code> to render SVG.</p><pre>${dot.replace(/\\n/g,'\n')}</pre></div>`;
  }
  html += '</div></div>';
  view.innerHTML = html;
}

/* ── DEFERRED ── */
function renderDeferred() {
  const view = document.getElementById('deferred-view');
  const deferred = tasks.filter(t => t.status === 'deferred');
  let html = '<h2 class="section-h">Deferred Tasks</h2>';
  if (deferred.length === 0) {
    html += '<div class="empty">No deferred tasks</div>';
  } else {
    deferred.forEach(t => {
      let meta = '';
      if (t.layer)      meta += `<span class="badge layer">${t.layer}</span>`;
      if (t.risk_level) meta += `<span class="badge risk-${t.risk_level}">${t.risk_level}</span>`;
      html += `<div class="deferred-card" data-id="${esc(t.id)}">
        <div class="task-id">${esc(t.id)}</div>
        <div class="task-title">${esc(t.title)}</div>
        <div class="task-meta">${meta}</div>`;
      if (t.defer_trigger) {
        html += `<div class="trigger-info"><div class="trigger-label">Trigger Condition</div><div>${esc(t.defer_trigger)}</div></div>`;
      }
      if (t.description) {
        html += `<div style="margin-top:10px;font-size:12px;color:var(--text3)">${esc(t.description).substring(0,200)}</div>`;
      }
      html += '</div>';
    });
  }
  view.innerHTML = html;
  bindCardClicks(view);
}

/* ── MODAL ── */
function showModal(task) {
  document.getElementById('modal-id').textContent = task.id;
  document.getElementById('modal-title').textContent = task.title;
  const statusLabels = {pending:'Pending',in_progress:'In Progress',in_review:'In Review',done:'Done',deferred:'Deferred',failed:'Failed',terminated:'Terminated'};
  let body = '';
  if (task.description) body += `<div class="modal-section"><h4>Description</h4><p>${esc(task.description)}</p></div>`;
  body += `<div class="modal-section"><h4>Metadata</h4><div class="modal-kv">`;
  body += `<span class="k">Status</span><span class="v">${statusLabels[task.status]||task.status}</span>`;
  if (task.layer)     body += `<span class="k">Layer</span><span class="v">${task.layer}</span>`;
  if (task.type)      body += `<span class="k">Type</span><span class="v">${task.type}</span>`;
  if (task.risk_level)body += `<span class="k">Risk</span><span class="v">${task.risk_level}</span>`;
  if (task.specialist)body += `<span class="k">Specialist</span><span class="v">${task.specialist}</span>`;
  if (task.batch !== undefined) body += `<span class="k">Batch</span><span class="v">${task.batch}</span>`;
  body += `</div></div>`;
  if (task.defer_trigger) body += `<div class="modal-section"><h4>Trigger Condition</h4><p style="background:var(--orange-bg);border:1px solid rgba(251,146,60,.2);padding:10px 14px;font-size:12px">${esc(task.defer_trigger)}</p></div>`;
  const deps = task.dependencies || [];
  if (deps.length) body += `<div class="modal-section"><h4>Dependencies (${deps.length})</h4><ul>${deps.map(d=>`<li>${esc(d)}</li>`).join('')}</ul></div>`;
  const criteria = task.acceptance_criteria || [];
  if (criteria.length) body += `<div class="modal-section"><h4>Acceptance Criteria</h4><ul>${criteria.map(c=>`<li>${esc(c)}</li>`).join('')}</ul></div>`;
  const files = task.files_to_touch || [];
  if (files.length) body += `<div class="modal-section"><h4>Files</h4><ul>${files.map(f=>`<li><code>${esc(f)}</code></li>`).join('')}</ul></div>`;
  document.getElementById('modal-body').innerHTML = body;
  document.getElementById('modal-overlay').classList.add('active');
}
function closeModal() { document.getElementById('modal-overlay').classList.remove('active'); }
document.getElementById('modal-overlay').addEventListener('click', e => { if (e.target.id === 'modal-overlay') closeModal(); });
document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModal(); });

/* ── TABS ── */
function bindTabs() {
  document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
      tab.classList.add('active');
      document.getElementById(tab.dataset.view + '-view').classList.add('active');
    });
  });
}

/* ── HELPERS ── */
function esc(s) { if (!s) return ''; const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }
function bindCardClicks(container) {
  container.querySelectorAll('.task-card, .deferred-card').forEach(card => {
    card.addEventListener('click', () => {
      const task = tasks.find(t => t.id === card.dataset.id);
      if (task) showModal(task);
    });
  });
}

init();
</script>
<script type="text/plain" id="embedded-svg">{{EMBEDDED_SVG}}</script>
</body>
</html>'''


def generate_dashboard(project_dir: Path) -> bool:
    """Generate dashboard.html for a project.

    Embeds task data, project metadata, milestones, and literature
    inline so the HTML is fully self-contained and works with file://.

    Returns True if dashboard was generated, False if no tasks found.
    """
    state = load_state(project_dir)
    tasks = state["tasks"]

    if not tasks:
        return False

    tasks_json = json.dumps(tasks, ensure_ascii=False)

    # Load extra project data (milestones, literature, etc.)
    extra = _load_project_extra(project_dir)
    extra_json = json.dumps(extra, ensure_ascii=False, default=str)

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
    html = html.replace("{{EXTRA_JSON}}", extra_json)
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
