#!/usr/bin/env python3
"""Block commits that put a private project name into this public repo.

`staged` (pre-commit) scans the path and content of every added, copied,
modified, renamed or type-changed file in the index; `message <file>`
(commit-msg) scans the commit message. The name list is kept outside the repo,
one string per line, matched case-insensitively; its path comes from
`git config privateNames.file`. When that is unset or the file is missing the
check passes with a one-line notice, because clones without the list must still
be able to commit. Output names list entries only by line number, never by text.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

TAG = "private-names"
CONFIG_KEY = "privateNames.file"
# `git commit -v` appends the diff below this line; git strips it before committing.
SCISSORS = "# ------------------------ >8 ------------------------"


class CheckError(Exception):
    pass


def git(*args: str) -> bytes:
    result = subprocess.run(["git", *args], capture_output=True)
    if result.returncode != 0:
        raise CheckError(f"git {' '.join(args)} failed: {result.stderr.decode('utf-8', 'replace').strip()}")
    return result.stdout


def list_path() -> Path | None:
    result = subprocess.run(["git", "config", "--path", "--get", CONFIG_KEY], capture_output=True)
    value = result.stdout.decode("utf-8", "replace").strip()
    if result.returncode != 0 or not value:
        print(f"{TAG}: {CONFIG_KEY} is not set; check skipped (see docs/install.md)", file=sys.stderr)
        return None
    path = Path(value)
    if not path.is_file():
        print(f"{TAG}: list file not found: {path}; check skipped", file=sys.stderr)
        return None
    return path


def load_names(path: Path) -> list[tuple[int, str]]:
    names = []
    try:
        text = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as error:
        raise CheckError(f"list file {path} is not UTF-8 ({error}); save it as UTF-8") from None
    for number, line in enumerate(text.splitlines(), 1):
        entry = line.strip()
        if entry and not entry.startswith("#"):
            names.append((number, entry.casefold()))
    return names


def hits(text: str, names: list[tuple[int, str]]) -> list[tuple[int, int]]:
    """(line number in text, line number of the matching list entry)."""
    found = []
    for line_no, line in enumerate(text.splitlines(), 1):
        folded = line.casefold()
        for entry_no, entry in names:
            if entry in folded:
                found.append((line_no, entry_no))
    return found


def masked(path: str, names: list[tuple[int, str]]) -> str:
    """The path with every matching entry replaced by its list line number."""
    out, folded = list(path), path.casefold()
    if len(folded) != len(path):  # casefold changed lengths, offsets would not line up
        return "<path hidden>"
    for entry_no, entry in names:
        start = folded.find(entry)
        while start != -1:
            out[start:start + len(entry)] = [f"<list entry {entry_no}>"] + [""] * (len(entry) - 1)
            start = folded.find(entry, start + len(entry))
    return "".join(out)


def staged_findings(names: list[tuple[int, str]]) -> list[str]:
    raw = git("diff", "--cached", "--raw", "-z", "--no-renames", "--diff-filter=ACMRT")
    fields = raw.split(b"\0")
    findings = []
    for meta, path_bytes in zip(fields[0::2], fields[1::2]):
        new_mode, new_sha = meta.split()[1], meta.split()[3]
        path = path_bytes.decode("utf-8", "replace")
        shown = masked(path, names)
        for _, entry_no in hits(path, names):
            findings.append(f"  {shown}: file path (list entry line {entry_no})")
        if new_mode == b"160000":  # submodule commit, no blob to read
            continue
        content = git("cat-file", "blob", new_sha.decode()).decode("utf-8", "replace")
        for line_no, entry_no in hits(content, names):
            findings.append(f"  {shown}:{line_no} (list entry line {entry_no})")
    return findings


def message_findings(message_file: str, names: list[tuple[int, str]]) -> list[str]:
    text = Path(message_file).read_text(encoding="utf-8", errors="replace")
    text = text.split("\n" + SCISSORS, 1)[0]
    return [f"  commit message line {line_no} (list entry line {entry_no})" for line_no, entry_no in hits(text, names)]


def main(argv: list[str]) -> int:
    if not argv or argv[0] not in {"staged", "message"} or (argv[0] == "message") != (len(argv) == 2):
        print(f"usage: {Path(sys.argv[0]).name} staged | message <file>", file=sys.stderr)
        return 2
    path = list_path()
    if path is None:
        return 0
    try:
        names = load_names(path)
        findings = staged_findings(names) if argv[0] == "staged" else message_findings(argv[1], names)
    except CheckError as error:
        print(f"{TAG}: commit blocked: {error}", file=sys.stderr)
        return 1
    if not findings:
        return 0
    what = "staged files contain" if argv[0] == "staged" else "the commit message contains"
    print(f"{TAG}: commit blocked: {what} a private project name from {path}", file=sys.stderr)
    print("\n".join(findings), file=sys.stderr)
    print(
        f"{TAG}: replace it with a codename (.claude/skills/maintain-guideline/SKILL.md §3), then commit again",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
