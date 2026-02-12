#!/usr/bin/env python3
"""Generate dependency graph visualization using Graphviz."""

import json
import sys
from pathlib import Path

def generate_dot(state_file: str, output_file: str):
    """Generate DOT file for dependency graph."""

    with open(state_file) as f:
        state = json.load(f)

    tasks = state.get('tasks', [])

    # Start DOT file
    dot = ['digraph Dependencies {']
    dot.append('  rankdir=LR;')
    dot.append('  node [shape=box, style=rounded];')
    dot.append('')

    # Define nodes with colors based on status and risk
    for task in tasks:
        task_id = task['id']
        title = task['title'][:30] + '...' if len(task['title']) > 30 else task['title']
        status = task.get('status', 'pending')
        risk = task.get('risk_level', 'low')

        # Color by status
        color_map = {
            'pending': '#3498db',
            'in_progress': '#f39c12',
            'done': '#2ecc71',
            'failed': '#e74c3c',
            'deferred': '#95a5a6'
        }

        # Border by risk
        border_map = {
            'low': '1',
            'medium': '2',
            'high': '3'
        }

        color = color_map.get(status, '#3498db')
        border = border_map.get(risk, '1')

        label = f"{task_id}\\n{title}"
        dot.append(f'  "{task_id}" [label="{label}", fillcolor="{color}", style="filled,rounded", penwidth={border}];')

    dot.append('')

    # Define edges (dependencies)
    for task in tasks:
        task_id = task['id']
        deps = task.get('dependencies', [])

        for dep in deps:
            dot.append(f'  "{dep}" -> "{task_id}";')

    # Add suspended dependencies (dashed lines)
    for task in tasks:
        task_id = task['id']
        suspended = task.get('suspended_dependencies', [])

        for dep in suspended:
            dot.append(f'  "{dep}" -> "{task_id}" [style=dashed, color=gray];')

    dot.append('}')

    # Write to file
    with open(output_file, 'w') as f:
        f.write('\n'.join(dot))

    print(f"Generated DOT file: {output_file}")
    print(f"To generate PNG: dot -Tpng {output_file} -o dependency_graph.png")
    print(f"To generate SVG: dot -Tsvg {output_file} -o dependency_graph.svg")

if __name__ == '__main__':
    state_file = 'state/project_state.json'
    output_file = 'dependency_graph.dot'

    if len(sys.argv) > 1:
        state_file = sys.argv[1]
    if len(sys.argv) > 2:
        output_file = sys.argv[2]

    generate_dot(state_file, output_file)
