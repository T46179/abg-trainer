import json
import random
import math
from collections import Counter

# ----------------------------
# Numeric formatting / rounding
# ----------------------------

PH_DP = 2
GAS_DP = 1
ELECTROLYTE_DP = 0
LACTATE_DP = 1
AG_DP = 1


def r_ph(x):
    return round(x, PH_DP)


def r_gas(x):
    return round(x, GAS_DP)


def r_lyte(x):
    return int(round(x))


def r_lactate(x):
    return round(x, LACTATE_DP)


def r_ag(x):
    return round(x, AG_DP)


def build_inputs(ph, paco2, hco3, na, cl, lactate=None):
    inputs = {
        "gas": {
            "ph": r_ph(ph),
            "paco2_mmHg": r_gas(paco2),
            "hco3_mmolL": r_gas(hco3),
        },
        "electrolytes": {
            "na_mmolL": r_lyte(na),
            "cl_mmolL": r_lyte(cl),
        }
    }

    if lactate is not None:
        inputs["lactate_mmolL"] = r_lactate(lactate)

    return inputs


def get_display_values(inputs):
    gas = inputs["gas"]
    ely = inputs["electrolytes"]
    return (
        gas["ph"],
        gas["paco2_mmHg"],
        gas["hco3_mmolL"],
        ely["na_mmolL"],
        ely["cl_mmolL"],
        inputs.get("lactate_mmolL"),
    )

#--------------------------
#DIFFICULTY SETTINGS
#--------------------------
def difficulty_label(level):
    mapping = {
        1: "beginner",
        2: "intermediate",
        3: "advanced",
        4: "expert"
    }
    return mapping.get(level, "custom")

def tier_name(level, is_mixed=False):
    if is_mixed:
        return "master"

    mapping = {
        1: "beginner",
        2: "competent",
        3: "advanced",
        4: "expert"
    }
    return mapping.get(level, "custom")


def skills_for_case(level, is_mixed=False):
    if is_mixed:
        return [
            "ph_status",
            "primary_disorder",
            "compensation",
            "anion_gap",
            "mixed_disorder_detection",
            "final_diagnosis"
        ]

    mapping = {
        1: ["ph_status", "primary_disorder", "final_diagnosis"],
        2: ["ph_status", "primary_disorder", "compensation", "final_diagnosis"],
        3: ["ph_status", "primary_disorder", "compensation", "anion_gap", "final_diagnosis"],
        4: ["ph_status", "primary_disorder", "compensation", "anion_gap", "final_diagnosis"]
    }
    return mapping.get(level, [])


def case_pool_for_archetype(archetype):
    mapping = {
        "dka": "core_metabolic",
        "diarrhoea_nagma": "core_metabolic",
        "vomiting_metabolic_alkalosis": "core_metabolic",
        "opioid_toxicity": "core_respiratory",
        "copd_chronic_retainer": "core_respiratory",
        "panic_hyperventilation": "core_respiratory",
        "salicylate_toxicity": "mixed_disorders"
    }
    return mapping.get(archetype, "core")


def base_xp_for_tier(tier):
    mapping = {
        "beginner": 10,
        "competent": 15,
        "advanced": 20,
        "expert": 25,
        "master": 30
    }
    return mapping.get(tier, 10)


def mastery_weight_for_tier(tier):
    mapping = {
        "beginner": 1.0,
        "competent": 1.0,
        "advanced": 1.1,
        "expert": 1.25,
        "master": 1.5
    }
    return mapping.get(tier, 1.0)
    
def attach_progression_metadata(case, level, archetype, is_mixed=False):
    tier = tier_name(level, is_mixed)

    case["archetype"] = archetype
    case["difficulty_level"] = level
    case["difficulty_label"] = difficulty_label(level)
    case["tier"] = tier
    case["skills_tested"] = skills_for_case(level, is_mixed)
    case["case_pool"] = case_pool_for_archetype(archetype)
    case["base_xp"] = base_xp_for_tier(tier)
    case["mastery_weight"] = mastery_weight_for_tier(tier)

    return case    
    
#------------------------------------
# HELPER FUNCTIONS
#------------------------------------
def winters_expected_paco2(hco3):
    return 1.5 * hco3 + 8


def calculate_ph_from_hco3_paco2(hco3, paco2):
    return r_ph(6.1 + math.log10(hco3 / (0.03 * paco2)))


def estimate_ph(hco3, paco2):
    return calculate_ph_from_hco3_paco2(hco3, paco2)


def chronic_respiratory_acidosis_expected_hco3(paco2):
    return 24 + 4 * ((paco2 - 40) / 10)


def metabolic_alkalosis_expected_paco2(hco3):
    return 0.7 * (hco3 - 24) + 40


def respiratory_alkalosis_expected_hco3_acute(paco2):
    return 24 - 2 * ((40 - paco2) / 10)


def anion_gap_category(ag):
    return "Raised" if ag > 16 else "Normal"


def calc_anion_gap(na, cl, hco3):
    return r_ag(na - (cl + hco3))


def derived_ph_status(ph):
    if ph < 7.35:
        return "Acidemia"
    if ph > 7.45:
        return "Alkalemia"
    return "Normal"


def in_range(value, low, high, tolerance=0.05):
    return (low - tolerance) <= value <= (high + tolerance)


def validate_question_flow(case):
    errors = []

    qf = case.get("questions_flow", [])
    keys = [q.get("key") for q in qf]

    expected_by_level = {
        1: ["ph_status", "primary_disorder", "final_diagnosis"],
        2: ["ph_status", "primary_disorder", "compensation", "final_diagnosis"],
        3: ["ph_status", "primary_disorder", "compensation", "anion_gap", "final_diagnosis"],
        4: ["ph_status", "primary_disorder", "compensation", "anion_gap", "final_diagnosis"],
    }

    difficulty = case.get("difficulty_level")
    expected = expected_by_level.get(difficulty)

    if expected and keys != expected:
        errors.append(
            f"questions_flow keys {keys} do not match expected {expected} for difficulty {difficulty}"
        )

    steps = [q.get("step") for q in qf]
    if steps != list(range(1, len(qf) + 1)):
        errors.append(f"questions_flow step numbering invalid: {steps}")

    for q in qf:
        opts = q.get("options", [])
        if not isinstance(opts, list) or len(opts) < 2:
            errors.append(f"question '{q.get('key')}' has invalid options list")

    return errors


