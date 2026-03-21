"""Metabolic ABG archetype generators.

Main functions:
- `generate_simple_nagma_case`
- `generate_simple_metabolic_alkalosis_case`
- `generate_dka_case`
- `generate_alcoholic_ketoacidosis_case`
- `generate_starvation_ketosis_case`
- `generate_toxic_alcohol_case`
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
from ..question_flow import (
    advanced_question_flow,
    beginner_question_flow,
    default_timing,
    intermediate_question_flow,
    shuffle_question_options,
)
from ..stems import generate_stem
from .common import build_answer_key, build_case, build_inputs

SIMPLE_NAGMA_VARIATION_BANDS = [
    {
        "name": "mild",
        "hco3_range": (18, 19),
        "anion_gap_range": (8, 11),
        "chloride_range": (107, 112),
        "sodium_range": (136, 142),
        "lactate_range": (0.8, 1.4),
        "compensation_delta_range": (0.0, 1.2),
        "stem_feature_range": (2, 3),
    },
    {
        "name": "moderate",
        "hco3_range": (16, 18),
        "anion_gap_range": (8, 11),
        "chloride_range": (108, 114),
        "sodium_range": (135, 141),
        "lactate_range": (0.8, 1.5),
        "compensation_delta_range": (-0.3, 1.0),
        "stem_feature_range": (2, 3),
    },
    {
        "name": "clear",
        "hco3_range": (14, 16),
        "anion_gap_range": (8, 12),
        "chloride_range": (109, 116),
        "sodium_range": (134, 140),
        "lactate_range": (0.8, 1.6),
        "compensation_delta_range": (-0.4, 0.8),
        "stem_feature_range": (2, 4),
    },
]

SIMPLE_METABOLIC_ALKALOSIS_VARIATION_BANDS = [
    {
        "name": "mild",
        "hco3_range": (29, 31),
        "anion_gap_range": (8, 11),
        "chloride_range": (96, 101),
        "sodium_range": (136, 142),
        "lactate_range": (0.8, 1.4),
        "compensation_delta_range": (-1.0, 1.0),
        "stem_feature_range": (2, 3),
    },
    {
        "name": "moderate",
        "hco3_range": (31, 33),
        "anion_gap_range": (8, 12),
        "chloride_range": (94, 100),
        "sodium_range": (136, 142),
        "lactate_range": (0.8, 1.5),
        "compensation_delta_range": (-1.0, 1.0),
        "stem_feature_range": (2, 3),
    },
    {
        "name": "clear",
        "hco3_range": (33, 35),
        "anion_gap_range": (8, 12),
        "chloride_range": (92, 99),
        "sodium_range": (135, 141),
        "lactate_range": (0.8, 1.6),
        "compensation_delta_range": (-1.2, 1.2),
        "stem_feature_range": (2, 4),
    },
]

DKA_VARIATION_BANDS = [
    {
        "name": "mild",
        "hco3_range": (13, 16),
        "anion_gap_range": (20, 24),
        "glucose_range": (16.0, 22.0),
        "lactate_range": (0.9, 1.8),
        "sodium_range": (136, 142),
        "compensation_delta_range": (-1.0, 1.0),
        "stem_feature_range": (2, 3),
    },
    {
        "name": "moderate",
        "hco3_range": (10, 13),
        "anion_gap_range": (24, 28),
        "glucose_range": (20.0, 28.0),
        "lactate_range": (1.0, 2.3),
        "sodium_range": (134, 141),
        "compensation_delta_range": (-1.5, 1.5),
        "stem_feature_range": (2, 4),
    },
    {
        "name": "severe",
        "hco3_range": (8, 10),
        "anion_gap_range": (28, 32),
        "glucose_range": (24.0, 34.0),
        "lactate_range": (1.4, 2.8),
        "sodium_range": (132, 140),
        "compensation_delta_range": (-1.8, 1.8),
        "stem_feature_range": (3, 4),
    },
]

ALCOHOLIC_KETOACIDOSIS_VARIATION_BANDS = [
    {
        "name": "mild",
        "hco3_range": (15, 18),
        "anion_gap_range": (18, 24),
        "chloride_range": (92, 100),
        "glucose_range": (4.2, 7.8),
        "lactate_range": (1.5, 3.0),
        "sodium_range": (132, 138),
        "compensation_delta_range": (-1.4, 1.0),
        "stem_feature_range": (2, 3),
    },
    {
        "name": "moderate",
        "hco3_range": (10, 14),
        "anion_gap_range": (22, 30),
        "chloride_range": (88, 98),
        "glucose_range": (4.0, 9.5),
        "lactate_range": (1.5, 3.5),
        "sodium_range": (130, 137),
        "compensation_delta_range": (-1.2, 1.2),
        "stem_feature_range": (3, 4),
    },
    {
        "name": "severe",
        "hco3_range": (6, 10),
        "anion_gap_range": (26, 36),
        "chloride_range": (84, 96),
        "glucose_range": (4.0, 11.0),
        "lactate_range": (1.5, 4.0),
        "sodium_range": (128, 136),
        "compensation_delta_range": (-1.0, 1.0),
        "stem_feature_range": (3, 4),
    },
]

STARVATION_KETOSIS_VARIATION_BANDS = [
    {
        "name": "mild",
        "hco3_range": (17, 20),
        "anion_gap_range": (17, 18),
        "chloride_range": (101, 108),
        "sodium_range": (134, 140),
        "glucose_range": (3.5, 6.0),
        "lactate_range": (0.8, 1.8),
        "potassium_range": (3.4, 4.3),
        "compensation_delta_range": (-1.0, 1.0),
        "stem_feature_range": (2, 3),
    },
    {
        "name": "moderate",
        "hco3_range": (15, 18),
        "anion_gap_range": (17, 21),
        "chloride_range": (98, 106),
        "sodium_range": (132, 140),
        "glucose_range": (3.3, 5.8),
        "lactate_range": (0.8, 2.0),
        "potassium_range": (3.3, 4.2),
        "compensation_delta_range": (-1.2, 1.2),
        "stem_feature_range": (2, 4),
    },
    {
        "name": "severe",
        "hco3_range": (12, 15),
        "anion_gap_range": (18, 24),
        "chloride_range": (95, 103),
        "sodium_range": (132, 138),
        "glucose_range": (3.2, 5.5),
        "lactate_range": (0.8, 2.2),
        "potassium_range": (3.1, 4.1),
        "compensation_delta_range": (-1.3, 1.3),
        "stem_feature_range": (3, 4),
    },
]

TOXIC_ALCOHOL_VARIATION_BANDS = [
    {
        "name": "mild",
        "hco3_range": (12, 16),
        "anion_gap_range": (20, 26),
        "chloride_range": (95, 104),
        "lactate_range": (1.0, 2.8),
        "sodium_range": (136, 144),
        "compensation_delta_range": (-1.2, 1.0),
        "stem_feature_range": (2, 3),
    },
    {
        "name": "moderate",
        "hco3_range": (9, 13),
        "anion_gap_range": (24, 32),
        "chloride_range": (90, 100),
        "lactate_range": (1.0, 3.2),
        "sodium_range": (136, 145),
        "compensation_delta_range": (-1.0, 1.0),
        "stem_feature_range": (3, 4),
    },
    {
        "name": "severe",
        "hco3_range": (5, 9),
        "anion_gap_range": (30, 40),
        "chloride_range": (84, 96),
        "lactate_range": (1.0, 3.5),
        "sodium_range": (136, 146),
        "compensation_delta_range": (-0.8, 0.8),
        "stem_feature_range": (3, 4),
    },
]

DIURETIC_ALKALOSIS_VARIATION_BANDS = [
    {
        "name": "subtle",
        "hco3_range": (30, 32),
        "anion_gap_range": (8, 12),
        "lactate_range": (0.8, 1.4),
        "sodium_range": (136, 142),
        "compensation_delta_range": (-1.0, 1.0),
        "stem_options": [
            "79-year-old on regular frusemide presents with light-headedness and recent poor oral intake after a small increase in diuretic use.",
            "69-year-old taking loop diuretics reports postural dizziness and fatigue after several days of reduced intake.",
            "74-year-old on diuretics presents with cramps and mild volume depletion after recent escalation of therapy for ankle swelling.",
        ],
    },
    {
        "name": "moderate",
        "hco3_range": (32, 35),
        "anion_gap_range": (8, 13),
        "lactate_range": (0.8, 1.6),
        "sodium_range": (134, 141),
        "compensation_delta_range": (-1.5, 1.5),
        "stem_options": [
            "81-year-old on regular frusemide presents with dizziness, weakness, and poor oral intake after several days of increased diuretic use.",
            "72-year-old with heart failure reports cramps and light-headedness after escalating loop diuretics for ankle swelling.",
            "68-year-old taking loop diuretics presents with postural symptoms, dry mucous membranes, and fatigue after recent volume depletion.",
        ],
    },
    {
        "name": "severe",
        "hco3_range": (35, 38),
        "anion_gap_range": (8, 14),
        "lactate_range": (0.8, 1.8),
        "sodium_range": (134, 140),
        "compensation_delta_range": (-2.0, 2.0),
        "stem_options": [
            "76-year-old on high-dose loop diuretics presents markedly volume depleted with weakness and worsening postural symptoms after several days of increased diuresis.",
            "83-year-old with heart failure presents with cramps, lethargy, and dry mucous membranes after recent aggressive diuretic escalation.",
            "71-year-old taking loop diuretics presents with fatigue, dizziness, and clear contraction symptoms after ongoing fluid loss.",
        ],
    },
]

URAEMIA_VARIATION_BANDS = [
    {
        "name": "mild",
        "hco3_range": (15, 18),
        "anion_gap_range": (18, 22),
        "lactate_range": (0.8, 1.6),
        "sodium_range": (136, 140),
        "compensation_delta_range": (-1.0, 1.0),
        "stem_options": [
            "66-year-old on haemodialysis presents with malaise and nausea after missing a recent dialysis session.",
            "72-year-old with advanced CKD presents with reduced appetite and progressive fatigue over several days.",
            "61-year-old with renal impairment presents with weakness and poor intake after worsening uraemic symptoms.",
        ],
    },
    {
        "name": "moderate",
        "hco3_range": (12, 15),
        "anion_gap_range": (22, 26),
        "lactate_range": (0.8, 1.8),
        "sodium_range": (134, 139),
        "compensation_delta_range": (-1.4, 1.4),
        "stem_options": [
            "64-year-old on haemodialysis presents lethargic and nauseated after missing recent dialysis sessions.",
            "71-year-old with advanced CKD presents with malaise, reduced urine output, and progressive weakness over several days.",
            "58-year-old with renal failure presents with poor appetite and increasing drowsiness after worsening oliguria.",
        ],
    },
    {
        "name": "severe",
        "hco3_range": (10, 12),
        "anion_gap_range": (26, 30),
        "lactate_range": (0.8, 2.2),
        "sodium_range": (132, 138),
        "compensation_delta_range": (-1.8, 1.8),
        "stem_options": [
            "59-year-old with renal failure presents with fluid overload, lethargy, and worsening oliguria after missing dialysis.",
            "68-year-old with advanced kidney disease presents drowsy with nausea, reduced urine output, and progressive weakness.",
            "63-year-old with uraemia presents increasingly somnolent with poor intake and signs of volume overload.",
        ],
    },
]


def generate_simple_nagma_case(case_id):
    band = random.choice(SIMPLE_NAGMA_VARIATION_BANDS)

    for _ in range(40):
        hco3 = random.randint(*band["hco3_range"])
        na = random.randint(*band["sodium_range"])
        target_ag = random.randint(*band["anion_gap_range"])
        cl = na - (hco3 + target_ag)
        ag = calc_anion_gap(na, cl, hco3)

        if not (band["chloride_range"][0] <= cl <= band["chloride_range"][1]):
            continue

        expected_paco2 = winters_expected_paco2(hco3)
        compensation_midpoint = expected_paco2 + random.uniform(*band["compensation_delta_range"])
        paco2_low = max(expected_paco2 - 2, compensation_midpoint - 0.8)
        paco2_high = min(expected_paco2 + 2, compensation_midpoint + 0.8)
        paco2 = round(random.uniform(paco2_low, paco2_high), 1)
        ph = estimate_ph(hco3, paco2)

        if ph >= 7.35:
            continue

        break
    else:
        raise ValueError(f"Unable to generate simple NAGMA values for {case_id}")

    lactate = round(random.uniform(*band["lactate_range"]), 1)
    ph_status = derived_ph_status(ph)
    explanation = (
        f"Low pH indicates acidaemia. Low HCO3 indicates a primary metabolic acidosis. "
        f"PaCO2 is reduced in the expected compensatory direction: Winter's formula predicts ~{expected_paco2:.1f} mmHg (+/-2), "
        f"and the measured PaCO2 is {paco2}. "
        f"Anion gap is {na} - ({cl} + {hco3}) = {ag}, which is normal. "
        f"The relatively high chloride fits a hyperchloraemic normal anion gap metabolic acidosis, such as GI bicarbonate loss."
    )
    clinical_stem, patient_gender = generate_stem(
        "simple_nagma",
        min_features=band["stem_feature_range"][0],
        max_features=band["stem_feature_range"][1],
        return_patient_gender=True,
    )

    return build_case(
        case_id=case_id,
        title="Simple normal anion gap metabolic acidosis",
        category="metabolic_acidosis_nagma",
        learning_objective="Recognise a simple bicarbonate-driven metabolic acidosis with a normal anion gap",
        tags=["simple_nagma", "nagma", "metabolic_acidosis", "bicarbonate_loss"],
        clinical_stem=clinical_stem,
        inputs=build_inputs(ph, paco2, hco3, na, cl, lactate=lactate),
        questions_flow=shuffle_question_options(
            beginner_question_flow([
                "GI bicarbonate loss",
                "Vomiting",
                "DKA",
                "Opioid toxicity",
                "Hyperventilation",
            ])
        ),
        answer_key=build_answer_key(
            ph_status=ph_status,
            primary_disorder="Metabolic acidosis",
            compensation="Appropriate",
            anion_gap_value=ag,
            anion_gap_category="Normal",
            final_diagnosis="GI bicarbonate loss",
            expected_compensation={
                "rule": "Winter",
                "expected_paco2_mmHg": round(expected_paco2, 1),
                "acceptable_range_mmHg": [round(expected_paco2 - 2, 1), round(expected_paco2 + 2, 1)],
            },
        ),
        explanation=explanation,
        timing=default_timing(),
        level=1,
        archetype="simple_nagma",
        patient_gender=patient_gender,
    )


def generate_simple_metabolic_alkalosis_case(case_id):
    band = random.choice(SIMPLE_METABOLIC_ALKALOSIS_VARIATION_BANDS)

    for _ in range(40):
        hco3 = random.randint(*band["hco3_range"])
        na = random.randint(*band["sodium_range"])
        target_ag = random.randint(*band["anion_gap_range"])
        cl = na - (hco3 + target_ag)
        ag = calc_anion_gap(na, cl, hco3)

        if not (band["chloride_range"][0] <= cl <= band["chloride_range"][1]):
            continue

        expected_paco2 = metabolic_alkalosis_expected_paco2(hco3)
        compensation_midpoint = expected_paco2 + random.uniform(*band["compensation_delta_range"])
        paco2 = round(random.uniform(compensation_midpoint - 0.8, compensation_midpoint + 0.8), 1)
        ph = estimate_ph(hco3, paco2)

        if ph <= 7.45:
            continue

        break
    else:
        raise ValueError(f"Unable to generate simple metabolic alkalosis values for {case_id}")

    lactate = round(random.uniform(*band["lactate_range"]), 1)
    explanation = (
        f"High pH indicates alkalaemia. Elevated HCO3 indicates a primary metabolic alkalosis. "
        f"PaCO2 is in the expected compensatory direction: metabolic alkalosis compensation predicts ~{expected_paco2:.1f} mmHg, "
        f"and the measured PaCO2 is {paco2}. "
        f"Anion gap is {na} - ({cl} + {hco3}) = {ag}, which is normal. "
        f"The low chloride and clinical context fit chloride-responsive metabolic alkalosis from gastric losses."
    )
    clinical_stem, patient_gender = generate_stem(
        "simple_metabolic_alkalosis",
        min_features=band["stem_feature_range"][0],
        max_features=band["stem_feature_range"][1],
        return_patient_gender=True,
    )

    return build_case(
        case_id=case_id,
        title="Simple metabolic alkalosis",
        category="metabolic_alkalosis",
        learning_objective="Recognise a simple metabolic alkalosis pattern with elevated bicarbonate and compensatory CO2 retention",
        tags=["simple_metabolic_alkalosis", "metabolic_alkalosis", "gastric_losses", "chloride_responsive"],
        clinical_stem=clinical_stem,
        inputs=build_inputs(ph, paco2, hco3, na, cl, lactate=lactate),
        questions_flow=shuffle_question_options(
            beginner_question_flow([
                "Gastric losses",
                "GI bicarbonate loss",
                "DKA",
                "Hyperventilation",
                "Opioid toxicity",
            ])
        ),
        answer_key=build_answer_key(
            ph_status=derived_ph_status(ph),
            primary_disorder="Metabolic alkalosis",
            compensation="Appropriate",
            anion_gap_value=ag,
            anion_gap_category="Normal" if ag <= 16 else "Raised",
            final_diagnosis="Gastric losses",
            expected_compensation={
                "rule": "Metabolic alkalosis compensation",
                "expected_paco2_mmHg": round(expected_paco2, 1),
                "acceptable_range_mmHg": [round(expected_paco2 - 3, 1), round(expected_paco2 + 3, 1)],
            },
        ),
        explanation=explanation,
        timing=default_timing(),
        level=1,
        archetype="simple_metabolic_alkalosis",
        patient_gender=patient_gender,
    )


def generate_starvation_ketosis_case(case_id):
    band = random.choice(STARVATION_KETOSIS_VARIATION_BANDS)

    for _ in range(40):
        hco3 = random.randint(*band["hco3_range"])
        na = random.randint(*band["sodium_range"])
        target_ag = random.randint(*band["anion_gap_range"])
        cl = na - (hco3 + target_ag)
        ag = calc_anion_gap(na, cl, hco3)

        if not (band["chloride_range"][0] <= cl <= band["chloride_range"][1]):
            continue

        expected_paco2 = winters_expected_paco2(hco3)
        compensation_midpoint = expected_paco2 + random.uniform(*band["compensation_delta_range"])
        paco2_low = max(expected_paco2 - 2, compensation_midpoint - 0.8)
        paco2_high = min(expected_paco2 + 2, compensation_midpoint + 0.8)
        paco2 = round(random.uniform(paco2_low, paco2_high), 1)
        ph = estimate_ph(hco3, paco2)

        if ph >= 7.34 and hco3 > 19:
            continue

        break
    else:
        raise ValueError(f"Unable to generate starvation ketosis values for {case_id}")
    glucose = round(random.uniform(*band["glucose_range"]), 1)
    lactate = None
    k = None

    if random.random() < 0.45:
        lactate = round(random.uniform(*band["lactate_range"]), 1)

    if random.random() < 0.4:
        k = round(random.uniform(*band["potassium_range"]), 1)

    ph_status = derived_ph_status(ph)
    if ph_status == "Acidaemia":
        ph_text = "Low pH indicates acidaemia."
    elif ph_status == "Normal":
        ph_text = "The pH is near normal, but the low HCO3 still indicates a primary metabolic acidosis with compensation."
    else:
        ph_text = "High pH is unusual here, but the low HCO3 still indicates a primary metabolic acidosis."

    lactate_text = ""
    if lactate is not None:
        lactate_text = (
            f" Lactate is {lactate}, which is absent or only mildly elevated and does not dominate the picture."
        )

    explanation = (
        f"{ph_text} Low HCO3 indicates a primary metabolic acidosis. "
        f"Winter's formula predicts PaCO2 ~{expected_paco2:.1f} (+/-2); measured {paco2} is appropriate compensation. "
        f"Anion gap is {na} - ({cl} + {hco3}) = {ag}, which is raised. "
        f"This is a relatively mild high anion gap metabolic acidosis in the setting of poor intake or fasting. "
        f"Glucose is {glucose} mmol/L rather than markedly elevated, which helps distinguish this from DKA, "
        f"and the stem lacks alcohol-related context that would suggest alcoholic ketoacidosis.{lactate_text}"
    )
    clinical_stem, patient_gender = generate_stem(
        "starvation_ketosis",
        min_features=band["stem_feature_range"][0],
        max_features=band["stem_feature_range"][1],
        return_patient_gender=True,
    )

    return build_case(
        case_id=case_id,
        title="Starvation ketosis (subtle HAGMA with appropriate respiratory compensation)",
        category="metabolic_acidosis_hagma",
        learning_objective="Recognise starvation ketosis as a subtle high anion gap metabolic acidosis with appropriate respiratory compensation and normal-range glucose",
        tags=["starvation_ketosis", "hagma", "metabolic_acidosis"],
        clinical_stem=clinical_stem,
        inputs=build_inputs(
            ph,
            paco2,
            hco3,
            na,
            cl,
            lactate=lactate,
            k=k,
            glucose=glucose,
        ),
        questions_flow=shuffle_question_options(
            advanced_question_flow([
                "Starvation ketosis",
                "Alcoholic ketoacidosis",
                "DKA",
                "Lactic acidosis",
                "Renal failure (uraemia)",
            ])
        ),
        answer_key=build_answer_key(
            ph_status=ph_status,
            primary_disorder="Metabolic acidosis",
            compensation="Appropriate",
            anion_gap_value=ag,
            anion_gap_category="Raised",
            final_diagnosis="Starvation ketosis",
            expected_compensation={
                "rule": "Winter",
                "expected_paco2_mmHg": round(expected_paco2, 1),
                "acceptable_range_mmHg": [round(expected_paco2 - 2, 1), round(expected_paco2 + 2, 1)],
            },
        ),
        explanation=explanation,
        timing=default_timing(),
        level=3,
        archetype="starvation_ketosis",
        patient_gender=patient_gender,
    )


def generate_alcoholic_ketoacidosis_case(case_id):
    band = random.choice(ALCOHOLIC_KETOACIDOSIS_VARIATION_BANDS)

    for _ in range(40):
        hco3 = random.randint(*band["hco3_range"])
        na = random.randint(*band["sodium_range"])
        cl = random.randint(*band["chloride_range"])
        ag = calc_anion_gap(na, cl, hco3)

        if band["anion_gap_range"][0] <= ag <= band["anion_gap_range"][1]:
            break
    else:
        raise ValueError(f"Unable to generate alcoholic ketoacidosis values for {case_id}")

    expected_paco2 = winters_expected_paco2(hco3)
    compensation_midpoint = expected_paco2 + random.uniform(*band["compensation_delta_range"])
    paco2_low = max(expected_paco2 - 2, compensation_midpoint - 0.8)
    paco2_high = min(expected_paco2 + 2, compensation_midpoint + 0.8)
    paco2 = round(random.uniform(paco2_low, paco2_high), 1)
    ph = estimate_ph(hco3, paco2)
    glucose = round(random.uniform(*band["glucose_range"]), 1)
    lactate = None

    if random.random() < 0.65:
        lactate = round(random.uniform(*band["lactate_range"]), 1)

    ph_status = derived_ph_status(ph)
    if ph_status == "Acidaemia":
        ph_text = "Low pH indicates acidaemia."
    elif ph_status == "Normal":
        ph_text = "The pH is near normal, but the low HCO3 still indicates a primary metabolic acidosis with compensation."
    else:
        ph_text = "High pH is unusual here, but the low HCO3 still indicates a primary metabolic acidosis."

    lactate_text = ""
    if lactate is not None:
        lactate_text = f" Lactate is {lactate}, which is not high enough to make this read as isolated lactic acidosis."

    explanation = (
        f"{ph_text} Low HCO3 indicates a primary high anion gap metabolic acidosis. "
        f"Winter's formula predicts PaCO2 ~{expected_paco2:.1f} (+/-2); measured {paco2} is appropriate compensation. "
        f"Anion gap is {na} - ({cl} + {hco3}) = {ag}, which is raised. "
        f"The clinical context fits alcoholic ketoacidosis, which commonly follows heavy alcohol use with poor intake and can occur without marked hyperglycaemia.{lactate_text}"
    )
    clinical_stem, patient_gender = generate_stem(
        "alcoholic_ketoacidosis",
        min_features=band["stem_feature_range"][0],
        max_features=band["stem_feature_range"][1],
        return_patient_gender=True,
    )

    return build_case(
        case_id=case_id,
        title="Alcoholic ketoacidosis (HAGMA with appropriate respiratory compensation)",
        category="metabolic_acidosis_hagma",
        learning_objective="Recognise alcoholic ketoacidosis as a high anion gap metabolic acidosis with appropriate respiratory compensation",
        tags=["alcoholic_ketoacidosis", "hagma", "metabolic_acidosis"],
        clinical_stem=clinical_stem,
        inputs=build_inputs(ph, paco2, hco3, na, cl, lactate=lactate, glucose=glucose),
        questions_flow=shuffle_question_options(
            advanced_question_flow([
                "Alcoholic ketoacidosis",
                "DKA",
                "Lactic acidosis",
                "Renal failure (uraemia)",
                "Toxic alcohol",
            ])
        ),
        answer_key=build_answer_key(
            ph_status=ph_status,
            primary_disorder="Metabolic acidosis",
            compensation="Appropriate",
            anion_gap_value=ag,
            anion_gap_category="Raised",
            final_diagnosis="Alcoholic ketoacidosis",
            expected_compensation={
                "rule": "Winter",
                "expected_paco2_mmHg": round(expected_paco2, 1),
                "acceptable_range_mmHg": [round(expected_paco2 - 2, 1), round(expected_paco2 + 2, 1)],
            },
        ),
        explanation=explanation,
        timing=default_timing(),
        level=3,
        archetype="alcoholic_ketoacidosis",
        patient_gender=patient_gender,
    )


def generate_toxic_alcohol_case(case_id):
    band = random.choice(TOXIC_ALCOHOL_VARIATION_BANDS)

    for _ in range(40):
        hco3 = random.randint(*band["hco3_range"])
        na = random.randint(*band["sodium_range"])
        cl = random.randint(*band["chloride_range"])
        ag = calc_anion_gap(na, cl, hco3)

        if band["anion_gap_range"][0] <= ag <= band["anion_gap_range"][1]:
            break
    else:
        raise ValueError(f"Unable to generate toxic alcohol values for {case_id}")

    expected_paco2 = winters_expected_paco2(hco3)
    compensation_midpoint = expected_paco2 + random.uniform(*band["compensation_delta_range"])
    paco2_low = max(expected_paco2 - 2, compensation_midpoint - 0.8)
    paco2_high = min(expected_paco2 + 2, compensation_midpoint + 0.8)
    paco2 = round(random.uniform(paco2_low, paco2_high), 1)
    ph = estimate_ph(hco3, paco2)
    lactate = None

    if random.random() < 0.45:
        lactate = round(random.uniform(*band["lactate_range"]), 1)

    ph_status = derived_ph_status(ph)
    if ph_status == "Acidaemia":
        ph_text = "Low pH indicates acidaemia."
    elif ph_status == "Normal":
        ph_text = "The pH is near normal, but the very low HCO3 still indicates a primary metabolic acidosis with compensation."
    else:
        ph_text = "High pH is unusual here, but the low HCO3 still indicates a primary metabolic acidosis."

    lactate_text = ""
    if lactate is not None:
        lactate_text = (
            f" Lactate is {lactate}, which is only mildly elevated and does not fully explain this degree of acidosis."
        )

    explanation = (
        f"{ph_text} Low HCO3 indicates a primary high anion gap metabolic acidosis. "
        f"Winter's formula predicts PaCO2 ~{expected_paco2:.1f} (+/-2); measured {paco2} is appropriate compensation. "
        f"Anion gap is {na} - ({cl} + {hco3}) = {ag}, which is raised. "
        f"The clinical context is concerning for toxic alcohol ingestion, which can cause severe high anion gap metabolic acidosis even without marked lactate elevation.{lactate_text}"
    )
    clinical_stem, patient_gender = generate_stem(
        "toxic_alcohol",
        min_features=band["stem_feature_range"][0],
        max_features=band["stem_feature_range"][1],
        return_patient_gender=True,
    )

    return build_case(
        case_id=case_id,
        title="Toxic alcohol (HAGMA with appropriate respiratory compensation)",
        category="metabolic_acidosis_hagma",
        learning_objective="Recognise toxic alcohol ingestion as a high anion gap metabolic acidosis with appropriate respiratory compensation",
        tags=["toxic_alcohol", "hagma", "metabolic_acidosis"],
        clinical_stem=clinical_stem,
        inputs=build_inputs(ph, paco2, hco3, na, cl, lactate=lactate),
        questions_flow=shuffle_question_options(
            advanced_question_flow([
                "Toxic alcohol",
                "Alcoholic ketoacidosis",
                "DKA",
                "Lactic acidosis",
                "Renal failure (uraemia)",
            ])
        ),
        answer_key=build_answer_key(
            ph_status=ph_status,
            primary_disorder="Metabolic acidosis",
            compensation="Appropriate",
            anion_gap_value=ag,
            anion_gap_category="Raised",
            final_diagnosis="Toxic alcohol",
            expected_compensation={
                "rule": "Winter",
                "expected_paco2_mmHg": round(expected_paco2, 1),
                "acceptable_range_mmHg": [round(expected_paco2 - 2, 1), round(expected_paco2 + 2, 1)],
            },
        ),
        explanation=explanation,
        timing=default_timing(),
        level=3,
        archetype="toxic_alcohol",
        patient_gender=patient_gender,
    )


def generate_dka_case(case_id):
    band = random.choice(DKA_VARIATION_BANDS)
    hco3 = random.randint(*band["hco3_range"])
    expected_paco2 = winters_expected_paco2(hco3)
    compensation_midpoint = expected_paco2 + random.uniform(*band["compensation_delta_range"])
    paco2 = round(random.uniform(compensation_midpoint - 0.8, compensation_midpoint + 0.8), 1)
    ph = estimate_ph(hco3, paco2)
    na = random.randint(*band["sodium_range"])
    target_ag = random.randint(*band["anion_gap_range"])
    cl = na - (hco3 + target_ag)
    ag = calc_anion_gap(na, cl, hco3)
    glucose = round(random.uniform(*band["glucose_range"]), 1)
    lactate = round(random.uniform(*band["lactate_range"]), 1)

    explanation = (
        f"Low pH = acidaemia. Low HCO3 indicates metabolic acidosis. "
        f"Winter's formula predicts PaCO2 ~{expected_paco2:.1f} (+/-2); measured {paco2} is appropriate compensation. "
        f"Anion gap is {na} - ({cl} + {hco3}) = {ag} (raised), consistent with HAGMA such as DKA."
    )
    clinical_stem, patient_gender = generate_stem(
        "dka",
        min_features=band["stem_feature_range"][0],
        max_features=band["stem_feature_range"][1],
        return_patient_gender=True,
    )

    return build_case(
        case_id=case_id,
        title="DKA (HAGMA with appropriate respiratory compensation)",
        category="metabolic_acidosis_hagma",
        learning_objective="Recognise high anion gap metabolic acidosis with appropriate respiratory compensation",
        tags=["dka", "hagma", "metabolic_acidosis"],
        clinical_stem=clinical_stem,
        inputs=build_inputs(ph, paco2, hco3, na, cl, lactate=lactate, glucose=glucose),
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
        patient_gender=patient_gender,
    )


def generate_vomiting_case(case_id):
    hco3 = random.randint(32, 40)
    expected_paco2 = metabolic_alkalosis_expected_paco2(hco3)
    paco2 = round(random.uniform(expected_paco2 - 2, expected_paco2 + 2), 1)
    ph = estimate_ph(hco3, paco2)
    na = random.randint(136, 142)
    target_ag = random.randint(8, 14)
    cl = na - (hco3 + target_ag)
    ag = calc_anion_gap(na, cl, hco3)
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
    band = random.choice(DIURETIC_ALKALOSIS_VARIATION_BANDS)
    hco3 = random.randint(*band["hco3_range"])
    expected_paco2 = metabolic_alkalosis_expected_paco2(hco3)
    compensation_midpoint = expected_paco2 + random.uniform(*band["compensation_delta_range"])
    paco2 = round(random.uniform(compensation_midpoint - 0.8, compensation_midpoint + 0.8), 1)
    ph = estimate_ph(hco3, paco2)
    na = random.randint(*band["sodium_range"])
    target_ag = random.randint(*band["anion_gap_range"])
    cl = na - (hco3 + target_ag)
    ag = calc_anion_gap(na, cl, hco3)
    lactate = round(random.uniform(*band["lactate_range"]), 1)

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
        clinical_stem=random.choice(band["stem_options"]),
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
    ag = calc_anion_gap(na, cl, hco3)
    lactate = round(random.uniform(0.8, 1.8), 1)

    stem_options = [
        "34-year-old presents dehydrated and weak after several days of high-output gastrointestinal losses.",
        "70-year-old from a nursing home presents with volume depletion following ongoing lower gastrointestinal fluid loss.",
        "29-year-old presents with light-headedness and dehydration after several days of gastroenteritis symptoms.",
    ]

    ph_label = derived_ph_status(ph)
    if ph_label == "Acidaemia":
        ph_text = "Low pH indicates acidaemia."
    elif ph_label == "Alkalaemia":
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
    band = random.choice(URAEMIA_VARIATION_BANDS)
    hco3 = random.randint(*band["hco3_range"])
    expected_paco2 = winters_expected_paco2(hco3)
    compensation_midpoint = expected_paco2 + random.uniform(*band["compensation_delta_range"])
    paco2 = round(random.uniform(compensation_midpoint - 0.8, compensation_midpoint + 0.8), 1)
    ph = estimate_ph(hco3, paco2)
    na = random.randint(*band["sodium_range"])
    target_ag = random.randint(*band["anion_gap_range"])
    cl = na - (hco3 + target_ag)
    ag = calc_anion_gap(na, cl, hco3)
    lactate = round(random.uniform(*band["lactate_range"]), 1)

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
        clinical_stem=random.choice(band["stem_options"]),
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
    clinical_stem, patient_gender = generate_stem("lactic_acidosis", return_patient_gender=True)
    inputs = build_inputs(ph, paco2, hco3, na, cl, lactate=lactate)
    gas = inputs["gas"]
    electrolytes = inputs["electrolytes"]
    lactate_value = inputs["other"]["lactate_mmolL"]
    displayed_expected_paco2 = round(winters_expected_paco2(gas["hco3_mmolL"]), 1)
    ag = calc_anion_gap(electrolytes["na_mmolL"], electrolytes["cl_mmolL"], gas["hco3_mmolL"])
    ph_status = derived_ph_status(gas["ph"])

    if ph_status == "Acidaemia":
        ph_text = f"pH is {gas['ph']}, so there is acidaemia."
    elif ph_status == "Alkalaemia":
        ph_text = f"pH is {gas['ph']}, so there is alkalaemia overall."
    else:
        ph_text = f"pH is {gas['ph']}, so the overall pH is near normal."

    explanation = (
        f"1. {ph_text} "
        f"2. HCO3 is {gas['hco3_mmolL']} mmol/L, which is low and indicates a primary metabolic acidosis. "
        f"3. For this metabolic acidosis, Winter's formula predicts a PaCO2 of about {displayed_expected_paco2} mmHg "
        f"(acceptable range {round(displayed_expected_paco2 - 2, 1)}-{round(displayed_expected_paco2 + 2, 1)}), "
        f"and the measured PaCO2 is {gas['paco2_mmHg']} mmHg, so the respiratory compensation is appropriate. "
        f"4. The anion gap is {electrolytes['na_mmolL']} - ({electrolytes['cl_mmolL']} + {gas['hco3_mmolL']}) = {ag}, which is raised. "
        f"5. Lactate is {lactate_value} mmol/L, which materially supports lactic acidosis, and the septic clinical context makes sepsis-related lactic acidosis the best fit."
    )

    return build_case(
        case_id=case_id,
        title="Lactic acidosis (sepsis)",
        category="metabolic_acidosis_hagma",
        clinical_stem=clinical_stem,
        inputs=inputs,
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
            ph_status=ph_status,
            primary_disorder="Metabolic acidosis",
            compensation="Appropriate",
            anion_gap_value=ag,
            anion_gap_category="Raised",
            final_diagnosis="Lactic acidosis",
            expected_compensation={
                "rule": "Winter",
                "expected_paco2_mmHg": displayed_expected_paco2,
                "acceptable_range_mmHg": [round(displayed_expected_paco2 - 2, 1), round(displayed_expected_paco2 + 2, 1)],
            },
        ),
        explanation=explanation,
        level=3,
        archetype="lactic_acidosis",
        patient_gender=patient_gender,
    )
