"""Shared helper builders for archetype generator modules."""

import re

from ..physiology import build_inputs as normalize_case_inputs, ensure_level_based_input_defaults
from ..progression import attach_progression_metadata
from ..stems import apply_age_gender_shorthand, extract_patient_gender


DIAGNOSIS_DISTRACTOR_POOL = [
    "Alcoholic ketoacidosis",
    "Opioid toxicity",
    "Hypoventilation",
    "COPD",
    "COPD exacerbation",
    "Pneumonia",
    "Neuromuscular weakness",
    "Sedative overdose",
    "Hyperventilation",
    "Panic attack / hyperventilation",
    "Panic attack",
    "Pulmonary embolism",
    "Vomiting",
    "Vomiting metabolic alkalosis",
    "Diuretic use",
    "DKA",
    "DKA with vomiting",
    "Salicylate toxicity",
    "Diarrhoea",
    "GI bicarbonate loss",
    "Gastric losses",
    "Mixed high anion gap metabolic acidosis and metabolic alkalosis",
    "Renal failure",
    "Renal failure (uraemia)",
    "Toxic alcohol",
    "Lactic acidosis",
    "Sepsis",
    "Asthma",
    "Pain",
    "Pregnancy",
]

DIAGNOSIS_CANONICAL_LABELS = {
    "acute copd": "copd exacerbation",
    "aspirin overdose": "salicylate toxicity",
    "benzodiazepine overdose": "sedative overdose",
    "diabetic ketoacidosis": "dka",
    "opioid overdose": "opioid toxicity",
    "panic hyperventilation": "panic attack / hyperventilation",
    "uraemia": "renal failure (uraemia)",
}

DIAGNOSIS_CONFLICT_GROUPS = (
    frozenset({"copd", "copd exacerbation"}),
    frozenset({"dka", "dka with vomiting"}),
    frozenset({"hyperventilation", "panic attack", "panic attack / hyperventilation"}),
    frozenset({"hypoventilation", "opioid toxicity", "sedative overdose"}),
    frozenset({"lactic acidosis", "sepsis"}),
    frozenset({"renal failure", "renal failure (uraemia)"}),
    frozenset({"vomiting", "vomiting metabolic alkalosis"}),
)

ALLOWED_DIAGNOSIS_OPTION_PAIRS = {
    frozenset(
        {
            "mixed high anion gap metabolic acidosis and metabolic alkalosis",
            "high anion gap metabolic acidosis",
        }
    ),
}

MECHANISM_LABELS = {
    "hypoventilation",
    "hyperventilation",
}

CAUSE_LABELS = {
    "opioid toxicity",
    "sedative overdose",
    "panic attack",
    "sepsis",
    "copd",
    "copd exacerbation",
}

GENERIC_MECHANISM_KEYWORDS = {"ventilation", "ventilatory"}


def build_inputs(
    ph,
    paco2,
    hco3,
    na,
    cl,
    lactate=None,
    *,
    pao2=None,
    base_excess=None,
    k=None,
    glucose=None,
    spo2=None,
    hb=None,
    methb=None,
    cohb=None,
):
    return normalize_case_inputs(
        ph,
        paco2,
        hco3,
        na,
        cl,
        lactate=lactate,
        pao2=pao2,
        base_excess=base_excess,
        k=k,
        glucose=glucose,
        spo2=spo2,
        hb=hb,
        methb=methb,
        cohb=cohb,
    )


def build_answer_key(
    ph_status,
    primary_disorder,
    compensation,
    anion_gap_value,
    anion_gap_category,
    final_diagnosis,
    expected_compensation=None,
    **extra_fields,
):
    answer_key = {
        "ph_status": ph_status,
        "primary_disorder": primary_disorder,
        "compensation": compensation,
        "anion_gap_value": anion_gap_value,
        "anion_gap_category": anion_gap_category,
        "final_diagnosis": final_diagnosis,
    }

    if expected_compensation is not None:
        answer_key["expected_compensation"] = expected_compensation

    answer_key.update(extra_fields)
    return answer_key


