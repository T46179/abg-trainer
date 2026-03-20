"""Shared static configuration for the ABG case generator.

This module centralizes constants used across generation and validation,
including progression settings, question labels/options, and the clinical
stem bank used to build varied case prompts.
"""

PROGRESSION_VERSION = "v1"

TESTING_MODE = True
TESTING_XP_MULTIPLIER = 5
CASES_PER_ARCHETYPE = 8

BASE_XP_BY_DIFFICULTY = {
    1: 10,
    2: 15,
    3: 25,
    4: 40,
}

PERFECT_CASE_BONUS_PERCENT = 0.10

SPEED_BONUS_TIERS = [
    {"max_seconds": 30, "bonus": 10},
    {"max_seconds": 45, "bonus": 7},
    {"max_seconds": 60, "bonus": 5},
    {"max_seconds": 90, "bonus": 3},
    {"max_seconds": 999999, "bonus": 0},
]

STREAK_BONUS_TIERS = [
    {"min_days": 3, "bonus": 2},
    {"min_days": 7, "bonus": 5},
    {"min_days": 14, "bonus": 8},
]

XP_REQUIRED_PER_LEVEL = {
    1: 30,
    2: 40,
    3: 50,
    4: 60,
    5: 80,
    6: 100,
    7: 120,
    8: 140,
    9: 160,
    10: 200,
    11: 240,
    12: 280,
    13: 320,
    14: 360,
    15: 400,
    16: 440,
    17: 480,
    18: 520,
    19: 560,
    20: 600,
    21: 640,
    22: 680,
    23: 720,
    24: 760,
}

DIFFICULTY_UNLOCK_LEVELS = {
    1: 1,
    2: 5,
    3: 10,
    4: 20,
}

FREE_DAILY_CASE_LIMIT = 5

QUESTION_LABELS = {
    "ph_status": "pH",
    "primary_disorder": "Primary acid-base disorder",
    "compensation": "Compensation",
    "anion_gap": "Anion gap",
    "additional_metabolic_process": "Additional metabolic disorder",
}

PROMPTS = {
    "ph_status": "What is the pH status?",
    "primary_disorder": "What is the primary acid-base disorder?",
    "compensation": "Is the physiological compensation appropriate?",
    "anion_gap": "What is the anion gap status?",
    "additional_metabolic_process": "Is an additional metabolic disorder present?",
}

OPTIONS = {
    "ph_status": ["Acidaemia", "Alkalaemia", "Normal"],
    "primary_disorder": [
        "Respiratory acidosis",
        "Respiratory alkalosis",
        "Metabolic acidosis",
        "Metabolic alkalosis",
    ],
    "compensation": ["Appropriate", "Inappropriate"],
    "anion_gap": ["Raised", "Normal"],
    "additional_metabolic_process": [
        "None",
        "Metabolic alkalosis",
        "Non-anion gap metabolic acidosis",
        "High anion gap metabolic acidosis",
    ],
}

