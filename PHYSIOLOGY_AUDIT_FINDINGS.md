# Physiology And Generator Audit Findings

## 1. Executive Summary

Overall judgment:
- The core physiology helper layer is mostly sound.
- Several single-process and newer mixed-process generators are physiologically coherent.
- The project is not yet safe for exam-facing educational use in its current state.

Why it is not yet safe:
- The core high-risk physiology issues fixed today are materially improved, but the project still needs a final regeneration and execution pass before it can be treated as release-safe.
- Remaining risk now sits more in explanation quality, live-payload freshness, and long-tail content drift than in the previously identified critical mixed-disorder scoring errors.

Biggest strengths:
- Shared formulas in `generator/physiology.py` are correct for the compensation models currently in use.
- `mixed_hagma_metabolic_alkalosis`, `respiratory_acidosis_hagma`, `respiratory_alkalosis_hagma`, the redesigned `dka_vomiting`, and the reworked `salicylate_toxicity` are now the strongest physiology-first parts of the mixed-disorder library.
- The generator consistently derives pH from Henderson-Hasselbalch logic and validates ABG consistency against it.
- The previous compensation-schema break in `acute_copd_exacerbation` and `sepsis_respiratory_alkalosis` has been corrected, so those intermediate cases are now answerable within the binary UI contract.
- Validation now enforces explicit archetype-contract coverage, generic answer-key membership for scored steps, mixed-case numeric proof checks, and diagnosis-critical adjunct-lab contracts in [generator/validation.py](E:/Desktop/abg-trainer/generator/validation.py).

Biggest concerns:
- The checked-in live payload may still lag the source generators until `docs/abg_cases.json` is regenerated and revalidated in an executable environment.
- Validation still does not broadly check explanation correctness.
- Progression metadata and performance analytics remain much shallower than the physiology model now supports.

## 2. What Appears Physiologically Strong

