# AI Project Context: ABG Trainer

Last updated: 2026-03-20

This document summarizes the architecture and case schema so external AI tools can understand the project even when only this file is provided.

This file is a high-level architecture snapshot for external AI tools such as ChatGPT, Codex, or other assistants. It is intended to be usable on its own if uploaded without the rest of the repository.

To keep it updateable as the architecture evolves, treat these files as the source of truth when refreshing this document:
- `generator/generate_cases.py`
- `generator/generators/common.py`
- `generator/generators/metabolic.py`
- `generator/generators/respiratory.py`
- `generator/generators/mixed.py`
- `generator/physiology.py`
- `generator/question_flow.py`
- `generator/progression.py`
- `generator/validation.py`
- `docs/index.html`
- `docs/app.js`
- `docs/styles.css`

## 1. Project Overview

ABG Trainer is an interactive arterial blood gas training platform.

Main goals:
- Teach acid-base interpretation.
- Generate physiologically coherent ABG cases.
- Progressively increase difficulty.
- Provide structured diagnostic reasoning practice.

The backend generation layer is written in Python. It creates validated case objects, exports them to JSON, and the static web frontend loads that JSON for practice sessions.

In practical terms:
- Python generates case data and progression metadata.
- The generator writes output to `docs/abg_cases.json`.
- The frontend loads that JSON and renders the learning experience in the browser.

## 2. Repository Structure

High-level structure:

```text
generator/
    config.py
    physiology.py
    progression.py
    question_flow.py
    stems.py
    validation.py
    reporting.py
    generate_cases.py

    generators/
        common.py
        metabolic.py
        respiratory.py
        mixed.py

    tests/
        test_generate_cases.py

docs/
    index.html
    app.js
    styles.css
    abg_cases.json

archive/
```

What the main modules do:

- `generator/config.py`
  - Shared static configuration.
  - Stores prompt text, option lists, stem-bank content, XP settings, difficulty unlock settings, and the explicit testing-mode flags used for feedback builds.

- `generator/physiology.py`
  - The core physiology/math helper layer.
  - Calculates pH, compensation expectations, anion gap, rounding, and pH status labels.

- `generator/progression.py`
  - Adds progression metadata to each case.
  - Defines difficulty labels, XP rules, unlock thresholds, dashboard/user state, progression simulations, and exposes testing-mode config to the frontend.

- `generator/question_flow.py`
  - Defines reusable question steps and difficulty-based question flow builders.
  - Controls which reasoning steps appear at each level.

- `generator/stems.py`
  - Builds varied clinical stems from configurable stem banks.
  - Helps create less repetitive prompts without changing the underlying physiology.

- `generator/validation.py`
  - Validates each generated case.
  - Checks physiologic plausibility, question flow structure, archetype-specific compensation expectations, and duplicate IDs.

- `generator/reporting.py`
  - Prints generation summaries and examples for local inspection when building the JSON payload.

- `generator/generate_cases.py`
  - Main generation entry point.
  - Imports all registered case builders, generates the full case set, validates it, shuffles it, and writes `docs/abg_cases.json`.

- `generator/generators/common.py`
  - Shared builders used by all archetype modules.
  - Provides `build_inputs()`, `build_answer_key()`, and `build_case()`.

- `generator/generators/metabolic.py`
  - Metabolic disorder archetype generators.

- `generator/generators/respiratory.py`
  - Respiratory disorder archetype generators.

- `generator/generators/mixed.py`
  - Mixed-disorder archetype generators.

- `generator/tests/test_generate_cases.py`
  - Coverage-style integration tests for case counts, structure, plausibility, and JSON output.

- `docs/index.html`
  - Static HTML shell for the training app.
  - Defines the dashboard, practice, results, learn, leaderboard, and profile views, plus the first-run practice intro modal, feedback/reset footer controls, and analytics script tags.

- `docs/app.js`
  - Frontend SPA controller for loading the generated payload, persisting user state in local storage, rendering all views, handling practice flow, scoring, analytics events, feedback links, and launch/testing access behavior.

- `docs/styles.css`
  - Frontend presentation layer.
  - Implements the current responsive card-based dashboard/practice/results/profile/leaderboard layout and modal/footer styling.

- `docs/abg_cases.json`
  - Generated data payload consumed by the frontend.

