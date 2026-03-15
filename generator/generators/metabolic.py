"""Metabolic ABG archetype generators.

Main functions:
- `generate_dka_case`
- `generate_vomiting_case`
- `generate_diarrhoea_case`
- `generate_lactate_case`

These builders create metabolic disorder cases and attach the expected
question flow, answer key, explanation, and progression metadata.
"""

import random

from ..physiology import (
    calc_anion_gap,
    calculate_ph_from_hco3_paco2,
    derived_ph_status,
    estimate_ph,
    metabolic_alkalosis_expected_paco2,
    winters_expected_paco2,
)
from ..progression import attach_progression_metadata
from ..question_flow import advanced_question_flow, default_timing, intermediate_question_flow, shuffle_question_options
from ..stems import generate_stem


def generate_dka_case(case_id):
    hco3 = random.randint(8, 16)
    expected_paco2 = winters_expected_paco2(hco3)
    paco2 = round(random.uniform(expected_paco2 - 2, expected_paco2 + 2), 1)
    ph = estimate_ph(hco3, paco2)
    na = random.randint(134, 142)
    target_ag = random.randint(22, 30)
    cl = na - (hco3 + target_ag)
    ag = na - (cl + hco3)
    lactate = round(random.uniform(1.0, 2.5), 1)

    explanation = (
        f"Low pH = acidaemia. Low HCO3 indicates metabolic acidosis. "
        f"Winter's formula predicts PaCO2 ~{expected_paco2:.1f} (+/-2); measured {paco2} is appropriate compensation. "
        f"Anion gap is {na} - ({cl} + {hco3}) = {ag} (raised), consistent with HAGMA such as DKA."
    )

    case = {
        "case_id": case_id,
        "title": "DKA (HAGMA with appropriate respiratory compensation)",
        "case_type": "ABG",
        "category": "metabolic_acidosis_hagma",
        "learning_objective": "Recognise high anion gap metabolic acidosis with appropriate respiratory compensation",
        "tags": ["dka", "hagma", "metabolic_acidosis"],
        "clinical_stem": generate_stem("dka"),
        "inputs": {
            "gas": {"ph": ph, "paco2_mmHg": paco2, "hco3_mmolL": hco3},
            "electrolytes": {"na_mmolL": na, "cl_mmolL": cl},
            "lactate_mmolL": lactate,
        },
        "questions_flow": shuffle_question_options(
            advanced_question_flow([
                "DKA",
                "Vomiting metabolic alkalosis",
                "Panic hyperventilation",
                "Salicylate toxicity",
            ])
        ),
        "answer_key": {
            "ph_status": derived_ph_status(ph),
            "primary_disorder": "Metabolic acidosis",
            "expected_compensation": {
                "rule": "Winter",
                "expected_paco2_mmHg": round(expected_paco2, 1),
                "acceptable_range_mmHg": [round(expected_paco2 - 2, 1), round(expected_paco2 + 2, 1)],
            },
            "compensation": "Appropriate",
            "anion_gap_value": ag,
            "anion_gap_category": "Raised",
            "final_diagnosis": "DKA",
        },
        "explanation": explanation,
        "timing": default_timing(),
    }

    return attach_progression_metadata(case, level=3, archetype="dka")


def generate_vomiting_case(case_id):
    hco3 = random.randint(32, 40)
    expected_paco2 = metabolic_alkalosis_expected_paco2(hco3)
    paco2 = round(random.uniform(expected_paco2 - 2, expected_paco2 + 2), 1)
    ph = estimate_ph(hco3, paco2)
    na = random.randint(136, 142)
    target_ag = random.randint(8, 14)
    cl = na - (hco3 + target_ag)
    ag = round(na - (cl + hco3), 1)
    lactate = round(random.uniform(0.8, 1.8), 1)

    stem_options = [
        "24-year-old presents dehydrated and weak after several days of persistent upper gastrointestinal losses.",
        "67-year-old presents with dizziness and volume depletion after recurrent nausea and retching.",
        "35-year-old presents with weakness and dehydration after ongoing gastrointestinal fluid loss.",
    ]

    explanation = (
        f"High pH indicates alkalaemia. Elevated HCO3 indicates a primary metabolic alkalosis. "
        f"Expected compensatory PaCO2 is ~{expected_paco2:.1f}; measured {paco2} is appropriate, "
        f"supporting metabolic alkalosis with expected respiratory compensation, as seen with vomiting."
    )

    case = {
        "case_id": case_id,
        "title": "Vomiting (metabolic alkalosis with respiratory compensation)",
        "case_type": "ABG",
        "category": "metabolic_alkalosis",
        "learning_objective": "Recognise metabolic alkalosis with appropriate respiratory compensation",
        "tags": ["vomiting", "metabolic_alkalosis", "chloride_responsive"],
        "clinical_stem": random.choice(stem_options),
        "inputs": {
            "gas": {"ph": ph, "paco2_mmHg": paco2, "hco3_mmolL": hco3},
            "electrolytes": {"na_mmolL": na, "cl_mmolL": cl},
            "lactate_mmolL": lactate,
        },
        "questions_flow": shuffle_question_options(
            intermediate_question_flow([
                "Vomiting",
                "Diuretic use",
                "COPD",
                "Panic attack",
                "DKA",
            ])
        ),
        "answer_key": {
            "ph_status": derived_ph_status(ph),
            "primary_disorder": "Metabolic alkalosis",
            "expected_compensation": {
                "rule": "Metabolic alkalosis compensation",
                "expected_paco2_mmHg": round(expected_paco2, 1),
                "acceptable_range_mmHg": [round(expected_paco2 - 3, 1), round(expected_paco2 + 3, 1)],
            },
            "compensation": "Appropriate",
            "anion_gap_value": ag,
            "anion_gap_category": "Normal" if ag <= 16 else "Raised",
            "final_diagnosis": "Vomiting",
        },
        "explanation": explanation,
        "timing": default_timing(),
    }

    return attach_progression_metadata(case, level=2, archetype="vomiting_metabolic_alkalosis")


