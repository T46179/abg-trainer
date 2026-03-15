"""Mixed-disorder ABG archetype generators.

Main functions:
- `generate_salicylate_case`
- `generate_dka_vomiting_case`

These builders cover cases where more than one primary acid-base process is
present and the question flow needs to support mixed-disorder reasoning.
"""

import random

from ..physiology import calc_anion_gap, calculate_ph_from_hco3_paco2, derived_ph_status, estimate_ph
from ..progression import attach_progression_metadata
from ..question_flow import advanced_question_flow, default_timing, expert_question_flow, shuffle_question_options
from ..stems import generate_stem


def generate_salicylate_case(case_id):
    paco2 = random.randint(18, 24)
    hco3 = random.randint(10, 16)
    ph = estimate_ph(hco3, paco2)
    na = random.randint(136, 142)
    target_ag = random.randint(20, 28)
    cl = na - (hco3 + target_ag)
    ag = na - (cl + hco3)
    lactate = round(random.uniform(1.0, 2.5), 1)

    stem_options = [
        "21-year-old presents with tinnitus, vomiting, fever, and rapid breathing after an overdose.",
        "34-year-old presents confused, tachypnoeic, and febrile with ringing in the ears.",
        "27-year-old presents with nausea, hyperventilation, and tinnitus after ingesting a large quantity of tablets.",
    ]

    explanation = (
        f"Both PaCO2 and HCO3 are low. This is not explained by a single primary disorder alone. "
        f"The low PaCO2 indicates a respiratory alkalosis, while the low HCO3 with raised anion gap "
        f"({na} âˆ’ ({cl} + {hco3}) = {ag}) indicates a high anion gap metabolic acidosis. "
        f"This is a mixed respiratory alkalosis and metabolic acidosis, classic for salicylate toxicity."
    )

    case = {
        "case_id": case_id,
        "title": "Salicylate toxicity (mixed respiratory alkalosis + HAGMA)",
        "case_type": "ABG",
        "category": "mixed_disorder",
        "learning_objective": "Recognise the mixed respiratory alkalosis and high anion gap metabolic acidosis of salicylate toxicity",
        "tags": ["salicylate", "mixed_disorder", "respiratory_alkalosis", "hagma", "toxicology"],
        "clinical_stem": random.choice(stem_options),
        "inputs": {
            "gas": {"ph": ph, "paco2_mmHg": paco2, "hco3_mmolL": hco3},
            "electrolytes": {"na_mmolL": na, "cl_mmolL": cl},
            "lactate_mmolL": lactate,
        },
        "questions_flow": shuffle_question_options(
            advanced_question_flow([
                "Salicylate toxicity",
                "DKA",
                "Diarrhoea",
                "Panic attack / hyperventilation",
                "Renal failure (uraemia)",
            ])
        ),
        "answer_key": {
            "ph_status": derived_ph_status(ph),
            "primary_disorder": "Metabolic acidosis",
            "expected_compensation": {
                "rule": "Mixed disorder present",
                "note": "Low PaCO2 and low HCO3 are due to two primary processes: respiratory alkalosis and HAGMA",
            },
            "compensation": "Inappropriate",
            "anion_gap_value": ag,
            "anion_gap_category": "Raised",
            "final_diagnosis": "Salicylate toxicity",
        },
        "explanation": explanation,
        "timing": default_timing(),
    }

    return attach_progression_metadata(case, level=4, archetype="salicylate_toxicity", is_mixed=True)


def generate_dka_vomiting_case(case_id):
    hco3 = random.uniform(12, 18)
    paco2 = random.uniform(30, 40)
    ph = calculate_ph_from_hco3_paco2(hco3, paco2)
    na = random.uniform(138, 144)
    cl = random.uniform(95, 100)
    ag = calc_anion_gap(na, cl, hco3)

    case = {
        "case_id": case_id,
        "title": "DKA with vomiting (mixed metabolic disorder)",
        "case_type": "ABG",
        "category": "mixed_disorder",
        "clinical_stem": generate_stem("dka_vomiting"),
        "inputs": {
            "gas": {"ph": ph, "paco2_mmHg": paco2, "hco3_mmolL": hco3},
            "electrolytes": {"na_mmolL": na, "cl_mmolL": cl},
        },
        "questions_flow": shuffle_question_options(
            expert_question_flow(
                [
                    "DKA with vomiting",
                    "DKA",
                    "Vomiting",
                    "Salicylate toxicity",
                    "Renal failure",
                ],
                include_additional_metabolic_process=True,
            )
        ),
        "answer_key": {
            "ph_status": derived_ph_status(ph),
            "primary_disorder": "Metabolic acidosis",
            "compensation": "Inappropriate",
            "anion_gap_value": ag,
            "anion_gap_category": "Raised",
            "additional_metabolic_process": "Metabolic alkalosis",
            "final_diagnosis": "DKA with vomiting",
        },
    }

    return attach_progression_metadata(case, level=4, archetype="dka_vomiting", is_mixed=True)
