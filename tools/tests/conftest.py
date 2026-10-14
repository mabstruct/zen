from __future__ import annotations

import os
from pathlib import Path

import pytest

FIXED_NOW = "2026-10-14T12:00:00+02:00"


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def make_pdf(text: str) -> bytes:
    stream = f"BT /F1 18 Tf 20 40 Td ({text}) Tj ET".encode()
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 100] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = b"%PDF-1.4\n"
    offsets = []
    for i, o in enumerate(objs, 1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + o + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return out


@pytest.fixture
def vault(tmp_path: Path) -> Path:
    """A small but complete vault. Timestamps are fixed strings."""
    v = tmp_path / "vault"
    (v / "_meta").mkdir(parents=True)
    (v / "00_inbox").mkdir()
    (v / "01_daily").mkdir()
    write(v / "02_templates" / "note.md", "---\ntitle: ''\ntype: note\n---\n")
    write(v / "10_ai" / "_cluster.md", "AI research and tooling\n")
    write(
        v / "10_ai" / "attention.md",
        "---\ntitle: Attention Is All You Need\ntype: companion\n"
        "created: 2026-10-01T10:00:00+02:00\nupdated: 2026-10-01T10:00:00+02:00\n"
        "tags: [transformers]\nsource:\n  kind: arxiv\n  url: https://arxiv.org/abs/1706.03762\n"
        "  local: _originals/1706.03762.pdf\n  hash: sha256:abc\n  captured: 2026-10-01T10:00:00+02:00\n"
        "snapshot: ok\nextraction: ok\n---\n## Summary\nThe transformer paper.\n\n## Extracted text\nlong text\n\nSee [pdf](_originals/1706.03762.pdf) and [gone](_originals/none.pdf).\n",
    )
    (v / "10_ai" / "_originals").mkdir()
    (v / "10_ai" / "_originals" / "1706.03762.pdf").write_bytes(b"%PDF-1.4 fake")
    write(
        v / "10_ai" / "my note.md",
        "---\ntitle: Notes on attention\ntype: note\ncreated: 2026-10-02T09:00:00+02:00\n"
        "updated: 2026-10-05T09:00:00+02:00\ningested: 2026-10-03T09:00:00+02:00\ntags: ai\n---\n"
        "See [the paper](attention.md) and [[Orphan]] and [missing](nope.md).\n",
    )
    write(
        v / "11_research" / "linker.md",
        "---\ntitle: Linker\ntype: note\ncreated: 2026-10-02T09:00:00+02:00\n"
        "updated: 2026-10-02T09:00:00+02:00\ningested: 2026-10-02T09:00:00+02:00\n---\n"
        "Links [note](../10_ai/my%20note.md) and [paper](../10_ai/attention.md) and [sp](../10_ai/my note.md) and [ab](<../10_ai/my note.md>).\n",
    )
    write(
        v / "11_research" / "orphan.md",
        "---\ntitle: Orphan\ntype: note\ncreated: 2026-01-01T09:00:00+02:00\n"
        "updated: 2026-01-01T09:00:00+02:00\n---\nNobody links here and I link nowhere.\n",
    )
    write(v / "00_inbox" / "old.md", "---\ntitle: Old inbox\ncreated: 2026-09-01T09:00:00+02:00\n---\nx\n")
    write(v / "90_wiki" / "SCHEMA.md", "# Schema\n")
    write(v / "90_wiki" / "INDEX.md", "# Wiki index\n")
    write(v / "90_wiki" / "LOG.md", "# Log\n")
    write(
        v / "90_wiki" / "topics" / "transformers.md",
        "---\ntitle: Transformers\ntype: wiki-topic\ncreated: 2026-10-03T09:00:00+02:00\n"
        "updated: 2026-10-03T09:00:00+02:00\nsources: [10_ai/attention.md]\nconfidence: medium\n---\n"
        "> [!conflict] #c-0001 — open\n> A: x — sources/a.md\n> B: y — sources/b.md\n> Decision: pending\n\n"
        "> [!conflict] #c-0002 — resolved\n> Decision: A holds\n",
    )
    write(v / "INDEX.md", "# stale\n")
    # deterministic mtimes for files without `updated`
    t = 1_700_000_000
    for p in v.rglob("*"):
        if p.is_file():
            os.utime(p, (t, t))
    os.utime(v / "INDEX.md", (t - 100, t - 100))  # generated output older than content → stale
    return v
