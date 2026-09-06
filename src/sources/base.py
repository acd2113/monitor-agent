import html
import re
from datetime import datetime
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse


def strip_html(text):
    text = html.unescape(text or "")
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\s+", " ", text).strip()


def parse_date(value):
    if not value:
        return None, True
    if isinstance(value, datetime):
        return value, False
    if isinstance(value, (tuple, list)):
        try:
            return datetime(*value[:6]), False
        except (TypeError, ValueError):
            pass
    text = str(value)
    try:
        return parsedate_to_datetime(text), False
    except (TypeError, ValueError):
        pass
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")), False
    except (TypeError, ValueError):
        pass
    return None, True


def hostname(url):
    return urlparse(url).netloc or url
