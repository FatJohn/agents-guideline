#!/usr/bin/env python3
"""Mechanical checks for the writing-principles skill.

Scans the Markdown files of one repository and reports, per principle, the lines
that break a machine-checkable rule (see SKILL.md, section "原則與判定").
Pure standard library; no ripgrep needed.

Usage:
    check_docs.py [--repo DIR] [--config FILE] [--exclude GLOB ...] [FILE ...]

Exit code: 0 no FAIL item, 1 at least one FAIL item, 2 usage or environment error.
"""

from __future__ import annotations

import argparse
import fnmatch
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional, Tuple
from urllib.parse import unquote

DEFAULT_TYPES = ("接入指南", "參考", "說明", "流程", "規則", "入口")
GUIDE_TYPE = "接入指南"
EXPLAIN_TYPE = "說明"

HISTORY_WORDS = r"原本|後來改成|後來改為|之前是|舊版|曾經|已改為|改版前|不再支援|取代了"
TIME_WORDS = r"目前|現在|最新|最近|即將|未來|之後會|將會|預計|規劃中|待實作|暫時|新增的|全新"
# Compounds that contain a trigger word but are ordinary prose (e.g. 出現在), stripped before the
# p2／p3 match. Off by default: a project opts in through IGNORE_WORDS in its config file.
IGNORE_WORDS = ""
ALLOW_MARKER = "<!-- allow-time-word -->"
GUIDE_BAD_H2 = ("設計", "架構", "為什麼", "決策", "取捨")
COPY_PREFIX = "> 本文件為副本"
COPY_LINE_RE = re.compile(
    r"^> 本文件為副本，權威版：\[[^\]]+\]\([^)]+\)。副本同步日：\d{4}-\d{2}-\d{2}。$"
)

# Ticket-like tokens that are not tickets.  Only used with the generic pattern.
NON_TICKET_PREFIXES = frozenset(
    "ISO RFC SHA UTF CVE IEEE TLS SSL HTTP AES UTC GMT ECMA OAUTH PKCE ES EN DIN BS X "
    "ID API URL UUID GUID USB HDMI PCI MD".split()
)
# ASCII-aware boundaries: Python's \b treats CJK as word characters, so "見PROJ-7" would not match.
DEFAULT_TICKET_RE = re.compile(r"(?<![A-Za-z0-9])[A-Z][A-Z0-9]{1,9}-[0-9]+(?![A-Za-z0-9])")
COMMIT_LINK_RE = re.compile(r"commit/[0-9a-f]{7,}|blob/[0-9a-f]{7,40}")
HEX_RE = re.compile(r"(?<![0-9A-Za-z])[0-9a-f]{7,40}(?![0-9A-Za-z])")

GUIDE_PHRASE_RE = re.compile(r"同上|如前述|請參考|見〈")
GUIDE_EXEMPT_H2_RE = re.compile(r"參考|下一步|延伸閱讀|相關文件|Next")

UNRELEASED_HIT_RE = re.compile(
    r"尚未發版|尚未發佈|未發佈|未發版|僅 main|(?i:only on main|unreleased)|未釋出"
)

EVIDENCE_TRIGGER_RE = re.compile(
    r"實測|驗證過|已測|測過|有測|未測|沒測|應該可以|理論上|預期可|未驗(?!簽)|推論"
)
EVIDENCE_OK_TESTED_RE = re.compile(r"已實測（\d{4}-\d{2}-\d{2}，[^）]+）")
EVIDENCE_OK_UNTESTED = "未實測"

VAGUE_LINK_RE = re.compile(r"(請見|詳見|見)(這裡|此處|本文件|該文件)|點此|這份文件|(?i:click here)")
LINE_ANCHOR_RE = re.compile(r"#L[0-9]+")

FENCE_RE = re.compile(r"^(\s*)(`{3,}|~{3,})(.*)$")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
LIST_RE = re.compile(r"^\s*([-*+]|\d+[.)])\s+")
THEMATIC_BREAK_RE = re.compile(r"^\s{0,3}([-*_])(\s*\1){2,}\s*$")
CODE_SPAN_RE = re.compile(r"(?<!`)(`+)(?!`)(.*?[^`])?\1(?!`)")
LINK_RE = re.compile(r"\[([^\]]*)\]\(\s*([^)\s]+)(?:\s+(?:\"[^\"]*\"|'[^']*'))?\s*\)")
TABLE_SEP_CELL_RE = re.compile(r"^:?-{1,}:?$")

