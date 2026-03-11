# Code Modernization Plugin for Claude Code

## What Is This?

This is a **Claude Code plugin** — a bundle of slash commands, subagents, hooks, and Python scripts that together orchestrate enterprise code modernization. It turns Claude Code into a migration workbench: analyzing legacy codebases, interviewing stakeholders, computing migration slices, generating golden test datasets, migrating code with confidence scoring, and gating commits behind human review.

The plugin follows the official Claude Code plugin format:

```
plugin/
├── .claude-plugin/
│   └── plugin.json           # Plugin manifest
├── commands/                  # 8 slash commands
├── agents/                    # 4 subagents
├── hooks/                     # Event-driven hooks
├── scripts/                   # Python computational scripts
└── templates/                 # Config and schema templates
```

When installed into a target project, it deploys to:

```
your-project/
├── .claude/
│   ├── commands/              # Slash commands (the user interface)
│   ├── agents/                # Subagents (specialist workers)
│   └── settings.json          # Hooks (automated validation)
├── .modernization/
│   ├── scripts/               # Python scripts (the computational engine)
│   └── schemas/               # JSON schemas (data contracts)
├── artifacts/                 # Generated artifacts (all outputs live here)
├── modernization.config.json  # Project configuration
└── CLAUDE.md                  # Project guide for Claude
```

---

## How Claude Code Plugins Work

A Claude Code plugin is a collection of **extension mechanisms** bundled together:

| Mechanism | Location | What It Does |
|-----------|----------|--------------|
| **Slash Commands** | `.claude/commands/*.md` | User-invoked prompts. Type `/codemap` and Claude follows the instructions in `codemap.md`. |
| **Subagents** | `.claude/agents/*.md` | Specialist AI workers. The orchestrator delegates tasks to agents that run in their own context with restricted tools. |
| **Hooks** | `.claude/settings.json` | Automated triggers. When Claude writes a `.java` file, the hook fires validation. When someone tries to overwrite the golden dataset, the hook blocks it. |
| **Scripts** | `.modernization/scripts/` | Python programs that do the heavy computation — scanning filesystems, building graphs, computing slices, scoring confidence. |
| **CLAUDE.md** | Project root | Persistent instructions that Claude reads at the start of every conversation. Defines the migration methodology. |

Commands are the **user interface**. Agents are the **workers**. Hooks are the **guardrails**. Scripts are the **engine**.

---

## Installation

### Prerequisites

- **Claude Code** CLI installed and authenticated
- **Python 3.8+** (for the analysis and validation scripts)
- **Git** (for VCS history analysis)

### Install the Plugin

```bash
# From the plugin directory, install into your target project:
./plugin/install.sh /path/to/your/legacy/project

# Or install into the current directory:
cd /path/to/your/legacy/project
/path/to/plugin/install.sh .

# Preview what will be installed without modifying anything:
./plugin/install.sh /path/to/project --dry-run
```

### Post-Install Configuration

Edit `modernization.config.json` in your project root:

```json
{
  "project": {
    "name": "payroll-system",
    "description": "COBOL payroll batch processing",
    "source_language": "cobol",
    "target_language": "java"
  },
  "scoring": {
    "thresholds": {
      "auto_approve": 95,
      "review_recommended": 80
    }
  }
}
```

### Verify Installation

Start Claude Code in your project and type `/codemap`. If you see Claude running the codebase analyzer, the plugin is working.

---

## The Migration Pipeline

The plugin implements a structured, gated pipeline. Here is the full flow:

