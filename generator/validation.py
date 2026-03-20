"""Validation rules for generated ABG cases.

This module checks question-flow structure, physiologic plausibility,
archetype-specific expectations, duplicate IDs, and retry logic for case
generation until a valid case is produced.
"""

from .config import OPTIONS
from .generators.common import diagnosis_labels_conflict, normalize_diagnosis_option
from .physiology import (
    acute_respiratory_acidosis_expected_hco3,
    anion_gap_category,
    calc_anion_gap,
    chronic_respiratory_acidosis_expected_hco3,
    derived_ph_status,
    estimate_ph,
    hagma_bicarbonate_preservation,
    in_range,
    isolated_hagma_expected_hco3,
    metabolic_alkalosis_expected_paco2,
    respiratory_alkalosis_expected_hco3_acute,
    winters_expected_paco2,
)


def get_case_optional_value(inputs, container, key, legacy_key=None):
    container_values = inputs.get(container, {})
    if isinstance(container_values, dict) and container_values.get(key) is not None:
        return container_values.get(key)
    if legacy_key:
        return inputs.get(legacy_key)
    return None


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


def validate_final_diagnosis_options(case):
    errors = []
    case_id = case.get("case_id", "<missing_case_id>")
    final_diagnosis = case.get("answer_key", {}).get("final_diagnosis")

    for question in case.get("questions_flow", []):
        if question.get("key") != "final_diagnosis":
            continue

        options = question.get("options", [])
        if final_diagnosis not in options:
            errors.append(f"{case_id}: final_diagnosis options missing correct answer '{final_diagnosis}'")

        for index, option in enumerate(options):
            normalized_option = normalize_diagnosis_option(option)

            for other_option in options[index + 1:]:
                if diagnosis_labels_conflict(option, other_option):
                    errors.append(
                        f"{case_id}: overlapping final_diagnosis options '{option}' and '{other_option}'"
                    )
                elif normalized_option == normalize_diagnosis_option(other_option):
                    errors.append(
                        f"{case_id}: duplicate normalized final_diagnosis options '{option}' and '{other_option}'"
                    )

    return errors


