"""Demographics + stay-date sampling (age, year, dates, identity)."""

from __future__ import annotations

import datetime
import re
from typing import Final

import numpy as np

from recode.models import Gender, Patient, Profile, Stay
from recode.referentials import ReferentialRegistry

_AGE_CLASS_RE: Final = re.compile(r"\[(\d+)-(\d+)\[")
_AGE_CLASS_OPEN_RE: Final = re.compile(r"\[(\d+)-\[")
_YEARS_OFFSET: Final = (2, 1, 0)
_DEFAULT_MAX_AGE: Final = 90


def _parse_age_class(age_class: str) -> tuple[int, int]:
    """Parse an age-class literal like ``"[18-30["`` into (min, max) bounds."""
    m = _AGE_CLASS_RE.match(age_class.strip())
    if m:
        return int(m.group(1)), int(m.group(2))
    m = _AGE_CLASS_OPEN_RE.match(age_class.strip())
    if m:
        return int(m.group(1)), _DEFAULT_MAX_AGE
    msg = f"Invalid age_class format: {age_class!r}"
    raise ValueError(msg)


def sample_age(age_class: str, rng: np.random.Generator) -> int:
    """Sample an integer age uniformly within the class bounds."""
    lo, hi = _parse_age_class(age_class)
    return int(rng.integers(lo, hi + 1))


def pick_year(rng: np.random.Generator) -> int:
    """Pick one of {today-2, today-1, today} uniformly."""
    today = datetime.date.today().year
    return today - int(rng.choice(_YEARS_OFFSET))


def _days_in_month(year: int, month: int) -> int:
    if month == 2:
        leap = year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
        return 29 if leap else 28
    if month in (4, 6, 9, 11):
        return 30
    return 31


def random_date_in_year(
    year: int, rng: np.random.Generator, *, exclude_weekends: bool = False
) -> datetime.date:
    """Random date in ``year``. If ``exclude_weekends``, resample until weekday."""
    while True:
        month = int(rng.integers(1, 13))
        day = int(rng.integers(1, _days_in_month(year, month) + 1))
        d = datetime.date(year, month, day)
        if not exclude_weekends or d.weekday() < 5:
            return d


def random_date_between(
    start: datetime.date, end: datetime.date, rng: np.random.Generator
) -> datetime.date:
    """Random date in ``[start, end]``."""
    delta = (end - start).days
    return start + datetime.timedelta(days=int(rng.integers(0, delta + 1)))


def _sample_los(profile: Profile, rng: np.random.Generator) -> int:
    """Sample length of stay from truncated normal, floored at 0."""
    mols = profile.los_mean if profile.los_mean is not None else 1.0
    sdlos = profile.los_sd if profile.los_sd is not None else 1.0
    return int(abs(rng.normal(mols, sdlos)))


def compute_stay_dates(
    profile: Profile, year: int, rng: np.random.Generator
) -> tuple[datetime.date, datetime.date]:
    """Return ``(date_entry, date_discharge)`` matching admission semantics.

    - Outpatient → same-day (entry == discharge).
    - Inpatient + URGENCES → any day of year.
    - Inpatient + programmé → weekday only.
    """
    if profile.admission_type == "Outpatient":
        d = random_date_in_year(year, rng, exclude_weekends=False)
        return d, d
    los = (
        profile.length_of_stay if profile.length_of_stay is not None else _sample_los(profile, rng)
    )
    exclude_we = profile.admission_mode != "URGENCES"
    entry = random_date_in_year(year, rng, exclude_weekends=exclude_we)
    return entry, entry + datetime.timedelta(days=los)


def sample_patient_identity(
    gender: Gender, registry: ReferentialRegistry, rng: np.random.Generator
) -> tuple[str, str]:
    """Sample a ``(first_name, last_name)`` pair title-cased."""
    names = registry.names
    first_candidates = names[(names["sexe"] == gender) & (names["prenom"].str.len() > 3)]
    last_candidates = names[names["nom"].str.len() > 3]
    first_state = int(rng.integers(0, 2**31))
    last_state = int(rng.integers(0, 2**31))
    first = str(first_candidates["prenom"].sample(n=1, random_state=first_state).iloc[0])
    last = str(last_candidates["nom"].sample(n=1, random_state=last_state).iloc[0])
    return first.title(), last.title()


def sample_hospital(registry: ReferentialRegistry, rng: np.random.Generator) -> str:
    """Sample one hospital name uniformly."""
    state = int(rng.integers(0, 2**31))
    return str(registry.hospitals["hospital"].sample(n=1, random_state=state).iloc[0])


def build_patient(
    profile: Profile,
    date_entry: datetime.date,
    registry: ReferentialRegistry,
    rng: np.random.Generator,
) -> Patient:
    """Build the Patient sub-model."""
    age = profile.age_exact if profile.age_exact is not None else sample_age(profile.age_class, rng)
    dob = random_date_between(
        date_entry - datetime.timedelta(days=365 * (age + 1)),
        date_entry - datetime.timedelta(days=365 * age),
        rng,
    )
    first, last = sample_patient_identity(profile.gender, registry, rng)
    return Patient(
        age=age, gender=profile.gender, first_name=first, last_name=last, date_of_birth=dob
    )


def build_stay(
    profile: Profile,
    date_entry: datetime.date,
    date_discharge: datetime.date,
    registry: ReferentialRegistry,
    rng: np.random.Generator,
) -> Stay:
    """Build the Stay sub-model (requires already-computed dates)."""
    med_gender: Gender = 1 if int(rng.integers(0, 2)) == 0 else 2
    first_med, last_med = sample_patient_identity(med_gender, registry, rng)
    hospital = sample_hospital(registry, rng)
    return Stay(
        date_entry=date_entry,
        date_discharge=date_discharge,
        admission_mode=profile.admission_mode,
        admission_type=profile.admission_type,
        discharge_disposition=profile.discharge_disposition,
        hospital=hospital,
        department=profile.specialty,
        physician_first_name=first_med,
        physician_last_name=last_med,
    )