# Reference limits for the p6 hints (hints only; never counted as FAIL).
P6_MAX_PARAGRAPH_SENTENCES = 5
P6_MAX_PARAGRAPH_CHARS = 220
P6_MAX_SENTENCE_CHARS = 80
P6_MAX_CELL_CHARS = 60

CONFIG_KEYS = (
    "TYPES",
    "NO_HEADER",
    "TICKET_RE",
    "UNRELEASED_PHRASE",
    "DOC_HOST_RE",
    "EXCLUDE",
    "HISTORY_WORDS",
    "TIME_WORDS",
    "IGNORE_WORDS",
)

HARD_IDS = (
    "p1", "p1b", "p2", "p3", "p3-allow", "p4t", "p4c", "p5", "p7", "p7a",
    "p8", "p9a", "p9b", "p9c", "p11", "p12",
)
HINT_IDS = ("p4h", "p6")
TITLES = {
    "p1": "p1 文件分型：檔頭（讀者／型別）缺漏",
    "p1b": "p1b 文件分型：標題與型別不符",
    "p2": "p2 正文只寫現況：歷史用語",
    "p3": "p3 不用時間性與承諾性用語",
    "p4t": "p4t 正文不放票號",
    "p4c": "p4c 正文不放 commit／blob 連結",
    "p5": "p5 接入指南步驟區不得依賴別份文件",
    "p7": "p7 未發版行為未用固定字樣",
    "p7a": "p7a 未發版 (a) 型位置不符",
    "p8": "p8 證據等級未用兩個固定值",
    "p9a": "p9a 含糊連結字",
    "p9b": "p9b 行號錨點",
    "p9c": "p9c 內部連結或 anchor 不存在",
    "p11": "p11 副本頁首格式",
    "p12": "p12 單一項目清單",
}


class Heading(NamedTuple):
    level: int
    text: str
    line: int  # 1-based
    slug: str


def slugify(text: str) -> str:
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text).replace("`", "")
    return re.sub(r"[^\w\- ]", "", text.strip().lower()).replace(" ", "-")


class Doc:
    """One Markdown file, parsed once: lines, fence state, headings."""

    def __init__(self, rel: str, text: str):
        self.rel = rel
        self.lines: List[str] = text.lstrip("﻿").splitlines()
        n = len(self.lines)
        self.in_fence = [False] * n
        self.fence_indent: Dict[int, int] = {}  # first line index of a fence region -> indent
        self.headings: List[Heading] = []
        self.doc_type: Optional[str] = None
        self._parse_fences()
        self._parse_headings()

    def _parse_fences(self) -> None:
        open_char = ""
        open_len = 0
        for i, line in enumerate(self.lines):
            m = FENCE_RE.match(line)
            if not open_char:
                if not m:
                    continue
                fence, info = m.group(2), m.group(3)
                if fence[0] == "`" and "`" in info:
                    continue  # inline code that merely starts with backticks
                open_char, open_len = fence[0], len(fence)
                self.in_fence[i] = True
                self.fence_indent[i] = len(m.group(1))
            else:
                self.in_fence[i] = True
                if (
                    m
                    and m.group(2)[0] == open_char
                    and len(m.group(2)) >= open_len
                    and not m.group(3).strip()
                ):
                    open_char = ""

    def _parse_headings(self) -> None:
        seen: Dict[str, int] = {}
        for i, line in enumerate(self.lines):
            if self.in_fence[i]:
                continue
            m = HEADING_RE.match(line)
            if not m:
                continue
            text = re.sub(r"\s+#+\s*$", "", m.group(2))
            slug = slugify(text)
            count = seen.get(slug, 0)
            seen[slug] = count + 1
            self.headings.append(
                Heading(len(m.group(1)), text, i + 1, slug if count == 0 else f"{slug}-{count}")
            )

    def anchors(self) -> frozenset:
        return frozenset(h.slug for h in self.headings)

    def links(self, index: int) -> List[Tuple[str, str]]:
        """(text, target) of the inline links on one line (callers skip fence lines)."""
        return [(m.group(1), m.group(2)) for m in LINK_RE.finditer(CODE_SPAN_RE.sub("", self.lines[index]))]


