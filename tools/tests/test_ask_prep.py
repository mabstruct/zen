import json
from pathlib import Path

from zen import ask_prep

HITS = [
    {
        "docid": "#ec65f3",
        "score": 0.99,
        "file": "qmd://zen/15_cosmology/sample-seventh.md",
        "line": 1269,
        "title": "Seventh rung: the Milky Way",
        "context": "ZEN personal knowledge vault.",
        "snippet": "@@ -1268,4 @@ (1267 before, 659 after)\nIn 1913, Russell presented\n“Relations Between the Spectra” to the\nRoyal Astronomical Society in London",
    },
    {
        "docid": "#a1b2c3",
        "score": 0.41,
        "file": "qmd://zen/90_wiki/entities/henry-norris-russell.md",
        "line": 18,
        "title": "Henry Norris Russell",
        "context": "",
        "snippet": "@@ -18,2 @@\n- Presented ... in 1913",
    },
]


def ok_qmd(question: str, n: int, root: Path):
    return 0, json.dumps(HITS), ""


def empty_qmd(question: str, n: int, root: Path):
    return 0, "[]", ""


def test_prints_index_without_health_and_wiki_index(vault: Path, capsys):
    assert ask_prep.run(vault, "anything", qmd=empty_qmd) == 0
    out = capsys.readouterr().out
    assert "# ZEN Index" in out
    assert "## 10_ai" in out
    assert "## Health" not in out
    assert "# Wiki index" in out


def test_reindexes_when_stale(vault: Path, capsys):
    assert (vault / "INDEX.md").read_text(encoding="utf-8").startswith("# stale")
    ask_prep.run(vault, "anything", qmd=empty_qmd)
    assert (vault / "INDEX.md").read_text(encoding="utf-8").startswith("# ZEN Index")
    assert "index rebuilt" in capsys.readouterr().out


def test_formats_qmd_hits_compactly(vault: Path, capsys):
    ask_prep.run(vault, "when did Russell present", qmd=ok_qmd)
    out = capsys.readouterr().out
    assert "### qmd hits for: when did Russell present" in out
    assert "1. [0.99] 15_cosmology/sample-seventh.md:1269 — Seventh rung: the Milky Way" in out
    assert "2. [0.41] 90_wiki/entities/henry-norris-russell.md:18 — Henry Norris Russell" in out
    assert "In 1913, Russell presented" in out
    assert "@@ -1268" not in out
    assert "qmd://" not in out


def test_qmd_failure_degrades_but_indexes_still_print(vault: Path, capsys):
    def broken(question, n, root):
        return 1, "", "Error: no index found\nmore"

    assert ask_prep.run(vault, "x", qmd=broken) == 0
    out = capsys.readouterr().out
    assert "qmd unavailable: Error: no index found" in out
    assert "# ZEN Index" in out and "# Wiki index" in out


def test_qmd_receives_question_n_and_project_root(vault: Path):
    seen = {}

    def spy(question, n, root):
        seen.update(question=question, n=n, root=root)
        return 0, "[]", ""

    ask_prep.run(vault, "what is attention", n=5, qmd=spy)
    assert seen == {"question": "what is attention", "n": 5, "root": vault.resolve().parent}


def test_main_entry_point(vault: Path, monkeypatch, capsys):
    monkeypatch.setattr(ask_prep, "default_qmd", empty_qmd)
    assert ask_prep.main(["--vault", str(vault), "what", "is", "attention"]) == 0
    assert "### qmd hits for: what is attention" in capsys.readouterr().out


def test_missing_vault_is_an_error(tmp_path: Path, capsys):
    assert ask_prep.run(tmp_path / "nope", "x", qmd=empty_qmd) == 2
    assert "no vault at" in capsys.readouterr().err
