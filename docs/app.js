const USER_STATE_STORAGE_KEY = "abgmaster_userState";
const USER_STATE_MODE_STORAGE_KEY = "abgmaster_userState_mode";
const PRACTICE_INTRO_SEEN_STORAGE_KEY = "practiceIntroSeen";

const userState = {
  xp: 0,
  level: 1,
  casesCompleted: 0,
  abandonedCases: 0,
  correctAnswers: 0,
  totalAnswers: 0,
  streak: 0,
  dailyCasesUsed: 0,
  lastCaseDate: null,
  unlockedDifficulties: ["beginner"],
  isPremium: false,
  badges: [],
  recentResults: []
};

const sessionState = {
  currentView: "dashboard",
  currentCase: null,
  currentDifficulty: "beginner",
  currentStepIndex: 0,
  stepResults: [],
  stepOptionOverrides: {},
  caseStartMs: null,
  timedMode: false
};

const appData = {
  cases: [],
  progressionConfig: null,
  dashboardState: null,
  defaultUserState: null,
  loadError: null,
  isLoaded: false,
  recentArchetypes: [],
  timerInterval: null,
  lastCaseSummary: null,
  practiceIntroContinue: null
};

const RECENT_ARCHETYPE_LIMIT = 2;
const VIEW_IDS = [
  "dashboardView",
  "practiceView",
  "resultsView",
  "learnView",
  "leaderboardView",
  "profileView"
];
const VIEW_NAME_TO_ID = {
  dashboard: "dashboardView",
  practice: "practiceView",
  results: "resultsView",
  learn: "learnView",
  leaderboard: "leaderboardView",
  profile: "profileView"
};
const DIFFICULTY_ORDER = ["beginner", "intermediate", "advanced", "master"];

