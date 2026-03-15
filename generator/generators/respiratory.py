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
from ..question_flow import beginner_question_flow, default_timing, intermediate_question_flow, shuffle_question_options
from ..stems import generate_stem
from .common import build_answer_key, build_case, build_inputs

ACUTE_COPD_VARIATION_BANDS = [
    {
        "name": "mild",
        "paco2_range": (68, 76),
        "hco3_range": (31, 35),
        "hco3_offset_range": (-1.0, 1.0),
        "sodium_range": (136, 142),
        "chloride_range": (100, 104),
        "stem_feature_range": (2, 3),
    },
    {
        "name": "moderate",
        "paco2_range": (76, 84),
        "hco3_range": (33, 37),
        "hco3_offset_range": (-1.0, 1.5),
        "sodium_range": (136, 142),
        "chloride_range": (98, 103),
        "stem_feature_range": (3, 4),
    },
    {
        "name": "severe",
        "paco2_range": (84, 92),
        "hco3_range": (34, 39),
        "hco3_offset_range": (-0.5, 2.0),
        "sodium_range": (135, 141),
        "chloride_range": (96, 102),
        "stem_feature_range": (3, 4),
    },
]


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

    return build_case(
        case_id=case_id,
        title="Opioid toxicity (acute respiratory acidosis)",
        category="respiratory_acidosis",
        learning_objective="Recognise acute respiratory acidosis due to hypoventilation with appropriate compensation",
        tags=["opioid", "respiratory_acidosis", "hypoventilation", "toxicology"],
        clinical_stem=random.choice(stem_options),
        inputs=build_inputs(ph, paco2, hco3, na, cl, lactate=lactate),
        questions_flow=shuffle_question_options(
            beginner_question_flow([
                "Opioid toxicity",
                "COPD",
                "Pneumonia",
                "Neuromuscular weakness",
                "Sedative overdose",
            ])
        ),
        answer_key=build_answer_key(
            ph_status=derived_ph_status(ph),
            primary_disorder="Respiratory acidosis",
            compensation="Appropriate",
            anion_gap_value=ag,
            anion_gap_category="Normal" if ag <= 16 else "Raised",
            final_diagnosis="Opioid toxicity",
            expected_compensation={
                "rule": "Acute respiratory acidosis",
                "expected_hco3_mmolL": round(expected_hco3, 1),
                "acceptable_range_mmolL": [round(expected_hco3 - 2, 1), round(expected_hco3 + 2, 1)],
            },
        ),
        explanation=explanation,
        timing=default_timing(),
        level=1,
        archetype="opioid_toxicity",
    )


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

    return build_case(
        case_id=case_id,
        title="COPD (chronic respiratory acidosis with metabolic compensation)",
        category="respiratory_acidosis",
        learning_objective="Recognise chronic respiratory acidosis with appropriate renal compensation",
        tags=["copd", "chronic_respiratory_acidosis", "compensation"],
        clinical_stem=random.choice(stem_options),
        inputs=build_inputs(ph, paco2, hco3, na, cl, lactate=lactate),
        questions_flow=shuffle_question_options(
            intermediate_question_flow([
                "COPD",
                "Opioid toxicity",
                "Neuromuscular weakness",
                "Sedative overdose",
                "Pneumonia",
            ])
        ),
        answer_key=build_answer_key(
            ph_status=derived_ph_status(ph),
            primary_disorder="Respiratory acidosis",
            compensation="Appropriate",
            anion_gap_value=ag,
            anion_gap_category="Normal" if ag <= 16 else "Raised",
            final_diagnosis="COPD",
            expected_compensation={
                "rule": "Chronic respiratory acidosis",
                "expected_hco3_mmolL": round(expected_hco3, 1),
                "acceptable_range_mmolL": [round(expected_hco3 - 2, 1), round(expected_hco3 + 2, 1)],
            },
        ),
        explanation=explanation,
        timing=default_timing(),
        level=2,
        archetype="copd_chronic_retainer",
    )


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

    return build_case(
        case_id=case_id,
        title="Panic / hyperventilation (acute respiratory alkalosis)",
        category="respiratory_alkalosis",
        learning_objective="Recognise acute respiratory alkalosis with appropriate metabolic compensation",
        tags=["panic", "hyperventilation", "respiratory_alkalosis"],
        clinical_stem=random.choice(stem_options),
        inputs=build_inputs(ph, paco2, hco3, na, cl, lactate=lactate),
        questions_flow=shuffle_question_options(
            beginner_question_flow([
                "Panic attack / hyperventilation",
                "Pulmonary embolism",
                "COPD",
                "Vomiting",
                "DKA",
            ])
        ),
        answer_key=build_answer_key(
            ph_status=derived_ph_status(ph),
            primary_disorder="Respiratory alkalosis",
            compensation="Appropriate",
            anion_gap_value=ag,
            anion_gap_category="Normal" if ag <= 16 else "Raised",
            final_diagnosis="Panic attack / hyperventilation",
            expected_compensation={
                "rule": "Acute respiratory alkalosis",
                "expected_hco3_mmolL": round(expected_hco3, 1),
                "acceptable_range_mmolL": [round(expected_hco3 - 2, 1), round(expected_hco3 + 2, 1)],
            },
        ),
        explanation=explanation,
        timing=default_timing(),
        level=1,
        archetype="panic_hyperventilation",
    )


