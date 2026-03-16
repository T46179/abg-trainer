"""Metabolic ABG archetype generators.

Main functions:
- `generate_dka_case`
- `generate_vomiting_case`
- `generate_diarrhoea_case`
- `generate_lactate_case`
- `generate_diuretic_alkalosis_case`
- `generate_uraemia_case`

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
from ..question_flow import advanced_question_flow, default_timing, intermediate_question_flow, shuffle_question_options
from ..stems import generate_stem
from .common import build_answer_key, build_case, build_inputs

DKA_VARIATION_BANDS = [
    {
        "name": "mild",
        "hco3_range": (13, 16),
        "anion_gap_range": (20, 24),
        "lactate_range": (0.9, 1.8),
        "sodium_range": (136, 142),
        "compensation_delta_range": (-1.0, 1.0),
        "stem_feature_range": (2, 3),
    },
    {
        "name": "moderate",
        "hco3_range": (10, 13),
        "anion_gap_range": (24, 28),
        "lactate_range": (1.0, 2.3),
        "sodium_range": (134, 141),
        "compensation_delta_range": (-1.5, 1.5),
        "stem_feature_range": (2, 4),
    },
    {
        "name": "severe",
        "hco3_range": (8, 10),
        "anion_gap_range": (28, 32),
        "lactate_range": (1.4, 2.8),
        "sodium_range": (132, 140),
        "compensation_delta_range": (-1.8, 1.8),
        "stem_feature_range": (3, 4),
    },
]


def generate_dka_case(case_id):
    band = random.choice(DKA_VARIATION_BANDS)
    hco3 = random.randint(*band["hco3_range"])
    expected_paco2 = winters_expected_paco2(hco3)
    compensation_midpoint = expected_paco2 + random.uniform(*band["compensation_delta_range"])
    paco2 = round(random.uniform(compensation_midpoint - 0.4, compensation_midpoint + 0.4), 1)
    ph = estimate_ph(hco3, paco2)
    na = random.randint(*band["sodium_range"])
    target_ag = random.randint(*band["anion_gap_range"])
    cl = na - (hco3 + target_ag)
    ag = na - (cl + hco3)
    lactate = round(random.uniform(*band["lactate_range"]), 1)

    explanation = (
        f"Low pH = acidaemia. Low HCO3 indicates metabolic acidosis. "
        f"Winter's formula predicts PaCO2 ~{expected_paco2:.1f} (+/-2); measured {paco2} is appropriate compensation. "
        f"Anion gap is {na} - ({cl} + {hco3}) = {ag} (raised), consistent with HAGMA such as DKA."
    )

    return build_case(
        case_id=case_id,
        title="DKA (HAGMA with appropriate respiratory compensation)",
        category="metabolic_acidosis_hagma",
        learning_objective="Recognise high anion gap metabolic acidosis with appropriate respiratory compensation",
        tags=["dka", "hagma", "metabolic_acidosis"],
        clinical_stem=generate_stem(
            "dka",
            min_features=band["stem_feature_range"][0],
            max_features=band["stem_feature_range"][1],
        ),
        inputs=build_inputs(ph, paco2, hco3, na, cl, lactate=lactate),
        questions_flow=shuffle_question_options(
            advanced_question_flow([
                "DKA",
                "Vomiting metabolic alkalosis",
                "Panic hyperventilation",
                "Salicylate toxicity",
            ])
        ),
        answer_key=build_answer_key(
            ph_status=derived_ph_status(ph),
            primary_disorder="Metabolic acidosis",
            compensation="Appropriate",
            anion_gap_value=ag,
            anion_gap_category="Raised",
            final_diagnosis="DKA",
            expected_compensation={
                "rule": "Winter",
                "expected_paco2_mmHg": round(expected_paco2, 1),
                "acceptable_range_mmHg": [round(expected_paco2 - 2, 1), round(expected_paco2 + 2, 1)],
            },
        ),
        explanation=explanation,
        timing=default_timing(),
        level=3,
        archetype="dka",
    )


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

    return build_case(
        case_id=case_id,
        title="Vomiting (metabolic alkalosis with respiratory compensation)",
        category="metabolic_alkalosis",
        learning_objective="Recognise metabolic alkalosis with appropriate respiratory compensation",
        tags=["vomiting", "metabolic_alkalosis", "chloride_responsive"],
        clinical_stem=random.choice(stem_options),
        inputs=build_inputs(ph, paco2, hco3, na, cl, lactate=lactate),
        questions_flow=shuffle_question_options(
            intermediate_question_flow([
                "Vomiting",
                "Diuretic use",
                "COPD",
                "Panic attack",
                "DKA",
            ])
        ),
        answer_key=build_answer_key(
            ph_status=derived_ph_status(ph),
            primary_disorder="Metabolic alkalosis",
            compensation="Appropriate",
            anion_gap_value=ag,
            anion_gap_category="Normal" if ag <= 16 else "Raised",
            final_diagnosis="Vomiting",
            expected_compensation={
                "rule": "Metabolic alkalosis compensation",
                "expected_paco2_mmHg": round(expected_paco2, 1),
                "acceptable_range_mmHg": [round(expected_paco2 - 3, 1), round(expected_paco2 + 3, 1)],
            },
        ),
        explanation=explanation,
        timing=default_timing(),
        level=2,
        archetype="vomiting_metabolic_alkalosis",
    )


def generate_diuretic_alkalosis_case(case_id):
    hco3 = random.randint(30, 38)
    expected_paco2 = metabolic_alkalosis_expected_paco2(hco3)
    paco2 = round(random.uniform(expected_paco2 - 2.5, expected_paco2 + 2.5), 1)
    ph = estimate_ph(hco3, paco2)
    na = random.randint(134, 142)
    target_ag = random.randint(8, 14)
    cl = na - (hco3 + target_ag)
    ag = round(na - (cl + hco3), 1)
    lactate = round(random.uniform(0.8, 1.8), 1)

    stem_options = [
        "81-year-old on regular frusemide presents with dizziness, weakness, and poor oral intake after several days of increased diuretic use.",
        "72-year-old with heart failure reports cramps and light-headedness after escalating loop diuretics for ankle swelling.",
        "68-year-old taking loop diuretics presents with postural symptoms, dry mucous membranes, and fatigue after recent volume depletion.",
    ]

    ph_status = derived_ph_status(ph)
    if ph_status == "Alkalaemia":
        ph_text = "High pH indicates alkalaemia."
    elif ph_status == "Acidaemia":
        ph_text = "Low pH is present, but the elevated HCO3 still indicates a primary metabolic alkalosis."
    else:
        ph_text = "The pH is near normal, but the elevated HCO3 still indicates a primary metabolic alkalosis with compensation."

    ag_text = "normal" if ag <= 16 else "raised"
    explanation = (
        f"{ph_text} Elevated HCO3 indicates a primary metabolic alkalosis. "
        f"Expected compensatory PaCO2 is ~{expected_paco2:.1f}; measured {paco2} is appropriate. "
        f"Anion gap is {na} - ({cl} + {hco3}) = {ag}, which is {ag_text}. "
        f"This pattern is most consistent with diuretic-associated contraction alkalosis from diuretic use."
    )

    return build_case(
        case_id=case_id,
        title="Diuretic use (metabolic alkalosis with respiratory compensation)",
        category="metabolic_alkalosis",
        learning_objective="Recognise chloride-responsive metabolic alkalosis from diuretic-associated volume depletion",
        tags=["diuretics", "metabolic_alkalosis", "chloride_responsive"],
        clinical_stem=random.choice(stem_options),
        inputs=build_inputs(ph, paco2, hco3, na, cl, lactate=lactate),
        questions_flow=shuffle_question_options(
            intermediate_question_flow([
                "Diuretic use",
                "Vomiting",
                "COPD",
                "Panic attack",
                "DKA",
            ])
        ),
        answer_key=build_answer_key(
            ph_status=derived_ph_status(ph),
            primary_disorder="Metabolic alkalosis",
            compensation="Appropriate",
            anion_gap_value=ag,
            anion_gap_category="Normal" if ag <= 16 else "Raised",
            final_diagnosis="Diuretic use",
            expected_compensation={
                "rule": "Metabolic alkalosis compensation",
                "expected_paco2_mmHg": round(expected_paco2, 1),
                "acceptable_range_mmHg": [round(expected_paco2 - 3, 1), round(expected_paco2 + 3, 1)],
            },
        ),
        explanation=explanation,
        timing=default_timing(),
        level=2,
        archetype="diuretic_metabolic_alkalosis",
    )


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

    return build_case(
        case_id=case_id,
        title="Diarrhoea (normal anion gap metabolic acidosis)",
        category="metabolic_acidosis_nagma",
        learning_objective="Recognise normal anion gap metabolic acidosis with appropriate respiratory compensation",
        tags=["diarrhoea", "nagma", "metabolic_acidosis"],
        clinical_stem=random.choice(stem_options),
        inputs=build_inputs(ph, paco2, hco3, na, cl, lactate=lactate),
        questions_flow=shuffle_question_options(
            advanced_question_flow([
                "Diarrhoea",
                "DKA",
                "Vomiting",
                "Renal failure (uraemia)",
                "Toxic alcohol",
            ])
        ),
        answer_key=build_answer_key(
            ph_status=derived_ph_status(ph),
            primary_disorder="Metabolic acidosis",
            compensation="Appropriate",
            anion_gap_value=ag,
            anion_gap_category="Normal",
            final_diagnosis="Diarrhoea",
            expected_compensation={
                "rule": "Winter",
                "expected_paco2_mmHg": round(expected_paco2, 1),
                "acceptable_range_mmHg": [round(expected_paco2 - 2, 1), round(expected_paco2 + 2, 1)],
            },
        ),
        explanation=explanation,
        timing=default_timing(),
        level=3,
        archetype="diarrhoea_nagma",
    )


def generate_uraemia_case(case_id):
    hco3 = random.randint(10, 18)
    expected_paco2 = winters_expected_paco2(hco3)
    paco2 = round(random.uniform(expected_paco2 - 2, expected_paco2 + 2), 1)
    ph = estimate_ph(hco3, paco2)
    na = random.randint(132, 140)
    target_ag = random.randint(18, 28)
    cl = na - (hco3 + target_ag)
    ag = round(na - (cl + hco3), 1)
    lactate = round(random.uniform(0.8, 2.2), 1)

    stem_options = [
        "64-year-old on haemodialysis presents lethargic and nauseated after missing recent dialysis sessions.",
        "71-year-old with advanced CKD presents with malaise, reduced urine output, and progressive weakness over several days.",
        "58-year-old with renal failure presents with fluid overload, poor appetite, and increasing drowsiness after worsening oliguria.",
    ]

    ph_status = derived_ph_status(ph)
    if ph_status == "Acidaemia":
        ph_text = "Low pH indicates acidaemia."
    elif ph_status == "Alkalaemia":
        ph_text = "High pH is present, but the markedly low HCO3 still indicates a primary metabolic acidosis."
    else:
        ph_text = "The pH is near normal, but the low HCO3 still indicates a primary metabolic acidosis with compensation."

    explanation = (
        f"{ph_text} Low HCO3 indicates a primary metabolic acidosis. "
        f"Winter's formula predicts PaCO2 ~{expected_paco2:.1f} (+/-2); measured {paco2} is appropriate compensation. "
        f"Anion gap is {na} - ({cl} + {hco3}) = {ag}, which is raised. "
        f"This pattern is most consistent with renal failure causing uraemic high anion gap metabolic acidosis."
    )

    return build_case(
        case_id=case_id,
        title="Renal failure (uraemic HAGMA with appropriate respiratory compensation)",
        category="metabolic_acidosis_hagma",
        learning_objective="Recognise high anion gap metabolic acidosis from uraemia with appropriate respiratory compensation",
        tags=["uraemia", "renal_failure", "hagma", "metabolic_acidosis"],
        clinical_stem=random.choice(stem_options),
        inputs=build_inputs(ph, paco2, hco3, na, cl, lactate=lactate),
        questions_flow=shuffle_question_options(
            advanced_question_flow([
                "Renal failure (uraemia)",
                "DKA",
                "Lactic acidosis",
                "Toxic alcohol",
                "Diarrhoea",
            ])
        ),
        answer_key=build_answer_key(
            ph_status=derived_ph_status(ph),
            primary_disorder="Metabolic acidosis",
            compensation="Appropriate",
            anion_gap_value=ag,
            anion_gap_category="Raised",
            final_diagnosis="Renal failure (uraemia)",
            expected_compensation={
                "rule": "Winter",
                "expected_paco2_mmHg": round(expected_paco2, 1),
                "acceptable_range_mmHg": [round(expected_paco2 - 2, 1), round(expected_paco2 + 2, 1)],
            },
        ),
        explanation=explanation,
        timing=default_timing(),
        level=3,
        archetype="uraemia",
    )


def generate_lactate_case(case_id):
    hco3 = random.uniform(10, 16)
    expected_paco2 = winters_expected_paco2(hco3)
    paco2 = random.uniform(expected_paco2 - 2, expected_paco2 + 2)
    ph = calculate_ph_from_hco3_paco2(hco3, paco2)
    na = random.uniform(138, 144)
    cl = random.uniform(95, 102)
    lactate = random.uniform(4, 10)
    ag = calc_anion_gap(na, cl, hco3)

    return build_case(
        case_id=case_id,
        title="Lactic acidosis (sepsis)",
        category="metabolic_acidosis_hagma",
        clinical_stem=generate_stem("lactic_acidosis"),
        inputs=build_inputs(ph, paco2, hco3, na, cl, lactate=lactate),
        questions_flow=shuffle_question_options(
            advanced_question_flow([
                "Lactic acidosis",
                "DKA",
                "Renal failure (uraemia)",
                "Toxic alcohol",
                "Salicylate toxicity",
            ])
        ),
        answer_key=build_answer_key(
            ph_status=derived_ph_status(ph),
            primary_disorder="Metabolic acidosis",
            compensation="Appropriate",
            anion_gap_value=ag,
            anion_gap_category="Raised",
            final_diagnosis="Lactic acidosis",
            expected_compensation={
                "rule": "Winter",
                "expected_paco2_mmHg": round(expected_paco2, 1),
                "acceptable_range_mmHg": [round(expected_paco2 - 2, 1), round(expected_paco2 + 2, 1)],
            },
        ),
        explanation="Sepsis commonly causes high anion gap metabolic acidosis due to lactate accumulation.",
        level=3,
        archetype="lactic_acidosis",
    )
