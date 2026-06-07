from filternarrange_format_jsonl import plugin


def test_detect_jsonl():
    sample = b'{"id":1,"name":"Ada"}\n{"id":2,"name":"Grace"}\n'
    res = plugin.detect(sample)
    assert res.format == "jsonl"
    assert res.confidence > 0.9


def test_single_json_object_not_jsonl():
    sample = b'{"id":1,"name":"Ada"}'
    res = plugin.detect(sample)
    assert res.confidence < 0.5


def test_json_array_not_jsonl():
    sample = b'[{"id":1}]'
    res = plugin.detect(sample)
    assert res.confidence < 0.1
