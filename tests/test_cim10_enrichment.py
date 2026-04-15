"""Tests for CIM-10 enrichment loading and prompt formatting."""
from pathlib import Path
import pytest
from utils_v2 import generate_scenario

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def gs():
    """generate_scenario instance pointed at fixtures dir for ref files."""
    instance = generate_scenario.__new__(generate_scenario)
    instance.path_ref = str(FIXTURES) + "/"
    instance.cim10_hierarchy = {}
    instance.cim10_notes = {}
    return instance


def test_load_hierarchy_indexes_by_code(gs):
    gs.load_cim10_hierarchy("cim10_hierarchy_sample.csv")
    assert "A048" in gs.cim10_hierarchy
    entry = gs.cim10_hierarchy["A048"]
    assert entry["chapter_code"] == "I"
    assert entry["chapter_label"] == "Maladies infectieuses et parasitaires"
    assert entry["block_code"] == "A00-A09"
    assert entry["block_label"] == "Maladies intestinales infectieuses"
    assert entry["category_code"] == "A04"
    assert entry["category_label"] == "Autres infections intestinales bactériennes"
    assert entry["level"] == "leaf"


def test_load_hierarchy_missing_file_warns_and_falls_back(gs, recwarn):
    gs.load_cim10_hierarchy("does_not_exist.csv")
    assert gs.cim10_hierarchy == {}
    assert any("not found" in str(w.message) for w in recwarn.list), \
        "expected a UserWarning about missing file"
