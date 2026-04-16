"""Tests for ReferentialRegistry."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

FIXTURES = Path("tests/fixtures/referentials")


def test_registry_loads_icd_official() -> None:
    from recode.referentials.registry import ReferentialRegistry

    reg = ReferentialRegistry(processed_dir=FIXTURES, constants_dir=FIXTURES / "constants")
    df = reg.icd_official
    assert isinstance(df, pd.DataFrame)
    assert "icd_code" in df.columns
    assert len(df) > 0


def test_registry_caches_properties() -> None:
    from recode.referentials.registry import ReferentialRegistry

    reg = ReferentialRegistry(processed_dir=FIXTURES, constants_dir=FIXTURES / "constants")
    df1 = reg.icd_official
    df2 = reg.icd_official
    assert df1 is df2


def test_registry_cancer_codes() -> None:
    from recode.referentials.constants import CancerCodes
    from recode.referentials.registry import ReferentialRegistry

    reg = ReferentialRegistry(processed_dir=FIXTURES, constants_dir=FIXTURES / "constants")
    codes = reg.cancer_codes
    assert isinstance(codes, CancerCodes)
    assert "C770" in codes.metastasis_lymph_nodes


def test_registry_missing_file_raises() -> None:
    from recode.referentials.registry import ReferentialRegistry

    reg = ReferentialRegistry(
        processed_dir=Path("/nonexistent"), constants_dir=Path("/nonexistent")
    )
    with pytest.raises(FileNotFoundError):
        _ = reg.icd_official
