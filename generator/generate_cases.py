"""Generator entry point.

This module wires together the shared helper modules and archetype-specific
case builders, assembles the full case set, validates it, and writes the
final JSON payload consumed by the static site.
"""

import json
import os
import random

from .config import CASES_PER_ARCHETYPE
from .generators import (
    generate_acute_copd_case,
    generate_alcoholic_ketoacidosis_case,
    generate_copd_case,
    generate_diuretic_alkalosis_case,
    generate_diarrhoea_case,
    generate_dka_case,
    generate_dka_vomiting_case,
    generate_lactate_case,
    generate_mixed_hagma_metabolic_alkalosis_case,
    generate_opioid_case,
    generate_panic_case,
    generate_respiratory_acidosis_hagma_case,
    generate_respiratory_alkalosis_hagma_case,
    generate_salicylate_case,
    generate_sepsis_case,
    generate_simple_metabolic_alkalosis_case,
    generate_simple_nagma_case,
    generate_simple_respiratory_acidosis_case,
    generate_simple_respiratory_alkalosis_case,
    generate_starvation_ketosis_case,
    generate_toxic_alcohol_case,
    generate_uraemia_case,
    generate_vomiting_case,
)
from .progression import (
    build_dashboard_state,
    build_default_user_state,
    build_progression_config,
    print_progression_engine_examples,
    run_progression_simulations,
)
from .reporting import print_generation_report, print_progression_examples
from .validation import generate_valid_case, validate_cases


CASE_BUILDERS = [
    ("DKA", generate_dka_case),
    ("AKA", generate_alcoholic_ketoacidosis_case),
    ("STARVATION", generate_starvation_ketosis_case),
    ("TOXIC_ALCOHOL", generate_toxic_alcohol_case),
    ("SIMPLE_NAGMA", generate_simple_nagma_case),
    ("SIMPLE_MET_ALK", generate_simple_metabolic_alkalosis_case),
    ("OPIOID", generate_opioid_case),
    ("COPD", generate_copd_case),
    ("VOMITING", generate_vomiting_case),
    ("DIURETIC", generate_diuretic_alkalosis_case),
    ("PANIC", generate_panic_case),
    ("SIMPLE_RESP_ALK", generate_simple_respiratory_alkalosis_case),
    ("DIARRHOEA", generate_diarrhoea_case),
    ("URAEMIA", generate_uraemia_case),
    ("SALICYLATE", generate_salicylate_case),
    ("MIXED_HAGMA_MET_ALK", generate_mixed_hagma_metabolic_alkalosis_case),
    ("RESP_ALK_HAGMA", generate_respiratory_alkalosis_hagma_case),
    ("RESP_ACID_HAGMA", generate_respiratory_acidosis_hagma_case),
    ("LACTATE", generate_lactate_case),
    ("SIMPLE_RESP_ACID", generate_simple_respiratory_acidosis_case),
    ("ACUTE_COPD", generate_acute_copd_case),
    ("SEPSIS", generate_sepsis_case),
    ("DKA_VOMIT", generate_dka_vomiting_case),
]


def get_output_path():
    default_output_path = os.path.join(os.path.dirname(__file__), "..", "docs", "abg_cases.json")
    return os.environ.get("ABG_CASES_OUTPUT_PATH", default_output_path)


def generate_all_cases():
    cases = []

    for prefix, generator_fn in CASE_BUILDERS:
        for i in range(CASES_PER_ARCHETYPE):
            case_id = f"{prefix}_{i + 1:03d}"
            cases.append(generate_valid_case(generator_fn, case_id))

    return cases


def main():
    cases = generate_all_cases()
    validation_errors = validate_cases(cases)

    if validation_errors:
        print("Validation failed:\n")
        for err in validation_errors:
            print(f"- {err}")
        raise ValueError(f"{len(validation_errors)} validation error(s) found.")

    random.shuffle(cases)

    output = {
        "progression_config": build_progression_config(),
        "default_user_state": build_default_user_state(),
        "dashboard_state": build_dashboard_state(),
        "cases": cases,
    }

    output_path = get_output_path()

    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(output, handle, indent=2)

    print_generation_report(cases)
    print_progression_examples()
    print_progression_engine_examples()
    run_progression_simulations()
    print(f"\nGenerated {len(cases)} cases successfully with validation passed")


if __name__ == "__main__":
    main()
