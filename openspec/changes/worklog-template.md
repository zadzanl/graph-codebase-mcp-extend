# worklog — [change-name]

> **Purpose:** Initial technical record and resume trace for agent handoffs. Worklogs are
> **NOT durable truth.** Promote durable decisions, current implemented truth, behavior
> contracts, and folder/tool usage rules to ADRs, `docs/tracking/current-truth.md`,
> `openspec/specs/**`, or nearest README files before the change is completed.
>
> Copy this template, fill it in, and delete this instruction block before committing.

---

## Latest resume state

> **Keep this block first and current.** Update the date and fields on every
> session that touches the change. Dates use day precision only (`YYYY-MM-DD`);
> do not include time-of-day or timezone precision.

**Updated:** YYYY-MM-DD
**Session status:** <!-- IN PROGRESS | BLOCKED | HANDOFF -->
**Change state:** <!-- proposal-ready | approved | in-progress | blocked | complete -->
**Implementation authorized:** <!-- yes | no — plus short qualifier if needed -->
**Active task:** <!-- `tasks.md` section or task ID currently being worked on -->

**Resume from:** <!-- Exact file, function, line, or command to resume from -->
**Next action:** <!-- One immediately actionable step for the next session -->
**Blockers:** <!-- Anything preventing progress; "None" if clear -->
**Last verification:** <!-- Command run, result, and outcome summary -->

## Technical trace

> **Compact tagged bullets.** Log only meaningful technical events: work that would
> save a future worker from rediscovering, rerunning, or re-deciding something.
> Skip filler prose, trivial keystrokes, and mechanical edits — summarize the atomic
> technical step instead.

**Supported tags:**

| Tag | Use when |
|-----|----------|
| `[discovery]` | Repo behavior, code path, or constraint discovered |
| `[edit]` | File, symbol, or data changed |
| `[test-fail]` | Test or validation command failed |
| `[test-pass]` | Test or validation command passed |
| `[benchmark]` | Performance or load measurement recorded |
| `[decision]` | Compromise or design choice made with trade-off |
| `[risk]` | New risk, regression risk, or edge case identified |
| `[promote]` | Durable truth moved to ADR, spec, current-truth, or README |
| `[obsolete]` | Stale content judged obsolete with short reason |

**Entries (newest first):**

- `[TAG] YYYY-MM-DD` <!-- meaningful event description -->
- `[TAG] YYYY-MM-DD` <!-- meaningful event description -->

---

## Acceptance Criteria Convention (for tasks.md)

When writing `tasks.md`, add explicit acceptance criteria as indented blockquote lines
immediately following the task checkbox line. The handoff brief generator will extract
these and embed them in the brief's task section.

Example:

```markdown
- [ ] 1.1 Add readiness gate / handoff status labels
  > Generator infers Handoff Status from worklog: no incomplete tasks → Closed, "implementation authorized: yes" → Ready, "planning-only"/"stub"/absent → Planning Only.
  > `--status` overrides inference. `--force` bypasses all safety gates.
  > `--change-level` on a completed change fails without `--force`.
```

If no acceptance criteria are provided, the generator falls back to generic criteria
with a single brief-level note. No per-task warnings are emitted.