def read_doc(path: Path, rel: str) -> Optional[Doc]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    return Doc(rel, text)


class Settings:
    def __init__(self) -> None:
        self.types: List[str] = list(DEFAULT_TYPES)
        self.no_header: List[str] = []
        self.ticket_re: Optional["re.Pattern[str]"] = None
        self.unreleased_phrase: str = ""
        self.doc_host_re: Optional["re.Pattern[str]"] = None
        self.excludes: List[str] = []
        self.history_re = re.compile(HISTORY_WORDS)
        self.time_re = re.compile(TIME_WORDS)
        self.ignore_re: Optional["re.Pattern[str]"] = re.compile(IGNORE_WORDS) if IGNORE_WORDS else None
        self.overrides: List[str] = []
        self.config_path: str = ""
        self.headerless = False

    @property
    def types_re(self) -> "re.Pattern[str]":
        alternatives = "|".join(re.escape(t) for t in self.types)
        return re.compile(rf"^型別：({alternatives})\s*$")


def load_config(path: Path) -> Dict[str, str]:
    config: Dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key not in CONFIG_KEYS:
            print(f"警告：{path} 有未知的設定鍵 {key}（已忽略）", file=sys.stderr)
            continue
        config[key] = value.strip()
    return config


def compile_regex(label: str, pattern: str) -> "re.Pattern[str]":
    try:
        return re.compile(pattern)
    except re.error as exc:
        raise ValueError(f"{label} 不是合法的 regex：{exc}") from exc


def build_settings(config: Dict[str, str], args: argparse.Namespace) -> Settings:
    s = Settings()
    s.headerless = args.headerless
    # List-like keys: config and CLI values are merged.  Scalars: CLI wins over config.
    extra_types = [t for t in (config.get("TYPES", "") + "|" + (args.types or "")).split("|") if t.strip()]
    s.types.extend(t.strip() for t in extra_types if t.strip() not in s.types)
    s.no_header = config.get("NO_HEADER", "").split()
    for item in args.no_header or []:
        s.no_header.extend(item.split())
    s.excludes = config.get("EXCLUDE", "").split() + list(args.exclude or [])
    ticket = args.ticket_re if args.ticket_re is not None else config.get("TICKET_RE", "")
    if ticket:
        s.ticket_re = compile_regex("TICKET_RE", ticket)
    phrase = args.unreleased_phrase if args.unreleased_phrase is not None else config.get("UNRELEASED_PHRASE", "")
    s.unreleased_phrase = phrase
    host = args.doc_host_re if args.doc_host_re is not None else config.get("DOC_HOST_RE", "")
    if host:
        s.doc_host_re = compile_regex("DOC_HOST_RE", host)
    if config.get("HISTORY_WORDS"):
        s.history_re = compile_regex("HISTORY_WORDS", config["HISTORY_WORDS"])
    if config.get("TIME_WORDS"):
        s.time_re = compile_regex("TIME_WORDS", config["TIME_WORDS"])
    if "IGNORE_WORDS" in config:
        s.ignore_re = compile_ignore_words(config["IGNORE_WORDS"], s)
    s.overrides = [k for k in ("HISTORY_WORDS", "TIME_WORDS", "IGNORE_WORDS") if config.get(k)]
    return s


def compile_ignore_words(value: str, s: Settings) -> Optional["re.Pattern[str]"]:
    """IGNORE_WORDS is a `|`-separated list of literal compounds, not a regex.

    Every entry must contain a p2／p3 trigger word and be longer than it; otherwise
    an entry such as `.`、`前` or `目前` would silently blank the whole check.
    """
    words = [w.strip() for w in value.split("|") if w.strip()]
    if not words:
        return None
    for w in words:
        hit = s.time_re.search(w) or s.history_re.search(w)
        if not hit or hit.group(0) == w:
            raise ValueError(
                f"IGNORE_WORDS 的「{w}」不是含觸發詞的複合詞（每項必須含 TIME_WORDS／HISTORY_WORDS 的某個詞且比它長）"
            )
    return re.compile("|".join(re.escape(w) for w in sorted(words, key=len, reverse=True)))


