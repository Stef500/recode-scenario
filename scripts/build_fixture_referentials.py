# scripts/build_fixture_referentials.py
"""Crée tests/fixtures/referentials/ — mini-référentiels couvrant les codes
utilisés par tests/fixtures/profiles.parquet, suffisants pour faire tourner
le pipeline de génération de bout en bout dans les tests unitaires.
"""

from pathlib import Path

import pandas as pd
import yaml

OUT = Path("tests/fixtures/referentials")
OUT.mkdir(parents=True, exist_ok=True)

# --- ICD officiel ---
icd_data = [
    ("C349", "Tumeur maligne des bronches et du poumon, sans précision", 1),
    ("C509", "Tumeur maligne du sein, sans précision", 1),
    ("D649", "Anémie, sans précision", 1),
    ("E110", "Diabète sucré de type 2 avec coma", 1),
    ("E11", "Diabète sucré de type 2", 1),
    ("E785", "Hyperlipidémie, sans précision", 1),
    ("H251", "Cataracte sénile nucléaire", 1),
    ("I10", "Hypertension essentielle (primitive)", 1),
    ("I500", "Insuffisance cardiaque congestive", 1),
    ("J159", "Pneumopathie bactérienne, sans précision", 1),
    ("K359", "Appendicite aiguë, sans précision", 1),
    ("N183", "Maladie rénale chronique, stade 3", 1),
    ("O800", "Accouchement spontané par présentation du sommet", 1),
    ("O829", "Accouchement par césarienne, sans précision", 1),
    ("Z511", "Séance de chimiothérapie pour tumeur", 1),
    ("Z513", "Séance de transfusion sanguine", 1),
    ("C780", "Tumeur maligne secondaire du poumon", 1),
    ("C770", "Métastase ganglionnaire de la tête, du cou", 1),
]
pd.DataFrame(icd_data, columns=["icd_code", "icd_code_description", "aut_mco"]).to_parquet(
    OUT / "icd_official.parquet", index=False
)

# --- DRG statistics ---
drg_stats = [
    ("02C05", 0.5, 0.3),
    ("04M05", 5.2, 1.8),
    ("05M09", 7.5, 2.5),
    ("06C12", 2.8, 0.9),
    ("09C04", 4.5, 1.5),
    ("10M11", 6.8, 2.1),
    ("14C06", 5.5, 1.2),
    ("14Z10", 3.2, 0.8),
    ("28Z07", 0.0, 0.0),
    ("28Z14", 0.0, 0.0),
]
pd.DataFrame(drg_stats, columns=["drg_parent_code", "los_mean", "los_sd"]).to_parquet(
    OUT / "drg_statistics.parquet", index=False
)

# --- DRG groups (libellés) ---
drg_groups = [
    ("02C05", "Interventions sur le cristallin"),
    ("04M05", "Infections et inflammations respiratoires"),
    ("05M09", "Insuffisances cardiaques"),
    ("06C12", "Appendicectomies"),
    ("09C04", "Mastectomies"),
    ("10M11", "Affections endocriniennes"),
    ("14C06", "Césariennes"),
    ("14Z10", "Accouchements par voie basse"),
    ("28Z07", "Chimiothérapie pour tumeur"),
    ("28Z14", "Transfusion"),
]
pd.DataFrame(drg_groups, columns=["drg_parent_code", "drg_parent_description"]).to_parquet(
    OUT / "drg_groups.parquet", index=False
)

# --- Cancer treatments (mini) ---
cancer = [
    (
        "C50",
        "Sein",
        "Carcinome canalaire infiltrant",
        "II",
        "RH+/HER2-",
        "Chirurgie + radiothérapie + hormonothérapie",
        "AC-T",
    ),
    ("C34", "Poumon", "Adénocarcinome", "IV", "EGFR+", "Thérapie ciblée", "Osimertinib"),
]
pd.DataFrame(
    cancer,
    columns=[
        "icd_parent_code",
        "primary_site",
        "histological_type",
        "stage",
        "biomarkers",
        "treatment_recommendation",
        "chemotherapy_regimen",
    ],
).to_parquet(OUT / "cancer_treatments.parquet", index=False)

# --- Names (small fake list) ---
names = [
    ("Jean", "Dupont", 1),
    ("Marie", "Martin", 2),
    ("Pierre", "Durand", 1),
    ("Sophie", "Bernard", 2),
    ("Luc", "Petit", 1),
    ("Claire", "Robert", 2),
    ("Marc", "Richard", 1),
    ("Anne", "Moreau", 2),
    ("Paul", "Simon", 1),
    ("Julie", "Laurent", 2),
]
pd.DataFrame(names, columns=["prenom", "nom", "sexe"]).to_parquet(
    OUT / "names.parquet", index=False
)

# --- Hospitals ---
pd.DataFrame({"hospital": ["CHU Test A", "CHU Test B", "Hôpital Test C"]}).to_parquet(
    OUT / "hospitals.parquet", index=False
)

# --- Procedures (profile distribution) ---
procedures = [
    ("JQGA004", "14C06", "O829", "[18-50[", 2, 50),
    ("JQGD001", "14Z10", "O800", "[18-50[", 2, 120),
]
pd.DataFrame(
    procedures,
    columns=["procedure", "drg_parent_code", "icd_primary_code", "cage2", "sexe", "nb"],
).to_parquet(OUT / "procedures.parquet", index=False)

