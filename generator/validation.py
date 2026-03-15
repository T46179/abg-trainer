"""Validation rules for generated ABG cases.

This module checks question-flow structure, physiologic plausibility,
archetype-specific expectations, duplicate IDs, and retry logic for case
generation until a valid case is produced.
"""

from .physiology import (
    anion_gap_category,
    calc_anion_gap,
    chronic_respiratory_acidosis_expected_hco3,
    derived_ph_status,
    estimate_ph,
    in_range,
    metabolic_alkalosis_expected_paco2,
    respiratory_alkalosis_expected_hco3_acute,
    winters_expected_paco2,
)


def validate_question_flow(case):
    errors = []
    question_flow = case.get("questions_flow", [])
    keys = [question.get("key") for question in question_flow]

    expected_by_level = {
        1: [
            ["ph_status", "primary_disorder"],
            ["ph_status", "primary_disorder", "final_diagnosis"],
        ],
        2: [
            ["ph_status", "primary_disorder", "compensation"],
            ["ph_status", "primary_disorder", "compensation", "final_diagnosis"],
        ],
        3: [
            ["ph_status", "primary_disorder", "compensation", "anion_gap"],
            ["ph_status", "primary_disorder", "compensation", "anion_gap", "final_diagnosis"],
        ],
        4: [
            ["ph_status", "primary_disorder", "compensation", "anion_gap"],
            ["ph_status", "primary_disorder", "compensation", "anion_gap", "final_diagnosis"],
            ["ph_status", "primary_disorder", "compensation", "anion_gap", "additional_metabolic_process"],
            ["ph_status", "primary_disorder", "compensation", "anion_gap", "additional_metabolic_process", "final_diagnosis"],
        ],
    }

    difficulty = case.get("difficulty_level")
    expected = expected_by_level.get(difficulty)

    if expected and keys not in expected:
        errors.append(
            f"questions_flow keys {keys} do not match expected flows {expected} for difficulty {difficulty}"
        )

    return errors


