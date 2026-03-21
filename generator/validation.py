"""Validation rules for generated ABG cases.

This module checks question-flow structure, answer-key membership, duplicate
IDs, physiologic plausibility, and archetype-specific validation contracts.
"""

from dataclasses import dataclass

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


QUESTION_ANSWER_KEY_FIELDS = {
    "ph_status": "ph_status",
    "primary_disorder": "primary_disorder",
    "compensation": "compensation",
    "anion_gap": "anion_gap_category",
    "additional_metabolic_process": "additional_metabolic_process",
    "final_diagnosis": "final_diagnosis",
}


@dataclass(frozen=True)
class ValidationContext:
    case: dict
    case_id: str
    archetype: str
    inputs: dict
    gas: dict
    electrolytes: dict
    answer_key: dict
    expected_compensation: dict
    ph: float
    paco2: float
    hco3: float
    na: float
    cl: float
    ag: float
    glucose: float
    lactate: float


@dataclass(frozen=True)
class ArchetypeValidationContract:
    name: str
    validator: callable


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


def validate_scored_step_answers(case):
    errors = []
    case_id = case.get("case_id", "<missing_case_id>")
    answer_key = case.get("answer_key", {})

    for question in case.get("questions_flow", []):
        question_key = question.get("key")
        answer_field = QUESTION_ANSWER_KEY_FIELDS.get(question_key)

        if answer_field is None:
            errors.append(f"{case_id}: no answer-key mapping declared for question step '{question_key}'")
            continue

        if answer_field not in answer_key:
            errors.append(f"{case_id}: answer_key missing '{answer_field}' for question step '{question_key}'")
            continue

        options = question.get("options")
        if not isinstance(options, list) or not options:
            errors.append(f"{case_id}: question step '{question_key}' must define a non-empty options list")
            continue

        correct_answer = answer_key.get(answer_field)
        if correct_answer not in options:
            errors.append(
                f"{case_id}: question step '{question_key}' options missing correct answer '{correct_answer}'"
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


def _winter_window(hco3):
    expected = round(winters_expected_paco2(hco3), 1)
    low = round(expected - 2, 1)
    high = round(expected + 2, 1)
    return expected, low, high


def _metabolic_alkalosis_window(hco3):
    expected = round(metabolic_alkalosis_expected_paco2(hco3), 1)
    low = round(expected - 3, 1)
    high = round(expected + 3, 1)
    return expected, low, high


def _acute_respiratory_acidosis_window(paco2):
    expected = round(acute_respiratory_acidosis_expected_hco3(paco2), 1)
    low = round(expected - 2, 1)
    high = round(expected + 2, 1)
    return expected, low, high


def _chronic_respiratory_acidosis_window(paco2):
    expected = round(chronic_respiratory_acidosis_expected_hco3(paco2), 1)
    low = round(expected - 2, 1)
    high = round(expected + 2, 1)
    return expected, low, high


def _acute_respiratory_alkalosis_window(paco2):
    expected = round(respiratory_alkalosis_expected_hco3_acute(paco2), 1)
    low = round(expected - 2, 1)
    high = round(expected + 2, 1)
    return expected, low, high


def _validate_expected_compensation_metadata(
    ctx,
    *,
    label,
    rule,
    expected_field,
    expected_value,
    range_field,
    low,
    high,
):
    errors = []
    expected_compensation = ctx.expected_compensation

    if expected_compensation.get("rule") != rule:
        errors.append(f"{ctx.case_id}: {label} expected rule should be {rule}")

    if expected_compensation.get(expected_field) != expected_value:
        errors.append(
            f"{ctx.case_id}: {label} expected {expected_field} should be {expected_value}, "
            f"got {expected_compensation.get(expected_field)}"
        )

    expected_range = expected_compensation.get(range_field)
    if expected_range != [low, high]:
        errors.append(
            f"{ctx.case_id}: {label} expected {range_field} should be [{low}, {high}], got {expected_range}"
        )

    return errors


def _validate_winter_compensation(ctx, *, label):
    errors = []
    expected, low, high = _winter_window(ctx.hco3)

    if not in_range(ctx.paco2, low, high):
        errors.append(f"{ctx.case_id}: {label} PaCO2 outside Winter range ({ctx.paco2} not in {low}-{high})")

    errors.extend(
        _validate_expected_compensation_metadata(
            ctx,
            label=label,
            rule="Winter",
            expected_field="expected_paco2_mmHg",
            expected_value=expected,
            range_field="acceptable_range_mmHg",
            low=low,
            high=high,
        )
    )
    return errors


def _validate_metabolic_alkalosis_compensation(ctx, *, label):
    errors = []
    expected, low, high = _metabolic_alkalosis_window(ctx.hco3)

    if not in_range(ctx.paco2, low, high):
        errors.append(
            f"{ctx.case_id}: {label} PaCO2 outside expected compensation range ({ctx.paco2} not in {low}-{high})"
        )

    errors.extend(
        _validate_expected_compensation_metadata(
            ctx,
            label=label,
            rule="Metabolic alkalosis compensation",
            expected_field="expected_paco2_mmHg",
            expected_value=expected,
            range_field="acceptable_range_mmHg",
            low=low,
            high=high,
        )
    )
    return errors


def _validate_acute_respiratory_acidosis_compensation(ctx, *, label):
    errors = []
    expected, low, high = _acute_respiratory_acidosis_window(ctx.paco2)

    if not in_range(ctx.hco3, low, high):
        errors.append(
            f"{ctx.case_id}: {label} HCO3 outside acute respiratory acidosis range ({ctx.hco3} not in {low}-{high})"
        )

    errors.extend(
        _validate_expected_compensation_metadata(
            ctx,
            label=label,
            rule="Acute respiratory acidosis",
            expected_field="expected_hco3_mmolL",
            expected_value=expected,
            range_field="acceptable_range_mmolL",
            low=low,
            high=high,
        )
    )
    return errors


def _validate_chronic_respiratory_acidosis_compensation(ctx, *, label):
    errors = []
    expected, low, high = _chronic_respiratory_acidosis_window(ctx.paco2)

    if not in_range(ctx.hco3, low, high):
        errors.append(
            f"{ctx.case_id}: {label} HCO3 outside chronic respiratory acidosis range ({ctx.hco3} not in {low}-{high})"
        )

    errors.extend(
        _validate_expected_compensation_metadata(
            ctx,
            label=label,
            rule="Chronic respiratory acidosis",
            expected_field="expected_hco3_mmolL",
            expected_value=expected,
            range_field="acceptable_range_mmolL",
            low=low,
            high=high,
        )
    )
    return errors


def _validate_acute_respiratory_alkalosis_compensation(ctx, *, label):
    errors = []
    expected, low, high = _acute_respiratory_alkalosis_window(ctx.paco2)

    if not in_range(ctx.hco3, low, high):
        errors.append(
            f"{ctx.case_id}: {label} HCO3 should fit acute respiratory alkalosis compensation ({ctx.hco3} not in {low}-{high})"
        )

    errors.extend(
        _validate_expected_compensation_metadata(
            ctx,
            label=label,
            rule="Acute respiratory alkalosis",
            expected_field="expected_hco3_mmolL",
            expected_value=expected,
            range_field="acceptable_range_mmolL",
            low=low,
            high=high,
        )
    )
    return errors


def _validate_expected_hco3_mismatch(ctx, *, label, rule):
    errors = []

    if rule == "Acute respiratory acidosis":
        expected, low, high = _acute_respiratory_acidosis_window(ctx.paco2)
    elif rule == "Chronic respiratory acidosis":
        expected, low, high = _chronic_respiratory_acidosis_window(ctx.paco2)
    elif rule == "Acute respiratory alkalosis":
        expected, low, high = _acute_respiratory_alkalosis_window(ctx.paco2)
    else:
        errors.append(f"{ctx.case_id}: {label} expected rule should be acute/chronic respiratory compensation")
        return errors

    if ctx.hco3 >= low:
        errors.append(
            f"{ctx.case_id}: {label} HCO3 should fall below the expected respiratory compensation range "
            f"({ctx.hco3} not below {low})"
        )

    errors.extend(
        _validate_expected_compensation_metadata(
            ctx,
            label=label,
            rule=rule,
            expected_field="expected_hco3_mmolL",
            expected_value=expected,
            range_field="acceptable_range_mmolL",
            low=low,
            high=high,
        )
    )
    return errors


def _validate_primary_and_diagnosis(ctx, *, primary_disorder, final_diagnosis, label):
    errors = []

    if ctx.answer_key.get("primary_disorder") != primary_disorder:
        errors.append(f"{ctx.case_id}: {label} should be {primary_disorder.lower()}")

    if ctx.answer_key.get("final_diagnosis") != final_diagnosis:
        errors.append(f"{ctx.case_id}: {label} final diagnosis mismatch")

    return errors


def _validate_glucose_floor(ctx, *, label, min_value):
    if ctx.glucose is None:
        return [f"{ctx.case_id}: {label} should include glucose"]
    if ctx.glucose < min_value:
        return [f"{ctx.case_id}: {label} glucose should support the diagnosis, got {ctx.glucose}"]
    return []


def _validate_glucose_ceiling(ctx, *, label, max_value, description):
    if ctx.glucose is None:
        return [f"{ctx.case_id}: {label} should include glucose"]
    if ctx.glucose > max_value:
        return [f"{ctx.case_id}: {label} glucose should {description}, got {ctx.glucose}"]
    return []


def _validate_glucose_range(ctx, *, label, low, high, description):
    if ctx.glucose is None:
        return [f"{ctx.case_id}: {label} should include glucose"]
    if not in_range(ctx.glucose, low, high):
        return [f"{ctx.case_id}: {label} glucose should {description}, got {ctx.glucose}"]
    return []


def _validate_lactate_floor(ctx, *, label, min_value):
    if ctx.lactate is None:
        return [f"{ctx.case_id}: {label} should include lactate"]
    if ctx.lactate < min_value:
        return [f"{ctx.case_id}: {label} lactate should materially support the diagnosis, got {ctx.lactate}"]
    return []


def _validate_lactate_ceiling(ctx, *, label, max_value, description):
    if ctx.lactate is None:
        return []
    if ctx.lactate > max_value:
        return [f"{ctx.case_id}: {label} lactate should {description}, got {ctx.lactate}"]
    return []


def _validate_hagma_evidence(ctx, *, label, lactate_min=None):
    errors = []

    if ctx.ag <= 16:
        errors.append(f"{ctx.case_id}: {label} should have raised anion gap, got {ctx.ag}")

    if lactate_min is not None:
        if ctx.lactate is None:
            errors.append(f"{ctx.case_id}: {label} should include lactate support for the added HAGMA")
        elif ctx.lactate < lactate_min:
            errors.append(
                f"{ctx.case_id}: {label} lactate should support the added HAGMA from the displayed numbers, got {ctx.lactate}"
            )

    return errors


def _validate_hagma_plus_metabolic_alkalosis(ctx, *, label, min_preservation):
    errors = []
    pure_hagma_hco3 = isolated_hagma_expected_hco3(ctx.ag)
    preservation = hagma_bicarbonate_preservation(ctx.ag, ctx.hco3)

    if ctx.answer_key.get("additional_metabolic_process") != "Metabolic alkalosis":
        errors.append(f"{ctx.case_id}: {label} should record additional metabolic alkalosis")

    if preservation < min_preservation:
        errors.append(
            f"{ctx.case_id}: {label} bicarbonate does not preserve enough delta-gap signal to prove added metabolic alkalosis"
        )

    if ctx.hco3 <= pure_hagma_hco3:
        errors.append(
            f"{ctx.case_id}: {label} bicarbonate should sit above isolated-HAGMA expectation ({ctx.hco3} not above {pure_hagma_hco3})"
        )

    return errors


def _validate_winter_hagma_case(ctx, *, label, final_diagnosis):
    errors = []
    errors.extend(
        _validate_primary_and_diagnosis(
            ctx,
            primary_disorder="Metabolic acidosis",
            final_diagnosis=final_diagnosis,
            label=label,
        )
    )
    if ctx.answer_key.get("compensation") != "Appropriate":
        errors.append(f"{ctx.case_id}: {label} compensation should be appropriate")
    errors.extend(_validate_hagma_evidence(ctx, label=label))
    errors.extend(_validate_winter_compensation(ctx, label=label))
    return errors


def _validate_winter_nagma_case(ctx, *, label, final_diagnosis):
    errors = []
    errors.extend(
        _validate_primary_and_diagnosis(
            ctx,
            primary_disorder="Metabolic acidosis",
            final_diagnosis=final_diagnosis,
            label=label,
        )
    )
    if ctx.answer_key.get("compensation") != "Appropriate":
        errors.append(f"{ctx.case_id}: {label} compensation should be appropriate")
    if ctx.ag > 16:
        errors.append(f"{ctx.case_id}: {label} should have normal anion gap, got {ctx.ag}")
    errors.extend(_validate_winter_compensation(ctx, label=label))
    return errors


def _validate_metabolic_alkalosis_case(ctx, *, label, final_diagnosis):
    errors = []
    errors.extend(
        _validate_primary_and_diagnosis(
            ctx,
            primary_disorder="Metabolic alkalosis",
            final_diagnosis=final_diagnosis,
            label=label,
        )
    )
    if ctx.answer_key.get("compensation") != "Appropriate":
        errors.append(f"{ctx.case_id}: {label} compensation should be appropriate")
    errors.extend(_validate_metabolic_alkalosis_compensation(ctx, label=label))
    return errors


def _validate_acute_respiratory_acidosis_case(ctx, *, label, final_diagnosis):
    errors = []
    errors.extend(
        _validate_primary_and_diagnosis(
            ctx,
            primary_disorder="Respiratory acidosis",
            final_diagnosis=final_diagnosis,
            label=label,
        )
    )
    if ctx.answer_key.get("compensation") != "Appropriate":
        errors.append(f"{ctx.case_id}: {label} compensation should be appropriate")
    errors.extend(_validate_acute_respiratory_acidosis_compensation(ctx, label=label))
    return errors


def _validate_acute_respiratory_alkalosis_case(ctx, *, label, final_diagnosis):
    errors = []
    errors.extend(
        _validate_primary_and_diagnosis(
            ctx,
            primary_disorder="Respiratory alkalosis",
            final_diagnosis=final_diagnosis,
            label=label,
        )
    )
    if ctx.answer_key.get("compensation") != "Appropriate":
        errors.append(f"{ctx.case_id}: {label} compensation should be appropriate")
    errors.extend(_validate_acute_respiratory_alkalosis_compensation(ctx, label=label))
    return errors


def _validate_dka(ctx):
    errors = []
    errors.extend(_validate_winter_hagma_case(ctx, label="DKA", final_diagnosis="DKA"))
    errors.extend(_validate_glucose_floor(ctx, label="DKA", min_value=14.0))
    return errors


def _validate_alcoholic_ketoacidosis(ctx):
    errors = []
    errors.extend(
        _validate_winter_hagma_case(
            ctx,
            label="alcoholic ketoacidosis",
            final_diagnosis="Alcoholic ketoacidosis",
        )
    )
    errors.extend(
        _validate_glucose_ceiling(
            ctx,
            label="alcoholic ketoacidosis",
            max_value=13.9,
            description="stay below classic DKA-range hyperglycaemia",
        )
    )
    errors.extend(
        _validate_lactate_ceiling(
            ctx,
            label="alcoholic ketoacidosis",
            max_value=4.0,
            description="stay mild if present",
        )
    )
    return errors


def _validate_starvation_ketosis(ctx):
    errors = []
    errors.extend(
        _validate_winter_hagma_case(
            ctx,
            label="starvation ketosis",
            final_diagnosis="Starvation ketosis",
        )
    )
    errors.extend(
        _validate_glucose_range(
            ctx,
            label="starvation ketosis",
            low=3.2,
            high=6.2,
            description="stay normal/low-normal",
        )
    )
    if ctx.lactate is not None and ctx.lactate > 2.2:
        errors.append(
            f"{ctx.case_id}: starvation ketosis lactate should stay absent or mildly elevated, got {ctx.lactate}"
        )
    return errors


def _validate_toxic_alcohol(ctx):
    errors = []
    errors.extend(_validate_winter_hagma_case(ctx, label="toxic alcohol", final_diagnosis="Toxic alcohol"))
    errors.extend(
        _validate_lactate_ceiling(
            ctx,
            label="toxic alcohol",
            max_value=3.5,
            description="remain absent or only mildly elevated",
        )
    )
    if ctx.lactate is not None and ctx.lactate >= (ctx.ag - 12):
        errors.append(
            f"{ctx.case_id}: toxic alcohol lactate should not be the main explanation for the HAGMA "
            f"(lactate {ctx.lactate}, delta AG {round(ctx.ag - 12, 1)})"
        )
    return errors


def _validate_diarrhoea_nagma(ctx):
    return _validate_winter_nagma_case(ctx, label="diarrhoea", final_diagnosis="Diarrhoea")


def _validate_simple_nagma(ctx):
    errors = []
    errors.extend(_validate_winter_nagma_case(ctx, label="simple NAGMA", final_diagnosis="GI bicarbonate loss"))
    if ctx.ph >= 7.35:
        errors.append(f"{ctx.case_id}: simple NAGMA should remain acidaemic for beginner clarity")
    if ctx.cl < 104:
        errors.append(f"{ctx.case_id}: simple NAGMA should be relatively hyperchloraemic, got Cl {ctx.cl}")
    return errors


def _validate_simple_metabolic_alkalosis(ctx):
    errors = []
    errors.extend(
        _validate_metabolic_alkalosis_case(
            ctx,
            label="simple metabolic alkalosis",
            final_diagnosis="Gastric losses",
        )
    )
    if ctx.ph <= 7.45:
        errors.append(f"{ctx.case_id}: simple metabolic alkalosis should remain alkalemic for beginner clarity")
    if ctx.hco3 <= 26:
        errors.append(f"{ctx.case_id}: simple metabolic alkalosis should have elevated bicarbonate")
    if ctx.cl > 103:
        errors.append(
            f"{ctx.case_id}: simple metabolic alkalosis should be relatively hypochloraemic, got Cl {ctx.cl}"
        )
    return errors


def _validate_opioid_toxicity(ctx):
    errors = []
    errors.extend(
        _validate_acute_respiratory_acidosis_case(
            ctx,
            label="opioid case",
            final_diagnosis="Opioid toxicity",
        )
    )
    if ctx.paco2 <= 40:
        errors.append(f"{ctx.case_id}: opioid case should have elevated PaCO2")
    return errors


def _validate_copd_chronic_retainer(ctx):
    errors = []
    errors.extend(
        _validate_primary_and_diagnosis(
            ctx,
            primary_disorder="Respiratory acidosis",
            final_diagnosis="COPD",
            label="COPD case",
        )
    )
    if ctx.answer_key.get("compensation") != "Appropriate":
        errors.append(f"{ctx.case_id}: COPD compensation should be appropriate")
    if ctx.paco2 <= 40:
        errors.append(f"{ctx.case_id}: COPD case should have elevated PaCO2")
    errors.extend(_validate_chronic_respiratory_acidosis_compensation(ctx, label="COPD"))
    return errors


def _validate_acute_copd_exacerbation(ctx):
    errors = []
    chronic_expected, chronic_low, chronic_high = _chronic_respiratory_acidosis_window(ctx.paco2)
    _acute_expected, _acute_low, acute_high = _acute_respiratory_acidosis_window(ctx.paco2)

    errors.extend(
        _validate_primary_and_diagnosis(
            ctx,
            primary_disorder="Respiratory acidosis",
            final_diagnosis="COPD exacerbation",
            label="acute COPD case",
        )
    )
    if ctx.answer_key.get("compensation") != "Inappropriate":
        errors.append(f"{ctx.case_id}: acute COPD compensation should be inappropriate under the binary model")
    if ctx.paco2 <= 65:
        errors.append(f"{ctx.case_id}: acute COPD case should have clearly elevated PaCO2")
    if ctx.ph >= 7.35:
        errors.append(f"{ctx.case_id}: acute COPD case should remain acidaemic")
    if ctx.ag > 16:
        errors.append(f"{ctx.case_id}: acute COPD case should keep a normal anion gap, got {ctx.ag}")
    if ctx.hco3 >= chronic_low:
        errors.append(
            f"{ctx.case_id}: acute COPD HCO3 should sit below isolated chronic compensation ({ctx.hco3} not below {chronic_low})"
        )
    if ctx.hco3 <= acute_high:
        errors.append(
            f"{ctx.case_id}: acute COPD HCO3 should remain above the acute-only range to preserve chronic background "
            f"({ctx.hco3} not above {acute_high})"
        )
    errors.extend(
        _validate_expected_compensation_metadata(
            ctx,
            label="acute COPD",
            rule="Chronic respiratory acidosis",
            expected_field="expected_hco3_mmolL",
            expected_value=chronic_expected,
            range_field="acceptable_range_mmolL",
            low=chronic_low,
            high=chronic_high,
        )
    )
    return errors


def _validate_sepsis_respiratory_alkalosis(ctx):
    errors = []
    errors.extend(
        _validate_acute_respiratory_alkalosis_case(
            ctx,
            label="sepsis case",
            final_diagnosis="Sepsis",
        )
    )
    if ctx.paco2 >= 35:
        errors.append(f"{ctx.case_id}: sepsis case should have reduced PaCO2")
    if ctx.ph <= 7.45:
        errors.append(f"{ctx.case_id}: sepsis case should remain alkalemic for teaching clarity")
    if ctx.ag > 16:
        errors.append(f"{ctx.case_id}: sepsis case should keep a normal anion gap, got {ctx.ag}")
    return errors


def _validate_vomiting_metabolic_alkalosis(ctx):
    errors = []
    errors.extend(
        _validate_metabolic_alkalosis_case(
            ctx,
            label="vomiting case",
            final_diagnosis="Vomiting",
        )
    )
    if ctx.ph <= 7.45:
        errors.append(f"{ctx.case_id}: vomiting case should be alkalemic")
    return errors


def _validate_diuretic_metabolic_alkalosis(ctx):
    errors = []
    errors.extend(
        _validate_metabolic_alkalosis_case(
            ctx,
            label="diuretic case",
            final_diagnosis="Diuretic use",
        )
    )
    if ctx.hco3 <= 24:
        errors.append(f"{ctx.case_id}: diuretic case should have elevated HCO3")
    return errors


def _validate_panic_hyperventilation(ctx):
    errors = []
    errors.extend(
        _validate_acute_respiratory_alkalosis_case(
            ctx,
            label="panic case",
            final_diagnosis="Panic attack / hyperventilation",
        )
    )
    if ctx.paco2 >= 40:
        errors.append(f"{ctx.case_id}: panic case should have low PaCO2")
    if ctx.ph <= 7.45:
        errors.append(f"{ctx.case_id}: panic case should be alkalemic")
    return errors


def _validate_simple_respiratory_alkalosis(ctx):
    errors = []
    errors.extend(
        _validate_acute_respiratory_alkalosis_case(
            ctx,
            label="simple respiratory alkalosis case",
            final_diagnosis="Hyperventilation",
        )
    )
    if ctx.paco2 >= 40:
        errors.append(f"{ctx.case_id}: simple respiratory alkalosis case should have low PaCO2")
    if ctx.ph <= 7.45:
        errors.append(f"{ctx.case_id}: simple respiratory alkalosis case should be alkalemic")
    return errors


def _validate_simple_respiratory_acidosis(ctx):
    errors = []
    errors.extend(
        _validate_acute_respiratory_acidosis_case(
            ctx,
            label="simple respiratory acidosis case",
            final_diagnosis="Hypoventilation",
        )
    )
    if ctx.paco2 <= 40:
        errors.append(f"{ctx.case_id}: simple respiratory acidosis case should have elevated PaCO2")
    return errors


def _validate_dka_vomiting(ctx):
    errors = []
    errors.extend(
        _validate_winter_hagma_case(
            ctx,
            label="DKA with vomiting",
            final_diagnosis="DKA with vomiting",
        )
    )
    errors.extend(_validate_glucose_floor(ctx, label="DKA with vomiting", min_value=14.0))
    errors.extend(
        _validate_hagma_plus_metabolic_alkalosis(
            ctx,
            label="DKA with vomiting",
            min_preservation=4.0,
        )
    )
    if ctx.hco3 >= 22:
        errors.append(f"{ctx.case_id}: DKA with vomiting bicarbonate should remain low overall, got {ctx.hco3}")
    if ctx.cl > 98:
        errors.append(f"{ctx.case_id}: DKA with vomiting should have low/low-normal chloride, got {ctx.cl}")
    if not (7.15 <= ctx.ph <= 7.40):
        errors.append(f"{ctx.case_id}: DKA with vomiting pH should stay 7.15-7.40, got {ctx.ph}")
    return errors


def _validate_salicylate_toxicity(ctx):
    errors = []
    question_keys = [question.get("key") for question in ctx.case.get("questions_flow", [])]

    errors.extend(
        _validate_primary_and_diagnosis(
            ctx,
            primary_disorder="Respiratory alkalosis",
            final_diagnosis="Salicylate toxicity",
            label="salicylate toxicity case",
        )
    )
    if "additional_metabolic_process" not in question_keys:
        errors.append(
            f"{ctx.case_id}: salicylate toxicity case should use the mixed question flow with an additional metabolic process step"
        )
    if ctx.answer_key.get("compensation") != "Inappropriate":
        errors.append(f"{ctx.case_id}: salicylate toxicity case compensation should be inappropriate")
    if ctx.answer_key.get("anion_gap_category") != "Raised":
        errors.append(f"{ctx.case_id}: salicylate toxicity case anion gap category should be Raised")
    if ctx.answer_key.get("additional_metabolic_process") != "High anion gap metabolic acidosis":
        errors.append(
            f"{ctx.case_id}: salicylate toxicity case should identify a concurrent high anion gap metabolic acidosis"
        )
    if ctx.paco2 >= 35:
        errors.append(f"{ctx.case_id}: salicylate toxicity case should have low PaCO2")
    errors.extend(_validate_hagma_evidence(ctx, label="salicylate toxicity case"))
    errors.extend(
        _validate_expected_hco3_mismatch(
            ctx,
            label="salicylate toxicity case",
            rule="Acute respiratory alkalosis",
        )
    )
    errors.extend(
        _validate_glucose_ceiling(
            ctx,
            label="salicylate toxicity case",
            max_value=13.9,
            description="stay well below DKA-range hyperglycaemia",
        )
    )
    errors.extend(
        _validate_lactate_ceiling(
            ctx,
            label="salicylate toxicity case",
            max_value=3.2,
            description="stay mild enough that salicylate remains the main explanation for the HAGMA",
        )
    )
    return errors


def _validate_mixed_hagma_metabolic_alkalosis(ctx):
    errors = []
    errors.extend(
        _validate_winter_hagma_case(
            ctx,
            label="mixed HAGMA/metabolic alkalosis",
            final_diagnosis="Mixed high anion gap metabolic acidosis and metabolic alkalosis",
        )
    )
    errors.extend(
        _validate_hagma_plus_metabolic_alkalosis(
            ctx,
            label="mixed HAGMA/metabolic alkalosis",
            min_preservation=3.0,
        )
    )
    if not (7.30 <= ctx.ph <= 7.42):
        errors.append(f"{ctx.case_id}: mixed HAGMA/metabolic alkalosis pH should stay 7.30-7.42, got {ctx.ph}")
    if not (17 <= ctx.hco3 <= 24):
        errors.append(
            f"{ctx.case_id}: mixed HAGMA/metabolic alkalosis HCO3 should stay 17-24, got {ctx.hco3}"
        )
    if ctx.cl > 96:
        errors.append(
            f"{ctx.case_id}: mixed HAGMA/metabolic alkalosis should have low/low-normal chloride, got {ctx.cl}"
        )
    return errors


def _validate_respiratory_alkalosis_hagma(ctx):
    errors = []
    errors.extend(
        _validate_primary_and_diagnosis(
            ctx,
            primary_disorder="Respiratory alkalosis",
            final_diagnosis="Respiratory alkalosis with concurrent high anion gap metabolic acidosis",
            label="respiratory alkalosis/HAGMA",
        )
    )
    if ctx.answer_key.get("additional_metabolic_process") != "High anion gap metabolic acidosis":
        errors.append(f"{ctx.case_id}: respiratory alkalosis/HAGMA should record additional HAGMA")
    if ctx.answer_key.get("compensation") != "Inappropriate":
        errors.append(f"{ctx.case_id}: respiratory alkalosis/HAGMA compensation should be inappropriate")
    if ctx.paco2 >= 35:
        errors.append(f"{ctx.case_id}: respiratory alkalosis/HAGMA should have clearly reduced PaCO2")
    errors.extend(
        _validate_expected_hco3_mismatch(
            ctx,
            label="respiratory alkalosis/HAGMA",
            rule="Acute respiratory alkalosis",
        )
    )
    errors.extend(_validate_hagma_evidence(ctx, label="respiratory alkalosis/HAGMA", lactate_min=2.2))
    if not (7.22 <= ctx.ph <= 7.44):
        errors.append(f"{ctx.case_id}: respiratory alkalosis/HAGMA pH should stay 7.22-7.44, got {ctx.ph}")
    return errors


def _validate_respiratory_acidosis_hagma(ctx):
    errors = []
    rule = ctx.expected_compensation.get("rule")
    errors.extend(
        _validate_primary_and_diagnosis(
            ctx,
            primary_disorder="Respiratory acidosis",
            final_diagnosis="Respiratory acidosis with concurrent high anion gap metabolic acidosis",
            label="respiratory acidosis/HAGMA",
        )
    )
    if ctx.answer_key.get("additional_metabolic_process") != "High anion gap metabolic acidosis":
        errors.append(f"{ctx.case_id}: respiratory acidosis/HAGMA should record additional HAGMA")
    if ctx.answer_key.get("compensation") != "Inappropriate":
        errors.append(f"{ctx.case_id}: respiratory acidosis/HAGMA compensation should be inappropriate")
    if ctx.paco2 <= 55:
        errors.append(f"{ctx.case_id}: respiratory acidosis/HAGMA should have clearly elevated PaCO2")
    errors.extend(_validate_expected_hco3_mismatch(ctx, label="respiratory acidosis/HAGMA", rule=rule))
    errors.extend(_validate_hagma_evidence(ctx, label="respiratory acidosis/HAGMA", lactate_min=2.2))
    if not (7.10 <= ctx.ph <= 7.40):
        errors.append(f"{ctx.case_id}: respiratory acidosis/HAGMA pH should stay 7.10-7.40, got {ctx.ph}")
    return errors


def _validate_lactic_acidosis(ctx):
    errors = []
    errors.extend(_validate_winter_hagma_case(ctx, label="lactate case", final_diagnosis="Lactic acidosis"))
    errors.extend(_validate_lactate_floor(ctx, label="lactic acidosis", min_value=4.0))
    return errors


def _validate_uraemia(ctx):
    return _validate_winter_hagma_case(ctx, label="uraemia case", final_diagnosis="Renal failure (uraemia)")


ARCHETYPE_VALIDATION_CONTRACTS = {
    "dka": ArchetypeValidationContract("winter_hagma_contract", _validate_dka),
    "alcoholic_ketoacidosis": ArchetypeValidationContract(
        "winter_hagma_contract",
        _validate_alcoholic_ketoacidosis,
    ),
    "starvation_ketosis": ArchetypeValidationContract("winter_hagma_contract", _validate_starvation_ketosis),
    "toxic_alcohol": ArchetypeValidationContract("winter_hagma_contract", _validate_toxic_alcohol),
    "diarrhoea_nagma": ArchetypeValidationContract("winter_nagma_contract", _validate_diarrhoea_nagma),
    "simple_nagma": ArchetypeValidationContract("winter_nagma_contract", _validate_simple_nagma),
    "simple_metabolic_alkalosis": ArchetypeValidationContract(
        "metabolic_alkalosis_contract",
        _validate_simple_metabolic_alkalosis,
    ),
    "opioid_toxicity": ArchetypeValidationContract(
        "acute_respiratory_acidosis_contract",
        _validate_opioid_toxicity,
    ),
    "copd_chronic_retainer": ArchetypeValidationContract(
        "chronic_respiratory_acidosis_contract",
        _validate_copd_chronic_retainer,
    ),
    "acute_copd_exacerbation": ArchetypeValidationContract(
        "acute_on_chronic_respiratory_acidosis_contract",
        _validate_acute_copd_exacerbation,
    ),
    "sepsis_respiratory_alkalosis": ArchetypeValidationContract(
        "acute_respiratory_alkalosis_contract",
        _validate_sepsis_respiratory_alkalosis,
    ),
    "vomiting_metabolic_alkalosis": ArchetypeValidationContract(
        "metabolic_alkalosis_contract",
        _validate_vomiting_metabolic_alkalosis,
    ),
    "diuretic_metabolic_alkalosis": ArchetypeValidationContract(
        "metabolic_alkalosis_contract",
        _validate_diuretic_metabolic_alkalosis,
    ),
    "panic_hyperventilation": ArchetypeValidationContract(
        "acute_respiratory_alkalosis_contract",
        _validate_panic_hyperventilation,
    ),
    "simple_respiratory_alkalosis": ArchetypeValidationContract(
        "acute_respiratory_alkalosis_contract",
        _validate_simple_respiratory_alkalosis,
    ),
    "simple_respiratory_acidosis": ArchetypeValidationContract(
        "acute_respiratory_acidosis_contract",
        _validate_simple_respiratory_acidosis,
    ),
    "dka_vomiting": ArchetypeValidationContract(
        "mixed_hagma_plus_metabolic_alkalosis_contract",
        _validate_dka_vomiting,
    ),
    "salicylate_toxicity": ArchetypeValidationContract("salicylate_mixed_contract", _validate_salicylate_toxicity),
    "mixed_hagma_metabolic_alkalosis": ArchetypeValidationContract(
        "mixed_hagma_plus_metabolic_alkalosis_contract",
        _validate_mixed_hagma_metabolic_alkalosis,
    ),
    "respiratory_alkalosis_hagma": ArchetypeValidationContract(
        "mixed_respiratory_plus_hagma_contract",
        _validate_respiratory_alkalosis_hagma,
    ),
    "respiratory_acidosis_hagma": ArchetypeValidationContract(
        "mixed_respiratory_plus_hagma_contract",
        _validate_respiratory_acidosis_hagma,
    ),
    "lactic_acidosis": ArchetypeValidationContract("winter_hagma_contract", _validate_lactic_acidosis),
    "uraemia": ArchetypeValidationContract("winter_hagma_contract", _validate_uraemia),
}


def get_uncovered_archetypes(archetypes):
    return sorted(set(archetypes) - set(ARCHETYPE_VALIDATION_CONTRACTS))


def validate_archetype_contract_coverage(cases):
    generated_archetypes = {case.get("archetype") for case in cases if case.get("archetype")}
    missing = get_uncovered_archetypes(generated_archetypes)

    if not missing:
        return []

    return [
        "validation coverage missing archetype contract(s): "
        + ", ".join(sorted(missing))
    ]


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
    if expected_compensation is not None and not isinstance(expected_compensation, dict):
        errors.append(f"{case_id}: answer_key.expected_compensation should be an object when present")
        expected_compensation = {}

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
    lactate = get_case_optional_value(inputs, "other", "lactate_mmolL", legacy_key="lactate_mmolL")

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

    compensation_steps = [
        question for question in case.get("questions_flow", [])
        if question.get("key") == "compensation"
    ]
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

    errors.extend(validate_question_flow(case))
    errors.extend(validate_scored_step_answers(case))
    errors.extend(validate_final_diagnosis_options(case))

    if errors:
        return errors

    contract = ARCHETYPE_VALIDATION_CONTRACTS.get(archetype)
    if contract is None:
        return [f"{case_id}: archetype '{archetype}' has no explicit validation contract"]

    ctx = ValidationContext(
        case=case,
        case_id=case_id,
        archetype=archetype,
        inputs=inputs,
        gas=gas,
        electrolytes=electrolytes,
        answer_key=answer_key,
        expected_compensation=expected_compensation or {},
        ph=ph,
        paco2=paco2,
        hco3=hco3,
        na=na,
        cl=cl,
        ag=ag,
        glucose=glucose,
        lactate=lactate,
    )

    errors.extend(contract.validator(ctx))
    return errors


def validate_cases(cases):
    errors = []
    seen_ids = set()

    errors.extend(validate_archetype_contract_coverage(cases))

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
