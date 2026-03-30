from skills.registry import build_default_registry


def test_registry_discovers_skills():
    registry = build_default_registry()
    skills = registry.describe()
    names = {item["name"] for item in skills}
    assert "RetrieveSkill" in names
    assert "GameIndustryTrendSkill" in names
    retrieve = next(item for item in skills if item["name"] == "RetrieveSkill")
    assert retrieve["skill_id"] == "retrieve"
    assert retrieve["skill_layer"] == "foundation"
    assert retrieve["required_inputs"]
