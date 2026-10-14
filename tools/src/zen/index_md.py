from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from .health import KINDS, Finding
from .vault import Doc, VaultScan

INBOUND_THRESHOLD = 3


def is_important(doc: Doc) -> bool:
    return bool(doc.summary) or doc.inbound >= INBOUND_THRESHOLD or "pinned" in doc.tags


def _target(rel: str) -> str:
    return f"<{rel}>" if " " in rel else rel


def _line(doc: Doc) -> str:
    parts = [f"- [{doc.title}]({_target(doc.rel)})"]
    detail = [doc.summary] if doc.summary else []
    if doc.tags:
        detail.append(" ".join(doc.tags))
    detail.append(f"updated {doc.updated[:10]}")
    return parts[0] + " — " + " · ".join(detail)


def render(scan: VaultScan, findings: list[Finding], now: datetime) -> str:
    docs = scan.docs.values()
    notes = sum(1 for d in docs if d.type in {"note", "daily"})
    companions = sum(1 for d in docs if d.type == "companion")
    wiki_pages = sum(1 for d in docs if d.type.startswith("wiki-") and d.type != "wiki-meta")
    open_conflicts = sum(1 for f in findings if f.kind == "open-conflict")

    out = ["# ZEN Index", ""]
    out.append(
        f"Generated {now.isoformat()} · {notes} notes · {companions} companions · "
        f"{len(scan.originals)} originals · {wiki_pages} wiki pages · {open_conflicts} open conflicts"
    )
    out.append("")
    out.append("Read this first. Open exactly the file you need. Regenerate with `zen-index`; never edit by hand.")
    out.append("")

    for c in scan.clusters:
        out.append(f"## {c.name}")
        out.append("")
        out.append(f"{c.description} — {c.notes} notes · {c.companions} companions · {c.originals} originals")
        out.append("")
        important = [d for d in docs if d.cluster == c.name and is_important(d)]
        for d in sorted(important, key=lambda d: (d.updated, d.rel), reverse=True):
            out.append(_line(d))
        if important:
            out.append("")

    out.append("## Wiki")
    out.append("")
    by_type: dict[str, list[Doc]] = defaultdict(list)
    for d in docs:
        if d.type.startswith("wiki-") and d.type != "wiki-meta":
            by_type[d.type].append(d)
    for t in sorted(by_type):
        out.append(f"### {t}")
        for d in sorted(by_type[t], key=lambda d: d.rel):
            out.append(f"- [{d.title}]({_target(d.rel)})")
        out.append("")
    if not by_type:
        out.append("No wiki pages yet. Run `/zen-ingest`.")
        out.append("")

    out.append("## Health")
    out.append("")
    by_kind: dict[str, list[Finding]] = defaultdict(list)
    for f in findings:
        by_kind[f.kind].append(f)
    if not findings:
        out.append("Clean.")
        out.append("")
    for kind in KINDS:
        if kind not in by_kind:
            continue
        out.append(f"### {kind}")
        for f in by_kind[kind]:
            out.append(f"- {f.path} — {f.detail}" if f.detail else f"- {f.path}")
        out.append("")
    return "\n".join(out).rstrip("\n") + "\n"
