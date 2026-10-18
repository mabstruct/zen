from pathlib import Path

from conftest import make_pdf, write
from zen import frontmatter as fm, intake

NOW = "2026-10-14T12:00:00+02:00"


def test_file_into_cluster_writes_original_and_companion(vault: Path, tmp_path: Path):
    src = tmp_path / "Deep Learning Survey.pdf"
    src.write_bytes(make_pdf("Survey text"))
    r = intake.intake_item(vault, str(src), "10_ai", now=NOW)
    assert r.status == "filed"
    assert r.original == "10_ai/_originals/deep-learning-survey.pdf"
    assert r.companion == "10_ai/deep-learning-survey.md"
    assert src.exists()  # outside the inbox: copied, not moved
    doc = fm.read(vault / r.companion)
    assert doc.meta["type"] == "companion" and doc.meta["created"] == NOW and doc.meta["updated"] == NOW
    assert doc.meta["source"]["kind"] == "file" and doc.meta["source"]["local"] == "_originals/deep-learning-survey.pdf"
    assert doc.meta["source"]["hash"].startswith("sha256:") and doc.meta["source"]["captured"] == NOW
    assert doc.meta["snapshot"] == "ok" and doc.meta["extraction"] == "ok"
    assert "ingested" not in doc.meta
    assert doc.body.startswith(f"# {doc.meta['title']}\n\n## Summary\n\n## Extracted text\n") and "Survey text" in doc.body
    assert doc.body.splitlines()[0] == "# " + doc.meta["title"]


def test_duplicate_by_hash_is_skipped_and_nothing_written(vault: Path, tmp_path: Path):
    src = tmp_path / "a.pdf"
    src.write_bytes(make_pdf("Same"))
    intake.intake_item(vault, str(src), "10_ai", now=NOW)
    before = sorted(p.relative_to(vault).as_posix() for p in vault.rglob("*") if p.is_file())
    other = tmp_path / "renamed.pdf"
    other.write_bytes(make_pdf("Same"))
    r = intake.intake_item(vault, str(other), "11_research", now=NOW)
    assert r.status == "duplicate" and r.companion == "10_ai/a.md"
    after = sorted(p.relative_to(vault).as_posix() for p in vault.rglob("*") if p.is_file())
    assert before == after


def test_name_collision_gets_suffix(vault: Path, tmp_path: Path):
    a = tmp_path / "a" / "paper.pdf"; a.parent.mkdir(); a.write_bytes(make_pdf("One"))
    b = tmp_path / "b" / "paper.pdf"; b.parent.mkdir(); b.write_bytes(make_pdf("Two"))
    intake.intake_item(vault, str(a), "10_ai", now=NOW)
    r = intake.intake_item(vault, str(b), "10_ai", now=NOW)
    assert r.companion == "10_ai/paper-2.md" and r.original == "10_ai/_originals/paper-2.pdf"


def test_no_cluster_lands_in_inbox(vault: Path, tmp_path: Path):
    src = tmp_path / "x.html"
    src.write_text("<p>hi</p>", encoding="utf-8")
    r = intake.intake_item(vault, str(src), None, now=NOW)
    assert r.status == "inbox" and r.companion == "00_inbox/x.md" and r.original == "00_inbox/_originals/x.html"


def test_unknown_cluster_fails(vault: Path, tmp_path: Path):
    src = tmp_path / "x.html"; src.write_text("<p>hi</p>", encoding="utf-8")
    r = intake.intake_item(vault, str(src), "99_nope", now=NOW)
    assert r.status == "failed" and "cluster" in r.note


def test_url_fetch_failure_writes_flagged_companion(vault: Path):
    def boom(u):
        raise OSError("timeout")

    r = intake.intake_item(vault, "https://example.com/a", "10_ai", fetch=boom, now=NOW)
    assert r.status == "filed" and r.original is None
    doc = fm.read(vault / r.companion)
    assert doc.meta["snapshot"] == "missing" and doc.meta["extraction"] == "none"
    assert doc.meta["source"] == {"kind": "url", "url": "https://example.com/a", "captured": NOW}


def test_arxiv_sets_url_and_local(vault: Path):
    r = intake.intake_item(vault, "2403.01234", "10_ai", fetch=lambda u: (make_pdf("Arxiv body"), "application/pdf"), now=NOW)
    doc = fm.read(vault / r.companion)
    assert doc.meta["source"]["kind"] == "arxiv" and doc.meta["source"]["url"] == "https://arxiv.org/abs/2403.01234"
    assert doc.meta["source"]["local"] == "_originals/2403.01234.pdf" and "Arxiv body" in doc.body