```
  DISCOVER          UNDERSTAND          PLAN             EXECUTE          VERIFY
┌──────────┐    ┌──────────────┐    ┌──────────┐    ┌──────────────┐   ┌────────┐
│ /codemap │───▶│   /elicit    │───▶│  Build   │───▶│   /migrate   │──▶│ Score  │
│ (shallow)│    │ (6 sessions) │    │  graph   │    │  per slice   │   │ & gate │
└──────────┘    └──────────────┘    │  & slice │    └──────────────┘   └────────┘
     │                │             └──────────┘          │                 │
     │                │                  │                │                 │
     ▼                ▼                  ▼                ▼                 ▼
 codemap.json   interview.json   slice-manifest.json   Java code    confidence-score.json
                                                      + quirks.md
```

Each stage produces **artifacts** that feed the next. All artifacts live in `artifacts/`. Work is resumable — if you stop mid-pipeline, you can pick up where you left off because every stage checks for existing artifacts.

Human review gates exist at:
1. After codemap — "Does this analysis look right?"
2. After interview synthesis — "Did I understand your system correctly?"
3. After slicing — "Do these migration boundaries make sense?"
4. After migration — Confidence score determines the gate level
5. Before commit — "Ready to create a PR?"

---

## Commands Reference

### `/modernize` — The Orchestrator

Drives the full pipeline from discovery to PR. This is the "autopilot" command.

```
/modernize                # Start from the beginning
/modernize migrate        # Resume from the migration stage
```

The orchestrator runs each stage in sequence, pausing at human gates. It is the recommended way to use the plugin for a complete migration.

---

### `/codemap` — Codebase Discovery

Scans your codebase using filesystem analysis, text heuristics, and VCS history.

```
/codemap                  # Shallow scan (fast, first 200 source files)
/codemap --shallow        # Same as above
/codemap --deep           # Full scan + dependency graph extraction
```

**What it finds:**
- Languages present and file counts
- Entry points (PROGRAM-ID, main(), `__main__`)
- Data sources (FD declarations, @Entity, SQL patterns)
- COBOL COPY/CALL relationships
- Git hotspots (most frequently changed files)
- Key contributors and recent activity

**Artifacts produced:**
- `artifacts/codemap.json` — Complete analysis
- `artifacts/dependency-graph.json` — Program dependencies (deep mode only)

**Supported languages:** COBOL, Java, Python, C#, PL/SQL. The analyzer auto-detects based on file extensions and source markers.

---

### `/elicit` — Stakeholder Interviews

Conducts structured interviews to extract knowledge that static analysis cannot see.

```
/elicit orientation              # Session 1: What is this system?
/elicit behavioral-contracts     # Session 2: How should it behave?
/elicit seam-mapping             # Session 3: Where are the boundaries?
/elicit target-state             # Session 4: What should the end state look like?
/elicit constraints              # Session 5: What are the non-negotiables?
/elicit synthesis                # Session 6: Confirm understanding
```

Each session asks 5-7 focused questions, one at a time. Claude adapts follow-up questions based on your answers and any prior codemap findings.

The recommended interleaving is:
1. `/codemap` (cheap, shallow scan)
2. `/elicit orientation` (now you have context to ask better questions)
3. `/codemap --deep` (targeted deep scan informed by the interview)
4. `/elicit behavioral-contracts` through `/elicit synthesis`

**Artifact produced:** `artifacts/interview.json` — Cumulative findings from all sessions.

---

### `/query-slices` — View Migration Slices

Shows the computed migration slices and their status.

```
/query-slices                    # Show available (unclaimed) slices
/query-slices --all              # Show all slices regardless of status
/query-slices --mine             # Show slices you've claimed
/query-slices --status=migrating # Filter by status
/query-slices --id=slice-001     # Detailed view of a specific slice
```

**Example output:**
```
Migration Slices — 5 total
  Available: 3 | Claimed: 1 | Approved: 1

  ID         Name                    Complexity  Programs  Status
  slice-001  Employee Salary         low         1         approved (score: 98.5)
  slice-002  Benefits Calculation    medium      2         claimed (alice)
  slice-003  Payroll Batch           high        4         available
  slice-004  Tax Withholding         low         1         available
  slice-005  Report Generator        medium      3         available
```