def validate_case(case):
    errors = []

    case_id = case.get("case_id", "<missing_case_id>")
    archetype = case.get("archetype")

    gas = case.get("inputs", {}).get("gas", {})
    ely = case.get("inputs", {}).get("electrolytes", {})
    ak = case.get("answer_key", {})
    exp = ak.get("expected_compensation", {})

    ph = gas.get("ph")
    paco2 = gas.get("paco2_mmHg")
    hco3 = gas.get("hco3_mmolL")
    na = ely.get("na_mmolL")
    cl = ely.get("cl_mmolL")

    required = {
        "ph": ph,
        "paco2_mmHg": paco2,
        "hco3_mmolL": hco3,
        "na_mmolL": na,
        "cl_mmolL": cl,
    }
    for name, value in required.items():
        if value is None:
            errors.append(f"{case_id}: missing required field {name}")

    if errors:
        return errors

    # Basic physiologic sanity checks
    if not (6.8 <= ph <= 7.8):
        errors.append(f"{case_id}: implausible pH {ph}")
    if not (10 <= paco2 <= 120):
        errors.append(f"{case_id}: implausible PaCO2 {paco2}")
    if not (3 <= hco3 <= 60):
        errors.append(f"{case_id}: implausible HCO3 {hco3}")
    if not (110 <= na <= 180):
        errors.append(f"{case_id}: implausible Na {na}")
    if not (50 <= cl <= 140):
        errors.append(f"{case_id}: implausible Cl {cl}")

    # pH status check
    derived_status = derived_ph_status(ph)
    if ak.get("ph_status") != derived_status:
        errors.append(
            f"{case_id}: ph_status mismatch (stored '{ak.get('ph_status')}', derived '{derived_status}')"
        )

    # anion gap check
    ag = calc_anion_gap(na, cl, hco3)
    stored_ag = ak.get("anion_gap_value")
    if stored_ag is None:
        errors.append(f"{case_id}: missing answer_key.anion_gap_value")
    elif abs(stored_ag - ag) > 0.15:
        errors.append(
            f"{case_id}: anion gap mismatch (stored {stored_ag}, derived {ag})"
        )

    derived_ag_category = anion_gap_category(ag)
    if ak.get("anion_gap_category") != derived_ag_category:
        errors.append(
            f"{case_id}: anion gap category mismatch (stored '{ak.get('anion_gap_category')}', derived '{derived_ag_category}')"
        )

    # recomputed pH check from HH equation
    estimated = estimate_ph(hco3, paco2)
    if abs(estimated - ph) > 0.06:
        errors.append(
            f"{case_id}: pH inconsistent with HCO3/PaCO2 (stored {ph}, estimated {estimated})"
        )

    # Archetype-specific checks
    if archetype == "dka":
        expected_paco2 = round(winters_expected_paco2(hco3), 1)
        low = round(expected_paco2 - 2, 1)
        high = round(expected_paco2 + 2, 1)

        if ak.get("primary_disorder") != "Metabolic acidosis":
            errors.append(f"{case_id}: DKA should be metabolic acidosis")
        if ak.get("final_diagnosis") != "DKA":
            errors.append(f"{case_id}: DKA final diagnosis mismatch")
        if ag <= 16:
            errors.append(f"{case_id}: DKA should have raised anion gap, got {ag}")
        if not in_range(paco2, low, high):
            errors.append(
                f"{case_id}: DKA PaCO2 outside Winter range ({paco2} not in {low}–{high})"
            )
        if exp.get("rule") != "Winter":
            errors.append(f"{case_id}: DKA expected rule should be Winter")

    elif archetype == "diarrhoea_nagma":
        expected_paco2 = round(winters_expected_paco2(hco3), 1)
        low = round(expected_paco2 - 2, 1)
        high = round(expected_paco2 + 2, 1)

        if ak.get("primary_disorder") != "Metabolic acidosis":
            errors.append(f"{case_id}: diarrhoea should be metabolic acidosis")
        if ak.get("final_diagnosis") != "Diarrhoea":
            errors.append(f"{case_id}: diarrhoea final diagnosis mismatch")
        if ag > 16:
            errors.append(f"{case_id}: diarrhoea should be normal AG, got {ag}")
        if not in_range(paco2, low, high):
            errors.append(
                f"{case_id}: diarrhoea PaCO2 outside Winter range ({paco2} not in {low}–{high})"
            )

    elif archetype == "opioid_toxicity":
        expected_hco3 = round(24 + ((paco2 - 40) / 10), 1)
        low = round(expected_hco3 - 2, 1)
        high = round(expected_hco3 + 2, 1)

        if ak.get("primary_disorder") != "Respiratory acidosis":
            errors.append(f"{case_id}: opioid case should be respiratory acidosis")
        if ak.get("final_diagnosis") != "Opioid toxicity":
            errors.append(f"{case_id}: opioid final diagnosis mismatch")
        if paco2 <= 40:
            errors.append(f"{case_id}: opioid case should have elevated PaCO2")
        if not in_range(hco3, low, high):
            errors.append(
                f"{case_id}: opioid HCO3 outside acute respiratory acidosis range ({hco3} not in {low}–{high})"
            )

    elif archetype == "copd_chronic_retainer":
        expected_hco3 = round(chronic_respiratory_acidosis_expected_hco3(paco2), 1)
        low = round(expected_hco3 - 2, 1)
        high = round(expected_hco3 + 2, 1)

        if ak.get("primary_disorder") != "Respiratory acidosis":
            errors.append(f"{case_id}: COPD case should be respiratory acidosis")
        if ak.get("final_diagnosis") != "COPD":
            errors.append(f"{case_id}: COPD final diagnosis mismatch")
        if paco2 <= 40:
            errors.append(f"{case_id}: COPD case should have elevated PaCO2")
        if not in_range(hco3, low, high):
            errors.append(
                f"{case_id}: COPD HCO3 outside chronic respiratory acidosis range ({hco3} not in {low}–{high})"
            )

    elif archetype == "vomiting_metabolic_alkalosis":
        expected_paco2 = round(metabolic_alkalosis_expected_paco2(hco3), 1)
        low = round(expected_paco2 - 3, 1)
        high = round(expected_paco2 + 3, 1)

        if ak.get("primary_disorder") != "Metabolic alkalosis":
            errors.append(f"{case_id}: vomiting case should be metabolic alkalosis")
        if ak.get("final_diagnosis") != "Vomiting":
            errors.append(f"{case_id}: vomiting final diagnosis mismatch")
        if ph <= 7.45:
            errors.append(f"{case_id}: vomiting case should be alkalemic")
        if not in_range(paco2, low, high):
            errors.append(
                f"{case_id}: vomiting PaCO2 outside expected compensation range ({paco2} not in {low}–{high})"
            )

    elif archetype == "panic_hyperventilation":
        expected_hco3 = round(respiratory_alkalosis_expected_hco3_acute(paco2), 1)
        low = round(expected_hco3 - 2, 1)
        high = round(expected_hco3 + 2, 1)

        if ak.get("primary_disorder") != "Respiratory alkalosis":
            errors.append(f"{case_id}: panic case should be respiratory alkalosis")
        if ak.get("final_diagnosis") != "Panic attack / hyperventilation":
            errors.append(f"{case_id}: panic final diagnosis mismatch")
        if paco2 >= 40:
            errors.append(f"{case_id}: panic case should have low PaCO2")
        if ph <= 7.45:
            errors.append(f"{case_id}: panic case should be alkalemic")
        if not in_range(hco3, low, high):
            errors.append(
                f"{case_id}: panic HCO3 outside acute respiratory alkalosis range ({hco3} not in {low}–{high})"
            )

    elif archetype == "salicylate_toxicity":
        if ak.get("primary_disorder") != "Mixed disorder":
            errors.append(f"{case_id}: salicylate case should be mixed disorder")
        if ak.get("final_diagnosis") != "Salicylate toxicity":
            errors.append(f"{case_id}: salicylate final diagnosis mismatch")
        if paco2 >= 40:
            errors.append(f"{case_id}: salicylate case should have low PaCO2")
        if hco3 >= 22:
            errors.append(f"{case_id}: salicylate case should have low HCO3")
        if ag <= 16:
            errors.append(f"{case_id}: salicylate case should have raised AG, got {ag}")
        if ak.get("compensation") != "Inappropriate":
            errors.append(f"{case_id}: salicylate compensation label should indicate mixed disorder")
            
    elif archetype == "lactic_acidosis":
        expected_paco2 = round(winters_expected_paco2(hco3), 1)
        low = round(expected_paco2 - 2, 1)
        high = round(expected_paco2 + 2, 1)

        if ak.get("primary_disorder") != "Metabolic acidosis":
            errors.append(f"{case_id}: lactate case should be metabolic acidosis")

        if ak.get("final_diagnosis") != "Lactic acidosis":
            errors.append(f"{case_id}: lactate final diagnosis mismatch")

        if ag <= 16:
            errors.append(f"{case_id}: lactate case should have raised anion gap, got {ag}")

        if not in_range(paco2, low, high):
            errors.append(
                f"{case_id}: lactate PaCO2 outside Winter range ({paco2} not in {low}–{high})"
            )

        if exp.get("rule") != "Winter":
            errors.append(f"{case_id}: lactate expected rule should be Winter")

    errors.extend(validate_question_flow(case))
    return errors


