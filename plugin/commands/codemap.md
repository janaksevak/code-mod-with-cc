You are running the codemap — automated codebase discovery.

Arguments: $ARGUMENTS
(Options: --shallow, --deep, or empty which defaults to shallow)

---

## WHAT YOU DO

Codemap performs layered discovery of the codebase:

1. **Filesystem structure** — Directory layout, file types, sizes
2. **Text heuristics** — Language detection, entry points, data flows, COPY/CALL/import patterns
3. **VCS history** — Change hotspots, ownership, recent activity
4. **Dependencies** — Call graphs, include chains, data file usage

---

## EXECUTION

### Determine depth
Parse $ARGUMENTS for depth flag. Default to "shallow" if not specified.

### Run the analyzer
```bash
python3 .modernization/scripts/codemap/analyzer.py \
  --root . \
  --depth <shallow|deep> \
  --output artifacts/codemap.json
```

### If deep: also build dependency graph
```bash
python3 .modernization/scripts/codemap/dependency_graph.py \
  --codemap artifacts/codemap.json \
  --output artifacts/dependency-graph.json
```

---

## PRESENT RESULTS

After running, read `artifacts/codemap.json` and present a structured summary:

### Overview
- Total files and breakdown by language
- Source vs config vs test vs docs ratio

### Architecture Signals
- Entry points (programs, main classes, request handlers)
- Data sources (databases, file I/O, external APIs)
- Shared components (copybooks, libraries, shared modules)

### VCS Insights (if available)
- Hotspot files (most frequently changed)
- Key contributors
- Recent activity patterns

### Risk Areas
- Files with high change frequency + many contributors (merge risk)
- Large files with no test coverage signals
- Orphaned files (no references from other code)

### Recommendations
- Suggested areas for deeper investigation
- Potential natural boundaries for slicing
- Dependencies that should be migrated first (shared copybooks, base classes)

---

## OUTPUT

The codemap artifact is saved to `artifacts/codemap.json`.
If deep mode was used, the dependency graph is at `artifacts/dependency-graph.json`.

These artifacts are consumed by:
- `/elicit` — to inform interview questions
- `/modernize` — to build the knowledge graph
- The slicer — to compute migration slices
