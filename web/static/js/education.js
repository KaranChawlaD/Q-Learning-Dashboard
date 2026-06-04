/** How-to guide and hyperparameter reference for the dashboard. */

import { els } from "./dom.js";

const HOWTO_STORAGE_KEY = "qlearning-howto-dismissed";

export const HYPERPARAMETER_HELP = {
  alpha: {
    title: "Alpha (α) — learning rate",
    equation:
      "Q(s,a) ← Q(s,a) + α · [ r + γ · maxₐ′ Q(s′,a′) − Q(s,a) ]",
    body: [
      "Alpha scales the TD error before it is added to Q(s,a). It answers: “How much should this single step change our belief?”",
      "Higher α learns faster from new experience but reacts strongly to noise. Lower α smooths updates and stabilizes training, but needs more episodes to converge.",
    ],
    tip: "Try 0.05–0.2 for steady learning on this small grid.",
  },
  gamma: {
    title: "Gamma (γ) — discount factor",
    equation: "target = r + γ · maxₐ′ Q(s′,a′)   (when not terminal)",
    body: [
      "Gamma controls how much the agent cares about future rewards versus immediate reward. It appears inside the bootstrap target of the Bellman update.",
      "γ near 1 values long paths to the bank; γ near 0 makes the agent greedy for instant payoff and ignore what happens after the next step.",
    ],
    tip: "0.9–0.99 is typical for gridworlds where the goal is far away.",
  },
  epsilon_start: {
    title: "Epsilon start (ε₀) — initial exploration",
    equation: "P(random action) = ε,   P(greedy action) = 1 − ε",
    body: [
      "At the start of training the agent usually picks a random legal action with probability ε, otherwise it follows the greedy Q-policy.",
      "A high ε₀ forces broad exploration early so every state-action pair gets visits before Q-values specialize.",
    ],
    tip: "1.0 means fully random at episode 0; lower values commit to the policy sooner.",
  },
  epsilon_end: {
    title: "Epsilon end (ε₁) — final exploration",
    equation: "ε decays linearly from ε₀ to ε₁ over decay episodes",
    body: [
      "By the end of the decay window the agent still explores occasionally with probability ε₁. That can help escape local optima late in training.",
      "ε₁ = 0 is pure exploitation: always take argmaxₐ Q(s,a). A small positive ε₁ keeps mild exploration through the last episodes.",
    ],
    tip: "Must be ≤ epsilon start.",
  },
  epsilon_decay_episodes: {
    title: "Epsilon decay episodes",
    equation: "ε(ep) = ε₀ + (ep / decay) · (ε₁ − ε₀)   for ep < decay",
    body: [
      "This is how many episodes the linear ε schedule runs before ε stays at ε₁.",
      "A longer decay keeps exploration high while Q is still noisy; a shorter decay switches to exploitation earlier.",
    ],
    tip: "Often set to 50–70% of total episodes.",
  },
  reward_goal: {
    title: "Reward (goal)",
    equation: "r = +reward_goal   when the agent enters the bank cell",
    body: [
      "The terminal reward for reaching the goal. It defines what “success” means in the reward signal that backs up through Q-learning.",
      "Larger goal reward makes reaching the bank dominate the return; the agent may tolerate longer detours if step penalties are small.",
    ],
    tip: "Default +100; keep positive so the bank stays attractive.",
  },
  reward_step: {
    title: "Reward (step)",
    equation: "r = reward_step   on each normal move (not blocked, not goal)",
    body: [
      "A per-step living cost encourages shorter paths. Negative values penalize wandering; values near 0 make only the goal matter.",
      "This term appears on almost every transition, so it strongly shapes the greedy policy the heatmap shows.",
    ],
    tip: "Typical range −1 to 0; more negative = stronger pressure for short routes.",
  },
  reward_blocked: {
    title: "Reward (blocked)",
    equation: "r = reward_blocked   when a move hits a wall or building",
    body: [
      "Blocked moves leave the agent in place but still deliver this reward. It should be ≤ step reward so bumping walls is no better than moving.",
      "More negative values teach the agent to avoid illegal moves faster.",
    ],
    tip: "Often 2–5× more negative than the step penalty.",
  },
  seed: {
    title: "Seed",
    equation: "randomness ← PRNG(seed) for ε-greedy tie-breaks and exploration",
    body: [
      "Fixes the pseudo-random sequence for action sampling during training. Same seed + same hyperparameters + same layout ⇒ reproducible runs.",
      "Changing the seed explores a different exploration path without changing the algorithm.",
    ],
    tip: "Use the same seed when comparing two hyperparameter settings fairly.",
  },
};

