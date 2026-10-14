from datetime import datetime
from pathlib import Path

from conftest import write
from zen import health, index_md, vault as vt

NOW = datetime.fromisoformat("2026-10-14T12:00:00+02:00")


def render(vault: Path) -> str:
    s = vt.scan(vault)
    return index_md.render(s, health.check(s, NOW), NOW)


def test_header_has_timestamp_and_totals(vault: Path):
    out = render(vault)
    assert out.startswith("# ZEN Index\n\nGenerated 2026-10-14T12:00:00+02:00 · ")
    assert "4 notes · 1 companions · 1 originals · 1 wiki pages · 1 open conflicts" in out


def test_cluster_sections_list_only_important_newest_first(vault: Path):
    write(vault / "10_ai" / "pinned.md", "---\ntitle: Pinned\ntype: note\nupdated: 2026-10-09T00:00:00+02:00\ntags: [pinned]\n---\nx\n")
    out = render(vault)
    ai = out.split("## 10_ai")[1].split("## 11_research")[0]
    assert "AI research and tooling" in ai
    assert "2 notes · 1 companions · 1 originals" in ai
    lines = [l for l in ai.splitlines() if l.startswith("- [")]
    assert lines == [
        "- [Pinned](10_ai/pinned.md) — pinned · updated 2026-10-09",
        "- [Attention Is All You Need](10_ai/attention.md) — The transformer paper. · transformers · updated 2026-10-01",
    ]


def test_inbound_threshold_makes_important(vault: Path):
    s = vt.scan(vault)
    assert index_md.is_important(s.docs["10_ai/attention.md"])  # has summary
    assert not index_md.is_important(s.docs["11_research/linker.md"])
    linker = s.docs["11_research/linker.md"]
    linker.inbound = 3
    assert index_md.is_important(linker)


def test_wiki_and_health_sections(vault: Path):
    out = render(vault)
    assert "## Wiki\n\n### wiki-topic\n- [Transformers](90_wiki/topics/transformers.md)" in out
    health_section = out.split("## Health")[1]
    assert "### open-conflict\n- 90_wiki/topics/transformers.md — #c-0001" in health_section
    block = health_section.split("### broken-link\n")[1].split("\n\n")[0].splitlines()
    assert "- 10_ai/my note.md — 10_ai/nope.md" in block
    assert "- 10_ai/attention.md — 10_ai/_originals/none.pdf" in block
    assert block.index("- 10_ai/attention.md — 10_ai/_originals/none.pdf") < block.index("- 10_ai/my note.md — 10_ai/nope.md")
    assert "### wiki-behind\n- 10_ai/my note.md" in health_section


def test_render_is_deterministic(vault: Path):
    assert render(vault) == render(vault)


def test_space_in_path_uses_angle_brackets(vault: Path):
    write(vault / "10_ai" / "with space.md", "---\ntitle: T\ntype: note\nupdated: 2026-10-09T00:00:00+02:00\ntags: [pinned]\n---\nx\n")
    out = render(vault)
    assert "- [T](<10_ai/with space.md>) — pinned · updated 2026-10-09" in out
