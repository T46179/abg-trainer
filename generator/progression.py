"""Progression and XP helpers for generated training data.

Main functions in this module:
- build progression metadata attached to each case
- calculate XP awards, levels, and unlocked difficulty
- build default user and dashboard state examples
- print progression examples and simulations used during generation
"""

from .config import (
    BASE_XP_BY_DIFFICULTY,
    DIFFICULTY_UNLOCK_LEVELS,
    FREE_DAILY_CASE_LIMIT,
    PERFECT_CASE_BONUS_PERCENT,
    PROGRESSION_VERSION,
    SPEED_BONUS_TIERS,
    STREAK_BONUS_TIERS,
    TESTING_MODE,
    TESTING_XP_MULTIPLIER,
    XP_REQUIRED_PER_LEVEL,
)


def difficulty_label(level):
    mapping = {
        1: "beginner",
        2: "intermediate",
        3: "advanced",
        4: "master",
    }
    return mapping.get(level, "custom")


def skills_for_case(level, is_mixed=False):
    if is_mixed:
        return [
            "ph_status",
            "primary_disorder",
            "compensation",
            "anion_gap",
            "mixed_disorder_detection",
            "final_diagnosis",
        ]

    mapping = {
        1: ["ph_status", "primary_disorder", "final_diagnosis"],
        2: ["ph_status", "primary_disorder", "compensation", "final_diagnosis"],
        3: ["ph_status", "primary_disorder", "compensation", "anion_gap", "final_diagnosis"],
        4: ["ph_status", "primary_disorder", "compensation", "anion_gap", "final_diagnosis"],
    }
    return mapping.get(level, [])


def case_pool_for_archetype(archetype):
    mapping = {
        "dka": "core_metabolic",
        "diuretic_metabolic_alkalosis": "core_metabolic",
        "diarrhoea_nagma": "core_metabolic",
        "uraemia": "core_metabolic",
        "vomiting_metabolic_alkalosis": "core_metabolic",
        "opioid_toxicity": "core_respiratory",
        "copd_chronic_retainer": "core_respiratory",
        "panic_hyperventilation": "core_respiratory",
        "salicylate_toxicity": "mixed_disorders",
    }
    return mapping.get(archetype, "core")


def base_xp_for_difficulty(level):
    return BASE_XP_BY_DIFFICULTY.get(level, 0)


def attach_progression_metadata(case, level, archetype, is_mixed=False):
    case["archetype"] = archetype
    case["difficulty_level"] = level
    case["difficulty_label"] = difficulty_label(level)
    case["skills_tested"] = skills_for_case(level, is_mixed)
    case["case_pool"] = case_pool_for_archetype(archetype)
    case["progression"] = {"base_xp": base_xp_for_difficulty(level)}
    return case


def perfect_case_bonus(level):
    base_xp = base_xp_for_difficulty(level)
    return round(base_xp * PERFECT_CASE_BONUS_PERCENT)


def speed_bonus_for_seconds(seconds):
    for tier in SPEED_BONUS_TIERS:
        if seconds <= tier["max_seconds"]:
            return tier["bonus"]
    return 0


def streak_bonus_for_days(streak_days):
    bonus = 0
    for tier in STREAK_BONUS_TIERS:
        if streak_days >= tier["min_days"]:
            bonus = tier["bonus"]
    return bonus


def xp_to_reach_level(target_level):
    if target_level <= 1:
        return 0

    total = 0
    for level in range(1, target_level):
        total += XP_REQUIRED_PER_LEVEL.get(level, 0)
    return total


def level_from_total_xp(total_xp):
    level = 1

    while True:
        xp_needed = XP_REQUIRED_PER_LEVEL.get(level)
        if xp_needed is None:
            return level

        threshold_for_next = xp_to_reach_level(level + 1)
        if total_xp < threshold_for_next:
            return level

        level += 1


def unlocked_difficulty_for_level(user_level):
    unlocked = 1
    for difficulty, required_level in DIFFICULTY_UNLOCK_LEVELS.items():
        if user_level >= required_level:
            unlocked = difficulty
    return unlocked


