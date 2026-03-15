"""Tests for the ABG case generator entry point and output shape."""

import json
import math
import os
import subprocess
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from unittest import mock


GENERATOR_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = GENERATOR_DIR.parent

from generator import generate_cases


class GenerateCasesTests(unittest.TestCase):
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

    def test_generate_all_cases_uses_unique_case_ids(self):
        cases = generate_cases.generate_all_cases()
        counts = Counter(case["case_id"] for case in cases)
        duplicates = sorted(case_id for case_id, count in counts.items() if count > 1)

        self.assertFalse(
            duplicates,
            msg=(
                "Duplicate case_id values found: "
                + ", ".join(f"{case_id} (x{counts[case_id]})" for case_id in duplicates)
            ),
        )

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

    def test_generated_cases_have_expected_question_flow_structure(self):
        cases = generate_cases.generate_all_cases()
        required_steps_by_level = {
            1: ["ph_status", "primary_disorder"],
            2: ["ph_status", "primary_disorder", "compensation"],
            3: ["ph_status", "primary_disorder", "compensation", "anion_gap"],
            4: ["ph_status", "primary_disorder", "compensation", "anion_gap"],
        }
        allowed_flows_by_level = {
            1: [
                ["ph_status", "primary_disorder"],
                ["ph_status", "primary_disorder", "final_diagnosis"],
            ],
            2: [
                ["ph_status", "primary_disorder", "compensation"],
                ["ph_status", "primary_disorder", "compensation", "final_diagnosis"],
            ],
            3: [
                ["ph_status", "primary_disorder", "compensation", "anion_gap"],
                ["ph_status", "primary_disorder", "compensation", "anion_gap", "final_diagnosis"],
            ],
            4: [
                ["ph_status", "primary_disorder", "compensation", "anion_gap"],
                ["ph_status", "primary_disorder", "compensation", "anion_gap", "final_diagnosis"],
                ["ph_status", "primary_disorder", "compensation", "anion_gap", "additional_metabolic_process"],
                ["ph_status", "primary_disorder", "compensation", "anion_gap", "additional_metabolic_process", "final_diagnosis"],
            ],
        }
        required_question_fields = {
            "ph_status": {"step", "key", "label", "prompt", "options"},
            "primary_disorder": {"step", "key", "label", "prompt", "options"},
            "compensation": {"step", "key", "label", "prompt", "options"},
            "anion_gap": {"step", "key", "label", "prompt", "options"},
            "additional_metabolic_process": {"step", "key", "label", "prompt", "options"},
            "final_diagnosis": {"step", "key", "prompt", "options"},
        }

        for case in cases:
            case_id = case["case_id"]
            difficulty = case["difficulty_level"]
            questions_flow = case["questions_flow"]
            flow_keys = [question.get("key") for question in questions_flow]
            missing_steps = [
                step for step in required_steps_by_level[difficulty] if step not in flow_keys
            ]

            self.assertFalse(
                missing_steps,
                msg=(
                    f"{case_id}: missing expected question steps for difficulty {difficulty}: "
                    + ", ".join(missing_steps)
                ),
            )
            self.assertIn(
                flow_keys,
                allowed_flows_by_level[difficulty],
                msg=(
                    f"{case_id}: questions_flow keys {flow_keys} do not match expected flows "
                    f"for difficulty {difficulty}: {allowed_flows_by_level[difficulty]}"
                ),
            )

            for question in questions_flow:
                question_key = question.get("key")
                missing_fields = sorted(required_question_fields[question_key] - question.keys())
                self.assertFalse(
                    missing_fields,
                    msg=(
                        f"{case_id}: question '{question_key}' missing required keys: "
                        + ", ".join(missing_fields)
                    ),
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
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "abg_cases.json"

            with mock.patch.dict(os.environ, {"ABG_CASES_OUTPUT_PATH": str(output_path)}):
                generate_cases.main()

            self.assertTrue(output_path.exists())

            with output_path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)

            self.assertIn("progression_config", payload)
            self.assertIn("default_user_state", payload)
            self.assertIn("dashboard_state", payload)
            self.assertIn("cases", payload)
            self.assertEqual(len(payload["cases"]), 55)

    def test_module_runs_via_package_execution(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "abg_cases.json"
            env = os.environ.copy()
            env["ABG_CASES_OUTPUT_PATH"] = str(output_path)

            result = subprocess.run(
                [sys.executable, "-m", "generator.generate_cases"],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                env=env,
            )

            self.assertEqual(
                result.returncode,
                0,
                msg=(
                    "python -m generator.generate_cases failed\n"
                    f"stdout:\n{result.stdout}\n"
                    f"stderr:\n{result.stderr}"
                ),
            )
            self.assertTrue(output_path.exists())


if __name__ == "__main__":
    unittest.main()
