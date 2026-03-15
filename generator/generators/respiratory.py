"""Respiratory ABG archetype generators.

Main functions:
- `generate_opioid_case`
- `generate_copd_case`
- `generate_panic_case`
- `generate_acute_copd_case`
- `generate_sepsis_case`

These builders generate respiratory acid-base cases with their matching
clinical stems, answers, and progression metadata.
"""

import random

from ..physiology import (
    calc_anion_gap,
    calculate_ph_from_hco3_paco2,
    chronic_respiratory_acidosis_expected_hco3,
    derived_ph_status,
    estimate_ph,
    respiratory_alkalosis_expected_hco3_acute,
)
from ..progression import attach_progression_metadata
from ..question_flow import beginner_question_flow, default_timing, intermediate_question_flow, shuffle_question_options
from ..stems import generate_stem


def generate_opioid_case(case_id):
    paco2 = random.randint(55, 75)
    expected_hco3 = 24 + ((paco2 - 40) / 10)
    hco3 = round(expected_hco3 + random.uniform(-1.0, 1.0), 1)
    ph = estimate_ph(hco3, paco2)
    na = random.randint(136, 142)
    target_ag = random.randint(8, 14)
    cl = na - (hco3 + target_ag)
    ag = round(na - (cl + hco3), 1)
    lactate = round(random.uniform(0.8, 2.0), 1)

    stem_options = [
        "27-year-old presents with reduced consciousness, shallow respirations, and pinpoint pupils.",
        "32-year-old is brought in drowsy with bradypnoea and decreased responsiveness.",
        "40-year-old presents with low GCS and hypoventilation after being found collapsed at home.",
    ]

    explanation = (
        f"Low pH = acidaemia. High PaCO2 indicates a primary respiratory acidosis. "
        f"For acute respiratory acidosis, expected HCO3 is ~{expected_hco3:.1f}; measured {hco3} is appropriate acute compensation. "
        f"This pattern fits acute hypoventilation, such as opioid toxicity."
    )

    case = {
        "case_id": case_id,
        "title": "Opioid toxicity (acute respiratory acidosis)",
        "case_type": "ABG",
        "category": "respiratory_acidosis",
        "learning_objective": "Recognise acute respiratory acidosis due to hypoventilation with appropriate compensation",
        "tags": ["opioid", "respiratory_acidosis", "hypoventilation", "toxicology"],
        "clinical_stem": random.choice(stem_options),
        "inputs": {
            "gas": {"ph": ph, "paco2_mmHg": paco2, "hco3_mmolL": hco3},
            "electrolytes": {"na_mmolL": na, "cl_mmolL": cl},
            "lactate_mmolL": lactate,
        },
        "questions_flow": shuffle_question_options(
            beginner_question_flow([
                "Opioid toxicity",
                "COPD",
                "Pneumonia",
                "Neuromuscular weakness",
                "Sedative overdose",
            ])
        ),
        "answer_key": {
            "ph_status": derived_ph_status(ph),
            "primary_disorder": "Respiratory acidosis",
            "expected_compensation": {
                "rule": "Acute respiratory acidosis",
                "expected_hco3_mmolL": round(expected_hco3, 1),
                "acceptable_range_mmolL": [round(expected_hco3 - 2, 1), round(expected_hco3 + 2, 1)],
            },
            "compensation": "Appropriate",
            "anion_gap_value": ag,
            "anion_gap_category": "Normal" if ag <= 16 else "Raised",
            "final_diagnosis": "Opioid toxicity",
        },
        "explanation": explanation,
        "timing": default_timing(),
    }

    return attach_progression_metadata(case, level=1, archetype="opioid_toxicity")


