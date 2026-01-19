# Codex Agent Instructions

Use this guide when working inside the Codex CLI for the `sonic-mgmt/spytest` workspace.

## Session Commands
- `/init` – initialize a new session; creates this `AGENTS.md` with Codex usage notes.
- `/status` – print the current Codex session configuration (sandbox, approvals, model, etc.).
- `/approvals` – adjust which actions Codex may perform without user approval.
- `/model` – select the model variant and reasoning effort for the session.
- `/review` – review the current workspace changes and highlight potential issues.

## Operating Guidelines
1. Respect the active sandbox and approval policy shown by `/status`.
2. Prefer non-destructive commands; never rollback user changes without explicit instruction.
3. Use `rg` for code or text searches; run shell commands via `bash -lc` with `workdir` set.
4. Default to ASCII when editing files and keep comments succinct and purposeful.
5. Summarize work clearly, referencing files with clickable paths (e.g., `src/app.ts:42`).
6. Suggest next steps only when they are natural follow-ups (tests, commits, etc.).
7. Ask for user guidance when requirements are ambiguous or when elevated permissions are needed.

## Validation Checklist
- Rerun relevant tests after modifications, or state explicitly if tests were not run.
- Inspect diffs for unintended changes before finishing a task.
- When reviewing, prioritize functional and regression risks, then report gaps in tests.
