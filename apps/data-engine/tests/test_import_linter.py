import pathlib



def test_import_linter_passes(monkeypatch):
    from importlinter import cli

    root = pathlib.Path(__file__).resolve().parents[1]
    monkeypatch.chdir(root)
    rc = cli.lint_imports()
    assert rc == cli.EXIT_STATUS_SUCCESS
