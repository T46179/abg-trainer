/** ---- CONFIG (Option A time bonus; whole-case; timer hidden by default) ---- **/
const SCORING = {
  perStepCorrect: 10,
  perfectCaseBonus: 30,
  timeBonusTiers: [
    { maxSeconds: 30, bonus: 20 },
    { maxSeconds: 45, bonus: 15 },
    { maxSeconds: 60, bonus: 10 },
    { maxSeconds: 90, bonus: 5 },
    { maxSeconds: Infinity, bonus: 0 },
  ]
};

let allCases = [];
let currentCase = null;
let currentStepIndex = 0;
let stepResults = []; // {key, correct, chosen, correctAnswer}
let caseStartMs = null;
let timerInterval = null;

let sessionScore = 0;
let sessionCasesCompleted = 0;

let progressionConfig = null;
let dashboardState = null;
let userState = null;

let recentArchetypes = [];
const RECENT_ARCHETYPE_LIMIT = 2;

/** Utility */
function pickRandom(arr) {
  return arr[Math.floor(Math.random() * arr.length)];
}
function calcAnionGap(na, cl, hco3) {
  return na - (cl + hco3);
}
function getTimeBonus(seconds) {
  for (const t of SCORING.timeBonusTiers) {
    if (seconds <= t.maxSeconds) return t.bonus;
  }
  return 0;
}
function nowMs() { return Date.now(); }

function getMode() {
  return document.getElementById("modeSelect").value; // chill | speed
}
function updateModeUI() {
  const mode = getMode();
  const pill = document.getElementById("modePill");
  const timer = document.getElementById("timerDisplay");
  if (mode === "speed") {
    pill.textContent = "Speedrun mode";
    timer.style.display = "block";
  } else {
    pill.textContent = "Chill mode";
    timer.style.display = "none";
  }
}

function prettyStepLabel(stepKey) {
  const labels = {
    ph_status: "pH",
    primary_disorder: "Primary disorder",
    compensation: "Compensation",
    anion_gap: "Anion gap",
    additional_metabolic_process: "Additional metabolic disorder",
    final_diagnosis: "Diagnosis"
  };
  return labels[stepKey] ?? stepKey;
}


