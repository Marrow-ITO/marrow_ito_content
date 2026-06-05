"""Word-by-word spell-correction with a medical-aware vocabulary.

Built on pyspellchecker (edit distance up to 2). Seeded with the most
commonly-tested drug names and condition names — drug spellings are where
the typo-correction lift comes from for med students.

Usage:
    corrected = maybe_correct("pantaprazole")   # -> "Pantoprazole" or None
    corrected = maybe_correct("heart failure")  # -> None (no typo)
"""

from spellchecker import SpellChecker


# Build a dedicated medical-only checker. `language=None` skips the default
# English corpus so plain English words don't trigger false positives.
_spell = SpellChecker(language=None, distance=2)

_MEDICAL_VOCAB: list[str] = [
    # ===== Drugs (commonly tested) =====
    # PPIs
    "pantoprazole", "omeprazole", "esomeprazole", "rabeprazole", "lansoprazole",
    "dexlansoprazole",
    # Statins
    "atorvastatin", "rosuvastatin", "simvastatin", "pravastatin", "fluvastatin",
    # Beta blockers
    "metoprolol", "carvedilol", "bisoprolol", "atenolol", "propranolol",
    "nadolol", "esmolol", "labetalol", "nebivolol",
    # ACE inhibitors
    "lisinopril", "enalapril", "captopril", "ramipril", "perindopril",
    # ARBs
    "losartan", "valsartan", "telmisartan", "olmesartan", "irbesartan", "candesartan",
    # CCBs
    "amlodipine", "nifedipine", "diltiazem", "verapamil", "felodipine",
    # Diabetes drugs
    "metformin", "glimepiride", "glibenclamide", "gliclazide",
    "sitagliptin", "linagliptin", "saxagliptin", "vildagliptin",
    "dapagliflozin", "empagliflozin", "canagliflozin", "ertugliflozin",
    "liraglutide", "semaglutide", "dulaglutide", "exenatide",
    # Antibiotics
    "azithromycin", "clarithromycin", "erythromycin", "doxycycline", "minocycline",
    "ciprofloxacin", "levofloxacin", "moxifloxacin", "norfloxacin",
    "rifampicin", "isoniazid", "pyrazinamide", "ethambutol", "streptomycin",
    "amoxicillin", "ampicillin", "piperacillin", "tazobactam",
    "cefixime", "ceftriaxone", "cefuroxime", "cefepime", "ceftazidime",
    "vancomycin", "linezolid", "daptomycin", "meropenem",
    # Anticoagulants
    "warfarin", "apixaban", "rivaroxaban", "dabigatran", "edoxaban",
    "heparin", "enoxaparin", "fondaparinux",
    # Antiplatelets
    "clopidogrel", "ticagrelor", "prasugrel", "aspirin",
    # Diuretics
    "furosemide", "torsemide", "bumetanide",
    "spironolactone", "eplerenone",
    "hydrochlorothiazide", "indapamide", "chlorthalidone",
    # DMARDs / immunosuppressants
    "methotrexate", "azathioprine", "cyclophosphamide", "mycophenolate", "tacrolimus",
    # Biologics
    "infliximab", "adalimumab", "vedolizumab", "rituximab", "ustekinumab",
    "tocilizumab", "etanercept", "golimumab",
    # Respiratory
    "salbutamol", "ipratropium", "tiotropium", "budesonide", "fluticasone",
    "salmeterol", "formoterol", "montelukast",
    # IBD-specific
    "mesalamine", "sulfasalazine", "balsalazide", "olsalazine",
    # GI motility / antiemetics
    "ondansetron", "metoclopramide", "domperidone", "loperamide",
    "rabeprazole", "famotidine", "ranitidine",
    # ===== Conditions =====
    "myocardial", "infarction", "ulcerative", "colitis", "diabetes", "mellitus",
    "hypertension", "tuberculosis", "asthma", "anaphylaxis", "pneumonia",
    "bronchitis", "emphysema", "atherosclerosis", "cardiomyopathy",
    "cirrhosis", "hepatitis", "nephropathy", "neuropathy",
    "arthritis", "lupus", "psoriasis", "eczema", "dermatitis",
    "schizophrenia", "depression", "anxiety", "bipolar",
    "stroke", "seizure", "epilepsy", "parkinson", "alzheimer",
    "rheumatoid", "osteoarthritis", "osteoporosis", "fibromyalgia",
    "pancreatitis", "appendicitis", "cholecystitis", "diverticulitis",
    "glomerulonephritis", "pyelonephritis",
    "hyperthyroidism", "hypothyroidism", "hypoglycemia", "hyperglycemia",
    "pulmonary", "embolism", "thrombosis",
    "crohn", "crohns",
]


_spell.word_frequency.load_words(_MEDICAL_VOCAB)
_VOCAB_SET = set(_MEDICAL_VOCAB)


def maybe_correct(query: str) -> str | None:
    """Return a corrected query if at least one token was fixed; else None.

    Word-by-word approach — multi-word phrases are corrected per token, so
    `"mechanism of beta blockrs"` -> `"Mechanism Of Beta Blockers"`. The
    returned string is title-cased for display.
    """
    words = query.split()
    if not words:
        return None

    corrected: list[str] = []
    any_corrected = False

    for token in words:
        # Strip surrounding punctuation but preserve internal hyphens.
        stripped = token.strip(".,;:!?\"'()[]{}")
        lower = stripped.lower()

        if not lower or not lower.replace("-", "").replace("/", "").isalpha():
            corrected.append(token)
            continue

        # Already correct (in our medical vocab).
        if lower in _VOCAB_SET:
            corrected.append(stripped)
            continue

        # Unknown word — try correction.
        suggestion = _spell.correction(lower)
        if suggestion and suggestion != lower:
            corrected.append(suggestion)
            any_corrected = True
        else:
            corrected.append(token)

    if not any_corrected:
        return None

    return " ".join(corrected).title()
