---
name: Foundational Operational Standards
description: Meta-principles for all work: synchronous subagents, full state verification, fail-fast debugging, ultradeep thinking
type: feedback
---

# Operational Standards

## Subagents (Synchronous Coordination)
- NEVER launch agents with interdependencies before predecessors complete — if Agent B needs Agent A's output, Agent A must finish and validate before B starts
- Verify subagents' work yourself — never trust responses without personal validation; reread results, check for accuracy
- Each subagent must report what memories it wrote — you must know where they documented learning so you can direct the next agent
- Coordinate via shared memories — many agents operate as one unified intelligence through shared memory state
- Read every document provided — no skimming; documents contain critical context

**Why:** Parallel execution of dependent tasks masks failures and creates debugging nightmares. Synchronous ordering with validation catches errors immediately.

## Code Standards
- No backwards compatibility — the system must work correctly after changes OR fail fast so errors are visible immediately
- Fail fast for debugging — don't mask errors, hide failures, or use workarounds; let systems break loudly so root causes surface quickly

**Why:** Silent failures and masked errors compound. System breakage reveals design flaws that need fixing, not hiding.

## Full State Verification (required after every logic change)
1. Source of Truth — identify where the final result lives (database row, file, state machine, memory, etc.)
2. Execute & Inspect — run the logic, then perform a separate independent read on the source of truth to confirm the change persisted
3. Edge Cases — simulate 3 boundary conditions: empty/null input, maximum limits, invalid formats; print system state before and after each
4. Evidence — produce a log or screenshot showing actual data in the system post-execution

**Why:** "It works on my machine" is not evidence. Verification prevents assumptions from becoming bugs in production.

## Manual Testing (required)
- Synthetic data with known inputs/outputs — not just "does it run," but "does it produce the right answer for X, Y, Z inputs?"
- Test happy path AND edge cases — success cases alone don't reveal brittleness
- Physically verify outputs exist where they should — if a trigger is supposed to cause outcome Y, go find Y (file exists, DB row updated, API returned data, etc.)
- On any error: stop → find root cause → fix it → update tests → retest

**Why:** Testing without verification is cargo cult debugging. You must see evidence that the system works as designed.
