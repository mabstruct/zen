from __future__ import annotations

import argparse
import contextlib
import io
import json
import subprocess
import sys
from pathlib import Path
from typing import Callable

from . import index_cli

QmdRunner = Callable[[str, int, Path], tuple[int, str, str]]


def default_qmd(question: str, n: int, root: Path) -> tuple[int, str, str]:
    try:
        p = subprocess.run(
            ["qmd", "query", question, "--json", "-n", str(n)],
            cwd=root, capture_output=True, text=True, timeout=600,
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        return 1, "", f"{type(e).__name__}: {e}"
    return p.returncode, p.stdout, p.stderr


def strip_health(index_text: str) -> str:
    return index_text.split("\n## Health", 1)[0].rstrip("\n") + "\n"


def format_hits(stdout: str) -> str:
    hits = json.loads(stdout or "[]")
    if not hits:
        return "(no hits)\n"
    lines = []
    for i, h in enumerate(hits, 1):
        path = str(h.get("file", "")).split("/", 3)[-1] if str(h.get("file", "")).startswith("qmd://") else str(h.get("file", ""))
        lines.append(f"{i}. [{float(h.get('score', 0)):.2f}] {path}:{h.get('line', '')} — {h.get('title', '')}")
        snippet = [s for s in str(h.get("snippet", "")).splitlines() if not s.startswith("@@")]
        lines.extend("   " + s for s in snippet)
    return "\n".join(lines) + "\n"


def run(vault: Path, question: str, n: int = 8, qmd: QmdRunner = default_qmd) -> int:
    vault = vault.resolve()
    if not vault.is_dir():
        print(f"no vault at {vault}", file=sys.stderr)
        return 2
    if index_cli.is_stale(vault):
        with contextlib.redirect_stdout(io.StringIO()):
            index_cli.run(vault)
        print("index rebuilt (was stale)\n")

    print("### vault/INDEX.md (Health omitted)\n")
    print(strip_health((vault / "INDEX.md").read_text(encoding="utf-8")))
    print("### vault/90_wiki/INDEX.md\n")
    wiki_index = vault / "90_wiki" / "INDEX.md"
    print(wiki_index.read_text(encoding="utf-8") if wiki_index.exists() else "(no wiki index)\n")

    print(f"### qmd hits for: {question}\n")
    rc, out, err = qmd(question, n, vault.parent)
    if rc != 0:
        print(f"qmd unavailable: {(err or out).strip().splitlines()[0] if (err or out).strip() else 'exit ' + str(rc)}")
        return 0
    print(format_hits(out))
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="zen-ask-prep", description="Brain-First ladder steps 0–3 in one call: stale check, INDEX.md, wiki INDEX.md, qmd hits.")
    ap.add_argument("question", nargs="+")
    ap.add_argument("--vault", type=Path, default=Path("vault"))
    ap.add_argument("-n", type=int, default=8, help="number of qmd hits")
    a = ap.parse_args(argv)
    return run(a.vault, " ".join(a.question), n=a.n)


if __name__ == "__main__":
    raise SystemExit(main())
