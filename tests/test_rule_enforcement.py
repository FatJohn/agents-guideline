"""Keep docs/rule-enforcement.md from going stale silently.

Fails when a source of rules gains an entry without a row in the table:
global/shared/rules/judgment.md (needs a row in the Claude part and in the Codex
part), global/claude/hooks/, the numbered 「邊界」 items of global/codex/AGENTS.md,
global/codex/rules/*.md and global/codex/agents/*.toml. Also fails when a row uses
a value outside the fixed set, or when a mechanical row points at a file or symbol
that does not exist.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
TABLE = REPO_ROOT / "docs" / "rule-enforcement.md"
JUDGMENT = REPO_ROOT / "global" / "shared" / "rules" / "judgment.md"
HOOKS = REPO_ROOT / "global" / "claude" / "hooks"
CODEX = REPO_ROOT / "global" / "codex"

VALUES = {"hook", "腳本", "測試", "設定", "verifier 合約", "注入文字", "按需文字"}
MECHANICAL = VALUES - {"注入文字", "按需文字"}

# Sections whose heading starts with this prefix describe the Codex side; every
# other section describes the Claude side.
CODEX_PREFIX = "Codex 端"


def table_rows() -> list[tuple[str, list[str]]]:
    """(section heading, cells) for every row of a four-column table
    (規則｜由什麼強制｜強制點｜備註), header and separator dropped."""
    rows = []
    section = ""
    for line in TABLE.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            section = line[3:].strip()
            continue
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 4 or cells[0] == "規則" or set(cells[0]) <= {"-"}:
            continue
        rows.append((section, cells))
    return rows


def judgment_keys() -> list[str]:
    entries = re.findall(r"^## (\d+)\. (.+?)\s*$", JUDGMENT.read_text(encoding="utf-8"), re.M)
    return [f"`global/shared/rules/judgment.md` {num}「{title}」" for num, title in entries]


class RuleEnforcementTableTests(unittest.TestCase):
    def setUp(self) -> None:
        self.sectioned = table_rows()
        self.rows = [cells for _, cells in self.sectioned]
        self.assertTrue(self.rows, "docs/rule-enforcement.md has no table rows")
        self.claude_rules = [c[0] for s, c in self.sectioned if not s.startswith(CODEX_PREFIX)]
        self.codex_rules = [c[0] for s, c in self.sectioned if s.startswith(CODEX_PREFIX)]

    def test_every_judgment_entry_has_a_row(self) -> None:
        keys = judgment_keys()
        self.assertTrue(keys, "no '## N. title' entries found in judgment.md")
        for key in keys:
            with self.subTest(entry=key):
                self.assertTrue(
                    any(key in r for r in self.claude_rules),
                    f"no Claude-side row for {key} in docs/rule-enforcement.md",
                )

    def test_every_judgment_entry_has_a_codex_row(self) -> None:
        keys = judgment_keys()
        self.assertTrue(keys, "no '## N. title' entries found in judgment.md")
        for key in keys:
            with self.subTest(entry=key):
                self.assertTrue(
                    any(key in r for r in self.codex_rules),
                    f"no row for {key} under a '## {CODEX_PREFIX}…' section",
                )

    def test_every_hook_has_a_row(self) -> None:
        hooks = sorted(p.name for p in HOOKS.iterdir() if p.is_file())
        self.assertTrue(hooks, "no hooks found")
        points = [r[2] for r in self.rows if r[1] == "hook"]
        for name in hooks:
            path = f"`global/claude/hooks/{name}`"
            with self.subTest(hook=name):
                self.assertTrue(any(p.startswith(path) for p in points), f"no hook row whose 強制點 is {path}")

    def test_every_codex_boundary_item_has_a_row(self) -> None:
        text = (CODEX / "AGENTS.md").read_text(encoding="utf-8")
        block = re.search(r"^## 邊界\s*$(.*?)^## ", text, re.M | re.S)
        self.assertIsNotNone(block, "no '## 邊界' section in global/codex/AGENTS.md")
        numbers = re.findall(r"^(\d+)\. ", block.group(1), re.M)
        self.assertTrue(numbers, "no numbered items under '## 邊界' in global/codex/AGENTS.md")
        for num in numbers:
            key = f"`global/codex/AGENTS.md`「邊界」{num}："
            with self.subTest(item=num):
                self.assertTrue(any(r.startswith(key) for r in self.codex_rules), f"no Codex row starting with {key}")

    def test_every_codex_rules_file_has_a_row(self) -> None:
        files = sorted(p.name for p in (CODEX / "rules").iterdir() if p.is_file())
        self.assertTrue(files, "no files in global/codex/rules")
        for name in files:
            key = f"`global/codex/rules/{name}`"
            with self.subTest(file=name):
                self.assertTrue(any(r.startswith(key) for r in self.codex_rules), f"no Codex row starting with {key}")

    def test_every_codex_agent_has_a_row(self) -> None:
        files = sorted(p.name for p in (CODEX / "agents").iterdir() if p.is_file())
        self.assertTrue(files, "no files in global/codex/agents")
        for name in files:
            key = f"`global/codex/agents/{name}`"
            with self.subTest(file=name):
                self.assertTrue(any(r.startswith(key) for r in self.codex_rules), f"no Codex row starting with {key}")

    def test_values_come_from_the_fixed_set(self) -> None:
        for rule, value, _, _ in self.rows:
            with self.subTest(rule=rule):
                self.assertIn(value, VALUES)

    def test_mechanical_rows_point_at_existing_symbols(self) -> None:
        for rule, value, point, _ in self.rows:
            if value not in MECHANICAL:
                continue
            with self.subTest(rule=rule):
                tokens = re.findall(r"`([^`]+)`", point)
                self.assertGreaterEqual(len(tokens), 2, f"強制點 needs a path and at least one symbol: {point}")
                target = REPO_ROOT / tokens[0]
                self.assertTrue(target.is_file(), f"missing file {tokens[0]}")
                text = target.read_text(encoding="utf-8")
                for symbol in tokens[1:]:
                    self.assertTrue(symbol in text, f"{symbol} not found in {tokens[0]}")


if __name__ == "__main__":
    unittest.main()
