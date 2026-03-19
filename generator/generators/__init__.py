"""Archetype generator package.

This package exposes the public case-builder functions grouped in the
submodules by clinical family: metabolic, respiratory, and mixed disorders.
"""

from .metabolic import (
    generate_alcoholic_ketoacidosis_case,
    generate_diuretic_alkalosis_case,
    generate_diarrhoea_case,
    generate_dka_case,
    generate_lactate_case,
    generate_simple_metabolic_alkalosis_case,
    generate_simple_nagma_case,
    generate_starvation_ketosis_case,
    generate_toxic_alcohol_case,
    generate_uraemia_case,
    generate_vomiting_case,
)
from .mixed import generate_dka_vomiting_case, generate_mixed_hagma_metabolic_alkalosis_case, generate_salicylate_case
from .respiratory import (
    generate_acute_copd_case,
    generate_copd_case,
    generate_opioid_case,
    generate_panic_case,
    generate_sepsis_case,
    generate_simple_respiratory_acidosis_case,
    generate_simple_respiratory_alkalosis_case,
)

__all__ = [
    "generate_acute_copd_case",
    "generate_alcoholic_ketoacidosis_case",
    "generate_copd_case",
    "generate_diuretic_alkalosis_case",
    "generate_diarrhoea_case",
    "generate_dka_case",
    "generate_dka_vomiting_case",
    "generate_lactate_case",
    "generate_mixed_hagma_metabolic_alkalosis_case",
    "generate_opioid_case",
    "generate_panic_case",
    "generate_salicylate_case",
    "generate_sepsis_case",
    "generate_simple_metabolic_alkalosis_case",
    "generate_simple_nagma_case",
    "generate_simple_respiratory_acidosis_case",
    "generate_simple_respiratory_alkalosis_case",
    "generate_starvation_ketosis_case",
    "generate_toxic_alcohol_case",
    "generate_uraemia_case",
    "generate_vomiting_case",
]
