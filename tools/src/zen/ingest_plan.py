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
    input_file = vault / plan["input"]
    if not input_file.is_file():
        errs.append(f"input not found: {plan['input']}")
    n_lines = len(input_file.read_text(encoding="utf-8").splitlines()) if input_file.is_file() else 0

    section = plan.get("section")
    last = not section or section.get("index") == section.get("count")
    lo, hi = 1, n_lines
    if section:
        rng = section.get("lines")
        if not (isinstance(section.get("index"), int) and isinstance(section.get("count"), int)
                and isinstance(rng, list) and len(rng) == 2 and 1 <= rng[0] <= rng[1] <= n_lines):
            errs.append("section needs index, count and lines [start, end] inside the input")
        else:
            lo, hi = rng
        if not str(plan.get("section_summary") or "").strip():
            errs.append("section plan needs a section_summary (one paragraph for the book's source page)")
        if last and not str(plan.get("summary") or "").strip():
            errs.append("the last section's plan needs the book summary for the companion")

    sp = plan["source_page"] or {}
    sp_path = str(sp.get("path", ""))
    if not (sp_path.startswith("sources/") and sp_path.endswith(".md") and sp.get("title") and (sp.get("body") or not last)):
        errs.append("source_page needs path sources/<stem>.md, title and body (body only in the last section of a book)")

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
        if "claims" in p:
            errs.append(f"{path}: thin plan — claims are written by the page writers, not the planner; give a brief and source_lines")
        if not str(p.get("brief") or "").strip():
            errs.append(f"{path}: missing brief (one line on what the page should cover)")
        ranges = p.get("source_lines") or []
        if not ranges:
            errs.append(f"{path}: missing source_lines (line ranges of the input the writer should read)")
        for r in ranges:
            ok = isinstance(r, list) and len(r) == 2 and all(isinstance(x, int) for x in r)
            if not ok or not (1 <= r[0] <= r[1] <= n_lines):
                errs.append(f"{path}: source_lines range {r} is not within lines 1–{n_lines} of the input")
            elif section and not (lo <= r[0] <= r[1] <= hi):
                errs.append(f"{path}: source_lines range {r} is outside this section's lines {lo}–{hi}")
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


def _book_source_body(plan: dict, plan_dir: Path | None) -> str:
    sec = plan["section"]
    plans = []
    for f in sorted((plan_dir or Path(".")).glob("section-*.yaml")):
        p = load(f)
        if p.get("section", {}).get("index") != sec["index"]:
            plans.append(p)
    plans.append(plan)
    plans.sort(key=lambda p: p["section"]["index"])
    done, count = len(plans), sec["count"]
    sp = plan["source_page"]
    head = f"# {sp['title']}\n\n"
    if sec["index"] == count and sp.get("body"):
        intro = str(sp["body"]).strip()
        intro = intro.split("\n", 1)[1].strip() if intro.startswith("# ") else intro
    else:
        intro = f"Book ingest in progress: {done} of {count} sections done."
    out = [head + intro, f"Vault file: [{plan['input']}](../../{plan['input']})", "## Sections"]
    for p in plans:
        s = p["section"]
        pages = p.get("section_pages") or s.get("pages")
        where = f" (pages {pages[0]}–{pages[1]})" if pages else ""
        out.append(f"### {s['index']}. {s['title']}{where}\n\n{str(p.get('section_summary') or '').strip()}")
    return "\n\n".join(out) + "\n"


def finish(vault: Path, plan: dict, plan_dir: Path | None = None) -> None:
    vault = vault.resolve()
    wiki = vault / "90_wiki"
    ts = plan["ingested"]
    sp = plan["source_page"]
    section = plan.get("section")
    last = not section or section["index"] == section["count"]
    sp_file = wiki / sp["path"]
    sp_existed = sp_file.exists()
    created = fm.read(sp_file).meta.get("created", ts) if sp_existed else ts
    meta = {"title": sp["title"], "type": "wiki-source", "created": created, "updated": ts,
            "sources": [plan["input"]], "confidence": "high", "tags": []}
    sp_file.parent.mkdir(parents=True, exist_ok=True)
    body = _book_source_body(plan, plan_dir) if section else str(sp["body"])
    fm.write(sp_file, fm.Document(meta, body))

    if last:
        _stamp_companion(vault, plan)

    pages = plan.get("pages") or []
    created_list = ([] if sp_existed else [sp["path"]]) + [p["path"] for p in pages if p["action"] == "create"]
    updated_list = ([sp["path"]] if sp_existed else []) + [p["path"] for p in pages if p["action"] == "update"]
    conflicts = plan.get("conflicts") or []
    word = "re-ingest" if sp_existed and not section else "ingest"
    where = f" (section {section['index']}/{section['count']}: {section['title']})" if section else ""
    mode = f"sectioned, section {section['index']}/{section['count']}" if section else "planned"
    entry = (
        f"\n## {ts} {word} {plan['input']}{where}\n"
        f"- created: {', '.join(created_list) or 'none'}\n"
        f"- updated: {', '.join(updated_list) or 'none'}\n"
        f"- conflicts: {', '.join(f'{c['id']} ({', '.join(c['pages'])})' for c in conflicts) or 'none'}\n"
        f"- mode: {mode}, {len(pages)} pages\n"
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
    sx = sub.add_parser("sections", help="write a section map for a long companion (book ingest)")
    sx.add_argument("input", help="vault-relative companion path")
    sx.add_argument("--vault", type=Path, default=Path("vault"))
    sx.add_argument("--max-tokens", type=int, default=30000)
    sx.add_argument("--out", type=Path, required=True)
    f = sub.add_parser("finish", help="write source page, companion stamp, LOG entry and wiki INDEX")
    f.add_argument("plan", type=Path)
    f.add_argument("--vault", type=Path, default=Path("vault"))
    a = ap.parse_args(argv)
    if a.cmd == "sections":
        from . import sections
        secs = sections.build((a.vault / a.input).read_text(encoding="utf-8"), max_tokens=a.max_tokens)
        data = {"input": a.input, "max_tokens": a.max_tokens, "sections": [
            {"index": i, "title": x.title, "pages": [x.first_page, x.last_page] if x.first_page else None,
             "lines": [x.start_line, x.end_line], "tokens": x.tokens} for i, x in enumerate(secs, 1)]}
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
        for x in data["sections"]:
            pg = f"p{x['pages'][0]}-{x['pages'][1]}" if x["pages"] else "-"
            print(f"{x['index']}. {pg:>10} {x['tokens']:>7,} tokens  lines {x['lines'][0]}-{x['lines'][1]}  {x['title']}")
        return 0
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
    finish(a.vault, p, plan_dir=a.plan.parent)
    print(f"finished {p['input']}: {len(p.get('pages') or [])} pages, {len(p.get('conflicts') or [])} conflicts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
