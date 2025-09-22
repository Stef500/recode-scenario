# recode-scenario
Creation of clinical scenario for medical documents generation

## Variables definition

***Variables dictionary*** :
* drg_code
* drg_description
* drg_parent_code
* drg_parent_code_description
* icd_code
* icd_code_description
* icd_parent_code
* icd_parent_code_description
* icd_primary_code : digonstic principal
* icd_primary_code_definition : digonstic principal
* icd_secondary : related diagnosis
* cage : age classes [0-1[, [1-5[,[15-18[, [5-10[, [10-15[, [30-40[, [50-60[, [18-30[, [40-50[, [60-70[, [70-80[, [80-[
* cage2 :  age classes [0-1[ , [1-5[ , [5-10[ , [10-15[ , [15-18[, [18-50[ , [50-[
* sexe : 1/2 (F)
* admission_mode
* discharge_disposition
* admission_type
       

***Table classification_profile***
* drg_parent_code
* icd_primary_code
* icd_primary_parent_code
* case_management_type
* cage
* cage2
* sexe

***Table secondary_diagnosis***
* drg_parent_code
* icd_primary_parent_code
* cage2
* sexe

For cancer, we use a ***synthetic treatment recommandation table*** :
* primary_site
* histological_type
* Stage	
* T : tumor (TNM)
* N : nodes (TNM)
* M	: metastasis (TNM)
* TNM_score	
* biomarkers
* treatment_recommandation
* chemotherapy_regimen


Use the col_names options when import files in the load function of the project to align the columns names of your files with this dictionary.



| French PMSI term                 | English equivalent                                         | Notes / Context                                                                 |
|---------------------------------|------------------------------------------------------------|--------------------------------------------------------------------------------|
| `Résumé PMSI`                     | Patient-level coded abstract / Discharge abstract          | Structured data for each hospitalization, includes ICD diagnoses, procedures, demographics. |
| `Code diagnostic principal (CDP)` | Primary diagnosis (`ICD code`)                              | Main reason for hospitalization.                                               |
| `Codes diagnostics associés (CDA)`| Secondary diagnoses (`ICD codes`)                            | Comorbidities or complications during the stay.                                |
| `Actes / Procédures`              | Procedures / `ICD procedure codes`                           | Coded interventions performed during hospitalization.                          |
| `DRG (Groupe Homogène de Malades)`| `DRG (Diagnosis-Related Group)`                               | Classification for resource use / reimbursement purposes.                      |
| `MDC (Groupe Diagnostic Majeur)`  | `MDC (Major Diagnostic Category)`                             | Top-level DRG grouping by body system or disease category.                     |
| `Données de séjour / patient`     | Case-level data / Patient-level data                         | Individual hospitalization record used for DRG assignment or analysis.         |
| `Mode entrée`                     | `Admission mode`                                          |  How the patient was admitted to the hospital.                              |
| `Mode de sortie`                     | `Discharge disposition`                                   |  How the patient was discharged from the hospital, including deceased.                        |
| `Mode d'hospitalisation`                     | `Type of admission`                                   |  Inpatient admission vs Outpatient admission                 |
| `Variables normalisées`           | Normalized variables / Standardized coded fields            | Coded fields derived from the patient record (`ICD`, procedures, demographics). |


## Hospitalization management type 
**Hospitalization management type** – a clinical abstraction derived from the combination of the principal diagnosis (`DP`) and the linked diagnosis (`DR`). This combination determines the DRG assignment and reflects the patient’s management mode during the hospital stay.

**Hospitalization management type** are inhéreted from ATIH coding rules : cf recap table [Guide Situations cliniques](https://docs.google.com/spreadsheets/d/1XRVeSn3VFSaM8o7bJYz7gGcyAFWN9Gn7Ko4x-tAOYjs/edit?usp=sharing).

**Hospitalization management type for chronic diseases** 

| Cancer                                                    | Diabetis                                                       | Other chronic diseases                                       |
|-----------------------------------------------------------|----------------------------------------------------------------|--------------------------------------------------------------|
| Hospital admission with initial diagnosis of the cancer   | Hospital admission with initial diagnosis of diabetes          | Hospital admission with initial diagnosis of the disease     |
| Hospital admission for cancer workup                      | Hospital admission for diabetes initial workup                 | Hospital admission for diagnostic workup                     |
| Hospital admission for initiation of treatment            | Hospital admission for initiation of treatment of the diabetes | Hospital admission for initiation of treatment               |
| Hospital admission for relapse or recurrence of the cancer| Hospital admission for change in therapeutic strategy          | Hospital admission for acute exacerbation of the disease     |


