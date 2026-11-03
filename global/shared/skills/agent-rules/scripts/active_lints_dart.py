#!/usr/bin/env python3
"""Resolve the lint rules a Dart / Flutter package actually has enabled.

Follows the ``include:`` chain of ``analysis_options.yaml`` (``package:`` URIs are resolved
through ``.dart_tool/package_config.json``, so run ``dart pub get`` first) and applies each
file's ``linter: rules:`` on top of the included set, the way the analyzer does.  Reports the
enabled set, the rules an included file turned on that this package turned off, and whether
``analyzer: plugins`` (custom_lint and friends) is active, since a package listed in
``pubspec.yaml`` with the plugin off contributes nothing.

Pure standard library: the YAML subset this needs (``include``, ``linter.rules`` as a list or
a ``name: true|false`` map, ``plugins``) is parsed by hand, so the file must use plain
two-space indentation.  Anything stranger prints a warning and is skipped.

Usage:
    active_lints_dart.py [--package DIR]                 # print enabled rules, one per line
    active_lints_dart.py [--package DIR] --has R [R …]   # exit 1 if any listed rule is not enabled
    active_lints_dart.py [--package DIR] --json          # machine-readable report

Exit code: 0; 1 when a --has rule is missing, an include cannot be resolved, or there is no options file.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

INCLUDE_RE = re.compile(r"^include:\s*(\S+)\s*$")
TOP_RE = re.compile(r"^(\w[\w-]*):\s*(.*)$")
LIST_ITEM_RE = re.compile(r"^\s*-\s*([\w-]+)\s*$")
MAP_ITEM_RE = re.compile(r"^\s*([\w-]+):\s*(true|false)\s*$")


def strip_comment(line: str) -> str:
    return re.sub(r"\s+#.*$", "", line.split("#", 1)[0] if line.lstrip().startswith("#") else line).rstrip()


def parse_options(path: Path) -> dict:
    """Return {'include': str|None, 'rules': {name: bool}, 'plugins': [..]} for one file."""
    include = None
    rules: dict[str, bool] = {}
    plugins: list[str] = []
    section: str | None = None      # top-level key
    sub: str | None = None          # e.g. 'rules' under linter, 'plugins' under analyzer
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = strip_comment(raw)
        if not line.strip():
            continue
        if not line.startswith(" "):
            m = INCLUDE_RE.match(line)
            if m:
                include = m.group(1).strip("'\"")
                section = sub = None
                continue
            m = TOP_RE.match(line)
            section = m.group(1) if m else None
            sub = None
            continue
        indent = len(line) - len(line.lstrip(" "))
        if indent == 2 and line.strip().endswith(":"):
            sub = line.strip()[:-1]
            continue
        if indent == 2 and section == "linter" and LIST_ITEM_RE.match(line):
            # `linter:\n  - rule` is not valid; keep going
            continue
        if section == "linter" and sub == "rules":
            m = MAP_ITEM_RE.match(line)
            if m:
                rules[m.group(1)] = m.group(2) == "true"
                continue
            m = LIST_ITEM_RE.match(line)
            if m:
                rules[m.group(1)] = True
                continue
            print(f"警告：{path} 的 rules 區有看不懂的行，略過：{raw}", file=sys.stderr)
        elif section in ("analyzer", "plugin") and sub == "plugins":
            m = LIST_ITEM_RE.match(line)
            if m:
                plugins.append(m.group(1))
            else:
                m = re.match(r"^\s*([\w-]+):", line)
                if m and len(line) - len(line.lstrip(" ")) == 4:
                    plugins.append(m.group(1))
    return {"include": include, "rules": rules, "plugins": plugins}


def resolve_include(spec: str, from_file: Path, package_dir: Path) -> Path:
    if spec.startswith("package:"):
        config = package_dir / ".dart_tool" / "package_config.json"
        if not config.exists():
            raise SystemExit(f"找不到 {config}，先跑 dart pub get 才能解析 {spec}")
        name, _, rest = spec[len("package:"):].partition("/")
        for pkg in json.loads(config.read_text(encoding="utf-8"))["packages"]:
            if pkg["name"] == name:
                root = urlparse(pkg["rootUri"])
                base = Path(unquote(root.path)) if root.scheme == "file" else (config.parent / pkg["rootUri"]).resolve()
                return (base / pkg.get("packageUri", "lib/") / rest).resolve()
        raise SystemExit(f"package_config.json 裡沒有 {name}，無法解析 {spec}")
    return (from_file.parent / spec).resolve()


def resolve(package_dir: Path) -> dict:
    start = package_dir / "analysis_options.yaml"
    if not start.exists():
        raise SystemExit(f"找不到 {start}")
    chain: list[Path] = []
    path = start
    seen: set[Path] = set()
    while path is not None:
        if path in seen:
            raise SystemExit(f"include 循環：{path}")
        seen.add(path)
        chain.append(path)
        parsed = parse_options(path)
        path = resolve_include(parsed["include"], path, package_dir) if parsed["include"] else None

    enabled: dict[str, bool] = {}
    disabled_here: list[str] = []
    plugins: list[str] = []
    for p in reversed(chain):              # base first, package last
        parsed = parse_options(p)
        plugins.extend(parsed["plugins"])
        for name, on in parsed["rules"].items():
            if p == start and not on and enabled.get(name):
                disabled_here.append(name)
            enabled[name] = on
    return {
        "chain": [str(p) for p in chain],
        "enabled": sorted(n for n, on in enabled.items() if on),
        "disabled_here": sorted(disabled_here),
        "plugins": plugins,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--package", default=".", help="Dart package 目錄（含 analysis_options.yaml）")
    ap.add_argument("--has", nargs="+", metavar="RULE", help="檢查這些 lint 是否啟用")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    report = resolve(Path(args.package).resolve())
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif args.has:
        missing = [r for r in args.has if r not in report["enabled"]]
        for r in args.has:
            state = "enabled" if r in report["enabled"] else ("disabled here" if r in report["disabled_here"] else "not enabled")
            print(f"{r}\t{state}")
        return 1 if missing else 0
    else:
        print("\n".join(report["enabled"]))
        print(f"SUMMARY enabled={len(report['enabled'])} disabled_here={len(report['disabled_here'])} "
              f"plugins={','.join(report['plugins']) or 'none'} chain={len(report['chain'])}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
