import pathlib
from filternarrange_format_xlsx import plugin


def test_detect_xlsx():
    fixture = pathlib.Path(__file__).parent / "fixtures/two_sheets.xlsx"
    with open(fixture, "rb") as f:
        sample = f.read(8192)
    res = plugin.detect(sample)
    assert res.format == "xlsx"
    assert res.confidence > 0.95


def test_zip_without_xl_workbook_not_xlsx():
    sample = b"PK\x03\x04" + b"\x00" * 100
    res = plugin.detect(sample)
    assert res.confidence < 0.5