- `archive/`
  - Historical generator versions and reference snapshots.

## 3. Case Generation Architecture

All case builders follow the same general pattern.

Each case generator typically:
1. Generates physiologically coherent lab values.
2. Calculates pH using Henderson-Hasselbalch logic.
3. Derives expected compensation.
4. Calculates anion gap.
5. Builds or selects a clinical stem.
6. Constructs the answer key.
7. Attaches a question flow.
8. Returns a complete case via `build_case()`.

Several archetypes also use variation bands. These bands widen replay variety by changing severity or subtlety ranges while preserving the same core physiological pattern, diagnosis family, and question flow.

Current band patterns include:
- `mild` / `moderate` / `severe`
- `subtle` / `moderate` / `severe`

Architecturally, these bands are used to vary:
- PaCO2 ranges
- HCO3 ranges or compensation deltas
- electrolyte ranges
- stem-feature density or stem-option severity

The important design point is that variation bands increase replayability and reduce case memorisation without changing the underlying acid-base physiology or the intended reasoning path for that archetype.

Standard case builder shape:

```python
build_case(
    case_id=...,
    title=...,
    category=...,
    learning_objective=...,
    tags=...,
    clinical_stem=...,
    inputs=...,
    questions_flow=...,
    answer_key=...,
    explanation=...,
    timing=...,
    level=...,
    archetype=...,
)
```

Important shared builders:
- `build_inputs()`
  - Normalizes the sparse shared `inputs` schema.
  - Core containers are `gas` and `electrolytes`, with an optional `other` container for richer non-core labs.
  - During the lactate migration, canonical lactate lives in `inputs.other.lactate_mmolL` while a legacy top-level `inputs.lactate_mmolL` mirror may still be emitted for backward compatibility.
- `build_answer_key()`
  - Normalizes the answer schema across archetypes.
- `build_case()`
  - Creates the final case object and attaches progression metadata such as difficulty, archetype, skills tested, and case pool.
  - Also applies centralized level-based input defaults before metadata attachment, including guaranteed `glucose_mmolL` for Master-level cases.

Architecturally, the important idea is that archetype modules are thin composers. They do not own global app logic. They combine:
- physiology helpers
- stem generation
- question flow
- answer-key construction
- progression metadata

## Case Data Schema

The generated frontend payload is now a wrapped JSON object rather than a bare case array. `docs/app.js` accepts either shape, but the current generated contract is:

```text
{
  progression_config: object,
  default_user_state: object,
  dashboard_state: object,
  cases: Case[]
}
```

Every generated case object still follows a standardized data-driven schema used by the frontend. The browser app relies on this structure rather than hard-coded diagnosis-specific UI logic.

Current case schema:

```text
{
  case_id: string,
  title: string,
  case_type: string,   // currently "ABG"
  category: string,
  clinical_stem: string,
  patient_gender?: string,

  inputs: {
    gas: {
      ph: number,
      paco2_mmHg: number,
      hco3_mmolL: number,
      pao2_mmHg?: number,
      base_excess_mEqL?: number,
      spo2_percent?: number
    },
    electrolytes: {
      na_mmolL: number,
      k_mmolL?: number,
      cl_mmolL: number,
      glucose_mmolL?: number
    },
    other?: {
      lactate_mmolL?: number,
      hb_gL?: number,
      methb_percent?: number,
      cohb_percent?: number
    },
    lactate_mmolL?: number   // legacy transitional mirror for backward compatibility
  },

  questions_flow: QuestionStep[],

  answer_key: {
    ph_status: string,
    primary_disorder: string,
    compensation: string,
    anion_gap_value: number,
    anion_gap_category: string,
    final_diagnosis: string,
    expected_compensation?: object,
    additional_metabolic_process?: string
  },

  learning_objective?: string,
  tags?: string[],
  explanation?: string,
  timing?: object,

  difficulty_level: number,
  difficulty_label: string,
  archetype: string,
  skills_tested: string[],
  case_pool: string
}
```

Key field roles:
- `inputs`
  - Raw ABG and electrolyte values used for interpretation.
