"""Mixed-disorder ABG archetype generators.

Main functions:
- `generate_salicylate_case`
- `generate_dka_vomiting_case`
- `generate_mixed_hagma_metabolic_alkalosis_case`

These builders cover cases where more than one primary acid-base process is
present and the question flow needs to support mixed-disorder reasoning.
"""

import random

from ..physiology import calc_anion_gap, calculate_ph_from_hco3_paco2, derived_ph_status, estimate_ph, winters_expected_paco2
from ..question_flow import advanced_question_flow, default_timing, expert_question_flow, shuffle_question_options
from ..stems import generate_stem
from .common import build_answer_key, build_case, build_inputs


MIXED_HAGMA_METABOLIC_ALKALOSIS_VARIATION_BANDS = [
    {
        "name": "obvious_mix",
        "anion_gap_range": (20, 24),
        "alkalosis_offset_range": (8, 11),
        "sodium_range": (136, 142),
        "chloride_range": (90, 96),
        "paco2_delta_range": (-0.8, 0.8),
        "ph_range": (7.34, 7.40),
        "alkalosis_signal_min": 5,
        "mild_lactate_range": (1.0, 1.8),
        "moderate_lactate_range": (3.0, 4.2),
        "moderate_lactate_probability": 0.2,
        "stem_options": [
            "31-year-old presents with persistent vomiting, postural dizziness, and dry mucous membranes after several days of gastroenteritis.",
            "42-year-old attends ED after alcohol-related illness with repeated emesis, limited intake, and increasing light-headedness.",
            "27-year-old is reviewed with ongoing nasogastric losses, abdominal discomfort, and worsening fatigue after surgery.",
            "36-year-old presents with prolonged vomiting and weakness during a febrile illness with poor oral tolerance.",
        ],
        "explanation_emphasis": "The bicarbonate is relatively preserved for the size of the anion gap rise, making the second metabolic process more obvious.",
    },
    {
        "name": "subtle_mix",
        "anion_gap_range": (24, 30),
        "alkalosis_offset_range": (8, 11),
        "sodium_range": (136, 143),
        "chloride_range": (90, 96),
        "paco2_delta_range": (-0.8, 0.8),
        "ph_range": (7.30, 7.36),
        "alkalosis_signal_min": 3,
        "mild_lactate_range": (1.1, 2.0),
        "moderate_lactate_range": (3.2, 5.0),
        "moderate_lactate_probability": 0.35,
        "stem_options": [
            "35-year-old presents with reduced intake, intermittent vomiting, and increasing fatigue during a prolonged febrile illness.",
            "46-year-old attends ED with abdominal discomfort, recent emesis, and fever after several days of presumed infection.",
            "29-year-old presents with metabolic stress, nausea, and repeated vomiting without tolerating much oral intake.",
            "38-year-old is reviewed after several days of alcohol-related vomiting and weakness with poor nutrition.",
        ],
        "explanation_emphasis": "The mixed picture is more subtle here because the bicarbonate is still low, but it is not low enough for an isolated HAGMA of this size.",
    },
    {
        "name": "near_normal_ph_trap",
        "anion_gap_range": (22, 27),
        "alkalosis_offset_range": (10, 13),
        "sodium_range": (136, 142),
        "chloride_range": (88, 96),
        "paco2_delta_range": (-0.7, 0.7),
        "ph_range": (7.35, 7.40),
        "alkalosis_signal_min": 5,
        "mild_lactate_range": (1.0, 1.9),
        "moderate_lactate_range": (3.0, 4.6),
        "moderate_lactate_probability": 0.25,
        "stem_options": [
            "51-year-old presents with postural light-headedness, persistent retching, and poor intake after several days of acute illness.",
            "33-year-old attends ED with ongoing emesis and weakness during metabolic stress after missing usual intake for several days.",
            "44-year-old is reviewed with nasogastric losses, fatigue, and intermittent fever in the post-operative period.",
            "40-year-old presents with recurrent vomiting and reduced intake during a prolonged systemic illness with increasing lethargy.",
        ],
        "explanation_emphasis": "The near-normal pH is a trap: the numbers still do not fit a single disorder because the bicarbonate is too high for the raised anion gap.",
    },
]


