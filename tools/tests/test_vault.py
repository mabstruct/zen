from pathlib import Path

from conftest import write
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


def _example(vault: Path, fence: str):
    from conftest import write

    write(
        vault / "11_research" / "examples.md",
        "---\ntitle: Examples\ntype: note\n---\n"
        f"Real [paper](../10_ai/attention.md) and `[x](nope-inline.md)`.\n\n{fence}md\n"
        "[gone](nope-fenced.md) [[NoSuchPage]]\n> [!conflict] #c-0099 — open\n> Decision: pending\n"
        f"{fence}\n",
    )
    return vt.scan(vault)


def test_code_fence_and_inline_code_ignored(vault: Path):
    s = _example(vault, "```")
    d = s.docs["11_research/examples.md"]
    assert d.links == ["10_ai/attention.md"]
    assert d.open_conflicts == []
    assert not any(src == d.rel for src, _ in s.broken_links)


def test_tilde_fence_ignored(vault: Path):
    s = _example(vault, "~~~")
    d = s.docs["11_research/examples.md"]
    assert d.links == ["10_ai/attention.md"]
    assert d.open_conflicts == []
    assert not any(src == d.rel for src, _ in s.broken_links)


def test_bad_frontmatter_and_numeric_tags_do_not_crash(vault: Path):
    from conftest import write
    write(vault / "11_research" / "bad.md", "---\ntitle: Re: budget\n---\n# Budget thoughts\n\nbody\n")
    write(vault / "11_research" / "num.md", "---\ntitle: N\ntags: 2024\n---\nx\n")
    s = vt.scan(vault)
    d = s.docs["11_research/bad.md"]
    assert d.title == "Budget thoughts" and d.frontmatter_error and d.frontmatter_error.count("\n") == 0
    assert s.docs["11_research/num.md"].tags == ["2024"]
    assert s.docs["11_research/num.md"].frontmatter_error is None


def test_root_level_cluster_md_is_ignored(vault: Path):
    write(vault / "_cluster.md", "stray description\n")
    vt.scan(vault)


def test_dotted_link_target_resolves_to_md_file(vault: Path):
    write(vault / "11_research" / "notes-v1.2.md", "---\ntitle: V12\ntype: note\n---\nx\n")
    write(vault / "11_research" / "ref.md", "---\ntitle: Ref\ntype: note\n---\nsee [v](notes-v1.2)\n")
    s = vt.scan(vault)
    assert "11_research/notes-v1.2.md" in s.docs["11_research/ref.md"].links
    assert not any(src == "11_research/ref.md" for src, _ in s.broken_links)


def test_path_style_and_md_suffixed_wikilinks_resolve(vault: Path):
    write(vault / "11_research" / "wl.md", "---\ntitle: WL\ntype: note\n---\n[[10_ai/attention]] and [[orphan.md]]\n")
    s = vt.scan(vault)
    assert {"10_ai/attention.md", "11_research/orphan.md"} <= set(s.docs["11_research/wl.md"].links)


def test_broken_wikilinks_are_reported_in_brackets(vault: Path):
    write(vault / "11_research" / "wl.md", "---\ntitle: WL\ntype: note\n---\n[[No Such Page]]\n")
    assert ("11_research/wl.md", "[[No Such Page]]") in vt.scan(vault).broken_links


def test_fence_inside_blockquote_is_stripped(vault: Path):
    write(vault / "11_research" / "bq.md", "---\ntitle: BQ\ntype: note\n---\n> ```\n> [x](ghost.md)\n> ```\n")
    s = vt.scan(vault)
    assert s.docs["11_research/bq.md"].links == []