def validate_case(case):
    errors = []
    case_id = case.get("case_id", "<missing_case_id>")
    archetype = case.get("archetype")

    gas = case.get("inputs", {}).get("gas", {})
    electrolytes = case.get("inputs", {}).get("electrolytes", {})
    answer_key = case.get("answer_key", {})
    expected_compensation = answer_key.get("expected_compensation", {})

    ph = gas.get("ph")
    paco2 = gas.get("paco2_mmHg")
    hco3 = gas.get("hco3_mmolL")
    na = electrolytes.get("na_mmolL")
    cl = electrolytes.get("cl_mmolL")

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

    derived_status = derived_ph_status(ph)
    if answer_key.get("ph_status") != derived_status:
        errors.append(
            f"{case_id}: ph_status mismatch (stored '{answer_key.get('ph_status')}', derived '{derived_status}')"
        )

    ag = calc_anion_gap(na, cl, hco3)
    stored_ag = answer_key.get("anion_gap_value")
    if stored_ag is None:
        errors.append(f"{case_id}: missing answer_key.anion_gap_value")
    elif abs(stored_ag - ag) > 0.15:
        errors.append(f"{case_id}: anion gap mismatch (stored {stored_ag}, derived {ag})")

    derived_ag_category = anion_gap_category(ag)
    if answer_key.get("anion_gap_category") != derived_ag_category:
        errors.append(
            f"{case_id}: anion gap category mismatch (stored '{answer_key.get('anion_gap_category')}', derived '{derived_ag_category}')"
        )

    estimated = estimate_ph(hco3, paco2)
    if abs(estimated - ph) > 0.06:
        errors.append(
            f"{case_id}: pH inconsistent with HCO3/PaCO2 (stored {ph}, estimated {estimated})"
        )

    if archetype == "dka":
        expected_paco2 = round(winters_expected_paco2(hco3), 1)
        low = round(expected_paco2 - 2, 1)
        high = round(expected_paco2 + 2, 1)

        if answer_key.get("primary_disorder") != "Metabolic acidosis":
            errors.append(f"{case_id}: DKA should be metabolic acidosis")
        if answer_key.get("final_diagnosis") != "DKA":
            errors.append(f"{case_id}: DKA final diagnosis mismatch")
        if ag <= 16:
            errors.append(f"{case_id}: DKA should have raised anion gap, got {ag}")
        if not in_range(paco2, low, high):
            errors.append(f"{case_id}: DKA PaCO2 outside Winter range ({paco2} not in {low}â€“{high})")
        if expected_compensation.get("rule") != "Winter":
            errors.append(f"{case_id}: DKA expected rule should be Winter")

    elif archetype == "diarrhoea_nagma":
        expected_paco2 = round(winters_expected_paco2(hco3), 1)
        low = round(expected_paco2 - 2, 1)
        high = round(expected_paco2 + 2, 1)

        if answer_key.get("primary_disorder") != "Metabolic acidosis":
            errors.append(f"{case_id}: diarrhoea should be metabolic acidosis")
        if answer_key.get("final_diagnosis") != "Diarrhoea":
            errors.append(f"{case_id}: diarrhoea final diagnosis mismatch")
        if ag > 16:
            errors.append(f"{case_id}: diarrhoea should be normal AG, got {ag}")
        if not in_range(paco2, low, high):
            errors.append(f"{case_id}: diarrhoea PaCO2 outside Winter range ({paco2} not in {low}â€“{high})")

    elif archetype == "opioid_toxicity":
        expected_hco3 = round(24 + ((paco2 - 40) / 10), 1)
        low = round(expected_hco3 - 2, 1)
        high = round(expected_hco3 + 2, 1)

        if answer_key.get("primary_disorder") != "Respiratory acidosis":
            errors.append(f"{case_id}: opioid case should be respiratory acidosis")
        if answer_key.get("final_diagnosis") != "Opioid toxicity":
            errors.append(f"{case_id}: opioid final diagnosis mismatch")
        if paco2 <= 40:
            errors.append(f"{case_id}: opioid case should have elevated PaCO2")
        if not in_range(hco3, low, high):
            errors.append(
                f"{case_id}: opioid HCO3 outside acute respiratory acidosis range ({hco3} not in {low}â€“{high})"
            )

    elif archetype == "copd_chronic_retainer":
        expected_hco3 = round(chronic_respiratory_acidosis_expected_hco3(paco2), 1)
        low = round(expected_hco3 - 2, 1)
        high = round(expected_hco3 + 2, 1)

        if answer_key.get("primary_disorder") != "Respiratory acidosis":
            errors.append(f"{case_id}: COPD case should be respiratory acidosis")
        if answer_key.get("final_diagnosis") != "COPD":
            errors.append(f"{case_id}: COPD final diagnosis mismatch")
        if paco2 <= 40:
            errors.append(f"{case_id}: COPD case should have elevated PaCO2")
        if not in_range(hco3, low, high):
            errors.append(
                f"{case_id}: COPD HCO3 outside chronic respiratory acidosis range ({hco3} not in {low}â€“{high})"
            )

    elif archetype == "vomiting_metabolic_alkalosis":
        expected_paco2 = round(metabolic_alkalosis_expected_paco2(hco3), 1)
        low = round(expected_paco2 - 3, 1)
        high = round(expected_paco2 + 3, 1)

        if answer_key.get("primary_disorder") != "Metabolic alkalosis":
            errors.append(f"{case_id}: vomiting case should be metabolic alkalosis")
        if answer_key.get("final_diagnosis") != "Vomiting":
            errors.append(f"{case_id}: vomiting final diagnosis mismatch")
        if ph <= 7.45:
            errors.append(f"{case_id}: vomiting case should be alkalemic")
        if not in_range(paco2, low, high):
            errors.append(
                f"{case_id}: vomiting PaCO2 outside expected compensation range ({paco2} not in {low}â€“{high})"
            )

    elif archetype == "panic_hyperventilation":
        expected_hco3 = round(respiratory_alkalosis_expected_hco3_acute(paco2), 1)
        low = round(expected_hco3 - 2, 1)
        high = round(expected_hco3 + 2, 1)

        if answer_key.get("primary_disorder") != "Respiratory alkalosis":
            errors.append(f"{case_id}: panic case should be respiratory alkalosis")
        if answer_key.get("final_diagnosis") != "Panic attack / hyperventilation":
            errors.append(f"{case_id}: panic final diagnosis mismatch")
        if paco2 >= 40:
            errors.append(f"{case_id}: panic case should have low PaCO2")
        if ph <= 7.45:
            errors.append(f"{case_id}: panic case should be alkalemic")
        if not in_range(hco3, low, high):
            errors.append(
                f"{case_id}: panic HCO3 outside acute respiratory alkalosis range ({hco3} not in {low}â€“{high})"
            )

    elif archetype == "salicylate_toxicity":
        if answer_key.get("primary_disorder") != "Metabolic acidosis":
            errors.append(
                f"{case_id}: salicylate case should be classified as metabolic acidosis in this framework"
            )
        if answer_key.get("final_diagnosis") != "Salicylate toxicity":
            errors.append(f"{case_id}: salicylate final diagnosis mismatch")
        if paco2 >= 40:
            errors.append(f"{case_id}: salicylate case should have low PaCO2")
        if hco3 >= 22:
            errors.append(f"{case_id}: salicylate case should have low HCO3")
        if ag <= 16:
            errors.append(f"{case_id}: salicylate case should have raised AG, got {ag}")
        if answer_key.get("compensation") != "Inappropriate":
            errors.append(f"{case_id}: salicylate compensation should be inappropriate")

    elif archetype == "lactic_acidosis":
        expected_paco2 = round(winters_expected_paco2(hco3), 1)
        low = round(expected_paco2 - 2, 1)
        high = round(expected_paco2 + 2, 1)

        if answer_key.get("primary_disorder") != "Metabolic acidosis":
            errors.append(f"{case_id}: lactate case should be metabolic acidosis")
        if answer_key.get("final_diagnosis") != "Lactic acidosis":
            errors.append(f"{case_id}: lactate final diagnosis mismatch")
        if ag <= 16:
            errors.append(f"{case_id}: lactate case should have raised anion gap, got {ag}")
        if not in_range(paco2, low, high):
            errors.append(f"{case_id}: lactate PaCO2 outside Winter range ({paco2} not in {low}â€“{high})")
        if expected_compensation.get("rule") != "Winter":
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

    for _attempt in range(1, max_attempts + 1):
        case = generator_fn(case_id)
        errors = validate_case(case)

        if not errors:
            return case

        last_errors = errors

    raise ValueError(
        f"Failed to generate valid case for {case_id} after {max_attempts} attempts.\n"
        + "\n".join(last_errors)
    )
