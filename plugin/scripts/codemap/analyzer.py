#!/usr/bin/env python3
"""
Codebase Analyzer — Filesystem structure, text heuristics, VCS history.

Produces artifacts/codemap.json with a layered view of the codebase:
  Layer 1: Filesystem tree (always)
  Layer 2: Text heuristics (language detection, entry points, data flows)
  Layer 3: VCS history (hotspots, ownership, change frequency)
  Layer 4: Dependency extraction (calls, copies, includes)

Usage:
  python3 analyzer.py --root /path/to/project [--depth shallow|deep] [--output artifacts/codemap.json]
"""

import argparse
import json
import os
import subprocess
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# Language heuristic patterns
LANGUAGE_SIGNATURES = {
    "cobol": {
        "extensions": [".cbl", ".cob", ".cpy", ".ccp"],
        "markers": ["IDENTIFICATION DIVISION", "PROCEDURE DIVISION", "WORKING-STORAGE", "PERFORM", "MOVE"],
        "entry_patterns": ["PROGRAM-ID"],
        "data_patterns": ["FD ", "01 ", "COPY "],
    },
    "java": {
        "extensions": [".java"],
        "markers": ["public class", "public static void main", "import java.", "package "],
        "entry_patterns": ["public static void main"],
        "data_patterns": ["@Entity", "@Table", "ResultSet", "PreparedStatement"],
    },
    "python": {
        "extensions": [".py"],
        "markers": ["def ", "class ", "import ", "from "],
        "entry_patterns": ['if __name__ == "__main__"', "if __name__ == '__main__'"],
        "data_patterns": ["pandas", "sqlalchemy", "django.db", "cursor.execute"],
    },
    "csharp": {
        "extensions": [".cs"],
        "markers": ["namespace ", "using System", "public class"],
        "entry_patterns": ["static void Main", "static async Task Main"],
        "data_patterns": ["DbContext", "SqlConnection", "Entity"],
    },
    "plsql": {
        "extensions": [".sql", ".pls", ".pkb", ".pks"],
        "markers": ["CREATE OR REPLACE", "DECLARE", "BEGIN", "PL/SQL"],
        "entry_patterns": ["CREATE OR REPLACE PROCEDURE", "CREATE OR REPLACE FUNCTION"],
        "data_patterns": ["SELECT ", "INSERT ", "UPDATE ", "DELETE "],
    },
}

IGNORE_DIRS = {
    ".git", ".svn", ".hg", "node_modules", "__pycache__", ".claude",
    "target", "build", "dist", ".gradle", ".idea", ".vscode",
    "vendor", "venv", ".venv", "env",
}

IGNORE_FILES = {
    ".DS_Store", "Thumbs.db", ".gitignore", ".gitattributes",
}


def scan_filesystem(root: str, max_depth: int = 20) -> dict:
    """Layer 1: Build filesystem tree with file metadata."""
    tree = {"type": "directory", "name": os.path.basename(root), "path": root, "children": []}
    file_index = []

    for dirpath, dirnames, filenames in os.walk(root):
        # Filter ignored directories in-place
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]

        rel_dir = os.path.relpath(dirpath, root)
        depth = 0 if rel_dir == "." else rel_dir.count(os.sep) + 1
        if depth > max_depth:
            dirnames.clear()
            continue

        for fname in filenames:
            if fname in IGNORE_FILES:
                continue
            fpath = os.path.join(dirpath, fname)
            rel_path = os.path.relpath(fpath, root)
            try:
                stat = os.stat(fpath)
                ext = os.path.splitext(fname)[1].lower()
                file_index.append({
                    "path": rel_path,
                    "extension": ext,
                    "size_bytes": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                })
            except OSError:
                continue

    return {
        "root": root,
        "total_files": len(file_index),
        "files": file_index,
    }


def detect_languages(file_index: list) -> dict:
    """Detect languages present in the codebase by extension frequency."""
    ext_counts = defaultdict(int)
    for f in file_index:
        if f["extension"]:
            ext_counts[f["extension"]] += 1

    detected = {}
    for lang, sig in LANGUAGE_SIGNATURES.items():
        matching_files = sum(ext_counts.get(ext, 0) for ext in sig["extensions"])
        if matching_files > 0:
            detected[lang] = {
                "file_count": matching_files,
                "extensions": [ext for ext in sig["extensions"] if ext_counts.get(ext, 0) > 0],
            }

    return detected


