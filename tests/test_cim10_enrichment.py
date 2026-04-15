"""Tests for CIM-10 enrichment loading and prompt formatting."""
from pathlib import Path
import pandas as pd
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
        "     Inclus : infections à Clostridium\n"
        "              ; infections à Yersinia\n"
        "              ; entérocolite à C. difficile non précisée\n"
        "     Exclus : intoxication alimentaire bactérienne (A05.-)\n"
        "              ; tuberculose intestinale (A18.3+ K93.0*)\n"
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


def test_format_enrichment_multiline_note_indented(gs):
    """An inclusion note with embedded newlines must be indented under its label."""
    gs.cim10_hierarchy = {}
    gs.cim10_notes = {
        "K528": {
            "inclusion_notes": [
                "Colite :\n - collagène\n - lymphocytaire\n - microscopique\nGastrite ou gastroentérite à éosinophiles"
            ],
            "exclusion_notes": [],
        }
    }
    result = gs._format_cim10_enrichment("K528", include_notes=True)
    expected = (
        "     Inclus : Colite :\n"
        "              - collagène\n"
        "              - lymphocytaire\n"
        "              - microscopique\n"
        "              Gastrite ou gastroentérite à éosinophiles\n"
    )
    assert result == expected


def test_prompt_section_enriches_dp_and_skips_non_eight_das(gs):
    """The 'Codage CIM10' section enriches DP always, DAS only when 4-char ending in 8."""
    gs.load_cim10_hierarchy("cim10_hierarchy_sample.csv")
    gs.load_cim10_notes("cim10_notes_sample.csv")

    # Minimal helpers used by make_prompts_marks_from_scenario
    gs.icd_codes_cancer = []   # not a cancer case

    def fake_get_icd_description(code):
        table = {
            "A048": "Autres infections intestinales bactériennes précisées",
            "E119": "Diabète sucré de type 2, sans complication",
            "A049": "Infection intestinale bactérienne, sans précision",
        }
        return table.get(code, code)
    gs.get_icd_description = fake_get_icd_description

    scenario = {
        "age": 65,
        "sexe": 1,
        "icd_primary_code": "A048",
        "icd_primary_description": "Autres infections intestinales bactériennes précisées",
        "icd_secondary_code": ["E119", "A049"],
        "text_secondary_icd_official": "",
        "case_management_type": "DP",
        "case_management_type_text": "Diagnostic principal",
        "case_management_description": "",
        "drg_parent_code": "06M05",
    }
    prompt = gs.make_prompts_marks_from_scenario(scenario)

    # DP enrichment present
    assert "Hiérarchie : Chapitre I — Maladies infectieuses et parasitaires" in prompt
    assert "Inclus : infections à Clostridium" in prompt

    # DAS A049 is 4-char ending in 9, NOT enriched (no Exclus block under it)
    assert "Exclus : diarrhée SAI (A09)" not in prompt

    # DAS E119 not ending in 8, NOT enriched
    e119_index = prompt.index("E119")
    after_e119 = prompt[e119_index:e119_index + 300]
    assert "Hiérarchie" not in after_e119


def test_prompt_section_enriches_das_in_eight(gs):
    """A DAS code with 4 chars ending in 8 gets its own enrichment block."""
    gs.load_cim10_hierarchy("cim10_hierarchy_sample.csv")
    gs.load_cim10_notes("cim10_notes_sample.csv")
    gs.icd_codes_cancer = []

    def fake_get_icd_description(code):
        return {"A048": "Autres infections intestinales bactériennes précisées"}.get(code, code)
    gs.get_icd_description = fake_get_icd_description

    scenario = {
        "age": 50, "sexe": 2,
        "icd_primary_code": "E119",
        "icd_primary_description": "Diabète sucré de type 2, sans complication",
        "icd_secondary_code": ["A048"],     # 4-char ending in 8 → enriched
        "text_secondary_icd_official": "",
        "case_management_type": "DP",
        "case_management_type_text": "Diagnostic principal",
        "case_management_description": "",
        "drg_parent_code": "10M05",
    }
    prompt = gs.make_prompts_marks_from_scenario(scenario)
    # DP enrichment (E119)
    assert "Chapitre IV — Maladies endocriniennes" in prompt
    # DAS enrichment (A048)
    assert "Inclus : infections à Clostridium" in prompt


