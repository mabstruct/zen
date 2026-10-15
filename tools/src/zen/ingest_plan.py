"""Deterministic support for planned (parallel) wiki ingest: check a plan, slice it into writer
batches, and finish a run by writing the single-owner files (source page, companion stamp,
LOG entry, wiki INDEX). The model work — planning and page writing — happens in agents."""
from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path, PurePosixPath

import yaml

from . import frontmatter as fm
from .vault import scan

FOLDER_TYPE = {"topics": "wiki-topic", "entities": "wiki-entity", "syntheses": "wiki-synthesis"}
TYPE_ORDER = ("wiki-source", "wiki-topic", "wiki-entity", "wiki-synthesis")
CITATION_RE = re.compile(r"\]\((?:\.\./)?sources/[^)\s]+\.md\)")
CONFLICT_ID_RE = re.compile(r"#c-(\d{4})")
INDEX_HEADER = "# Wiki index\n\nMaintained by `/zen-ingest`. One line per page.\n"


def load(path: Path) -> dict:
    return yaml.load(path.read_text(encoding="utf-8"), Loader=fm._Loader) or {}


def next_conflict_id(wiki: Path) -> int:
    log = wiki / "LOG.md"
    ids = [int(n) for n in CONFLICT_ID_RE.findall(log.read_text(encoding="utf-8"))] if log.exists() else []
    return max(ids, default=0) + 1


def check(vault: Path, plan: dict) -> list[str]:
    wiki = vault.resolve() / "90_wiki"
    errs: list[str] = []
    for key in ("input", "ingested", "source_page", "pages"):
        if key not in plan:
            errs.append(f"missing key: {key}")
    if errs:
        return errs
    if not (vault / plan["input"]).is_file():
        errs.append(f"input not found: {plan['input']}")

    sp = plan["source_page"] or {}
    sp_path = str(sp.get("path", ""))
    if not (sp_path.startswith("sources/") and sp_path.endswith(".md") and sp.get("title") and sp.get("body")):
        errs.append("source_page needs path sources/<stem>.md, title and body")

    pages = plan["pages"] or []
    planned = {str(p.get("path")) for p in pages}
    existing = {p.relative_to(wiki).as_posix() for p in wiki.rglob("*.md")} if wiki.exists() else set()
    targets = planned | existing | {sp_path}
    defined = [str(c.get("id")) for c in (plan.get("conflicts") or [])]

    for p in pages:
        path = str(p.get("path", ""))
        folder = PurePosixPath(path).parts[0] if path else ""
        if folder not in FOLDER_TYPE or not path.endswith(".md"):
            errs.append(f"{path}: pages go under topics/, entities/ or syntheses/ as .md")
        elif p.get("type") != FOLDER_TYPE[folder]:
            errs.append(f"{path}: type {p.get('type')} does not match folder (expected {FOLDER_TYPE[folder]})")
        action = p.get("action")
        if action == "create" and (wiki / path).exists():
            errs.append(f"{path}: action create, but the page already exists — use update")
        elif action == "update" and not (wiki / path).exists():
            errs.append(f"{path}: action update, but the page does not exist — use create")
        elif action not in ("create", "update"):
            errs.append(f"{path}: action must be create or update")
        if not p.get("title"):
            errs.append(f"{path}: missing title")
        for claim in p.get("claims") or []:
            if not CITATION_RE.search(str(claim)):
                errs.append(f"{path}: uncited claim (needs a link to a sources/ page): {str(claim)[:60]}")
        for link in p.get("links") or []:
            if str(link) not in targets:
                errs.append(f"{path}: link target {link} is neither planned nor an existing wiki page")
        for cid in p.get("conflicts") or []:
            if str(cid) not in defined:
                errs.append(f"{path}: conflict {cid} is not defined in conflicts:")

    start = next_conflict_id(wiki)
    for i, c in enumerate(plan.get("conflicts") or []):
        expected = f"#c-{start + i:04d}"
        if str(c.get("id")) != expected:
            errs.append(f"conflict id {c.get('id')} out of sequence — expected {expected}")
        for pg in c.get("pages") or []:
            if str(pg) not in planned:
                errs.append(f"conflict {c.get('id')}: page {pg} is not a planned page")
        for side in ("a", "b"):
            if not isinstance(c.get(side), dict) or not c[side].get("claim") or not c[side].get("source"):
                errs.append(f"conflict {c.get('id')}: side {side} needs claim and source")
    return errs


def batches(plan: dict, size: int) -> list[list[str]]:
    paths = [str(p["path"]) for p in plan.get("pages") or []]
    return [paths[i:i + size] for i in range(0, len(paths), size)]


