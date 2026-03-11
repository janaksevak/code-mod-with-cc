You are orchestrating the migration of a single claimed slice.

Arguments: $ARGUMENTS
(Required: slice ID, e.g., "slice-001")

---

## PREREQUISITES

1. Slice must be claimed (run `/claim-slice` first)
2. `artifacts/slice-manifest.json` must exist
3. `artifacts/codemap.json` should exist (for context)
4. `artifacts/interview.json` should exist (for behavioral contracts)

---

## MIGRATION PIPELINE

### Step 0: Load context
- Read the slice from the manifest
- Read the codemap and interview artifacts
- Update slice status to "migrating"

### Step 1: Document the source code
Delegate to the **cobol-documenter** subagent (or appropriate language documenter).
Pass it the program files listed in the slice.

Wait for `<program>-analysis.md` to be produced. Read it.

### Step 2: Generate golden test dataset
Delegate to the **golden-dataset-builder** subagent.
It will:
- Generate synthetic test inputs covering all code paths
- Compile and run the source program against all inputs
- Capture outputs as the golden (reference) dataset
- Document quirks discovered during execution

Wait for the golden dataset to be complete and validated.
Read `<program>-quirks.md`. This is the behavioral spec.

### Step 3: Set up validation harness
Confirm the validation scripts are in place:
```bash
ls .modernization/scripts/validation/confidence_scorer.py
ls .modernization/scripts/validation/semantic_diff.py
```

If semantic diff rules exist at `artifacts/semantic-diff-rules.json`,
validate them:
```bash
python3 .modernization/scripts/validation/semantic_diff.py \
  --rules artifacts/semantic-diff-rules.json --validate-rules
```

### Step 4: Write the target code
This is where the actual migration happens. Based on:
- The analysis document (Step 1)
- The quirks document (Step 2)
- The interview artifacts (behavioral contracts, target state)
- The modernization config (`modernization.config.json`)

Write the target language implementation. Follow the rules in the
project's CLAUDE.md for code structure, naming conventions, and
architecture patterns.

The PostToolUse hook will automatically trigger validation after
each source file is written.

### Step 5: Build and validate
After all target files are written:
```bash
# Build (language-specific — check modernization.config.json)
# Example for Java:
cd <project-dir>/java && mvn clean package -q

# Run full validation
python3 .modernization/scripts/validation/semantic_diff.py \
  --cobol-dir <golden-outputs> \
  --java-dir <target-outputs> \
  --rules artifacts/semantic-diff-rules.json \
  --output artifacts/validation-results.json
```

### Step 6: Score confidence
```bash
python3 .modernization/scripts/validation/confidence_scorer.py \
  --results artifacts/validation-results.json \
  --quirks <program>-quirks.md \
  --config modernization.config.json \
  --output artifacts/confidence-score.json
```

Read the score output. Present it to the user.

### Step 7: Gate decision
Based on the confidence score:

**Score >= 95 (auto-approve eligible):**
- Present the score and test results
- Ask: "Confidence is high. Ready to commit?"
- If yes → proceed to commit

**Score 80-94 (human review recommended):**
- Present the score, test results, AND the diff
- Highlight which test cases are failing or marginal
- Ask: "Review recommended. Would you like to approve, request changes, or investigate further?"

**Score < 80 (human review required):**
- STOP. Do not proceed.
- Present the score with full failure details
- Suggest: "Consider running `/elicit` to understand what's different"
- Suggest: "Check if semantic diff rules need updating"
- Update slice status to "review_required"

### Step 8: Update manifest
Update the slice status in `artifacts/slice-manifest.json`:
- If approved: status → "approved", confidence_score → <score>
- If needs work: status → "migrating" (keep working)
- If blocked: status → "review_required"

---

## RULES
- Never skip the documentation stage. Understanding before coding.
- Never skip the golden dataset. Tests before code.
- Replicate quirks exactly. Match the source behavior, don't "fix" it.
- If validation fails, read the failure output carefully. Fix the root cause.
- Do not brute-force. If something fails 3 times, step back and investigate.
