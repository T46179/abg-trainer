"""Mixed-disorder ABG archetype generators.

Main functions:
- `generate_salicylate_case`
- `generate_dka_vomiting_case`
- `generate_mixed_hagma_metabolic_alkalosis_case`
- `generate_respiratory_alkalosis_hagma_case`
- `generate_respiratory_acidosis_hagma_case`

These builders cover cases where more than one primary acid-base process is
present and the question flow needs to support mixed-disorder reasoning.
"""

import random

from ..physiology import (
    acute_respiratory_acidosis_expected_hco3,
    calc_anion_gap,
    chronic_respiratory_acidosis_expected_hco3,
    derived_ph_status,
    estimate_ph,
    hagma_bicarbonate_preservation,
    isolated_hagma_expected_hco3,
    respiratory_alkalosis_expected_hco3_acute,
    winters_expected_paco2,
)
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

RESPIRATORY_ACIDOSIS_HAGMA_VARIATION_BANDS = [
    {
        "name": "septic_hypercapnic_failure",
        "compensation_rule": "Chronic respiratory acidosis",
        "paco2_range": (64, 78),
        "anion_gap_range": (20, 26),
        "hco3_delta_adjust_range": (-1.0, 1.0),
        "sodium_range": (136, 142),
        "chloride_range": (86, 96),
        "ph_range": (7.16, 7.31),
        "min_hco3_gap_below_chronic": 5,
        "lactate_range": (3.2, 5.8),
        "stem_options": [
            "68-year-old with chronic lung disease presents with fever, worsening dyspnoea, and increasing confusion after several days of productive cough.",
            "72-year-old with known CO2 retention attends ED with infective symptoms, drowsiness, and hypotension.",
            "65-year-old with chronic respiratory disease is brought in with escalating somnolence, increased work of breathing, and suspected pneumonia.",
            "74-year-old with severe COPD presents with fatigue, fever, and worsening hypercapnic symptoms during an acute illness.",
        ],
    },
    {
        "name": "shock_on_chronic_respiratory_failure",
        "compensation_rule": "Chronic respiratory acidosis",
        "paco2_range": (60, 74),
        "anion_gap_range": (22, 30),
        "hco3_delta_adjust_range": (-1.0, 0.8),
        "sodium_range": (136, 143),
        "chloride_range": (86, 97),
        "ph_range": (7.12, 7.28),
        "min_hco3_gap_below_chronic": 6,
        "lactate_range": (3.8, 6.6),
        "stem_options": [
            "63-year-old with chronic ventilatory failure presents with cool peripheries, tachycardia, and worsening drowsiness during a severe infection.",
            "70-year-old with advanced COPD is reviewed for increasing confusion, poor perfusion, and progressive breathlessness.",
            "67-year-old with chronic hypercapnia presents with lethargy, hypotension, and escalating respiratory fatigue.",
            "75-year-old with longstanding respiratory disease is brought in with reduced consciousness and signs of systemic hypoperfusion.",
        ],
    },
    {
        "name": "borderline_ph_trap",
        "compensation_rule": "Chronic respiratory acidosis",
        "paco2_range": (55, 64),
        "anion_gap_range": (17, 21),
        "hco3_delta_adjust_range": (-0.8, 0.8),
        "sodium_range": (136, 142),
        "chloride_range": (86, 96),
        "ph_range": (7.26, 7.30),
        "min_hco3_gap_below_chronic": 4,
        "lactate_range": (2.8, 4.8),
        "stem_options": [
            "71-year-old with chronic CO2 retention presents with fever, increasing drowsiness, and reduced oral intake during an infective exacerbation.",
            "69-year-old with severe COPD attends ED with worsening somnolence, tachycardia, and a new oxygen requirement.",
            "76-year-old with chronic respiratory failure is reviewed for confusion and worsening breathlessness on a background of systemic illness.",
            "73-year-old with known hypercapnia presents with lethargy and suspected infection after several days of deterioration.",
        ],
    },
    {
        "name": "acute_respiratory_failure_hagma",
        "compensation_rule": "Acute respiratory acidosis",
        "paco2_range": (58, 72),
        "anion_gap_range": (20, 28),
        "gap_below_expected_range": (4.5, 8.0),
        "sodium_range": (136, 143),
        "chloride_range": (88, 100),
        "ph_range": (7.05, 7.24),
        "lactate_range": (3.2, 6.2),
        "stem_options": [
            "48-year-old is brought in after suspected sedative overdose with shallow respirations, cool peripheries, and worsening confusion.",
            "56-year-old presents with acute ventilatory failure after aspiration, now with hypotension and increasing drowsiness.",
            "43-year-old is found with bradypnoea after opioid use and remains mottled and poorly perfused on arrival.",
            "61-year-old presents with reduced consciousness, shallow breathing, and severe infection after an aspiration event.",
        ],
    },
    {
        "name": "near_miss_compensation",
        "compensation_rule": "Chronic respiratory acidosis",
        "paco2_range": (62, 78),
        "anion_gap_range": (18, 21),
        "gap_below_expected_range": (2.2, 3.8),
        "sodium_range": (136, 143),
        "chloride_range": (86, 97),
        "ph_range": (7.24, 7.34),
        "lactate_range": (2.6, 4.5),
        "stem_options": [
            "70-year-old with chronic CO2 retention presents with mild hypotension, fever, and increasing lethargy during an infective exacerbation.",
            "67-year-old with severe COPD attends ED with worsening somnolence and systemic illness after several days of reduced intake.",
            "74-year-old with chronic ventilatory failure presents with drowsiness, tachycardia, and suspected pneumonia.",
            "69-year-old with known hypercapnia is reviewed for worsening confusion and poor perfusion during an acute illness.",
        ],
    },
]

