"""Guards for global/claude/settings.snippets.json.

The file holds only what docs/install.md tells the user to merge into
~/.claude/settings.json by hand.  These tests keep it valid JSON, keep every hook
command pointing at a hook script that exists in global/claude/hooks, and keep the
JSON blocks printed in docs/install.md identical to the snippets file.
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SNIPPETS = REPO_ROOT / "global" / "claude" / "settings.snippets.json"
HOOKS = REPO_ROOT / "global" / "claude" / "hooks"
INSTALL = REPO_ROOT / "docs" / "install.md"

HOOK_COMMAND = re.compile(r'^bash "\$HOME/\.claude/hooks/([A-Za-z0-9_.-]+\.sh)"$')


def snippets() -> dict:
    return json.loads(SNIPPETS.read_text(encoding="utf-8"))


def install_json_blocks() -> list:
    text = INSTALL.read_text(encoding="utf-8")
    return [json.loads(block) for block in re.findall(r"```json\n(.*?)```", text, re.S)]


class SettingsSnippetsTests(unittest.TestCase):
    def test_only_the_documented_settings_are_present(self) -> None:
        data = snippets()

        self.assertEqual(sorted(data), ["env", "hooks"])
        self.assertEqual(sorted(data["env"]), ["RIPGREP_CONFIG_PATH"])
        self.assertEqual(sorted(data["hooks"]), ["PreToolUse", "SessionStart"])
        self.assertEqual(data["hooks"]["PreToolUse"][0]["matcher"], "Edit|Write|MultiEdit|NotebookEdit")

    def test_every_hook_command_names_an_existing_script(self) -> None:
        commands = [
            hook["command"]
            for entries in snippets()["hooks"].values()
            for entry in entries
            for hook in entry["hooks"]
        ]

        self.assertEqual(len(commands), 2)
        for command in commands:
            match = HOOK_COMMAND.match(command)
            self.assertIsNotNone(match, command)
            self.assertTrue((HOOKS / match.group(1)).is_file(), command)

    def test_install_md_prints_the_same_json(self) -> None:
        data = snippets()
        blocks = install_json_blocks()

        self.assertIn({"env": data["env"]}, blocks)
        self.assertIn(data["hooks"]["SessionStart"][0], blocks)
        self.assertIn(data["hooks"]["PreToolUse"][0], blocks)


if __name__ == "__main__":
    unittest.main()