- The schema is intentionally wide but sparse: only explicitly provided fields are emitted.
- Canonical containers are `gas`, `electrolytes`, and optional `other`.
- The frontend can currently display optional `pao2_mmHg`, `base_excess_mEqL`, `k_mmolL`, `glucose_mmolL`, and lactate when present.
- `starvation_ketosis` is the first archetype that actively uses the widened schema for `inputs.electrolytes.glucose_mmolL`.
- During the transition to the canonical `other` container, lactate may appear in either `inputs.other.lactate_mmolL` or the legacy top-level `inputs.lactate_mmolL`.
- `questions_flow`
  - Defines the step-by-step reasoning questions shown to the learner.
- `patient_gender`
  - Optional top-level metadata currently carrying `"M"` or `"F"` for the shorthand used in `clinical_stem`.
  - Intended as lightweight future-facing metadata and not yet used by frontend logic.
- `answer_key`
  - Contains the correct interpretation used by the scoring logic.
  - `additional_metabolic_process` is currently used on Master mixed-disorder flows and supports `"None"`, `"Metabolic alkalosis"`, `"Non-anion gap metabolic acidosis"`, and `"High anion gap metabolic acidosis"`.
- `explanation`
  - Provides the educational explanation shown after completion.
- `difficulty_level` / `difficulty_label`
  - Determine difficulty and drive frontend filtering, unlocking, and labels.
- `archetype`
  - Identifies the physiological pattern used to generate the case.
- `skills_tested` / `case_pool`
  - Progression metadata attached by `generator/progression.py` and consumed by the broader app contract.

The wrapped payload also carries frontend-facing progression state:
- `progression_config`
  - XP rules, speed bonuses, testing-mode flags, unlock levels, daily limits, and difficulty labels.
- `default_user_state`
  - The generated baseline local user state.
- `dashboard_state`
  - Precomputed dashboard-facing user and difficulty summary data.

## 4. Physiology Engine

The key physiology and numeric helpers live in `generator/physiology.py`.

Important functions include:
- `estimate_ph`
- `calculate_ph_from_hco3_paco2`
- `winters_expected_paco2`
- `metabolic_alkalosis_expected_paco2`
- `acute_respiratory_acidosis_expected_hco3`
- `respiratory_alkalosis_expected_hco3_acute`
- `chronic_respiratory_acidosis_expected_hco3`
- `calc_anion_gap`
- `derived_ph_status`

What this means architecturally:
- The generator does not produce random disconnected numbers.
- It produces ABG combinations that are designed to obey known acid-base relationships.
- Validation then checks that the generated case still matches those expected formulas within tolerance.

Examples of built-in physiologic reasoning:
- Metabolic acidosis uses Winter's formula for expected respiratory compensation.
- Metabolic alkalosis uses expected compensatory PaCO2.
- Acute respiratory acidosis estimates expected bicarbonate rise.
- Acute respiratory alkalosis estimates expected bicarbonate reduction.
- Chronic respiratory acidosis estimates expected bicarbonate elevation.
- Anion gap is computed directly from sodium, chloride, and bicarbonate.

This physiology layer is what keeps the training cases medically coherent.

## 5. Question Flow System

Question flow is defined in `generator/question_flow.py`.

Main flow builders:
- `beginner_question_flow`
- `intermediate_question_flow`
- `advanced_question_flow`
- `expert_question_flow`

Typical diagnostic reasoning steps:
1. pH status
2. Primary disorder
3. Compensation
4. Anion gap
5. Additional mixed disorder reasoning at the highest level

There is also:
- `shuffle_question_options()`

Current role of the question flow system:
- It determines which reasoning steps the learner must perform.
- It keeps question structure consistent across archetypes.
- It scales cognitive load by difficulty.

Frontend rendering keeps option order static for most question types. The main exception is `final_diagnosis`: diagnosis options are sanitized generator-side to remove conflicting duplicates, then reshuffled client-side once per attempt so order stays stable during that attempt while reducing memorisation and duplicate-distractor issues.

Typical difficulty progression:
- Beginner: pH status, primary disorder, then diagnosis.
- Intermediate: adds compensation.
- Advanced: adds anion gap.
- Expert/master: can add extra mixed-disorder interpretation such as `additional_metabolic_process`.

## 6. Current Archetype Library

Archetypes are organized by module. They represent acid-base patterns first, and only secondarily the clinical scenario that explains them.

### Metabolic

