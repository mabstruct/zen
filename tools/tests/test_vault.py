from pathlib import Path

from zen import vault as vt


def test_cluster_of():
    assert vt.cluster_of("10_ai/x.md") == "10_ai"
    assert vt.cluster_of("00_inbox/x.md") == "00_inbox"
    assert vt.cluster_of("90_wiki/topics/t.md") == "90_wiki"
    assert vt.cluster_of("INDEX.md") is None


def test_scan_finds_docs_and_skips_generated_templates_originals(vault: Path):
    s = vt.scan(vault)
    assert "10_ai/attention.md" in s.docs
    assert "02_templates/note.md" not in s.docs
    assert "INDEX.md" not in s.docs
    assert "_meta/map.json" not in s.docs
    assert s.originals == ["10_ai/_originals/1706.03762.pdf"]


def test_clusters_only_1x_folders_with_counts_and_description(vault: Path):
    s = vt.scan(vault)
    names = [c.name for c in s.clusters]
    assert names == ["10_ai", "11_research"]
    ai = s.clusters[0]
    assert ai.description == "AI research and tooling"
    assert (ai.notes, ai.companions, ai.originals) == (1, 1, 1)
    assert s.clusters[1].description == "11_research"


def test_links_resolve_relative_percent_encoded_and_wikilinks(vault: Path):
    s = vt.scan(vault)
    linker = s.docs["11_research/linker.md"]
    assert linker.links == ["10_ai/my note.md", "10_ai/attention.md", "10_ai/my note.md", "10_ai/my note.md"]
    note = s.docs["10_ai/my note.md"]
    assert "10_ai/attention.md" in note.links
    assert "11_research/orphan.md" in note.links  # [[Orphan]] resolved by title
    assert ("10_ai/my note.md", "10_ai/nope.md") in s.broken_links


def test_inbound_counts(vault: Path):
    s = vt.scan(vault)
    assert s.docs["10_ai/attention.md"].inbound == 2
    assert s.docs["10_ai/my note.md"].inbound == 1
    assert s.docs["11_research/linker.md"].inbound == 0


def test_tags_string_becomes_list_and_title_fallbacks(vault: Path, tmp_path: Path):
    s = vt.scan(vault)
    assert s.docs["10_ai/my note.md"].tags == ["ai"]
    (vault / "10_ai" / "untitled.md").write_text("# Heading title\n\ntext\n", encoding="utf-8")
    (vault / "10_ai" / "bare.md").write_text("no heading\n", encoding="utf-8")
    s = vt.scan(vault)
    assert s.docs["10_ai/untitled.md"].title == "Heading title"
    assert s.docs["10_ai/bare.md"].title == "bare"
    assert s.docs["10_ai/bare.md"].type == "note"


def test_summary_timestamps_and_conflicts(vault: Path):
    s = vt.scan(vault)
    paper = s.docs["10_ai/attention.md"]
    assert paper.summary == "The transformer paper."
    assert paper.captured == "2026-10-01T10:00:00+02:00"
    assert paper.ingested is None
    orphan = s.docs["11_research/orphan.md"]
    assert orphan.updated == "2026-01-01T09:00:00+02:00"
    inbox = s.docs["00_inbox/old.md"]
    assert inbox.updated.startswith("2023-11-14")  # mtime fallback (1_700_000_000)
    assert s.inbox == ["00_inbox/old.md"]
    wiki = s.docs["90_wiki/topics/transformers.md"]
    assert wiki.open_conflicts == ["#c-0001"]
    assert s.docs["90_wiki/SCHEMA.md"].type == "wiki-meta"


def test_links_to_originals_are_valid_but_not_doc_links(vault: Path):
    s = vt.scan(vault)
    assert "10_ai/_originals/1706.03762.pdf" not in s.docs["10_ai/attention.md"].links
    assert not any(t == "10_ai/_originals/1706.03762.pdf" for _, t in s.broken_links)
    assert ("10_ai/attention.md", "10_ai/_originals/none.pdf") in s.broken_links


def test_scan_tolerates_non_mapping_frontmatter(vault: Path):
    (vault / "10_ai" / "bad.md").write_text("---\n- a\n---\n# Bad\n", encoding="utf-8")
    s = vt.scan(vault)
    assert "10_ai/bad.md" in s.docs
