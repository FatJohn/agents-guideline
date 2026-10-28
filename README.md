# agents-guideline — a long-lived working system for AI coding agents

Readers: people and AI agents who adopt, install or maintain this system.

Type: entry point (README).

English | [繁體中文](README.zh-TW.md)

> **Language note (English README only).** The rules, skills, agent definitions and docs in this repo are written in Traditional Chinese (Taiwan usage). To read them in English, have your own AI agent translate them into a copy, keeping file names, paths and quoted 「」 section titles verbatim, or cross-file references break. This README is self-contained, so you can follow the design without reading Chinese.

## What this is

A working system that takes effect once installed into `~/.claude/` or `~/.codex/`. Claude Code and Codex each get one minimal global entry point: six boundaries plus a routing table.

Everything else is split into skills, agent contracts and rubrics, loaded only when needed. The goal is steady, verifiable work from different coding agents.

## Design concepts

Keep always-loaded content minimal, and leave "who may claim done" to independent acceptance.

### Layers and load timing

Always-loaded content holds only what every job needs; everything else loads on demand.

| Layer | Installed at | When loaded | Read by |
|---|---|---|---|
| Global entry point | `~/.claude/CLAUDE.md`, `~/.codex/AGENTS.md` | Always, every session | The platform's agents |
| `judgment.md` | `~/.claude/rules/` | Claude: always, in full; Codex: via the route table | Claude agents (subagents pay too); Codex on demand |
| Host facts | `~/.claude/host-facts.md` | Always; one file per machine | The platform's agents |
| Controller route card | `~/.claude/route-card.md` | Main conversation only, via SessionStart hook | Main conversation (controller) |
| Skills | `~/.claude/skills/`, `~/.agents/skills/` | Only when a description matches | Agents whose task matches |
| Agent contracts | `~/.claude/agents/`, `~/.codex/agents/` | On delegation, into the subagent context | The delegated subagent |
| Rubrics | `~/.claude/rubrics/` | Never auto-loaded | Verifier contracts; Codex `reviewer` too |
| `docs/` | In the repo, not installed | Never auto-loaded | Maintainers and agents, on demand |

`~/.claude/rules/` is an unconditionally always-loaded area: every file there loads in full each session, so only `judgment.md` is installed.

The route card stays out of that area, and subagents do not inherit it.

### Role model: controller and verifier

The main conversation is the controller: it plans, implements, checks and reports, and does all of that itself. Subagents exist for three uses only: fresh-context acceptance, fresh code review, and side research. Parallel work is done by several top-level sessions, each in its own worktree, not by implementer subagents (v4, 2026-10-29; the measurements behind it are in `docs/reviews/v4-2026-10.md`).

- Controller (main conversation): starts in its own worktree, implements and fixes itself; shows the user the diff and gets per-occasion authorization before touching CI or release config.
- `verifier`: fresh context, judges only, never produces.
- Independent issues get one top-level session each (`worktree-session` skill); the current session only inventories.

Delegation table (abridged from `global/claude/route-card.md`):

| Task | Delegate to |
|---|---|
| Acceptance | `verifier`, `model: opus`; always for any document before merge or ready, code by dispatch skill §1 tiers, still applies when project rules name only code-review |
| Fresh review of a code diff | Fresh subagent running `code-review` skill, never the main conversation itself; adds to `verifier`, never replaces it; after fixing findings, re-verify per dispatch skill §2 |
| Side research | Answer is in the files (which files have X, lists, numbers): `Explore`, `model: haiku`. Reading several long documents, cross-source comparison, conclusions that need reasoning: `general-purpose`, `model: sonnet`. Second opinion: `codex:codex-rescue` |
| Implementation, fixes, docs, planning | Not delegated: the controller does them |

### Model per seat

Each seat sets its model in one place; cheap defaults go to the high-volume seats and expensive capability is switched on per task. The main conversation takes `settings.json` `model`/`effortLevel` (a cheap default such as sonnet/high suits a controller that mostly inventories, launches issue sessions and reports; switch with `/model` for a single heavy task instead of editing settings). Issue sessions are pinned to opus/medium by the `--model`/`--effort` flags that the `require-issue-session-model.sh` hook enforces. `verifier` takes its frontmatter; `Explore`/`general-purpose` take the route card. Where each is set and what breaks without it: 「每個座位的 model 在哪設、怎麼選」 in [`docs/design/mechanism.md`](docs/design/mechanism.md).

### Six boundaries

Both entry points share one set of six boundaries, mapped one-to-one in 「邊界」 of `global/claude/CLAUDE.md` and `global/codex/AGENTS.md`.

