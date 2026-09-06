from src.models import SourceItem
from src.pipeline.keyword_filter import filter_items


def test_keyword_filter_rules(tmp_path):
    rule_file = tmp_path / "rules.txt"
    rule_file.write_text(
        "OpenAI\n"
        "+产品\n"
        "!八卦\n"
        "/GPT|Claude/\n",
        encoding="utf-8",
    )

    items = [
        SourceItem(title="OpenAI 产品发布 GPT-5", url="https://a.com/1", source="a"),
        SourceItem(title="OpenAI 八卦", url="https://a.com/2", source="a"),
        SourceItem(title="Claude 产品更新", url="https://a.com/3", source="a"),
    ]

    result = filter_items(items, str(rule_file))
    assert len(result) >= 1
    assert result[0].title == "OpenAI 产品发布 GPT-5"