- `simple_nagma` - Beginner
- `simple_metabolic_alkalosis` - Beginner
- `dka` - Advanced
- `alcoholic_ketoacidosis` - Advanced
- `starvation_ketosis` - Advanced
- `toxic_alcohol` - Advanced
- `vomiting_metabolic_alkalosis` - Intermediate
- `diuretic_metabolic_alkalosis` - Intermediate
- `diarrhoea_nagma` - Advanced
- `lactic_acidosis` - Advanced
- `uraemia` - Advanced

### Respiratory

- `panic_hyperventilation` - Beginner
- `opioid_toxicity` - Beginner
- `copd_chronic_retainer` - Intermediate
- `acute_copd_exacerbation` - Intermediate
- `sepsis_respiratory_alkalosis` - Intermediate
- `simple_respiratory_alkalosis` - Beginner
- `simple_respiratory_acidosis` - Beginner

### Mixed

- `salicylate_toxicity` - Master
- `dka_vomiting` - Master
- `mixed_hagma_metabolic_alkalosis` - Master
- `respiratory_alkalosis_hagma` - Master
- `respiratory_acidosis_hagma` - Master

Design interpretation:
- An archetype is not just a diagnosis label.
- It is a reusable physiological pattern with a consistent compensation profile, diagnostic explanation, and question structure.
- Some archetypes now include mild/moderate/severe or subtle/moderate/severe variation bands to improve replay variety without changing the underlying acid-base pattern.
- This now includes `simple_respiratory_alkalosis` and `simple_respiratory_acidosis`, which represent single-process respiratory disorders aimed primarily at beginner pattern recognition.
- `mixed_hagma_metabolic_alkalosis` now also uses structured variation bands (`obvious_mix`, `subtle_mix`, and `near_normal_ph_trap`) to vary how strongly the additional metabolic alkalosis is signalled while preserving the same Master-level mixed-disorder reasoning path.
- `respiratory_alkalosis_hagma` is the respiratory-alkalosis counterpart to the respiratory-acidosis mixed archetype. It uses acute respiratory alkalosis compensation expectations and variation bands (`obvious_mixed`, `near_normal_ph_trap`, and `subtle_mismatch`) so learners must detect that bicarbonate is too low for a single respiratory process while the anion gap stays clearly raised.
- `respiratory_acidosis_hagma` now spans chronic obvious mismatches, an acute respiratory failure + HAGMA variant, and a subtle near-miss compensation variant while remaining one Master mixed-disorder archetype.
- In those respiratory archetypes, variation bands adjust severity while preserving the same disorder pattern, compensation logic, and beginner question flow.
- Respiratory generators still compute anion gap through the shared `calc_anion_gap()` helper in `generator/physiology.py`. This keeps the schema and answer-key structure consistent across archetypes, even when anion-gap reasoning is not required at lower levels.

Current live difficulty assignment in the generated dataset:
- Beginner: `opioid_toxicity`, `panic_hyperventilation`, `simple_metabolic_alkalosis`, `simple_nagma`, `simple_respiratory_acidosis`, `simple_respiratory_alkalosis`
- Intermediate: `acute_copd_exacerbation`, `copd_chronic_retainer`, `diuretic_metabolic_alkalosis`, `sepsis_respiratory_alkalosis`, `vomiting_metabolic_alkalosis`
- Advanced: `alcoholic_ketoacidosis`, `diarrhoea_nagma`, `dka`, `lactic_acidosis`, `starvation_ketosis`, `toxic_alcohol`, `uraemia`
- Master: `dka_vomiting`, `mixed_hagma_metabolic_alkalosis`, `respiratory_acidosis_hagma`, `respiratory_alkalosis_hagma`, `salicylate_toxicity`

At present, each archetype maps to exactly one difficulty level in `docs/abg_cases.json`; no archetype currently spans multiple difficulty tiers.

## Current Case Pool Size

Each archetype typically produces multiple cases rather than a single fixed case.

Current generation configuration in the live dataset:
- 8 cases generated per archetype.

Estimated case pool size:

Metabolic archetypes:
- `simple_nagma`
- `simple_metabolic_alkalosis`
- `dka`
- `alcoholic_ketoacidosis`
- `starvation_ketosis`
- `toxic_alcohol`
- `vomiting_metabolic_alkalosis`
- `diuretic_metabolic_alkalosis`
- `diarrhoea_nagma`
- `lactic_acidosis`
- `uraemia`