def calculate_case_xp_award(
    difficulty_level,
    perfect_case=False,
    seconds_taken=None,
    streak_days=0,
):
    base_xp = base_xp_for_difficulty(difficulty_level)
    perfect_bonus = perfect_case_bonus(difficulty_level) if perfect_case else 0
    speed_bonus = speed_bonus_for_seconds(seconds_taken) if seconds_taken is not None else 0
    streak_bonus = streak_bonus_for_days(streak_days)
    total_xp = base_xp + perfect_bonus + speed_bonus + streak_bonus

    return {
        "base_xp": base_xp,
        "perfect_bonus": perfect_bonus,
        "speed_bonus": speed_bonus,
        "streak_bonus": streak_bonus,
        "total_xp": total_xp,
    }


def build_progression_config():
    return {
        "version": PROGRESSION_VERSION,
        "testing_mode": TESTING_MODE,
        "testing_xp_multiplier": TESTING_XP_MULTIPLIER,
        "base_xp_by_difficulty": BASE_XP_BY_DIFFICULTY,
        "perfect_case_bonus_percent": PERFECT_CASE_BONUS_PERCENT,
        "speed_bonus_tiers": SPEED_BONUS_TIERS,
        "streak_bonus_tiers": STREAK_BONUS_TIERS,
        "xp_required_per_level": XP_REQUIRED_PER_LEVEL,
        "difficulty_unlock_levels": DIFFICULTY_UNLOCK_LEVELS,
        "free_daily_case_limit": FREE_DAILY_CASE_LIMIT,
        "difficulty_labels": {
            level: difficulty_label(level) for level in sorted(BASE_XP_BY_DIFFICULTY.keys())
        },
    }


def process_case_completion(
    current_total_xp,
    difficulty_level,
    perfect_case=False,
    seconds_taken=None,
    streak_days=0,
):
    xp_award = calculate_case_xp_award(
        difficulty_level=difficulty_level,
        perfect_case=perfect_case,
        seconds_taken=seconds_taken,
        streak_days=streak_days,
    )

    previous_total_xp = current_total_xp
    new_total_xp = current_total_xp + xp_award["total_xp"]
    previous_level = level_from_total_xp(previous_total_xp)
    new_level = level_from_total_xp(new_total_xp)
    previous_unlocked_difficulty = unlocked_difficulty_for_level(previous_level)
    new_unlocked_difficulty = unlocked_difficulty_for_level(new_level)

    return {
        "xp_award": xp_award,
        "previous_total_xp": previous_total_xp,
        "new_total_xp": new_total_xp,
        "previous_level": previous_level,
        "new_level": new_level,
        "leveled_up": new_level > previous_level,
        "levels_gained": new_level - previous_level,
        "previous_unlocked_difficulty": previous_unlocked_difficulty,
        "new_unlocked_difficulty": new_unlocked_difficulty,
        "difficulty_unlocked": new_unlocked_difficulty > previous_unlocked_difficulty,
    }


def get_level_progress(total_xp):
    level = level_from_total_xp(total_xp)
    current_level_start_xp = xp_to_reach_level(level)
    xp_needed_for_next_level = XP_REQUIRED_PER_LEVEL.get(level)

    if xp_needed_for_next_level is None:
        return {
            "level": level,
            "xp_into_level": total_xp - current_level_start_xp,
            "xp_needed_for_next_level": None,
            "current_level_start_xp": current_level_start_xp,
            "next_level_total_xp": None,
        }

    return {
        "level": level,
        "xp_into_level": total_xp - current_level_start_xp,
        "xp_needed_for_next_level": xp_needed_for_next_level,
        "current_level_start_xp": current_level_start_xp,
        "next_level_total_xp": current_level_start_xp + xp_needed_for_next_level,
    }


def build_user_progression_state(total_xp, streak_days=0):
    level = level_from_total_xp(total_xp)
    unlocked_difficulty = unlocked_difficulty_for_level(level)
    level_progress = get_level_progress(total_xp)

    return {
        "total_xp": total_xp,
        "level": level,
        "level_progress": level_progress,
        "unlocked_difficulty": unlocked_difficulty,
        "unlocked_difficulty_label": difficulty_label(unlocked_difficulty),
        "streak_days": streak_days,
    }


