import json
from datetime import datetime
from pathlib import Path

from zen import map_json, vault as vt

NOW = datetime.fromisoformat("2026-10-14T12:00:00+02:00")


def test_nodes_cover_docs_originals_tags(vault: Path):
    m = map_json.build(vt.scan(vault), NOW)
    ids = {n["id"] for n in m["nodes"]}
    assert "10_ai/attention.md" in ids
    assert "10_ai/_originals/1706.03762.pdf" in ids
    assert "tag:transformers" in ids
    paper = next(n for n in m["nodes"] if n["id"] == "10_ai/attention.md")
    assert paper["cluster"] == "10_ai" and paper["type"] == "companion"
    assert paper["captured"] == "2026-10-01T10:00:00+02:00" and paper["ingested"] is None
    assert m["generated"] == "2026-10-14T12:00:00+02:00"


def test_edges_link_tag_source_wiki_only_to_existing_nodes(vault: Path):
    m = map_json.build(vt.scan(vault), NOW)
    edges = {(e["from"], e["to"], e["kind"]) for e in m["edges"]}
    assert ("11_research/linker.md", "10_ai/attention.md", "link") in edges
    assert ("10_ai/attention.md", "tag:transformers", "tag") in edges
    assert ("10_ai/attention.md", "10_ai/_originals/1706.03762.pdf", "source") in edges
    assert ("90_wiki/topics/transformers.md", "10_ai/attention.md", "wiki") in edges
    assert not any(e["to"] == "10_ai/nope.md" for e in m["edges"])


def test_json_serialisable_and_sorted(vault: Path):
    m = map_json.build(vt.scan(vault), NOW)
    json.dumps(m)
    assert [n["id"] for n in m["nodes"]] == sorted(n["id"] for n in m["nodes"])


def test_duplicate_links_give_one_edge(vault: Path):
    m = map_json.build(vt.scan(vault), NOW)
    edges = [(e["from"], e["to"], e["kind"]) for e in m["edges"]]
    assert len(edges) == len(set(edges))
    assert edges.count(("11_research/linker.md", "10_ai/my note.md", "link")) == 1


def test_scalar_sources_is_one_wiki_edge(vault: Path):
    from conftest import write
    write(vault / "90_wiki" / "topics" / "single.md",
          "---\ntitle: Single\ntype: wiki-topic\nsources: 10_ai/attention.md\nconfidence: low\n---\nx\n")
    m = map_json.build(vt.scan(vault), NOW)
    assert ("90_wiki/topics/single.md", "10_ai/attention.md", "wiki") in {(e["from"], e["to"], e["kind"]) for e in m["edges"]}


def test_nodes_carry_confidence_and_open_conflicts(vault: Path):
    from conftest import write
    write(vault / "90_wiki" / "topics" / "c.md",
          "---\ntitle: C\ntype: wiki-topic\nsources: [10_ai/attention.md]\nconfidence: medium\n---\n"
          "> [!conflict] #c-0007 — open\n> A: x\n\n> [!conflict] #c-0002 — resolved\n> A: y\n")
    nodes = {n["id"]: n for n in map_json.build(vt.scan(vault), NOW)["nodes"]}
    assert nodes["90_wiki/topics/c.md"]["confidence"] == "medium"
    assert nodes["90_wiki/topics/c.md"]["conflicts"] == ["#c-0007"]
    assert nodes["10_ai/attention.md"]["confidence"] is None
    assert nodes["10_ai/attention.md"]["conflicts"] == []
    assert nodes["10_ai/_originals/1706.03762.pdf"]["confidence"] is None
