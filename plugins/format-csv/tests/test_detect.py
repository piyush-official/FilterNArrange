from filternarrange_format_csv.detect import detect_csv


def test_detect_simple_csv(people_csv_bytes):
    r = detect_csv(people_csv_bytes)
    assert r.format == "csv"
    assert r.confidence >= 0.6


def test_detect_returns_zero_for_binary():
    r = detect_csv(b"\x89PNG\r\n\x1a\n binary data")
    assert r.confidence < 0.4
