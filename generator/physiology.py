"""Physiology and numeric helper functions for ABG case generation.

Main responsibilities:
- round and format generated values consistently
- calculate pH and compensation expectations
- derive anion gap and pH status labels
- provide small reusable clinical math helpers
"""

import math
import random


PH_DP = 2
GAS_DP = 1
ELECTROLYTE_DP = 0
LACTATE_DP = 1
AG_DP = 1
POTASSIUM_DP = 1
GLUCOSE_DP = 1
BASE_EXCESS_DP = 1
OXYGEN_DP = 1
PERCENT_DP = 1
HB_DP = 0
MASTER_DEFAULT_GLUCOSE_RANGE = (4.2, 5.8)


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


def r_potassium(x):
    return round(x, POTASSIUM_DP)


def r_glucose(x):
    return round(x, GLUCOSE_DP)


def r_base_excess(x):
    return round(x, BASE_EXCESS_DP)


def r_oxygen(x):
    return round(x, OXYGEN_DP)


def r_percent(x):
    return round(x, PERCENT_DP)


def r_hb(x):
    return int(round(x))


INPUT_SCHEMA = {
    "gas": (
        ("ph", "ph", r_ph),
        ("paco2", "paco2_mmHg", r_gas),
        ("hco3", "hco3_mmolL", r_gas),
        ("pao2", "pao2_mmHg", r_oxygen),
        ("base_excess", "base_excess_mEqL", r_base_excess),
        ("spo2", "spo2_percent", r_percent),
    ),
    "electrolytes": (
        ("na", "na_mmolL", r_lyte),
        ("k", "k_mmolL", r_potassium),
        ("cl", "cl_mmolL", r_lyte),
        ("glucose", "glucose_mmolL", r_glucose),
    ),
    "other": (
        ("lactate", "lactate_mmolL", r_lactate),
        ("hb", "hb_gL", r_hb),
        ("methb", "methb_percent", r_percent),
        ("cohb", "cohb_percent", r_percent),
    ),
}


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
    values = {
        "ph": ph,
        "paco2": paco2,
        "hco3": hco3,
        "na": na,
        "cl": cl,
        "lactate": lactate,
        "pao2": pao2,
        "base_excess": base_excess,
        "k": k,
        "glucose": glucose,
        "spo2": spo2,
        "hb": hb,
        "methb": methb,
        "cohb": cohb,
    }

    inputs = {}
    for container, fields in INPUT_SCHEMA.items():
        normalized = {}
        for arg_name, field_name, rounder in fields:
            raw_value = values.get(arg_name)
            if raw_value is None:
                continue
            normalized[field_name] = rounder(raw_value)

        if normalized:
            inputs[container] = normalized

    # Transitional compatibility: keep the legacy top-level lactate path.
    canonical_lactate = inputs.get("other", {}).get("lactate_mmolL")
    if canonical_lactate is not None:
        inputs["lactate_mmolL"] = canonical_lactate

    return inputs


def ensure_level_based_input_defaults(inputs, *, level):
    normalized_inputs = dict(inputs or {})
    electrolytes = dict(normalized_inputs.get("electrolytes") or {})

    if level >= 4 and electrolytes.get("glucose_mmolL") is None:
        electrolytes["glucose_mmolL"] = r_glucose(random.uniform(*MASTER_DEFAULT_GLUCOSE_RANGE))
        normalized_inputs["electrolytes"] = electrolytes

    return normalized_inputs


def get_display_values(inputs):
    gas = inputs["gas"]
    electrolytes = inputs["electrolytes"]
    other = inputs.get("other", {})
    return (
        gas["ph"],
        gas["paco2_mmHg"],
        gas["hco3_mmolL"],
        electrolytes["na_mmolL"],
        electrolytes["cl_mmolL"],
        other.get("lactate_mmolL", inputs.get("lactate_mmolL")),
    )


def winters_expected_paco2(hco3):
    return 1.5 * hco3 + 8


def calculate_ph_from_hco3_paco2(hco3, paco2):
    return r_ph(6.1 + math.log10(hco3 / (0.03 * paco2)))


def estimate_ph(hco3, paco2):
    return calculate_ph_from_hco3_paco2(hco3, paco2)


def acute_respiratory_acidosis_expected_hco3(paco2):
    return 24 + ((paco2 - 40) / 10)


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


def isolated_hagma_expected_hco3(anion_gap, *, normal_anion_gap=12, normal_hco3=24):
    return r_gas(normal_hco3 - (anion_gap - normal_anion_gap))


def hagma_bicarbonate_preservation(anion_gap, hco3, *, normal_anion_gap=12, normal_hco3=24):
    expected_hco3 = isolated_hagma_expected_hco3(
        anion_gap,
        normal_anion_gap=normal_anion_gap,
        normal_hco3=normal_hco3,
    )
    return r_gas(hco3 - expected_hco3)


def derived_ph_status(ph):
    if ph < 7.35:
        return "Acidaemia"
    if ph > 7.45:
        return "Alkalaemia"
    return "Normal"


def in_range(value, low, high, tolerance=0.05):
    return (low - tolerance) <= value <= (high + tolerance)
