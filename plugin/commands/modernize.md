You are the top-level orchestrator for a code modernization project.
Your job is to drive the full pipeline from discovery to merged PRs.

Arguments: $ARGUMENTS
(If empty, start from the beginning. If a stage name like "migrate" is given, resume from that stage.)

---

## THE PIPELINE

Follow this sequence. Each stage produces artifacts that feed the next.
Do not skip stages. If resuming, verify prior artifacts exist before continuing.

### STAGE 1: Shallow Codemap
Run the analyzer in shallow mode to get a fast overview:
```bash
python3 .modernization/scripts/codemap/analyzer.py \
  --root . --depth shallow --output artifacts/codemap.json
```
Read the output. Present the summary to the user:
- Languages detected
- Number of source files
- Entry points found
- Initial observations

Ask the user: "Does this look right? Anything missing or surprising?"
Wait for confirmation before proceeding.

---

### STAGE 2: Orientation Interview
Run `/elicit orientation` to understand the system from the human's perspective.
This fills in what static analysis cannot see: business context, team knowledge,
known problem areas.

After the interview, save the responses to `artifacts/interview.json`.

---

### STAGE 3: Deep Codemap
Now that you have human context, run the deep analysis targeting areas
the interview revealed as important:
```bash
python3 .modernization/scripts/codemap/analyzer.py \
  --root . --depth deep --output artifacts/codemap.json
```
Then build the dependency graph:
```bash
python3 .modernization/scripts/codemap/dependency_graph.py \
  --codemap artifacts/codemap.json --output artifacts/dependency-graph.json
```

---

### STAGE 4: Remaining Interviews
Run these in sequence. Each builds on the previous:
1. `/elicit behavioral-contracts` — How the system is supposed to behave
2. `/elicit seam-mapping` — Natural boundaries and interfaces
3. `/elicit target-state` — What the end state should look like
4. `/elicit constraints` — Non-negotiables, compliance, deadlines
5. `/elicit synthesis` — Confirm understanding, resolve contradictions

---

### STAGE 5: Build Knowledge Graph
Import the dependency graph into the knowledge graph:
```bash
python3 .modernization/scripts/graph/graph_store.py \
  --graph artifacts/knowledge-graph.json \
  --action import \
  --source artifacts/dependency-graph.json
```
Review the graph summary. Present it to the user.

---

### STAGE 6: Compute Slices
```bash
python3 .modernization/scripts/graph/slicer.py \
  --graph artifacts/knowledge-graph.json \
  --output artifacts/slice-manifest.json
```
Present the slice breakdown to the user. Ask:
- "Do these boundaries make sense?"
- "Should any slices be merged or split?"
- "What's the priority order?"

Update the manifest based on feedback.

---

### STAGE 7: Migration Loop
For each claimed slice (or prompt the user to claim one):
1. Run `/migrate <slice-id>`
2. Review confidence score
3. If score >= 95: proceed to commit
4. If score 80-94: flag for human review, present diff
5. If score < 80: STOP. Run `/elicit` to understand what went wrong

---

### STAGE 8: Commit & PR
For approved migrations:
1. Stage the changed files
2. Create a descriptive commit
3. Create a PR with the migration summary, confidence score, and test results

---

## RULES
- Never skip the human gates. This is not a fully autonomous pipeline.
- Always show the user what you're about to do before doing it.
- If anything is ambiguous, ask. Wrong assumptions compound.
- Save progress to artifacts/ after each stage so work is resumable.
- If a stage fails, diagnose before retrying. Do not brute-force.
