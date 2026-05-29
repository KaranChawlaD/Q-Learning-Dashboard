# Contributing to Q-Learning Dashboard

Thanks for your interest in contributing! This document covers how to set up a local development environment, report bugs, suggest enhancements, and submit pull requests.

For a project overview and end-user docs, see [`README.md`](README.md).

- [Code of Conduct](#code-of-conduct)
- [Local Development Setup](#local-development-setup)
- [Reporting Bugs](#reporting-bugs)
- [Suggesting Enhancements](#suggesting-enhancements)
- [Pull Request Workflow](#pull-request-workflow)
- [Coding Standards](#coding-standards)
- [Commit Message Style](#commit-message-style)
- [Manual Smoke Tests](#manual-smoke-tests)
- [Frontend Changes](#frontend-changes)
- [Documentation Updates](#documentation-updates)
- [License](#license)

## Code of Conduct

Be respectful, assume good intent, and keep discussions focused on the code. Personal attacks, harassment, and discriminatory language are not welcome.

## Local Development Setup

### 1. Prerequisites

- **Python 3.10+** (the project's Ruff config targets `py310`; older versions may work but are not tested)
- **Git**
- A modern browser for the dashboard (Chrome, Firefox, Edge, Safari)

### 2. Fork and clone

```bash
git clone https://github.com/<your-username>/Q-Learning.git
cd Q-Learning
git remote add upstream https://github.com/<original-owner>/Q-Learning.git
```

### 3. Create a virtual environment

```bash
# Windows (PowerShell)
python -m venv .venv
.venv\Scripts\Activate.ps1

# macOS / Linux
python -m venv .venv
source .venv/bin/activate
```

### 4. Install development dependencies

`requirements-dev.txt` includes everything in `requirements.txt` plus Ruff and pytest:

```bash
pip install -r requirements-dev.txt
```

### 5. Verify the install

Each of these should run cleanly:

```bash
python run.py --help                   # dispatcher help
python run.py train                    # ~5 seconds, writes assets/q_table.npy
python run.py web --no-browser --port 8765   # Ctrl+C to stop
pytest -q                              # unit tests pass
ruff check .                           # lint passes
ruff format --check .                  # formatting passes
```

If any of these fail on a fresh clone, that's a bug — please open an issue.

## Reporting Bugs

Before filing a bug:

1. Search the [issue tracker](../../issues) to see if it's already reported.
2. Try to reproduce on the latest `main`.
3. Make sure the reproduction is minimal — the smallest set of steps that triggers the issue.

When filing, include:

- **Environment**: OS + version, Python version (`python --version`), browser + version (for dashboard bugs), `pip freeze` output if you suspect a dependency
- **Steps to reproduce**: numbered, copy-pasteable
- **Expected behavior**: what you thought would happen
- **Actual behavior**: what actually happened
- **Logs**: full Python traceback for backend issues; browser DevTools console output for dashboard issues
- **Screenshots / screen recordings**: especially helpful for layout, animation, and chart issues
- **Q-table artifact** (`assets/q_table.npy` + `assets/q_meta.json`) if the bug depends on training state

If the bug is a security issue, do **not** open a public issue — email the maintainer instead.

## Suggesting Enhancements

For small, obvious improvements (typo fixes, CSS tweaks, minor refactors), feel free to open a pull request directly.

For anything larger — new features, dependency additions, architectural changes, breaking changes to artifact formats — please **open an issue first** to discuss the approach. This avoids wasted effort if the design needs to change.

When proposing an enhancement:

- Describe the problem you're solving, not just the solution you have in mind
- Reference any related items in the [Roadmap](README.md#roadmap)
- For UI changes, sketch the layout or attach a mockup
- For algorithm changes, briefly explain how it affects the Q-table format and whether existing artifacts will still load

## Pull Request Workflow

### 1. Sync with upstream

```bash
git fetch upstream
git checkout main
git merge upstream/main
```

### 2. Create a feature branch

Use a short, descriptive name. Suggested prefixes:

- `feat/` — new feature (e.g. `feat/dashboard-comparison-mode`)
- `fix/` — bug fix (e.g. `fix/heatmap-arrows-on-bank`)
- `refactor/` — internal restructuring with no behavior change
- `docs/` — documentation only
- `chore/` — build, deps, tooling

```bash
git checkout -b feat/your-feature-name
```

### 3. Make changes

- Keep PRs focused on a single concern. Multiple unrelated changes should be split into separate PRs.
- Update the README, in-code docstrings, and the [Version History](README.md#version-history) when behavior changes (see [Documentation Updates](#documentation-updates)).
- Don't commit generated artifacts (`assets/q_table.npy`, `assets/q_meta.json`) unless the change is specifically about the artifact format.
- Don't commit virtual environments, IDE files, or OS metadata (`.gitignore` covers the common ones).

### 4. Lint, format, and smoke-test

```bash
ruff format .
ruff check .
```

Then run the [Manual Smoke Tests](#manual-smoke-tests) appropriate for what you changed. Include `pytest -q` in the PR **Testing** section when you touch Python.

### 5. Commit

Follow the [Commit Message Style](#commit-message-style) below.

### 6. Push and open the PR

```bash
git push origin feat/your-feature-name
```

Then open a pull request against `main`. The PR description should include:

- **Summary** — 1-2 sentences on what changed and why
- **Changes** — bullet list of the substantive code/doc changes
- **Testing** — what you ran (`ruff`, `python run.py train`, dashboard click-throughs, etc.)
- **Screenshots** — required for any visual change to the dashboard or pygame modes
- **Linked issue** — `Fixes #123` / `Refs #123` if applicable
- **Breaking changes** — flagged explicitly, with a migration note

### 7. Review

- A maintainer will review and may request changes.
- Push additional commits to the same branch; they'll be squashed on merge unless the PR title says otherwise.
- Be patient — this is a small project run by volunteers.

## Coding Standards

### Python

- **Ruff** is the source of truth for formatting and linting. Config lives in `pyproject.toml` (`[tool.ruff]`). Don't override it locally.
- **Type hints** on public functions, dataclasses, and any new module-level constants. Existing code uses `from __future__ import annotations` so PEP 604 union syntax (`int | None`) is fine on Python 3.10+.
- **Docstrings** on public functions and modules — short, focused on intent, not on what the code obviously does.
- **No comments that just narrate code.** Write comments only to explain non-obvious tradeoffs or constraints.
- **Imports** are auto-sorted by Ruff (isort rules). First-party packages (`qlearning`, `web`) are configured.
- **Avoid new dependencies** unless they're genuinely needed. If you do add one, pin it in `requirements.txt` (or `requirements-dev.txt` for dev-only) and explain why in the PR.

### Algorithm and environment changes

- **`qlearning/env.py` defines grid dimensions, actions, and the default layout.** CLI `train` and `manual` use `DEFAULT_LAYOUT`; the web dashboard sends a custom `GridLayout` via the `start_training` WebSocket command. Changing validation rules or `GridLayout` affects the dashboard first — keep `parse_layout` / `validate_layout` in sync with the frontend editor.
- **The web dashboard reuses `qlearning/train.py`'s `env_step`, `choose_action`, `epsilon_for`, `greedy_path`, and `save_artifacts` directly** (with a per-session `GridLayout`). If you change their signatures, update `web/server.py:Trainer` and `qlearning/evaluate.py` in the same PR.
- **Post-training checks** live in `qlearning/evaluate.py` and are surfaced in the dashboard's model-tests panel. Update tests in `tests/test_evaluate.py` when you add or change cases.
- **Q-table artifact format changes are breaking** for anyone with a saved `assets/q_table.npy`. Bump the version history accordingly and ideally add a load-time compatibility check.
- **Determinism**: training uses `random.Random(cfg.seed)`. Don't introduce non-determinism (no bare `random.*` calls, no `np.random` without a seeded generator) — it makes regressions much harder to bisect.

## Commit Message Style

Use **imperative mood**, like the message is finishing the sentence "If applied, this commit will…":

- Good: `Add restart button to dashboard`
- Good: `Fix heatmap arrow direction on epsilon=0 cells`
- Bad: `Added restart button` / `Fixes some bugs` / `Updates`

Format:

```
<short subject line, ≤ 72 chars, imperative, no trailing period>

<optional body explaining the why, wrapped at ~72 chars. The "what"
should already be clear from the diff; the body is for context that
isn't obvious from reading the code.>

Refs #123
```

One commit per logical change is preferred. Squash fixup commits before opening the PR (or let the maintainer squash on merge).

## Manual Smoke Tests

Run the relevant subset of these checks before opening a PR. Automated coverage lives in `tests/` (`pytest -q`).

**For any Python change:**

```bash
ruff format .
ruff check .
pytest -q
python run.py train       # completes, writes assets/q_table.npy (default layout)
```

**For dashboard backend changes (`web/server.py`, `qlearning/evaluate.py`):**

```bash
python run.py web --no-browser --port 8765
# In a browser, hit http://127.0.0.1:8765
# Setup: drag agent + bank onto grid, add buildings, Start Training
# Training: status pill, heatmap, agent moves, chart updates,
# pause/resume, speed selector (1-6), save, model tests after completion
# Reset (R): returns to environment editor
# Watch the browser DevTools console for errors
```

**For dashboard frontend changes (`web/static/*`):**

- Hard-refresh the page (Ctrl+Shift+R) to bypass cached assets
- **Setup mode:** left card shows Environment + Design controls; right card shows Hyperparameter Lab
- **Setup mode:** palette hides agent/bank after placement; each building type can be placed multiple times; validation message and Start Training enable/disable correctly
- **Setup mode:** unsolvable layouts (no start→bank path through free cells) show an error and keep Start Training disabled
- **Hyperparameter Lab:** slider/number inputs stay in sync; Reset defaults restores initial values; invalid combinations (for example epsilon end > epsilon start) block training with a visible error
- **Training mode:** metrics, controls, chart, and heatmap appear after Start Training
- Test at multiple viewport widths (laptop ~1366×768, ultrawide, mobile ~400px wide)
- Verify keyboard shortcuts in training mode (`Space`, `1`–`6`, `S`, `R`, `←`/`→`)
- Expand model-test rows after training completes; confirm pass/fail details render
- Watch the DevTools console — any uncaught error fails the smoke test

When adding or moving frontend logic, keep modules small and update the table in [Frontend Changes](#frontend-changes) if you add a new file.

**For algorithm changes (`qlearning/train.py`, `qlearning/env.py`):**

- Run `python run.py train` on the **default layout** and verify the greedy path is still **19 steps** (`seed=42`)
- Verify the 100-episode average length converges to roughly **20** steps on the default map
- If you change layout validation, include at least one test proving solvable layouts pass and unsolvable layouts fail
- If you change `TrainConfig` defaults, justify it in the PR — the existing values are tuned for the default map
- Run `pytest -q`; add or update tests when behavior changes

**For manual mode changes (`qlearning/manual.py`):**

- `python run.py manual` opens, arrow keys move the agent, `Esc` quits
- Walking into obstacles or off the grid leaves the agent in place

## Frontend Changes

The dashboard frontend is intentionally **vanilla HTML/CSS/JS with no build step**. There is no `package.json`, no bundler, no transpiler, no framework. The UI is loaded as **native ES modules** (`<script type="module" src="/static/js/main.js">`).

This is a deliberate constraint — it keeps the project trivial to install, debug, and serve. **Please don't introduce a build pipeline without discussing it in an issue first.**

### Module layout (`web/static/js/`)

| File | Responsibility |
|------|----------------|
| `main.js` | Entry point: binds DOM events, starts WebSocket |
| `state.js` | Mutable session state (socket, layout draft, sprites) |
| `constants.js` | Grid size, palette items, sprite paths |
| `dom.js` | Cached `document.getElementById` references |
| `commands.js` | Outbound WebSocket messages |
| `websocket.js` | Connection lifecycle and inbound message handling |
| `hyperparams.js` | Setup-time hyperparameter controls + validation |
| `layout.js` | Layout draft helpers and validation copy |
| `setup-editor.js` | Palette, drag-and-drop, piece placement |
| `grid.js` | Policy heatmap canvas rendering |
| `chart.js` | Steps-per-episode chart |
| `model-tests.js` | Post-training test-case panel |
| `render-loop.js` | `requestAnimationFrame` scheduling |
| `ui.js` | Panel visibility, status pill, metrics text |
| `sprites.js` | Image loading |
| `canvas.js` / `color.js` | Low-level drawing utilities |

What that means in practice:

- Use modern syntax that works in current browsers without transpilation (ES2020+ is fine; `async/await`, optional chaining, nullish coalescing, etc.)
- No TypeScript, no JSX, no Sass — plain `.js`, `.html`, `.css`
- No npm dependencies — load anything external from a CDN with an integrity hash, or vendor it into `web/static/`
- CSS variables for theming (already wired up in `:root`); avoid hardcoding colors mid-stylesheet
- Prefer adding a new module over growing an existing one past ~250 lines; keep imports acyclic (`commands.js` and `state.js` are shared leaves)

## Documentation Updates

Update documentation in the same PR as the change. Specifically:

- **README.md** — if you change subcommands, options, file layout, or user-visible behavior
- **README.md → Version History** — add a new entry for any user-visible change. Increment the version sensibly:
  - Patch (`v0.X.Y` → `v0.X.Y+1`): bug fixes, doc-only changes, internal refactors
  - Minor (`v0.X.Y` → `v0.X+1.0`): new features, new subcommands, new options
  - Major (`v0.X.Y` → `v1.0.0+`): breaking artifact-format or CLI changes
- **CONTRIBUTING.md** (this file) — if the workflow itself changes
- **Docstrings** — if the function's behavior or contract changes

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE) that covers the project. Don't include code or assets you don't have the right to relicense under MIT.
