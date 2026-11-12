"""
Step 4: Transform the nested FHIR JSON into clean, flat tables.

FHIR resources are nested (a name is a list inside a list...). Analysts need rows
and columns, so this script "flattens" the data with pandas and produces:
  - patients.csv               one row per patient
  - observations_long.csv      one row per measurement (long format)
  - patients_with_vitals.csv   one row per patient, vitals as columns (the clean table)
"""
import json
from datetime import date

import pandas as pd

PROJECT_SYSTEM = "https://example.org/fhir-portfolio-project"

# LOINC code -> clean column name
VITAL_COLUMNS = {
    "8867-4": "heart_rate_bpm",
    "8310-5": "temperature_c",
}


def age_from(birth_date):
    b = date.fromisoformat(birth_date)
    t = date.today()
    return t.year - b.year - ((t.month, t.day) < (b.month, b.day))


def flatten_patient(p):
    name = p["name"][0]
    mrn = next((i["value"] for i in p.get("identifier", []) if i.get("system") == PROJECT_SYSTEM), None)
    return {
        "patient_id": p["id"],
        "mrn": mrn,
        "given_name": " ".join(name.get("given", [])),
        "family_name": name.get("family"),
        "gender": p.get("gender"),
        "birth_date": p.get("birthDate"),
        "age_years": age_from(p["birthDate"]),
    }


def flatten_observation(o):
    coding = o["code"]["coding"][0]
    q = o["valueQuantity"]
    return {
        "observation_id": o["id"],
        "patient_id": o["subject"]["reference"].split("/")[1],
        "loinc_code": coding["code"],
        "measurement": coding.get("display") or o["code"].get("text"),
        "value": q["value"],
        "unit": q["unit"],
        "recorded_at": o.get("effectiveDateTime"),
        "status": o["status"],
    }


def main():
    with open("retrieved_resources.json") as f:
        data = json.load(f)

    patients = pd.DataFrame([flatten_patient(p) for p in data["patients"]])
    obs = pd.DataFrame([flatten_observation(o) for o in data["observations"]])

    # Wide format: one row per patient, one column per vital sign
    obs["column"] = obs["loinc_code"].map(VITAL_COLUMNS).fillna(obs["measurement"])
    vitals = obs.pivot_table(index="patient_id", columns="column", values="value", aggfunc="first").reset_index()
    vitals.columns.name = None

    clean = patients.merge(vitals, on="patient_id", how="left").sort_values("mrn").reset_index(drop=True)

    patients.to_csv("patients.csv", index=False)
    obs.drop(columns="column").to_csv("observations_long.csv", index=False)
    clean.to_csv("patients_with_vitals.csv", index=False)

    print("CLEAN TABLE (patients_with_vitals.csv):\n")
    print(clean.to_string(index=False))
    print(f"\nRows: {len(clean)} patients, {len(obs)} observations")
    print("Saved: patients.csv, observations_long.csv, patients_with_vitals.csv")


if __name__ == "__main__":
    main()