def validate_cases(cases):
    errors = []
    seen_ids = set()

    for case in cases:
        case_id = case.get("case_id", "<missing_case_id>")

        if case_id in seen_ids:
            errors.append(f"{case_id}: duplicate case_id")
        seen_ids.add(case_id)

        errors.extend(validate_case(case))

    return errors    

def generate_valid_case(generator_fn, case_id, max_attempts=50):
    last_errors = []

    for attempt in range(1, max_attempts + 1):
        case = generator_fn(case_id)
        errors = validate_case(case)

        if not errors:
            return case

        last_errors = errors

    raise ValueError(
        f"Failed to generate valid case for {case_id} after {max_attempts} attempts.\n"
        + "\n".join(last_errors)
    )


from collections import Counter

def print_generation_report(cases):
    archetypes = Counter(case.get("archetype", "unknown") for case in cases)
    difficulties = Counter(case.get("difficulty_level", "unknown") for case in cases)

    ph_values = [case["inputs"]["gas"]["ph"] for case in cases]
    paco2_values = [case["inputs"]["gas"]["paco2_mmHg"] for case in cases]
    hco3_values = [case["inputs"]["gas"]["hco3_mmolL"] for case in cases]

    print("\nGeneration report")
    print("-----------------")
    print(f"Total cases: {len(cases)}")
    print(f"Archetypes: {dict(archetypes)}")
    print(f"Difficulties: {dict(difficulties)}")
    print(f"pH range: {min(ph_values)} → {max(ph_values)}")
    print(f"PaCO2 range: {min(paco2_values)} → {max(paco2_values)}")
    print(f"HCO3 range: {min(hco3_values)} → {max(hco3_values)}")
    
    
def q_ph_status():
    return {
        "step": 1,
        "key": "ph_status",
        "prompt": "Is the patient acidemic, alkalemic, or normal?",
        "options": ["Acidemia", "Alkalemia", "Normal"]
    }


def q_acid_base_disorder():
    return {
        "step": 2,
        "key": "primary_disorder",
        "prompt": "What is the acid-base disorder?",
        "options": [
            "Metabolic acidosis",
            "Metabolic alkalosis",
            "Respiratory acidosis",
            "Respiratory alkalosis",
            "Mixed disorder"
        ]
    }


def q_compensation(step=3):
    return {
        "step": step,
        "key": "compensation",
        "prompt": "Is compensation appropriate?",
        "options": ["Appropriate", "Inappropriate"]
    }


def q_anion_gap(step=4):
    return {
        "step": step,
        "key": "anion_gap",
        "prompt": "Calculate the anion gap (Na − (Cl + HCO3)).",
        "options": ["Normal", "Raised"]
    }


def q_final_diagnosis(step, options):
    return {
        "step": step,
        "key": "final_diagnosis",
        "prompt": "Most likely diagnosis?",
        "options": options
    }

def beginner_question_flow(final_options):
    return [
        q_ph_status(),
        q_acid_base_disorder(),
        q_final_diagnosis(3, final_options)
    ]


def intermediate_question_flow(final_options):
    return [
        q_ph_status(),
        q_acid_base_disorder(),
        q_compensation(3),
        q_final_diagnosis(4, final_options)
    ]


def advanced_question_flow(final_options):
    return [
        q_ph_status(),
        q_acid_base_disorder(),
        q_compensation(3),
        q_anion_gap(4),
        q_final_diagnosis(5, final_options)
    ]    


def shuffle_question_options(questions_flow):
    shuffled = []
    for question in questions_flow:
        q = dict(question)
        if "options" in q:
            q["options"] = q["options"][:]
            random.shuffle(q["options"])
        shuffled.append(q)
    return shuffled  

# -------------------------------------
# Stem variation system
# -------------------------------------

