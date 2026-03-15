"""Reporting helpers for the generator.

These functions print high-level summaries of the generated case set and
sample XP calculations so generation output is easier to inspect manually.
"""

from collections import Counter

from .progression import calculate_case_xp_award


def print_generation_report(cases):
    archetypes = Counter(case.get("archetype", "unknown") for case in cases)
    difficulties = Counter(case.get("difficulty_level", "unknown") for case in cases)

    ph_values = [case["inputs"]["gas"]["ph"] for case in cases]
    paco2_values = [case["inputs"]["gas"]["paco2_mmHg"] for case in cases]
    hco3_values = [case["inputs"]["gas"]["hco3_mmolL"] for case in cases]

    print("\nGeneration report")
    print("-----------------")
    print(f"Total cases: {len(cases)}")
    print(f"Archetypes: {dict(archetypes)}")
    print(f"Difficulties: {dict(difficulties)}")
    print(f"pH range: {min(ph_values)} â†’ {max(ph_values)}")
    print(f"PaCO2 range: {min(paco2_values)} â†’ {max(paco2_values)}")
    print(f"HCO3 range: {min(hco3_values)} â†’ {max(hco3_values)}")


def print_progression_examples():
    examples = [
        ("Beginner perfect fast", calculate_case_xp_award(1, perfect_case=True, seconds_taken=40, streak_days=0)),
        ("Intermediate perfect streak", calculate_case_xp_award(2, perfect_case=True, seconds_taken=28, streak_days=7)),
        ("Master not perfect", calculate_case_xp_award(4, perfect_case=False, seconds_taken=80, streak_days=0)),
    ]

    print("\nProgression examples")
    print("--------------------")
    for name, result in examples:
        print(f"{name}: {result}")
