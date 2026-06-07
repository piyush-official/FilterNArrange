from filternarrange_format_xml import plugin


def test_detect_xml_decl():
    sample = b'<?xml version="1.0"?><root><x>1</x></root>'
    res = plugin.detect(sample)
    assert res.format == "xml"
    assert res.confidence > 0.95


def test_detect_xml_no_decl():
    sample = b"<root><x>1</x></root>"
    res = plugin.detect(sample)
    assert res.confidence > 0.8


def test_not_xml():
    res = plugin.detect(b"name=foo")
    assert res.confidence < 0.1
