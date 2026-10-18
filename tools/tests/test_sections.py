from zen import sections as sec


def book(pages: list[list[str]]) -> str:
    """A companion whose extracted text has one page per entry (lines)."""
    head = "---\ntitle: Book\ntype: companion\n---\n# Book\n\n## Summary\n\n## Extracted text\n"
    body = "\n\n".join(f"<!-- page {i} -->\n" + "\n".join(lines) for i, lines in enumerate(pages, 1))
    return head + body + "\n"


FILL = ["lorem ipsum dolor sit amet " * 20] * 3   # ~1.6k chars of body per page


def gilgamesh_like() -> list[list[str]]:
    pages = [["Cover art"], ["Contents", "Introduction xiii", "Tablet I 1"]]
    for n in range(3, 9):                                     # introduction, both sides headed
        pages.append([str(n), "Introduction", *FILL])
    pages.append(["THE STANDARD VERSION", "Tablet I opening", *FILL])     # chapter opening, no running head
    for n in range(10, 22):                                   # left = book title, right = section
        right = n % 2 == 0
        if n < 16:
            h = "I. The Standard Version, Tablet I" if n != 12 else "1. The Standard Version, Tab/et I"
        else:
            h = "I. The Standard Version, Tablet II"
        pages.append([str(n), h if right else ("THE EPIC OF GILGAMESH" if n != 13 else "THE E PIe 0 F G I L G A M E S H"), *FILL])
    pages.append([str(22), "Glossary of Proper Nouns", *FILL])
    pages.append([str(23), "Glossary of Proper Nouns", *FILL])
    return pages


def test_heads_normalised_title_ignored_openings_go_forward():
    s = sec.build(book(gilgamesh_like()), max_tokens=10**9, merge=False)
    assert [x.title for x in s] == [
        "Introduction",
        "I. The Standard Version, Tablet I",
        "I. The Standard Version, Tablet II",
        "Glossary of Proper Nouns",
    ]
    assert (s[0].first_page, s[0].last_page) == (1, 8)        # cover and contents join the first section
    assert (s[1].first_page, s[1].last_page) == (9, 15)       # chapter opening page 9 joins Tablet I
    assert (s[2].first_page, s[2].last_page) == (16, 21)
    assert (s[3].first_page, s[3].last_page) == (22, 23)


def test_line_ranges_cover_the_extracted_text_without_gaps():
    text = book(gilgamesh_like())
    s = sec.build(text, max_tokens=10**9, merge=False)
    lines = text.splitlines()
    assert lines[s[0].start_line - 1] == "<!-- page 1 -->"
    for a, b in zip(s, s[1:]):
        assert b.start_line == a.end_line + 1
        assert lines[b.start_line - 1].startswith("<!-- page ")
    assert s[-1].end_line == len(lines)


def test_adjacent_sections_merge_up_to_the_budget():
    text = book(gilgamesh_like())
    raw = sec.build(text, max_tokens=10**9, merge=False)
    budget = raw[0].tokens + raw[1].tokens + 10
    merged = sec.build(text, max_tokens=budget)
    assert merged[0].title == "Introduction – I. The Standard Version, Tablet I"
    assert (merged[0].first_page, merged[0].last_page) == (1, 15)
    assert all(m.tokens <= budget for m in merged)


def test_oversized_section_is_split_by_pages():
    text = book(gilgamesh_like())
    s = sec.build(text, max_tokens=2000)
    assert all(x.tokens <= 2000 or x.first_page == x.last_page for x in s)
    assert any(x.title.endswith("(part 2)") for x in s)


def test_without_page_markers_falls_back_to_size_chunks():
    text = "---\ntitle: T\n---\n# T\n\n## Summary\n\n## Extracted text\n" + "\n\n".join(["para " * 300] * 10) + "\n"
    s = sec.build(text, max_tokens=1000)
    assert len(s) > 1 and s[0].title == "Part 1"
    assert all(x.first_page is None for x in s)


def test_cli_writes_section_map(vault, tmp_path, capsys):
    import yaml
    from zen import ingest_plan
    (vault / "10_ai" / "book.md").write_text(book(gilgamesh_like()), encoding="utf-8")
    out = tmp_path / "sections.yaml"
    assert ingest_plan.main(["sections", "10_ai/book.md", "--vault", str(vault), "--out", str(out), "--max-tokens", "100000"]) == 0
    data = yaml.safe_load(out.read_text(encoding="utf-8"))
    assert data["input"] == "10_ai/book.md" and data["sections"][0]["index"] == 1
    assert data["sections"][0]["pages"] == [1, 23] and "1." in capsys.readouterr().out
