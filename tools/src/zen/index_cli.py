from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from . import health, index_md, map_json
from .vault import SKIP_DIRS, scan

OUTPUTS = ("INDEX.md", "_meta/map.json")


def _content_mtime(vault: Path) -> float:
    latest = 0.0
    for dirpath, dirnames, filenames in os.walk(vault):
        dirnames[:] = [d for d in dirnames if d not in (SKIP_DIRS - {"_originals"})]
        latest = max(latest, Path(dirpath).stat().st_mtime)  # a delete or rename changes only the folder
        for f in filenames:
            p = Path(dirpath) / f
            rel = p.relative_to(vault).as_posix()
            if rel in OUTPUTS or f.startswith("."):
                continue
            latest = max(latest, p.stat().st_mtime)
    return latest


def is_stale(vault: Path) -> bool:
    index = vault / "INDEX.md"
    if not index.exists() or not (vault / "_meta" / "map.json").exists():
        return True
    return _content_mtime(vault) > index.stat().st_mtime


def run(vault: Path, check: bool = False, now: datetime | None = None) -> int:
    vault = vault.resolve()
    if not vault.is_dir():
        print(f"no vault at {vault} — run scripts/ws-init.sh or pass --vault", file=sys.stderr)
        return 2
    if check:
        if is_stale(vault):
            print(f"stale: {vault / 'INDEX.md'} is older than vault content — run zen-index", file=sys.stderr)
            return 1
        print("index is current")
        return 0
    now = now or datetime.now().astimezone().replace(microsecond=0)
    s = scan(vault)
    findings = health.check(s, now)
    text = index_md.render(s, findings, now)
    (vault / "_meta").mkdir(exist_ok=True)
    (vault / "INDEX.md").write_text(text, encoding="utf-8")
    (vault / "_meta" / "map.json").write_text(json.dumps(map_json.build(s, now), indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(text.splitlines()[2])
    print()
    print("## Health" + text.split("## Health", 1)[1])
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="zen-index", description="Rebuild vault/INDEX.md and vault/_meta/map.json.")
    ap.add_argument("--vault", type=Path, default=Path("vault"))
    ap.add_argument("--check", action="store_true", help="exit 1 if INDEX.md is older than vault content")
    a = ap.parse_args(argv)
    return run(a.vault, check=a.check)


if __name__ == "__main__":
    raise SystemExit(main())
