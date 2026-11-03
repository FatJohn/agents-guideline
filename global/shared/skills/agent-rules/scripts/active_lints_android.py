#!/usr/bin/env python3
"""Resolve the Android Lint issues a Gradle module actually has enabled.

Android Lint ships ~500 issues; about 40 are disabled by default and the CLI's
``--list`` does not say which.  ``lint --show`` (no ids) dumps every issue with a
``NOTE: This issue is disabled by default!`` line for those, so this script parses
that dump, then applies the module's own switches:

* ``lint.xml`` next to the module build file: ``<issue id="X" severity="ignore|…">``
* the Kotlin DSL ``lint { disable += setOf("A", "B"); enable += setOf("C"); checkOnly += … }``
  block in ``build.gradle.kts`` (also ``disable("A")`` / ``disable += "A"`` forms)

It is a static reading of the config, not a Gradle run: a ``lint {}`` block built from
variables, or a ``lint.xml`` placed elsewhere, is not seen, and the script says so.
Pure standard library.

Usage:
    active_lints_android.py --module <dir> [--lint <path to cmdline-tools/*/bin/lint>]
    active_lints_android.py --module <dir> --has HardcodedText StopShip
    active_lints_android.py --module <dir> --json
    active_lints_android.py --module <dir> --dump <saved output of lint --show>   # no lint binary needed

Exit code: 0; 1 when a --has issue is not enabled, the lint binary is missing, or the
dump cannot be parsed.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from xml.etree import ElementTree

ISSUE_HEAD_RE = re.compile(r"^([A-Za-z][A-Za-z0-9_.]*)\n-{3,}\n", re.M)
SEVERITY_RE = re.compile(r"^Severity: (\w+)", re.M)
DISABLED_RE = re.compile(r"^NOTE: This issue is disabled by default!", re.M)
QUOTED_RE = re.compile(r'"([A-Za-z][A-Za-z0-9_.]*)"')


def find_lint_binary(explicit: str | None) -> Path:
    if explicit:
        p = Path(explicit)
        if p.exists():
            return p
        raise SystemExit(f"找不到 lint：{explicit}")
    sdk = os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT") or str(Path.home() / "Library/Android/sdk")
    candidates = sorted(glob.glob(f"{sdk}/cmdline-tools/*/bin/lint"))
    if not candidates:
        raise SystemExit(f"找不到 cmdline-tools 的 lint（看過 {sdk}/cmdline-tools/*/bin/lint）；用 --lint 指定")
    return Path(candidates[-1])


def parse_show_dump(text: str) -> dict[str, dict]:
    """{issue id: {'severity': str, 'default_enabled': bool}} from ``lint --show``."""
    issues: dict[str, dict] = {}
    heads = list(ISSUE_HEAD_RE.finditer(text))
    for i, m in enumerate(heads):
        body = text[m.end(): heads[i + 1].start() if i + 1 < len(heads) else len(text)]
        sev = SEVERITY_RE.search(body)
        issues[m.group(1)] = {
            "severity": sev.group(1) if sev else "?",
            "default_enabled": DISABLED_RE.search(body) is None,
        }
    if not issues:
        raise SystemExit("lint --show 的輸出解析不到任何 issue；格式可能變了")
    return issues


def parse_gradle_lint_block(build_file: Path) -> dict[str, set[str]]:
    """Statically read disable／enable／checkOnly id sets from a ``lint { }`` block."""
    result = {"disable": set(), "enable": set(), "checkOnly": set()}
    if not build_file.exists():
        return result
    text = build_file.read_text(encoding="utf-8")
    m = re.search(r"\blint\s*\{", text)
    if not m:
        return result
    depth, i = 1, m.end()
    while i < len(text) and depth:
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        i += 1
    block = text[m.end(): i - 1]
    for key in result:
        for stmt in re.finditer(rf"\b{key}\b\s*(\+=|\()\s*(.*?)(\n|$)", block):
            result[key].update(QUOTED_RE.findall(stmt.group(2)))
    return result


def parse_lint_xml(path: Path) -> dict[str, str]:
    """{issue id: severity} from lint.xml; 'ignore' means disabled."""
    if not path.exists():
        return {}
    out: dict[str, str] = {}
    for issue in ElementTree.parse(path).getroot().iter("issue"):
        iid, sev = issue.get("id"), issue.get("severity")
        if iid and sev:
            out[iid] = sev
    return out


def resolve(module: Path, lint_bin: Path | None, dump_file: Path | None = None) -> dict:
    if dump_file is not None:
        text = dump_file.read_text(encoding="utf-8")
        source = str(dump_file)
    else:
        assert lint_bin is not None
        dump = subprocess.run([str(lint_bin), "--show"], capture_output=True, text=True, encoding="utf-8", check=False)
        if dump.returncode != 0 and not dump.stdout:
            raise SystemExit(f"{lint_bin} --show 失敗：{dump.stderr.strip()[:200]}")
        text, source = dump.stdout, str(lint_bin)
    issues = parse_show_dump(text)

    build_file = next((module / n for n in ("build.gradle.kts", "build.gradle") if (module / n).exists()), module / "build.gradle.kts")
    gradle = parse_gradle_lint_block(build_file)
    xml = parse_lint_xml(module / "lint.xml")

    enabled: dict[str, bool] = {iid: meta["default_enabled"] for iid, meta in issues.items()}
    for iid, sev in xml.items():
        if iid in enabled:
            enabled[iid] = sev != "ignore"
    for iid in gradle["enable"]:
        if iid in enabled:
            enabled[iid] = True
    for iid in gradle["disable"]:
        if iid in enabled:
            enabled[iid] = False
    if gradle["checkOnly"]:
        enabled = {iid: iid in gradle["checkOnly"] for iid in enabled}

    unknown = sorted((gradle["disable"] | gradle["enable"] | gradle["checkOnly"] | set(xml)) - set(issues))
    return {
        "lint": source,
        "module": str(module),
        "build_file": str(build_file) if build_file.exists() else None,
        "lint_xml": str(module / "lint.xml") if xml else None,
        "enabled": sorted(i for i, on in enabled.items() if on),
        "disabled_by_default_and_still_off": sorted(i for i, on in enabled.items() if not on and not issues[i]["default_enabled"]),
        "disabled_here": sorted(i for i, on in enabled.items() if not on and issues[i]["default_enabled"]),
        "enabled_here": sorted(i for i in gradle["enable"] if i in issues and not issues[i]["default_enabled"]),
        "unknown_ids_in_config": unknown,
        "total": len(issues),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--module", default=".", help="Gradle 模組目錄（含 build.gradle.kts，可有 lint.xml）")
    ap.add_argument("--lint", help="cmdline-tools 的 lint 可執行檔；預設在 $ANDROID_HOME 下找最新版")
    ap.add_argument("--dump", help="已存檔的 lint --show 輸出；給了就不呼叫 lint")
    ap.add_argument("--has", nargs="+", metavar="ISSUE")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    dump_file = Path(args.dump) if args.dump else None
    report = resolve(Path(args.module).resolve(), None if dump_file else find_lint_binary(args.lint), dump_file)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    if args.has:
        missing = []
        for iid in args.has:
            if iid in report["enabled"]:
                state = "enabled"
            elif iid in report["disabled_here"]:
                state = "disabled here"
            elif iid in report["disabled_by_default_and_still_off"]:
                state = "disabled by default"
            else:
                state = "not an issue id"
            if state != "enabled":
                missing.append(iid)
            print(f"{iid}\t{state}")
        return 1 if missing else 0
    print("\n".join(report["enabled"]))
    print(
        f"SUMMARY total={report['total']} enabled={len(report['enabled'])} "
        f"disabled_here={len(report['disabled_here'])} enabled_here={len(report['enabled_here'])} "
        f"default_off={len(report['disabled_by_default_and_still_off'])} unknown_ids={len(report['unknown_ids_in_config'])}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
