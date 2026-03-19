"""Clinical stem generation helpers.

The main function, `generate_stem`, turns structured prompt fragments from
the shared stem bank into varied scenario text for each archetype.
"""

import random
import re

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


def _collapse_spaces(text):
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _format_age_with_gender(age_text, gender):
    cleaned = _collapse_spaces(age_text)
    if not cleaned:
        return ""

    match = re.match(r"^(?P<age>\d+)(?:\s*-\s*year\s*-\s*old|\s+year\s+old)?$", cleaned, flags=re.IGNORECASE)
    if not match:
        return cleaned

    age = match.group("age")
    return f"{age}{gender}" if gender else age


def apply_age_gender_shorthand(stem_text, gender=None):
    cleaned = _collapse_spaces(stem_text)
    if not cleaned:
        return cleaned

    if re.search(r"\b\d+[MF]\b", cleaned):
        return cleaned

    gender = gender or random.choice(["M", "F"])

    def replace_age(match):
        return f"{match.group('age')}{gender}"

    return re.sub(
        r"\b(?P<age>\d+)(?:\s*-\s*year\s*-\s*old|\s+year\s+old)\b",
        replace_age,
        cleaned,
        count=1,
        flags=re.IGNORECASE,
    )


def extract_patient_gender(stem_text):
    cleaned = _collapse_spaces(stem_text)
    match = re.search(r"\b\d+(?P<gender>[MF])\b", cleaned)
    if not match:
        return None
    return match.group("gender")


def _leading_connector(fragment):
    match = re.match(r"^(with|after)\b", fragment, flags=re.IGNORECASE)
    if not match:
        return None
    return match.group(1).lower()


def _strip_leading_connector(fragment, connector):
    return _collapse_spaces(re.sub(rf"^{connector}\s+", "", fragment, flags=re.IGNORECASE))


def _clause_contains_after(context):
    current_clause = re.split(r"[.!?]", context or "")[-1]
    return bool(re.search(r"\bafter\b", current_clause, flags=re.IGNORECASE))


def _normalize_feature_fragment(
    fragment,
    *,
    base_connector=None,
    previous_connector=None,
    clause_has_after=False,
    force_strip_with=False,
):
    cleaned = _collapse_spaces(fragment)
    leading = _leading_connector(cleaned)

    if leading == "with" and (
        base_connector in {"with", "include"} or previous_connector == "with" or force_strip_with
    ):
        cleaned = _strip_leading_connector(cleaned, "with")
    elif leading == "after" and (
        base_connector in {"with", "include", "after"} or previous_connector == "after" or clause_has_after
    ):
        cleaned = _strip_leading_connector(cleaned, "after")

    cleaned = _collapse_spaces(cleaned)
    return cleaned, _leading_connector(cleaned)


def _join_feature_list(features, style):
    if not features:
        return ""
    if len(features) == 1:
        return features[0]
    if len(features) == 2:
        return f"{features[0]} and {features[1]}"
    if style == "and_only":
        return " and ".join(features)
    if len(features) == 3:
        return f"{features[0]}, {features[1]}, and {features[2]}"
    return f"{', '.join(features[:-1])}, and {features[-1]}"


def _format_feature_clause(features, style, *, base_connector=None, clause_has_after=False):
    normalized_features = []
    previous_connector = None

    for index, feature in enumerate(features):
        normalized_feature, previous_connector = _normalize_feature_fragment(
            feature,
            base_connector=base_connector,
            previous_connector=previous_connector,
            clause_has_after=clause_has_after,
            force_strip_with=index > 0,
        )
        normalized_features.append(normalized_feature)

    return _join_feature_list(normalized_features, style)


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
    base = _collapse_spaces(f"{age} {opener}")
    style = random.choice(["comma_and", "and_only", "two_sentence"])
    opener_has_after = bool(re.search(r"\bafter\b", opener, flags=re.IGNORECASE))

    if style == "two_sentence" and len(features) >= 3:
        if opener_has_after:
            first_sentence = f"{base}."
            second_sentence = (
                f"Other features include "
                f"{_format_feature_clause(features, 'and_only', base_connector='include', clause_has_after=True)}."
            )
            return f"{first_sentence} {second_sentence}"

        first_sentence = (
            f"{base} with "
            f"{_format_feature_clause(features[:2], 'and_only', base_connector='with')}."
        )
        second_sentence = (
            f"Other features include "
            f"{_format_feature_clause(features[2:], 'and_only', base_connector='include')}."
        )
        return f"{first_sentence} {second_sentence}"

    connector = ", with" if opener_has_after else " with"
    feature_text = _format_feature_clause(
        features,
        style,
        base_connector="with",
        clause_has_after=opener_has_after,
    )
    return f"{base}{connector} {feature_text}."


