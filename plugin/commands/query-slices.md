You are querying the slice manifest to show available migration work.

Arguments: $ARGUMENTS
(Options: --all, --available, --mine, --status=<status>, --id=<slice-id>, or empty which shows available slices)

---

## WHAT YOU DO

Read `artifacts/slice-manifest.json` and present the slices in a clear,
actionable format. Engineers use this to decide what to work on next.

---

## EXECUTION

### Load the manifest
Read `artifacts/slice-manifest.json`. If it doesn't exist, tell the user
to run `/codemap --deep` and then `/modernize` to generate slices.

### Parse arguments
- `--all` — Show all slices regardless of status
- `--available` — Show only unclaimed slices (default)
- `--mine` — Show slices claimed by the current user
- `--status=<status>` — Filter by status (available, claimed, migrating, validating, approved, merged)
- `--id=<slice-id>` — Show detailed view of a specific slice

### Display

#### Summary view (default)
```
Migration Slices — 12 total
  Available: 8 | Claimed: 2 | Migrating: 1 | Approved: 1 | Merged: 0

  ID         Name                    Complexity  Programs  Dependencies  Status
  ─────────  ──────────────────────  ──────────  ────────  ────────────  ─────────
  slice-001  Employee Salary         low         1         0             available
  slice-002  Benefits Calculation    medium      2         slice-001     claimed (alice)
  slice-003  Payroll Batch           high        4         slice-001,002 available
  ...
```

#### Detail view (--id=slice-xxx)
```
Slice: slice-001 — Employee Salary Processing
Status: available
Complexity: low
Priority: 1

Programs:
  - empsal/cobol/EMPSAL.CBL

Copybooks:
  - EMPSAL-RECORD.CPY

Data Files:
  - empsal/test_data/*.dat

Dependencies (must be migrated first):
  (none)

Depended on by:
  - slice-002 (Benefits Calculation)
  - slice-003 (Payroll Batch)

Notes:
  Standalone program with no upstream dependencies.
  Good candidate for first migration.

To claim: /claim-slice slice-001
```

---

## RECOMMENDATIONS

After showing the slices, offer guidance:
1. Highlight slices with no dependencies (good starting points)
2. Flag slices with many dependents (high-value targets)
3. Warn about slices blocked by unclaimed dependencies
4. Suggest a migration order based on the dependency graph
