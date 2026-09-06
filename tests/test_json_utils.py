from src.utils import clean_json_tags, extract_json


def test_extract_json_with_fence():
    raw = '```json\n{"a": 1}\n```'
    assert extract_json(raw) == {"a": 1}


def test_extract_json_after_reasoning():
    raw = 'Here is the result: {"b": 2}'
    assert extract_json(raw) == {"b": 2}


def test_clean_json_tags():
    assert clean_json_tags('```json\n{"a": 1}\n```') == '{"a": 1}'
