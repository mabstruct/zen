import subprocess
from pathlib import Path

from zen import sync_schema

TEMPLATE = "# Wiki schema\n\nRule one.\nRule two.\n"


def setup(tmp_path: Path, vault_text: str | None) -> tuple[Path, Path]:
    tpl = tmp_path / "workspace-template" / "90_wiki" / "SCHEMA.md"
    tpl.parent.mkdir(parents=True)
    tpl.write_text(TEMPLATE, encoding="utf-8")
    vault = tmp_path / "vault"
    (vault / "90_wiki").mkdir(parents=True)
    if vault_text is not None:
        (vault / "90_wiki" / "SCHEMA.md").write_text(vault_text, encoding="utf-8")
    return vault, tpl


def git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def test_check_in_sync(tmp_path: Path, capsys):
    vault, tpl = setup(tmp_path, TEMPLATE)
    assert sync_schema.run(vault, tpl, check=True) == 0
    assert "in sync" in capsys.readouterr().out


def test_check_drift_reports_diff_and_changes_nothing(tmp_path: Path, capsys):
    vault, tpl = setup(tmp_path, "# Wiki schema\n\nRule one.\n")
    assert sync_schema.run(vault, tpl, check=True) == 1
    out = capsys.readouterr().out
    assert "+Rule two." in out
    assert (vault / "90_wiki" / "SCHEMA.md").read_text(encoding="utf-8") == "# Wiki schema\n\nRule one.\n"


def test_sync_copies_template(tmp_path: Path, capsys):
    vault, tpl = setup(tmp_path, "# old\n")
    assert sync_schema.run(vault, tpl) == 0
    assert (vault / "90_wiki" / "SCHEMA.md").read_text(encoding="utf-8") == TEMPLATE
    assert "updated" in capsys.readouterr().out


def test_sync_when_missing(tmp_path: Path):
    vault, tpl = setup(tmp_path, None)
    assert sync_schema.run(vault, tpl, check=True) == 1
    assert sync_schema.run(vault, tpl) == 0
    assert (vault / "90_wiki" / "SCHEMA.md").read_text(encoding="utf-8") == TEMPLATE


def test_refuses_to_overwrite_uncommitted_edits(tmp_path: Path, capsys):
    vault, tpl = setup(tmp_path, "# committed\n")
    git(vault, "init", "-q", "-b", "main")
    git(vault, "-c", "user.email=t@t", "-c", "user.name=t", "add", "-A")
    git(vault, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "x")
    (vault / "90_wiki" / "SCHEMA.md").write_text("# local edit\n", encoding="utf-8")
    assert sync_schema.run(vault, tpl) == 1
    assert "uncommitted" in capsys.readouterr().err
    assert (vault / "90_wiki" / "SCHEMA.md").read_text(encoding="utf-8") == "# local edit\n"
    assert sync_schema.run(vault, tpl, force=True) == 0
    assert (vault / "90_wiki" / "SCHEMA.md").read_text(encoding="utf-8") == TEMPLATE


def test_committed_drift_is_synced_without_force(tmp_path: Path):
    vault, tpl = setup(tmp_path, "# committed old\n")
    git(vault, "init", "-q", "-b", "main")
    git(vault, "-c", "user.email=t@t", "-c", "user.name=t", "add", "-A")
    git(vault, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "x")
    assert sync_schema.run(vault, tpl) == 0


def test_main_defaults_resolve_from_repo_layout(tmp_path: Path, monkeypatch):
    vault, tpl = setup(tmp_path, TEMPLATE)
    monkeypatch.chdir(tmp_path / "workspace-template")
    assert sync_schema.main(["--check", "--vault", str(vault), "--template", str(tpl)]) == 0
