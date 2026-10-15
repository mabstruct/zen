from __future__ import annotations

import argparse
import contextlib
import io
import posixpath
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from urllib.parse import quote, unquote

from . import frontmatter as fm, index_cli
from .intake import INBOX, _free
from .vault import FENCE_RE, MD_LINK_RE, TITLE_RE, scan

CLUSTER_NAME_RE = re.compile(r"1\d_[^/\\]+")
FM_BLOCK_RE = re.compile(r"\A---\r?\n.*?\r?\n---\r?\n?", re.DOTALL)


@dataclass
class MoveResult:
    status: str  # moved | planned | refused
    new_path: str | None = None
    note: str = ""
    rewritten: list[str] = field(default_factory=list)


def _norm(rel_dir: str, target: str) -> str:
    joined = posixpath.normpath(posixpath.join(rel_dir, target)) if not target.startswith("/") else target.lstrip("/")
    return joined


def _rel(from_dir: str, to: str) -> str:
    return posixpath.relpath(to, from_dir or ".")


def _rewrite_links(body: str, from_dir_old: str, from_dir_new: str, mapping: dict[str, str]) -> str:
    """Rewrite markdown link targets in body (outside code fences).

    A link is rewritten when the path it resolves to (from from_dir_old) is a key in mapping,
    or when from_dir_new differs from from_dir_old (the containing doc moved)."""

    def sub(m: re.Match) -> str:
        angle, bare = m.group(1), m.group(2)
        raw = angle if angle is not None else bare
        title = ""
        if angle is None:
            t = TITLE_RE.search(raw)
            if t:
                title, raw = t.group(0), raw[: t.start()]
        lead = len(raw) - len(raw.lstrip())
        target = raw.strip()
        if not target or "://" in target or target.startswith(("mailto:", "#")):
            return m.group(0)
        path, _, frag = target.partition("#")
        decoded = unquote(path)
        resolved = _norm(from_dir_old, decoded)
        new_target = mapping.get(resolved, resolved)
        if new_target == resolved and from_dir_new == from_dir_old:
            return m.group(0)
        new_rel = _rel(from_dir_new, new_target)
        if new_rel == decoded:
            return m.group(0)
        frag_s = f"#{frag}" if frag else ""
        text = m.group(0)[: m.group(0).index("](") + 2]
        if angle is not None or (" " in new_rel and "%20" not in path):
            return f"{text}<{new_rel}{frag_s}>)"
        enc = quote(new_rel, safe="/._-~") if "%" in path else new_rel
        return f"{text}{' ' * lead}{enc}{frag_s}{title})"

    out, fence = [], None
    for line in body.split("\n"):
        mf = FENCE_RE.match(line)
        if fence is None and mf:
            fence = mf.group(1)
            out.append(line)
        elif fence is not None:
            if mf and mf.group(1)[0] == fence[0] and len(mf.group(1)) >= len(fence):
                fence = None
            out.append(line)
        else:
            out.append(MD_LINK_RE.sub(sub, line))
    return "\n".join(out)


def _split(text: str) -> tuple[str, str]:
    m = FM_BLOCK_RE.match(text)
    return (text[: m.end()], text[m.end():]) if m else ("", text)


def _replace_path_token(text: str, old: str, new: str) -> str:
    return re.sub(rf"(?<![\w/.-]){re.escape(old)}(?![\w/.-])", new, text)


