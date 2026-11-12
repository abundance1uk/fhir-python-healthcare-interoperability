# FHIR resources explained: Patient and Observation

All records in this project are **synthetic**. They were created for learning and stored on the public HAPI FHIR test server (FHIR R4), which is open to everyone and is wiped periodically.

## What FHIR is

FHIR (Fast Healthcare Interoperability Resources) is a standard for exchanging health data between systems. Instead of one giant patient file, FHIR splits health information into small, typed building blocks called **resources** (Patient, Observation, Encounter, Condition, and so on). Each resource is a JSON document with an agreed structure, and resources point to one another through **references**.

Systems talk to a FHIR server over ordinary web requests (REST):

| Action | HTTP request | Used in this project |
|---|---|---|
| Create a resource | `POST /Patient` | Step 1 |
| Read one resource by ID | `GET /Patient/524813` | Step 2 |
| Search for resources | `GET /Patient?identifier=...` | Step 2 |

A successful create returns status `201`, a successful read or search returns `200`, and a missing resource returns `404`.

## The Patient resource

A **Patient** holds the administrative information about the person receiving care. It is *who* the record is about.

```json
{
  "resourceType": "Patient",
  "id": "524813",
  "identifier": [{"system": "https://example.org/fhir-portfolio-project", "value": "demo-001"}],
  "name": [{"use": "official", "family": "Demo", "given": ["Ada"]}],
  "gender": "female",
  "birthDate": "1990-04-12"
}
```

| Field | Meaning |
|---|---|
| `id` | The server-assigned ID, unique on that server |
| `identifier` | An ID from a named system (for example a hospital number). The `system` says who issued it, and the `value` is the number. Here it lets me find only my own records on a shared server |
| `name` | A list, because people can have several names (official, nickname, maiden). Each has `family` and a list of `given` names |
| `gender` | Administrative gender, restricted to `male`, `female`, `other` or `unknown` |
| `birthDate` | A date in `YYYY-MM-DD` format |

## The Observation resource

An **Observation** records one measurement or finding about a patient: a vital sign, a lab result, a smoking status. It is *what was measured*.

```json
{
  "resourceType": "Observation",
  "status": "final",
  "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "vital-signs"}]}],
  "code": {"coding": [{"system": "http://loinc.org", "code": "8867-4", "display": "Heart rate"}]},
  "subject": {"reference": "Patient/524813"},
  "effectiveDateTime": "2026-11-12T20:44:00+00:00",
  "valueQuantity": {"value": 72, "unit": "beats/minute", "system": "http://unitsofmeasure.org", "code": "/min"}
}
```

| Field | Meaning |
|---|---|
| `status` | Where the result is in its life cycle (`preliminary`, `final`, `amended`, ...). `final` means complete |
| `category` | Broad grouping, here `vital-signs`, which lets systems filter |
| `code` | **What** was measured, using a standard code. LOINC `8867-4` means heart rate, so any system can understand it without reading free text |
| `subject` | **Who** it is about: a reference to a Patient |
| `effectiveDateTime` | When the measurement applies to |
| `valueQuantity` | The result: a number plus a unit. The `code` uses UCUM, the standard for units (`/min`, `Cel` for degrees Celsius) |

## How the two resources connect

The key FHIR idea is the **reference**. The Observation does not copy the patient's name or birth date. It holds `"subject": {"reference": "Patient/524813"}`, a pointer to the Patient. Patient details are stored once and every measurement links back to them, which avoids duplication and keeps systems consistent.

```
Patient/524813 (Ada Demo)
   |-- Observation: Heart rate 72 beats/minute
   `-- Observation: Body temperature 36.8 degC
```

## Other terms used

- **Bundle:** the wrapper a search returns. The matching resources sit in its `entry` list, which is why the code reads `bundle["entry"][i]["resource"]`.
- **LOINC:** a standard code system for observations and lab tests (`8867-4` heart rate, `8310-5` body temperature).
- **UCUM:** a standard code system for units of measure.
- **Interoperability:** different systems exchanging data and understanding it the same way. Standard codes, units and structures are what make that possible.

## Why validate and flatten

- **Validation** catches malformed or implausible data (a future birth date, a temperature of 98.6 recorded as degrees Celsius) before it spreads to other systems.
- **Flattening** turns nested JSON into a table (one row per patient) so that analysts can use it in Excel, SQL or dashboards.