def generate_salicylate_case(case_id):
    paco2 = random.randint(18, 24)
    hco3 = random.randint(10, 16)
    ph = estimate_ph(hco3, paco2)
    na = random.randint(136, 142)
    target_ag = random.randint(20, 28)
    cl = na - (hco3 + target_ag)
    ag = calc_anion_gap(na, cl, hco3)
    lactate = round(random.uniform(1.0, 2.5), 1)

    stem_options = [
        "21-year-old presents with tinnitus, vomiting, fever, and rapid breathing after an overdose.",
        "34-year-old presents confused, tachypnoeic, and febrile with ringing in the ears.",
        "27-year-old presents with nausea, hyperventilation, and tinnitus after ingesting a large quantity of tablets.",
    ]

    explanation = (
        f"Both PaCO2 and HCO3 are low. This is not explained by a single primary disorder alone. "
        f"The low PaCO2 indicates a respiratory alkalosis, while the low HCO3 with raised anion gap "
        f"({ag:.1f}) indicates a high anion gap metabolic acidosis. "
        f"This is a mixed respiratory alkalosis and metabolic acidosis, classic for salicylate toxicity."
    )

    return build_case(
        case_id=case_id,
        title="Salicylate toxicity (mixed respiratory alkalosis + HAGMA)",
        category="mixed_disorder",
        learning_objective="Recognise the mixed respiratory alkalosis and high anion gap metabolic acidosis of salicylate toxicity",
        tags=["salicylate", "mixed_disorder", "respiratory_alkalosis", "hagma", "toxicology"],
        clinical_stem=random.choice(stem_options),
        inputs=build_inputs(ph, paco2, hco3, na, cl, lactate=lactate),
        questions_flow=shuffle_question_options(
            advanced_question_flow([
                "Salicylate toxicity",
                "DKA",
                "Diarrhoea",
                "Panic attack / hyperventilation",
                "Renal failure (uraemia)",
            ])
        ),
        answer_key=build_answer_key(
            ph_status=derived_ph_status(ph),
            primary_disorder="Metabolic acidosis",
            compensation="Inappropriate",
            anion_gap_value=ag,
            anion_gap_category="Raised",
            final_diagnosis="Salicylate toxicity",
            expected_compensation={
                "rule": "Mixed disorder present",
                "note": "Low PaCO2 and low HCO3 are due to two primary processes: respiratory alkalosis and HAGMA",
            },
        ),
        explanation=explanation,
        timing=default_timing(),
        level=4,
        archetype="salicylate_toxicity",
        is_mixed=True,
    )