def print_progression_engine_examples():
    examples = [
        {
            "name": "Beginner perfect fast case",
            "current_total_xp": 0,
            "difficulty_level": 1,
            "perfect_case": True,
            "seconds_taken": 40,
            "streak_days": 0,
        },
        {
            "name": "Intermediate perfect streak case",
            "current_total_xp": 220,
            "difficulty_level": 2,
            "perfect_case": True,
            "seconds_taken": 28,
            "streak_days": 7,
        },
        {
            "name": "Master case slower, not perfect",
            "current_total_xp": 900,
            "difficulty_level": 4,
            "perfect_case": False,
            "seconds_taken": 80,
            "streak_days": 3,
        },
    ]

    print("\nProgression engine examples")
    print("---------------------------")

    for example in examples:
        result = process_case_completion(
            current_total_xp=example["current_total_xp"],
            difficulty_level=example["difficulty_level"],
            perfect_case=example["perfect_case"],
            seconds_taken=example["seconds_taken"],
            streak_days=example["streak_days"],
        )
        progress = get_level_progress(result["new_total_xp"])

        print(f"\n{example['name']}")
        print(f"XP award: {result['xp_award']}")
        print(f"Old XP: {result['previous_total_xp']} -> New XP: {result['new_total_xp']}")
        print(f"Level: {result['previous_level']} -> {result['new_level']}")
        print(f"Unlocked difficulty: {difficulty_label(result['new_unlocked_difficulty'])}")
        print(f"XP into current level: {progress['xp_into_level']}")
        print(f"XP needed for next level: {progress['xp_needed_for_next_level']}")


def simulate_user_progression(case_results_per_day, starting_xp=0, starting_streak=0):
    total_xp = starting_xp
    streak_days = starting_streak
    history = []

    for day_index, day_cases in enumerate(case_results_per_day, start=1):
        if day_cases:
            streak_days += 1
        else:
            streak_days = 0

        day_start_xp = total_xp
        day_start_level = level_from_total_xp(total_xp)
        case_summaries = []

        for case_result in day_cases:
            outcome = process_case_completion(
                current_total_xp=total_xp,
                difficulty_level=case_result["difficulty_level"],
                perfect_case=case_result.get("perfect_case", False),
                seconds_taken=case_result.get("seconds_taken"),
                streak_days=streak_days,
            )
            total_xp = outcome["new_total_xp"]
            case_summaries.append(outcome)

        day_end_level = level_from_total_xp(total_xp)
        unlocked_difficulty = unlocked_difficulty_for_level(day_end_level)

        history.append({
            "day": day_index,
            "cases_completed": len(day_cases),
            "streak_days": streak_days,
            "day_start_xp": day_start_xp,
            "day_end_xp": total_xp,
            "xp_gained_today": total_xp - day_start_xp,
            "day_start_level": day_start_level,
            "day_end_level": day_end_level,
            "unlocked_difficulty": unlocked_difficulty,
            "unlocked_difficulty_label": difficulty_label(unlocked_difficulty),
            "case_summaries": case_summaries,
        })

    return {
        "final_total_xp": total_xp,
        "final_level": level_from_total_xp(total_xp),
        "final_unlocked_difficulty": unlocked_difficulty_for_level(level_from_total_xp(total_xp)),
        "final_unlocked_difficulty_label": difficulty_label(
            unlocked_difficulty_for_level(level_from_total_xp(total_xp))
        ),
        "history": history,
    }


def print_simulation_summary(simulation_result):
    print("\nUser progression simulation")
    print("---------------------------")

    for day in simulation_result["history"]:
        print(
            f"Day {day['day']}: "
            f"{day['cases_completed']} cases, "
            f"streak {day['streak_days']}, "
            f"+{day['xp_gained_today']} XP, "
            f"Level {day['day_start_level']} -> {day['day_end_level']}, "
            f"Unlocked: {day['unlocked_difficulty_label']}"
        )

    print("\nFinal result")
    print(f"Total XP: {simulation_result['final_total_xp']}")
    print(f"Level: {simulation_result['final_level']}")
    print(f"Unlocked difficulty: {simulation_result['final_unlocked_difficulty_label']}")


