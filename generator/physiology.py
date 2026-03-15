"""Physiology and numeric helper functions for ABG case generation.

Main responsibilities:
- round and format generated values consistently
- calculate pH and compensation expectations
- derive anion gap and pH status labels
- provide small reusable clinical math helpers
"""

import math


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
        },
    }

    if lactate is not None:
        inputs["lactate_mmolL"] = r_lactate(lactate)

    return inputs


def get_display_values(inputs):
    gas = inputs["gas"]
    electrolytes = inputs["electrolytes"]
    return (
        gas["ph"],
        gas["paco2_mmHg"],
        gas["hco3_mmolL"],
        electrolytes["na_mmolL"],
        electrolytes["cl_mmolL"],
        inputs.get("lactate_mmolL"),
    )


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
        return "Acidaemia"
    if ph > 7.45:
        return "Alkalaemia"
    return "Normal"


def in_range(value, low, high, tolerance=0.05):
    return (low - tolerance) <= value <= (high + tolerance)
