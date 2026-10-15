from __future__ import annotations

import argparse
from pathlib import Path

from . import index_cli, intake


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="zen-intake", description="File originals and write markdown companions. No AI.")
    ap.add_argument("specs", nargs="*", help="file path, URL, arXiv id/URL or DOI; none = process 00_inbox")
    ap.add_argument("--cluster", help="target cluster folder, e.g. 10_ai")
    ap.add_argument("--vault", type=Path, default=Path("vault"))
    ap.add_argument("--no-index", action="store_true")
    a = ap.parse_args(argv)

    if a.specs:
        specs: list[str] = []
        for s in a.specs:
            p = Path(s)
            if p.is_dir():
                specs.extend(str(f) for f in sorted(p.iterdir(), key=lambda f: f.name) if f.is_file() and not f.name.startswith("."))
            else:
                specs.append(s)
        report = intake.Report([intake.intake_item(a.vault, s, a.cluster) for s in specs])
    else:
        report = intake.intake_inbox(a.vault, a.cluster)
    print(report.summary())
    if not a.no_index:
        print()
        index_cli.run(a.vault)
    return 1 if any(i.status == "failed" for i in report.items) else 0


if __name__ == "__main__":
    raise SystemExit(main())
