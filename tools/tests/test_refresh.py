from datetime import datetime
from pathlib import Path

from zen import frontmatter as fm, health, intake, intake_cli, refresh, vault as vt

T1 = "2026-10-01T10:00:00+02:00"
T2 = "2026-10-15T12:00:00+02:00"
PAGE_A = b"<html><head><title>Page A</title></head><body><p>Body A</p></body></html>"
PAGE_B = b"<html><head><title>Page A</title></head><body><p>Body B changed</p></body></html>"


def boom(url):
    raise OSError("timeout")


def serve(data: bytes):
    return lambda url: (data, "text/html; charset=utf-8")


def missing_companion(vault: Path) -> str:
    r = intake.intake_item(vault, "https://example.com/a", "10_ai", fetch=boom, now=T1)
    assert r.status == "filed"
    return r.companion


def captured_companion(vault: Path, data: bytes = PAGE_A) -> str:
    r = intake.intake_item(vault, "https://example.com/a", "10_ai", fetch=serve(data), now=T1)
    assert r.status == "filed"
    return r.companion


def snapshot(vault: Path) -> dict[str, bytes]:
    return {p.relative_to(vault).as_posix(): p.read_bytes() for p in vault.rglob("*") if p.is_file()}


# --- retry-missing ---

def test_retry_missing_fills_companion_in_place(vault: Path):
    rel = missing_companion(vault)
    rep = refresh.retry_missing(vault, fetch=serve(PAGE_A), now=T2)
    assert [(i.companion, i.status) for i in rep.items] == [(rel, "refreshed")]
    doc = fm.read(vault / rel)
    assert doc.meta["snapshot"] == "ok" and doc.meta["extraction"] == "ok"
    assert doc.meta["created"] == T1 and doc.meta["updated"] == T2
    assert doc.meta["source"]["captured"] == T2 and doc.meta["source"]["hash"].startswith("sha256:")
    assert doc.meta["title"] == "Page A" and doc.body.startswith("# Page A\n")
    assert "Body A" in doc.body
    local = doc.meta["source"]["local"]
    assert (vault / "10_ai" / local).read_bytes() == PAGE_A


def test_retry_missing_still_failing_leaves_file_untouched(vault: Path):
    rel = missing_companion(vault)
    before = (vault / rel).read_bytes()
    rep = refresh.retry_missing(vault, fetch=boom, now=T2)
    assert [(i.companion, i.status) for i in rep.items] == [(rel, "still-missing")]
    assert "timeout" in rep.items[0].note
    assert (vault / rel).read_bytes() == before


def test_retry_missing_duplicate_content_refused(vault: Path, tmp_path: Path):
    rel = missing_companion(vault)
    local = tmp_path / "same.html"
    local.write_bytes(PAGE_A)
    assert intake.intake_item(vault, str(local), "11_research", now=T1).status == "filed"
    before = (vault / rel).read_bytes()
    rep = refresh.retry_missing(vault, fetch=serve(PAGE_A), now=T2)
    assert rep.items[0].status == "duplicate" and "11_research/same.md" in rep.items[0].note
    assert (vault / rel).read_bytes() == before


def test_retry_missing_with_nothing_missing(vault: Path):
    assert refresh.retry_missing(vault, fetch=serve(PAGE_A), now=T2).items == []


# --- recapture ---

def test_recapture_unchanged_touches_nothing(vault: Path):
    rel = captured_companion(vault)
    before = snapshot(vault)
    r = refresh.recapture(vault, rel, fetch=serve(PAGE_A), now=T2)
    assert r.status == "unchanged"
    assert snapshot(vault) == before


def test_recapture_changed_replaces_snapshot_and_clears_summary(vault: Path):
    rel = captured_companion(vault)
    p = vault / rel
    doc = fm.read(p)
    doc.meta["ingested"] = T1
    doc.body = doc.body.replace("## Summary\n", "## Summary\nOld summary line.\n")
    fm.write(p, doc)
    old_hash = doc.meta["source"]["hash"]

    r = refresh.recapture(vault, rel, fetch=serve(PAGE_B), now=T2)
    assert r.status == "refreshed" and r.companion == rel
    doc = fm.read(p)
    assert doc.meta["created"] == T1 and doc.meta["ingested"] == T1
    assert doc.meta["updated"] == T2 and doc.meta["source"]["captured"] == T2
    assert doc.meta["source"]["hash"] != old_hash
    assert "Old summary line." not in doc.body and "## Summary\n\n## Extracted text\n" in doc.body
    assert "Body B changed" in doc.body and "Body A" not in doc.body
    assert (vault / "10_ai" / doc.meta["source"]["local"]).read_bytes() == PAGE_B
    findings = health.check(vt.scan(vault), datetime.fromisoformat(T2))
    assert rel in [f.path for f in findings if f.kind == "wiki-behind"]


def test_recapture_without_url_refused(vault: Path, tmp_path: Path):
    local = tmp_path / "x.html"
    local.write_bytes(PAGE_A)
    rel = intake.intake_item(vault, str(local), "10_ai", now=T1).companion
    r = refresh.recapture(vault, rel, fetch=serve(PAGE_B), now=T2)
    assert r.status == "failed" and "source.url" in r.note


def test_recapture_duplicate_content_refused(vault: Path, tmp_path: Path):
    rel = captured_companion(vault)
    other = tmp_path / "b.html"
    other.write_bytes(PAGE_B)
    intake.intake_item(vault, str(other), "11_research", now=T1)
    before = (vault / rel).read_bytes()
    r = refresh.recapture(vault, rel, fetch=serve(PAGE_B), now=T2)
    assert r.status == "duplicate"
    assert (vault / rel).read_bytes() == before


def test_recapture_fetch_failure_reported(vault: Path):
    rel = captured_companion(vault)
    before = snapshot(vault)
    r = refresh.recapture(vault, rel, fetch=boom, now=T2)
    assert r.status == "failed" and "timeout" in r.note
    assert snapshot(vault) == before


def test_recapture_unknown_path_refused(vault: Path):
    assert refresh.recapture(vault, "10_ai/nope.md", fetch=serve(PAGE_A), now=T2).status == "failed"


# --- CLI ---

def test_cli_retry_missing_and_recapture(vault: Path, monkeypatch, capsys):
    rel = missing_companion(vault)
    monkeypatch.setattr(refresh, "default_fetch", serve(PAGE_A))
    assert intake_cli.main(["--retry-missing", "--vault", str(vault), "--no-index"]) == 0
    assert "refreshed: 1" in capsys.readouterr().out
    monkeypatch.setattr(refresh, "default_fetch", serve(PAGE_B))
    assert intake_cli.main(["--recapture", rel, "--vault", str(vault), "--no-index"]) == 0
    assert "refreshed" in capsys.readouterr().out