STEM_BANK = {

    "dka": {
        "ages": ["19-year-old", "23-year-old", "27-year-old", "31-year-old"],
        "openers": ["presents to ED", "is brought to ED", "attends ED"],
        "feature_groups": {
            "respiratory": [
                "tachypnoeic",
                "with deep rapid breathing"
            ],
            "gi": [
                "with abdominal pain",
                "with vomiting"
            ],
            "volume": [
                "dehydrated",
                "with reduced oral intake"
            ],
            "metabolic": [
                "with polyuria",
                "feeling generally unwell"
            ]
        },
        "patterns": [
            "{age} {opener} {f1}, {f2}, and {f3}.",
            "{age} {opener} with {f1} and {f2}.",
            "{age} {opener} unwell with {f1} and {f2}."
        ]
    },

    "dka_vomiting": {
        "ages": ["24-year-old", "28-year-old", "30-year-old"],
        "openers": ["presents to ED", "is brought to ED", "attends ED"],
        "feature_groups": {
            "diabetes_context": [
                "with type 1 diabetes",
                "after missed insulin doses"
            ],
            "respiratory": [
                "with deep rapid breathing",
                "tachypnoeic"
            ],
            "gi": [
                "with persistent vomiting",
                "with abdominal pain"
            ],
            "volume": [
                "dehydrated",
                "with reduced oral intake"
            ]
        },
        "patterns": [
            "{age} {opener} {f1}, {f2}, and {f3}.",
            "{age} {opener} with {f1} and {f2}.",
            "{age} {opener} unwell with {f1}, {f2}, and {f3}."
        ]
    },

    "vomiting_metabolic_alkalosis": {
        "ages": ["35-year-old", "40-year-old", "45-year-old"],
        "openers": ["presents to ED", "attends ED", "is brought in"],
        "feature_groups": {
            "vomiting": [
                "with persistent vomiting",
                "after several days of vomiting"
            ],
            "volume": [
                "with dehydration",
                "with reduced oral intake"
            ],
            "symptoms": [
                "with lightheadedness",
                "with weakness"
            ],
            "general": [
                "with nausea",
                "feeling generally unwell"
            ]
        },
        "patterns": [
            "{age} {opener} {f1} and {f2}.",
            "{age} {opener} with {f1}, {f2}, and {f3}.",
            "{age} {opener} unwell with {f1} and {f2}."
        ]
    },

    "diarrhoea_nagma": {
        "ages": ["32-year-old", "38-year-old", "42-year-old"],
        "openers": ["presents to ED", "attends ED", "is brought in"],
        "feature_groups": {
            "bowel_loss": [
                "with profuse diarrhoea",
                "after several days of diarrhoea"
            ],
            "volume": [
                "with dehydration",
                "with reduced oral intake"
            ],
            "abdominal": [
                "with abdominal cramps",
                "with abdominal discomfort"
            ],
            "systemic": [
                "with weakness",
                "feeling generally unwell"
            ]
        },
        "patterns": [
            "{age} {opener} {f1} and {f2}.",
            "{age} {opener} with {f1}, {f2}, and {f3}.",
            "{age} {opener} unwell with {f1} and {f2}."
        ]
    },

    "panic_hyperventilation": {
        "ages": ["22-year-old", "25-year-old", "29-year-old"],
        "openers": ["presents to ED", "is brought in", "attends ED"],
        "feature_groups": {
            "breathing": [
                "hyperventilating",
                "with sudden onset dyspnoea"
            ],
            "anxiety": [
                "with anxiety",
                "visibly distressed"
            ],
            "chest": [
                "with chest tightness",
                "with a sensation of not getting enough air"
            ],
            "peripheral": [
                "with tingling in the fingers",
                "with lightheadedness"
            ]
        },
        "patterns": [
            "{age} {opener} {f1} and {f2}.",
            "{age} {opener} with {f1}, {f2}, and {f3}.",
            "{age} {opener} anxious and {f1}, with {f2}."
        ]
    },

    "lactic_acidosis": {
        "ages": ["60-year-old", "65-year-old", "72-year-old"],
        "openers": ["presents to ED", "is brought in", "is admitted"],
        "feature_groups": {
            "sepsis_signs": [
                "febrile",
                "with rigors"
            ],
            "perfusion": [
                "hypotensive",
                "tachycardic"
            ],
            "severity": [
                "with increasing oxygen requirements",
                "with confusion"
            ],
            "context": [
                "with suspected sepsis",
                "appearing critically unwell"
            ]
        },
        "patterns": [
            "{age} {opener} {f1}, {f2}, and {f3}.",
            "{age} {opener} with {f1} and {f2}.",
            "{age} {opener} unwell with {f1}, {f2}, and {f3}."
        ]
    },

    "opioid_toxicity": {
        "ages": ["27-year-old", "32-year-old", "40-year-old"],
        "openers": ["is brought to ED", "is found collapsed", "presents"],
        "feature_groups": {
            "consciousness": [
                "with reduced consciousness",
                "with decreased responsiveness"
            ],
            "respiratory": [
                "with shallow respirations",
                "with bradypnoea"
            ],
            "tox_clues": [
                "with pinpoint pupils",
                "after suspected opioid use"
            ],
            "severity": [
                "difficult to rouse",
                "with low GCS"
            ]
        },
        "patterns": [
            "{age} {opener} {f1} and {f2}.",
            "{age} {opener} with {f1}, {f2}, and {f3}.",
            "{age} {opener} drowsy, with {f1} and {f2}."
        ]
    },

    "copd_chronic_retainer": {
        "ages": ["68-year-old", "72-year-old", "75-year-old"],
        "openers": ["presents", "attends ED", "is brought in"],
        "feature_groups": {
            "background": [
                "with chronic COPD",
                "with long-standing dyspnoea"
            ],
            "retention": [
                "with chronic hypercapnia",
                "known to retain CO2"
            ],
            "symptoms": [
                "with reduced exercise tolerance",
                "with chronic breathlessness"
            ],
            "airways": [
                "with productive cough",
                "with wheeze"
            ]
        },
        "patterns": [
            "{age} {opener} {f1} and {f2}.",
            "{age} {opener} with {f1}, {f2}, and {f3}.",
            "{age} {opener} with background {f1} and {f2}."
        ]
    },

    "acute_copd_exacerbation": {
        "ages": ["65-year-old", "68-year-old", "72-year-old"],
        "openers": ["presents", "is brought to ED", "attends ED"],
        "feature_groups": {
            "worsening": [
                "with worsening dyspnoea",
                "after several days of breathlessness"
            ],
            "airways": [
                "with productive cough",
                "with wheeze"
            ],
            "hypercapnia": [
                "with increasing somnolence",
                "with hypercapnic symptoms"
            ],
            "background": [
                "with known COPD",
                "with chronic respiratory disease"
            ]
        },
        "patterns": [
            "{age} {opener} {f1} and {f2}.",
            "{age} {opener} {f1}, {f2}, and {f3}.",
            "{age} {opener} with {f1} on a background of {f2}."
        ]
    },

    "sepsis_respiratory_alkalosis": {
        "ages": ["50-year-old", "55-year-old", "60-year-old"],
        "openers": ["presents to ED", "is brought to ED", "attends ED"],
        "feature_groups": {
            "infection": [
                "febrile",
                "with rigors"
            ],
            "respiratory": [
                "tachypnoeic",
                "with respiratory distress"
            ],
            "circulation": [
                "tachycardic",
                "hypotensive"
            ],
            "source": [
                "with pneumonia",
                "with suspected sepsis"
            ]
        },
        "patterns": [
            "{age} {opener} {f1}, {f2}, and {f3}.",
            "{age} {opener} with {f1} and {f2}.",
            "{age} {opener} unwell with {f1}, {f2}, and {f3}."
        ]
    },

    "salicylate_toxicity": {
        "ages": ["18-year-old", "22-year-old", "30-year-old"],
        "openers": ["presents to ED", "is brought to ED", "attends ED"],
        "feature_groups": {
            "tox_context": [
                "after possible overdose",
                "after ingestion of unknown tablets"
            ],
            "respiratory": [
                "tachypnoeic",
                "hyperventilating"
            ],
            "ent": [
                "with tinnitus",
                "complaining of ringing in the ears"
            ],
            "systemic": [
                "with nausea and vomiting",
                "with confusion"
            ]
        },
        "patterns": [
            "{age} {opener} {f1}, {f2}, and {f3}.",
            "{age} {opener} with {f1} and {f2}.",
            "{age} {opener} unwell with {f1}, {f2}, and {f3}."
        ]
    }
}


