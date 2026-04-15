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


def test_load_notes_splits_pipe_separator(gs):
    gs.load_cim10_notes("cim10_notes_sample.csv")
    assert "A048" in gs.cim10_notes
    notes = gs.cim10_notes["A048"]
    assert notes["inclusion_notes"] == [
        "infections à Clostridium",
        "infections à Yersinia",
        "entérocolite à C. difficile non précisée",
    ]
    assert notes["exclusion_notes"] == [
        "intoxication alimentaire bactérienne (A05.-)",
        "tuberculose intestinale (A18.3+ K93.0*)",
    ]


def test_load_notes_handles_empty_column(gs):
    gs.load_cim10_notes("cim10_notes_sample.csv")
    assert gs.cim10_notes["A049"]["inclusion_notes"] == []
    assert gs.cim10_notes["A049"]["exclusion_notes"] == ["diarrhée SAI (A09)"]


def test_load_notes_missing_file_silent(gs, recwarn):
    gs.load_cim10_notes("does_not_exist.csv")
    assert gs.cim10_notes == {}
    assert any("not found" in str(w.message) for w in recwarn.list), \
        "expected a UserWarning about missing file"


def test_format_enrichment_hierarchy_only(gs):
    """Code present in hierarchy, no notes → only the Hiérarchie line."""
    gs.load_cim10_hierarchy("cim10_hierarchy_sample.csv")
    # notes NOT loaded → cim10_notes is {}
    result = gs._format_cim10_enrichment("E119", include_notes=True)
    expected = (
        "     Hiérarchie : Chapitre IV — Maladies endocriniennes\n"
        "                  > Bloc E10-E14 — Diabète sucré\n"
        "                  > Catégorie E11 — Diabète sucré de type 2\n"
    )
    assert result == expected


def test_format_enrichment_full_hierarchy_and_notes(gs):
    gs.load_cim10_hierarchy("cim10_hierarchy_sample.csv")
    gs.load_cim10_notes("cim10_notes_sample.csv")
    result = gs._format_cim10_enrichment("A048", include_notes=True)
    expected = (
        "     Hiérarchie : Chapitre I — Maladies infectieuses et parasitaires\n"
        "                  > Bloc A00-A09 — Maladies intestinales infectieuses\n"
        "                  > Catégorie A04 — Autres infections intestinales bactériennes\n"
        "     Inclus : infections à Clostridium ; infections à Yersinia ; entérocolite à C. difficile non précisée\n"
        "     Exclus : intoxication alimentaire bactérienne (A05.-) ; tuberculose intestinale (A18.3+ K93.0*)\n"
    )
    assert result == expected


def test_format_enrichment_only_exclusion(gs):
    """Code with only exclusion note, no inclusion."""
    gs.load_cim10_hierarchy("cim10_hierarchy_sample.csv")
    gs.load_cim10_notes("cim10_notes_sample.csv")
    result = gs._format_cim10_enrichment("A049", include_notes=True)
    assert "Inclus :" not in result
    assert "Exclus : diarrhée SAI (A09)" in result


def test_format_enrichment_silent_fallback_missing_code(gs):
    """Code not present in any loaded referential → empty string."""
    gs.load_cim10_hierarchy("cim10_hierarchy_sample.csv")
    gs.load_cim10_notes("cim10_notes_sample.csv")
    assert gs._format_cim10_enrichment("Z999") == ""


def test_format_enrichment_silent_fallback_nothing_loaded(gs):
    """No referential loaded at all → empty string, no exception."""
    assert gs._format_cim10_enrichment("A048") == ""
