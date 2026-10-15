from __future__ import annotations

from pathlib import Path, PurePosixPath

from . import frontmatter as fm, sources
from .extract import extract
from .intake import LARGE_BYTES, ItemResult, Report, _free, _heading, _known
from .vault import scan

default_fetch = sources.default_fetch


def _update(vault: Path, rel: str, data: bytes, filename: str, now: str) -> ItemResult:
    """Replace a companion's snapshot in place: original, extracted text, hash, dates."""
    path = vault / rel
    doc = fm.read(path)
    meta = doc.meta
    source = meta.setdefault("source", {})
    h = sources.sha256(data)
    if source.get("hash") == h:
        return ItemResult(rel, "unchanged", companion=rel)
    by_hash, _ = _known(vault)
    if by_hash.get(h, rel) != rel:
        return ItemResult(rel, "duplicate", companion=rel, note=f"same content as {by_hash[h]}")

    cluster_dir = path.parent
    old_local = source.get("local")
    old_path = (cluster_dir / old_local) if old_local else None
    if old_path and old_path.is_file() and old_path.suffix == PurePosixPath(filename).suffix:
        orig = old_path
    else:
        orig = _free(cluster_dir / "_originals" / filename)
    previous = orig.read_bytes() if orig.exists() else None
    orig.parent.mkdir(parents=True, exist_ok=True)
    orig.write_bytes(data)
    try:
        ex = extract(orig)
        old_title = str(meta.get("title") or "")
        if not old_title or old_title == source.get("url") or old_title == path.stem:
            meta["title"] = ex.title or _heading(ex.markdown) or old_title or path.stem
        source.update({"local": f"_originals/{orig.name}", "hash": h, "captured": now})
        meta["snapshot"] = "ok"
        meta["extraction"] = ex.status
        if ex.error:
            meta["extraction_error"] = ex.error
        else:
            meta.pop("extraction_error", None)
        if len(data) > LARGE_BYTES:
            meta["large"] = True
        else:
            meta.pop("large", None)
        meta["updated"] = now
        body = f"# {meta['title']}\n\n## Summary\n\n## Extracted text\n" + ex.markdown
        fm.write(path, fm.Document(meta, body))
    except Exception as e:
        if previous is None:
            orig.unlink(missing_ok=True)
        else:
            orig.write_bytes(previous)
        return ItemResult(rel, "failed", companion=rel, note=f"{type(e).__name__}: {e}")
    if old_path and old_path != orig and old_path.is_file():
        old_path.unlink()
    return ItemResult(rel, "refreshed", companion=rel, original=orig.relative_to(vault).as_posix())


def _fetch(url: str, fetch) -> tuple[bytes | None, str, str | None]:
    res = sources.resolve(url, fetch=fetch)
    return res.data, res.filename, res.error


def retry_missing(vault: Path, *, fetch=None, now: str | None = None) -> Report:
    vault = vault.resolve()
    fetch = fetch or default_fetch
    now = now or fm.now_iso()
    report = Report()
    for d in sorted(scan(vault).docs.values(), key=lambda d: d.rel):
        src = d.meta.get("source")
        if d.type != "companion" or d.meta.get("snapshot") != "missing" or not isinstance(src, dict) or not src.get("url"):
            continue
        data, filename, err = _fetch(src["url"], fetch)
        if data is None:
            report.items.append(ItemResult(d.rel, "still-missing", companion=d.rel, note=err or "no data"))
            continue
        report.items.append(_update(vault, d.rel, data, filename, now))
    return report


def recapture(vault: Path, rel: str, *, fetch=None, now: str | None = None) -> ItemResult:
    vault = vault.resolve()
    fetch = fetch or default_fetch
    now = now or fm.now_iso()
    path = vault / rel
    if not rel.endswith(".md") or not path.is_file():
        return ItemResult(rel, "failed", note=f"no such vault file: {rel}")
    meta = fm.read(path).meta
    src = meta.get("source")
    if meta.get("type") != "companion" or not isinstance(src, dict) or not src.get("url"):
        return ItemResult(rel, "failed", companion=rel, note="no source.url to re-fetch (local files cannot be recaptured)")
    data, filename, err = _fetch(src["url"], fetch)
    if data is None:
        return ItemResult(rel, "failed", companion=rel, note=err or "no data")
    return _update(vault, rel, data, filename, now)
