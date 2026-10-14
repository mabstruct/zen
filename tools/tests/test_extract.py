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
