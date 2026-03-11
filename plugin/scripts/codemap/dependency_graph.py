#!/usr/bin/env python3
"""
Dependency Graph Extractor — Builds program-level dependency graph from codemap.

Reads artifacts/codemap.json and produces artifacts/dependency-graph.json
containing nodes (programs, copybooks, data files) and edges (CALLS, COPIES,
READS, WRITES).

Usage:
  python3 dependency_graph.py --codemap artifacts/codemap.json --output artifacts/dependency-graph.json
"""

import argparse
import json
import os
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path


def extract_cobol_dependencies(codemap: dict) -> dict:
    """Extract dependencies from COBOL heuristics."""
    nodes = {}
    edges = []

    root = codemap["root"]
    heuristics = codemap.get("heuristics", {})

    # Programs as nodes (from entry points)
    for ep in heuristics.get("entry_points", []):
        node_id = ep["file"]
        if node_id not in nodes:
            nodes[node_id] = {
                "id": node_id,
                "type": "program",
                "language": ep["language"],
                "properties": {
                    "entry_line": ep["line"],
                    "is_entry_point": True,
                },
            }

    # Copybooks as nodes + COPIES edges
    for cb in heuristics.get("copybooks", []):
        copybook_id = cb["copybook"]
        if copybook_id not in nodes:
            nodes[copybook_id] = {
                "id": copybook_id,
                "type": "copybook",
                "language": "cobol",
                "properties": {},
            }
        edges.append({
            "from": cb["file"],
            "to": copybook_id,
            "type": "COPIES",
            "properties": {"line": cb["line"]},
        })
        # Ensure the program node exists
        if cb["file"] not in nodes:
            nodes[cb["file"]] = {
                "id": cb["file"],
                "type": "program",
                "language": "cobol",
                "properties": {"is_entry_point": False},
            }

    # CALL edges
    for call in heuristics.get("call_graph_hints", []):
        callee_id = call["callee"]
        if callee_id not in nodes:
            nodes[callee_id] = {
                "id": callee_id,
                "type": "program",
                "language": "cobol",
                "properties": {"is_entry_point": False, "discovered_via": "call"},
            }
        edges.append({
            "from": call["caller"],
            "to": callee_id,
            "type": "CALLS",
            "properties": {"line": call["line"]},
        })
        if call["caller"] not in nodes:
            nodes[call["caller"]] = {
                "id": call["caller"],
                "type": "program",
                "language": "cobol",
                "properties": {"is_entry_point": False},
            }

    # Data sources → data file nodes + READS/WRITES edges
    for ds in heuristics.get("data_sources", []):
        if ds["language"] == "cobol" and ds["pattern"] == "FD ":
            # File descriptor — implies data file
            fd_id = f"datafile:{ds['file']}:{ds['line']}"
            if fd_id not in nodes:
                nodes[fd_id] = {
                    "id": fd_id,
                    "type": "data_file",
                    "language": "cobol",
                    "properties": {"declared_in": ds["file"], "line": ds["line"]},
                }
            edges.append({
                "from": ds["file"],
                "to": fd_id,
                "type": "USES_FILE",
                "properties": {"line": ds["line"]},
            })

    return {"nodes": nodes, "edges": edges}


def extract_java_dependencies(codemap: dict) -> dict:
    """Extract dependencies from Java heuristics."""
    nodes = {}
    edges = []

    for ep in codemap.get("heuristics", {}).get("entry_points", []):
        if ep["language"] == "java":
            nodes[ep["file"]] = {
                "id": ep["file"],
                "type": "program",
                "language": "java",
                "properties": {"entry_line": ep["line"], "is_entry_point": True},
            }

    return {"nodes": nodes, "edges": edges}


def extract_generic_dependencies(codemap: dict) -> dict:
    """Fallback extractor for languages without specific heuristics."""
    nodes = {}
    edges = []

    for ep in codemap.get("heuristics", {}).get("entry_points", []):
        nodes[ep["file"]] = {
            "id": ep["file"],
            "type": "program",
            "language": ep["language"],
            "properties": {"entry_line": ep["line"], "is_entry_point": True},
        }

    return {"nodes": nodes, "edges": edges}


LANGUAGE_EXTRACTORS = {
    "cobol": extract_cobol_dependencies,
    "java": extract_java_dependencies,
}


def build_dependency_graph(codemap: dict) -> dict:
    """Build the full dependency graph from codemap data."""
    all_nodes = {}
    all_edges = []

    languages = codemap.get("summary", {}).get("languages", {})

    for lang in languages:
        extractor = LANGUAGE_EXTRACTORS.get(lang, extract_generic_dependencies)
        result = extractor(codemap)
        all_nodes.update(result["nodes"])
        all_edges.extend(result["edges"])

    # Enrich nodes with VCS data if available
    vcs = codemap.get("vcs", {})
    if vcs.get("available"):
        hotspot_map = {h["file"]: h for h in vcs.get("hotspots", [])}
        for node_id, node in all_nodes.items():
            if node_id in hotspot_map:
                node["properties"]["change_frequency"] = hotspot_map[node_id]["change_count"]
                node["properties"]["contributors"] = hotspot_map[node_id]["authors"]

    graph = {
        "version": "1.0",
        "generated_at": datetime.now().isoformat(),
        "metadata": {
            "source": "codemap",
            "languages": list(languages.keys()),
            "node_count": len(all_nodes),
            "edge_count": len(all_edges),
        },
        "nodes": list(all_nodes.values()),
        "edges": all_edges,
    }

    return graph


def main():
    parser = argparse.ArgumentParser(description="Dependency Graph Extractor")
    parser.add_argument("--codemap", required=True, help="Path to codemap.json")
    parser.add_argument("--output", default="artifacts/dependency-graph.json")
    args = parser.parse_args()

    with open(args.codemap) as f:
        codemap = json.load(f)

    graph = build_dependency_graph(codemap)

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(graph, f, indent=2)

    print(f"[dependency-graph] Built graph: {graph['metadata']['node_count']} nodes, {graph['metadata']['edge_count']} edges")
    print(f"[dependency-graph] Written to {args.output}")


if __name__ == "__main__":
    main()