def apply_heuristics(root: str, file_index: list, languages: dict, depth: str = "shallow") -> dict:
    """Layer 2: Text heuristics — entry points, data flows, structure."""
    heuristics = {
        "entry_points": [],
        "data_sources": [],
        "copybooks": [],
        "call_graph_hints": [],
        "structural_patterns": [],
    }

    # Only scan source files for the detected languages
    source_extensions = set()
    for lang_info in languages.values():
        source_extensions.update(lang_info["extensions"])

    source_files = [f for f in file_index if f["extension"] in source_extensions]

    # Limit scan in shallow mode
    if depth == "shallow":
        source_files = source_files[:200]

    for finfo in source_files:
        fpath = os.path.join(root, finfo["path"])
        try:
            with open(fpath, "r", encoding="utf-8", errors="replace") as fh:
                content = fh.read(50000)  # First 50KB
        except (OSError, UnicodeDecodeError):
            continue

        lines = content.split("\n")

        for lang, sig in LANGUAGE_SIGNATURES.items():
            if finfo["extension"] not in sig["extensions"]:
                continue

            # Entry points
            for pattern in sig["entry_patterns"]:
                for i, line in enumerate(lines):
                    if pattern in line:
                        heuristics["entry_points"].append({
                            "file": finfo["path"],
                            "line": i + 1,
                            "pattern": pattern,
                            "language": lang,
                        })

            # Data patterns
            for pattern in sig["data_patterns"]:
                for i, line in enumerate(lines):
                    if pattern in line:
                        heuristics["data_sources"].append({
                            "file": finfo["path"],
                            "line": i + 1,
                            "pattern": pattern,
                            "language": lang,
                        })
                        break  # One per file per pattern

            # COBOL-specific: copybook references
            if lang == "cobol":
                for i, line in enumerate(lines):
                    stripped = line.strip()
                    if stripped.startswith("COPY "):
                        copybook = stripped.split()[1].rstrip(".")
                        heuristics["copybooks"].append({
                            "file": finfo["path"],
                            "line": i + 1,
                            "copybook": copybook,
                        })
                    # CALL statements
                    if "CALL " in stripped and lang == "cobol":
                        parts = stripped.split("CALL ")
                        if len(parts) > 1:
                            callee = parts[1].split()[0].strip("'\".")
                            heuristics["call_graph_hints"].append({
                                "caller": finfo["path"],
                                "callee": callee,
                                "line": i + 1,
                            })

    # Deduplicate data sources
    seen = set()
    deduped = []
    for ds in heuristics["data_sources"]:
        key = (ds["file"], ds["pattern"])
        if key not in seen:
            seen.add(key)
            deduped.append(ds)
    heuristics["data_sources"] = deduped

    return heuristics


def analyze_vcs_history(root: str, max_commits: int = 500) -> dict:
    """Layer 3: VCS history — hotspots, ownership, change frequency."""
    vcs = {
        "available": False,
        "hotspots": [],
        "authors": {},
        "recent_changes": [],
    }

    try:
        result = subprocess.run(
            ["git", "log", f"--max-count={max_commits}", "--pretty=format:%H|%ae|%ai|%s", "--name-only"],
            cwd=root, capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            return vcs
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return vcs

    vcs["available"] = True
    file_changes = defaultdict(int)
    file_authors = defaultdict(set)
    author_commits = defaultdict(int)

    current_commit = None
    for line in result.stdout.split("\n"):
        line = line.strip()
        if not line:
            continue
        if "|" in line and line.count("|") >= 3:
            parts = line.split("|", 3)
            current_commit = {
                "hash": parts[0],
                "author": parts[1],
                "date": parts[2],
                "message": parts[3],
            }
            author_commits[parts[1]] += 1
            if len(vcs["recent_changes"]) < 20:
                vcs["recent_changes"].append(current_commit)
        elif current_commit:
            file_changes[line] += 1
            file_authors[line].add(current_commit["author"])

    # Compute hotspots (most frequently changed files)
    hotspots = sorted(file_changes.items(), key=lambda x: x[1], reverse=True)[:30]
    vcs["hotspots"] = [
        {"file": f, "change_count": c, "authors": list(file_authors[f])}
        for f, c in hotspots
    ]

    vcs["authors"] = {
        author: {"commit_count": count}
        for author, count in sorted(author_commits.items(), key=lambda x: x[1], reverse=True)
    }

    return vcs


def build_codemap(root: str, depth: str = "shallow", output: str = None) -> dict:
    """Build the complete codemap artifact."""
    print(f"[codemap] Scanning {root} (depth={depth})...")

    # Layer 1: Filesystem
    print("[codemap] Layer 1: Filesystem structure...")
    fs = scan_filesystem(root)

    # Detect languages
    languages = detect_languages(fs["files"])
    print(f"[codemap] Detected languages: {', '.join(languages.keys()) or 'none'}")

    # Layer 2: Text heuristics
    print("[codemap] Layer 2: Text heuristics...")
    heuristics = apply_heuristics(root, fs["files"], languages, depth)

    # Layer 3: VCS history
    print("[codemap] Layer 3: VCS history...")
    vcs = analyze_vcs_history(root)

    codemap = {
        "version": "1.0",
        "generated_at": datetime.now().isoformat(),
        "depth": depth,
        "root": root,
        "summary": {
            "total_files": fs["total_files"],
            "languages": languages,
            "entry_points": len(heuristics["entry_points"]),
            "data_sources": len(heuristics["data_sources"]),
            "vcs_available": vcs["available"],
        },
        "filesystem": {
            "total_files": fs["total_files"],
            "files_by_extension": _group_by_extension(fs["files"]),
        },
        "heuristics": heuristics,
        "vcs": vcs,
    }

    if output:
        os.makedirs(os.path.dirname(output), exist_ok=True)
        with open(output, "w") as f:
            json.dump(codemap, f, indent=2)
        print(f"[codemap] Written to {output}")

    return codemap


def _group_by_extension(files: list) -> dict:
    groups = defaultdict(list)
    for f in files:
        ext = f["extension"] or "(no extension)"
        groups[ext].append(f["path"])
    return {ext: {"count": len(paths), "files": paths[:20]} for ext, paths in groups.items()}


def main():
    parser = argparse.ArgumentParser(description="Codebase Analyzer")
    parser.add_argument("--root", required=True, help="Project root directory")
    parser.add_argument("--depth", choices=["shallow", "deep"], default="shallow")
    parser.add_argument("--output", default="artifacts/codemap.json")
    args = parser.parse_args()

    codemap = build_codemap(args.root, args.depth, args.output)

    print(f"\n[codemap] Summary:")
    print(f"  Files: {codemap['summary']['total_files']}")
    print(f"  Languages: {json.dumps(codemap['summary']['languages'], indent=2)}")
    print(f"  Entry points: {codemap['summary']['entry_points']}")
    print(f"  Data sources: {codemap['summary']['data_sources']}")


if __name__ == "__main__":
    main()
