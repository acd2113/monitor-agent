import json
import re


def clean_json_tags(text):
    text = re.sub(r"```json\s*", "", text)
    text = re.sub(r"```", "", text)
    return text.strip()


def remove_reasoning_from_output(text):
    start = -1
    for i, ch in enumerate(text):
        if ch in "{[":
            start = i
            break
    if start != -1:
        return text[start:].strip()
    return text.strip()


def fix_incomplete_json(text):
    text = re.sub(r",\s*}", "}", text)
    text = re.sub(r",\s*]", "]", text)
    open_braces = text.count("{")
    close_braces = text.count("}")
    open_brackets = text.count("[")
    close_brackets = text.count("]")
    if open_braces > close_braces:
        text += "}" * (open_braces - close_braces)
    if open_brackets > close_brackets:
        text += "]" * (open_brackets - close_brackets)
    return text


def extract_json(text):
    cleaned = clean_json_tags(text)
    cleaned = remove_reasoning_from_output(cleaned)
    try:
        return json.loads(cleaned)
    except (json.JSONDecodeError, TypeError):
        pass

    fixed = fix_incomplete_json(cleaned)
    try:
        return json.loads(fixed)
    except (json.JSONDecodeError, TypeError):
        pass

    match = re.search(r"\{.*\}|\[.*\]", cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except (json.JSONDecodeError, TypeError):
            pass
    return None
