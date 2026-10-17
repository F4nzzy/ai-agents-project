"""Fill the live addenda in DECISIONS.md from JSON this machine just wrote.

Leaves the recording tables alone. If a live file is missing, that block
stays as "not run yet".
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DECISIONS = ROOT / "DECISIONS.md"


def _load(name: str) -> dict | None:
    path = ROOT / "artifacts" / name
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _between(text: str, start: str, end: str, body: str) -> str:
    a = text.find(start)
    b = text.find(end)
    if a < 0 or b < 0 or b < a:
        raise SystemExit(f"missing markers {start!r} .. {end!r}")
    return text[: a + len(start)] + "\n" + body.rstrip() + "\n" + text[b:]


def week4() -> str:
    large = _load("week04_agent_live_qwen2.5_7b.json")
    small = _load("week04_agent_live_qwen3_4b-instruct.json")
    bare = _load("week04_agent_notools.json")
    defense = _load("week04_defenses.json")
    if not any((large, small, bare, defense)):
        return "Live on this laptop: not run yet."
    lines = ["Live on this laptop, after `scripts/finish_weeks.sh`:"]
    if large and large.get("source") == "live":
        lines.append(
            f"- qwen2.5:7b with tools: {large['passed']}/{large['total']}, "
            f"failed {large['failed'] or 'none'}. "
            f"Tool abuse {large['tool_abuse'] or 'none'}. "
            f"Invented {large['invented'] or 'none'}. "
            f"Injection reached {large['injection_seen'] or 'no task'}, "
            f"followed {large['injection_followed'] or 'no task'}."
        )
    if small and small.get("source") == "live":
        lines.append(
            f"- qwen3:4b-instruct with tools: {small['passed']}/{small['total']}, "
            f"failed {small['failed'] or 'none'}."
        )
    if bare and bare.get("source") == "live":
        lines.append(
            f"- no-tool baseline on {bare['model']}: "
            f"{bare['passed']}/{bare['total']}."
        )
    if defense and defense.get("rows"):
        rows = defense["rows"]
        blocked = sum(1 for r in rows if r.get("reached") and not r.get("followed"))
        lines.append(
            f"- defense ladder: {blocked}/{len(rows)} blocked the marker "
            f"after it had reached the model."
        )
    lines.append(
        "These are this machine's runs. The 5/10 table above stays the recording."
    )
    return "\n".join(lines)


def week5() -> str:
    data = _load("week05_architectures.json")
    if not data or not data.get("rows"):
        return "Live on this laptop, three runs each: not run yet."
    rows = data["rows"]
    # The replay file is also named week05_architectures.json and gets
    # overwritten by a live run. Replay rows have no "source" field and the
    # recording's baseline seconds are about 40. A live run is whatever
    # 01_compare.py last wrote. If every row is missing a machine-local
    # marker we still summarise it, and we say so.
    by: dict[str, list] = {}
    for row in rows:
        by.setdefault(row["architecture"], []).append(row)
    lines = ["Last `01_compare.py` table written to week05_architectures.json:"]
    for arch, group in by.items():
        green = sum(bool(r.get("green")) for r in group)
        tok = sum(r.get("tokens") or 0 for r in group) // len(group)
        sec = sum(r.get("seconds") or 0 for r in group) / len(group)
        lines.append(f"- {arch}: {green}/{len(group)}, mean tokens {tok}, mean seconds {sec:.1f}")
    lines.append(
        "If those seconds are ~40/15/29, this file is still the 2026-08-11 recording. "
        "A live run replaces it; check the seconds before quoting it as this laptop."
    )
    return "\n".join(lines)


def main() -> None:
    text = DECISIONS.read_text(encoding="utf-8")
    text = _between(text, "<!-- LIVE_WEEK4 -->", "<!-- /LIVE_WEEK4 -->", week4())
    text = _between(text, "<!-- LIVE_WEEK5 -->", "<!-- /LIVE_WEEK5 -->", week5())
    DECISIONS.write_text(text, encoding="utf-8")
    print("DECISIONS.md live addenda refreshed")


if __name__ == "__main__":
    main()