# ---------------------------------------------------------------- scope


def git_tracked_markdown(repo: Path) -> Optional[List[str]]:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), "ls-files", "-z", "--", "*.md"],
            capture_output=True,
            check=False,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    names = [n for n in result.stdout.decode("utf-8", "replace").split("\0") if n]
    return [n for n in names if (repo / n).is_file()]


def walk_markdown(repo: Path) -> List[str]:
    found = []
    for path in repo.rglob("*.md"):
        rel = path.relative_to(repo)
        if ".git" in rel.parts or "node_modules" in rel.parts or not path.is_file():
            continue
        found.append(rel.as_posix())
    return found


def default_scope(repo: Path) -> List[str]:
    """Tracked *.md files; a non-git directory or one with nothing tracked is walked instead."""
    names = git_tracked_markdown(repo)
    if not names:
        names = walk_markdown(repo)
    kept = [n for n in names if "changelog" not in n.lower() and not n.startswith("docs/adr/")]
    return sorted(set(kept))


def apply_excludes(names: List[str], globs: List[str]) -> List[str]:
    cleaned = [g[2:] if g.startswith("./") else g for g in globs]
    return [n for n in names if not any(fnmatch.fnmatchcase(n, g) for g in cleaned)]


def resolve_explicit(repo: Path, files: List[str]) -> List[Tuple[str, Path]]:
    resolved = []
    for name in files:
        path = Path(name)
        if not path.is_file() and not path.is_absolute() and (repo / name).is_file():
            path = repo / name
        if not path.is_file():
            raise FileNotFoundError(f"找不到檔案：{name}")
        path = path.resolve()
        try:
            rel = path.relative_to(repo).as_posix()
        except ValueError:
            rel = path.as_posix()
        resolved.append((rel, path))
    return resolved


# ---------------------------------------------------------------- checks


class Report:
    def __init__(self) -> None:
        self.hits: Dict[str, List[Tuple[str, int, str]]] = {k: [] for k in HARD_IDS + HINT_IDS}

    def add(self, key: str, rel: str, line: int, text: str) -> None:
        self.hits[key].append((rel, line, text))

    def count(self, key: str) -> int:
        return len(self.hits[key])


def show(line: str) -> str:
    text = line.strip()
    return text if len(text) <= 160 else text[:160] + "…"


def check_header(doc: Doc, s: Settings, report: Report, exempt: bool) -> None:
    lines = doc.lines
    start = 0
    heading_line = 1
    problem: Optional[Tuple[int, str]] = None
    if not s.headerless:
        h1 = next((h for h in doc.headings if h.level == 1), None)
        if h1 is None:
            problem = (1, "沒有 `# ` 標題，無法定位檔頭")
        else:
            start = h1.line
            heading_line = h1.line
    nonempty = [(i, l) for i, l in enumerate(lines[start:], start) if l.strip()] if problem is None else []
    if nonempty and nonempty[0][1].startswith(COPY_PREFIX):
        nonempty = nonempty[1:]
    if problem is None:
        if not nonempty or not re.match(r"^讀者：\S", nonempty[0][1]):
            offender = nonempty[0] if nonempty else None
            problem = (offender[0] + 1 if offender else heading_line, "標題之下第 1 個非空行不是 `讀者：…`")
        elif len(nonempty) < 2 or not s.types_re.match(nonempty[1][1]):
            offender = nonempty[1] if len(nonempty) > 1 else None
            problem = (
                offender[0] + 1 if offender else nonempty[0][0] + 1,
                "標題之下第 2 個非空行不是 `型別：<" + "|".join(s.types) + ">`",
            )
    if len(nonempty) >= 2:
        m = s.types_re.match(nonempty[1][1])
        if m:
            doc.doc_type = m.group(1)
    if problem is not None and not exempt:
        report.add("p1", doc.rel, problem[0], problem[1])


