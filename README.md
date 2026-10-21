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

### Role model: controller, worker, verifier

The main conversation is the controller: it plans, delegates, checks and reports, while separate roles implement and verify.

- Controller (main conversation): no grunt work; it edits itself only for single-point, low-risk, mechanically verifiable fixes with a clear scope, never CI or release config.
- `worker`: starts only from an approved plan the controller signed off; a missing plan is sent back.
- `verifier`: fresh context, judges only, never produces.

Delegation table (abridged from `global/claude/route-card.md`):

| Task | Delegate to |
|---|---|
| Scan the repo, find files with X, build a list | `Explore`, `model: haiku` |
| Read long documents, browse the web | `general-purpose`, sonnet |
| Implement, fix bugs, refactor, batch edits, docs | `worker` |
| Design and architecture trade-offs | `Plan`, opus |
| Cross-file reasoning, hard reviews | `general-purpose`, opus |
| Acceptance | `verifier`, `model: opus`; always for any document before merge or ready, code by dispatch skill §6 tiers, still applies when project rules name only code-review |
| Fresh review of a code diff | Fresh subagent running `code-review` skill, never the main conversation itself; adds to `verifier`, never replaces it; after fixing findings, re-verify per dispatch skill §7 |

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
| `dispatch` | Delegating, model choice, escalation, post-review fixes | Both platforms |
| `handoff` | Writing briefs, reports, verdicts; wrap-up, compact | Both platforms |
| `git-commit` | Writing a commit message or squash-merge title | Both platforms |
| `create-pr` | Opening a Pull Request from a branch | Both platforms |
| `parallel-dispatch` | Splitting work across 2+ agents or independent issues | Both platforms |
| `writing-principles` | Writing, editing or reviewing READMEs, guides, design docs | Both platforms |
| `maintain-guideline` | Changing this system itself (`global/**`, entry points) | repo-only |
| `usage-review` | Measuring Claude Code usage and dispatch behavior | repo-only |

## Agents

Claude defines only `worker` and `verifier`; Codex has 11 roles. Each definition file pins model and effort.

### Claude Code

`Explore`, `Plan` and `general-purpose` are built into Claude Code; the route card assigns their uses.

| Name | Role | model | effort | tools |
|---|---|---|---|---|
| `worker` | Implements from an approved plan; no plan, no work | `claude-sonnet-5-5` | `xhigh` | Read, Write, Edit, Bash, Glob, Grep, LSP |
| `verifier` | Fresh-context acceptance: PASS/FAIL/UNSURE per criterion | `opus` | `medium` | Read, Bash, Glob, Grep, LSP |

### Codex

Codex uses three tiers, Luna, Terra and Sol, from low to high. The escalation rules (Luna to Terra, Terra to Sol) are in 「升降級路徑」 of `global/codex/rules/dispatch.md`.

| Name | Role | model | reasoning effort |
|---|---|---|---|
| `scanner` | Low-risk read-only scans: lists, classification, checks | `gpt-5.6-luna` | `medium` |
| `explorer` | Read-only exploration, cross-file tracing, research | `gpt-5.6-terra` | `medium` |
| `planner` | Read-only planning: scope, risks, invariants, phases | `gpt-5.6-terra` | `high` |
| `worker` | Standard implementer; needs a complete approved plan | `gpt-5.6-luna` | `max` |
| `pro_worker` | Implementation with known complexity signals | `gpt-5.6-terra` | `high` |
| `recovery_worker` | Takes over after Luna falls short or fails twice | `gpt-5.6-terra` | `high` |
| `reviewer` | Read-only adversarial review in a fresh context | `gpt-5.6-terra` | `high` |
| `verifier` | Ordinary fresh-context acceptance; judges only | `gpt-5.6-terra` | `high` |
| `escalation_planner` | Read-only root-cause plan once Terra is the limit | `gpt-5.6-sol` | `medium` |
| `escalation_worker` | Hard implementation once Terra is confirmed short | `gpt-5.6-sol` | `medium` |
| `sol_verifier` | High-risk acceptance: security, irreversible, architecture | `gpt-5.6-sol` | `high` |

## Installation

Full steps are in [`docs/install.md`](docs/install.md), whose 「安裝對應」 table lists where each file installs. Pick by platform and privilege:

- **Claude Code, macOS/Linux**: symlinks; edits to the repo take effect immediately.
- **Codex, macOS/Linux**: symlinks for `AGENTS.md` and skills; a sync script writes agent TOML files as regular files.
- **Windows (PowerShell)**: run in an administrator PowerShell, which installs both Claude Code and Codex.
- **Regular-file sync**: for machines that cannot elevate; `scripts/sync-profile.py` writes copies; rerun it after every repo change.

For a new machine (no file in `global/shared/hosts/`), probe it and create its file by following 「新機器建檔（5 分鐘探測清單）」 in [`docs/new-host.md`](docs/new-host.md).

`docs/install.md`, `docs/new-host.md` and `docs/repo-layout.md` exist in Chinese only.

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
