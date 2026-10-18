from __future__ import annotations

import argparse
import difflib
import subprocess
import sys
from pathlib import Path

REL = Path("90_wiki") / "SCHEMA.md"
REPO_ROOT = Path(__file__).resolve().parents[3]


def _uncommitted(vault: Path) -> bool:
    try:
        p = subprocess.run(["git", "status", "--porcelain", "--", str(REL)], cwd=vault,
                           capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return p.returncode == 0 and bool(p.stdout.strip())


def run(vault: Path, template: Path, *, check: bool = False, force: bool = False) -> int:
    target = vault / REL
    want = template.read_text(encoding="utf-8")
    have = target.read_text(encoding="utf-8") if target.exists() else None
    if have == want:
        print("SCHEMA in sync")
        return 0
    if check:
        if have is None:
            print(f"SCHEMA missing in workspace: {target}")
        else:
            diff = difflib.unified_diff(have.splitlines(), want.splitlines(),
                                        "workspace", "template", lineterm="", n=1)
            print("SCHEMA differs from the template (+ = template):")
            print("\n".join(diff))
        return 1
    if have is not None and not force and _uncommitted(vault):
        print(f"refusing: {target} has uncommitted changes — commit them or pass --force", file=sys.stderr)
        return 1
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(want, encoding="utf-8")
    print(f"SCHEMA updated from {template}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="zen-sync-schema", description="Copy the template's wiki SCHEMA into the workspace, or check for drift. No AI.")
    ap.add_argument("--vault", type=Path, default=REPO_ROOT / "vault")
    ap.add_argument("--template", type=Path, default=REPO_ROOT / "workspace-template" / REL)
    ap.add_argument("--check", action="store_true", help="exit 1 and show a diff if the workspace SCHEMA differs")
    ap.add_argument("--force", action="store_true", help="overwrite even if the workspace SCHEMA has uncommitted edits")
    a = ap.parse_args(argv)
    return run(a.vault, a.template, check=a.check, force=a.force)


if __name__ == "__main__":
    raise SystemExit(main())