def check_heading_vs_type(doc: Doc, report: Report) -> None:
    for h in doc.headings:
        if doc.doc_type == GUIDE_TYPE and h.level == 2 and any(w in h.text for w in GUIDE_BAD_H2):
            report.add("p1b", doc.rel, h.line, f"接入指南的 H2 含設計類字眼：{h.text}")
        if doc.doc_type == EXPLAIN_TYPE and h.level in (2, 3) and "步驟" in h.text:
            report.add("p1b", doc.rel, h.line, f"說明的標題含「步驟」：{h.text}")


def check_line_patterns(doc: Doc, s: Settings, report: Report) -> None:
    phrase = s.unreleased_phrase
    for i, line in enumerate(doc.lines):
        n = i + 1
        scrubbed = s.ignore_re.sub("", line) if s.ignore_re else line
        if s.history_re.search(scrubbed):
            report.add("p2", doc.rel, n, show(line))
        if ALLOW_MARKER in line:
            report.add("p3-allow", doc.rel, n, show(line))
        elif s.time_re.search(scrubbed):
            report.add("p3", doc.rel, n, show(line))
        if not line.startswith(COPY_PREFIX):
            if ticket_in(line, s):
                report.add("p4t", doc.rel, n, show(line))
            if COMMIT_LINK_RE.search(line):
                report.add("p4c", doc.rel, n, show(line))
            if HEX_RE.search(line):
                report.add("p4h", doc.rel, n, show(line))
        if UNRELEASED_HIT_RE.search(line):
            if not phrase:
                report.add("p7", doc.rel, n, show(line) + "  （未設定 UNRELEASED_PHRASE）")
            elif not unreleased_ok(line, phrase):
                report.add("p7", doc.rel, n, show(line))
        if not line.startswith("#") and EVIDENCE_TRIGGER_RE.search(line):
            rest = EVIDENCE_OK_TESTED_RE.sub("", line).replace(EVIDENCE_OK_UNTESTED, "")
            if EVIDENCE_TRIGGER_RE.search(rest):
                report.add("p8", doc.rel, n, show(line))
        if VAGUE_LINK_RE.search(line):
            report.add("p9a", doc.rel, n, show(line))
        if LINE_ANCHOR_RE.search(line):
            report.add("p9b", doc.rel, n, show(line))


def ticket_in(line: str, s: Settings) -> bool:
    if s.ticket_re is not None:
        return bool(s.ticket_re.search(line))
    return any(
        m.group(0).rsplit("-", 1)[0] not in NON_TICKET_PREFIXES
        for m in DEFAULT_TICKET_RE.finditer(line)
    )


def unreleased_ok(line: str, phrase: str) -> bool:
    return line.strip() == f"> {phrase}。" or f"（{phrase}）" in line or f"// {phrase}" in line


def check_unreleased_placement(doc: Doc, s: Settings, report: Report) -> None:
    phrase = s.unreleased_phrase
    if not phrase:
        return
    blockquote = f"> {phrase}。"
    heading_idx = {h.line - 1 for h in doc.headings if h.level in (2, 3)}
    for i, line in enumerate(doc.lines):
        if doc.in_fence[i] or line.strip() != blockquote:
            continue
        placed = i >= 2 and not doc.lines[i - 1].strip() and (i - 2) in heading_idx
        if not placed:
            report.add("p7a", doc.rel, i + 1, "(a) 型字樣沒有緊接在 H2／H3 之後（標題、一個空行、該行）")


def is_internal_doc_link(target: str, s: Settings) -> bool:
    t = target.strip("<>")
    if s.doc_host_re is not None and s.doc_host_re.search(t):
        return True
    if "://" in t or t.startswith(("#", "mailto:")):
        return False
    return t.split("#", 1)[0].split("?", 1)[0].lower().endswith(".md")


