from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path, PurePosixPath
from urllib.parse import unquote

import yaml

from . import frontmatter as fm

SKIP_DIRS = {"_meta", "_originals", "02_templates", ".git", ".qmd", ".obsidian"}
GENERATED_FILES = {"INDEX.md"}
MD_LINK_RE = re.compile(r"(?<!!)\[[^\]]*\]\(\s*(?:<([^>]*)>[^)]*|([^)]*))\)")
TITLE_RE = re.compile(r"\s+\"[^\"]*\"\s*$")
WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")
CONFLICT_RE = re.compile(r"^> \[!conflict\] (#c-\d+) — open\s*$", re.M)
HEADING_RE = re.compile(r"^#\s+(.+?)\s*$", re.M)
CLUSTER_RE = re.compile(r"^1\d_")


@dataclass
class Doc:
    rel: str
    cluster: str | None
    title: str
    type: str
    tags: list[str]
    meta: dict
    links: list[str]
    summary: str
    created: str | None
    updated: str
    captured: str | None
    ingested: str | None
    size: int
    open_conflicts: list[str] = field(default_factory=list)
    inbound: int = 0
    frontmatter_error: str | None = None


@dataclass
class Cluster:
    name: str
    description: str
    notes: int = 0
    companions: int = 0
    originals: int = 0


@dataclass
class VaultScan:
    root: Path
    docs: dict[str, Doc]
    clusters: list[Cluster]
    originals: list[str]
    broken_links: list[tuple[str, str]]
    inbox: list[str]


def cluster_of(rel: str) -> str | None:
    head = PurePosixPath(rel).parts[0]
    return head if re.match(r"^\d\d_", head) else None


def _mtime_iso(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime).astimezone().replace(microsecond=0).isoformat()


def _summary_of(body: str) -> str:
    in_summary = False
    for line in body.splitlines():
        if line.startswith("## "):
            if in_summary:
                return ""
            in_summary = line.strip() == "## Summary"
            continue
        if in_summary and line.strip():
            return line.strip()
    return ""


def _tags_of(meta: dict) -> list[str]:
    raw = meta.get("tags")
    if raw is None:
        return []
    if isinstance(raw, str):
        return [raw]
    if isinstance(raw, list):
        return [str(t) for t in raw]
    return [str(raw)]


def _title_of(meta: dict, body: str, path: Path) -> str:
    if meta.get("title"):
        return str(meta["title"])
    m = HEADING_RE.search(body)
    return m.group(1) if m else path.stem


def _type_of(meta: dict, rel: str) -> str:
    if meta.get("type"):
        return str(meta["type"])
    return "wiki-meta" if rel.startswith("90_wiki/") else "note"


FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
BLOCKQUOTE_RE = re.compile(r"^(?:\s*>\s?)+")
INLINE_CODE_RE = re.compile(r"(?<!`)(`+)(?!`)(.+?)(?<!`)\1(?!`)")


def _strip_code(body: str) -> str:
    out: list[str] = []
    fence: str | None = None
    for line in body.split("\n"):
        m = FENCE_RE.match(BLOCKQUOTE_RE.sub("", line))
        if fence is None:
            if m:
                fence = m.group(1)[0] * len(m.group(1))
                out.append("")
            else:
                out.append(INLINE_CODE_RE.sub(" ", line))
        else:
            out.append("")
            if m and m.group(1)[0] == fence[0] and len(m.group(1)) >= len(fence) and not BLOCKQUOTE_RE.sub("", line).strip().strip(fence[0]):
                fence = None
    return "\n".join(out)


def _raw_links(body: str) -> tuple[list[str], list[str]]:
    md: list[str] = []
    for angle, bare in MD_LINK_RE.findall(body):
        t = angle if angle else TITLE_RE.sub("", bare.strip())
        t = unquote(t.split("#")[0].strip())
        if t and "://" not in t and not t.startswith("mailto:"):
            md.append(t)
    wiki = [w.strip() for w in WIKILINK_RE.findall(body)]
    return md, wiki


def _resolve_md(rel_dir: PurePosixPath, target: str) -> str:
    joined = rel_dir / target if not target.startswith("/") else PurePosixPath(target.lstrip("/"))
    parts: list[str] = []
    for part in joined.parts:
        if part == "..":
            if parts:
                parts.pop()
        elif part != ".":
            parts.append(part)
    out = "/".join(parts)
    return out if PurePosixPath(out).suffix else out + ".md"


