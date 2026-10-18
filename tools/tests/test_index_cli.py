import json
import os
import time
from datetime import datetime
from pathlib import Path

from zen import index_cli

NOW = datetime.fromisoformat("2026-10-14T12:00:00+02:00")


def test_run_writes_both_outputs(vault: Path, capsys):
    assert index_cli.run(vault, now=NOW) == 0
    assert (vault / "INDEX.md").read_text(encoding="utf-8").startswith("# ZEN Index")
    m = json.loads((vault / "_meta" / "map.json").read_text(encoding="utf-8"))
    assert m["generated"] == "2026-10-14T12:00:00+02:00"
    out = capsys.readouterr().out
    assert "open conflicts" in out and "## Health" in out


def test_is_stale_and_check_mode(vault: Path):
    assert index_cli.is_stale(vault)  # fixture INDEX.md is older than content
    index_cli.run(vault, now=NOW)
    assert not index_cli.is_stale(vault)
    assert index_cli.run(vault, check=True) == 0
    time.sleep(0.01)
    p = vault / "10_ai" / "attention.md"
    os.utime(p, None)
    assert index_cli.is_stale(vault)
    assert index_cli.run(vault, check=True) == 1


def test_missing_index_is_stale(vault: Path):
    (vault / "INDEX.md").unlink()
    assert index_cli.is_stale(vault)


def test_main_default_vault_arg(vault: Path, monkeypatch):
    monkeypatch.chdir(vault.parent)
    assert index_cli.main([]) == 0
    assert (vault / "INDEX.md").exists()


def test_run_is_idempotent(vault: Path):
    index_cli.run(vault, now=NOW)
    first = (vault / "INDEX.md").read_bytes(), (vault / "_meta" / "map.json").read_bytes()
    index_cli.run(vault, now=NOW)
    assert first == ((vault / "INDEX.md").read_bytes(), (vault / "_meta" / "map.json").read_bytes())


def test_deleting_a_note_makes_index_stale(vault: Path):
    index_cli.run(vault, now=NOW)
    assert not index_cli.is_stale(vault)
    time.sleep(0.01)
    (vault / "11_research" / "orphan.md").unlink()
    assert index_cli.is_stale(vault)


def test_renaming_a_note_makes_index_stale(vault: Path):
    index_cli.run(vault, now=NOW)
    p = vault / "11_research" / "orphan.md"
    st = p.stat().st_mtime
    time.sleep(0.01)
    p.rename(vault / "11_research" / "renamed.md")
    os.utime(vault / "11_research" / "renamed.md", (st, st))  # mv keeps the file mtime
    assert index_cli.is_stale(vault)


def test_missing_vault_is_a_clear_error(tmp_path: Path, capsys):
    assert index_cli.run(tmp_path / "nope") == 2
    assert index_cli.run(tmp_path / "nope", check=True) == 2
    assert "no vault at" in capsys.readouterr().err