def run(vault: Path, rel: str, cluster: str, *, now: str | None = None, dry_run: bool = False) -> MoveResult:
    vault = vault.resolve()
    now = now or fm.now_iso()
    rel = rel.strip().lstrip("./") if not rel.startswith("..") else rel
    src = vault / rel
    parts = PurePosixPath(rel).parts
    if not rel.endswith(".md") or not src.is_file():
        return MoveResult("refused", note=f"not a vault markdown file: {rel}")
    if len(parts) != 2 or not (CLUSTER_NAME_RE.fullmatch(parts[0]) or parts[0] == INBOX):
        return MoveResult("refused", note=f"only files directly in a cluster or {INBOX}/ can be moved: {rel}")
    if not CLUSTER_NAME_RE.fullmatch(cluster) or not (vault / cluster).is_dir():
        return MoveResult("refused", note=f"unknown cluster: {cluster}")
    if parts[0] == cluster:
        return MoveResult("refused", note=f"{rel} is already in {cluster}")

    old_dir, new_dir = parts[0], cluster
    new_doc = _free(vault / new_dir / parts[1])
    new_rel = new_doc.relative_to(vault).as_posix()
    mapping = {rel: new_rel}

    text = src.read_text(encoding="utf-8")
    try:
        meta = fm.parse(text).meta
    except Exception:
        meta = {}
    old_orig = new_orig = None
    local = (meta.get("source") or {}).get("local") if isinstance(meta.get("source"), dict) else None
    if local:
        candidate = (vault / old_dir / local).resolve()
        if candidate.is_file() and candidate.is_relative_to((vault / old_dir).resolve()):
            old_orig = candidate.relative_to(vault).as_posix()
            new_orig_path = _free(vault / new_dir / "_originals" / candidate.name)
            new_orig = new_orig_path.relative_to(vault).as_posix()
            mapping[old_orig] = new_orig

    s = scan(vault)
    referrers = sorted(d.rel for d in s.docs.values() if d.rel != rel and rel in d.links)
    citing = sorted(d.rel for d in s.docs.values() if d.rel != rel and rel in [str(x) for x in (d.meta.get("sources") or [])])
    touched = sorted(set(referrers) | set(citing))

    if dry_run:
        print(f"move {rel} → {new_rel}")
        if old_orig:
            print(f"move {old_orig} → {new_orig}")
        for t in touched:
            print(f"rewrite {t}")
        return MoveResult("planned", new_path=new_rel, rewritten=touched)

    broken_before = len(s.broken_links)
    backups: dict[Path, str] = {}

    def save(p: Path, content: str) -> None:
        if p not in backups and p.exists():
            backups[p] = p.read_text(encoding="utf-8")
        p.write_text(content, encoding="utf-8")

    moved: list[tuple[Path, Path]] = []
    try:
        head, body = _split(text)
        if old_orig and new_orig and PurePosixPath(old_orig).name != PurePosixPath(new_orig).name:
            head = head.replace(f"_originals/{PurePosixPath(old_orig).name}", f"_originals/{PurePosixPath(new_orig).name}")
        new_text = head + _rewrite_links(body, old_dir, new_dir, mapping)
        if old_orig and new_orig:
            dst = vault / new_orig
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(vault / old_orig), dst)
            moved.append((vault / old_orig, dst))
        new_doc.parent.mkdir(parents=True, exist_ok=True)
        new_doc.write_text(new_text, encoding="utf-8")
        backups[src] = text
        src.unlink()
        moved.append((src, new_doc))

        for t in touched:
            p = vault / t
            t_text = p.read_text(encoding="utf-8")
            t_head, t_body = _split(t_text)
            if t in citing:
                t_head = _replace_path_token(t_head, rel, new_rel)
            t_dir = posixpath.dirname(t)
            t_body = _rewrite_links(t_body, t_dir, t_dir, mapping)
            if t_head + t_body != t_text:
                save(p, t_head + t_body)

        log = vault / "90_wiki" / "LOG.md"
        if log.exists():
            entry = f"\n## {now} move {rel} → {new_rel}\n"
            if old_orig:
                entry += f"- original: {old_orig} → {new_orig}\n"
            entry += f"- rewritten: {', '.join(touched) if touched else 'none'}\n"
            save(log, log.read_text(encoding="utf-8").rstrip("\n") + "\n" + entry)

        if len(scan(vault).broken_links) > broken_before:
            raise RuntimeError("move would add broken links")
    except Exception as e:
        for p, content in backups.items():
            if p == src:
                continue
            p.write_text(content, encoding="utf-8")
        for a, b in reversed(moved):
            if b.exists():
                if a == src:
                    b.unlink()
                    src.write_text(text, encoding="utf-8")
                else:
                    shutil.move(str(b), a)
        return MoveResult("refused", note=f"rolled back: {type(e).__name__}: {e}")

    with contextlib.redirect_stdout(io.StringIO()):
        index_cli.run(vault)
    return MoveResult("moved", new_path=new_rel, rewritten=touched)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="zen-move", description="Move a note or companion (and its original) to another cluster, rewriting every reference. No AI.")
    ap.add_argument("path", help="vault-relative path, e.g. 15_era/sample-seventh.md")
    ap.add_argument("--cluster", required=True, help="target cluster folder, e.g. 15_cosmology")
    ap.add_argument("--vault", type=Path, default=Path("vault"))
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    r = run(a.vault, a.path, a.cluster, dry_run=a.dry_run)
    if r.status == "moved":
        print(f"moved {a.path} → {r.new_path}; rewrote {len(r.rewritten)} file(s): {', '.join(r.rewritten) or 'none'}")
    elif r.status == "refused":
        print(f"refused: {r.note}")
    return 0 if r.status in ("moved", "planned") else 1


if __name__ == "__main__":
    raise SystemExit(main())
