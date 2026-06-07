from filternarrange_filter_column.plugin import plugin


def test_validate_missing_kind_fails():
    errs = plugin.validate({"keep": ["a"]})
    assert any(e.field == "kind" for e in errs)


def test_validate_empty_keep_fails():
    errs = plugin.validate({"kind": "column", "keep": []})
    assert any(e.field == "keep" for e in errs)


def test_validate_wrong_kind_fails():
    errs = plugin.validate({"kind": "row", "keep": ["a"]})
    assert any(e.field == "kind" for e in errs)


def test_validate_ok():
    errs = plugin.validate({"kind": "column", "keep": ["a"]})
    assert errs == []
