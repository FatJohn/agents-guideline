"""Shared helpers for the usage-review skill: pricing, time parsing, text classification.

Pure standard library (Python >= 3.10). Nothing here knows about a particular machine,
project or time window; everything comes from arguments or from pricing.json.
"""
from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
DEFAULT_PRICING_PATH = Path(__file__).resolve().parent / "pricing.json"
FAMILIES = ("opus", "sonnet", "haiku", "fable")

UTC = dt.timezone.utc

# ---------------------------------------------------------------- pricing


def load_pricing(path: str | Path | None = None) -> dict:
    """Load pricing.json (default: the file next to this module) and validate its shape."""
    p = Path(path) if path else DEFAULT_PRICING_PATH
    with open(p, encoding="utf-8") as fh:
        data = json.load(fh)
    models = data.get("models")
    mult = data.get("cache_write_multiplier")
    if not isinstance(models, list) or not models:
        raise ValueError(f"{p}: 'models' must be a non-empty list")
    if not isinstance(mult, dict) or "5m" not in mult or "1h" not in mult:
        raise ValueError(f"{p}: 'cache_write_multiplier' needs '5m' and '1h'")
    for entry in models:
        for key in ("match", "input", "output", "cache_read"):
            if key not in entry:
                raise ValueError(f"{p}: model entry {entry!r} lacks {key!r}")
    # Longest match first, so a specific id wins over a prefix of it.
    data["_sorted_models"] = sorted(models, key=lambda e: len(e["match"]), reverse=True)
    data["_path"] = str(p)
    return data


def price_for(model: str | None, pricing: dict) -> dict | None:
    """Return the pricing entry whose 'match' is a substring of the model id (longest first)."""
    if not model:
        return None
    ordered = pricing.get("_sorted_models")
    if ordered is None:
        ordered = sorted(pricing["models"], key=lambda e: len(e["match"]), reverse=True)
    for entry in ordered:
        if entry["match"] in model:
            return entry
    return None


def family(model: str | None) -> str:
    """opus / sonnet / haiku / fable / other, by substring of the model id."""
    m = (model or "").lower()
    for fam in FAMILIES:
        if fam in m:
            return fam
    return "other"


def estimate_output(model: str | None, out_raw: int, vis: int, pricing: dict) -> int:
    """Heuristic output_tokens estimate from pricing['output_correction'] (see its note)."""
    fam = family(model)
    for rule in (pricing.get("output_correction") or {}).get("rules", []):
        if rule.get("family") != fam:
            continue
        if "add_tokens" in rule:
            return out_raw + int(rule["add_tokens"])
        if "min_visible_chars_ratio" in rule:
            return max(out_raw, int(rule["min_visible_chars_ratio"] * vis))
    return out_raw


def cost(req: dict, pricing: dict, corrected: bool = False) -> float | None:
    """USD cost of one normalized request, or None when the model matches no pricing entry.

    cache_creation tokens are priced per TTL: req['cw5m'] at the 5m multiplier and
    req['cw1h'] at the 1h multiplier (extract.py puts the whole total into cw1h when the
    breakdown is missing, which is an upper bound). With corrected=True the output side
    uses req['out_est'] (computed on the fly when absent).
    """
    entry = price_for(req.get("model"), pricing)
    if entry is None:
        return None
    mult = pricing["cache_write_multiplier"]
    if corrected:
        out = req.get("out_est")
        if out is None:
            out = estimate_output(req.get("model"), req.get("out_raw") or 0, req.get("vis") or 0, pricing)
    else:
        out = req.get("out_raw") or 0
    p_in = entry["input"]
    return (
        (req.get("inp") or 0) * p_in
        + (req.get("cw5m") or 0) * p_in * mult["5m"]
        + (req.get("cw1h") or 0) * p_in * mult["1h"]
        + (req.get("cr") or 0) * entry["cache_read"]
        + out * entry["output"]
    ) / 1e6


# ---------------------------------------------------------------- time

_FRACTION = re.compile(r"(\.\d+)")
_OFFSET = re.compile(r"^([+-])(\d{2}):?(\d{2})?$")


def _fromiso(s: str) -> dt.datetime:
    s = s.strip()
    if s.endswith(("Z", "z")):
        s = s[:-1] + "+00:00"
    try:
        return dt.datetime.fromisoformat(s)
    except ValueError:
        # Python 3.10 only accepts 3 or 6 fractional digits; normalise to 6.
        fixed = _FRACTION.sub(lambda m: (m.group(1) + "000000")[:7], s, count=1)
        return dt.datetime.fromisoformat(fixed)


def parse_ts(s: str) -> dt.datetime:
    """Parse a jsonl timestamp ('2026-10-11T23:47:03.390Z') into an aware UTC datetime."""
    t = _fromiso(s)
    if t.tzinfo is None:
        t = t.replace(tzinfo=UTC)
    return t.astimezone(UTC)


