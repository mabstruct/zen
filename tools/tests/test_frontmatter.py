from pathlib import Path

from zen import frontmatter as fm


def test_parse_splits_meta_and_body():
    doc = fm.parse("---\ntitle: Hello\ntags: [a, b]\n---\n# Hello\n\nbody\n")
    assert doc.meta == {"title": "Hello", "tags": ["a", "b"]}
    assert doc.body == "# Hello\n\nbody\n"


def test_parse_without_frontmatter_returns_empty_meta():
    doc = fm.parse("# Just text\n")
    assert doc.meta == {}
    assert doc.body == "# Just text\n"


def test_timestamps_stay_strings_and_round_trip_unquoted():
    text = "---\ntitle: T\ncreated: 2026-10-14T18:02:11+02:00\n---\nbody\n"
    doc = fm.parse(text)
    assert doc.meta["created"] == "2026-10-14T18:02:11+02:00"
    assert isinstance(doc.meta["created"], str)
    assert fm.dump(doc) == text


def test_dump_preserves_key_order_and_unicode():
    doc = fm.Document({"title": "Über ZEN", "type": "note"}, "x\n")
    assert fm.dump(doc) == "---\ntitle: Über ZEN\ntype: note\n---\nx\n"


def test_now_iso_has_offset_and_no_microseconds():
    s = fm.now_iso()
    assert len(s) == 25  # 2026-10-14T18:02:11+02:00
    assert s[19] in "+-"
    assert "." not in s


def test_read_write_round_trip(tmp_path: Path):
    p = tmp_path / "n.md"
    fm.write(p, fm.Document({"title": "A"}, "b\n"))
    assert fm.read(p).meta == {"title": "A"}
    assert p.read_text(encoding="utf-8") == "---\ntitle: A\n---\nb\n"


def test_empty_frontmatter_block_is_parsed_as_empty_meta():
    doc = fm.parse("---\n---\n# Body\n")
    assert doc.meta == {} and doc.body == "# Body\n"


def test_long_values_are_not_folded():
    title = "A very long title " * 8
    out = fm.dump(fm.Document({"title": title.strip()}, "x\n"))
    assert out.splitlines()[1] == "title: " + title.strip()


def test_dump_with_empty_meta_writes_body_only():
    assert fm.dump(fm.Document({}, "# Body\n")) == "# Body\n"
