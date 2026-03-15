"""Shared helper builders for archetype generator modules."""

from ..progression import attach_progression_metadata


def build_inputs(ph, paco2, hco3, na, cl, lactate=None):
    inputs = {
        "gas": {"ph": ph, "paco2_mmHg": paco2, "hco3_mmolL": hco3},
        "electrolytes": {"na_mmolL": na, "cl_mmolL": cl},
    }

    if lactate is not None:
        inputs["lactate_mmolL"] = lactate

    return inputs


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
):
    case = {
        "case_id": case_id,
        "title": title,
        "case_type": case_type,
        "category": category,
        "clinical_stem": clinical_stem,
        "inputs": inputs,
        "questions_flow": questions_flow,
        "answer_key": answer_key,
    }

    if learning_objective is not None:
        case["learning_objective"] = learning_objective
    if tags is not None:
        case["tags"] = tags
    if explanation is not None:
        case["explanation"] = explanation
    if timing is not None:
        case["timing"] = timing

    return attach_progression_metadata(case, level=level, archetype=archetype, is_mixed=is_mixed)
