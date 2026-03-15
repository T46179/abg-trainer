"""Tests for the ABG case generator entry point and output shape."""

import json
import math
import shutil
import sys
import unittest
from collections import Counter
from pathlib import Path


GENERATOR_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = GENERATOR_DIR.parent
WORKSPACE_ROOT = REPO_ROOT.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from generator import generate_cases  # noqa: E402


class GenerateCasesTests(unittest.TestCase):
    def setUp(self):
        self.output_path = REPO_ROOT / "docs" / "abg_cases.json"
        self.backup_path = self.output_path.with_suffix(".json.test-backup")

        if self.output_path.exists():
            shutil.copy2(self.output_path, self.backup_path)

    def tearDown(self):
        if self.backup_path.exists():
            shutil.move(self.backup_path, self.output_path)

    def test_generate_all_cases_preserves_expected_archetype_counts(self):
        cases = generate_cases.generate_all_cases()
        counts = Counter(case["archetype"] for case in cases)

        expected = {
            "dka": 5,
            "opioid_toxicity": 5,
            "copd_chronic_retainer": 5,
            "vomiting_metabolic_alkalosis": 5,
            "panic_hyperventilation": 5,
            "diarrhoea_nagma": 5,
            "salicylate_toxicity": 5,
            "lactic_acidosis": 5,
            "acute_copd_exacerbation": 5,
            "sepsis_respiratory_alkalosis": 5,
            "dka_vomiting": 5,
        }

        self.assertEqual(len(cases), 55)
        self.assertEqual(dict(counts), expected)

    def test_every_case_has_required_fields(self):
        cases = generate_cases.generate_all_cases()

        required_top_level = {
            "case_id",
            "title",
            "case_type",
            "category",
            "clinical_stem",
            "inputs",
            "questions_flow",
            "answer_key",
            "archetype",
            "difficulty_level",
        }

        for case in cases:
            self.assertTrue(required_top_level.issubset(case.keys()), msg=case.get("case_id"))
            self.assertIn("gas", case["inputs"], msg=case["case_id"])
            self.assertIn("electrolytes", case["inputs"], msg=case["case_id"])
            self.assertIsInstance(case["questions_flow"], list, msg=case["case_id"])
            self.assertGreater(len(case["questions_flow"]), 0, msg=case["case_id"])
            self.assertIsInstance(case["answer_key"], dict, msg=case["case_id"])

    def test_generated_cases_are_physically_plausible(self):
        cases = generate_cases.generate_all_cases()

        for case in cases:
            gas = case["inputs"]["gas"]
            case_id = case["case_id"]

            self.assertTrue(6.8 <= gas["ph"] <= 7.8, msg=f"{case_id}: implausible pH {gas['ph']}")
            self.assertTrue(
                10 <= gas["paco2_mmHg"] <= 120,
                msg=f"{case_id}: implausible PaCO2 {gas['paco2_mmHg']}",
            )
            self.assertTrue(
                5 <= gas["hco3_mmolL"] <= 60,
                msg=f"{case_id}: implausible HCO3 {gas['hco3_mmolL']}",
            )

    def test_generated_cases_match_henderson_hasselbalch_within_tolerance(self):
        cases = generate_cases.generate_all_cases()

        for case in cases:
            gas = case["inputs"]["gas"]
            case_id = case["case_id"]
            expected_ph = 6.1 + math.log10(gas["hco3_mmolL"] / (0.03 * gas["paco2_mmHg"]))
            rounded_expected_ph = round(expected_ph, 2)

            self.assertAlmostEqual(
                gas["ph"],
                rounded_expected_ph,
                delta=0.03,
                msg=(
                    f"{case_id}: pH {gas['ph']} inconsistent with Henderson-Hasselbalch "
                    f"estimate {rounded_expected_ph}"
                ),
            )

    def test_main_writes_valid_json_payload(self):
        generate_cases.main()

        self.assertTrue(self.output_path.exists())

        with self.output_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)

        self.assertIn("progression_config", payload)
        self.assertIn("default_user_state", payload)
        self.assertIn("dashboard_state", payload)
        self.assertIn("cases", payload)
        self.assertEqual(len(payload["cases"]), 55)


if __name__ == "__main__":
    unittest.main()
