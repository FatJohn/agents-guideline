#!/usr/bin/env python3
"""Audit which defence layers a repo actually has: does each check run, run in CI, and fail CI.

Read-only. Standard library only. Usage:

    python3 layer_audit.py --repo <path> [--format markdown|json] [--github]

Every row has: layer, check, status, evidence, note. Status is one of STATUSES below.
"Configured but not blocking" (local-only / non-blocking / inactive) is always a
different value from "blocking". There is no score and no grade on purpose.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

STATUSES = {
    "blocking": "有在擋：啟用、CI 會跑、違規讓 CI 失敗",
    "non-blocking": "CI 會跑，但失敗不擋（continue-on-error、|| true、只到 warning、一般 PR 不跑）",
    "local-only": "有設定或本機指令，CI 沒有呼叫",
    "inactive": "套件或設定在，但沒有被載入執行",
    "present": "非執行型的項目存在（常駐檔、範本、測試檔）",
    "absent": "沒找到；證據欄寫搜尋過哪裡",
    "unknown": "腳本判不出來，要人或 AI 看",
}
# Better first; used to pick one status for a tool that shows up several times.
STATUS_ORDER = ["blocking", "non-blocking", "unknown", "local-only", "inactive", "present", "absent"]

LAYERS = ("結構", "機器擋", "跑起來驗", "文字規則", "獨立審查")

SKIP_DIRS = {".git", "node_modules", "build", ".dart_tool", ".build", "Pods", ".gradle", "DerivedData",
             ".worktrees", ".orca", "dist", "coverage", ".venv", "venv", "__pycache__", ".tools", ".kotlin"}

# Where each language's "list the enabled lint rules" procedure lives (agent-rules owns it).
AGENT_RULES_REF = {
    "TypeScript": "agent-rules/references/typescript-eslint.md",
    "JavaScript": "agent-rules/references/typescript-eslint.md",
    "Dart": "agent-rules/references/dart-flutter.md",
    "Swift": "agent-rules/references/swift-ios.md",
    "Kotlin": "agent-rules/references/kotlin-android.md",
}
UNTESTED_LANGS = {"Go", "Python", ".NET"}


@dataclass
class Row:
    layer: str
    check: str
    status: str
    evidence: str
    note: str = ""
    baseline: bool = False


# --------------------------------------------------------------------------- tiny YAML subset


class YMap(dict):
    def __init__(self):
        super().__init__()
        self.lines: dict[str, int] = {}


class YList(list):
    def __init__(self):
        super().__init__()
        self.lines: list[int] = []


def _strip_comment(text: str) -> str:
    quote = None
    prev = ""
    for i, ch in enumerate(text):
        if quote:
            if ch == quote:
                quote = None
        elif ch in "\"'" and (prev.strip() == "" or prev.rstrip()[-1:] in ":-[,{"):
            quote = ch
        elif ch == "#" and (i == 0 or text[i - 1] in " \t"):
            return text[:i].rstrip()
        prev = text[: i + 1]
    return text.rstrip()


def _scalar(val: str):
    val = val.strip()
    if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
        return val[1:-1]
    if val.startswith("[") and val.endswith("]"):
        out = YList()
        for part in val[1:-1].split(","):
            if part.strip():
                out.append(_scalar(part))
        return out
    return val


def _split_key(content: str):
    """Return (key, value) if content is `key: value` / `key:`, else None."""
    m = re.match(r"""^(?:"([^"]*)"|'([^']*)'|([^\s"'#][^:]*?))\s*:(?:\s+(.*)|\s*)$""", content)
    if not m:
        return None
    key = m.group(1) if m.group(1) is not None else (m.group(2) if m.group(2) is not None else m.group(3))
    return key.strip(), (m.group(4) or "").strip()


class _Yaml:
    def __init__(self, text: str):
        self.raw = text.splitlines()
        self.override: dict[int, tuple[int, str]] = {}

    def entry(self, idx):
        if idx in self.override:
            return self.override[idx]
        line = self.raw[idx]
        content = _strip_comment(line)
        if not content.strip():
            return None
        return len(content) - len(content.lstrip(" ")), content.strip()

    def next_sig(self, idx):
        while idx < len(self.raw):
            e = self.entry(idx)
            if e is not None and not e[1].startswith("---"):
                return idx
            idx += 1
        return idx

    def block_scalar(self, idx, parent_indent, style):
        lines = []
        j = idx + 1
        while j < len(self.raw):
            line = self.raw[j]
            if line.strip() and (len(line) - len(line.lstrip(" "))) <= parent_indent:
                break
            lines.append(line)
            j += 1
        while lines and not lines[-1].strip():
            lines.pop()
        ind = min((len(x) - len(x.lstrip(" ")) for x in lines if x.strip()), default=0)
        body = [x[ind:] for x in lines]
        text = "\n".join(body) if style.startswith("|") else " ".join(x.strip() for x in body)
        return text, j

    def parse(self, idx, min_indent):
        idx = self.next_sig(idx)
        if idx >= len(self.raw):
            return None, idx
        indent, content = self.entry(idx)
        if indent < min_indent:
            return None, idx
        if content == "-" or content.startswith("- "):
            return self.parse_seq(idx, indent)
        if _split_key(content):
            return self.parse_map(idx, indent)
        return _scalar(content), idx + 1

    def value_after_key(self, idx, indent, val):
        if val[:1] in "|>" and re.fullmatch(r"[|>][-+]?\d*", val):
            return self.block_scalar(idx, indent, val)
        if val:
            return _scalar(val), idx + 1
        nxt = self.next_sig(idx + 1)
        if nxt < len(self.raw):
            n_indent, n_content = self.entry(nxt)
            if n_indent > indent or (n_indent == indent and (n_content == "-" or n_content.startswith("- "))):
                return self.parse(nxt, n_indent)
        return "", idx + 1

    def parse_map(self, idx, indent):
        out = YMap()
        while True:
            idx = self.next_sig(idx)
            if idx >= len(self.raw):
                break
            e_indent, content = self.entry(idx)
            if e_indent != indent or content.startswith("- ") or content == "-":
                break
            kv = _split_key(content)
            if not kv:
                break
            key, val = kv
            out.lines[key] = idx + 1
            out[key], idx = self.value_after_key(idx, indent, val)
        return out, idx

    def parse_seq(self, idx, indent):
        out = YList()
        while True:
            idx = self.next_sig(idx)
            if idx >= len(self.raw):
                break
            e_indent, content = self.entry(idx)
            if e_indent != indent or not (content == "-" or content.startswith("- ")):
                break
            out.lines.append(idx + 1)
            rest = content[1:].lstrip()
            if not rest:
                item, idx = self.parse(idx + 1, indent + 1)
            elif _split_key(rest) and not rest.startswith(("'", '"', "[", "{")) or re.match(r"^['\"][^'\"]+['\"]\s*:", rest):
                self.override[idx] = (indent + (len(content) - len(rest)), rest)
                item, idx = self.parse_map(idx, self.override[idx][0])
            else:
                item, idx = _scalar(rest), idx + 1
            out.append(item)
        return out, idx


def parse_yaml(text: str):
    try:
        node, _ = _Yaml(text).parse(0, 0)
        return node
    except (IndexError, ValueError, RecursionError):
        return None


# --------------------------------------------------------------------------- repo access


