import { els } from "./dom.js";
import { appState } from "./state.js";

function formatTestDetails(details) {
  if (!details) return "";
  if (details.path) {
    return details.path.map((c) => `(${c[0]}, ${c[1]})`).join(" -> ");
  }
  return JSON.stringify(details, null, 2);
}

export function renderModelTests(modelTests) {
  if (!modelTests) {
    els.testsCard.classList.add("hidden");
    els.testsCard.setAttribute("aria-hidden", "true");
    appState.renderedTestsKey = null;
    return;
  }

  const key = JSON.stringify(modelTests.tests.map((t) => [t.id, t.passed, t.actual]));
  if (key === appState.renderedTestsKey) {
    els.testsCard.classList.remove("hidden");
    els.testsCard.setAttribute("aria-hidden", "false");
    return;
  }
  appState.renderedTestsKey = key;

  els.testsCard.classList.remove("hidden");
  els.testsCard.setAttribute("aria-hidden", "false");

  const { passed, total, allPassed } = modelTests;
  els.testsSummary.textContent = `${passed}/${total} passed`;
  els.testsSummary.classList.remove("is-pass", "is-fail");
  els.testsSummary.classList.add(allPassed ? "is-pass" : "is-fail");
  els.testsSubtitle.textContent = allPassed
    ? "All checks passed — greedy policy is ready"
    : "Some checks failed — expand a case to inspect expected vs actual";

  els.testsList.innerHTML = "";
  modelTests.tests.forEach((test, index) => {
    const item = document.createElement("article");
    item.className = `test-case ${test.passed ? "is-pass" : "is-fail"}`;
    item.setAttribute("role", "listitem");

    const head = document.createElement("button");
    head.type = "button";
    head.className = "test-case-head";
    head.setAttribute("aria-expanded", "false");
    head.innerHTML = `
      <svg class="test-case-chevron" viewBox="0 0 16 16" fill="none" aria-hidden="true">
        <path d="M6 4l4 4-4 4" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
      <span class="test-case-status ${test.passed ? "is-pass" : "is-fail"}" aria-hidden="true">
        ${test.passed ? "✓" : "✕"}
      </span>
      <span class="test-case-title">${test.name}</span>
      <span class="test-case-index">Case ${index + 1}</span>
    `;

    const body = document.createElement("div");
    body.className = "test-case-body";
    body.innerHTML = `
      <p class="test-case-desc">${test.description}</p>
      <div class="test-case-io">
        <div class="test-io-row">
          <span class="test-io-label">Expected</span>
          <p class="test-io-value">${test.expected}</p>
        </div>
        <div class="test-io-row">
          <span class="test-io-label">Actual</span>
          <p class="test-io-value ${test.passed ? "is-pass" : "is-fail"}">${test.actual}</p>
        </div>
        ${
          test.details
            ? `<div class="test-io-row">
          <span class="test-io-label">Details</span>
          <p class="test-io-value">${formatTestDetails(test.details)}</p>
        </div>`
            : ""
        }
      </div>
    `;

    head.addEventListener("click", () => {
      const open = item.classList.toggle("is-open");
      head.setAttribute("aria-expanded", open ? "true" : "false");
    });

    item.appendChild(head);
    item.appendChild(body);
    els.testsList.appendChild(item);
  });
}