def _stamp_companion(vault: Path, plan: dict) -> None:
    path = vault / plan["input"]
    doc = fm.read(path)
    ts = plan["ingested"]
    body = doc.body
    if plan.get("title"):
        doc.meta["title"] = plan["title"]
        body = re.sub(r"^# .*$", f"# {plan['title']}", body, count=1, flags=re.M)
    m = re.search(r"^## Summary\n(.*?)(?=^## |\Z)", body, flags=re.M | re.S)
    if m and not m.group(1).strip() and plan.get("summary"):
        body = body[: m.start(1)] + str(plan["summary"]).strip("\n") + "\n\n" + body[m.end(1):].lstrip("\n")
    doc.meta["ingested"] = ts
    doc.meta["updated"] = ts
    fm.write(path, fm.Document(doc.meta, body))


def regenerate_index(vault: Path) -> None:
    wiki = vault / "90_wiki"
    groups: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
    for d in scan(vault).docs.values():
        if d.rel.startswith("90_wiki/") and d.type in TYPE_ORDER:
            groups[d.type].append((d.title, d.rel[len("90_wiki/"):], d.updated[:10]))
    out = [INDEX_HEADER]
    for t in TYPE_ORDER:
        out.append(f"## {t}\n")
        rows = sorted(groups[t], key=lambda r: (r[0].casefold(), r[1]))
        if rows:
            out.append("\n".join(f"- [{title}]({rel}) · {t} · {day}" for title, rel, day in rows) + "\n")
    (wiki / "INDEX.md").write_text("\n".join(out), encoding="utf-8")


def finish(vault: Path, plan: dict) -> None:
    vault = vault.resolve()
    wiki = vault / "90_wiki"
    ts = plan["ingested"]
    sp = plan["source_page"]
    sp_file = wiki / sp["path"]
    sp_existed = sp_file.exists()
    created = fm.read(sp_file).meta.get("created", ts) if sp_existed else ts
    meta = {"title": sp["title"], "type": "wiki-source", "created": created, "updated": ts,
            "sources": [plan["input"]], "confidence": "high", "tags": []}
    sp_file.parent.mkdir(parents=True, exist_ok=True)
    fm.write(sp_file, fm.Document(meta, str(sp["body"])))

    _stamp_companion(vault, plan)

    pages = plan.get("pages") or []
    created_list = ([] if sp_existed else [sp["path"]]) + [p["path"] for p in pages if p["action"] == "create"]
    updated_list = ([sp["path"]] if sp_existed else []) + [p["path"] for p in pages if p["action"] == "update"]
    conflicts = plan.get("conflicts") or []
    word = "re-ingest" if sp_existed else "ingest"
    entry = (
        f"\n## {ts} {word} {plan['input']}\n"
        f"- created: {', '.join(created_list) or 'none'}\n"
        f"- updated: {', '.join(updated_list) or 'none'}\n"
        f"- conflicts: {', '.join(f'{c['id']} ({', '.join(c['pages'])})' for c in conflicts) or 'none'}\n"
        f"- mode: planned, {len(pages)} pages\n"
    )
    log = wiki / "LOG.md"
    log.write_text(log.read_text(encoding="utf-8").rstrip("\n") + "\n" + entry, encoding="utf-8")

    regenerate_index(vault)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="zen-plan", description="Check, batch and finish a planned wiki ingest. No AI.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check", help="validate a plan against the wiki")
    c.add_argument("plan", type=Path)
    c.add_argument("--vault", type=Path, default=Path("vault"))
    b = sub.add_parser("batches", help="print writer batches, one line of page paths per batch")
    b.add_argument("plan", type=Path)
    b.add_argument("--size", type=int, default=6)
    f = sub.add_parser("finish", help="write source page, companion stamp, LOG entry and wiki INDEX")
    f.add_argument("plan", type=Path)
    f.add_argument("--vault", type=Path, default=Path("vault"))
    a = ap.parse_args(argv)
    p = load(a.plan)
    if a.cmd == "check":
        errs = check(a.vault, p)
        for e in errs:
            print(e, file=sys.stderr)
        print("plan ok" if not errs else f"plan has {len(errs)} error(s)")
        return 0 if not errs else 1
    if a.cmd == "batches":
        for batch in batches(p, a.size):
            print(" ".join(batch))
        return 0
    finish(a.vault, p)
    print(f"finished {p['input']}: {len(p.get('pages') or [])} pages, {len(p.get('conflicts') or [])} conflicts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