def test_prompt_section_full_golden_block(gs):
    """Lock in the exact multi-line format of the 'Codage CIM10' block."""
    gs.load_cim10_hierarchy("cim10_hierarchy_sample.csv")
    gs.load_cim10_notes("cim10_notes_sample.csv")
    gs.icd_codes_cancer = []

    def fake_get_icd_description(code):
        return {
            "A048": "Autres infections intestinales bactériennes précisées",
            "E119": "Diabète sucré de type 2, sans complication",
            "A049": "Infection intestinale bactérienne, sans précision",
        }.get(code, code)
    gs.get_icd_description = fake_get_icd_description

    scenario = {
        "age": 65, "sexe": 1,
        "icd_primary_code": "A048",
        "icd_primary_description": "Autres infections intestinales bactériennes précisées",
        "icd_secondary_code": ["E119", "A049"],
        "text_secondary_icd_official": "",
        "case_management_type": "DP",
        "case_management_type_text": "Diagnostic principal",
        "case_management_description": "",
        "drg_parent_code": "06M05",
    }
    prompt = gs.make_prompts_marks_from_scenario(scenario)

    expected_block = (
        "- Codage CIM10 :\n"
        "   * Diagnostic principal : Autres infections intestinales bactériennes précisées (A048)\n"
        "     Hiérarchie : Chapitre I — Maladies infectieuses et parasitaires\n"
        "                  > Bloc A00-A09 — Maladies intestinales infectieuses\n"
        "                  > Catégorie A04 — Autres infections intestinales bactériennes\n"
        "     Inclus : infections à Clostridium\n"
        "              ; infections à Yersinia\n"
        "              ; entérocolite à C. difficile non précisée\n"
        "     Exclus : intoxication alimentaire bactérienne (A05.-)\n"
        "              ; tuberculose intestinale (A18.3+ K93.0*)\n"
        "   * Diagnostic associés : \n"
        "   - Diabète sucré de type 2, sans complication (E119)\n"
        "   - Infection intestinale bactérienne, sans précision (A049)\n"
    )
    assert expected_block in prompt, (
        f"expected_block not found in prompt.\n\nPrompt was:\n{prompt}"
    )


def test_prompt_section_string_secondary_codes_defensive(gs):
    """If icd_secondary_code is accidentally a string (CSV round-trip), don't iterate characters."""
    gs.load_cim10_hierarchy("cim10_hierarchy_sample.csv")
    gs.load_cim10_notes("cim10_notes_sample.csv")
    gs.icd_codes_cancer = []
    gs.get_icd_description = lambda code: code  # stub returns code itself

    scenario = {
        "age": 40, "sexe": 1,
        "icd_primary_code": "A048",
        "icd_primary_description": "Autres infections intestinales bactériennes précisées",
        "icd_secondary_code": "['E119', 'A049']",  # string, not a list — simulates CSV reload
        "text_secondary_icd_official": "- Fallback line (X00)\n",
        "case_management_type": "DP",
        "case_management_type_text": "Diagnostic principal",
        "case_management_description": "",
        "drg_parent_code": "06M05",
    }
    prompt = gs.make_prompts_marks_from_scenario(scenario)
    # The defensive guard should have reset secondary_codes to [] and triggered the elif fallback
    assert "Fallback line (X00)" in prompt
    # No char-by-char iteration (which would produce lines for '[', "'", 'E', etc.)
    assert "   - [" not in prompt
    assert "   - '" not in prompt