export const HOWTO_STEPS = [
  {
    title: "Design your gridworld",
    text: "Drag the agent (start), bank (goal), and buildings from the palette onto the 12×9 grid. Right-click a cell to clear it. Training stays disabled until a path exists from agent to bank.",
    image: "/assets/sprites/business_man_1_forward.png",
    imageAlt: "Agent sprite",
    extraImages: [
      { src: "/assets/elems/bank.png", alt: "Bank goal" },
      { src: "/assets/elems/building_1.png", alt: "Building obstacle" },
    ],
  },
  {
    title: "Tune hyperparameters",
    text: "Use the Hyperparameter Lab to set α, γ, ε schedule, and rewards. Click ⓘ beside any label to see how it enters the Q-learning update equation.",
    image: null,
    diagram: "Q ← Q + α ( r + γ max Q′ − Q )",
  },
  {
    title: "Start training",
    text: "Press Start Training when the layout is valid. The view switches to a live policy heatmap, metrics, and a steps-per-episode chart.",
    image: null,
    diagram: "SETUP → TRAINING",
  },
  {
    title: "Watch and control the run",
    text: "Space pauses or resumes; keys 1–6 change speed. After training finishes, review Model Tests. Use Export (E) to save a JSON snapshot or Import (I) to load one.",
    image: null,
    diagram: "Heatmap = maxₐ Q(s,a) per cell",
  },
];

let hpInfoTrapHandler = null;
let howtoTrapHandler = null;

function trapFocus(dialogEl, onClose) {
  const focusable = dialogEl.querySelectorAll(
    'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
  );
  const first = focusable[0];
  const last = focusable[focusable.length - 1];
  first?.focus();

  function onKeyDown(event) {
    if (event.key === "Escape") {
      event.preventDefault();
      onClose();
      return;
    }
    if (event.key !== "Tab" || focusable.length === 0) return;
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }
  document.addEventListener("keydown", onKeyDown);
  return () => document.removeEventListener("keydown", onKeyDown);
}

function openDialog(dialogEl, onClose) {
  dialogEl.classList.remove("hidden");
  dialogEl.setAttribute("aria-hidden", "false");
  document.body.classList.add("modal-open");
  const releaseTrap = trapFocus(dialogEl, onClose);
  return () => {
    releaseTrap();
    dialogEl.classList.add("hidden");
    dialogEl.setAttribute("aria-hidden", "true");
    document.body.classList.remove("modal-open");
  };
}

export function openHyperparameterInfo(key) {
  const help = HYPERPARAMETER_HELP[key];
  if (!help) return;

  els.hpInfoTitle.textContent = help.title;
  els.hpInfoEquation.textContent = help.equation;
  els.hpInfoBody.innerHTML = help.body.map((p) => `<p>${p}</p>`).join("");
  els.hpInfoTip.textContent = help.tip ? `Tip: ${help.tip}` : "";

  if (hpInfoTrapHandler) hpInfoTrapHandler();
  hpInfoTrapHandler = openDialog(els.hpInfoModal, closeHyperparameterInfo);
}

export function closeHyperparameterInfo() {
  if (hpInfoTrapHandler) {
    hpInfoTrapHandler();
    hpInfoTrapHandler = null;
  }
}

export function openHowToModal() {
  if (!els.howtoSteps.childElementCount) {
    for (const step of HOWTO_STEPS) {
      const article = document.createElement("article");
      article.className = "howto-step";
      let mediaHtml = "";
      if (step.image) {
        mediaHtml += `<div class="howto-figures">`;
        mediaHtml += `<img class="howto-figure" src="${step.image}" alt="${step.imageAlt || ""}" width="44" height="44" />`;
        for (const extra of step.extraImages || []) {
          mediaHtml += `<img class="howto-figure" src="${extra.src}" alt="${extra.alt}" width="44" height="44" />`;
        }
        mediaHtml += `</div>`;
      } else if (step.diagram) {
        mediaHtml = `<div class="howto-diagram" aria-hidden="true">${step.diagram}</div>`;
      }
      article.innerHTML = `
        <h4>${step.title}</h4>
        ${mediaHtml}
        <p>${step.text}</p>
      `;
      els.howtoSteps.appendChild(article);
    }
  }

  if (howtoTrapHandler) howtoTrapHandler();
  howtoTrapHandler = openDialog(els.howtoModal, closeHowToModal);
}

export function closeHowToModal() {
  if (howtoTrapHandler) {
    howtoTrapHandler();
    howtoTrapHandler = null;
  }
  if (els.howtoDismiss.checked) {
    localStorage.setItem(HOWTO_STORAGE_KEY, "1");
  }
}

export function bindEducation() {
  document.querySelectorAll("[data-hp-info]").forEach((btn) => {
    btn.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      openHyperparameterInfo(btn.dataset.hpInfo);
    });
  });

  els.howtoOpenBtn.addEventListener("click", () => openHowToModal());
  els.howtoCloseBtn.addEventListener("click", () => closeHowToModal());
  els.howtoGotItBtn.addEventListener("click", () => closeHowToModal());

  els.howtoModal.addEventListener("click", (event) => {
    if (event.target === els.howtoModal) closeHowToModal();
  });
  els.hpInfoModal.addEventListener("click", (event) => {
    if (event.target === els.hpInfoModal) closeHyperparameterInfo();
  });
  els.hpInfoCloseBtn.addEventListener("click", () => closeHyperparameterInfo());

  if (!localStorage.getItem(HOWTO_STORAGE_KEY)) {
    requestAnimationFrame(() => openHowToModal());
  }
}
