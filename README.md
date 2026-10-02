# agents-guideline — a long-lived working system for AI coding agents

English | [繁體中文](README.zh-TW.md)

> **Language note (English README only).** The rules, skills, agent definitions and docs in this repo are written in Traditional Chinese (Taiwan usage). If you read English, ask your own AI agent to translate them into an English copy before you adopt them, and have it keep file names, paths and quoted section-title citations (written with 「」 in the originals) verbatim, or the cross-file references will break. This README is self-contained: the core concepts below cover the system's design, so you can follow it without reading Chinese.

## Core concepts

### Positioning

A working system that takes effect once installed into `~/.claude/` or `~/.codex/`: model-dispatch rules, judgment criteria, acceptance rubrics, an acceptance agent, and a maintenance protocol. Goal: let different coding agents produce verifiable work at a steady quality in this environment.

### Design background and writing principles

Background: built in one pass on 2026-07-06 by a top-tier model (Fable 5) for all later sessions to reuse. The structure borrows from `goad-dot-claude`. Machine differences are isolated in `hosts/<key>.md` (each machine installs only its own file; a macOS main machine plus a Windows desktop, and a new machine is probed and given a file by an AI; the `<REPO>` mapping table is in `rules/05-hosts.md`).

Writing principles (revised 2026-07-25 per [the context-engineering guide for Claude 5 generation models](https://claude.com/blog/the-new-rules-of-context-engineering-for-claude-5-generation-models)): **write this environment's gotchas and authorization boundaries, not generic ways of working.** Judgment the model already has is not written as a decision tree; self-documenting interfaces (agent definitions) get no fill-in-the-blank examples; each rule keeps exactly one canonical location; only content needed at the start of every job goes into the always-loaded `rules/`. The principle is "fewer rules means a stronger model", not "more rules means safer".

### Always-loaded vs read-on-demand

⚠️ **`~/.claude/rules/` is an unconditionally always-loaded area**: Claude Code loads every `*.md` there that has no `paths` frontmatter in full at the start of each session, a fixed context cost paid by every session. So only content needed at the start of every job goes in `rules/`; long content used only in specific situations goes in `skills/` (maintenance protocol), `rubrics/` (acceptance criteria) or `docs/` (archives and situational reference), and those three directories are **not auto-loaded**.

### Three iron laws

1. **No completion claim without evidence** (test output / CI link / read-back result). Every report is graded: verified (with evidence) / pending CI / unverified.
2. **Outbound or irreversible actions need explicit authorization in this session**: sending messages or email, merging a PR, pushing a shared branch, publishing, deleting or overwriting files you did not create. When already authorized explicitly in this session, act without asking again. Authorization is valid per occasion and per target and must not be generalized into standing policy.
3. **No self-verification**: acceptance goes to a fresh-context acceptance agent, never to an agent that inherited the producer's context. Details: Claude `rules/10-dispatch.md` §5「驗證不自驗」; Codex `codex/rules/10-dispatch-codex.md` §6「驗證語意」.

### Known degradation modes and prevention (maintainers must read)

1. **Ritual death**: templates are copied but acceptance criteria become empty words → test: could another agent decide pass or fail from that sentence alone; a verifier FAILs vague criteria on sight
2. **Bloat death**: every pitfall gets stuffed into the rules → lessons go only into `rules/50-lessons.md`; promoting one to an official criterion follows the `maintain-guideline` skill's process; line/byte thresholds trigger slimming; once promoted, move the lesson into `docs/lessons-archive.md` so the same thing never takes two places in the always-loaded area
3. **Always-loaded-area bloat death**: long content used only in specific situations is put in `rules/` → every session pays a fixed cost. Test: is this content needed at the start of every job? If not, put it in `skills/`／`rubrics/`／`docs/`
4. **Over-specification death**: decision trees hard-coded for judgments the model already makes, fill-in-the-blank examples attached to self-documenting interfaces → rules conflict and the model burns extra reasoning. The sunset clause (`maintain-guideline` skill §5) is the cure: is a rule about "a gotcha of this environment" or "a generic way of working"? Delete the latter
5. **Staleness death**: model names or tool parameters change and the docs don't follow, so the whole system loses credibility → facts carry a verification date, are re-checked after 90 days, and a rotten one is fixed as it is found
6. **Broken-link death**: a file is renamed and routing points to a path that no longer exists → `rg` for references before renaming; a broken link is P0
7. **Bypass death**: "this task is simple, no need to follow the rules" → simple tasks are exactly where context blow-up starts; if a rule seems unreasonable, raise it through the process, never bypass it silently

### Honesty clause: what this system cannot fix

Decomposition, templates and fresh-context acceptance raise **execution quality**; they cannot fix **taste and ambiguous questions** (long-term architecture trade-offs, copy tone, whether a feature should exist). When you hit one, in order: follow the repo's existing conventions → use the strongest available model → produce several candidates for the user to choose from → state plainly that "this is beyond what the system can guarantee".

## Installation

Full steps (including post-install verification and caveats) are in [`docs/install.md`](docs/install.md). Pick by platform and privilege:

- **Claude Code, macOS/Linux**: Claude Code on macOS/Linux; symlink install, the repo is the single source of truth and edits take effect immediately.
- **Codex, macOS/Linux**: Codex on macOS/Linux; `AGENTS.md` and skills are symlinks, agent TOML files are written as regular files by a sync script.
- **Windows (PowerShell)**: Windows; run in an administrator PowerShell, which installs both Claude Code and Codex.
- **Regular-file sync**: machines that cannot elevate; `scripts/sync-profile.py` writes regular-file copies, and the sync must be re-run after every repo change.

For a new machine (no file for it in `hosts/`), probe it and create its file by following 「新機器建檔」 in [`docs/new-host.md`](docs/new-host.md). `docs/install.md`, `docs/new-host.md` and `docs/repo-layout.md` exist in Chinese only, since agents and rules cite them.

## Directory map

Per-file purposes are in 「檔案結構」 of [`docs/repo-layout.md`](docs/repo-layout.md).

| Path | Purpose |
|------|---------|
| `CLAUDE.md`, `AGENTS.md` | Global entry points (one each for Claude Code and Codex): routing and iron laws only |
| `rules/` | **Auto-loaded every session (always-loaded)**: only rules needed at the start of every job |
| `hosts/` | Per-machine facts `hosts/<key>.md`; imported via the global `CLAUDE.md`, also always-loaded, each machine installs only its own file |
| `skills/`, `rubrics/`, `docs/` | **Read on demand, not auto-loaded**: maintenance protocol and shared skills, acceptance criteria, situational reference |
| `agents/` | Claude Code agent definitions: `worker`, `worker-opus`, `verifier` |
| `codex/` | Codex-specific: dispatch rules and delegation templates, agent TOML, skills |
| `scripts/`, `tests/` | Install sync scripts, the sunset-review measurement script, and tests |
