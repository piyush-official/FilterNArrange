import pytest
from filternarrange_engine.core.canonical import Column, TabularData
from filternarrange_engine.core.filter_spec import RegexSpec
from filternarrange_engine.core.types import TypeTag
from filternarrange_filter_regex import plugin


async def _aiter(items):
    for r in items:
        yield r


def _make(rows):
    return TabularData(
        schema=[
            Column("id", TypeTag.INTEGER, False),
            Column("name", TypeTag.STRING, False),
            Column("note", TypeTag.STRING, True),
        ],
        rows=_aiter(rows),
    )


@pytest.mark.asyncio
async def test_regex_any_string_col():
    td = _make([
        {"id": 1, "name": "Ada",   "note": "loves haskell"},
        {"id": 2, "name": "Grace", "note": "COBOL"},
        {"id": 3, "name": "Kid",   "note": "plays"},
    ])
    out = plugin.apply(td, RegexSpec(pattern=r"\bCOBOL\b"))
    rows = [r async for r in out.rows]
    assert [r["name"] for r in rows] == ["Grace"]


@pytest.mark.asyncio
async def test_flags_i():
    td = _make([{"id": 1, "name": "Ada", "note": "cobol fans"}])
    out = plugin.apply(td, RegexSpec(pattern="COBOL", flags=["i"]))
    rows = [r async for r in out.rows]
    assert len(rows) == 1


def test_validate_bad_pattern():
    errs = plugin.validate(RegexSpec(pattern="(unclosed"))
    assert errs and "regex" in errs[0].lower()
