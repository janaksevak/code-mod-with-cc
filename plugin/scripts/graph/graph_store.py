#!/usr/bin/env python3
"""
Graph Store — JSON-backed knowledge graph with query operations.

MVP implementation using a JSON file. Interface designed to be swappable
to Neo4j (via MCP server) in a later iteration.

The graph stores:
  - Nodes: programs, copybooks, data files, modules, slices
  - Edges: CALLS, COPIES, READS, WRITES, DEPENDS_ON, BELONGS_TO
  - Properties: metadata on both nodes and edges

Usage as library:
  from graph_store import GraphStore
  gs = GraphStore("artifacts/knowledge-graph.json")
  gs.add_node("EMPSAL.CBL", "program", {"language": "cobol"})
  gs.add_edge("EMPSAL.CBL", "EMPSAL-RECORD", "COPIES")
  programs = gs.query_nodes(type="program")
  deps = gs.get_dependencies("EMPSAL.CBL")

Usage as CLI:
  python3 graph_store.py --graph artifacts/knowledge-graph.json --action summary
  python3 graph_store.py --graph artifacts/knowledge-graph.json --action import --source artifacts/dependency-graph.json
  python3 graph_store.py --graph artifacts/knowledge-graph.json --action query --type program
  python3 graph_store.py --graph artifacts/knowledge-graph.json --action dependencies --node "EMPSAL.CBL"
"""

import argparse
import json
import os
from datetime import datetime
from typing import Optional


class GraphStore:
    """JSON-backed knowledge graph."""

    def __init__(self, path: str):
        self.path = path
        self._graph = self._load()

    def _load(self) -> dict:
        if os.path.exists(self.path):
            with open(self.path) as f:
                return json.load(f)
        return {
            "version": "1.0",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "nodes": {},
            "edges": [],
        }

    def save(self):
        self._graph["updated_at"] = datetime.now().isoformat()
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w") as f:
            json.dump(self._graph, f, indent=2)

    # --- Node operations ---

    def add_node(self, node_id: str, node_type: str, properties: dict = None):
        self._graph["nodes"][node_id] = {
            "id": node_id,
            "type": node_type,
            "properties": properties or {},
            "added_at": datetime.now().isoformat(),
        }

    def get_node(self, node_id: str) -> Optional[dict]:
        return self._graph["nodes"].get(node_id)

    def update_node(self, node_id: str, properties: dict):
        if node_id in self._graph["nodes"]:
            self._graph["nodes"][node_id]["properties"].update(properties)
            self._graph["nodes"][node_id]["updated_at"] = datetime.now().isoformat()

    def remove_node(self, node_id: str):
        self._graph["nodes"].pop(node_id, None)
        self._graph["edges"] = [
            e for e in self._graph["edges"]
            if e["from"] != node_id and e["to"] != node_id
        ]

    def query_nodes(self, node_type: str = None, **prop_filters) -> list:
        results = []
        for node in self._graph["nodes"].values():
            if node_type and node["type"] != node_type:
                continue
            if prop_filters:
                props = node.get("properties", {})
                if all(props.get(k) == v for k, v in prop_filters.items()):
                    results.append(node)
            else:
                results.append(node)
        return results

    # --- Edge operations ---

    def add_edge(self, from_id: str, to_id: str, edge_type: str, properties: dict = None):
        # Avoid duplicate edges
        for e in self._graph["edges"]:
            if e["from"] == from_id and e["to"] == to_id and e["type"] == edge_type:
                e["properties"].update(properties or {})
                return
        self._graph["edges"].append({
            "from": from_id,
            "to": to_id,
            "type": edge_type,
            "properties": properties or {},
        })

    def get_edges(self, from_id: str = None, to_id: str = None, edge_type: str = None) -> list:
        results = []
        for e in self._graph["edges"]:
            if from_id and e["from"] != from_id:
                continue
            if to_id and e["to"] != to_id:
                continue
            if edge_type and e["type"] != edge_type:
                continue
            results.append(e)
        return results

    def remove_edge(self, from_id: str, to_id: str, edge_type: str):
        self._graph["edges"] = [
            e for e in self._graph["edges"]
            if not (e["from"] == from_id and e["to"] == to_id and e["type"] == edge_type)
        ]

    # --- Graph queries ---

    def get_dependencies(self, node_id: str, recursive: bool = False, _visited: set = None) -> list:
        """Get all nodes that node_id depends on (outgoing edges)."""
        if _visited is None:
            _visited = set()
        if node_id in _visited:
            return []
        _visited.add(node_id)

        deps = []
        for e in self._graph["edges"]:
            if e["from"] == node_id:
                dep_node = self.get_node(e["to"])
                if dep_node:
                    deps.append({"node": dep_node, "relationship": e["type"]})
                    if recursive:
                        deps.extend(self.get_dependencies(e["to"], recursive=True, _visited=_visited))
        return deps

    def get_dependents(self, node_id: str) -> list:
        """Get all nodes that depend on node_id (incoming edges)."""
        deps = []
        for e in self._graph["edges"]:
            if e["to"] == node_id:
                dep_node = self.get_node(e["from"])
                if dep_node:
                    deps.append({"node": dep_node, "relationship": e["type"]})
        return deps

    def get_connected_component(self, node_id: str) -> set:
        """Get all nodes reachable from node_id (bidirectional)."""
        visited = set()
        queue = [node_id]
        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            for e in self._graph["edges"]:
                if e["from"] == current and e["to"] not in visited:
                    queue.append(e["to"])
                if e["to"] == current and e["from"] not in visited:
                    queue.append(e["from"])
        return visited

    def get_topological_order(self) -> list:
        """Return nodes in dependency order (dependencies first)."""
        in_degree = {nid: 0 for nid in self._graph["nodes"]}
        for e in self._graph["edges"]:
            if e["to"] in in_degree:
                in_degree[e["to"]] += 1

        queue = [nid for nid, deg in in_degree.items() if deg == 0]
        order = []
        while queue:
            node = queue.pop(0)
            order.append(node)
            for e in self._graph["edges"]:
                if e["from"] == node and e["to"] in in_degree:
                    in_degree[e["to"]] -= 1
                    if in_degree[e["to"]] == 0:
                        queue.append(e["to"])

        # Append any remaining (cycles)
        remaining = [nid for nid in self._graph["nodes"] if nid not in order]
        order.extend(remaining)
        return order

    # --- Import ---

    def import_dependency_graph(self, dep_graph: dict):
        """Import nodes and edges from a dependency-graph.json."""
        for node in dep_graph.get("nodes", []):
            node_id = node["id"]
            self.add_node(node_id, node["type"], node.get("properties", {}))
            if "language" in node:
                self.update_node(node_id, {"language": node["language"]})

        for edge in dep_graph.get("edges", []):
            self.add_edge(edge["from"], edge["to"], edge["type"], edge.get("properties", {}))

    # --- Summary ---

    def summary(self) -> dict:
        node_types = {}
        for n in self._graph["nodes"].values():
            t = n["type"]
            node_types[t] = node_types.get(t, 0) + 1

        edge_types = {}
        for e in self._graph["edges"]:
            t = e["type"]
            edge_types[t] = edge_types.get(t, 0) + 1

        return {
            "total_nodes": len(self._graph["nodes"]),
            "total_edges": len(self._graph["edges"]),
            "node_types": node_types,
            "edge_types": edge_types,
            "created_at": self._graph.get("created_at"),
            "updated_at": self._graph.get("updated_at"),
        }


