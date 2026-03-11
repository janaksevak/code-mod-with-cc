You are manually triggering validation for a migration.

Arguments: $ARGUMENTS
(Options: --slice=<id>, --full, --score-only, or empty which validates the current slice)

---

## WHAT YOU DO

Run the validation pipeline outside the automatic hook flow. Useful for:
- Re-running validation after fixing issues
- Running with semantic diff rules
- Getting a confidence score without the full migration pipeline
- Validating specific test cases

---

## EXECUTION

### Determine scope
- `--slice=<id>` — Validate a specific slice
- `--full` — Validate all migrated slices
- `--score-only` — Just compute the confidence score from existing results
- Empty — Validate the most recently migrated slice

### Load context
Read `artifacts/slice-manifest.json` to find the slice details.
Read `modernization.config.json` for project configuration.

### Run validation

**Step 1: Semantic diff comparison**
```bash
python3 .modernization/scripts/validation/semantic_diff.py \
  --cobol-dir <golden-outputs-dir> \
  --java-dir <target-outputs-dir> \
  --rules artifacts/semantic-diff-rules.json \
  --output artifacts/validation-results.json
```

**Step 2: Confidence scoring**
```bash
python3 .modernization/scripts/validation/confidence_scorer.py \
  --results artifacts/validation-results.json \
  --quirks <program>-quirks.md \
  --config modernization.config.json \
  --output artifacts/confidence-score.json
```

### Present results

Show:
1. Test case results (pass/fail per case)
2. Semantic diff rules that were applied
3. Remaining differences (if any)
4. Confidence score breakdown
5. Gate decision

If any tests fail, show the byte-level diff for the first failure
so the engineer knows exactly what to fix.