def build_test_scenarios():
    return {
        "fast_beginner": [
            [
                {"difficulty_level": 1, "perfect_case": True, "seconds_taken": 35},
                {"difficulty_level": 1, "perfect_case": True, "seconds_taken": 42},
                {"difficulty_level": 1, "perfect_case": False, "seconds_taken": 55},
                {"difficulty_level": 1, "perfect_case": True, "seconds_taken": 38},
                {"difficulty_level": 1, "perfect_case": False, "seconds_taken": 65},
            ],
            [
                {"difficulty_level": 1, "perfect_case": True, "seconds_taken": 30},
                {"difficulty_level": 1, "perfect_case": True, "seconds_taken": 40},
                {"difficulty_level": 1, "perfect_case": True, "seconds_taken": 48},
                {"difficulty_level": 1, "perfect_case": False, "seconds_taken": 58},
                {"difficulty_level": 1, "perfect_case": True, "seconds_taken": 36},
            ],
            [
                {"difficulty_level": 1, "perfect_case": True, "seconds_taken": 29},
                {"difficulty_level": 1, "perfect_case": True, "seconds_taken": 34},
                {"difficulty_level": 1, "perfect_case": False, "seconds_taken": 52},
                {"difficulty_level": 1, "perfect_case": True, "seconds_taken": 41},
                {"difficulty_level": 1, "perfect_case": True, "seconds_taken": 33},
            ],
            [
                {"difficulty_level": 1, "perfect_case": True, "seconds_taken": 27},
                {"difficulty_level": 1, "perfect_case": True, "seconds_taken": 39},
                {"difficulty_level": 1, "perfect_case": True, "seconds_taken": 44},
                {"difficulty_level": 1, "perfect_case": False, "seconds_taken": 61},
                {"difficulty_level": 1, "perfect_case": True, "seconds_taken": 35},
            ],
        ],
        "average_beginner": [
            [
                {"difficulty_level": 1, "perfect_case": False, "seconds_taken": 62},
                {"difficulty_level": 1, "perfect_case": True, "seconds_taken": 54},
                {"difficulty_level": 1, "perfect_case": False, "seconds_taken": 70},
                {"difficulty_level": 1, "perfect_case": False, "seconds_taken": 58},
                {"difficulty_level": 1, "perfect_case": True, "seconds_taken": 47},
            ],
            [
                {"difficulty_level": 1, "perfect_case": False, "seconds_taken": 60},
                {"difficulty_level": 1, "perfect_case": True, "seconds_taken": 50},
                {"difficulty_level": 1, "perfect_case": False, "seconds_taken": 68},
                {"difficulty_level": 1, "perfect_case": True, "seconds_taken": 45},
                {"difficulty_level": 1, "perfect_case": False, "seconds_taken": 72},
            ],
            [
                {"difficulty_level": 1, "perfect_case": True, "seconds_taken": 49},
                {"difficulty_level": 1, "perfect_case": False, "seconds_taken": 63},
                {"difficulty_level": 1, "perfect_case": True, "seconds_taken": 52},
                {"difficulty_level": 1, "perfect_case": False, "seconds_taken": 66},
                {"difficulty_level": 1, "perfect_case": True, "seconds_taken": 44},
            ],
            [
                {"difficulty_level": 1, "perfect_case": False, "seconds_taken": 59},
                {"difficulty_level": 1, "perfect_case": True, "seconds_taken": 46},
                {"difficulty_level": 1, "perfect_case": False, "seconds_taken": 64},
                {"difficulty_level": 1, "perfect_case": True, "seconds_taken": 43},
                {"difficulty_level": 1, "perfect_case": False, "seconds_taken": 69},
            ],
        ],
        "very_fast_user": [
            [
                {"difficulty_level": 1, "perfect_case": True, "seconds_taken": 24},
                {"difficulty_level": 1, "perfect_case": True, "seconds_taken": 28},
                {"difficulty_level": 1, "perfect_case": True, "seconds_taken": 26},
                {"difficulty_level": 1, "perfect_case": True, "seconds_taken": 29},
                {"difficulty_level": 1, "perfect_case": True, "seconds_taken": 25},
            ],
            [
                {"difficulty_level": 1, "perfect_case": True, "seconds_taken": 24},
                {"difficulty_level": 1, "perfect_case": True, "seconds_taken": 27},
                {"difficulty_level": 1, "perfect_case": True, "seconds_taken": 28},
                {"difficulty_level": 1, "perfect_case": True, "seconds_taken": 29},
                {"difficulty_level": 1, "perfect_case": True, "seconds_taken": 26},
            ],
            [
                {"difficulty_level": 1, "perfect_case": True, "seconds_taken": 23},
                {"difficulty_level": 1, "perfect_case": True, "seconds_taken": 25},
                {"difficulty_level": 1, "perfect_case": True, "seconds_taken": 27},
                {"difficulty_level": 1, "perfect_case": True, "seconds_taken": 29},
                {"difficulty_level": 1, "perfect_case": True, "seconds_taken": 24},
            ],
        ],
    }


