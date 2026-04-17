"""Tests for TreatmentRecommendation model."""

from __future__ import annotations


def test_treatment_recommendation_with_aliases() -> None:
    from recode.models import TreatmentRecommendation

    data = {
        "Code CIM": "C50",
        "Localisation": "Sein",
        "Type Histologique": "Carcinome canalaire",
        "Stade": "II",
        "Marqueurs Tumoraux": "HER2+",
        "Traitement": "Chirurgie + radiothérapie",
        "Protocole de Chimiothérapie": "AC-T",
    }
    tr = TreatmentRecommendation.model_validate(data)
    assert tr.icd_parent_code == "C50"
    assert tr.chemotherapy_regimen == "AC-T"
