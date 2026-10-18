from __future__ import annotations

from datetime import datetime
from pathlib import PurePosixPath

from .vault import VaultScan, cluster_of


def build(scan: VaultScan, now: datetime) -> dict:
    nodes: dict[str, dict] = {}
    edges: list[dict] = []

    for d in scan.docs.values():
        nodes[d.rel] = {
            "id": d.rel, "path": d.rel, "title": d.title, "type": d.type, "cluster": d.cluster,
            "tags": d.tags, "size": d.size, "created": d.created, "updated": d.updated,
            "captured": d.captured, "ingested": d.ingested,
        }
    for o in scan.originals:
        nodes[o] = {
            "id": o, "path": o, "title": PurePosixPath(o).name, "type": "original", "cluster": cluster_of(o),
            "tags": [], "size": (scan.root / o).stat().st_size, "created": None, "updated": None,
            "captured": None, "ingested": None,
        }
    for d in scan.docs.values():
        for t in d.tags:
            tid = f"tag:{t}"
            nodes.setdefault(tid, {"id": tid, "path": None, "title": t, "type": "tag", "cluster": None, "tags": [],
                                    "size": 0, "created": None, "updated": None, "captured": None, "ingested": None})

    seen: set[tuple[str, str, str]] = set()

    def add(frm: str, to: str, kind: str) -> None:
        if frm in nodes and to in nodes and (frm, to, kind) not in seen:
            seen.add((frm, to, kind))
            edges.append({"from": frm, "to": to, "kind": kind})

    for d in scan.docs.values():
        for t in d.links:
            add(d.rel, t, "link")
        for t in d.tags:
            add(d.rel, f"tag:{t}", "tag")
        src = d.meta.get("source")
        if isinstance(src, dict) and src.get("local") and d.cluster:
            add(d.rel, f"{d.cluster}/{src['local']}", "source")
        srcs = d.meta.get("sources") or []
        for s in [srcs] if isinstance(srcs, str) else srcs:
            add(d.rel, str(s), "wiki")

    edges.sort(key=lambda e: (e["from"], e["to"], e["kind"]))
    return {"generated": now.isoformat(), "nodes": [nodes[k] for k in sorted(nodes)], "edges": edges}
