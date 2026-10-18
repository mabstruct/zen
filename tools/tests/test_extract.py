from pathlib import Path

from conftest import make_pdf
from zen import extract as ex


def test_pdf(tmp_path: Path):
    p = tmp_path / "a.pdf"
    p.write_bytes(make_pdf("Hello ZEN"))
    r = ex.extract(p)
    assert r.status == "ok" and "Hello ZEN" in r.markdown


def test_html_title_and_text(tmp_path: Path):
    p = tmp_path / "a.html"
    p.write_text("<html><head><title>Page T</title></head><body><h1>Head</h1><p>Body text</p></body></html>", encoding="utf-8")
    r = ex.extract(p)
    assert r.status == "ok" and "Body text" in r.markdown and r.title == "Page T"


def test_docx(tmp_path: Path):
    import docx

    d = docx.Document()
    d.add_paragraph("Docx body here")
    p = tmp_path / "a.docx"
    d.save(p)
    r = ex.extract(p)
    assert r.status == "ok" and "Docx body here" in r.markdown


def test_image_is_opaque(tmp_path: Path):
    p = tmp_path / "a.png"
    p.write_bytes(b"\x89PNG\r\n")
    r = ex.extract(p)
    assert r.status == "none" and r.markdown == "" and r.error is None


def test_corrupt_pdf_fails_softly(tmp_path: Path):
    p = tmp_path / "bad.pdf"
    p.write_bytes(b"not a pdf")
    r = ex.extract(p)
    assert r.status == "failed" and r.error and r.markdown == ""


def test_pdf_preserves_word_spacing(tmp_path: Path):
    p = tmp_path / "s.pdf"
    p.write_bytes(make_pdf("The dominant sequence transduction models"))
    r = ex.extract(p)
    assert "The dominant sequence transduction models" in r.markdown
    assert all(len(t) <= 25 for t in r.markdown.split())


def test_pdf_title_from_metadata_or_none(tmp_path: Path):
    p = tmp_path / "t.pdf"
    p.write_bytes(make_pdf("Hello ZEN"))
    assert ex.extract(p).title is None


def test_html_title_is_a_plain_str(tmp_path: Path):
    p = tmp_path / "t.html"
    p.write_text("<html><head><title>Page T</title></head><body><p>x</p></body></html>", encoding="utf-8")
    r = ex.extract(p)
    assert type(r.title) is str and r.title == "Page T"


def test_office_files_need_zip_magic(tmp_path: Path):
    for name in ("bad.docx", "bad.pptx", "bad.xlsx"):
        p = tmp_path / name
        p.write_bytes(b"not a zip")
        assert ex.extract(p).status == "failed", name


def test_uppercase_suffix_is_handled(tmp_path: Path):
    p = tmp_path / "UP.PDF"
    p.write_bytes(make_pdf("Upper case"))
    assert "Upper case" in ex.extract(p).markdown


def test_html_without_title_has_none(tmp_path: Path):
    p = tmp_path / "nt.html"
    p.write_text("<html><body><p>No title here</p></body></html>", encoding="utf-8")
    r = ex.extract(p)
    assert r.status == "ok" and r.title is None