def test_image_companion_is_metadata_only(vault: Path, tmp_path: Path):
    src = tmp_path / "diagram.png"; src.write_bytes(b"\x89PNG\r\n")
    r = intake.intake_item(vault, str(src), "10_ai", now=NOW)
    doc = fm.read(vault / r.companion)
    assert doc.meta["extraction"] == "none" and doc.body == "# diagram\n\n## Summary\n\n## Extracted text\n"


def test_large_file_flag(vault: Path, tmp_path: Path, monkeypatch):
    monkeypatch.setattr(intake, "LARGE_BYTES", 10)
    src = tmp_path / "big.txt"; src.write_text("x" * 100, encoding="utf-8")
    r = intake.intake_item(vault, str(src), "10_ai", now=NOW)
    assert fm.read(vault / r.companion).meta["large"] is True


def test_inbox_raw_note_normalised_and_moved_by_cluster_key(vault: Path):
    (vault / "00_inbox" / "idea.md").write_text("# Big idea\n\ncluster-less text\n", encoding="utf-8")
    (vault / "00_inbox" / "filed.md").write_text("---\ncluster: 11_research\ntags: one\n---\n# Filed\n", encoding="utf-8")
    rep = intake.intake_inbox(vault, None, now=NOW)
    statuses = {i.input: i.status for i in rep.items}
    assert statuses["00_inbox/idea.md"] == "inbox" and statuses["00_inbox/filed.md"] == "filed"
    idea = fm.read(vault / "00_inbox" / "idea.md")
    assert idea.meta == {"title": "Big idea", "type": "note", "created": NOW, "updated": NOW, "tags": []}
    assert not (vault / "00_inbox" / "filed.md").exists()
    filed = fm.read(vault / "11_research" / "filed.md")
    assert filed.meta["tags"] == ["one"] and "cluster" not in filed.meta and filed.meta["title"] == "Filed"


def test_inbox_original_is_moved_not_copied(vault: Path):
    src = vault / "00_inbox" / "drop.html"; src.write_text("<p>drop</p>", encoding="utf-8")
    rep = intake.intake_inbox(vault, "10_ai", now=NOW)
    assert rep.items[0].status == "filed" and not src.exists()
    assert (vault / "10_ai" / "_originals" / "drop.html").exists()


def test_report_summary_counts(vault: Path, tmp_path: Path):
    src = tmp_path / "x.html"; src.write_text("<p>hi</p>", encoding="utf-8")
    rep = intake.Report([intake.intake_item(vault, str(src), "10_ai", now=NOW), intake.intake_item(vault, str(src), "10_ai", now=NOW)])
    assert "filed: 1" in rep.summary() and "duplicate: 1" in rep.summary()


def test_staged_original_follows_companion_when_filed(vault: Path):
    (vault / "00_inbox" / "drop.html").write_text("<p>drop</p>", encoding="utf-8")
    intake.intake_inbox(vault, None, now=NOW)
    assert (vault / "00_inbox" / "_originals" / "drop.html").exists()
    intake.intake_inbox(vault, "10_ai", now=NOW)
    doc = fm.read(vault / "10_ai" / "drop.md")
    assert doc.meta["source"]["local"] == "_originals/drop.html"
    assert (vault / "10_ai" / "_originals" / "drop.html").exists()
    assert not (vault / "00_inbox" / "_originals" / "drop.html").exists()


def test_failed_url_is_deduped_by_url(vault: Path):
    def boom(u):
        raise OSError("timeout")

    intake.intake_item(vault, "https://example.com/a", "10_ai", fetch=boom, now=NOW)
    before = sorted(p.name for p in vault.rglob("*") if p.is_file())
    r = intake.intake_item(vault, "https://example.com/a", "10_ai", fetch=boom, now=NOW)
    assert r.status == "duplicate"
    assert before == sorted(p.name for p in vault.rglob("*") if p.is_file())


def test_bad_item_does_not_stop_batch(vault: Path):
    (vault / "00_inbox" / "bad.md").write_text("---\n- a\n---\n# X\n", encoding="utf-8")
    (vault / "00_inbox" / "good.html").write_text("<p>ok</p>", encoding="utf-8")
    rep = intake.intake_inbox(vault, "10_ai", now=NOW)
    st = {Path(i.input).name: i.status for i in rep.items}
    assert st["good.html"] == "filed" and st["bad.md"] == "failed"


def test_extraction_failure_rolls_back(vault: Path, tmp_path: Path, monkeypatch):
    def boom(p):
        raise RuntimeError("boom")

    monkeypatch.setattr(intake, "extract", boom)
    src = tmp_path / "x.txt"; src.write_text("hi", encoding="utf-8")
    r = intake.intake_item(vault, str(src), "10_ai", now=NOW)
    assert r.status == "failed"
    assert not list((vault / "10_ai" / "_originals").glob("x*"))
    assert not (vault / "10_ai" / "x.md").exists()


