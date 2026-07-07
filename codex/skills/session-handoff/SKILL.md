---
name: session-handoff
description: Use when the user asks to wrap up, remember progress, create a handoff, resume later, update current status, or record what happened in this Codex session. Produces a concise project-local handoff with goal, completed work, verification status, blockers, and next steps.
---

# Session Handoff

## Purpose

Create a concise handoff artifact that lets a future Codex or Claude session resume without replaying the whole conversation.

This skill complements Codex Memories. Memories are generated local recall; this handoff is an explicit, reviewable project artifact for current work state.

## Default Output

Prefer this order:

1. If the user gives a path, write there.
2. If inside a project/repo, write `.codex/HANDOFF.md` at the project root.
3. If the repo already has `.remember/`, also update `.remember/now.md` only when the user explicitly wants Claude/remember compatibility.
4. If writing is blocked, return the handoff in chat and say it was not written.

Do not write secrets, tokens, private credentials, or raw tool logs.

## Workflow

1. Identify the active project root and the user’s current goal.
2. Summarize only durable state, not the full transcript.
3. Separate verified facts from guesses.
4. Include exact file paths and commands only when they are useful for resuming.
5. If tests or checks were run, record the command and result. If not, mark verification as not run.
6. Keep the handoff short enough to scan in under one minute.

## Template

```markdown
# Handoff

Updated: YYYY-MM-DD HH:MM TZ
Project: /absolute/project/path

## Goal

- <current objective in one or two bullets>

## Completed

- <durable completed work, with file paths when relevant>

## Verification

- Status: verified | partially verified | not verified
- Evidence: <commands/results, CI links, or read-back summary>

## Current State

- <important decisions, constraints, or state a future session must preserve>

## Next Steps

- <ordered next actions>

## Blockers / Risks

- <known blockers, uncertainties, or permissions needed>
```

## Quality Bar

- Use absolute paths for files outside the current repo; repo-relative paths are fine inside the handoff when the project root is stated.
- Never say “done” unless verification evidence exists.
- Keep raw logs out; quote only the key line if needed.
- If the handoff updates an existing file, preserve still-relevant prior state and remove stale completed items.
