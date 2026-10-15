from __future__ import annotations

import argparse
from pathlib import Path

from . import index_cli, intake, refresh


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="zen-intake", description="File originals and write markdown companions. No AI.")
    ap.add_argument("specs", nargs="*", help="file path, URL, arXiv id/URL or DOI; none = process 00_inbox")
    ap.add_argument("--cluster", help="target cluster folder, e.g. 10_ai")
    ap.add_argument("--vault", type=Path, default=Path("vault"))
    ap.add_argument("--no-index", action="store_true")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--retry-missing", action="store_true", help="re-fetch every companion with snapshot: missing")
    mode.add_argument("--recapture", metavar="VAULT_PATH", help="re-fetch one companion's source.url and replace its snapshot if it changed")
    a = ap.parse_args(argv)

    if (a.retry_missing or a.recapture) and (a.specs or a.cluster):
        ap.error("--retry-missing/--recapture take no specs and no --cluster")
    if a.retry_missing:
        report = refresh.retry_missing(a.vault)
    elif a.recapture:
        report = intake.Report([refresh.recapture(a.vault, a.recapture)])
    elif a.specs:
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
