import { els } from "./dom.js";

const FIELD_MAP = [
  { key: "alpha", range: "hpAlphaRange", number: "hpAlphaNumber", type: "float" },
  { key: "gamma", range: "hpGammaRange", number: "hpGammaNumber", type: "float" },
  {
    key: "epsilon_start",
    range: "hpEpsilonStartRange",
    number: "hpEpsilonStartNumber",
    type: "float",
  },
  { key: "epsilon_end", range: "hpEpsilonEndRange", number: "hpEpsilonEndNumber", type: "float" },
  {
    key: "epsilon_decay_episodes",
    range: "hpEpsilonDecayRange",
    number: "hpEpsilonDecayNumber",
    type: "int",
  },
  { key: "reward_goal", range: "hpRewardGoalRange", number: "hpRewardGoalNumber", type: "float" },
  { key: "reward_step", range: "hpRewardStepRange", number: "hpRewardStepNumber", type: "float" },
  {
    key: "reward_blocked",
    range: "hpRewardBlockedRange",
    number: "hpRewardBlockedNumber",
    type: "float",
  },
  { key: "seed", range: "hpSeedRange", number: "hpSeedNumber", type: "int" },
];

let defaults = null;
let isBound = false;

function normalizeValue(value, type) {
  if (type === "int") return String(Math.round(Number(value)));
  return String(Number(value));
}

function parseValue(value, type) {
  return type === "int" ? Number.parseInt(value, 10) : Number.parseFloat(value);
}

function fieldElements(field) {
  return {
    rangeEl: els[field.range],
    numberEl: els[field.number],
  };
}

function setFieldValue(field, rawValue) {
  const normalized = normalizeValue(rawValue, field.type);
  const { rangeEl, numberEl } = fieldElements(field);
  rangeEl.value = normalized;
  numberEl.value = normalized;
}

function setValidationMessage(message, isError = false) {
  els.labValidation.textContent = message;
  els.labValidation.classList.toggle("is-error", isError);
  els.labValidation.classList.toggle("is-ready", !isError && Boolean(message));
}

export function applyHyperparameterDefaults(trainConfig) {
  defaults = {
    alpha: Number(trainConfig.alpha),
    gamma: Number(trainConfig.gamma),
    epsilon_start: Number(trainConfig.epsilon_start),
    epsilon_end: Number(trainConfig.epsilon_end),
    epsilon_decay_episodes: Number(trainConfig.epsilon_decay_episodes),
    reward_goal: Number(trainConfig.reward_goal),
    reward_step: Number(trainConfig.reward_step),
    reward_blocked: Number(trainConfig.reward_blocked),
    seed: Number(trainConfig.seed),
  };
  for (const field of FIELD_MAP) {
    setFieldValue(field, defaults[field.key]);
  }
  setValidationMessage("Tip: tweak values to compare convergence behavior.");
}

function currentValues() {
  const values = {};
  for (const field of FIELD_MAP) {
    const { numberEl } = fieldElements(field);
    values[field.key] = parseValue(numberEl.value, field.type);
  }
  return values;
}

export function readHyperparameterPayload() {
  const payload = currentValues();
  for (const field of FIELD_MAP) {
    const value = payload[field.key];
    if (!Number.isFinite(value)) {
      return { ok: false, message: `Invalid value for ${field.key.replace("_", " ")}.` };
    }
  }
  if (payload.epsilon_end > payload.epsilon_start) {
    return { ok: false, message: "Epsilon end must be less than or equal to epsilon start." };
  }
  if (payload.reward_blocked > payload.reward_step) {
    return { ok: false, message: "Blocked-move reward should be <= step reward." };
  }
  return { ok: true, payload };
}

function syncField(field, source) {
  const { rangeEl, numberEl } = fieldElements(field);
  const sourceEl = source === "range" ? rangeEl : numberEl;
  const targetEl = source === "range" ? numberEl : rangeEl;
  targetEl.value = normalizeValue(sourceEl.value, field.type);
  setValidationMessage("Tip: tweak values to compare convergence behavior.");
}

function bindField(field) {
  const { rangeEl, numberEl } = fieldElements(field);
  rangeEl.addEventListener("input", () => syncField(field, "range"));
  numberEl.addEventListener("input", () => syncField(field, "number"));
}

export function bindHyperparameterLab() {
  if (isBound) return;
  isBound = true;
  for (const field of FIELD_MAP) bindField(field);
  els.labResetBtn.addEventListener("click", () => {
    if (!defaults) return;
    for (const field of FIELD_MAP) {
      setFieldValue(field, defaults[field.key]);
    }
    setValidationMessage("Reset to training defaults.");
  });
}

export function setHyperparameterError(message) {
  setValidationMessage(message, true);
}