def generate_dka_vomiting_case(case_id):
    hco3 = random.uniform(12, 18)
    paco2 = random.uniform(30, 40)
    ph = calculate_ph_from_hco3_paco2(hco3, paco2)
    na = random.uniform(138, 144)
    cl = random.uniform(95, 100)
    ag = calc_anion_gap(na, cl, hco3)
    clinical_stem, patient_gender = generate_stem("dka_vomiting", return_patient_gender=True)

    return build_case(
        case_id=case_id,
        title="DKA with vomiting (mixed metabolic disorder)",
        category="mixed_disorder",
        clinical_stem=clinical_stem,
        inputs=build_inputs(ph, paco2, hco3, na, cl),
        questions_flow=shuffle_question_options(
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
        answer_key=build_answer_key(
            ph_status=derived_ph_status(ph),
            primary_disorder="Metabolic acidosis",
            compensation="Inappropriate",
            anion_gap_value=ag,
            anion_gap_category="Raised",
            final_diagnosis="DKA with vomiting",
            additional_metabolic_process="Metabolic alkalosis",
        ),
        level=4,
        archetype="dka_vomiting",
        is_mixed=True,
        patient_gender=patient_gender,
    )


def generate_mixed_hagma_metabolic_alkalosis_case(case_id):
    band = random.choice(MIXED_HAGMA_METABOLIC_ALKALOSIS_VARIATION_BANDS)

    for _ in range(80):
        na = random.randint(*band["sodium_range"])
        target_ag = random.randint(*band["anion_gap_range"])
        delta_ag = target_ag - 12
        pure_hagma_hco3 = 24 - delta_ag
        alkalosis_offset = random.randint(*band["alkalosis_offset_range"])
        hco3 = pure_hagma_hco3 + alkalosis_offset

        if not (17 <= hco3 <= 24):
            continue

        cl = na - (hco3 + target_ag)
        if not (band["chloride_range"][0] <= cl <= band["chloride_range"][1]):
            continue

        ag = calc_anion_gap(na, cl, hco3)
        expected_paco2 = winters_expected_paco2(hco3)
        compensation_midpoint = expected_paco2 + random.uniform(*band["paco2_delta_range"])
        paco2_low = max(expected_paco2 - 2, compensation_midpoint - 0.7)
        paco2_high = min(expected_paco2 + 2, compensation_midpoint + 0.7)
        paco2 = round(random.uniform(paco2_low, paco2_high), 1)
        ph = estimate_ph(hco3, paco2)

        if not (band["ph_range"][0] <= ph <= band["ph_range"][1]):
            continue

        delta_hco3 = 24 - hco3
        alkalosis_signal = delta_ag - delta_hco3
        if alkalosis_signal < band["alkalosis_signal_min"]:
            continue

        break
    else:
        raise ValueError(f"Unable to generate mixed HAGMA + metabolic alkalosis values for {case_id}")

    if random.random() < band["moderate_lactate_probability"]:
        lactate = round(random.uniform(*band["moderate_lactate_range"]), 1)
    else:
        lactate = round(random.uniform(*band["mild_lactate_range"]), 1)
    clinical_stem = random.choice(band["stem_options"])
    lactate_explanation = (
        f"Lactate is {lactate}, so lactate contributes to the raised anion gap, but it does not fully explain the picture because the bicarbonate remains too preserved and the chloride is still low. "
        if lactate >= 3.0
        else f"Lactate is only {lactate}, so it does not fully account for the raised anion gap on its own. "
    )
    explanation = (
        f"1. The anion gap is {na} - ({cl} + {hco3}) = {ag}, which is raised, so there is a high anion gap metabolic acidosis. "
        f"2. PaCO2 is {paco2}, which is appropriate for the observed metabolic acidosis because Winter's formula predicts ~{expected_paco2:.1f} mmHg (+/-2). "
        f"3. The bicarbonate is {hco3}, which is too high for an isolated HAGMA of this magnitude; {band['explanation_emphasis']} "
        f"4. Chloride is low at {cl}, which supports a concurrent chloride-responsive metabolic alkalosis rather than a single-process acidosis. {lactate_explanation}"
        f"5. The overall pattern is a mixed high anion gap metabolic acidosis and metabolic alkalosis."
    )

    return build_case(
        case_id=case_id,
        title="Mixed HAGMA and metabolic alkalosis",
        category="mixed_disorder",
        learning_objective="Recognise a mixed high anion gap metabolic acidosis with concurrent metabolic alkalosis",
        tags=["mixed_disorder", "anion_gap", "metabolic"],
        clinical_stem=clinical_stem,
        inputs=build_inputs(ph, paco2, hco3, na, cl, lactate=lactate),
        questions_flow=shuffle_question_options(
            expert_question_flow(
                [
                    "Mixed high anion gap metabolic acidosis and metabolic alkalosis",
                    "High anion gap metabolic acidosis",
                    "Metabolic alkalosis",
                    "DKA",
                    "Lactic acidosis",
                ],
                include_additional_metabolic_process=True,
            )
        ),
        answer_key=build_answer_key(
            ph_status=derived_ph_status(ph),
            primary_disorder="Metabolic acidosis",
            compensation="Appropriate",
            anion_gap_value=ag,
            anion_gap_category="Raised",
            final_diagnosis="Mixed high anion gap metabolic acidosis and metabolic alkalosis",
            expected_compensation={
                "rule": "Winter",
                "expected_paco2_mmHg": round(expected_paco2, 1),
                "acceptable_range_mmHg": [round(expected_paco2 - 2, 1), round(expected_paco2 + 2, 1)],
            },
            additional_metabolic_process="Metabolic alkalosis",
        ),
        explanation=explanation,
        timing=default_timing(),
        level=4,
        archetype="mixed_hagma_metabolic_alkalosis",
        is_mixed=True,
    )