def generate_acute_copd_case(case_id):
    band = random.choice(ACUTE_COPD_VARIATION_BANDS)
    paco2 = random.uniform(*band["paco2_range"])
    expected_hco3 = chronic_respiratory_acidosis_expected_hco3(paco2)
    hco3 = round(expected_hco3 + random.uniform(*band["hco3_offset_range"]), 1)
    hco3 = min(max(hco3, band["hco3_range"][0]), band["hco3_range"][1])
    ph = calculate_ph_from_hco3_paco2(hco3, paco2)
    na = random.randint(*band["sodium_range"])
    cl = random.randint(*band["chloride_range"])

    return build_case(
        case_id=case_id,
        title="COPD exacerbation (acute-on-chronic respiratory acidosis)",
        category="respiratory_acidosis",
        clinical_stem=generate_stem(
            "acute_copd_exacerbation",
            min_features=band["stem_feature_range"][0],
            max_features=band["stem_feature_range"][1],
        ),
        inputs=build_inputs(ph, paco2, hco3, na, cl),
        questions_flow=shuffle_question_options(
            intermediate_question_flow([
                "COPD exacerbation",
                "Opioid toxicity",
                "Neuromuscular weakness",
                "Asthma",
                "Pneumonia",
            ])
        ),
        answer_key=build_answer_key(
            ph_status=derived_ph_status(ph),
            primary_disorder="Respiratory acidosis",
            compensation="Chronic with acute worsening",
            anion_gap_value=calc_anion_gap(na, cl, hco3),
            anion_gap_category="Normal",
            final_diagnosis="COPD exacerbation",
        ),
        explanation="COPD exacerbations cause acute rises in CO2 on a background of chronic respiratory acidosis.",
        level=2,
        archetype="acute_copd_exacerbation",
    )


def generate_sepsis_case(case_id):
    paco2 = random.uniform(22, 30)
    hco3 = random.uniform(22, 26)
    na = random.randint(136, 142)
    cl = random.randint(100, 106)
    ph = calculate_ph_from_hco3_paco2(hco3, paco2)

    return build_case(
        case_id=case_id,
        title="Sepsis (respiratory alkalosis)",
        category="respiratory_alkalosis",
        clinical_stem=generate_stem("sepsis_respiratory_alkalosis"),
        inputs=build_inputs(ph, paco2, hco3, na, cl),
        questions_flow=shuffle_question_options(
            intermediate_question_flow([
                "Sepsis",
                "Panic attack",
                "Pain",
                "Pulmonary embolism",
                "Pregnancy",
            ])
        ),
        answer_key=build_answer_key(
            ph_status=derived_ph_status(ph),
            primary_disorder="Respiratory alkalosis",
            compensation="None",
            anion_gap_value=calc_anion_gap(na, cl, hco3),
            anion_gap_category="Normal",
            final_diagnosis="Sepsis",
        ),
        explanation="Sepsis commonly causes respiratory alkalosis due to hyperventilation.",
        level=2,
        archetype="sepsis_respiratory_alkalosis",
    )
