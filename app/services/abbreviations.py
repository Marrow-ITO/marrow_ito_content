"""Hard-coded concept dictionaries used by the /api/search pipeline.

Three lookups:
  - ABBREVIATIONS  — lowercase abbrev -> canonical (title-cased) expanded form.
                     Whole-query match only.
  - RELATED        — canonical expanded form -> related concepts (title-cased).
                     Used as a fallback to populate `related_concepts` in the
                     response when the concept graph has no edges for a term.
  - NO_RESULTS_FALLBACK — known bad queries -> hand-curated suggestions.
                          Catches the demo's `bowl inflamation` case.
"""

# Whole-query (case-insensitive) abbreviation expansion.
ABBREVIATIONS: dict[str, str] = {
    # Cardiology
    "mi": "Myocardial Infarction",
    "ami": "Acute Myocardial Infarction",
    "stemi": "ST-Elevation Myocardial Infarction",
    "nstemi": "Non-ST-Elevation Myocardial Infarction",
    "acs": "Acute Coronary Syndrome",
    "hf": "Heart Failure",
    "chf": "Congestive Heart Failure",
    "hfref": "Heart Failure with Reduced Ejection Fraction",
    "hfpef": "Heart Failure with Preserved Ejection Fraction",
    "cad": "Coronary Artery Disease",
    "af": "Atrial Fibrillation",
    "afib": "Atrial Fibrillation",
    "htn": "Hypertension",
    "dvt": "Deep Vein Thrombosis",
    "pe": "Pulmonary Embolism",
    # GI
    "ibd": "Inflammatory Bowel Disease",
    "uc": "Ulcerative Colitis",
    "gerd": "Gastroesophageal Reflux Disease",
    "pud": "Peptic Ulcer Disease",
    "nafld": "Non-Alcoholic Fatty Liver Disease",
    "ibs": "Irritable Bowel Syndrome",
    # Endocrine
    "dm": "Diabetes Mellitus",
    "t1dm": "Type 1 Diabetes Mellitus",
    "t2dm": "Type 2 Diabetes Mellitus",
    "dka": "Diabetic Ketoacidosis",
    "pcos": "Polycystic Ovary Syndrome",
    # Respiratory
    "copd": "Chronic Obstructive Pulmonary Disease",
    "ards": "Acute Respiratory Distress Syndrome",
    "tb": "Tuberculosis",
    # Renal
    "aki": "Acute Kidney Injury",
    "ckd": "Chronic Kidney Disease",
    "uti": "Urinary Tract Infection",
    # Neuro
    "cva": "Cerebrovascular Accident",
    "tia": "Transient Ischemic Attack",
    # ID
    "hiv": "Human Immunodeficiency Virus",
    "aids": "Acquired Immunodeficiency Syndrome",
    # Pharm
    "ppi": "Proton Pump Inhibitor",
    "ace": "Angiotensin Converting Enzyme Inhibitor",
    "arb": "Angiotensin Receptor Blocker",
    "nsaid": "Non-Steroidal Anti-Inflammatory Drug",
    "ssri": "Selective Serotonin Reuptake Inhibitor",
}


# Title-cased canonical -> related concepts (also title-cased).
RELATED_CONCEPTS: dict[str, list[str]] = {
    "Myocardial Infarction": ["STEMI", "NSTEMI", "Acute Coronary Syndrome"],
    "Acute Coronary Syndrome": ["STEMI", "NSTEMI", "Unstable Angina"],
    "Heart Failure": ["HFrEF", "HFpEF", "Cardiomyopathy"],
    "Congestive Heart Failure": ["HFrEF", "HFpEF", "Heart Failure"],
    "Hypertension": ["ACE Inhibitor", "ARB", "Pre-eclampsia"],
    "Atrial Fibrillation": ["Anticoagulation", "Rate Control", "Rhythm Control"],
    "Inflammatory Bowel Disease": ["Ulcerative Colitis", "Crohn's Disease"],
    "Ulcerative Colitis": ["Crohn's Disease", "Inflammatory Bowel Disease"],
    "Gastroesophageal Reflux Disease": ["Pantoprazole", "Omeprazole", "PPI"],
    "Diabetes Mellitus": ["Type 1 Diabetes", "Type 2 Diabetes", "HbA1c"],
    "Type 2 Diabetes Mellitus": ["Metformin", "SGLT2 Inhibitor", "GLP-1 Agonist"],
    "Diabetic Ketoacidosis": ["Insulin", "Fluid Resuscitation", "HHS"],
    "Chronic Obstructive Pulmonary Disease": ["Bronchodilators", "ICS", "Smoking Cessation"],
    "Tuberculosis": ["MDR-TB", "Mycobacterium", "RIPE regimen"],
    "Chronic Kidney Disease": ["AKI", "Dialysis", "Renal Failure"],
    "Acute Kidney Injury": ["Pre-renal", "Intrinsic", "Post-renal"],
    "Cerebrovascular Accident": ["Ischemic Stroke", "Hemorrhagic Stroke", "TIA"],
    "Polycystic Ovary Syndrome": ["Insulin Resistance", "Metformin", "Hyperandrogenism"],
    "Proton Pump Inhibitor": ["Pantoprazole", "Omeprazole", "Esomeprazole"],
    "Pantoprazole": ["Omeprazole", "Esomeprazole", "PPI"],
    "Omeprazole": ["Pantoprazole", "Esomeprazole", "PPI"],
}


# Hard-coded fallback suggestions for queries we know will fail to vector-match.
NO_RESULTS_FALLBACK: dict[str, list[str]] = {
    "bowl inflamation": ["Inflammatory Bowel Disease", "Ulcerative Colitis", "Bowel obstruction"],
    "bowel inflamation": ["Inflammatory Bowel Disease", "Ulcerative Colitis", "Bowel obstruction"],
    "bowl inflammation": ["Inflammatory Bowel Disease", "Ulcerative Colitis", "Bowel obstruction"],
}


# Default fallback when query is truly out-of-scope and no specific match exists.
DEFAULT_FALLBACK_SUGGESTIONS: list[str] = [
    "Heart Failure",
    "Inflammatory Bowel Disease",
    "Diabetes Mellitus",
    "Hypertension",
]
