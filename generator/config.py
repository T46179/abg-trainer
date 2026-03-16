"""Shared static configuration for the ABG case generator.

This module centralizes constants used across generation and validation,
including progression settings, question labels/options, and the clinical
stem bank used to build varied case prompts.
"""

PROGRESSION_VERSION = "v1"

TESTING_MODE = True
TESTING_XP_MULTIPLIER = 5

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
    ],
}

STEM_BANK = {
    "dka": {
        "ages": ["18-year-old", "19-year-old", "23-year-old", "27-year-old", "31-year-old", "34-year-old"],
        "openers": ["presents to ED", "is brought to ED", "attends ED", "comes to ED"],
        "feature_groups": {
            "respiratory": ["tachypnoea", "deep rapid breathing", "rapid breathing"],
            "gi": ["abdominal pain", "vomiting", "nausea and abdominal discomfort"],
            "volume": ["dehydration", "reduced oral intake", "marked thirst"],
            "metabolic": ["polyuria", "general malaise", "recent weight loss"],
        },
        "patterns": [
            "{age} {opener} {f1}, {f2}, and {f3}.",
            "{age} {opener} with {f1} and {f2}.",
            "{age} {opener} unwell with {f1} and {f2}.",
            "{age} {opener} after several days of illness, with {f1} and {f2}.",
            "{age} {opener} with {f1}, {f2}, and appears volume depleted.",
        ],
    },
    "dka_vomiting": {
        "ages": ["24-year-old", "28-year-old", "30-year-old"],
        "openers": ["presents to ED", "is brought to ED", "attends ED"],
        "feature_groups": {
            "diabetes_context": ["with type 1 diabetes", "after missed insulin doses"],
            "respiratory": ["with deep rapid breathing", "tachypnoeic"],
            "gi": ["with persistent vomiting", "with abdominal pain"],
            "volume": ["dehydrated", "with reduced oral intake"],
        },
        "patterns": [
            "{age} {opener} {f1}, {f2}, and {f3}.",
            "{age} {opener} with {f1} and {f2}.",
            "{age} {opener} unwell with {f1}, {f2}, and {f3}.",
        ],
    },
    "vomiting_metabolic_alkalosis": {
        "ages": ["35-year-old", "40-year-old", "45-year-old"],
        "openers": ["presents to ED", "attends ED", "is brought in"],
        "feature_groups": {
            "vomiting": ["with persistent vomiting", "after several days of vomiting"],
            "volume": ["with dehydration", "with reduced oral intake"],
            "symptoms": ["with lightheadedness", "with weakness"],
            "general": ["with nausea", "feeling generally unwell"],
        },
        "patterns": [
            "{age} {opener} {f1} and {f2}.",
            "{age} {opener} with {f1}, {f2}, and {f3}.",
            "{age} {opener} unwell with {f1} and {f2}.",
        ],
    },
    "diarrhoea_nagma": {
        "ages": ["32-year-old", "38-year-old", "42-year-old"],
        "openers": ["presents to ED", "attends ED", "is brought in"],
        "feature_groups": {
            "bowel_loss": ["with profuse diarrhoea", "after several days of diarrhoea"],
            "volume": ["with dehydration", "with reduced oral intake"],
            "abdominal": ["with abdominal cramps", "with abdominal discomfort"],
            "systemic": ["with weakness", "feeling generally unwell"],
        },
        "patterns": [
            "{age} {opener} {f1} and {f2}.",
            "{age} {opener} with {f1}, {f2}, and {f3}.",
            "{age} {opener} unwell with {f1} and {f2}.",
        ],
    },
    "panic_hyperventilation": {
        "ages": ["20-year-old", "22-year-old", "25-year-old", "29-year-old", "33-year-old"],
        "openers": ["presents to ED", "is brought in", "attends ED", "comes to ED"],
        "feature_groups": {
            "breathing": ["hyperventilation", "sudden dyspnoea", "rapid breathing"],
            "anxiety": ["anxiety", "visible distress", "recent emotional stress"],
            "chest": ["chest tightness", "a sensation of not getting enough air", "non-pleuritic chest discomfort"],
            "peripheral": ["tingling in the fingers", "lightheadedness", "perioral tingling"],
        },
        "patterns": [
            "{age} {opener} {f1} and {f2}.",
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
            "sepsis_signs": ["febrile", "with rigors"],
            "perfusion": ["hypotensive", "tachycardic"],
            "severity": ["with increasing oxygen requirements", "with confusion"],
            "context": ["with suspected sepsis", "appearing critically unwell"],
        },
        "patterns": [
            "{age} {opener} {f1}, {f2}, and {f3}.",
            "{age} {opener} with {f1} and {f2}.",
            "{age} {opener} unwell with {f1}, {f2}, and {f3}.",
        ],
    },
    "opioid_toxicity": {
        "ages": ["27-year-old", "32-year-old", "40-year-old"],
        "openers": ["is brought to ED", "is found collapsed", "presents"],
        "feature_groups": {
            "consciousness": ["with reduced consciousness", "with decreased responsiveness"],
            "respiratory": ["with shallow respirations", "with bradypnoea"],
            "tox_clues": ["with pinpoint pupils", "after suspected opioid use"],
            "severity": ["difficult to rouse", "with low GCS"],
        },
        "patterns": [
            "{age} {opener} {f1} and {f2}.",
            "{age} {opener} with {f1}, {f2}, and {f3}.",
            "{age} {opener} drowsy, with {f1} and {f2}.",
        ],
    },
    "copd_chronic_retainer": {
        "ages": ["68-year-old", "72-year-old", "75-year-old"],
        "openers": ["presents", "attends ED", "is brought in"],
        "feature_groups": {
            "background": ["with chronic COPD", "with long-standing dyspnoea"],
            "retention": ["with chronic hypercapnia", "known to retain CO2"],
            "symptoms": ["with reduced exercise tolerance", "with chronic breathlessness"],
            "airways": ["with productive cough", "with wheeze"],
        },
        "patterns": [
            "{age} {opener} {f1} and {f2}.",
            "{age} {opener} with {f1}, {f2}, and {f3}.",
            "{age} {opener} with background {f1} and {f2}.",
        ],
    },
    "acute_copd_exacerbation": {
        "ages": ["61-year-old", "65-year-old", "68-year-old", "72-year-old", "76-year-old"],
        "openers": ["presents", "is brought to ED", "attends ED", "comes to ED"],
        "feature_groups": {
            "worsening": ["worsening dyspnoea", "several days of breathlessness", "increased work of breathing"],
            "airways": ["productive cough", "wheeze", "increased sputum"],
            "hypercapnia": ["increasing somnolence", "hypercapnic symptoms", "increased drowsiness"],
            "background": ["known COPD", "chronic respiratory disease", "a history of COPD"],
        },
        "patterns": [
            "{age} {opener} {f1} and {f2}.",
            "{age} {opener} {f1}, {f2}, and {f3}.",
            "{age} {opener} with {f1} on a background of {f2}.",
            "{age} {opener} after several days of infective symptoms, with {f1} and {f2}.",
            "{age} {opener} with {f1}, {f2}, on a background of {f3}.",
        ],
    },
    "sepsis_respiratory_alkalosis": {
        "ages": ["50-year-old", "55-year-old", "60-year-old"],
        "openers": ["presents to ED", "is brought to ED", "attends ED"],
        "feature_groups": {
            "infection": ["febrile", "with rigors"],
            "respiratory": ["tachypnoeic", "with respiratory distress"],
            "circulation": ["tachycardic", "hypotensive"],
            "source": ["with pneumonia", "with suspected sepsis"],
        },
        "patterns": [
            "{age} {opener} {f1}, {f2}, and {f3}.",
            "{age} {opener} with {f1} and {f2}.",
            "{age} {opener} unwell with {f1}, {f2}, and {f3}.",
        ],
    },
    "salicylate_toxicity": {
        "ages": ["18-year-old", "22-year-old", "30-year-old"],
        "openers": ["presents to ED", "is brought to ED", "attends ED"],
        "feature_groups": {
            "tox_context": ["after possible overdose", "after ingestion of unknown tablets"],
            "respiratory": ["tachypnoeic", "hyperventilating"],
            "ent": ["with tinnitus", "complaining of ringing in the ears"],
            "systemic": ["with nausea and vomiting", "with confusion"],
        },
        "patterns": [
            "{age} {opener} {f1}, {f2}, and {f3}.",
            "{age} {opener} with {f1} and {f2}.",
            "{age} {opener} unwell with {f1}, {f2}, and {f3}.",
        ],
    },
}