def generate_stem(archetype, min_features=2, max_features=3):
    bank = STEM_BANK[archetype]

    age = random.choice(bank["ages"])
    opener = random.choice(bank["openers"])
    pattern = random.choice(bank["patterns"])

    selected_features = []

    if "feature_groups" in bank:
        group_names = list(bank["feature_groups"].keys())
        n_to_use = min(len(group_names), random.randint(min_features, max_features))
        chosen_groups = random.sample(group_names, n_to_use)

        for group_name in chosen_groups:
            selected_features.append(random.choice(bank["feature_groups"][group_name]))
    else:
        n_to_use = min(len(bank["features"]), random.randint(min_features, max_features))
        selected_features = random.sample(bank["features"], n_to_use)

    while len(selected_features) < 3:
        selected_features.append(selected_features[-1])

    return pattern.format(
        age=age,
        opener=opener,
        f1=selected_features[0],
        f2=selected_features[1],
        f3=selected_features[2]
    )

#------------------------------------------------------------------------------
# GENERATORS
#------------------------------------------------------------------------------
    
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
        f"Low pH = acidemia. Low HCO3 indicates metabolic acidosis. "
        f"Winter’s formula predicts PaCO2 ~{expected_paco2:.1f} (±2); measured {paco2} is appropriate compensation. "
        f"Anion gap is {na} − ({cl} + {hco3}) = {ag} (raised), consistent with HAGMA such as DKA."
    )
    level = 3
    archetype = "dka"
    tier = tier_name(level)
        
    case = {
        "case_id": case_id,
        "title": "DKA (HAGMA with appropriate respiratory compensation)",
        "case_type": "ABG",
        "category": "metabolic_acidosis_hagma",
        "learning_objective": "Recognise high anion gap metabolic acidosis with appropriate respiratory compensation",
        "tags": ["dka", "hagma", "metabolic_acidosis"],
        "clinical_stem": generate_stem("dka"),
        "inputs": {
            "gas": {
                "ph": ph,
                "paco2_mmHg": paco2,
                "hco3_mmolL": hco3
            },
            "electrolytes": {
                "na_mmolL": na,
                "cl_mmolL": cl
            },
            "lactate_mmolL": lactate
        },
        "questions_flow": shuffle_question_options(
            advanced_question_flow([
                "DKA",
                "Diarrhoea",
                "Renal failure (uraemia)",
                "Toxic alcohol",
                "Salicylate toxicity"
            ])
        ),
        "answer_key": {
            "ph_status": derived_ph_status(ph),
            "primary_disorder": "Metabolic acidosis",
            "expected_compensation": {
                "rule": "Winter",
                "expected_paco2_mmHg": round(expected_paco2, 1),
                "acceptable_range_mmHg": [
                    round(expected_paco2 - 2, 1),
                    round(expected_paco2 + 2, 1)
                ]
            },
            "compensation": "Appropriate",
            "anion_gap_value": ag,
            "anion_gap_category": "Raised",
            "final_diagnosis": "DKA"
        },
        "explanation": explanation,
        "timing": {
            "timer_visible_by_default": False,
            "time_bonus_scope": "whole_case",
            "time_bonus_tiers_seconds_inclusive": [
                {"max_seconds": 30, "bonus": 20},
                {"max_seconds": 45, "bonus": 15},
                {"max_seconds": 60, "bonus": 10},
                {"max_seconds": 90, "bonus": 5},
                {"max_seconds": 999999, "bonus": 0}
            ]
        }
    }

    return attach_progression_metadata(case, level=3, archetype="dka")


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
    "40-year-old presents with low GCS and hypoventilation after being found collapsed at home."
]

    explanation = (
        f"Low pH = acidemia. High PaCO2 indicates a primary respiratory acidosis. "
        f"For acute respiratory acidosis, expected HCO3 is ~{expected_hco3:.1f}; measured {hco3} is appropriate acute compensation. "
        f"This pattern fits acute hypoventilation, such as opioid toxicity."
    )

    level = 2
    archetype = "opioid_toxicity"
    tier = tier_name(level)

    case = {
        "case_id": case_id,
        "title": "Opioid toxicity (acute respiratory acidosis)",
        "case_type": "ABG",
        "category": "respiratory_acidosis",
        "learning_objective": "Recognise acute respiratory acidosis due to hypoventilation with appropriate compensation",
        "tags": ["opioid", "respiratory_acidosis", "hypoventilation", "toxicology"],
        "clinical_stem": random.choice(stem_options),
        "inputs": {
            "gas": {
                "ph": ph,
                "paco2_mmHg": paco2,
                "hco3_mmolL": hco3
            },
            "electrolytes": {
                "na_mmolL": na,
                "cl_mmolL": cl
            },
            "lactate_mmolL": lactate
        },
        "questions_flow": shuffle_question_options(
    intermediate_question_flow([
        "Opioid toxicity",
        "COPD",
        "Pneumonia",
        "Neuromuscular weakness",
        "Sedative overdose"
    ])
),
        "answer_key": {
            "ph_status": "Acidemia",
            "primary_disorder": "Respiratory acidosis",
            "expected_compensation": {
                "rule": "Acute respiratory acidosis",
                "expected_hco3_mmolL": round(expected_hco3, 1),
                "acceptable_range_mmolL": [
                    round(expected_hco3 - 2, 1),
                    round(expected_hco3 + 2, 1)
                ]
            },
            "compensation": "Appropriate",
            "anion_gap_value": ag,
            "anion_gap_category": "Normal" if ag <= 16 else "Raised",
            "final_diagnosis": "Opioid toxicity"
        },
        "explanation": explanation,
        "timing": {
            "timer_visible_by_default": False,
            "time_bonus_scope": "whole_case",
            "time_bonus_tiers_seconds_inclusive": [
                {"max_seconds": 30, "bonus": 20},
                {"max_seconds": 45, "bonus": 15},
                {"max_seconds": 60, "bonus": 10},
                {"max_seconds": 90, "bonus": 5},
                {"max_seconds": 999999, "bonus": 0}
            ]
        }
    }

    return attach_progression_metadata(case, level=2, archetype="opioid_toxicity")

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
    "65-year-old with chronic respiratory symptoms presents with worsening shortness of breath over several days."
]

    explanation = (
        f"pH is low or near-normal with elevated PaCO2, indicating respiratory acidosis. "
        f"In chronic respiratory acidosis, HCO3 should rise by ~4 mmol/L per 10 mmHg PaCO2 above 40. "
        f"Expected HCO3 is ~{expected_hco3:.1f}; measured {hco3} is appropriately elevated, "
        f"consistent with chronic respiratory compensation seen in COPD."
    )

    level = 2
    archetype = "copd_chronic_retainer"
    tier = tier_name(level)

    case = {
        "case_id": case_id,
        "title": "COPD (chronic respiratory acidosis with metabolic compensation)",
        "case_type": "ABG",
        "category": "respiratory_acidosis",
        "learning_objective": "Recognise chronic respiratory acidosis with appropriate renal compensation",
        "tags": ["copd", "chronic_respiratory_acidosis", "compensation"],
        "clinical_stem": random.choice(stem_options),
        "inputs": {
            "gas": {
                "ph": ph,
                "paco2_mmHg": paco2,
                "hco3_mmolL": hco3
            },
            "electrolytes": {
                "na_mmolL": na,
                "cl_mmolL": cl
            },
            "lactate_mmolL": lactate
        },
       "questions_flow": shuffle_question_options(
    intermediate_question_flow([
        "COPD",
        "Opioid toxicity",
        "Neuromuscular weakness",
        "Sedative overdose",
        "Pneumonia"
    ])
),
        "answer_key": {
            "ph_status": "Acidemia" if ph < 7.35 else "Normal",
            "primary_disorder": "Respiratory acidosis",
            "expected_compensation": {
                "rule": "Chronic respiratory acidosis",
                "expected_hco3_mmolL": round(expected_hco3, 1),
                "acceptable_range_mmolL": [
                    round(expected_hco3 - 2, 1),
                    round(expected_hco3 + 2, 1)
                ]
            },
            "compensation": "Appropriate",
            "anion_gap_value": ag,
            "anion_gap_category": "Normal" if ag <= 16 else "Raised",
            "final_diagnosis": "COPD"
        },
        "explanation": explanation,
        "timing": {
            "timer_visible_by_default": False,
            "time_bonus_scope": "whole_case",
            "time_bonus_tiers_seconds_inclusive": [
                {"max_seconds": 30, "bonus": 20},
                {"max_seconds": 45, "bonus": 15},
                {"max_seconds": 60, "bonus": 10},
                {"max_seconds": 90, "bonus": 5},
                {"max_seconds": 999999, "bonus": 0}
            ]
        }
    }

    return attach_progression_metadata(case, level=2, archetype="copd_chronic_retainer")

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
    "35-year-old presents with weakness and dehydration after ongoing gastrointestinal fluid loss."
]

    explanation = (
        f"High pH indicates alkalemia. Elevated HCO3 indicates a primary metabolic alkalosis. "
        f"Expected compensatory PaCO2 is ~{expected_paco2:.1f}; measured {paco2} is appropriate, "
        f"supporting metabolic alkalosis with expected respiratory compensation, as seen with vomiting."
    )

    level = 2
    archetype = "vomiting_metabolic_alkalosis"
    tier = tier_name(level)
    
    case = {
        "case_id": case_id,
        "title": "Vomiting (metabolic alkalosis with respiratory compensation)",
        "case_type": "ABG",
        "category": "metabolic_alkalosis",
        "learning_objective": "Recognise metabolic alkalosis with appropriate respiratory compensation",
        "tags": ["vomiting", "metabolic_alkalosis", "chloride_responsive"],
        "clinical_stem": random.choice(stem_options),
        "inputs": {
            "gas": {
                "ph": ph,
                "paco2_mmHg": paco2,
                "hco3_mmolL": hco3
            },
            "electrolytes": {
                "na_mmolL": na,
                "cl_mmolL": cl
            },
            "lactate_mmolL": lactate
        },
       "questions_flow": shuffle_question_options(
    intermediate_question_flow([
        "Vomiting",
        "Diuretic use",
        "COPD",
        "Panic attack",
        "DKA"
    ])
),
        "answer_key": {
            "ph_status": "Alkalemia",
            "primary_disorder": "Metabolic alkalosis",
            "expected_compensation": {
                "rule": "Metabolic alkalosis compensation",
                "expected_paco2_mmHg": round(expected_paco2, 1),
                "acceptable_range_mmHg": [
                    round(expected_paco2 - 3, 1),
                    round(expected_paco2 + 3, 1)
                ]
            },
            "compensation": "Appropriate",
            "anion_gap_value": ag,
            "anion_gap_category": "Normal" if ag <= 16 else "Raised",
            "final_diagnosis": "Vomiting"
        },
        "explanation": explanation,
        "timing": {
            "timer_visible_by_default": False,
            "time_bonus_scope": "whole_case",
            "time_bonus_tiers_seconds_inclusive": [
                {"max_seconds": 30, "bonus": 20},
                {"max_seconds": 45, "bonus": 15},
                {"max_seconds": 60, "bonus": 10},
                {"max_seconds": 90, "bonus": 5},
                {"max_seconds": 999999, "bonus": 0}
            ]
        }
    }
    
    return attach_progression_metadata(case, level=2, archetype="vomiting_metabolic_alkalosis")

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
    "26-year-old presents with acute dyspnoea, dizziness, and hand paraesthesiae with a normal cardiorespiratory examination."
]

    explanation = (
        f"High pH indicates alkalemia. Low PaCO2 indicates a primary respiratory alkalosis. "
        f"In acute respiratory alkalosis, expected HCO3 is ~{expected_hco3:.1f}; measured {hco3} is appropriate, "
        f"consistent with acute hyperventilation such as panic."
    )
    
    level = 1
    archetype = "panic_hyperventilation"
    tier = tier_name(level)

    case = {
        "case_id": case_id,
        "title": "Panic / hyperventilation (acute respiratory alkalosis)",
        "case_type": "ABG",
        "category": "respiratory_alkalosis",
        "learning_objective": "Recognise acute respiratory alkalosis with appropriate metabolic compensation",
        "tags": ["panic", "hyperventilation", "respiratory_alkalosis"],
        "clinical_stem": random.choice(stem_options),
        "inputs": {
            "gas": {
                "ph": ph,
                "paco2_mmHg": paco2,
                "hco3_mmolL": hco3
            },
            "electrolytes": {
                "na_mmolL": na,
                "cl_mmolL": cl
            },
            "lactate_mmolL": lactate
        },
        "questions_flow": shuffle_question_options(
    beginner_question_flow([
        "Panic attack / hyperventilation",
        "Pulmonary embolism",
        "COPD",
        "Vomiting",
        "DKA"
    ])
),
        "answer_key": {
            "ph_status": "Alkalemia",
            "primary_disorder": "Respiratory alkalosis",
            "expected_compensation": {
                "rule": "Acute respiratory alkalosis",
                "expected_hco3_mmolL": round(expected_hco3, 1),
                "acceptable_range_mmolL": [
                    round(expected_hco3 - 2, 1),
                    round(expected_hco3 + 2, 1)
                ]
            },
            "compensation": "Appropriate",
            "anion_gap_value": ag,
            "anion_gap_category": "Normal" if ag <= 16 else "Raised",
            "final_diagnosis": "Panic attack / hyperventilation"
        },
        "explanation": explanation,
        "timing": {
            "timer_visible_by_default": False,
            "time_bonus_scope": "whole_case",
            "time_bonus_tiers_seconds_inclusive": [
                {"max_seconds": 30, "bonus": 20},
                {"max_seconds": 45, "bonus": 15},
                {"max_seconds": 60, "bonus": 10},
                {"max_seconds": 90, "bonus": 5},
                {"max_seconds": 999999, "bonus": 0}
            ]
        }
    }

    return attach_progression_metadata(case, level=1, archetype="panic_hyperventilation")

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
        "29-year-old presents with light-headedness and dehydration after several days of gastroenteritis symptoms."
    ]

    ph_label = derived_ph_status(ph)

    if ph_label == "Acidemia":
        ph_text = "Low pH indicates acidemia."
    elif ph_label == "Alkalemia":
        ph_text = "High pH indicates alkalemia."
    else:
        ph_text = "The pH is in the normal range, but the low HCO3 still indicates a primary metabolic acidosis with respiratory compensation."

    explanation = (
        f"{ph_text} Low HCO3 indicates a primary metabolic acidosis. "
        f"Winter’s formula predicts PaCO2 ~{expected_paco2:.1f} (±2); measured {paco2} is appropriate compensation. "
        f"Anion gap is {na} − ({cl} + {hco3}) = {ag}, which is normal, consistent with NAGMA such as diarrhoea."
    )

    level = 3
    archetype = "diarrhoea_nagma"
    tier = tier_name(level)

    case = {
        "case_id": case_id,
        "title": "Diarrhoea (normal anion gap metabolic acidosis)",
        "case_type": "ABG",
        "category": "metabolic_acidosis_nagma",
        "learning_objective": "Recognise normal anion gap metabolic acidosis with appropriate respiratory compensation",
        "tags": ["diarrhoea", "nagma", "metabolic_acidosis"],
        "clinical_stem": random.choice(stem_options),
        "inputs": {
            "gas": {
                "ph": ph,
                "paco2_mmHg": paco2,
                "hco3_mmolL": hco3
            },
            "electrolytes": {
                "na_mmolL": na,
                "cl_mmolL": cl
            },
            "lactate_mmolL": lactate
        },
        "questions_flow": shuffle_question_options(
            advanced_question_flow([
                "Diarrhoea",
                "DKA",
                "Vomiting",
                "Renal failure (uraemia)",
                "Toxic alcohol"
            ])
        ),
        "answer_key": {
            "ph_status": derived_ph_status(ph),
            "primary_disorder": "Metabolic acidosis",
            "expected_compensation": {
                "rule": "Winter",
                "expected_paco2_mmHg": round(expected_paco2, 1),
                "acceptable_range_mmHg": [
                    round(expected_paco2 - 2, 1),
                    round(expected_paco2 + 2, 1)
                ]
            },
            "compensation": "Appropriate",
            "anion_gap_value": ag,
            "anion_gap_category": "Normal",
            "final_diagnosis": "Diarrhoea"
        },
        "explanation": explanation,
        "timing": {
            "timer_visible_by_default": False,
            "time_bonus_scope": "whole_case",
            "time_bonus_tiers_seconds_inclusive": [
                {"max_seconds": 30, "bonus": 20},
                {"max_seconds": 45, "bonus": 15},
                {"max_seconds": 60, "bonus": 10},
                {"max_seconds": 90, "bonus": 5},
                {"max_seconds": 999999, "bonus": 0}
            ]
        }
    }
    
    return attach_progression_metadata(case, level=3, archetype="diarrhoea_nagma")
    
