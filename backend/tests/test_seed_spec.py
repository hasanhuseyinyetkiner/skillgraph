from app.seed import validate_seed_spec
from app.seed_data import RELATIONS, RESOURCES, ROLES, SKILLS


def test_seed_spec_counts_and_cycle() -> None:
    validate_seed_spec()
    assert len(SKILLS) >= 80
    assert len(ROLES) >= 20
    assert len(RESOURCES) >= 30
    families = {family for _title, family, _summary, _reqs in ROLES}
    assert "Data & Analytics" in families
    assert "Quality Engineering" in families
    assert any(item[2] == "prerequisite" and item[0] == "Legacy SOAP" for item in RELATIONS)