RESPIRATORY_ALKALOSIS_HAGMA_VARIATION_BANDS = [
    {
        "name": "obvious_mixed",
        "paco2_range": (20, 28),
        "anion_gap_range": (22, 30),
        "gap_below_expected_range": (5.0, 8.0),
        "sodium_range": (136, 143),
        "chloride_range": (94, 110),
        "ph_range": (7.22, 7.36),
        "lactate_range": (3.0, 5.8),
        "stem_options": [
            "54-year-old presents with severe infection, tachypnoea, cool peripheries, and worsening confusion after a day of rigors.",
            "62-year-old attends ED with fever, marked tachypnoea, hypotension, and increasing lethargy during a presumed septic illness.",
            "47-year-old is reviewed for rapid breathing, abdominal discomfort, and poor perfusion in the setting of systemic infection.",
            "58-year-old presents with severe tachypnoea, clammy skin, and progressive drowsiness during an acute infective illness.",
        ],
        "explanation_emphasis": "The bicarbonate is clearly too low for isolated respiratory alkalosis, so this is not just hyperventilation.",
    },
    {
        "name": "near_normal_ph_trap",
        "paco2_range": (18, 24),
        "anion_gap_range": (21, 27),
        "gap_below_expected_range": (6.0, 8.5),
        "sodium_range": (136, 143),
        "chloride_range": (94, 110),
        "ph_range": (7.35, 7.44),
        "lactate_range": (2.6, 4.8),
        "stem_options": [
            "49-year-old presents with fever, rapid breathing, and light-headedness with worsening perfusion over several hours.",
            "36-year-old attends ED with severe tachypnoea, vomiting, and increasing lethargy during a systemic illness.",
            "44-year-old is reviewed with marked hyperventilation, abdominal pain, and poor intake after a prolonged febrile illness.",
            "57-year-old presents with tachypnoea, diaphoresis, and worsening confusion despite only a near-normal overall pH.",
        ],
        "explanation_emphasis": "The pH is a trap here: a near-normal overall pH does not make this a single-process disorder.",
    },
    {
        "name": "subtle_mismatch",
        "paco2_range": (24, 32),
        "anion_gap_range": (18, 22),
        "gap_below_expected_range": (2.5, 4.2),
        "sodium_range": (136, 143),
        "chloride_range": (94, 110),
        "ph_range": (7.32, 7.42),
        "lactate_range": (2.2, 4.0),
        "stem_options": [
            "52-year-old presents with tachypnoea, fever, and worsening fatigue during a systemic illness with reduced intake.",
            "61-year-old attends ED with rapid breathing, malaise, and intermittent hypotension after several days of infection.",
            "41-year-old is reviewed for persistent tachypnoea and lethargy during metabolic stress after poor oral tolerance.",
            "55-year-old presents with sepsis physiology and marked respiratory drive, but the bicarbonate change is only modestly out of keeping with simple respiratory alkalosis.",
        ],
        "explanation_emphasis": "The bicarbonate sits closer to the expected compensatory value, but it is still too low to fit a single respiratory process.",
    },
]