def run_progression_simulations():
    scenarios = build_test_scenarios()

    for scenario_name, case_results_per_day in scenarios.items():
        print(f"\n=== Scenario: {scenario_name} ===")
        simulation = simulate_user_progression(case_results_per_day)
        print_simulation_summary(simulation)


def build_default_user_state():
    total_xp = 0
    streak_days = 0
    level = level_from_total_xp(total_xp)
    unlocked_difficulty = unlocked_difficulty_for_level(level)

    return {
        "total_xp": total_xp,
        "level": level,
        "level_progress": get_level_progress(total_xp),
        "unlocked_difficulty": unlocked_difficulty,
        "unlocked_difficulty_label": difficulty_label(unlocked_difficulty),
        "streak_days": streak_days,
        "cases_completed_today": 0,
        "daily_case_limit": FREE_DAILY_CASE_LIMIT,
        "cases_remaining_today": FREE_DAILY_CASE_LIMIT,
        "subscription_tier": "free",
    }


def build_difficulty_cards(user_level=1, subscription_tier="free"):
    cards = []
    tier = str(subscription_tier).lower()

    for difficulty in sorted(DIFFICULTY_UNLOCK_LEVELS.keys()):
        required_level = DIFFICULTY_UNLOCK_LEVELS[difficulty]
        label = difficulty_label(difficulty)
        unlocked_by_level = tier == "exam_prep" or user_level >= required_level

        cards.append({
            "difficulty_level": difficulty,
            "label": label.title(),
            "unlock_level": required_level,
            "is_unlocked": unlocked_by_level,
            "is_locked": not unlocked_by_level,
        })

    return cards


def build_dashboard_state(
    total_xp=0,
    streak_days=0,
    cases_completed_today=0,
    subscription_tier="free",
):
    user_state = build_user_progression_state(total_xp, streak_days=streak_days)
    daily_limit = None if subscription_tier in ["premium", "exam_prep"] else FREE_DAILY_CASE_LIMIT
    cases_remaining_today = None if daily_limit is None else max(0, daily_limit - cases_completed_today)

    return {
        "user": {
            "subscription_tier": subscription_tier,
            "total_xp": user_state["total_xp"],
            "level": user_state["level"],
            "level_progress": user_state["level_progress"],
            "unlocked_difficulty": user_state["unlocked_difficulty"],
            "unlocked_difficulty_label": user_state["unlocked_difficulty_label"],
            "streak_days": streak_days,
            "cases_completed_today": cases_completed_today,
            "daily_case_limit": daily_limit,
            "cases_remaining_today": cases_remaining_today,
        },
        "difficulty_cards": build_difficulty_cards(
            user_level=user_state["level"],
            subscription_tier=subscription_tier,
        ),
        "stats": {
            "cases_completed": 0,
            "accuracy_percent": 0,
            "recent_badges": [],
        },
    }