def main():
    parser = argparse.ArgumentParser(description="Graph Store CLI")
    parser.add_argument("--graph", required=True, help="Path to knowledge-graph.json")
    parser.add_argument("--action", required=True,
                        choices=["summary", "import", "query", "dependencies", "dependents", "topo-order"])
    parser.add_argument("--source", help="Source file for import action")
    parser.add_argument("--type", help="Node type filter for query")
    parser.add_argument("--node", help="Node ID for dependency queries")
    args = parser.parse_args()

    gs = GraphStore(args.graph)

    if args.action == "summary":
        s = gs.summary()
        print(json.dumps(s, indent=2))

    elif args.action == "import":
        if not args.source:
            print("ERROR: --source required for import")
            return
        with open(args.source) as f:
            dep_graph = json.load(f)
        gs.import_dependency_graph(dep_graph)
        gs.save()
        s = gs.summary()
        print(f"Imported. Graph now has {s['total_nodes']} nodes, {s['total_edges']} edges.")

    elif args.action == "query":
        nodes = gs.query_nodes(node_type=args.type)
        for n in nodes:
            print(json.dumps(n, indent=2))

    elif args.action == "dependencies":
        if not args.node:
            print("ERROR: --node required")
            return
        deps = gs.get_dependencies(args.node, recursive=True)
        for d in deps:
            print(f"  {d['relationship']} → {d['node']['id']} ({d['node']['type']})")

    elif args.action == "dependents":
        if not args.node:
            print("ERROR: --node required")
            return
        deps = gs.get_dependents(args.node)
        for d in deps:
            print(f"  {d['node']['id']} ({d['node']['type']}) → {d['relationship']}")

    elif args.action == "topo-order":
        order = gs.get_topological_order()
        for i, nid in enumerate(order):
            node = gs.get_node(nid)
            print(f"  {i+1}. {nid} ({node['type']})")


if __name__ == "__main__":
    main()
