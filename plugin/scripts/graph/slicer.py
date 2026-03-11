#!/usr/bin/env python3
"""
Slice Computation — Derives migration slices from the knowledge graph.

A "slice" is a self-contained unit of migration work: one or more programs
plus their direct dependencies (copybooks, data files), with a clear
boundary and minimal cross-slice coupling.

Algorithm:
  1. Find all program nodes (entry points first)
  2. For each program, compute its dependency closure
  3. Group programs that share dependencies into the same slice
  4. Order slices by dependency (shared copybooks first, leaf programs last)
  5. Estimate complexity based on file count, LOC, and coupling

Usage:
  python3 slicer.py --graph artifacts/knowledge-graph.json --output artifacts/slice-manifest.json
  python3 slicer.py --graph artifacts/knowledge-graph.json --output artifacts/slice-manifest.json --strategy connected-components
"""

import argparse
import json
import os
from datetime import datetime

# Import graph store from sibling module
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from graph_store import GraphStore


def compute_slices_by_entry_point(gs: GraphStore) -> list:
    """One slice per entry-point program + its dependencies."""
    programs = gs.query_nodes(node_type="program")
    entry_points = [p for p in programs if p.get("properties", {}).get("is_entry_point")]

    # Fall back to all programs if no entry points detected
    if not entry_points:
        entry_points = programs

    slices = []
    for i, prog in enumerate(entry_points):
        prog_id = prog["id"]
        deps = gs.get_dependencies(prog_id, recursive=True)

        dep_ids = [d["node"]["id"] for d in deps]
        all_ids = [prog_id] + dep_ids

        # Classify components
        programs_in_slice = [prog_id] + [d["node"]["id"] for d in deps if d["node"]["type"] == "program"]
        copybooks = [d["node"]["id"] for d in deps if d["node"]["type"] == "copybook"]
        data_files = [d["node"]["id"] for d in deps if d["node"]["type"] == "data_file"]

        # Estimate complexity
        complexity = _estimate_complexity(len(programs_in_slice), len(copybooks), len(data_files))

        # Determine dependencies on other slices (deferred — filled after all slices computed)
        slices.append({
            "id": f"slice-{i+1:03d}",
            "name": _derive_slice_name(prog_id),
            "programs": programs_in_slice,
            "copybooks": copybooks,
            "data_files": data_files,
            "all_components": all_ids,
            "status": "available",
            "claimed_by": None,
            "confidence_score": None,
            "priority": i + 1,
            "complexity": complexity,
            "dependencies": [],  # Cross-slice dependencies
            "notes": "",
        })

    # Compute cross-slice dependencies
    _compute_cross_slice_deps(slices)

    return slices


def compute_slices_by_connected_components(gs: GraphStore) -> list:
    """One slice per connected component in the graph."""
    all_nodes = set(n["id"] for n in gs.query_nodes())
    visited = set()
    components = []

    for node_id in all_nodes:
        if node_id not in visited:
            component = gs.get_connected_component(node_id)
            visited.update(component)
            components.append(component)

    slices = []
    for i, component in enumerate(sorted(components, key=len, reverse=True)):
        programs = []
        copybooks = []
        data_files = []

        for nid in component:
            node = gs.get_node(nid)
            if not node:
                continue
            if node["type"] == "program":
                programs.append(nid)
            elif node["type"] == "copybook":
                copybooks.append(nid)
            elif node["type"] == "data_file":
                data_files.append(nid)

        if not programs:
            continue

        complexity = _estimate_complexity(len(programs), len(copybooks), len(data_files))
        name = _derive_slice_name(programs[0]) if programs else f"component-{i+1}"

        slices.append({
            "id": f"slice-{i+1:03d}",
            "name": name,
            "programs": programs,
            "copybooks": copybooks,
            "data_files": data_files,
            "all_components": list(component),
            "status": "available",
            "claimed_by": None,
            "confidence_score": None,
            "priority": i + 1,
            "complexity": complexity,
            "dependencies": [],
            "notes": "",
        })

    return slices


def _estimate_complexity(num_programs: int, num_copybooks: int, num_data_files: int) -> str:
    score = num_programs * 3 + num_copybooks * 2 + num_data_files
    if score <= 3:
        return "low"
    elif score <= 8:
        return "medium"
    elif score <= 15:
        return "high"
    else:
        return "very_high"


def _derive_slice_name(program_id: str) -> str:
    name = os.path.splitext(os.path.basename(program_id))[0]
    return name.replace("_", " ").replace("-", " ").title()


def _compute_cross_slice_deps(slices: list):
    """Identify shared components across slices → cross-slice dependencies."""
    # Map component → slices that contain it
    component_to_slices = {}
    for s in slices:
        for comp in s["all_components"]:
            component_to_slices.setdefault(comp, []).append(s["id"])

    # Shared components create dependencies
    for s in slices:
        deps = set()
        for comp in s["all_components"]:
            for other_slice_id in component_to_slices.get(comp, []):
                if other_slice_id != s["id"]:
                    deps.add(other_slice_id)
        s["dependencies"] = sorted(deps)


def build_manifest(slices: list, config: dict = None) -> dict:
    """Build the complete slice manifest."""
    return {
        "version": "1.0",
        "generated_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "config": config or {},
        "summary": {
            "total_slices": len(slices),
            "available": sum(1 for s in slices if s["status"] == "available"),
            "claimed": sum(1 for s in slices if s["status"] == "claimed"),
            "migrating": sum(1 for s in slices if s["status"] == "migrating"),
            "approved": sum(1 for s in slices if s["status"] == "approved"),
            "merged": sum(1 for s in slices if s["status"] == "merged"),
            "complexity_breakdown": {
                "low": sum(1 for s in slices if s["complexity"] == "low"),
                "medium": sum(1 for s in slices if s["complexity"] == "medium"),
                "high": sum(1 for s in slices if s["complexity"] == "high"),
                "very_high": sum(1 for s in slices if s["complexity"] == "very_high"),
            },
        },
        "slices": slices,
    }


STRATEGIES = {
    "entry-point": compute_slices_by_entry_point,
    "connected-components": compute_slices_by_connected_components,
}


def main():
    parser = argparse.ArgumentParser(description="Slice Computation")
    parser.add_argument("--graph", required=True, help="Path to knowledge-graph.json")
    parser.add_argument("--output", default="artifacts/slice-manifest.json")
    parser.add_argument("--strategy", choices=list(STRATEGIES.keys()), default="entry-point")
    args = parser.parse_args()

    gs = GraphStore(args.graph)
    compute_fn = STRATEGIES[args.strategy]
    slices = compute_fn(gs)
    manifest = build_manifest(slices)

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"[slicer] Computed {len(slices)} slices using '{args.strategy}' strategy")
    for s in slices:
        dep_str = f" (depends on: {', '.join(s['dependencies'])})" if s["dependencies"] else ""
        print(f"  {s['id']}: {s['name']} [{s['complexity']}] — {len(s['programs'])} programs, {len(s['copybooks'])} copybooks{dep_str}")
    print(f"[slicer] Written to {args.output}")


if __name__ == "__main__":
    main()
