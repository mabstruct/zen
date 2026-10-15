from pathlib import Path

from conftest import write
from zen import frontmatter as fm, move, vault as vt

NOW = "2026-10-15T12:00:00+02:00"


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def test_moves_companion_and_original_and_keeps_source_local(vault: Path):
    r = move.run(vault, "10_ai/attention.md", "11_research", now=NOW)
    assert r.status == "moved" and r.new_path == "11_research/attention.md"
    assert (vault / "11_research" / "attention.md").exists()
    assert (vault / "11_research" / "_originals" / "1706.03762.pdf").exists()
    assert not (vault / "10_ai" / "attention.md").exists()
    assert not (vault / "10_ai" / "_originals" / "1706.03762.pdf").exists()
    meta = fm.read(vault / "11_research" / "attention.md").meta
    assert meta["source"]["local"] == "_originals/1706.03762.pdf"
    assert meta["updated"] == "2026-10-01T10:00:00+02:00"  # a move is not a content change


def test_rewrites_inbound_links_from_both_directions(vault: Path):
    move.run(vault, "10_ai/attention.md", "11_research", now=NOW)
    assert "[paper](attention.md)" in read(vault / "11_research" / "linker.md")
    assert "[the paper](../11_research/attention.md)" in read(vault / "10_ai" / "my note.md")
    assert "[note](../10_ai/my%20note.md)" in read(vault / "11_research" / "linker.md")  # untouched
    s = vt.scan(vault)
    assert "11_research/attention.md" in s.docs["11_research/linker.md"].links
    assert "11_research/attention.md" in s.docs["10_ai/my note.md"].links
    assert s.docs["11_research/attention.md"].inbound == 2


def test_rewrites_wiki_sources_and_logs_move(vault: Path):
    move.run(vault, "10_ai/attention.md", "11_research", now=NOW)
    page = fm.read(vault / "90_wiki" / "topics" / "transformers.md")
    assert page.meta["sources"] == ["11_research/attention.md"]
    assert page.meta["updated"] == "2026-10-03T09:00:00+02:00"
    log = read(vault / "90_wiki" / "LOG.md")
    assert f"## {NOW} move 10_ai/attention.md → 11_research/attention.md" in log


def test_no_new_broken_links_and_index_rebuilt(vault: Path):
    before = len(vt.scan(vault).broken_links)
    move.run(vault, "10_ai/attention.md", "11_research", now=NOW)
    after = vt.scan(vault)
    assert len(after.broken_links) == before
    assert read(vault / "INDEX.md").startswith("# ZEN Index")
    assert "11_research/attention.md" in read(vault / "INDEX.md")


def test_collision_renames_original_and_rewrites_local(vault: Path):
    (vault / "11_research" / "_originals").mkdir()
    (vault / "11_research" / "_originals" / "1706.03762.pdf").write_bytes(b"other")
    write(vault / "11_research" / "attention.md", "---\ntitle: Other\ntype: note\n---\nx\n")
    r = move.run(vault, "10_ai/attention.md", "11_research", now=NOW)
    assert r.new_path == "11_research/attention-2.md"
    meta = fm.read(vault / "11_research" / "attention-2.md").meta
    assert meta["source"]["local"] == "_originals/1706.03762-2.pdf"
    assert (vault / "11_research" / "_originals" / "1706.03762-2.pdf").read_bytes() == b"%PDF-1.4 fake"


def test_moves_plain_note_without_original(vault: Path):
    r = move.run(vault, "11_research/orphan.md", "10_ai", now=NOW)
    assert r.status == "moved" and (vault / "10_ai" / "orphan.md").exists()
    assert "[[Orphan]]" in read(vault / "10_ai" / "my note.md")  # wikilink by title needs no rewrite
    assert "10_ai/orphan.md" in vt.scan(vault).docs["10_ai/my note.md"].links


def test_refusals_touch_nothing(vault: Path):
    snapshot = sorted(p.relative_to(vault).as_posix() for p in vault.rglob("*") if p.is_file())
    assert move.run(vault, "10_ai/attention.md", "10_ai", now=NOW).status == "refused"
    assert move.run(vault, "10_ai/attention.md", "99_nope", now=NOW).status == "refused"
    assert move.run(vault, "10_ai/missing.md", "11_research", now=NOW).status == "refused"
    assert move.run(vault, "90_wiki/topics/transformers.md", "11_research", now=NOW).status == "refused"
    assert snapshot == sorted(p.relative_to(vault).as_posix() for p in vault.rglob("*") if p.is_file())


def test_dry_run_reports_plan_and_touches_nothing(vault: Path, capsys):
    snapshot = sorted(p.relative_to(vault).as_posix() for p in vault.rglob("*") if p.is_file())
    r = move.run(vault, "10_ai/attention.md", "11_research", now=NOW, dry_run=True)
    assert r.status == "planned"
    out = capsys.readouterr().out
    assert "11_research/attention.md" in out and "linker.md" in out and "transformers.md" in out
    assert snapshot == sorted(p.relative_to(vault).as_posix() for p in vault.rglob("*") if p.is_file())


def test_main_entry(vault: Path, capsys):
    assert move.main(["10_ai/attention.md", "--cluster", "11_research", "--vault", str(vault)]) == 0
    assert "moved" in capsys.readouterr().out
    assert move.main(["10_ai/attention.md", "--cluster", "11_research", "--vault", str(vault)]) == 1