def generate_diarrhoea_case(case_id):
    hco3 = random.randint(12, 20)
    expected_paco2 = winters_expected_paco2(hco3)
    paco2 = round(random.uniform(expected_paco2 - 2, expected_paco2 + 2), 1)
    ph = estimate_ph(hco3, paco2)
    na = random.randint(136, 142)
    target_ag = random.randint(8, 12)
    cl = na - (hco3 + target_ag)
    ag = na - (cl + hco3)
    lactate = round(random.uniform(0.8, 1.8), 1)

    stem_options = [
        "34-year-old presents dehydrated and weak after several days of high-output gastrointestinal losses.",
        "70-year-old from a nursing home presents with volume depletion following ongoing lower gastrointestinal fluid loss.",
        "29-year-old presents with light-headedness and dehydration after several days of gastroenteritis symptoms.",
    ]

    ph_label = derived_ph_status(ph)
    if ph_label == "acidaemia":
        ph_text = "Low pH indicates acidaemia."
    elif ph_label == "alkalaemia":
        ph_text = "High pH indicates alkalaemia."
    else:
        ph_text = "The pH is in the normal range, but the low HCO3 still indicates a primary metabolic acidosis with respiratory compensation."

    explanation = (
        f"{ph_text} Low HCO3 indicates a primary metabolic acidosis. "
        f"Winter's formula predicts PaCO2 ~{expected_paco2:.1f} (+/-2); measured {paco2} is appropriate compensation. "
        f"Anion gap is {na} - ({cl} + {hco3}) = {ag}, which is normal, consistent with NAGMA such as diarrhoea."
    )

    case = {
        "case_id": case_id,
        "title": "Diarrhoea (normal anion gap metabolic acidosis)",
        "case_type": "ABG",
        "category": "metabolic_acidosis_nagma",
        "learning_objective": "Recognise normal anion gap metabolic acidosis with appropriate respiratory compensation",
        "tags": ["diarrhoea", "nagma", "metabolic_acidosis"],
        "clinical_stem": random.choice(stem_options),
        "inputs": {
            "gas": {"ph": ph, "paco2_mmHg": paco2, "hco3_mmolL": hco3},
            "electrolytes": {"na_mmolL": na, "cl_mmolL": cl},
            "lactate_mmolL": lactate,
        },
        "questions_flow": shuffle_question_options(
            advanced_question_flow([
                "Diarrhoea",
                "DKA",
                "Vomiting",
                "Renal failure (uraemia)",
                "Toxic alcohol",
            ])
        ),
        "answer_key": {
            "ph_status": derived_ph_status(ph),
            "primary_disorder": "Metabolic acidosis",
            "expected_compensation": {
                "rule": "Winter",
                "expected_paco2_mmHg": round(expected_paco2, 1),
                "acceptable_range_mmHg": [round(expected_paco2 - 2, 1), round(expected_paco2 + 2, 1)],
            },
            "compensation": "Appropriate",
            "anion_gap_value": ag,
            "anion_gap_category": "Normal",
            "final_diagnosis": "Diarrhoea",
        },
        "explanation": explanation,
        "timing": default_timing(),
    }

    return attach_progression_metadata(case, level=3, archetype="diarrhoea_nagma")


def generate_lactate_case(case_id):
    hco3 = random.uniform(10, 16)
    expected_paco2 = winters_expected_paco2(hco3)
    paco2 = random.uniform(expected_paco2 - 2, expected_paco2 + 2)
    ph = calculate_ph_from_hco3_paco2(hco3, paco2)
    na = random.uniform(138, 144)
    cl = random.uniform(95, 102)
    lactate = random.uniform(4, 10)
    ag = calc_anion_gap(na, cl, hco3)

    case = {
        "case_id": case_id,
        "title": "Lactic acidosis (sepsis)",
        "case_type": "ABG",
        "category": "metabolic_acidosis_hagma",
        "clinical_stem": generate_stem("lactic_acidosis"),
        "inputs": {
            "gas": {"ph": ph, "paco2_mmHg": paco2, "hco3_mmolL": hco3},
            "electrolytes": {"na_mmolL": na, "cl_mmolL": cl},
            "lactate_mmolL": lactate,
        },
        "questions_flow": shuffle_question_options(
            advanced_question_flow([
                "Lactic acidosis",
                "DKA",
                "Renal failure (uraemia)",
                "Toxic alcohol",
                "Salicylate toxicity",
            ])
        ),
        "answer_key": {
            "ph_status": derived_ph_status(ph),
            "primary_disorder": "Metabolic acidosis",
            "expected_compensation": {
                "rule": "Winter",
                "expected_paco2_mmHg": round(expected_paco2, 1),
                "acceptable_range_mmHg": [round(expected_paco2 - 2, 1), round(expected_paco2 + 2, 1)],
            },
            "compensation": "Appropriate",
            "anion_gap_value": ag,
            "anion_gap_category": "Raised",
            "final_diagnosis": "Lactic acidosis",
        },
        "explanation": "Sepsis commonly causes high anion gap metabolic acidosis due to lactate accumulation.",
    }

    return attach_progression_metadata(case, level=3, archetype="lactic_acidosis")