DKA_VOMITING_VARIATION_BANDS = [
    {
        "name": "obvious_preserved_hco3",
        "anion_gap_range": (28, 34),
        "alkalosis_offset_range": (7, 10),
        "hco3_range": (13, 18),
        "sodium_range": (134, 142),
        "chloride_range": (84, 94),
        "glucose_range": (24.0, 34.0),
        "paco2_delta_range": (-0.8, 0.8),
        "ph_range": (7.16, 7.30),
        "alkalosis_signal_min": 5.0,
    },
    {
        "name": "subtle_preserved_hco3",
        "anion_gap_range": (24, 30),
        "alkalosis_offset_range": (5, 7),
        "hco3_range": (12, 17),
        "sodium_range": (134, 141),
        "chloride_range": (86, 96),
        "glucose_range": (20.0, 30.0),
        "paco2_delta_range": (-0.8, 0.8),
        "ph_range": (7.15, 7.29),
        "alkalosis_signal_min": 4.0,
    },
    {
        "name": "near_normal_ph_trap",
        "anion_gap_range": (24, 28),
        "alkalosis_offset_range": (8, 10),
        "hco3_range": (18, 21),
        "sodium_range": (134, 142),
        "chloride_range": (84, 94),
        "glucose_range": (18.0, 28.0),
        "paco2_delta_range": (-0.7, 0.7),
        "ph_range": (7.33, 7.39),
        "alkalosis_signal_min": 5.0,
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
    band = random.choice(DKA_VOMITING_VARIATION_BANDS)

    for _ in range(80):
        na = random.randint(*band["sodium_range"])
        target_ag = random.randint(*band["anion_gap_range"])
        pure_hagma_hco3 = isolated_hagma_expected_hco3(target_ag)
        alkalosis_offset = random.randint(*band["alkalosis_offset_range"])
        hco3 = pure_hagma_hco3 + alkalosis_offset

        if not (band["hco3_range"][0] <= hco3 <= band["hco3_range"][1]):
            continue

        cl = na - (hco3 + target_ag)
        if not (band["chloride_range"][0] <= cl <= band["chloride_range"][1]):
            continue

        ag = calc_anion_gap(na, cl, hco3)
        alkalosis_signal = hagma_bicarbonate_preservation(ag, hco3)
        if alkalosis_signal < band["alkalosis_signal_min"]:
            continue

        expected_paco2 = winters_expected_paco2(hco3)
        compensation_midpoint = expected_paco2 + random.uniform(*band["paco2_delta_range"])
        paco2_low = max(expected_paco2 - 2, compensation_midpoint - 0.7)
        paco2_high = min(expected_paco2 + 2, compensation_midpoint + 0.7)
        paco2 = round(random.uniform(paco2_low, paco2_high), 1)
        ph = estimate_ph(hco3, paco2)

        if not (band["ph_range"][0] <= ph <= band["ph_range"][1]):
            continue

        break
    else:
        raise ValueError(f"Unable to generate DKA with vomiting values for {case_id}")

    glucose = round(random.uniform(*band["glucose_range"]), 1)
    pure_hagma_hco3 = isolated_hagma_expected_hco3(ag)
    expected_paco2 = winters_expected_paco2(hco3)
    ph_status = derived_ph_status(ph)

    if ph_status == "Acidaemia":
        ph_text = "The pH is low, so there is overall acidaemia."
    elif ph_status == "Normal":
        ph_text = "The pH is near normal, which is a common trap in mixed metabolic disorders."
    else:
        ph_text = "The pH is only mildly alkalaemic, which can mislead if you rely on pH alone."

    explanation = (
        f"1. {ph_text} The low bicarbonate still makes the overall pattern metabolic rather than a primary respiratory problem. "
        f"2. The anion gap is {na} - ({cl} + {hco3}) = {ag}, which is raised, so there is a high anion gap metabolic acidosis. "
        f"Glucose is {glucose}, which strongly supports DKA as the cause of that HAGMA. "
        f"3. For an isolated HAGMA of this size, the bicarbonate would be expected to be about {pure_hagma_hco3}. "
        f"The actual bicarbonate is {hco3}, so it is preserved by about {alkalosis_signal} mmol/L rather than falling as far as expected. "
        f"That delta-gap mismatch proves an additional metabolic alkalosis, which fits vomiting and chloride loss. "
        f"4. PaCO2 is {paco2}, and Winter's formula for the displayed bicarbonate predicts about {expected_paco2:.1f} mmHg (+/-2), "
        f"so the respiratory response is appropriate for the displayed metabolic disturbance rather than a second respiratory primary process. "
        f"5. This is DKA with concurrent metabolic alkalosis from vomiting."
    )
    clinical_stem, patient_gender = generate_stem("dka_vomiting", return_patient_gender=True)

    return build_case(
        case_id=case_id,
        title="DKA with vomiting (mixed metabolic disorder)",
        category="mixed_disorder",
        clinical_stem=clinical_stem,
        inputs=build_inputs(ph, paco2, hco3, na, cl, glucose=glucose),
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
            ph_status=ph_status,
            primary_disorder="Metabolic acidosis",
            compensation="Appropriate",
            anion_gap_value=ag,
            anion_gap_category="Raised",
            final_diagnosis="DKA with vomiting",
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


def generate_respiratory_alkalosis_hagma_case(case_id):
    band = _respiratory_alkalosis_hagma_band_for_case(case_id)

    for _ in range(150):
        paco2 = round(random.uniform(*band["paco2_range"]), 1)
        expected_hco3 = respiratory_alkalosis_expected_hco3_acute(paco2)
        gap_below_expected = round(random.uniform(*band["gap_below_expected_range"]), 1)
        hco3 = round(expected_hco3 - gap_below_expected, 1)

        if hco3 < 8 or hco3 > 22:
            continue

        na = random.randint(*band["sodium_range"])
        target_ag = random.randint(*band["anion_gap_range"])
        cl = int(round(na - (hco3 + target_ag)))
        if not (band["chloride_range"][0] <= cl <= band["chloride_range"][1]):
            continue

        ag = calc_anion_gap(na, cl, hco3)
        ph = estimate_ph(hco3, paco2)
        if not (band["ph_range"][0] <= ph <= band["ph_range"][1]):
            continue

        break
    else:
        raise ValueError(f"Unable to generate respiratory alkalosis + HAGMA values for {case_id}")

    lactate = round(random.uniform(*band["lactate_range"]), 1)
    expected_hco3_low = round(expected_hco3 - 2, 1)
    expected_hco3_high = round(expected_hco3 + 2, 1)
    clinical_stem = random.choice(band["stem_options"])

    if ph < 7.35:
        ph_summary = "acidaemia overall"
    elif ph > 7.45:
        ph_summary = "alkalaemia overall"
    else:
        ph_summary = "a near-normal overall pH"

    explanation = (
        f"1. pH is {ph}, so there is {ph_summary}. "
        f"2. PaCO2 is {paco2} mmHg, which is clearly low and indicates a primary respiratory alkalosis. "
        f"3. If this were isolated acute respiratory alkalosis, HCO3 should be about {expected_hco3:.1f} mmol/L "
        f"(acceptable range {expected_hco3_low}-{expected_hco3_high}), but the actual HCO3 is {hco3} mmol/L. "
        f"This does not fit expected compensation for a single respiratory process. {band['explanation_emphasis']} "
        f"4. The anion gap is {na} - ({cl} + {hco3}) = {ag}, which is raised; lactate is {lactate}, supporting a concurrent high anion gap metabolic acidosis. "
        f"5. The overall pattern is respiratory alkalosis with concurrent high anion gap metabolic acidosis."
    )

    return build_case(
        case_id=case_id,
        title="Respiratory alkalosis with concurrent HAGMA",
        category="mixed_disorder",
        learning_objective="Recognise respiratory alkalosis with a concurrent high anion gap metabolic acidosis when bicarbonate is too low for isolated respiratory alkalosis",
        tags=["mixed_disorder", "respiratory_alkalosis", "hagma", "anion_gap", "hyperventilation"],
        clinical_stem=clinical_stem,
        inputs=build_inputs(ph, paco2, hco3, na, cl, lactate=lactate),
        questions_flow=shuffle_question_options(
            expert_question_flow(
                [
                    "Respiratory alkalosis with concurrent high anion gap metabolic acidosis",
                    "Respiratory alkalosis",
                    "High anion gap metabolic acidosis",
                    "Sepsis",
                    "Salicylate toxicity",
                    "Panic attack / hyperventilation",
                ],
                include_additional_metabolic_process=True,
            )
        ),
        answer_key=build_answer_key(
            ph_status=derived_ph_status(ph),
            primary_disorder="Respiratory alkalosis",
            compensation="Inappropriate",
            anion_gap_value=ag,
            anion_gap_category="Raised",
            final_diagnosis="Respiratory alkalosis with concurrent high anion gap metabolic acidosis",
            expected_compensation={
                "rule": "Acute respiratory alkalosis",
                "expected_hco3_mmolL": round(expected_hco3, 1),
                "acceptable_range_mmolL": [expected_hco3_low, expected_hco3_high],
            },
            additional_metabolic_process="High anion gap metabolic acidosis",
        ),
        explanation=explanation,
        timing=default_timing(),
        level=4,
        archetype="respiratory_alkalosis_hagma",
        is_mixed=True,
    )


def generate_respiratory_acidosis_hagma_case(case_id):
    band = _respiratory_acidosis_hagma_band_for_case(case_id)

    for _ in range(100):
        paco2 = round(random.uniform(*band["paco2_range"]), 1)
        expected_hco3 = _expected_hco3_for_rule(band["compensation_rule"], paco2)
        target_ag = random.randint(*band["anion_gap_range"])

        if band.get("gap_below_expected_range") is not None:
            gap_below_expected = round(random.uniform(*band["gap_below_expected_range"]), 1)
            hco3 = round(expected_hco3 - gap_below_expected, 1)
        else:
            delta_ag = target_ag - 12
            hco3 = round(expected_hco3 - delta_ag + random.uniform(*band["hco3_delta_adjust_range"]), 1)
            gap_below_expected = round(expected_hco3 - hco3, 1)

        if hco3 < 18 or hco3 > 36:
            continue

        na = random.randint(*band["sodium_range"])
        cl = int(round(na - (hco3 + target_ag)))
        if not (band["chloride_range"][0] <= cl <= band["chloride_range"][1]):
            continue

        ag = calc_anion_gap(na, cl, hco3)
        ph = estimate_ph(hco3, paco2)
        if not (band["ph_range"][0] <= ph <= band["ph_range"][1]):
            continue

        if gap_below_expected < band.get("min_hco3_gap_below_chronic", 0):
            continue

        break
    else:
        raise ValueError(f"Unable to generate respiratory acidosis + HAGMA values for {case_id}")

    lactate = round(random.uniform(*band["lactate_range"]), 1)
    expected_hco3_low = round(expected_hco3 - 2, 1)
    expected_hco3_high = round(expected_hco3 + 2, 1)
    clinical_stem = random.choice(band["stem_options"])
    mismatch_phrase = (
        "The bicarbonate is close to the expected compensatory value, but it is still too low to fit a single respiratory process."
        if band["name"] == "near_miss_compensation"
        else "The bicarbonate is too low to fit isolated respiratory compensation."
    )
    compensation_label = band["compensation_rule"].lower()

    explanation = (
        f"1. pH is {ph}, so this is {'acidaemia' if ph < 7.35 else 'a near-normal pH overall'}. "
        f"2. PaCO2 is {paco2} mmHg, which is clearly elevated and indicates respiratory acidosis. "
        f"3. If this were isolated {compensation_label}, HCO3 should be about {expected_hco3:.1f} mmol/L "
        f"(acceptable range {expected_hco3_low}-{expected_hco3_high}), but the actual HCO3 is {hco3} mmol/L. {mismatch_phrase} "
        f"4. The anion gap is {na} - ({cl} + {hco3}) = {ag}, which is raised; lactate is {lactate}, supporting a concurrent high anion gap metabolic acidosis. "
        f"5. The overall pattern is respiratory acidosis with concurrent high anion gap metabolic acidosis."
    )

    return build_case(
        case_id=case_id,
        title="Respiratory acidosis with concurrent HAGMA",
        category="mixed_disorder",
        learning_objective="Recognise respiratory acidosis with a concurrent high anion gap metabolic acidosis when bicarbonate is too low for isolated respiratory compensation",
        tags=["mixed_disorder", "respiratory_acidosis", "hagma", "hypercapnia", "anion_gap"],
        clinical_stem=clinical_stem,
        inputs=build_inputs(ph, paco2, hco3, na, cl, lactate=lactate),
        questions_flow=shuffle_question_options(
            expert_question_flow(
                [
                    "Respiratory acidosis with concurrent high anion gap metabolic acidosis",
                    "Respiratory acidosis",
                    "High anion gap metabolic acidosis",
                    "COPD exacerbation",
                    "Lactic acidosis",
                    "Opioid toxicity",
                ],
                include_additional_metabolic_process=True,
            )
        ),
        answer_key=build_answer_key(
            ph_status=derived_ph_status(ph),
            primary_disorder="Respiratory acidosis",
            compensation="Inappropriate",
            anion_gap_value=ag,
            anion_gap_category="Raised",
            final_diagnosis="Respiratory acidosis with concurrent high anion gap metabolic acidosis",
            expected_compensation={
                "rule": band["compensation_rule"],
                "expected_hco3_mmolL": round(expected_hco3, 1),
                "acceptable_range_mmolL": [expected_hco3_low, expected_hco3_high],
            },
            additional_metabolic_process="High anion gap metabolic acidosis",
        ),
        explanation=explanation,
        timing=default_timing(),
        level=4,
        archetype="respiratory_acidosis_hagma",
        is_mixed=True,
    )


def _expected_hco3_for_rule(rule, paco2):
    if rule == "Acute respiratory acidosis":
        return acute_respiratory_acidosis_expected_hco3(paco2)
    if rule == "Chronic respiratory acidosis":
        return chronic_respiratory_acidosis_expected_hco3(paco2)
    raise ValueError(f"Unsupported respiratory compensation rule: {rule}")


def _respiratory_acidosis_hagma_band_for_case(case_id):
    try:
        case_number = int(str(case_id).split("_")[-1])
    except (TypeError, ValueError):
        return random.choice(RESPIRATORY_ACIDOSIS_HAGMA_VARIATION_BANDS)

    # Cycle across bands so the fixed 8-case pool always covers the acute and near-miss variants.
    band_index = (case_number - 1) % len(RESPIRATORY_ACIDOSIS_HAGMA_VARIATION_BANDS)
    return RESPIRATORY_ACIDOSIS_HAGMA_VARIATION_BANDS[band_index]


def _respiratory_alkalosis_hagma_band_for_case(case_id):
    try:
        case_number = int(str(case_id).split("_")[-1])
    except (TypeError, ValueError):
        return random.choice(RESPIRATORY_ALKALOSIS_HAGMA_VARIATION_BANDS)

    # Cycle across bands so the fixed 8-case pool always covers the major mixed-pattern variants.
    band_index = (case_number - 1) % len(RESPIRATORY_ALKALOSIS_HAGMA_VARIATION_BANDS)
    return RESPIRATORY_ALKALOSIS_HAGMA_VARIATION_BANDS[band_index]
