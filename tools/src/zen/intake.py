from __future__ import annotations

import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from . import frontmatter as fm, sources
from .extract import extract
from .vault import scan

LARGE_BYTES = 50 * 1024 * 1024
INBOX = "00_inbox"


@dataclass
class ItemResult:
    input: str
    status: str
    companion: str | None = None
    original: str | None = None
    note: str = ""


@dataclass
class Report:
    items: list[ItemResult] = field(default_factory=list)

    def summary(self) -> str:
        counts = {s: sum(1 for i in self.items if i.status == s) for s in ("filed", "inbox", "duplicate", "failed")}
        lines = [", ".join(f"{k}: {v}" for k, v in counts.items())]
        for i in self.items:
            where = i.companion or "-"
            lines.append(f"  {i.status:9} {i.input} -> {where}{(' (' + i.note + ')') if i.note else ''}")
        return "\n".join(lines)


def _target_dir(vault: Path, cluster: str | None) -> tuple[Path, str] | str:
    if cluster is None:
        return vault / INBOX, "inbox"
    if not re.fullmatch(r"1\d_[^/\\]+", cluster) or not (vault / cluster).is_dir():
        return f"unknown cluster: {cluster}"
    return vault / cluster, "filed"


def _free(path: Path) -> Path:
    if not path.exists():
        return path
    n = 2
    while True:
        cand = path.with_name(f"{path.stem}-{n}{path.suffix}")
        if not cand.exists():
            return cand
        n += 1


def _known(vault: Path) -> tuple[dict[str, str], dict[str, str]]:
    by_hash: dict[str, str] = {}
    by_url: dict[str, str] = {}
    for d in scan(vault).docs.values():
        src = d.meta.get("source")
        if isinstance(src, dict):
            if src.get("hash"):
                by_hash[src["hash"]] = d.rel
            if src.get("url"):
                by_url[src["url"]] = d.rel
    return by_hash, by_url


def intake_item(vault: Path, spec: str, cluster: str | None, *, fetch=sources.default_fetch, now: str | None = None,
                known: tuple[dict, dict] | None = None) -> ItemResult:
    vault = vault.resolve()
    now = now or fm.now_iso()
    target = _target_dir(vault, cluster)
    if isinstance(target, str):
        return ItemResult(spec, "failed", note=target)
    target_dir, status = target

    res = sources.resolve(spec, fetch=fetch)
    if res.kind == "file" and res.data is None:
        return ItemResult(spec, "failed", note=res.error or "unreadable")

    by_hash, by_url = known if known is not None else _known(vault)
    if res.url and res.url in by_url:
        return ItemResult(spec, "duplicate", companion=by_url[res.url], note="same url already in vault")

    source: dict = {"kind": res.kind}
    if res.url:
        source["url"] = res.url
    meta: dict = {"title": "", "type": "companion", "created": now, "updated": now, "tags": [], "source": source}
    body_text = ""
    original_rel: str | None = None
    stem = PurePosixPath(res.filename).stem

    if res.data is None:
        source["captured"] = now
        meta["snapshot"] = "missing"
        meta["extraction"] = "none"
        meta["title"] = res.url or stem
    else:
        h = sources.sha256(res.data)
        dup = by_hash.get(h)
        if dup:
            return ItemResult(spec, "duplicate", companion=dup, note="same content already in vault")
        orig_path = _free(target_dir / "_originals" / res.filename)
        orig_path.parent.mkdir(parents=True, exist_ok=True)
        src_path = Path(spec) if res.kind == "file" else None
        moved = bool(src_path and src_path.resolve().is_relative_to(vault / INBOX))
        if moved:
            shutil.move(str(src_path), orig_path)
        else:
            orig_path.write_bytes(res.data)
        try:
            stem = orig_path.stem
            ex = extract(orig_path)
            source.update({"local": f"_originals/{orig_path.name}", "hash": h, "captured": now})
            meta["snapshot"] = "ok"
            meta["extraction"] = ex.status
            if ex.error:
                meta["extraction_error"] = ex.error
            if len(res.data) > LARGE_BYTES:
                meta["large"] = True
            meta["title"] = ex.title or _heading(ex.markdown) or stem
            body_text = ex.markdown
            original_rel = orig_path.relative_to(vault).as_posix()
            comp_path = _free(target_dir / f"{stem}.md")
            fm.write(comp_path, fm.Document(meta, f"# {meta['title']}\n\n## Summary\n\n## Extracted text\n" + body_text))
        except Exception as e:
            if moved:
                shutil.move(str(orig_path), src_path)
            else:
                orig_path.unlink(missing_ok=True)
            return ItemResult(spec, "failed", note=f"{type(e).__name__}: {e}")
        by_hash[h] = comp_path.relative_to(vault).as_posix()
        if res.url:
            by_url[res.url] = by_hash[h]
        return ItemResult(spec, status, companion=comp_path.relative_to(vault).as_posix(), original=original_rel, note="")

    comp_path = _free(target_dir / f"{stem}.md")
    fm.write(comp_path, fm.Document(meta, f"# {meta['title']}\n\n## Summary\n\n## Extracted text\n"))
    if res.url:
        by_url[res.url] = comp_path.relative_to(vault).as_posix()
    return ItemResult(spec, status, companion=comp_path.relative_to(vault).as_posix(), original=None, note=res.error or "")