- `generator/physiology.py` is directionally strong. Winter's formula, metabolic alkalosis compensation, acute respiratory acidosis bicarbonate rise, acute respiratory alkalosis bicarbonate fall, chronic respiratory acidosis bicarbonate rise, Henderson-Hasselbalch pH calculation, and AG calculation are all standard and implemented correctly in [generator/physiology.py](E:/Desktop/abg-trainer/generator/physiology.py#L175), [generator/physiology.py](E:/Desktop/abg-trainer/generator/physiology.py#L187), [generator/physiology.py](E:/Desktop/abg-trainer/generator/physiology.py#L191), [generator/physiology.py](E:/Desktop/abg-trainer/generator/physiology.py#L195), [generator/physiology.py](E:/Desktop/abg-trainer/generator/physiology.py#L199), and [generator/physiology.py](E:/Desktop/abg-trainer/generator/physiology.py#L207).
- The single-process beginner metabolic archetypes are mostly well shaped. `simple_nagma` and `simple_metabolic_alkalosis` intentionally keep pH clearly abnormal for beginner clarity and keep chloride direction physiologically aligned with the stated diagnosis in [generator/generators/metabolic.py](E:/Desktop/abg-trainer/generator/generators/metabolic.py#L326) and [generator/generators/metabolic.py](E:/Desktop/abg-trainer/generator/generators/metabolic.py#L407).
- The higher-risk HAGMA archetypes `starvation_ketosis`, `alcoholic_ketoacidosis`, `toxic_alcohol`, and `uraemia` are better than average. They use AG ranges, respiratory compensation windows, and context modifiers that usually support the named diagnosis rather than just generating generic HAGMA numbers in [generator/generators/metabolic.py](E:/Desktop/abg-trainer/generator/generators/metabolic.py#L485), [generator/generators/metabolic.py](E:/Desktop/abg-trainer/generator/generators/metabolic.py#L597), [generator/generators/metabolic.py](E:/Desktop/abg-trainer/generator/generators/metabolic.py#L685), and [generator/generators/metabolic.py](E:/Desktop/abg-trainer/generator/generators/metabolic.py#L1031).
- The strongest mixed-disorder implementations are `mixed_hagma_metabolic_alkalosis`, `respiratory_acidosis_hagma`, `respiratory_alkalosis_hagma`, and the redesigned `dka_vomiting`. They explicitly compare actual values against an expected compensation model rather than using vague "partial compensation" language in [generator/generators/mixed.py](E:/Desktop/abg-trainer/generator/generators/mixed.py) and [generator/validation.py](E:/Desktop/abg-trainer/generator/validation.py).
- Validation is substantially stronger than before because it now uses explicit archetype contracts, validates every scored step against its option list, audits archetype coverage across generated cases, and applies physiology-specific mixed-case plus adjunct-lab checks in [generator/validation.py](E:/Desktop/abg-trainer/generator/validation.py).

## 3. Findings By Severity

### Critical

- No current critical finding remains after the compensation-schema fix and the full `dka_vomiting` redesign.
- The remaining issues are still important for exam-facing release, but they are now better described as major educational-safety and robustness problems rather than immediately unsound live physiology.

### Major

- Title: Validation coverage is incomplete in exactly the places that most need it
- Severity: Major
- Issue:
  The original audit concern was valid, but most of the specific coverage gaps have now been addressed. The remaining gap is narrower: validation still does not broadly validate explanation correctness, and required distractor preservation still depends on targeted sanitizer allowlists rather than a formal contract per archetype.
- Why it matters:
  A case can still pass numeric validation while teaching the wrong lesson. That is especially risky for exam users, because the vulnerable failures now sit in explanation wording, distractor quality, and label framing rather than raw acid-base arithmetic.
- Evidence:
  `validation.py` now declares explicit archetype contracts, enforces generic scored-step answer membership, and validates mixed numeric proof plus diagnosis-critical labs in [generator/validation.py](E:/Desktop/abg-trainer/generator/validation.py). The remaining uncovered area is explanation-versus-physiology validation, and mixed distractor preservation is still handled indirectly through `sanitize_final_diagnosis_options()` allow-pairs in [generator/generators/common.py](E:/Desktop/abg-trainer/generator/generators/common.py).
- Recommended fix:
  Keep the current contract-based validation architecture, then add reusable explanation-versus-physiology checks and, if mixed distractor regressions recur, archetype-specific required-distractor assertions.

- Title: Salicylate cases are represented awkwardly enough to risk teaching the wrong "primary disorder"
- Severity: Major
- Issue:
  This finding has been addressed in source. `generate_salicylate_case` now models salicylate as respiratory alkalosis with concurrent high anion gap metabolic acidosis in [generator/generators/mixed.py](E:/Desktop/abg-trainer/generator/generators/mixed.py#L334).
- Why it matters:
  This was a genuine educational-safety issue because the previous schema forced an incorrect single-process framing onto classic salicylate mixed physiology.
- Evidence:
  The source generator now stores `primary_disorder="Respiratory alkalosis"`, `compensation="Inappropriate"`, `anion_gap_category="Raised"`, and `additional_metabolic_process="High anion gap metabolic acidosis"` with explicit acute respiratory alkalosis mismatch metadata in [generator/generators/mixed.py](E:/Desktop/abg-trainer/generator/generators/mixed.py#L334). The corresponding validator in [generator/validation.py](E:/Desktop/abg-trainer/generator/validation.py#L869) now fails any drift back to the old single-process model.
- Recommended fix:
  Completed in source. Regenerate `docs/abg_cases.json` in a runnable environment so the live payload matches the corrected salicylate model.

- Title: Final-diagnosis option sanitization is mutating curated distractors in physiology-significant ways
- Severity: Major
- Issue:
  This remains a watch area, but the mixed respiratory archetypes that failed today have been patched with a minimal sanitizer allowlist update in [generator/generators/common.py](E:/Desktop/abg-trainer/generator/generators/common.py).
- Why it matters:
  This weakens mixed-disorder teaching when explicitly curated single-process comparators disappear and generic backfill options replace them.
- Evidence:
  `respiratory_acidosis_hagma` and `respiratory_alkalosis_hagma` define explicit final-diagnosis distractors in [generator/generators/mixed.py](E:/Desktop/abg-trainer/generator/generators/mixed.py), and their current tests now assert preservation of the intended curated comparators in [generator/tests/test_generate_cases.py](E:/Desktop/abg-trainer/generator/tests/test_generate_cases.py).
- Recommended fix:
  The immediate regression was fixed with narrow allow-pair additions. A broader distractor-contract system can still wait unless this starts recurring across more archetypes.

### Moderate

- Title: Diarrhoea explanations can misstate pH status
- Severity: Moderate
- Issue:
  This finding has now been addressed in source. `generate_diarrhoea_case` now compares `derived_ph_status()` against the helper's actual enum outputs in [generator/generators/metabolic.py](E:/Desktop/abg-trainer/generator/generators/metabolic.py#L971).
- Why it matters:
  The original bug could tell a learner the pH was normal when the stored answer key correctly said acidaemia. That was a teaching-loop problem rather than a raw physiology-generation problem.
- Evidence:
  The explanation branch now uses `Acidaemia`, `Alkalaemia`, and `Normal` consistently, and the targeted explanation test in [generator/tests/test_generate_cases.py](E:/Desktop/abg-trainer/generator/tests/test_generate_cases.py#L823) would fail if this capitalization bug returned.
- Recommended fix:
  Completed in source. Keep the targeted test so this cannot silently regress.

- Title: The mixed-disorder schema handles extra metabolic processes better than extra respiratory ones
- Severity: Moderate
- Issue:
  This is still structurally true in general, but salicylate is no longer blocked by it because it now uses the same "respiratory primary + additional metabolic process" pattern as `respiratory_alkalosis_hagma`.
- Why it matters:
  It forces the system to flatten some genuine mixed disorders into awkward primary labels or omit a key reasoning step from the question flow.
- Evidence:
  `salicylate_toxicity` now fits the existing mixed master flow in [generator/generators/mixed.py](E:/Desktop/abg-trainer/generator/generators/mixed.py#L334), so this is a future-generalization issue rather than a current salicylate blocker.
- Recommended fix:
  Introduce a more general "additional_process" schema or a separate mixed-pattern question step for master mixed cases.

- Title: `lactic_acidosis` is physiologically okay but educationally under-explained
- Severity: Moderate
- Issue:
  This finding has now been addressed in source. `generate_lactate_case` still generates the same physiology pattern, but its explanation now explicitly walks through pH status, primary disorder, Winter compensation, anion gap calculation, and why the lactate/sepsis context fits lactic acidosis in [generator/generators/metabolic.py](E:/Desktop/abg-trainer/generator/generators/metabolic.py#L1104).
- Why it matters:
  The previous one-line explanation did not reinforce the exact reasoning steps the learner was being scored on, which weakened the educational value of an otherwise sound archetype.
- Evidence:
  The updated explanation now references pH, HCO3, Winter's formula, anion gap, lactate, and septic context, and the targeted content test in [generator/tests/test_generate_cases.py](E:/Desktop/abg-trainer/generator/tests/test_generate_cases.py#L842) locks those teaching elements in place.
- Recommended fix:
  Completed in source. Regenerate `docs/abg_cases.json` in a runnable environment so the live payload picks up the stronger lactic-acidosis explanation.

### Minor

- Title: Some answer-key numeric derivations are done before display rounding
- Severity: Minor
- Issue:
  A few builders still calculate AG from pre-rounded floats and then display rounded integers after `build_inputs()`.
- Why it matters:
  This usually only creates 0.1-level drift, but it is a future threshold risk if more cases get closer to the AG cutoff.
- Evidence:
  `generate_lactate_case` still uses random floats for electrolytes in [generator/generators/metabolic.py](E:/Desktop/abg-trainer/generator/generators/metabolic.py#L1099).
- Recommended fix:
  Calculate the stored AG from the post-round displayed values.

### Watchlist / Future Risk

- Title: Validation only partially checks generic answer-key membership
- Severity: Watchlist
- Issue:
  Validation now guards compensation answers when a compensation question is present, but the broader pattern is still incomplete. `validate_final_diagnosis_options()` in [generator/validation.py](E:/Desktop/abg-trainer/generator/validation.py#L69) remains diagnosis-specific, and there is still no equally broad generic validation that all other answer-key fields always appear in their option sets.
- Why it matters:
  The specific compensation drift that previously shipped is now blocked, but similar schema mismatches could still recur in other question types.
- Recommended fix:
  Extend the same idea across every scored step, not just compensation and final diagnosis.

- Title: Shared default glucose injection is useful, but diagnostically dangerous
- Severity: Watchlist
- Issue:
  The Master-level default in [generator/physiology.py](E:/Desktop/abg-trainer/generator/physiology.py#L150) is safe for generic schema completeness, but unsafe for diagnosis families where glucose meaningfully differentiates causes.
- Why it matters:
  Future archetypes can accidentally inherit a "normal glucose" they did not intend, exactly as the earlier `dka_vomiting` bug demonstrated.
- Recommended fix:
  Limit auto-filled glucose to archetypes where a default normal value is diagnostically neutral, or make the helper opt-in rather than automatic.

- Title: Mixed-case distractor quality can drift silently as the diagnosis-conflict heuristics evolve
- Severity: Watchlist
- Issue:
  The token-overlap rules in [generator/generators/common.py](E:/Desktop/abg-trainer/generator/generators/common.py#L199) are broad and not physiology-aware.
- Why it matters:
  Future mixed archetypes can appear to have well-designed distractors in source but ship with a different educational contrast in the payload.
- Recommended fix:
  Add archetype-level assertions for required final-diagnosis distractors, not just uniqueness/non-overlap.

## 4. Archetype-By-Archetype Review

- `simple_nagma`: Strong. Clear beginner hyperchloraemic NAGMA pattern with pH kept acidemic and compensation constrained.
- `simple_metabolic_alkalosis`: Strong. Clear beginner alkalosis pattern with chloride direction and respiratory compensation aligned.
- `dka`: Probably correct, but it would teach more safely with explicit glucose.
- `dka`: Stronger than before. It now includes explicit DKA-supportive glucose in source and validation.
- `alcoholic_ketoacidosis`: Stronger than average. Good use of mild lactate and now explicit non-DKA glucose framing.
- `starvation_ketosis`: Strong. Good use of low-normal glucose and mild AG ranges.
- `toxic_alcohol`: Strong. Good distinction from lactate-heavy HAGMA.
- `vomiting_metabolic_alkalosis`: Fine physiologically.
- `diuretic_metabolic_alkalosis`: Fine physiologically.
- `diarrhoea_nagma`: Improved. The explanation branch now matches the stored pH-status enum correctly.
- `lactic_acidosis`: Improved. Physiology remains acceptable and the explanation now teaches the scored reasoning steps explicitly.
- `uraemia`: Strong enough.
- `opioid_toxicity`: Fine acute respiratory acidosis physiology.
- `simple_respiratory_acidosis`: Fine beginner respiratory acidosis archetype.
- `copd_chronic_retainer`: Strong chronic respiratory acidosis implementation.
- `panic_hyperventilation`: Fine acute respiratory alkalosis implementation.
- `simple_respiratory_alkalosis`: Fine beginner respiratory alkalosis archetype.
- `sepsis_respiratory_alkalosis`: Improved. It now fits the binary compensation contract as acute respiratory alkalosis with defensible appropriate compensation and explicit expected-compensation metadata.
- `acute_copd_exacerbation`: Improved. It now fits the binary contract as respiratory acidosis scored `Inappropriate` relative to isolated chronic compensation, with the acute-on-chronic nuance carried in the explanation.
- `salicylate_toxicity`: Improved substantially. It now teaches the intended classic pattern as respiratory alkalosis with concurrent HAGMA and validates the mixed physiology numerically.
- `mixed_hagma_metabolic_alkalosis`: Strong and probably the best current mixed archetype.
- `respiratory_acidosis_hagma`: Strong. Good use of chronic vs acute compensation rules and mismatch logic.
- `respiratory_alkalosis_hagma`: Strong. Good counterpart to the respiratory-acidosis mixed archetype.
- `dka_vomiting`: Improved substantially. It now has explicit DKA-supportive glucose, delta-gap evidence for concurrent metabolic alkalosis, Winter-consistent respiratory compensation, and targeted validation. The remaining weakness is distractor sanitization rather than core physiology.

## 5. Validation Gap Review

What validation currently catches well:
- Generic schema completeness and numeric plausibility in [generator/validation.py](E:/Desktop/abg-trainer/generator/validation.py#L98).
- Henderson-Hasselbalch consistency via re-derived pH.
- AG recalculation from displayed values.
- Many archetype-specific compensation models for the stronger metabolic and mixed archetypes.
- Generic scored-step answer membership against option lists.
- Explicit archetype coverage auditing across generated cases.
- Binary compensation membership when a compensation question is present.
- `dka`, `dka_vomiting`, `alcoholic_ketoacidosis`, `starvation_ketosis`, `lactic_acidosis`, `toxic_alcohol`, and `salicylate_toxicity` now have adjunct-lab support/contradiction checks where relevant.
- Mixed cases now validate second-process proof numerically rather than trusting labels alone.
- Final-diagnosis option overlap and duplication.

What validation currently misses:
- Explanation correctness against the displayed physiology.
- Whether every archetype with curated final-diagnosis distractors has a formal required-distractor contract.

What should eventually be validated:
- Every registered archetype should declare its compensation rule explicitly or declare that no compensation question should be asked.
- Mixed cases should validate that the second process is actually proven by the numbers, not just by the stem.
- Diagnosis-critical adjunct labs such as glucose in DKA-family cases should be archetype-specific, not just schema-complete.
- Explanation text should be checked against the displayed physiology for archetypes where the explanation is part of the teaching contract.

## 6. Recommended Next Actions

Must fix before wider release:
- Regenerate and revalidate `docs/abg_cases.json` in an environment with a runnable Python toolchain so the shipped payload matches the corrected source generators and validators.
- Add broader validation for explanation correctness and, if needed, formal required-distractor contracts for mixed archetypes.
- Re-audit and regenerate `docs/abg_cases.json` after any further physiology-critical fixes.

Should improve soon:
- Improve progression/performance metadata if the product is going to introduce weakness-driven remediation.
- Continue raising explanation quality in archetypes that are still shorter or less explicit than the strongest metabolic generators.

Can wait:
- Clean up progression metadata drift such as incomplete `case_pool` mapping.
- Refine distractor curation once the physiology and scoring model are reliable.
