"""
Step 5 (bonus): a tiny FastAPI endpoint that serves the clean table.

It reads patients_with_vitals.csv (created by 04_transform_to_table.py) and
exposes it as JSON. FastAPI also builds interactive documentation for free at /docs.

Run with:   python -m uvicorn api:app --reload
Then open:  http://127.0.0.1:8000/docs
"""
from pathlib import Path
from typing import Optional

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

CSV_PATH = Path(__file__).parent / "patients_with_vitals.csv"

app = FastAPI(
    title="Synthetic FHIR Patient Vitals API",
    description="Serves a flattened table built from synthetic FHIR Patient and "
                "Observation resources. All data is synthetic.",
    version="1.0.0",
)


class PatientVitals(BaseModel):
    patient_id: str
    mrn: Optional[str] = None
    given_name: str
    family_name: str
    gender: str
    birth_date: str
    age_years: int
    heart_rate_bpm: Optional[float] = None
    temperature_c: Optional[float] = None


# ---- data helpers (plain Python, no web code) -------------------------------

def load_df() -> pd.DataFrame:
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"{CSV_PATH.name} not found. Run 04_transform_to_table.py first.")
    return pd.read_csv(CSV_PATH, dtype={"patient_id": str})


def to_records(df: pd.DataFrame) -> list:
    """Convert a DataFrame to JSON-friendly dicts, turning NaN into None."""
    return df.astype(object).where(df.notna(), None).to_dict(orient="records")


def apply_filters(df, gender=None, min_age=None, max_age=None, min_temp=None):
    if gender:
        df = df[df["gender"].str.lower() == gender.lower()]
    if min_age is not None:
        df = df[df["age_years"] >= min_age]
    if max_age is not None:
        df = df[df["age_years"] <= max_age]
    if min_temp is not None:
        df = df[df["temperature_c"] >= min_temp]
    return df


def build_summary(df: pd.DataFrame) -> dict:
    def avg(col):
        value = df[col].mean()
        return None if pd.isna(value) else round(float(value), 1)

    return {
        "patients": int(len(df)),
        "by_gender": {k: int(v) for k, v in df["gender"].value_counts().items()},
        "mean_age_years": avg("age_years"),
        "mean_heart_rate_bpm": avg("heart_rate_bpm"),
        "mean_temperature_c": avg("temperature_c"),
    }


# ---- routes -----------------------------------------------------------------

@app.get("/")
def root():
    return {
        "message": "Synthetic FHIR Patient Vitals API",
        "docs": "/docs",
        "endpoints": ["/patients", "/patients/{patient_id}", "/summary"],
    }


@app.get("/patients", response_model=list[PatientVitals])
def list_patients(
    gender: Optional[str] = Query(None, description="male, female, other or unknown"),
    min_age: Optional[int] = Query(None, ge=0),
    max_age: Optional[int] = Query(None, ge=0),
    min_temp: Optional[float] = Query(None, description="Minimum body temperature in degrees Celsius"),
):
    df = apply_filters(load_df(), gender, min_age, max_age, min_temp)
    return to_records(df)


@app.get("/patients/{patient_id}", response_model=PatientVitals)
def get_patient(patient_id: str):
    df = load_df()
    match = df[df["patient_id"] == patient_id]
    if match.empty:
        raise HTTPException(status_code=404, detail=f"Patient {patient_id} not found")
    return to_records(match)[0]


@app.get("/summary")
def summary():
    return build_summary(load_df())