**Requires:** `artifacts/slice-manifest.json` (generated by `/codemap --deep` + graph construction)

---

### `/claim-slice` — Claim a Slice

Locks a slice for your migration work. Prevents conflicting work by other engineers.

```
/claim-slice slice-003           # Claim slice-003
/claim-slice slice-003 --release # Release your claim
```

Claiming checks that:
- The slice exists and is available
- Warns if upstream dependencies are unclaimed (doesn't block, but warns)

After claiming, the command suggests: "Next step: `/migrate slice-003`"

---

### `/migrate` — Migrate a Slice

Orchestrates the full migration pipeline for a single claimed slice.

```
/migrate slice-003
```

**What happens (5 stages):**

**Stage 1 — Document:** The `cobol-documenter` subagent reads the source code and produces a structured analysis: data layouts, business rules, file I/O patterns, quirks, and byte offsets.

**Stage 2 — Golden Dataset:** The `golden-dataset-builder` subagent generates synthetic test inputs covering all code paths (normal, boundary, overflow, error, edge cases), runs the source program against them, and captures the outputs as the immutable reference dataset. It also documents behavioral quirks discovered during execution.

**Stage 3 — Validate Harness:** Confirms the validation scripts and semantic diff rules are in place.

**Stage 4 — Write Target Code:** Claude writes the target implementation based on the analysis, quirks, and interview artifacts. The PostToolUse hook fires validation after each file is written.

**Stage 5 — Score & Gate:** The confidence scorer evaluates the migration:

| Score | Gate | What Happens |
|-------|------|--------------|
| >= 95 | Auto-approve eligible | "Confidence is high. Ready to commit?" |
| 80-94 | Human review recommended | Shows the diff and failing test cases |
| < 80 | Human review **required** | Stops. Suggests investigation with `/elicit` |

---

### `/validate` — Manual Validation

Runs validation outside the automatic hook flow.

```
/validate                        # Validate the most recent migration
/validate --slice=slice-003      # Validate a specific slice
/validate --full                 # Validate all migrated slices
/validate --score-only           # Just compute the confidence score
```

Useful for re-running after fixing issues, or when you want to check the score without triggering the full pipeline.

---

### `/batch` — Bulk Migration

Runs `/migrate` across multiple slices in dependency order.

```
/batch                           # Migrate all available slices
/batch --dry-run                 # Show the execution plan without running
/batch --slices=001,002,003      # Migrate specific slices
```

Batch mode:
- Computes topological order from the dependency graph
- Only processes a slice if all its dependencies are approved
- **Stops on the first failure** — never skips a failing slice
- Reports progress after each slice

Dry run shows the plan:
```
Batch Plan — 5 slices

  1. slice-001  Employee Salary         [low]    no deps
  2. slice-004  Tax Withholding         [low]    no deps
  3. slice-002  Benefits Calculation    [medium] after slice-001
  4. slice-005  Report Generator        [medium] after slice-004
  5. slice-003  Payroll Batch           [high]   after slice-001, slice-002
```

---

## Subagents Reference

Subagents are specialist workers that the orchestrator delegates to. They run in their own context with restricted tool access.

### `cobol-documenter`
**Model:** Sonnet | **Tools:** Read, Grep, Glob (read-only)

Produces `<program>-analysis.md` with: program overview, data structures (with byte offsets), business rules, file I/O patterns, quirks and risks, migration risk ratings.

### `golden-dataset-builder`
**Model:** Sonnet | **Tools:** Read, Write, Bash, Glob, Grep

Generates test cases across 5 categories (NC/BC/BO/ER/EC), runs the source program with the safe runner, captures golden outputs, and documents quirks in `<program>-quirks.md`.

### `code-analyzer`
**Model:** Sonnet | **Tools:** Read, Grep, Glob, Bash (read-only)

Language-agnostic codebase analysis. Use this for non-COBOL codebases. Produces the same structured output as `cobol-documenter` but works with any language.

### `migration-scorer`
**Model:** Sonnet | **Tools:** Read, Bash, Glob, Grep (read-only)

Independent quality assessor. Evaluates test results, quirks coverage, semantic diff results, build quality, and documentation completeness. Produces a scored assessment with gate recommendation.

---

## Confidence Scoring

The scorer evaluates migrations on 5 dimensions:

| Component | Weight | What It Measures |
|-----------|--------|------------------|
| Byte match | 50% | Test pass rate (golden output vs target output) |
| Coverage | 20% | Diversity of test categories covered |
| Quirks documented | 15% | Completeness of behavioral quirks documentation |
| Semantic match | 10% | Semantic equivalence after diff rules are applied |
| Structural quality | 5% | Clean build, no warnings |

**Thresholds** (configurable in `modernization.config.json`):
- **>= 95**: Auto-approve eligible
- **80-94**: Human review recommended
- **< 80**: Human review required (gate blocks commit)

---

## Semantic Diff Rules

Sometimes byte-for-byte differences are acceptable (trailing spaces, date format changes, floating point precision). Semantic diff rules let you declare these exceptions.

Edit `artifacts/semantic-diff-rules.json`:

```json
{
  "rules": [
    {
      "id": "trailing-spaces",
      "type": "regex_replace",
      "pattern": " +$",
      "replacement": "",
      "apply_to": "both",
      "enabled": true
    },
    {
      "id": "commission-tolerance",
      "type": "numeric_tolerance",
      "field_offset": 60,
      "field_length": 9,
      "tolerance": 0.01,
      "enabled": true
    }
  ]
}
```

**Rule types:**
- `regex_replace` — Normalize with regex before comparison
- `field_transform` — Transform a specific field (e.g., strip dashes from dates)
- `numeric_tolerance` — Allow small numeric differences in a specific field

Validate your rules: `python3 .modernization/scripts/validation/semantic_diff.py --rules artifacts/semantic-diff-rules.json --validate-rules`

---

## Artifacts Reference

All generated artifacts live in `artifacts/`. Here is what each file contains and which commands produce/consume it:

| Artifact | Produced By | Consumed By | Contents |
|----------|-------------|-------------|----------|
| `codemap.json` | `/codemap` | `/elicit`, graph builder | Filesystem, heuristics, VCS analysis |
| `dependency-graph.json` | `/codemap --deep` | Graph store | Nodes (programs, copybooks) and edges (CALLS, COPIES) |
| `knowledge-graph.json` | `/modernize` (stage 5) | Slicer | Full knowledge graph with all relationships |
| `interview.json` | `/elicit` | `/migrate`, `/modernize` | Stakeholder responses and cumulative findings |
| `slice-manifest.json` | Slicer | `/query-slices`, `/claim-slice`, `/migrate`, `/batch` | Slice definitions, status, ownership, scores |
| `semantic-diff-rules.json` | Template | `/validate`, `/migrate` | Acceptable difference rules |
| `validation-results.json` | `/validate`, `/migrate` | Confidence scorer | Per-test-case pass/fail with byte-level diffs |
| `confidence-score.json` | `/validate`, `/migrate` | Gate decisions | Score, components, gate recommendation |

---

## Hooks Reference

The plugin installs these hooks in `.claude/settings.json`:

| Event | Trigger | Action |
|-------|---------|--------|
| `PostToolUse` | `Write(*.java)` | Notifies that validation will run after build |
| `PostToolUse` | `Write(*.py)` | Notifies if writing in migration context |
| `PreToolUse` | `Write(.env*)` | **Blocks** — protects secrets, directs to config file |
| `PreToolUse` | `Write(artifacts/golden_dataset/*)` | **Blocks** — golden dataset is immutable once created |

---

## Python Scripts Reference

These scripts can be run directly from the command line or invoked by the slash commands.

### Codebase Analyzer
```bash
python3 .modernization/scripts/codemap/analyzer.py \
  --root /path/to/project \
  --depth shallow|deep \
  --output artifacts/codemap.json
```

### Dependency Graph Builder
```bash
python3 .modernization/scripts/codemap/dependency_graph.py \
  --codemap artifacts/codemap.json \
  --output artifacts/dependency-graph.json
```

### Knowledge Graph Store
```bash
# Import dependencies into the graph
python3 .modernization/scripts/graph/graph_store.py \
  --graph artifacts/knowledge-graph.json \
  --action import \
  --source artifacts/dependency-graph.json

# Query the graph
python3 .modernization/scripts/graph/graph_store.py \
  --graph artifacts/knowledge-graph.json \
  --action query --type program

# Show dependency order
python3 .modernization/scripts/graph/graph_store.py \
  --graph artifacts/knowledge-graph.json \
  --action topo-order

# Summary
python3 .modernization/scripts/graph/graph_store.py \
  --graph artifacts/knowledge-graph.json \
  --action summary
```

### Slice Computation
```bash
python3 .modernization/scripts/graph/slicer.py \
  --graph artifacts/knowledge-graph.json \
  --output artifacts/slice-manifest.json \
  --strategy entry-point|connected-components
```

### Semantic Diff
```bash
# Compare two files
python3 .modernization/scripts/validation/semantic_diff.py \
  --cobol output_cobol.dat --java output_java.dat \
  --rules artifacts/semantic-diff-rules.json

# Compare directories
python3 .modernization/scripts/validation/semantic_diff.py \
  --cobol-dir golden_dataset/ --java-dir java_outputs/ \
  --rules artifacts/semantic-diff-rules.json \
  --output artifacts/validation-results.json
```

### Confidence Scorer
```bash
python3 .modernization/scripts/validation/confidence_scorer.py \
  --results artifacts/validation-results.json \
  --quirks empsal-quirks.md \
  --config modernization.config.json \
  --output artifacts/confidence-score.json
```

---

## Workflow Examples

### Example 1: First-Time Migration (Full Pipeline)

```
You:    /modernize
Claude: [Runs shallow codemap]
        Found 12 COBOL programs, 8 copybooks, 3 data files.
        Does this look right?
You:    Yes, but we also have JCL scripts in the jcl/ directory
Claude: [Noted. Running orientation interview]
        What does this system do in plain language?
You:    It processes weekly payroll for 50,000 employees...
        [... 6 interview sessions ...]
Claude: [Runs deep codemap, builds graph, computes slices]
        I found 5 migration slices:
          slice-001: Employee Salary (low complexity, no deps)
          slice-002: Benefits (medium, depends on slice-001)
          ...
        Do these boundaries make sense?
You:    Yes. Start with slice-001.
Claude: [Claims slice-001, runs /migrate]
        [Documents COBOL, generates golden dataset, writes Java]
        Confidence score: 98.5 / 100 — Auto-approve eligible.
        Ready to commit?
You:    Yes.
Claude: [Creates commit and PR]
```

### Example 2: Engineer Picks Up a Slice

```
You:    /query-slices --available
Claude: 3 slices available:
          slice-003: Payroll Batch [high] — depends on slice-001, slice-002
          slice-004: Tax Withholding [low] — no deps
          slice-005: Report Generator [medium] — depends on slice-004
        Recommendation: Start with slice-004 (no dependencies).

You:    /claim-slice slice-004
Claude: Claimed slice-004 (Tax Withholding).
        Next: /migrate slice-004

You:    /migrate slice-004
Claude: [Full migration pipeline runs...]
```

### Example 3: Handling a Low Confidence Score

```
Claude: Confidence score: 72.3 / 100 — REVIEW REQUIRED.
        Failing tests:
          BO-001: Overflow — COBOL wraps at 10 digits, Java throws exception
          BO-002: Same issue

        The target implementation needs to replicate COBOL's modular arithmetic
        for overflow cases. Would you like to:
        1. Add a semantic diff rule to accept this difference
        2. Fix the Java to match COBOL behavior
        3. Run /elicit to discuss overflow handling

You:    Fix the Java. COBOL behavior is the requirement.
Claude: [Fixes overflow handling, re-runs validation]
        Confidence score: 99.2 / 100 — Auto-approve eligible.
```

### Example 4: Bulk Migration

```
You:    /batch --dry-run
Claude: Batch Plan — 5 slices
          1. slice-001 (no deps)
          2. slice-004 (no deps)
          3. slice-002 (after 001)
          4. slice-005 (after 004)
          5. slice-003 (after 001, 002)

        Ready to proceed?

You:    Go.
Claude: [Migrates slice-001... score 98.5, approved]
        [Migrates slice-004... score 97.2, approved]
        [Migrates slice-002... score 91.3, review recommended]

        Batch paused. slice-002 scored 91.3 — review recommended.
        Would you like to approve, investigate, or stop?
```

---

## Configuration Reference

`modernization.config.json` controls all plugin behavior:

```json
{
  "project": {
    "name": "payroll-system",          // Project identifier
    "source_language": "cobol",        // Source language
    "target_language": "java"          // Target language
  },
  "scoring": {
    "weights": {
      "byte_match": 0.50,             // Test pass rate weight
      "coverage": 0.20,               // Test diversity weight
      "quirks_documented": 0.15,      // Quirks doc completeness
      "semantic_match": 0.10,         // Post-rule match rate
      "structural": 0.05              // Build quality
    },
    "thresholds": {
      "auto_approve": 95,             // Score for auto-approval
      "review_recommended": 80        // Score below this requires review
    }
  },
  "slicing": {
    "strategy": "entry-point",        // or "connected-components"
    "max_slice_size": 10              // Max programs per slice
  },
  "build": {
    "command": "cd empsal/java && mvn clean package -q"
  }
}
```

---

## Extending the Plugin

### Adding Support for a New Source Language

1. Add language signatures to `scripts/codemap/analyzer.py` in `LANGUAGE_SIGNATURES`
2. Add an extractor function to `scripts/codemap/dependency_graph.py`
3. Create a new documenter agent in `agents/` (e.g., `plsql-documenter.md`)
4. Update the golden-dataset-builder to handle the new language's execution

### Adding a Custom Semantic Diff Rule Type

1. Add a new `_apply_*` method to `SemanticDiffEngine` in `scripts/validation/semantic_diff.py`
2. Handle the new type in the `compare()` method
3. Document the new rule type in `artifacts/semantic-diff-rules.json`

### Swapping the JSON Graph for Neo4j

The `GraphStore` class in `scripts/graph/graph_store.py` is designed with a swappable interface. To use Neo4j:

1. Create an MCP server wrapping Neo4j
2. Implement the same methods: `add_node`, `get_node`, `query_nodes`, `add_edge`, `get_dependencies`, etc.
3. Update the commands to use the MCP server instead of the Python script

---

## Troubleshooting

**"artifacts/slice-manifest.json not found"**
Run `/codemap --deep` first, then the graph construction and slicer stages. Or run `/modernize` to execute the full pipeline.

**"No compiled JAR file found"**
The validation hook fires after `.java` writes, but before Maven builds. Run `mvn clean package` first, then re-run `/validate`.

**Confidence score is 0**
No test results found. Ensure the golden dataset has been generated and validation has been run.

**Hook blocks my write to golden dataset**
The golden dataset is immutable by design. To regenerate, delete the `golden_dataset/` directory first, then re-run the dataset builder.

**Two engineers claimed the same slice**
The manifest file is the source of truth. Coordinate with your team. For multi-user environments, a database-backed locking mechanism is planned for a future version.