def generate_copd_case(case_id):
    paco2 = random.randint(55, 75)
    expected_hco3 = chronic_respiratory_acidosis_expected_hco3(paco2)
    hco3 = round(expected_hco3 + random.uniform(-1.0, 1.0), 1)
    ph = estimate_ph(hco3, paco2)
    na = random.randint(136, 142)
    target_ag = random.randint(8, 14)
    cl = na - (hco3 + target_ag)
    ag = round(na - (cl + hco3), 1)
    lactate = round(random.uniform(0.8, 2.0), 1)

    stem_options = [
        "68-year-old smoker presents with worsening dyspnoea, productive cough, and chronic exercise limitation.",
        "72-year-old with longstanding breathlessness presents with increased sputum and fatigue.",
        "65-year-old with chronic respiratory symptoms presents with worsening shortness of breath over several days.",
    ]

    explanation = (
        f"pH is low or near-normal with elevated PaCO2, indicating respiratory acidosis. "
        f"In chronic respiratory acidosis, HCO3 should rise by ~4 mmol/L per 10 mmHg PaCO2 above 40. "
        f"Expected HCO3 is ~{expected_hco3:.1f}; measured {hco3} is appropriately elevated, "
        f"consistent with chronic respiratory compensation seen in COPD."
    )

    case = {
        "case_id": case_id,
        "title": "COPD (chronic respiratory acidosis with metabolic compensation)",
        "case_type": "ABG",
        "category": "respiratory_acidosis",
        "learning_objective": "Recognise chronic respiratory acidosis with appropriate renal compensation",
        "tags": ["copd", "chronic_respiratory_acidosis", "compensation"],
        "clinical_stem": random.choice(stem_options),
        "inputs": {
            "gas": {"ph": ph, "paco2_mmHg": paco2, "hco3_mmolL": hco3},
            "electrolytes": {"na_mmolL": na, "cl_mmolL": cl},
            "lactate_mmolL": lactate,
        },
        "questions_flow": shuffle_question_options(
            intermediate_question_flow([
                "COPD",
                "Opioid toxicity",
                "Neuromuscular weakness",
                "Sedative overdose",
                "Pneumonia",
            ])
        ),
        "answer_key": {
            "ph_status": derived_ph_status(ph),
            "primary_disorder": "Respiratory acidosis",
            "expected_compensation": {
                "rule": "Chronic respiratory acidosis",
                "expected_hco3_mmolL": round(expected_hco3, 1),
                "acceptable_range_mmolL": [round(expected_hco3 - 2, 1), round(expected_hco3 + 2, 1)],
            },
            "compensation": "Appropriate",
            "anion_gap_value": ag,
            "anion_gap_category": "Normal" if ag <= 16 else "Raised",
            "final_diagnosis": "COPD",
        },
        "explanation": explanation,
        "timing": default_timing(),
    }

    return attach_progression_metadata(case, level=2, archetype="copd_chronic_retainer")


def generate_panic_case(case_id):
    paco2 = random.randint(22, 32)
    expected_hco3 = respiratory_alkalosis_expected_hco3_acute(paco2)
    hco3 = round(expected_hco3 + random.uniform(-0.5, 0.5), 1)
    ph = estimate_ph(hco3, paco2)
    na = random.randint(136, 141)
    target_ag = random.randint(8, 14)
    cl = na - (hco3 + target_ag)
    ag = round(na - (cl + hco3), 1)
    lactate = round(random.uniform(0.6, 1.8), 1)

    stem_options = [
        "22-year-old presents with sudden shortness of breath, tingling fingers, and chest tightness during emotional distress.",
        "30-year-old presents with rapid breathing, light-headedness, and perioral tingling after an acute stressful event.",
        "26-year-old presents with acute dyspnoea, dizziness, and hand paraesthesiae with a normal cardiorespiratory examination.",
    ]

    explanation = (
        f"High pH indicates alkalaemia. Low PaCO2 indicates a primary respiratory alkalosis. "
        f"In acute respiratory alkalosis, expected HCO3 is ~{expected_hco3:.1f}; measured {hco3} is appropriate, "
        f"consistent with acute hyperventilation such as panic."
    )

    case = {
        "case_id": case_id,
        "title": "Panic / hyperventilation (acute respiratory alkalosis)",
        "case_type": "ABG",
        "category": "respiratory_alkalosis",
        "learning_objective": "Recognise acute respiratory alkalosis with appropriate metabolic compensation",
        "tags": ["panic", "hyperventilation", "respiratory_alkalosis"],
        "clinical_stem": random.choice(stem_options),
        "inputs": {
            "gas": {"ph": ph, "paco2_mmHg": paco2, "hco3_mmolL": hco3},
            "electrolytes": {"na_mmolL": na, "cl_mmolL": cl},
            "lactate_mmolL": lactate,
        },
        "questions_flow": shuffle_question_options(
            beginner_question_flow([
                "Panic attack / hyperventilation",
                "Pulmonary embolism",
                "COPD",
                "Vomiting",
                "DKA",
            ])
        ),
        "answer_key": {
            "ph_status": derived_ph_status(ph),
            "primary_disorder": "Respiratory alkalosis",
            "expected_compensation": {
                "rule": "Acute respiratory alkalosis",
                "expected_hco3_mmolL": round(expected_hco3, 1),
                "acceptable_range_mmolL": [round(expected_hco3 - 2, 1), round(expected_hco3 + 2, 1)],
            },
            "compensation": "Appropriate",
            "anion_gap_value": ag,
            "anion_gap_category": "Normal" if ag <= 16 else "Raised",
            "final_diagnosis": "Panic attack / hyperventilation",
        },
        "explanation": explanation,
        "timing": default_timing(),
    }

    return attach_progression_metadata(case, level=1, archetype="panic_hyperventilation")