def check_guide_steps(doc: Doc, s: Settings, report: Report) -> None:
    if doc.doc_type != GUIDE_TYPE:
        return
    h2s = [h for h in doc.headings if h.level == 2]
    for idx, h in enumerate(h2s):
        if GUIDE_EXEMPT_H2_RE.search(h.text):
            continue
        end = h2s[idx + 1].line - 1 if idx + 1 < len(h2s) else len(doc.lines)
        for i in range(h.line, end):
            if doc.in_fence[i]:
                continue
            line = doc.lines[i]
            if GUIDE_PHRASE_RE.search(line):
                report.add("p5", doc.rel, i + 1, show(line))
            for _text, target in doc.links(i):
                if is_internal_doc_link(target, s):
                    report.add("p5", doc.rel, i + 1, "步驟區內有指向別份文件的連結：" + target)


class LinkChecker:
    def __init__(self, repo: Path) -> None:
        self.repo = repo
        self._anchors: Dict[Path, frozenset] = {}

    def anchors_of(self, path: Path, doc: Optional[Doc] = None) -> frozenset:
        if path not in self._anchors:
            parsed = doc if doc is not None else read_doc(path, path.name)
            self._anchors[path] = parsed.anchors() if parsed is not None else frozenset()
        return self._anchors[path]

    def problem(self, doc: Doc, doc_path: Path, target: str) -> Optional[str]:
        t = target.strip("<>")
        if "://" in t or t.startswith(("mailto:", "tel:", "data:")):
            return None
        raw_path, _, raw_anchor = t.partition("#")
        raw_path = unquote(raw_path.split("?", 1)[0])
        anchor = unquote(raw_anchor).lower()
        if raw_path:
            base = self.repo if raw_path.startswith("/") else doc_path.parent
            dest = Path(os.path.normpath(str(base / raw_path.lstrip("/"))))
            if not dest.exists():
                return "目標檔案不存在：" + raw_path
        else:
            dest = doc_path
        if anchor and dest.is_file() and dest.suffix.lower() == ".md":
            known = self.anchors_of(dest, doc if dest == doc_path else None)
            if anchor not in known:
                return "目標沒有對應標題的 anchor：#" + raw_anchor
        return None


def check_links(doc: Doc, doc_path: Path, checker: LinkChecker, report: Report) -> None:
    for i, _line in enumerate(doc.lines):
        if doc.in_fence[i]:
            continue
        for _text, target in doc.links(i):
            message = checker.problem(doc, doc_path, target)
            if message:
                report.add("p9c", doc.rel, i + 1, f"[{target}] {message}")


def check_copy_header(doc: Doc, s: Settings, report: Report) -> None:
    start = 0
    if not s.headerless:
        h1 = next((h for h in doc.headings if h.level == 1), None)
        if h1 is None:
            return
        start = h1.line
    for i in range(start, len(doc.lines)):
        line = doc.lines[i]
        if not line.strip():
            continue
        if line.startswith(COPY_PREFIX) and not COPY_LINE_RE.match(line.rstrip()):
            report.add("p11", doc.rel, i + 1, show(line))
        return


def check_lists(doc: Doc, report: Report) -> None:
    """Report lists that have exactly one item (nested items and loose lists count as one list)."""
    lines = doc.lines
    n = len(lines)
    count = 0
    first = -1
    kind = ""
    i = 0

    def close() -> None:
        nonlocal count, first, kind
        if count == 1:
            report.add("p12", doc.rel, first + 1, show(lines[first]))
        count, first, kind = 0, -1, ""

    while i < n:
        line = lines[i]
        if doc.in_fence[i]:
            j = i
            while j + 1 < n and doc.in_fence[j + 1] and (j + 1) not in doc.fence_indent:
                j += 1
            if not (count and doc.fence_indent.get(i, 0) > 0):
                close()  # an indented code block stays inside the open list item
            i = j + 1
            continue
        if not line.strip():
            pass  # a blank line only ends the list if the next non-blank line is neither item nor indented
        elif THEMATIC_BREAK_RE.match(line):
            close()  # `* * *` is a thematic break, not a list
        elif LIST_RE.match(line):
            marker = LIST_RE.match(line).group(1)
            this_kind = "ordered" if marker[0].isdigit() else "bullet"
            if count and line[0] not in " \t" and this_kind != kind:
                close()  # a top-level change of list type starts a new list (CommonMark)
            if not count:
                first, kind = i, this_kind
            count += 1
        elif not (count and line[0] in " \t"):
            close()
        i += 1
    close()


