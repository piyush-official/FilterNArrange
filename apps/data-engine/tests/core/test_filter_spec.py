import pytest
from filternarrange_engine.core.filter_spec import (
    parse_filter_spec, ColumnSpec, RowSpec, ExpressionSpec, RegexSpec,
)


def test_parse_column_spec():
    spec = parse_filter_spec({"kind": "column", "include": ["a", "b"]})
    assert isinstance(spec, ColumnSpec)
    assert spec.include == ["a", "b"]


def test_parse_row_spec():
    spec = parse_filter_spec({"kind": "row", "predicate": {"col": "age", "op": "gt", "value": 18}})
    assert isinstance(spec, RowSpec)
    assert spec.predicate.op == "gt"


def test_parse_expression_spec():
    spec = parse_filter_spec({"kind": "expression", "expr": "age > 18 AND country = 'IN'"})
    assert isinstance(spec, ExpressionSpec)


def test_parse_regex_spec():
    spec = parse_filter_spec({"kind": "regex", "pattern": "^foo", "flags": ["i"]})
    assert isinstance(spec, RegexSpec)
    assert spec.flags == ["i"]


def test_unknown_kind_raises():
    with pytest.raises(ValueError, match="unknown filter kind"):
        parse_filter_spec({"kind": "nope"})
