"""Split a long companion into sections for a sectioned (book) ingest. No AI.

Uses the page markers that PDF extraction writes (`<!-- page N -->`) and each page's running
head. A head that repeats on a large share of pages is the book title and carries no section
information; heads are normalised against OCR noise before they are compared. Without page
markers the text is cut into size-based parts at paragraph boundaries."""
from __future__ import annotations

import difflib
import re
from collections import Counter
from dataclasses import dataclass, field

PAGE_RE = re.compile(r"^<!-- page (\d+) -->$")
NUM_RE = re.compile(r"^(?:\d+|[ivxlcdm]+)$", re.I)
LEAD_NUM_RE = re.compile(r"^\s*[0-9ivxl]+\.\s*")
TITLE_SHARE = 0.2
FUZZY = 0.85


@dataclass
class Section:
    title: str
    first_page: int | None
    last_page: int | None
    start_line: int  # 1-based, inclusive, in the companion file
    end_line: int
    tokens: int
    heads: list[str] = field(default_factory=list)


def _key(head: str) -> str:
    s = head.lower().replace("/", "l")
    s = LEAD_NUM_RE.sub("", s)
    return re.sub(r"[^a-z0-9]", "", s)


def _tokens(lines: list[str]) -> int:
    return sum(len(l) + 1 for l in lines) // 4


def _extracted_start(lines: list[str]) -> int:
    for i, l in enumerate(lines):
        if l.strip() == "## Extracted text":
            return i + 1
    return 0


def _fallback(lines: list[str], start: int, max_tokens: int) -> list[Section]:
    """Size-based parts at paragraph boundaries (blank lines)."""
    out: list[Section] = []
    first, tok = start, 0
    for i in range(start, len(lines)):
        tok += (len(lines[i]) + 1) // 4
        boundary = not lines[i].strip()
        if boundary and tok >= max_tokens * 0.9 and i > first:
            out.append(Section(f"Part {len(out) + 1}", None, None, first + 1, i + 1, tok))
            first, tok = i + 1, 0
    if first < len(lines):
        out.append(Section(f"Part {len(out) + 1}", None, None, first + 1, len(lines), tok))
    return out


def build(text: str, *, max_tokens: int = 30000, merge: bool = True) -> list[Section]:
    lines = text.splitlines()
    start = _extracted_start(lines)
    markers = [(i, int(m.group(1))) for i in range(start, len(lines)) if (m := PAGE_RE.match(lines[i].strip()))]
    if not markers:
        return _fallback(lines, start, max_tokens)

    pages = []  # (page number, first line index, last line index, body lines)
    for k, (idx, num) in enumerate(markers):
        end = markers[k + 1][0] - 1 if k + 1 < len(markers) else len(lines) - 1
        pages.append((num, idx, end, lines[idx + 1:end + 1]))

    raw_heads: list[str | None] = []
    for _, _, _, body in pages:
        cand = [l.strip() for l in body if l.strip()][:3]
        heads = [l for l in cand[:2] if not NUM_RE.match(l)]
        raw_heads.append(heads[0] if heads else None)

    counts = Counter(_key(h) for h in raw_heads if h)
    parity: dict[str, Counter] = {}
    for (num, *_), h in zip(pages, raw_heads):
        if h:
            parity.setdefault(_key(h), Counter())[num % 2] += 1
    # the book title: frequent, and printed on one side of the spread only
    frequent = {k for k, n in counts.items()
                if n / len(pages) > TITLE_SHARE and max(parity[k].values()) / n >= 0.8}
    ignored = set(frequent) | {k for k in counts if any(difflib.SequenceMatcher(None, k, f).ratio() >= FUZZY for f in frequent)}
    display = {}
    for h in raw_heads:
        if h:
            display.setdefault(_key(h), Counter())[h] += 1

    # per page: section key, "title" (book-title page: stays with previous), or None (no head: goes forward)
    marks: list[str | None] = []
    for h in raw_heads:
        k = _key(h) if h else None
        if k in ignored:
            marks.append("title")
        elif k and counts[k] >= 2:
            marks.append(k)
        else:
            marks.append(None)

    known = [m if m not in (None, "title") else None for m in marks]
    assigned: list[str | None] = known[:]
    for i, m in enumerate(marks):
        if assigned[i]:
            continue
        prev = next((assigned[j] for j in range(i - 1, -1, -1) if assigned[j]), None)
        nxt = next((known[j] for j in range(i + 1, len(known)) if known[j]), None)
        assigned[i] = (prev or nxt) if m == "title" else (nxt or prev)
    if not any(assigned):
        return _fallback(lines, start, max_tokens)

    groups: list[list[int]] = []
    for i, key in enumerate(assigned):
        if groups and assigned[groups[-1][-1]] == key:
            groups[-1].append(i)
        else:
            groups.append([i])

    def make(idx: list[int], title: str, heads: list[str]) -> Section:
        first, last = pages[idx[0]], pages[idx[-1]]
        body = [l for i in idx for l in pages[i][3]]
        return Section(title, first[0], last[0], first[1] + 1, last[2] + 1, _tokens(body), heads)

    raw: list[Section] = []
    for g in groups:
        key = assigned[g[0]]
        head = display[key].most_common(1)[0][0] if key in display else "Front matter"
        sec = make(g, head, [head])
        if sec.tokens <= max_tokens or len(g) == 1:
            raw.append(sec)
            continue
        part, n = [], 1
        for i in g:
            if part and make(part + [i], "", []).tokens > max_tokens:
                raw.append(make(part, f"{head} (part {n})", [head]))
                part, n = [], n + 1
            part.append(i)
        raw.append(make(part, f"{head} (part {n})", [head]))

    if not merge:
        return raw
    out: list[Section] = []
    for s in raw:
        if out and out[-1].tokens + s.tokens <= max_tokens:
            a = out[-1]
            heads = a.heads + [h for h in s.heads if h not in a.heads]
            out[-1] = Section(f"{heads[0]} – {heads[-1]}" if len(heads) > 1 else heads[0],
                              a.first_page, s.last_page, a.start_line, s.end_line, a.tokens + s.tokens, heads)
        else:
            out.append(s)
    return out
