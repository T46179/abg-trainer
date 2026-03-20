# Physiology And Generator Audit Findings

## 1. Executive Summary

Overall judgment:
- The core physiology helper layer is mostly sound.
- Several single-process and newer mixed-process generators are physiologically coherent.
- The project is not yet safe for exam-facing educational use in its current state.

Why it is not yet safe:
- One important mixed archetype, `salicylate_toxicity`, still teaches an awkward and potentially misleading forced primary-disorder label.
- Validation coverage is still incomplete enough that explanation drift, adjunct-lab drift, and distractor drift can slip through silently.

Biggest strengths:
- Shared formulas in `generator/physiology.py` are correct for the compensation models currently in use.
- `mixed_hagma_metabolic_alkalosis`, `respiratory_acidosis_hagma`, `respiratory_alkalosis_hagma`, and the redesigned `dka_vomiting` are now the strongest physiology-first parts of the mixed-disorder library.
- The generator consistently derives pH from Henderson-Hasselbalch logic and validates ABG consistency against it.
- The previous compensation-schema break in `acute_copd_exacerbation` and `sepsis_respiratory_alkalosis` has been corrected, so those intermediate cases are now answerable within the binary UI contract.

Biggest concerns:
- `salicylate_toxicity` still asks learners to force a single primary-disorder label onto physiology that is genuinely cross-system.
- Validation still does not broadly check explanation correctness, adjunct-lab support, or preservation of intended distractors.
- A mixed-disorder schema that handles extra metabolic processes reasonably well but handles mixed respiratory-plus-metabolic teaching awkwardly.

## 2. What Appears Physiologically Strong