function normalizeSubscriptionTier(value) {
  const normalized = String(value ?? "").toLowerCase();
  if (normalized === "premium" || normalized === "exam_prep") return normalized;
  return "free";
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function setText(id, value) {
  const element = document.getElementById(id);
  if (element) element.textContent = value;
}

function trackEvent(name, params = {}) {
  if (typeof window.gtag === "function") {
    window.gtag("event", name, params);
  }
}

function trackPageView(viewName) {
  if (typeof window.gtag === "function") {
    window.gtag("event", "page_view", {
      page_title: viewName,
      page_path: "/" + viewName
    });
  }
}

function setHtml(id, value) {
  const element = document.getElementById(id);
  if (element) element.innerHTML = value;
}

function setWidth(id, value) {
  const element = document.getElementById(id);
  if (element) element.style.width = value;
}

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function shuffleArray(items) {
  const shuffled = Array.isArray(items) ? [...items] : [];

  for (let index = shuffled.length - 1; index > 0; index -= 1) {
    const swapIndex = Math.floor(Math.random() * (index + 1));
    [shuffled[index], shuffled[swapIndex]] = [shuffled[swapIndex], shuffled[index]];
  }

  return shuffled;
}

function toTitleCase(value) {
  return String(value ?? "")
    .replaceAll("_", " ")
    .replace(/\b\w/g, char => char.toUpperCase());
}

function nowMs() {
  return Date.now();
}

function todayKey() {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function yesterdayKey() {
  const date = new Date();
  date.setDate(date.getDate() - 1);
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function calculateAccuracy(correctAnswers = userState.correctAnswers, totalAnswers = userState.totalAnswers) {
  if (!totalAnswers) return 100;
  return Math.round((correctAnswers / totalAnswers) * 100);
}

function isTestingMode() {
  return Boolean(appData.progressionConfig?.testing_mode);
}

function getConfiguredSubscriptionTier() {
  return normalizeSubscriptionTier(
    appData.dashboardState?.user?.subscription_tier ??
    appData.defaultUserState?.subscription_tier ??
    (userState.isPremium ? "premium" : "free")
  );
}

function getEffectiveSubscriptionTier() {
  if (isTestingMode()) return "testing";
  return getConfiguredSubscriptionTier();
}

function getEffectiveUnlockedDifficulty() {
  const subscriptionTier = getEffectiveSubscriptionTier();

  if (subscriptionTier === "testing" || subscriptionTier === "exam_prep") {
    return DIFFICULTY_ORDER.length;
  }

  if (subscriptionTier === "premium") {
    return getUnlockedDifficultyKeys(userState.level).length;
  }

  return 1;
}

function canAccessLearn() {
  const subscriptionTier = getEffectiveSubscriptionTier();
  return subscriptionTier === "testing" || subscriptionTier === "premium" || subscriptionTier === "exam_prep";
}

function canAccessDifficulty(difficultyLevel) {
  const requestedLevel = typeof difficultyLevel === "number"
    ? difficultyLevel
    : getDifficultyLevel(difficultyLevel);
  return requestedLevel <= getEffectiveUnlockedDifficulty();
}

function getAccessibleDifficultyKeys() {
  return getDifficultyMeta()
    .filter(item => canAccessDifficulty(item.level))
    .map(item => item.key);
}

function normalizeDifficultyKey(difficultyKey = sessionState.currentDifficulty) {
  const normalized = String(difficultyKey ?? "").toLowerCase();
  const requestedLevel = getDifficultyLevel(normalized);

  if (canAccessDifficulty(requestedLevel)) {
    return getDifficultyLabel(requestedLevel);
  }

  const accessible = getAccessibleDifficultyKeys();
  return accessible[accessible.length - 1] ?? "beginner";
}

function canStartNewCase() {
  const subscriptionTier = getEffectiveSubscriptionTier();
  if (subscriptionTier === "testing" || subscriptionTier === "premium" || subscriptionTier === "exam_prep") {
    return true;
  }

  const remaining = getCasesRemainingToday();
  return remaining == null || remaining > 0;
}

function getEffectiveXpMultiplier() {
  if (!isTestingMode()) return 1;
  return Math.max(1, Number(appData.progressionConfig?.testing_xp_multiplier ?? 1));
}

function getPersistenceModeSignature() {
  return JSON.stringify({
    testingMode: isTestingMode()
  });
}

function getDifficultyLabel(level) {
  const configured = appData.progressionConfig?.difficulty_labels?.[level];
  return String(configured ?? DIFFICULTY_ORDER[level - 1] ?? `difficulty_${level}`).toLowerCase();
}

function getDifficultyLevel(label) {
  const normalized = String(label ?? "").toLowerCase();
  for (const [level, mappedLabel] of Object.entries(appData.progressionConfig?.difficulty_labels ?? {})) {
    if (String(mappedLabel).toLowerCase() === normalized) {
      return Number(level);
    }
  }

  const fallbackIndex = DIFFICULTY_ORDER.indexOf(normalized);
  return fallbackIndex >= 0 ? fallbackIndex + 1 : 1;
}

function getDifficultyMeta() {
  return DIFFICULTY_ORDER.map((key, index) => {
    const level = index + 1;
    return {
      key,
      level,
      label: toTitleCase(getDifficultyLabel(level)),
      unlockLevel: Number(appData.progressionConfig?.difficulty_unlock_levels?.[level] ?? level),
      availableCases: appData.cases.filter(caseItem => Number(caseItem.difficulty_level ?? 1) === level).length
    };
  });
}

function getUnlockedDifficultyKeys(level = userState.level) {
  return getDifficultyMeta()
    .filter(item => level >= item.unlockLevel)
    .map(item => item.key);
}

function sanitizeUnlockedDifficulties(difficulties) {
  const normalized = Array.isArray(difficulties)
    ? difficulties.map(item => String(item).toLowerCase()).filter(Boolean)
    : [];

  const allowed = new Set(DIFFICULTY_ORDER);
  const unique = normalized.filter((item, index) => allowed.has(item) && normalized.indexOf(item) === index);
  return unique.length ? unique : ["beginner"];
}

function getXpRequiredForLevel(level) {
  return Number(appData.progressionConfig?.xp_required_per_level?.[level] ?? 0);
}

function getLevelFromXp(xp) {
  const configured = appData.progressionConfig?.xp_required_per_level;
  if (!configured) return Math.max(1, userState.level);

  let runningTotal = 0;
  let currentLevel = 1;

  while (true) {
    const needed = getXpRequiredForLevel(currentLevel);
    if (!needed) return currentLevel;
    if (xp < runningTotal + needed) return currentLevel;
    runningTotal += needed;
    currentLevel += 1;
  }
}

function getLevelProgress() {
  let consumedXp = 0;
  for (let level = 1; level < userState.level; level += 1) {
    consumedXp += getXpRequiredForLevel(level);
  }

  const xpForNextLevel = getXpRequiredForLevel(userState.level);
  const xpIntoLevel = Math.max(0, userState.xp - consumedXp);
  const progressPercent = xpForNextLevel
    ? Math.min(100, Math.round((xpIntoLevel / xpForNextLevel) * 100))
    : 100;

  return {
    xpIntoLevel,
    xpForNextLevel,
    progressPercent
  };
}

function getTimeBonus(secondsTaken) {
  const tiers = appData.progressionConfig?.speed_bonus_tiers ?? [];
  for (const tier of tiers) {
    if (secondsTaken <= Number(tier.max_seconds ?? Number.POSITIVE_INFINITY)) {
      return Number(tier.bonus ?? 0);
    }
  }
  return 0;
}

function getPerfectBonus(difficultyLevel) {
  const base = Number(appData.progressionConfig?.base_xp_by_difficulty?.[difficultyLevel] ?? 0);
  const percentage = Number(appData.progressionConfig?.perfect_case_bonus_percent ?? 0);
  return Math.round(base * percentage);
}

function getBaseXp(difficultyLevel) {
  return Number(appData.progressionConfig?.base_xp_by_difficulty?.[difficultyLevel] ?? 10);
}

function getDailyLimit() {
  return Number(appData.progressionConfig?.free_daily_case_limit ?? 0);
}

function getCasesRemainingToday() {
  const dailyLimit = getDailyLimit();
  const subscriptionTier = getEffectiveSubscriptionTier();
  if (subscriptionTier === "testing" || subscriptionTier === "premium" || subscriptionTier === "exam_prep" || !dailyLimit) {
    return null;
  }
  return Math.max(0, dailyLimit - userState.dailyCasesUsed);
}

function mapDefaultUserState(source) {
  const level = Number(source?.level ?? 1);
  const unlockedFromSource = [];

  if (source?.unlocked_difficulty_label) {
    unlockedFromSource.push(String(source.unlocked_difficulty_label).toLowerCase());
  }

  if (source?.unlocked_difficulty != null) {
    unlockedFromSource.push(getDifficultyLabel(Number(source.unlocked_difficulty)));
  }

  return {
    xp: Number(source?.total_xp ?? source?.xp ?? 0),
    level,
    casesCompleted: Number(appData.dashboardState?.stats?.cases_completed ?? source?.cases_completed ?? 0),
    abandonedCases: Number(source?.abandoned_cases ?? source?.abandonedCases ?? 0),
    correctAnswers: Number(source?.correct_answers ?? 0),
    totalAnswers: Number(source?.total_answers ?? 0),
    streak: Number(source?.streak_days ?? source?.streak ?? 0),
    dailyCasesUsed: Number(source?.cases_completed_today ?? source?.dailyCasesUsed ?? 0),
    lastCaseDate: source?.lastCaseDate ?? null,
    unlockedDifficulties: sanitizeUnlockedDifficulties([
      ...unlockedFromSource,
      ...getUnlockedDifficultyKeys(level)
    ]),
    isPremium: String(source?.subscription_tier ?? "").toLowerCase() === "premium" || Boolean(source?.isPremium),
    badges: Array.isArray(appData.dashboardState?.stats?.recent_badges)
      ? [...appData.dashboardState.stats.recent_badges]
      : Array.isArray(source?.badges)
        ? [...source.badges]
        : []
  };
}

function loadUserState() {
  const fallbackState = mapDefaultUserState(appData.defaultUserState ?? appData.dashboardState?.user ?? {});

  try {
    const expectedModeSignature = getPersistenceModeSignature();
    const persistedModeSignature = window.localStorage.getItem(USER_STATE_MODE_STORAGE_KEY);

    if (persistedModeSignature !== expectedModeSignature) {
      window.localStorage.removeItem(USER_STATE_STORAGE_KEY);
      window.localStorage.setItem(USER_STATE_MODE_STORAGE_KEY, expectedModeSignature);
      return fallbackState;
    }

    const raw = window.localStorage.getItem(USER_STATE_STORAGE_KEY);
    if (!raw) return fallbackState;

    const parsed = JSON.parse(raw);
    return {
      ...fallbackState,
      ...parsed,
      unlockedDifficulties: sanitizeUnlockedDifficulties(parsed?.unlockedDifficulties ?? fallbackState.unlockedDifficulties),
      badges: Array.isArray(parsed?.badges) ? parsed.badges : fallbackState.badges
    };
  } catch (error) {
    console.warn("Failed to load persisted user state.", error);
    return fallbackState;
  }
}

function saveUserState() {
  try {
    window.localStorage.setItem(USER_STATE_MODE_STORAGE_KEY, getPersistenceModeSignature());
    window.localStorage.setItem(USER_STATE_STORAGE_KEY, JSON.stringify(userState));
  } catch (error) {
    console.warn("Failed to save persisted user state.", error);
  }
}

function hasSeenPracticeIntro() {
  try {
    return window.localStorage.getItem(PRACTICE_INTRO_SEEN_STORAGE_KEY) === "true";
  } catch (error) {
    console.warn("Failed to read practice intro state.", error);
    return false;
  }
}

function markPracticeIntroSeen() {
  try {
    window.localStorage.setItem(PRACTICE_INTRO_SEEN_STORAGE_KEY, "true");
  } catch (error) {
    console.warn("Failed to persist practice intro state.", error);
  }
}

function closePracticeIntroModal() {
  const modal = document.getElementById("practiceIntroModal");
  if (!modal) return;

  modal.classList.add("is-hidden");
  modal.setAttribute("aria-hidden", "true");
}

function continueFromPracticeIntro() {
  markPracticeIntroSeen();
  closePracticeIntroModal();

  const onContinue = appData.practiceIntroContinue;
  appData.practiceIntroContinue = null;

  if (typeof onContinue === "function") {
    onContinue();
  }
}

function maybeShowPracticeIntro(onContinue) {
  if (hasSeenPracticeIntro()) {
    onContinue();
    return;
  }

  const modal = document.getElementById("practiceIntroModal");
  if (!modal) {
    onContinue();
    return;
  }

  appData.practiceIntroContinue = onContinue;
  modal.classList.remove("is-hidden");
  modal.setAttribute("aria-hidden", "false");
}

function syncUserStateDerivedFields() {
  userState.level = Math.max(1, getLevelFromXp(userState.xp));
  userState.unlockedDifficulties = sanitizeUnlockedDifficulties([
    ...userState.unlockedDifficulties,
    ...getUnlockedDifficultyKeys(userState.level)
  ]);
}

function addBadgeIfMissing(badge) {
  if (!userState.badges.includes(badge)) {
    userState.badges.push(badge);
  }
}

function evaluateBadges() {
  if (userState.casesCompleted >= 1) addBadgeIfMissing("First case complete");
  if (userState.casesCompleted >= 10) addBadgeIfMissing("Ten-case round");
  if (userState.streak >= 3) addBadgeIfMissing("Three-day streak");
  if (userState.level >= 5) addBadgeIfMissing("Intermediate unlocked");
}

function showView(viewName) {
  const requestedView = VIEW_NAME_TO_ID[viewName] ? viewName : "dashboard";
  const nextView = requestedView === "learn" && !canAccessLearn() ? "dashboard" : requestedView;

  if (nextView === "practice" && (!sessionState.currentCase || sessionState.currentView === "results")) {
    startNewCase(sessionState.currentDifficulty);
    return;
  }

  sessionState.currentView = nextView;
  trackPageView(nextView);

  VIEW_IDS.forEach(viewId => {
    const view = document.getElementById(viewId);
    if (!view) return;
    view.classList.toggle("is-active", viewId === VIEW_NAME_TO_ID[nextView]);
  });
}

function pickRandom(items) {
  if (!items.length) return null;
  return items[Math.floor(Math.random() * items.length)];
}

function calcAnionGap(na, cl, hco3) {
  return na - (cl + hco3);
}

function prettyStepLabel(stepKey) {
  const labels = {
    ph_status: "pH status",
    primary_disorder: "Primary disorder",
    compensation: "Compensation",
    anion_gap: "Anion gap",
    additional_metabolic_process: "Additional process",
    final_diagnosis: "Diagnosis"
  };
  return labels[stepKey] ?? toTitleCase(stepKey);
}

function formatValue(value, decimals = 1) {
  if (value == null || Number.isNaN(Number(value))) return "--";
  return Number(value).toFixed(decimals);
}

function isCorrectAnswer(caseItem, stepKey, chosen) {
  const answerKey = caseItem.answer_key ?? {};

  if (stepKey === "anion_gap") {
    const gas = caseItem.inputs?.gas ?? {};
    const electrolytes = caseItem.inputs?.electrolytes ?? {};
    const gap = calcAnionGap(
      Number(electrolytes.na_mmolL),
      Number(electrolytes.cl_mmolL),
      Number(gas.hco3_mmolL)
    );
    return chosen === (gap > 16 ? "Raised" : "Normal");
  }

  return chosen === answerKey[stepKey];
}

function getCorrectAnswer(caseItem, stepKey) {
  const answerKey = caseItem.answer_key ?? {};

  if (stepKey === "anion_gap") {
    const gas = caseItem.inputs?.gas ?? {};
    const electrolytes = caseItem.inputs?.electrolytes ?? {};
    const gap = calcAnionGap(
      Number(electrolytes.na_mmolL),
      Number(electrolytes.cl_mmolL),
      Number(gas.hco3_mmolL)
    );
    return gap > 16 ? "Raised" : "Normal";
  }

  if (answerKey[stepKey] != null) return answerKey[stepKey];
  if (stepKey === "anion_gap" && answerKey.anion_gap_category) return answerKey.anion_gap_category;
  return "Unknown";
}

function getCurrentElapsedSeconds() {
  if (!sessionState.caseStartMs) return 0;
  return (nowMs() - sessionState.caseStartMs) / 1000;
}

function stopTimer() {
  if (appData.timerInterval) {
    window.clearInterval(appData.timerInterval);
    appData.timerInterval = null;
  }
}

function updatePracticeTimer() {
  const timerLabel = document.getElementById("practiceTimerValue");
  if (!timerLabel) return;
  if (!sessionState.caseStartMs || !sessionState.timedMode) {
    timerLabel.textContent = "Timer hidden";
    return;
  }

  timerLabel.textContent = `${getCurrentElapsedSeconds().toFixed(1)}s elapsed`;
}

function startTimer() {
  stopTimer();
  sessionState.caseStartMs = nowMs();
  updatePracticeTimer();
  appData.timerInterval = window.setInterval(updatePracticeTimer, 100);
}

function caseMatchesDifficulty(caseItem, difficultyKey) {
  const level = getDifficultyLevel(difficultyKey);
  const caseDifficultyLevel = Number(caseItem.difficulty_level ?? 1);
  const caseDifficultyLabel = String(caseItem.difficulty_label ?? getDifficultyLabel(caseDifficultyLevel)).toLowerCase();
  return caseDifficultyLevel === level || caseDifficultyLabel === difficultyKey;
}

function getEligibleCasesForDifficulty(difficultyKey) {
  const exactMatches = appData.cases.filter(caseItem => caseMatchesDifficulty(caseItem, difficultyKey));
  const pool = exactMatches.length ? exactMatches : [...appData.cases];

  const withoutRecent = pool.filter(caseItem => !appData.recentArchetypes.includes(caseItem.archetype));
  return withoutRecent.length ? withoutRecent : pool;
}

function rememberRecentArchetype(caseItem) {
  if (!caseItem?.archetype) return;
  appData.recentArchetypes.push(caseItem.archetype);
  if (appData.recentArchetypes.length > RECENT_ARCHETYPE_LIMIT) {
    appData.recentArchetypes.shift();
  }
}

function normalizeDiagnosisOption(value) {
  return String(value ?? "")
    .toLowerCase()
    .replace(/[\/\-(),]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function diagnosisOptionsOverlap(left, right) {
  const leftNormalized = normalizeDiagnosisOption(left);
  const rightNormalized = normalizeDiagnosisOption(right);

  if (!leftNormalized || !rightNormalized) return false;
  if (leftNormalized === rightNormalized) return true;

  const leftTokens = leftNormalized.split(" ");
  const rightTokens = rightNormalized.split(" ");
  const shorterTokens = leftTokens.length <= rightTokens.length ? leftTokens : rightTokens;
  const longerTokens = leftTokens.length > rightTokens.length ? leftTokens : rightTokens;

  return shorterTokens.every(token => longerTokens.includes(token));
}

function getDiagnosisOptionPool() {
  return appData.cases.flatMap(item => {
    const diagnosisStep = (item?.questions_flow ?? []).find(step => step?.key === "final_diagnosis");

    return [
      item?.answer_key?.final_diagnosis,
      ...(Array.isArray(diagnosisStep?.options) ? diagnosisStep.options : [])
    ];
  });
}

function buildDiagnosisOptionOverride(caseItem, step) {
  const targetCount = step.options.length;
  const correctDiagnosis = caseItem?.answer_key?.final_diagnosis;
  // Deduplicate diagnosis options to avoid duplicate or near-duplicate distractors.
  const sanitizedOptions = [];

  function tryAddOption(option) {
    const trimmedOption = String(option ?? "").trim();
    if (!trimmedOption) return false;

    const duplicate = sanitizedOptions.some(existingOption =>
      existingOption.trim() === trimmedOption ||
      normalizeDiagnosisOption(existingOption) === normalizeDiagnosisOption(trimmedOption) ||
      diagnosisOptionsOverlap(existingOption, trimmedOption)
    );

    if (duplicate) return false;

    sanitizedOptions.push(trimmedOption);
    return true;
  }

  tryAddOption(correctDiagnosis);
  step.options.forEach(tryAddOption);

  getDiagnosisOptionPool().forEach(option => {
    if (sanitizedOptions.length < targetCount) {
      tryAddOption(option);
    }
  });

  return shuffleArray(sanitizedOptions);
}

function buildStepOptionOverrides(caseItem) {
  const overrides = {};

  (caseItem?.questions_flow ?? []).forEach((step, index) => {
    if (step?.key === "final_diagnosis" && Array.isArray(step.options)) {
      overrides[index] = buildDiagnosisOptionOverride(caseItem, step);
    }
  });

  return overrides;
}

function resetPracticeSession() {
  sessionState.currentCase = null;
  sessionState.currentStepIndex = 0;
  sessionState.stepResults = [];
  sessionState.stepOptionOverrides = {};
  sessionState.caseStartMs = null;
  stopTimer();
}

function startNewCase(difficultyKey = sessionState.currentDifficulty) {
  if (!appData.cases.length) {
    appData.loadError = "Cases are unavailable. Check that abg_cases.json is present in the same folder.";
    renderApp();
    return;
  }

  const nextDifficulty = normalizeDifficultyKey(difficultyKey);
  sessionState.currentDifficulty = nextDifficulty;

  if (!canStartNewCase()) {
    resetPracticeSession();
    sessionState.currentView = "dashboard";
    renderApp();
    return;
  }

  appData.loadError = null;
  sessionState.currentStepIndex = 0;
  sessionState.stepResults = [];
  sessionState.currentView = "practice";
  appData.lastCaseSummary = null;

  const selectedCase = pickRandom(getEligibleCasesForDifficulty(nextDifficulty));
  if (!selectedCase) {
    appData.loadError = "No eligible case could be selected.";
    renderApp();
    return;
  }

  sessionState.currentCase = selectedCase;
  
  trackEvent("case_started", {
  case_id: selectedCase.case_id,
  archetype: selectedCase.archetype,
  difficulty: nextDifficulty
});
  sessionState.stepOptionOverrides = buildStepOptionOverrides(selectedCase);
  rememberRecentArchetype(selectedCase);
  startTimer();
  renderApp();
}

function answerCurrentStep(choice) {
  const caseItem = sessionState.currentCase;
  if (!caseItem) return;

  const step = caseItem.questions_flow?.[sessionState.currentStepIndex];
  if (!step) return;
  if (sessionState.stepResults[sessionState.currentStepIndex]) return;

  sessionState.stepResults.push({
    key: step.key,
    label: step.label ?? prettyStepLabel(step.key),
    prompt: step.prompt,
    chosen: choice,
    correctAnswer: getCorrectAnswer(caseItem, step.key),
    correct: isCorrectAnswer(caseItem, step.key, choice)
  });
  
  trackEvent("step_answered", {
	  case_id: caseItem.case_id,
	  step: step.key,
	  correct: isCorrectAnswer(caseItem, step.key, choice)
	});

  renderPractice();
  updatePracticeTimer();
}

function continuePracticeStep() {
  if (!sessionState.currentCase) return;

  if (sessionState.currentStepIndex < (sessionState.currentCase.questions_flow?.length ?? 0) - 1) {
    sessionState.currentStepIndex += 1;
    renderPractice();
    return;
  }

  finishCase();
}

function updateDailyStreak() {
  const today = todayKey();
  if (userState.lastCaseDate === today) {
    userState.dailyCasesUsed += 1;
    return;
  }

  if (userState.lastCaseDate === yesterdayKey()) {
    userState.streak += 1;
  } else {
    userState.streak = 1;
  }

  userState.lastCaseDate = today;
  userState.dailyCasesUsed = 1;
}

function finishCase() {
  const caseItem = sessionState.currentCase;
  if (!caseItem) return;

  const difficultyLevel = Number(caseItem.difficulty_level ?? getDifficultyLevel(sessionState.currentDifficulty));
  const elapsedSeconds = getCurrentElapsedSeconds();
  stopTimer();
  const totalSteps = caseItem.questions_flow?.length ?? 0;
  const correctSteps = sessionState.stepResults.filter(result => result.correct).length;
  const accuracy = totalSteps ? Math.round((correctSteps / totalSteps) * 100) : 0;
  const perfectCase = totalSteps > 0 && correctSteps === totalSteps;

  const baseXp = getBaseXp(difficultyLevel);
  const perfectBonus = perfectCase ? getPerfectBonus(difficultyLevel) : 0;
  const speedBonus = sessionState.timedMode ? getTimeBonus(elapsedSeconds) : 0;
  const totalXpAward = Math.round((baseXp + perfectBonus + speedBonus) * getEffectiveXpMultiplier());

  userState.xp += totalXpAward;
  userState.casesCompleted += 1;
  userState.correctAnswers += correctSteps;
  userState.totalAnswers += totalSteps;

  const caseCorrect = correctSteps === totalSteps;
  userState.recentResults.push(caseCorrect);

  if (userState.recentResults.length > 20) {
    userState.recentResults.shift();
  }
  updateDailyStreak();
  syncUserStateDerivedFields();
  evaluateBadges();
  saveUserState();

  appData.lastCaseSummary = {
    caseId: caseItem.case_id,
    title: caseItem.title ?? "ABG Case",
    difficulty: toTitleCase(sessionState.currentDifficulty),
    explanation: caseItem.explanation ?? "",
    learningObjective: caseItem.learning_objective ?? "Review the reasoning steps and pattern recognition for this case.",
    elapsedSeconds,
    accuracy,
    correctSteps,
    totalSteps,
    totalXpAward,
    baseXp,
    perfectBonus,
    speedBonus,
    level: userState.level,
    stepResults: clone(sessionState.stepResults),
    caseData: clone(caseItem)
  };
  
  trackEvent("case_completed", {
  case_id: caseItem.case_id,
  archetype: caseItem.archetype,
  difficulty: sessionState.currentDifficulty,
  accuracy: accuracy,
  elapsed_seconds: Math.round(elapsedSeconds)
});

  sessionState.currentView = "results";
  renderApp();
}

function openCaseFeedbackForm() {
  const caseItem = appData.lastCaseSummary?.caseData;
  const gas = caseItem?.inputs?.gas;
  const caseId = caseItem?.case_id;

  if (!caseId || gas?.ph == null || gas?.paco2_mmHg == null || gas?.hco3_mmolL == null) return;

  const valuesSummary = `pH ${gas.ph} / PaCO2 ${gas.paco2_mmHg} / HCO3 ${gas.hco3_mmolL}`;
  const formUrl = `https://docs.google.com/forms/d/e/1FAIpQLScrfFqV6EwEDzIWkYcfFrUw4L-zjmwj0aIDg2bwNPwMYBTz6Q/viewform?usp=pp_url&entry.2070020822=${encodeURIComponent(caseId)}&entry.134622764=${encodeURIComponent(valuesSummary)}`;

	trackEvent("feedback_opened", {
	  case_id: caseId
	});
  window.open(formUrl, "_blank");
}

async function loadCases() {
  const response = await fetch("./abg_cases.json", { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Failed to load JSON: ${response.status}`);
  }

  const payload = await response.json();
  if (Array.isArray(payload)) {
    return {
      cases: payload,
      progressionConfig: null,
      dashboardState: null,
      defaultUserState: null
    };
  }

  if (payload && Array.isArray(payload.cases)) {
    return {
      cases: payload.cases,
      progressionConfig: payload.progression_config ?? null,
      dashboardState: payload.dashboard_state ?? null,
      defaultUserState: payload.default_user_state ?? null
    };
  }

  throw new Error("JSON format not recognized.");
}

function renderNavbar() {
  const levelProgress = getLevelProgress();
  const nav = document.getElementById("navBar");
  if (!nav) return;

  setText("navStreakValue", String(userState.streak));
  setText("navLevelPill", `Level ${userState.level}`);
  setText(
    "navProgressLabel",
    levelProgress.xpForNextLevel
      ? `${levelProgress.xpIntoLevel} / ${levelProgress.xpForNextLevel} XP`
      : `${userState.xp} XP`
  );
  setWidth("navProgressFill", `${levelProgress.progressPercent}%`);

  const timedToggle = document.getElementById("timedModeToggle");
  if (timedToggle) timedToggle.checked = sessionState.timedMode;

  nav.querySelectorAll(".nav-tab").forEach(link => {
    link.classList.toggle("is-active", link.dataset.view === sessionState.currentView);
  });
}

function renderDashboard() {
  const levelProgress = getLevelProgress();
  const recent = userState.recentResults ?? [];
  const accuracy = recent.length
    ? Math.round((recent.filter(result => result).length / recent.length) * 100)
    : 100;
  const casesRemaining = getCasesRemainingToday();
  const difficultyCards = getDifficultyMeta()
    .map(item => {
      const unlocked = canAccessDifficulty(item.level);

      return `
        <button
          class="difficulty-card ${unlocked ? "is-unlocked" : "is-locked"}"
          type="button"
          data-action="start-case"
          data-difficulty="${item.key}"
          ${unlocked ? "" : "disabled"}
        >
          <div class="difficulty-head">
            <div class="difficulty-name">${escapeHtml(item.label)}</div>
            <span class="difficulty-badge">
              ${unlocked ? "Unlocked" : "Locked"}
            </span>
          </div>

          ${unlocked ? "" : `<div class="difficulty-meta">Unlock at Level ${item.unlockLevel}</div>`}
        </button>
      `;
    })
    .join("");
  const recentBadges = userState.badges.slice(-3).reverse();
  const recentBadgeMarkup = recentBadges.length
    ? recentBadges.map(badge => `
        <div class="badge-card">
          <strong>${escapeHtml(badge)}</strong>
        </div>
      `).join("")
    : "";


	const resetBtn = document.getElementById("resetProgressBtn");

	if (resetBtn) {
	  resetBtn.onclick = () => {
		const confirmed = confirm("Reset all progress? This will clear XP, level, and streak.");

		if (confirmed) {
		  localStorage.clear();
		  location.reload();
		}
	  };
	}
  const practiceBtn = document.getElementById("dashboardPracticeBtn");
  if (practiceBtn) {
    practiceBtn.dataset.difficulty = sessionState.currentDifficulty;
  }

  setText("dashboardHeading", "Welcome back, Guest User!");
  setText("dashboardSubtitle", "");
  setText("dashboardProgressLabel", "Progress to Next Level");
  setText(
    "dashboardProgressValue",
    levelProgress.xpForNextLevel
      ? `${levelProgress.xpIntoLevel} / ${levelProgress.xpForNextLevel} XP`
      : `${userState.xp} XP`
  );
  setWidth("dashboardProgressFill", `${levelProgress.progressPercent}%`);

  setText("dashboardLevelValue", String(userState.level));
  setText(
    "dashboardLevelSubcopy",
    `${userState.xp} / ${getXpRequiredForLevel(userState.level)} XP`
  );
  setText("dashboardCasesValue", String(userState.casesCompleted));
  setText("dashboardCasesSubcopy", "Total interpretations");
  setText("dashboardAccuracyValue", `${accuracy}%`);
  setText("dashboardAccuracySubcopy", "Recent performance");
  setText("dashboardStreakValue", String(userState.streak));
  const longest = userState.longestStreak ?? userState.streak ?? 0;

  setText(
    "dashboardStreakSubcopy",
    `Longest: ${longest} day${longest === 1 ? "" : "s"}`
  );

  setText(
    "dashboardCasesRemaining",
    casesRemaining == null ? "" : `${casesRemaining} case${casesRemaining === 1 ? "" : "s"} remaining today`
  );
  setHtml("dashboardDifficultyGrid", difficultyCards);
  setHtml("dashboardRecentBadges", recentBadgeMarkup);
}

function renderAbgMetrics(caseItem) {
  const gas = caseItem.inputs?.gas ?? {};
  const electrolytes = caseItem.inputs?.electrolytes ?? {};
  const lactate = caseItem.inputs?.lactate_mmolL;
  const difficultyLevel = Number(caseItem.difficulty_level ?? 1);
  const showReferences = difficultyLevel <= 2;
  const showAbnormalHighlighting = difficultyLevel <= 3;

  const metrics = [
    {
      label: "pH",
      reference: "Normal: 7.35 - 7.45",
      value: formatValue(gas.ph, 2),
      abnormal: gas.ph < 7.35 || gas.ph > 7.45
    },
    {
      label: "PaCO2",
      reference: "Normal: 35 - 45 mmHg",
      value: gas.paco2_mmHg != null ? `${formatValue(gas.paco2_mmHg, 1)} mmHg` : "--",
      abnormal: gas.paco2_mmHg < 35 || gas.paco2_mmHg > 45
    },
    {
      label: "HCO3",
      reference: "Normal: 22 - 26 mmol/L",
      value: gas.hco3_mmolL != null ? `${formatValue(gas.hco3_mmolL, 1)} mmol/L` : "--",
      abnormal: gas.hco3_mmolL < 22 || gas.hco3_mmolL > 26
    },
    {
      label: "PaO2",
      reference: "Normal: 80 - 100 mmHg",
      value: gas.pao2_mmHg != null ? `${formatValue(gas.pao2_mmHg, 1)} mmHg` : "--",
      abnormal: gas.pao2_mmHg < 80 || gas.pao2_mmHg > 100
    },
    {
      label: "Base excess",
      reference: "Normal: -2 to +2 mEq/L",
      value: gas.base_excess_mEqL != null ? `${formatValue(gas.base_excess_mEqL, 1)} mEq/L` : "--",
      abnormal: gas.base_excess_mEqL < -2 || gas.base_excess_mEqL > 2
    },
    {
      label: "Na",
      reference: "Normal: 135 - 145 mmol/L",
      value: electrolytes.na_mmolL != null ? `${formatValue(electrolytes.na_mmolL, 0)} mmol/L` : "--",
      abnormal: electrolytes.na_mmolL < 135 || electrolytes.na_mmolL > 145
    },
    {
      label: "Cl",
      reference: "Normal: 98 - 106 mmol/L",
      value: electrolytes.cl_mmolL != null ? `${formatValue(electrolytes.cl_mmolL, 0)} mmol/L` : "--",
      abnormal: electrolytes.cl_mmolL < 98 || electrolytes.cl_mmolL > 106
    },
    {
      label: "Lactate",
      reference: "Normal: 0.5 - 2.0 mmol/L",
      value: lactate != null ? `${formatValue(lactate, 1)} mmol/L` : "--",
      abnormal: lactate < 0.5 || lactate > 2
    }
  ];

  return metrics
    .filter(metric => metric.value !== "--")
    .map(metric => {
      return `
        <div class="value-item">
          <div class="value-copy">
            <span class="value-label">${metric.label}</span>
            ${showReferences ? `<span class="value-reference">${metric.reference}</span>` : ""}
          </div>
          <strong class="value-number ${showAbnormalHighlighting && metric.abnormal ? "value-abnormal" : ""}">
            ${escapeHtml(metric.value)}
          </strong>
        </div>
      `;
    })
    .join("");
}

function renderPractice() {
  setText("practiceTitle", "Practice Mode");
  sessionState.currentDifficulty = normalizeDifficultyKey(sessionState.currentDifficulty);
  const levelProgress = getLevelProgress();
  setText(
    "practiceLevelLine",
    levelProgress.xpForNextLevel
      ? `Level ${userState.level} • ${levelProgress.xpIntoLevel} / ${levelProgress.xpForNextLevel} XP`
      : `Level ${userState.level}`
  );

  const difficultySelect = document.getElementById("practiceDifficultySelect");
  if (difficultySelect) {
    difficultySelect.innerHTML = getAccessibleDifficultyKeys().map(diff => `
      <option
        value="${escapeHtml(diff)}"
      >
        ${escapeHtml(toTitleCase(diff))}
      </option>
    `).join("");
    difficultySelect.value = sessionState.currentDifficulty;
  }

  const casesRemaining = getCasesRemainingToday();
  const alert = document.getElementById("practiceCasesAlert");
  if (alert) {
    if (casesRemaining == null) {
      alert.classList.add("is-hidden");
      alert.textContent = "";
    } else {
      alert.classList.remove("is-hidden");
      alert.textContent = `${casesRemaining} case${casesRemaining === 1 ? "" : "s"} remaining today`;
    }
  }

  if (!sessionState.currentCase) {
    setText("practiceStem", "");
    setHtml("practiceMetrics", "");
    setText("practiceQuestionLabel", "Interpret the ABG");
    setText("practiceQuestionMeta", "");
    setText("practicePrompt", "");
    setHtml("practiceStepProgress", "");
    setHtml("practiceOptions", "");
    setText("practiceTimerValue", sessionState.timedMode ? "0.0s elapsed" : "Timer hidden");
    const feedback = document.getElementById("practiceFeedback");
    if (feedback) feedback.className = "practice-feedback is-hidden";
    return;
  }

  const caseItem = sessionState.currentCase;
  const totalSteps = caseItem.questions_flow?.length ?? 0;
  const currentStep = caseItem.questions_flow?.[sessionState.currentStepIndex];
  const currentResult = sessionState.stepResults[sessionState.currentStepIndex] ?? null;
  const currentOptions = sessionState.stepOptionOverrides[sessionState.currentStepIndex] ?? currentStep?.options ?? [];
  const stepPills = (caseItem.questions_flow ?? [])
  .map((step, index) => {

    const result = sessionState.stepResults[index];
    const done = index < sessionState.stepResults.length;
    const incorrect = result && !result.correct;
    const current = index === sessionState.currentStepIndex;

    return `
      <span class="step-pill 
        ${done && !incorrect ? "is-done" : ""}
        ${incorrect ? "is-incorrect" : ""}
        ${current ? "is-current" : ""}">
        ${index + 1}. ${escapeHtml(step.label ?? prettyStepLabel(step.key))}
      </span>
    `;
  })
  .join("");
  setText("practiceStem", caseItem.clinical_stem ?? "");
  setText(
    "practiceQuestionLabel",
    currentStep?.label ?? "Interpret the ABG"
  );
  setText(
    "practiceQuestionMeta",
    `Question ${sessionState.currentStepIndex + 1} of ${totalSteps}`
  );
  setText("practicePrompt", currentStep?.prompt ?? "");
  setHtml("practiceStepProgress", stepPills);
  setHtml("practiceMetrics", renderAbgMetrics(caseItem));
  setHtml(
    "practiceOptions",
    currentResult ? "" : currentOptions.map(option => `
      <button
        class="option-btn"
        type="button"
        data-action="answer"
        data-option="${escapeHtml(option)}"
      >
        ${escapeHtml(option)}
      </button>
    `).join("")
  );

  const feedback = document.getElementById("practiceFeedback");
  if (feedback) {
    if (currentResult) {
      feedback.className = `practice-feedback ${currentResult.correct ? "is-correct" : "is-incorrect"}`;
      setText("practiceFeedbackTitle", currentResult.correct ? "Correct!" : "Incorrect");
      setText("practiceFeedbackAnswer", `Your answer: ${currentResult.chosen}`);
      setText("practiceFeedbackCorrect", `Correct answer: ${currentResult.correctAnswer}`);
      setText("practiceFeedbackCopy", "");
      setText(
        "practiceContinueBtn",
        sessionState.currentStepIndex < totalSteps - 1 ? "Continue" : "Finish case"
      );
    } else {
      feedback.className = "practice-feedback is-hidden";
      setText("practiceFeedbackTitle", "");
      setText("practiceFeedbackAnswer", "");
      setText("practiceFeedbackCorrect", "");
      setText("practiceFeedbackCopy", "");
      setText("practiceContinueBtn", "Continue");
    }
  }
  updatePracticeTimer();
}

function renderResults() {
  const resultsExplanationSection = document.getElementById("resultsExplanationSection");

  if (!appData.lastCaseSummary) {
    setText("resultsTitle", "Results");
    setText("resultsObjective", "");
    setText("resultsDifficultyChip", toTitleCase(sessionState.currentDifficulty));
    setText("resultsTimeChip", "0.0s");
    setText("resultsOutcomeLabel", "Results");
    setText("resultsAccuracyValue", "0%");
    setText("resultsXpValue", "+0");
    setText("resultsCorrectValue", "0 / 0");
    setText("resultsLevelValue", String(userState.level));
    setText("resultsExplanation", "");
    setHtml("resultsValuesGrid", "");
    setHtml("resultsStepList", "");
    if (resultsExplanationSection) resultsExplanationSection.classList.add("is-hidden");
    return;
  }

  const summary = appData.lastCaseSummary;
  const perfectCase = summary.correctSteps === summary.totalSteps && summary.totalSteps > 0;
  const resultRows = summary.stepResults
    .map(stepResult => `
      <div class="review-item ${stepResult.correct ? "is-correct" : "is-incorrect"}">
        <div class="review-step">${escapeHtml(stepResult.label)}</div>
        <div class="review-answer">You chose ${escapeHtml(stepResult.chosen)}. Correct answer: ${escapeHtml(stepResult.correctAnswer)}.</div>
      </div>
    `)
    .join("");

  const resultTitle = summary.title || "";

  if (resultTitle.includes("(")) {
    const [mainTitle, rest] = resultTitle.split("(");
    setHtml(
      "resultsTitle",
      `${escapeHtml(mainTitle.trim())}<br><span class="case-subtitle">${escapeHtml(rest.replace(")", "").trim())}</span>`
    );
  } else {
    setText("resultsTitle", resultTitle);
  }
  setText("resultsObjective", "");
  setText("resultsDifficultyChip", summary.difficulty);
  setText("resultsTimeChip", `${summary.elapsedSeconds.toFixed(1)}s`);
  setText("resultsOutcomeLabel", perfectCase ? "Correct!" : "Incorrect");
  setText("resultsAccuracyValue", `${summary.accuracy}%`);
  setText("resultsXpValue", `+${summary.totalXpAward}`);
  setText("resultsCorrectValue", `${summary.correctSteps} / ${summary.totalSteps}`);
  setText("resultsLevelValue", String(summary.level));
  setText("resultsExplanation", summary.explanation ?? "");
  setHtml("resultsValuesGrid", renderResultsValues(summary.caseData));
  setHtml("resultsStepList", resultRows);

  if (resultsExplanationSection) {
    resultsExplanationSection.classList.toggle("is-hidden", !summary.explanation);
  }

  const resultsSummaryCard = document.getElementById("resultsSummaryCard");
  if (resultsSummaryCard) {
    resultsSummaryCard.className = `fig-card result-state-card ${perfectCase ? "is-correct" : "is-incorrect"}`;
  }
}

function renderResultsValues(caseItem) {
  const gas = caseItem?.inputs?.gas ?? {};
  const electrolytes = caseItem?.inputs?.electrolytes ?? {};
  const lactate = caseItem?.inputs?.lactate_mmolL;

  const metrics = [
    ["pH", formatValue(gas.ph, 2)],
    ["PaCO2", gas.paco2_mmHg != null ? `${formatValue(gas.paco2_mmHg, 1)} mmHg` : "--"],
    ["HCO3", gas.hco3_mmolL != null ? `${formatValue(gas.hco3_mmolL, 1)} mmol/L` : "--"],
    ["Na", electrolytes.na_mmolL != null ? `${formatValue(electrolytes.na_mmolL, 0)} mmol/L` : "--"],
    ["Cl", electrolytes.cl_mmolL != null ? `${formatValue(electrolytes.cl_mmolL, 0)} mmol/L` : "--"],
    ["Lactate", lactate != null ? `${formatValue(lactate, 1)} mmol/L` : "--"]
  ];

  return metrics
    .filter(([, value]) => value !== "--")
    .map(([label, value]) => `
      <div class="results-value-tile">
        <span class="results-value-label">${label}</span>
        <strong class="results-value-number">${escapeHtml(value)}</strong>
      </div>
    `)
    .join("");
}

function renderLearn() {
  if (!canAccessLearn()) {
    setHtml("learnGrid", "");
    return;
  }

  const objectives = new Map();
  for (const caseItem of appData.cases) {
    const difficultyKey = getDifficultyLabel(Number(caseItem.difficulty_level ?? 1));
    if (!objectives.has(difficultyKey)) objectives.set(difficultyKey, []);
    if (objectives.get(difficultyKey).length < 3 && caseItem.learning_objective) {
      objectives.get(difficultyKey).push(caseItem.learning_objective);
    }
  }

  setHtml("learnGrid", getDifficultyMeta().map(item => `
    <article class="learn-card">
      <h2>${escapeHtml(item.label)}</h2>
      <p>${item.availableCases} cases available</p>
      <div class="learn-points">
        ${(objectives.get(item.key) ?? []).map(objective => `
          <div class="learn-point">${escapeHtml(objective)}</div>
        `).join("")}
      </div>
    </article>
  `).join(""));
}

function renderLeaderboard() {
  const localPlayer = {
    name: "You",
    xp: userState.xp,
    accuracy: calculateAccuracy(),
    level: userState.level
  };

  const leaderboard = [
    { name: "Dr. Rivera", xp: 720, accuracy: 92, level: 8 },
    { name: "Triage Fox", xp: 610, accuracy: 88, level: 7 },
    { name: "You", xp: localPlayer.xp, accuracy: localPlayer.accuracy, level: localPlayer.level },
    { name: "Ward Eight", xp: 280, accuracy: 76, level: 4 }
  ]
    .sort((left, right) => right.xp - left.xp)
    .map((entry, index) => ({ ...entry, rank: index + 1 }));
  const userEntry = leaderboard.find(entry => entry.name === "You") ?? leaderboard[0];

  setText("leaderboardUserRank", `#${userEntry.rank}`);
  setText("leaderboardUserLevel", `Level ${userEntry.level}`);
  setText("leaderboardUserXp", `${userEntry.xp} XP`);
  setText("leaderboardUserAccuracy", `${userEntry.accuracy}% accuracy`);

  setHtml("leaderboardList", leaderboard.map(entry => `
    <div class="leaderboard-row">
      <span class="leaderboard-rank">${entry.rank}</span>
      <div class="leaderboard-main">
        <div class="leaderboard-name">${escapeHtml(entry.name)}</div>
        <div class="leaderboard-meta">Level ${entry.level} • ${entry.accuracy}% accuracy</div>
      </div>
      <div class="leaderboard-xp">${entry.xp} XP</div>
    </div>
  `).join(""));

  setHtml("leaderboardTopList", leaderboard.slice(0, 3).map(entry => `
    <div class="top-card">
      <div class="top-rank">#${entry.rank}</div>
      <div class="top-name">${escapeHtml(entry.name)}</div>
      <div class="top-meta">Level ${entry.level}</div>
      <div class="top-meta">${entry.accuracy}% accuracy</div>
    </div>
  `).join(""));
}

function renderProfile() {
  const progress = getLevelProgress();
  const badges = userState.badges.length
    ? userState.badges.map(badge => `
      <div class="badge-card">
        <strong>${escapeHtml(badge)}</strong>
      </div>
    `).join("")
    : `<div class="badge-card"><strong></strong></div>`;

  setText("profileUsernameValue", "");
  setText("profileSpecialtyValue", "");
  setText("profileXpValue", String(userState.xp));
  setText("profileLevelValue", String(userState.level));
  setText("profileAccuracyValue", `${calculateAccuracy()}%`);
  setText(
    "profileNextLevelValue",
    progress.xpForNextLevel ? `${progress.xpIntoLevel}/${progress.xpForNextLevel}` : `${userState.xp}`
  );
  setWidth("profileProgressFill", `${progress.progressPercent}%`);
  setText("profileCasesValue", String(userState.casesCompleted));
  setText("profileStreakValue", String(userState.streak));
  setText("profileBadgeCount", `${userState.badges.length} of 4 badges earned`);
  const membershipPill = document.getElementById("profileMembershipPill");
  if (membershipPill) {
    if (userState.isPremium) {
      membershipPill.classList.remove("is-hidden");
      membershipPill.textContent = "Premium Member";
    } else {
      membershipPill.classList.add("is-hidden");
      membershipPill.textContent = "";
    }
  }
  setHtml("profileBadgeList", badges);
}

function renderApp() {
  sessionState.currentDifficulty = normalizeDifficultyKey(sessionState.currentDifficulty);
  renderNavbar();
  renderDashboard();
  renderPractice();
  renderResults();
  renderLearn();
  renderLeaderboard();
  renderProfile();
  showView(sessionState.currentView);
}

function returnToDashboard() {
  resetPracticeSession();
  sessionState.currentView = "dashboard";
  renderApp();
}

function handleDocumentClick(event) {
  const actionTarget = event.target.closest("[data-action]");
  if (!actionTarget) return;

  const { action } = actionTarget.dataset;

  if (action === "view") {
    if (actionTarget.dataset.view === "practice") {
      maybeShowPracticeIntro(() => {
        showView("practice");
        renderNavbar();
      });
    } else {
      showView(actionTarget.dataset.view);
      renderNavbar();
    }
    return;
  }

  if (action === "start-case") {
    maybeShowPracticeIntro(() => {
      startNewCase(actionTarget.dataset.difficulty || sessionState.currentDifficulty);
    });
    return;
  }

  if (action === "answer") {
    answerCurrentStep(actionTarget.dataset.option ?? "");
    return;
  }

  if (action === "continue-step") {
    continuePracticeStep();
    return;
  }

  if (action === "next-case") {
    if (sessionState.currentCase && sessionState.currentView !== "results") {
      const confirmed = confirm("Start a new case? Your current case progress will be lost.");
      if (!confirmed) return;

      userState.abandonedCases += 1;
      saveUserState();
    }

    maybeShowPracticeIntro(() => {
      startNewCase(sessionState.currentDifficulty);
    });
    return;
  }

  if (action === "return-dashboard") {
    returnToDashboard();
  }
}

function handleDocumentChange(event) {
  if (event.target.id === "timedModeToggle") {
    sessionState.timedMode = Boolean(event.target.checked);
    renderNavbar();
    renderPractice();
    return;
  }

  if (event.target.id === "practiceDifficultySelect") {
    sessionState.currentDifficulty = event.target.value || sessionState.currentDifficulty;
    startNewCase(sessionState.currentDifficulty);
  }
}

window.addEventListener("error", event => {
  console.error("GLOBAL FRONTEND ERROR:", event.error || event.message);
});

window.addEventListener("unhandledrejection", event => {
  console.error("UNHANDLED PROMISE REJECTION:", event.reason);
});

document.addEventListener("click", handleDocumentClick);
document.addEventListener("change", handleDocumentChange);

const reportCaseBtn = document.getElementById("reportCaseBtn");
if (reportCaseBtn) {
  reportCaseBtn.addEventListener("click", openCaseFeedbackForm);
}

const practiceIntroStartBtn = document.getElementById("practiceIntroStartBtn");
if (practiceIntroStartBtn) {
  practiceIntroStartBtn.addEventListener("click", continueFromPracticeIntro);
}

(async function init() {
  try {
    const data = await loadCases();
    appData.cases = data.cases ?? [];
    appData.progressionConfig = data.progressionConfig ?? null;
    appData.dashboardState = data.dashboardState ?? null;
    appData.defaultUserState = data.defaultUserState ?? null;
    appData.loadError = null;
    appData.isLoaded = true;

    Object.assign(userState, loadUserState());
    syncUserStateDerivedFields();
    saveUserState();
  } catch (error) {
    appData.loadError = error.message;
    appData.isLoaded = true;
    console.error("INIT ERROR:", error);
  }

  renderApp();
})();
