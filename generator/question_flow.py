from config import OPTIONS, PROMPTS, QUESTION_LABELS, SPEED_BONUS_TIERS


def default_timing():
    return {
        "timer_visible_by_default": False,
        "time_bonus_scope": "whole_case",
        "time_bonus_tiers_seconds_inclusive": SPEED_BONUS_TIERS[:],
    }


def q_ph_status():
    return {
        "step": 1,
        "key": "ph_status",
        "label": QUESTION_LABELS["ph_status"],
        "prompt": PROMPTS["ph_status"],
        "options": OPTIONS["ph_status"][:],
    }


def q_acid_base_disorder():
    return {
        "step": 2,
        "key": "primary_disorder",
        "label": QUESTION_LABELS["primary_disorder"],
        "prompt": PROMPTS["primary_disorder"],
        "options": OPTIONS["primary_disorder"][:],
    }


def q_compensation(step=3):
    return {
        "step": step,
        "key": "compensation",
        "label": QUESTION_LABELS["compensation"],
        "prompt": PROMPTS["compensation"],
        "options": OPTIONS["compensation"][:],
    }


def q_anion_gap(step=4):
    return {
        "step": step,
        "key": "anion_gap",
        "label": QUESTION_LABELS["anion_gap"],
        "prompt": PROMPTS["anion_gap"],
        "options": OPTIONS["anion_gap"][:],
    }


def q_additional_metabolic_process(step=5):
    return {
        "step": step,
        "key": "additional_metabolic_process",
        "label": QUESTION_LABELS["additional_metabolic_process"],
        "prompt": PROMPTS["additional_metabolic_process"],
        "options": OPTIONS["additional_metabolic_process"][:],
    }


def q_final_diagnosis(step, options):
    return {
        "step": step,
        "key": "final_diagnosis",
        "prompt": "Most likely diagnosis?",
        "options": options,
    }


def beginner_question_flow(final_diagnosis_options=None):
    flow = [q_ph_status(), q_acid_base_disorder()]
    if final_diagnosis_options:
        flow.append(q_final_diagnosis(3, final_diagnosis_options))
    return flow


def intermediate_question_flow(final_diagnosis_options=None):
    flow = [q_ph_status(), q_acid_base_disorder(), q_compensation(3)]
    if final_diagnosis_options:
        flow.append(q_final_diagnosis(4, final_diagnosis_options))
    return flow


def advanced_question_flow(final_diagnosis_options=None):
    flow = [q_ph_status(), q_acid_base_disorder(), q_compensation(3), q_anion_gap(4)]
    if final_diagnosis_options:
        flow.append(q_final_diagnosis(5, final_diagnosis_options))
    return flow


def expert_question_flow(
    final_diagnosis_options=None,
    include_additional_metabolic_process=False,
):
    flow = [q_ph_status(), q_acid_base_disorder(), q_compensation(3), q_anion_gap(4)]
    next_step = 5

    if include_additional_metabolic_process:
        flow.append(q_additional_metabolic_process(5))
        next_step = 6

    if final_diagnosis_options:
        flow.append(q_final_diagnosis(next_step, final_diagnosis_options))

    return flow


def shuffle_question_options(flow):
    shuffled_flow = []

    for question in flow:
        question_copy = question.copy()
        shuffled_flow.append(question_copy)

    return shuffled_flow