def _render_pattern(age, opener, pattern, features):
    rendered = pattern.format(age=age, opener=opener, f1="{f1}", f2="{f2}", f3="{f3}")
    previous_connector = None

    for index, placeholder in enumerate(["{f1}", "{f2}", "{f3}"]):
        if placeholder not in rendered or index >= len(features):
            continue

        prefix, suffix = rendered.split(placeholder, 1)
        prefix_clean = prefix.rstrip()
        base_connector = None

        if re.search(r"\binclude(?:s)?\s*$", prefix_clean, flags=re.IGNORECASE):
            base_connector = "include"
        elif re.search(r"\bwith\s*$", prefix_clean, flags=re.IGNORECASE):
            base_connector = "with"
        elif re.search(r"\bafter\s*$", prefix_clean, flags=re.IGNORECASE):
            base_connector = "after"

        feature_text, previous_connector = _normalize_feature_fragment(
            features[index],
            base_connector=base_connector,
            previous_connector=previous_connector,
            clause_has_after=_clause_contains_after(prefix_clean),
            force_strip_with=index > 0,
        )
        rendered = f"{prefix}{feature_text}{suffix}"

    return _collapse_spaces(rendered)


def generate_stem(archetype, min_features=2, max_features=4, return_patient_gender=False):
    bank = STEM_BANK[archetype]

    gender = random.choice(["M", "F"])
    age = random.choice(bank["ages"])
    opener = random.choice(bank["openers"])
    selected_features = []

    if "feature_groups" in bank:
        group_names = list(bank["feature_groups"].keys())
        n_to_use = min(len(group_names), random.randint(min_features, max_features))
        selected_by_group = {}

        if archetype == "alcoholic_ketoacidosis":
            context_groups = [group for group in ["alcohol", "intake", "gi"] if group in group_names]
            sign_groups = [group for group in ["withdrawal", "volume", "respiratory"] if group in group_names]
            chosen_groups = []

            if context_groups:
                chosen_groups.append(random.choice(context_groups))

            if n_to_use > 1 and sign_groups:
                chosen_groups.append(random.choice(sign_groups))

            remaining_groups = [
                group for group in group_names
                if group not in chosen_groups
            ]
            random.shuffle(remaining_groups)
            chosen_groups.extend(remaining_groups[: max(0, n_to_use - len(chosen_groups))])

            for group_name in chosen_groups:
                selected_by_group[group_name] = random.choice(bank["feature_groups"][group_name])

            ordered_group_names = ["alcohol", "intake", "gi", "withdrawal", "volume", "respiratory"]
            selected_features = [
                selected_by_group[group_name]
                for group_name in ordered_group_names
                if group_name in selected_by_group
            ]
        elif archetype == "starvation_ketosis":
            context_groups = [group for group in ["intake"] if group in group_names]
            supportive_groups = [group for group in ["illness", "general", "volume", "gi"] if group in group_names]
            chosen_groups = []

            if context_groups:
                chosen_groups.extend(context_groups)

            if n_to_use > len(chosen_groups) and supportive_groups:
                chosen_groups.append(random.choice(supportive_groups))

            remaining_groups = [
                group for group in group_names
                if group not in chosen_groups
            ]
            random.shuffle(remaining_groups)
            chosen_groups.extend(remaining_groups[: max(0, n_to_use - len(chosen_groups))])

            for group_name in chosen_groups:
                selected_by_group[group_name] = random.choice(bank["feature_groups"][group_name])

            ordered_group_names = ["intake", "illness", "general", "volume", "gi"]
            selected_features = [
                selected_by_group[group_name]
                for group_name in ordered_group_names
                if group_name in selected_by_group
            ]
        elif archetype == "toxic_alcohol":
            context_groups = [group for group in ["exposure", "neurologic", "visual"] if group in group_names]
            chosen_groups = []

            if context_groups:
                chosen_groups.append(random.choice(context_groups))

            remaining_groups = [
                group for group in group_names
                if group not in chosen_groups
            ]
            random.shuffle(remaining_groups)
            chosen_groups.extend(remaining_groups[: max(0, n_to_use - len(chosen_groups))])

            for group_name in chosen_groups:
                selected_by_group[group_name] = random.choice(bank["feature_groups"][group_name])

            selected_features = list(selected_by_group.values())
        else:
            chosen_groups = random.sample(group_names, n_to_use)

            for group_name in chosen_groups:
                selected_by_group[group_name] = random.choice(bank["feature_groups"][group_name])

            selected_features = _apply_optional_feature_bundle(archetype, selected_by_group)
    else:
        n_to_use = min(len(bank["features"]), random.randint(min_features, max_features))
        selected_features = random.sample(bank["features"], n_to_use)

    actual_features = selected_features[:]
    if archetype not in {"alcoholic_ketoacidosis", "starvation_ketosis"}:
        random.shuffle(actual_features)
    compatible_patterns = [
        pattern for pattern in bank["patterns"] if _pattern_feature_count(pattern) <= len(actual_features)
    ]
    pattern = random.choice(compatible_patterns or bank["patterns"])

    if len(actual_features) <= 3 and random.choice([True, False]):
        selected_for_pattern = [
            actual_features[0],
            actual_features[1] if len(actual_features) > 1 else actual_features[0],
            actual_features[2] if len(actual_features) > 2 else actual_features[-1],
        ]
        stem = apply_age_gender_shorthand(_render_pattern(age, opener, pattern, selected_for_pattern), gender=gender)
        return (stem, gender) if return_patient_gender else stem

    stem = apply_age_gender_shorthand(_build_dynamic_stem(age, opener, actual_features), gender=gender)
    return (stem, gender) if return_patient_gender else stem
