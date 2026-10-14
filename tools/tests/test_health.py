from datetime import datetime
from pathlib import Path

from conftest import write
from zen import health, vault as vt

NOW = datetime.fromisoformat("2026-10-14T12:00:00+02:00")


def kinds(findings, kind):
    return sorted(f.path for f in findings if f.kind == kind)


def test_inbox_stale_uses_created_then_mtime(vault: Path):
    f = health.check(vt.scan(vault), NOW)
    assert kinds(f, "inbox-stale") == ["00_inbox/old.md"]
    write(vault / "00_inbox" / "fresh.md", "---\ntitle: F\ncreated: 2026-10-13T12:00:00+02:00\n---\nx\n")
    f = health.check(vt.scan(vault), NOW)
    assert kinds(f, "inbox-stale") == ["00_inbox/old.md"]


def test_snapshot_missing_extraction_failed_large(vault: Path):
    write(
        vault / "10_ai" / "web.md",
        "---\ntitle: W\ntype: companion\nsource:\n  kind: url\n  url: https://x\nsnapshot: missing\n"
        "extraction: failed\nlarge: true\n---\n## Summary\n\n## Extracted text\n",
    )
    f = health.check(vt.scan(vault), NOW)
    assert kinds(f, "snapshot-missing") == ["10_ai/web.md"]
    assert kinds(f, "extraction-failed") == ["10_ai/web.md"]
    assert kinds(f, "large-file") == ["10_ai/web.md"]


def test_orphans_broken_links_duplicates(vault: Path):
    write(vault / "11_research" / "dup.md", "---\ntitle: Orphan\ntype: note\n---\n[x](linker.md)\n")
    f = health.check(vt.scan(vault), NOW)
    assert kinds(f, "orphan") == ["00_inbox/old.md"]  # orphan.md now has an inbound wikilink + dup links out
    assert [(x.path, x.detail) for x in f if x.kind == "broken-link"] == [
        ("10_ai/attention.md", "10_ai/_originals/none.pdf"),
        ("10_ai/my note.md", "10_ai/nope.md"),
    ]
    assert kinds(f, "duplicate-title") == ["11_research/dup.md", "11_research/orphan.md"]


def test_never_ingested_and_wiki_behind_strictly_newer(vault: Path):
    f = health.check(vt.scan(vault), NOW)
    assert kinds(f, "never-ingested") == ["00_inbox/old.md", "10_ai/attention.md", "11_research/orphan.md"]
    assert kinds(f, "wiki-behind") == ["10_ai/my note.md"]  # updated 10-05 > ingested 10-03
    assert "11_research/linker.md" not in kinds(f, "wiki-behind")  # equal timestamps


def test_open_conflicts_listed_with_page(vault: Path):
    f = health.check(vt.scan(vault), NOW)
    c = [x for x in f if x.kind == "open-conflict"]
    assert [(x.path, x.detail) for x in c] == [("90_wiki/topics/transformers.md", "#c-0001")]


def test_report_order_follows_kinds(vault: Path):
    f = health.check(vt.scan(vault), NOW)
    order = [health.KINDS.index(x.kind) for x in f]
    assert order == sorted(order)