def _resolve_wikilink(name: str, rel_dir: PurePosixPath, docs: dict, by_title: dict, by_stem: dict) -> str | None:
    key = name[:-3] if name.lower().endswith(".md") else name
    for cand in (key + ".md", _resolve_md(rel_dir, key + ".md")):
        if cand in docs:
            return cand
    return by_title.get(name.lower()) or by_title.get(key.lower()) or by_stem.get(PurePosixPath(key).name.lower())


def scan(root: Path) -> VaultScan:
    root = root.resolve()
    docs: dict[str, Doc] = {}
    originals: list[str] = []
    pending_wikilinks: dict[str, list[str]] = {}
    cluster_desc: dict[str, str] = {}
    cluster_dirs: list[str] = []

    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = PurePosixPath(Path(dirpath).relative_to(root).as_posix()) if dirpath != str(root) else PurePosixPath()
        if rel_dir.parts and rel_dir.parts[0] not in cluster_dirs and CLUSTER_RE.match(rel_dir.parts[0]):
            cluster_dirs.append(rel_dir.parts[0])
        if Path(dirpath).name == "_originals":
            for f in filenames:
                if not f.startswith("."):
                    originals.append((rel_dir / f).as_posix())
            dirnames[:] = []
            continue
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS or d == "_originals")
        for f in sorted(filenames):
            if not f.endswith(".md") or f.startswith("."):
                continue
            rel = (rel_dir / f).as_posix()
            if rel in GENERATED_FILES:
                continue
            path = root / rel
            if f == "_cluster.md":
                if not rel_dir.parts:
                    continue
                text = path.read_text(encoding="utf-8").strip()
                cluster_desc[rel_dir.parts[0]] = text.splitlines()[0] if text else ""
                continue
            fm_error: str | None = None
            try:
                doc = fm.read(path)
            except (ValueError, yaml.YAMLError) as e:
                doc = fm.Document({}, path.read_text(encoding="utf-8"))
                lines = f"{type(e).__name__}: {e}".splitlines()
                fm_error = lines[0] if lines else type(e).__name__
            code_free = _strip_code(doc.body)
            md_links, wiki_links = _raw_links(code_free)
            links = [_resolve_md(rel_dir, t) for t in md_links]
            pending_wikilinks[rel] = wiki_links
            docs[rel] = Doc(
                rel=rel,
                cluster=cluster_of(rel),
                title=_title_of(doc.meta, doc.body, path),
                type=_type_of(doc.meta, rel),
                tags=_tags_of(doc.meta),
                meta=doc.meta,
                links=links,
                summary=_summary_of(doc.body),
                created=doc.meta.get("created"),
                updated=doc.meta.get("updated") or _mtime_iso(path),
                captured=(doc.meta.get("source") or {}).get("captured") if isinstance(doc.meta.get("source"), dict) else None,
                ingested=doc.meta.get("ingested"),
                size=path.stat().st_size,
                open_conflicts=CONFLICT_RE.findall(code_free),
                frontmatter_error=fm_error,
            )

    by_title = {d.title.lower(): d.rel for d in docs.values()}
    by_stem = {PurePosixPath(d.rel).stem.lower(): d.rel for d in docs.values()}
    broken: list[tuple[str, str]] = []
    for rel, names in pending_wikilinks.items():
        rel_dir = PurePosixPath(rel).parent
        for name in names:
            target = _resolve_wikilink(name, rel_dir, docs, by_title, by_stem)
            if target:
                docs[rel].links.append(target)
            else:
                broken.append((rel, f"[[{name}]]"))
    for d in docs.values():
        kept: list[str] = []
        counted: set[str] = set()
        for target in d.links:
            if target not in docs and not (root / target).exists() and target + ".md" in docs:
                target = target + ".md"
            if target in docs:
                kept.append(target)
                if target not in counted:
                    counted.add(target)
                    docs[target].inbound += 1
            elif (root / target).exists():
                continue
            else:
                kept.append(target)
                if (d.rel, target) not in broken:
                    broken.append((d.rel, target))
        d.links = kept

    clusters: list[Cluster] = []
    for name in sorted(cluster_dirs):
        c = Cluster(name=name, description=cluster_desc.get(name) or name)
        for d in docs.values():
            if d.cluster == name:
                if d.type == "companion":
                    c.companions += 1
                else:
                    c.notes += 1
        c.originals = sum(1 for o in originals if o.startswith(name + "/"))
        clusters.append(c)

    inbox = sorted(rel for rel in docs if rel.startswith("00_inbox/"))
    return VaultScan(root=root, docs=docs, clusters=clusters, originals=sorted(originals), broken_links=broken, inbox=inbox)