def _heading(markdown: str) -> str | None:
    for line in markdown.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return None


def _normalise_note(path: Path, now: str) -> tuple[fm.Document, str | None]:
    doc = fm.read(path)
    cluster = doc.meta.pop("cluster", None)
    tags = doc.meta.get("tags")
    doc.meta["tags"] = [tags] if isinstance(tags, str) else [str(t) for t in (tags or [])]
    doc.meta.setdefault("title", _heading(doc.body) or path.stem)
    doc.meta.setdefault("type", "note")
    doc.meta.setdefault("created", now)
    doc.meta.setdefault("updated", now)
    ordered = {k: doc.meta[k] for k in ("title", "type", "created", "updated", "tags") if k in doc.meta}
    ordered.update({k: v for k, v in doc.meta.items() if k not in ordered})
    return fm.Document(ordered, doc.body), (str(cluster) if cluster else None)


def _file_note(vault: Path, path: Path, doc: fm.Document, target_dir: Path) -> str:
    src = doc.meta.get("source")
    local = src.get("local") if isinstance(src, dict) and doc.meta.get("type") == "companion" else None
    moved_orig: tuple[Path, Path] | None = None
    if local:
        old = vault / INBOX / str(local)
        if old.resolve().is_relative_to((vault / INBOX / "_originals").resolve()) and old.is_file():
            new = _free(target_dir / "_originals" / Path(local).name)
            new.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(old), new)
            moved_orig = (old, new)
            src["local"] = f"_originals/{new.name}"
    dest = _free(target_dir / path.name)
    try:
        fm.write(dest, doc)
    except Exception:
        if moved_orig:
            shutil.move(str(moved_orig[1]), moved_orig[0])
        raise
    path.unlink()
    return dest.relative_to(vault).as_posix()


def intake_inbox(vault: Path, cluster: str | None, *, fetch=sources.default_fetch, now: str | None = None) -> Report:
    vault = vault.resolve()
    now = now or fm.now_iso()
    inbox = vault / INBOX
    report = Report()
    known = _known(vault)
    for path in sorted(inbox.iterdir()):
        if path.is_dir() or path.name.startswith("."):
            continue
        rel = path.relative_to(vault).as_posix()
        try:
            if path.suffix.lower() == ".md":
                doc, note_cluster = _normalise_note(path, now)
                chosen = cluster or note_cluster
                target = _target_dir(vault, chosen)
                if isinstance(target, str):
                    report.items.append(ItemResult(rel, "failed", note=target))
                    continue
                target_dir, status = target
                if status == "inbox":
                    fm.write(path, doc)
                    report.items.append(ItemResult(rel, "inbox", companion=rel, note="no cluster"))
                else:
                    report.items.append(ItemResult(rel, "filed", companion=_file_note(vault, path, doc, target_dir)))
            else:
                report.items.append(intake_item(vault, str(path), cluster, fetch=fetch, now=now, known=known))
        except Exception as e:
            report.items.append(ItemResult(rel, "failed", note=f"{type(e).__name__}: {e}"))
    return report
