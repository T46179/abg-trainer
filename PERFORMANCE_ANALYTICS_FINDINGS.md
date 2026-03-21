# Performance Analytics Findings

## Current Analytics Already In The App

- Local user-state metrics are already persisted in [docs/app.js](E:/Desktop/abg-trainer/docs/app.js#L7), [docs/app.js](E:/Desktop/abg-trainer/docs/app.js#L399), and [docs/app.js](E:/Desktop/abg-trainer/docs/app.js#L1092). The app currently stores aggregate learning data such as XP, level, cases completed, streak, total correct answers, total answers, and a short `recentResults` buffer.
- The app also keeps one detailed post-case review in `lastCaseSummary` in [docs/app.js](E:/Desktop/abg-trainer/docs/app.js#L1133), which includes the completed case, elapsed time, accuracy, and per-step correctness for the most recent attempt only.
- Product analytics are already wired through Google Analytics in [docs/index.html](E:/Desktop/abg-trainer/docs/index.html#L4) and [docs/app.js](E:/Desktop/abg-trainer/docs/app.js#L92). Current tracked events are `case_started`, `step_answered`, `case_completed`, and `feedback_opened`.
- Session replay and click-behavior analytics are also present through Microsoft Clarity in [docs/index.html](E:/Desktop/abg-trainer/docs/index.html#L18).
- The generated case payload already exposes useful classification metadata such as `archetype`, `difficulty_level`, `case_pool`, `skills_tested`, and `tags` in [generator/progression.py](E:/Desktop/abg-trainer/generator/progression.py#L77) and [docs/abg_cases.json](E:/Desktop/abg-trainer/docs/abg_cases.json).

## What The App Can Support Today

- Overall performance summary:
  cases completed, total accuracy, streak, XP, level, badges
- A recent-performance snapshot:
  the dashboard currently computes performance from the last 20 case outcomes in [docs/app.js](E:/Desktop/abg-trainer/docs/app.js#L1293)
- Detailed review of the most recently completed case:
  per-step correct/incorrect results, elapsed time, explanation, and case values in [docs/app.js](E:/Desktop/abg-trainer/docs/app.js#L1562)

## What Is Missing For A Real Performance Feature

- There is no persistent attempt history beyond aggregate counters and the last completed case.
- The app does not currently retain, per attempt:
  `case_id`, `archetype`, `difficulty`, `skills_tested`, timestamp, elapsed time, or per-step correctness history
- Because of that, the app cannot currently derive:
  weakest archetypes, weakest skills, weakest question steps, trend lines, or targeted remediation lists
- The existing dashboard "Performance" button is not a real analytics destination. In [docs/index.html](E:/Desktop/abg-trainer/docs/index.html#L133) it exists, but in [docs/app.js](E:/Desktop/abg-trainer/docs/app.js#L1819) it just returns to the dashboard.
- Case curation currently selects by difficulty, seen-case history, and recent archetype avoidance in [docs/app.js](E:/Desktop/abg-trainer/docs/app.js#L853), not by user weakness.

## Recommended Direction

- Best near-term option:
  add a client-side attempt-history model in localStorage and derive a performance view from that
- Best long-term option:
  move attempt history to a backend/user-account model if cross-device persistence or richer personalization is required

## Suggested Data Model For A Future Performance View

Store one record per completed case with:

- `case_id`
- `archetype`
- `difficulty_level`
- `skills_tested`
- `timestamp`
- `elapsed_seconds`
- `total_steps`
- `correct_steps`
- `step_results`
- `final_accuracy_percent`

Recommended derived aggregates:

- accuracy by `archetype`
- accuracy by `skills_tested`
- accuracy by question step key:
  `ph_status`, `primary_disorder`, `compensation`, `anion_gap`, `additional_metabolic_process`, `final_diagnosis`
- average completion time by difficulty/archetype
- recently missed cases
- retry queue for weak areas

## Recommended UX Flow

- User clicks `Performance` from the dashboard.
- Performance screen shows:
  overall accuracy, recent trend, average speed, weakest skill, weakest archetype
- Breakdown sections show:
  performance by skill, archetype, difficulty, and question step
- Action cards let the user:
  practice weak skills, retry weak archetypes, or repeat recently missed cases

## Recommendation Summary

- Use existing GA/Clarity for product analytics only.
- Use case metadata already present in the payload as the taxonomy for weakness analysis.
- Add persistent attempt history before building a real performance screen.
- Do not build weakness-driven curation on top of the current `recentResults` boolean buffer; it is too shallow for reliable recommendations.