STEM_BANK = {
    "dka": {
        "ages": ["18-year-old", "19-year-old", "23-year-old", "27-year-old", "31-year-old", "34-year-old"],
        "openers": ["presents to ED", "is brought to ED", "attends ED", "presents to ED"],
        "feature_groups": {
            "respiratory": ["tachypnoea", "deep breathing", "Kussmaul respirations"],
            "gi": ["abdominal pain", "vomiting", "nausea and abdominal discomfort"],
            "volume": ["dehydration", "reduced oral intake", "marked thirst"],
            "metabolic": ["polyuria", "general malaise", "recent weight loss"],
        },
        "patterns": [
            "{age} {opener} with {f1}, {f2}, and {f3}.",
            "{age} {opener} with {f1} and {f2}.",
            "{age} {opener} with {f1} and {f2}.",
            "{age} {opener} after several days of symptoms, with {f1} and {f2}.",
            "{age} {opener} with {f1}, {f2}, and dehydration.",
        ],
    },
    "alcoholic_ketoacidosis": {
        "ages": ["26-year-old", "31-year-old", "36-year-old", "42-year-old", "48-year-old"],
        "openers": ["presents to ED", "attends ED", "is brought in", "presents to ED"],
        "feature_groups": {
            "alcohol": [
                "recent alcohol binge",
                "recent heavy alcohol intake",
                "heavy alcohol use",
            ],
            "intake": [
                "poor oral intake",
                "reduced oral intake",
                "minimal oral intake",
            ],
            "gi": [
                "repeated vomiting",
                "nausea and abdominal pain",
                "epigastric pain",
            ],
            "withdrawal": [
                "early withdrawal symptoms",
                "diaphoresis",
                "tremor",
            ],
            "volume": [
                "dehydration",
                "dry mucous membranes",
                "postural light-headedness",
            ],
            "respiratory": [
                "tachypnoea",
            ],
        },
        "patterns": [
            "{age} {opener} with {f1} and {f2}.",
            "{age} {opener} with {f1}, {f2}, and {f3}.",
            "{age} {opener} with {f1} and {f2}.",
            "{age} {opener} with {f1}, {f2}, and {f3}.",
            "{age} {opener} with {f1}, {f2}, and dehydration.",
        ],
    },
    "starvation_ketosis": {
        "ages": ["22-year-old", "29-year-old", "35-year-old", "43-year-old", "51-year-old", "58-year-old"],
        "openers": ["presents to ED", "attends ED", "is reviewed in ED", "presents for assessment"],
        "feature_groups": {
            "intake": [
                "several days of poor oral intake",
                "reduced intake due to prolonged nausea",
                "minimal oral intake during a recent illness",
                "fasting with very limited oral intake",
            ],
            "general": [
                "fatigue",
                "light-headedness",
                "recent weight loss",
                "general weakness",
            ],
            "volume": [
                "mild dehydration",
                "dry mucous membranes",
                "postural symptoms",
            ],
            "gi": [
                "nausea",
                "reduced appetite",
                "occasional vomiting",
            ],
            "illness": [
                "prolonged viral symptoms",
                "difficulty eating because of mouth pain",
                "reduced intake after several days of illness",
            ],
        },
        "patterns": [
            "{age} {opener} with {f1} and {f2}.",
            "{age} {opener} with {f1}, {f2}, and {f3}.",
            "{age} {opener} after several days of poor intake, with {f1} and {f2}.",
            "{age} {opener} with {f1}. Other features include {f2} and {f3}.",
        ],
    },
    "toxic_alcohol": {
        "ages": ["29-year-old", "34-year-old", "41-year-old", "47-year-old", "55-year-old"],
        "openers": ["presents to ED", "is brought in", "attends ED", "presents to ED"],
        "feature_groups": {
            "exposure": [
                "uncertain toxic exposure",
                "possible ingestion of a suspicious substance",
                "found near an open solvent container",
            ],
            "neurologic": [
                "confusion",
                "altered mental status",
                "difficulty focusing",
            ],
            "visual": [
                "blurred vision",
                "visual blurring",
            ],
            "gi": [
                "unexplained vomiting",
                "severe abdominal pain",
                "epigastric pain",
            ],
            "renal": [
                "flank pain",
                "oliguria",
            ],
            "systemic": [
                "tachypnoea",
                "dehydration",
            ],
        },
        "patterns": [
            "{age} {opener} with {f1} and {f2}.",
            "{age} {opener} with {f1}, {f2}, and {f3}.",
            "{age} {opener} with {f1}. Other features include {f2} and {f3}.",
            "{age} {opener} with {f1}, {f2}, and {f3}.",
            "{age} {opener} with {f1}, {f2}, and dehydration.",
        ],
    },
    "dka_vomiting": {
        "ages": ["24-year-old", "28-year-old", "30-year-old"],
        "openers": ["presents to ED", "is brought to ED", "attends ED"],
        "feature_groups": {
            "diabetes_context": ["type 1 diabetes", "missed insulin doses"],
            "respiratory": ["deep breathing", "tachypnoea"],
            "gi": ["persistent vomiting", "abdominal pain"],
            "volume": ["dehydration", "reduced oral intake"],
        },
        "patterns": [
            "{age} {opener} with {f1}, {f2}, and {f3}.",
            "{age} {opener} with {f1} and {f2}.",
            "{age} {opener} with {f1}, {f2}, and {f3}.",
        ],
    },
    "mixed_hagma_metabolic_alkalosis": {
        "ages": ["24-year-old", "29-year-old", "35-year-old", "42-year-old", "51-year-old"],
        "openers": ["presents to ED", "attends ED", "is reviewed in ED", "presents for assessment"],
        "feature_groups": {
            "vomiting": [
                "several days of vomiting",
                "persistent retching",
                "ongoing emesis",
            ],
            "intake": [
                "reduced oral intake",
                "minimal oral intake",
                "poor intake during a recent illness",
            ],
            "volume": [
                "dry mucous membranes",
                "postural light-headedness",
                "dehydration",
            ],
            "stress": [
                "malaise",
                "fatigue",
                "abdominal discomfort",
            ],
            "illness": [
                "a recent febrile illness",
                "several days of metabolic stress",
                "ongoing systemic unwellness",
            ],
        },
        "patterns": [
            "{age} {opener} with {f1} and {f2}.",
            "{age} {opener} with {f1}, {f2}, and {f3}.",
            "{age} {opener} after several days of illness, with {f1} and {f2}.",
            "{age} {opener} with {f1}. Other features include {f2} and {f3}.",
        ],
    },
    "vomiting_metabolic_alkalosis": {
        "ages": ["35-year-old", "40-year-old", "45-year-old"],
        "openers": ["presents to ED", "attends ED", "is brought in"],
        "feature_groups": {
            "vomiting": ["persistent vomiting", "several days of vomiting"],
            "volume": ["dehydration", "reduced oral intake"],
            "symptoms": ["light-headedness", "weakness"],
            "general": ["nausea", "malaise"],
        },
        "patterns": [
            "{age} {opener} with {f1} and {f2}.",
            "{age} {opener} with {f1}, {f2}, and {f3}.",
            "{age} {opener} with {f1} and {f2}.",
        ],
    },
    "diarrhoea_nagma": {
        "ages": ["32-year-old", "38-year-old", "42-year-old"],
        "openers": ["presents to ED", "attends ED", "is brought in"],
        "feature_groups": {
            "bowel_loss": ["profuse diarrhoea", "several days of diarrhoea"],
            "volume": ["dehydration", "reduced oral intake"],
            "abdominal": ["abdominal cramps", "abdominal discomfort"],
            "systemic": ["weakness", "malaise"],
        },
        "patterns": [
            "{age} {opener} with {f1} and {f2}.",
            "{age} {opener} with {f1}, {f2}, and {f3}.",
            "{age} {opener} with {f1} and {f2}.",
        ],
    },
    "simple_nagma": {
        "ages": ["24-year-old", "31-year-old", "37-year-old", "45-year-old", "53-year-old"],
        "openers": ["presents to ED", "attends ED", "is reviewed in ED", "presents for assessment"],
        "feature_groups": {
            "loss_context": [
                "several days of diarrhoea",
                "high-output ileostomy losses",
                "ongoing enteric fluid loss",
                "increased stoma output",
            ],
            "volume": [
                "dry mucous membranes",
                "mild dehydration",
                "postural light-headedness",
            ],
            "systemic": [
                "fatigue",
                "general weakness",
                "malaise",
            ],
            "abdominal": [
                "abdominal cramps",
                "loose stool symptoms",
                "reduced oral intake",
            ],
        },
        "patterns": [
            "{age} {opener} with {f1} and {f2}.",
            "{age} {opener} with {f1}, {f2}, and {f3}.",
            "{age} {opener} after ongoing gastrointestinal losses, with {f1} and {f2}.",
            "{age} {opener} with {f1}. Other features include {f2} and {f3}.",
        ],
    },
    "simple_metabolic_alkalosis": {
        "ages": ["26-year-old", "34-year-old", "41-year-old", "49-year-old", "57-year-old"],
        "openers": ["presents to ED", "attends ED", "is reviewed in ED", "presents for assessment"],
        "feature_groups": {
            "loss_context": [
                "recurrent vomiting",
                "ongoing nasogastric losses",
                "several days of upper gastrointestinal fluid loss",
                "persistent retching",
            ],
            "volume": [
                "dry mucous membranes",
                "mild volume depletion",
                "postural light-headedness",
            ],
            "systemic": [
                "fatigue",
                "general weakness",
                "malaise",
            ],
            "gi": [
                "nausea",
                "reduced oral intake",
                "abdominal discomfort",
            ],
        },
        "patterns": [
            "{age} {opener} with {f1} and {f2}.",
            "{age} {opener} with {f1}, {f2}, and {f3}.",
            "{age} {opener} after ongoing upper gastrointestinal losses, with {f1} and {f2}.",
            "{age} {opener} with {f1}. Other features include {f2} and {f3}.",
        ],
    },
    "panic_hyperventilation": {
        "ages": ["20-year-old", "22-year-old", "25-year-old", "29-year-old", "33-year-old"],
        "openers": ["presents to ED", "is brought in", "attends ED", "presents to ED"],
        "feature_groups": {
            "breathing": ["hyperventilation", "sudden dyspnoea", "tachypnoea"],
            "anxiety": ["anxiety", "visible distress", "recent emotional stress"],
            "chest": ["chest tightness", "air hunger", "non-pleuritic chest discomfort"],
            "peripheral": ["digital paraesthesia", "light-headedness", "perioral tingling"],
        },
        "patterns": [
            "{age} {opener} with {f1} and {f2}.",
            "{age} {opener} with {f1}, {f2}, and {f3}.",
            "{age} {opener} anxious and {f1}, with {f2}.",
            "{age} {opener} shortly after emotional stress, with {f1} and {f2}.",
            "{age} {opener} with abrupt symptoms of {f1}, {f2}, and {f3}.",
        ],
    },
    "lactic_acidosis": {
        "ages": ["60-year-old", "65-year-old", "72-year-old"],
        "openers": ["presents to ED", "is brought in", "is admitted"],
        "feature_groups": {
            "sepsis_signs": ["fever", "rigors"],
            "perfusion": ["hypotension", "tachycardia"],
            "severity": ["increasing oxygen requirements", "confusion"],
            "context": ["suspected sepsis", "critical illness"],
        },
        "patterns": [
            "{age} {opener} with {f1}, {f2}, and {f3}.",
            "{age} {opener} with {f1} and {f2}.",
            "{age} {opener} with {f1}, {f2}, and {f3}.",
        ],
    },
    "opioid_toxicity": {
        "ages": ["27-year-old", "32-year-old", "40-year-old"],
        "openers": ["is brought to ED", "is found collapsed", "presents"],
        "feature_groups": {
            "consciousness": ["reduced consciousness", "decreased responsiveness"],
            "respiratory": ["shallow respirations", "bradypnoea"],
            "tox_clues": ["pinpoint pupils", "suspected opioid use"],
            "severity": ["difficulty rousing", "low GCS"],
        },
        "patterns": [
            "{age} {opener} with {f1} and {f2}.",
            "{age} {opener} with {f1}, {f2}, and {f3}.",
            "{age} {opener} drowsy, with {f1} and {f2}.",
        ],
    },
    "copd_chronic_retainer": {
        "ages": ["68-year-old", "72-year-old", "75-year-old"],
        "openers": ["presents", "attends ED", "is brought in"],
        "feature_groups": {
            "background": ["chronic COPD", "long-standing dyspnoea"],
            "retention": ["chronic hypercapnia", "CO2 retention"],
            "symptoms": ["reduced exercise tolerance", "chronic breathlessness"],
            "airways": ["productive cough", "wheeze"],
        },
        "patterns": [
            "{age} {opener} with {f1} and {f2}.",
            "{age} {opener} with {f1}, {f2}, and {f3}.",
            "{age} {opener} with background {f1} and {f2}.",
        ],
    },
    "acute_copd_exacerbation": {
        "ages": ["61-year-old", "65-year-old", "68-year-old", "72-year-old", "76-year-old"],
        "openers": ["presents", "is brought to ED", "attends ED", "presents to ED"],
        "feature_groups": {
            "worsening": ["worsening dyspnoea", "several days of breathlessness", "increased work of breathing"],
            "airways": ["productive cough", "wheeze", "increased sputum"],
            "hypercapnia": ["increasing somnolence", "hypercapnic symptoms", "increased drowsiness"],
            "background": ["known COPD", "chronic respiratory disease", "a history of COPD"],
        },
        "patterns": [
            "{age} {opener} with {f1} and {f2}.",
            "{age} {opener} with {f1}, {f2}, and {f3}.",
            "{age} {opener} with {f1} on a background of {f2}.",
            "{age} {opener} after several days of infective symptoms, with {f1} and {f2}.",
            "{age} {opener} with {f1}, {f2}, on a background of {f3}.",
        ],
    },
    "sepsis_respiratory_alkalosis": {
        "ages": ["50-year-old", "55-year-old", "60-year-old"],
        "openers": ["presents to ED", "is brought to ED", "attends ED"],
        "feature_groups": {
            "infection": ["fever", "rigors"],
            "respiratory": ["tachypnoea", "respiratory distress"],
            "circulation": ["tachycardia", "hypotension"],
            "source": ["pneumonia", "suspected sepsis"],
        },
        "patterns": [
            "{age} {opener} with {f1}, {f2}, and {f3}.",
            "{age} {opener} with {f1} and {f2}.",
            "{age} {opener} with {f1}, {f2}, and {f3}.",
        ],
    },
    "salicylate_toxicity": {
        "ages": ["18-year-old", "22-year-old", "30-year-old"],
        "openers": ["presents to ED", "is brought to ED", "attends ED"],
        "feature_groups": {
            "tox_context": ["possible overdose", "ingestion of unknown tablets"],
            "respiratory": ["tachypnoea", "hyperventilation"],
            "ent": ["tinnitus", "ringing in the ears"],
            "systemic": ["nausea and vomiting", "confusion"],
        },
        "patterns": [
            "{age} {opener} with {f1}, {f2}, and {f3}.",
            "{age} {opener} with {f1} and {f2}.",
            "{age} {opener} with {f1}, {f2}, and {f3}.",
        ],
    },
}
