from pathlib import Path

import yaml

from conftest import write
from zen import frontmatter as fm, ingest_plan as ip

TS = "2026-10-16T10:00:00+02:00"


def plan(**over) -> dict:
    p = {
        "input": "10_ai/attention.md",
        "ingested": TS,
        "title": None,
        "summary": "The transformer paper.\nAttention only.",
        "source_page": {
            "path": "sources/attention.md",
            "title": "Attention Is All You Need",
            "body": "# Attention Is All You Need\n\nClaims here.\n\n- Back to [the companion](../../10_ai/attention.md)\n",
        },
        "pages": [
            {
                "path": "topics/self-attention.md",
                "action": "create",
                "type": "wiki-topic",
                "title": "Self-attention",
                "claims": ["Self-attention relates positions. ([attention](../sources/attention.md))"],
                "links": ["topics/transformers.md", "entities/vaswani.md"],
                "conflicts": [],
            },
            {
                "path": "entities/vaswani.md",
                "action": "create",
                "type": "wiki-entity",
                "title": "Ashish Vaswani",
                "claims": ["First author. ([attention](../sources/attention.md))"],
                "links": ["topics/self-attention.md"],
                "conflicts": [],
            },
            {
                "path": "topics/transformers.md",
                "action": "update",
                "type": "wiki-topic",
                "title": "Transformers",
                "claims": ["Uses no recurrence. ([attention](../sources/attention.md))"],
                "links": ["topics/self-attention.md", "sources/attention.md"],
                "conflicts": ["#c-0001"],
            },
        ],
        "conflicts": [
            {
                "id": "#c-0001",
                "pages": ["topics/transformers.md"],
                "a": {"claim": "Uses recurrence.", "source": "sources/other.md", "captured": "2026-03-01"},
                "b": {"claim": "Uses no recurrence.", "source": "sources/attention.md", "captured": "2026-10-01"},
            }
        ],
    }
    p.update(over)
    return p


def errors(vault: Path, p: dict) -> list[str]:
    return ip.check(vault, p)


def test_valid_plan_has_no_errors(vault: Path):
    assert errors(vault, plan()) == []


def test_create_on_existing_and_update_on_missing(vault: Path):
    p = plan()
    p["pages"][0]["path"] = "topics/transformers.md"
    p["pages"][2]["path"] = "topics/nope.md"
    e = errors(vault, p)
    assert any("create" in x and "topics/transformers.md" in x and "exists" in x for x in e)
    assert any("update" in x and "topics/nope.md" in x for x in e)


def test_type_must_match_folder(vault: Path):
    p = plan()
    p["pages"][1]["type"] = "wiki-topic"
    assert any("entities/vaswani.md" in x and "type" in x for x in errors(vault, p))


def test_links_must_resolve_to_planned_or_existing(vault: Path):
    p = plan()
    p["pages"][0]["links"].append("topics/ghost.md")
    assert any("topics/ghost.md" in x for x in errors(vault, p))


def test_every_claim_cites_a_source_page(vault: Path):
    p = plan()
    p["pages"][1]["claims"].append("An uncited claim.")
    assert any("uncited" in x.lower() or "citation" in x for x in errors(vault, p))


def test_conflict_ids_continue_from_log(vault: Path):
    (vault / "90_wiki" / "LOG.md").write_text("# Log\n\n## x ingest a\n- conflicts: #c-0007 (topics/t.md)\n", encoding="utf-8")
    e = errors(vault, plan())
    assert any("#c-0008" in x for x in e)  # expected next id named in the error


def test_page_conflict_reference_must_be_defined(vault: Path):
    p = plan()
    p["pages"][0]["conflicts"] = ["#c-0002"]
    assert any("#c-0002" in x for x in errors(vault, p))


def test_source_page_path(vault: Path):
    p = plan()
    p["source_page"]["path"] = "topics/attention.md"
    assert any("source_page" in x for x in errors(vault, p))