- `generator/physiology.py` is directionally strong. Winter's formula, metabolic alkalosis compensation, acute respiratory acidosis bicarbonate rise, acute respiratory alkalosis bicarbonate fall, chronic respiratory acidosis bicarbonate rise, Henderson-Hasselbalch pH calculation, and AG calculation are all standard and implemented correctly in [generator/physiology.py](E:/Desktop/abg-trainer/generator/physiology.py#L175), [generator/physiology.py](E:/Desktop/abg-trainer/generator/physiology.py#L187), [generator/physiology.py](E:/Desktop/abg-trainer/generator/physiology.py#L191), [generator/physiology.py](E:/Desktop/abg-trainer/generator/physiology.py#L195), [generator/physiology.py](E:/Desktop/abg-trainer/generator/physiology.py#L199), and [generator/physiology.py](E:/Desktop/abg-trainer/generator/physiology.py#L207).
- The single-process beginner metabolic archetypes are mostly well shaped. `simple_nagma` and `simple_metabolic_alkalosis` intentionally keep pH clearly abnormal for beginner clarity and keep chloride direction physiologically aligned with the stated diagnosis in [generator/generators/metabolic.py](E:/Desktop/abg-trainer/generator/generators/metabolic.py#L326) and [generator/generators/metabolic.py](E:/Desktop/abg-trainer/generator/generators/metabolic.py#L407).
- The higher-risk HAGMA archetypes `starvation_ketosis`, `alcoholic_ketoacidosis`, `toxic_alcohol`, and `uraemia` are better than average. They use AG ranges, respiratory compensation windows, and context modifiers that usually support the named diagnosis rather than just generating generic HAGMA numbers in [generator/generators/metabolic.py](E:/Desktop/abg-trainer/generator/generators/metabolic.py#L485), [generator/generators/metabolic.py](E:/Desktop/abg-trainer/generator/generators/metabolic.py#L597), [generator/generators/metabolic.py](E:/Desktop/abg-trainer/generator/generators/metabolic.py#L685), and [generator/generators/metabolic.py](E:/Desktop/abg-trainer/generator/generators/metabolic.py#L1031).
- The strongest mixed-disorder implementations are `mixed_hagma_metabolic_alkalosis`, `respiratory_acidosis_hagma`, `respiratory_alkalosis_hagma`, and the redesigned `dka_vomiting`. They explicitly compare actual values against an expected compensation model rather than using vague "partial compensation" language in [generator/generators/mixed.py](E:/Desktop/abg-trainer/generator/generators/mixed.py) and [generator/validation.py](E:/Desktop/abg-trainer/generator/validation.py).
- Validation is stronger than before because compensation answers with a compensation question must now stay inside the binary option set, `acute_copd_exacerbation` plus `sepsis_respiratory_alkalosis` now have archetype-specific checks, and `dka_vomiting` now validates hyperglycaemia support, delta-gap-preserved bicarbonate, and Winter-consistent respiratory compensation in [generator/validation.py](E:/Desktop/abg-trainer/generator/validation.py).

## 3. Findings By Severity

### Critical

- No current critical finding remains after the compensation-schema fix and the full `dka_vomiting` redesign.
- The remaining issues are still important for exam-facing release, but they are now better described as major educational-safety and robustness problems rather than immediately unsound live physiology.

### Major

- Title: Validation coverage is incomplete in exactly the places that most need it
- Severity: Major
- Issue:
  Validation is stronger than before, but it still does not broadly validate explanation correctness, diagnosis-supporting adjunct labs across all archetypes, or preservation of required final-diagnosis distractors after sanitization.
- Why it matters:
  A case can still pass numeric validation while teaching the wrong lesson. That is especially risky for exam users, because the vulnerable failures now sit in explanation wording, distractor quality, and label framing rather than raw acid-base arithmetic.
- Evidence:
  `validation.py` now contains targeted branches for the previously broken respiratory intermediate archetypes and for `dka_vomiting`, but there is still no generic check that an explanation matches the displayed physiology or that curated mixed-disorder distractors survive `sanitize_final_diagnosis_options()` in [generator/generators/common.py](E:/Desktop/abg-trainer/generator/generators/common.py).
- Recommended fix:
  Extend validation beyond raw numeric plausibility. Add reusable checks for explanation-versus-physiology consistency, diagnosis-supporting adjunct labs where relevant, and required distractor presence for mixed cases.

- Title: Salicylate cases are represented awkwardly enough to risk teaching the wrong "primary disorder"
- Severity: Major
- Issue:
  `generate_salicylate_case` hardcodes `primary_disorder="Metabolic acidosis"` in [generator/generators/mixed.py](E:/Desktop/abg-trainer/generator/generators/mixed.py#L282), even though the explanation correctly says the low PaCO2 indicates respiratory alkalosis and some live cases are alkalemic or near-normal.
- Why it matters:
  The learner is explicitly asked to choose a primary disorder. In current salicylate cases, the answer key can tell them to click "Metabolic acidosis" even when the pH is alkalemic and the explanation itself says respiratory alkalosis is present. That is pedagogically unstable for exam users.
- Evidence:
  Live salicylate case [docs/abg_cases.json](E:/Desktop/abg-trainer/docs/abg_cases.json#L8231) stores `ph_status = "Alkalaemia"` and `primary_disorder = "Metabolic acidosis"`, while the explanation at [docs/abg_cases.json](E:/Desktop/abg-trainer/docs/abg_cases.json#L8251) says the low PaCO2 indicates respiratory alkalosis.
- Recommended fix:
  Either change the question model for salicylate so it asks for "overall pattern" rather than a forced primary single-process label, or add a schema path that can encode a concurrent respiratory process explicitly.

- Title: Final-diagnosis option sanitization is mutating curated distractors in physiology-significant ways
- Severity: Major
- Issue:
  Mixed archetypes define pedagogically chosen distractors in their generators, but `sanitize_final_diagnosis_options()` in [generator/generators/common.py](E:/Desktop/abg-trainer/generator/generators/common.py#L229) can remove them and backfill from a generic pool in [generator/generators/common.py](E:/Desktop/abg-trainer/generator/generators/common.py#L10).
- Why it matters:
  This weakens mixed-disorder teaching. The intended "mixed vs single-process" distractors can disappear silently, so the final question may stop testing the physiology the archetype was designed to teach.
- Evidence:
  `dka_vomiting` still requests `["DKA with vomiting", "DKA", "Vomiting", "Salicylate toxicity", "Renal failure"]` in [generator/generators/mixed.py](E:/Desktop/abg-trainer/generator/generators/mixed.py), but the shipped payload example [docs/abg_cases.json](E:/Desktop/abg-trainer/docs/abg_cases.json) still backfills away the most educationally important single-process comparators.
- Recommended fix:
  Stop using token-overlap heuristics as the final authority for mixed-disorder diagnosis sets. Preserve explicitly authored distractors unless there is a truly identical label collision.

### Moderate

- Title: Diarrhoea explanations can misstate pH status
- Severity: Moderate
- Issue:
  `generate_diarrhoea_case` compares `derived_ph_status()` against lowercase strings in [generator/generators/metabolic.py](E:/Desktop/abg-trainer/generator/generators/metabolic.py#L981) and [generator/generators/metabolic.py](E:/Desktop/abg-trainer/generator/generators/metabolic.py#L983), but `derived_ph_status()` returns capitalized values in [generator/physiology.py](E:/Desktop/abg-trainer/generator/physiology.py#L211).
- Why it matters:
  Feedback text can tell a learner the pH is normal when the case is actually acidemic. That is not just cosmetic if the explanation is part of the teaching loop.
- Evidence:
  The lowercase comparisons can never match the capitalized helper output.
- Recommended fix:
  Normalize the string comparison or compare against the helper's actual enum values.

- Title: The mixed-disorder schema handles extra metabolic processes better than extra respiratory ones
- Severity: Moderate
- Issue:
  `additional_metabolic_process` is explicitly metabolic-only in [generator/config.py](E:/Desktop/abg-trainer/generator/config.py#L99). That works for the HAGMA-plus-respiratory archetypes, but not for salicylate or any future case where the second process is respiratory.
- Why it matters:
  It forces the system to flatten some genuine mixed disorders into awkward primary labels or omit a key reasoning step from the question flow.
- Evidence:
  `salicylate_toxicity` is a mixed respiratory alkalosis plus HAGMA case in [generator/generators/mixed.py](E:/Desktop/abg-trainer/generator/generators/mixed.py#L240), but there is no schema path to ask the learner to name the concurrent respiratory process.
- Recommended fix:
  Introduce a more general "additional_process" schema or a separate mixed-pattern question step for master mixed cases.

- Title: `lactic_acidosis` is physiologically okay but educationally under-explained
- Severity: Moderate
- Issue:
  `generate_lactate_case` produces plausible HAGMA numbers in [generator/generators/metabolic.py](E:/Desktop/abg-trainer/generator/generators/metabolic.py#L1096), but its explanation is only `"Sepsis commonly causes high anion gap metabolic acidosis due to lactate accumulation."`
- Why it matters:
  The answer key expects the learner to reason through primary disorder, compensation, and anion gap, but the explanation does not reinforce those steps.
- Evidence:
  See [generator/generators/metabolic.py](E:/Desktop/abg-trainer/generator/generators/metabolic.py#L1125) versus the one-line explanation at [generator/generators/metabolic.py](E:/Desktop/abg-trainer/generator/generators/metabolic.py#L1133).
- Recommended fix:
  Bring the explanation up to the same standard as the stronger metabolic generators.

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
- `alcoholic_ketoacidosis`: Stronger than average. Good use of mild lactate and non-hyperglycaemic framing.
- `starvation_ketosis`: Strong. Good use of low-normal glucose and mild AG ranges.
- `toxic_alcohol`: Strong. Good distinction from lactate-heavy HAGMA.
- `vomiting_metabolic_alkalosis`: Fine physiologically.
- `diuretic_metabolic_alkalosis`: Fine physiologically.
- `diarrhoea_nagma`: Physiology is fine; explanation logic is bugged.
- `lactic_acidosis`: Physiology acceptable, explanation underpowered.
- `uraemia`: Strong enough.
- `opioid_toxicity`: Fine acute respiratory acidosis physiology.
- `simple_respiratory_acidosis`: Fine beginner respiratory acidosis archetype.
- `copd_chronic_retainer`: Strong chronic respiratory acidosis implementation.
- `panic_hyperventilation`: Fine acute respiratory alkalosis implementation.
- `simple_respiratory_alkalosis`: Fine beginner respiratory alkalosis archetype.
- `sepsis_respiratory_alkalosis`: Improved. It now fits the binary compensation contract as acute respiratory alkalosis with defensible appropriate compensation and explicit expected-compensation metadata.
- `acute_copd_exacerbation`: Improved. It now fits the binary contract as respiratory acidosis scored `Inappropriate` relative to isolated chronic compensation, with the acute-on-chronic nuance carried in the explanation.
- `salicylate_toxicity`: Genuine mixed physiology, but the forced primary-disorder labelling is educationally awkward.
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
- Binary compensation membership when a compensation question is present.
- `dka_vomiting` now validates hyperglycaemia support, preserved bicarbonate above isolated-HAGMA expectations, and Winter-consistent compensation.
- Final-diagnosis option overlap and duplication.

What validation currently misses:
- Generic answer-key membership for non-diagnosis steps other than compensation.
- Explanation correctness against the displayed physiology.
- Whether diagnosis-supporting contextual labs such as glucose or lactate support the named diagnosis across the whole library rather than only in archetypes with bespoke checks.
- Whether mixed-case diagnosis distractors still include the intended single-process comparators after sanitization.

What should eventually be validated:
- Every registered archetype should declare its compensation rule explicitly or declare that no compensation question should be asked.
- Every step's correct answer should be validated against its option list.
- Mixed cases should validate that the second process is actually proven by the numbers, not just by the stem.
- Diagnosis-critical adjunct labs such as glucose in DKA-family cases should be archetype-specific, not just schema-complete.

## 6. Recommended Next Actions

Must fix before wider release:
- Rework salicylate question modelling so it does not force a misleading single primary disorder.
- Add broader validation for explanation correctness, adjunct-lab support, and required mixed-case distractors.
- Re-audit and regenerate `docs/abg_cases.json` after any further physiology-critical fixes.

Should improve soon:
- Add generic answer-key-versus-option validation for all question steps.
- Fix the diarrhoea explanation branch bug.
- Make explanation quality more consistent for cases like `lactic_acidosis`.

Can wait:
- Clean up progression metadata drift such as incomplete `case_pool` mapping.
- Refine distractor curation once the physiology and scoring model are reliable.