def validate_case(case):
    errors = []
    case_id = case.get("case_id", "<missing_case_id>")
    archetype = case.get("archetype")

    inputs = case.get("inputs", {})
    gas = inputs.get("gas", {})
    electrolytes = inputs.get("electrolytes", {})
    answer_key = case.get("answer_key", {})
    expected_compensation = answer_key.get("expected_compensation", {})

    if not isinstance(inputs, dict):
        return [f"{case_id}: inputs should be an object"]
    if not isinstance(gas, dict):
        errors.append(f"{case_id}: inputs.gas should be an object")
    if not isinstance(electrolytes, dict):
        errors.append(f"{case_id}: inputs.electrolytes should be an object")

    other = inputs.get("other")
    if other is not None and not isinstance(other, dict):
        errors.append(f"{case_id}: inputs.other should be an object when present")

    if errors:
        return errors

    legacy_lactate = inputs.get("lactate_mmolL")
    canonical_lactate = get_case_optional_value(inputs, "other", "lactate_mmolL")
    if (
        legacy_lactate is not None
        and canonical_lactate is not None
        and abs(legacy_lactate - canonical_lactate) > 0.05
    ):
        errors.append(
            f"{case_id}: legacy lactate ({legacy_lactate}) and inputs.other.lactate_mmolL ({canonical_lactate}) disagree"
        )

    ph = gas.get("ph")
    paco2 = gas.get("paco2_mmHg")
    hco3 = gas.get("hco3_mmolL")
    na = electrolytes.get("na_mmolL")
    cl = electrolytes.get("cl_mmolL")
    glucose = electrolytes.get("glucose_mmolL")

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

    if case.get("difficulty_level") == 4 and glucose is None:
        errors.append(f"{case_id}: master-level cases should include glucose_mmolL")

    compensation_steps = [question for question in case.get("questions_flow", []) if question.get("key") == "compensation"]
    if compensation_steps and answer_key.get("compensation") not in OPTIONS["compensation"]:
        errors.append(
            f"{case_id}: compensation answer '{answer_key.get('compensation')}' must be one of {OPTIONS['compensation']}"
        )

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
            errors.append(f"{case_id}: DKA PaCO2 outside Winter range ({paco2} not in {low}-{high})")
        if expected_compensation.get("rule") != "Winter":
            errors.append(f"{case_id}: DKA expected rule should be Winter")

    elif archetype == "alcoholic_ketoacidosis":
        expected_paco2 = round(winters_expected_paco2(hco3), 1)
        low = round(expected_paco2 - 2, 1)
        high = round(expected_paco2 + 2, 1)

        if answer_key.get("primary_disorder") != "Metabolic acidosis":
            errors.append(f"{case_id}: alcoholic ketoacidosis should be metabolic acidosis")
        if answer_key.get("final_diagnosis") != "Alcoholic ketoacidosis":
            errors.append(f"{case_id}: alcoholic ketoacidosis final diagnosis mismatch")
        if ag <= 16:
            errors.append(f"{case_id}: alcoholic ketoacidosis should have raised anion gap, got {ag}")
        if not in_range(paco2, low, high):
            errors.append(
                f"{case_id}: alcoholic ketoacidosis PaCO2 outside Winter range ({paco2} not in {low}-{high})"
            )
        if expected_compensation.get("rule") != "Winter":
            errors.append(f"{case_id}: alcoholic ketoacidosis expected rule should be Winter")

    elif archetype == "starvation_ketosis":
        expected_paco2 = round(winters_expected_paco2(hco3), 1)
        low = round(expected_paco2 - 2, 1)
        high = round(expected_paco2 + 2, 1)

        if answer_key.get("primary_disorder") != "Metabolic acidosis":
            errors.append(f"{case_id}: starvation ketosis should be metabolic acidosis")
        if answer_key.get("final_diagnosis") != "Starvation ketosis":
            errors.append(f"{case_id}: starvation ketosis final diagnosis mismatch")
        if ag <= 16:
            errors.append(f"{case_id}: starvation ketosis should have at least a mildly raised anion gap, got {ag}")
        if not in_range(paco2, low, high):
            errors.append(
                f"{case_id}: starvation ketosis PaCO2 outside Winter range ({paco2} not in {low}-{high})"
            )
        if expected_compensation.get("rule") != "Winter":
            errors.append(f"{case_id}: starvation ketosis expected rule should be Winter")
        if glucose is None:
            errors.append(f"{case_id}: starvation ketosis should include glucose")
        elif not in_range(glucose, 3.2, 6.2):
            errors.append(f"{case_id}: starvation ketosis glucose should stay normal/low-normal, got {glucose}")

        lactate = get_case_optional_value(inputs, "other", "lactate_mmolL", legacy_key="lactate_mmolL")
        if lactate is not None and lactate > 2.2:
            errors.append(f"{case_id}: starvation ketosis lactate should stay absent or mildly elevated, got {lactate}")

    elif archetype == "toxic_alcohol":
        expected_paco2 = round(winters_expected_paco2(hco3), 1)
        low = round(expected_paco2 - 2, 1)
        high = round(expected_paco2 + 2, 1)

        if answer_key.get("primary_disorder") != "Metabolic acidosis":
            errors.append(f"{case_id}: toxic alcohol should be metabolic acidosis")
        if answer_key.get("final_diagnosis") != "Toxic alcohol":
            errors.append(f"{case_id}: toxic alcohol final diagnosis mismatch")
        if ag <= 16:
            errors.append(f"{case_id}: toxic alcohol should have raised anion gap, got {ag}")
        if not in_range(paco2, low, high):
            errors.append(f"{case_id}: toxic alcohol PaCO2 outside Winter range ({paco2} not in {low}-{high})")
        if expected_compensation.get("rule") != "Winter":
            errors.append(f"{case_id}: toxic alcohol expected rule should be Winter")

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
            errors.append(f"{case_id}: diarrhoea PaCO2 outside Winter range ({paco2} not in {low}-{high})")

    elif archetype == "simple_nagma":
        expected_paco2 = round(winters_expected_paco2(hco3), 1)
        low = round(expected_paco2 - 2, 1)
        high = round(expected_paco2 + 2, 1)

        if answer_key.get("primary_disorder") != "Metabolic acidosis":
            errors.append(f"{case_id}: simple NAGMA should be metabolic acidosis")
        if answer_key.get("final_diagnosis") != "GI bicarbonate loss":
            errors.append(f"{case_id}: simple NAGMA final diagnosis mismatch")
        if ph >= 7.35:
            errors.append(f"{case_id}: simple NAGMA should remain acidaemic for beginner clarity")
        if ag > 16:
            errors.append(f"{case_id}: simple NAGMA should have a normal anion gap, got {ag}")
        if cl < 104:
            errors.append(f"{case_id}: simple NAGMA should be relatively hyperchloraemic, got Cl {cl}")
        if not in_range(paco2, low, high):
            errors.append(f"{case_id}: simple NAGMA PaCO2 outside Winter range ({paco2} not in {low}-{high})")
        if expected_compensation.get("rule") != "Winter":
            errors.append(f"{case_id}: simple NAGMA expected rule should be Winter")

    elif archetype == "simple_metabolic_alkalosis":
        expected_paco2 = round(metabolic_alkalosis_expected_paco2(hco3), 1)
        low = round(expected_paco2 - 3, 1)
        high = round(expected_paco2 + 3, 1)

        if answer_key.get("primary_disorder") != "Metabolic alkalosis":
            errors.append(f"{case_id}: simple metabolic alkalosis should be metabolic alkalosis")
        if answer_key.get("final_diagnosis") != "Gastric losses":
            errors.append(f"{case_id}: simple metabolic alkalosis final diagnosis mismatch")
        if ph <= 7.45:
            errors.append(f"{case_id}: simple metabolic alkalosis should remain alkalemic for beginner clarity")
        if hco3 <= 26:
            errors.append(f"{case_id}: simple metabolic alkalosis should have elevated bicarbonate")
        if cl > 103:
            errors.append(f"{case_id}: simple metabolic alkalosis should be relatively hypochloraemic, got Cl {cl}")
        if not in_range(paco2, low, high):
            errors.append(
                f"{case_id}: simple metabolic alkalosis PaCO2 outside compensation range ({paco2} not in {low}-{high})"
            )
        if expected_compensation.get("rule") != "Metabolic alkalosis compensation":
            errors.append(f"{case_id}: simple metabolic alkalosis expected rule should be metabolic alkalosis compensation")

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
                f"{case_id}: opioid HCO3 outside acute respiratory acidosis range ({hco3} not in {low}-{high})"
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
                f"{case_id}: COPD HCO3 outside chronic respiratory acidosis range ({hco3} not in {low}-{high})"
            )

    elif archetype == "acute_copd_exacerbation":
        expected_chronic_hco3 = round(chronic_respiratory_acidosis_expected_hco3(paco2), 1)
        chronic_low = round(expected_chronic_hco3 - 2, 1)
        chronic_high = round(expected_chronic_hco3 + 2, 1)
        expected_acute_hco3 = round(acute_respiratory_acidosis_expected_hco3(paco2), 1)
        acute_high = round(expected_acute_hco3 + 2, 1)

        if answer_key.get("primary_disorder") != "Respiratory acidosis":
            errors.append(f"{case_id}: acute COPD case should be respiratory acidosis")
        if answer_key.get("final_diagnosis") != "COPD exacerbation":
            errors.append(f"{case_id}: acute COPD final diagnosis mismatch")
        if answer_key.get("compensation") != "Inappropriate":
            errors.append(f"{case_id}: acute COPD compensation should be inappropriate under the binary model")
        if paco2 <= 65:
            errors.append(f"{case_id}: acute COPD case should have clearly elevated PaCO2")
        if ph >= 7.35:
            errors.append(f"{case_id}: acute COPD case should remain acidaemic")
        if ag > 16:
            errors.append(f"{case_id}: acute COPD case should keep a normal anion gap, got {ag}")
        if hco3 >= chronic_low:
            errors.append(
                f"{case_id}: acute COPD HCO3 should sit below isolated chronic compensation ({hco3} not below {chronic_low})"
            )
        if hco3 <= acute_high:
            errors.append(
                f"{case_id}: acute COPD HCO3 should remain above the acute-only range to preserve chronic background ({hco3} not above {acute_high})"
            )
        if expected_compensation.get("rule") != "Chronic respiratory acidosis":
            errors.append(f"{case_id}: acute COPD expected rule should reference chronic respiratory acidosis")
        expected_range = expected_compensation.get("acceptable_range_mmolL")
        if expected_range != [chronic_low, chronic_high]:
            errors.append(
                f"{case_id}: acute COPD expected HCO3 range should be [{chronic_low}, {chronic_high}], got {expected_range}"
            )

    elif archetype == "sepsis_respiratory_alkalosis":
        expected_hco3 = round(respiratory_alkalosis_expected_hco3_acute(paco2), 1)
        low = round(expected_hco3 - 2, 1)
        high = round(expected_hco3 + 2, 1)

        if answer_key.get("primary_disorder") != "Respiratory alkalosis":
            errors.append(f"{case_id}: sepsis case should be respiratory alkalosis")
        if answer_key.get("final_diagnosis") != "Sepsis":
            errors.append(f"{case_id}: sepsis final diagnosis mismatch")
        if answer_key.get("compensation") != "Appropriate":
            errors.append(f"{case_id}: sepsis compensation should be appropriate under the binary model")
        if paco2 >= 35:
            errors.append(f"{case_id}: sepsis case should have reduced PaCO2")
        if ph <= 7.45:
            errors.append(f"{case_id}: sepsis case should remain alkalemic for teaching clarity")
        if ag > 16:
            errors.append(f"{case_id}: sepsis case should keep a normal anion gap, got {ag}")
        if not in_range(hco3, low, high):
            errors.append(
                f"{case_id}: sepsis HCO3 should fit acute respiratory alkalosis compensation ({hco3} not in {low}-{high})"
            )
        if expected_compensation.get("rule") != "Acute respiratory alkalosis":
            errors.append(f"{case_id}: sepsis expected rule should be acute respiratory alkalosis")
        expected_range = expected_compensation.get("acceptable_range_mmolL")
        if expected_range != [low, high]:
            errors.append(
                f"{case_id}: sepsis expected HCO3 range should be [{low}, {high}], got {expected_range}"
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
                f"{case_id}: vomiting PaCO2 outside expected compensation range ({paco2} not in {low}-{high})"
            )

    elif archetype == "diuretic_metabolic_alkalosis":
        expected_paco2 = round(metabolic_alkalosis_expected_paco2(hco3), 1)
        low = round(expected_paco2 - 3, 1)
        high = round(expected_paco2 + 3, 1)

        if answer_key.get("primary_disorder") != "Metabolic alkalosis":
            errors.append(f"{case_id}: diuretic case should be metabolic alkalosis")
        if answer_key.get("final_diagnosis") != "Diuretic use":
            errors.append(f"{case_id}: diuretic final diagnosis mismatch")
        if hco3 <= 24:
            errors.append(f"{case_id}: diuretic case should have elevated HCO3")
        if not in_range(paco2, low, high):
            errors.append(
                f"{case_id}: diuretic PaCO2 outside expected compensation range ({paco2} not in {low}-{high})"
            )
        if expected_compensation.get("rule") != "Metabolic alkalosis compensation":
            errors.append(f"{case_id}: diuretic expected rule should be metabolic alkalosis compensation")

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
                f"{case_id}: panic HCO3 outside acute respiratory alkalosis range ({hco3} not in {low}-{high})"
            )

    elif archetype == "simple_respiratory_alkalosis":
        expected_hco3 = round(respiratory_alkalosis_expected_hco3_acute(paco2), 1)
        low = round(expected_hco3 - 2, 1)
        high = round(expected_hco3 + 2, 1)

        if answer_key.get("primary_disorder") != "Respiratory alkalosis":
            errors.append(f"{case_id}: simple respiratory alkalosis case should be respiratory alkalosis")
        if answer_key.get("final_diagnosis") != "Hyperventilation":
            errors.append(f"{case_id}: simple respiratory alkalosis final diagnosis mismatch")
        if paco2 >= 40:
            errors.append(f"{case_id}: simple respiratory alkalosis case should have low PaCO2")
        if ph <= 7.45:
            errors.append(f"{case_id}: simple respiratory alkalosis case should be alkalemic")
        if not in_range(hco3, low, high):
            errors.append(
                f"{case_id}: simple respiratory alkalosis HCO3 outside acute respiratory alkalosis range ({hco3} not in {low}-{high})"
            )

    elif archetype == "simple_respiratory_acidosis":
        expected_hco3 = round(24 + ((paco2 - 40) / 10), 1)
        low = round(expected_hco3 - 2, 1)
        high = round(expected_hco3 + 2, 1)

        if answer_key.get("primary_disorder") != "Respiratory acidosis":
            errors.append(f"{case_id}: simple respiratory acidosis case should be respiratory acidosis")
        if answer_key.get("final_diagnosis") != "Hypoventilation":
            errors.append(f"{case_id}: simple respiratory acidosis final diagnosis mismatch")
        if paco2 <= 40:
            errors.append(f"{case_id}: simple respiratory acidosis case should have elevated PaCO2")
        if not in_range(hco3, low, high):
            errors.append(
                f"{case_id}: simple respiratory acidosis HCO3 outside acute respiratory acidosis range ({hco3} not in {low}-{high})"
            )

    elif archetype == "dka_vomiting":
        expected_paco2 = round(winters_expected_paco2(hco3), 1)
        low = round(expected_paco2 - 2, 1)
        high = round(expected_paco2 + 2, 1)
        pure_hagma_hco3 = isolated_hagma_expected_hco3(ag)
        alkalosis_signal = hagma_bicarbonate_preservation(ag, hco3)

        if answer_key.get("primary_disorder") != "Metabolic acidosis":
            errors.append(f"{case_id}: DKA with vomiting should be metabolic acidosis")
        if answer_key.get("final_diagnosis") != "DKA with vomiting":
            errors.append(f"{case_id}: DKA with vomiting final diagnosis mismatch")
        if answer_key.get("additional_metabolic_process") != "Metabolic alkalosis":
            errors.append(f"{case_id}: DKA with vomiting should record additional metabolic alkalosis")
        if answer_key.get("compensation") != "Appropriate":
            errors.append(f"{case_id}: DKA with vomiting respiratory compensation should be appropriate")
        if glucose is None:
            errors.append(f"{case_id}: DKA with vomiting should include glucose")
        elif glucose < 14:
            errors.append(f"{case_id}: DKA with vomiting glucose should support DKA, got {glucose}")
        if ag <= 16:
            errors.append(f"{case_id}: DKA with vomiting should have raised AG, got {ag}")
        if hco3 >= 22:
            errors.append(f"{case_id}: DKA with vomiting bicarbonate should remain low overall, got {hco3}")
        if alkalosis_signal < 4:
            errors.append(
                f"{case_id}: DKA with vomiting should preserve bicarbonate above isolated-HAGMA expectations by at least 4 mmol/L"
            )
        if hco3 <= pure_hagma_hco3:
            errors.append(
                f"{case_id}: DKA with vomiting bicarbonate should sit above isolated-HAGMA expectation ({hco3} not above {pure_hagma_hco3})"
            )
        if cl > 98:
            errors.append(f"{case_id}: DKA with vomiting should have low/low-normal chloride, got {cl}")
        if not in_range(paco2, low, high):
            errors.append(
                f"{case_id}: DKA with vomiting PaCO2 outside Winter range ({paco2} not in {low}-{high})"
            )
        if not (7.15 <= ph <= 7.40):
            errors.append(f"{case_id}: DKA with vomiting pH should stay 7.15-7.40, got {ph}")
        if expected_compensation.get("rule") != "Winter":
            errors.append(f"{case_id}: DKA with vomiting expected rule should be Winter")
        if expected_compensation.get("expected_paco2_mmHg") != expected_paco2:
            errors.append(
                f"{case_id}: DKA with vomiting expected PaCO2 should be {expected_paco2}, got {expected_compensation.get('expected_paco2_mmHg')}"
            )
        expected_range = expected_compensation.get("acceptable_range_mmHg")
        if expected_range != [low, high]:
            errors.append(
                f"{case_id}: DKA with vomiting expected PaCO2 range should be [{low}, {high}], got {expected_range}"
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

    elif archetype == "mixed_hagma_metabolic_alkalosis":
        expected_paco2 = round(winters_expected_paco2(hco3), 1)
        low = round(expected_paco2 - 2, 1)
        high = round(expected_paco2 + 2, 1)
        delta_ag = ag - 12
        delta_hco3 = 24 - hco3

        if answer_key.get("primary_disorder") != "Metabolic acidosis":
            errors.append(f"{case_id}: mixed HAGMA/metabolic alkalosis should be metabolic acidosis")
        if answer_key.get("final_diagnosis") != "Mixed high anion gap metabolic acidosis and metabolic alkalosis":
            errors.append(f"{case_id}: mixed HAGMA/metabolic alkalosis final diagnosis mismatch")
        if answer_key.get("additional_metabolic_process") != "Metabolic alkalosis":
            errors.append(f"{case_id}: mixed HAGMA/metabolic alkalosis should record additional metabolic alkalosis")
        if answer_key.get("compensation") != "Appropriate":
            errors.append(f"{case_id}: mixed HAGMA/metabolic alkalosis compensation should be appropriate")
        if not (7.30 <= ph <= 7.42):
            errors.append(f"{case_id}: mixed HAGMA/metabolic alkalosis pH should stay 7.30-7.42, got {ph}")
        if not (17 <= hco3 <= 24):
            errors.append(f"{case_id}: mixed HAGMA/metabolic alkalosis HCO3 should stay 17-24, got {hco3}")
        if ag <= 16:
            errors.append(f"{case_id}: mixed HAGMA/metabolic alkalosis should have raised AG, got {ag}")
        if cl > 96:
            errors.append(f"{case_id}: mixed HAGMA/metabolic alkalosis should have low/low-normal chloride, got {cl}")
        if (delta_ag - delta_hco3) < 3:
            errors.append(
                f"{case_id}: mixed HAGMA/metabolic alkalosis should have bicarbonate preserved above isolated-HAGMA expectations"
            )
        if not in_range(paco2, low, high):
            errors.append(
                f"{case_id}: mixed HAGMA/metabolic alkalosis PaCO2 outside Winter range ({paco2} not in {low}-{high})"
            )
        if expected_compensation.get("rule") != "Winter":
            errors.append(f"{case_id}: mixed HAGMA/metabolic alkalosis expected rule should be Winter")

    elif archetype == "respiratory_alkalosis_hagma":
        expected_hco3 = round(respiratory_alkalosis_expected_hco3_acute(paco2), 1)
        low = round(expected_hco3 - 2, 1)
        high = round(expected_hco3 + 2, 1)

        if answer_key.get("primary_disorder") != "Respiratory alkalosis":
            errors.append(f"{case_id}: respiratory alkalosis/HAGMA should be respiratory alkalosis")
        if answer_key.get("final_diagnosis") != "Respiratory alkalosis with concurrent high anion gap metabolic acidosis":
            errors.append(f"{case_id}: respiratory alkalosis/HAGMA final diagnosis mismatch")
        if answer_key.get("additional_metabolic_process") != "High anion gap metabolic acidosis":
            errors.append(f"{case_id}: respiratory alkalosis/HAGMA should record additional HAGMA")
        if answer_key.get("compensation") != "Inappropriate":
            errors.append(f"{case_id}: respiratory alkalosis/HAGMA compensation should be inappropriate")
        if paco2 >= 35:
            errors.append(f"{case_id}: respiratory alkalosis/HAGMA should have clearly reduced PaCO2")
        if hco3 >= low:
            errors.append(
                f"{case_id}: respiratory alkalosis/HAGMA HCO3 should fall below the expected respiratory compensation range ({hco3} not below {low})"
            )
        if ag <= 16:
            errors.append(f"{case_id}: respiratory alkalosis/HAGMA should have raised AG, got {ag}")
        if not (7.22 <= ph <= 7.44):
            errors.append(f"{case_id}: respiratory alkalosis/HAGMA pH should stay 7.22-7.44, got {ph}")
        if expected_compensation.get("rule") != "Acute respiratory alkalosis":
            errors.append(f"{case_id}: respiratory alkalosis/HAGMA expected rule should be acute respiratory alkalosis")
        expected_range = expected_compensation.get("acceptable_range_mmolL")
        if expected_range != [low, high]:
            errors.append(
                f"{case_id}: respiratory alkalosis/HAGMA expected HCO3 range should be [{low}, {high}], got {expected_range}"
            )

    elif archetype == "respiratory_acidosis_hagma":
        compensation_rule = answer_key.get("expected_compensation", {}).get("rule")
        if compensation_rule == "Acute respiratory acidosis":
            expected_hco3 = round(acute_respiratory_acidosis_expected_hco3(paco2), 1)
        elif compensation_rule == "Chronic respiratory acidosis":
            expected_hco3 = round(chronic_respiratory_acidosis_expected_hco3(paco2), 1)
        else:
            expected_hco3 = None
            errors.append(
                f"{case_id}: respiratory acidosis/HAGMA expected rule should be acute or chronic respiratory acidosis"
            )

        if expected_hco3 is None:
            low = None
            high = None
        else:
            low = round(expected_hco3 - 2, 1)
            high = round(expected_hco3 + 2, 1)

        if answer_key.get("primary_disorder") != "Respiratory acidosis":
            errors.append(f"{case_id}: respiratory acidosis/HAGMA should be respiratory acidosis")
        if answer_key.get("final_diagnosis") != "Respiratory acidosis with concurrent high anion gap metabolic acidosis":
            errors.append(f"{case_id}: respiratory acidosis/HAGMA final diagnosis mismatch")
        if answer_key.get("additional_metabolic_process") != "High anion gap metabolic acidosis":
            errors.append(f"{case_id}: respiratory acidosis/HAGMA should record additional HAGMA")
        if answer_key.get("compensation") != "Inappropriate":
            errors.append(f"{case_id}: respiratory acidosis/HAGMA compensation should be inappropriate")
        if paco2 <= 55:
            errors.append(f"{case_id}: respiratory acidosis/HAGMA should have clearly elevated PaCO2")
        if ag <= 16:
            errors.append(f"{case_id}: respiratory acidosis/HAGMA should have raised AG, got {ag}")
        if low is not None and hco3 >= low:
            errors.append(
                f"{case_id}: respiratory acidosis/HAGMA HCO3 should fall below the expected respiratory compensation range ({hco3} not below {low})"
            )
        if not (7.10 <= ph <= 7.40):
            errors.append(f"{case_id}: respiratory acidosis/HAGMA pH should stay 7.10-7.40, got {ph}")
        expected_range = expected_compensation.get("acceptable_range_mmolL")
        if low is not None and expected_range != [low, high]:
            errors.append(
                f"{case_id}: respiratory acidosis/HAGMA expected HCO3 range should be [{low}, {high}], got {expected_range}"
            )

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
            errors.append(f"{case_id}: lactate PaCO2 outside Winter range ({paco2} not in {low}-{high})")
        if expected_compensation.get("rule") != "Winter":
            errors.append(f"{case_id}: lactate expected rule should be Winter")

    elif archetype == "uraemia":
        expected_paco2 = round(winters_expected_paco2(hco3), 1)
        low = round(expected_paco2 - 2, 1)
        high = round(expected_paco2 + 2, 1)

        if answer_key.get("primary_disorder") != "Metabolic acidosis":
            errors.append(f"{case_id}: uraemia case should be metabolic acidosis")
        if answer_key.get("final_diagnosis") != "Renal failure (uraemia)":
            errors.append(f"{case_id}: uraemia final diagnosis mismatch")
        if ag <= 16:
            errors.append(f"{case_id}: uraemia case should have raised anion gap, got {ag}")
        if not in_range(paco2, low, high):
            errors.append(f"{case_id}: uraemia PaCO2 outside Winter range ({paco2} not in {low}-{high})")
        if expected_compensation.get("rule") != "Winter":
            errors.append(f"{case_id}: uraemia expected rule should be Winter")

    errors.extend(validate_question_flow(case))
    errors.extend(validate_final_diagnosis_options(case))
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
