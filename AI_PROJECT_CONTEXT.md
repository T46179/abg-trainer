# AI Project Context: ABG Trainer

Last updated: 2026-03-16

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
  - Stores prompt text, option lists, stem-bank content, XP settings, and difficulty unlock settings.

- `generator/physiology.py`
  - The core physiology/math helper layer.
  - Calculates pH, compensation expectations, anion gap, rounding, and pH status labels.

- `generator/progression.py`
  - Adds progression metadata to each case.
  - Defines difficulty labels, XP rules, unlock thresholds, dashboard/user state, and progression simulations.

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

- `docs/app.js`
  - Frontend logic for loading cases, rendering questions, scoring, timing, and practice flow.

- `docs/styles.css`
  - Frontend presentation layer.

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

Standard case shape:

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
  - Normalizes the `gas`, `electrolytes`, and optional `lactate` input structure.
- `build_answer_key()`
  - Normalizes the answer schema across archetypes.
- `build_case()`
  - Creates the final case object and attaches progression metadata such as difficulty, archetype, skills tested, and case pool.

Architecturally, the important idea is that archetype modules are thin composers. They do not own global app logic. They combine:
- physiology helpers
- stem generation
- question flow
- answer-key construction
- progression metadata

## Case Data Schema

Every generated case object follows a standardized schema used by the frontend. The browser-side app is data-driven and relies on this case structure rather than hard-coded diagnoses or per-case UI logic.

Illustrative case schema:

```text
{
  case_id: string,
  title: string,
  category: string,
  learning_objective: string,
  tags: string[],

  clinical_stem: string,

  inputs: {
    gas: {
      ph: number,
      paco2: number,
      hco3: number
    },
    electrolytes: {
      na: number,
      cl: number
    },
    lactate?: number
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

  explanation: string,
  timing: object,
  level: number,
  archetype: string
}
```

Key field roles:
- `inputs`
  - Raw ABG and electrolyte values used for interpretation.
- `questions_flow`
  - Defines the step-by-step reasoning questions shown to the learner.
- `answer_key`
  - Contains the correct interpretation used by the scoring logic.
- `explanation`
  - Provides the educational explanation shown after completion.
- `level`
  - Determines difficulty.
- `archetype`
  - Identifies the physiological pattern used to generate the case.

In the real generated payload, progression metadata and difficulty labels are also attached, but the schema above captures the most important architecture-level contract external AI tools need to reason about the system.

## 4. Physiology Engine

The key physiology and numeric helpers live in `generator/physiology.py`.

Important functions include:
- `estimate_ph`
- `calculate_ph_from_hco3_paco2`
- `winters_expected_paco2`
- `metabolic_alkalosis_expected_paco2`
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

Typical difficulty progression:
- Beginner: pH status, primary disorder, then diagnosis.
- Intermediate: adds compensation.
- Advanced: adds anion gap.
- Expert/master: can add extra mixed-disorder interpretation such as `additional_metabolic_process`.

## 6. Current Archetype Library

Archetypes are organized by module. They represent acid-base patterns first, and only secondarily the clinical scenario that explains them.

### Metabolic

- `dka`
- `vomiting_metabolic_alkalosis`
- `diuretic_metabolic_alkalosis`
- `diarrhoea_nagma`
- `lactic_acidosis`
- `uraemia`

### Respiratory

- `panic_hyperventilation`
- `opioid_toxicity`
- `copd_chronic_retainer`
- `acute_copd_exacerbation`
- `sepsis_respiratory_alkalosis`
- `simple_respiratory_alkalosis`
- `simple_respiratory_acidosis`

### Mixed

- `salicylate_toxicity`
- `dka_vomiting`

Design interpretation:
- An archetype is not just a diagnosis label.
- It is a reusable physiological pattern with a consistent compensation profile, diagnostic explanation, and question structure.
- Some archetypes now include mild/moderate/severe or subtle/moderate/severe variation bands to improve replay variety without changing the underlying acid-base pattern.
- This now includes `simple_respiratory_alkalosis` and `simple_respiratory_acidosis`, where bands vary severity and subtlety while preserving the same beginner single-process respiratory pattern.
- Respiratory generators also standardize anion gap calculation through the shared physiology helper, and the severe bands in the simple respiratory archetypes allow slightly broader acute-compensation variability for replay realism without changing the intended disorder pattern.

## Current Case Pool Size

Each archetype typically produces multiple cases rather than a single fixed case.

Typical generation configuration:
- Approximately 5 cases generated per archetype.

Estimated case pool size:

Metabolic archetypes:
- `dka`
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

Current archetype count:
- Metabolic: 6
- Respiratory: 7
- Mixed: 2

Total archetypes: 15

Typical generated dataset size:
- ~5 cases per archetype
- ~75 cases total

These numbers may change as new archetypes, generators, or variation bands are added.

## 7. Difficulty System

The platform uses progression levels tied to reasoning complexity.

Levels:
- Level 1: beginner
- Level 2: intermediate
- Level 3: advanced
- Level 4: expert/master

Important note:
- In code, the level-4 difficulty label is currently `"master"` in `progression.py`.
- Conceptually, it serves the expert/master tier.

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
- Level 4: mixed-disorder interpretation and more complex reasoning.

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
- `app.js` fetches the generated JSON, manages session state, renders the case/question/result cards, and handles scoring and timing.
- `styles.css` controls layout and styling.

Data flow:
1. Python generation writes `abg_cases.json`.
2. The browser fetches `abg_cases.json`.
3. The app selects cases and walks the learner through the case's `questions_flow`.
4. The frontend reads `answer_key` and progression metadata to score and display results.

This means the web app is data-driven. Most educational logic is encoded in the generated case payload rather than hard-coded separately for each diagnosis.

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

## Summary For External AI Tools

If only this file is available, the most important architectural facts are:

- This is a Python-to-JSON case generator feeding a static browser app.
- The generator is modular: physiology helpers, question-flow builders, stem builders, validation, and archetype modules are separated.
- Archetypes are reusable physiological teaching patterns.
- `build_case()` is the common output contract.
- The frontend is mostly a renderer and state machine over generated case data.
- Changes should usually be made in the generator layer first, then registered in `generate_cases.py`, then validated against tests and the JSON output.
