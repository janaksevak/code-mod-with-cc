You are running a structured elicitation session with the human.

Arguments: $ARGUMENTS
(Required: session name — one of: orientation, behavioral-contracts, seam-mapping, target-state, constraints, synthesis)

---

## PURPOSE

The codemap sees structure. You need to see meaning. These interviews
extract what static analysis cannot: business context, institutional
knowledge, political constraints, and known failure modes.

Each session has a specific focus. Run them in order. Each builds on
the previous. Responses are saved to `artifacts/interview.json`.

---

## BEFORE YOU START

1. Read `artifacts/interview.json` if it exists (prior session data)
2. Read `artifacts/codemap.json` if it exists (codemap findings)
3. Adapt your questions based on what you already know

---

## SESSION DEFINITIONS

### orientation
**Goal**: Understand what this system is and why it matters.
Ask these questions (adapt based on codemap findings):

1. "What does this system do in plain language? Who uses it?"
2. "How old is this codebase? What's its history?"
3. "What are the most critical business processes it supports?"
4. "What happens if this system goes down for an hour? A day?"
5. "Who knows this system best? Are they available?"
6. "Has anyone attempted modernization before? What happened?"
7. "What's driving this modernization effort now?"

### behavioral-contracts
**Goal**: Document how the system is *supposed* to behave.

1. "Walk me through the main processing flow — what goes in, what comes out?"
2. "What are the critical calculations or business rules?"
3. "Are there any implicit rules that aren't in the code? (regulatory, business conventions)"
4. "What edge cases cause problems? What inputs break things?"
5. "Are there batch vs online processing differences?"
6. "What does 'correct output' look like? How is it verified today?"
7. "Are there any known bugs that people work around instead of fixing?"

### seam-mapping
**Goal**: Identify natural boundaries for slicing.

1. "Looking at [codemap findings], do these groupings match how your team thinks about the system?"
2. "Which parts of the system talk to each other most?"
3. "Are there parts that could run independently if disconnected?"
4. "Where are the data boundaries? (Different databases, file systems, message queues)"
5. "Which interfaces are stable vs frequently changing?"
6. "Are there any shared components that everything depends on?"
7. "If you had to split this system in half, where would you cut?"

### target-state
**Goal**: Define what success looks like.

1. "What language/platform is the target?"
2. "Should the migrated code be a 1:1 translation or a re-architecture?"
3. "What level of output fidelity is required? (byte-for-byte, functional equivalence, behavioral equivalence)"
4. "What new capabilities should the modernized system have?"
5. "What current capabilities can be dropped?"
6. "Are there deployment constraints? (cloud, on-prem, hybrid)"
7. "What does the testing strategy look like post-migration?"

### constraints
**Goal**: Identify non-negotiables.

1. "What's the timeline? Any hard deadlines?"
2. "Are there compliance/regulatory requirements affecting the migration?"
3. "What's the team composition? How many engineers, what skills?"
4. "Is there a parallel-run requirement? (old and new running simultaneously)"
5. "What's the rollback strategy if something goes wrong?"
6. "Are there budget constraints on tooling or infrastructure?"
7. "What organizational approvals are needed?"

### synthesis
**Goal**: Confirm understanding, resolve contradictions, fill gaps.

Review all prior sessions and:
1. Present a summary of your understanding
2. Highlight any contradictions between sessions
3. Ask: "What did I miss? What did I get wrong?"
4. Ask: "What keeps you up at night about this migration?"
5. Ask: "If you could guarantee one thing about the outcome, what would it be?"
6. Confirm the priority order for migration slices
7. Agree on the confidence threshold for auto-approval

---

## HOW TO CONDUCT THE SESSION

- Ask ONE question at a time. Wait for the answer.
- Listen for implicit information. If they mention something important in passing, follow up.
- Don't lead the witness. Ask open questions first, then drill down.
- If they say "it depends," find out what it depends on.
- If they say "I don't know," ask who would know.
- Keep the session focused. If it veers off topic, gently redirect.
- Summarize what you heard at the end. Ask if you got it right.

---

## SAVING RESULTS

After each session, update `artifacts/interview.json`:
```json
{
  "sessions": {
    "<session-name>": {
      "conducted_at": "ISO timestamp",
      "questions_asked": [...],
      "responses": [...],
      "key_findings": [...],
      "open_questions": [...],
      "action_items": [...]
    }
  },
  "cumulative_findings": {
    "business_context": "...",
    "critical_processes": [...],
    "known_risks": [...],
    "constraints": [...],
    "target_state": {...}
  }
}
```

Create the file if it doesn't exist. Merge into it if it does.
The cumulative_findings section should be updated after each session
to reflect everything learned so far.
