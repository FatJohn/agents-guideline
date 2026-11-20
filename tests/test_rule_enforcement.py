"""Keep docs/rule-enforcement.md from going stale silently.

Fails when global/shared/rules/judgment.md gains an entry or global/claude/hooks/
gains a hook without a row in the table, when a row uses a value outside the fixed
set, or when a mechanical row points at a file or symbol that does not exist.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
TABLE = REPO_ROOT / "docs" / "rule-enforcement.md"
JUDGMENT = REPO_ROOT / "global" / "shared" / "rules" / "judgment.md"
HOOKS = REPO_ROOT / "global" / "claude" / "hooks"

VALUES = {"hook", "腳本", "測試", "設定", "verifier 合約", "注入文字", "按需文字"}
MECHANICAL = VALUES - {"注入文字", "按需文字"}


def table_rows() -> list[list[str]]:
    """Rows of every four-column table (規則｜由什麼強制｜強制點｜備註), header and separator dropped."""
    rows = []
    for line in TABLE.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 4 or cells[0] == "規則" or set(cells[0]) <= {"-"}:
            continue
        rows.append(cells)
    return rows


class RuleEnforcementTableTests(unittest.TestCase):
    def setUp(self) -> None:
        self.rows = table_rows()
        self.assertTrue(self.rows, "docs/rule-enforcement.md has no table rows")

    def test_every_judgment_entry_has_a_row(self) -> None:
        entries = re.findall(r"^## (\d+)\. (.+?)\s*$", JUDGMENT.read_text(encoding="utf-8"), re.M)
        self.assertTrue(entries, "no '## N. title' entries found in judgment.md")
        rules = [r[0] for r in self.rows]
        for num, title in entries:
            key = f"`global/shared/rules/judgment.md` {num}「{title}」"
            with self.subTest(entry=key):
                self.assertTrue(any(key in r for r in rules), f"no row for {key} in docs/rule-enforcement.md")

    def test_every_hook_has_a_row(self) -> None:
        hooks = sorted(p.name for p in HOOKS.iterdir() if p.is_file())
        self.assertTrue(hooks, "no hooks found")
        points = [r[2] for r in self.rows if r[1] == "hook"]
        for name in hooks:
            path = f"`global/claude/hooks/{name}`"
            with self.subTest(hook=name):
                self.assertTrue(any(p.startswith(path) for p in points), f"no hook row whose 強制點 is {path}")

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
