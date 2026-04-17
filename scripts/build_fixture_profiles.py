# scripts/build_fixture_profiles.py
"""Crée tests/fixtures/profiles.parquet — 10 profils synthétiques couvrant
les principales branches du pipeline de génération.

Profils choisis pour activer les règles ATIH les plus représentatives :
- 2× cancer (chirurgie / médical)
- 2× obstétrique (accouchement voie basse / césarienne)
- 2× chronique (diabète / insuffisance cardiaque)
- 2× aigu (urgences)
- 1× ambulatoire (chimio)
- 1× session répétitive (transfusion)

Tous les codes utilisés sont des codes CIM/GHM RÉELS de la nomenclature ATIH
publique mais les profils eux-mêmes sont entièrement inventés (aucune donnée
patient réelle).
"""

from pathlib import Path

import pandas as pd

PROFILES: list[dict] = [
    # 1. Cancer du sein chirurgical (femme 45-50)
    {
        "drg_parent_code": "09C04",
        "drg_parent_description": "Mastectomies",
        "icd_primary_code": "C509",
        "icd_primary_parent_code": "C50",
        "case_management_type": "C509",
        "cage": "[40-50[",
        "cage2": "[18-50[",
        "sexe": 2,
        "los": 5,
        "los_mean": 4.5,
        "los_sd": 1.5,
        "nb": 100,
        "admission_mode": "DOMICILE",
        "admission_type": "Inpatient",
        "discharge_disposition": "DOMICILE",
        "icd_secondary_code": "",
        "specialty": "CHIRURGIE GENERALE",
        "age2": 45,
    },
    # 2. Chimiothérapie ambulatoire (cancer du poumon, homme 60-70)
    {
        "drg_parent_code": "28Z07",
        "drg_parent_description": "Chimiothérapie pour tumeur",
        "icd_primary_code": "Z511",
        "icd_primary_parent_code": "Z51",
        "case_management_type": "C349",
        "cage": "[60-70[",
        "cage2": "[50-[",
        "sexe": 1,
        "los": 0,
        "los_mean": 0.0,
        "los_sd": 0.0,
        "nb": 50,
        "admission_mode": "DOMICILE",
        "admission_type": "Outpatient",
        "discharge_disposition": "DOMICILE",
        "icd_secondary_code": "",
        "specialty": "ONCOLOGIE MEDICALE",
        "age2": 65,
    },
    # 3. Accouchement voie basse spontané
    {
        "drg_parent_code": "14Z10",
        "drg_parent_description": "Accouchements par voie basse",
        "icd_primary_code": "O800",
        "icd_primary_parent_code": "O80",
        "case_management_type": "O800",
        "cage": "[18-30[",
        "cage2": "[18-50[",
        "sexe": 2,
        "los": 3,
        "los_mean": 3.2,
        "los_sd": 0.8,
        "nb": 200,
        "admission_mode": "DOMICILE",
        "admission_type": "Inpatient",
        "discharge_disposition": "DOMICILE",
        "icd_secondary_code": "",
        "specialty": "OBSTETRIQUE",
        "age2": 28,
    },
    # 4. Césarienne urgente
    {
        "drg_parent_code": "14C06",
        "drg_parent_description": "Césariennes",
        "icd_primary_code": "O829",
        "icd_primary_parent_code": "O82",
        "case_management_type": "O829",
        "cage": "[30-40[",
        "cage2": "[18-50[",
        "sexe": 2,
        "los": 6,
        "los_mean": 5.5,
        "los_sd": 1.2,
        "nb": 80,
        "admission_mode": "URGENCES",
        "admission_type": "Inpatient",
        "discharge_disposition": "DOMICILE",
        "icd_secondary_code": "",
        "specialty": "OBSTETRIQUE",
        "age2": 33,
    },
    # 5. Diabète type 2 décompensé (homme 70+)
    {
        "drg_parent_code": "10M11",
        "drg_parent_description": "Affections endocriniennes",
        "icd_primary_code": "E110",
        "icd_primary_parent_code": "E11",
        "case_management_type": "E110",
        "cage": "[70-80[",
        "cage2": "[50-[",
        "sexe": 1,
        "los": 7,
        "los_mean": 6.8,
        "los_sd": 2.1,
        "nb": 60,
        "admission_mode": "URGENCES",
        "admission_type": "Inpatient",
        "discharge_disposition": "DOMICILE",
        "icd_secondary_code": "I10 N183",
        "specialty": "ENDOCRINOLOGIE",
        "age2": 75,
    },
    # 6. Insuffisance cardiaque chronique décompensée
    {
        "drg_parent_code": "05M09",
        "drg_parent_description": "Insuffisances cardiaques",
        "icd_primary_code": "I500",
        "icd_primary_parent_code": "I50",
        "case_management_type": "I500",
        "cage": "[80-[",
        "cage2": "[50-[",
        "sexe": 2,
        "los": 8,
        "los_mean": 7.5,
        "los_sd": 2.5,
        "nb": 70,
        "admission_mode": "URGENCES",
        "admission_type": "Inpatient",
        "discharge_disposition": "DOMICILE",
        "icd_secondary_code": "I10 E785 N183",
        "specialty": "CARDIOLOGIE",
        "age2": 82,
    },
    # 7. Pneumopathie aiguë (urgences)
    {
        "drg_parent_code": "04M05",
        "drg_parent_description": "Infections respiratoires",
        "icd_primary_code": "J159",
        "icd_primary_parent_code": "J15",
        "case_management_type": "J159",
        "cage": "[60-70[",
        "cage2": "[50-[",
        "sexe": 1,
        "los": 5,
        "los_mean": 5.2,
        "los_sd": 1.8,
        "nb": 90,
        "admission_mode": "URGENCES",
        "admission_type": "Inpatient",
        "discharge_disposition": "DOMICILE",
        "icd_secondary_code": "",
        "specialty": "PNEUMOLOGIE",
        "age2": 67,
    },
    # 8. Transfusion répétitive (anémie)
    {
        "drg_parent_code": "28Z14",
        "drg_parent_description": "Transfusion",
        "icd_primary_code": "Z513",
        "icd_primary_parent_code": "Z51",
        "case_management_type": "D649",
        "cage": "[80-[",
        "cage2": "[50-[",
        "sexe": 2,
        "los": 0,
        "los_mean": 0.0,
        "los_sd": 0.0,
        "nb": 40,
        "admission_mode": "DOMICILE",
        "admission_type": "Outpatient",
        "discharge_disposition": "DOMICILE",
        "icd_secondary_code": "",
        "specialty": "MEDECINE INTERNE",
        "age2": 85,
    },
    # 9. Appendicectomie (chirurgie programmée jeune adulte)
    {
        "drg_parent_code": "06C12",
        "drg_parent_description": "Appendicectomies",
        "icd_primary_code": "K359",
        "icd_primary_parent_code": "K35",
        "case_management_type": "K359",
        "cage": "[18-30[",
        "cage2": "[18-50[",
        "sexe": 1,
        "los": 3,
        "los_mean": 2.8,
        "los_sd": 0.9,
        "nb": 110,
        "admission_mode": "URGENCES",
        "admission_type": "Inpatient",
        "discharge_disposition": "DOMICILE",
        "icd_secondary_code": "",
        "specialty": "CHIRURGIE GENERALE",
        "age2": 24,
    },
    # 10. Cataracte ambulatoire (personne âgée)
    {
        "drg_parent_code": "02C05",
        "drg_parent_description": "Interventions cristallin",
        "icd_primary_code": "H251",
        "icd_primary_parent_code": "H25",
        "case_management_type": "H251",
        "cage": "[70-80[",
        "cage2": "[50-[",
        "sexe": 2,
        "los": 0,
        "los_mean": 0.0,
        "los_sd": 0.0,
        "nb": 150,
        "admission_mode": "DOMICILE",
        "admission_type": "Outpatient",
        "discharge_disposition": "DOMICILE",
        "icd_secondary_code": "",
        "specialty": "OPHTALMOLOGIE",
        "age2": 73,
    },
]


def main() -> None:
    df = pd.DataFrame(PROFILES)
    out = Path("tests/fixtures/profiles.parquet")
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, index=False)
    print(f"Wrote {len(df)} synthetic profiles → {out}")


if __name__ == "__main__":
    main()
