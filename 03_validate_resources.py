"""
Step 3: Validate the retrieved FHIR resources.

Two layers of checking:
  A. SCHEMA check  - is the JSON a structurally valid FHIR resource?
                     (uses the fhir.resources library if it is installed; skipped if not)
  B. RULE check    - does the data make sense? (our own data-quality rules)

At the end, the same rules are run on three deliberately BROKEN records to prove
the validator actually catches problems.
"""
import csv
import json
import re
from datetime import date

VALID_GENDERS = {"male", "female", "other", "unknown"}
VALID_OBS_STATUS = {"registered", "preliminary", "final", "amended", "corrected",
                    "cancelled", "entered-in-error", "unknown"}

# LOINC code -> (expected UCUM unit code, plausible min, plausible max, label)
EXPECTED = {
    "8867-4": ("/min", 20, 250, "Heart rate"),
    "8310-5": ("Cel", 30, 45, "Body temperature"),
}


def schema_check(resource):
    """Return a list of schema problems, or None if the library is not installed."""
    try:
        from fhir.resources import construct_fhir_element
    except ImportError:
        return None
    try:
        construct_fhir_element(resource["resourceType"], resource)
        return []
    except Exception as exc:  # the library raises detailed validation errors
        return [f"schema: {str(exc).splitlines()[0]}"]


def check_patient(p):
    issues = []
    if not p.get("id"):
        issues.append("missing id")
    names = p.get("name") or []
    if not names or not names[0].get("family"):
        issues.append("missing family name")
    if p.get("gender") not in VALID_GENDERS:
        issues.append(f"invalid gender '{p.get('gender')}'")
    bd = p.get("birthDate")
    if not bd or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", bd):
        issues.append("birthDate missing or not YYYY-MM-DD")
    else:
        try:
            if date.fromisoformat(bd) > date.today():
                issues.append("birthDate is in the future")
        except ValueError:
            issues.append("birthDate is not a real date")
    return issues


def check_observation(o, patient_ids):
    issues = []
    if o.get("status") not in VALID_OBS_STATUS:
        issues.append(f"invalid status '{o.get('status')}'")

    ref = (o.get("subject") or {}).get("reference", "")
    if not ref.startswith("Patient/"):
        issues.append("subject does not reference a Patient")
    elif ref.split("/")[1] not in patient_ids:
        issues.append(f"subject {ref} not found among retrieved patients")

    codings = (o.get("code") or {}).get("coding") or []
    loinc = next((c.get("code") for c in codings if c.get("system") == "http://loinc.org"), None)
    q = o.get("valueQuantity")
    if not loinc:
        issues.append("no LOINC code")
    if not q or not isinstance(q.get("value"), (int, float)):
        issues.append("valueQuantity missing or not numeric")
    elif loinc in EXPECTED:
        unit, lo, hi, label = EXPECTED[loinc]
        if q.get("code") != unit:
            issues.append(f"{label}: unit code '{q.get('code')}' should be '{unit}'")
        if not (lo <= q["value"] <= hi):
            issues.append(f"{label}: value {q['value']} outside plausible range {lo}-{hi}")
    return issues


def validate(resource, patient_ids):
    schema = schema_check(resource)
    rules = (check_patient(resource) if resource["resourceType"] == "Patient"
             else check_observation(resource, patient_ids))
    return schema, rules


def main():
    with open("retrieved_resources.json") as f:
        data = json.load(f)
    patient_ids = {p["id"] for p in data["patients"]}

    rows = []
    for res in data["patients"] + data["observations"]:
        schema, rules = validate(res, patient_ids)
        problems = (schema or []) + rules
        rows.append({
            "resourceType": res["resourceType"],
            "id": res["id"],
            "schema_checked": "yes" if schema is not None else "no (library not installed)",
            "status": "PASS" if not problems else "FAIL",
            "issues": "; ".join(problems),
        })

    passed = sum(r["status"] == "PASS" for r in rows)
    print(f"Validated {len(rows)} resources: {passed} passed, {len(rows) - passed} failed")
    if rows and rows[0]["schema_checked"] != "yes":
        print("Note: fhir.resources is not installed, so only our data-quality rules ran.")
    for r in rows:
        print(f"  {r['status']}  {r['resourceType']}/{r['id']}  {r['issues']}")

    with open("validation_report.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print("\nSaved validation_report.csv")

    # ---- Self-test: prove the validator catches bad data ----
    print("\nSELF-TEST with deliberately broken records (every one should FAIL):")
    broken = [
        {"resourceType": "Patient", "id": "bad1", "gender": "femle", "birthDate": "2090-01-01"},
        {"resourceType": "Observation", "id": "bad2", "status": "final",
         "subject": {"reference": f"Patient/{next(iter(patient_ids))}"},
         "code": {"coding": [{"system": "http://loinc.org", "code": "8310-5"}]},
         "valueQuantity": {"value": 98.6, "unit": "degC", "code": "Cel"}},
        {"resourceType": "Observation", "id": "bad3", "status": "done",
         "code": {"coding": [{"system": "http://loinc.org", "code": "8867-4"}]},
         "valueQuantity": {"value": 72, "unit": "beats/minute", "code": "/min"}},
    ]
    for b in broken:
        _, rules = validate(b, patient_ids)
        print(f"  {'FAIL' if rules else 'PASS (unexpected!)'}  {b['resourceType']}/{b['id']}  {'; '.join(rules)}")


if __name__ == "__main__":
    main()