1. The project spec outranks the global entry point.
2. No completion claim without evidence; reports use three grades, defined in the next section.
3. Outbound or irreversible actions (sending messages or email, merging, pushing a shared branch, publishing, deleting or overwriting files you did not create) need authorization in this session, valid per occasion and per target.
4. No self-verification: acceptance goes to a fresh-context `verifier`; Codex sends high-risk acceptance to `sol_verifier`.
5. One writer per working tree at a time.
6. An interruptible long task leaves a resumable context; the format is in the `handoff` skill.

### Evidence and convergence of acceptance

A completion claim carries rerunnable evidence, and the verifier's four statuses decide when acceptance stops.

Reports use three grades: verified, pending CI and unverified. Verified needs a rerunnable command and its output.

Before marking something unverified, confirm that no tool can verify it (`global/shared/rules/judgment.md`, 「完成的三個條件」).

The verifier reports a status on its first line, highest priority first (`global/shared/rules/judgment.md`, 「驗收的停止端」):

| Status | Meaning |
|---|---|
| `INCONCLUSIVE` | UNSURE or undecided condition; get evidence first |
| `OPEN` | No missing evidence; a behavioral artifact has a FAIL |
| `PROSE-ONLY` | Only non-behavioral FAILs; stop after read-back |
| `CONVERGED` | All required conditions PASS; stop acceptance |

Irreversible side effects split into two sides that choose the acceptance path (`judgment.md`, 「不可逆副作用的定義」):

- General side: normal-flow operations the system can rebuild or resend, such as writing backend state, clearing a local cache or requesting notification permission; ordinary acceptance.
- High-risk side: decision-level work (architecture, security design, permission model) and effects that cannot be rebuilt or resent, such as deleting user data, charging money or sending email; it wins when both sides apply.

### Four handoff cards

Handoffs use four fixed-field cards, so the receiver never rereads the conversation. The fields are in `global/shared/skills/handoff/SKILL.md`.

| Card | Direction | Purpose |
|---|---|---|
| Brief card | controller → subagent | Goal, scope, acceptance criteria, report format |
| Report card | subagent → controller | Changes, status, verification output, grade |
| Verdict card | verifier → controller | Status first, then per-criterion verdicts |
| Session handoff card | session → the next session or agent | Position, done, to check, next steps, risks |

### Principles for writing rules

Rules cover this environment's gotchas and authorization boundaries, not generic ways of working.

- Judgment the model already has is not written as a decision tree; self-documenting interfaces (agent definitions) get no fill-in-the-blank examples.
- Each rule keeps exactly one canonical location.
- Only content needed at the start of every job stays always-loaded.
- A lesson goes into `docs/lessons.md` first and is promoted to an official criterion only through the `maintain-guideline` process.

The principle is "fewer rules means a stronger model", not "more rules means safer".

### Same shape on both platforms

The Claude and Codex entry points carry the same boundaries and routing table; only platform wording differs.

- `global/shared/`: shared skills, rubrics, rules and hosts; one edit takes effect on both sides.
- `global/claude/`, `global/codex/`: platform-only content; Claude has hooks and the route card, Codex has dispatch rules and prompt templates, and both have agent definitions.
- Deliberately split roles are written separately: Claude's `verifier` also covers high-risk acceptance, while Codex sends it to `sol_verifier`.
- The mapping matrix is in 「兩平台同步矩陣」 of `.claude/skills/maintain-guideline/SKILL.md`.

## Skills

Shared skills come from `global/shared/skills/` and install into `~/.claude/skills/` and `~/.agents/skills/`. Two more are repo-only and load only when you work in this repo.

| Name | Triggers when | Installed at |
|---|---|---|
| `dispatch` | Acceptance, fresh review, side research, post-review fixes, changing course when stuck | Both platforms |
| `handoff` | Writing briefs, reports, verdicts; wrap-up, compact | Both platforms |
| `git-commit` | Writing a commit message or squash-merge title | Both platforms |
| `create-pr` | Opening a Pull Request from a branch | Both platforms |
| `worktree-session` | Starting work in a worktree, one session per independent issue, cleaning worktrees | Both platforms |
| `writing-principles` | Writing, editing or reviewing READMEs, guides, design docs | Both platforms |
| `maintain-guideline` | Changing this system itself (`global/**`, entry points) | repo-only |
| `usage-review` | Measuring Claude Code usage and dispatch behavior | repo-only |

## Agents

Claude defines only `verifier`; Codex keeps its own role set. Each definition file pins model and effort.

### Claude Code

`Explore`, `Plan` and `general-purpose` are built into Claude Code; the route card assigns their uses.