class Repo:
    def __init__(self, root: Path):
        self.root = root
        self.files = self._list_files()
        self._cache: dict[str, str] = {}

    def _list_files(self) -> list[str]:
        try:
            out = subprocess.run(["git", "-C", str(self.root), "ls-files", "-z"], capture_output=True, check=True)
            files = [f for f in out.stdout.decode("utf-8", "replace").split("\0") if f]
            if files:
                return sorted(f for f in files if (self.root / f).is_file())
        except (OSError, subprocess.CalledProcessError):
            pass
        found = []
        for dirpath, dirnames, filenames in os.walk(self.root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for name in filenames:
                found.append(os.path.relpath(os.path.join(dirpath, name), self.root).replace(os.sep, "/"))
        return sorted(found)

    def read(self, rel: str) -> str:
        if rel not in self._cache:
            try:
                self._cache[rel] = (self.root / rel).read_text(encoding="utf-8", errors="replace")
            except OSError:
                self._cache[rel] = ""
        return self._cache[rel]

    def exists(self, rel: str) -> bool:
        return rel in self.files or (self.root / rel).is_file()

    def glob(self, *patterns: str) -> list[str]:
        return [f for f in self.files if any(fnmatch.fnmatch(f, p) or fnmatch.fnmatch(os.path.basename(f), p) for p in patterns)]

    def first_line(self, rel: str, pattern: str) -> str:
        """`path:line text` for the first line matching pattern, else just the path."""
        for i, line in enumerate(self.read(rel).splitlines(), 1):
            if re.search(pattern, line):
                return f"{rel}:{i} `{line.strip()[:120]}`"
        return rel


def short(text: str, n: int = 110) -> str:
    text = " ".join(text.split())
    return text if len(text) <= n else text[: n - 1] + "…"


# --------------------------------------------------------------------------- CI model


@dataclass
class Invocation:
    """One shell line CI ends up executing, with how it got there and why it might not block."""

    text: str
    origin: str  # e.g. ".github/workflows/ci.yml:33"
    chain: list[str] = field(default_factory=list)
    swallow: list[str] = field(default_factory=list)  # reasons a failure would not fail CI
    gate: list[str] = field(default_factory=list)  # reasons it does not run on (normal) PRs
    soft: list[str] = field(default_factory=list)  # reasons the script cannot tell
    wf: str = ""
    job: str = ""

    def evidence(self) -> str:
        hops = " → ".join([f"{self.origin} `{short(self.chain[0], 70)}`"] + [f"`{short(c, 70)}`" for c in self.chain[1:]])
        return hops


PR_EVENTS = {"pull_request", "pull_request_target", "merge_group"}
SAFE_IF = re.compile(r"^\s*(\$\{\{)?\s*(!?\s*cancelled\(\)|always\(\)|success\(\)|failure\(\)|steps\.[\w-]+\.(outcome|conclusion)\s*[!=]=\s*'\w+'|hashFiles\([^)]*\)\s*!=\s*''|&&|\|\||\s|\(|\))*\s*(\}\})?\s*$")
NOT_PR_IF = re.compile(r"github\.event_name\s*!=\s*['\"]pull_request['\"]|github\.event_name\s*==\s*['\"](push|schedule|workflow_dispatch|release)['\"]|startsWith\(\s*github\.ref\s*,\s*['\"]refs/tags")


def _triggers(on) -> set[str]:
    if isinstance(on, str):
        return {on}
    if isinstance(on, list):
        return {str(x) for x in on}
    if isinstance(on, dict):
        return set(on.keys())
    return set()


def _if_reason(cond: str, where: str) -> tuple[list[str], list[str]]:
    cond = str(cond)
    if not cond or SAFE_IF.match(cond):
        return [], []
    if NOT_PR_IF.search(cond):
        return [f"{where} `if: {short(cond, 80)}`：一般 PR 不跑"], []
    return [], [f"{where} 有條件 `if: {short(cond, 80)}`，腳本未判讀"]


def _truthy(val) -> str:
    v = str(val).strip().lower()
    if v == "true":
        return "true"
    if "${{" in v:
        return "expr"
    return ""


def github_invocations(repo: Repo) -> tuple[list[Invocation], list[str], list[Row]]:
    wf_files = [f for f in repo.files if re.match(r"^\.github/workflows/[^/]+\.ya?ml$", f)]
    parsed = {}
    notes: list[Row] = []
    for wf in wf_files:
        doc = parse_yaml(repo.read(wf))
        if not isinstance(doc, dict):
            notes.append(Row("機器擋", "CI 設定解析", "unknown", wf, "YAML 解析失敗，這個 workflow 的指令沒有列入"))
            continue
        parsed[wf] = doc
    # workflow_call callers: reusable workflows inherit callers' triggers.
    triggers = {wf: _triggers(doc.get("on", doc.get(True, ""))) for wf, doc in parsed.items()}
    callers: dict[str, set[str]] = {}
    for wf, doc in parsed.items():
        for job in (doc.get("jobs") or {}).values():
            if isinstance(job, dict) and str(job.get("uses", "")).startswith("./.github/workflows/"):
                callers.setdefault(str(job["uses"])[2:].split("@")[0], set()).add(wf)
    for _ in range(3):
        for wf in parsed:
            if "workflow_call" in triggers[wf]:
                for c in callers.get(wf, ()):
                    triggers[wf] |= triggers.get(c, set())

    out: list[Invocation] = []
    for wf, doc in parsed.items():
        trig = triggers[wf]
        wf_gate = [] if trig & PR_EVENTS else [f"{wf} 只在 {', '.join(sorted(trig)) or '（無 on）'} 觸發，PR 不跑"]
        default_shell = str(((doc.get("defaults") or {}).get("run") or {}).get("shell", "")) if isinstance(doc.get("defaults"), dict) else ""
        jobs = doc.get("jobs") or {}
        if not isinstance(jobs, dict):
            continue
        for jname, job in jobs.items():
            if not isinstance(job, dict):
                continue
            j_line = jobs.lines.get(jname, 0) if isinstance(jobs, YMap) else 0
            j_gate, j_soft = _if_reason(job.get("if", ""), f"{wf}:{j_line} job `{jname}`")
            j_swallow = []
            coe = _truthy(job.get("continue-on-error", ""))
            if coe == "true":
                j_swallow.append(f"{wf}:{j_line} job `{jname}` continue-on-error: true")
            elif coe == "expr":
                j_soft.append(f"job `{jname}` continue-on-error 是運算式")
            job_shell = str(((job.get("defaults") or {}).get("run") or {}).get("shell", default_shell)) if isinstance(job.get("defaults"), dict) else default_shell
            steps = job.get("steps") or []
            if not isinstance(steps, list):
                continue
            for k, step in enumerate(steps):
                if not isinstance(step, dict) or "run" not in step:
                    continue
                s_line = step.lines.get("run", 0) if isinstance(step, YMap) else 0
                s_gate, s_soft = _if_reason(step.get("if", ""), f"{wf}:{s_line} step")
                s_swallow = []
                coe = _truthy(step.get("continue-on-error", ""))
                if coe == "true":
                    s_swallow.append(f"{wf}:{s_line} step continue-on-error: true")
                elif coe == "expr":
                    s_soft.append("step continue-on-error 是運算式")
                shell = str(step.get("shell", job_shell))
                pipefail = shell.strip() == "bash" or "pipefail" in shell
                base = Invocation(
                    text="", origin=f"{wf}:{s_line}",
                    swallow=j_swallow + s_swallow, gate=wf_gate + j_gate + s_gate, soft=j_soft + s_soft,
                    wf=wf, job=jname,
                )
                cwd = str(step.get("working-directory", "") or (((job.get("defaults") or {}).get("run") or {}).get("working-directory", "") if isinstance(job.get("defaults"), dict) else ""))
                out.extend(expand_block(repo, str(step["run"]), base, cwd, pipefail, set_e=True))
    github_invocations.parsed = parsed  # type: ignore[attr-defined]
    return out, wf_files, notes


def required_jobs(parsed: dict, contexts: list[str]) -> set[tuple[str, str]]:
    """(workflow, job) pairs whose failure reaches a required status check through `needs:`."""
    want = {re.sub(r"\s*\(.*\)$", "", c).strip() for c in contexts}
    req: set[tuple[str, str]] = set()
    for wf, doc in parsed.items():
        jobs = doc.get("jobs") or {}
        if not isinstance(jobs, dict):
            continue
        for jname, job in jobs.items():
            name = str(job.get("name", "")) if isinstance(job, dict) else ""
            if jname in want or re.sub(r"\s*\(.*\)$", "", name).strip() in want or any(c.endswith(f"/ {jname}") for c in contexts):
                req.add((wf, jname))
    changed = True
    while changed:
        changed = False
        for wf, jname in list(req):
            job = (parsed[wf].get("jobs") or {}).get(jname)
            if not isinstance(job, dict):
                continue
            needs = job.get("needs", [])
            needs = [needs] if isinstance(needs, str) else list(needs or [])
            targets = [(wf, n) for n in needs]
            uses = str(job.get("uses", ""))
            if uses.startswith("./.github/workflows/"):
                callee = uses[2:].split("@")[0]
                targets += [(callee, j) for j in (parsed.get(callee, {}).get("jobs") or {})]
            for t in targets:
                if t not in req:
                    req.add(t)
                    changed = True
    return req


def apply_required(invs: list[Invocation], parsed: dict, contexts: list[str]) -> None:
    req = required_jobs(parsed, contexts)
    if not req:
        return  # no context matched a job here; cannot tell, leave as is
    for inv in invs:
        if inv.wf and (inv.wf, inv.job) not in req:
            inv.gate.append(f"job `{inv.job}` 不在必要檢查（{', '.join(contexts)}）的 needs 鏈上，失敗不擋 merge")


def gitlab_invocations(repo: Repo) -> list[Invocation]:
    if not repo.exists(".gitlab-ci.yml"):
        return []
    doc = parse_yaml(repo.read(".gitlab-ci.yml"))
    out = []
    if not isinstance(doc, dict):
        return out
    for jname, job in doc.items():
        if not isinstance(job, dict) or "script" not in job:
            continue
        line = doc.lines.get(jname, 0) if isinstance(doc, YMap) else 0
        sw = [f".gitlab-ci.yml:{line} job `{jname}` allow_failure: true"] if _truthy(job.get("allow_failure", "")) == "true" else []
        gate = []
        if "merge_request" not in json.dumps(job, ensure_ascii=False) and ("only" in job or "rules" in job):
            gate.append(f".gitlab-ci.yml:{line} job `{jname}` 的 only／rules 沒提到 merge request")
        script = job["script"]
        lines = script if isinstance(script, list) else [script]
        for cmd in lines:
            base = Invocation(text="", origin=f".gitlab-ci.yml:{line}", swallow=list(sw), gate=list(gate),
                              soft=["GitLab CI 解析未實測"])
            out.extend(expand_block(repo, str(cmd), base, "", pipefail=False, set_e=True))
    return out


SWALLOW_RES = [
    (re.compile(r"\|\|\s*(true|:|exit\s+0|echo\b)"), "`|| true` 類寫法吞掉失敗"),
    (re.compile(r";\s*(true|:|exit\s+0)\s*$"), "結尾 `; true` 吞掉失敗"),
]
HANDLED = re.compile(r"\|\||&&\s*$|^\s*(if|elif|while|until|!)\b|\bexit\b|\$\(|^\s*\w+=")


def _logical_lines(text: str) -> list[str]:
    lines, buf = [], ""
    for raw in text.splitlines():
        stripped = raw.rstrip()
        if stripped.endswith("\\"):
            buf += stripped[:-1] + " "
            continue
        buf += raw
        lines.append(buf)
        buf = ""
    if buf:
        lines.append(buf)
    return lines


def expand_block(repo: Repo, text: str, parent: Invocation, cwd: str, pipefail: bool, set_e: bool, depth: int = 0) -> list[Invocation]:
    out: list[Invocation] = []
    lines, heredoc = [], None
    for ln in _logical_lines(text):
        if heredoc:
            if ln.strip() == heredoc:
                heredoc = None
            continue
        if not ln.strip() or ln.strip().startswith("#"):
            continue
        lines.append(ln)
        m = re.search(r"<<-?\s*['\"]?(\w+)['\"]?", ln)
        if m:
            heredoc = m.group(1)  # heredoc bodies are data, not commands
    set_plus_e = False
    for i, line in enumerate(lines):
        checked = bool(re.search(r"PIPESTATUS|\$\?", " ".join(lines[i + 1:i + 4])))
        if re.search(r"\bset\s+\+e\b", line):
            set_plus_e = True
        if re.search(r"\bset\s+-\w*o\s+pipefail|\bset\s+-\w*e", line):
            set_plus_e = False if re.search(r"\bset\s+-\w*e", line) else set_plus_e
            if "pipefail" in line:
                pipefail = True
        inv = Invocation(text=line.strip(), origin=parent.origin, chain=parent.chain + [line.strip()],
                         swallow=list(parent.swallow), gate=list(parent.gate), soft=list(parent.soft), wf=parent.wf, job=parent.job)
        for rx, why in SWALLOW_RES:
            if rx.search(line):
                inv.swallow.append(f"`{short(line, 60)}`：{why}")
        if set_plus_e and not checked:
            inv.swallow.append("前面有 `set +e`，失敗不會中止，後面也沒有檢查 `$?`／`PIPESTATUS`")
        if not set_e and i < len(lines) - 1 and not HANDLED.search(line):
            inv.soft.append("腳本沒有 `set -e` 且這行不是最後一行，失敗可能被後面的指令蓋掉")
        inv.pipefail = pipefail or checked  # type: ignore[attr-defined]
        out.append(inv)
        if depth < 3:
            out.extend(_expand_indirect(repo, line, inv, cwd, pipefail, depth))
    return out


def _resolve(repo: Repo, cwd: str, rel: str) -> str | None:
    rel = rel.strip("'\"")
    for base in (cwd, ""):
        cand = os.path.normpath(os.path.join(base, rel)).replace(os.sep, "/")
        if cand.startswith("./"):
            cand = cand[2:]
        if repo.exists(cand):
            return cand
    return None


def _package_json(repo: Repo, cwd: str) -> tuple[str, dict]:
    for rel in (os.path.join(cwd, "package.json") if cwd else "package.json", "package.json"):
        rel = os.path.normpath(rel).replace(os.sep, "/")
        if repo.exists(rel):
            try:
                return rel, json.loads(repo.read(rel))
            except ValueError:
                return rel, {}
    return "", {}


def _makefile_target(repo: Repo, cwd: str, target: str) -> tuple[str, str] | None:
    for name in ("Makefile", "makefile", "GNUmakefile"):
        rel = _resolve(repo, cwd, name)
        if not rel:
            continue
        lines = repo.read(rel).splitlines()
        for i, line in enumerate(lines):
            if re.match(rf"^{re.escape(target)}\s*:(?!=)", line):
                recipe = []
                for nxt in lines[i + 1:]:
                    if nxt.startswith("\t"):
                        recipe.append(nxt[1:])
                    elif nxt.strip() == "":
                        continue
                    else:
                        break
                return f"{rel}:{i + 1}", "\n".join(recipe)
    return None


PM_RUN = re.compile(r"(?:^|[\s;&|(])(?:pnpm|yarn|bun)\s+(?:run\s+)?((?!exec\b|dlx\b|install\b|add\b|i\b|-)[\w:.-]+)|(?:^|[\s;&|(])npm\s+(?:run(?:-script)?\s+([\w:.-]+)|(test|start)\b)")
MAKE_RUN = re.compile(r"(?:^|[\s;&|(])make\s+(?:-\S+\s+)*([\w.-]+)")
SH_RUN = re.compile(r"(?:^|[\s;&|(])(?:(?:/bin/|/usr/bin/env\s+)?(?:bash|sh|zsh)\s+(?:-\w+\s+)*)?((?:\.{0,2}/)?[\w./-]+\.sh)\b")


def _expand_indirect(repo: Repo, line: str, inv: Invocation, cwd: str, pipefail: bool, depth: int) -> list[Invocation]:
    out = []
    m = PM_RUN.search(line)
    if m:
        name = m.group(1) or m.group(2) or m.group(3)
        rel, pkg = _package_json(repo, cwd)
        script = (pkg.get("scripts") or {}).get(name) if isinstance(pkg, dict) else None
        if script:
            sub = Invocation(text="", origin=inv.origin, chain=inv.chain + [f"{rel} scripts.{name}"],
                             swallow=list(inv.swallow), gate=list(inv.gate), soft=list(inv.soft), wf=inv.wf, job=inv.job)
            # npm runs scripts with `sh -c`: `a; b` keeps going after a fails.
            for part_i, part in enumerate(re.split(r"\s*&&\s*", script)):
                pieces = re.split(r"\s*;\s*", part)
                for j, piece in enumerate(pieces):
                    child = expand_block(repo, piece, sub, cwd, pipefail, set_e=True, depth=depth + 1)
                    if j < len(pieces) - 1:
                        for c in child:
                            c.swallow.append(f"{rel} scripts.{name} 用 `;` 串接，前段失敗會被後段蓋掉")
                    out.extend(child)
    m = MAKE_RUN.search(line)
    if m:
        found = _makefile_target(repo, cwd, m.group(1))
        if found:
            where, recipe = found
            sub = Invocation(text="", origin=inv.origin, chain=inv.chain + [f"{where} make {m.group(1)}"],
                             swallow=list(inv.swallow), gate=list(inv.gate), soft=list(inv.soft), wf=inv.wf, job=inv.job)
            for rline in recipe.splitlines():
                child = expand_block(repo, rline.lstrip("@"), sub, cwd, pipefail, set_e=True, depth=depth + 1)
                if rline.lstrip("@").startswith("-"):
                    for c in child:
                        c.swallow.append(f"{where} recipe 行首 `-` 忽略失敗")
                out.extend(child)
    for sm in SH_RUN.finditer(line):
        rel = _resolve(repo, cwd, sm.group(1))
        if not rel or rel in " ".join(inv.chain[:-1]):
            continue
        body = repo.read(rel)
        has_e = bool(re.search(r"^\s*set\s+-\w*e", body, re.M)) or bool(re.match(r"#!.*\s-\w*e", body))
        has_pf = "pipefail" in body
        sub = Invocation(text="", origin=inv.origin, chain=inv.chain + [rel],
                         swallow=list(inv.swallow), gate=list(inv.gate), soft=list(inv.soft), wf=inv.wf, job=inv.job)
        out.extend(expand_block(repo, body, sub, os.path.dirname(rel), has_pf, set_e=has_e, depth=depth + 1))
    return out


# --------------------------------------------------------------------------- tool catalogue


def _gradle(tasks: str):
    rx = re.compile(rf"(?:gradlew|\bgradle)\b.*?(?<![\w-])(?::?[\w-]+:)*(?:{tasks})(?![\w-])")
    return lambda line: bool(rx.search(line))


def _rx(pattern: str):
    rx = re.compile(pattern)
    return lambda line: bool(rx.search(line))


@dataclass
class Tool:
    id: str
    lang: str
    kind: str  # format | lint | types | structure | test | integration | other
    match: object
    configs: tuple = ()
    deps: tuple = ()
    needs_flag: tuple = ()  # (regex, reason) – without it a failure does not fail the command
    warn_flag: tuple = ()  # (regex, reason) – without it only warnings slip through
    note: str = ""


TOOLS = [
    # TypeScript / JavaScript
    Tool("eslint", "JS/TS", "lint", _rx(r"(?:^|[\s/])eslint(?:\s|$)|\bnext\s+lint\b"),
         ("eslint.config.*", ".eslintrc", ".eslintrc.*"), ("eslint",),
         warn_flag=(r"--max-warnings[ =]0\b", "沒帶 `--max-warnings 0`，設成 warn 的規則不會讓 CI 失敗")),
    Tool("prettier", "JS/TS", "format", _rx(r"(?:^|[\s/])prettier\b"), (".prettierrc", ".prettierrc.*", "prettier.config.*"), ("prettier",),
         needs_flag=(r"\s(--check|-c|--list-different|-l)\b", "沒帶 `--check`，只會改檔不會失敗")),
    Tool("biome", "JS/TS", "lint", _rx(r"\bbiome\s+(check|ci|lint|format)\b"), ("biome.json", "biome.jsonc"), ("@biomejs/biome",), note="未實測"),
    Tool("tsc", "JS/TS", "types", _rx(r"(?:^|[\s/&;])(vue-)?tsc(?:\s|$)"), ("tsconfig.json",), ("typescript",)),
    Tool("dependency-cruiser", "JS/TS", "structure", _rx(r"\bdepcruise\b"), (".dependency-cruiser.*",), ("dependency-cruiser",)),
    Tool("knip", "JS/TS", "other", _rx(r"\bknip\b"), ("knip.json", "knip.jsonc", "knip.config.*"), ("knip",)),
    Tool("js-unit-test", "JS/TS", "test", _rx(r"(?:^|[\s/])(vitest|jest|mocha)\b|\bnode\s+--test\b|\bplaywright\s+test\b.*-c\s+\S*unit")),
    Tool("playwright", "JS/TS", "integration", _rx(r"\bplaywright\s+test\b"), ("playwright.config.*",), ("@playwright/test",)),
    Tool("cypress", "JS/TS", "integration", _rx(r"\bcypress\s+run\b"), ("cypress.config.*",), ("cypress",), note="未實測"),
    # Dart / Flutter
    Tool("dart format", "Dart", "format", _rx(r"\bdart\s+format\b"),
         needs_flag=(r"--set-exit-if-changed", "沒帶 `--set-exit-if-changed`，格式不符也 exit 0")),
    Tool("dart/flutter analyze", "Dart", "lint", _rx(r"\b(dart|flutter)\s+analyze\b"), ("analysis_options.yaml",),
         warn_flag=(r"\bflutter\s+analyze\b(?!.*--no-fatal-infos)|--fatal-infos", "`dart analyze` 預設不把 info 當失敗，而 lint 規則多數是 info；要帶 `--fatal-infos`")),
    Tool("custom_lint", "Dart", "lint", _rx(r"\bcustom_lint\b"), (), ("custom_lint",)),
    Tool("flutter/dart test", "Dart", "test", _rx(r"\b(flutter|dart)\s+test\b")),
    Tool("flutter integration_test", "Dart", "integration", _rx(r"\bflutter\s+(test\s+integration_test|drive)\b|\bpatrol\s+test\b"), ("integration_test/*",), ("integration_test", "patrol")),
    # Swift
    Tool("SwiftLint", "Swift", "lint", _rx(r"(?:^|[\s/])swiftlint(?:\s+lint)?(?:\s|$)"), (".swiftlint.yml", ".swiftlint.yaml"),
         warn_flag=(r"--strict\b", "沒帶 `--strict`，warning 級規則不會讓 CI 失敗")),
    Tool("swift-format", "Swift", "format", _rx(r"\bswift[- ]format\s+lint\b"), (".swift-format",),
         needs_flag=(r"--strict\b", "沒帶 `--strict`，swift-format 的發現是 warning、不會讓 CI 失敗")),
    Tool("SwiftFormat", "Swift", "format", _rx(r"(?:^|[\s/])swiftformat\b.*--lint"), (".swiftformat",), note="未實測"),
    Tool("swift compile", "Swift", "types", _rx(r"\bswift\s+(build|test)\b|\bxcodebuild\b.*\b(build|test|build-for-testing|analyze)\b|\bfastlane\s+(scan|test|build)\b|\bflutter\s+build\s+ios\b")),
    Tool("swift test", "Swift", "test", _rx(r"\bswift\s+test\b|\bxcodebuild\b.*\btest\b|\bfastlane\s+(scan|test)\b")),
    # Kotlin / Android
    Tool("ktlint", "Kotlin", "lint", _gradle(r"ktlintCheck|lintKotlin\w*|check|build"), ("*.editorconfig",),
         ("org.jlleitschuh.gradle.ktlint", "org.jmailen.kotlinter")),
    Tool("detekt", "Kotlin", "lint", _gradle(r"detekt\w*|check|build"), ("detekt.yml", "detekt-config.yml"), ("io.gitlab.arturbosch.detekt", "dev.detekt")),
    Tool("spotless", "Kotlin", "format", _gradle(r"spotlessCheck|check|build"), (), ("com.diffplug.spotless",), note="未實測"),
    Tool("Android Lint", "Kotlin", "lint", _gradle(r"lint(?:Debug|Release|Vital\w*)?|check|build"), ("lint.xml",), ("com.android.application", "com.android.library")),
    Tool("kotlin compile", "Kotlin", "types", _gradle(r"assemble\w*|build|compile\w*|test\w*|check|lint\w*")
         ),
    Tool("gradle unit test", "Kotlin", "test", _gradle(r"test\w*|check|build")),
    Tool("android instrumented test", "Kotlin", "integration", _gradle(r"connected\w*AndroidTest|\w+AndroidTest"), ("*/src/androidTest/*",)),
    # Go – detection rules only, not exercised on a real repo
    Tool("gofmt", "Go", "format", _rx(r"\bgofmt\b|\bgofumpt\b"), needs_flag=(r"test\s+-z|\|\s*(tee|wc)|--?d\b.*exit|diff", "`gofmt -l` 只列檔不失敗，要接 `test -z`"), note="未實測"),
    Tool("golangci-lint", "Go", "lint", _rx(r"\bgolangci-lint\s+run\b"), (".golangci.yml", ".golangci.yaml", ".golangci.toml"), note="未實測"),
    Tool("go vet", "Go", "types", _rx(r"\bgo\s+(vet|build)\b|\bstaticcheck\b"), note="未實測"),
    Tool("go test", "Go", "test", _rx(r"\bgo\s+test\b"), note="未實測"),
    # Python – detection rules only
    Tool("ruff format", "Python", "format", _rx(r"\bruff\s+format\b|\bblack\b"), needs_flag=(r"--check|--diff", "沒帶 `--check`，只會改檔不會失敗"), note="未實測"),
    Tool("ruff/flake8", "Python", "lint", _rx(r"\bruff\s+check\b|\bruff\s+\.|\bflake8\b|\bpylint\b"), ("ruff.toml", ".ruff.toml", ".flake8"), note="未實測"),
    Tool("mypy/pyright", "Python", "types", _rx(r"\bmypy\b|\bpyright\b"), ("mypy.ini",), note="未實測"),
    Tool("pytest", "Python", "test", _rx(r"\bpytest\b|python3?\s+-m\s+(pytest|unittest)"), note="未實測"),
    # .NET – detection rules only
    Tool("dotnet format", ".NET", "format", _rx(r"\bdotnet\s+format\b"), needs_flag=(r"--verify-no-changes", "沒帶 `--verify-no-changes`，只會改檔不會失敗"), note="未實測"),
    Tool("dotnet build", ".NET", "types", _rx(r"\bdotnet\s+(build|test)\b"), note="未實測"),
    Tool("dotnet test", ".NET", "test", _rx(r"\bdotnet\s+test\b"), note="未實測"),
]
TOOL_LANG = {"JS/TS": ("TypeScript", "JavaScript")}
OTHER_CI_TOOLS = [("gitleaks", r"\bgitleaks\b"), ("semgrep", r"\bsemgrep\b"), ("actionlint", r"actionlint\b"),
                  ("shellcheck", r"\bshellcheck\b"), ("codeql", r"codeql")]


# --------------------------------------------------------------------------- detection helpers


def detect_languages(repo: Repo) -> dict[str, list[str]]:
    """Language -> manifest paths. Only languages with a manifest count toward the baseline."""
    langs: dict[str, list[str]] = {}

    def has(ext):
        return any(f.endswith(ext) for f in repo.files)

    pkgs = repo.glob("package.json")
    if pkgs:
        langs["TypeScript" if repo.glob("tsconfig.json") or has(".ts") else "JavaScript"] = pkgs[:3]
    if repo.glob("pubspec.yaml"):
        langs["Dart"] = repo.glob("pubspec.yaml")[:3]
    swift_manifest = repo.glob("Package.swift", "*.podspec") + sorted({f.split(".xcodeproj/")[0] + ".xcodeproj" for f in repo.files if ".xcodeproj/" in f})
    if swift_manifest and has(".swift"):
        langs["Swift"] = swift_manifest[:3]
    gradle = repo.glob("build.gradle", "build.gradle.kts")
    if gradle and (has(".kt") or has(".java")):
        langs["Kotlin"] = gradle[:3]
    if repo.glob("go.mod"):
        langs["Go"] = repo.glob("go.mod")[:3]
    if repo.glob("pyproject.toml", "setup.py", "setup.cfg", "requirements.txt"):
        langs["Python"] = repo.glob("pyproject.toml", "setup.py", "setup.cfg", "requirements.txt")[:3]
    if repo.glob("*.csproj", "*.sln", "*.fsproj"):
        langs[".NET"] = repo.glob("*.csproj", "*.sln", "*.fsproj")[:3]
    return langs


def tool_langs(tool: Tool) -> tuple:
    return TOOL_LANG.get(tool.lang, (tool.lang,))


def find_config(repo: Repo, tool: Tool) -> list[str]:
    hits = repo.glob(*tool.configs) if tool.configs else []
    deps = []
    if tool.deps:
        dep_files = repo.glob("package.json", "pubspec.yaml", "*.gradle", "*.gradle.kts", "libs.versions.toml")
        for f in dep_files:
            text = repo.read(f)
            for d in tool.deps:
                if re.search(rf"[\"'\s]{re.escape(d)}[\"'\s:]", text):
                    deps.append(repo.first_line(f, re.escape(d)))
                    break
    if tool.id == "ktlint" and not deps:
        return []  # .editorconfig alone does not mean ktlint
    if tool.id == "Android Lint" and not deps:
        return []
    return hits + deps


def gradle_plugin_applied(repo: Repo, plugin_ids: tuple) -> tuple[bool, str]:
    """Plugin declared in the version catalog but applied nowhere is the 'in deps, not running' illusion."""
    builds = repo.glob("*.gradle", "*.gradle.kts")
    aliases = {}
    for toml in repo.glob("libs.versions.toml"):
        for line in repo.read(toml).splitlines():
            m = re.match(r"\s*([\w-]+)\s*=\s*\{[^}]*id\s*=\s*\"([^\"]+)\"", line)
            if m and m.group(2) in plugin_ids:
                aliases[m.group(1)] = (toml, m.group(2))
    for b in builds:
        for i, line in enumerate(repo.read(b).splitlines(), 1):
            if "apply false" in line or "apply(false)" in line:
                continue
            for pid in plugin_ids:
                if re.search(rf"id\s*\(?\s*[\"']{re.escape(pid)}[\"']|apply\s*\(?\s*plugin\s*[:=]\s*[\"']{re.escape(pid)}[\"']|plugins\.apply\(\s*[\"']{re.escape(pid)}", line):
                    return True, f"{b}:{i} `{line.strip()[:100]}`"
            for alias in aliases:
                alias_rx = re.sub(r"[-_.]", "[-_.]", re.sub(r"[^\w.-]", "", alias))
                if re.search(rf"libs\.plugins\.{alias_rx}(?![\w.])", line):
                    return True, f"{b}:{i} `{line.strip()[:100]}`"
    if aliases:
        toml, pid = next(iter(aliases.values()))
        return False, f"{toml} 宣告了 `{pid}`，但沒有任何 build 檔套用"
    return False, ""


def gradle_flag(repo: Repo, pattern: str) -> str:
    for b in repo.glob("*.gradle", "*.gradle.kts", "lint.xml"):
        hit = repo.first_line(b, pattern)
        if hit != b:
            return hit
    return ""


# --------------------------------------------------------------------------- per-layer checks


NOISE_LINE = re.compile(r"^\s*(echo|printf|mkdir|unzip|tar|curl|wget|cp|mv|chmod|rm|ln|cat|test|\[|command\s+-v|which|brew\s+install|apt-get|sudo|local\s|export\s|#)")
INSTALL_CALL = re.compile(r"(^|[\s/])(install|download|setup|bootstrap)[-_][\w.-]*\.sh\b")
NOISE_CHAIN = re.compile(r"(^|/)(install|download|setup|bootstrap)[-_]")


def is_noise(inv: Invocation) -> bool:
    """Lines that only mention a tool (installing it, printing its name) are not runs of it."""
    return bool(NOISE_LINE.match(inv.text) or INSTALL_CALL.search(inv.text) or any(NOISE_CHAIN.search(c) for c in inv.chain[1:]))


def classify(tool: Tool, invs: list[Invocation], repo: Repo) -> list[tuple[str, Invocation, list[str]]]:
    """For every CI line that runs this tool: (status, invocation, reasons)."""
    res = []
    for inv in invs:
        if not tool.match(inv.text) or is_noise(inv):
            continue
        reasons = list(inv.gate) + list(inv.swallow)
        if not getattr(inv, "pipefail", True):
            m = re.search(r"(?<!\|)\|(?!\|)", inv.text)
            if m:
                reasons.append("管線沒有 pipefail，`| tee` 之類會吞掉前段的失敗")
        if tool.needs_flag and not re.search(tool.needs_flag[0], inv.text):
            reasons.append(tool.needs_flag[1])
        if reasons:
            res.append(("non-blocking", inv, reasons))
        elif inv.soft:
            res.append(("unknown", inv, list(inv.soft)))
        else:
            res.append(("blocking", inv, []))
    return res


def best(results, warn_rx: str = ""):
    def key(r):
        warned = bool(warn_rx) and not re.search(warn_rx, r[1].text)
        return (STATUS_ORDER.index(r[0]), warned)
    return sorted(results, key=key)[0] if results else None


def machine_rows(repo: Repo, invs: list[Invocation], langs: dict) -> tuple[list[Row], dict]:
    rows: list[Row] = []
    by_kind: dict[tuple[str, str], list[Row]] = {}
    for tool in TOOLS:
        if not any(l in langs for l in tool_langs(tool)):
            continue
        cfg = find_config(repo, tool)
        results = classify(tool, invs, repo)
        layer = {"structure": "結構", "test": "跑起來驗", "integration": "跑起來驗"}.get(tool.kind, "機器擋")
        lang = next(l for l in tool_langs(tool) if l in langs)
        ref = AGENT_RULES_REF.get(lang, "")
        note = "；".join(x for x in [tool.note, "未實測語言" if lang in UNTESTED_LANGS else ""] if x)
        # plugin-based Gradle tools: listed in the catalog but never applied
        if tool.id in ("ktlint", "detekt", "spotless", "Android Lint"):
            applied, where = gradle_plugin_applied(repo, tool.deps)
            if not applied:
                if where:
                    rows.append(Row(layer, f"{tool.id}（{lang}）", "inactive", where, "依賴或版本目錄有，但 plugin 沒套用，task 不存在"))
                continue
            cfg = [where] + [c for c in cfg if not c.startswith(where.split(":")[0])]
            # only count `check`/`build` as running this tool when a plugin is applied
        if not results and not cfg:
            continue
        chosen = best(results, tool.warn_flag[0] if tool.warn_flag else "")
        if chosen:
            status, inv, reasons = chosen
            evidence = inv.evidence()
            if len(results) > 1:
                evidence += f"（CI 共 {len(results)} 處呼叫）"
            detail = "；".join(dict.fromkeys(reasons))
            if status == "blocking":
                weak = [r for r in results if r[0] != "blocking"]
                if weak:
                    detail = f"另有 {len(weak)} 處呼叫不擋，例如 {weak[0][1].origin}：{weak[0][2][0] if weak[0][2] else weak[0][0]}"
            row = Row(layer, f"{tool.id}（{lang}）", status, evidence, "；".join(x for x in [detail, note] if x))
            if tool.id in ("ktlint", "detekt", "spotless") and re.search(r"(?<![\w-])(check|build)(?![\w-])", inv.text) and not re.search(r"ktlint|lintKotlin|detekt|spotless", inv.text):
                row.note = "；".join(x for x in [row.note, "經由 Gradle `check`／`build` 任務；plugin 是否掛在 check 上未逐一驗證"] if x)
            if tool.id in ("ktlint", "detekt"):
                ig = gradle_flag(repo, r"ignoreFailures\s*(=|\()\s*true")
                if ig:
                    row.status, row.note = "non-blocking", f"{ig}：ignoreFailures 讓違規不失敗"
            if tool.id == "Android Lint":
                ab = gradle_flag(repo, r"abortOnError\s*(=\s*)?false|abortOnError\s+false")
                if ab:
                    row.status, row.note = "non-blocking", f"{ab}：abortOnError false"
            rows.append(row)
            for kind in (tool.kind,) + ALSO_KINDS.get(tool.id, ()):
                by_kind.setdefault((kind, lang), []).append(row)
            if tool.id == "eslint":
                fmt = eslint_format_row(repo, row, cfg)
                if fmt:
                    rows.append(fmt)
                    by_kind.setdefault(("format", lang), []).append(fmt)
            # warning-only rules: a second row, so "blocking" never hides a warning-severity hole
            if row.status == "blocking":
                warn_reason = ""
                if tool.warn_flag and not re.search(tool.warn_flag[0], inv.text):
                    warn_reason = tool.warn_flag[1]
                    if tool.id == "eslint" and not any(re.search(r"[\"']warn[\"']|:\s*1\b", repo.read(c.split(":")[0])) for c in cfg if repo.exists(c.split(":")[0])):
                        warn_reason = ""
                if tool.id == "Android Lint" and not gradle_flag(repo, r"warningsAsErrors\s*(=\s*)?true|warningsAsErrors\s+true"):
                    warn_reason = "沒有 `warningsAsErrors = true`，warning 級 issue 不擋"
                if warn_reason:
                    rows.append(Row(layer, f"{tool.id} 的 warning 級規則（{lang}）", "non-blocking", inv.evidence(),
                                    "；".join(x for x in [warn_reason, f"逐條嚴重度見 {ref}" if ref else ""] if x)))
        else:
            row = Row(layer, f"{tool.id}（{lang}）", "local-only", "；".join(cfg[:3]), "；".join(x for x in ["CI 沒有呼叫", note] if x))
            rows.append(row)
            for kind in (tool.kind,) + ALSO_KINDS.get(tool.id, ()):
                by_kind.setdefault((kind, lang), []).append(row)
    rows.extend(dart_plugin_rows(repo, invs, langs))
    rows.extend(eslint_plugin_rows(repo, langs))
    return rows, by_kind


def dart_plugin_rows(repo: Repo, invs, langs) -> list[Row]:
    if "Dart" not in langs:
        return []
    rows = []
    for opts in repo.glob("analysis_options.yaml"):
        text = repo.read(opts)
        if re.search(r"^plugins:", text, re.M):
            runs_dart = any(re.search(r"\bdart\s+analyze\b", i.text) and not i.gate and not i.swallow for i in invs)
            if not runs_dart:
                rows.append(Row("機器擋", "analyzer plugin 規則（Dart）", "inactive", repo.first_line(opts, r"^plugins:"),
                                "頂層 `plugins:` 的規則只有 `dart analyze` 會報，`flutter analyze` 不跑（見 agent-rules/references/dart-flutter.md）；CI 沒有會擋的 `dart analyze`"))
    for pub in repo.glob("pubspec.yaml"):
        if re.search(r"^\s+custom_lint:", repo.read(pub), re.M):
            base = os.path.dirname(pub)
            opts = os.path.join(base, "analysis_options.yaml").lstrip("/")
            if "custom_lint" not in repo.read(opts):
                rows.append(Row("機器擋", "custom_lint（Dart）", "inactive", repo.first_line(pub, r"custom_lint:"),
                                f"{opts} 的 analyzer plugins 沒列 custom_lint"))
    return rows


def eslint_plugin_rows(repo: Repo, langs) -> list[Row]:
    if not ({"TypeScript", "JavaScript"} & set(langs)):
        return []
    configs = repo.glob("eslint.config.*", ".eslintrc", ".eslintrc.*")
    if not configs:
        return []
    cfg_text = "\n".join(repo.read(c) for c in configs)
    shared = re.search(r"""(?:from|require\()\s*['"]((?:@[^/'"]+/)?eslint-config[^'"]*)['"]""", cfg_text)
    rows = []
    for pkg_path in repo.glob("package.json")[:1]:
        try:
            pkg = json.loads(repo.read(pkg_path))
        except ValueError:
            continue
        deps = {**(pkg.get("dependencies") or {}), **(pkg.get("devDependencies") or {})}
        for name in deps:
            if re.match(r"^(eslint-plugin-|@[^/]+/eslint-plugin)", name) and name not in cfg_text:
                short_name = re.sub(r"^eslint-plugin-|/eslint-plugin.*$", "", name)
                if not re.search(rf"[\"'/]{re.escape(short_name)}[\"'/]|\b{re.escape(short_name)}\b", cfg_text):
                    if shared:
                        rows.append(Row("機器擋", f"ESLint plugin `{name}`", "unknown", repo.first_line(pkg_path, re.escape(name)),
                                        f"設定沒有直接引用，但載入了共用設定 `{shared.group(1)}`，可能由它載入；用 `eslint --print-config` 確認（agent-rules/references/typescript-eslint.md）"))
                    else:
                        rows.append(Row("機器擋", f"ESLint plugin `{name}`", "inactive", repo.first_line(pkg_path, re.escape(name)),
                                        "在依賴清單裡，但 ESLint 設定沒有引用（agent-rules/references/typescript-eslint.md）"))
    return rows


ALSO_KINDS = {"ktlint": ("format",), "spotless": ("lint",), "biome": ("format",), "dart/flutter analyze": ("types",),
              "playwright": ("test",), "cypress": ("test",), "flutter integration_test": ("test",), "android instrumented test": ("test",)}
ESLINT_FORMAT_RX = r"@antfu/eslint-config|@stylistic/|eslint-plugin-prettier|prettier/prettier|eslint-plugin-format|formatters\s*:"


def eslint_format_row(repo: Repo, eslint_row: Row, cfg: list[str]):
    """Formatting enforced through ESLint (stylistic rules, prettier plugin) counts as the formatter."""
    for c in repo.glob("eslint.config.*", ".eslintrc", ".eslintrc.*"):
        hit = repo.first_line(c, ESLINT_FORMAT_RX)
        if hit != c:
            if re.search(r"stylistic\s*:\s*false", repo.read(c)) and not re.search(r"@stylistic/|prettier|formatters\s*:\s*true", repo.read(c)):
                return None
            lang = eslint_row.check.split("（")[-1].rstrip("）")
            return Row("機器擋", f"格式化經由 ESLint（{lang}）", eslint_row.status, f"{hit}；執行見 eslint 那一列",
                       "格式規則跟著 eslint 的狀態；個別 stylistic 規則可能被關掉，用 `eslint --print-config` 確認（agent-rules/references/typescript-eslint.md）")
    return None


KIND_LABEL = {"format": "格式化", "lint": "lint", "types": "型別或靜態分析"}


def baseline_rows(by_kind: dict, langs: dict) -> list[Row]:
    rows = []
    for lang in langs:
        for kind in ("format", "lint", "types"):
            items = by_kind.get((kind, lang), [])
            if items:
                pick = sorted(items, key=lambda r: STATUS_ORDER.index(r.status))[0]
                rows.append(Row("機器擋", f"{KIND_LABEL[kind]}（{lang}）", pick.status, f"見 {pick.check} 那一列", "", baseline=True))
            else:
                note = "未實測語言；偵測規則可能不全" if lang in UNTESTED_LANGS else ""
                rows.append(Row("機器擋", f"{KIND_LABEL[kind]}（{lang}）", "absent",
                                f"CI 指令（含展開的 package scripts、Makefile、shell 腳本）與設定檔都沒有找到 {lang} 的{KIND_LABEL[kind]}工具", note, baseline=True))
    return rows


CUSTOM_CHECK = re.compile(r"(?:^|[\s/])((?:check|lint|verify|guard|scan)[-_][\w.-]+\.(?:sh|py|mjs|js|ts|rb))\b")


def custom_check_rows(invs: list[Invocation]) -> list[Row]:
    """Repo-specific gates (grep checks, index checks) the catalogue cannot name."""
    seen: dict[str, list[Invocation]] = {}
    for inv in invs:
        m = CUSTOM_CHECK.search(inv.text)
        if m and not is_noise(inv) and not re.match(r"^\s*(echo|printf|[\w-]+=)", inv.text):
            seen.setdefault(m.group(1), []).append(inv)
    rows = []
    for name, hits in sorted(seen.items()):
        good = [i for i in hits if not i.gate and not i.swallow]
        inv = (good or hits)[0]
        rows.append(Row("機器擋", f"自訂檢查 {name}", "blocking" if good else "non-blocking", inv.evidence(),
                        "；".join(dict.fromkeys(inv.gate + inv.swallow)) or "它守什麼要讀腳本；腳本自己會不會漏判不在本檢查範圍"))
    return rows


def hook_rows(repo: Repo) -> list[Row]:
    rows = []
    hook_files = repo.glob(".githooks/*", ".husky/*", ".pre-commit-config.yaml", "lefthook.yml", "lefthook.yaml", ".lefthook.yml")
    hook_files = [h for h in hook_files if not h.startswith(".husky/_/")]
    pkg_hooks = [p for p in repo.glob("package.json") if re.search(r"simple-git-hooks|\"husky\"", repo.read(p))]
    if not hook_files and not pkg_hooks:
        return [Row("機器擋", "pre-commit／pre-push hook", "absent", "找過 .githooks/、.husky/、.pre-commit-config.yaml、lefthook.yml、package.json 的 simple-git-hooks")]
    runs = []
    text = "\n".join(repo.read(h) for h in hook_files)
    for tool in TOOLS:
        if tool.kind in ("format", "lint", "types") and any(tool.match(l) for l in text.splitlines()):
            runs.append(tool.id)
    for name, rx in OTHER_CI_TOOLS:
        if re.search(rx, text):
            runs.append(name)
    install = ""
    if any(h.startswith(".githooks/") for h in hook_files):
        setters = [f for f in repo.files if f.endswith(("package.json", "Makefile", ".sh")) and "core.hooksPath" in repo.read(f) and "git config" in repo.read(f)]
        install = "；`.githooks/` 要每個 clone 自己跑 `git config core.hooksPath .githooks`" + ("" if not setters else f"，{setters[0]} 有設定指令")
    rows.append(Row("機器擋", "pre-commit／pre-push hook", "present", "；".join((hook_files + pkg_hooks)[:4]),
                    f"hook 內呼叫：{', '.join(runs) or '沒認出格式化／lint 工具'}{install}；hook 只在本機、可 `--no-verify` 跳過"))
    return rows


def other_ci_rows(invs: list[Invocation]) -> list[Row]:
    rows = []
    for name, rx in OTHER_CI_TOOLS:
        hits = [i for i in invs if re.search(rx, i.text) and not is_noise(i)]
        if not hits:
            continue
        good = [i for i in hits if not i.gate and not i.swallow]
        inv = (good or hits)[0]
        status = "blocking" if good else "non-blocking"
        rows.append(Row("機器擋", f"{name}（其他 CI 檢查）", status, inv.evidence(), "；".join(dict.fromkeys(inv.gate + inv.swallow))))
    return rows


TEST_GLOBS = {
    "TypeScript": ("*.test.ts", "*.test.tsx", "*.spec.ts", "*.spec.tsx", "*.test.js", "*.spec.js", "*.test.mjs"),
    "JavaScript": ("*.test.js", "*.spec.js", "*.test.mjs", "*.test.jsx"),
    "Dart": ("*_test.dart",),
    "Swift": ("*Tests.swift", "*Test.swift"),
    "Kotlin": ("*Test.kt", "*Tests.kt", "*Test.java"),
    "Go": ("*_test.go",),
    "Python": ("test_*.py", "*_test.py"),
    ".NET": ("*Tests.cs", "*Test.cs"),
}
MOCK_RX = re.compile(r"package:(mockito|mocktail)/|\b(jest|vi)\.mock\(|import io\.mockk|org\.mockito|unittest\.mock|from mock import|\bgomock\b|\bMoq\b|NSubstitute|Cuckoo")


def run_rows(repo: Repo, invs, langs, by_kind) -> list[Row]:
    rows = []
    for lang in langs:
        tests = [f for f in repo.glob(*TEST_GLOBS.get(lang, ())) if "/fixtures/" not in f]
        if lang in ("Kotlin",):
            tests = [f for f in tests if "/src/test" in f or "/src/androidTest" in f or "/src/sharedTest" in f] or tests
        note = "未實測語言" if lang in UNTESTED_LANGS else ""
        if tests:
            mocks = [f for f in tests if MOCK_RX.search(repo.read(f))]
            rows.append(Row("跑起來驗", f"測試檔（{lang}）", "present", f"{len(tests)} 個，例如 {tests[0]}", note))
            rows.append(Row("跑起來驗", f"測試是不是只測 mock（{lang}）", "unknown",
                            f"{len(mocks)}/{len(tests)} 個測試檔 import mock 函式庫" + (f"，例如 {mocks[0]}" if mocks else ""),
                            "要 AI 判讀：mock 只是線索，手寫 fake 也可能只測自己"))
        else:
            rows.append(Row("跑起來驗", f"測試檔（{lang}）", "absent", f"找過 {', '.join(TEST_GLOBS.get(lang, ()))}", note))
        test_rows = by_kind.get(("test", lang), [])
        if not test_rows:
            rows.append(Row("跑起來驗", f"測試進 CI（{lang}）", "absent", "CI 指令（含展開）沒有找到測試指令", note))
    for pkg in repo.glob("package.json")[:1]:
        try:
            scripts = json.loads(repo.read(pkg)).get("scripts") or {}
        except ValueError:
            scripts = {}
        chains = " ".join(" ".join(i.chain) for i in invs)
        for name in scripts:
            if re.match(r"^test(:|$)", name) and f"scripts.{name}" not in chains:
                rows.append(Row("跑起來驗", f"package script `{name}`", "local-only", f"{pkg} scripts.{name} `{short(scripts[name], 60)}`", "CI 沒有呼叫這個 script；是否已被別的 CI 指令涵蓋要人看"))
    # one-command start
    starts = []
    for pkg in repo.glob("package.json")[:1]:
        try:
            scripts = json.loads(repo.read(pkg)).get("scripts") or {}
        except ValueError:
            scripts = {}
        for k in ("dev", "start", "serve", "preview"):
            if k in scripts:
                starts.append(f"{pkg} scripts.{k} `{short(scripts[k], 50)}`")
                break
    for mk in repo.glob("Makefile", "justfile"):
        hit = repo.first_line(mk, r"^(run|dev|start|serve|up)\s*:")
        if hit != mk:
            starts.append(hit)
    starts += repo.glob("docker-compose.yml", "docker-compose.yaml", "compose.yaml", "Procfile")[:1]
    examples = sorted({f.split("/")[0] for f in repo.files if re.match(r"^(example|examples|Examples|sample|samples|demo)/", f)})
    if starts:
        rows.append(Row("跑起來驗", "一行啟動指令", "present", "；".join(starts[:3])))
    elif examples:
        rows.append(Row("跑起來驗", "一行啟動指令", "unknown", f"沒有 dev／start 指令；有範例 app 目錄 {', '.join(examples)}", "函式庫型 repo：能不能一行把範例跑起來要人看"))
    else:
        rows.append(Row("跑起來驗", "一行啟動指令", "absent", "找過 package.json scripts（dev／start／serve／preview）、Makefile／justfile 的 run／dev／start、docker-compose、Procfile、example 目錄"))
    # integration / driver presence when no CI row exists for it
    for lang in langs:
        if not by_kind.get(("integration", lang)):
            dirs = [f for f in repo.files if re.search(r"(^|/)(integration_test|e2e|UITests|[\w]+UITests|androidTest|\.maestro)/", f)]
            if dirs:
                rows.append(Row("跑起來驗", f"整合測試或驅動工具（{lang}）", "local-only", dirs[0], "有目錄，CI 指令沒有找到對應的執行"))
    return rows


RESIDENT = ("AGENTS.md", "CLAUDE.md", ".claude/CLAUDE.md", "GEMINI.md", ".cursorrules", ".github/copilot-instructions.md")


def text_rows(repo: Repo) -> list[Row]:
    rows = []
    found = []
    for rel in RESIDENT:
        path = repo.root / rel
        if path.is_file():
            size = path.stat().st_size
            link = f"（symlink → {os.readlink(path)}）" if path.is_symlink() else ""
            imports = re.findall(r"^@(\S+)", repo.read(rel), re.M)
            found.append(f"{rel} {size} bytes{link}" + (f"，@ 匯入 {', '.join(imports[:3])}" if imports else ""))
    if found:
        rows.append(Row("文字規則", "常駐檔", "present", "；".join(found)))
    else:
        rows.append(Row("文字規則", "常駐檔", "absent", f"找過 {', '.join(RESIDENT)}"))
    rows.append(Row("文字規則", "文字規則有沒有機器擋", "unknown", "—", "逐條分類交給 agent-rules skill（`agent-rules/SKILL.md` 第 2 步）"))
    return rows


AI_REVIEW = {
    ".gemini/config.yaml": "Gemini Code Assist", ".gemini/styleguide.md": "Gemini Code Assist",
    ".coderabbit.yaml": "CodeRabbit", ".coderabbit.yml": "CodeRabbit", ".github/copilot-instructions.md": "GitHub Copilot",
    ".cursor/BUGBOT.md": "Cursor Bugbot", "greptile.json": "Greptile", ".greptile.json": "Greptile",
}


def review_rows(repo: Repo, github: bool, protection: Row | None = None) -> list[Row]:
    rows = []
    tpl = repo.glob(".github/pull_request_template.md", ".github/PULL_REQUEST_TEMPLATE.md", ".github/PULL_REQUEST_TEMPLATE/*",
                    "docs/pull_request_template.md", "pull_request_template.md", ".gitlab/merge_request_templates/*")
    rows.append(Row("獨立審查", "PR 範本", "present" if tpl else "absent", "；".join(tpl[:2]) or "找過 .github/、docs/、根目錄的 pull_request_template 與 .gitlab/merge_request_templates/"))
    owners = repo.glob(".github/CODEOWNERS", "CODEOWNERS", "docs/CODEOWNERS")
    rows.append(Row("獨立審查", "CODEOWNERS", "present" if owners else "absent", owners[0] if owners else "找過 .github/、根目錄、docs/"))
    ai = [f"{rel}（{name}）" for rel, name in AI_REVIEW.items() if repo.exists(rel)]
    for wf in repo.glob(".github/workflows/*"):
        hit = repo.first_line(wf, r"anthropics/claude-code-action|coderabbitai/|openai/codex-action|google-github-actions/run-gemini")
        if hit != wf:
            ai.append(hit)
    rows.append(Row("獨立審查", "AI reviewer 設定", "present" if ai else "absent", "；".join(ai[:3]) or f"找過 {', '.join(AI_REVIEW)} 與 workflow 內的 review action",
                    "有設定不代表會擋 merge；reviewer 只留言時算建議" if ai else ""))
    rows.append(protection if protection is not None else branch_protection_row(repo) if github else
                Row("獨立審查", "分支保護與必要檢查", "unknown", "—", "本機檔案看不到；加 `--github` 用 gh api 唯讀查詢"))
    return rows


def _gh(args: list[str]):
    try:
        p = subprocess.run(["gh", "api", *args], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as e:
        return None, str(e)
    if p.returncode != 0:
        return None, (p.stdout + p.stderr).strip()[:160]
    try:
        return json.loads(p.stdout or "null"), ""
    except ValueError:
        return None, "非 JSON 回應"


def branch_protection_row(repo: Repo) -> Row:
    row, _ = branch_protection(repo)
    return row


def branch_protection(repo: Repo) -> tuple[Row, list[str]]:
    contexts: list[str] = []
    try:
        url = subprocess.run(["git", "-C", str(repo.root), "remote", "get-url", "origin"], capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return Row("獨立審查", "分支保護與必要檢查", "unknown", "沒有 origin remote"), contexts
    m = re.search(r"github\.com[:/]([^/]+)/([^/]+?)(?:\.git)?$", url)
    if not m:
        return Row("獨立審查", "分支保護與必要檢查", "unknown", "origin 不是 GitHub", ""), contexts
    slug = f"{m.group(1)}/{m.group(2)}"
    info, err = _gh([f"repos/{slug}"])
    if not info:
        return Row("獨立審查", "分支保護與必要檢查", "unknown", f"gh api repos/<origin>：{err}"), contexts
    branch = info.get("default_branch", "main")
    found = []
    prot, perr = _gh([f"repos/{slug}/branches/{branch}/protection"])
    if prot:
        checks = ((prot.get("required_status_checks") or {}).get("contexts")) or []
        contexts += checks
        reviews = (prot.get("required_pull_request_reviews") or {}).get("required_approving_review_count")
        found.append(f"branch protection：必要檢查 {checks or '無'}，必要 review 數 {reviews if reviews is not None else '未要求'}")
    rules, rerr = _gh([f"repos/{slug}/rules/branches/{branch}"])
    if isinstance(rules, list) and rules:
        types = []
        for r in rules:
            t = r.get("type")
            if t == "required_status_checks":
                ctx = [c.get("context") for c in (r.get("parameters") or {}).get("required_status_checks", [])]
                contexts += [c for c in ctx if c]
                types.append(f"required_status_checks {ctx}")
            elif t == "pull_request":
                types.append(f"pull_request（review 數 {(r.get('parameters') or {}).get('required_approving_review_count')}）")
            else:
                types.append(str(t))
        found.append(f"ruleset：{', '.join(types)}")
    if found:
        return Row("獨立審查", "分支保護與必要檢查", "present", f"`{branch}`：" + "；".join(found), "以 gh api 唯讀查詢"), contexts
    if "Not Found" in perr or "not protected" in perr.lower():
        return Row("獨立審查", "分支保護與必要檢查", "absent" if not rerr else "unknown", f"`{branch}`：{perr or rerr}", "以 gh api 唯讀查詢；branch protection 需要 admin 權限才讀得到，404 也可能是權限不足"), contexts
    return Row("獨立審查", "分支保護與必要檢查", "unknown", f"`{branch}`：{perr or rerr or '無規則回應'}", "以 gh api 唯讀查詢"), contexts


def structure_rows(repo: Repo, langs, by_kind, invs) -> list[Row]:
    rows = []
    arch_tests = [f for f in repo.files if re.search(r"(?i)(architecture|arch|layering|konsist|archunit)[\w-]*(test|spec)?\.(kt|java|ts|dart|swift|py|sh)$", f)
                  or re.search(r"(?i)check-?layer", f)]
    arch_lint = []
    for c in repo.glob("eslint.config.*", ".eslintrc", ".eslintrc.*"):
        hit = repo.first_line(c, r"no-restricted-(imports|paths)|import(-x)?/no-restricted-paths|boundaries/")
        if hit != c:
            arch_lint.append(hit)
    for g in repo.glob("*.gradle.kts", "*.gradle", "libs.versions.toml"):
        hit = repo.first_line(g, r"konsist|archunit")
        if hit != g:
            arch_lint.append(hit)
    has_struct = any(by_kind.get(("structure", l)) for l in langs)
    for f in arch_tests[:3]:
        name = os.path.basename(f)
        ran = [i for i in invs if name in i.text or f in " ".join(i.chain)]
        if ran:
            good = [i for i in ran if not i.gate and not i.swallow]
            inv = (good or ran)[0]
            rows.append(Row("結構", f"架構檢查 {name}", "blocking" if good else "non-blocking", inv.evidence(), "；".join(dict.fromkeys(inv.gate + inv.swallow))))
        else:
            rows.append(Row("結構", f"架構檢查 {name}", "unknown", f, "檔名像架構測試；是否隨一般測試指令執行要人看"))
    for hit in arch_lint[:3]:
        rows.append(Row("結構", "限制 import 方向的 lint 規則", "present", hit, "跟著所屬 lint 那一列的狀態"))
    if not arch_tests and not arch_lint and not has_struct:
        rows.append(Row("結構", "架構測試或 import 方向 lint", "absent",
                        "找過檔名含 architecture／layering／konsist／archunit 的測試與腳本、ESLint 的 no-restricted-imports／boundaries、dependency-cruiser、Gradle 的 Konsist／ArchUnit"))
    rows.append(Row("結構", "一件事是不是只有一種寫法", "unknown", "—", "要 AI 判斷"))
    return rows


def ci_presence_rows(repo: Repo, wf_files: list[str]) -> list[Row]:
    rows = []
    others = repo.glob("bitrise.yml", "codemagic.yaml", "azure-pipelines.yml", "Jenkinsfile", ".circleci/config.yml",
                       "bitbucket-pipelines.yml", ".travis.yml", ".buildkite/*", ".woodpecker.yml", ".drone.yml")
    if wf_files:
        rows.append(Row("機器擋", "CI 設定", "present", f"{len(wf_files)} 個 GitHub Actions workflow：{', '.join(os.path.basename(w) for w in wf_files[:8])}"))
    if repo.exists(".gitlab-ci.yml"):
        rows.append(Row("機器擋", "CI 設定", "present", ".gitlab-ci.yml", "GitLab CI 解析未實測"))
    for o in others:
        rows.append(Row("機器擋", "CI 設定", "unknown", o, "腳本不解析這種 CI；這個檔裡的指令沒有列入，相關列可能誤判為 local-only／absent"))
    if not rows:
        rows.append(Row("機器擋", "CI 設定", "absent", "找過 .github/workflows/、.gitlab-ci.yml、bitrise、codemagic、azure、Jenkinsfile、CircleCI、Bitbucket、Travis、Buildkite"))
    return rows


# --------------------------------------------------------------------------- main


def audit(root: Path, github: bool = False) -> dict:
    repo = Repo(root)
    langs = detect_languages(repo)
    gh_invs, wf_files, parse_notes = github_invocations(repo)
    protection = None
    if github:
        protection, contexts = branch_protection(repo)
        if contexts:
            apply_required(gh_invs, getattr(github_invocations, "parsed", {}), sorted(set(contexts)))
    invs = gh_invs + gitlab_invocations(repo)
    rows: list[Row] = []
    rows += ci_presence_rows(repo, wf_files) + parse_notes
    machine, by_kind = machine_rows(repo, invs, langs)
    rows += structure_rows(repo, langs, by_kind, invs)
    rows += baseline_rows(by_kind, langs)
    rows += [r for r in machine if r.layer == "機器擋"]
    rows += other_ci_rows(invs)
    rows += custom_check_rows(invs)
    rows += hook_rows(repo)
    rows += [r for r in machine if r.layer == "結構"]
    rows += [r for r in machine if r.layer == "跑起來驗"]
    rows += run_rows(repo, invs, langs, by_kind)
    rows += text_rows(repo)
    rows += review_rows(repo, github, protection)
    order = {l: i for i, l in enumerate(LAYERS)}
    rows.sort(key=lambda r: order.get(r.layer, 99))
    for r in rows:
        assert r.status in STATUSES, r
    return {
        "repo": str(root),
        "languages": {k: v for k, v in langs.items()},
        "agent_rules_refs": {k: AGENT_RULES_REF[k] for k in langs if k in AGENT_RULES_REF},
        "statuses": STATUSES,
        "rows": [asdict(r) for r in rows],
    }


def to_markdown(result: dict) -> str:
    out = [f"# 防線層稽核：{result['repo']}", ""]
    langs = result["languages"]
    out.append("偵測到的語言（有 manifest 才算）：" + ("、".join(f"{k}（{', '.join(v)}）" for k, v in langs.items()) or "無"))
    untested = [k for k in langs if k in UNTESTED_LANGS]
    if untested:
        out.append(f"未實測語言：{'、'.join(untested)}，偵測規則沒有在真實 repo 跑過。")
    if result["agent_rules_refs"]:
        out.append("逐條列出啟用中的 lint 規則：" + "、".join(f"{k} 見 `{v}`" for k, v in result["agent_rules_refs"].items()))
    out += ["", "狀態值：" + "；".join(f"`{k}` {v}" for k, v in result["statuses"].items()), ""]
    out += ["| 層 | 檢查項 | 狀態 | 證據 | 備註 |", "|---|---|---|---|---|"]
    for r in result["rows"]:
        check = ("【基本盤】" if r["baseline"] else "") + r["check"]
        cells = [r["layer"], check, f"`{r['status']}`", r["evidence"], r["note"]]
        out.append("| " + " | ".join(c.replace("|", "\\|").replace("\n", " ") for c in cells) + " |")
    gaps = [r for r in result["rows"] if r["baseline"] and r["status"] != "blocking"]
    out += ["", "基本盤（格式化、lint、型別或靜態分析進 CI 且會失敗）沒達到的：" + ("、".join(f"{g['check']}＝`{g['status']}`" for g in gaps) or "無")]
    return "\n".join(out) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="唯讀稽核一個 repo 各層防線有沒有在擋（不打分數）")
    ap.add_argument("--repo", required=True, help="目標 repo 路徑")
    ap.add_argument("--format", choices=("markdown", "json"), default="markdown")
    ap.add_argument("--github", action="store_true", help="另用 gh api 唯讀查分支保護與 ruleset")
    args = ap.parse_args(argv)
    root = Path(args.repo).resolve()
    if not root.is_dir():
        print(f"layer_audit: not a directory: {root}", file=sys.stderr)
        return 2
    result = audit(root, github=args.github)
    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(to_markdown(result), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
