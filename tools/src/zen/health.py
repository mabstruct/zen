from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta

from .vault import VaultScan

KINDS = (
    "bad-frontmatter",
    "inbox-stale",
    "snapshot-missing",
    "extraction-failed",
    "large-file",
    "orphan",
    "broken-link",
    "duplicate-title",
    "never-ingested",
    "wiki-behind",
    "open-conflict",
)
CONTENT_TYPES = {"note", "companion", "daily"}


@dataclass
class Finding:
    kind: str
    path: str
    detail: str = ""


def _ts(s: object) -> datetime | None:
    if not isinstance(s, str) or not s:
        return None
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    return dt.astimezone() if dt.tzinfo is None else dt


def check(scan: VaultScan, now: datetime, inbox_days: int = 7) -> list[Finding]:
    out: list[Finding] = []
    docs = scan.docs

    for d in docs.values():
        if d.frontmatter_error:
            out.append(Finding("bad-frontmatter", d.rel, d.frontmatter_error))

    cutoff = now - timedelta(days=inbox_days)
    for rel in scan.inbox:
        d = docs[rel]
        when = _ts(d.created) or _ts(d.updated)
        if when and when < cutoff:
            out.append(Finding("inbox-stale", rel, f"since {when.date()}"))

    for d in docs.values():
        if d.meta.get("snapshot") == "missing":
            out.append(Finding("snapshot-missing", d.rel, str((d.meta.get("source") or {}).get("url", ""))))
    for d in docs.values():
        if d.meta.get("extraction") == "failed":
            out.append(Finding("extraction-failed", d.rel))
    for d in docs.values():
        if d.meta.get("large") is True:
            out.append(Finding("large-file", d.rel))

    for d in docs.values():
        if d.type in CONTENT_TYPES and d.inbound == 0 and not any(t in docs for t in d.links):
            out.append(Finding("orphan", d.rel))

    for src, target in scan.broken_links:
        out.append(Finding("broken-link", src, target))

    titles: dict[str, list[str]] = defaultdict(list)
    for d in docs.values():
        if d.type in CONTENT_TYPES:
            titles[d.title.strip().lower()].append(d.rel)
    for title, rels in sorted(titles.items()):
        if len(rels) > 1:
            for rel in sorted(rels):
                out.append(Finding("duplicate-title", rel, title))

    for d in docs.values():
        if d.type in CONTENT_TYPES and d.ingested is None:
            out.append(Finding("never-ingested", d.rel))
    for d in docs.values():
        if d.type in CONTENT_TYPES and d.ingested is not None:
            upd, ing = _ts(d.updated), _ts(d.ingested)
            if upd and ing and upd > ing:
                out.append(Finding("wiki-behind", d.rel, f"updated {d.updated} > ingested {d.ingested}"))

    for d in docs.values():
        for cid in d.open_conflicts:
            out.append(Finding("open-conflict", d.rel, cid))

    out.sort(key=lambda f: (KINDS.index(f.kind), f.path, f.detail))
    return out
