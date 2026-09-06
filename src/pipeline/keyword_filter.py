import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class KeywordRuleGroup:
    required: list[str] = field(default_factory=list)
    normal: list[str] = field(default_factory=list)
    exclude: list[str] = field(default_factory=list)
    regex: list[re.Pattern] = field(default_factory=list)
    max_count: int = 0
    display: str = ""


def load_rules(path):
    text = Path(path).read_text(encoding="utf-8")
    groups = []
    current = KeywordRuleGroup()

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            if current.required or current.normal or current.regex:
                groups.append(current)
                current = KeywordRuleGroup()
            continue

        if line.startswith("+"):
            current.required.append(line[1:].strip().lower())
        elif line.startswith("!"):
            current.exclude.append(line[1:].strip().lower())
        elif line.startswith("@"):
            try:
                current.max_count = int(line[1:])
            except ValueError:
                pass
        elif line.startswith("/"):
            match = re.match(r"^/(.+)/[a-z]*$", line)
            if match:
                current.regex.append(re.compile(match.group(1), re.IGNORECASE))
        elif "=>" in line:
            left, right = line.split("=>", 1)
            current.display = right.strip()
            left = left.strip()
            if left:
                current.normal.append(left.lower())
        else:
            current.normal.append(line.lower())

    if current.required or current.normal or current.regex:
        groups.append(current)
    return groups


def _matches(item, group):
    title = (item.title or "").lower()
    if group.required and not all(word in title for word in group.required):
        return False
    if group.normal and not any(word in title for word in group.normal):
        return False
    if group.exclude and any(word in title for word in group.exclude):
        return False
    if group.regex and not any(pattern.search(title) for pattern in group.regex):
        return False
    return True


def filter_items(items, path):
    groups = load_rules(path)
    if not groups:
        return items

    selected = []
    seen = set()
    for group in groups:
        matched = [item for item in items if _matches(item, group)]
        if group.max_count > 0:
            matched = matched[: group.max_count]
        for item in matched:
            key = item.url or item.title
            if key not in seen:
                seen.add(key)
                selected.append(item)
    return selected
