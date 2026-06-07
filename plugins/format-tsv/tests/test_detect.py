from filternarrange_format_tsv import plugin


def test_detect_tab_dominant():
    sample = b"id\tname\tage\n1\tAda\t37\n2\tGrace\t85\n"
    res = plugin.detect(sample)
    assert res.format == "tsv"
    assert res.confidence > 0.9


def test_detect_csv_returns_low_conf():
    sample = b"id,name,age\n1,Ada,37\n"
    res = plugin.detect(sample)
    assert res.confidence < 0.3