Respiratory archetypes:
- `panic_hyperventilation`
- `opioid_toxicity`
- `copd_chronic_retainer`
- `acute_copd_exacerbation`
- `sepsis_respiratory_alkalosis`
- `simple_respiratory_alkalosis`
- `simple_respiratory_acidosis`

Mixed archetypes:
- `salicylate_toxicity`
- `dka_vomiting`
- `mixed_hagma_metabolic_alkalosis`
- `respiratory_alkalosis_hagma`
- `respiratory_acidosis_hagma`

Current archetype count:
- Metabolic: 11
- Respiratory: 7
- Mixed: 5

Total archetypes: 23

Current generated dataset size:
- 8 cases per archetype
- 184 cases total

Variation bands increase effective replay diversity beyond the raw archetype count without requiring a larger archetype library.

These numbers may change as new archetypes, generators, or variation bands are added.

## 7. Difficulty System

The platform uses progression levels tied to reasoning complexity.

The XP progression table is now explicitly defined through Level 24. The progression engine uses the absence of a Level 25 requirement as the cap/terminal threshold for computing advancement beyond the current late-game range.

Levels:
- Level 1: Beginner
- Level 2: Intermediate
- Level 3: Advanced
- Level 4: Master

Important note:
- In code, the level-4 difficulty label is `"master"` in `progression.py` and in the generated progression metadata.
- In the UI, the highest tier is also presented as Master.
- Master cases unlock at Level 20.
- Level 25 is the current reachable cap under the existing progression engine because XP requirements are defined through Level 24.
- This tier contains the highest interpretation complexity, including mixed-disorder reasoning where applicable.

Difficulty controls:
- Question flow depth.
- Disorder complexity.
- Whether mixed disorders are present.
- Skills tested.
- Base XP and unlock progression.

Typical mapping:
- Level 1: simple single-process pattern recognition.
- Level 2: single-process cases with compensation reasoning.
- Level 3: more complete metabolic reasoning including anion gap.
- Level 4: mixed-disorder interpretation and the highest overall reasoning complexity.

Current progression pacing intent:
- Early levels are front-loaded so beginners can make visible progress quickly.
- Beginner is designed to act as the initial hook, especially for free users limited to beginner difficulty and 5 cases per day.
- Intermediate and especially Advanced are intentionally longer progression bands.
- Master is an aspirational unlock at Level 20 and remains the highest difficulty tier through the current Level 25 cap.
- This pacing supports the freemium model: quick early reward, longer mid-game progression, and a meaningful late-game Master grind without adding a new tier.

## 8. Frontend Architecture

The frontend is a static site located in `docs/`.

Key files:
- `docs/index.html`
- `docs/app.js`
- `docs/styles.css`

Case data is loaded from:
- `docs/abg_cases.json`

Frontend model:
- `index.html` provides the static shell.
- `app.js` fetches the generated JSON, manages SPA view state, renders cases dynamically, and handles scoring, timing, and case navigation.
- `styles.css` controls layout and styling.

Current frontend shell and UI behavior:
- The HTML shell now exposes six SPA views: dashboard, practice, results, learn, leaderboard, and profile.
- The Learn renderer still exists in `docs/app.js`, but the primary nav currently shows Learn as a disabled placeholder in `docs/index.html`.
- The header includes sticky navigation plus streak, level, and XP progress chrome.
- The dashboard is card-based and now emphasizes level progress, recent badges, and difficulty unlock cards.
- Practice mode includes a first-run intro modal, difficulty selector, step-progress pills, and richer value rendering.
- Results now include a stronger summary state card, answer review list, values recap, and a "Provide Feedback" action that opens a prefilled Google Form for the completed case.
- Leaderboard and profile are distinct frontend views rendered in the browser from local/mock state rather than a live backend service.
- The footer now includes a global feedback link plus a reset-progress control that clears local storage and reloads the app.
- `index.html` also includes Google Analytics (`gtag`) and Microsoft Clarity instrumentation.

Data flow:
1. Python generation writes `abg_cases.json`.
2. The browser fetches `abg_cases.json`.
3. The app selects cases and walks the learner through the case's `questions_flow`.
4. The frontend reads `answer_key` and progression metadata to score and display results.

This means the web app is fully JSON-driven. Most educational logic is encoded in the generated case payload rather than hard-coded separately for each diagnosis.

