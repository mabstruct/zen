from pathlib import Path

import pytest

from zen import sources as src


def test_classify():
    assert src.classify("https://arxiv.org/abs/2403.01234v2") == ("arxiv", "2403.01234v2")
    assert src.classify("arxiv:2403.01234") == ("arxiv", "2403.01234")
    assert src.classify("2403.01234") == ("arxiv", "2403.01234")
    assert src.classify("https://arxiv.org/pdf/2403.01234.pdf") == ("arxiv", "2403.01234")
    assert src.classify("doi:10.1000/xyz123") == ("doi", "10.1000/xyz123")
    assert src.classify("https://doi.org/10.1000/xyz123") == ("doi", "10.1000/xyz123")
    assert src.classify("https://example.com/post?x=1") == ("url", "https://example.com/post?x=1")
    assert src.classify("notes/My File.PDF") == ("file", "notes/My File.PDF")


def test_slugify_ascii_lowercase_hyphens_limit():
    assert src.slugify("Über ZEN — Ein Test!.pdf") == "uber-zen-ein-test.pdf"
    assert src.slugify("My File.PDF") == "my-file.pdf"
    assert src.slugify("no-ext") == "no-ext"
    assert len(src.slugify("x" * 200 + ".md")) == 83


def test_sha256():
    assert src.sha256(b"abc").startswith("sha256:ba7816bf")


def test_resolve_file(tmp_path: Path):
    p = tmp_path / "Report Q3.docx"
    p.write_bytes(b"data")
    r = src.resolve(str(p))
    assert (r.kind, r.url, r.filename, r.data, r.error) == ("file", None, "report-q3.docx", b"data", None)


def test_resolve_arxiv_fetches_pdf():
    calls = []

    def fetch(url):
        calls.append(url)
        return b"%PDF", "application/pdf"

    r = src.resolve("2403.01234v2", fetch=fetch)
    assert calls == ["https://arxiv.org/pdf/2403.01234v2"]
    assert (r.kind, r.url, r.filename, r.data) == ("arxiv", "https://arxiv.org/abs/2403.01234v2", "2403.01234v2.pdf", b"%PDF")


def test_resolve_url_html_with_charset_saved_as_html():
    r = src.resolve("https://example.com/blog/post-1", fetch=lambda u: (b"<html>x</html>", "text/html; charset=utf-8"))
    assert r.kind == "url" and r.filename == "example-com-blog-post-1.html" and r.data == b"<html>x</html>"


def test_resolve_url_pdf_content_type():
    r = src.resolve("https://example.com/paper", fetch=lambda u: (b"%PDF", "application/pdf"))
    assert r.filename == "example-com-paper.pdf"


def test_resolve_doi_goes_through_doi_org():
    r = src.resolve("10.1000/xyz123", fetch=lambda u: (b"%PDF", "application/pdf") if u == "https://doi.org/10.1000/xyz123" else pytest.fail(u))
    assert (r.kind, r.url, r.filename) == ("doi", "https://doi.org/10.1000/xyz123", "10-1000-xyz123.pdf")


def test_resolve_fetch_failure_keeps_url_and_filename():
    def boom(u):
        raise OSError("timeout")

    r = src.resolve("https://example.com/a", fetch=boom)
    assert r.data is None and "timeout" in r.error and r.filename == "example-com-a.html" and r.url == "https://example.com/a"


def test_resolve_missing_file():
    r = src.resolve("/nonexistent/file.pdf")
    assert r.data is None and "not found" in r.error.lower()


def test_url_and_doi_stems_ignore_dots():
    html = lambda u: (b"x", "text/html")
    pdf = lambda u: (b"x", "application/pdf")
    assert src.resolve("https://example.com/", fetch=html).filename == "example-com.html"
    assert src.resolve("https://example.com/x.pdf", fetch=pdf).filename == "example-com-x-pdf.pdf"
    assert src.resolve("10.1000/abc.v2", fetch=pdf).filename == "10-1000-abc-v2.pdf"


def test_classify_arxiv_variants():
    assert src.classify("hep-th/9901001") == ("arxiv", "hep-th/9901001")
    assert src.classify("https://arxiv.org/abs/2403.01234?context=cs") == ("arxiv", "2403.01234")
    assert src.classify("https://export.arxiv.org/pdf/2403.01234v1") == ("arxiv", "2403.01234v1")


def test_resolve_old_style_arxiv():
    calls = []

    def fetch(u):
        calls.append(u)
        return b"%PDF", "application/pdf"

    r = src.resolve("hep-th/9901001", fetch=fetch)
    assert calls == ["https://arxiv.org/pdf/hep-th/9901001"]
    assert r.filename == "hep-th-9901001.pdf" and r.url == "https://arxiv.org/abs/hep-th/9901001"


def test_classify_existing_relative_path_is_file(tmp_path: Path, monkeypatch):
    (tmp_path / "10.1000").mkdir()
    (tmp_path / "10.1000" / "notes.pdf").write_bytes(b"x")
    monkeypatch.chdir(tmp_path)
    assert src.classify("10.1000/notes.pdf") == ("file", "10.1000/notes.pdf")


def test_resolve_bad_fetcher_shape_raises():
    with pytest.raises(ValueError):
        src.resolve("https://example.com/a", fetch=lambda u: b"just bytes")
