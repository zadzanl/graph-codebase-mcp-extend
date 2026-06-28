---
name: opsx-handoff
description: Prepare a self-contained handoff brief for async cloud agents from an OpenSpec change.
---

Prepare a handoff brief for an OpenSpec change so that a cloud-based async agent (Jules, Copilot Cloud, Claude web, etc.) can pick up tasks independently.

Use the **openspec-prepare-handoff** skill to guide the workflow:
1. Select which change to hand off
2. Choose task-level or change-level scope
3. Add session context if needed
4. Generate the self-contained brief
5. Review and commit

If no change name is provided in the prompt, list available active changes from `openspec/changes/` (exclude `archive/` and `worklog-template.md`) and ask the user to select one.
