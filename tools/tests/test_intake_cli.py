from pathlib import Path

from zen import intake_cli


def test_main_files_and_reindexes(vault: Path, tmp_path: Path, capsys):
    src = tmp_path / "x.html"; src.write_text("<p>hi</p>", encoding="utf-8")
    assert intake_cli.main([str(src), "--cluster", "10_ai", "--vault", str(vault)]) == 0
    out = capsys.readouterr().out
    assert "filed: 1" in out and "## Health" in out
    assert (vault / "INDEX.md").read_text(encoding="utf-8").startswith("# ZEN Index")


def test_main_inbox_mode_and_failure_exit_code(vault: Path, capsys):
    (vault / "00_inbox" / "n.md").write_text("---\ncluster: 99_bad\n---\n# N\n", encoding="utf-8")
    assert intake_cli.main(["--vault", str(vault), "--no-index"]) == 1
    assert "failed: 1" in capsys.readouterr().out


def test_folder_spec_expands_sorted_skipping_dotfiles(vault: Path, tmp_path: Path, capsys):
    d = tmp_path / "drop"
    d.mkdir()
    (d / "b.html").write_text("<p>b</p>", encoding="utf-8")
    (d / "a.html").write_text("<p>a</p>", encoding="utf-8")
    (d / ".hidden").write_text("x", encoding="utf-8")
    assert intake_cli.main([str(d), "--cluster", "10_ai", "--vault", str(vault), "--no-index"]) == 0
    out = capsys.readouterr().out
    assert "filed: 2" in out and out.index("a.html") < out.index("b.html")
