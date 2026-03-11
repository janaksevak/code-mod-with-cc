You are claiming a migration slice for the current engineer.

Arguments: $ARGUMENTS
(Required: slice ID, e.g., "slice-001". Optional: --release to unclaim.)

---

## WHAT YOU DO

Update the slice manifest to mark a slice as claimed by the current engineer.
This prevents conflicting work and establishes ownership.

---

## EXECUTION

### Parse arguments
Extract the slice ID from $ARGUMENTS. Check for --release flag.

### Load manifest
Read `artifacts/slice-manifest.json`. If missing, tell the user to run
`/query-slices` first.

### Validate the claim

**For claiming:**
1. Check the slice exists
2. Check status is "available" — if not, show who claimed it and when
3. Check dependencies: warn (but don't block) if upstream slices are unclaimed
4. Update the slice:
   ```json
   {
     "status": "claimed",
     "claimed_by": "<user>",
     "claimed_at": "<ISO timestamp>"
   }
   ```

**For releasing (--release):**
1. Check the slice exists
2. Check it's currently claimed
3. Reset to available:
   ```json
   {
     "status": "available",
     "claimed_by": null,
     "claimed_at": null
   }
   ```

### Save the manifest
Write the updated manifest back to `artifacts/slice-manifest.json`.

### Confirm

After claiming, show:
- Slice details (programs, copybooks, dependencies)
- Recommended next step: `/migrate <slice-id>`
- Any warnings about unclaimed dependencies

After releasing, show:
- Confirmation of release
- Current available slices count

---

## CONFLICT DETECTION

If two engineers try to claim the same slice, the manifest file is the
source of truth. Since Claude Code sessions are single-user, conflicts
only arise if two engineers edit the same manifest file. Warn the user
to coordinate with their team.

For future iteration: use a lock file or database for multi-user coordination.

---

## DEPENDENCY WARNINGS

If a claimed slice depends on unclaimed slices, show:
```
WARNING: slice-003 depends on:
  - slice-001 (available — not yet claimed)
  - slice-002 (claimed by alice — in progress)

You can start documentation and analysis, but migration validation
will require slice-001 and slice-002 to be completed first.
```
