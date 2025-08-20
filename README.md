# recode-scenario
Creation of clinical scenario for medical documents generation

Data description

| French PMSI term                 | English equivalent                                         | Notes / Context                                                                 |
|---------------------------------|------------------------------------------------------------|--------------------------------------------------------------------------------|
| `Résumé PMSI`                     | Patient-level coded abstract / Discharge abstract          | Structured data for each hospitalization, includes ICD diagnoses, procedures, demographics. |
| `Code diagnostic principal (CDP)` | Primary diagnosis (`ICD code`)                              | Main reason for hospitalization.                                               |
| `Codes diagnostics associés (CDA)`| Secondary diagnoses (`ICD codes`)                            | Comorbidities or complications during the stay.                                |
| `Actes / Procédures`              | Procedures / `ICD procedure codes`                           | Coded interventions performed during hospitalization.                          |
| `DRG (Groupe Homogène de Malades)`| `DRG (Diagnosis-Related Group)`                               | Classification for resource use / reimbursement purposes.                      |
| `MDC (Groupe Diagnostic Majeur)`  | `MDC (Major Diagnostic Category)`                             | Top-level DRG grouping by body system or disease category.                     |
| `Données de séjour / patient`     | Case-level data / Patient-level data                         | Individual hospitalization record used for DRG assignment or analysis.         |
| `Variables normalisées`           | Normalized variables / Standardized coded fields            | Coded fields derived from the patient record (`ICD`, procedures, demographics). |


**Hospitalization management type** – a clinical abstraction derived from the combination of the principal diagnosis (`DP`) and the linked diagnosis (`DR`). This combination determines the DRG assignment and reflects the patient’s management mode during the hospital stay.
