import random

from config import STEM_BANK


def generate_stem(archetype, min_features=2, max_features=3):
    bank = STEM_BANK[archetype]

    age = random.choice(bank["ages"])
    opener = random.choice(bank["openers"])
    pattern = random.choice(bank["patterns"])

    selected_features = []

    if "feature_groups" in bank:
        group_names = list(bank["feature_groups"].keys())
        n_to_use = min(len(group_names), random.randint(min_features, max_features))
        chosen_groups = random.sample(group_names, n_to_use)

        for group_name in chosen_groups:
            selected_features.append(random.choice(bank["feature_groups"][group_name]))
    else:
        n_to_use = min(len(bank["features"]), random.randint(min_features, max_features))
        selected_features = random.sample(bank["features"], n_to_use)

    while len(selected_features) < 3:
        selected_features.append(selected_features[-1])

    return pattern.format(
        age=age,
        opener=opener,
        f1=selected_features[0],
        f2=selected_features[1],
        f3=selected_features[2],
    )
