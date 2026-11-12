"""
Step 2: Retrieve the synthetic resources created in Step 1.

Two ways of retrieving data from a FHIR server are shown:
  1. READ   - fetch one resource when you know its ID:   GET /Patient/{id}
  2. SEARCH - ask for all resources matching a rule:     GET /Patient?identifier=...
A search returns a "Bundle": a wrapper that holds a list of resources in "entry".
"""
import json

import requests

BASE = "https://hapi.fhir.org/baseR4"
HEADERS = {"Accept": "application/fhir+json"}
PROJECT_SYSTEM = "https://example.org/fhir-portfolio-project"


def get(path, params=None):
    resp = requests.get(f"{BASE}/{path}", headers=HEADERS, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def bundle_resources(bundle):
    """Pull the resources out of a search Bundle (empty list if no matches)."""
    return [e["resource"] for e in bundle.get("entry", [])]


def main():
    with open("created_ids.json") as f:
        created = json.load(f)

    # 1. READ one Patient by ID
    first_id = created[0]["patient_id"]
    patient = get(f"Patient/{first_id}")
    print(f"READ Patient/{first_id}: {patient['name'][0]['given'][0]} "
          f"{patient['name'][0]['family']}, born {patient['birthDate']}\n")

    # 2. SEARCH for all of OUR patients using our project identifier
    #    (the public server holds other people's data too)
    patients = []
    for item in created:
        bundle = get("Patient", {"identifier": f"{PROJECT_SYSTEM}|{item['mrn']}"})
        patients.extend(bundle_resources(bundle))
    print(f"SEARCH found {len(patients)} of our Patient records")

    # 3. SEARCH for the Observations that belong to each Patient
    observations = []
    for p in patients:
        bundle = get("Observation", {"subject": f"Patient/{p['id']}", "_count": 50})
        observations.extend(bundle_resources(bundle))
    print(f"SEARCH found {len(observations)} Observation records\n")

    for o in observations:
        q = o["valueQuantity"]
        print(f"  {o['subject']['reference']}: {o['code']['text']} = {q['value']} {q['unit']}")

    with open("retrieved_resources.json", "w") as f:
        json.dump({"patients": patients, "observations": observations}, f, indent=2)
    print("\nSaved raw FHIR JSON to retrieved_resources.json")


if __name__ == "__main__":
    main()
