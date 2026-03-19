import json
import re
from pathlib import Path

# ===== SETTINGS =====
JSON_FILE = Path(r"E:\Desktop\abg-trainer\docs\abg_cases.json")
OUTPUT_DIR = Path(r"E:\Desktop\abg-trainer\extracted cases")
GROUP_BY = "final_diagnosis"  # options: "final_diagnosis", "archetype", "case_id_prefix"


def safe_filename(name: str) -> str:
    """Make a string safe to use as a Windows filename."""
    name = str(name).strip().lower()
    name = name.replace("/", " - ")
    name = re.sub(r'[<>:"\\|?*]', "", name)
    name = re.sub(r"\s+", "_", name)
    return name


def get_group_name(case: dict, group_by: str) -> str:
    """Pick the grouping label for a case."""
    if group_by == "final_diagnosis":
        return (
            case.get("answer_key", {}).get("final_diagnosis")
            or case.get("archetype")
            or case.get("case_id", "unknown").split("_")[0]
        )

    if group_by == "archetype":
        return (
            case.get("archetype")
            or case.get("answer_key", {}).get("final_diagnosis")
            or case.get("case_id", "unknown").split("_")[0]
        )

    if group_by == "case_id_prefix":
        return case.get("case_id", "unknown").split("_")[0]

    return "unknown"


def main():
    if not JSON_FILE.exists():
        print(f"JSON file not found: {JSON_FILE}")
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with JSON_FILE.open("r", encoding="utf-8") as f:
        data = json.load(f)

    cases = data.get("cases", [])
    if not cases:
        print("No cases found under 'cases' in the JSON file.")
        return

    grouped = {}

    for case in cases:
        group_name = get_group_name(case, GROUP_BY)
        grouped.setdefault(group_name, []).append(case)

    for group_name, group_cases in grouped.items():
        filename = safe_filename(group_name) + ".txt"
        output_path = OUTPUT_DIR / filename

        with output_path.open("w", encoding="utf-8") as f:
            f.write(f"Group: {group_name}\n")
            f.write(f"Number of cases: {len(group_cases)}\n")
            f.write("=" * 80 + "\n\n")

            for case in group_cases:
                f.write(json.dumps(case, indent=2, ensure_ascii=False))
                f.write("\n\n" + "-" * 80 + "\n\n")

        print(f"Saved: {output_path}")

    print("\nDone.")


if __name__ == "__main__":
    main()