In practical frontend terms, `docs/app.js` is primarily responsible for:
- session state
- local persistence and persistence-boundary resets
- XP and level progression display
- timing state
- case selection and navigation
- rendering dashboard, practice, results, learn, leaderboard, and profile views
- practice intro onboarding flow
- per-case feedback URL generation
- analytics event tracking for page views, case starts, answers, completions, and feedback opens

Launch-mode access control is also enforced in `docs/app.js` through centralized helpers rather than scattered per-view conditions. That frontend access layer is responsible for:
- learn-mode gating
- difficulty access by subscription tier
- free-tier daily case limits
- testing-mode bypass behavior

The educational reasoning itself still lives mainly in the generated payload:
- `questions_flow` defines the learner's reasoning path
- `answer_key` defines correctness and explanatory interpretation
- progression metadata defines difficulty labels, unlocks, and XP behavior

Current practice rendering details that matter architecturally:
- The practice metrics panel is schema-driven and conditionally shows reference ranges for lower-difficulty cases.
- Abnormal-value highlighting is also difficulty-sensitive and currently shown through Advanced.
- The frontend supports optional display of `pao2_mmHg`, `base_excess_mEqL`, `k_mmolL`, `glucose_mmolL`, and lactate in addition to pH, PaCO2, HCO3, sodium, and chloride.
- `glucose_mmolL` is hidden at Beginner/Intermediate, shown at Advanced only when present, and always shown at Master because the generator guarantees a glucose value there.
- Advanced cases keep abnormal-value highlighting on by default but now expose an optional practice-only reference-range toggle; Master keeps ranges off.
- Frontend lactate rendering is transition-safe and reads both the canonical `inputs.other.lactate_mmolL` path and the legacy top-level `inputs.lactate_mmolL` path.
- Final-diagnosis distractors are de-duplicated twice: once in generator helpers and again in browser-side option assembly to avoid near-identical answer choices.
- Practice intro state is persisted separately from user progression state through `practiceIntroSeen` in local storage.
- Seen-case tracking is also persisted separately from progression state as per-difficulty `case_id` lists in local storage.
- Case selection is priority-based rather than simple random repeat avoidance: exact difficulty first, then unseen cases first, then recent-archetype avoidance as a secondary filter, with repeats allowed only after unseen-pool exhaustion.

## Testing Mode

The project now includes an explicit generated testing override intended for feedback collection only.

Configuration:
- `TESTING_MODE = True` in `generator/config.py`
- `TESTING_XP_MULTIPLIER = 5` in `generator/config.py`

How it works:
- `generator/progression.py` includes these values in `progression_config`
- `docs/app.js` reads them from the generated JSON payload
- launch mode remains the default behavior

When `TESTING_MODE` is enabled:
- paywall and difficulty access restrictions are bypassed
- learn mode is available
- the daily free-case limit is bypassed
- all difficulties are immediately accessible
- XP is multiplied using the configured testing multiplier so testers can reach higher tiers quickly

Current frontend copy also reflects this testing posture explicitly through the practice intro modal, which tells testers that all difficulties are unlocked and that the build is running with a 5x XP multiplier.

When `TESTING_MODE` is disabled:
- launch behavior is restored
- free tier is restricted to beginner access and the daily case limit
- premium uses progression-based difficulty access with unlimited cases
- exam prep bypasses difficulty locks while still keeping XP/progression active

To keep switching predictable, the frontend treats testing mode as a persistence boundary. If the generated testing-mode flag changes between runs, the saved local user state is reset so stale tester unlocks do not silently carry into launch mode.

## 9. Design Principles

When creating or modifying archetypes, the system generally follows these rules:

- Numbers must drive diagnosis.
- Stems should support context but not give away the answer.
- Physiology must be internally consistent.
- Compensation should follow accepted formulas.
- Each archetype should represent a distinct acid-base pattern.
- Validation should be able to detect broken or implausible cases.
- Difficulty should reflect reasoning burden, not just rarer diagnoses.
- The same structural schema should be reused across cases so the frontend remains simple.

## 10. How To Add a New Archetype

Standard implementation path:

1. Create a generator function in the appropriate module:
   - `generator/generators/metabolic.py`
   - `generator/generators/respiratory.py`
   - `generator/generators/mixed.py`
