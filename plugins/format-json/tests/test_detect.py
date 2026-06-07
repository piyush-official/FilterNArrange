from filternarrange_format_json.detect import detect_json


def test_detect_array(people_json):
    r = detect_json(people_json)
    assert r.format == "json"
    assert r.confidence >= 0.9


def test_detect_object(nested_json):
    r = detect_json(nested_json)
    assert r.format == "json"
    assert r.confidence >= 0.9


def test_detect_garbage():
    r = detect_json(b"not json at all !!!")
    assert r.confidence == 0.0