def generate_acute_copd_case(case_id):
    paco2 = random.uniform(70, 90)
    hco3 = random.uniform(32, 38)
    ph = calculate_ph_from_hco3_paco2(hco3, paco2)
    na = random.randint(136, 142)
    cl = random.randint(98, 104)

    case = {
        "case_id": case_id,
        "title": "COPD exacerbation (acute-on-chronic respiratory acidosis)",
        "case_type": "ABG",
        "category": "respiratory_acidosis",
        "clinical_stem": generate_stem("acute_copd_exacerbation"),
        "inputs": {
            "gas": {"ph": ph, "paco2_mmHg": paco2, "hco3_mmolL": hco3},
            "electrolytes": {"na_mmolL": na, "cl_mmolL": cl},
        },
        "questions_flow": shuffle_question_options(
            intermediate_question_flow([
                "COPD exacerbation",
                "Opioid toxicity",
                "Neuromuscular weakness",
                "Asthma",
                "Pneumonia",
            ])
        ),
        "answer_key": {
            "ph_status": derived_ph_status(ph),
            "primary_disorder": "Respiratory acidosis",
            "compensation": "Chronic with acute worsening",
            "anion_gap_value": calc_anion_gap(na, cl, hco3),
            "anion_gap_category": "Normal",
            "final_diagnosis": "COPD exacerbation",
        },
        "explanation": "COPD exacerbations cause acute rises in COâ‚‚ on a background of chronic respiratory acidosis.",
    }

    return attach_progression_metadata(case, level=2, archetype="acute_copd_exacerbation")


def generate_sepsis_case(case_id):
    paco2 = random.uniform(22, 30)
    hco3 = random.uniform(22, 26)
    na = random.randint(136, 142)
    cl = random.randint(100, 106)
    ph = calculate_ph_from_hco3_paco2(hco3, paco2)

    case = {
        "case_id": case_id,
        "title": "Sepsis (respiratory alkalosis)",
        "case_type": "ABG",
        "category": "respiratory_alkalosis",
        "clinical_stem": generate_stem("sepsis_respiratory_alkalosis"),
        "inputs": {
            "gas": {"ph": ph, "paco2_mmHg": paco2, "hco3_mmolL": hco3},
            "electrolytes": {"na_mmolL": na, "cl_mmolL": cl},
        },
        "questions_flow": shuffle_question_options(
            intermediate_question_flow([
                "Sepsis",
                "Panic attack",
                "Pain",
                "Pulmonary embolism",
                "Pregnancy",
            ])
        ),
        "answer_key": {
            "ph_status": derived_ph_status(ph),
            "primary_disorder": "Respiratory alkalosis",
            "compensation": "None",
            "anion_gap_value": calc_anion_gap(na, cl, hco3),
            "anion_gap_category": "Normal",
            "final_diagnosis": "Sepsis",
        },
        "explanation": "Sepsis commonly causes respiratory alkalosis due to hyperventilation.",
    }

    return attach_progression_metadata(case, level=2, archetype="sepsis_respiratory_alkalosis")