def test_batches_preserve_order():
    p = {"pages": [{"path": f"topics/p{i}.md"} for i in range(5)]}
    assert ip.batches(p, 2) == [["topics/p0.md", "topics/p1.md"], ["topics/p2.md", "topics/p3.md"], ["topics/p4.md"]]


def _write_planned_pages(vault: Path):
    w = vault / "90_wiki"
    write(w / "topics" / "self-attention.md", f"---\ntitle: Self-attention\ntype: wiki-topic\ncreated: {TS}\nupdated: {TS}\nsources: [10_ai/attention.md]\nconfidence: low\n---\nx\n")
    write(w / "entities" / "vaswani.md", f"---\ntitle: Ashish Vaswani\ntype: wiki-entity\ncreated: {TS}\nupdated: {TS}\nsources: [10_ai/attention.md]\nconfidence: low\n---\nx\n")


def test_finish_writes_source_page_companion_log_and_index(vault: Path):
    _write_planned_pages(vault)
    ip.finish(vault, plan())
    src = fm.read(vault / "90_wiki" / "sources" / "attention.md")
    assert src.meta == {"title": "Attention Is All You Need", "type": "wiki-source", "created": TS, "updated": TS,
                        "sources": ["10_ai/attention.md"], "confidence": "high", "tags": []}
    assert "Back to [the companion]" in src.body

    comp = fm.read(vault / "10_ai" / "attention.md")
    assert comp.meta["ingested"] == TS and comp.meta["updated"] == TS
    assert "## Summary\nThe transformer paper.\n" in comp.body  # existing summary kept

    log = (vault / "90_wiki" / "LOG.md").read_text(encoding="utf-8")
    assert f"## {TS} ingest 10_ai/attention.md\n" in log
    assert "- created: sources/attention.md, topics/self-attention.md, entities/vaswani.md" in log
    assert "- updated: topics/transformers.md" in log
    assert "- conflicts: #c-0001 (topics/transformers.md)" in log

    idx = (vault / "90_wiki" / "INDEX.md").read_text(encoding="utf-8")
    assert "## wiki-topic\n\n- [Self-attention](topics/self-attention.md) · wiki-topic · 2026-10-16\n- [Transformers](topics/transformers.md) · wiki-topic · 2026-10-03\n" in idx
    assert "- [Ashish Vaswani](entities/vaswani.md) · wiki-entity · 2026-10-16" in idx
    assert "- [Attention Is All You Need](sources/attention.md) · wiki-source · 2026-10-16" in idx


def test_finish_fills_empty_summary_and_sets_title(vault: Path):
    _write_planned_pages(vault)
    comp = vault / "10_ai" / "attention.md"
    doc = fm.read(comp)
    doc.meta["title"] = "1706.03762"
    doc.body = doc.body.replace("The transformer paper.\n", "")
    doc.body = "# 1706.03762\n\n" + doc.body
    fm.write(comp, doc)
    ip.finish(vault, plan(title="Attention Is All You Need", summary="Line one.\nLine two."))
    doc = fm.read(comp)
    assert doc.meta["title"] == "Attention Is All You Need"
    assert doc.body.startswith("# Attention Is All You Need\n")
    assert "## Summary\nLine one.\nLine two.\n" in doc.body


def test_cli_check_and_batches(vault: Path, tmp_path: Path, capsys):
    f = tmp_path / "plan.yaml"
    f.write_text(yaml.safe_dump(plan(), sort_keys=False, allow_unicode=True), encoding="utf-8")
    assert ip.main(["check", str(f), "--vault", str(vault)]) == 0
    assert "plan ok" in capsys.readouterr().out
    assert ip.main(["batches", str(f), "--size", "2"]) == 0
    out = capsys.readouterr().out.splitlines()
    assert out == ["topics/self-attention.md entities/vaswani.md", "topics/transformers.md"]
    bad = plan()
    bad["pages"][0]["links"].append("topics/ghost.md")
    f.write_text(yaml.safe_dump(bad, sort_keys=False), encoding="utf-8")
    assert ip.main(["check", str(f), "--vault", str(vault)]) == 1