def test_path_traversal_cluster_rejected(vault: Path, tmp_path: Path):
    src = tmp_path / "x.txt"; src.write_text("hi", encoding="utf-8")
    assert intake.intake_item(vault, str(src), "10_ai/../..", now=NOW).status == "failed"


def test_bad_frontmatter_elsewhere_does_not_stop_inbox(vault: Path):
    (vault / "11_research").mkdir(exist_ok=True)
    (vault / "11_research" / "bad.md").write_text("---\ntitle: Re: budget\n---\n# B\n", encoding="utf-8")
    (vault / "00_inbox" / "good.html").write_text("<p>hi</p>", encoding="utf-8")
    r = intake.intake_inbox(vault, "10_ai", now=NOW)
    assert any(i.input.endswith("good.html") and i.status == "filed" for i in r.items)
    assert (vault / "10_ai" / "good.md").exists()


def test_source_local_outside_originals_is_not_moved(vault: Path, tmp_path: Path):
    outside = tmp_path / "outside.txt"
    outside.write_text("secret", encoding="utf-8")
    (vault / "00_inbox" / "c.md").write_text(
        "---\ntitle: C\ntype: companion\nsource:\n  kind: file\n  local: ../../../outside.txt\n---\n# C\n", encoding="utf-8")
    r = intake.intake_inbox(vault, "10_ai", now=NOW)
    assert r.items[0].status == "filed"
    assert outside.exists()
    assert not (vault / "10_ai" / "_originals" / "outside.txt").exists()
    assert not (vault / "00_inbox" / "_originals").exists() or not list((vault / "00_inbox" / "_originals").iterdir())


def test_companion_write_failure_leaves_no_partial_file(vault: Path, tmp_path: Path, monkeypatch):
    src = tmp_path / "w.html"; src.write_text("<p>w</p>", encoding="utf-8")

    def half_write(path, doc):
        Path(path).write_text("partial", encoding="utf-8")
        raise OSError("disk full")

    monkeypatch.setattr(intake.fm, "write", half_write)
    r = intake.intake_item(vault, str(src), "10_ai", now=NOW)
    assert r.status == "failed" and "disk full" in r.note
    assert not (vault / "10_ai" / "w.md").exists()
    assert not (vault / "10_ai" / "_originals" / "w.html").exists()


def test_rollback_moves_inbox_file_back(vault: Path, monkeypatch):
    src = vault / "00_inbox" / "back.html"; src.write_text("<p>b</p>", encoding="utf-8")
    monkeypatch.setattr(intake, "extract", lambda p: (_ for _ in ()).throw(RuntimeError("boom")))
    rep = intake.intake_inbox(vault, "10_ai", now=NOW)
    assert [i.status for i in rep.items if "back.html" in i.input] == ["failed"]
    assert src.exists() and not (vault / "10_ai" / "_originals" / "back.html").exists()


def test_original_and_companion_share_one_stem_on_collision(vault: Path, tmp_path: Path):
    write(vault / "10_ai" / "paper.md", "---\ntitle: A note called paper\ntype: note\n---\nx\n")
    src = tmp_path / "paper.pdf"; src.write_bytes(make_pdf("Paper body"))
    r = intake.intake_item(vault, str(src), "10_ai", now=NOW)
    assert r.companion == "10_ai/paper-2.md" and r.original == "10_ai/_originals/paper-2.pdf"


def test_inbox_items_report_vault_relative_input(vault: Path):
    (vault / "00_inbox" / "drop.html").write_text("<p>d</p>", encoding="utf-8")
    rep = intake.intake_inbox(vault, "10_ai", now=NOW)
    assert "00_inbox/drop.html" in [i.input for i in rep.items]


def test_raw_note_scalar_tags_become_strings(vault: Path):
    (vault / "00_inbox" / "t.md").write_text("---\ntags: 2024\n---\n# T\n", encoding="utf-8")
    intake.intake_inbox(vault, None, now=NOW)
    assert fm.read(vault / "00_inbox" / "t.md").meta["tags"] == ["2024"]


def test_inbox_duplicates_are_moved_aside_and_reported_once(vault: Path, tmp_path: Path):
    first = tmp_path / "same.html"; first.write_text("<p>same</p>", encoding="utf-8")
    assert intake.intake_item(vault, str(first), "10_ai", now=NOW).status == "filed"
    (vault / "00_inbox" / "again.html").write_text("<p>same</p>", encoding="utf-8")
    rep = intake.intake_inbox(vault, None, now=NOW)
    dup = [i for i in rep.items if "again.html" in i.input]
    assert dup[0].status == "duplicate" and "00_inbox/_duplicates/again.html" in dup[0].note
    assert not (vault / "00_inbox" / "again.html").exists()
    assert (vault / "00_inbox" / "_duplicates" / "again.html").exists()
    assert not [i for i in intake.intake_inbox(vault, None, now=NOW).items if "again.html" in i.input]