def sentences_of(text: str) -> List[str]:
    return [p.strip() for p in re.split(r"[。！？]", text) if p.strip()]


def visible_length(text: str) -> int:
    return len(re.sub(r"\]\([^)]*\)", "]", text))


def check_readability_hints(doc: Doc, report: Report) -> None:
    lines = doc.lines
    paragraph: List[Tuple[int, str]] = []

    def flush() -> None:
        if not paragraph:
            return
        first = paragraph[0][0] + 1
        text = " ".join(l.strip() for _, l in paragraph)
        sents = sentences_of(text)
        chars = visible_length(text)
        if len(sents) > P6_MAX_PARAGRAPH_SENTENCES or chars > P6_MAX_PARAGRAPH_CHARS:
            report.add("p6", doc.rel, first, f"段落 {len(sents)} 句／{chars} 字（參考上限 5 句／220 字）：{show(text)[:60]}…")
        for sent in sents:
            if visible_length(sent) > P6_MAX_SENTENCE_CHARS:
                report.add("p6", doc.rel, first, f"單句 {visible_length(sent)} 字（參考上限 80 字）：{sent[:60]}…")
        paragraph.clear()

    for i, line in enumerate(lines):
        stripped = line.strip()
        if doc.in_fence[i]:
            flush()
            continue
        if stripped.startswith("|"):
            flush()
            for cell in table_cells(stripped):
                if visible_length(cell) > P6_MAX_CELL_CHARS:
                    report.add("p6", doc.rel, i + 1, f"表格格 {visible_length(cell)} 字（參考上限 60 字）：{cell[:60]}…")
            continue
        is_text = (
            bool(stripped)
            and not HEADING_RE.match(line)
            and not LIST_RE.match(line)
            and not stripped.startswith((">", "<!--"))
            and line[0] not in " \t"
        )
        if is_text:
            paragraph.append((i, line))
        else:
            flush()
    flush()


def table_cells(row: str) -> List[str]:
    cells = [c.strip() for c in row.replace("\\|", "\0").strip("|").split("|")]
    cells = [c.replace("\0", "|") for c in cells]
    if cells and all(TABLE_SEP_CELL_RE.match(c) for c in cells if c):
        return []
    return cells


def scan_doc(doc: Doc, doc_path: Path, s: Settings, checker: LinkChecker, report: Report) -> None:
    exempt = any(fnmatch.fnmatchcase(doc.rel, pattern) for pattern in s.no_header)
    check_header(doc, s, report, exempt)
    check_heading_vs_type(doc, report)
    check_line_patterns(doc, s, report)
    check_unreleased_placement(doc, s, report)
    check_guide_steps(doc, s, report)
    check_links(doc, doc_path, checker, report)
    check_copy_header(doc, s, report)
    check_lists(doc, report)
    check_readability_hints(doc, report)


# ---------------------------------------------------------------- output


