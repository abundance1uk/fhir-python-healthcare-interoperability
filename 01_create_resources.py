"""
Step 1: Create synthetic Patient and Observation resources on the HAPI FHIR
public test server, then save the server-assigned IDs.

IMPORTANT: the HAPI public server is open to everyone. Only ever send
FAKE, synthetic data. Never use real patient information.
"""
import json
from datetime import datetime, timezone

import requests

BASE = "https://hapi.fhir.org/baseR4"
HEADERS = {
    "Content-Type": "application/fhir+json",
    "Accept": "application/fhir+json",
}

# A project-specific identifier system lets us find only OUR records later,
# because the public server holds data from many other people.
PROJECT_SYSTEM = "https://example.org/fhir-portfolio-project"

SYNTHETIC_PATIENTS = [
    {"mrn": "demo-001", "given": "Ada", "family": "Demo", "gender": "female", "birth": "1990-04-12",
     "heart_rate": 72, "temp_c": 36.8},
    {"mrn": "demo-002", "given": "Tunde", "family": "Demo", "gender": "male", "birth": "1984-09-30",
     "heart_rate": 88, "temp_c": 37.9},
    {"mrn": "demo-003", "given": "Ngozi", "family": "Demo", "gender": "female", "birth": "2001-01-25",
     "heart_rate": 64, "temp_c": 36.5},
]


def build_patient(p):
    return {
        "resourceType": "Patient",
        "identifier": [{"system": PROJECT_SYSTEM, "value": p["mrn"]}],
        "name": [{"use": "official", "family": p["family"], "given": [p["given"]]}],
        "gender": p["gender"],
        "birthDate": p["birth"],
    }


def build_observation(patient_id, loinc_code, display, value, unit, ucum_code):
    return {
        "resourceType": "Observation",
        "status": "final",
        "category": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                "code": "vital-signs",
                "display": "Vital Signs",
            }]
        }],
        "code": {
            "coding": [{"system": "http://loinc.org", "code": loinc_code, "display": display}],
            "text": display,
        },
        "subject": {"reference": f"Patient/{patient_id}"},
        "effectiveDateTime": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "valueQuantity": {
            "value": value,
            "unit": unit,
            "system": "http://unitsofmeasure.org",
            "code": ucum_code,
        },
    }


def post(resource_type, body):
    resp = requests.post(f"{BASE}/{resource_type}", headers=HEADERS, json=body, timeout=30)
    resp.raise_for_status()
    return resp.json()


def main():
    created = []
    for p in SYNTHETIC_PATIENTS:
        patient = post("Patient", build_patient(p))
        pid = patient["id"]
        print(f"Created Patient/{pid} ({p['given']} {p['family']})")

        hr = post("Observation", build_observation(pid, "8867-4", "Heart rate", p["heart_rate"], "beats/minute", "/min"))
        temp = post("Observation", build_observation(pid, "8310-5", "Body temperature", p["temp_c"], "degC", "Cel"))
        print(f"  Created Observation/{hr['id']} (heart rate) and Observation/{temp['id']} (temperature)")

        created.append({"mrn": p["mrn"], "patient_id": pid,
                        "observation_ids": [hr["id"], temp["id"]]})

    with open("created_ids.json", "w") as f:
        json.dump(created, f, indent=2)
    print("\nSaved IDs to created_ids.json")


if __name__ == "__main__":
    main()
