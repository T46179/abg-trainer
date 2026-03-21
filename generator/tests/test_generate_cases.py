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
from copy import deepcopy
from pathlib import Path
from unittest import mock


GENERATOR_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = GENERATOR_DIR.parent

from generator import generate_cases
from generator.config import DIFFICULTY_UNLOCK_LEVELS, STEM_BANK, XP_REQUIRED_PER_LEVEL
from generator.generators.common import build_case, build_inputs, diagnosis_labels_conflict, normalize_diagnosis_option
from generator.physiology import (
    acute_respiratory_acidosis_expected_hco3,
    calc_anion_gap,
    chronic_respiratory_acidosis_expected_hco3,
    estimate_ph,
    hagma_bicarbonate_preservation,
    isolated_hagma_expected_hco3,
    respiratory_alkalosis_expected_hco3_acute,
    winters_expected_paco2,
)
from generator.progression import get_level_progress, level_from_total_xp, unlocked_difficulty_for_level, xp_to_reach_level
from generator.stems import generate_stem
from generator.validation import (
    ARCHETYPE_VALIDATION_CONTRACTS,
    validate_archetype_contract_coverage,
    validate_case,
    validate_cases,
)


class GenerateCasesTests(unittest.TestCase):
    STEP_ANSWER_FIELDS = {
        "ph_status": "ph_status",
        "primary_disorder": "primary_disorder",
        "compensation": "compensation",
        "anion_gap": "anion_gap_category",
        "additional_metabolic_process": "additional_metabolic_process",
        "final_diagnosis": "final_diagnosis",
    }

    @staticmethod
    def _get_case_lactate(case):
        inputs = case["inputs"]
        other = inputs.get("other", {})
        return other.get("lactate_mmolL", inputs.get("lactate_mmolL"))

    @staticmethod
    def _find_question(case, key):
        return next(question for question in case["questions_flow"] if question.get("key") == key)

    @classmethod
    def _answer_for_step(cls, case, key):
        return case["answer_key"][cls.STEP_ANSWER_FIELDS[key]]

    @staticmethod
    def _get_generated_case(archetype):
        return next(
            case for case in generate_cases.generate_all_cases()
            if case["archetype"] == archetype
        )

    @staticmethod
    def _rewrite_displayed_values(case, *, paco2=None, hco3=None, na=None, cl=None):
        gas = case["inputs"]["gas"]
        electrolytes = case["inputs"]["electrolytes"]

        if paco2 is not None:
            gas["paco2_mmHg"] = round(paco2, 1)
        if hco3 is not None:
            gas["hco3_mmolL"] = round(hco3, 1)
        if na is not None:
            electrolytes["na_mmolL"] = na
        if cl is not None:
            electrolytes["cl_mmolL"] = cl

        gas["ph"] = estimate_ph(gas["hco3_mmolL"], gas["paco2_mmHg"])
        ag = calc_anion_gap(
            electrolytes["na_mmolL"],
            electrolytes["cl_mmolL"],
            gas["hco3_mmolL"],
        )
        case["answer_key"]["anion_gap_value"] = ag
        case["answer_key"]["anion_gap_category"] = "Raised" if ag > 16 else "Normal"
        return ag

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
            "respiratory_alkalosis_hagma": 8,
            "respiratory_acidosis_hagma": 8,
            "lactic_acidosis": 8,
            "simple_respiratory_acidosis": 8,
            "acute_copd_exacerbation": 8,
            "sepsis_respiratory_alkalosis": 8,
            "dka_vomiting": 8,
        }

        self.assertEqual(len(cases), 184)
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

    def test_cases_with_compensation_question_use_supported_binary_answers(self):
        cases = generate_cases.generate_all_cases()

        for case in cases:
            has_compensation_step = any(
                question.get("key") == "compensation"
                for question in case["questions_flow"]
            )
            if not has_compensation_step:
                continue

            self.assertIn(
                case["answer_key"]["compensation"],
                {"Appropriate", "Inappropriate"},
                msg=f"{case['case_id']}: compensation answer must stay within the binary UI options",
            )

    def test_generated_archetypes_have_explicit_validation_contracts(self):
        cases = generate_cases.generate_all_cases()
        coverage_errors = validate_archetype_contract_coverage(cases)
        generated_archetypes = {case["archetype"] for case in cases}

        self.assertFalse(coverage_errors, msg="\n".join(coverage_errors))
        self.assertSetEqual(generated_archetypes, set(ARCHETYPE_VALIDATION_CONTRACTS))

    def test_generated_cases_pass_full_validation(self):
        cases = generate_cases.generate_all_cases()
        errors = validate_cases(cases)

        self.assertFalse(errors, msg="\n".join(errors))

    def test_validation_rejects_case_without_explicit_archetype_contract(self):
        case = deepcopy(self._get_generated_case("dka"))
        case["case_id"] = "BROKEN_CONTRACT_001"
        case["archetype"] = "future_unvalidated_archetype"

        errors = validate_case(case)

        self.assertTrue(
            any("no explicit validation contract" in error for error in errors),
            msg=errors,
        )

    def test_validation_rejects_correct_answers_missing_from_options_for_each_scored_step(self):
        base_case = self._get_generated_case("dka_vomiting")

        for question_key in self.STEP_ANSWER_FIELDS:
            with self.subTest(question_key=question_key):
                case = deepcopy(base_case)
                question = self._find_question(case, question_key)
                correct_answer = self._answer_for_step(case, question_key)
                question["options"] = [option for option in question["options"] if option != correct_answer]

                errors = validate_case(case)

                self.assertTrue(
                    any(
                        f"question step '{question_key}' options missing correct answer '{correct_answer}'" in error
                        for error in errors
                    ),
                    msg=errors,
                )

    def test_validation_rejects_dka_vomiting_without_numeric_proof_of_metabolic_alkalosis(self):
        case = deepcopy(self._get_generated_case("dka_vomiting"))
        electrolytes = case["inputs"]["electrolytes"]
        gas = case["inputs"]["gas"]
        ag = calc_anion_gap(electrolytes["na_mmolL"], electrolytes["cl_mmolL"], gas["hco3_mmolL"])
        isolated_hco3 = isolated_hagma_expected_hco3(ag)
        replacement_cl = int(round(electrolytes["na_mmolL"] - (isolated_hco3 + ag)))
        winter_paco2 = round(winters_expected_paco2(isolated_hco3), 1)

        self._rewrite_displayed_values(
            case,
            paco2=winter_paco2,
            hco3=isolated_hco3,
            cl=replacement_cl,
        )

        errors = validate_case(case)

        self.assertTrue(
            any("does not preserve enough delta-gap signal" in error for error in errors),
            msg=errors,
        )

    def test_validation_rejects_respiratory_alkalosis_hagma_without_hco3_mismatch(self):
        case = deepcopy(self._get_generated_case("respiratory_alkalosis_hagma"))
        electrolytes = case["inputs"]["electrolytes"]
        gas = case["inputs"]["gas"]
        ag = calc_anion_gap(electrolytes["na_mmolL"], electrolytes["cl_mmolL"], gas["hco3_mmolL"])
        expected_hco3 = round(respiratory_alkalosis_expected_hco3_acute(gas["paco2_mmHg"]), 1)
        replacement_cl = int(round(electrolytes["na_mmolL"] - (expected_hco3 + ag)))

        self._rewrite_displayed_values(
            case,
            hco3=expected_hco3,
            cl=replacement_cl,
        )
        rewritten_ph = case["inputs"]["gas"]["ph"]
        case["answer_key"]["ph_status"] = (
            "Acidaemia" if rewritten_ph < 7.35 else "Alkalaemia" if rewritten_ph > 7.45 else "Normal"
        )

        errors = validate_case(case)

        self.assertTrue(
            any("should fall below the expected respiratory compensation range" in error for error in errors),
            msg=errors,
        )

    def test_validation_rejects_salicylate_if_reverted_to_single_process_schema(self):
        case = deepcopy(self._get_generated_case("salicylate_toxicity"))
        case["questions_flow"] = [
            question for question in case["questions_flow"]
            if question.get("key") != "additional_metabolic_process"
        ]
        case["answer_key"]["primary_disorder"] = "Metabolic acidosis"
        case["answer_key"].pop("additional_metabolic_process", None)

        errors = validate_case(case)

        self.assertTrue(
            any("should use the mixed question flow with an additional metabolic process step" in error for error in errors),
            msg=errors,
        )
        self.assertTrue(
            any("should be respiratory alkalosis" in error for error in errors),
            msg=errors,
        )
        self.assertTrue(
            any("should identify a concurrent high anion gap metabolic acidosis" in error for error in errors),
            msg=errors,
        )

    def test_validation_rejects_salicylate_without_hco3_mismatch(self):
        case = deepcopy(self._get_generated_case("salicylate_toxicity"))
        electrolytes = case["inputs"]["electrolytes"]
        gas = case["inputs"]["gas"]
        ag = calc_anion_gap(electrolytes["na_mmolL"], electrolytes["cl_mmolL"], gas["hco3_mmolL"])
        expected_hco3 = round(respiratory_alkalosis_expected_hco3_acute(gas["paco2_mmHg"]), 1)
        replacement_cl = int(round(electrolytes["na_mmolL"] - (expected_hco3 + ag)))

        self._rewrite_displayed_values(
            case,
            hco3=expected_hco3,
            cl=replacement_cl,
        )

        errors = validate_case(case)

        self.assertTrue(
            any("should fall below the expected respiratory compensation range" in error for error in errors),
            msg=errors,
        )

    def test_validation_rejects_salicylate_with_dka_like_glucose(self):
        case = deepcopy(self._get_generated_case("salicylate_toxicity"))
        case["inputs"]["electrolytes"]["glucose_mmolL"] = 20.0

        errors = validate_case(case)

        self.assertTrue(
            any("stay well below DKA-range hyperglycaemia" in error for error in errors),
            msg=errors,
        )

    def test_validation_rejects_salicylate_with_lactate_dominant_gap(self):
        case = deepcopy(self._get_generated_case("salicylate_toxicity"))
        case["inputs"].setdefault("other", {})["lactate_mmolL"] = 5.5
        case["inputs"]["lactate_mmolL"] = 5.5

        errors = validate_case(case)

        self.assertTrue(
            any("salicylate remains the main explanation for the HAGMA" in error for error in errors),
            msg=errors,
        )

    def test_validation_rejects_dka_family_without_supportive_glucose(self):
        for archetype in ("dka", "dka_vomiting"):
            with self.subTest(archetype=archetype):
                case = deepcopy(self._get_generated_case(archetype))
                case["inputs"]["electrolytes"]["glucose_mmolL"] = 6.0

                errors = validate_case(case)

                self.assertTrue(
                    any("glucose should support the diagnosis" in error for error in errors),
                    msg=errors,
                )

    def test_validation_rejects_alcoholic_ketoacidosis_with_dka_like_glucose(self):
        case = deepcopy(self._get_generated_case("alcoholic_ketoacidosis"))
        case["inputs"]["electrolytes"]["glucose_mmolL"] = 18.0

        errors = validate_case(case)

        self.assertTrue(
            any("stay below classic DKA-range hyperglycaemia" in error for error in errors),
            msg=errors,
        )

    def test_validation_rejects_lactic_acidosis_without_supportive_lactate(self):
        case = deepcopy(self._get_generated_case("lactic_acidosis"))
        case["inputs"]["other"]["lactate_mmolL"] = 1.8
        case["inputs"]["lactate_mmolL"] = 1.8

        errors = validate_case(case)

        self.assertTrue(
            any("lactate should materially support the diagnosis" in error for error in errors),
            msg=errors,
        )

    def test_validation_rejects_toxic_alcohol_if_lactate_becomes_main_hagma_explanation(self):
        case = deepcopy(self._get_generated_case("toxic_alcohol"))
        electrolytes = case["inputs"]["electrolytes"]
        gas = case["inputs"]["gas"]
        ag = calc_anion_gap(electrolytes["na_mmolL"], electrolytes["cl_mmolL"], gas["hco3_mmolL"])
        dominant_lactate = round((ag - 12) + 1.0, 1)
        case["inputs"].setdefault("other", {})["lactate_mmolL"] = dominant_lactate
        case["inputs"]["lactate_mmolL"] = dominant_lactate

        errors = validate_case(case)

        self.assertTrue(
            any("should not be the main explanation for the HAGMA" in error for error in errors),
            msg=errors,
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
            self.assertIn("glucose_mmolL", electrolytes, msg=case["case_id"])
            self.assertLess(
                electrolytes["glucose_mmolL"],
                14.0,
                msg=f"{case['case_id']}: alcoholic ketoacidosis should not look like classic DKA",
            )
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

    def test_dka_cases_match_expected_pattern(self):
        cases = [
            case for case in generate_cases.generate_all_cases()
            if case["archetype"] == "dka"
        ]

        self.assertEqual(len(cases), 8)

        for case in cases:
            gas = case["inputs"]["gas"]
            electrolytes = case["inputs"]["electrolytes"]
            answer_key = case["answer_key"]
            ag = electrolytes["na_mmolL"] - (electrolytes["cl_mmolL"] + gas["hco3_mmolL"])
            expected_paco2 = winters_expected_paco2(gas["hco3_mmolL"])

            self.assertEqual(answer_key["final_diagnosis"], "DKA")
            self.assertEqual(answer_key["primary_disorder"], "Metabolic acidosis")
            self.assertEqual(answer_key["anion_gap_category"], "Raised")
            self.assertIn("glucose_mmolL", electrolytes, msg=case["case_id"])
            self.assertGreaterEqual(
                electrolytes["glucose_mmolL"],
                14.0,
                msg=f"{case['case_id']}: DKA glucose should support the diagnosis",
            )
            self.assertGreater(ag, 16, msg=case["case_id"])
            self.assertAlmostEqual(
                gas["paco2_mmHg"],
                expected_paco2,
                delta=2.0,
                msg=f"{case['case_id']}: PaCO2 should follow Winter compensation",
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

    def test_diarrhoea_explanations_match_stored_ph_status(self):
        cases = [
            case for case in generate_cases.generate_all_cases()
            if case["archetype"] == "diarrhoea_nagma"
        ]

        self.assertEqual(len(cases), 8)

        for case in cases:
            explanation = case["explanation"]
            ph_status = case["answer_key"]["ph_status"]

            if ph_status == "Acidaemia":
                self.assertIn("Low pH indicates acidaemia.", explanation, msg=case["case_id"])
            elif ph_status == "Alkalaemia":
                self.assertIn("High pH indicates alkalaemia.", explanation, msg=case["case_id"])
            else:
                self.assertIn("The pH is in the normal range", explanation, msg=case["case_id"])

    def test_lactic_acidosis_explanations_cover_key_reasoning_steps(self):
        cases = [
            case for case in generate_cases.generate_all_cases()
            if case["archetype"] == "lactic_acidosis"
        ]

        self.assertEqual(len(cases), 8)

        for case in cases:
            explanation = case["explanation"].lower()

            self.assertIn("pH is".lower(), explanation, msg=case["case_id"])
            self.assertIn("hco3", explanation, msg=case["case_id"])
            self.assertIn("metabolic acidosis", explanation, msg=case["case_id"])
            self.assertIn("winter", explanation, msg=case["case_id"])
            self.assertIn("appropriate", explanation, msg=case["case_id"])
            self.assertIn("anion gap", explanation, msg=case["case_id"])
            self.assertIn("lactate", explanation, msg=case["case_id"])
            self.assertIn("septic clinical context", explanation, msg=case["case_id"])
            self.assertIn("lactic acidosis", explanation, msg=case["case_id"])

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

    def test_dka_vomiting_cases_match_expected_mixed_metabolic_pattern(self):
        cases = [
            case for case in generate_cases.generate_all_cases()
            if case["archetype"] == "dka_vomiting"
        ]

        self.assertEqual(len(cases), 8)

        for case in cases:
            gas = case["inputs"]["gas"]
            electrolytes = case["inputs"]["electrolytes"]
            answer_key = case["answer_key"]
            ag = electrolytes["na_mmolL"] - (electrolytes["cl_mmolL"] + gas["hco3_mmolL"])
            expected_paco2 = winters_expected_paco2(gas["hco3_mmolL"])
            pure_hagma_hco3 = isolated_hagma_expected_hco3(ag)
            alkalosis_signal = hagma_bicarbonate_preservation(ag, gas["hco3_mmolL"])

            self.assertEqual(answer_key["primary_disorder"], "Metabolic acidosis")
            self.assertEqual(answer_key["compensation"], "Appropriate")
            self.assertEqual(answer_key["anion_gap_category"], "Raised")
            self.assertEqual(answer_key["additional_metabolic_process"], "Metabolic alkalosis")
            self.assertEqual(answer_key["final_diagnosis"], "DKA with vomiting")
            self.assertEqual(answer_key["expected_compensation"]["rule"], "Winter")
            self.assertIn("glucose_mmolL", electrolytes, msg=case["case_id"])
            self.assertGreaterEqual(
                electrolytes["glucose_mmolL"],
                14.0,
                msg=f"{case['case_id']}: glucose should support DKA rather than default normal master glucose",
            )
            self.assertGreater(ag, 16, msg=case["case_id"])
            self.assertLess(gas["hco3_mmolL"], 22, msg=case["case_id"])
            self.assertGreater(
                gas["hco3_mmolL"],
                pure_hagma_hco3,
                msg=f"{case['case_id']}: bicarbonate should be preserved above isolated HAGMA expectations",
            )
            self.assertGreaterEqual(
                alkalosis_signal,
                4.0,
                msg=f"{case['case_id']}: delta-gap logic should prove additional metabolic alkalosis",
            )
            self.assertAlmostEqual(
                gas["paco2_mmHg"],
                expected_paco2,
                delta=2.0,
                msg=f"{case['case_id']}: PaCO2 should sit near Winter compensation for the displayed bicarbonate",
            )

    def test_sepsis_cases_match_expected_acute_respiratory_alkalosis_pattern(self):
        cases = [
            case for case in generate_cases.generate_all_cases()
            if case["archetype"] == "sepsis_respiratory_alkalosis"
        ]

        self.assertEqual(len(cases), 8)

        for case in cases:
            gas = case["inputs"]["gas"]
            electrolytes = case["inputs"]["electrolytes"]
            answer_key = case["answer_key"]
            ag = electrolytes["na_mmolL"] - (electrolytes["cl_mmolL"] + gas["hco3_mmolL"])
            expected_hco3 = respiratory_alkalosis_expected_hco3_acute(gas["paco2_mmHg"])

            self.assertEqual(answer_key["final_diagnosis"], "Sepsis")
            self.assertEqual(answer_key["primary_disorder"], "Respiratory alkalosis")
            self.assertEqual(answer_key["compensation"], "Appropriate")
            self.assertEqual(answer_key["expected_compensation"]["rule"], "Acute respiratory alkalosis")
            self.assertLess(gas["paco2_mmHg"], 35, msg=case["case_id"])
            self.assertGreater(gas["ph"], 7.45, msg=case["case_id"])
            self.assertLessEqual(ag, 16, msg=case["case_id"])
            self.assertAlmostEqual(
                gas["hco3_mmolL"],
                expected_hco3,
                delta=2.0,
                msg=f"{case['case_id']}: HCO3 should fit acute respiratory alkalosis compensation",
            )

    def test_acute_copd_cases_match_binary_inappropriate_compensation_pattern(self):
        cases = [
            case for case in generate_cases.generate_all_cases()
            if case["archetype"] == "acute_copd_exacerbation"
        ]

        self.assertEqual(len(cases), 8)

        for case in cases:
            gas = case["inputs"]["gas"]
            electrolytes = case["inputs"]["electrolytes"]
            answer_key = case["answer_key"]
            ag = electrolytes["na_mmolL"] - (electrolytes["cl_mmolL"] + gas["hco3_mmolL"])
            expected_chronic_hco3 = chronic_respiratory_acidosis_expected_hco3(gas["paco2_mmHg"])
            expected_acute_hco3 = acute_respiratory_acidosis_expected_hco3(gas["paco2_mmHg"])

            self.assertEqual(answer_key["final_diagnosis"], "COPD exacerbation")
            self.assertEqual(answer_key["primary_disorder"], "Respiratory acidosis")
            self.assertEqual(answer_key["compensation"], "Inappropriate")
            self.assertEqual(answer_key["expected_compensation"]["rule"], "Chronic respiratory acidosis")
            self.assertGreater(gas["paco2_mmHg"], 65, msg=case["case_id"])
            self.assertLess(gas["ph"], 7.35, msg=case["case_id"])
            self.assertLessEqual(ag, 16, msg=case["case_id"])
            self.assertLess(
                gas["hco3_mmolL"],
                expected_chronic_hco3 - 2,
                msg=f"{case['case_id']}: HCO3 should sit below isolated chronic compensation",
            )
            self.assertGreater(
                gas["hco3_mmolL"],
                expected_acute_hco3 + 2,
                msg=f"{case['case_id']}: HCO3 should still reflect chronic background above acute-only compensation",
            )

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

    def test_respiratory_acidosis_hagma_cases_match_expected_pattern(self):
        cases = [
            case for case in generate_cases.generate_all_cases()
            if case["archetype"] == "respiratory_acidosis_hagma"
        ]

        self.assertEqual(len(cases), 8)
        acute_case_count = 0
        near_miss_case_count = 0

        for case in cases:
            gas = case["inputs"]["gas"]
            electrolytes = case["inputs"]["electrolytes"]
            answer_key = case["answer_key"]
            ag = electrolytes["na_mmolL"] - (electrolytes["cl_mmolL"] + gas["hco3_mmolL"])
            compensation_rule = answer_key["expected_compensation"]["rule"]

            if compensation_rule == "Acute respiratory acidosis":
                expected_hco3 = acute_respiratory_acidosis_expected_hco3(gas["paco2_mmHg"])
                acute_case_count += 1
            else:
                expected_hco3 = chronic_respiratory_acidosis_expected_hco3(gas["paco2_mmHg"])

            self.assertEqual(answer_key["primary_disorder"], "Respiratory acidosis")
            self.assertEqual(answer_key["compensation"], "Inappropriate")
            self.assertEqual(answer_key["anion_gap_category"], "Raised")
            self.assertEqual(answer_key["additional_metabolic_process"], "High anion gap metabolic acidosis")
            self.assertEqual(
                answer_key["final_diagnosis"],
                "Respiratory acidosis with concurrent high anion gap metabolic acidosis",
            )
            self.assertGreater(gas["paco2_mmHg"], 55, msg=case["case_id"])
            self.assertGreater(ag, 16, msg=case["case_id"])
            self.assertLess(gas["hco3_mmolL"], expected_hco3 - 2, msg=case["case_id"])
            self.assertGreaterEqual(gas["ph"], 7.10, msg=case["case_id"])
            self.assertLessEqual(gas["ph"], 7.40, msg=case["case_id"])

            gap_below_expected_midpoint = expected_hco3 - gas["hco3_mmolL"]
            if compensation_rule == "Chronic respiratory acidosis" and 2.2 <= gap_below_expected_midpoint <= 3.8:
                near_miss_case_count += 1

            additional_process_options = next(
                question["options"]
                for question in case["questions_flow"]
                if question.get("key") == "additional_metabolic_process"
            )
            self.assertIn("High anion gap metabolic acidosis", additional_process_options, msg=case["case_id"])

            diagnosis_options = next(
                question["options"]
                for question in case["questions_flow"]
                if question.get("key") == "final_diagnosis"
            )
            self.assertIn("Respiratory acidosis", diagnosis_options, msg=case["case_id"])
            self.assertIn("High anion gap metabolic acidosis", diagnosis_options, msg=case["case_id"])
            self.assertIn("COPD exacerbation", diagnosis_options, msg=case["case_id"])
            self.assertIn("Lactic acidosis", diagnosis_options, msg=case["case_id"])
            self.assertIn("Opioid toxicity", diagnosis_options, msg=case["case_id"])

            explanation = case.get("explanation", "").lower()
            if compensation_rule == "Acute respiratory acidosis":
                self.assertIn("acute respiratory acidosis", explanation, msg=case["case_id"])
            if 2.2 <= gap_below_expected_midpoint <= 3.8:
                self.assertIn("close to the expected compensatory value", explanation, msg=case["case_id"])

        self.assertGreaterEqual(acute_case_count, 1)
        self.assertGreaterEqual(near_miss_case_count, 1)

    def test_respiratory_alkalosis_hagma_cases_match_expected_pattern(self):
        cases = [
            case for case in generate_cases.generate_all_cases()
            if case["archetype"] == "respiratory_alkalosis_hagma"
        ]

        self.assertEqual(len(cases), 8)
        near_normal_case_count = 0
        subtle_mismatch_case_count = 0

        for case in cases:
            gas = case["inputs"]["gas"]
            electrolytes = case["inputs"]["electrolytes"]
            answer_key = case["answer_key"]
            ag = electrolytes["na_mmolL"] - (electrolytes["cl_mmolL"] + gas["hco3_mmolL"])
            expected_hco3 = respiratory_alkalosis_expected_hco3_acute(gas["paco2_mmHg"])
            gap_below_expected_midpoint = expected_hco3 - gas["hco3_mmolL"]

            self.assertEqual(answer_key["primary_disorder"], "Respiratory alkalosis")
            self.assertEqual(answer_key["compensation"], "Inappropriate")
            self.assertEqual(answer_key["anion_gap_category"], "Raised")
            self.assertEqual(answer_key["additional_metabolic_process"], "High anion gap metabolic acidosis")
            self.assertEqual(
                answer_key["final_diagnosis"],
                "Respiratory alkalosis with concurrent high anion gap metabolic acidosis",
            )
            self.assertEqual(answer_key["expected_compensation"]["rule"], "Acute respiratory alkalosis")
            self.assertLess(gas["paco2_mmHg"], 35, msg=case["case_id"])
            self.assertGreater(ag, 16, msg=case["case_id"])
            self.assertLess(gas["hco3_mmolL"], expected_hco3 - 2, msg=case["case_id"])
            self.assertGreaterEqual(gas["ph"], 7.22, msg=case["case_id"])
            self.assertLessEqual(gas["ph"], 7.44, msg=case["case_id"])

            if 7.35 <= gas["ph"] <= 7.44:
                near_normal_case_count += 1
            if 2.5 <= gap_below_expected_midpoint <= 4.2:
                subtle_mismatch_case_count += 1

            additional_process_options = next(
                question["options"]
                for question in case["questions_flow"]
                if question.get("key") == "additional_metabolic_process"
            )
            self.assertIn("High anion gap metabolic acidosis", additional_process_options, msg=case["case_id"])

            diagnosis_options = next(
                question["options"]
                for question in case["questions_flow"]
                if question.get("key") == "final_diagnosis"
            )
            self.assertIn("Respiratory alkalosis", diagnosis_options, msg=case["case_id"])
            self.assertIn("High anion gap metabolic acidosis", diagnosis_options, msg=case["case_id"])
            self.assertIn("Sepsis", diagnosis_options, msg=case["case_id"])
            self.assertIn("Salicylate toxicity", diagnosis_options, msg=case["case_id"])
            self.assertIn("Panic attack / hyperventilation", diagnosis_options, msg=case["case_id"])

            explanation = case.get("explanation", "").lower()
            self.assertIn("acute respiratory alkalosis", explanation, msg=case["case_id"])
            self.assertIn("does not fit expected compensation for a single respiratory process", explanation, msg=case["case_id"])
            if 2.5 <= gap_below_expected_midpoint <= 4.2:
                self.assertIn("closer to the expected compensatory value", explanation, msg=case["case_id"])

        self.assertGreaterEqual(near_normal_case_count, 1)
        self.assertGreaterEqual(subtle_mismatch_case_count, 1)

    def test_salicylate_cases_match_expected_mixed_pattern(self):
        cases = [
            case for case in generate_cases.generate_all_cases()
            if case["archetype"] == "salicylate_toxicity"
        ]

        self.assertEqual(len(cases), 8)
        alkalemic_case_count = 0
        near_normal_case_count = 0
        acidemic_case_count = 0

        for case in cases:
            gas = case["inputs"]["gas"]
            electrolytes = case["inputs"]["electrolytes"]
            answer_key = case["answer_key"]
            ag = electrolytes["na_mmolL"] - (electrolytes["cl_mmolL"] + gas["hco3_mmolL"])
            expected_hco3 = respiratory_alkalosis_expected_hco3_acute(gas["paco2_mmHg"])
            question_keys = [question.get("key") for question in case["questions_flow"]]
            lactate = self._get_case_lactate(case)

            self.assertEqual(
                question_keys,
                ["ph_status", "primary_disorder", "compensation", "anion_gap", "additional_metabolic_process", "final_diagnosis"],
            )
            self.assertEqual(answer_key["primary_disorder"], "Respiratory alkalosis")
            self.assertEqual(answer_key["compensation"], "Inappropriate")
            self.assertEqual(answer_key["anion_gap_category"], "Raised")
            self.assertEqual(answer_key["additional_metabolic_process"], "High anion gap metabolic acidosis")
            self.assertEqual(answer_key["final_diagnosis"], "Salicylate toxicity")
            self.assertEqual(answer_key["expected_compensation"]["rule"], "Acute respiratory alkalosis")
            self.assertLess(gas["paco2_mmHg"], 35, msg=case["case_id"])
            self.assertGreater(ag, 16, msg=case["case_id"])
            self.assertLess(gas["hco3_mmolL"], expected_hco3 - 2, msg=case["case_id"])
            self.assertLess(electrolytes["glucose_mmolL"], 14.0, msg=case["case_id"])
            self.assertIsNotNone(lactate, msg=case["case_id"])
            self.assertLessEqual(lactate, 3.2, msg=case["case_id"])

            if gas["ph"] < 7.35:
                acidemic_case_count += 1
            elif gas["ph"] > 7.45:
                alkalemic_case_count += 1
            else:
                near_normal_case_count += 1

            additional_process_options = next(
                question["options"]
                for question in case["questions_flow"]
                if question.get("key") == "additional_metabolic_process"
            )
            self.assertIn("High anion gap metabolic acidosis", additional_process_options, msg=case["case_id"])

            diagnosis_options = next(
                question["options"]
                for question in case["questions_flow"]
                if question.get("key") == "final_diagnosis"
            )
            self.assertIn(
                "Respiratory alkalosis with concurrent high anion gap metabolic acidosis",
                diagnosis_options,
                msg=case["case_id"],
            )
            self.assertIn("Respiratory alkalosis", diagnosis_options, msg=case["case_id"])
            self.assertIn("High anion gap metabolic acidosis", diagnosis_options, msg=case["case_id"])
            self.assertIn("DKA", diagnosis_options, msg=case["case_id"])
            self.assertIn("Panic attack / hyperventilation", diagnosis_options, msg=case["case_id"])

            explanation = case.get("explanation", "").lower()
            self.assertIn("acute respiratory alkalosis", explanation, msg=case["case_id"])
            self.assertIn("bicarbonate is too low for isolated acute respiratory alkalosis", explanation, msg=case["case_id"])
            self.assertIn("classic for salicylate toxicity", explanation, msg=case["case_id"])

        self.assertGreaterEqual(alkalemic_case_count, 1)
        self.assertGreaterEqual(near_normal_case_count, 1)
        self.assertGreaterEqual(acidemic_case_count, 1)

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
            self.assertEqual(len(payload["cases"]), 184)

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
