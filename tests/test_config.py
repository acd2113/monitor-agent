from src.config import settings


def test_quality_first_defaults():
    assert settings.max_search_rounds == 4
    assert settings.max_web_searches == 6
    assert settings.relevance_threshold >= 0.8
    assert settings.title_sim_threshold == 0.90
    assert settings.content_jaccard_threshold == 0.88
    assert settings.classify_batch_size == 5
