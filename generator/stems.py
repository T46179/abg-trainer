"""Clinical stem generation helpers.

The main function, `generate_stem`, turns structured prompt fragments from
the shared stem bank into varied scenario text for each archetype.
"""

import random

from .config import STEM_BANK

OPTIONAL_FEATURE_BUNDLES = {
    "dka": [
        {
            "groups": ("gi", "volume"),
            "templates": [
                "{gi} with {volume}",
                "{volume} and {gi}",
            ],
        },
    ],
    "acute_copd_exacerbation": [
        {
            "groups": ("worsening", "airways"),
            "templates": [
                "{worsening} with {airways}",
                "{airways} with {worsening}",
            ],
        },
    ],
    "panic_hyperventilation": [
        {
            "groups": ("breathing", "chest"),
            "templates": [
                "{breathing} with {chest}",
                "{chest} with {breathing}",
            ],
        },
        {
            "groups": ("breathing", "peripheral"),
            "templates": [
                "{breathing} with {peripheral}",
                "{peripheral} with {breathing}",
            ],
        },
    ],
}


def _pattern_feature_count(pattern):
    if "{f3}" in pattern:
        return 3
    if "{f2}" in pattern:
        return 2
    return 1


def _join_feature_list(features, style):
    if len(features) == 1:
        return features[0]
    if len(features) == 2:
        return f"{features[0]} and {features[1]}"
    if style == "and_only":
        return " and ".join(features)
    if len(features) == 3:
        return f"{features[0]}, {features[1]}, and {features[2]}"
    return f"{', '.join(features[:-1])}, and {features[-1]}"


def _apply_optional_feature_bundle(archetype, selected_by_group):
    bundle_rules = OPTIONAL_FEATURE_BUNDLES.get(archetype, [])
    random.shuffle(bundle_rules)

    for rule in bundle_rules:
        if random.random() >= 0.5:
            continue

        groups = rule["groups"]
        if not all(group in selected_by_group for group in groups):
            continue

        template = random.choice(rule["templates"])
        bundled_feature = template.format(**selected_by_group)
        remaining_features = [
            feature
            for group_name, feature in selected_by_group.items()
            if group_name not in groups
        ]
        return [bundled_feature, *remaining_features]

    return list(selected_by_group.values())


def _build_dynamic_stem(age, opener, features):
    base = f"{age} {opener}"
    style = random.choice(["comma_and", "and_only", "two_sentence"])

    if style == "two_sentence" and len(features) >= 3:
        first_sentence = f"{base} with {_join_feature_list(features[:2], 'and_only')}."
        second_sentence = f"Associated features include {_join_feature_list(features[2:], 'and_only')}."
        return f"{first_sentence} {second_sentence}"

    return f"{base} with {_join_feature_list(features, style)}."


def generate_stem(archetype, min_features=2, max_features=4):
    bank = STEM_BANK[archetype]

    age = random.choice(bank["ages"])
    opener = random.choice(bank["openers"])
    selected_features = []

    if "feature_groups" in bank:
        group_names = list(bank["feature_groups"].keys())
        n_to_use = min(len(group_names), random.randint(min_features, max_features))
        chosen_groups = random.sample(group_names, n_to_use)
        selected_by_group = {}

        for group_name in chosen_groups:
            selected_by_group[group_name] = random.choice(bank["feature_groups"][group_name])

        selected_features = _apply_optional_feature_bundle(archetype, selected_by_group)
    else:
        n_to_use = min(len(bank["features"]), random.randint(min_features, max_features))
        selected_features = random.sample(bank["features"], n_to_use)

    actual_features = selected_features[:]
    random.shuffle(actual_features)
    compatible_patterns = [
        pattern for pattern in bank["patterns"] if _pattern_feature_count(pattern) <= len(actual_features)
    ]
    pattern = random.choice(compatible_patterns or bank["patterns"])

    if len(actual_features) <= 3 and random.choice([True, False]):
        return pattern.format(
            age=age,
            opener=opener,
            f1=actual_features[0],
            f2=actual_features[1] if len(actual_features) > 1 else actual_features[0],
            f3=actual_features[2] if len(actual_features) > 2 else actual_features[-1],
        )

    return _build_dynamic_stem(age, opener, actual_features)