# --- Procedure official (CCAM with descriptions) ---
procedure_official = [
    ("JQGA004", "Césarienne"),
    ("JQGD001", "Accouchement spontané par voie basse"),
    ("DAFA001", "Examen anatomopathologique"),
]
pd.DataFrame(procedure_official, columns=["procedure", "procedure_description"]).to_parquet(
    OUT / "procedure_official.parquet", index=False
)

# --- Secondary ICD (profile distribution) ---
secondary_icd = [
    ("I10", "05M09", "I500", "[50-[", 2, 60, "Chronic", "I50"),
    ("E785", "05M09", "I500", "[50-[", 2, 40, "Chronic", "E78"),
    ("N183", "05M09", "I500", "[50-[", 2, 20, "Chronic", "N18"),
]
pd.DataFrame(
    secondary_icd,
    columns=[
        "icd_secondary_code",
        "drg_parent_code",
        "icd_primary_code",
        "cage2",
        "sexe",
        "nb",
        "type",
        "icd_primary_parent_code",
    ],
).to_parquet(OUT / "secondary_icd.parquet", index=False)

# --- Specialty referential ---
specialty = [
    ("02C05", "OPHTALMOLOGIE", 1.0, "[18-30["),
    ("04M05", "PNEUMOLOGIE", 1.0, "[60-70["),
    ("05M09", "CARDIOLOGIE", 1.0, "[80-["),
    ("06C12", "CHIRURGIE GENERALE", 1.0, "[18-30["),
    ("09C04", "CHIRURGIE GENERALE", 1.0, "[40-50["),
    ("10M11", "ENDOCRINOLOGIE", 1.0, "[70-80["),
    ("14C06", "OBSTETRIQUE", 1.0, "[30-40["),
    ("14Z10", "OBSTETRIQUE", 1.0, "[18-30["),
    ("28Z07", "ONCOLOGIE MEDICALE", 1.0, "[60-70["),
    ("28Z14", "MEDECINE INTERNE", 1.0, "[80-["),
]
pd.DataFrame(specialty, columns=["drg_parent_code", "specialty", "ratio", "age"]).to_parquet(
    OUT / "specialty.parquet", index=False
)

# --- Constants YAML ---
(OUT / "constants").mkdir(exist_ok=True)
(OUT / "constants/cancer_codes.yaml").write_text(
    yaml.safe_dump(
        {
            "metastasis_lymph_nodes": [
                "C770",
                "C771",
                "C772",
                "C773",
                "C774",
                "C775",
                "C778",
                "C779",
            ],
            "metastasis_other": ["C780", "C781", "C782", "C783", "C784", "C785"],
            "contact_treatment": ["Z491", "Z511", "Z512", "Z5101", "Z513", "Z516"],
            "chemotherapy_non_tumoral": ["Z512"],
            "all_cancer": ["C509", "C50", "C349", "C34"],
        }
    )
)
(OUT / "constants/drg_categories.yaml").write_text(
    yaml.safe_dump(
        {
            "chemotherapy_root_codes": ["28Z07", "17M05", "17M06"],
            "radiotherapy_root_codes": ["17K04", "17K05"],
            "vaginal_delivery_groups": [
                "14C03",
                "14Z09",
                "14Z10",
                "14Z11",
                "14Z12",
                "14Z13",
                "14Z14",
            ],
            "c_section_groups": ["14C06", "14C07", "14C08"],
            "transplant": ["27Z02", "27Z03", "27Z04"],
            "transfusion": ["28Z14"],
            "apheresis": ["28Z16"],
            "palliative_care": ["23Z02"],
            "stomies": ["06M17"],
            "deceased": ["04M24"],
            "diagnostic_workup": ["23M03"],
        }
    )
)
(OUT / "constants/icd_categories.yaml").write_text(
    yaml.safe_dump(
        {
            "ascites": ["R18"],
            "pleural_effusion": ["J90", "J91", "J940", "J941"],
            "chronic_intractable_pain": ["R5210", "R5218"],
            "cosmetic_surgery": ["Z410", "Z411"],
            "prophylactic_intervention": ["Z400", "Z401", "Z408"],
            "plastic_surgery": ["Z420", "Z421"],
            "comfort_intervention": ["Z4180"],
            "overnight_study": ["Z040"],
            "sensitization_tests": ["Z012"],
            "exclusions": [],
            "exclusion_specialty": [],
        }
    )
)
(OUT / "constants/procedure_codes.yaml").write_text(
    yaml.safe_dump(
        {
            "vaginal_delivery": ["JQGD001", "JQGD002"],
            "c_section": ["JQGA002", "JQGA003", "JQGA004", "JQGA005"],
        }
    )
)

# --- Chronic (mini, empty for fixtures) ---
pd.DataFrame({"code": [], "chronic": [], "libelle": []}).astype(
    {"code": str, "chronic": int, "libelle": str}
).to_parquet(OUT / "chronic.parquet", index=False)

# --- Complications (mini, empty) ---
pd.DataFrame({"icd_code": pd.Series(dtype=str)}).to_parquet(
    OUT / "complications.parquet", index=False
)

# --- ICD synonyms (mini) ---
pd.DataFrame(
    {"icd_code": ["I500"], "icd_code_description": ["Insuffisance cardiaque décompensée"]}
).to_parquet(OUT / "icd_synonyms.parquet", index=False)

print(f"Wrote mini-referentials to {OUT}")