2. Generate physiologic values consistent with the intended disorder.
3. Compute expected compensation.
4. Compute anion gap when relevant.
5. Create a concise explanation string.
6. Attach the appropriate question flow for the intended difficulty.
7. Return the final case via `build_case()`.
8. Add the generator to the central registry in `generator/generate_cases.py`.
9. Export it via `generator/generators/__init__.py` if needed.
10. Update tests and validation rules if the new archetype introduces new expectations.

Implementation guidance:
- Reuse helpers from `physiology.py`, `question_flow.py`, and `generators/common.py`.
- Prefer stems that cue the right context without making the answer trivial.
- Keep answer-key fields aligned with the shared schema used by the frontend.

## Generator Design Contract

When proposing or implementing changes in this project, external AI tools should follow these rules:

1. Preserve the core architecture
- Keep physiology logic in `generator/physiology.py`
- Keep question flow logic in `generator/question_flow.py`
- Keep archetype-specific case builders in:
  - `generator/generators/metabolic.py`
  - `generator/generators/respiratory.py`
  - `generator/generators/mixed.py`
- Keep shared case-building helpers in `generator/generators/common.py`
- Keep progression logic in `generator/progression.py`
- Keep validation rules in `generator/validation.py`

2. Archetypes should be physiology-first
- Archetypes represent acid-base patterns before diagnoses
- New cases should be differentiated by physiology, not just different story text
- The numbers should drive the interpretation more than the clinical stem

3. Generated cases must be internally coherent
- Use physiology helper functions instead of inventing disconnected values
- Compensation should match accepted formulas within the project's tolerance
- Anion gap should be derived from sodium, chloride, and bicarbonate
- pH should be calculated from HCO3 and PaCO2 using project helpers

4. Reuse the shared case schema
- All cases should return through `build_case()`
- Inputs should be created with `build_inputs()`
- Answers should be created with `build_answer_key()`
- Do not invent parallel schemas unless the whole project is intentionally being redesigned

5. Difficulty should reflect reasoning burden
- Level 1: simple single-process pattern recognition
- Level 2: compensation reasoning added
- Level 3: anion gap reasoning added
- Level 4: mixed-disorder interpretation added
- Do not assign higher levels just because a diagnosis is rare; complexity should come from interpretation

6. Frontend logic should stay data-driven
- Prefer encoding educational logic in the generated case payload
- Avoid pushing diagnosis-specific hardcoding into `docs/app.js`
- Frontend changes should usually support schema-driven rendering, not one-off case logic

7. Stems should support but not give away the answer
- Stems should be clinically plausible
- They should not be so specific that the diagnosis is obvious without reading the numbers
- Favor variation in wording and severity while preserving the same physiological pattern

8. New answer-key fields require coordinated updates
- If a new case requires additional answer fields, update:
  - documentation
  - validation
  - tests
  - any frontend logic that depends on the field
- Keep `AI_PROJECT_CONTEXT.md` accurate whenever schema changes

9. Prefer variation bands before unlimited new archetypes
- If a pattern already exists but feels repetitive, first consider adding variation bands
- Add new archetypes when they introduce a genuinely distinct acid-base pattern

10. Keep documentation aligned with code
- `AI_PROJECT_CONTEXT.md` should reflect actual implemented architecture, not aspirational features
- If new archetypes are added, update the archetype library and case pool summary
- If schema changes, update the case data schema section

External AI tools should treat this contract as the default rule set unless the user explicitly requests a broader redesign.

## 11. Future Extensions

Plausible future expansions include:

- Osmolar gap cases.
- Additional toxicology cases.
- More mixed-disorder generators.
- Adaptive difficulty selection.
- User analytics and performance tracking.
- Larger archetype libraries.
- More advanced respiratory compensation variants.
- Additional frontend filtering or study modes.
- AI explanations 
- Stewart Analysis
- Global leaderboards
- badges/achievements with founder badges

## Summary For External AI Tools

If only this file is available, the most important architectural facts are:

- This is a Python-to-JSON case generator feeding a static browser app.
- The generator is modular: physiology helpers, question-flow builders, stem builders, validation, and archetype modules are separated.
- Archetypes are reusable physiological teaching patterns.
- `build_case()` is the common output contract.
- The frontend is mostly a renderer and state machine over generated case data.
- Changes should usually be made in the generator layer first, then registered in `generate_cases.py`, then validated against tests and the JSON output.