from scripts.build_cim10_enrichment import parse_rdf_to_dataframes, validate_hierarchy


def test_parse_rdf_produces_hierarchy_rows():
    hierarchy_df, notes_df = parse_rdf_to_dataframes(
        str(FIXTURES / "cim10_sample.ttl")
    )
    codes = set(hierarchy_df["code"])
    assert {"I", "A00-A09", "A04", "A048"} <= codes

    a048 = hierarchy_df[hierarchy_df["code"] == "A048"].iloc[0]
    assert a048["parent_code"] == "A04"
    assert a048["level"] == "category"
    assert a048["chapter_code"] == "I"
    assert a048["block_code"] == "A00-A09"
    assert a048["category_code"] == "A04"


def test_parse_rdf_produces_notes_rows():
    _, notes_df = parse_rdf_to_dataframes(str(FIXTURES / "cim10_sample.ttl"))
    assert "A048" in set(notes_df["code"])
    a048 = notes_df[notes_df["code"] == "A048"].iloc[0]
    inclusion_items = a048["inclusion_notes"].split("|")
    assert "infections à Clostridium" in inclusion_items
    assert "infections à Yersinia" in inclusion_items
    assert a048["exclusion_notes"] == "intoxication alimentaire bactérienne (A05.-)"


def test_validate_hierarchy_flags_missing_chapter_level():
    """If no concept has level='chapter', warn about predicate mapping."""
    df = pd.DataFrame([
        {"code": "A00", "level": "", "parent_code": ""},
        {"code": "A000", "level": "", "parent_code": "A00"},
    ])
    warnings = validate_hierarchy(df, expected_count=2, tolerance=0)
    assert any("dc:type predicate mapping likely wrong" in w for w in warnings)


def test_validate_hierarchy_flags_suspiciously_few_categories():
    """If category count is < expected/2, warn."""
    df = pd.DataFrame([
        {"code": "I", "level": "chapter", "parent_code": ""},
        {"code": "A00", "level": "category", "parent_code": "I"},
    ])
    warnings = validate_hierarchy(df, expected_count=100, tolerance=200)
    assert any("Suspiciously few categories" in w for w in warnings)


def test_validate_hierarchy_flags_missing_parent():
    df = pd.DataFrame([
        {"code": "A00", "level": "category", "parent_code": ""},
        {"code": "B00", "level": "category", "parent_code": "B"},
    ])
    warnings = validate_hierarchy(df, expected_count=2, tolerance=0)
    assert any("empty parent_code" in w for w in warnings)


def test_validate_hierarchy_flags_unexpected_count():
    df = pd.DataFrame([{"code": "A00", "level": "chapter", "parent_code": ""}])
    warnings = validate_hierarchy(df, expected_count=100, tolerance=10)
    assert any("Unexpected concept count" in w for w in warnings)


def test_validate_hierarchy_clean_returns_empty():
    # A sample where non-chapter codes all have parents, count matches, and
    # level distribution is plausible (1 chapter + > expected/2 categories).
    rows = [{"code": "I", "level": "chapter", "parent_code": ""}]
    # Add enough categories so the "suspiciously few categories" check passes.
    # expected_count=10, tolerance=0 → need > 5 categories. 6 categories does it.
    for i in range(6):
        rows.append({"code": f"A00{i}", "level": "category", "parent_code": "A00"})
    # Add 3 more rows (an extra category + blocks) to reach expected_count=10.
    rows.append({"code": "A00", "level": "category", "parent_code": "I"})
    rows.append({"code": "A00-A09", "level": "block", "parent_code": "I"})
    rows.append({"code": "B00", "level": "category", "parent_code": "A00"})
    df = pd.DataFrame(rows)
    assert len(df) == 10
    warnings = validate_hierarchy(df, expected_count=10, tolerance=0)
    assert warnings == [], f"expected no warnings, got: {warnings}"