def parse_tz(tz: Any = None) -> dt.tzinfo:
    """tz may be None (system local zone), a tzinfo, '+08:00' / '+0800', 'Z' / 'UTC', or an IANA name."""
    if tz is None:
        return dt.datetime.now().astimezone().tzinfo or UTC
    if isinstance(tz, dt.tzinfo):
        return tz
    text = str(tz).strip()
    if text.upper() in ("Z", "UTC"):
        return UTC
    m = _OFFSET.match(text)
    if m:
        delta = dt.timedelta(hours=int(m.group(2)), minutes=int(m.group(3) or 0))
        return dt.timezone(delta if m.group(1) == "+" else -delta)
    from zoneinfo import ZoneInfo  # stdlib; raises if the name is unknown

    return ZoneInfo(text)


def parse_cli_time(s: str, tz: Any = None) -> dt.datetime:
    """Parse --since / --until. An explicit offset wins; a naive value is read in tz (default: local)."""
    t = _fromiso(s)
    if t.tzinfo is None:
        t = t.replace(tzinfo=parse_tz(tz))
    return t.astimezone(UTC)


def fmt_ts(t: dt.datetime) -> str:
    """ISO 8601 UTC with a 'Z' suffix, millisecond precision."""
    return t.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def fmt_offset(tz: dt.tzinfo, at: dt.datetime | None = None) -> str:
    """'+08:00' style offset of tz at the given instant (default: now)."""
    at = at or dt.datetime.now(UTC)
    off = at.astimezone(tz).utcoffset() or dt.timedelta(0)
    total = int(off.total_seconds() // 60)
    sign = "+" if total >= 0 else "-"
    return f"{sign}{abs(total) // 60:02d}:{abs(total) % 60:02d}"


# ---------------------------------------------------------------- text

_SYSTEM_REMINDER = re.compile(r"<system-reminder>.*?</system-reminder>", re.S)


def strip_system_reminders(text: str) -> str:
    """Remove <system-reminder>...</system-reminder> blocks. Rules text lives inside them,
    so any string count on raw jsonl text must go through this first."""
    return _SYSTEM_REMINDER.sub("", text or "")


def classify_human(text: str, is_meta: bool = False) -> str:
    """Classify the text of a type:"user" record that is not a tool_result.

    human / peer / command / ask_answer / compact / notification / meta.
    A '[Subagent hand-back]' agent-message is the harness delivering a subagent report,
    not another session talking, so it is 'notification' rather than 'peer'.
    Text that is empty once system-reminders are stripped is 'meta' (never 'human').
    """
    if is_meta:
        return "meta"
    clean = strip_system_reminders(text).strip()
    if not clean:
        return "meta"
    if clean.startswith("[ASK-ANSWER]"):
        return "ask_answer"
    if clean.startswith("<task-notification>"):
        return "notification"
    if clean.startswith("<agent-message") or "Another Claude session sent a message" in clean[:400]:
        return "notification" if "[Subagent hand-back]" in clean[:1000] else "peer"
    if clean.startswith(("<command-name>", "<command-message>", "<command-args>", "<local-command")):
        return "command"
    if clean.startswith("This session is being continued"):
        return "compact"
    return "human"


_NOTIF_BLOCK = re.compile(r"<task-notification>(.*?)</task-notification>", re.S)


def _tag(block: str, name: str) -> str | None:
    m = re.search(rf"<{name}>(.*?)</{name}>", block, re.S)
    return m.group(1).strip() if m else None


def _int(s: str | None) -> int | None:
    try:
        return int(s) if s is not None else None
    except ValueError:
        return None


def parse_task_notifications(text: str) -> list[dict]:
    """All <task-notification> blocks found in text (system-reminders stripped first)."""
    out = []
    for block in _NOTIF_BLOCK.findall(strip_system_reminders(text)):
        usage = _tag(block, "usage") or ""
        out.append(
            {
                "task_id": _tag(block, "task-id"),
                "tool_use_id": _tag(block, "tool-use-id"),
                "status": _tag(block, "status"),
                "subagent_tokens": _int(_tag(usage, "subagent_tokens")),
                "tool_uses": _int(_tag(usage, "tool_uses")),
                "duration_ms": _int(_tag(usage, "duration_ms")),
            }
        )
    return out


def parse_task_notification(text: str) -> dict | None:
    """First <task-notification> in text as {task_id, tool_use_id, status, subagent_tokens,
    tool_uses, duration_ms} (the three numbers come from its <usage> element), or None."""
    found = parse_task_notifications(text)
    return found[0] if found else None


# ---------------------------------------------------------------- data file


def load_data(path: str | Path) -> dict:
    """Load an extract.py output file and check its schema_version."""
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    version = data.get("schema_version") if isinstance(data, dict) else None
    if version != SCHEMA_VERSION:
        raise ValueError(
            f"{path}: schema_version {version!r} is not supported (expected {SCHEMA_VERSION}); "
            "re-run extract.py with this version of the skill"
        )
    return data
