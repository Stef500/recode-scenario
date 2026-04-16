"""Génère tests/fixtures/golden_scenarios.csv depuis la baseline corrigée
de utils_v2.py, en utilisant tests/fixtures/profiles.parquet et
tests/fixtures/referentials/.

C'est la référence de régression pour le nouveau code Phase 3+.
Exécuter avec le même seed (42) produira toujours le même CSV.
"""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, ".")

FIXTURES = Path("tests/fixtures")
REF = FIXTURES / "referentials"
BASE_SEED = 42


def _patch_pandas_readers():
    """Neutralise les appels pd.read_csv/read_excel vers des fichiers absents
    pendant l'instantiation de generate_scenario. Restaure ensuite les
    fonctions originales.
    """
    original_read_csv = pd.read_csv
    original_read_excel = pd.read_excel

    def safe_read_csv(path, *args, **kwargs):
        try:
            return original_read_csv(path, *args, **kwargs)
        except (FileNotFoundError, OSError):
            return pd.DataFrame({"code": [], "icd_code": [], "CIM10": []})

    def safe_read_excel(path, *args, **kwargs):
        try:
            return original_read_excel(path, *args, **kwargs)
        except (FileNotFoundError, OSError):
            return pd.DataFrame(
                {
                    "code": [],
                    "icd_code": [],
                    "CIM10": [],
                    "racine": [],
                    "dms": [],
                    "dsd": [],
                    "libelle_racine": [],
                    "chronic": [],
                    "libelle": [],
                }
            )

    pd.read_csv = safe_read_csv
    pd.read_excel = safe_read_excel
    return original_read_csv, original_read_excel


def _restore_pandas_readers(original_read_csv, original_read_excel):
    pd.read_csv = original_read_csv
    pd.read_excel = original_read_excel


def setup_generator():
    """Instancie generate_scenario et hydrate les référentiels depuis parquet."""
    original_csv, original_excel = _patch_pandas_readers()
    try:
        from utils_v2 import generate_scenario

        gs = generate_scenario(path_ref=str(REF) + "/", path_data=str(REF) + "/")
    finally:
        _restore_pandas_readers(original_csv, original_excel)

    # Hydrate les DataFrames depuis les parquet fixtures (overwrite les stubs
    # vides créés par la constructor sous monkey-patch).
    gs.df_icd_official = pd.read_parquet(REF / "icd_official.parquet")
    gs.df_icd_valid = gs.df_icd_official.copy()
    gs.df_term_icd = gs.df_icd_official.assign(categ=gs.df_icd_official.icd_code.str.slice(0, 3))

    gs.drg_statistics = pd.read_parquet(REF / "drg_statistics.parquet")
    gs.drg_parents_groups = pd.read_parquet(REF / "drg_groups.parquet")
    gs.df_cancer_treatment_recommandation = pd.read_parquet(REF / "cancer_treatments.parquet")
    gs.df_names = pd.read_parquet(REF / "names.parquet")
    gs.df_hospitals = pd.read_parquet(REF / "hospitals.parquet")
    gs.ref_sep = pd.read_parquet(REF / "specialty.parquet")

    # Frames vides pour les référentiels non couverts par les fixtures.
    gs.df_secondary_icd = pd.DataFrame(
        columns=[
            "icd_secondary_code",
            "drg_parent_code",
            "icd_primary_code",
            "cage2",
            "sexe",
            "nb",
            "type",
            "icd_primary_parent_code",
        ]
    )
    gs.df_procedures = pd.DataFrame(
        columns=[
            "procedure",
            "drg_parent_code",
            "icd_primary_code",
            "cage2",
            "sexe",
            "nb",
        ]
    )
    gs.df_procedure_official = pd.DataFrame(columns=["procedure", "procedure_description"])
    gs.pathology_procedure = pd.Series([], dtype=str)
    gs.df_complications = pd.DataFrame(columns=["icd_code"])
    gs.df_chronic = pd.DataFrame(columns=["code", "chronic", "libelle"])
    gs.icd_codes_chronic = []
    gs.df_icd_synonyms = pd.DataFrame(columns=["icd_code", "icd_code_description"])
    gs.icd_codes_cancer = ["C509", "C50", "C349", "C34"]
    gs.df_classification_profile = pd.DataFrame()

    # Année de simulation figée pour la reproductibilité inter-dates.
    gs.simulations_years = [2023, 2024, 2025]

    return gs


_PREFIX_NON_CANCER = (
    "Le compte rendu suivant respecte les élements suivants :\n"
    "        - les diagnostics ont une formulation moins formelle que la définition du code\n"
    "        - le plan du CRH est conforme aux recommandations.\n        "
)
_PREFIX_CANCER = (
    "Le compte rendu suivant respecte les élements suivants :\n"
    "        - les diagnostics ont une formulation moins formelle que la définition du code\n"
    "        - le type histologique et la valeur des biomarqueurs si recherchés\n"
    "        - le plan du CRH est conforme aux recommandations.\n        "
)


def main():
    from utils_v2 import derive_scenario_rng

    gs = setup_generator()
    profiles = pd.read_parquet(FIXTURES / "profiles.parquet")

    rows = []
    for _, raw in profiles.iterrows():
        profile = raw.copy()
        rng = derive_scenario_rng(profile, base_seed=BASE_SEED)
        scenario = gs.generate_scenario_from_profile(profile, rng=rng)
        # Build prompts + prefix via the baseline methods
        user_prompt = gs.make_prompts_marks_from_scenario(scenario)
        try:
            system_prompt = gs.create_system_prompt(scenario)
        except (FileNotFoundError, OSError):
            system_prompt = ""
        prefix = (
            _PREFIX_CANCER
            if scenario["icd_primary_code"] in gs.icd_codes_cancer
            else _PREFIX_NON_CANCER
        )
        row = dict(scenario)
        row["user_prompt"] = user_prompt
        row["system_prompt"] = system_prompt
        row["prefix"] = prefix
        row["prefix_len"] = len(prefix)
        rows.append(row)

    df = pd.DataFrame(rows)
    out = FIXTURES / "golden_scenarios.csv"
    df.to_csv(out, index=False)
    print(f"Wrote {len(df)} golden scenarios -> {out}")
    print(f"Columns ({len(df.columns)}): {list(df.columns)}")


if __name__ == "__main__":
    main()
