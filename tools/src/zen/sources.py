from __future__ import annotations

import hashlib
import re
import time
import unicodedata
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

Fetcher = Callable[[str], tuple[bytes, str]]

_ARXIV_ID = r"(\d{4}\.\d{4,5}(?:v\d+)?|[a-z-]+(?:\.[A-Z]{2})?/\d{7}(?:v\d+)?)"
ARXIV_URL_RE = re.compile(r"^https?://(?:[a-z]+\.)?arxiv\.org/(?:abs|pdf)/" + _ARXIV_ID + r"(?:\.pdf)?/?(?:[?#].*)?$", re.I)
ARXIV_BARE_RE = re.compile(r"^(?:arxiv:)?" + _ARXIV_ID + r"$", re.I)
DOI_RE = re.compile(r"^(?:https?://(?:dx\.)?doi\.org/|doi:)?(10\.\d{4,9}/\S+)$", re.I)
MAX_BYTES = 200 * 1024 * 1024
DEADLINE_S = 300
USER_AGENT = "zen-intake/0.1 (+https://github.com/mabstruct/zen)"
PDF_TYPES = ("application/pdf", "application/x-pdf")


@dataclass
class Resolved:
    kind: str
    url: str | None
    filename: str
    data: bytes | None
    error: str | None = None


def classify(spec: str) -> tuple[str, str]:
    s = spec.strip()
    if Path(s).exists():
        return "file", s
    if m := ARXIV_URL_RE.match(s):
        return "arxiv", m.group(1)
    if m := ARXIV_BARE_RE.match(s):
        return "arxiv", m.group(1)
    if m := DOI_RE.match(s):
        return "doi", m.group(1)
    if re.match(r"^https?://", s, re.I):
        return "url", s
    return "file", s


def slugify(name: str, max_len: int = 80) -> str:
    stem, dot, ext = name.rpartition(".")
    if not dot or "/" in ext or " " in ext or len(ext) > 5:
        stem, ext = name, ""
    stem = unicodedata.normalize("NFKD", stem).encode("ascii", "ignore").decode()
    stem = re.sub(r"[^a-z0-9]+", "-", stem.lower()).strip("-")[:max_len].strip("-") or "untitled"
    return f"{stem}.{ext.lower()}" if ext else stem


def _slug_stem(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:80].strip("-") or "untitled"


def sha256(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def default_fetch(url: str) -> tuple[bytes, str]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/pdf, text/html;q=0.9, */*;q=0.5"})
    start = time.monotonic()
    chunks: list[bytes] = []
    size = 0
    with urllib.request.urlopen(req, timeout=60) as resp:  # timeout is per socket operation
        while True:
            if time.monotonic() - start > DEADLINE_S:
                raise TimeoutError(f"download took longer than {DEADLINE_S} s")
            chunk = resp.read(1 << 16)
            if not chunk:
                break
            size += len(chunk)
            if size > MAX_BYTES:
                raise ValueError(f"download larger than {MAX_BYTES // (1 << 20)} MB")
            chunks.append(chunk)
        return b"".join(chunks), resp.headers.get("Content-Type", "") or ""


def _ext_for(content_type: str, fallback: str) -> str:
    ct = content_type.split(";")[0].strip().lower()
    if ct in PDF_TYPES:
        return "pdf"
    if ct in ("text/html", "application/xhtml+xml"):
        return "html"
    if ct == "text/plain":
        return "txt"
    if ct == "text/markdown":
        return "md"
    return fallback


def _url_slug(url: str) -> str:
    u = urlparse(url)
    base = (u.netloc + u.path).rstrip("/") or u.netloc
    return _slug_stem(f"{base}-{u.query}" if u.query else base)


def resolve(spec: str, fetch: Fetcher = default_fetch) -> Resolved:
    kind, ident = classify(spec)
    if kind == "file":
        p = Path(ident)
        if not p.is_file():
            return Resolved("file", None, slugify(p.name), None, f"file not found: {ident}")
        return Resolved("file", None, slugify(p.name), p.read_bytes())
    if kind == "arxiv":
        fetch_url, url, base = f"https://arxiv.org/pdf/{ident}", f"https://arxiv.org/abs/{ident}", ident.replace("/", "-")
    elif kind == "doi":
        fetch_url = url = f"https://doi.org/{ident}"
        base = _slug_stem(ident)
    else:
        fetch_url = url = ident
        base = _url_slug(ident)
    try:
        result = fetch(fetch_url)
    except Exception as e:  # network boundary: any failure is reported, never raised
        fallback = "pdf" if kind in ("arxiv", "doi") else "html"
        return Resolved(kind, url, f"{base}.{fallback}", None, f"{type(e).__name__}: {e}")
    data, ctype = result
    ext = _ext_for(ctype, "pdf" if kind in ("arxiv", "doi") else "html")
    return Resolved(kind, url, f"{base}.{ext}", data)