| Name | Role | model | effort | tools |
|---|---|---|---|---|
| `verifier` | Fresh-context acceptance: PASS/FAIL/UNSURE per criterion | `opus` | `medium` | Read, Bash, Glob, Grep, LSP |

### Codex

Codex uses three tiers, Luna, Terra and Sol, from low to high. All five roles are read-only or probe-only; implementation and planning stay in the main conversation (the implementer and planner roles were retired in v4, 2026-10-29).

| Name | Role | model | reasoning effort |
|---|---|---|---|
| `scanner` | Side research where the answer is in the files: lists, classification, checks | `gpt-5.6-luna` | `medium` |
| `explorer` | Side research that needs reasoning: cross-file tracing, long documents, external docs | `gpt-5.6-terra` | `medium` |
| `reviewer` | Fresh-context adversarial review of a code diff | `gpt-5.6-terra` | `high` |
| `verifier` | Ordinary fresh-context acceptance; judges only | `gpt-5.6-terra` | `high` |
| `sol_verifier` | High-risk acceptance: security, irreversible, architecture | `gpt-5.6-sol` | `high` |

## Installation

Full steps are in [`docs/install.md`](docs/install.md), whose 「安裝對應」 table lists where each file installs. Pick by platform and privilege:

- **Claude Code, macOS/Linux**: symlinks; edits to the repo take effect immediately.
- **Codex, macOS/Linux**: symlinks for `AGENTS.md` and skills; a sync script writes agent TOML files as regular files.
- **Windows (PowerShell)**: run in an administrator PowerShell, which installs both Claude Code and Codex.
- **Regular-file sync**: for machines that cannot elevate; `scripts/sync-profile.py` writes copies; rerun it after every repo change.

For a new machine (no file in `global/shared/hosts/`), probe it and create its file by following 「新機器建檔（5 分鐘探測清單）」 in [`docs/new-host.md`](docs/new-host.md).

How the installed pieces work at runtime (what loads when, what each hook enforces, which `settings.json` fields the system depends on, and what a rebuild has to restore on both sides) is explained in 「運作機制」 of [`docs/design/mechanism.md`](docs/design/mechanism.md).

`docs/install.md`, `docs/new-host.md`, `docs/design/mechanism.md` and `docs/repo-layout.md` exist in Chinese only.

## Directory map

Per-file purposes are in 「檔案結構」 of [`docs/repo-layout.md`](docs/repo-layout.md).

| Path | Purpose |
|---|---|
| `CLAUDE.md`, `AGENTS.md` | This repo's own project spec, not a global entry point |
| `global/` | What installs into `~/.claude`, `~/.codex`, `~/.agents` |
| `global/claude/` | Claude Code only: entry, route card, hooks, agents |
| `global/codex/` | Codex only: entry, dispatch rules, templates, agents |
| `global/shared/` | Shared: judgment, skills, rubrics, hosts |
| `.claude/skills/` | Repo-only skills, not installed globally |
| `docs/` | Design notes, rationale, install guides, lessons; on demand |
| `scripts/`, `tests/` | Sync scripts, usage scripts, tests |

## Known degradation modes and prevention (maintainers must read)

1. **Ritual death**: templates are copied but acceptance criteria are empty words → another agent must be able to decide pass or fail from the sentence alone; a verifier FAILs vague criteria.
2. **Bloat death**: every pitfall gets stuffed into the rules → lessons go to `docs/lessons.md` first (active cap: 8 entries) and move to `docs/lessons-archive.md` once promoted; a tripwire schedules a sunset review.
3. **Always-loaded-area bloat death**: long situational content sits in the always-loaded area, so every session pays → ask "does every job need this?"; if not, use a skill, a rubric or `docs/`.
4. **Over-specification death**: decision trees for judgments the model already makes → apply the sunset clause and keep only this environment's gotchas (`maintain-guideline`, 「瘦身協議」).
5. **Staleness death**: model names or tool parameters change and docs lag → facts carry a probe or verification date, are rechecked before use, and a stale one is fixed on the spot.
6. **Broken-link death**: a renamed file or heading leaves routing pointing nowhere → `rg --hidden` for references before renaming and fix them in the same change (`maintain-guideline`, 「路由完整性（防斷鏈）」).
7. **Bypass death**: "this task is simple, no need to follow the rules" → if a rule seems unreasonable, raise it through the process, never bypass it silently.

## Honesty clause: what this system cannot fix

Decomposition, templates and fresh-context acceptance raise **execution quality**, not **taste and ambiguous questions** such as long-term architecture trade-offs, copy tone or whether a feature should exist.

When you hit one, in order: follow the repo's conventions → use the strongest available model → offer candidates for the user to choose from.

If that is not enough, state plainly that "this is beyond what the system can guarantee".
