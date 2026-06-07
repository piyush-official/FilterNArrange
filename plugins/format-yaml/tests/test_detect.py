from filternarrange_format_yaml import plugin


def test_detect_yaml_doc():
    sample = b"name: Ada\nage: 37\nlanguages:\n  - python\n  - ada\n"
    res = plugin.detect(sample)
    assert res.format == "yaml"
    assert res.confidence > 0.7


def test_detect_yaml_doc_marker():
    sample = b"---\nfoo: bar\n"
    res = plugin.detect(sample)
    assert res.confidence > 0.9


def test_json_is_not_yaml():
    sample = b'{"a":1}'
    res = plugin.detect(sample)
    assert res.confidence < 0.4
