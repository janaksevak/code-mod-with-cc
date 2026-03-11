You are running batch migration across multiple slices.

Arguments: $ARGUMENTS
(Options: --all-available, --slices=001,002,003, --dry-run, or empty which processes all available slices in dependency order)

---

## WHAT YOU DO

Batch orchestrates `/migrate` across multiple slices sequentially,
respecting dependency order. This is the "scale" mode — when you
have many slices to migrate and want to process them systematically.

---

## EXECUTION

### Load manifest
Read `artifacts/slice-manifest.json`.

### Determine which slices to process
- `--all-available` or empty — All slices with status "available" or "claimed"
- `--slices=001,002,003` — Specific slice IDs
- `--dry-run` — Show what would be processed without executing

### Compute execution order
Use the dependency graph to order slices:
```bash
python3 .modernization/scripts/graph/graph_store.py \
  --graph artifacts/knowledge-graph.json \
  --action topo-order
```

Only process a slice if all its dependencies have status "approved" or "merged".
Skip blocked slices and report them.

### Execute

For each slice in order:

1. **Claim** (if not already claimed)
   - Auto-claim for batch processing

2. **Migrate**
   - Run the full `/migrate` pipeline
   - Capture the confidence score

3. **Gate check**
   - If score >= auto-approve threshold: mark approved, continue
   - If score < threshold: STOP the batch, report the blocking slice
   - Do NOT skip failing slices — they may block downstream slices

4. **Report progress**
   After each slice, update and display:
   ```
   Batch Progress: 3/8 slices complete
     slice-001: approved (score: 98.5)
     slice-002: approved (score: 96.2)
     slice-003: approved (score: 97.8)
     slice-004: IN PROGRESS...
     slice-005: pending (blocked by slice-004)
     slice-006: pending
     slice-007: pending
     slice-008: pending (blocked by slice-006)
   ```

### Final report

After the batch completes (or stops):
- Summary of processed slices
- Confidence scores
- Any slices that need human attention
- Remaining unprocessed slices
- Suggested next steps

---

## DRY RUN

With `--dry-run`, show the execution plan without running anything:
```
Batch Plan — 8 slices

Execution order (respecting dependencies):
  1. slice-001  Employee Salary         [low]      no deps
  2. slice-002  Benefits Calculation    [medium]   after slice-001
  3. slice-005  Tax Withholding         [low]      no deps
  4. slice-003  Payroll Batch           [high]     after slice-001, slice-002
  ...

Estimated: 8 migration cycles
Blocked: 0 slices
Ready to start: 3 slices (no dependencies)
```

---

## RULES
- Never skip a failing slice. Investigate and resolve.
- Respect dependency order strictly.
- Stop the batch on the first failure that needs human review.
- Save progress after each slice so the batch can be resumed.
