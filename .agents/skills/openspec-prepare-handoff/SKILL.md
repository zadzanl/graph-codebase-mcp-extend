---
name: openspec-prepare-handoff
description: Prepare a self-contained handoff brief for async agents (cloud-hosted, local worktree, stale branch, or other isolated environment). Use when the user wants to hand off tasks from an OpenSpec change to a handed-off agent that will work independently.
license: MIT
compatibility: Requires Python 3.8+ (no openspec CLI required).
metadata:
  author: rebel-robot-game
  version: "2.0"
---

Prepare a self-contained handoff brief for async handed-off agents.

**Input**: Optionally specify a change name and/or task IDs. If omitted, prompt the user.

---

## Steps

### 1. Select the change

If a change name is provided, use it. Otherwise:
- Infer from conversation context if the user mentioned a change
- Auto-select if only one active change exists
- If ambiguous, list available changes from `openspec/changes/` (exclude `archive/` and `worklog-template.md`) and ask the user to select

Announce: "Preparing handoff for change: **<name>**"

### 2. Read the change context

Read these files from the change directory:
- `proposal.md`
- `design.md`
- `tasks.md`
- `worklog.md`
- Any specs in `specs/*/spec.md`

Summarize the change state to the user: what's done, what's pending, what's blocked. Note whether the worklog has an implementation authorization marker and whether the change is ready for handoff.

### 3. Check readiness and status

The generator infers a `Handoff Status` from the worklog:
- No incomplete tasks → **Closed** (generator will refuse change-level unless `--force`)
- Worklog says "implementation authorized: yes" → **Ready**
- Worklog says "planning-only" or "stub" → **Planning Only**
- Worklog exists but has no implementation marker → **Planning Only**
- No worklog exists → **Draft**

If the inferred status is not Ready, warn the user. The user can override with `--status Ready` or bypass all gates with `--force`. Recommend adding explicit acceptance criteria to `tasks.md` (lines under tasks starting with `  > `) before generating a Ready brief.

### 4. Select handoff scope

**Ask the user**: Change-level (entire change) or task-level (specific tasks)?

- **Change-level**: All incomplete tasks become one brief. Fails if no incomplete tasks remain (use `--force` to override).
- **Task-level**: Present the task list from `tasks.md`. Ask the user which tasks to include. Support comma-separated task IDs (e.g., `1.1,1.2,2.1`).

Also ask: "Do you have any session-specific context to include? (e.g., partial progress, known issues, files already modified)" If yes, capture this text.

### 5. Generate the handoff brief

Run the generation script:
```bash
python tools/generate_handoff_brief.py --change "<name>" [options]
```

Options:
- `--tasks 1.1,1.2,2.1` for task-level handoff
- `--change-level` for change-level handoff
- `--extra-context "text"` for session-specific context (wrap in quotes)
- `--status Ready` to override inferred status
- `--force` to bypass all safety gates (readiness, completed-change, duplicate assignment)

If the script fails, fall back to generating the brief manually by assembling the sections from the files you already read.

### 6. Review and present

Read the generated brief back. Check that:
- The Handoff Status in the header is correct.
- The `## Reconciliation Rule` is present and instructs the agent to trust their local state.
- The `## Before You Start` section includes pre-work acknowledgement instructions.
- The `## When You're Done` section includes the verification matrix and task completion evidence guidance.
- The `## Handoff Lifecycle` block shows `Lifecycle status: OPEN`.
- Any `⚠️ Extraction Warning` blocks are noted.

Present a summary to the user:
- Brief file path
- Handoff Status
- Number of tasks included
- Suggested branch name
- Key constraints
- Any extraction warnings

The handed-off agent should send a pre-work acknowledgement before making substantive edits. This is especially important for isolated environments (local worktrees, stale branches, remote checkouts) where drift between the brief snapshot and local state is likely.

Ask: "Does this brief look correct? Ready to commit/share?"

### 7. Share the brief

Once approved, share the brief through the agreed channel:
```bash
git add openspec/changes/<name>/handoff/
git commit -m "handoff: prepare brief for <name>"
```

Remind the user to make the brief available to the handed-off agent (push, copy, share branch, etc.).

### 8. Closeout (after handoff completion)

After the handed-off agent delivers output and the local orchestrator accepts it:
- Mark the brief's `## Handoff Lifecycle` block to `Lifecycle status: CLOSED`.
- If a newer brief supersedes this one, mark it `Lifecycle status: SUPERSEDED` instead.
- Update `tasks.md` checkboxes based on the task completion evidence (only the local orchestrator modifies `tasks.md`).
- Update the change worklog with the acceptance event.

---

## Brief Format Reference

The generated brief contains these sections:
1. **Header** — brief ID, source change, timestamp, handoff status, mode, suggested branch, snapshot note
2. **Repo Context** — condensed stack, truth precedence, safety rules, test command, current baseline; includes `⚠️ Extraction Warning` if any extraction used a fallback
3. **Current State** — what's done, what exists, what's blocked
4. **Assigned Tasks** — specific tasks with acceptance criteria (explicit when available in `tasks.md`, generic otherwise with a brief-level note)
5. **Relevant Files** — paths to read with descriptions
6. **Reconciliation Rule** — instructions for reconciling the brief snapshot against local repo state
7. **Before You Start** — pre-work acknowledgement loop instructions
8. **When You're Done** — scope, tests, worklog update, task completion evidence, verification matrix table
9. **Constraints** — scope boundaries, style rules
10. **Handoff Lifecycle** — lifecycle status (OPEN, CLOSED, SUPERSEDED) and assigned task IDs
