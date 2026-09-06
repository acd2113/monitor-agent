from src.sources.rss import RSSParser


RSS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>Example</title><item>
<title>RSS title</title>
<link>https://example.com/rss/1</link>
<guid>rss-1</guid>
<pubDate>Sun, 06 Sep 2026 10:00:00 GMT</pubDate>
<description><![CDATA[<p>RSS summary</p>]]></description>
</item></channel></rss>"""

ATOM_XML = """<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"><title>Example</title><entry>
<title>Atom title</title>
<link href="https://example.com/atom/1"/>
<id>atom-1</id>
<updated>2026-09-06T10:00:00Z</updated>
<summary>Atom summary</summary>
</entry></feed>"""

JSON_FEED = '{"version": "https://jsonfeed.org/version/1.1", "title": "Example", "items": [{"id": "jf-1", "url": "https://example.com/json/1", "title": "JSON title", "date_published": "2026-09-06T10:00:00Z", "content_text": "JSON summary"}]}'


def test_parse_rss():
    items = RSSParser().parse(RSS_XML)
    assert len(items) == 1
    assert items[0].title == "RSS title"
    assert items[0].url == "https://example.com/rss/1"
    assert items[0].guid == "rss-1"
    assert items[0].published_missing is False


def test_parse_atom():
    items = RSSParser().parse(ATOM_XML)
    assert len(items) == 1
    assert items[0].title == "Atom title"
    assert items[0].published_missing is False


def test_parse_json_feed():
    items = RSSParser().parse(JSON_FEED)
    assert len(items) == 1
    assert items[0].title == "JSON title"
    assert items[0].guid == "jf-1"
    assert items[0].published_missing is False
