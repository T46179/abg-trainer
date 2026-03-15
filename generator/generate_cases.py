"""Generator entry point.

This module wires together the shared helper modules and archetype-specific
case builders, assembles the full case set, validates it, and writes the
final JSON payload consumed by the static site.
"""

import json
import os
import random

from .generators import (
    generate_acute_copd_case,
    generate_copd_case,
    generate_diarrhoea_case,
    generate_dka_case,
    generate_dka_vomiting_case,
    generate_lactate_case,
    generate_opioid_case,
    generate_panic_case,
    generate_salicylate_case,
    generate_sepsis_case,
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
    ("OPIOID", generate_opioid_case),
    ("COPD", generate_copd_case),
    ("VOMITING", generate_vomiting_case),
    ("PANIC", generate_panic_case),
    ("DIARRHOEA", generate_diarrhoea_case),
    ("SALICYLATE", generate_salicylate_case),
    ("LACTATE", generate_lactate_case),
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
        for i in range(5):
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