def render(report: Report, scanned: int, repo: Path, s: Settings) -> Tuple[str, bool]:
    out: List[str] = []
    extra = " ".join(s.excludes) if s.excludes else "無"
    out.append(f"掃描檔：{scanned} 個（repo={repo}；預設排除：changelog、docs/adr/；--exclude／EXCLUDE：{extra}）")
    overrides = "、".join(s.overrides) if s.overrides else "無"
    out.append(f"設定檔：{s.config_path or '無'}；詞表覆寫：{overrides}")
    for key in HARD_IDS:
        if key == "p3-allow" or not report.hits[key]:
            continue
        out.append(f"== {TITLES[key]}")
        for rel, line, text in report.hits[key]:
            out.append(f"{rel}:{line}: {text}")
    if report.hits["p3-allow"]:
        out.append("== p3-allow：行內 allow marker 使用清單（不計 FAIL；交付時逐檔給 verifier 看）")
        per_file: Dict[str, int] = {}
        for rel, line, text in report.hits["p3-allow"]:
            per_file[rel] = per_file.get(rel, 0) + 1
            out.append(f"{rel}:{line}: {text}")
        for rel, number in per_file.items():
            out.append(f"逐檔：{rel} = {number}")
    if report.hits["p4h"] or report.hits["p6"]:
        out.append("== 提示（不計入 FAIL）")
        for key, label in (("p4h", "p4h 7–40 位 hex 字串（只能是版本號、雜湊值範例或程式碼範例）"), ("p6", "p6 超過參考上限的位置")):
            if report.hits[key]:
                out.append(f"-- {label}")
                for rel, line, text in report.hits[key]:
                    out.append(f"{rel}:{line}: {text}")
    hard = " ".join(f"{k}={report.count(k)}" for k in HARD_IDS)
    hints = " ".join(f"{k}={report.count(k)}" for k in HINT_IDS)
    failed = any(report.count(k) for k in HARD_IDS if k != "p3-allow")
    out.append(f"SUMMARY {hard} | hints {hints}")
    out.append("RESULT FAIL" if failed else "RESULT PASS")
    return "\n".join(out) + "\n", failed


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="check_docs.py",
        description="writing-principles 的機械檢查：掃一個 repo 的 Markdown，逐原則列出命中。",
    )
    p.add_argument("files", nargs="*", metavar="FILE", help="只掃這些檔（不套預設排除）；省略則掃預設範圍")
    p.add_argument("--repo", default=".", help="目標 repo 目錄（預設 cwd）")
    p.add_argument("--config", help="設定檔路徑（預設 <repo>/.writing-principles.conf，不存在就略過）")
    p.add_argument("--exclude", action="append", metavar="GLOB", help="額外排除的路徑 glob（對相對路徑 fnmatch），可重複；每個都要在 PR 說明")
    p.add_argument("--ticket-re", help="票號 regex（覆寫設定 TICKET_RE）")
    p.add_argument("--unreleased-phrase", help="未發版固定字樣（覆寫設定 UNRELEASED_PHRASE）")
    p.add_argument("--types", help="額外文件型別，以 | 分隔（與設定 TYPES 合併）")
    p.add_argument("--no-header", action="append", metavar="PATHS", help="免檔頭的路徑，空白分隔，可重複（與設定 NO_HEADER 合併）")
    p.add_argument("--headerless", action="store_true", help="wiki 讀回檔：沒有 # 標題，檔頭取檔案最前兩個非空行")
    p.add_argument("--doc-host-re", help="視為『別份文件』的 wiki 網域 regex（覆寫設定 DOC_HOST_RE）")
    p.add_argument("--list", action="store_true", help="只印掃描範圍內的檔案後結束")
    return p


def main(argv: List[str]) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    args = build_parser().parse_args(argv)
    repo = Path(args.repo).resolve()
    if not repo.is_dir():
        print(f"錯誤：--repo 不是目錄：{args.repo}", file=sys.stderr)
        return 2
    try:
        config_path = Path(args.config) if args.config else repo / ".writing-principles.conf"
        if args.config and not config_path.is_file():
            raise FileNotFoundError(f"找不到設定檔：{args.config}")
        config = load_config(config_path) if config_path.is_file() else {}
        settings = build_settings(config, args)
        settings.config_path = str(config_path) if config_path.is_file() else ""
        if args.files:
            targets = resolve_explicit(repo, args.files)
        else:
            names = apply_excludes(default_scope(repo), settings.excludes)
            targets = [(n, repo / n) for n in names]
    except (ValueError, FileNotFoundError) as exc:
        print(f"錯誤：{exc}", file=sys.stderr)
        return 2
    if not targets:
        print("錯誤：掃描範圍內沒有任何 Markdown 檔（檢查 --repo、--exclude 與 EXCLUDE）", file=sys.stderr)
        return 2
    if args.list:
        for rel, _path in targets:
            print(rel)
        return 0
    report = Report()
    checker = LinkChecker(repo)
    for rel, path in targets:
        doc = read_doc(path, rel)
        if doc is None:
            print(f"錯誤：讀不到檔案：{path}", file=sys.stderr)
            return 2
        scan_doc(doc, path, settings, checker, report)
    text, failed = render(report, len(targets), repo, settings)
    sys.stdout.write(text)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