def normalize_diagnosis_option(label):
    normalized = re.sub(r"[\/\-,()]", " ", str(label or "").lower())
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return DIAGNOSIS_CANONICAL_LABELS.get(normalized, normalized)


def diagnosis_labels_conflict(left, right):
    left_normalized = normalize_diagnosis_option(left)
    right_normalized = normalize_diagnosis_option(right)

    if not left_normalized or not right_normalized:
        return False

    if frozenset({left_normalized, right_normalized}) in ALLOWED_DIAGNOSIS_OPTION_PAIRS:
        return False

    if left_normalized == right_normalized:
        return True

    return any(
        left_normalized in group and right_normalized in group
        for group in DIAGNOSIS_CONFLICT_GROUPS
    ) or _diagnosis_labels_conflict_by_tokens(left_normalized, right_normalized)


def _diagnosis_labels_conflict_by_tokens(left_normalized, right_normalized):
    if (
        left_normalized in MECHANISM_LABELS and right_normalized in CAUSE_LABELS
    ) or (
        right_normalized in MECHANISM_LABELS and left_normalized in CAUSE_LABELS
    ):
        return True

    if any(word in left_normalized for word in GENERIC_MECHANISM_KEYWORDS) and right_normalized in CAUSE_LABELS:
        return True

    if any(word in right_normalized for word in GENERIC_MECHANISM_KEYWORDS) and left_normalized in CAUSE_LABELS:
        return True

    left_tokens = set(left_normalized.split())
    right_tokens = set(right_normalized.split())

    if not left_tokens or not right_tokens:
        return False

    if left_tokens.issubset(right_tokens) or right_tokens.issubset(left_tokens):
        return True

    overlap_ratio = len(left_tokens & right_tokens) / max(len(left_tokens), len(right_tokens))
    if overlap_ratio >= 0.5:
        return True

    return False


def sanitize_final_diagnosis_options(questions_flow, answer_key):
    final_diagnosis = answer_key.get("final_diagnosis")

    for question in questions_flow:
        if question.get("key") != "final_diagnosis":
            continue

        options = question.get("options")
        if not isinstance(options, list):
            continue

        target_count = len(options)
        sanitized_options = []

        def try_add_option(option):
            option_text = str(option or "").strip()
            if not option_text:
                return False

            if any(diagnosis_labels_conflict(existing, option_text) for existing in sanitized_options):
                return False

            sanitized_options.append(option_text)
            return True

        try_add_option(final_diagnosis)

        for option in options:
            if len(sanitized_options) >= target_count:
                break
            try_add_option(option)

        for option in DIAGNOSIS_DISTRACTOR_POOL:
            if len(sanitized_options) >= target_count:
                break
            try_add_option(option)

        question["options"] = sanitized_options


def build_case(
    *,
    case_id,
    title,
    category,
    clinical_stem,
    inputs,
    questions_flow,
    answer_key,
    level,
    archetype,
    case_type="ABG",
    learning_objective=None,
    tags=None,
    explanation=None,
    timing=None,
    is_mixed=False,
    patient_gender=None,
):
    normalized_inputs = ensure_level_based_input_defaults(inputs, level=level)
    resolved_patient_gender = patient_gender or extract_patient_gender(clinical_stem)
    normalized_stem = apply_age_gender_shorthand(clinical_stem, gender=resolved_patient_gender)
    resolved_patient_gender = resolved_patient_gender or extract_patient_gender(normalized_stem)

    case = {
        "case_id": case_id,
        "title": title,
        "case_type": case_type,
        "category": category,
        "clinical_stem": normalized_stem,
        "inputs": normalized_inputs,
        "questions_flow": questions_flow,
        "answer_key": answer_key,
    }

    sanitize_final_diagnosis_options(case["questions_flow"], answer_key)

    if learning_objective is not None:
        case["learning_objective"] = learning_objective
    if tags is not None:
        case["tags"] = tags
    if explanation is not None:
        case["explanation"] = explanation
    if timing is not None:
        case["timing"] = timing
    if resolved_patient_gender is not None:
        case["patient_gender"] = resolved_patient_gender

    return attach_progression_metadata(case, level=level, archetype=archetype, is_mixed=is_mixed)