/** Load JSON */
async function loadCases() {
  const res = await fetch("./abg_cases.json", { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to load JSON: ${res.status}`);

  const data = await res.json();

  // Legacy format support (old JSON with only cases)
  if (Array.isArray(data)) {
    return {
      cases: data,
      progressionConfig: null,
      dashboardState: null,
      userState: null
    };
  }

  // New structured format
  if (data && Array.isArray(data.cases)) {
    return {
      cases: data.cases,
      progressionConfig: data.progression_config ?? null,
      dashboardState: data.dashboard_state ?? null,
      userState: data.default_user_state ?? null
    };
  }

  throw new Error("JSON format not recognized.");
}

/** Render case header */
function renderCaseCard(c) {
  const gas = c.inputs?.gas ?? {};
  const ely = c.inputs?.electrolytes ?? {};
  const lact = c.inputs?.lactate_mmolL;

  const sessionText = `Session: ${sessionCasesCompleted} cases • Score: ${sessionScore}`;

  function isAbnormal(value, low, high) {
    if (value == null) return false;
    return value < low || value > high;
  }

  function formatValue(value, decimals = 1) {
    if (value == null) return "—";
    return Number(value).toFixed(decimals);
  }

  function resultRow(label, rangeText, valueText, abnormal) {
    return `
      <div class="abg-row">
        <div class="abg-row-left">
          <div class="abg-label">${label}</div>
          <div class="abg-range">${rangeText}</div>
        </div>
        <div class="abg-value ${abnormal ? "abnormal" : ""}">
          ${valueText}
        </div>
      </div>
    `;
  }

  const ph = gas.ph;
  const paco2 = gas.paco2_mmHg;
  const hco3 = gas.hco3_mmolL;
  const pao2 = gas.pao2_mmHg;
  const baseExcess = gas.base_excess_mEqL;

  document.getElementById("caseCard").innerHTML = `
    <div class="practice-header">
      <div>
        <div class="practice-title">Practice Mode</div>
        <div class="practice-subtitle">${sessionText}</div>
      </div>
    </div>

    <div class="card-section">
      <div class="section-title">Clinical Scenario</div>
      <p class="scenario-text">${c.clinical_stem ?? ""}</p>
    </div>

    <div class="card-section">
      <div class="section-title">ABG Results</div>

      <div class="abg-panel">
        ${resultRow(
          "pH",
          "Normal: 7.35 - 7.45",
          formatValue(ph, 2),
          isAbnormal(ph, 7.35, 7.45)
        )}

        ${resultRow(
          "PaCO₂",
          "Normal: 35 - 45 mmHg",
          `${formatValue(paco2, 1)} mmHg`,
          isAbnormal(paco2, 35, 45)
        )}

        ${resultRow(
          "HCO₃⁻",
          "Normal: 22 - 26 mmol/L",
          `${formatValue(hco3, 1)} mmol/L`,
          isAbnormal(hco3, 22, 26)
        )}

        ${pao2 != null ? resultRow(
          "PaO₂",
          "Normal: 80 - 100 mmHg",
          `${formatValue(pao2, 1)} mmHg`,
          isAbnormal(pao2, 80, 100)
        ) : ""}

        ${baseExcess != null ? resultRow(
          "Base Excess",
          "Normal: -2 to +2 mEq/L",
          `${formatValue(baseExcess, 1)} mEq/L`,
          isAbnormal(baseExcess, -2, 2)
        ) : ""}

        ${ely.na_mmolL != null ? resultRow(
          "Na⁺",
          "Normal: 135 - 145 mmol/L",
          `${formatValue(ely.na_mmolL, 0)} mmol/L`,
          isAbnormal(ely.na_mmolL, 135, 145)
        ) : ""}

        ${ely.cl_mmolL != null ? resultRow(
          "Cl⁻",
          "Normal: 98 - 106 mmol/L",
          `${formatValue(ely.cl_mmolL, 0)} mmol/L`,
          isAbnormal(ely.cl_mmolL, 98, 106)
        ) : ""}

        ${lact != null ? resultRow(
          "Lactate",
          "Normal: < 2.0 mmol/L",
          `${formatValue(lact, 1)} mmol/L`,
          lact >= 2.0
        ) : ""}
      </div>
    </div>
  `;
}


/** Render current step question */
function renderStep() {
  const qaCard = document.getElementById("qaCard");
  const resultCard = document.getElementById("resultCard");
  resultCard.style.display = "none";
  qaCard.style.display = "block";

  const flow = currentCase.questions_flow;
  const step = flow[currentStepIndex];

	qaCard.innerHTML = `
	  <h3>${step.label ?? step.prompt ?? `Question ${currentStepIndex + 1}`}</h3>
	  <div class="step-meta">Question ${currentStepIndex + 1} of ${flow.length}</div>
	  <p><b>${step.prompt}</b></p>
	  <div id="options" class="option-grid"></div>
	`;

  const optionsDiv = document.getElementById("options");

  step.options.forEach(opt => {
    const btn = document.createElement("button");
    btn.textContent = opt;
    btn.className = "option-btn";

    btn.onclick = () => {
      const buttons = optionsDiv.querySelectorAll("button");
      buttons.forEach(b => {
        b.disabled = true;
        b.classList.remove("selected");
      });

      btn.classList.add("selected");
      handleAnswer(step.key, opt);
    };

    optionsDiv.appendChild(btn);
  });

  document.getElementById("nextBtn").disabled = true;
}


/** Check answer against answer_key */
function isCorrect(stepKey, chosen) {
  const ak = currentCase.answer_key ?? {};

  if (stepKey === "anion_gap") {
    // Accept "Raised"/"Normal" based on computed AG threshold
    const gas = currentCase.inputs?.gas ?? {};
    const ely = currentCase.inputs?.electrolytes ?? {};
    const ag = calcAnionGap(ely.na_mmolL, ely.cl_mmolL, gas.hco3_mmolL);
    const category = ag > 16 ? "Raised" : "Normal";
    return chosen === category;
  }

  return chosen === ak[stepKey];
}

function correctAnswerFor(stepKey) {
  const ak = currentCase.answer_key ?? {};

  if (stepKey === "anion_gap") {
    const gas = currentCase.inputs?.gas ?? {};
    const ely = currentCase.inputs?.electrolytes ?? {};
    const ag = calcAnionGap(ely.na_mmolL, ely.cl_mmolL, gas.hco3_mmolL);
    return (ag > 16 ? "Raised" : "Normal");
  }

  return ak[stepKey];
}

function handleAnswer(stepKey, chosen) {
  const correct = isCorrect(stepKey, chosen);
  const correctAns = correctAnswerFor(stepKey);

  stepResults.push({ key: stepKey, correct, chosen, correctAnswer: correctAns });

  // Show immediate feedback, then enable “Next case” only if finished, otherwise proceed
  const qaCard = document.getElementById("qaCard");
  const resultCard = document.getElementById("resultCard");

  qaCard.style.display = "none";
  resultCard.style.display = "block";

let extraFeedback = "";

if (stepKey === "anion_gap" && (currentCase.difficulty_level ?? 1) >= 3) {
  const gas = currentCase.inputs?.gas ?? {};
  const ely = currentCase.inputs?.electrolytes ?? {};

  if (
    ely.na_mmolL != null &&
    ely.cl_mmolL != null &&
    gas.hco3_mmolL != null
  ) {
    const ag = ely.na_mmolL - (ely.cl_mmolL + gas.hco3_mmolL);

    extraFeedback = `
      <p><b>Anion gap:</b> ${ag.toFixed(1)}</p>
      <p class="muted">Reference range: 8–12 mmol/L</p>
    `;
  }
}


resultCard.innerHTML = `
  <div class="result-box ${correct ? "result-correct" : "result-incorrect"}">

    <div class="result-title">
      ${correct ? "Correct ✓" : "Incorrect"}
    </div>

    <div class="result-details">
      <p><b>Your answer:</b> ${chosen}</p>
      <p><b>Correct answer:</b> ${correctAns}</p>
${extraFeedback}
    </div>

    <button id="continueBtn">
      ${currentStepIndex < currentCase.questions_flow.length - 1 ? "Continue" : "Finish case"}
    </button>

  </div>
`;


  document.getElementById("continueBtn").onclick = () => {
    if (currentStepIndex < currentCase.questions_flow.length - 1) {
      currentStepIndex++;
      renderStep();
    } else {
      finishCase();
    }
  };
}

function finishCase() {
  stopTimer();

  const elapsedSeconds = (nowMs() - caseStartMs) / 1000;
  const timeBonus = getTimeBonus(elapsedSeconds);

  const correctSteps = stepResults.filter(s => s.correct).length;
  const baseScore = correctSteps * SCORING.perStepCorrect;
  const perfect = (correctSteps === currentCase.questions_flow.length);
  const perfectBonus = perfect ? SCORING.perfectCaseBonus : 0;

  const caseScore = baseScore + perfectBonus + timeBonus;

  sessionScore += caseScore;
  sessionCasesCompleted += 1;

  const xpResult = applyCaseXp(
    currentCase.difficulty_level ?? 1,
    perfect,
    elapsedSeconds
  );

  const resultCard = document.getElementById("resultCard");
  const qaCard = document.getElementById("qaCard");
  qaCard.style.display = "none";
  resultCard.style.display = "block";

  const breakdownRows = stepResults.map(s =>
    `<li><b>${prettyStepLabel(s.key)}</b>: ${s.correct ? "✅" : "❌"} (you: ${s.chosen} | correct: ${s.correctAnswer})</li>`
  ).join("");

const xpBlock = xpResult ? `
  <hr>
  <h4>XP earned</h4>
  <p><b>+${xpResult.totalXpAward} XP</b></p>
  ${
    xpResult.leveledUp
      ? `<p><b>Level up!</b></p>`
      : ""
  }
  ${
    xpResult.difficultyUnlocked
      ? `<p><b>New difficulty unlocked:</b> ${getDifficultyLabel(xpResult.newUnlockedDifficulty)}</p>`
      : ""
  }
` : "";

  resultCard.innerHTML = `
    <h3>Case complete</h3>

    ${xpBlock}

    <p><b>Explanation</b><br/>${currentCase.explanation ?? ""}</p>

    <details>
      <summary>Show step breakdown</summary>
      <ul>${breakdownRows}</ul>
    </details>

  `;

  document.getElementById("nextBtn").disabled = false;
}


function startTimer() {
  caseStartMs = nowMs();
  const timerEl = document.getElementById("timerDisplay");

  timerInterval = setInterval(() => {
    const elapsed = (nowMs() - caseStartMs) / 1000;
    if (getMode() === "speed") {
      timerEl.textContent = `Time: ${elapsed.toFixed(1)}s`;
    }
  }, 100);
}

function stopTimer() {
  if (timerInterval) clearInterval(timerInterval);
  timerInterval = null;
}

/** Load next random case */
function loadNextCase() {
  stepResults = [];
  currentStepIndex = 0;

  const subscriptionTier =
    dashboardState?.user?.subscription_tier ??
    userState?.subscription_tier ??
    "free";

  const maxDifficulty =
    subscriptionTier === "exam_prep"
      ? 4
      : (userState?.unlocked_difficulty ?? 1);

  let availableCases = allCases.filter(
    c => (c.difficulty_level ?? 1) <= maxDifficulty
  );

  let filteredCases = availableCases.filter(
    c => !recentArchetypes.includes(c.archetype)
  );

  if (!filteredCases.length) {
    filteredCases = availableCases;
  }

  currentCase = pickRandom(filteredCases);

  if (currentCase?.archetype) {
    recentArchetypes.push(currentCase.archetype);
    if (recentArchetypes.length > RECENT_ARCHETYPE_LIMIT) {
      recentArchetypes.shift();
    }
  }

  renderCaseCard(currentCase);
  renderStep();
  stopTimer();
  startTimer();

  document.getElementById("nextBtn").disabled = true;
}


/** UI wiring */
document.getElementById("nextBtn").onclick = loadNextCase;
document.getElementById("resetBtn").onclick = () => {
  sessionScore = 0;
  sessionCasesCompleted = 0;
  if (currentCase) renderCaseCard(currentCase);
};
document.getElementById("modeSelect").onchange = updateModeUI;


function renderProgression() {
  if (!userState) return;

  const level = userState.level;
  const xpInto = userState.level_progress?.xp_into_level ?? 0;
  const xpNeeded = userState.level_progress?.xp_needed_for_next_level;
  const unlockedLabel = userState.unlocked_difficulty_label ?? "Beginner";

  const el = document.getElementById("progressionDebug");
  if (!el) return;

  el.innerHTML = `
    <strong>Level ${level}</strong><br>
    XP: ${xpNeeded == null ? `${userState.total_xp} total` : `${xpInto} / ${xpNeeded}`}<br>
    Unlocked: ${unlockedLabel}
  `;
}


function getBaseXpForDifficulty(difficultyLevel) {
  if (!progressionConfig?.base_xp_by_difficulty) return 0;
  return progressionConfig.base_xp_by_difficulty[difficultyLevel] ?? 0;
}

function getPerfectXpBonus(difficultyLevel, perfectCase) {
  if (!perfectCase) return 0;

  const baseXp = getBaseXpForDifficulty(difficultyLevel);
  const percent = progressionConfig?.perfect_case_bonus_percent ?? 0;
  return Math.round(baseXp * percent);
}

function getSpeedXpBonus(secondsTaken) {
  const tiers = progressionConfig?.speed_bonus_tiers ?? [];
  for (const tier of tiers) {
    if (secondsTaken <= tier.max_seconds) return tier.bonus;
  }
  return 0;
}

function getStreakXpBonus(streakDays) {
  const tiers = progressionConfig?.streak_bonus_tiers ?? [];
  let bonus = 0;

  for (const tier of tiers) {
    if (streakDays >= tier.min_days) {
      bonus = tier.bonus;
    }
  }

  return bonus;
}

function getXpRequiredForLevel(level) {
  return progressionConfig?.xp_required_per_level?.[level] ?? null;
}

function getLevelFromTotalXp(totalXp) {
  let level = 1;

  while (true) {
    const xpNeeded = getXpRequiredForLevel(level);
    if (xpNeeded == null) return level;

    let thresholdForNext = 0;
    for (let l = 1; l <= level; l++) {
      thresholdForNext += progressionConfig?.xp_required_per_level?.[l] ?? 0;
    }

    if (totalXp < thresholdForNext) return level;
    level++;
  }
}

function getDifficultyLabel(difficultyLevel) {
  return progressionConfig?.difficulty_labels?.[difficultyLevel] ?? `Difficulty ${difficultyLevel}`;
}

function getUnlockedDifficultyForLevel(level) {
  const unlocks = progressionConfig?.difficulty_unlock_levels ?? {};
  let unlocked = 1;

  for (const [difficulty, requiredLevel] of Object.entries(unlocks)) {
    if (level >= requiredLevel) {
      unlocked = Number(difficulty);
    }
  }

  return unlocked;
}

function getLevelProgressFromXp(totalXp) {
  const level = getLevelFromTotalXp(totalXp);

  let currentLevelStartXp = 0;
  for (let l = 1; l < level; l++) {
    currentLevelStartXp += progressionConfig?.xp_required_per_level?.[l] ?? 0;
  }

  const xpNeededForNextLevel = getXpRequiredForLevel(level);

  return {
    level,
    xp_into_level: totalXp - currentLevelStartXp,
    xp_needed_for_next_level: xpNeededForNextLevel,
    current_level_start_xp: currentLevelStartXp,
    next_level_total_xp:
      xpNeededForNextLevel == null ? null : currentLevelStartXp + xpNeededForNextLevel
  };
}

function applyCaseXp(difficultyLevel, perfectCase, secondsTaken) {
  if (!userState || !progressionConfig) return null;

  const baseXp = getBaseXpForDifficulty(difficultyLevel);
  const perfectBonus = getPerfectXpBonus(difficultyLevel, perfectCase);
  const speedBonus = getSpeedXpBonus(secondsTaken);
  const streakBonus = getStreakXpBonus(userState.streak_days ?? 0);

  const totalXpAward = baseXp + perfectBonus + speedBonus + streakBonus;

  const previousTotalXp = userState.total_xp ?? 0;
  const previousLevel = userState.level ?? 1;
  const previousUnlockedDifficulty = userState.unlocked_difficulty ?? 1;

  const newTotalXp = previousTotalXp + totalXpAward;
  const newLevel = getLevelFromTotalXp(newTotalXp);
  const newUnlockedDifficulty = getUnlockedDifficultyForLevel(newLevel);
  const newLevelProgress = getLevelProgressFromXp(newTotalXp);

  userState.total_xp = newTotalXp;
  userState.level = newLevel;
  userState.level_progress = newLevelProgress;
  userState.unlocked_difficulty = newUnlockedDifficulty;
  userState.unlocked_difficulty_label = getDifficultyLabel(newUnlockedDifficulty);
  userState.cases_completed_today = (userState.cases_completed_today ?? 0) + 1;

  if (userState.daily_case_limit != null) {
    userState.cases_remaining_today = Math.max(
      0,
      userState.daily_case_limit - userState.cases_completed_today
    );
  }

  renderProgression();

  return {
    baseXp,
    perfectBonus,
    speedBonus,
    streakBonus,
    totalXpAward,
    previousLevel,
    newLevel,
    leveledUp: newLevel > previousLevel,
    previousUnlockedDifficulty,
    newUnlockedDifficulty,
    difficultyUnlocked: newUnlockedDifficulty > previousUnlockedDifficulty
  };
}

/** Init */
(async function init() {
  updateModeUI();

  try {
    const data = await loadCases();

    allCases = data.cases;
    progressionConfig = data.progressionConfig;
    dashboardState = data.dashboardState;
    userState = data.userState;
	
	renderProgression();

    console.log("allCases =", allCases);
    console.log("firstCase =", allCases[0]);

    if (!Array.isArray(allCases) || !allCases.length) {
      throw new Error("No cases found in JSON.");
    }

    const startBtn = document.getElementById("startBtn");
    console.log("binding startBtn =", startBtn);

    if (startBtn) {
      startBtn.onclick = () => {
        console.log("Start button clicked");

        document.getElementById("startCard").style.display = "none";
        document.getElementById("caseCard").style.display = "block";

        console.log("About to load next case");
        console.log("allCases =", allCases);

        loadNextCase();
      };
    }

  } catch (e) {
    console.error("INIT ERROR:", e);
    document.getElementById("caseCard").innerHTML = `
      <p class="incorrect">Error loading cases.</p>
      <pre>${e.message}</pre>
      <p class="muted">Check that <code>abg_cases.json</code> exists in the same folder as the live site files.</p>
    `;
  }
})();