def generate_salicylate_case(case_id):
    # Mixed disorder:
    # Respiratory alkalosis + HAGMA

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
    "27-year-old presents with nausea, hyperventilation, and tinnitus after ingesting a large quantity of tablets."
]

    explanation = (
        f"Both PaCO2 and HCO3 are low. This is not explained by a single primary disorder alone. "
        f"The low PaCO2 indicates a respiratory alkalosis, while the low HCO3 with raised anion gap "
        f"({na} − ({cl} + {hco3}) = {ag}) indicates a high anion gap metabolic acidosis. "
        f"This is a mixed respiratory alkalosis and metabolic acidosis, classic for salicylate toxicity."
    )
    
    level = 4
    archetype = "salicylate_toxicity"
    tier = tier_name(level, is_mixed=True)

    case = {
        "case_id": case_id,
        "title": "Salicylate toxicity (mixed respiratory alkalosis + HAGMA)",
        "case_type": "ABG",
        "category": "mixed_disorder",
        "learning_objective": "Recognise the mixed respiratory alkalosis and high anion gap metabolic acidosis of salicylate toxicity",
        "tags": ["salicylate", "mixed_disorder", "respiratory_alkalosis", "hagma", "toxicology"],
        "clinical_stem": random.choice(stem_options),
        "inputs": {
            "gas": {
                "ph": ph,
                "paco2_mmHg": paco2,
                "hco3_mmolL": hco3
            },
            "electrolytes": {
                "na_mmolL": na,
                "cl_mmolL": cl
            },
            "lactate_mmolL": lactate
        },
        "questions_flow": shuffle_question_options(
    advanced_question_flow([
        "Salicylate toxicity",
        "DKA",
        "Diarrhoea",
        "Panic attack / hyperventilation",
        "Renal failure (uraemia)"
    ])
),
        "answer_key": {
            "ph_status": (
                "Acidemia" if ph < 7.35 else
                "Alkalemia" if ph > 7.45 else
                "Normal"
            ),
            "primary_disorder": "Mixed disorder",
            "expected_compensation": {
                "rule": "Mixed disorder present",
                "note": "Low PaCO2 and low HCO3 are due to two primary processes: respiratory alkalosis and HAGMA"
            },
            "compensation": "Inappropriate",
            "anion_gap_value": ag,
            "anion_gap_category": "Raised",
            "final_diagnosis": "Salicylate toxicity"
        },
        "explanation": explanation,
        "timing": {
            "timer_visible_by_default": False,
            "time_bonus_scope": "whole_case",
            "time_bonus_tiers_seconds_inclusive": [
                {"max_seconds": 30, "bonus": 20},
                {"max_seconds": 45, "bonus": 15},
                {"max_seconds": 60, "bonus": 10},
                {"max_seconds": 90, "bonus": 5},
                {"max_seconds": 999999, "bonus": 0}
            ]
        }
    }
    
    return attach_progression_metadata(case, level=4, archetype="salicylate_toxicity", is_mixed=True)
    
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
            "gas": {
                "ph": ph,
                "paco2_mmHg": paco2,
                "hco3_mmolL": hco3
            },
            "electrolytes": {
                "na_mmolL": na,
                "cl_mmolL": cl
            },
            "lactate_mmolL": lactate
        },

        "questions_flow": shuffle_question_options(
            advanced_question_flow([
                "Lactic acidosis",
                "DKA",
                "Renal failure (uraemia)",
                "Toxic alcohol",
                "Salicylate toxicity"
            ])
        ),

        "answer_key": {
            "ph_status": derived_ph_status(ph),
            "primary_disorder": "Metabolic acidosis",
            "expected_compensation": {
                "rule": "Winter",
                "expected_paco2_mmHg": round(expected_paco2, 1),
                "acceptable_range_mmHg": [
                    round(expected_paco2 - 2, 1),
                    round(expected_paco2 + 2, 1)
                ]
            },
            "compensation": "Appropriate",
            "anion_gap_value": ag,
            "anion_gap_category": "Raised",
            "final_diagnosis": "Lactic acidosis"
        },

        "explanation": "Sepsis commonly causes high anion gap metabolic acidosis due to lactate accumulation."
    }

    return attach_progression_metadata(case, level=3, archetype="lactic_acidosis")
    
    
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
            "gas": {
                "ph": ph,
                "paco2_mmHg": paco2,
                "hco3_mmolL": hco3
            },
            "electrolytes": {
                "na_mmolL": na,
                "cl_mmolL": cl
            }
        },

        "questions_flow": shuffle_question_options(
            intermediate_question_flow([
                "COPD exacerbation",
                "Opioid toxicity",
                "Neuromuscular weakness",
                "Asthma",
                "Pneumonia"
            ])
        ),

        "answer_key": {
            "ph_status": derived_ph_status(ph),
            "primary_disorder": "Respiratory acidosis",
            "compensation": "Chronic with acute worsening",
            "anion_gap_value": calc_anion_gap(na, cl, hco3),
            "anion_gap_category": "Normal",
            "final_diagnosis": "COPD exacerbation"
        },

        "explanation": "COPD exacerbations cause acute rises in CO₂ on a background of chronic respiratory acidosis."
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
            "gas": {
                "ph": ph,
                "paco2_mmHg": paco2,
                "hco3_mmolL": hco3
            },
            "electrolytes": {
                "na_mmolL": na,
                "cl_mmolL": cl
            }
        },

        "questions_flow": shuffle_question_options(
            intermediate_question_flow([
                "Sepsis",
                "Panic attack",
                "Pain",
                "Pulmonary embolism",
                "Pregnancy"
            ])
        ),

        "answer_key": {
            "ph_status": derived_ph_status(ph),
            "primary_disorder": "Respiratory alkalosis",
            "compensation": "None",
            "anion_gap_value": calc_anion_gap(na, cl, hco3),
            "anion_gap_category": "Normal",
            "final_diagnosis": "Sepsis"
        },

        "explanation": "Sepsis commonly causes respiratory alkalosis due to hyperventilation."
    }

    return attach_progression_metadata(case, level=2, archetype="sepsis_respiratory_alkalosis")
    
    
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
            "gas": {
                "ph": ph,
                "paco2_mmHg": paco2,
                "hco3_mmolL": hco3
            },
            "electrolytes": {
                "na_mmolL": na,
                "cl_mmolL": cl
            }
        },

        "questions_flow": shuffle_question_options(
            advanced_question_flow([
                "DKA with vomiting",
                "DKA",
                "Vomiting",
                "Salicylate toxicity",
                "Renal failure"
            ])
        ),

        "answer_key": {
            "ph_status": derived_ph_status(ph),
            "primary_disorder": "Mixed metabolic disorder",
            "anion_gap_value": ag,
            "anion_gap_category": "Raised",
            "final_diagnosis": "DKA with vomiting"
        },

        "explanation": "DKA causes high anion gap metabolic acidosis while vomiting causes metabolic alkalosis."
    }

    return attach_progression_metadata(case, level=4, archetype="dka_vomiting", is_mixed=True)
    
