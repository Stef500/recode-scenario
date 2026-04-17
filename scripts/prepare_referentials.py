"""Convert raw referentials (Excel/CSV/TXT) to normalized Parquet files.

Reads from ``referentials/raw/``, writes to ``referentials/processed/``.
Each output is validated against its Pandera schema.

Run this once per source update (not part of the normal user workflow).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
from loguru import logger

sys.path.insert(0, "src")
from recode.referentials.schemas import (
    CancerTreatmentSchema,
    ChronicSchema,
    Cim10HierarchySchema,
    Cim10NotesSchema,
    DrgGroupsSchema,
    DrgStatisticsSchema,
    HospitalsSchema,
    IcdOfficialSchema,
    IcdSynonymsSchema,
    NamesSchema,
    ProcedureOfficialSchema,
    SpecialtySchema,
)

RAW = Path("referentials/raw")
OUT = Path("referentials/processed")


def _ensure_out() -> None:
    OUT.mkdir(parents=True, exist_ok=True)


def prepare_icd_official() -> None:
    src = RAW / "CIM_ATIH_2025/LIBCIM10MULTI.TXT"
    if not src.exists():
        logger.warning("Skip icd_official: {} not found", src)
        return
    df = pd.read_csv(
        src,
        sep="|",
        header=None,
        encoding="latin-1",
        names=[
            "icd_code",
            "aut_mco",
            "pos",
            "aut_ssr",
            "icd_code_description_short",
            "icd_code_description",
        ],
    )
    df["icd_code"] = df["icd_code"].astype(str).str.replace(" ", "")
    df = df[["icd_code", "icd_code_description", "aut_mco"]]
    df = IcdOfficialSchema.validate(df)
    df.to_parquet(OUT / "icd_official.parquet", index=False)
    logger.success("icd_official.parquet: {} rows", len(df))


def prepare_drg_statistics() -> None:
    src = RAW / "stat_racines.xlsx"
    if not src.exists():
        logger.warning("Skip drg_statistics: {} not found", src)
        return
    df = pd.read_excel(src)
    df = df.rename(columns={"racine": "drg_parent_code", "dms": "los_mean", "dsd": "los_sd"})
    df = df[["drg_parent_code", "los_mean", "los_sd"]]
    df = DrgStatisticsSchema.validate(df)
    df.to_parquet(OUT / "drg_statistics.parquet", index=False)
    logger.success("drg_statistics.parquet: {} rows", len(df))


def prepare_drg_groups() -> None:
    src = RAW / "ghm_rghm_regroupement_2024.xlsx"
    if not src.exists():
        logger.warning("Skip drg_groups: {} not found", src)
        return
    df = pd.read_excel(src)
    df = df.rename(
        columns={"racine": "drg_parent_code", "libelle_racine": "drg_parent_description"}
    )
    df = df[["drg_parent_code", "drg_parent_description"]]
    df = DrgGroupsSchema.validate(df)
    df.to_parquet(OUT / "drg_groups.parquet", index=False)
    logger.success("drg_groups.parquet: {} rows", len(df))


def prepare_cancer_treatments() -> None:
    src = RAW / "Tableau récapitulatif traitement cancer.xlsx"
    if not src.exists():
        logger.warning("Skip cancer_treatments: {} not found", src)
        return
    df = pd.read_excel(src)
    df = df.rename(
        columns={
            "Code CIM": "icd_parent_code",
            "Localisation": "primary_site",
            "Type Histologique": "histological_type",
            "Stade": "stage",
            "Marqueurs Tumoraux": "biomarkers",
            "Traitement": "treatment_recommendation",
            "Protocole de Chimiothérapie": "chemotherapy_regimen",
        }
    )
    cols = [
        c
        for c in [
            "icd_parent_code",
            "primary_site",
            "histological_type",
            "stage",
            "biomarkers",
            "treatment_recommendation",
            "chemotherapy_regimen",
        ]
        if c in df.columns
    ]
    df = df[cols]
    df = CancerTreatmentSchema.validate(df)
    df.to_parquet(OUT / "cancer_treatments.parquet", index=False)
    logger.success("cancer_treatments.parquet: {} rows", len(df))


def prepare_names() -> None:
    src = RAW / "prenoms_nom_sexe.csv"
    if not src.exists():
        logger.warning("Skip names: {} not found", src)
        return
    df = pd.read_csv(src, sep=";").dropna()
    df = df[["prenom", "nom", "sexe"]]
    df["sexe"] = df["sexe"].astype(int)
    df = NamesSchema.validate(df)
    df.to_parquet(OUT / "names.parquet", index=False)
    logger.success("names.parquet: {} rows", len(df))


def prepare_hospitals() -> None:
    src = RAW / "chu"
    if not src.exists():
        logger.warning("Skip hospitals: {} not found", src)
        return
    df = pd.read_csv(src, names=["hospital"])
    df = HospitalsSchema.validate(df)
    df.to_parquet(OUT / "hospitals.parquet", index=False)
    logger.success("hospitals.parquet: {} rows", len(df))


def prepare_specialty() -> None:
    src = RAW / "dictionnaire_spe_racine.xlsx"
    if not src.exists():
        logger.warning("Skip specialty: {} not found", src)
        return
    df = pd.read_excel(src)
    df = df.rename(
        columns={
            "racine": "drg_parent_code",
            "lib_spe_uma": "specialty",
            "ratio_spe_racine": "ratio",
        }
    )
    if "age" not in df.columns:
        df["age"] = None
    df = df[["drg_parent_code", "specialty", "ratio", "age"]]
    df = SpecialtySchema.validate(df)
    df.to_parquet(OUT / "specialty.parquet", index=False)
    logger.success("specialty.parquet: {} rows", len(df))


def prepare_chronic() -> None:
    src = RAW / "Affections chroniques.xlsx"
    if not src.exists():
        logger.warning("Skip chronic: {} not found", src)
        return
    df = pd.read_excel(src, header=None, names=["code", "chronic", "libelle"])
    df = ChronicSchema.validate(df)
    df.to_parquet(OUT / "chronic.parquet", index=False)
    logger.success("chronic.parquet: {} rows", len(df))


def prepare_complications() -> None:
    src = RAW / "cma.csv"
    if not src.exists():
        logger.warning("Skip complications: {} not found", src)
        return
    df = pd.read_csv(src).dropna()
    df.to_parquet(OUT / "complications.parquet", index=False)
    logger.success("complications.parquet: {} rows", len(df))


def prepare_icd_synonyms() -> None:
    src = RAW / "cim_synonymes.csv"
    if not src.exists():
        logger.warning("Skip icd_synonyms: {} not found", src)
        return
    df = pd.read_csv(src).dropna()
    df = df.rename(columns={"dictionary_keys": "icd_code_description", "code": "icd_code"})
    df = df[["icd_code", "icd_code_description"]]
    df = IcdSynonymsSchema.validate(df)
    df.to_parquet(OUT / "icd_synonyms.parquet", index=False)
    logger.success("icd_synonyms.parquet: {} rows", len(df))


def prepare_procedure_official() -> None:
    src = RAW / "ccam_actes_2024.xlsx"
    if not src.exists():
        logger.warning("Skip procedure_official: {} not found", src)
        return
    df = pd.read_excel(src)
    df = df.rename(columns={"code": "procedure", "libelle_long": "procedure_description"})
    df = df[["procedure", "procedure_description"]]
    df = ProcedureOfficialSchema.validate(df)
    df.to_parquet(OUT / "procedure_official.parquet", index=False)
    logger.success("procedure_official.parquet: {} rows", len(df))


def prepare_cim10_hierarchy() -> None:
    src = RAW / "CIM_ATIH_2025/cim10_hierarchy.csv"
    if not src.exists():
        logger.warning("Skip cim10_hierarchy: {} not found", src)
        return
    df = pd.read_csv(src, dtype=str, keep_default_na=False)
    df = Cim10HierarchySchema.validate(df)
    df.to_parquet(OUT / "cim10_hierarchy.parquet", index=False)
    logger.success("cim10_hierarchy.parquet: {} rows", len(df))


def prepare_cim10_notes() -> None:
    src = RAW / "CIM_ATIH_2025/cim10_notes.csv"
    if not src.exists():
        logger.warning("Skip cim10_notes: {} not found", src)
        return
    df = pd.read_csv(src, dtype=str, keep_default_na=False)
    df = Cim10NotesSchema.validate(df)
    df.to_parquet(OUT / "cim10_notes.parquet", index=False)
    logger.success("cim10_notes.parquet: {} rows", len(df))


def main() -> None:
    _ensure_out()
    logger.info("Preparing referentials: {} -> {}", RAW, OUT)
    prepare_icd_official()
    prepare_drg_statistics()
    prepare_drg_groups()
    prepare_cancer_treatments()
    prepare_names()
    prepare_hospitals()
    prepare_specialty()
    prepare_chronic()
    prepare_complications()
    prepare_icd_synonyms()
    prepare_procedure_official()
    prepare_cim10_hierarchy()
    prepare_cim10_notes()
    logger.success("All referentials prepared.")


if __name__ == "__main__":
    main()
