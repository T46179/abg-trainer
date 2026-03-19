"""Tests for the ABG case generator entry point and output shape."""

import json
import math
import os
import re
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
from generator.config import DIFFICULTY_UNLOCK_LEVELS, STEM_BANK, XP_REQUIRED_PER_LEVEL
from generator.generators.common import build_case, build_inputs, diagnosis_labels_conflict, normalize_diagnosis_option
from generator.physiology import winters_expected_paco2
from generator.progression import get_level_progress, level_from_total_xp, unlocked_difficulty_for_level, xp_to_reach_level
from generator.stems import generate_stem


class GenerateCasesTests(unittest.TestCase):
    @staticmethod
    def _get_case_lactate(case):
        inputs = case["inputs"]
        other = inputs.get("other", {})
        return other.get("lactate_mmolL", inputs.get("lactate_mmolL"))

    def test_build_inputs_supports_wide_sparse_schema(self):
        inputs = build_inputs(
            7.11,
            28.4,
            9.6,
            138,
            101,
            lactate=3.2,
            pao2=78.4,
            base_excess=-14.2,
            k=5.6,
            glucose=24.9,
        )

        self.assertEqual(inputs["gas"]["ph"], 7.11)
        self.assertEqual(inputs["gas"]["paco2_mmHg"], 28.4)
        self.assertEqual(inputs["gas"]["hco3_mmolL"], 9.6)
        self.assertEqual(inputs["gas"]["pao2_mmHg"], 78.4)
        self.assertEqual(inputs["gas"]["base_excess_mEqL"], -14.2)
        self.assertEqual(inputs["electrolytes"]["na_mmolL"], 138)
        self.assertEqual(inputs["electrolytes"]["cl_mmolL"], 101)
        self.assertEqual(inputs["electrolytes"]["k_mmolL"], 5.6)
        self.assertEqual(inputs["electrolytes"]["glucose_mmolL"], 24.9)
        self.assertEqual(inputs["other"]["lactate_mmolL"], 3.2)
        self.assertEqual(inputs["lactate_mmolL"], 3.2)
        self.assertNotIn("spo2_percent", inputs["gas"])
        self.assertNotIn("hb_gL", inputs.get("other", {}))

    def test_build_case_injects_normal_glucose_for_master_cases_without_glucose(self):
        case = build_case(
            case_id="MASTER_GLUCOSE_001",
            title="Master default glucose check",
            category="mixed_disorder",
            clinical_stem="Test stem.",
            inputs=build_inputs(7.31, 24, 12, 140, 100),
            questions_flow=[],
            answer_key={
                "ph_status": "Acidaemia",
                "primary_disorder": "Metabolic acidosis",
                "compensation": "Inappropriate",
                "anion_gap_value": 28,
                "anion_gap_category": "Raised",
                "final_diagnosis": "Test diagnosis",
            },
            level=4,
            archetype="test_master_glucose",
        )

        glucose = case["inputs"]["electrolytes"].get("glucose_mmolL")
        self.assertIsNotNone(glucose)
        self.assertGreaterEqual(glucose, 4.2)
        self.assertLessEqual(glucose, 5.8)

    def test_progression_extends_to_level_25_without_new_difficulty_tiers(self):
        self.assertEqual(
            {level: XP_REQUIRED_PER_LEVEL[level] for level in range(20, 25)},
            {
                20: 600,
                21: 640,
                22: 680,
                23: 720,
                24: 760,
            },
        )
        self.assertEqual(DIFFICULTY_UNLOCK_LEVELS[4], 20)
        self.assertEqual(unlocked_difficulty_for_level(20), 4)
        self.assertEqual(unlocked_difficulty_for_level(25), 4)

    def test_level_25_is_current_effective_cap(self):
        level_25_threshold = xp_to_reach_level(25)

        self.assertEqual(level_from_total_xp(level_25_threshold), 25)
        self.assertEqual(level_from_total_xp(level_25_threshold + 5000), 25)

        progress = get_level_progress(level_25_threshold + 5000)
        self.assertEqual(progress["level"], 25)
        self.assertIsNone(progress["xp_needed_for_next_level"])
        self.assertIsNone(progress["next_level_total_xp"])

    def test_generate_all_cases_preserves_expected_archetype_counts(self):
        cases = generate_cases.generate_all_cases()
        counts = Counter(case["archetype"] for case in cases)

        expected = {
            "dka": 8,
            "alcoholic_ketoacidosis": 8,
            "starvation_ketosis": 8,
            "toxic_alcohol": 8,
            "simple_nagma": 8,
            "simple_metabolic_alkalosis": 8,
            "opioid_toxicity": 8,
            "copd_chronic_retainer": 8,
            "vomiting_metabolic_alkalosis": 8,
            "diuretic_metabolic_alkalosis": 8,
            "panic_hyperventilation": 8,
            "simple_respiratory_alkalosis": 8,
            "diarrhoea_nagma": 8,
            "uraemia": 8,
            "salicylate_toxicity": 8,
            "mixed_hagma_metabolic_alkalosis": 8,
            "lactic_acidosis": 8,
            "simple_respiratory_acidosis": 8,
            "acute_copd_exacerbation": 8,
            "sepsis_respiratory_alkalosis": 8,
            "dka_vomiting": 8,
        }

        self.assertEqual(len(cases), 168)
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

    def test_generated_master_cases_include_glucose(self):
        cases = [
            case for case in generate_cases.generate_all_cases()
            if case["difficulty_level"] == 4
        ]

        self.assertTrue(cases)
        for case in cases:
            glucose = case["inputs"]["electrolytes"].get("glucose_mmolL")
            self.assertIsNotNone(glucose, msg=f"{case['case_id']}: master cases should include glucose")

    def test_generated_stems_use_age_gender_shorthand(self):
        for archetype in STEM_BANK:
            stem = generate_stem(archetype)
            self.assertRegex(
                stem,
                r"\b\d+[MF]\b",
                msg=f"{archetype}: stem should include ED-style age/gender shorthand",
            )
            self.assertNotIn("year-old", stem, msg=f"{archetype}: stem should not use long-form age wording")

    def test_all_generated_case_stems_use_age_gender_shorthand(self):
        cases = generate_cases.generate_all_cases()

        for case in cases:
            stem = case["clinical_stem"]
            self.assertRegex(
                stem,
                r"\b\d+[MF]\b",
                msg=f"{case['case_id']}: case stem should include ED-style age/gender shorthand",
            )
            self.assertNotIn(
                "year-old",
                stem,
                msg=f"{case['case_id']}: case stem should not retain long-form age wording",
            )

    def test_generated_cases_include_patient_gender_matching_stem(self):
        cases = generate_cases.generate_all_cases()

        for case in cases:
            stem = case["clinical_stem"]
            gender_match = re.search(r"\b\d+(?P<gender>[MF])\b", stem)

            self.assertIsNotNone(gender_match, msg=f"{case['case_id']}: stem should contain age/gender shorthand")
            self.assertIn(case.get("patient_gender"), {"M", "F"}, msg=f"{case['case_id']}: patient_gender should be present")
            self.assertEqual(
                case.get("patient_gender"),
                gender_match.group("gender"),
                msg=f"{case['case_id']}: patient_gender should match stem shorthand",
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

    def test_alcoholic_ketoacidosis_cases_match_expected_pattern(self):
        cases = [
            case for case in generate_cases.generate_all_cases()
            if case["archetype"] == "alcoholic_ketoacidosis"
        ]

        self.assertEqual(len(cases), 8)

        for case in cases:
            gas = case["inputs"]["gas"]
            electrolytes = case["inputs"]["electrolytes"]
            answer_key = case["answer_key"]
            ag = electrolytes["na_mmolL"] - (electrolytes["cl_mmolL"] + gas["hco3_mmolL"])
            expected_paco2 = winters_expected_paco2(gas["hco3_mmolL"])

            self.assertEqual(answer_key["final_diagnosis"], "Alcoholic ketoacidosis")
            self.assertEqual(answer_key["primary_disorder"], "Metabolic acidosis")
            self.assertEqual(answer_key["anion_gap_category"], "Raised")
            self.assertGreater(ag, 16, msg=case["case_id"])
            self.assertAlmostEqual(
                gas["paco2_mmHg"],
                expected_paco2,
                delta=2.0,
                msg=f"{case['case_id']}: PaCO2 should follow Winter compensation",
            )

            lactate = self._get_case_lactate(case)
            if lactate is not None:
                self.assertLessEqual(
                    lactate,
                    4.0,
                    msg=f"{case['case_id']}: lactate should stay mild if present",
                )

    def test_toxic_alcohol_cases_match_expected_pattern(self):
        cases = [
            case for case in generate_cases.generate_all_cases()
            if case["archetype"] == "toxic_alcohol"
        ]

        self.assertEqual(len(cases), 8)

        for case in cases:
            gas = case["inputs"]["gas"]
            electrolytes = case["inputs"]["electrolytes"]
            answer_key = case["answer_key"]
            ag = electrolytes["na_mmolL"] - (electrolytes["cl_mmolL"] + gas["hco3_mmolL"])
            expected_paco2 = winters_expected_paco2(gas["hco3_mmolL"])

            self.assertEqual(answer_key["final_diagnosis"], "Toxic alcohol")
            self.assertEqual(answer_key["primary_disorder"], "Metabolic acidosis")
            self.assertEqual(answer_key["anion_gap_category"], "Raised")
            self.assertGreater(ag, 16, msg=case["case_id"])
            self.assertAlmostEqual(
                gas["paco2_mmHg"],
                expected_paco2,
                delta=2.0,
                msg=f"{case['case_id']}: PaCO2 should follow Winter compensation",
            )

            lactate = self._get_case_lactate(case)
            if lactate is not None:
                self.assertLessEqual(
                    lactate,
                    3.5,
                    msg=f"{case['case_id']}: lactate should stay absent or mild if present",
                )

    def test_starvation_ketosis_cases_match_expected_pattern(self):
        cases = [
            case for case in generate_cases.generate_all_cases()
            if case["archetype"] == "starvation_ketosis"
        ]

        self.assertEqual(len(cases), 8)

        for case in cases:
            gas = case["inputs"]["gas"]
            electrolytes = case["inputs"]["electrolytes"]
            answer_key = case["answer_key"]
            ag = electrolytes["na_mmolL"] - (electrolytes["cl_mmolL"] + gas["hco3_mmolL"])
            expected_paco2 = winters_expected_paco2(gas["hco3_mmolL"])
            glucose = electrolytes.get("glucose_mmolL")

            self.assertEqual(answer_key["final_diagnosis"], "Starvation ketosis")
            self.assertEqual(answer_key["primary_disorder"], "Metabolic acidosis")
            self.assertEqual(answer_key["anion_gap_category"], "Raised")
            self.assertGreater(ag, 16, msg=case["case_id"])
            self.assertLessEqual(gas["hco3_mmolL"], 20, msg=f"{case['case_id']}: starvation ketosis should not have HCO3 above 20")
            self.assertIsNotNone(glucose, msg=f"{case['case_id']}: starvation ketosis should include glucose")
            self.assertGreaterEqual(glucose, 3.2, msg=case["case_id"])
            self.assertLessEqual(glucose, 6.2, msg=case["case_id"])
            if gas["ph"] >= 7.34:
                self.assertLessEqual(
                    gas["hco3_mmolL"],
                    19,
                    msg=f"{case['case_id']}: near-normal pH starvation ketosis should still have clearly reduced HCO3",
                )
            self.assertAlmostEqual(
                gas["paco2_mmHg"],
                expected_paco2,
                delta=2.0,
                msg=f"{case['case_id']}: PaCO2 should follow Winter compensation",
            )

            lactate = self._get_case_lactate(case)
            if lactate is not None:
                self.assertLessEqual(
                    lactate,
                    2.2,
                    msg=f"{case['case_id']}: lactate should stay absent or only mildly elevated if present",
                )

    def test_simple_nagma_cases_match_expected_pattern(self):
        cases = [
            case for case in generate_cases.generate_all_cases()
            if case["archetype"] == "simple_nagma"
        ]

        self.assertEqual(len(cases), 8)

        for case in cases:
            gas = case["inputs"]["gas"]
            electrolytes = case["inputs"]["electrolytes"]
            answer_key = case["answer_key"]
            ag = electrolytes["na_mmolL"] - (electrolytes["cl_mmolL"] + gas["hco3_mmolL"])
            expected_paco2 = winters_expected_paco2(gas["hco3_mmolL"])

            self.assertEqual(answer_key["final_diagnosis"], "GI bicarbonate loss")
            self.assertEqual(answer_key["primary_disorder"], "Metabolic acidosis")
            self.assertEqual(answer_key["anion_gap_category"], "Normal")
            self.assertLessEqual(ag, 16, msg=case["case_id"])
            self.assertLess(gas["ph"], 7.35, msg=f"{case['case_id']}: beginner simple NAGMA should stay acidaemic")
            self.assertLess(gas["hco3_mmolL"], 22, msg=f"{case['case_id']}: simple NAGMA should have low bicarbonate")
            self.assertGreaterEqual(
                electrolytes["cl_mmolL"],
                104,
                msg=f"{case['case_id']}: simple NAGMA should be relatively hyperchloraemic",
            )
            self.assertAlmostEqual(
                gas["paco2_mmHg"],
                expected_paco2,
                delta=2.0,
                msg=f"{case['case_id']}: PaCO2 should follow Winter compensation",
            )

    def test_simple_metabolic_alkalosis_cases_match_expected_pattern(self):
        cases = [
            case for case in generate_cases.generate_all_cases()
            if case["archetype"] == "simple_metabolic_alkalosis"
        ]

        self.assertEqual(len(cases), 8)

        for case in cases:
            gas = case["inputs"]["gas"]
            electrolytes = case["inputs"]["electrolytes"]
            answer_key = case["answer_key"]
            ag = electrolytes["na_mmolL"] - (electrolytes["cl_mmolL"] + gas["hco3_mmolL"])
            expected_paco2 = 0.7 * (gas["hco3_mmolL"] - 24) + 40

            self.assertEqual(answer_key["final_diagnosis"], "Gastric losses")
            self.assertEqual(answer_key["primary_disorder"], "Metabolic alkalosis")
            self.assertGreater(gas["ph"], 7.45, msg=f"{case['case_id']}: beginner simple metabolic alkalosis should stay alkalemic")
            self.assertGreater(gas["hco3_mmolL"], 26, msg=f"{case['case_id']}: simple metabolic alkalosis should have elevated bicarbonate")
            self.assertLessEqual(ag, 16, msg=case["case_id"])
            self.assertLessEqual(
                electrolytes["cl_mmolL"],
                103,
                msg=f"{case['case_id']}: simple metabolic alkalosis should be relatively hypochloraemic",
            )
            self.assertAlmostEqual(
                gas["paco2_mmHg"],
                expected_paco2,
                delta=3.0,
                msg=f"{case['case_id']}: PaCO2 should follow metabolic alkalosis compensation",
            )

    def test_mixed_hagma_metabolic_alkalosis_cases_match_expected_pattern(self):
        cases = [
            case for case in generate_cases.generate_all_cases()
            if case["archetype"] == "mixed_hagma_metabolic_alkalosis"
        ]

        self.assertEqual(len(cases), 8)

        for case in cases:
            gas = case["inputs"]["gas"]
            electrolytes = case["inputs"]["electrolytes"]
            answer_key = case["answer_key"]
            ag = electrolytes["na_mmolL"] - (electrolytes["cl_mmolL"] + gas["hco3_mmolL"])
            expected_paco2 = winters_expected_paco2(gas["hco3_mmolL"])
            delta_ag = ag - 12
            delta_hco3 = 24 - gas["hco3_mmolL"]

            self.assertEqual(answer_key["primary_disorder"], "Metabolic acidosis")
            self.assertEqual(answer_key["anion_gap_category"], "Raised")
            self.assertEqual(answer_key["additional_metabolic_process"], "Metabolic alkalosis")
            self.assertEqual(
                answer_key["final_diagnosis"],
                "Mixed high anion gap metabolic acidosis and metabolic alkalosis",
            )
            self.assertGreater(ag, 16, msg=case["case_id"])
            self.assertGreaterEqual(gas["ph"], 7.30, msg=case["case_id"])
            self.assertLessEqual(gas["ph"], 7.42, msg=case["case_id"])
            self.assertGreaterEqual(gas["hco3_mmolL"], 17, msg=case["case_id"])
            self.assertLessEqual(gas["hco3_mmolL"], 24, msg=case["case_id"])
            self.assertLessEqual(electrolytes["cl_mmolL"], 96, msg=case["case_id"])
            self.assertGreaterEqual(delta_ag - delta_hco3, 3, msg=case["case_id"])
            self.assertAlmostEqual(
                gas["paco2_mmHg"],
                expected_paco2,
                delta=2.0,
                msg=f"{case['case_id']}: PaCO2 should follow Winter compensation",
            )

            diagnosis_options = next(
                question["options"]
                for question in case["questions_flow"]
                if question.get("key") == "final_diagnosis"
            )
            self.assertIn("High anion gap metabolic acidosis", diagnosis_options, msg=case["case_id"])

            lactate = self._get_case_lactate(case)
            if lactate is not None:
                self.assertGreaterEqual(lactate, 1.0, msg=case["case_id"])
                self.assertLessEqual(lactate, 5.0, msg=case["case_id"])

    def test_final_diagnosis_options_are_unique_and_non_overlapping(self):
        cases = generate_cases.generate_all_cases()

        for case in cases:
            final_diagnosis = case["answer_key"]["final_diagnosis"]
            diagnosis_steps = [
                question for question in case["questions_flow"]
                if question.get("key") == "final_diagnosis"
            ]

            for question in diagnosis_steps:
                options = question["options"]

                self.assertIn(
                    final_diagnosis,
                    options,
                    msg=f"{case['case_id']}: final diagnosis missing from options",
                )

                normalized_options = [normalize_diagnosis_option(option) for option in options]
                self.assertEqual(
                    len(normalized_options),
                    len(set(normalized_options)),
                    msg=f"{case['case_id']}: duplicate normalized diagnosis options {options}",
                )

                for index, option in enumerate(options):
                    for other_option in options[index + 1:]:
                        self.assertFalse(
                            diagnosis_labels_conflict(option, other_option),
                            msg=(
                                f"{case['case_id']}: overlapping final diagnosis options "
                                f"{option!r} and {other_option!r}"
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
            self.assertEqual(len(payload["cases"]), 168)

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