cases = []

for i in range(5):
    cases.append(generate_valid_case(generate_dka_case, f"DKA_{i+1:03d}"))

for i in range(5):
    cases.append(generate_valid_case(generate_opioid_case, f"OPIOID_{i+1:03d}"))

for i in range(5):
    cases.append(generate_valid_case(generate_copd_case, f"COPD_{i+1:03d}"))

for i in range(5):
    cases.append(generate_valid_case(generate_vomiting_case, f"VOMITING_{i+1:03d}"))

for i in range(5):
    cases.append(generate_valid_case(generate_panic_case, f"PANIC_{i+1:03d}"))

for i in range(5):
    cases.append(generate_valid_case(generate_diarrhoea_case, f"DIARRHOEA_{i+1:03d}"))

for i in range(5):
    cases.append(generate_valid_case(generate_salicylate_case, f"SALICYLATE_{i+1:03d}"))
    
for i in range(5):
    cases.append(generate_valid_case(generate_lactate_case, f"LACTATE_{i+1:03d}"))

for i in range(5):
    cases.append(generate_valid_case(generate_acute_copd_case, f"ACUTE_COPD_{i+1:03d}"))

for i in range(5):
    cases.append(generate_valid_case(generate_sepsis_case, f"SEPSIS_{i+1:03d}"))

for i in range(5):
    cases.append(generate_valid_case(generate_dka_vomiting_case, f"DKA_VOMIT_{i+1:03d}"))

validation_errors = validate_cases(cases)

if validation_errors:
    print("Validation failed:\n")
    for err in validation_errors:
        print(f"- {err}")
    raise ValueError(f"{len(validation_errors)} validation error(s) found.")

random.shuffle(cases)

output = {
    "cases": cases
}

import os

output_path = os.path.join(os.path.dirname(__file__), "..", "abg_cases.json")

with open(output_path, "w") as f:
    json.dump(output, f, indent=2)

print_generation_report(cases)

print(f"\nGenerated {len(cases)} cases successfully with validation passed")