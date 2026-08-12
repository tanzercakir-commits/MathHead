"""Legacy recommendation must never regain prose- or keyword-based routing authority."""

from mathhead.router import route


def test_exact_tool_name_remains_a_compatibility_lookup():
    result = route("recommend_tool", {"query": "verify_equality", "limit": 5})
    assert result.status == "ok"
    assert [item["tool"] for item in result.recommendations] == ["verify_equality"]
    assert result.recommendations[0]["score"] == 1


def test_prose_keywords_descriptions_and_substrings_do_not_select():
    for query in (
        "verify that two expressions are equal",
        "derivative claim",
        "verify_equal",
        "equality",
        "VERIFY_EQUALITY",
    ):
        result = route("recommend_tool", {"query": query, "limit": 99})
        assert result.status == "unknown"
        assert result.reason_code == "EXACT_NAME_NOT_FOUND"
        assert result.recommendations == []
