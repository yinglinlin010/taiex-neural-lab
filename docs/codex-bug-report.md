## Scheduled maintenance checkpoint (2026-10-29 12:54 snapshot; scale-safe momentum angle)

- **Latest review / reproduced defect:** `artifacts/regression-monitor/latest-checks.json` at `2026-10-29T12:54:45+08:00` is WARN (41 PASS, 2 WARN, 2 intentional SKIP). Local stock coverage is 10/10 and locked-data isolation passes. Training smoke was skipped because a user training job is active; final-test confirmation UI remains skipped by policy. The other WARN is viewport bounding-box drift from the prior monitor run (network 22px, results 120px, loss 120px, metrics 142px); this snapshot does not establish its cause. Independently reproduced a current Step-20 numerical defect: `v=(1e-200,2e-200), g=(2e-200,1e-200)` contains finite nonzero vectors with a defined angle, but the former `dot/(|v||g|)` formula underflowed its denominator and rejected the result.
- **Exact defect fix:** `web/app.js` now computes cosine and projections from a normalized gradient and normalized velocity components. The angle and projection remain defined for the tiny finite example without multiplying tiny norms. Added an executable regression case and extended the safe browser predicate to cover the tiny-vector angle.
- **Roadmap advance:** Guided Step 20 now visibly teaches that positive rescaling of either nonzero vector leaves their angle unchanged. The synthetic example has cosine 0.8 and angle 36.87° at ordinary and `1e-200` scales; the note is part of the browser acceptance predicate. Updated `web/index.html`, `scripts/regression_monitor.py`, `tests/test_system.py`, and `docs/learning-guide.md`. This advances a bounded neural-network geometry lesson, not training or model-quality evidence.
- **Verification:** Focused Step-20 tests: `2 passed, 101 deselected`, one existing Starlette/httpx deprecation warning. Safe project suite: `221 passed, 1 deselected`, same warning. `node --check web/app.js`, Python AST parsing for monitor/tests, and scoped `git diff --check` pass. No post-edit browser rendering is claimed; the 12:54 screenshots predate this change.
- **Remaining / next checkpoint:** Run browser-only Step-20 acceptance at desktop and 390px for ordinary/tiny positive rescaling, 2D/3D, zero vectors, blank and invalid inputs. Separately inspect the observed viewport drift against the approved reference before attributing or changing layout. Keep training smoke and locked-test UI skipped while the user's training job is active. Popular-stock expansion beyond local 10/10 needs an authorized local source; cross-symbol magnitude comparisons need compatible ordinary OOF summaries. No credentials, locked observations, or `final-test-*.json` were accessed/changed/consumed; no final test, market refresh, training, deployment, publication, or external messaging occurred.

## Scheduled maintenance checkpoint (2026-10-29, angle readout and review freshness)

- **Latest review / reproduced documentation defect:** The current `artifacts/regression-monitor/latest-checks.json` is timestamped `2026-10-29T11:07:29+08:00` and reports 43 PASS, 0 WARN, 0 FAIL, plus intentional training-smoke and locked-test UI SKIPs. The leading review summaries still describe older 09:17 / 10:31 failures. Comparing them with the current JSON and the embedded 11:07 monitor sections reproduces stale review status; no current application failure was reported. Updated this checkpoint so the active review state is clear; older entries remain historical.
- **Exact feature change:** Guided Step 20's 2D/3D momentum vector readout now shows the angle `θ=arccos(v·g/(|v||g|))` in degrees alongside direction cosine and projection. Synthetic defaults render 53.40° for `v=(1,2,2), g=(2,1,0)` and 36.87° for `v=(1,2), g=(2,1)`; aligned, opposite, perpendicular, and zero-vector cases are covered, with zero-vector angle undefined. Updated `web/app.js`, `scripts/regression_monitor.py`, `tests/test_system.py`, and `docs/learning-guide.md`. This advances a bounded neural-network learning milestone only; it is not training or model-quality evidence.
- **Verification:** Focused Step 20 tests: 2 passed, 99 deselected. Safe project suite: 219 passed, 1 deselected, with one existing Starlette/httpx deprecation warning. `node --check web/app.js`, Python AST parsing for monitor/tests, and scoped `git diff --check` pass. The 11:07 desktop/mobile browser PASS predates this angle addition; post-edit viewport acceptance is not claimed.
- **Remaining / next checkpoint:** Run browser-only Step 20 acceptance at desktop and 390px for 2D/3D angle output, zero vectors, blank and invalid inputs; keep training smoke and locked-test UI skipped. Popular-stock local coverage remains 10/10 and expansion needs an authorized local source. Cross-symbol rise/fall magnitude teaching still needs comparable ordinary OOF summaries. No credentials, locked observations, or `final-test-*.json` were accessed/changed/consumed; no final test, market refresh, training, deployment, publication, or external messaging occurred.

## Scheduled maintenance checkpoint (2026-10-29 10:33 +08:00, vector-boundary monitor repair and projection lesson)

- **Latest review evidence:** `artifacts/regression-monitor/latest-checks.json` at `2026-10-29T10:31:55+08:00` reports FAIL in the aggregate 「報酬與區間互動教學」 check. The named clause is `方向餘弦邊界=False`; other listed checks include popular-stock local coverage 10/10 and locked-data isolation PASS. Training smoke and the one-time locked-test UI are SKIP. The saved snapshot records the suite result as 220 passed with one existing deprecation warning.
- **Highest-priority concrete defect, independently reproduced:** The browser monitor's 3D fixture is `v=(1,2,2), g=(2,1,0)`. Current calculation returns `|v|=3` and `|g|=√5≈2.2361`; the monitor incorrectly required both norms to equal 3. A direct Node execution of the current calculation reproduces the false predicate while cosine `0.5962847940` and the other boundary cases are correct. This is a stale monitor expectation, not an arithmetic defect.
- **Exact defect fix:** `scripts/regression_monitor.py` now compares `gNorm` with `Math.sqrt(5)` at `1e-12` tolerance. `tests/test_system.py` asserts the corrected monitor contract and rejects the old equality.
- **Roadmap increment:** The Guided Step 20 synthetic momentum-vector lesson now visibly checks the orthogonal decomposition `|v|² = parallel² + perpendicular²`. Its default 3D example reports both sides as `9.0000`; switching to 2D reports both as `5.0000`. The browser monitor checks these visible outputs, renderer acceptance asserts both cases, and `docs/learning-guide.md` now correctly states `|g|=√5` for the 3D example. This is a bounded neural-network learning aid using synthetic vectors, not training or model-quality evidence.
- **Verification:** `./.venv/bin/python -m pytest -q tests/test_system.py -k 'momentum_direction_geometry_and_input_boundaries or momentum_direction_preloads_non_degenerate_three_dimensional_example'` → 2 passed, 99 deselected, one existing Starlette/httpx deprecation warning. `node --check web/app.js`, Python AST parsing for monitor/tests, and scoped `git diff --check` pass. No post-edit browser render was run; the saved browser snapshot predates the change.
- **Remaining / next checkpoint:** Run only browser acceptance for Guided Step 20 at desktop and 390px, checking 2D/3D decomposition, zero vectors, blank input, and invalid input. Keep training smoke and locked-test UI skipped. Popular-stock expansion beyond local 10/10 still needs an authorized local source; cross-symbol rise/fall magnitude learning still needs compatible ordinary OOF summaries. The broader neural-network learning objective remains incomplete. No credentials, locked observations, or `final-test-*.json` were accessed, changed, or consumed; no one-time final test, training, market refresh, deployment, publication, or external messaging occurred.

## Scheduled maintenance checkpoint (2026-10-29, Step 20 diagnosis and selectable vector dimension)

- **Latest review evidence:** `artifacts/regression-monitor/latest-checks.json` at `2026-10-29T09:17:34+08:00` is FAIL. Safe regression tests passed (218 passed, one existing Starlette/httpx deprecation warning), popular-stock local coverage is 10/10, and locked-data isolation passed. Training smoke and one-time locked-test UI were skipped. The latest run could not fetch the local preview (`URLError: Operation not permitted`) and the browser check stopped because the project environment lacks `PIL`; it therefore provides no current browser verdict for Guided Step 20.
- **Highest-priority defect disposition and exact fix:** The prior saved Step 20 aggregate failure could not be reproduced from current renderer code. A direct Node execution confirmed its default three-step output, reversal/weight-rise explanation, and blank-input guidance match the monitor's expectations. The monitor previously reduced nine meaningful UI assertions to one boolean, hiding which assertion failed. `scripts/regression_monitor.py` now returns named Step 20 checks (visibility, step, each update, reversal, trace, blank recovery, 2D and 3D output) and includes them in failure detail. The current monitor also imports Pillow and Playwright, but `requirements.txt` declared neither; both are now declared and covered by a dependency-manifest test. A later browser run can identify the failing subcondition once the environment is provisioned.
- **Roadmap increment:** Guided Step 20 now has an explicit two/three-dimensional selector. In 2D, third-component fields are hidden and excluded from calculation; in 3D, all six components are used. The default remains the non-degenerate `v=(1,2,2), g=(2,1,0)` example. Updated `web/index.html`, `web/app.js`, `tests/test_system.py`, `scripts/regression_monitor.py`, `requirements.txt`, and `docs/learning-guide.md`. This is synthetic geometry teaching, not training or model-quality evidence.
- **Verification:** `./.venv/bin/python -m pytest -q tests/test_system.py -k 'momentum_direction or regression_monitor_dependencies'` → 3 passed, 97 deselected, one existing deprecation warning. `node --check web/app.js`, Python AST parsing for monitor/tests, and scoped `git diff --check` pass. The monitor's own 218-test suite also passed. Live desktop/390px rendering remains unverified because the browser prerequisites/local connection failed as recorded above. An initial system-Python bytecode compile attempt was blocked writing outside the project; it was replaced with an in-memory AST parse.
- **Remaining / next checkpoint:** Install the newly declared maintenance dependencies and Playwright browser runtime in the project environment, and provide an allowed local preview path; then rerun browser-only Step 20 at desktop and 390px for both dimensions, zero vectors, blank input, and invalid values. Keep training smoke and locked-test UI skipped. Popular-stock expansion beyond local 10/10 still needs an authorized local source; real cross-symbol rise/fall magnitude learning needs comparable ordinary OOF summaries. No credentials, locked observations, or `final-test-*.json` were accessed/changed/consumed; no one-time final test, market refresh, training, deployment, publication, or external messaging occurred.

## Scheduled maintenance checkpoint (2026-10-29, 3D momentum direction example)

- **Latest review / reproduced maintenance defect:** `artifacts/regression-monitor/latest-checks.json` at `2026-10-29T08:41:22+08:00` is PASS (45 checks, no FAIL/WARN; pytest 217 passed, 1 warning). Local popular-stock consistency 10/10 and locked-data isolation PASS; training smoke and one-time locked-test UI are intentional SKIP. The previous leading checkpoint cited 08:06, reproducing stale review status by timestamp comparison; no current runtime failure appears in the snapshot.
- **Exact change:** Step 20's advertised 3D direction controls defaulted `v₃=g₃=0`, so the initial example was only 2D. It now opens with `v=(1,2,2), g=(2,1,0)` and labels this a 3D example. Output is dimension 3, `v·g=4`, cosine `0.5963`, parallel component `1.7889`, perpendicular magnitude `2.4083`. Updated `web/index.html`, `tests/test_system.py`, and `docs/learning-guide.md`.
- **Milestone / evidence:** Advanced a bounded synthetic neural-network learning subtask: learners can observe a non-degenerate three-dimensional momentum decomposition. Focused check `./.venv/bin/python -m pytest -q tests/test_system.py -k 'momentum_direction'` → 2 passed, 97 deselected, 1 existing Starlette/httpx deprecation warning. `node --check web/app.js` and scoped `git diff --check` pass. This is geometry instruction, not training or model-quality evidence. Latest browser snapshot predates the edit; post-edit rendering is unverified.
- **Remaining / next checkpoint:** Verify default 3D plus editable 2D/3D, zero, blank, and invalid cases at desktop and 390px in browser-only mode; refresh only safe browser evidence. Keep training smoke and locked-test UI skipped. Popular-stock expansion beyond local 10/10 needs an authorized local source; real cross-symbol magnitude learning needs comparable ordinary OOF summaries. No credentials, locked observations, or `final-test-*.json` were accessed/changed; no final test, market refresh, training, deployment, publication, or external messaging.

## Scheduled maintenance checkpoint (2026-10-29, momentum direction dimension lesson)

- **Latest review / defect disposition:** `artifacts/regression-monitor/latest-checks.json` timestamp `2026-10-29T08:06:14+08:00` is PASS. It records 217 passing tests, local popular-stock consistency 10/10, and locked-data isolation PASS; training smoke and one-time locked-test UI are SKIP. No new application defect was independently reproduced; the earlier 07:30 monitor failure was a stale predicate, later PASS snapshot supersedes it.
- **Roadmap increment / exact change:** Guided step 20 momentum direction now accepts arbitrary equal-dimension velocity and gradient vectors through a generalized projection calculation; the lesson visibly offers a 3D example alongside the existing 2D interpretation and reports dimension count, signed parallel component, and perpendicular magnitude. Zero vectors remain explicitly undefined; blank, unequal dimension, and non-finite cases are rejected. This is synthetic neural-network learning, not training or model-quality evidence.
- **Verification:** `./.venv/bin/python -m pytest -q tests/test_system.py -k 'momentum_direction_geometry_and_input_boundaries or monitor'` → 21 passed, 77 deselected, one existing Starlette/httpx deprecation warning. `node --check web/app.js`, Python AST parsing for monitor/tests, and scoped `git diff --check` pass. The saved browser snapshot predates this change; post-edit desktop/390px rendering is not claimed.
- **Remaining / next checkpoint:** Run browser-only step-20 acceptance at desktop and 390px for 2D/3D, zero-vector, blank, and invalid cases; keep training smoke and locked-test UI skipped. Broader neural-network learning remains incomplete. Popular-stock expansion beyond local 10/10 requires an authorized local source; real cross-symbol magnitude learning needs comparable ordinary OOF summaries. No credentials, protected observations, or `final-test-*.json` were accessed/changed/consumed; no final test, market refresh, training, deployment, publication, or external messaging.

## Scheduled maintenance checkpoint (2026-10-29, momentum feedback and acceptance repair)

- **Latest AGY review / independently reproduced defect:** `artifacts/regression-monitor/latest-checks.json` timestamp `2026-10-29T07:30:40+08:00` reports FAIL only in the aggregate Guided lesson check: “第二十步兩步動量與方向=False”; pytest is 217 passed / 1 warning, local popular-stock consistency 10/10, locked-data isolation PASS, while training smoke and one-time locked-test UI are SKIP. Current code and focused renderer tests show lesson 20 now has three gradients/updates, but the browser predicate still expected the old two-step text and six-field blank-input message. The monitor therefore failed on stale acceptance criteria, not on the calculation.
- **Exact changes:** Updated `scripts/regression_monitor.py` to check the three-step output, the third-step reversal and weight rise, and seven-field blank-input guidance. Updated `tests/test_system.py` to guard the three-step monitor contract. In `web/app.js`, the visible lesson now explicitly reports whether velocity reversed and whether weight rose/fell/stayed fixed after the third gradient, with before/after values.
- **Roadmap milestone advanced:** Guided lesson 20 now makes delayed momentum reversal directly observable: default velocity changes `1.8050 → -0.3755` and weight rises `1.67450 → 1.71205` despite a negative third gradient. This is fixed-gradient synthetic teaching, not model training or model-quality evidence.
- **Verification:** Focused tests → `2 passed, 96 deselected`; safe suite `./.venv/bin/python -m pytest -q -k 'not public_api_and_async_validation_job'` → `216 passed, 1 deselected, 1 existing Starlette/httpx deprecation warning`; `node --check web/app.js`, Python AST parsing, and `git diff --check` pass. The saved AGY browser snapshot predates these edits; no post-edit browser or desktop/390px render is claimed.
- **Remaining / next checkpoint:** Run browser-only lesson-20 acceptance at desktop and 390px for default, edited, and blank inputs; do not run training smoke or locked-test UI. Keep the broader neural-network learning goal incomplete. Popular-stock expansion beyond local 10/10 needs an authorized local source; real cross-symbol magnitude lessons need comparable ordinary OOF summaries. No credentials, protected observations, or `final-test-*.json` were accessed/changed/consumed; no final test, market refresh, training, deployment, publication, or external messaging.

## Scheduled maintenance checkpoint (2026-10-29, guided-tab state in weight-decay acceptance)

- **Latest AGY review / reproduced defect:** `artifacts/regression-monitor/latest-checks.json` at `2026-10-29T03:18:18+08:00` is FAIL only for the combined 「報酬與區間互動教學」 check; the final clause is `純 SGD 權重衰減=False`. Its safe pytest snapshot is 215 passed / 1 deselected, popular-stock local coverage is 10/10, and locked-data isolation PASS; training smoke and locked-test UI are SKIP. Comparing current predicate sequencing found that the weight-decay check called `guided_fixture()` (which ensures Guided mode) but then ran a second raw `page.evaluate()` after subsequent checks had switched away from that tab. The content fixture therefore queried hidden Guided DOM and reported false.
- **Exact defect fix:** Changed `scripts/regression_monitor.py` so the weight-decay browser acceptance also runs through `guided_fixture()`. Its default values, edited values, and blank-input checks are retained. The renderer and arithmetic did not need changes.
- **Bounded milestone advanced:** Reliable automated acceptance now exercises the existing visible pure-SGD coupled-L2 / decoupled-weight-decay comparison in Guided mode. It checks default equality (both 1.9300), edited equality (both 0.4300), and blank-input feedback. This is synthetic learning only, not training or model-quality evidence.
- **Verification:** `./.venv/bin/python -m pytest -q tests/test_system.py -k 'weight_decay_comparison_matches_coupled_l2_for_sgd or monitor'` → 21 passed, 77 deselected, 1 existing Starlette/httpx deprecation warning. Safe project selection `./.venv/bin/python -m pytest -q -k 'not public_api_and_async_validation_job'` → 215 passed, 1 deselected, same warning. The saved AGY JSON is pre-fix; no post-fix browser/desktop/390px run is claimed.
- **Remaining / next checkpoint:** Run browser-only guided acceptance at desktop and 390px for default, edited, and blank inputs; preserve training smoke and locked-test UI skips. Broader neural-network learning remains incomplete. Popular-stock expansion beyond local 10/10 needs an authorized local source; cross-symbol magnitude instruction needs comparable ordinary OOF summaries. No credentials, protected observations, or `final-test-*.json` accessed/changed/consumed; no one-time final test, market refresh, training, deployment, publication, or external messaging.

## Scheduled maintenance checkpoint (2026-10-29, guided lesson fixture and weight-decay visibility)

- **Latest AGY review evidence:** `artifacts/regression-monitor/latest-checks.json` at `2026-10-29T01:28:32+08:00` is FAIL only for the aggregate 「報酬與區間互動教學」 predicate; its final clause is `純 SGD 權重衰減=False`. The same snapshot reports 208 passed / 1 deselected, popular-stock local coverage 10/10, and locked-data isolation PASS; training smoke and locked-test UI are SKIP.
- **Independent reproduction and defect:** The current UI hid the weight-decay exercise unless `lessonIndex===25`, and the monitor also hard-coded index 25 for L2 and weight-decay fixture setup. Current lesson structure makes this positional coupling brittle; focused source inspection plus executable renderer checks confirm the exercise is intended to accompany the L2 lesson. This created a user-visible missing interaction and a monitor false negative when lesson ordering changed.
- **Exact change:** `web/app.js` now finds the L2 lesson by its stable title and shows the weight-decay exercise with that lesson. `scripts/regression_monitor.py` locates both L2 and weight-decay browser fixtures by lesson title. `tests/test_system.py` now asserts that stable fixture locator remains present.
- **Roadmap milestone advanced:** The guided L2 lesson now reliably presents its pure-SGD coupled-L2 / decoupled-weight-decay comparison, including editable inputs and invalid-input feedback. This is a synthetic learning aid only; no model training or quality claim. Popular-stock coverage remains 10/10; adding symbols requires an authorized local data source.
- **Verification:** focused tests: `2 passed, 95 deselected`; safe project suite `./.venv/bin/python -m pytest -q -k 'not public_api_and_async_validation_job'`: `208 passed, 1 deselected, 1 warning` (existing Starlette/httpx deprecation). `node --check web/app.js`, Python AST parsing for monitor/tests, and scoped `git diff --check` pass. The saved monitor JSON is pre-fix; full monitor/browser desktop and 390px acceptance was not run.
- **Remaining / next checkpoint:** Run safe browser-only monitor acceptance for the guided L2/weight-decay interaction at desktop and 390px; update the saved monitor snapshot only through the approved safe monitor path, keeping training smoke and locked-test UI skipped. Continue the broader neural-network milestone; cross-symbol magnitude learning still needs comparable ordinary OOF summaries. No credentials, protected observations, or `final-test-*.json` were read/written/consumed; no final test, market refresh, training, deployment, publication, or external messaging.

## Scheduled maintenance checkpoint (2026-10-28, monitor interpreter and L2 baseline comparison)

- **Latest review evidence and reproduced defect:** `artifacts/regression-monitor/latest-checks.json` records a 2026-10-28 22:23 FAIL: its safe pytest selection had one collection error. Running the same selection with system Python 3.9 reproduced `ModuleNotFoundError: No module named 'mcp'` in `tests/test_paper_agent.py`; `mcp>=1.12,<2.0` is declared in `requirements.txt` and the project `.venv` contains it. The monitor used `sys.executable`, so a scheduled run inherited the caller interpreter instead of the project environment.
- **Exact defect fix:** `scripts/regression_monitor.py` now chooses an executable project `.venv` Python (Unix or Windows layout), falling back to `sys.executable` only when no project interpreter exists. Monitor output records the chosen interpreter. Added `test_monitor_pytest_prefers_project_virtualenv_and_falls_back` to cover both selection and fallback.
- **Roadmap increment:** Step 26 now explains the λ=0 baseline beside the regularized optimum: at λ=0, the minimum remains the data objective's preferred `w=1`; for λ>0 it moves toward zero. Added observable rendered-output acceptance, browser-monitor clause coverage, and a learning-guide note. This is a synthetic one-parameter lesson, not model-training or quality evidence.
- **Verification:** focused tests → `2 passed, 94 deselected`; monitor's actual safe pytest runner → `206 passed, 1 deselected, 1 warning`. The warning is an existing Starlette/httpx deprecation. `node --check web/app.js`, Python compilation, and scoped `git diff --check` pass. The saved JSON remains pre-fix evidence; no full browser/desktop/390px check was run after this edit.
- **Remaining / next checkpoint:** Run safe Step-26 browser acceptance at desktop and 390px for λ=0 and λ=0.1 optimum outputs plus learning-rate stability cases; keep training smoke and locked-test UI excluded. Popular-stock coverage remains 10/10 pending an authorized local source; cross-symbol magnitude lessons still need comparable ordinary OOF summaries. No credentials, protected observations, or `final-test-*.json` were accessed/changed/consumed; no final test, market refresh, training, deployment, publication, or external messaging.

## Scheduled maintenance checkpoint (2026-10-28, L2 regularized optimum)

- **Latest review evidence:** `artifacts/regression-monitor/latest-checks.json` is timestamped `2026-10-28T21:49:18+08:00`, overall PASS with 45 checks and no FAIL/WARN. Its saved safe-suite snapshot is 184 passed / 1 deselected; local popular-stock coverage is 10/10 and locked-data isolation passes. Training smoke and one-time locked-test UI are SKIP.
- **Highest-priority independently reproduced defect:** The active synthetic objective `L(w)=(w−1)²+λw²` had no visible minimum explanation despite claiming L2 pulls weights toward zero. Setting the gradient `2(w−1)+2λw` to zero gives `w*=1/(1+λ)`, so at λ=0.1 the optimum is 0.9091 rather than the data-only optimum 1. The previous UI omitted this central tradeoff.
- **Exact fix / milestone:** Step 26 calculator now returns the analytic optimum; the visible result and explanatory paragraph show it, the renderer test asserts 0.9091, the browser monitor checks the clause independently, and the learning guide records the derivation and limitation. This advances the incomplete neural-network learning milestone with a synthetic interactive concept, not model training or quality evidence.
- **Verification:** `python3 -m pytest -q tests/test_system.py -k l2_regularization_lesson_calculates_data_and_penalty_gradients` → 1 passed, 94 deselected. The first run exposed a missing HTML explanation; after adding it, the focused rerun passes.
- **Remaining / next checkpoint:** Run safe Step-26 browser acceptance at desktop and 390px after the source edit, including λ=0 and λ=0.1 optimum checks; do not run training smoke or locked-test UI. Popular-stock coverage remains 10/10 pending an authorized local source, and real cross-symbol magnitude lessons still need comparable ordinary OOF summaries. No credentials, protected observations, or `final-test-*.json` were accessed; no final test, market refresh, training, deployment, publication, or external messaging.

## Scheduled maintenance checkpoint (2026-10-28 21:30 +08:00, L2 learning-rate stability)

- **Latest AGY review / defect disposition:** `artifacts/regression-monitor/latest-checks.json` at `2026-10-28T21:11:11+08:00` is PASS across 45 checks with no FAIL/WARN; its saved safe suite is 184 passed / 1 deselected. Local popular-stock coverage is 10/10 and locked-data isolation passes; training smoke and one-time locked-test UI are SKIP. I independently probed the active L2 calculator's finite-result boundary with allowed rates and found no accepted non-finite deltas; the earlier extreme-rate candidate was rejected by existing guards. No current higher-priority concrete defect reproduced, so no defect fix is claimed.
- **Roadmap increment / exact change:** Step 26 now derives the critical step size for its synthetic objective `L(w)=(w−1)²+λw²`: `η*=1/(1+λ)`. It explains three observable regions: below the limit the error contracts, at the limit it alternates without shrinking, and above it the error grows. With λ=0.1 the visible threshold is 0.9091; acceptance exercises η=0.5, the threshold, and η=2. The learning guide states this one-dimensional quadratic result does not establish stability for a multi-layer network or real training. This advances the incomplete neural-network learning milestone only; it is not training or model-quality evidence.
- **Exact files changed:** `web/app.js`, `web/index.html`, `scripts/regression_monitor.py`, `tests/test_system.py`, and `docs/learning-guide.md`.
- **Verification:** `python3 -m pytest -q tests/test_system.py -k l2_regularization_lesson_calculates_data_and_penalty_gradients` → `1 passed, 94 deselected`; `node --check web/app.js`, Python AST parsing of tests/monitor, and scoped `git diff --check` pass. The browser fixture includes named stable/critical/divergent cases but was not run this checkpoint; the JSON is pre-edit evidence.
- **Remaining / next checkpoint:** Keep the broader neural-network goal incomplete. Run browser-only Step 26 at desktop and 390px, including λ changes and η below/equal/above the threshold, alongside cancellation, blank input, and overshoot; continue excluding training smoke and locked-test UI. Popular-stock coverage remains 10/10; expansion needs an authorized local source. Real cross-symbol rise/fall magnitude learning still needs comparable ordinary OOF summaries. No credentials, protected observations, or `final-test-*.json` accessed/changed/consumed; no final test, market refresh, training, deployment, publication, or external messaging.

## Scheduled maintenance checkpoint (2026-10-28 16:10 +08:00, L2 gradient contribution reading)

- **Latest review:** `artifacts/regression-monitor/latest-checks.json` at `2026-10-28T15:52:31+08:00` reports PASS with no FAIL/WARN; local popular-stock coverage is 10/10 and locked-data isolation passes. Training smoke and locked-test UI are SKIP. I independently reviewed the current L2 renderer and monitor contracts; no higher-priority defect reproduced.
- **Roadmap increment:** Step 26 now displays each component's signed contribution to the combined gradient. For default `w=2, λ=0.1`, data and penalty contribute 83.3% and 16.7%; at exact cancellation, both shares are explicitly undefined because the denominator is zero. The lesson explains negative or over-100% contributions as opposing terms that partly cancel. This is an observable synthetic neural-network learning increment, not training or model-quality evidence.
- **Exact changes:** `web/app.js` renders the contribution percentages; `web/index.html` explains signed shares and the zero-denominator case; `docs/learning-guide.md` records the examples; `scripts/regression_monitor.py` asserts both default and cancellation output; `tests/test_system.py` provides executable renderer checks.
- **Verification:** Focused test `python3 -m pytest -q tests/test_system.py -k l2_regularization_lesson_calculates_data_and_penalty_gradients` passes (`1 passed, 94 deselected`). Initial runs found missing monitor coverage and a stale HTML-copy assertion; both were updated, and the final focused run passes. Post-edit browser/desktop/390px rendering and the full suite are not verified.
- **Remaining / next checkpoint:** Keep the neural-network milestone incomplete. Run browser-only step 26 at desktop and 390px and check default, exact cancellation, λ=0, blank input, and overshoot, excluding training smoke and locked-test UI. Popular-stock expansion beyond local 10/10 needs an authorized local source; real cross-symbol magnitude lessons need comparable ordinary OOF summaries. No credentials, protected observations, or `final-test-*.json` accessed/changed/consumed; no final test, market refresh, training, deployment, or publication.

## Scheduled maintenance checkpoint (2026-10-28 15:16 +08:00, L2 monitor diagnostics)

- **Latest review:** `artifacts/regression-monitor/latest-checks.json` at `2026-10-28T15:16:32+08:00` is PASS: 184 passed / 1 deselected, local symbols 10/10, locked-data isolation PASS. Training smoke and locked-test UI are policy SKIPs.
- **Finding:** The older 14:05 AGY failure reported only aggregate L2 failure. Comparing the monitor expectation and renderer isolated stale near-cancellation expectation `1.0e-13` versus actual `5.0e-13`, corrected by 14:43. Current L2 arithmetic passes; the concrete defect addressed now was unhelpful failure diagnostics.
- **Change:** `scripts/regression_monitor.py` retains named L2 browser-clause outcomes and prints failed clause names in the aggregate detail. `tests/test_system.py` asserts that this diagnostic path remains wired.
- **Evidence:** Focused L2 acceptance `1 passed, 94 deselected`; safe suite `184 passed, 1 deselected`; JS syntax, Python AST parse, scoped diff checks pass. Browser fixture not rerun after this diagnostic change; desktop/390px proof remains pending.
- **Next:** Run browser-only step 26 at desktop and 390px and verify failed clauses are named, excluding training smoke and locked-test UI. Neural-network learning remains incomplete; stock expansion beyond 10/10 awaits authorized local data, and cross-symbol magnitude teaching awaits comparable ordinary OOF summaries.

## Scheduled maintenance checkpoint (2026-10-28 14:20 +08:00, L2 browser finding and tradeoff exercise)

- **Latest AGY review / defect disposition:** `artifacts/regression-monitor/latest-checks.json` at `2026-10-28T14:05:36+08:00` is overall FAIL; its sole failure is the combined 「報酬與區間互動教學」 browser predicate, with `L2 正則化互動=False`. Safe suite snapshot is 184 passed / 1 deselected; local popular-stock coverage 10/10 and locked-data isolation PASS; training smoke and one-time locked-test UI SKIP. The snapshot does not preserve L2 predicate subclauses. Local preview at `127.0.0.1:8000` is unavailable, so the browser failure could not be independently localized. No defect fix is claimed; resolving it requires a safe isolated browser fixture that reports individual clauses.
- **Roadmap increment:** Guided step 26 now shows a fixed synthetic tradeoff case (`w=0.5, η=0.1, λ=0.1`): `ΔLdata=−0.0819`, `ΔLpenalty=+0.00981`; the text states that the larger data-loss decrease makes total loss decrease. This adds an immediately observable comparison to the neural-network learning lesson. Updated `web/app.js`, `web/index.html`, `tests/test_system.py`, and `docs/learning-guide.md`. Synthetic arithmetic only; no training or model-quality claim.
- **Verification:** Focused renderer acceptance passes (`1 passed, 94 deselected`); exact output is asserted. `node --check web/app.js`, Python AST parsing of monitor/tests, and scoped `git diff --check` pass. No full suite or browser/desktop/390px rendering was run.
- **Remaining / next checkpoint:** Reproduce the L2 monitor failure in an isolated browser without writing shared monitor state, and report the failing predicate clause before fixing it. Then check step 26 at desktop and 390px. Keep neural-network learning incomplete; popular-stock expansion past local 10/10 needs an authorized local data source, and real cross-symbol magnitude lessons need comparable ordinary OOF summaries. No credentials, locked observations, or `final-test-*.json` accessed; no final test, market refresh, training, deployment, publication, or external messaging.

## Scheduled maintenance checkpoint (2026-10-28 12:05 +08:00, scale-aware L2 cancellation)

- **Latest AGY review:** `artifacts/regression-monitor/latest-checks.json` at `2026-10-28T11:40:50+08:00` is PASS; its saved safe suite is `184 passed, 1 deselected`, local popular-stock coverage 10/10, browser desktop/390px, magnitude lessons, and locked-data isolation PASS. Training smoke and one-time locked-test UI are policy SKIPs. No review failure was recorded.
- **Highest-priority concrete defect reproduced and fixed:** Current L2 direction reading used a fixed absolute `1e-12` equality tolerance. Opposing gradients `2e-13` and `−1e-13` differ by 50% yet fell inside that tolerance and were incorrectly labeled “正好抵銷”. `web/app.js` now classifies opposing gradients with a relative tolerance scaled to the larger magnitude; `tests/test_system.py` and `scripts/regression_monitor.py` cover unequal and equal tiny opposing gradients.
- **Roadmap advance:** Guided step 26 visibly compares synthetic micro-gradients `2×10⁻¹³` and `−1×10⁻¹³`, reports relative difference `0.50`, and says the data term still leads. The equal-magnitude branch remains checked as cancellation. Updated `web/app.js`, `web/index.html`, `scripts/regression_monitor.py`, `tests/test_system.py`, and `docs/learning-guide.md`. This advances numerical interpretation in the incomplete neural-network lesson; synthetic only, with no training or model-quality claim.
- **Verification:** Safe selection `python3 -m pytest -q tests/test_system.py -k 'not public_api_and_async_validation_job'` passes `94 passed, 1 deselected`; `node --check web/app.js`, Python AST parse for monitor/tests, and `git diff --check` pass. The first full run found the renderer fixture had omitted the newly extracted classifier; fixture now loads the classifier and the rerun passes. The AGY browser snapshot predates the edit, so live rendering at desktop/390px is not claimed.
- **Next checkpoint / boundaries:** Run browser-only guided step-26 acceptance at desktop and 390px, checking the new micro-gradient line alongside default, exact cancellation, λ=0, blank input, and overshoot; continue excluding training smoke and locked-test UI. Keep the broader learning roadmap incomplete. Popular-stock expansion beyond local 10/10 requires an authorized local source; real cross-symbol magnitude lessons require comparable ordinary OOF summaries. No credentials, locked observations, or `final-test-*.json` were accessed; no final test, market refresh, training, deployment, or publication.

## Scheduled maintenance checkpoint (2026-10-28 11:20 +08:00, L2 loss-change decomposition)

- **Latest AGY review and defect disposition:** `artifacts/regression-monitor/latest-checks.json` at `2026-10-28T11:04:35+08:00` reports overall PASS; safe suite snapshot `184 passed, 1 deselected`; local popular-stock coverage 10/10; direction/magnitude exercises, desktop/390px, and locked-data isolation PASS. Training smoke and one-time locked-test UI are SKIP. I reviewed the current checks and relevant implementation; no current review failure or higher-priority concrete defect reproduced. The JSON is pre-change evidence.
- **Exact implementation and milestone:** Guided step 26 now reports `ΔLdata`, `ΔLpenalty`, and their sum `ΔL` after its synthetic L2 SGD update. At `w=2, η=0.1, λ=0.1`, the visible values are `−0.4224`, `−0.0902`, and `−0.5126` (`1.4000→0.8874`). Added executable renderer assertions, browser-fixture predicate coverage, and guide text. This advances the incomplete neural-network learning objective with an observable decomposition of objective change; arithmetic is synthetic and is not training or model-quality evidence.
- **Verification:** Focused L2 test `1 passed, 94 deselected`; safe project selection `184 passed, 1 deselected` via `python3 -m pytest -q -k 'not public_api_and_async_validation_job'`; `node --check web/app.js`, Python AST parsing of monitor/tests, and scoped `git diff --check` pass. No post-edit browser or desktop/390px rendering is claimed.
- **Remaining / next checkpoint:** Run safe browser-only step-26 acceptance at desktop and 390px for λ=0, changed component shares, cancellation, blank input, overshoot, and the new Δ-loss decomposition; exclude training smoke and locked-test UI. Broader neural-network learning remains incomplete. Popular-stock expansion beyond local 10/10 needs an authorized local source; real cross-symbol magnitude instruction needs comparable ordinary OOF summaries. No credentials, locked observations, or `final-test-*.json` were accessed; no one-time final test, market refresh, training, deployment, or publication occurred.

## Scheduled maintenance checkpoint (2026-10-28 10:45 +08:00, L2 ratio and overflow direction)

- **Latest review data:** `artifacts/regression-monitor/latest-checks.json` at `2026-10-28T10:29:07+08:00` reports PASS; its safe suite is `184 passed, 1 deselected`, popular-stock local coverage is 10/10, Loss pointer/keyboard and desktop/390px checks pass, and locked-data isolation passes. Training smoke and one-time locked-test UI are SKIP. No supplied current failure reproduced.
- **Highest-priority independently reproduced defect:** `calculateL2Regularization(1e200, 0.1, 1)` formed `dataGradient * penaltyGradient`, overflowing that product to Infinity. The direction classifier therefore mislabeled opposite-sign gradients as aligned before the existing finite-result guard rejected the calculation.
- **Exact fix:** `web/app.js` now compares gradient signs directly with `Math.sign`, avoiding the overflow product. `tests/test_system.py` exercises the `w=1e200` case and requires the invalid extreme calculation to be rejected.
- **Roadmap increment:** The visible L2 lesson now shows the pre-update data-loss and penalty shares. At `w=2, λ=0.1`, it displays data 71.4% and penalty 28.6%; the guide, HTML prompt, executable test, and browser predicate describe and check this. This is synthetic instruction, not training or model-quality evidence; the broad neural-network milestone remains incomplete.
- **Verification:** Focused tests: `2 passed, 93 deselected`; JS syntax, Python AST parsing, and scoped `git diff --check` pass. Initial acceptance found a stale copy assertion after the prompt changed; it was updated to assert the new prompt and numeric display, then passed. No post-edit desktop/mobile browser rendering is claimed; the AGY snapshot predates these changes.
- **Remaining / next checkpoint:** Run the safe browser-only guided acceptance at desktop and 390px for step 26, including λ=0, changed loss shares, direction cancellation, blank input, and overshoot. Keep training smoke and locked-test UI excluded. Stock expansion beyond local 10/10 needs an authorized local source; real cross-symbol magnitude instruction needs comparable ordinary OOF summaries. No credentials, locked observations, or `final-test-*.json` were accessed; no final test, data refresh, training, deployment, or publication occurred.

## Scheduled maintenance checkpoint (2026-10-28 08:25 +08:00, activation loss visibility)

- **Latest review and highest-priority defect:** `artifacts/regression-monitor/latest-checks.json` at `2026-10-28T08:03:51+08:00` reports PASS, including 182 passed / 1 deselected, 10/10 local popular-stock coverage, Loss pointer/keyboard, desktop/mobile, and locked-data isolation. Training smoke and one-time locked-test UI are SKIP. I independently inspected Guided step 21 and found a concrete learning omission: it displayed activation outputs, local derivatives, and loss gradients but not the squared losses, so learners could not compare the error term that drives those gradients. No current review failure required a separate bug fix.
- **Exact change and roadmap advance:** `web/app.js` now calculates and displays `(f(z)-y)^2` for Sigmoid, ReLU, and Tanh beside each local derivative and squared-loss gradient. Step copy defines the loss and chain-rule gradient, and the guide records synthetic `z=2,y=1` and `y=0` values. Tests and the routine browser predicate assert the rendered default losses (`0.0142`, `1.0000`, `0.0013`) and target-change example (`0.7758`, `4.0000`, `0.9293`). This advances the incomplete neural-network learning milestone with an observable error-to-gradient connection; it is synthetic teaching, not training or model-quality evidence.
- **Verification:** Focused acceptance passed (`2 passed, 91 deselected`); safe project suite passed (`182 passed, 1 deselected`, excluding `public_api_and_async_validation_job`). `node --check web/app.js`, Python AST parsing for monitor/tests, and scoped `git diff --check` passed. An initial run exposed stale documentation/test values (the target-zero Sigmoid loss is `0.7758`, not `0.7746`) and missing function-name wording in the guide; both were corrected. The supplied browser snapshot predates this edit; no post-edit browser/desktop/390px evidence is claimed.
- **Remaining / next checkpoint:** Safely verify step 21 at desktop and 390px, including target changes, saturation, and blank-input feedback, with training smoke and locked-test UI excluded. Popular-stock expansion beyond local 10/10 needs an authorized local source; genuine cross-symbol magnitude instruction needs comparable ordinary OOF summaries. Broader neural-network learning remains incomplete. No credentials, locked observations, or `final-test-*.json` were accessed or changed; no final test, data refresh, training, deployment, or publication occurred.

## Scheduled maintenance checkpoint (2026-10-28 07:10 +08:00, target-aware activation gradients)

- **Latest review and defect disposition:** `artifacts/regression-monitor/latest-checks.json` is timestamped `2026-10-28T06:55:11+08:00`, overall PASS. Safe suite snapshot is `182 passed, 1 deselected`; popular-stock local coverage is 10/10; desktop, 390px, Loss pointer/keyboard, and locked-data-isolation checks pass. Training smoke and one-time locked-test UI are SKIP. I checked the reported high-priority failures and reproduced no current concrete defect; the latest clean report supersedes older Loss-hover failures.
- **Roadmap increment and exact change:** Extended Guided step 21's activation comparison with an editable synthetic target `y`. `calculateActivationComparison(z, y)` now reports squared-loss gradients `2(f(z)-y)f′(z)` for Sigmoid, ReLU, and Tanh alongside their local derivatives. At `z=2,y=1`, Sigmoid gradient is `−2.503e−2`; changing `y=0` keeps the local derivative `0.1050` but changes the loss gradient to `+1.850e−1`. The saturated `z=8,y=1` example remains `−2.248e−7`. Updated `web/app.js`, `web/index.html`, `tests/test_system.py`, `scripts/regression_monitor.py`, and `docs/learning-guide.md`. This is synthetic instruction, not model training or quality evidence.
- **Acceptance and verification:** Focused activation checks pass (`2 passed, 91 deselected`). Safe project selection passes (`182 passed, 1 deselected`). `node --check web/app.js`, Python AST parsing for monitor/tests, and scoped `git diff --check` pass. The initial safe-suite run exposed a stale source-string contract for a retired monitor output; updated it to assert the live numeric and target-aware acceptance predicates, then reran successfully. The supplied 06:55 browser snapshot predates the edit; no post-edit browser/desktop/390px claim is made.
- **Status and next checkpoint:** Neural-network learning remains incomplete; verify step 21 target changes, saturation, and blank input at desktop and 390px through a safe browser path that skips training smoke and locked-test UI. Popular-stock expansion beyond local 10/10 needs an authorized local source; real cross-symbol magnitude learning needs comparable ordinary OOF summaries. No credentials, locked observations, or `final-test-*.json` were accessed or changed; no final test, data refresh, training, deployment, or publication occurred.

## Scheduled maintenance checkpoint (2026-10-28, status freshness and sigmoid-gradient lesson)

- **Latest review and defect:** The latest supplied AGY snapshot is `2026-10-28T06:19:13+08:00`, overall PASS, with 43 PASS and 2 policy SKIP checks; safe pytest snapshot is 181 passed / 1 deselected. It reports local popular-stock coverage 10/10, Loss chart pointer and keyboard tooltip PASS, and locked-data isolation PASS. Training smoke and the one-time locked-test UI are SKIP. The newest entries in the four maintenance records still cited 04:32 or earlier as latest, independently reproducing stale review status.
- **Status correction:** This checkpoint records the current snapshot across `scratchpad.md`, `CODEX.md`, `docs/codex-bug-report.md`, and `docs/project-status-and-goals.md`. The supplied AGY JSON and generated artifacts were not rewritten.
- **Roadmap increment:** Guided step 14 now compares ReLU and Sigmoid local gradients for the same synthetic input and target. At `z=2, y=1`, ReLU gradient is `2` and Sigmoid gradient is about `−0.0250`; at `z=8, y=1`, the Sigmoid derivative is about `3.352e−4` and its loss gradient about `−2.248e−7`, with saturation guidance. This advances neural-network learning with an observable single-neuron example; it is not model training or quality evidence.
- **Implementation and verification:** Changed `web/app.js`, `web/index.html`, `tests/test_system.py`, `scripts/regression_monitor.py`, and `docs/learning-guide.md`. Focused step-14 checks pass (`2 passed, 91 deselected`); safe project selection passes (`182 passed, 1 deselected`). `node --check web/app.js`, Python AST parsing for monitor/tests, and scoped `git diff --check` pass. The monitor predicate now checks both the moderate-gradient and saturated-gradient outputs. The 06:19 browser snapshot predates this edit; no post-edit browser or viewport acceptance is claimed.
- **Remaining / next checkpoint:** Run the safe project test selection and static checks, then verify step 14 at desktop and 390px through the synthetic browser fixture when a browser-only route is available. Keep the neural-network learning goal incomplete. Popular-stock expansion beyond 10/10 local symbols needs an authorized local source; real cross-symbol rise/fall magnitude learning needs comparable ordinary OOF summaries. No credentials, locked observations, or `final-test-*.json` were accessed or changed; no final test, market refresh, real-data training, deployment, or publication occurred.

## Scheduled maintenance checkpoint (2026-10-28 04:36 +08:00, hover monitor and magnitude lesson)

- **Latest AGY review:** `artifacts/regression-monitor/latest-checks.json` is timestamped `2026-10-28T04:32:26+08:00`, overall FAIL. The sole failing browser check is Loss chart pointer tooltip; keyboard reports Epoch 2 correctly. The snapshot records `181 passed, 1 deselected`, local popular-stock coverage 10/10, locked-data isolation PASS, and training smoke / one-time locked-test UI SKIP.
- **Highest-priority defect and fix:** The current live UI responds to mouse movement over the Loss chart: the tooltip became visible at Epoch 12 with Train and Validation values. This contradicts the AGY pointer-hover failure and indicates a brittle monitor interaction. The local Playwright browser could not launch (`TargetClosedError`, Chrome exited with SIGABRT), so the AGY failure was not reproduced through the same runner. Changed `scripts/regression_monitor.py` to hover the SVG `.loss-hit-area` directly and wait for a visible Epoch tooltip before reading it; added a source-contract test.
- **Roadmap increment:** Guided step 15 now compares mean absolute predicted and actual return magnitude separately for actual-up and actual-down samples, alongside each group's MAE, zero-return baseline, and direction errors. Its default synthetic output is up `0.60 / 0.20 pp` and down `0.25 / 0.15 pp` (predicted / actual). Updated `web/app.js`, `web/index.html`, the lesson guide, executable acceptance, and the browser lesson predicate. This is synthetic learning content, not OOF evidence or model-quality evidence.
- **Verification:** Focused tests for step 15 and monitor hover acceptance: `2 passed`. Safe project suite: `181 passed, 1 deselected`. `node --check web/app.js`, Python AST parsing for monitor/tests, and scoped `git diff --check` passed. In the live browser, moving across the chart displayed the Epoch 12 tooltip; fresh Playwright desktop/mobile monitor acceptance remains unverified because Chromium would not launch.
- **Remaining / next checkpoint:** Re-run the revised monitor when its Chromium runtime launches, then verify the updated lesson at desktop and 390px without training smoke or locked-test UI. Keep neural-network learning incomplete; real cross-symbol magnitude comparison still needs comparable ordinary OOF summaries, and expanding beyond 10/10 local stocks needs an authorized local data source. No credentials, locked observations, or `final-test-*.json` were accessed; no final test, market refresh, training, deployment, or publication occurred.

## Scheduled maintenance checkpoint (2026-10-28 04:26 +08:00, Loss pointer touch boundary)

## Scheduled maintenance checkpoint (2026-10-28 02:47 +08:00, momentum projection lesson)

- **Latest review evidence:** `artifacts/regression-monitor/latest-checks.json` is timestamped `2026-10-28T02:43:17+08:00`, overall FAIL. Its pytest record is `1 failed, 179 passed, 1 deselected`; the independent safe rerun reproduced that same test failure. The browser Loss tooltip check also reports pointer hover missing while keyboard navigation works. Local popular-stock coverage is 10/10; locked-data isolation passes. Training smoke and one-time locked-test UI are SKIP.
- **Highest-priority reproduced failure and correction:** `tests/test_paper_trading.py::test_walk_interaction_uses_a_clear_foreground_lane_and_a_slow_ping_pong_route` expected obsolete patrol, seat-visibility, walker-rendering, and seat-position source snippets. Current code already uses an explicit two-endpoint patrol, a visible-ID set, office-map employee rendering, and `getPaperSeatPosition`; the old assertions rejected that implementation. Replaced those stale source-string expectations with checks for the current route and layout behavior. No paper-trading behavior was changed. The supplied browser Loss pointer-hover failure was not independently reproduced in a live browser this turn and remains open for the next checkpoint.
- **Bounded roadmap advance:** Guided step 20's editable two-dimensional momentum example now displays the signed velocity component parallel to the gradient and the perpendicular component magnitude, in addition to dot product and direction cosine. For `v=(0.5,0), g=(1,0)`, the visible decomposition is parallel `0.5000`, perpendicular `0.0000`; for `v=(1,0), g=(0,2)`, it is `0.0000` and `1.0000`; reverse `g=(-1,0)` gives parallel `−0.5000`. Updated `web/app.js`, `web/index.html`, `scripts/regression_monitor.py`, `tests/test_system.py`, and `docs/learning-guide.md`. This is synthetic math instruction only; the broader neural-network learning goal remains incomplete and this is not model-quality evidence.
- **Verification:** Focused checks for the stale patrol acceptance and momentum projection passed (`2 passed`). Full safe project selection `python3 -m pytest -q -k 'not public_api_and_async_validation_job'` passed (`180 passed, 1 deselected`). `node --check web/app.js`, Python AST parsing for the monitor and both test files, and scoped `git diff --check` passed. The latest monitor JSON predates these edits; no post-edit browser/viewport acceptance is claimed.
- **Remaining / next checkpoint:** Diagnose and reproduce the Loss chart pointer hover in browser, then verify the new step-20 projection output at desktop and 390px and refresh only routine safe browser evidence. Keep popular-stock expansion open until an authorized local data source exists; genuine cross-symbol rise/fall magnitude work still needs comparable ordinary OOF summaries. No credentials, locked observations, or `final-test-*.json` were accessed; no one-time final test, market-data refresh, training smoke, deployment, or publication was run.

## Scheduled maintenance checkpoint (2026-10-28, Adam underflow guard)

- **AGY status:** `artifacts/regression-monitor/latest-checks.json` at `2026-10-28T00:05:45+08:00` is PASS with no FAIL/WARN. Local popular-stock coverage is 10/10; holdout isolation PASS; training smoke and one-time locked-test UI SKIP.
- **Reproduced defect:** Adam step 25 accepted finite nonzero gradients `1e−200` and `−1e−200` with `β₂=.999`, `ε=1e−300`. Squaring underflowed the second moment to zero and produced a spurious `w₂≈5.26e97`.
- **Fix and roadmap:** `web/app.js` rejects squared-moment underflow and gives recovery guidance; `docs/learning-guide.md` explains the numeric boundary. This advances a bounded synthetic neural-learning subtask only.
- **Evidence / open failure:** Dedicated underflow pytest passes; safe project selection passes (`89 passed, 1 deselected`, excluding the Adam UI integration test). Direct Node execution confirms rejection; JS/AST and scoped diff checks pass. The broader Adam UI integration pytest still fails in renderer execution following blank ε validation; this remains unresolved and must be diagnosed before broad acceptance. No browser verification or model-quality claim.
- **Next checkpoint / safety:** Fix or accurately isolate the renderer failure without weakening assertions, then run safe tests excluding training and locked UI. Local stock expansion awaits authorized data; true cross-symbol magnitude teaching awaits comparable ordinary OOF summaries. No secrets, locked observations, final-test files, one-time final test, refresh, training, deploy, or publish.

## Prior scheduled maintenance checkpoint (2026-10-27, β₂ memory comparison)

- **Latest review / reproduced maintenance defect:** `artifacts/regression-monitor/latest-checks.json` is timestamped `2026-10-27T23:25:47+08:00` and reports PASS, 45 checks (43 PASS, 2 intentional SKIP), 179 passed / 1 deselected, local popular-stock coverage 10/10, desktop and 390px checks PASS, and locked-data isolation PASS. Training smoke and the one-time locked-test UI are SKIP. The leading checkpoint in these maintenance records still cited 22:50:07, so its review status was stale; direct timestamp comparison reproduced the defect. No current runtime failure was reported by the supplied checks or independently found in the reviewed Adam lesson logic.
- **Exact record repair:** Updated this checkpoint in `scratchpad.md`, `CODEX.md`, `docs/codex-bug-report.md`, and `docs/project-status-and-goals.md`. The monitor JSON and its screenshots were not changed.
- **Roadmap increment:** Guided step 25 now compares the current β₂ against β₂=0 for the same two synthetic gradients. At defaults (`g₁=2`, `g₂=−1`, `η=0.1`, `β₁=0.9`, `ε=1e−8`, current `β₂=0.999`), the displayed denominator/update are `1.0000 / 0.0421` for β₂=0 and `1.5809 / 0.0266` for β₂=0.999. This makes the square-gradient history's effect on the second-step denominator observable. Updated `web/app.js`, its executable acceptance in `tests/test_system.py`, the browser monitor predicate in `scripts/regression_monitor.py`, and `docs/learning-guide.md`. This is fixed-gradient teaching arithmetic, not training or model-quality evidence; the broader neural-network learning goal remains incomplete.
- **Verification:** Focused Adam acceptance `python3 -m pytest -q tests/test_system.py -k adam_first_step_shows_bias_correction_and_sgd_comparison` → 1 passed, 88 deselected. The first expanded assertion run exposed that the Node test harness did not serialize the newly captured β₂=0.900 output; added that result to the harness and reran successfully. Safe project selection `python3 -m pytest -q -k 'not public_api_and_async_validation_job'` → 179 passed, 1 deselected. `node --check web/app.js`, Python AST parsing for monitor/tests, and scoped `git diff --check` passed. The supplied browser/desktop/390px evidence predates this change; no post-edit browser rendering is claimed.
- **Remaining / next checkpoint:** In browser-only mode, verify the β₂ comparison at desktop and 390px, then refresh routine browser evidence without training smoke or the locked-test UI. Popular-stock expansion still needs an authorized local data source; real cross-symbol rise/fall magnitude comparison needs compatible ordinary OOF summaries. No credentials, locked observations, or `final-test-*.json` were accessed or changed; no one-time final test, market refresh, training, deployment, or publication occurred.

## Scheduled maintenance checkpoint (2026-10-27, learning summary count and Adam moment roles)

- **Latest review evidence:** `artifacts/regression-monitor/latest-checks.json` is timestamped `2026-10-27T22:50:07+08:00`: overall PASS, 45 checks (43 PASS, 2 intentional SKIP), no FAIL/WARN, 179 passed / 1 deselected, popular-stock local coverage 10/10, desktop and 390px browser checks PASS, locked-data isolation PASS. Training smoke and one-time locked-test UI are SKIP. The snapshot predates this edit.
- **Highest-priority concrete defect / exact fix:** Initial `web/index.html` said “24 步導學” while the current lesson catalog and progress widget both expose 25 steps. The mismatch was directly reproduced from current markup and contradicted the passing browser monitor's 25-step catalog. Updated the initial summary to 25 and changed the source-contract test that had encoded the stale count.
- **Roadmap increment:** Adam step 25 now explicitly explains that β₁ controls signed-gradient first-moment memory and update direction, while β₂ controls squared-gradient second-moment memory and denominator scale. Existing controls recompute these outputs independently. Updated the learning guide and executable acceptance assertion. This is a fixed-gradient teaching feature, not training or model-quality evidence; the broader neural-network learning objective remains incomplete.
- **Verification:** Focused acceptance `python3 -m pytest -q tests/test_system.py::test_gradient_clipping_lesson_has_observable_bounded_update tests/test_system.py::test_adam_first_step_shows_bias_correction_and_sgd_comparison` → 2 passed. Safe suite `python3 -m pytest -q -k 'not public_api_and_async_validation_job'` → 179 passed, 1 deselected. `node --check web/app.js`, monitor/test Python AST parsing, and scoped `git diff --check` passed. No post-edit browser render is claimed; the latest AGY browser evidence is pre-edit.
- **Next checkpoint / limits:** In browser-only mode, confirm the initial summary and step 25 at desktop and 390px, including separate β₁/β₂ edits; then refresh the routine monitor without training smoke or locked-test UI. Popular-stock expansion still needs an authorized local data source, and real cross-symbol magnitude comparison needs compatible ordinary OOF summaries. No credentials, locked observations, or `final-test-*.json` were accessed or changed; no one-time final test, market refresh, training, deployment, or publication occurred.

## Current maintenance checkpoint (2026-10-27, Adam near-cancellation precision)

- **Review:** Latest supplied AGY snapshot is `2026-10-27T21:38:43+08:00`, PASS, no FAIL/WARN; safe suite snapshot 179 passed / 1 deselected, popular-stock coverage 10/10, holdout isolation PASS. Training smoke and locked-test UI SKIP.
- **Reproduced defect / fix:** Step 25 with `g₁=2`, `g₂=−1.79999`, `β₁=.9` has nonzero `m̂₂≈5.26e-6` opposite `g₂`; old four-decimal display showed `0.0000`. Near-zero nonzero moments now render in scientific notation in the summary and explanation; exact cancellation keeps its separate message.
- **Roadmap:** Advanced the incomplete neural-network learning goal with an interactive exact-vs-near-cancellation distinction using synthetic fixed gradients. No training or model-quality claim.
- **Evidence:** Focused acceptance `1 passed, 88 deselected`; safe selection `179 passed, 1 deselected`; JS syntax, Python AST, and diff checks pass. No post-edit browser/viewport claim; snapshot predates the edit.
- **Next:** Inspect step 25 at desktop and 390px. Popular-stock expansion needs an authorized local source; cross-symbol magnitude learning needs comparable ordinary OOF summaries. No protected observations/final-test files accessed; no final test, market refresh, training, deployment, or publication.

## Scheduled maintenance checkpoint (2026-10-27, Adam zero-moment direction)

- **Latest review evidence:** `artifacts/regression-monitor/latest-checks.json` is timestamped `2026-10-27T21:03:20+08:00`: overall PASS, 45 checks, no FAIL/WARN, safe pytest snapshot 179 passed / 1 deselected, popular-stock local coverage 10/10, and locked-data isolation PASS. Real-data training smoke and the one-time locked-test UI are SKIP. The snapshot predates this change.
- **Highest-priority reproduced defect and exact fix:** In current `web/app.js`, step 25 compared `sign(g₂)` with `sign(m̂₂)` without handling `m̂₂=0`. The synthetic inputs `g₁=2`, `g₂=−1.8`, `β₁=0.9` make the history and current contributions `0.18` and `−0.18`, so `m̂₂=0`; the old output incorrectly said the directions were opposite. The renderer now distinguishes exact cancellation (Adam has no second-step direction), zero current gradient with retained history, and both gradients/moment zero. Added executable and browser-monitor assertions for cancellation and the both-zero case.
- **Roadmap advance:** Advanced the incomplete neural-network learning objective with an observable step-25 edge case. The learner can set `g₂=−1.8` and see that the current gradient still has a direction while Adam's accumulated second-step moment does not. This is fixed-gradient teaching arithmetic, not model training or quality evidence. Added the explanation to `docs/learning-guide.md`; broader learning and real cross-symbol rise/fall magnitude objectives remain incomplete.
- **Verification:** `python3 -m pytest -q tests/test_system.py -k adam_first_step_shows_bias_correction_and_sgd_comparison` → 1 passed, 88 deselected. `python3 -m pytest -q -k 'not public_api_and_async_validation_job'` → 179 passed, 1 deselected. No post-change browser/viewport result is claimed; the AGY JSON remains unchanged and predates the edit.
- **Next checkpoint / limits:** Verify step 25 at desktop and 390px in browser-only mode for opposite, aligned, zero-current-gradient, exact-cancellation, both-zero, blank-input, and ε cases. Popular-stock expansion still requires an authorized local source; real cross-symbol magnitude work still needs comparable ordinary OOF summaries. No credentials, locked observations, or `final-test-*.json` were accessed or changed; no final test, market refresh, training, deployment, or publication occurred.

## Scheduled maintenance checkpoint (2026-10-27, Adam moment decomposition and review freshness)

- **Latest review / highest-priority defect:** The supplied `artifacts/regression-monitor/latest-checks.json` is timestamped `2026-10-27T20:27:57+08:00`, overall PASS, with 45 listed checks and no failure/warning; its pytest snapshot is 179 passed / 1 deselected. Training smoke and the one-time locked-test UI are SKIP. Each maintenance record still led with the 19:53 review, so the stale review checkpoint was independently reproduced by comparing its timestamp to the current snapshot. The snapshot predates this turn's code edit.
- **Exact record repair:** Added this current checkpoint to `scratchpad.md`, `CODEX.md`, `docs/codex-bug-report.md`, and `docs/project-status-and-goals.md`; the monitor JSON was left unchanged.
- **Bounded roadmap advance:** Guided step 25 now displays Adam's second-step first-moment sources separately: `β₁m₁` (retained history) and `(1−β₁)g₂` (current gradient), then their sum `m₂`. Defaults show `0.1800 + (−0.1000) = 0.0800`, making visible why a reversed gradient can reduce but not yet reverse the accumulated moment. This is a synthetic learning milestone, not model training or quality evidence; the broader neural-network learning objective remains incomplete.
- **Implementation / acceptance evidence:** Changed `web/app.js`, `scripts/regression_monitor.py`, `tests/test_system.py`, and `docs/learning-guide.md`. Focused Adam acceptance: `python3 -m pytest -q tests/test_system.py -k adam_first_step_shows_bias_correction_and_sgd_comparison` → 1 passed, 88 deselected. Safe project selection: `python3 -m pytest -q -k 'not public_api_and_async_validation_job'` → 179 passed, 1 deselected. `node --check web/app.js`, Python AST parsing for monitor/tests, and scoped `git diff --check` pass. The first focused run exposed an outdated output-string assertion; it was updated to assert the new visible decomposition, then the focused and safe selections passed. No post-edit browser/viewport check is claimed.
- **Remaining / next checkpoint:** Verify Guided step 25 at desktop and 390px in browser-only mode, including opposite/aligned/zero gradients and blank inputs; exclude training smoke and locked-test UI. Popular-stock coverage remains local 10/10 and expansion needs an authorized source; real cross-symbol direction/magnitude work needs comparable ordinary OOF summaries. No credentials, locked observations, or `final-test-*.json` were read, changed, or consumed; no final test, market refresh, training, deployment, or publication occurred.

## Scheduled maintenance checkpoint (2026-10-27, zero-gradient semantics and current review)

- **Latest review / reproduced defect:** `artifacts/regression-monitor/latest-checks.json` at `2026-10-27T19:53:32+08:00` is PASS with 45 checks and no FAIL/WARN; real-data training smoke and the one-time locked-test UI are SKIP. The top maintenance records still cited 19:19, so the review-status lag was reproduced. Separately, current step-25 code used `sign(g₂) !== sign(m̂₂)` to label opposition; with synthetic `g₁=2, g₂=0`, it incorrectly called a zero gradient “opposite.”
- **Exact defect fix:** Updated `web/app.js` so `g₂=0` is described as having no direction while Adam retains its accumulated direction. Added executable coverage in `tests/test_system.py` and browser predicate coverage in `scripts/regression_monitor.py`; `docs/learning-guide.md` records the zero-gradient case. No model/training code or market data changed.
- **Roadmap increment:** Advanced the neural-network learning objective with a bounded step-25 edge-case lesson: learners can set the second synthetic gradient to zero and see the distinction between no current gradient direction and Adam's nonzero historical moment. This clarifies the existing Adam lesson; it does not establish optimizer or model quality.
- **Verification:** Focused acceptance `python3 -m pytest -q tests/test_system.py -k adam_first_step_shows_bias_correction_and_sgd_comparison` → `1 passed, 88 deselected`. Safe project selection `python3 -m pytest -q -k 'not public_api_and_async_validation_job'` → `179 passed, 1 deselected`. The 19:53 monitor snapshot predates this edit; no post-edit browser viewport check is claimed.
- **Remaining / next checkpoint:** Keep the broader learning goal incomplete. Run browser-only step-25 acceptance at desktop and 390px, checking opposite, aligned, zero, blank, and ε cases; do not enter training smoke or locked-test UI. Popular-stock coverage remains local 10/10 and expansion needs an authorized source; real cross-symbol direction/magnitude work still needs comparable ordinary OOF summaries. No credentials, locked observations, or `final-test-*.json` were read, changed, or consumed; no final test, market refresh, training, deployment, or publication occurred.



- **Latest review / reproduced defect:** `artifacts/regression-monitor/latest-checks.json` is timestamped `2026-10-27T19:19:03+08:00`, overall PASS, with 45 checks and no FAIL/WARN. The only skips are real-data training smoke and the one-time locked-test UI. Its latest timestamp is newer than the 18:43 timestamp in the leading sections of the maintenance records; comparing the supplied JSON with those records reproduced stale review status. No current product failure was found.
- **Exact record correction:** Updated the leading review checkpoint in `scratchpad.md`, `CODEX.md`, `docs/codex-bug-report.md`, and `docs/project-status-and-goals.md` to cite the 19:19 snapshot. The JSON itself was not modified.
- **Bounded roadmap advance:** Guided step 25 now explains when the current second-step gradient `g₂` opposes Adam's bias-corrected accumulated moment `m̂₂`. With synthetic defaults `g₁=2`, `g₂=−1`, Adam has `m̂₂=0.4211`: Adam continues its prior direction while SGD follows the reversed current gradient. When the second gradient is aligned (`g₂=2`), the lesson labels the directions the same. This is formula teaching only, not training or model-quality evidence.
- **Implementation / acceptance:** Updated `web/app.js`, `scripts/regression_monitor.py`, `tests/test_system.py`, and `docs/learning-guide.md`. Focused executable acceptance: `1 passed, 88 deselected`; safe project selection `python3 -m pytest -q -k 'not public_api_and_async_validation_job'`: `179 passed, 1 deselected`; `node --check web/app.js`, Python AST parsing, and scoped `git diff --check` pass. No post-change browser or viewport acceptance is claimed; the supplied snapshot predates this change.
- **Remaining / next checkpoint:** Keep the broader neural-network learning objective incomplete. Run browser-only step 25 acceptance at desktop and 390px, excluding training smoke and locked-test UI. Popular-stock coverage remains local 10/10 and expansion requires an authorized source; real cross-symbol direction/magnitude learning needs comparable ordinary OOF summaries. No credentials, locked observations, or `final-test-*.json` were read, changed, or consumed; no final test, market refresh, training, deployment, or publication.

## Scheduled maintenance checkpoint (2026-10-27, Adam denominator lesson)

- **Latest review / defect disposition:** `artifacts/regression-monitor/latest-checks.json` at `2026-10-27T18:43:35+08:00` is PASS with no failed checks; its saved suite is 179 passed / 1 deselected, local popular-stock coverage 10/10, and locked-data isolation PASS. Training smoke and locked-test UI are SKIP. I investigated whether the editable Adam ε was omitted from the calculation helper: direct current-code evaluation confirms the renderer passes ε and ε=0.1 changes the expected weights (`0.9000→0.8797`); this was not a defect. No higher-priority product defect was reproduced.
- **Milestone advanced:** Guided step 25 now displays the second-step Adam denominator `√v̂₂+ε`, the positive update amount, and the resulting negative weight change separately. With synthetic defaults, ε=`1e-8` gives denominator `1.5809`, update amount `0.0266`, weight change `−0.0266`, and `w₂=0.8734`; ε=`0.1` gives `1.6809`, `0.0250`, `−0.0250`, and `w₂=0.8797`. This makes the stabilizer's effect on update size observable. It is synthetic instruction, not training or model-quality evidence.
- **Exact change / verification:** Updated `web/app.js`, the Adam browser predicate in `scripts/regression_monitor.py`, executable acceptance in `tests/test_system.py`, and `docs/learning-guide.md`. Focused acceptance: `1 passed, 88 deselected`; safe suite: `179 passed, 1 deselected`; `node --check web/app.js`, Python AST parsing, and `git diff --check` pass. The first focused run caught incorrect rounding and mislabeled sign expectations in the new assertion; output inspection corrected them and the focused plus safe suites then passed. No post-change browser/viewport run is claimed.
- **Status / next checkpoint:** Neural-network learning remains incomplete. Next inspect steps 18, 24, and 25 at desktop and 390px through browser-only acceptance, excluding training smoke and locked-test UI. Popular-stock coverage remains local 10/10 and expansion needs an authorized source; cross-symbol magnitude work needs comparable ordinary OOF summaries. No credentials, protected observations, or `final-test-*.json` accessed/changed/consumed; no final test, market refresh, training, deployment, or publication.

## Scheduled maintenance checkpoint (2026-10-27, Adam epsilon lesson and review freshness)

- **Latest review evidence:** `artifacts/regression-monitor/latest-checks.json` at `2026-10-27T18:07:14+08:00` reports overall PASS: safe regression selection `179 passed, 1 deselected`, local popular-stock coverage `10/10`, direction/magnitude and Guided lesson checks PASS, and locked-data isolation PASS. Real-data training smoke and one-time locked-test UI are SKIP.
- **Highest-priority reproduced defect and exact fix:** The top “latest” sections of the maintenance records still pointed to a 07:06 FAIL even though the supplied current snapshot is 18:07 PASS and a later 17:31 Adam step-25 update existed farther down. Comparing timestamps and contents reproduced this stale-status defect. Replaced the leading checkpoint in `scratchpad.md`, `CODEX.md`, `docs/codex-bug-report.md`, and `docs/project-status-and-goals.md` with the current review disposition, work, evidence, and next checkpoint.
- **Bounded roadmap milestone advanced:** Guided step 25 now exposes Adam's denominator stabilizer `ε` as an editable input, validates `0 < ε ≤ 1`, and prints it in scientific notation. At the existing synthetic gradients and optimizer settings, default `ε=1e-8` retains `w₁=0.9000 → w₂=0.8734`; `ε=0.1` visibly changes this to `w₁=0.9048 → w₂=0.8797`. Empty ε receives actionable range guidance. The learning guide and browser acceptance predicate cover the same values. This is synthetic teaching, not model training or quality evidence.
- **Implementation and verification:** Updated `web/index.html`, `web/app.js`, `scripts/regression_monitor.py`, `tests/test_system.py`, `docs/learning-guide.md`, and the four requested maintenance/status records. Focused Adam acceptance: `1 passed, 88 deselected`. Safe suite: `179 passed, 1 deselected`. `node --check web/app.js`, Python AST parsing for monitor/tests, and `git diff --check` passed. Live desktop browser inspection after the edit confirmed step 25 at default ε=1e-8 and after changing ε to 0.1; the 18:07 snapshot predates the edit. Mobile 390px rendering remains unverified.
- **Remaining / next checkpoint:** Run browser-only acceptance for steps 18 and 24 at desktop and 390px, then inspect step 25 at 390px and its blank-ε recovery; exclude training smoke and locked-test UI. Keep the broader learning objective incomplete. Popular-stock expansion needs an authorized local source; real cross-symbol magnitude learning needs comparable ordinary OOF summaries. No credentials, locked observations, or `final-test-*.json` were read, changed, or consumed; no one-time final test, market refresh, training, deployment, or publication occurred.
## Scheduled maintenance update (2026-10-27, mini-batch grouping path)

- **Latest review evidence:** `artifacts/regression-monitor/latest-checks.json` is timestamped `2026-10-27T03:19:45+08:00` and reports overall FAIL solely because its saved pytest snapshot says `1 failed, 176 passed, 1 deselected`. Other listed checks pass, including local popular-stock coverage 10/10 and locked-data isolation; browser desktop/390px checks passed in that snapshot. Training smoke and one-time locked-test UI are SKIP. The reported source diff points to `tests/test_paper_trading.py`; rerunning the exact safe selection twice returned `177 passed, 1 deselected` both times, so no current failure or product defect was independently reproduced and no defect fix is claimed.
- **Roadmap increment:** Guided step 19's synthetic mini-batch comparison now shows a second grouping of the same gradients. With `w=2`, gradients `(-2,4,1,1)`, and `η=0.1`, grouping `(1–2),(3–4)` gives `2→1.9000→1.8000`; grouping `(1,3),(2,4)` gives `2→2.0500→1.8000`. The interface explains that the two fixed-gradient mini-batch groupings both end at 1.8000 while following different intermediate paths; one full-batch update ends at 1.9000. Updated `web/app.js`, `scripts/regression_monitor.py`, `tests/test_system.py`, and `docs/learning-guide.md`. This is synthetic instruction, not model training or model-quality evidence.
- **Verification:** Focused batch-gradient acceptance `1 passed, 86 deselected`; safe suite `177 passed, 1 deselected`; `node --check web/app.js`, Python AST parsing for monitor/tests, and scoped `git diff --check` pass. The monitor's browser predicate now checks the new visible path, but no post-change browser or viewport run is claimed.
- **Remaining / next checkpoint:** Keep the broader neural-network learning goal incomplete. Run browser-only step-19 acceptance at desktop and 390px, excluding training smoke and locked-test UI. Popular-stock expansion still needs an authorized local data source; real cross-symbol magnitude teaching still needs comparable ordinary OOF summaries. No credentials, locked observations, or `final-test-*.json` were read, changed, or consumed; no final test, training, market refresh, deployment, or publication occurred.

## Scheduled maintenance update (2026-10-27, model-choice predicate and signed weight movement)

- **Latest review evidence:** `artifacts/regression-monitor/latest-checks.json` at `2026-10-27T02:08:54+08:00` reports PASS, 171 passed / 1 deselected, 10/10 local symbols and locked-data isolation PASS; training smoke and one-time locked-test UI are SKIP.
- **Highest-priority reproduced defect and fix:** The current browser monitor described “multi-model checkboxes=5” but only counted elements. Five duplicate or disabled model controls could still pass. The predicate now checks that the enabled values are exactly `{mlp,rnn,lstm,gru,tcn}` and reports observed versus expected IDs. Added a regression contract.
- **Roadmap increment:** Guided step 23 now prints signed weight movement `Δw` separately from loss delta. For `g=4`, `η=.25`, `w:3→2`, it shows `Δw=−1` and loss `4→1`; copy clarifies that `w←w−ηg` means a negative gradient can increase the weight. Updated `scripts/regression_monitor.py`, `web/app.js`, `web/index.html`, `tests/test_system.py`, and `docs/learning-guide.md`. This is synthetic teaching, not model-quality evidence.
- **Verification:** Focused acceptance `2 passed`; safe suite `172 passed, 1 deselected`; `node --check web/app.js`, Python AST parsing for monitor/tests, and scoped `git diff --check` pass. The supplied AGY browser snapshot predates edits; no post-change browser/desktop/390px check is claimed.
- **Remaining / next checkpoint:** Keep the broader learning goal incomplete. Run browser-only checks at desktop/390px for the exact enabled model set and signed `Δw`. Popular-stock expansion needs an authorized local source; real cross-symbol magnitude learning needs comparable ordinary OOF summaries. No credentials, locked observations, or `final-test-*.json` read/changed/consumed; no final test, training, refresh, deployment, or publication.
## Scheduled maintenance update (2026-10-27, review disposition and learning increment)

- **Current review evidence:** The requested latest snapshot is `artifacts/regression-monitor/latest-checks.json` at `2026-10-27T00:58:30+08:00`, overall PASS, 170 passed / 1 deselected, 10/10 local popular-stock coverage, and locked-data isolation PASS. Real-data training smoke and one-time locked-test UI are SKIP. Current report/source comparison did not independently reproduce a concrete defect; older failures are superseded and no bug fix is claimed.
- **Exact implementation:** Guided step 23 now prints distance to minimum `|w−1|` and observed distance ratio after each update, in addition to loss delta. The default `c=1`, `w₀=3`, `η=0.25` synthetic trace yields distances `2,1,0.5,0.25,0.125` and ratios `0.5`, consistent with `1−2ηc`. Updated `web/app.js`, `web/index.html`, `docs/learning-guide.md`, monitor predicate, and renderer test.
- **Verification and limits:** Focused pytest `1 passed`; safe project selection `170 passed, 1 deselected`; JS syntax, Python AST parsing, and scoped `git diff --check` passed. The AGY snapshot is pre-change; browser rendering at desktop/390px has not been rerun. This synthetic lesson does not establish model quality.
- **Next checkpoint / safety:** Run browser-only lesson acceptance at desktop and 390px excluding training smoke and locked-test UI. Keep the overall learning milestone open. No credentials, final-test files, or locked holdout observations were accessed or consumed; no final test, market refresh, training, deployment, or publication occurred.

## Scheduled maintenance update (2026-10-27, truthful idle diagnostics and loss deltas)

- **Latest review evidence:** `artifacts/regression-monitor/latest-checks.json` at `2026-10-27T00:22:57+08:00` is overall PASS with 0 FAIL and 0 WARN; its pytest snapshot is `169 passed, 1 deselected`, popular-stock local coverage is 10/10, and locked-data isolation passes. Training smoke and one-time locked-test UI are SKIP. This snapshot predates the edits below.
- **Highest-priority reproduced defect and fix:** The idle-training monitor actually compares the toolbar Epoch to the configured epoch count (zero-padded), while its diagnostic said Epoch remained “待命.” Since the UI displays e.g. `025`, the PASS text was factually misleading. Updated the detail to state that training stayed idle and Epoch matches the configured value, including both observed and configured labels. Added a regression contract.
- **Roadmap increment:** Guided step 23's main synthetic gradient-descent trace now displays each step's ΔL and whether loss decreased, increased, or stayed constant. For `L=(w−1)²`, `w:3→2` now visibly reports `ΔL=−3.0000（下降）`; the guide explains the reading. This is synthetic learning content, not model training or quality evidence.
- **Verification:** Focused tests `2 passed`; safe suite `python3 -m pytest -q -k 'not public_api_and_async_validation_job'` → `170 passed, 1 deselected`; `node --check web/app.js`, Python AST parsing, and scoped `git diff --check` pass. No browser rerun; desktop/390px rendering is unverified, and the AGY snapshot remains pre-change.
- **Remaining / next checkpoint:** Run browser-only checks for idle Epoch diagnostics and step-23 ΔL at desktop and 390px, excluding training smoke and locked-test UI. Learning remains incomplete. Popular-stock expansion still requires an authorized local source; real cross-symbol magnitude learning requires comparable ordinary OOF summaries. No locked observations or `final-test-*.json` were accessed/changed/consumed; no final test, training, market refresh, deployment, or publication occurred.

## Scheduled maintenance update (2026-10-26, mini-batch update comparison)

- **Current AGY result:** Latest requested snapshot is overall PASS with no FAIL/WARN. It reports 169 passed and 1 deselected, local popular-stock coverage 10/10, and locked-data isolation PASS; training smoke and one-time locked-test UI are SKIP.
- **Bug disposition:** No concrete current defect was independently reproduced from current code or checks. The previous failures are older than the latest PASS snapshot. No bug fix is claimed.
- **Bounded roadmap improvement:** Guided step 19 compares a full batch update with two sequential mini-batch updates using four fixed synthetic gradients. Defaults show full batch `w=2→1.9`; mini-batches show `2→1.9→1.8`. The UI clarifies this holds gradients fixed for instruction; actual training recomputes gradients after updates.
- **Evidence / limitation:** Focused renderer acceptance `1 passed`; safe pytest selection `169 passed, 1 deselected`; JS syntax, monitor/test AST parsing, and scoped diff check passed. No post-change browser acceptance is claimed; the AGY render predates the change. This does not establish training or model quality.
- **Next checkpoint:** Run browser-only step-19 acceptance at desktop and 390px, excluding training smoke and locked-test UI. Popular-stock expansion remains dependent on an authorized source; real cross-symbol magnitude reading needs comparable ordinary OOF summaries.

## Scheduled maintenance update (2026-10-26, current review and bounded learning increment)

- **Current AGY snapshot:** `artifacts/regression-monitor/latest-checks.json`, `2026-10-26T23:08:56+08:00`, overall PASS with no FAIL/WARN. The recorded browser checks include Guided learning, desktop and 390px layouts, 10/10 local popular-stock coverage, and holdout isolation. Training smoke and the one-time locked-test UI are skipped.
- **Bug disposition:** No new highest-priority defect could be independently reproduced from current code/checks. The snapshot is newer than the 22:34 failure recorded below and includes the previously corrected monitor fixture. Do not report that older failure as current.
- **Bounded improvement:** Step 23 now names the dynamics implied by `1−2ηc` next to each synthetic loss path. The executable fixture checks one-step minimum, alternating convergence, boundary oscillation, and alternating divergence. This is a teaching improvement, not a model-performance finding.
- **Evidence/limit:** Focused test `1 passed`; safe suite `169 passed, 1 deselected`; JavaScript syntax, monitor/test AST parsing, and scoped diff checks passed. The AGY screenshot/check run predates this code change, so browser rendering after the change is still unverified. No claim of model quality, real-data training, or holdout evaluation.
- **Next checkpoint:** Re-run browser-only acceptance at desktop and 390px for the dynamics labels and editable inputs while continuing to exclude training smoke and locked-test UI. Keep popular-stock expansion blocked on an authorized data source and cross-symbol magnitude learning on comparable ordinary OOF summaries.

## Scheduled maintenance update (2026-10-26, gradient-descent fixture and stability lesson)

- **Latest AGY review:** `artifacts/regression-monitor/latest-checks.json` at `2026-10-26T22:34:11+08:00` reports overall FAIL. Only failing check is the multi-mode return/interval lesson group, specifically `多步梯度下降軌跡=False`; its safe pytest snapshot is `169 passed, 1 deselected`. Popular-stock local coverage (10/10), cross-symbol magnitude exercise, desktop and 390px checks, and locked-data isolation pass; real-data training smoke and locked-test confirmation UI are skipped.
- **Highest-priority defect reproduced:** Current implementation and focused renderer acceptance calculate the expected trajectories correctly. The browser predicate changed curvature to `c=2` after setting `η=1`, but did not reset η before checking the `c=2, η=.5` oscillation; it therefore observed a valid but different trajectory and reported a false FAIL.
- **Exact fix:** The monitor fixture now binds and explicitly sets the learning-rate input for each scenario. Expected `c=2, η=.5` values are `w: 3→−1→3`, and `c=2, η=.75` values are `w: 3→−3→9`. No product arithmetic was changed.
- **Roadmap increment:** Guided step 23 now explains the quadratic error multiplier `1−2ηc`: `0<ηc<1` converges, `ηc=1` reaches the minimum in one step, and `ηc>1` alternates and diverges. Synthetic acceptance verifies the one-step minimum (`c=1, η=.5`), near-boundary convergence (`η=.49`), oscillation, and divergence. This is learning content, not training or model-quality evidence.
- **Verification:** `python3 -m pytest -q tests/test_system.py::test_gradient_descent_trace_shows_recomputed_steps_and_rejects_invalid_inputs` → `1 passed`; `node --check web/app.js`, Python AST parsing of monitor/tests, and scoped `git diff --check` pass. AGY browser evidence is pre-change; no post-change browser or viewport acceptance is claimed.
- **Remaining / next checkpoint:** Re-run browser-only step-23 acceptance at desktop and 390px, including curvature, rate, start-weight, and step-count edits; keep training smoke and locked-test UI excluded. Neural-network learning remains incomplete. Popular-stock coverage is 10/10 locally and expansion needs an authorized data source; real cross-symbol magnitude learning needs compatible ordinary OOF summaries. No protected observations or `final-test-*.json` were accessed, changed, or consumed; no final test, market refresh, training, deployment, or publication occurred.

## Scheduled maintenance update (2026-10-26, curvature and gradient-descent stability)

- **Latest review / defect triage:** `artifacts/regression-monitor/latest-checks.json` at `2026-10-26T21:58:57+08:00` is overall PASS, including desktop and 390px browser checks, holdout isolation, and `169 passed, 1 deselected`. Routine real-data training smoke and one-time locked-test confirmation UI are SKIP by policy. No concrete defect was independently reproduced, so no bug fix is claimed.
- **Roadmap increment:** Guided step 23 now exposes a bounded curvature control `c` for synthetic `L(w)=c(w−1)²`, with gradient `2c(w−1)`. The user-visible trace and three-rate comparison recalculate from the selected curvature. Copy explains that curvature amplifies gradients and changes the stable learning-rate range. Updated `web/app.js`, `web/index.html`, `scripts/regression_monitor.py`, `tests/test_system.py`, and `docs/learning-guide.md`.
- **Observable acceptance:** Synthetic tests confirm `c=1, η=.25` yields the established halving trajectory; `c=2, η=.5` oscillates with constant loss (`w: 3→−1→3`, `L: 8→8→8`); `c=2, η=.75` diverges (`w: 3→−3→9`, `L: 8→32→128`); and out-of-range curvature is rejected. These are instructional calculations, not training or model-quality evidence.
- **Verification:** Focused test `python3 -m pytest -q tests/test_system.py::test_gradient_descent_trace_shows_recomputed_steps_and_rejects_invalid_inputs` → `1 passed`; `node --check web/app.js`, Python AST parsing for monitor/tests, and scoped `git diff --check` passed. The AGY snapshot predates this change; no post-change browser or viewport acceptance is claimed.
- **Remaining / next checkpoint:** Run browser-only Guided step-23 acceptance at desktop and 390px, excluding training smoke and locked-test UI, including edits to curvature, start weight, and update count. The broader neural-network learning milestone remains incomplete. Popular-stock local coverage remains 10/10 and expansion needs an authorized source; real cross-symbol magnitude learning needs compatible ordinary OOF summaries. No locked observations or `final-test-*.json` were accessed, modified, or consumed; no final test, market refresh, training, deployment, or publication occurred.

## Scheduled maintenance update (2026-10-26, batch-gradient direction sensitivity)

- **Review / defect:** The latest AGY check at `2026-10-26T20:45:54+08:00` is PASS. It includes browser Guided interaction, desktop and 390px checks; routine training smoke and the one-time final-test UI are intentionally skipped. I inspected the current acceptance and code without finding a concrete current defect to reproduce, so no bug fix is claimed.
- **Roadmap increment:** Advanced the incomplete neural-network learning objective in Guided step 19. The batch-gradient readout now interprets the leave-one-out comparison: it states whether omitting the most influential sample preserves the batch update direction, reverses the gradient sign, or changes a zero update into a nonzero update. Synthetic checks cover default `(-2,4,1,1)` (direction unchanged), `(-1,1,0,0)` (zero-to-nonzero), and `(-1,4,0,0)` (sign reversal). Updated the learning guide and browser acceptance predicate.
- **Verification:** Focused renderer test: `1 passed`; safe project selection `python3 -m pytest -q -k 'not public_api_and_async_validation_job'`: `169 passed, 1 deselected`; `node --check web/app.js`, Python AST parsing for monitor/tests, and scoped `git diff --check` passed. The tests execute synthetic arithmetic and actual renderer output only; no training or model-quality claim. Browser acceptance was not rerun after the change, so the latest AGY snapshot is pre-change evidence.
- **Remaining / next checkpoint:** Run browser-only Guided acceptance at desktop and 390px for the new direction readout, excluding training smoke and locked-test UI. Popular-stock local coverage remains 10/10 and expansion needs an authorized source; real cross-symbol rise/fall magnitude interpretation needs comparable ordinary OOF summaries. The broader neural-network learning milestone remains incomplete. No locked observations or `final-test-*.json` were accessed, modified, or consumed; no final test, market refresh, training, deployment, or publication occurred.

## Scheduled maintenance update (2026-10-26, batch-gradient sample sensitivity)

- **Review / defect:** `artifacts/regression-monitor/latest-checks.json` at `2026-10-26T17:39:01+08:00` reports overall PASS; the only SKIPs are routine training smoke and the one-time final-test confirmation UI. No concrete current defect was independently reproduced, so no bug fix is claimed.
- **Roadmap increment:** Advanced the incomplete neural-network learning objective in Guided step 19. The batch-gradient calculator now reports the largest change in mean gradient when any single sample gradient is omitted. For synthetic `(-2,4,1,1)`, the mean is `1` and the maximum leave-one-out shift is `1`; for `(1,1,1,1)` it is `0`; for `(-1,1,0,0)` it is `1/3`. The visible result labels this as sensitivity of the current batch, not a model-quality metric. Updated the learning guide, executable renderer test, and browser-monitor acceptance predicate.
- **Verification:** Focused renderer test: `1 passed`; safe project selection `python3 -m pytest -q -k 'not public_api_and_async_validation_job'`: `167 passed, 1 deselected`; `node --check web/app.js`, Python AST parsing for monitor/tests, and `git diff --check` passed. This is synthetic arithmetic only; no training or model-quality evidence. Browser acceptance was not rerun after the change.
- **Remaining / next checkpoint:** Run browser-only Guided acceptance at desktop and 390px for the new readout, excluding training smoke and locked-test UI. Popular-stock local coverage remains 10/10 and expansion needs an authorized source; real cross-symbol rise/fall magnitude interpretation needs comparable ordinary OOF summaries. No locked observations or `final-test-*.json` were accessed, modified, or consumed; no final test, market refresh, training, deployment, or publication occurred.

## Scheduled maintenance update (2026-10-26, floating-point catalog checks and gradient-spread interpretation)

- **Latest AGY evidence:** `artifacts/regression-monitor/latest-checks.json` at `2026-10-26T16:26:47+08:00` reports Guided catalog failures at clauses 81 and 95, plus two regression-test failures. Navigation itself passed (`1→2→1`). The artifact's safe pytest result is `2 failed, 165 passed, 1 deselected` and predates these fixes.
- **Highest-priority independently reproduced defect:** Catalog clause 81 compared the computed single-neuron loss to `0.04` with strict floating-point equality; clause 95 did the same for a multi-input gradient and `-0.8`. Running the exact safe suite reproduced the two failing source-contract tests: they expected combined assertion strings while the monitor already checked the corresponding subclauses separately. The computed values are subject to floating-point rounding, which can make the browser catalog reject correct arithmetic.
- **Exact changes:** Replaced the two fragile loss/gradient equality checks with absolute-error tolerances below `1e-12`. Updated source-contract assertions to check the existing component clauses independently. The batch-gradient result now explains that nonzero standard deviation means individual gradients typically differ from their mean, while zero means every gradient equals the mean; the learning guide and executable renderer test cover both states.
- **Roadmap increment:** Advanced the unfinished neural-network learning milestone with a direct interpretation of the batch-gradient spread statistic. Synthetic values only: `[-2,4,1,1]` produces SD `2.1213` and the interface explains spread; `[1,1,1,1]` produces SD `0` and the interface explains complete agreement. This is not training or model-quality evidence. Popular-stock coverage remains 10/10 local symbols; expansion needs an authorized source, and real cross-symbol magnitude reading still needs comparable ordinary OOF summaries.
- **Verification:** Reproduced pre-fix safe selection: `2 failed, 165 passed, 1 deselected`. Focused post-fix tests: `3 passed`; complete safe selection `python3 -m pytest -q -k 'not public_api_and_async_validation_job'`: `167 passed, 1 deselected`. `node --check web/app.js`, Python AST parsing for monitor/tests, and scoped `git diff --check` passed. Browser/desktop/390px acceptance was not rerun; latest AGY JSON remains unchanged pre-fix evidence.
- **Remaining / next checkpoint:** Re-run Guided browser acceptance at desktop and 390px to confirm catalog clauses 81 and 95 after the tolerance fix. Continue neural-network learning in bounded steps; popular-stock expansion awaits authorized data and real cross-symbol magnitude reading awaits comparable ordinary OOF summaries. No `final-test-*.json` or locked observations were accessed, written, or consumed; no one-time final test, market refresh, training, deployment, or publication occurred.

## Scheduled maintenance update (2026-10-26, Guided catalog diagnostics and batch-gradient spread)

- **Latest AGY evidence:** `artifacts/regression-monitor/latest-checks.json` at `2026-10-26T15:52:03+08:00` reports one FAIL, `多模式學習互動`. Navigation values are `1→2→1`; the opaque lesson-catalog conjunction is false. The recorded safe pytest snapshot is `164 passed, 1 deselected` and predates this change.
- **Highest-priority defect / reproduction:** The monitor reduced 116 catalog assertions to one boolean, so the reported catalog failure could not identify its cause. The direct browser attempt could not run because Chrome aborted at launch; no product defect is independently confirmed. Changed the monitor to retain each clause result and report failed clause indices, preserving the full pass/fail gate.
- **Roadmap increment:** Guided batch-gradient lesson (step 19) exposes population variance and standard deviation. Synthetic `[-2,4,1,1]` has mean `1`, variance `4.5`, SD `2.1213`; `[1,1,1,1]` has the same mean but variance `0`. This teaches that equal batch-average updates can hide different sample disagreement. No training or model-quality claim.
- **Verification:** Focused tests `2 passed`; `node --check web/app.js`, Python AST parsing for monitor/tests, and scoped `git diff --check` passed. No browser rerun or viewport acceptance is claimed; the AGY JSON remains unchanged pre-change evidence.
- **Remaining / next checkpoint:** Run the browser-only Guided check when Chrome is available and use the new clause indices to isolate any catalog mismatch; inspect desktop and 390px. Popular-stock coverage remains local 10/10 pending an authorized source; real cross-symbol magnitude work still needs compatible ordinary OOF summaries. No locked observations or `final-test-*.json` accessed, final test, market refresh, training, deployment, or publication.

## Scheduled maintenance update (2026-10-26, batch-gradient spread and catalog failure triage)

- **Latest AGY evidence:** `artifacts/regression-monitor/latest-checks.json` reports one FAIL: `多模式學習互動`, with navigation `1→2→1` passing and `課程目錄=False`. The report does not expose the false catalog clause. Safe pytest snapshot in that artifact: `164 passed, 1 deselected`; it is pre-change evidence.
- **Defect disposition:** Reviewed the current monitor predicate and lesson catalog. The catalog result is one large conjunction, so the saved failure cannot identify its failing clause. A direct browser reproduction was attempted against the local app, but installed Chrome aborted at launch with `SIGABRT`; no individual product defect was independently reproduced, and no speculative predicate change is claimed.
- **Exact implementation change:** Guided step 19's editable batch-gradient result now computes and displays population variance and standard deviation alongside the mean and range. For gradients `[-2,4,1,1]`, mean `1`, variance `4.5`, standard deviation `2.1213`; four `+1` gradients have the same mean but variance `0`. The monitor's executable lesson predicate now checks these values. Updated `docs/learning-guide.md`.
- **Milestone advanced:** Bounded neural-network learning increment makes per-sample gradient spread observable when batches produce the same mean update. This is synthetic arithmetic, not model training or model-quality evidence.
- **Verification:** `python3 -m pytest -q tests/test_system.py::test_batch_gradient_lesson_exposes_direction_disagreement` → `1 passed`; browser catalog diagnosis remains unverified because Chrome did not launch. No training, locked-test UI, final test, or market refresh was run.
- **Remaining / next checkpoint:** In a browser-capable environment, split the catalog aggregate into named diagnostic clauses and rerun Guided navigation/catalog at desktop and 390px, excluding training and locked-test UI. Popular-stock local coverage remains 10/10 and expansion needs an authorized source; cross-symbol rise/fall magnitude reading still needs compatible ordinary OOF summaries.

## Scheduled maintenance update (2026-10-26, negative-z ReLU acceptance and explanation)

- **Latest AGY evidence:** `artifacts/regression-monitor/latest-checks.json` at `2026-10-26T14:05:42+08:00` is FAIL. Safe pytest snapshot: `162 passed, 1 deselected`; browser failures are lesson interaction and multi-mode Guided navigation. Popular-stock local coverage is 10/10; routine training smoke and locked-test UI were skipped; holdout-isolation check passed.
- **Highest-priority independently reproduced defect:** The step-17 browser predicate changes `x₁` to `−2` while retaining `w₁=0.5, x₂=1, w₂=−0.4, b=0.2`. That produces `z=−1.20`, but the predicate expected `z=0` and a zero-sum contribution state. The assertion is mathematically inconsistent with its fixture and marks the correct inactive-ReLU branch as FAIL.
- **Exact change:** Corrected the predicate to require `z=−1.20`, ReLU output 0, defined signed contributions, and all three gradients 0. The rendered lesson now explains that `z≤0` gives `ReLU′(z)=0`, hence local gradients are zero. Updated `docs/learning-guide.md` and executable renderer acceptance.
- **Milestone advanced:** The two-input forward-pass lesson now shows why negative pre-activation blocks the local gradient, with an editable example (`x₁=−2` gives `z=−1.2`, output 0, gradients 0). This is synthetic neural-network instruction, not model training or quality evidence.
- **Verification:** Focused pytest: `2 passed, 75 deselected`; `node --check web/app.js`; Python AST parse for monitor/tests passed. No browser rerun or desktop/390px acceptance; the 14:05 JSON is pre-change evidence.
- **Remaining / next checkpoint:** The separate multi-mode Guided navigation check still fails (`課程目錄=False`); inspect the remaining catalog predicate against the active 22-step lesson content, then use a browser-only route excluding training smoke and locked-test UI. Popular-stock coverage remains 10/10 until an authorized source is available; real cross-symbol magnitude reading needs compatible ordinary OOF summaries. No protected observations or `final-test-*.json` accessed; no final test, market refresh, training, deployment, or publication.

## 2026-10-26 maintenance review: missing saved-summary guard

- **Review input:** `artifacts/regression-monitor/latest-checks.json`, `2026-10-26T09:59:26+08:00`, overall FAIL. Safe suite snapshot is PASS (`157 passed, 1 deselected`); browser failures are saved-summary fixture and multi-mode Guided next/back.
- **Highest-priority reproduced defect:** With an unavailable summary, `savedComparisonCompatibility()` returned a generic inability-to-judge message. The existing monitor's `statusVisible` acceptance requires an explicit no-ranking state, so its saved-summary FAIL follows from current code.
- **Correction:** Missing-summary output now explicitly says `不可直接排名`, states that both symbols need ordinary walk-forward summaries, and tells the learner to complete those validations. Added a Node-backed acceptance test against the actual function and updated `docs/learning-guide.md`.
- **Roadmap progress:** The rise/fall magnitude comparison flow now makes its prerequisite state actionable. This is interface/learning guidance only; no live cross-symbol comparison or quality claim.
- **Evidence:** `2 passed, 71 deselected`; `node --check web/app.js`; Python AST parse for monitor and tests; scoped `git diff --check`. No post-change browser/desktop/390px evidence.
- **Remaining / next checkpoint:** Browser-only run without training smoke or locked-test UI; inspect the missing-summary state and capture a locator/state trace for Guided next/back at desktop and 390px. Local popular-stock list remains 10/10; additional coverage needs an authorized source, and comparison needs compatible ordinary OOF summaries.

## 2026-10-26 maintenance review: lesson count and clipping-angle output

- **Review input:** `artifacts/regression-monitor/latest-checks.json` at `2026-10-26T08:45:08+08:00` reports FAIL; safe pytest snapshot is PASS (`156 passed, 1 deselected`). Browser groups fail for lesson interaction, saved-summary fixture, and multi-mode learning.
- **Highest-priority reproduced defect:** The visible `#learningSummary` advertised 23 steps, but the current lesson catalog and browser acceptance use 22. The navigation aggregate checks that the summary count matches the catalog, so the stale count makes acceptance fail.
- **Correction:** Updated the visible count to 22 and added a regression contract for the count/check alignment.
- **Roadmap increment:** Four-dimensional clipping now shows the direction change in degrees as well as cosine. Synthetic `(1,2,2,4)` at limit 2 yields global-norm clipping `1.0000 / 0.00°` and component clipping `0.9430 / 19.44°`. Guide and browser acceptance updated; no training or model-quality inference.
- **Verification:** Focused pytest `1 passed, 70 deselected`; `node --check web/app.js`, Python AST parse, and scoped `git diff --check` passed. No post-change browser or viewport run; latest AGY artifact remains pre-change.
- **Remaining / checkpoint:** Re-run browser-only acceptance without training smoke or locked-test UI; localize saved-summary and remaining lesson failures and inspect navigation at desktop/390px. Popular-stock coverage remains 10/10 pending authorized source; real cross-symbol magnitude work requires compatible ordinary OOF summaries.

## 2026-10-26 maintenance review: Guided navigation acceptance coupling

- **Review input:** `latest-checks.json` at `2026-10-26T06:59:54+08:00` reports FAIL; safe pytest snapshot PASS (`155 passed, 1 deselected`). Multi-mode navigation reports FAIL alongside lesson and saved-summary browser groups.
- **Highest-priority reproduced defect:** `lesson_ok` required `(reset_notice_hidden or "已恢復上次進度" in lesson_resume_notice)` while also checking next/back. A valid resumed session can show the notice, so navigation acceptance fails for an unrelated expected UI state. Reset notice hiding is already captured immediately after the monitor's explicit fresh reset.
- **Exact change:** Removed the notice disjunction from `lesson_ok`. Added `reset_notice_hidden` as a separate required input to `learning_ok`, preserving both navigation and fresh-reset acceptance.
- **Roadmap increment:** Step 22 clipping exercise now prompts a limit sweep across 0, 0.5, 1, and 4 and explains the resulting weights for `w=2,g=4,η=0.1`: 2, 1.95, 1.9, 1.6. Updated learning guide and executable source/renderer contract. Synthetic arithmetic only; no model-quality claim.
- **Verification:** Focused pytest `2 passed, 68 deselected`; JS syntax, Python AST and scoped diff checks pass. No browser rerun; latest AGY JSON remains pre-change evidence.
- **Remaining / checkpoint:** Browser-only run at desktop/390px without training smoke or locked-test UI; test fresh and resumed Guided navigation and trace saved-summary fixture. Popular-stock coverage is 10/10 until an authorized source is available; comparable ordinary OOF summaries remain needed for real cross-symbol magnitude reading. No protected data/final-test access, final test, market refresh, training, deployment, or publication.

## 2026-10-26 maintenance review: step-18 fixture isolation

- **Review input:** Latest monitor artifact `2026-10-26T06:23:34+08:00` reports FAIL for lesson interaction, saved-summary fixture, and multi-mode navigation. Its safe pytest snapshot passed (`155 passed, 1 deselected`).
- **Highest-priority reproduced issue:** In the monitor's current ordering, the multi-input fixture empties `#multiInputX1`; the following gradient-update fixture read the same DOM controls without restoring defaults. The step-18 acceptance therefore calculated an invalid input state and failed. This reproduces an acceptance fixture defect, not a learner-facing product defect.
- **Correction:** Restore x₁, w₁, x₂, w₂, bias, target and η before the step-18 fixture render. The new predicate also checks the displayed loss trend. Added visible output stating whether the synthetic update decreased, increased, or preserved loss; the learning guide documents the default descent and η=0.5 overshoot cases.
- **Verification:** Focused tests `2 passed, 68 deselected`; safe test selection `155 passed, 1 deselected`; `node --check web/app.js` and scoped `git diff --check` pass. No browser rerun; latest artifact remains pre-change evidence. This is synthetic lesson math, not training or model-quality evidence.
- **Open items / checkpoint:** Browser-only check step 18 at desktop/390px; then obtain fresh state/locator evidence for saved-summary and multi-mode navigation FAILs. Popular stock coverage is 10/10 locally and needs an authorized data source to expand. Real cross-symbol magnitude comparison needs compatible ordinary OOF summaries. Locked holdout and `final-test-*.json` were not accessed; no final test, data refresh, training smoke, deployment or publication.

## Scheduled maintenance update (2026-10-26, gradient-update acceptance and labeled SGD readout)

- **Latest AGY evidence:** `artifacts/regression-monitor/latest-checks.json` at `2026-10-26T05:41:58+08:00` reports overall FAIL. The safe pytest snapshot was PASS (`153 passed, 1 deselected`); browser groups fail for lesson interactions (step 18), saved-summary fixture, and multi-mode navigation. Local stock coverage is 10/10; training smoke and locked-test UI are skipped.
- **Highest-priority reproduced defect:** The step-18 predicate expected an initial `w₁=0.6` although the current widget defaults to `0.5`, and required derivative labels that were absent from the rendered update result. Recalculation from current defaults gives `z=0.8`, `L=0.04`, gradients `(-0.8,-0.4,-0.4)`, and with η=0.1 the updated parameters `(0.58,-0.36,0.24)` and loss `0.0016`; the stale predicate therefore marked this correct flow FAIL.
- **Exact changes:** Corrected the browser predicate to match the actual default and substitution results. The step-18 result now labels `∂L/∂w₁`, `∂L/∂w₂`, and `∂L/∂b` before showing each `θnew=θ−η×gradient` substitution. Updated the learning guide and added a Node-backed renderer acceptance for default values, η=0.5, and invalid η.
- **Milestone advanced / limits:** Advanced the neural-network learning objective by making each named derivative directly traceable to its parameter update. Acceptance output includes `∂L/∂w₁=-0.8000` and `w₁ 0.5−0.1×(-0.8000)=0.5800`, with updated loss `0.0016`; η=0.5 yields loss `1.0000`, and η=2 is rejected. This is synthetic arithmetic, not training or model-quality evidence; the broader milestone remains incomplete.
- **Verification:** Focused renderer pytest: `1 passed, 69 deselected`; safe project selection: `154 passed, 1 deselected`. `node --check web/app.js`, monitor/test AST parsing, and scoped `git diff --check` passed. No browser rerun or desktop/390px acceptance is claimed; the latest JSON remains pre-change review data.
- **Remaining / next checkpoint:** Trace the still-failing saved-summary fixture and Guided next/back browser flow with fresh locator/state evidence, then inspect step 18 and navigation at desktop/390px using a browser-only route that excludes training smoke and locked-test UI. Popular-stock coverage stays at 10/10 until an authorized source is available; real cross-symbol magnitude reading still needs compatible ordinary OOF summaries. No protected holdout or `final-test-*.json` was read/written/consumed; no final test, market refresh, deployment, or publication occurred.

## Scheduled maintenance update (2026-10-26, explicit SGD parameter substitutions)

- **Latest AGY evidence / defect triage:** `artifacts/regression-monitor/latest-checks.json` at `2026-10-26T04:33:24+08:00` reports FAIL in lesson interactions (step-18 gradient update subcheck), saved-summary fixture, and multi-mode navigation; the safe pytest selection is PASS (`151 passed, 1 deselected`), stock coverage is 10/10, training smoke and locked-test UI are skipped. I checked the step-18 arithmetic at `η=0.5`: the current calculator yields updated loss `1.0000`, which matches its predicate, so this report alone does not establish a live failure. The saved-summary and navigation browser failures remain unlocalized; the browser run has not been repeated.
- **Highest-priority concrete defect reproduced:** The accepted step-18 readout showed gradients and final parameter values, but omitted the substituted `θnew = θ − η × gradient` calculation. This left the visible result insufficient to trace how each update was obtained.
- **Exact change:** `renderGradientUpdateExercise()` now prints the substitution for `w₁`, `w₂`, and `b`, including current parameter, selected learning rate, gradient, and updated parameter. Updated the guide, browser predicate, and source-contract test to pin all three equations.
- **Observable milestone / acceptance:** With defaults, it displays `w₁ 0.6−0.1×(-0.8000)=0.6800`, `w₂ -0.4−0.1×(-0.4000)=-0.3600`, and `b 0.2−0.1×(-0.4000)=0.2400`, followed by updated loss `0.0016`. This advances the neural-network learning milestone with synthetic SGD arithmetic only; it is not training or model-quality evidence.
- **Verification:** Focused learning/saved-summary selection passed (`3 passed, 66 deselected`). The full safe selection first caught a stale assertion for the prior result-copy form; after updating that contract to the new rendered form, it passed (`152 passed, 1 deselected`). `node --check web/app.js`, Python AST parsing for monitor/tests, and scoped `git diff --check` passed. The latest JSON remains pre-change review evidence; no post-change browser or desktop/390px acceptance is claimed.
- **Remaining / next checkpoint:** Run a browser-only lesson path excluding training smoke and locked-test UI to verify step 18 and capture fresh locators/state for saved-summary and Guided navigation at desktop/390px. Popular-stock local coverage remains 10/10 and expansion needs an authorized source; real cross-symbol magnitude comparison still needs compatible ordinary OOF summaries. No locked observations or `final-test-*.json` were read or changed; no final test, training smoke, market refresh, deployment, or publication occurred.

## Scheduled maintenance update (2026-10-26, navigation fixture reset)

- **Current review:** Latest JSON is `2026-10-26T02:11:29+08:00`; safe pytest PASS (`143 passed, 1 deselected`), while three browser groups fail (lesson interactions, saved-summary fixture, multi-mode navigation).
- **Reproduced and fixed:** Monitor later set `lessonIndex=21`, then reset only that value before expecting a seven-click path from lesson 1 to 8. The saved progress snapshot remained at 21. Reset now synchronizes both lesson indices before rendering; source contract covers the reset/order.
- **User-visible increment:** Added learner guidance about browser-local saved progress, previous lesson, restart, and site-data clearing; guide and acceptance test updated.
- **Verification:** Focused `2 passed, 64 deselected`; JS syntax, Python AST and scoped diff checks passed. Browser rerun not done, so latest JSON remains pre-fix evidence. Other reported browser failures remain unresolved.
- **Next:** Capture a fresh browser-only trace for ReLU, gradient update, saved-summary and navigation at desktop/390px; exclude training smoke and locked-test UI. No protected data, final test, market refresh, deployment or publication.

## Scheduled maintenance update (2026-10-26, direction-conditioned OOF error)

- **Latest AGY review / defect disposition:** `artifacts/regression-monitor/latest-checks.json` is timestamped `2026-10-26T00:58:08+08:00`: overall FAIL, with browser checks for lesson interaction, saved-summary fixture, and multi-mode navigation; routine pytest is PASS (`141 passed, 1 deselected`), stock coverage is 10/10, training smoke and locked-test UI were skipped. I inspected the current predicates and fixtures but could not independently reproduce a concrete product defect from source alone. The prior 00:21:07 summary in this file is stale relative to the JSON. No defect fix is claimed; browser failures remain open for a browser-capable trace.
- **Exact implementation:** Extended `directionMixSummary()` to report MAE and valid sample count grouped by the actual return direction, count strict up/down sign mismatches, and keep a wrong-direction prediction inside its actual-direction group's MAE. Null/blank pairs remain excluded. Updated the learning guide and synthetic browser-monitor predicate.
- **Observable acceptance:** Synthetic pairs produce rising-group MAE 2.000 pp (n=3), falling-group MAE 1.000 pp (n=2), and one strict direction mismatch; a null pair is excluded. The focused renderer/monitor contract and saved-summary tests passed (`3 passed, 62 deselected`). Post-edit safe selection passed (`70 passed, 1 deselected`); `scripts/synthetic_regression.py`, `node --check web/app.js`, monitor/test Python AST parsing, and scoped `git diff --check` passed.
- **Milestone advanced / limits:** Advanced the predicted rise/fall magnitude objective with actual-direction-conditioned OOF error. This is a synthetic acceptance fixture and display logic only, not model-quality evidence. Popular-stock expansion still needs an authorized data source; real cross-symbol comparison still needs compatible ordinary OOF summaries.
- **Remaining / next checkpoint:** In a browser-capable environment, trace the three current browser FAIL groups and inspect this readout at desktop/390px. No `final-test-*.json` or locked observations were read or changed; no final test, market refresh, training smoke, deployment, or publication occurred.

## Scheduled maintenance update (2026-10-26, two-step momentum learning)

- **Latest AGY review / defect disposition:** `artifacts/regression-monitor/latest-checks.json` at `2026-10-26T00:21:07+08:00` reports three browser FAIL groups: interval/ReLU/later lesson interaction, cross-symbol saved-summary fixture, and multi-mode navigation. Its safe selection passed (`140 passed, 1 deselected`); popularity coverage was 10/10 and no training smoke or locked-test UI was run. I compared the failing predicates with current monitor/app logic; no concrete source defect was independently reproduced. A focused read-only Playwright attempt could not launch because the installed package has no Chromium executable. I did not download one. No defect fix is claimed; these browser failures remain open pending a browser-capable environment and locator/trace evidence.
- **Exact implementation:** Extended lesson 20's momentum calculator with editable second-step gradient `gₜ₊₁`. It carries the computed first-step velocity into the next update and displays both velocity/weight pairs plus a two-step β=0 comparison. Updated the in-page explanation, guide, and browser acceptance predicate.
- **Observable acceptance:** For β=0.9, previous velocity 0.5, gradients 1 and 0.5, weight 2, and η=0.1, the lesson displays `(vₜ,wₜ)=(1.4500,1.8550)` then `(vₜ₊₁,wₜ₊₁)=(1.8050,1.6745)`. With β=0, the two-step weight is 1.8500. Blank second gradient is rejected. Focused tests: `2 passed, 61 deselected`; `node --check web/app.js`, monitor/test Python AST parsing, and scoped `git diff --check` passed. Initial test runs exposed stale expected copy and a strict float-equality assertion; expectations were corrected to the current UI and a tolerance, without weakening the production check.
- **Milestone and limits:** Advanced the incomplete neural-network learning objective with an interactive explanation of momentum state carried across two updates. It uses synthetic arithmetic only; it is not training or model-quality evidence. Popular-stock local coverage remains 10/10 and needs an authorized source to expand. Real cross-symbol rise/fall magnitude comparison still needs compatible ordinary OOF summaries.
- **Next checkpoint / safety:** On a browser-capable local environment, trace the three reported failures and inspect lesson 20 at desktop and 390px without training or locked-test UI. Then refresh acceptance evidence. No protected observations or `final-test-*.json` were opened or changed; no final test, market refresh, deployment, or publication occurred.

## Scheduled maintenance update (2026-10-25, mini-batch aggregation and lesson check)

- **Latest review / reproduced defect:** `artifacts/regression-monitor/latest-checks.json` at `2026-10-25T21:59:05+08:00` reports three browser FAIL groups while its safe pytest selection passes. In the current monitor, the batch-gradient fixture sets `lessonIndex=18` (array entry 18 is step 19) but requires `第 20 / 22 步`; `renderLesson()` formats progress as `lessonIndex + 1`, so this predicate is necessarily false and pollutes the lesson/navigation check. This is a monitor acceptance defect, not evidence of a broken lesson. The other interval/ReLU, saved-summary, and navigation details are not independently localized this round.
- **Exact change:** Corrected the batch-gradient browser predicate to expect `第 19 / 22 步`. Extended the four-sample calculator and visible result to compare mean aggregation with direct summation. For gradients `(-2,4,1,1)`, mean 1 updates weight 2 to 1.9, while sum 4 updates it to 1.6 at the same learning rate. The guide, browser predicate and executable renderer contract now cover both values.
- **Roadmap status:** Advanced the neural-network learning objective with an editable explanation that averaging prevents update scale from multiplying directly with batch size. Popular-stock local coverage remains 10/10; expansion still needs an authorized source. Real cross-symbol rise/fall magnitude comparison still needs compatible ordinary OOF summaries. No model-quality claim.
- **Verification:** Focused pytest `2 passed, 60 deselected`; safe pytest selection `131 passed, 1 deselected`; `node --check web/app.js`, Python AST parsing and `git diff --check` passed. The latest AGY JSON remains unchanged pre-fix evidence; no browser/desktop/390px acceptance is claimed.
- **Remaining / next checkpoint:** Run the browser-only lesson route at desktop and 390px, excluding training smoke and locked-test UI; separately localize the remaining interval/ReLU, saved-summary, and navigation failures with fresh locator evidence. No locked observations or `final-test-*.json` accessed; no final test, market refresh, deployment, or publication.

## Scheduled maintenance update (2026-10-25, mini-batch formula contract)

- **Severity / source:** `artifacts/regression-monitor/latest-checks.json` at `2026-10-25T20:48:04+08:00` reports `1 failed, 130 passed, 1 deselected`. Safe reproduction identifies `test_mult_input_neuron_lesson_contract`: the displayed lesson uses Unicode minus `−` in `(−2+4+1+1)/4=1`, while test and browser predicate expected ASCII `-`. The false catalog condition contributes to the reported navigation/lesson failure. Other reported saved-summary failure is not yet independently localized.
- **Fix and feature:** Test and monitor now assert the visible formula. The four-gradient renderer explains exact cancellation when the user enters `(-1,1,0,0)`: average 0, weight 2 unchanged, despite two nonzero opposite gradients. Learning guide and renderer test updated.
- **Verification:** Focused contracts passed (`2 passed, 60 deselected`); safe pytest selection passed (`131 passed, 1 deselected`); JS syntax and Python AST checks passed. The first focused rerun found a second stale ASCII-minus source assertion; it was updated before the passing rerun. No full browser monitor or viewport acceptance is claimed; JSON remains the unchanged pre-fix report. This is synthetic education, not model-quality evidence.
- **Next checkpoint:** Collect browser locators for remaining lesson and saved-summary FAILs without training smoke or locked-test UI. No protected observations, final-test files, market data refresh, deployment or publication touched.

## Scheduled maintenance update (2026-10-25, stale batch-gradient acceptance predicate)

- **Severity / source:** Latest regression check `2026-10-25T20:12:20+08:00` reports “多模式學習互動” FAIL. The current monitor catalog condition expected the obsolete formula `(−2+4)/2=1`. The current step 19 lesson and widget use four gradients, `(-2+4+1+1)/4=1`; the hyphen character also differed (ASCII versus Unicode). Source comparison reproduces the false predicate. Since `lesson_ok` includes `lesson_catalog_ok`, the condition forces navigation acceptance false.
- **Fix:** Monitor now asserts the current four-gradient formula, and lesson copy now matches the widget's four inputs.
- **Related user-visible progress:** Mini-batch results now display the sample gradient range as well as sign counts, average, and one update. The default `(-2,4,1,1)` yields range −2…4, average 1, and weight 1.9 from 2 at rate 0.1. Guide updated.
- **Verification:** Focused contracts passed 3 tests with 59 deselected; JS syntax, Python AST, and scoped diff checks passed including the added test assertion. Full browser monitor was not rerun, and latest JSON remains pre-fix evidence. No model-quality inference.
- **Next checkpoint:** Safe browser-only verification of lesson 19/navigation at desktop and 390px; obtain fresh locator details for the remaining interval/ReLU and saved-summary failures. No locked holdout/final-test observations accessed or consumed.

## Scheduled maintenance update (2026-10-25, resume-state isolation and cross-symbol reading order)

- **Latest review / reproduced defect:** `artifacts/regression-monitor/latest-checks.json` at `2026-10-25T19:03:11+08:00` reports four FAIL groups. The Guided-navigation predicate resets `lessonIndex` to 0 but leaves the loaded `savedLearningProgress.lessonIndex` unchanged. `renderLesson()` used the current index to decide whether a resume notice should show, then incorrectly labeled the next lesson as resumed from the old saved index. This is independently reproduced from current app and monitor logic and explains the navigation failure; later lesson-control failures are consistent with that contaminated monitor state. The saved-comparison and Loss-pointer failures were not independently reproduced from source alone.
- **Exact fix:** Resume notice visibility now requires actual saved progress and a nonzero current lesson; the notice names the current lesson. Both monitor lesson resets synchronize the in-memory saved-progress snapshot to zero. The browser acceptance records that the notice is hidden at the reset state and accepts the notice after one-step navigation only when shown correctly.
- **Roadmap increment:** The cross-symbol lesson card and learning guide now teach a concrete reading order: compare direction shares, then compare actual/predicted absolute magnitudes separately for up and down moves; neither direction agreement nor magnitude similarity compensates for direction mismatch. This is a user-visible learning step with a source contract. It uses synthetic lesson examples and makes no model-quality claim.
- **Verification:** Focused pytest `3 passed, 59 deselected`; `node --check web/app.js`, Python AST parsing for monitor/tests, and scoped `git diff --check` passed. One initial new contract failed because the phrase in HTML used a shorter label; the assertion now checks the shared concept wording and passes. Full browser monitor was not rerun, so no rendered desktop/390px acceptance is claimed. Latest review JSON remains unchanged pre-fix evidence.
- **Remaining / next checkpoint:** Run a browser-only check excluding training smoke and all locked-test UI to confirm Guided next/back, lesson widgets, and the new cross-symbol card at desktop and 390px. Separately trace saved-summary compatibility and Loss pointer tooltip failures. Popular-stock local coverage remains 10/10; expansion needs an authorized source. Real cross-symbol magnitude reading still needs comparable ordinary OOF summaries. No protected holdout or `final-test-*.json` was read or changed; no final test, market refresh, training smoke, deployment, or publication occurred.

## Scheduled maintenance update (2026-10-25, idle Epoch contract and batch-gradient direction lesson)

- **Latest review / independently reproduced defect:** The latest `artifacts/regression-monitor/latest-checks.json` is timestamped `2026-10-25T17:14:33+08:00` and reports FAIL for “例行瀏覽器檢查不啟動訓練”. The current app sets `#toolbarEpoch` to the configured epoch count padded to three digits (`025` by default) while idle (`web/app.js`, `updateConfigSummary()`); the monitor incorrectly accepted only `待命` or `—` (`scripts/regression_monitor.py`). Thus an idle page with no `.is-training` class was reported as failed. This is a monitor predicate defect, not evidence of training or model failure.
- **Exact correction:** The monitor now checks that the idle toolbar Epoch equals the configured `#epochs` value padded to three digits, and independently confirms `#network` has no `is-training` class. It does not start training or alter the current settings.
- **Roadmap increment / observable acceptance:** The four-sample mini-batch lesson now reports counts of positive, negative, and zero gradients and explains when opposite signs partly cancel before averaging. Default synthetic gradients `(-2,4,1,1)` show 3 positive, 1 negative, average `1`, one update, and `w: 2 → 1.9`. Added executable renderer acceptance and updated the learning guide and browser predicate. Synthetic instruction only; no training or model-quality claim.
- **Verification:** Focused pytest `1 passed, 58 deselected`; safe `tests/test_system.py` selection `58 passed, 1 deselected`; `node --check web/app.js`, Python AST parsing for monitor/tests, and scoped `git diff --check` passed. The browser monitor was not rerun; no browser or desktop/390px acceptance is claimed. The latest AGY JSON remains unchanged pre-change review data.
- **Remaining / next checkpoint:** Re-run a browser-only route with training smoke and locked-test UI excluded, verify idle toolbar acceptance, and trace the reported lesson interaction, saved-comparison fixture, Guided-navigation, and Loss-pointer failures. Neural-network learning remains incomplete. Popular-stock coverage remains 10/10 local symbols and expansion requires an authorized source; genuine cross-symbol magnitude reading still needs comparable ordinary OOF summaries. No `final-test-*.json` or locked holdout observations were read or changed; no final test, market refresh, deployment, or publication occurred.

## Scheduled maintenance update (2026-10-25, four-dimensional clipping comparison)

- **Latest review and reproduced defect:** `artifacts/regression-monitor/latest-checks.json` at `2026-10-25T13:10:11+08:00` is FAIL. It reports a pytest failure. Running the monitor's safe pytest selection reproduced `test_gradient_clipping_lesson_has_observable_bounded_update`: its exact expected objects omitted the per-component clipping fields that the current 2D and N-dimensional calculators correctly return. This was a stale regression contract, not a newly discovered model or market-data defect.
- **Exact correction:** Updated the expected 2D and 4D result objects to include per-component clipped values and norms. Extended `calculateVectorGradientClippingN()` and its 4D renderer to show both global L2 norm scaling and per-component clamping. For `(1,2,2,4)` with limit `2`, norm clipping gives `(0.4,0.8,0.8,1.6)` with norm `2`; component clipping gives `(1,2,2,2)` with norm `sqrt(13) ≈ 3.6056`. Updated the learning guide and monitor's four-dimensional acceptance predicates.
- **Roadmap increment / acceptance:** Advanced the neural-network learning subtask from a 2D comparison to a four-parameter example that makes direction changes observable. Synthetic arithmetic only; no model-training or quality claim.
- **Verification and limits:** The focused clipping test passed (`1 passed, 55 deselected`); the safe `tests/test_system.py` selection passed (`53 passed, 3 deselected`). `node --check web/app.js`, Python AST parsing for the monitor and test file, and scoped `git diff --check` passed. No browser or visual desktop/390px acceptance was run. `latest-checks.json` remains unchanged pre-change review data.
- **Remaining / next checkpoint:** Trace the reported lesson-widget, saved-comparison, Guided-navigation, and Loss-pointer browser failures in a browser-only route that excludes training smoke and locked-test UI. Popular-stock coverage remains locally 10/10 and expansion needs an authorized source. Real cross-symbol magnitude interpretation still needs comparable ordinary OOF summaries. No holdout observations or `final-test-*.json` were read or changed; no final test, market refresh, deployment, or publication occurred.

## 2026-10-25: Latest AGY triage and clipping comparison

**Review evidence.** AGY at `2026-10-25T12:34:58+08:00` reports failures in lesson widgets, the saved-comparison fixture, guided navigation, and Loss pointer tooltip. Current source uses SVG bounding-box coordinate conversion; the monitor targets a point inside the plot. The tooltip failure is not independently reproduced from source alone, so no current application defect is claimed. The previous 11:25 diagnosis does not establish the cause of this newer result.

**Bounded change.** The 2D gradient-clipping exercise now places global L2 norm clipping and per-component clipping side by side. For `(3,4)` and limit `1`, the outputs are `(0.6,0.8)` with norm `1` and `(1,1)` with norm `1.4142`, respectively; the latter changes direction. Updated the learning guide with the same example.

**Acceptance and limits.** Current HTML defaults and renderer source expose the comparison, and manual arithmetic confirms both outputs. No test or browser flow was run per maintenance boundary; rendered desktop/mobile acceptance remains pending. This synthetic lesson does not establish training stability or model quality. No protected observations were accessed, and no market data was downloaded or refreshed.

**Next checkpoint.** Verify changed inputs and both rendered outputs at desktop and 390px in a safe browser-only flow. Trace the four reported failures with locators while excluding training smoke and locked-test UI. Popular-stock coverage remains local 10/10; expansion requires an authorized source. Real cross-symbol magnitude reading still depends on compatible ordinary OOF summaries.

## 2026-10-25: Responsive Loss pointer and negative momentum history

**Finding and fix.** AGY at 11:25:47 reports that the Loss pointer tooltip is missing although keyboard navigation works. The handler mixed screen-matrix SVG coordinates with fixed viewBox geometry. Pointer x is now converted from the SVG bounding rectangle in CSS pixels to the 660-unit viewBox. A regression contract checks this path and guards against the previous conversion.

**Roadmap increment.** The momentum lesson and guide now expose negative prior velocity: β=0.5 and vₜ₋₁=−0.5 contribute −0.25; with gₜ=1 the velocity is 0.75 and η=0.1 updates w=2 to 1.925. Focused pytest: 2 passed, 54 deselected; JS syntax, monitor AST and scoped diff checks passed. No browser or model-quality claim.

**Next checkpoint.** Verify pointer and keyboard tooltip at desktop/390px in a browser-only route excluding training and locked-test UI, then localize the remaining lesson, saved-summary and navigation failures. Popular-stock expansion needs an authorized source; cross-symbol magnitude comparison needs comparable ordinary OOF summaries.

## Scheduled maintenance update (2026-10-25, narrow comparison labels)

- **Latest review and reproduced defect:** `artifacts/regression-monitor/latest-checks.json` at `2026-10-25T10:16:23+08:00` is FAIL. The 390px chart check reports 0/8 rotated labels. Current `renderComparison()` emitted `.bar-label` only, so the monitor predicate required `.bar-label-rotated` without any renderer path capable of satisfying it. The chart also lacked the hinted narrow-screen short-label treatment.
- **Exact change:** `renderComparison()` now uses compact labels at SVG widths ≤420px, retains the full model name in each SVG `<title>`, and shows `#comparisonCompactHint`. Existing long names shorten to seven characters plus an ellipsis; short names stay intact. Desktop labels remain full.
- **Roadmap increment / observable acceptance:** Advanced the chart-readability subtask for model comparisons. A synthetic 390px renderer fixture verifies two labels carry the compact class, “Random Forest” displays as “Random…”, its full title is retained, and the compact hint is visible. This is interface readability evidence, not model-quality evidence.
- **Verification:** Focused pytest `2 passed, 53 deselected` (comparison renderer plus existing momentum monitor contract); `node --check web/app.js`, regression-monitor Python AST parsing, and scoped `git diff --check` passed. The full browser monitor was not run; no visual/browser acceptance is claimed. Other latest FAIL groups (interval/later lessons, saved-summary fixture, multi-mode navigation, Loss hover) remain unlocalized.
- **Remaining / next checkpoint:** Run a browser-only acceptance path excluding training smoke and locked-test UI; verify the 390px label treatment and trace those remaining failures. Popular-stock coverage is still local 10/10 and expansion needs an authorized source; real cross-symbol magnitude comparison needs comparable ordinary OOF summaries. Neural-network learning remains incomplete. No protected data access, final test, market refresh, deployment, or publication.

## 2026-10-25: Configured-epoch acceptance and momentum baseline

**Reproduced defect.** AGY at 09:40:28 reports the terminal animation group as FAIL. The monitor bundled output arrival with a hard-coded `025` epoch label, but the app formats the completed label from `buildConfig().epochs`; any other valid epoch setting could therefore create a false animation failure.

**Fix.** The monitor now reads the configured completion label and reports output-stage arrival separately from epoch-label matching. The 09:41:40 browser attempt could not proceed because sandbox local HTTP returned `Operation not permitted` and Chrome exited with `TargetClosedError`; the separated browser assertions remain unverified.

**Roadmap increment and evidence.** Lesson 20 now compares β=0, β=0.5, and selected β using fixed synthetic inputs. Defaults show velocity/weight values of 1.0000/1.9000, 1.2500/1.8750, and 1.4500/1.8550. Focused pytest: 1 passed, 52 deselected; safe suite: 122 passed, 1 deselected; JS syntax, Python AST, and scoped diff checks passed. This is math instruction, not model-quality evidence.

**Next checkpoint.** Verify animation output and epoch synchronization at a non-default setting in a browser; inspect the new lesson at desktop and 390px; trace the other 09:40 AGY failures. No protected holdout/final-test access, final test, data refresh, deployment, or publication.

## 2026-10-25: AGY lesson acceptance and interval readout

**Reproduced defect.** The latest review artifact (`2026-10-25T02:35:41+08:00`) reports interval/lesson and navigation failures. In current monitor code, Guided selection is invoked from `page.evaluate()` as a raw DOM click; this bypasses Playwright's visible user interaction path and leaves hidden-state acceptance vulnerable. Some fixtures also repeat a click on the current Guided tab before setting lesson index.

**Fix.** Monitor now resets only its page-local lesson state, performs a Playwright `#tabGuided` locator click, and renders the lesson. Direct lesson fixtures no longer issue redundant tab clicks. No saved comparison root cause is claimed: current fixture is assembled with `savedValidationSummary()` and matching metadata, but no post-change browser acceptance was run.

**Roadmap increment and evidence.** Lesson 11 displays interval total width in percentage points in addition to endpoints; +0.6% center with spreads 0.4/0.7 gives widths 0.80/1.40 pp. Focused tests: 3 passed, 44 deselected; safe suite: 71 passed; JS syntax, Python AST and diff checks passed. No browser desktop/390px evidence and no model-quality inference.

**Next checkpoint.** Add/run a browser-only path excluding training smoke and locked-test UI; verify navigation, interval readout and saved-summary compatibility at desktop and 390px. Popular-stock expansion still needs an authorized data source; real cross-symbol magnitude requires comparable ordinary OOF summaries.


## Scheduled maintenance update (2026-10-25, AGY review)

- **Reproduced defects:** Latest AGY `2026-10-25T00:45:57+08:00` reports lesson failures. The monitor selects Lab, then directly renders Guided-only exercises without switching back; these remain hidden. The saved-comparison compatible fixture supplies only partial protocol metadata, omitting required `model` and `period`, so current compatibility logic correctly rejects it.
- **Fix:** Monitor fixtures now select Guided before rendering. Compatible records are created by the actual `savedValidationSummary()` from two complete synthetic validation records with matching protocol, model, setup and date range. Incompatible examples remain checked.
- **Roadmap work:** Lesson 11 and learning guide compare interval width at fixed center: 0.8 pp versus 1.4 pp. Synthetic arithmetic only; no probability/coverage or model-quality claim.
- **Verification:** Focused pytest `7 passed, 39 deselected`; safe pytest `69 passed, 1 deselected`; `node --check web/app.js`, Python AST parse and `git diff --check` pass. The initial targeted run caught the obsolete fixture assertion; it was updated to the new real-summary contract. AGY JSON is unchanged pre-fix evidence; browser/desktop/390px verification remains pending.
- **Next checkpoint:** Browser-only acceptance for lesson navigation, interval interaction and saved summaries at desktop and 390px; exclude training smoke and locked-test UI. Popular-stock local coverage remains 10/10; expansion requires authorized data; genuine cross-symbol magnitude reading requires comparable ordinary OOF summaries. No protected data access, final test, refresh, deployment or publication.

## Scheduled maintenance update (2026-10-24, lesson monitor state and interval visualization)

- **Finding:** Latest AGY record `2026-10-24T23:32:40+08:00` is FAIL. I independently reproduced monitor-side hidden-state acceptance failures from current code: direct lesson checks select by `lessonIndex` while Lab is active, leaving Guided hidden; the next/back check also runs after selecting Lab. The saved-comparison fixture FAIL is not independently reproduced from the current predicate and remains open.
- **Exact change:** Monitor now switches back to Guided before checking/resolving lesson widgets and navigation, after resetting only its in-memory lesson state. Added a visible interval band with accessible lower/center/upper values; edits recalculate endpoints, and invalid values hide the diagram. The guide states this band represents width only, not probability density.
- **Verification:** Focused pytest `6 passed, 39 deselected`; `node --check web/app.js`, Python AST parsing of monitor/tests, and `git diff --check` passed. The old AGY JSON remains unchanged as pre-change evidence; no post-change browser or desktop/390px claim.
- **Next checkpoint:** Safe browser-only acceptance without training smoke or locked-test UI for Guided navigation, interval and cross-symbol saved-summary checks, desktop and 390px. Popular local stocks remain 10/10; real cross-symbol magnitude needs ordinary OOF outputs under one protocol. No holdout/final-test access, market refresh, final test, deployment, or publication.
## Scheduled maintenance update (2026-10-25, terminal animation acceptance sequence)

The latest AGY artifact (`2026-10-25T08:31:48+08:00`) reports that the training animation did not finish at the output. Source inspection reproduced an acceptance-sequence defect: the check calls `updateProgress(completed)` once, which stops the synthetic animation, then reads the status before the subsequent completed-state poll that preserves the output label. The routine monitor itself was not run.

The monitor now applies a second synthetic completed-state update before checking the terminal label. No live training or protected observations were involved. This is a monitor correction; it does not establish a training-animation browser pass.

Lesson 20 now displays the momentum contribution split: with β=0.9, previous velocity 0.5, and current gradient 1, the prior contribution is 0.4500, the current contribution is 1.0000, and their sum is 1.4500; the synthetic updated weight is 1.855. The learning guide and renderer acceptance test were updated. Focused pytest: `3 passed, 48 deselected`; safe suite: `116 passed, 1 deselected`; JS syntax, Python AST and scoped diff checks passed. No browser/390px or model-quality claim.

The other latest AGY failures (lesson interactions, saved-summary fixture, Guided navigation and loss hover) remain untriaged. Next checkpoint: create a browser-only acceptance path that cannot start training or open locked-test UI, collect exact failures, then inspect lesson 20 at desktop and 390px. Popular-stock coverage remains local 10/10; more symbols require an authorized source. Real cross-symbol magnitude comparison needs comparable ordinary OOF summaries.

## 排程維護更新（2026-10-24，啟用函數比較與 AGY fixture 覆核）

- **AGY 最高優先缺陷覆核：** `artifacts/regression-monitor/latest-checks.json` 22:18+08:00 為 FAIL，其中已保存摘要 fixture 回報 False。依要求對照目前程式，以相同的 next-close、horizon=1、simple、模型、期間與 `setupSignature` 執行 `savedComparisonCompatibility()`，得到「條件一致、可描述性並列」；monitor predicate 亦核對現行完整前綴。此項目前無法獨立重現，故未將 AGY 舊結果當作根因，也未作推測性修補。其餘 lesson FAIL 未以安全 browser-only 路徑重現，仍待定位。原始 AGY JSON 保留。
- **路線圖功能增量：** 第 21 步啟用函數互動新增 Tanh，與 Sigmoid、ReLU 共用可調 z，並即時顯示三者輸出及局部導數；學習指南同步補上公式、正負輸入算例及合成資料限制。這是神經網路數學教學增量，不代表模型品質或哪種架構較佳。
- **可觀察驗收與證據：** 實際 JavaScript 函式在 z=2 得 Tanh=0.96402758、導數=0.07065082；z=−2 得 Tanh=−0.96402758、導數=0.07065082；z=0、空值及非有限輸入亦已核對。契約 pytest `2 passed, 40 deselected`；`node --check web/app.js`、monitor/test Python AST、`git diff --check` 通過。首輪契約測試因指南未用 monitor 所要求的導數識別名稱而失敗；補上精確公式名稱後重跑通過，沒有放寬檢查。未執行 browser monitor，沒有桌面／390px 畫面驗收主張。
- **剩餘／下一 checkpoint：** 用不觸發訓練、不開啟鎖定測試 UI 的 browser-only 流程重查區間互動、跨標的摘要與導學導航，記錄 selector／traceback，並驗收 Tanh lesson 桌面及 390px。熱門股仍維持既有本機 10/10；新增標的需授權資料來源，真實跨標的幅度比較仍需同協定的一般 OOF 摘要。未讀寫或消耗 `final-test-*.json`／locked holdout，未跑一次性 final test、刷新行情、部署或發布；不作模型品質主張。

## 排程維護更新（2026-10-24，跨標的相容 fixture 與條件清單）

- **AGY 起始結果／最高優先缺陷：** `artifacts/regression-monitor/latest-checks.json` 21:42:31+08:00 為 FAIL。獨立重現跨標的摘要 monitor fixture 缺陷：相容案例只補 `execution: next_close`，沒有提供必要的 horizon、returnType、setupSignature；`savedComparisonCompatibility()` 因其他相容條件缺失正確拒絕，monitor 卻把它當成相容預期，因此「已保存摘要 fixture=False」是測試資料契約錯誤。
- **精確修正：** fixture 為兩筆摘要補上相同的 horizon=1、simple 報酬及訓練設定簽章；保留舊協定案例的拒絕檢查。AGY JSON 保留原狀作為改前證據。
- **路線圖進展：** 跨標的已保存摘要新增六項可比條件清單，逐項顯示目標協定、期間、報酬定義、模型、訓練設定及驗證日期是否一致，並標示僅供分別閱讀或可描述性並列。同步學習指南及 CSS。這是比較方法教學，不是跨股模型品質結論。
- **可觀察接受條件：** 聚焦測試核對相容案例全一致、不相容訓練簽章、缺少 next-close 協定；實際 JavaScript checklist 預期正確指出「訓練設定缺少或不同」及「目標協定缺少或不同」，並區分描述性並列與不可直接排名。改後聚焦 pytest `2 passed, 40 deselected`；直接執行實際 JavaScript checklist，核對相容案例列出六項一致並提示描述性並列、不相容訓練簽章提示不可直接排名、缺少協定提示目標協定不一致。`node --check web/app.js`、monitor/test Python AST parse、`git diff --check` 通過。未重跑完整 browser monitor，故無改後瀏覽器或桌面／390px 通過主張。
- **剩餘／下一 checkpoint：** 對最新三項 AGY lesson FAIL 建立安全 browser-only 定位流程，重查區間互動、跨標的摘要及導學導航，並在桌面／390px 驗收新清單。熱門股仍以已報告本機 10/10 為基準；新增覆蓋需授權來源，真實跨標的比較待相同協定的一般 OOF 摘要。未讀寫或消耗 `final-test-*.json`／locked holdout，未跑一次性 final test、刷新行情、部署或發布；不作模型品質主張。

## 排程維護更新（2026-10-24，摘要接受條件與啟用函數導學）

- **AGY 起始結果／最高優先缺陷：** `artifacts/regression-monitor/latest-checks.json` 20:30:02+08:00 為 FAIL。跨標的檢查的合成摘要 fixture 將合法相容結果字串與過時的 `compatibleGuard.startsWith('目標協定、模型、預測期間')` 比對；現行 `savedComparisonCompatibility()` 回傳的實際連續前綴是「目標協定、模型、訓練設定、預測期間」。這可由函式字面值和監測 predicate 獨立重現，造成健康摘要被判失敗。另有互動導學檢查失敗；尚未證明它們是產品缺陷，保留待瀏覽器定位。
- **精確修正：** monitor predicate 更新為核對現行完整前綴；lesson catalog 及導學進度接受條件同步更新到新增的 21 步。
- **路線圖增量：** 導學新增第 21 步「Sigmoid 與 ReLU」，可調合成輸入 z，並列輸出與局部導數。z=2 時 Sigmoid 約 0.8808、ReLU=2、導數約 0.1050／1；z=−2 時 Sigmoid 約 0.1192、ReLU=0、導數約 0.1050／0；空值及非有限值顯示提示。指南註明這是局部算術教學，不是市場模型比較。
- **接受證據：** 聚焦 pytest `5 passed, 35 deselected`；抽取實際 JS 計算函式，以 Node 核對正負 z、空值與無限值；`node --check web/app.js`、monitor/test Python AST、`git diff --check` 通過。未重跑完整 browser monitor，無改後 browser 或桌面／390px 通過主張；最新 AGY 是改前證據。
- **剩餘／下一 checkpoint：** 建立不觸發訓練 smoke 的 browser-only 檢查，實際驗收跨標的 fixture、21/21 課程及新互動桌面／390px，並取得目前 AGY 其他兩項 lesson FAIL 的 selector／具體原因。熱門股仍維持本機既有 10/10；真實跨標的比較仍待同協定一般 OOF 摘要。未讀寫或消耗 locked holdout／`final-test-*.json`，未執行一次性 final test、刷新行情、部署或發布；不作模型品質主張。

## Scheduled maintenance update (2026-10-24, lesson-check isolation and magnitude calibration)

- **Latest AGY / independently reproduced defect:** `artifacts/regression-monitor/latest-checks.json` at 19:53:50+08:00 reports FAIL. The interval acceptance predicate still expected `第 11 / 15 步` while current `LESSONS` has 20 steps. Separately, the browser session began the lesson sequence at saved step 8; because the monitor assumed a fresh step 1, its later lesson widgets remained hidden. Both follow from current predicate and page-state setup; the recorded FAILs were not treated as evidence of broken lesson calculators.
- **Exact fix:** `scripts/regression_monitor.py` now disables lesson-progress saving for the monitor page, resets only its in-memory lesson index/tab before navigation, and expects 11 / 20 in the interval predicate. The user's stored progress is not rewritten by monitor navigation.
- **Visible roadmap increment:** Cross-symbol learning now shows synthetic actual-versus-predicted average upward magnitude and absolute gap: group A 0.60 vs 0.80 pp (0.20 gap), group B 1.00 vs 1.40 pp (0.40 gap). It states group B is more overpredicted in this example and still requires OOF errors/baselines for any real comparison. Guide and browser acceptance contract updated. No market data or quality claim.
- **Evidence:** Focused pytest `3 passed, 35 deselected`; `node --check web/app.js`; Python AST parse for monitor/tests; `git diff --check` all passed. No browser monitor rerun, so latest AGY remains pre-change evidence and desktop/390px browser acceptance is pending.
- **Next checkpoint:** Run safe browser-only acceptance for the reset lesson flow and cross-symbol magnitude example; inspect desktop and 390px. Popular-stock coverage remains the existing local 10/10. More symbols need authorized data; real cross-symbol magnitude teaching needs comparable ordinary OOF outputs. No holdout or `final-test-*.json` access, one-time final test, data refresh, deployment, or publication.

## 排程維護更新（2026-10-24，AGY 隱藏狀態修正與矩陣圖示）

- **最高優先缺陷與獨立重現：** 起始 `artifacts/regression-monitor/latest-checks.json` 為 `2026-10-24T18:43:20+08:00`、overall FAIL。矩陣小測位於折疊的 `#math` `<details>` 中，monitor 未展開它便點擊 `#tabLab`，Playwright 因祖先不可見而逾時；DOM 結構可直接重現。MLP 維度檢查則受使用者保存的 `state.forwardTrace` 影響：`renderNetworkStage()` 只有無 trace 才顯示架構示例，故未隔離 trace 時接受條件不穩定。
- **精確修正：** monitor 在點選 `#tabLab` 前展開 `#math > summary`；檢查 MLP 架構預覽前將頁面內 `state.forwardTrace` 設為 `null`，只改當次測試記憶體狀態，不保存或改寫任何使用者資料。
- **推進的可見學習里程碑：** 矩陣格圖新增可見「列：神經元」和「欄：輸入」軸標籤；完整維度文字及 6×6 截圖上限仍明確保留。指南同步說明。這是神經網路權重形狀教學增量，不是模型訓練或品質證據。
- **改後驗證：** 聚焦契約測試 `2 passed, 33 deselected`；`node --check web/app.js`、monitor/test Python AST 及 `git diff --check` 通過。未重跑完整 browser monitor，故起始 FAIL 不視為已由瀏覽器清除。
- **剩餘／下一 checkpoint：** 安全 browser-only 驗收折疊面板展開、MLP 無 trace 矩陣例子及維度小測錯答／正答，並檢視桌面／390px。熱門股沿用本機 10/10 基準；跨標的漲跌幅讀圖仍待相同協定的一般 OOF 結果。未讀寫或消耗 `final-test-*.json`／locked holdout，未執行一次性 final test、刷新行情、部署或發布；不作模型品質主張。

## 排程維護更新（2026-10-24，AGY 隱藏狀態修正與矩陣圖示）

- **最高優先缺陷與獨立重現：** 起始 `artifacts/regression-monitor/latest-checks.json` 為 `2026-10-24T18:07:29+08:00`、overall FAIL。前向動畫的 MLP 維度條件在 monitor 先還原原模型後才檢查；原模型若為 GRU 等非 MLP，`renderNetworkStage()` 不會顯示 MLP 專屬維度例子，故條件必為 False。另一個瀏覽器 FAIL 的 traceback 顯示它點選 `tensorShapeAnswer` 時該 label 不可見；目前學習中心預設 Guided，選項位於隱藏的 Lab 面板。兩者均由現行檢查順序與 UI tab 狀態重現，沒有把瀏覽器錯誤歸咎於產品動畫。
- **精確修正：** `scripts/regression_monitor.py` 在維度檢查前明確選 MLP，檢查後再還原原模型；點選矩陣小測前先開啟 `#tabLab`。原 AGY JSON 保留作為改前證據。
- **推進的可見學習里程碑：** `renderTensorShapeExercise()` 現以小格圖表示權重矩陣的列與欄，提供 `role=img` 的列／欄說明；最大只畫 6×6 格，完整維度仍用文字呈現，並明示截顯提示。指南同步說明。這是神經網路矩陣形狀的可見學習增量，不是模型訓練或品質證據。
- **改後接受證據：** 聚焦 pytest `3 passed, 32 deselected`，涵蓋原有題目回饋、3×2／4×5 格圖、超過 6 格的截顯提示、無效維度拒絕，以及 monitor 先切 MLP／Lab 的順序；`node --check web/app.js`、monitor/test Python AST、`git diff --check` 通過。未執行完整 browser monitor（含訓練 smoke），因此沒有改後瀏覽器或桌面／390px 通過主張；起始 JSON 仍是改前 FAIL。
- **剩餘／下一 checkpoint：** 安全 browser-only 驗收 MLP inspector、Lab 小測錯答／正答及桌面／390px 矩陣圖示，再刷新監測結果。熱門股維持既有本機 10/10；擴充需要授權來源。跨標的漲跌方向／幅度仍待相同協定的一般 OOF 結果。未讀寫或消耗 `final-test-*.json`／locked holdout，未執行一次性 final test、刷新行情、部署或發布；無模型品質主張。

## 排程維護更新（2026-10-24，AGY 失敗覆核與矩陣維度小測）

- **最高優先缺陷及獨立重現：** 起始 `artifacts/regression-monitor/latest-checks.json` 時間 16:55:36+08:00，overall FAIL。動畫與模型控制兩項的 MLP 維度子檢查仍搜尋過時文案 `W 為 2×3`／`W a 的結果為 2 維`；目前 renderer 實際呈現 `a∈ℝ³`、`W∈ℝ²ˣ³`、`Wa∈ℝ²`、`結果為 2 維`，故 acceptance 在真實頁面內容上必然為 False。導學另外有舊的 17/19 步總數檢查，與現行 20 步目錄矛盾。未將其他 FAIL 擅自歸因為產品缺陷。
- **精確修改：** 統一 monitor 的維度檢查為現行 renderer 文案；將仍殘留的 17/19 步瀏覽器預期改為 20 步，並保留個別步驟索引及算例檢查。原 `latest-checks.json` 保留為改前證據。
- **推進的學習里程碑：** 架構維度練習新增選擇題：3 維輸入、2 個神經元應配 2×3 權重矩陣。錯答提示按「列代表神經元、欄對應輸入」引導重想；答對說明矩陣相乘後得到 2 維輸出。這是可操作的概念檢查，非模型品質證據。
- **改後驗證：** `node --check web/app.js`、monitor/test Python AST、`tests/test_system.py` 聚焦驗收（2 passed，32 deselected）及 `git diff --check` 通過。monitor 內已加入 browser wrong/right feedback 接受條件；本輪未執行 browser monitor（其流程會觸發訓練 smoke），所以不宣稱改後瀏覽器或視覺通過。
- **剩餘／下一 checkpoint：** 安全 browser-only 驗收 MLP inspector、20 步導學及此選擇題，再檢視桌面／390px。熱門股已有本機 10/10 覆蓋；擴充需授權資料。跨標的漲跌幅讀圖仍待相同協定的一般 OOF 結果。本輪未讀寫或消耗 `final-test-*.json`／locked holdout，未跑一次性 final test、刷新行情、部署或發布，無模型品質主張。

## 排程維護更新（2026-10-24，AGY browser predicate 修正與 MLP 維度教學接受條件）

- **改前審查與最高優先缺陷：** `artifacts/regression-monitor/latest-checks.json` 時間 15:06:40+08:00，overall FAIL。瀏覽器檢查 traceback 指向 `scripts/regression_monitor.py` 的 `lesson_catalog_ok`：`page.evaluate()` 傳入的超長 JavaScript 字串有括號錯誤，Playwright 回報 `SyntaxError: Unexpected token ')'`，可由改前 expression 獨立重現；因此課程 catalog 與後續瀏覽器接受條件無法完成。另兩個 MLP 檢查回報維度文案為 False：一處要求 `結果為 2 維`，但實際 UI 文案是 `W a 的結果為 2 維`，字串差異可由目前 renderer 與接受條件確認。沒有依錯誤摘要推定產品動畫故障。
- **精確修改：** 將 catalog 接受式拆成具名的 `momentum`、`batch`、`gradient`、`forward`、`multi`、`interval` 等中間值，保留原課程、算例、輸入拒絕及元件條件；把 MLP 維度檢查改為逐字核對目前可見的 `W 為 2×3` 和 `W a 的結果為 2 維`。同步更新契約測試，使其核對具名批次梯度計算與更新容差。
- **推進的學習里程碑：** MLP 未訓練隱藏層的可見例子現在有一致的 browser 接受條件：3 維輸入 × 2×3 權重矩陣得到 2 維輸出。這讓既有架構教學子任務可由 monitor 明確驗收；不代表整體神經網路學習目標完成，也不代表模型品質。
- **改後證據：** 改後 catalog predicate 由 Python AST 擷取並交給 Node `new Function` 編譯，語法 PASS；20 步條件仍在。`node --check web/app.js`、monitor/test Python AST、聚焦 pytest `2 passed, 31 deselected`、`git diff --check` 通過。完整 browser monitor 未執行，因其包含隔離訓練 smoke；因此沒有改後瀏覽器或桌面／390px 視覺 PASS 主張。`latest-checks.json` 保留為改前證據。
- **剩餘／下一 checkpoint：** 在 browser-only、無訓練路徑驗收 MLP 維度文字、RNN/LSTM/GRU 階段切換及桌面／390px；再執行安全 monitor 前先確認不會接觸鎖定 UI。熱門股目前僅有既有本機 10/10 證據，新增覆蓋需授權來源；跨標的漲跌方向／幅度仍待一致協定的一般 OOF 輸出。本輪未讀寫或消耗 `final-test-*.json`／locked holdout，未跑一次性 final test、未刷新行情、未訓練或部署發布，沒有模型品質主張。

## 排程維護更新（2026-10-24，網路階段 inspector 缺陷與矩陣維度教學）

- **最新 AGY 結果／最高優先缺陷：** `artifacts/regression-monitor/latest-checks.json` 時間 14:32:21+08:00，overall FAIL；唯一 FAIL 的 traceback 是 `renderNetworkStage()` 讀取未定義的 `kind`，由 monitor 呼叫 `activateNetworkStage(1, false)` 可直接重現 `ReferenceError`。其他列出檢查通過，包含熱門股本機覆蓋 10/10 及鎖定資料隔離。
- **精確修正：** `web/app.js` 的 `renderNetworkStage()` 改用 `currentModel() === 'mlp'` 判斷模型，不再依賴另一函式區域變數 `kind`。沒有改寫 AGY JSON，保留為改前證據。
- **推進的可見學習里程碑：** 修復後，MLP 隱藏層 inspector 可顯示原已設計但此前無法到達的矩陣維度例子：輸入 3 維、2 個神經元時 W 為 2×3，輸出為 2 維。Browser monitor 現明確核對矩陣維度教學文字；課程指南已記載此教學。這是架構維度學習小步，不是訓練或模型品質證據。
- **改後驗收：** `node --check web/app.js`、monitor/test Python AST、`tests/test_system.py::test_mult_input_neuron_lesson_contract`（1 passed）、`git diff --check` 通過。該契約也核對 monitor 的矩陣教學接受條件。完整 browser monitor 未執行（包含訓練 smoke），所以沒有改後視覺／瀏覽器通過主張；不以 smoke 推論品質。
- **剩餘／下一 checkpoint：** 在安全 browser-only 環境執行前向傳播 inspector 驗收，確認 MLP 可見 2×3 維度說明及 RNN/LSTM/GRU 階段切換無 JS error，再看桌面與 390px。熱門股仍是檢查記錄中的本機 10/10；新增覆蓋需授權資料來源。跨標的漲跌方向／幅度仍需同協定的一般 OOF 輸出。未讀寫或消耗 holdout／`final-test-*.json`，未執行一次性 final test、刷新行情、部署或發布，無模型品質主張。

## 排程維護更新（2026-10-24，重播等待修正與動量教學）

- **AGY 最高優先缺陷與獨立重現：** 起始 `latest-checks.json` 13:23:48+08:00 為 overall FAIL（17 項 PASS、1 項 FAIL）；唯一 FAIL 的 traceback 指向 `scripts/regression_monitor.py:450`。檢查流程先按重播，產品會重設到輸入層並停住，隨後 monitor 卻等待動畫步驟離開 0，期間沒有按播放；因此等待必定逾時。這是 monitor 接受流程缺陷，不是動畫產品故障。
- **精確修正：** 在該次重播後增加 `#playNetwork` click，再等待步驟前進和 pause 啟用。保留 `latest-checks.json` 為改前證據，未跑完整 monitor，故尚無改後 browser 通過主張。
- **路線圖進展：** 學習導覽由 19 增為 20 步，新增動量最佳化公式及手算例：β=0.9、v 前值 0.5、g=1、η=0.1，得 v=1.45、權重變化 −0.145。同步首頁步數、學習指南、monitor 的課程接受條件與契約測試。此為合成數學教學，不是模型品質證據，神經網路學習目標仍未完成。
- **驗證證據：** `node --check web/app.js` 通過；monitor 與測試 Python AST 通過；聚焦 pytest `2 passed, 31 deselected` 通過；`git diff --check` 通過。首輪聚焦檢查因既有測試仍要求 19 步而失敗，更新契約後重跑通過，未弱化檢查。沒有改後桌面／390px 視覺驗收。
- **剩餘／下一 checkpoint：** 在可用瀏覽器執行 monitor，確認重播後播放等待、20 步課程及桌面／390px。熱門股本機覆蓋沿用 10/10；擴充需授權來源。跨標的漲跌方向／幅度仍需一致協定的一般 OOF 結果。未讀寫或消耗 locked holdout／`final-test-*.json`，未跑一次性 final test、刷新行情、部署或發布；無模型品質主張。

## 2026-10-24 12:13：AGY 截圖逾時覆核與小批次互動

- **覆核結果：** 最新 AGY（12:13:56+08:00）因 Playwright 實際截圖 2500ms timeout 為 FAIL。檢查目前 `scripts/regression_monitor.py`，browser 例外已回報 FAIL，overall 聚合也保留 FAIL；可見結果未獨立重現程式缺陷。因此不把此環境／瀏覽器逾時記成程式修補，原 JSON 不變。下一次應取得 Playwright locator／stack 以定位 timeout。
- **可見功能變更：** 導學第 19 步新增兩筆梯度可調互動，先取平均後只更新一次權重。合成預設 `w=2`、`g₁=−2`、`g₂=4`、`η=0.1` 得平均梯度 1、更新後權重 1.9；不代表實際訓練或模型品質。
- **驗證：** JS syntax、Python AST、有效與無效輸入算例及聚焦 pytest `2 passed, 31 deselected` 通過，`git diff --check` 通過。未做改後 browser/桌面/390px 驗收。
- **下一步：** 可用本機服務及 Chrome 時驗收第 19 步與桌面／390px，收集 timeout locator／stack。熱門股仍沿用本機 10/10；新增覆蓋需授權資料來源。跨標的方向／幅度需一致協定的一般 OOF 輸出。

## 歷史紀錄：2026-10-24 瀏覽器驗收失敗被降級為警告

- **歷史狀態：** 早期版本的 `browser_check()` 曾將 Playwright 例外回報 WARN；12:13 覆核時現行版本已回報 FAIL，且 overall 聚合保留 FAIL。
- **修正：** browser 實際截圖／互動流程例外改回報 FAIL。未執行到 browser 驗收時不再能通過整體狀態。
- **學習增量：** 新增第 18 步雙輸入神經元的一次 SGD 互動，顯示參數更新及損失變化；純合成算例。其 browser 條件檢查預設與更改學習率及超界輸入。
- **驗證：** `node --check`、monitor／test AST、隔離實際 JS 算例（loss 0.04 → 約 0.0016，更新權重／偏置，拒絕 η=2）、聚焦 pytest 2 passed／31 deselected、安全 pytest 56 passed／1 deselected、`git diff --check` 通過。第一次 harness 的精確浮點比較失敗，改容差驗算後通過。完整 browser monitor 未跑，沒有改後畫面證據。
- **下一步：** 在 Chrome／本機服務可用環境做第 18 步與桌面／390px browser 驗收；最新改前 JSON不代表修正後通過。


## Scheduled maintenance update (2026-10-24, multi-input neuron backpropagation)

- **AGY review / defect decision:** `latest-checks.json` at 10:29:58+08:00 reports 17 PASS and 1 WARN. The warning is a Playwright 2500ms timeout without selector or traceback. The earlier `.price-path` wait was corrected from the nonexistent `d` attribute to nonempty `points`; the current summary cannot independently identify this warning's cause, so no speculative fix was made.
- **Bounded roadmap progress:** Lesson 17 now accepts a target y for its two-input ReLU neuron and displays single-example squared loss, backpropagated delta, and gradients for both weights and bias. The guide and browser monitor acceptance condition were updated. Negative z demonstrates ReLU's zero local derivative. This is synthetic math instruction, not model-quality evidence.
- **Verification:** `node --check web/app.js`, monitor AST parsing, five executions of the actual JS calculation (default gradients -0.8/-0.4/-0.4; target zero gradients 3.2/1.6/1.6; negative-z zero gradients; blank and overflow rejected), safe pytest `55 passed, 1 deselected`, and `git diff --check` passed. The full monitor/browser was not run; there is no post-change visual evidence.
- **Next checkpoint / limits:** Use a safe browser environment to verify lesson 17 and desktop/390px layout and capture the warning's locator/stack. Cross-symbol rise/fall magnitude reading still needs general OOF outputs under a consistent protocol; popular-stock expansion requires an authorized source. No locked holdout or `final-test-*.json` was read, written, or consumed; no one-time final test, market refresh, deployment, or publication occurred.

## 排程維護更新（2026-10-24，第 15 步課程契約補齊）

- **可重現缺陷：** 改前 AGY JSON 08:42:17+08:00 為 1 WARN／其餘 PASS；browser WARN 是無定位資訊的 8000ms timeout，不能確認其根因。另由現行程式清點 `LESSONS` 得 14 項，然而 `web/index.html` 初始進度及 `scripts/regression_monitor.py` 要求 15 步，課程目錄、進度比例及最後一步重啟契約不一致。
- **精確變更：** 新增第 15 步「方向與幅度誤差」互動，呈現方向一致性與絕對誤差百分點；空白／非有限值拒絕，零值獨立作持平。monitor 驗收步驟 15、兩種方向案例、算例與空值分支。指南新增同一算式與限制。
- **改後證據：** `node --check web/app.js`、monitor AST、15 項課程清點、5 個隔離案例、安全 pytest 54 passed／1 deselected、`git diff --check` 通過。未執行完整 browser monitor，改前 JSON 不代表改後瀏覽器通過；不主張模型品質。
- **下一 checkpoint：** 在可用 browser 環境核對最後步互動、重新開始及桌面／390px，並追查 timeout 的 selector／stack。未讀寫或消耗 locked holdout／`final-test-*.json`，未執行一次性 final test、行情刷新、部署或發布。

## 最新 AGY 維護覆核（2026-10-24 07:31:35+08:00；ReLU 梯度互動）

## 排程維護更新（2026-10-24；15 步接受條件與可調 ReLU 目標）

- **改前結果／獨立重現：** AGY `latest-checks.json` 08:06:17+08:00 overall WARN，唯一摘要 WARN 是 Playwright `wait_for_function` 8000ms timeout；JSON 未含 locator／stack。現行 monitor 課程 catalog/progress 條件仍要求 13 步，但 `LESSONS` 有 15 步，因此可獨立重現該接受條件必為 false；不能據此認定為 8 秒 timeout 的根因。
- **精確修正與里程碑：** `scripts/regression_monitor.py` 改為核對 15 步並檢查 ReLU 目標欄位。第 14 步新增可調合成目標 y，呈現 `L=(ŷ−y)²` 與 `dL/dz=2(ŷ−y)ReLU′(z)`；指南同步。推進神經網路梯度學習一小步，不宣告大里程碑完成或模型品質。
- **改後證據：** `node --check web/app.js`、monitor AST、隔離 7 組算式與邊界、pytest 54 passed／1 deselected、`git diff --check` 通過。browser-only 未能執行：本機 8000 bind 回報 `Operation not permitted`，Playwright Chromium binary 缺失，指定 Chrome launch `TargetClosedError`。未執行完整 monitor。
- **剩餘／下一 checkpoint：** 在瀏覽器可用環境實驗 y=1/3、z 正／負、桌面／390px，並取得 8 秒等待的 selector／stack。未讀寫或消耗 locked holdout／`final-test-*.json`，未跑 final test、更新行情、部署或發布。

## 改前 AGY 維護覆核（2026-10-24 07:31:35+08:00；ReLU 梯度互動）

- **最高優先缺陷覆核：** AGY overall WARN，只有瀏覽器實際截圖檢查在 Playwright `wait_for_function` 8000ms timeout。其它檢查包含資料狀態、熱門股覆蓋 10/10、切片、walk-forward 邊界、訓練契約、pytest 54 passed／1 deselected、鎖定隔離均為 PASS。JSON 未提供 locator 或 traceback；不能從該摘要獨立重現確切程式缺陷，故不臆測修改。完整 monitor 未重跑。
- **精確功能增量：** 導學新增第 14 步互動，總數 15。調整合成 z 即時顯示 ReLU 輸出及目標 1、平方損失下梯度；空值／非有限輸入顯示提示。同步首頁、指南和 browser 接受條件，沒有模型品質主張。
- **驗收／限制：** `node --check web/app.js`、monitor Python AST、隔離算例（z=2 → 2/2；z=−2 → 0/0；空值／溢位拒絕）及 `git diff --check` 通過。改前 07:31 JSON 不作改後畫面證據。未讀寫或消耗 locked holdout／`final-test-*.json`，未跑 final test、更新行情、部署發布。
- **下一 checkpoint：** 安全 browser-only 驗收新步的正／負輸入及桌面／390px，並取得具體信息定位 8 秒等待 timeout。跨標的 OOF 讀圖仍待同協定的一般驗證輸出；熱門股仍以本機 10/10 為既有覆蓋證據。

## 最新 AGY 維護覆核（2026-10-24 05:43:34+08:00）

- **最新報告項目：** overall WARN；唯一 WARN 為 Playwright browser `wait_for_function` 1500ms timeout。當前 monitor 在套用實驗歷程後等待進階設定 `<details>` 開啟；產品 handler 透過 `setTimeout(..., 0)` 延後開啟並還原 draft 設定，monitor 等待條件已補成兩者都成立。
- **獨立重現的最高優先缺陷：** 同一 browser path 的 `lesson_ok` 在 `interval_ui_ok` 指派前引用該區域變數，條件成立時會造成 `UnboundLocalError`。已移除提前引用；區間交互仍在稍後的 `conversion_ok` 驗收。
- **精確修正：** `scripts/regression_monitor.py` 移除 `lesson_ok` 中尚未賦值的名稱，並改為同時等待進階設定已開啟且 `#modelType` 已還原到保存模型，timeout 調為 5000ms。接受條件更直接檢查歷程套用後的兩個可見結果。
- **改後驗證／限制：** `node --check web/app.js`、Python AST、monitor 變數順序檢查、lesson contract 與算式斷言、`git diff --check` 通過。完整 browser monitor 未執行，故本輪 WARN 尚未以新 browser 結果結案；保留 05:43 改前 JSON。lesson 12 的手算為梯度 −8、更新權重 1.8、損失 4→0.16，僅合成教學。
- **下一 checkpoint：** 以不觸發 final-test UI 的 browser-only 檢查驗收歷程恢復、鏈鎖律導學及桌面／390px 顯示。熱門股本機覆蓋沿用 10/10；真實跨標的 OOF 教學需一致協定的一般驗證資料。未讀寫 locked holdout 或 `final-test-*.json`，未執行 final test、行情刷新、部署或發布。

# AGY 維護更新（2026-10-24，前向動畫重播缺陷）

- **改前檢查：** `artifacts/regression-monitor/latest-checks.json` 03:54:21+08:00：動畫重播回輸入 FAIL，模型選擇／TCN 因果式 FAIL，Playwright 截圖 WARN（頁面 evaluate SyntaxError）；pytest 53 passed／1 deselected，鎖定資料隔離 PASS。
- **最高優先缺陷重現與修正：** 現行 `#replayNetwork` handler 呼叫 `resetNetworkMotion(); playNetworkMotion()`。播放函式同步呼叫 advance，立即把輸入 step 0 推到 step 1，故 monitor 的重播檢查失敗。改為 reset 後 `activateNetworkStage(0, false)`，停留於輸入層，按鈕標示「從輸入播放」。TCN 驗收條件也由錯誤搜尋英文小寫 `causal` 改為檢查 UI 實際提供的「因果卷積」及只讀最後時間位置。
- **路線圖增量：** 在未訓練 MLP 隱藏層增加 3 維輸入、2 個神經元、`W` 形狀 2×3、輸出 2 維的可見示例，補足矩陣乘法維度學習；指南與 monitor 接受條件同步。只提供合成形狀，不代表模型品質。
- **驗證：** `node --check web/app.js`、monitor AST、重播／TCN／維度五項接受斷言、`python3 -m pytest -q -k 'not public_api_and_async_validation_job'`（53 passed／1 deselected）、`git diff --check` PASS。未跑完整 browser monitor；03:54 JSON 是改前結果，Playwright 截圖語法 WARN 仍未重驗。
- **下一 checkpoint：** 先讓 monitor 不操作 final-test UI，再安全重驗重播、維度示例和桌面／390px。未讀寫或消耗 `final-test-*.json`／locked holdout，未跑一次性 final test、未更新行情、未部署發布。

## 排程維護進度（2026-10-24，監測器回呼修正與特徵一致比較）

- **最新 AGY 結果與最高優先缺陷：** 起始 `latest-checks.json` 為 03:18:54+08:00，程式回歸 53 passed／1 deselected，切片、比較契約、桌面互動及鎖定隔離 PASS；browser WARN 的具體錯誤是 Playwright `wait_for_function` 使用 `arguments[0]`，該 predicate 中 `arguments` 未定義。獨立核對現行同一行確認缺陷可重現。
- **精確修改：** `scripts/regression_monitor.py` 改用已支援的 predicate 參數 `step`，排除未定義 `arguments`。跨標的比較狀態現在明示訓練設定包含輸入特徵與回看日數；`web/app.js` 原有設定簽章已將這些項目納入相容判定。指南、聚焦 pytest 與 browser fixture 同步覆蓋特徵設定不一致。
- **可觀察里程碑與證據：** 推進預測幅度／神經網路學習的公平跨標的摘要讀法，對不可比設定給出具體解釋；未宣稱真實跨股 OOF 結果或模型品質。`node --check web/app.js`、monitor AST、比較相容測試 1 passed、安全 pytest 53 passed／1 deselected、`git diff --check` 通過。改後 monitor 03:21:11：切片、訓練契約、pytest 與鎖定隔離 PASS；predicate 已越過原故障位置，但首頁 HTTP 因 sandbox `Operation not permitted` FAIL，Chrome 因同環境限制 TargetClosed WARN，故 browser 視覺未驗收。隔離訓練 smoke 只驗流程，不作品質證據。
- **剩餘／下一 checkpoint：** 在允許本機 HTTP 與 Playwright 的安全環境重跑 monitor，確認自動播放後暫停再繼續的步驟推進，以及跨股相容提示桌面／390px 呈現。真實跨標的讀圖仍需相同 next-close、模型、設定、期間、報酬定義和日期範圍的一般 OOF 結果；熱門股既有本機清單 10/10，擴充需授權來源。本輪未讀寫／消耗 `final-test-*.json` 或 locked holdout，未跑一次性 final test、未刷新行情、未部署發布。

## 最新維護覆核（2026-10-24，跨標的摘要協定警示）

- **AGY 覆核：** `artifacts/regression-monitor/latest-checks.json` 為 02:08:39+08:00。FAIL 是本機 8000 Connection refused，browser 因同一不可達服務為 WARN；樣本切片、模型比較契約、pytest 52 passed／1 deselected、鎖定隔離 PASS。服務狀態不是可重現的程式缺陷。
- **獨立重現：** 兩份本機一般驗證摘要的 `result` 均無 `execution` 欄位，雖然現行目標合約已是 `next_close`；`savedValidationSummary()` 仍輸出 MAE／基準差並放入跨標的面板。這些舊資料的執行協定未知，不應暗示可直接排名。
- **確切修改：** `web/app.js` 回傳摘要的 execution、horizon、returnType 與訓練設定簽章，新增比較相容性判定並在面板顯示狀態。必須兩筆都使用 next-close，且模型、訓練設定、預測期間、報酬定義、驗證日期區間相同，才標示可作描述性並列；否則顯示不可直接排名和重跑一般驗證的說明。單檔各自的 OOF 與基準仍可閱讀。`web/styles.css` 增加狀態區塊；學習指南和 monitor 同步。
- **驗收證據：** `node --check web/app.js`、monitor AST、`python3 -m pytest -q tests/test_saved_comparison_compatibility.py`（1 passed）通過，覆蓋舊協定、同協定和 horizon 不同案例。完整 monitor／browser 未執行；02:08 JSON 是改前結果，不當作改後驗收。
- **剩餘／下一 checkpoint：** 以不載入 holdout 輸出的安全瀏覽器檢查狀態訊息與桌面／390px 排版。真實跨標的 OOF 讀圖仍需相同 next-close、模型及訓練設定、horizon、報酬定義、日期範圍的一般 walk-forward 結果。熱門股仍為既有本機 10/10，擴股須有授權資料來源。未讀寫／消耗 `final-test-*.json` 或 locked holdout，未跑 final test、未刷新資料、未部署發布，無模型品質主張。

## 排程維護進度（2026-10-24，學習率與平方損失連動）

- 起始 AGY JSON 01:33:07+08:00：程式測試 52 passed／1 deselected，切片、比較契約、holdout 隔離 PASS；HTTP Connection refused、browser WARN 同因本機 8000 未監聽。monitor 的 HTTP 檢查只 probe URL；未發現可重現的程式缺陷，不把環境失敗誤報成程式修復。
- 第九步互動加入固定合成目標 W=1 與 L=(W−1)² 的更新前後 loss。預設步驟從 W=2 更新到 1.95，loss 由 1 降到 0.9025；η=10 時 W新=−3、loss 升到 16。指南與 browser 接受條件同步，且明示不代表真實模型收斂。
- 驗收：Node syntax、Python AST、9 個隔離數值案例、pytest 安全子集 52 passed／1 deselected、git diff check 通過。未執行 browser monitor，起始 JSON 不是改後證據。下一步在服務可用且不觸發 final-test UI 的瀏覽器環境，驗收此步和桌面／390px 顯示。
- 未觸碰 locked holdout／`final-test-*.json`，未執行一次性 final test、行情更新、部署或外部發布。

## 排程維護進度（2026-10-24，梯度方向教學與空值修正）

- **AGY 結果與最高優先缺陷：** 最新 `artifacts/regression-monitor/latest-checks.json` 時間為 2026-10-24 00:58:29+08:00。切片、模型比較契約、pytest（51 passed／1 deselected）及鎖定隔離均 PASS；首頁因 `127.0.0.1:8000` Connection refused 為 FAIL，browser 因同一服務不可達為 WARN。這是未監聽的本機服務狀態。另由現行 `calculateGradientStep('', 0.5, 0.1)` 獨立重現可見缺陷：空字串被 `Number()` 轉成 0，互動算式會把未填權重當成有效零值。
- **精確修改：** 梯度計算先拒絕空白欄位，畫面提示填妥三個有限數值；有效算式補上梯度為正／負／零時權重下降／上升／不變的即時解讀。教學指南修正一處損失函數定義錯寫為半平方的矛盾，與 `numpy_mlp_trace()`、畫面及 PyTorch 單筆 MSE 定義一致。回歸 monitor 接受條件涵蓋正負零梯度、空值／溢位拒絕及正梯度畫面解讀。
- **路線圖增量：** 推進神經網路學習中「梯度符號如何改變參數」的可操作練習；這只解釋單次更新方向，不代表整體損失下降或模型品質提升。未宣告學習里程碑完成。
- **驗收證據：** `node --check web/app.js`、monitor／ML Python AST、獨立執行五個計算案例（正、負、零、空白、超範圍）、安全 pytest 子集 51 passed／1 deselected、`git diff --check` 均通過。完整 monitor／browser 未執行；00:58 JSON 是改前證據，不能當成本輪畫面驗收。未以 smoke 主張品質。
- **剩餘／下一 checkpoint：** 本機服務可用時用安全 browser monitor 驗收第九步三種梯度方向、清空欄位提示及桌面／390px 可讀性，確認 monitor 不會觸發鎖定測試。熱門股既有本機覆蓋維持 10/10，擴充仍需授權來源；跨標的真實 OOF 方向／幅度讀圖仍待一般驗證資料。未讀寫 `final-test-*.json`／locked holdout、未跑一次性 final test、未刷新行情、未部署發布。

## 排程維護進度（2026-10-24，MSE 反向傳播係數說明）

- **最新 AGY 覆核：** `artifacts/regression-monitor/latest-checks.json` 為 2026-10-23 23:16:39+08:00。首頁 HTTP FAIL 是 `Connection refused`，瀏覽器因同一服務不可達而 WARN；`check_http()` 只探測 URL。獨立確認本機 8000 未監聽，這是執行環境狀態，沒有可重現的應用缺陷。
- **具體學習缺口與修正：** `app/ml.py::numpy_mlp_trace()` 使用 `L=(ŷ−y)²` 並計算 `δ²=2(ŷ−y)`，與單筆 PyTorch `MSELoss` 梯度一致；學習材料未解釋常見 `½(ŷ−y)²` 慣例會令梯度少一個 2。前端反向傳播步驟和 `docs/learning-guide.md` 現在明講兩種定義、梯度及係數來源。monitor 的 trace API 檢查核對 loss／梯度算式，瀏覽器接受條件核對可見說明。
- **改後接受證據：** `node --check web/app.js`、monitor Python AST、`numpy_mlp_trace()` 的 MSE／2e 算式及 NumPy/PyTorch 梯度 parity、前端／指南／monitor 接受文字檢查、`git diff --check` 通過。完整 monitor 未跑：最新記錄顯示服務未監聽，且完整流程含訓練 smoke；未以 smoke 作模型品質證據。瀏覽器視覺仍待可用服務環境驗收。
- **路線圖狀態與下一 checkpoint：** 推進神經網路學習中的「反向傳播與損失函數」小步；其他推導與完整互動驗收仍待做，不宣告整個里程碑完成。下一步在安全本機服務可用時執行不觸碰 final test 的 browser monitor，確認 trace 四步中係數說明桌面／390px 可讀，並核對現行 Loss hover。熱門股仍採已知本機 10/10 覆蓋，不擴充資料來源。未讀寫 `final-test-*.json`／locked holdout，未執行 final test、下載或刷新行情、部署或發布；無模型品質主張。

## 排程維護進度（2026-10-23，預測幅度導學第十步）

- **最高優先覆核：** 最新 AGY 22:43 overall FAIL 是 `127.0.0.1:8000` connection refused，browser 隨之 WARN。現行 monitor 的 HTTP check 只有探測 URL，沒有啟動服務；獨立覆核判為服務狀態，未重現程式缺陷，故不虛構修復。
- **路線圖增量：** 新增第十步導學，以合成預測 +0.6% 與實際 +0.2% 說明方向正確、幅度高估 0.4 個百分點；點明逐筆 OOF、MAE 和簡單基準仍是評估所需。初始化進度、學習指南和 monitor 接受條件一併更新。
- **證據與限制：** `node --check web/app.js`、Python AST、五項靜態接受條件及 `git diff --check` 通過。未執行完整 monitor／browser；22:43 是改前 JSON，尚無改後畫面證據。
- **下一 checkpoint：** 服務與 Chrome 可用時重跑 monitor，檢查步進第 9/10、10/10、返回及桌面／390px。熱門股既有本機覆蓋為 10/10；跨標的真實 OOF 讀圖需一般驗證材料。未接觸 locked holdout／`final-test-*.json`、未執行 final test、行情更新、部署或發布；無品質主張。

## 排程維護進度（2026-10-23，學習率步幅導學）

- **AGY 缺陷覆核：** 起始 `artifacts/regression-monitor/latest-checks.json` 為 22:09:46+08:00，整體 FAIL。唯一 FAIL 是首頁 HTTP `Connection refused`，瀏覽器因同一連線拒絕而 WARN。檢視 monitor 可見它只探測設定好的 `127.0.0.1:8000`，並不啟動服務；目前服務未監聽，故這是環境／服務狀態，未能獨立重現為程式缺陷。未改寫改前檢查結果。
- **路線圖小步：** 導學新增第九步「學習率」，以合成 `W=2`、梯度 `0.5` 算出 η=0.1 時 1.95、η=0.5 時 1.75，並說明單次更新不代表收斂或預測改善。第八步報酬換算器維持在第八步，HTML 初始進度更新為 1/9；學習指南新增同一算例。Regression monitor 增加第九步內容及第八步練習位置接受條件。
- **接受證據：** `node --check web/app.js`、monitor Python AST、從目前 JS 解析 LESSONS 並核對 9 步及 1.95／1.75 算例、`git diff --check` 通過。未執行完整 monitor／瀏覽器；22:09 JSON 是改前結果。未以 smoke 推論模型品質。
- **仍待完成／下一 checkpoint：** 先於安全本機服務可用時執行 regression monitor，確認導學前進／返回、末步、報酬換算仍正常，並檢視桌面／390px；本機熱門股資料覆蓋最新既有證據為 10/10，擴充資料清單需另有已授權資料來源及更新流程。跨標的真實 OOF 方向／幅度讀圖仍待一般驗證輸出。未讀寫 `final-test-*.json`／locked holdout、未執行 final test、未刷新行情、未部署或發布。

## 排程維護覆核（2026-10-23，報酬換算教學接受性）


## 排程維護覆核（2026-10-23，報酬換算有效範圍）

- **最高優先可重現缺陷：** 對數報酬 −101% 可合法換算，但同值簡單報酬無效；原 `renderReturnConversion()` 將 null 傳入 `.toLocaleString()`，造成 UI 例外。監測器也把 log 模式的 −101% 錯判為無效，並使用錯誤的預期換算值。
- **修復：** 有效主值仍顯示，無效比較明確顯示「簡單報酬定義無效」；simple −101% 顯示原輸入限制。監測器分別驗收兩種輸入定義，期望值校正為 20,000×exp(−1.01)=7,284.38。學習指南說明 log return 可低於 −100%，以及 simple-return 對照無效。
- **已前進的學習增量：** 第八步換算器新增可操作的有效範圍比較，幫助學習者辨認報酬定義差異；不涉及模型預測或品質。
- **證據：** `node --check web/app.js`、Python AST、從實際 JS 原始碼隔離執行四個邊界案例及 renderer 輸出、`git diff --check` 均通過。完整 monitor 21:01:18 FAIL：本機 HTTP 被 sandbox 拒絕，Playwright Chrome `TargetClosedError` 為 WARN；pytest 14 passed／1 deselected、隔離 smoke 及 holdout isolation PASS。browser 新案例未執行，沒有桌面／手機驗收。
- **下一 checkpoint／安全界線：** 在允許本機 HTTP／Chrome 的環境重跑 monitor，驗收 simple/log +1%、log −101%、simple −101% 及桌面／390px 呈現。熱門股仍以本機 10/10 覆蓋為最近證據；真實跨標的 OOF 讀圖待一般驗證輸出。未讀寫 `final-test-*.json` 或 locked holdout、未執行 final test、未更新行情；smoke 不作模型品質證據。

- **最高優先缺陷覆核：** 最新 AGY `2026-10-23T20:22:35+08:00` 為 40 項全 PASS。檢查殘差有效值處理、已保存驗證摘要的 null MAE 邊界及 `/api/data/status` 回傳，未從當前實作重現新的高優先缺陷。
- **功能增量：** 學習中心第八步新增報酬換算器：可編輯點位、百分比及簡單／對數定義，並並列同數字在另一報酬定義下的換算。非法點位及簡單報酬 ≤ −100% 顯示輸入說明。Monitor 增加 UI 接受條件。
- **驗證狀態：** `node --check web/app.js`、monitor AST 與隔離算式（20,000×1.01=20,200；20,000×exp(0.01)≈20,201.00；拒絕 −101%）通過。20:25:06 改後完整 monitor FAIL：首頁 socket 被 sandbox 拒絕、Chrome TargetClosedError 導致 browser WARN；其餘 6 項 PASS，pytest 14 passed／1 deselected，鎖定隔離 PASS。新 browser 接受條件未執行；20:22 JSON 是改前 40/40。
- **下一 checkpoint／界線：** 在允許本機 HTTP／Chrome 的環境重跑 monitor，核對新接受條件及桌面／390px 顯示；本輪沒有瀏覽器驗收。未讀寫 `final-test-*.json`／locked holdout、未執行一次性 final test、未刷新行情；smoke 不作品質證據。

# 序列觀測站 (taiex-neural-lab) 實測問題報告與修復指南


## Scheduled maintenance update (2026-10-26, Guided navigation fixture synchronization)

- **Latest AGY evidence:** `artifacts/regression-monitor/latest-checks.json` at `2026-10-26T10:35:07+08:00` reports overall FAIL. Safe pytest snapshot is `158 passed, 1 deselected`; the sole reported browser failure is `多模式學習互動`, specifically `導學前進/返回=False`. Local popular-stock coverage is 10/10; training smoke and locked-test UI were skipped, and locked-test isolation passed. This JSON predates the changes below.
- **Highest-priority reproduced defect:** The monitor navigation fixture reset `lessonIndex` and the saved-progress snapshot after earlier browser exercises but did not call `renderLesson()`. Its displayed progress could therefore remain at a previously exercised step while the fixture treated it as step 1, making the next/back acceptance depend on stale rendered state.
- **Exact change:** The fixture now calls `renderLesson()` immediately after resetting its in-memory state, without persisting that reset to browser storage. Failure detail now records start, next, and back step numbers. Added a focused source-contract regression test.
- **Roadmap progress:** Advanced the neural-network learning milestone's Guided navigation reliability: acceptance now starts from a visible, controlled first step and reports each transition. This is navigation/fixture evidence, not training or model-quality evidence.
- **Verification:** Focused pytest `2 passed, 72 deselected`; `node --check web/app.js`, Python AST parsing of monitor/tests, and scoped `git diff --check` passed. No post-change browser run or desktop/390px render acceptance is claimed.; combined focused learning/data-guard/UI selection `30 passed, 68 deselected`
- **Remaining / next checkpoint:** Re-run browser-only acceptance without training smoke or locked-test UI to confirm next/back and collect start/next/back detail; trace any remaining failure. Saved-summary and lesson failures from earlier snapshots should be retested against current code. Popular-stock expansion still needs an authorized data source; real cross-symbol rise/fall magnitude comparison needs compatible ordinary OOF summaries. No protected data, final test, market refresh, training, deployment, or publication occurred.

## 2026-10-25 maintenance finding and progress

- **Reproduced defect:** AGY 09:40:28 reported the network completion check as failed. The current app sets the completed epoch label from `buildConfig().epochs`, while the monitor hard-coded `025` and bundled that comparison with output-stage arrival. At any configured epoch count other than 25, the monitor could falsely report that the animation failed to reach output.
- **Change:** The monitor now reads the configured completion label and reports terminal output arrival and epoch-label matching as separate conditions.
- **User-visible increment:** Lesson 20's momentum calculator now includes the β=0 no-carryover reference beside β=0.5 and the user-selected β. For its default synthetic values the outputs are β=0: velocity 1.0000, weight 1.9000; β=0.5: 1.2500, 1.8750; β=0.9: 1.4500, 1.8550. Guide updated; this is formula teaching only.
- **Verification and limits:** Focused pytest `1 passed, 52 deselected`; safe suite `122 passed, 1 deselected`; `node --check`, Python AST, and scoped diff checks passed. Browser run was attempted but blocked by sandbox local HTTP denial and Chrome `TargetClosedError`. No visual/browser acceptance is claimed. Other 09:40 AGY browser failures remain unverified.
- **Next checkpoint:** Run the separated animation acceptance with a browser at a non-default epoch setting; investigate interval/ReLU/later lessons, saved-summary fixture, Guided navigation, Loss hover, and 390px axis labels; inspect the new momentum comparison at desktop and 390px. Keep local coverage at 10/10 until an authorized data source is available; real cross-symbol magnitude learning requires comparable ordinary OOF summaries. No locked holdout or final-test artifact was accessed; no one-time final test or market refresh was run.

## 排程維護覆核（2026-10-24，browser 動畫等待逾時）

- **改前：** AGY JSON 05:09:21+08:00 有 18 PASS／1 WARN／0 FAIL，WARN 為 Playwright wait-for-function 1500ms timeout。既有檢查明示 reduced-motion 下動畫不應執行；若仍期待計時器推進就會逾時。
- **精確修正：** 將自動播放／暫停測項設為 `no-preference`，明確等待動畫步驟前進與 pause 啟用後再暫停；reduced-motion 獨立驗收手動步進的靜態階段。保留原檢查要求，沒有放寬為無條件通過。Monitor 不開啟或點擊一次性 final-test UI。
- **路線圖：** 維持第 11 步合成區間算術教學（中心 +0.6%、尺度 0.4pp、顯示 +0.20% 至 +1.00%）；本輪未新增產品功能，未提升整體里程碑狀態。
- **證據／下一步：** 改後須做 Python AST、源碼接受條件、pytest 安全集合與 diff check；未重跑 browser monitor，改前 JSON 不能當改後證據。下一 checkpoint 是在可用安全瀏覽器驗收動畫時序、區間互動、桌面／390px。未讀寫／消耗 locked holdout 或 `final-test-*.json`，未執行 final test、行情刷新、部署發布，無模型品質結論。
## 排程維護覆核（2026-10-23，導學初始進度不一致）

- **起始證據與重現：** 最新 AGY 於 19:45:43 為 39/39 PASS。`web/index.html` 的導學初始文字仍是「第 1 / 6 步」，而 `LESSONS` 有 7 項；因此載入 JS 前顯示錯誤總數。舊 monitor 只檢查渲染後 DOM，故未捕捉靜態初始狀態。
- **修正與學習增量：** 初始文字改為 1/8；新增簡單報酬 +1% 與對數報酬 +1% 轉換為 20,200／約 20,201 點的導學，說明換算值不是模型直接預測或成交價。Monitor 新增 8 步及算例／限制接受條件。
- **改後證據：** `node --check web/app.js`、monitor AST、靜態接受斷言與 `git diff --check` 通過。19:48 monitor 整體 FAIL：首頁 socket 被 sandbox 拒絕、Chrome `TargetClosedError`，故新增 browser 接受條件未執行；walk-forward 切片、隔離 MLP/GRU smoke、pytest 14 passed／1 deselected、鎖定路徑隔離 PASS。19:45 是改前結果。下一步在允許本機 HTTP／Chrome 的環境確認初始進度、步進返回及手機版可讀性。未讀寫 holdout／`final-test-*.json`，未執行 final test 或行情更新；smoke 不作品質主張。

## 排程維護覆核（2026-10-23，窄螢幕多模型 X 軸標籤）

- **起始證據與重現：** 最新 AGY `latest-checks.json` 為 `2026-10-23T18:35:29+08:00`，唯一 FAIL 是 390px viewport rotated/short labels=0/8。現行 `renderComparison()` 對 8 列不旋轉；這與 monitor 八模型接受條件直接矛盾。
- **修正：** 六組以上的窄圖使用旋轉短標籤，窄版縮短歷史平均及零報酬名稱，SVG title 保留完整名；頁面加上短標籤提示，monitor 核對提示可見。
- **路線圖小步：** 手機模型比較讀圖新增短名與完整名對照提示，屬神經網路學習工作台的有限進展，不代表模型品質。
- **改後驗證：** JS syntax、monitor AST、隔離接受斷言和 `git diff --check` 通過。完整 browser monitor 未執行，起始 FAIL 尚無改後瀏覽器證據。
- **下一步：** 安全執行 browser monitor，確認 390px 八標籤／提示可見，桌面仍可讀且無水平溢位。未碰 `final-test-*.json`／locked holdout、未執行 final test、未刷新資料或訓練。

## 排程維護覆核（2026-10-23，鎖定區間中繼資料最小化）

- **起始證據：** 最新 AGY `latest-checks.json` 為 `2026-10-23T17:59:55+08:00`、39/39 PASS。`check_splits_and_train()` 的邊界檢查將所有保留區 target 數及首末日期寫進一般報告；這是可由目前程式重現的非必要鎖定區間揭露，亦容易被讀成已測得結果。
- **修正：** 報告只記錄邊界索引與邊界後樣本數，明示其為切分中繼資料，未讀取或評估觀測值；時間序列 validation target 邊界條件不變。
- **學習功能：** 學習中心加入切分邊界判讀任務及即時正誤回饋，指南說明切分資訊不構成模型成績，任務不讀取或執行鎖定資料。
- **驗證狀態：** `node --check web/app.js`、4 個 Python AST、6 項隔離接受斷言、聚焦 API 測試（1 passed）及 `git diff --check` 通過。完整 browser monitor 未執行；17:59 JSON 是改前證據。
- **下一 checkpoint：** 驗收 browser 任務正誤回饋與桌面／390px 顯示，確認更新 monitor 報告只含中繼資料。未讀寫 `final-test-*.json`／locked holdout，未執行 final test、未更新行情，無品質主張。

## 排程維護覆核（2026-10-23，逐折誤差缺值）

- **起始證據：** `latest-checks.json` 時間 `2026-10-23T16:44:07+08:00`，37/37 PASS。另以現行程式重現缺值邊界：逐折圖把 `residual:null` 透過 fallback 算作零；缺 actual/predicted 時雖產生 NaN，原列仍增加累計平均的分母。
- **修正：** `renderDiagnostics()` 為每列產生有限 residual，僅在 actual 與 predicted 完整時 fallback；逐折誤差曲線及 n 僅採有效列，圖例顯示排除數，無有效殘差時顯示空狀態。Monitor 加入隔離 browser fixture。
- **路線圖進度：** learning guide 新增如何閱讀逐折圖例有效 n、缺值不等於零誤差。這是殘差診斷學習的有界子任務；完整跨標的 OOF 學習仍待一般驗證結果。
- **改後證據／限制：** `node --check web/app.js`、Python AST、fixture（有效 residual=[0.01, 0.004]，平均絕對值 0.700 pp）和 pytest 14 passed／1 deselected 通過。未跑完整 browser monitor；起始 JSON 仍為改前結果。`git diff --check` 在更新四份記錄後執行。
- **下一 checkpoint：** 安全 browser monitor 驗收新 fixture 及桌面／390px 呈現。未讀寫 `final-test-*.json` 或 locked holdout，未執行 final test、行情更新或訓練；隔離驗收不是模型品質證據。

## 排程維護覆核（2026-10-23 03:00，方向接受條件位置過期）

- **缺陷重現：** 最新完整監測 `2026-10-23T03:00:14+08:00` 有一項 FAIL。detail 列明殘差、校準和指南條件均通過，只有 `UI direction=False`。monitor 搜尋 `.metrics-explainer` 中的方向計分字句；目前 UI 把正式方向準確率定義放在 `button[aria-label="評估指標說明"]` 的 title，故舊 selector 造成可重現的假 FAIL。
- **確切修改：** 更新 `direction_ui_ok`，分別檢查 tooltip 定義、指南逐筆計分和 `#directionMix` 的實際／預測摘要。接受檢查仍要求內容存在，沒有刪除或放寬為無條件通過。
- **使用者可見學習功能：** 評估卡新增可展開的合成多數類別例子：實際 8 漲 2 跌、全部猜漲仍得 80%，但無法辨認下跌；指南新增相同解釋與比較 MAE、方向比例和簡單基準的提示。
- **改後驗證／限制：** `node --check web/app.js`、monitor Python AST、6 項靜態接受斷言及 `git diff --check` 通過；未重跑 browser monitor，03:00 FAIL 仍是最後完整監測結果。桌面／手機畫面尚未驗收；最新 JSON 的設計比對項另有 WARN。監測中隔離 smoke 僅為執行檢查，不作預測品質證據。
- **下一步：** 通過靜態檢查後，在可安全隔離一般驗證資料且不呈現 locked-test 輸出的 Chrome 情境執行 monitor，確認方向 tooltip、分布摘要和新展開例子於桌面／390px 的呈現。未讀寫 `final-test-*.json` 或 holdout，未執行 final test、行情更新或模型訓練。


## 排程維護覆核（2026-10-23，校準診斷失敗資訊缺口）

- **具體缺陷與重現：** 最新 regression JSON `2026-10-23T02:24:30+08:00` 的校準診斷項目 FAIL。檢查以多個子條件計算 `diagnostic_ok`，但 detail 只列部分圖表案例，未列五個教學／UI 子條件；閱讀目前 monitor 的布林合取與 detail 格式即可重現，無法從這筆 JSON 判定真正觸發 FAIL 的子條件。
- **修改：** monitor detail 現在輸出 `calibration_guide_ok`、`direction_guide_ok`、`direction_magnitude_guide_ok`、`magnitude_guide_ok` 和 `direction_ui_ok`。保留原 FAIL，不猜測底層成因。
- **同輪學習功能：** 加入加權校準偏差互動題，接受條件要求錯答提示、正確的 −0.125 個百分點／高估解讀及合成資料限制。
- **證據狀態：** `node --check web/app.js`、Python AST 解析、5 項隔離接受斷言及 `git diff --check` 通過；未跑完整 browser monitor，原 FAIL 尚未被新結果取代。新互動無桌面／手機驗收證據。現有頁面的可及性快照曾意外包含已保存鎖定測試輸出；未操作或修改，隨即停止瀏覽器檢查。
- **下一步：** 在安全 Chrome 環境重跑 monitor，先用新 detail 找出校準 FAIL 的實際子條件，再確認互動與窄螢幕顯示。未使用或修改 locked holdout／`final-test-*.json`，未跑 final test、資料更新或模型訓練；不作模型品質結論。

## 排程維護覆核（2026-10-23 01:16 AGY）

- **最高優先可重現問題：** 前向傳播檢查 FAIL 的 MLP 子條件要求固定第一層算式；實際 `networkStageEquation(step)` 依 `step` 產生動態層號，檢查與 UI 不一致。第二個診斷 FAIL 由文件接受片語過時造成：指南用「方向摘要會並列實際與預測…」，monitor 卻要求舊片語。
- **確切修正：** monitor 對 MLP 公式採空白正規化及通用 `z/W/a/b/ReLU` 結構判斷，避免依賴停留在哪個隱藏層；指南接受字串更新成現行片語。RNN/LSTM/GRU 公式仍逐模型核對。
- **路線圖進度：** 讓逐層 MLP 算式與指南中的方向／幅度解讀具備匹配可見內容的接受檢查；屬有限學習增量，不宣稱整體里程碑完成。
- **證據與限制：** Python AST 編譯、隔離接受條件、`git diff --check` 通過。尚未重跑 browser monitor，故 01:16 JSON 兩項 FAIL 尚待瀏覽器確認，不能標記整體回歸通過。
- **下一 checkpoint：** 在 Chrome 可用環境安全執行 monitor，確認 MLP 動態公式、RNN/LSTM/GRU 算式及診斷檢查；未讀寫 locked holdout／`final-test-*.json`，未執行 final test、訓練或資料更新。

## 排程維護進度（2026-10-23，公式回歸狀態隔離與循環網路學習）

- **最新起始問題與重現：** 讀取最新 AGY `latest-checks.json`（00:39:41+08:00，overall FAIL）：前向傳播「層公式=False」，診斷檢查也 FAIL。前向檢查只在頁面當下選到 MLP 時才成立；但它沒有設定模型選擇，會受瀏覽器保存的上次設定影響，故同一 MLP 公式接受條件非決定性。診斷 FAIL 的隱藏子條件可由 monitor 程式對照指南重現：文件已用「方向準確率」取代舊的「方向命中率」，接受詞未同步。
- **確切修正：** monitor 在驗證公式前明確選 MLP、重設步進狀態，再逐一切換 RNN/LSTM/GRU 檢查算式。同步校正指南接受詞為「方向準確率」。
- **路線圖小步：** 前向傳播逐層提示新增可讀的 LSTM 記憶／輸出更新式、GRU 閘門及候選狀態混合式；指南說明各公式是架構概念。回歸接受條件逐模型核對 MLP、RNN、LSTM、GRU 的隱藏層算式。
- **改後證據：** `node --check web/app.js`、monitor Python AST、pytest 安全子集（14 passed，1 deselected）通過。完整 monitor 於 00:42:04 執行：walk-forward 切分、隔離 MLP/GRU 1 epoch smoke、pytest、鎖定隔離均 PASS；整體 FAIL 是本機首頁 socket 被 sandbox 拒絕（`Operation not permitted`），Chrome `TargetClosedError` 導致瀏覽器 WARN。故新公式的 browser 接受條件尚未執行；smoke 不作模型品質證據。報告未把失敗改成通過。
- **仍待完成／下一 checkpoint：** 在允許本機 HTTP 與 Chrome 的環境重跑 monitor，確認四模型公式、診斷接受條件及桌面／390px 畫面後刷新 JSON。跨標的真實 OOF 學習仍待一般個股驗證輸出；熱門股本機覆蓋仍為 10/10。本輪未讀寫 `final-test-*.json` 或 locked holdout、未執行一次性 final test、未刷新行情或訓練模型。

## 維護覆核（2026-10-22，殘差診斷缺值）

- **最高優先缺陷與重現：** 起始 AGY JSON `2026-10-22T23:30:24+08:00` 唯一 FAIL 為診斷圖檢查。`renderDiagnostics()` 對 `residual:null` 使用 `Number()` 會得到 0；若 residual 缺失，fallback 亦未先確認 actual/predicted 可用，可能把缺值當作真實殘差，污染分布、平均與峰度。
- **確切修正：** residual 非 null／undefined／空字串才採用；否則只有 actual 與 predicted 都非空才相減。沒有有限值時顯示空狀態，不輸出直方圖／統計。Monitor 加入 null/incomplete 與全缺資料 fixture。
- **路線圖進展：** 學習指南新增缺值殘差閱讀步驟，讓學習者區別缺資料與零報酬，推進神經網路誤差診斷學習。
- **改後驗證：** Node 隔離 fixture 確認一筆不完整配對不納入，剩餘殘差均值 1.000 pp；全缺資料顯示明確提示。`node --check web/app.js`、monitor AST compile、`git diff --check` 與 pytest 安全子集（14 passed／1 deselected）通過。未跑完整 browser monitor；起始 JSON 仍是最後的 browser 結果，不能標記該 FAIL 已由瀏覽器回歸清除。
- **下一 checkpoint：** 在可用瀏覽器環境執行新 monitor 接受案例及桌面／390px 手機驗收；後續用一般個股 OOF 摘要進行跨標的讀圖。未讀寫 locked holdout／`final-test-*.json`、未執行 final test、未更新行情、沒有模型品質主張。

## 維護覆核（2026-10-22，跨標的摘要輸出安全）

- **最高優先缺陷與重現：** 起始 AGY JSON `2026-10-22T22:52:05+08:00` 為 36/36 PASS，無報告失敗。現行跨標的比較將保存摘要的動態名稱／日期值拼入 `innerHTML`，標記字串會被解析為 DOM 元素，可形成注入路徑。
- **確切修正：** `renderSavedComparisonLines()` 以 `createElement` 和 `textContent` 將動態列作純文字呈現；monitor fixture 注入 `<img ...>` 並確認不產生 `img` 元素。
- **路線圖增量：** OOF 方向摘要並列實際／預測各方向平均絕對幅度；指南說明不同方向各自取樣、無樣本與描述限制。
- **改後證據：** Node stub 將 `<img ...>` 保留於 `textContent`，方向摘要隔離案例精確顯示實際上漲 2.000pp／預測 1.500pp、實際／預測下跌各 1.000pp。JS syntax、monitor Python AST、`git diff --check` PASS。22:55 完整 monitor FAIL：首頁 HTTP 被 sandbox `Operation not permitted` 阻擋，Chrome `TargetClosedError` 使 browser check 為 WARN；pytest 14 passed／1 deselected，鎖定隔離 PASS。新 browser fixture 未能執行，起始 JSON 為改前證據。
- **下一 checkpoint：** 在本機 HTTP 與 Chrome 可啟動的環境重跑 monitor，驗收純文字輸出、幅度數字和桌面／390px 手機版；再等待一般個股 OOF 摘要作實際讀圖。

## 維護覆核（2026-10-22，缺值 MAE 與校準加權算例）

- **最高優先缺陷與重現：** 最新 AGY JSON `2026-10-22T22:09:16+08:00` 為全項 PASS。獨立檢查 `savedValidationSummary()` 發現 `Number(null) === 0`：已保存摘要若模型或基準 MAE 為 `null`，會顯示成 0.000% 並可能輸出錯誤差值。以現行轉換路徑可重現，屬摘要資料完整性缺陷。
- **確切修正：** MAE 僅在原值非 null／undefined／空字串、可轉數字且非負時採用；無效模型 MAE 顯示「不可用」，無效基準不顯示基準差值。Regression monitor 加入 null model／baseline fixture。
- **路線圖增量：** 校準圖的可展開合成例子增加兩組樣本數加權計算，並呈現不加權會把偏差方向看反；更新學習指南與 monitor 接受條件。此為預測幅度學習的一個有限步驟，不宣稱完整里程碑完成。
- **改後證據：** `node --check web/app.js`、monitor Python AST、隔離 null model／baseline 摘要行為、加權算例內容接受檢查及 `git diff --check` 均通過。未重跑完整 browser monitor，故 22:09 JSON 是改前證據，不表示本輪改後瀏覽器通過。未讀寫 locked holdout／`final-test-*.json`、未執行 final test、未刷新市場資料。
- **下一 checkpoint：** 在安全 browser monitor 驗收 null MAE 分支及可展開加權算例的桌面／手機可見性；再以一般個股 OOF 結果完成實際跨標的方向／幅度讀圖。熱門股本機覆蓋已由最新 JSON 顯示 10/10；不以 smoke 或合成資料主張模型品質。

## 維護覆核（2026-10-22，跨標的 OOF 誤差差值）

- **失敗覆核：** 起始最新 monitor 是 20:59:32、36/36 PASS、0 WARN／FAIL；未發現可獨立重現的當前產品回歸失敗。獨立檢查發現已保存跨標的摘要只並列模型與簡單基準 MAE，沒有直接呈現其差值，增加讀圖心算負擔。
- **變更與學習進度：** `savedValidationSummary()` 在兩個有效非負 MAE 都存在時顯示模型 MAE 減基準 MAE 的百分點差，正值標示模型誤差較大、負值標示較小；缺少基準不推算。指南補上方向解讀及跨標的時間限制，regression monitor 增加正差、負差和缺基準接受案例。
- **改後證據：** 隔離 Node 行為接受案例通過（模型 1.000% 對基準 1.200% 得 −0.200pp；對 0.800% 得 +0.200pp；無基準時不顯示差值）。JavaScript syntax、monitor Python compile、`git diff --check` 通過。未執行完整 browser monitor／pytest，20:59 JSON 是改前結果，不作改後 UI 證據。
- **剩餘／下一 checkpoint：** 安全 browser monitor 驗收桌面及 390px 差值顯示與缺基準分支；有一般個股 OOF 時核對驗證期間及基準是否可比。未讀寫 locked holdout/final-test、未跑一次性 final test、未刷新行情。差值只描述驗證資料，不證明模型品質。

## 維護覆核（2026-10-22，校準圖缺值配對）

- **起始證據：** 最新既有 AGY JSON 為 20:22:36、36/36 PASS。獨立檢查現行 `renderCalibration()` 發現 actual/predicted 直接經 `Number()` 轉換；JavaScript 的 `Number(null)` 為 0，會把不完整配對錯算成零報酬，污染校準組與有號／絕對幅度摘要。此為目前程式缺陷，舊檢查沒有此接受案例。
- **確切變更：** 對 null、undefined、空字串及非有限值排除配對；結果卡摘要顯示排除筆數，即使有效筆數不足兩筆也揭露。學習指南解釋缺值不視為零；`scripts/regression_monitor.py` 增加兩個 null 配對 fixture，檢查僅有效配對進入圖表及排除數可見。
- **驗收證據與限制：** 隔離 Node 行為案例通過：四列中只繪製 2 筆有效配對、顯示排除 2 筆；單一有效列分支顯示有效 1／排除 1。`node --check web/app.js`、monitor Python compile、`git diff --check` 通過。20:25 monitor 整體 FAIL：首頁 HTTP 被 sandbox 以 `Operation not permitted` 阻擋，Chrome/Playwright 啟動中止；pytest 14 passed／1 deselected、隔離 MLP/GRU smoke 及鎖定隔離檢查 PASS。新增 browser fixture 尚未實際執行，最新 JSON 不可描述為全套回歸通過。
- **路線圖進度與下一 checkpoint：** 前進預測幅度學習：顯示校準有效樣本及排除配對數，避免缺值被誤讀為零。下一步在可用本機 socket／Chrome 的環境重跑安全 browser monitor，驗收 null fixture 與桌面／手機呈現。未讀寫 holdout/final-test、未執行一次性 final test、未刷新行情；隔離 smoke 不作模型品質主張。

## 維護覆核（2026-10-22，跨標的既有驗證摘要）

- **最新失敗覆核：** 本輪起始 `latest-checks.json` 為 19:46:29、36/36 PASS；19:11 的跨標的資料聲明互動失敗已修復，現行程式和 monitor 條件一致，無新的可重現高優先缺陷。
- **路線圖變更：** 學習卡可讀取個股與 TAIEX 已保存的一般驗證摘要，並列 OOF MAE、已保存的 naive／historical mean MAE、驗證期間、方向分布及預測幅度。缺失時明示；驗證期間或基準不同需先對齊才可比較。讀取端點僅為 `/api/validation/latest`。
- **接受證據：** monitor 新增 synthetic fixture 核對數值與缺結果分支；JS syntax、Python compile、`git diff --check` 通過。完整 monitor 卡在先行隔離訓練 smoke 超過 30 秒後由維護流程中斷，未取得改後 browser／pytest 證據。19:46 JSON 是改前結果。
- **下一檢查點／限制：** 用無訓練 smoke 的 browser fixture 驗收桌面與 390px 版面；有實際保存的一般個股驗證結果時再核對呈現。未觸碰 holdout/final-test、未執行一次性 final test、未刷新行情，沒有模型品質結論。

## 維護覆核（2026-10-22 19:11，跨標的練習 FAIL）

- **可重現缺陷：** 最新 AGY `latest-checks.json` 為 35 PASS／0 WARN／1 FAIL。跨標的練習錯答及正答回饋均正常，但合成資料限制在回答後不可見。原因是固定資料聲明與互動 feedback 共用 `#crossAssetFeedback`，JS 以答題訊息覆寫該節點。
- **修復及學習增量：** 聲明移到獨立固定可見 `.learning-data-note`；feedback 區獨立且初始隱藏，答題時再顯示。實驗任務增加四項「下一步比較」清單（OOF 誤差、基準、相同期間、幅度校準）。monitor 現在在互動後檢查聲明可見與清單文字。
- **驗證：** `node --check web/app.js`、monitor Python compile、隔離接受斷言、`git diff --check` 通過。沒有執行完整 browser monitor；19:11 JSON 是改前結果，不能算修復後通過。
- **剩餘／下一 checkpoint：** 安全瀏覽器巡檢錯答和正答後的即時回饋及聲明持續可見，確認桌面／手機清單版面，再以新 JSON 驗收。真正跨標的 OOF 示例仍待一般驗證資料。未讀寫 final-test/holdout，未執行 final test 或刷新資料；無品質主張。

## 維護覆核（2026-10-22）

- 最新 AGY JSON 為 18:36:09、35/35 PASS、0 WARN、0 FAIL；前向傳播逐層節點／連線檢查 PASS。獨立對照目前 `activateNetworkStage()`，第二層狀態與 monitor 條件相符；17:28 的歷史 FAIL 已非現況，沒有重複修補。
- 本輪沒有新增可重現產品缺陷。已前進的學習任務為跨標的方向／幅度合成讀圖互動，新增 browser 驗收涵蓋錯答提示、正答與資料標示。
- 驗證：JS syntax、Python compile、靜態接受條件、`git diff --check` 通過。browser monitor 未執行，故互動尚無瀏覽器改後證據。
- 下一步：在安全 browser monitor 驗收桌面與手機；之後再以一般個股 OOF 驗證結果教學實際跨標的比較。不可消耗 locked holdout 或執行一次性 final test。

## 最新 AGY 覆核（2026-10-22，前向傳播動畫）

- **獨立重現的最高優先問題：** `artifacts/regression-monitor/latest-checks.json` 記錄於 2026-10-22 17:28:46，整體 FAIL，唯一失敗為神經網路前向傳播動畫中的「節點與連線逐層點亮」。步進、播放、暫停與 reduced-motion 分支均通過。現行 `activateNetworkStage()` 將 traversed 連線延遲至再下一步（`layer < step - 1`），且輸入層也被套上 reached，狀態視覺定義錯位。
- **修正：** 前端只把已完成的隱藏層標記 reached，輸入保持其輸入語意；訊號抵達下一層時，前一段連線即標記 traversed。監測器接受條件同時核對輸入 active、第二層 active、第一段連線 traversed 和下一段仍未 traversed。
- **路線圖增量：** 學習指南補充動畫狀態顏色、代表連線與「概念示意而非真實權重／梯度」的說明，推進神經網路前向傳播學習。
- **改後驗證：** JS 語法、monitor Python compile、源碼狀態斷言及 `git diff --check` 通過。Playwright、Puppeteer、jsdom 不可用，因此改後瀏覽器顯示尚未驗收；最新 JSON 是改前失敗，不是改後結果。完整 monitor 未執行。
- **下一步：** 在可用瀏覽器重跑前向傳播 monitor，檢查輸入、已完成隱藏層、目前層與已傳遞線條在桌面／手機的實際顯示，再核對暫停／重播。不得以此主張預測品質；不讀寫 holdout、不執行 final test、不刷新市場資料。

## 動畫品質修正：前向傳播

- **發現：** 待機時節點呼吸、突觸連線及特徵箭頭都持續循環；播放時整層連線同時快速閃動，視覺噪音偏高。
- **修正：** 待機改為靜態；前向傳播逐層停留 820ms，以 8 條代表連線分批掃過，其他連線降為低對比；取消節點反覆放大脈衝，改用狀態顏色與柔和陰影轉換。
- **驗收：** 本機 Chrome 播放至完成、狀態文字逐層更新，第 2 層僅 8 條路徑流動。手機 390px reduced-motion 會停用動畫，控制按鈕各 44px，無橫向溢位；Node 語法檢查、git diff whitespace 檢查通過。完整 monitor／pytest 未執行。


## 2026-10-22 最新覆核：歷史缺陷狀態與本機標的覆蓋

- **最高優先審查缺陷：** 歷史 Bug 9 建議把鎖定測試預測疊回一般走勢圖；這會把受保護觀測帶入日常頁面與監測流程，與本任務隔離邊界衝突。該段只是過往功能建議，不能作為當前待辦。
- **核對：** 最新 monitor JSON 為 2026-10-22 16:54:11、35/35 PASS，其中「鎖定測試圖表隔離」確認 routine browser checks 不檢查 holdout DOM；「鎖定測試資料隔離」亦 PASS。沒有讀取或執行 final-test 資料。
- **可重現的維護缺陷與修正：** 先前維護摘要將覆蓋 UI 的桌面／手機驗收誤列為待辦，與最新 monitor 證據不符。已更新狀態：10/10 本機個股可用，桌面標的列可見覆蓋數與同步選取，手機標的列可橫向瀏覽且無頁面溢位。
- **里程碑與下一工作：** 熱門股覆蓋可見性小步已有 monitor 驗收；仍待以一般個股 OOF 驗證結果進行跨標的方向／幅度讀圖。不增加或刷新市場資料。本次使用既有 JSON 證據，沒有重跑 monitor。

## 2026-10-22 排程維護：例行監測觸碰鎖定觀測

- **最高優先缺陷與重現：** 最新 15:04:32 機器結果為 35/35 PASS，但 `scripts/regression_monitor.py` 的瀏覽器檢查會讀取 `#finalPredictionChart` 的線條和預測表列數；首頁載入資料狀態亦包含 `finalTest`，完整結果再把該 metadata 寫入 `latest-checks.json`。這使 routine monitor 會檢視已揭露的 holdout UI 狀態，與「不得讀取／消耗鎖定觀測」邊界衝突。此為監測器隔離缺陷，非模型錯誤。
- **修正：** 移除鎖定圖表的 DOM 查詢，改為明確記錄 monitor 不檢查 holdout；狀態回應進入檢查器時立即剔除 `finalTest`，回歸 JSON 不再保存該欄；檔案狀態保護只列路徑、不讀檔案內容。保留隔離訓練時阻止 final-state writer 的保護。
- **路線圖小步：** 驗證方向分布新增「實際結果至少 70% 集中於單一方向」提醒，說明方向分數可能受類別比例影響。指南界定 70% 為閱讀提示，不是交易或選模門檻；monitor 加入集中／未集中案例。
- **驗收證據：** Node 隔離案例確認 100% 集中時提示、均衡樣本不提示、空資料為空；monitor Python compile、來源隔離靜態條件、`node --check web/app.js`、安全 pytest（14 passed, 1 deselected）和 `git diff --check` 通過。沒有重跑完整 browser monitor，避免透過 dashboard 初始載入讀取 holdout UI；15:04:32 的 35/35 是修改前結果。
- **剩餘／下一 checkpoint：** 在能以一般驗證狀態啟動瀏覽器的隔離環境驗證完整頁面提示，並確認最新 monitor JSON 不含 `finalTest`。熱門股仍為本機 10 檔；下一個大步是跨標的 walk-forward 讀圖。未讀取/改寫 `final-test-*.json`、未執行 final test、未刷新市場資料；不作模型品質主張。

## 2026-10-22 維護覆核：歷史確認項目狀態

本報告下方的「確定性缺陷」是歷史檢查線索，不能直接視為現行未修問題。依目前程式和最新 `artifacts/regression-monitor/latest-checks.json`（14:27:43，34/34 PASS）覆核：Bug 1 多模型比較已追加所有模型且監測通過；Bug 2 的 422 陣列錯誤已轉成人類可讀訊息且監測通過；Bug 3 描述不成立，現行 `_metrics` 對零預測定義為中性半分，指南、測試及介面一致。Bug 4、5、6 亦有現行測項通過。後續項目需逐項按當前程式重現後再定級，勿依本節以下舊有「實測確認」標題判定仍未修復。

本次額外推進方向學習：驗證結果同時呈現逐筆 OOF 實際方向與預測方向的漲／跌／持平或中性比例；新增 browser monitor 合成接受案例，含比例和空資料分支。此為方向分布的教學觀察，不是模型品質或預測優勢證據。

驗收證據與範圍：Node 合成案例確認實際／預測方向各 2 上漲、1 下跌、1 持平／中性，空資料回傳空摘要，不完整 actual/predicted pair 一起排除；`node --check web/app.js`、monitor Python compile、安全 pytest 子集（14 passed, 1 deselected）及 `git diff --check` 通過。browser monitor 已加入同一接受案例。最新既有完整 monitor 的 34/34 PASS 是改動前結果；本輪沒有重跑會讀取鎖定測試圖表的完整 monitor。下一檢查點是在可安全隔離一般驗證狀態的環境執行 browser monitor 新增案例；不可消耗鎖定觀測。

## 視覺審查後續補記（GOOD+ 建議）

- **審查跟進：** GOOD+ 巡檢建議為神經網路畫布增加暗色極客終端視覺。已在 `web/styles.css` 為網路區局部加入深色網格背景、節點分層色、連線及啟動狀態光暈；頁面其餘面板不變。
- **現場證據：** 本機 Chrome 1600px 截圖 `artifacts/regression-monitor/network-dark-canvas.png`。播放後 6 個節點 active、30 條連線 flowing；390px 手機在 reduced-motion 模式下節點和連線動畫皆關閉，操作鈕高度均為 44px，水平溢位 0px。`git diff --check` 通過。
- **狀態：** 視覺抽查完成；未執行完整 regression monitor、pytest、模型訓練或 final test。沒有發現需要新增到 bug backlog 的重現問題。

## 最新排程維護補記（2026-10-22，14:18）

- **缺陷重現：** `app/ml.py::_metrics` 明確以 `predicted_sign == 0` 給 0.5 分；相反地，指南和結果卡曾說零報酬不計入。舊 monitor 斷言也檢查該錯誤文案。這是當前可重現的學習規格缺陷，非模型計算故障。
- **修正與功能：** 保留指標算法，將指南/UI/monitor 接受條件對齊中性零預測規則；驗證卡片依逐筆 OOF 實際值顯示上漲、下跌、持平計數與比例。沒有逐筆結果時提示重新訓練。
- **證據/限制：** Node 語法、Python AST 解析、靜態接受條件、`git diff --check` 通過。pytest 未安裝且 uv 離線快取無 pytest；不宣稱單測或完整 monitor 通過。13:53:44 舊檢查 14 PASS/3 WARN/0 FAIL，WARN 是使用者訓練繁忙和瀏覽器逾時，並非修改後證據。
- **下一 checkpoint：** 在 pytest/Chrome 可用環境驗證計分邊界和比例 UI 的桌面/手機分支，重跑安全 monitor。不得觸碰一次性鎖定測試或更新市場資料。


## 最新排程維護補記（2026-10-22，13:16）

- **審查資料缺陷：** 頂部舊補記聲稱 12:41、33/33；實際輸入 JSON 是 13:15:08、34/34 PASS，造成證據時間與項目數不一致。已據最新檔更新三份審查文件；當前沒有可獨立重現的產品錯誤。暖機起點程式修復已在現有 `build_samples()` 與測試中驗證，不重複改動。
- **學習功能：** 結果指標卡現說明方向準確率如何逐筆比較正負號，以及零預測依現行算法得半分；指南新增方向答對／答錯算例與漲跌比例限制。回歸監測增加 UI/指南接受斷言。
- **驗收與限制：** JS 語法、Python compile、diff whitespace 和方向指標單測 1 passed。13:16:43 改後 monitor 6 PASS／1 WARN／1 FAIL；資料切片、walk-forward 邊界、隔離 MLP/GRU smoke、pytest 14 passed／1 deselected、鎖定測試檔雜湊不變皆通過。首頁 HTTP 因環境 `Operation not permitted`、瀏覽器因 Chrome 程序受限，完整回歸未通過；smoke 不代表模型品質。
- **下一步：** 在允許本機連線及 Chrome 的環境重跑 monitor，觀察桌面／手機新增說明；接著以一般驗證資料示範方向指標和幅度校準的不同用途。未執行鎖定測試或資料刷新。

## 維護發現與修復（2026-10-22）

- **優先缺陷：** 最新回歸檢查 33/33 PASS，沒有檢查失敗。從現行 `app/data.py::build_samples()` 獨立重現特徵暖機起點錯誤：以 `key.rsplit("_", 1)[1]` 推導暖機長度，令 `return_1` 被當成首列有效於 1；然而第一個有效日報酬在第 1 列，回看 20 日最早 origin 應為 20，錯誤公式卻要求 origin 39。選擇多特徵時也可能額外丟失合法樣本。
- **修正：** 明確映射 return_1→1、return_5/volatility_5→5、return_20/volatility_20→20，再從最新有效列推導回看窗。加入參數化測試。
- **可觀察證據：** 聚焦 pytest `4 passed, 11 deselected`；起點檢查確認 `return_1`、`return_1 + volatility_5`、`return_1 + return_20` 分別為 20、24、39；程式編譯與 `git diff --check` 通過。沒有執行完整回歸、瀏覽器或訓練。
- **路線圖小步：** 學習指南加入 20,000 點在 +1% 簡單報酬下換算 20,200 點、+1% 對數報酬下換算約 20,201 點，明確註明換算並非模型價格輸出或成交價；monitor 新增文案接受檢查。指南接受條件通過。
- **下一 checkpoint：** 下次安全 monitor 驗證新檢查及桌面／手機，再以一般個股驗證輸出作讀圖學習。鎖定測試檔與市場資料均未觸碰；不依 smoke 結果宣稱模型品質。

## 排程維護紀錄（2026-10-22）

- 讀取最新監測資料後，未發現當前失敗：33/33 PASS。歷史頂部 CTA 假失敗已由現行 monitor 的 POST route 攔截與 payload 比對修復，故未重複改動。
- 本輪學習里程碑：`docs/learning-guide.md` 補上有號幅度偏差逐步算例，並在 `scripts/regression_monitor.py` 校準檢查加入指南算式、正負偏差和避免把零偏差等同準確的接受條件。
- 驗收：Node 語法、Python compile、文件接受檢查與 diff whitespace check 通過。尚無本輪完整瀏覽器／回歸證據。下一步在下次完整監測驗證新斷言，再使用一般個股 walk-forward 結果作教學讀圖；不執行鎖定測試、不推論模型品質。
> **交付對象**：供協同開發者 / 側邊 Codex Agent 進行直接修復與實作。  
> **測試時間**：2026-10-21  
> **測試環境**：本機服務 `http://127.0.0.1:8000/`、FastAPI 2.0.0、PyTorch 2.8.0、Python 3.9
> **專案路徑**：`taiex-neural-lab/`

## 2026-10-22 維護覆核（方向摘要缺失值）

- **現行缺陷與重現：** `web/app.js::directionMixSummary()` 對 `actual`、`predicted` 無條件套用 `Number()`；JavaScript 的 `Number(null) === 0`，使缺值配對錯算為持平／中性，污染比例摘要。
- **修正：** 先排除 null、undefined、空字串及非有限值；加入預測上漲和下跌各自的平均絕對報酬幅度（百分點）。監測器接受案例檢查缺值排除、2/1/1 方向組成及合成幅度，指南說明其解讀限制。
- **可見驗收：** `node --check web/app.js`、Python `compile()` 通過；隔離 Node 案例確認不完整配對不計入、上漲平均 1.500pp、下跌平均 1.000pp、空輸入不產生摘要。最新既有 monitor 15:42:46 為修改前 35/35，未作本輪回歸證據；完整 browser monitor／pytest 未執行。
- **狀態與下一 checkpoint：** 此為漲跌幅學習的小步，並非模型品質證據。下一步在不載入 holdout UI 的 browser fixture 驗收桌面／手機，再跑安全 monitor 確認 JSON 不含 `finalTest`。熱門股仍 10 檔；跨標的 OOF 教學未完成。未讀寫鎖定測試資料、未執行一次性測試、未刷新市場資料。

---

## 📌 實測確認的 5 大確定性缺陷 (Confirmed Bugs)

### Bug 1: 多模型訓練時基準比較表覆蓋問題 (Comparisons Overwrite)
* **問題檔案**：[`taiex-neural-lab/app/ml.py`](file:///Users/yinglin/orca/projects/ndhu%20ai%20class/taiex-neural-lab/app/ml.py#L279-L289)
* **實測重現**：
  呼叫 `/api/experiments` 並設定 `modelTypes: ['mlp', 'rnn']`。
  * 期望結果：`result['comparisons']` 應同時包含 MLP 與 RNN。
  * 實測結果：`result['comparisons']` 僅包含 `['歷史平均', '預測零報酬', 'Ridge 線性迴歸', 'Random Forest', 'RNN']`，前面的 MLP 被迴圈內的賦值覆蓋。
* **原因分析**：
  ```python
  # app/ml.py 第 279 行附近：
  for model_index, kind in enumerate(model_types):
      ...
      comparisons = [
          ("historical_mean", "歷史平均", np.asarray(all_mean)),
          ("naive", "預測零報酬", np.asarray(all_zero)),
          ("ridge", "Ridge 線性迴歸", np.asarray(all_ridge)),
          ("forest", "Random Forest", np.asarray(all_forest)),
          (kind, MODEL_NAMES[kind], np.asarray(all_predicted)),
      ]
      result["comparisons"] = [ ... ] # 每次迴圈直接重寫！
  ```
* **修復方式**：
  基準模型（歷史平均、Naive、Ridge、Random Forest）只需在最外層計算一次，並將所有訓練的神經網路追加進 `comparisons` 清單中。

---

### Bug 2: 前端 API 錯誤呈現 `[object Object]` (Pydantic 422 格式未處理)
* **問題檔案**：[`taiex-neural-lab/web/app.js`](file:///Users/yinglin/orca/projects/ndhu%20ai%20class/taiex-neural-lab/web/app.js#L12-L17)
* **實測重現**：
  若參數輸入不合法的範圍（例如 `lookback < 5` 或 `horizon = 10`），FastAPI 回傳 `422 Unprocessable Entity`，其 JSON 為：
  ```json
  {"detail":[{"loc":["body","lookback"],"msg":"Input should be greater than or equal to 5"}]}
  ```
  在 JavaScript 中：`new Error(payload.detail)` 會將 Array of Object 強制轉為字串，導致頁面彈出紅字：**`[object Object]`**。
* **修復方式**：
  修改 `app.js` 的 `api()` 函式：
  ```javascript
  let message = payload.detail;
  if (Array.isArray(message)) {
    message = message.map((d) => d.msg || JSON.stringify(d)).join('； ');
  } else if (typeof message === 'object' && message !== null) {
    message = JSON.stringify(message);
  }
  const error = new Error(message || `服務回應 ${response.status}`);
  ```

---

### Bug 3: 零報酬基準（Naive Baseline）的方向準確率恆為 0.0%
* **問題檔案**：[`taiex-neural-lab/app/ml.py`](file:///Users/yinglin/orca/projects/ndhu%20ai%20class/taiex-neural-lab/app/ml.py#L106)
* **實測結果**：
  實測 `m['zeroBaseline']['directionAccuracy']` 恆等於 `0.0`。
* **原因分析**：
  計算公式為：
  ```python
  direction = float(np.mean(np.sign(actual) == np.sign(predicted)))
  ```
  對於 Naive 基準，`predicted` 全為 0，`np.sign(0.0) == 0`。而實際報酬率 `actual` 絕大多數不為 0（不是正報酬就是負報酬，sign 為 +1 或 -1）。兩者相等的機率為 0，導致基準方向準確率固定顯示 `0.0%`，失去參考價值。
* **修復方式**：
  對於零預測或平盤預測，業界標準常以是否大於零（`predicted > 0` vs `actual > 0`）或將 0 視為未預測漲跌；若要保持連續符號，可定義：
  ```python
  direction = float(np.mean((actual >= 0) == (predicted >= 0)))
  ```
  或者當預測為 0 時給予中立隨機期望值 0.5。

---

### Bug 4: 前端 UI 模型選擇器只支援單選，無法進行「多網路架構對照」
* **問題檔案**：[`taiex-neural-lab/web/index.html`](file:///Users/yinglin/orca/projects/ndhu%20ai%20class/taiex-neural-lab/web/index.html#L60)、[`taiex-neural-lab/web/app.js`](file:///Users/yinglin/orca/projects/ndhu%20ai%20class/taiex-neural-lab/web/app.js#L46-L57)
* **實測結果**：
  HTML 目前僅有單一 `<select id="modelType">`，送出的 payload 為 `modelTypes: [currentModel()]`。
  使用者在瀏覽器上無法同時選取 MLP、RNN、LSTM、GRU 並排比較驗證指標，違背了專案文件中承諾的「同時比較多種網路架構」的特色。
* **建議改進**：
  可提供「多選 Checkbox」或「一鍵跑所有架構」按鈕，讓 `comparisons` 圖表能同時繪製所有 4 種網路與基準模型的比較柱狀圖。

---

### Bug 5: 參數控制介面未依模型類型（MLP vs 循環網路）動態隱藏/切換
* **問題檔案**：[`taiex-neural-lab/web/index.html`](file:///Users/yinglin/orca/projects/ndhu%20ai%20class/taiex-neural-lab/web/index.html#L44-L45)
* **實測結果**：
  * 選 **MLP** 時：畫面仍出現「循環層數」，修改完全無效。
  * 選 **RNN / LSTM / GRU** 時：畫面仍出現「MLP 隱藏層寬度（第 1/2/3 層）」，但內部僅使用第 1 層作為 `hidden_units`，第 2、3 層完全無效。
  * 單層循環網路時，頂部面板依然顯示 `Dropout 0.2`，但 PyTorch 單層 RNN 不支援 dropout（實際為 0.0）。
* **建議改進**：
  在 `renderArchitecture()` 時，若為 MLP 則顯示隱藏層 1~3 寬度；若為 RNN/LSTM/GRU 則隱藏 2、3 層輸入框，並將「第 1 層」更名為「隱狀態單元數 (Hidden Units)」。

---

### Bug 6: Uvicorn 開發重載監聽整個目錄，寫入資料或文件時會中斷進行中的訓練 (StatReload Crash)
* **問題檔案**：[`taiex-neural-lab/app/__main__.py`](file:///Users/yinglin/orca/projects/ndhu%20ai%20class/taiex-neural-lab/app/__main__.py#L7)
* **實測現象**：
  當背景正在執行驗證或鎖定測試時，只要 `data/` 下產生了狀態檔（如 `data/latest-validation-sequence-v1.json`、`taiex_close.csv`），或是在 `docs/` 編輯報告，Uvicorn 會偵測到檔案變更並立即觸發全伺服器重載（StatReload）。重載會清空記憶體中的 `jobs` 字典，並強制中止背景執行緒，導致前端突然收到 `404 找不到這個實驗工作`。
* **修復方式**：
  在 `app/__main__.py` 啟動 uvicorn 時指定監聽目錄，排除 `data/` 與 `docs/`：
  ```python
  uvicorn.run(
      "app.main:app",
      host="127.0.0.1",
      port=8000,
      reload=True,
      reload_dirs=["app", "web"],
      reload_excludes=["data/*", "docs/*", "*.csv", "*.json"]
  )
  ```

---

### Bug 7: 手機與窄螢幕（≤600px）下「取消訓練」按鈕被完全隱藏 (Uncancelable Job on Mobile)
* **問題檔案**：[`taiex-neural-lab/web/styles.css`](file:///Users/yinglin/orca/projects/ndhu%20ai%20class/taiex-neural-lab/web/styles.css#L54)
* **實測現象**：
  CSS 在 `@media(max-width:600px)` 規則中直接設定了 `.button-secondary{display:none}`。
  而頁面底部的「取消」按鈕 `<button id="cancelJob" class="button button-secondary">` 因此在手機或窄視窗下被強制隱藏。若使用者點擊訓練後需要等待數十個 Epoch，將完全沒有按鈕可以中止訓練。
* **修復方式**：
  不要在 `@media(max-width:600px)` 中隱藏 `.button-secondary`，改為響應式縮小 padding 或維持可點擊圖示按鈕。

---

### Bug 8: 進階設定面板缺乏點擊外部關閉（Click-Outside）機制
* **問題檔案**：[`taiex-neural-lab/web/app.js`](file:///Users/yinglin/orca/projects/ndhu%20ai%20class/taiex-neural-lab/web/app.js#L381)、[`taiex-neural-lab/web/index.html`](file:///Users/yinglin/orca/projects/ndhu%20ai%20class/taiex-neural-lab/web/index.html#L39)
* **實測現象**：
  點擊「☷ 進階設定」或頂部齒輪 `⚙` 打開面板後，點擊畫面其他空白處或圖表，面板不會自動收合，常會遮蔽下方的價格圖表與網路結構圖。
* **修復方式**：
  在 `init()` 中加入全域點擊事件：
  ```javascript
  document.addEventListener('click', (event) => {
    const menu = byId('advancedMenu');
    if (menu.open && !menu.contains(event.target) && !byId('settingsShortcut').contains(event.target)) {
      menu.open = false;
    }
  });
  ```

---

### Bug 9: 鎖定測試計算了預測時間序列（Predictions），但前端完全未渲染 (Dead Data)
**狀態（2026-10-22）：歷史項目已實作，且原建議不再適用。** 不得將鎖定觀測疊入一般走勢圖；日常 UI/monitor 必須保持 holdout 隔離。以下內容只保留作修復歷史。
* **問題檔案**：[`taiex-neural-lab/app/ml.py`](file:///Users/yinglin/orca/projects/ndhu%20ai%20class/taiex-neural-lab/app/ml.py#L340-L343)、[`taiex-neural-lab/web/app.js`](file:///Users/yinglin/orca/projects/ndhu%20ai%20class/taiex-neural-lab/web/app.js#L312-L317)
* **實測現象**：
  後端 `run_final_test` 在第 340 行精心抽取並計算了 100 筆測試集實際值與預測值 `predictions: [{"date": ..., "actual": ..., "predicted": ...}]`。
  但前端 `renderFinal()` 僅顯示一行文字（MAE/RMSE/R²），完全沒有把這 100 筆預測值畫在時間序列折線圖上或顯示殘差對照，浪費了後端的計算，也無法讓使用者視覺化看出模型在哪個時間段預測失準。
* **建議改進**：
  在 `renderFinal` 中將 `result.predictions` 繪製在 `#historyChart` 的測試集區間（以不同顏色虛線覆蓋），直觀展示實際收盤 vs 模型預測軌跡。

* **修復與回歸驗證（2026-10-21）**：已在鎖定測試結果區新增獨立的報酬率圖與抽樣表，兩條線分別代表實際報酬與預測報酬，不與收盤指數共用座標軸。Playwright 實測目前已儲存的鎖定測試有兩條曲線與 103 筆圖表資料列；排程檢查不會再次執行一次性測試。

---

### Bug 10: 特徵計算起始索引未考慮長窗口 lookback 造成無效迴圈 (Start Index Misalignment)
* **問題檔案**：[`taiex-neural-lab/app/data.py`](file:///Users/yinglin/orca/projects/ndhu%20ai%20class/taiex-neural-lab/app/data.py#L221)
* **實測現象**：
  當勾選 `volatility_20` 特徵時，該特徵在索引 $0 \le t < 20$ 時全為 NaN。而樣本的時間窗口需要往前看 `lookback` 天。
  若 `lookback = 20`，要使整個窗口皆為有限數值，第一個合法 origin 必須是 $20 + 20 - 1 = 39$。
  但第 221 行寫死：`start = max(20, lookback - 1) = 20`。
  導致迴圈從 $20$ 到 $38$ 的所有迭代全部因含有 NaN 被第 230 行的 `continue` 默默丟棄，白跑近 20 次無效切片。
* **修復方式**：
  動態計算所選特徵的最大滾動窗口：
  ```python
  max_feature_window = max([int(k.split("_")[1]) for k in selected_features if "_" in k] or [1])
  start = max_feature_window + lookback - 1
  ```

---

### Bug 11: 手機版時間序列圖與資料切分軌道發生碰撞重疊 (Phase Rail Overlap on Mobile)
* **檢驗來源**：[`artifacts/regression-monitor/latest-mobile.png`](artifacts/regression-monitor/latest-mobile.png)
* **問題檔案**：[`web/styles.css`](web/styles.css) 第 54 行 (`@media(max-width:600px)`)
* **實測現象**：
  在手機窄視窗（390px 寬度）下，由於 `.timeline-panel .chart-frame` 在部分樣式階層繼承了固定高度或缺少底部間距，`.phase-rail`（包含訓練集、驗證集、測試集的彩色文字方塊）被向上推擠，**直接重疊在收盤價折線圖的底部與 X 軸年份刻度（2010, 2013, 2016...）上方**，導致文字與圖表曲線互相打架、難以閱讀。
* **修復方式**：
  在 `@media (max-width: 600px)` 內，明確宣告 `.timeline-panel .chart-frame { height: auto; min-height: 0; }` 並設定 `.phase-rail { margin-top: 10px; }`。

---

### Bug 12: 基準比較圖於勾選多種網路時 X 軸標籤擁擠 (Comparison Labels Congestion)
* **問題檔案**：[`web/app.js`](web/app.js) `renderComparison()`
* **實測現象**：
  當使用者在進階設定勾選比較全部 4 種網路（MLP、RNN、LSTM、GRU）時，加上原有 4 個基準（歷史平均、Naive、Ridge、RF），長條圖群組將達到 8 組。在較窄螢幕下，X 軸標籤文字容易互相貼齊。
* **修復方式**：
  在 `renderComparison` 中縮減模型名稱長度（如 `Ridge`、`隨機森林`、`歷史均值`、`零報酬`），並在長條群組大於 5 組時將字級縮至 `9px`。

---

## 🛠️ 其他工程建議

1. **反向傳播教學示例統一與損失函數說明**：
   * `app/ml.py` 的 `numpy_mlp_trace()` 使用了 $L = \frac{1}{2}(\hat{y}-y)^2$ 以消去係數 2，而實際訓練模型使用的是 PyTorch 原生 `nn.MSELoss()`（未除以 2，梯度為 $2(\hat{y}-y)$）。建議在 UI 說明加註兩者差異，避免學生推導時困惑。

<!-- regression-monitor:latest:start -->
## 自動回歸監測（2026-10-29T12:59:40+08:00）

整體：**PASS**（PASS 43／WARN 0／FAIL 0）。每 30 分鐘本機執行；不更新外部資料、不執行鎖定測試。

### 新問題與待辦
- 無新增失敗或待辦。

### 來源檔變更
- `scripts/regression_monitor.py`, `tests/test_system.py`, `web/app.js`, `web/index.html`
- 差異／快照紀錄：`artifacts/regression-monitor/source-diff-latest.md`。

### 本輪摘要
- pytest：**PASS**，222 passed, 1 warning in 29.82s。API／非同步驗證測試使用隔離儲存，不會覆寫本機驗證結果。
- 訓練 smoke check：**SKIP**，例行維護不啟動訓練 smoke；本輪只檢查切片與 walk-forward 邊界
- 瀏覽器：桌面 PASS；手機 PASS。截圖：`artifacts/regression-monitor/latest-desktop.png`、`artifacts/regression-monitor/latest-mobile.png`。
- 設計稿：PASS；已擷取桌面與手機畫面；元件幾何數據與前次快照一致 像素差異僅供參考，資料與頁面狀態不同。
- 完整逐項結果：`artifacts/regression-monitor/latest-checks.json`。

<!-- regression-monitor:latest:end -->

## 2026-10-22 維護覆核與處理

### 最新回歸失敗：頂部訓練入口檢查器誤報

**重現依據：** `artifacts/regression-monitor/latest-checks.json` 的「頂部參數到訓練入口與歷程保存」為 FAIL。檢查器點擊 `#topTrain` 並要求 `#jobError` 包含 `monitor intercepted`，但其程式段未攔截 API 請求。現行 `web/app.js` 已將按鈕綁定至 `startJob(false)`，故要求的錯誤字串並非可靠的送出證據。

**修正：** `scripts/regression_monitor.py` 於測項掛上 `/api/experiments` route，記錄 POST 後立即 abort；與 `buildConfig()` 核對模型清單、特徵及回看長度，並確認取消後錯誤狀態出現。訓練不會真正開始。

**狀態：** 修正後於 2026-10-22 10:45 重跑完整監測，該測項 PASS；總計 30 項 PASS、0 WARN、0 FAIL，pytest 11 passed／1 deselected。結果見 `artifacts/regression-monitor/latest-checks.json`。

### 路線圖小步：近零預測校準圖的座標解讀

`web/app.js` 對校準圖使用涵蓋零點的座標範圍，當分組數值集中於零附近時，摘要附上範圍及座標解讀提示。此為驗證集描述介面，不代表模型校準品質或未來預測能力。下一步以合成負報酬、近零預測及小樣本情境做瀏覽器驗收，並補入學習指南。

**安全範圍：** 本輪未執行訓練或鎖定測試，未讀寫 `final-test-*.json`，亦未更新資料。

## 2026-10-22 11:00｜自動改後驗收結果

先前此紀錄提到完整瀏覽器回歸尚未完成；截至本段已由 LaunchAgent 實際完成整輪改前／改後驗收。第三次循環的預檢和 Codex 改動後巡檢均 exit 0，總計 30 項 PASS、0 WARN、0 FAIL，pytest 11 passed／1 deselected。巡檢包含校準高估方向、近零混合偏差、負值小樣本和合成示例展開；手機 390px 與桌面截圖均已產生。驗收資料：`artifacts/continuous-improvement/latest-cycle.json`、`artifacts/regression-monitor/latest-checks.json`、`artifacts/regression-monitor/latest-desktop.png`、`artifacts/regression-monitor/latest-mobile.png`。

此驗收只使用驗證結果或合成教學值；沒有執行鎖定測試、改訓練模型或刷新資料。後續仍需把「加權有號偏差」寫入學習指南，策略成交價格／時間假設仍未實作。

## 最新覆核（2026-10-22 11:06）

學習指南和報告模板現已加入校準分組、加權絕對差、有號偏差及限制。回歸範圍新增 10 檔本機股票的資料狀態／序列一致性檢查和台積電前端切換；10/10 資料可用、切換和切回均通過。完整回歸 **32 PASS、0 WARN、0 FAIL**，pytest **11 passed／1 deselected**，桌面與 390px 手機畫面通過。第一次增加校準區塊後的舊幾何基準曾報高度變化警告；基準更新後再次執行，警告消失，畫面截圖正常。

後續檢查點是以至少一檔個股完成一般驗證，觀察不同期間下校準摘要是否清楚。只執行監測器隔離的 1 epoch MLP／GRU 流程檢查；未訓練使用者設定的模型、未更新行情，也未執行或觸碰鎖定測試。

11:09 追加的全套回歸再次確認 32 項通過、0 警告、0 失敗；pytest 11 passed／1 deselected，版面幾何一致性警告已清除。11:11 又加入 390px 手機的校準示例檢查，確認可展開、SVG 可見且無水平溢出；全套更新為 33/33 PASS、0 WARN、0 FAIL，pytest 11 passed／1 deselected。

### 30 分鐘改進循環的驗證

2026-10-22 10:41 由 LaunchAgent 實際啟動一次完整流程。初次巡檢抓出上述監測器假性 FAIL；Codex 改正攔截器後，10:45 的完整巡檢已確認全部 30 項通過。為使後續排程不會只在改碼前測一次，`scripts/continuous_improvement.py` 已加入改碼後完整巡檢，並把前測、Codex 與後測退出碼分開記錄。排程週期為 1800 秒；遇到失敗會留在日誌和三份審查文件中，下一輪繼續處理。

## 2026-10-22 10:40｜學習功能新增與驗收

本輪沒有由回歸巡檢重現的程式失敗；依路線圖推進「預測漲跌幅是否有意義」的學習內容，新增驗證資料預測幅度校準圖。圖表從 walk-forward out-of-fold 預測形成最多 8 個等樣本分組，點位比較組平均預測與組平均實際報酬，並呈現理想校準線、樣本數、預測範圍和分組加權幅度差。只作驗證集描述，不用於選模或宣稱未來準確。

**驗收證據：** regression monitor 30/30 通過（0 WARN、0 FAIL）；校準圖渲染 8 個分組和理想線；桌面與 390px 手機巡檢無 JS 錯誤；pytest 11 passed／1 deselected；lock-state JSON 雜湊前後一致。來源：`artifacts/regression-monitor/latest-checks.json`。

**後續：** 另驗證小樣本及預測值高度集中於零時的圖表可讀性，並補充學習指南說明。尚未完成時序隔離的策略成交假設，不應將訊號描述為實際買賣績效。

## 2026-10-22｜排程維護：校準圖教學補充

**缺陷檢查：** 最新 regression-monitor JSON 為 30/30 PASS、0 WARN、0 FAIL，沒有可獨立重現的當前失敗。曾假設常數預測會令校準圖座標除零，但現有 extent 由預測與實際分組均值共同計算並加 padding，重現不成立；因此沒有宣稱修復程式缺陷。

**功能變更：** 學習中心新增第 6 步「預測幅度校準」，說明橫軸、縱軸、理想線與組均值偏差，並提醒驗證分組統計不保證未來表現。校準結果卡新增可展開的固定合成例子：預測 1.0%／實際 0.5% 為高估，預測 0.5%／實際 1.0% 為低估，明示與市場資料無關。檔案：`web/app.js`、`web/index.html`、`web/styles.css`。

**接受證據：** `node --check web/app.js`、`git diff --check` 與隔離靜態接受檢查通過，確認 SVG 有兩個標記點、軸標籤、合成資料揭露，導學含解讀限制。嘗試使用現有 Chrome tab 做實際頁面檢視時，Cua 工具拒絕綁定該 tab，故瀏覽器視覺驗收尚未完成。

**安全／下一步：** 未執行訓練、鎖定測試或資料刷新；沒有讀寫任何 `final-test-*.json`。下一檢查點是重跑安全回歸監測，桌面及 390px 手機展開範例確認可讀，並用近零、負報酬及兩筆資料狀況驗證校準圖座標和摘要。

## 2026-10-22｜維護：校準偏差方向摘要

**缺陷檢查：** 最新巡檢 JSON 顯示 30/30 PASS，沒有當前監測失敗。直接檢查 `renderCalibration()` 發現摘要只計算 `abs(actual - predicted)` 的加權幅度差；高估和低估情境會顯示同一絕對數字，不能教學解讀偏差方向。

**實際變更：** `web/app.js` 保留絕對加權差並新增分組加權有號偏差，明示整體高估、低估或接近零及其百分點值。`scripts/regression_monitor.py` 加上低樣本近零混合偏差和同方向高估的瀏覽器斷言。

**驗收證據：** 隔離 Node VM 執行渲染函式，確認 1.0% 預測對 0.5% 實際顯示整體高估 −0.500 個百分點；近零混合偏差顯示接近零，SVG 不含 NaN/Infinity。`node --check web/app.js`、Python `compile()`、`git diff --check` 通過。

**限制與下一步：** 嘗試完整監測時本機 HTTP server socket bind 遭 PermissionError，故未得到本輪瀏覽器、pytest 或全套監測結果。最新 JSON 的 30/30 PASS 是修改前證據。未執行訓練、資料更新、鎖定測試，也未讀寫 `final-test-*.json`。下一 checkpoint：在允許本機服務的環境重跑 monitor，觀察桌面／手機畫面與新增偏差方向案例，之後補學習中心的有號偏差說明。
## 2026-10-22：跨標的 browser fixture 無法解析

- **狀態：已修正，待完整瀏覽器驗收。** 最新 AGY 報告 `artifacts/regression-monitor/latest-checks.json` 時間 `2026-10-22T21:34:27+08:00` 為 WARN。可重現原因不是應用 UI：monitor 在 `savedValidationSummary` 的 `modelBetter` JavaScript fixture 多一個右大括號，Playwright `Page.evaluate` 因此報 `SyntaxError: Unexpected token '}'`。
- **變更：** 刪除該多餘大括號，保留 MAE 差值為正時的檢查；並在學習指南加入按組筆數加權有號校準偏差的兩組手算例。
- **證據：** monitor Python AST 解析通過，AST 抽出的 fixture 經 `node --check` 通過；`node --check web/app.js` 與 `git diff --check` 通過。尚未重跑 Playwright monitor，不能聲稱 browser 渲染或接受條件通過。pytest 與隔離 smoke 的 PASS 只屬於起始 JSON 所記錄的改前執行。
- **下一步：** 在可啟動本機 Chrome 的環境重跑安全 monitor，驗收跨標的 saved-summary fixture、桌面／手機畫面與其他回歸。保持 locked holdout 與 `final-test-*.json` 隔離；不做 final test、不刷新行情。短訓練 smoke 不代表模型品質。

## 2026-10-23｜Playground 式逐筆前向探查

- **修改：** MLP 驗證結果新增第一個 walk-forward 折樣本的標準化輸入、各 ReLU 隱藏層 activation、PyTorch 線性層權重與輸出。前端將 activation 明度及權重正負／相對量級映射到節點與連線；控制列調整為說明在上、播放按鈕在下。不同設定會將既有 trace 標為過期。
- **已確認：** 本機 Chrome `127.0.0.1:8000/#network` 能載入新模型區與空狀態；第一版的窄文案問題經截圖發現並修正。JS 語法、Python compile、diff whitespace 通過。
- **限制：** 本輪沒有跑正式訓練，故尚未在 UI 看見真實 activation/權重呈現；RNN/LSTM/GRU 尚無逐神經元 trace。未執行 AGY 完整巡檢、鎖定測試或資料更新；不能聲稱訓練後視覺或全站回歸通過。

## 2026-10-23｜Playground 工作台整體重構

- 對照 TensorFlow Playground 後，將模型區由窄幅架構卡改為同一工作台：特徵側欄、可調 1–4 層網路、置頂傳播控制、大型網路畫布、訓練後前向數值區。
- 網路節點改為圓形與淺色畫布；權重採正藍／負橘，線寬映射權重幅度。未訓練時清楚標為架構預覽；真實數值仍只在 MLP 訓練完成後呈現。
- MLP 隱藏層可於工作台增減 1–4 層，設定寫入草稿並由既有訓練 API 送出；RNN/LSTM/GRU 控制層數時使用相同步進器。保存/回復設定時保留模型類型與層數。
- 輸入張量為回看天數 × 特徵數；圖中為便於讀取而抽樣顯示輸入節點，已加註避免把節點數誤認完整張量維度。
- 手機版錨點增加頂部導覽偏移，避免直接跳到工作台時標題被導覽列遮住。
- 手動瀏覽確認：1440px 與 390px 版面可渲染，畫面寬度未超出 viewport；層數按鈕增至 4 再減回 3 正常，瀏覽器未回報 JavaScript page error。未執行自動化測試。
- 邊界：此為金融迴歸專題的 Playground 式工作台，非逐像素複製原站；傳播按鈕是前向示範，真正的 walk-forward 訓練仍由「訓練模型」執行。

### 2026-10-23 版面修正追記

- 修正：模型區特徵容器缺少關閉標籤，造成動畫、網路圖與數值輸出全被瀏覽器巢狀到特徵欄。現在四個工作區區塊為同層網格項目。
- 修正：響應式斷點下的主欄與模型欄寬互相衝突；1440px 以上採資料圖/工作區左右並列，較窄桌機與平板改上下排列，390px 單欄。行動版 document scrollWidth=390。
- 驗收：手動呈現 1440px/1024px/390px，層數增加與減少可操作，頁面無 JS error。尚未以訓練後權重資料驗收 trace 欄的長數值排列。

## 2026-10-23｜人工視覺巡檢更新：神經網路畫布

- 狀態：已處理本次參考圖視覺差異。架構圖畫布改為近黑底，空心高對比節點，預覽連線採青藍/珊瑚色，動畫流動採柔金色；真實訓練權重 inline 樣式保有更高優先級。
- 防誤讀：圖例補充未訓練顏色為示意；只有 MLP 訓練後顯示抽樣權重。
- 驗證證據：Playwright 實際載入 `http://127.0.0.1:8000/#network`；1440px/390px 均無水平溢位，90 條連線生成，播放中觀察到 9 條流動高亮，page errors 為 0；computed style 為暗色畫布、`#55b8d8` 青藍線、`#ef8c72` 珊瑚線與深色空心節點。`node --check web/app.js`、`git diff --check` 通過。
- 範圍：僅重新美編神經網路架構圖；其他金融結果圖未套黑底，以保留數據圖的原語意色。未跑訓練、鎖定測試或行情更新。
# 維護覆核（2026-10-23）

- **起始證據：** `artifacts/regression-monitor/latest-checks.json` 為 `2026-10-23T03:34:00+08:00`、overall FAIL。前向傳播公式與校準 UI direction 兩項 FAIL；視覺稿比對另有 WARN。
- **獨立重現／修正：** 動畫 monitor 檢查隱藏層公式時，`renderNetworkStage()` 顯示求和展開式但省略 `z=Wa+b`。已在 `web/app.js` 同時顯示矩陣式、展開式和 ReLU。路線圖新增的神經元算例見 `docs/learning-guide.md`，只用合成數值，不代表模型表現。
- **驗收證據：** `node --check web/app.js`、monitor AST、4 項隔離接受斷言、pytest 安全子集（14 passed／1 deselected）與 `git diff --check` 通過。未執行完整 monitor，起始 JSON 是改前狀態，不能算 browser 修復驗收。未訓練／更新資料／執行 final test。
- **剩餘與下一步：** 校準 UI direction 接受失敗仍未修；檢查實際 tooltip 是否需補上逐筆計分與零預測規則，更新對應指南與 monitor。接著於不顯示任何鎖定輸出的安全瀏覽器環境驗收前向公式和方向說明，再更新完整回歸結果。
# 2026-10-23：例行資料狀態 API 暴露鎖定測試結果

- **嚴重度：** 高，破壞一次性 holdout 隔離邊界。
- **起始證據：** `latest-checks.json` 17:18:46 為 WARN；一般 status 檢查 PASS，但獨立靜態追蹤可見 `app.data.data_status()` 呼叫 `read_final_state()` 並回傳 `finalTest`。`/api/data/status` 對 TAIEX 使用此函式；首頁 `renderStatus()` 將結果放入 `state.finalState`，初始化的鎖定狀態 render 可呼叫 `renderFinal()` 呈現 saved result 和預測列。Monitor 在 response 收到後才移除欄位，未隔離 API／瀏覽器消費路徑。
- **修正：** 移除一般 `data_status()` 的 final-state 讀取；新增只回傳狀態及 mismatch metadata 的 `/api/data/lock-status`。首頁一般資料初始化不再接受 final payload，改由 metadata endpoint 更新鎖定標籤。Monitor 和系統測試加入 payload schema 接受條件。
- **驗證：** 聚焦 API test 1 passed，明確檢查普通 status 不含 `finalTest`、lock-status 欄位限於 metadata；JS syntax、Python AST、教學／隔離接受斷言、`git diff --check` PASS。未重跑完整 monitor，因起始報告顯示使用者訓練 active。
- **保護邊界：** 未讀取、寫入或渲染 locked holdout；未跑 final test、刷新市場資料或宣稱模型品質。
- **後續：** active user job 結束後重跑 browser monitor，核對 metadata 狀態 UI 和桌面／390px；監測需將普通 status schema 與 lock-status metadata 都列入檢查。

## 排程維護覆核（2026-10-23，方向與幅度分開判讀）

- **缺陷覆核：** 最新 AGY `latest-checks.json` 為 19:10:17+08:00，39 項 PASS、無 WARN／FAIL。檢視目前方向摘要與診斷路徑，未找到可獨立重現的高優先缺陷；沒有將既有通過項目包裝成缺陷修復。
- **路線圖實作：** 導學新增第 7 步，示範方向相同但幅度高估 0.8pp，以及方向相反但絕對誤差 0.2pp。`docs/learning-guide.md` 說明方向指標、MAE 與校準圖各自回答的問題；`web/index.html` 初始步數同步為 7。
- **改後接受證據：** `node --check web/app.js`、monitor Python AST、隔離接受斷言（步驟數、算例數字及合成限制）與 `git diff --check` 通過。未跑改後完整 browser monitor；19:10 JSON 是改前證據。
- **剩餘／下一 checkpoint：** 執行安全 browser monitor，驗收步進／返回／重啟以及桌面／390px 呈現；之後以一般 OOF 結果做跨標的讀圖。未讀寫 `final-test-*.json` 或 locked holdout，未跑 final test、未更新行情或訓練，無模型品質主張。

## 2026-10-23｜AGY FAIL：訓練完成動畫穩定與 Loss 教學

- **起始結果：** 最新 AGY JSON 21:36:07+08:00 overall FAIL。訓練動畫「完成抵達輸出並停止」為 False；Loss hover tooltip 未顯示，但左右鍵定位 Epoch 2 成功。
- **缺陷與修正：** `web/app.js` 完成輸出狀態原只保留 2.6 秒，重複 completed 輪詢會反覆進入停止處理並重啟重置時序。延長可見狀態至 5 秒，且輸出階段重複 completed 輪詢保留完成文案。隔離 source assertion 覆蓋完成分支及延遲值。browser 重驗尚未執行，不能稱為修復已由瀏覽器驗收。
- **路線圖增量：** `docs/learning-guide.md` 新增訓練／驗證 Loss 讀圖教學，並在 monitor 加入對應指南接受條件。內容說明對數刻度、Epoch hover／方向鍵及跨折和基準解讀限制。
- **證據：** `node --check web/app.js`、monitor AST、5 項聚焦接受斷言、`git diff --check` PASS。完整 monitor 未跑，因現行 browser check 會點 `#runFinal`，可能啟動禁用的一次性最終測試。Loss hover FAIL 尚待確認；應檢查安全 monitor fixture 的游標座標是否落在有效繪圖區，並另以一般圖表 fixture 重驗。
- **下一 checkpoint／界線：** 移除 monitor 中觸發 final test 的互動後再執行安全 browser 驗收，確認動畫停留、Loss hover、桌面／390px。未讀寫 locked holdout 或 `final-test-*.json`，未跑 final test、未刷新行情或訓練，無模型品質主張。
## 2026-10-24：Regression monitor 樣本時間與比較列契約過期

- **重現：** 最新 AGY 23:50:23+08:00 樣本檢查回報 FAIL，detail 同時顯示 origin=39 符合期望。直接使用本機一般資料切片可見 monitor 條件錯把 target 要求為 origin+1；正確資料契約為 entry=origin+1、target=entry+horizon。另一 FAIL 將比較清單和模型種類固定寫成舊契約，現行驗證結果由四個基準列加上本次請求模型組成。
- **修正：** monitor 依 entry/horizon 驗收索引，基準列要求固定且後續比較列須對齊模型結果；逐折樣本與殘差一致性檢查保留。
- **路線圖：** 學習指南加入時間索引簡式與 h=1 時 target=t+2 解釋，作為可見的監督標籤學習小步。
- **證據：** 切片重現 4041 樣本、origin=39；直接檢查 entry/target 公式通過。`pytest -q -k 'not public_api_and_async_validation_job'`: 51 passed, 1 deselected；`node --check web/app.js`、`git diff --check` 通過。完整 monitor/browser 未跑；舊 JSON 是改前狀態，首頁 connection refused。未以訓練 smoke 推論品質。
- **後續：** 用不觸及 locked holdout 的 fixture 驗收新比較契約；確認安全 monitor 不會執行 final-test 控制後，再做桌面／390px browser 驗收。未讀寫受保護 final-test 資料、未跑 final test、未刷新行情、未部署發布。
## 排程維護進度（2026-10-24，學習率互動算式）

- **最高優先覆核：** 最新 JSON 00:24:27+08:00 的唯一 FAIL 是首頁 Connection refused，browser 同因 WARN；切片、比較契約、51 passed／1 deselected、隔離檢查通過。monitor `check_http()` 不啟動服務，8000 未監聽，屬環境狀態，未發現可重現程式缺陷。
- **改動與學習增量：** 導學第九步新增可調 W、梯度及 η 的單步算式，限 η∈[0,10]，無效數值有提示；指南同步說明合成值限制。monitor 新增 1.95／1.75 與元件存在／可見驗收。
- **驗證與後續：** 聚焦驗收待回填；完整 monitor 不執行以避免訓練 smoke，且服務拒絕連線，因此不宣稱 browser 驗收。下一 checkpoint 是無服務計算檢查、安全 pytest 子集及可用瀏覽器時桌面／390px 驗收。未接觸 `final-test-*.json`、locked holdout、行情更新或外部發布。

## 自動回歸監測覆核（2026-10-24，02:45 AGY）

- 最新檢查為 6 PASS／1 WARN／1 FAIL。FAIL 是首頁 `127.0.0.1:8000` Connection refused，browser 因相同服務不可達而 WARN。現行 `check_http()` 只向設定 URL 發請求，不負責啟動服務；未重現應用程式缺陷，因此不把服務未監聽寫成程式修復。
- 神經網路工作台本輪有界進展：動畫 monitor 新增「暫停後繼續會前進」及「重播會回輸入層」兩個瀏覽器接受條件。接受證據為 JS 語法、monitor AST、狀態控制器源碼斷言及 diff whitespace 通過。未執行改後完整 browser monitor，02:45 JSON 為改前證據。
- 下一 checkpoint：安全 browser monitor 可用後實際驗收續播／重播與桌面、390px；跨標的 OOF 解讀待同協定一般驗證輸出。未觸碰 `final-test-*.json`／locked holdout、未跑一次性測試或行情更新，無模型品質主張。

## 排程維護進度（2026-10-24，區間不確定性導學）

- **改前缺陷：** AGY 04:30:05+08:00 整體 WARN。browser sequence 在重播後立即點擊仍 disabled 的 pause 按鈕而 timeout。當前 replay 明確回到輸入層；播放首次 timer callback 後才啟用 pause。這是可重現的監測器等待時序問題。monitor 已在第二次 pause click 前等待按鈕啟用。改前 JSON 保留，不宣稱新瀏覽器已通過。
- **路線圖增量：** 學習中心新增第 11 步「單一預測值與預測區間」，以純合成中心 +0.6%、尺度 0.4 個百分點展示 +0.20% 至 +1.00%；改尺度即時計算，拒絕空白、負值、溢位。指南區分算術示意和模型估計區間，並記錄未來需用一般驗證資料檢查逐筆覆蓋率、區間寬度、資料時序隔離及跨期間穩定性。
- **驗收狀態：** monitor 已核對第 11 步、計算結果、尺度變更、無效輸入及指南限制；完整 browser monitor 尚未執行。聚焦 `node --check web/app.js`、兩個 Python AST、隔離算式測試及 `git diff --check` 通過；安全 pytest 54 passed／1 deselected。曾因 harness ROOT／Path 名稱錯誤兩度失敗，修正後重跑成功。不能以 smoke 或合成例子宣稱模型品質。
- **下一步與安全：** 完成聚焦驗證；安全 browser monitor 前需排除其中會點擊鎖定測試確認 UI 的步驟，之後驗收 desktop／390px 和 replay timing。未讀寫／消耗 locked holdout 或 `final-test-*.json`，未執行 final test、更新資料、部署或發布。

## 排程維護進度（2026-10-24，截圖等待與預測幅度教學）

- **改前 AGY：** `latest-checks.json` 06:19:46+08:00 為 18 PASS／1 WARN。WARN 是 Playwright 1500ms wait timeout。現行 desktop monitor 在切換台積電並返回 TAIEX 後未等待圖表 SVG 路徑完成，截圖可能讀取重繪中的頁面狀態。
- **修正及增量：** 在 monitor 加入圖表 path 可用等待。學習中心增為 13 步；第 10 步可調參考點位、預測報酬與報酬類型，顯示上漲／下跌／持平、絕對幅度及點位算術；指南說明這是合成換算。
- **驗證：** JS syntax、monitor AST／接受條件、6 項算式與邊界、pytest 54 passed／1 deselected、`git diff --check` PASS。完整 monitor 未執行；改前 JSON 不作改後視覺證據。
- **待辦：** 安全 browser-only 驗收第 10 步桌面與 390px、確認截圖時序修正。未讀寫或消耗 locked holdout／`final-test-*.json`、未跑 final test、更新行情或部署；不主張模型品質。
## 最新 AGY 維護覆核（2026-10-24 06:55:33+08:00；改後監測 06:57:02）

- **改前報告：** `artifacts/regression-monitor/latest-checks.json` overall WARN，16 項 PASS、1 項 WARN、0 FAIL。唯一 WARN 是 Playwright `wait_for_function` 逾時 8000ms。先前已修正歷程套用設定等待及 monitor callback 順序；本次檢視最新監測程式未找到可在當前環境獨立重現的產品程式錯誤。
- **改後重跑：** `python3 scripts/regression_monitor.py` 收尾於 06:57:02，首頁 HTTP 因 sandbox `Operation not permitted` FAIL，Playwright Chrome 啟動為 `TargetClosedError` WARN，故無法重現原 8000ms predicate timeout，也無改後截圖驗收。walk-forward 切片與邊界、隔離 1-epoch 訓練 smoke、pytest 54 passed／1 deselected、鎖定測試隔離均 PASS。這些 smoke 僅證明路徑可跑，不代表模型品質。
- **最高優先缺陷結論：** 原 browser 等待 WARN 尚無改後重現；現有 FAIL/WARN 是環境拒絕本機 socket／Chrome 啟動，未把它們冒稱為應用修復，也沒有弱化檢查。
- **本輪實作：** 導學增至 14 步，第 13 步用 `ŷ=ReLU(z)`、`L=(ŷ−1)²` 說明鏈鎖律：z=2 時局部梯度 2；z=−2 時梯度 0。補充 ReLU 零點不可微的次梯度慣例和算例限制。更新首頁初始進度、學習指南及 browser monitor 接受條件。
- **驗收證據：** `node --check web/app.js`、monitor AST、lesson contract（14 步與 UI 計數、monitor 第 13 步內容條件）、獨立梯度算式、pytest（54 passed／1 deselected）、`git diff --check` 通過。Browser 實際畫面待可用環境驗收。
- **下一 checkpoint／安全狀態：** 使用不啟動 final-test UI 的 browser-only 檢查，驗收第 13 步和桌面／390px；再用一致協定的一般 walk-forward 驗證輸出教跨標的方向／幅度。熱門股保持已知本機 10/10，未擴充未授權來源。本輪未讀寫或消耗 `final-test-*.json`／locked holdout，未執行一次性 final test、下載或刷新行情、部署或發布。
# AGY 維護覆核（2026-10-24 09:17:47+08:00；polyline timeout 修復）

- **改前證據與重現：** `artifacts/regression-monitor/latest-checks.json` 顯示 browser 8000ms timeout WARN，其餘檢查 PASS。`web/app.js` 以 `<polyline class="price-path" points="${xs}"/>` 繪圖；monitor `scripts/regression_monitor.py` 卻在切回 TAIEX 後等待 `.price-path` 的 `d` 屬性。SVG polyline 不提供此屬性，等待永不成立。
- **修正：** monitor 改等待該 polyline 的 `points` 非空，與 DOM renderer 一致。
- **同輪可見進展：** 導學新增第 16 步單一神經元前向傳播互動，計算 z=wx+b 與 ReLU 輸出；首頁、指南及 monitor 接受條件同步。
- **證據與限制：** JS 語法、Python AST、selector 靜態契約、提取實際計算函式驗證正負輸入／空白／溢位、安全 pytest 54 passed／1 deselected、diff check 通過。Browser 改後未完成：Playwright Chrome 啟動以 `TargetClosedError` 結束；不可宣稱 timeout 已由瀏覽器實測排除。原 JSON 留作改前結果。
- **下一 checkpoint：** 在支援 Playwright Chrome 的環境執行安全 browser monitor，核對 TAIEX polyline 重繪等待、第 16 步和桌面／390px。未讀寫或消耗 locked holdout／`final-test-*.json`，未執行 final test、行情刷新、部署或發布；無模型品質主張。
# 排程維護更新（2026-10-24，多輸入神經元與 replay 接受條件）

- **AGY 起始結果／缺陷：** `latest-checks.json` 09:53:37+08:00 記錄 17 PASS／1 WARN。WARN 是 browser `wait_for_function` 1500ms timeout，沒有 selector／stack，根因未定。獨立重現另一項 monitor 時序缺陷：產品 replay 將網路重置到輸入層並保持暫停，原接受步驟卻沒有呼叫播放就等待 pause control 啟用，條件不能成立。
- **精確修正：** `scripts/regression_monitor.py` 在等待前明確點播放，再等待 pause 啟用，點擊後驗證狀態含「已暫停」。不宣稱此修正必然消除未定位的 AGY WARN。
- **有界使用者功能：** 課程新增第 17 步「多輸入神經元」互動，計算 `z=w₁x₁+w₂x₂+b` 及 `ReLU(z)`；預設得 0.8，另一案例負 z 輸出 0，並拒絕空值。同步 `web/index.html`、`docs/learning-guide.md` 及 monitor 接受條件。這是可觀察數學教學，不是模型訓練或品質證據。
- **改後驗收／下一步：** `node --check web/app.js`、monitor/test AST、實際函式正／負／空值／溢位案例、lesson contract pytest（1 passed／31 deselected）及 diff check 通過。完整 monitor 不執行，避免其訓練 smoke；改前 JSON 不算改後 browser 驗收。下一 checkpoint 是 browser-only 驗收 pause 流程、第 17 步桌面／390px，並為剩餘 1500ms wait 取得定位堆疊。未讀寫或消耗 holdout／`final-test-*.json`、未跑一次性 final test、行情刷新、部署或發布。

## 2026-10-24 維護覆核與進展

- 10:29:58+08:00 AGY 結果 17 PASS／1 WARN；唯一 WARN 為 Playwright 2500ms timeout，沒有 selector／stack。此前 `.price-path` 的錯誤 `d` 等待已改成非空 `points`。當前資料不足以獨立重現本次 WARN 根因，故保留為待查。
- 已把兩輸入神經元導學擴充為可調目標 y、ReLU 平方損失及 backprop 權重／偏置梯度，並更新指南和 monitor acceptance。
- 證據：JS syntax、monitor AST、實際計算五案例、安全 pytest 55 passed／1 deselected、diff check 通過。改後 browser 未執行；不聲稱畫面驗收或模型品質。
- 下一 checkpoint：安全 browser 驗收步驟和桌面／390px，並取得等待 timeout 的 selector／stack；OOF 跨標的及授權熱門股來源仍待處理。
## 2026-10-24 maintenance: stale lesson progress acceptance contract

- **Finding:** The monitor expected lesson 15 to show `第 15 / 17 步`, while the current lesson catalog contained 18 entries. This was a concrete impossible browser acceptance predicate, independently confirmed from the current monitor and catalog. The current AGY browser timeout remains unlocalized because its detail gives no selector or traceback.
- **Fix:** Updated lesson progress checks to the current 19-step catalog and added a monitor assertion for the new mini-batch gradient lesson. The 2500 ms timeout was not attributed to this mismatch.
- **Evidence:** JS syntax and monitor/test AST parse passed; lesson catalog contains 19 entries and the expected arithmetic example; focused pytest `2 passed, 31 deselected`. The pre-change latest JSON is unchanged, and there is no post-change browser run.
- **Next checkpoint:** Browser-only verification of lesson 19 and desktop/390px; record the outstanding timeout locator/stack. No model-quality inference from these checks.
## 2026-10-24：AGY 截圖逾時覆核與小批次互動

- **覆核結果：** 最新 AGY（12:13:56+08:00）因 Playwright 實際截圖 2500ms timeout 為 FAIL。檢查目前 `scripts/regression_monitor.py`，browser 例外已回報 FAIL，overall 聚合也保留 FAIL；可見結果未獨立重現程式缺陷。因此不把此環境／瀏覽器逾時記成程式修補，原 JSON 不變。下一次應取得 Playwright locator／stack 以定位 timeout。
- **可見功能變更：** 導學第 19 步新增兩筆梯度可調互動，先取平均後只更新一次權重。合成預設 `w=2`、`g₁=−2`、`g₂=4`、`η=0.1` 得平均梯度 1、更新後權重 1.9；不代表實際訓練或模型品質。
- **驗證：** JS syntax、Python AST、有效與無效輸入算例及聚焦 pytest `2 passed, 31 deselected` 通過，`git diff --check` 通過。未做改後 browser/桌面/390px 驗收。
- **下一步：** 可用本機服務及 Chrome 時驗收第 19 步與桌面／390px，收集 timeout locator／stack。熱門股仍沿用本機 10/10；新增覆蓋需授權資料來源。跨標的方向／幅度需一致協定的一般 OOF 輸出。

## 排程維護進度（2026-10-24，批次梯度步驟可見性與比較）

- **改前 AGY／獨立重現：** `latest-checks.json` 時間 12:49:03+08:00，整體 FAIL；Playwright `wait_for_function` 2500ms timeout 是唯一 FAIL，摘要沒有定位資訊。另由現行 `renderLesson()` 獨立重現產品缺陷：DOM 已有第 19 步 `batchGradientExercise`，但渲染函式沒有切換其 `hidden` 狀態，因此使用者到最後一步仍看不到互動。
- **精確修正：** 第 19 步現在解除批次梯度互動的隱藏並即時渲染。monitor 的 browser 例外 detail 加入 traceback，讓下一次 Playwright timeout 能定位實際等待點；既有改前 JSON 未改寫。
- **路線圖增量：** 第 19 步在可編輯兩筆梯度、權重與學習率之外，並列批次平均後更新一次，以及套用同一組固定梯度的逐筆更新結果。預設 `w=2,g₁=−2,g₂=4,η=0.1` 得批次 `1.9000`、逐筆 `1.8000`。說明限定為固定梯度合成示例；真實逐筆訓練會重新計算梯度。
- **接受證據：** `node --check web/app.js`、monitor AST、隔離實際 renderer 輸出（1.0000／1.9000／1.8000）、safe pytest `56 passed, 1 deselected` 與 `git diff --check` 通過。browser monitor 未執行；沒有改後桌面／390px 證據，12:49 JSON 仍是舊結果。無模型品質主張。
- **剩餘／下一 checkpoint：** 在安全 browser-only 環境驗收 19/19 可見、輸入更新、空值提示及桌面／390px；browser 重跑時取得完整 traceback 定位 2500ms wait。熱門股沿用本機 10/10，擴充需授權資料來源；跨標的方向／幅度比較仍待相同協定的一般 OOF。未讀寫或消耗 locked holdout／`final-test-*.json`，未執行一次性 final test、行情刷新、部署發布或訓練。
## 2026-10-24 scheduled maintenance: monitor string API mismatch

- **Finding:** The latest AGY record (13:57:58+08:00) reports one browser-check FAIL. Current source independently confirms the traceback: `page.locator(...).inner_text()` returns a Python `str`, but line 455 called `.includes("已暫停")`, a JavaScript method. This deterministically raises `AttributeError` and aborts the browser check.
- **Fix:** Use Python containment (`"已暫停" in status_text`). Kept the JSON as historical pre-fix evidence; did not run the full monitor.
- **Verification:** Static source check confirms no `inner_text().includes` remains; Python AST and focused pytest passed (`2 passed, 31 deselected`). Browser confirmation remains pending.
- **Roadmap progress:** Lesson 20 now has an interactive synthetic momentum update with five editable values, validation, and visible velocity/weight output. Default output is velocity 1.45 and weight 1.855. JS syntax and isolated calculator checks passed; no quality claim.
- **Next step:** Run safe browser-only lesson 20 and desktop/390px acceptance when browser environment is available. Do not use locked holdouts or final-test artifacts.
## 2026-10-24 15:43 AGY：手機換算器檢查選錯課程

- **重現：** `latest-checks.json` traceback 指向 monitor 對 `#returnConversionExercise` 呼叫 `scroll_into_view_if_needed()`，元素不可見。現行 renderer 僅在 `lessonIndex === 7` 顯示換算器；monitor 卻先設 `lessonIndex=LESSONS.length-1`，所以隨課程成長必然選到別步。
- **修復：** 手機視覺檢查先選 index 7，再檢查欄位堆疊、觸控尺寸、固定列遮擋與水平溢位。保留 AGY JSON 作為改前紀錄；未執行改後 browser monitor。
- **旁支學習進度：** 新增可調輸入特徵數與神經元數的可見矩陣維度練習，預設 3 輸入／2 神經元 → W 為 2×3、輸出 2 維；5／4 → W 為 4×5、輸出 4 維，無效整數拒絕。聚焦 acceptance 2 passed；不代表模型品質。
- **後續：** 其餘 AGY failure 中仍有舊 lesson 步數 predicate，逐項對照實際課程並修正；再用不含訓練及 locked UI 的 browser-only 驗收。此輪未讀寫／消耗 locked holdout 或 `final-test-*.json`，未跑一次性 final test、更新行情、訓練、部署或發布。
## 2026-10-24 16:20 AGY: MLP dimension teaching contract mismatch

- **Reproduction:** Latest AGY JSON reports `MLP 矩陣維度教學=False` in both forward-animation and model-controls checks. `renderNetworkStage()` showed “輸出為 2 維”, while browser acceptance searches for “W a 的結果為 2 維”. The current app showed the intended concept but failed the exact visible-content contract.
- **Fix:** The inspector now renders the aligned shape chain `a∈ℝ³`, `W∈ℝ²ˣ³`, `Wa∈ℝ²`, and the accepted “W a 的結果為 2 維” wording. Updated the contract test to assert rendered notation.
- **Verification:** `node --check web/app.js`, Python AST parse, focused pytest `1 passed`, and `git diff --check` passed. Initial pytest revealed its stale phrase expectation; corrected and reran. Browser visual acceptance remains pending.
- **Roadmap:** Added an explicit input-matrix-output shape explanation linking the existing dimension practice to MLP forward propagation. Next reconcile other stale 19-step checks against the 20-step lesson catalog and run safe browser-only desktop/390px acceptance. No locked holdout/final-test access or quality claim.
## 排程維護更新（2026-10-24，AGY radio 可見性逾時與維度小測）

- **改前結果／缺陷：** 最新起始 AGY `latest-checks.json` 17:32:06+08:00 為 FAIL。維度動畫與模型控制接受檢查使用過時的矩陣文案；browser traceback 指向 Playwright `.check()` 點選 `tensorShapeAnswer` 隱藏 radio，因元素不可見而 timeout。現行 UI label 可見，對照可獨立確認操作不匹配。
- **精確修正：** MLP 維度條件核對 `a∈ℝ³`、`W∈ℝ²ˣ³`、`Wa∈ℝ²` 與 2 維結果；radio 操作改點可見 label，接續確認錯答和正答回饋。
- **路線圖進度：** 維度題的回饋／指南更清楚解釋列對應神經元、欄對應輸入、乘積輸出維度等於神經元數。僅推進神經網路學習小任務，沒有品質主張。
- **驗證：** `node --check web/app.js`、monitor/test AST、focused pytest 2 passed／32 deselected、`git diff --check` PASS。未跑完整 monitor，因含訓練 smoke；無改後 browser／桌面／390px 證據。原 JSON 保留為改前狀態。
- **待辦／限制：** 用不觸發訓練或鎖定 UI 的 browser-only 路徑驗收兩個可見 label、矩陣說明及桌面／390px。未讀寫 holdout／`final-test-*.json`，未跑一次性 final test、行情刷新、訓練、部署或發布；不主張模型品質。


## 排程維護更新（2026-10-24，學習中心續學與 AGY 折疊面板）

- **最高優先缺陷與重現：** 起始 AGY `latest-checks.json`（2026-10-24 19:18:36+08:00）為 FAIL；唯一 FAIL 是 Playwright 點 `#tabGuided` 逾時，locator 已解析但不可見。現行 `web/index.html` 將 tabs 放在預設收合的 `<details id="math">` 內，而 `scripts/regression_monitor.py` 在這段流程未展開祖先就點 tab；DOM 階層和呼叫順序可獨立重現。
- **精確修正：** Monitor 在 tab click 前檢查 `#math.open`，必要時點 summary 展開。
- **路線圖功能：** 學習中心保存導學步驟與目前 tab 至瀏覽器本機儲存，重載恢復；越界索引、未知 tab、損壞 JSON 或儲存不可用時回到第 1 步／逐步導學。
- **改後驗收：** 聚焦 pytest `2 passed, 34 deselected`；JS syntax、monitor/test AST、初始化接線檢查及 `git diff --check` 通過。完整 browser monitor 未執行，因此沒有改後桌面／390px 證據。
- **下一 checkpoint：** browser-only 驗收折疊中心、導學步驟/tab 重載恢復與桌面／390px。熱門股沿用本機 10/10；跨標的方向／幅度仍待同協定一般 OOF。未讀寫 holdout／`final-test-*.json`，未跑一次性 final test、刷新行情、部署或發布；無模型品質主張。

## 2026-10-24 21:06 AGY review and cross-symbol magnitude lesson

- The latest AGY JSON reports three FAIL groups: return/interval lesson, saved cross-symbol summary fixture, and multi-mode learning navigation. Current source inspection confirms the saved-summary monitor prefix matches the app compatibility copy and the lesson catalog checks 21 steps. Without a browser-only rerun, the remaining reported failures are not independently attributable to current product code; they remain open for locator-level reproduction.
- Added synthetic downward-magnitude comparisons to the cross-symbol lesson and guide: group A actual/predicted 0.50/0.70 pp, group B 0.80/1.20 pp. The browser monitor now checks both displayed examples.
- Focused pytest: 2 passed, 39 deselected. JS syntax, Python AST, and diff check passed. No browser verification or model-quality claim.
- Next: safely rerun the failed browser checks and inspect desktop/390px. Protected holdout and final-test data were not accessed; no final test, data refresh, training, deployment, or publication.
## 排程維護更新（2026-10-24，續學導航誤報）

- **AGY 證據：** `artifacts/regression-monitor/latest-checks.json` 22:54:38+08:00 為 FAIL；多模式學習互動中的「導學前進/返回」為 False。
- **獨立重現：** 頁面初始化從 localStorage 恢復 `lessonIndex`，而 monitor 雖暫停保存，仍沿用實際載入的記憶體步數。接受條件硬性要求起點 1、下一步 2、返回 1；保存於第 8 步便會形成 8→9→8，monitor 會錯判。這是監測接受條件缺陷，不是導航按鈕失效。
- **修改及可見學習增量：** 接受條件改為相對起點核對並檢查 21 步目錄；非第一步要求恢復提示。UI 顯示「已恢復上次進度」、步數與課程標題。
- **證據：** pytest 聚焦契約 `3 passed, 40 deselected`，JS syntax、Python AST、diff check PASS。未執行完整 browser monitor；尚無實際瀏覽器重載與桌面／390px 畫面驗收。改前 AGY JSON 未修改。
- **下一步：** 在不觸發訓練 smoke／鎖定測試 UI 的 browser-only 路徑保存第 8 步、重載、驗證恢復提示與相對前進返回；另定位區間互動、跨標的摘要兩項 AGY FAIL。未觸碰 holdout／`final-test-*.json`，未跑一次性 final test、刷新行情或部署發布。
# 2026-10-25 AGY lesson monitor and interval learning

- **Starting evidence:** Latest AGY JSON (`2026-10-25T00:09:55+08:00`) is FAIL: return/interval lesson, multi-mode navigation, and pytest (`1 failed, 67 passed, 1 deselected`). The JSON remains unchanged as pre-change evidence.
- **Reproduction:** Re-ran `python3 -m pytest -q -k 'not public_api_and_async_validation_job'`; `test_monitor_isolates_lesson_progress_and_uses_current_catalog_length` failed because the monitor lacked the expected in-memory reset and Guided tab selection. Current browser flow also rendered direct-index lesson checks while Lab was active and invoked Guided Back while Lab remained selected.
- **Fix:** Isolate lesson state in the monitor page, select Guided before lesson rendering/navigation, and explicitly return to Lab only for Lab checks. This does not alter user progress.
- **Roadmap increment:** Interval lesson now explains scale-to-width with a visible synthetic example: center +0.6%, spreads 0.4/0.7 produce widths 0.8/1.4 percentage points. The guide and monitor calculation contract agree; this is not a model-estimated interval.
- **Verification:** Focused pytest `4 passed, 65 deselected`; safe suite `68 passed, 1 deselected`; `node --check web/app.js`, Python AST, and `git diff --check` passed. No post-change browser or responsive visual result is claimed.
- **Remaining / next checkpoint:** Run a browser-only acceptance path without training smoke or locked-test UI for Guided navigation and interval UI at desktop/390px. The saved-comparison fixture failure remains unresolved pending locator-level reproduction. No locked holdout/final-test access, final test, market refresh, training, deployment, or publication.

## 2026-10-25 scheduled maintenance: AGY triage and lesson contract

The latest AGY report (2026-10-25 01:22:28+08:00) has three browser-only failures: interval/lesson UI, saved-comparison fixture, and guided navigation. The safe pytest subset passed before edits (69 passed, 1 deselected), so those browser symptoms were not independently reproduced from current checks. I did not run the full monitor because it includes training smoke; the raw JSON remains unchanged and is not treated as post-change evidence.

A concrete current acceptance-contract issue was the fixed 21-step count: extending the lesson catalog without updating the monitor would reject the final lesson. The contract now expects 22 steps and checks the new final lesson. Added the visible gradient-clipping exercise with acceptance values (2,4,1,0.1) → clipped gradient 1 / updated weight 1.9; in-bound gradient 0.5 → updated weight 1.95; blank input and negative clipping limit are rejected.

Verification: focused pytest 13 passed / 34 deselected; safe suite 70 passed / 1 deselected; Node-executed arithmetic, `node --check web/app.js`, Python AST parse, and `git diff --check` passed. Browser-only and desktop/390px checks remain outstanding. No model-quality claim. Next checkpoint is browser-only lesson 22 acceptance and locator-level reproduction of the three AGY failures; no final-test/holdout access, final test, market refresh, training, deploy, or publish occurred.
# 2026-10-25 scheduled maintenance: latest AGY triage

- Latest record is `2026-10-25T01:59:55+08:00`, overall FAIL. Three groups fail: lesson interval/ReLU/later-step UI, saved-comparison fixture, and guided navigation.
- Reviewed current source and relevant safe tests. The browser-specific failures were not independently reproduced as a current defect; focused tests passed (4 passed, 43 deselected). No speculative fix was made and the report JSON remains pre-change evidence. Full monitor is excluded because it includes training smoke.
- Bounded roadmap increment: gradient-clipping lesson compares unclipped and clipped outcomes. For w=2, g=4, c=1, eta=0.1: 1.6 versus 1.9; for g=0.5 both are 1.95. Guide and monitor acceptance updated. This is synthetic arithmetic only.
- Verification: pytest focused subset, `node --check web/app.js`, Python AST, and `git diff --check` passed. Browser/390px verification remains open.
- Next checkpoint: run browser-only locator-level reproduction without training or locked-test UI, then inspect lesson 22 at desktop and 390px. Popular-stock coverage remains local 10/10; expansion requires an authorized source. Cross-symbol magnitude requires comparable ordinary OOF summaries. No holdout/final-test read/write, final test, market refresh, training, deployment, or publication.

## Scheduled maintenance update (2026-10-25, SGD gradient visibility)

- **Review triage:** AGY at 03:12:01+08:00 reports three browser failure groups. Current source maps interval and ReLU exercises to their intended lesson indices, so those report details are not independently reproduced as product defects. The saved-summary and navigation failures remain open pending safe browser traces.
- **Reproduced gap / change:** The Lesson 18 renderer computed gradients for both weights and bias but omitted them from visible output. It now shows all three gradients before updated parameters and losses. The guide and monitor acceptance predicate were aligned.
- **Evidence:** Focused pytest `1 passed, 46 deselected`; safe pytest `70 passed, 1 deselected`. Node execution of the actual renderer showed gradients −0.8000/−0.4000/−0.4000, updated parameters 0.5800/−0.3600/0.2400, and loss 0.0400 → 0.0016. JS syntax, monitor/test Python AST, and diff checks passed. No browser visual pass or model-quality claim is made; latest AGY is pre-change evidence.
- **Next checkpoint:** Verify output and rejection branch in a browser-only path at desktop and 390px, excluding training smoke and locked-test UI; local popular-stock coverage remains 10/10, and real cross-symbol magnitude still requires comparable ordinary OOF summaries.

# Scheduled maintenance update (2026-10-25, stale Guided lesson-count predicate)

- **Review evidence:** Latest AGY (`2026-10-25T03:48:17+08:00`) is FAIL with interval/later-lesson, saved-comparison and Guided-navigation failures. Full monitor was not run because it includes training smoke.
- **Reproduced defect and fix:** Guided navigation checked that start/next/return progress totals were the literal `21`, while the current catalog has 22 lessons. Updated the predicate to compare against live `LESSONS.length`, so future course additions do not stale this check.
- **Roadmap increment:** Lesson 15 now presents signed bias alongside direction agreement and absolute magnitude error. Synthetic +0.6% predicted vs +0.2% actual reads overprediction +0.40 pp; +0.1% vs +0.3% reads underprediction −0.20 pp. Updated learning guide and browser predicate.
- **Verification:** Focused pytest `3 passed, 45 deselected`; `node --check web/app.js`, Python AST parsing and `git diff --check` passed. No post-change browser, desktop or 390px evidence. No model-quality inference.
- **Remaining / next checkpoint:** Browser-only verification of Guided navigation, interval interaction and saved-summary fixture with locator details; inspect desktop and 390px. Popular-stock local coverage remains 10/10, while expansion needs an authorized source and actual cross-symbol magnitude comparison needs comparable ordinary OOF summaries. No holdout/final-test access, final test, market refresh, training, deployment or publication.
## 2026-10-25: AGY browser monitor integer-count exception

**Reproduced defect.** Latest review record `2026-10-25T04:23:23+08:00` reports a browser-check failure at `lesson_start.group(2) == ... str(len(page.evaluate("LESSONS.length")))`. Playwright returns `LESSONS.length` as an integer; Python `len(int)` raises the reported `TypeError` and aborts the monitor check.

**Exact fix.** Convert the returned integer directly to text with `str(page.evaluate("LESSONS.length"))`. The source contract now requires that expression and rejects the prior `len(int)` form.

**Roadmap increment and evidence.** Lesson 22 now displays absolute update step sizes before and after clipping, alongside updated weights. The synthetic clipped example gives 0.4000→0.1000 and weight 1.6000→1.9000; the in-limit example stays 0.0500. Focused pytest: 2 passed, 46 deselected, including actual JS calculation. `node --check`, Python AST and `git diff --check` pass. No browser or viewport rerun; no model-quality inference.

**Next checkpoint.** Run safe browser-only acceptance without training smoke or locked-test UI; inspect Guided navigation, clipping, interval and saved comparison at desktop and 390px.

## 2026-10-25: AGY lesson acceptance failures caused by tab state

The latest review reported failures for interval, ReLU and later lesson widgets. Current monitor flow could leave the learning center on another tab after keyboard-tab acceptance, while direct fixture code only changed `lessonIndex` and re-rendered. Those lesson nodes then remained under a hidden Guided panel, so visibility predicates failed independently of calculator behavior.

**Correction:** the monitor now selects Guided with a Playwright locator before every direct lesson fixture. This reproduces the visible interaction and isolates each check from prior tab state. Existing reset suppresses progress persistence for that monitor page only.

**Verification:** 4 focused tests passed, full safe project suite 72 passed; actual interval/magnitude renderers and saved-summary compatibility fixture were evaluated; JS syntax, Python AST and diff checks passed. AGY JSON was retained unchanged as pre-change evidence. No browser rerun or desktop/390px visual result is claimed. The reported saved-summary fixture failure was not reproduced from current code.

**Next checkpoint:** create/use a browser-only monitor path that excludes training smoke and locked-test UI, then verify Guided navigation and lesson widgets at desktop and 390px.
# Scheduled maintenance update (2026-10-25, AGY triage and gradient retention)

- **Latest review:** `artifacts/regression-monitor/latest-checks.json` (`2026-10-25T05:35:03+08:00`) reports failures for interval/lesson interaction, the saved-comparison fixture, and Guided navigation. Safe pytest reproduces no current failure (`71 passed, 1 deselected`), and source inspection did not establish a concrete product defect behind those browser-only symptoms. The complete monitor was not run because it includes a training smoke. Preserve the JSON as pre-change evidence.
- **Change:** Lesson 22 now displays the retained gradient fraction alongside clipped value, step size, and updated weight. For `g=4`, limit `1`, it reports 25.0%; for `g=0.5`, it reports 100.0%; zero gradient is defined as 100.0%. HTML explanation, guide, monitor acceptance, and focused contract align.
- **Evidence:** Focused pytest `1 passed, 47 deselected`; safe suite `71 passed, 1 deselected`; `node --check web/app.js`, Python AST parse, and `git diff --check` pass. Browser/responsive rendering remains unverified. This demonstrates synthetic arithmetic only, not model quality or training stability.
- **Next action:** Capture locator-level evidence in a browser-only run that excludes training smoke and locked-test UI, then inspect Guided navigation, interval controls, saved comparison, and lesson 22 at desktop/390px. Popular stocks remain locally covered 10/10; more symbols require an authorized data source, while real cross-symbol magnitude comparison requires comparable ordinary OOF summaries.
## 2026-10-25: routine monitor training side effect and baseline teaching gap

**Concrete defect.** The latest AGY report (`2026-10-25T06:11:03+08:00`) records an isolated 1-epoch `/api/experiments` smoke in scheduled monitoring. Current `check_splits_and_train()` independently confirms that routine runs start this job when no user training is active. Scheduled maintenance explicitly forbids training, so this is a concrete task-boundary violation. No evidence indicates locked observations were read; the same report says persistence was isolated and locked-data checks passed.

**Fix.** Keep sample generation, finite-input and chronological walk-forward-boundary checks. Remove the training route call from the routine function and record `FastAPI／PyTorch 真實資料訓練` as SKIP. Contract test asserts no experiment POST remains in this routine.

**Roadmap increment.** Lesson 15 now compares absolute prediction error with the zero-return baseline and labels lower/equal/higher. Synthetic +0.6/+0.2 returns 0.40 vs 0.20 pp (higher); 0/+0.1 returns 0.10 vs 0.10 pp (equal); +0.05/+0.10 is lower. Guide notes that real assessment needs ordinary OOF predictions and a same-period baseline. This is teaching arithmetic, not a model claim.

**Evidence.** Focused tests: 4 passed, 46 deselected. Safe suite: 73 passed, 1 deselected. `node --check web/app.js`, Python AST parse and `git diff --check` passed. The initial tie fixture used −0.1/+0.1, which is not a tie; test evidence caught it and both example and guide were corrected to 0/+0.1. No post-change browser or desktop/390px evidence.

**Other AGY findings / next checkpoint.** Interval lesson, saved-summary fixture and Guided navigation FAILs remain unclaimed as product defects pending a training-free browser trace. Build that path without locked-test UI, then collect desktop/390px evidence. Popular-stock local coverage remains 10/10; expansion needs an authorized source; true cross-symbol magnitude work needs comparable ordinary OOF summaries. No protected-file access, final test, market refresh, training, deployment, publication or model-quality claim.
## 2026-10-25: latest browser failures and gradient-vector lesson

The latest AGY artifact (`2026-10-25T06:47:14+08:00`) reports failures in interval/ReLU lesson interaction, saved-summary compatibility, and Guided navigation. Current source and the safe regression suite (`79 passed, 1 deselected`) do not independently reproduce a concrete defect. These remain open; next diagnostic is a browser-only trace with locators and state captured, excluding training smoke and locked-test UI.

Roadmap work adds a visible global L2 gradient clipping example to lesson 22. For synthetic gradient `(3,4)`, norm 5, a norm limit of 1 scales it to `(0.6,0.8)`. The guide distinguishes this from per-component clipping. This is a bounded math lesson, not training or model-quality evidence. Focused pytest `1 passed, 49 deselected`; `node --check web/app.js`, Python AST parsing for monitor/tests, and `git diff --check` passed. No browser visual acceptance.
## Scheduled review follow-up (2026-10-25, AGY 07:21)

- **Review evidence:** `artifacts/regression-monitor/latest-checks.json` at `2026-10-25T07:21:20+08:00` reports FAIL for lesson interactions, saved-summary fixture, and Guided navigation; pytest is PASS (`79 passed, 1 deselected`).
- **Reproduced monitor defects:** Lesson fixture helper clicked Guided and immediately ran JS without confirming the tab/panel transition. It now waits for `aria-selected=true` and `#learningGuided.hidden=false`. The compatible saved-summary fixtures omitted training setup fields, so `savedValidationSummary()` produced empty setup signatures and the guard properly rejected them. Fixtures now use identical explicit setup metadata for both symbols.
- **Roadmap feature:** Lesson 22 adds a live global L2 clipping calculator for two gradient components. Default `(3,4)` at norm limit 1 displays original norm 5, scale 0.2, clipped `(0.6000,0.8000)`, and new norm 1; below-limit and invalid-input behavior are covered.
- **Verification:** Four focused tests passed; JS syntax, monitor/test AST parsing, and diff check passed. No full monitor rerun or visual browser acceptance is claimed; the other Guided/interval/ReLU browser findings remain pending independent browser tracing.
- **Next checkpoint:** Browser-only state/locator trace without training smoke or locked-test UI; inspect lesson 22 on desktop and 390px. Do not claim overall learning completion or model quality.
## 2026-10-25 — Loss pointer acceptance coordinates

- **Evidence:** `artifacts/regression-monitor/latest-checks.json` at `2026-10-25T07:57:13+08:00` reports Loss hover text missing while keyboard navigation returns Epoch 2. The monitor targeted `box.x + width * .54` on a responsive SVG with viewBox width 660 and plot starting at x=66, so its pointer could land in the left margin. It read hover text before keyboard, but combined it only after keyboard navigation, making the evidence less isolated.
- **Finding:** Current app transforms pointer coordinates through `getScreenCTM().inverse()` and clamps to available epochs. The reproduced defect is the monitor fixture's target, not a reproduced product tooltip failure.
- **Fix:** Target x=354 in the 660-unit SVG plot and require a standalone hover predicate before focusing and checking ArrowRight. Keep the AGY JSON unchanged as pre-fix evidence.
- **Verification:** Focused tests `2 passed, 48 deselected`; JS syntax, monitor/test AST, scoped diff check passed. Browser rerun remains pending.
- **Other reported FAILs:** Training animation completion starts an experiment and was not reproduced because scheduled maintenance must not train. Interval/lesson UI, saved-summary fixture, and Guided navigation still need a browser-only trace without training smoke or locked-test UI.
# Scheduled maintenance update (2026-10-25, terminal animation check and momentum coefficient)

- **Review data:** `artifacts/regression-monitor/latest-checks.json` at `2026-10-25T09:06:34+08:00` reports terminal animation FAIL, lesson widget failures, saved-comparison fixture FAIL, Guided navigation FAIL, and Loss tooltip hover FAIL. Training and locked-test checks are SKIP.
- **Independently reproduced highest-priority issue:** In `scripts/regression_monitor.py`, completion is simulated and asserted through the training animation handler. The first completed update stops animation and advances the diagram to output; a later completed poll preserves the terminal message. The monitor already performs that second in-memory update, and its comment now documents why. No training request was made. The latest review artifact remains unchanged as pre-fix evidence.
- **Roadmap feature:** Lesson 20 now presents a side-by-side momentum-coefficient calculation with actual default inputs held constant. β=0.9 gives 0.4500 prior contribution, 1.4500 velocity, and weight 1.855; β=0.5 gives 0.2500, 1.2500, and 1.875. The guide and renderer test cover the visible output.
- **Verification:** Focused pytest `2 passed, 49 deselected`; `node --check web/app.js`; monitor/test Python AST parse; scoped `git diff --check`. No browser, desktop/390px, or model-quality claim.
- **Open work / next checkpoint:** Reproduce the remaining browser failures using a browser-only path that avoids training start and locked-test UI; obtain locator-level evidence for Guided navigation, interval/later lesson widgets, saved-summary fixture, and Loss hover, then inspect desktop/390px. Neural-network learning remains incomplete. Popular-stock coverage remains local 10/10; expansion requires an authorized source, and real cross-symbol magnitude comparison requires comparable ordinary OOF summaries.
# Scheduled maintenance report (2026-10-25)

## Reproduced highest-priority defect

The latest review data at `2026-10-25T10:50:42+08:00` reports FAIL groups for lesson widgets, saved comparison, Guided navigation, and Loss hover. The monitor source reproduces a false navigation failure path: it selects Lab, switches to Guided, and clicks `#lessonBack` immediately without waiting for Guided visibility. The browser test now waits for `aria-selected=true` and `#learningGuided.hidden=false` before navigation. A focused source-contract test enforces this order.

## Bounded roadmap increment

The neural-network learning guide's gradient-clipping subtask now supports a four-component synthetic vector. `(1,2,2,4)` has L2 norm 5; limit 2 gives scale 0.4, clipped components `(0.4,0.8,0.8,1.6)`, and norm 2. The calculator rejects blank/non-finite inputs, negative limits, and more than 64 components. The guide and browser-monitor acceptance criteria cover output and invalid cases. It does not connect to training or establish model quality.

## Verification and remaining work

Focused pytest: `3 passed, 122 deselected`. Safe suite: `124 passed, 1 deselected`. `node --check web/app.js`, Python AST parsing, and scoped `git diff --check` passed. The browser monitor was not run because it includes training smoke, so browser and desktop/390px appearance remain unverified. Next checkpoint: a browser-only route that omits training and locked-test UI, followed by diagnosis of the other reported failures. Popular-stock expansion needs an authorized data source; real cross-symbol magnitude analysis needs comparable ordinary OOF summaries. No protected data was accessed, no final test or data refresh was run, and nothing was deployed or published.

## Scheduled maintenance update (2026-10-25, latest AGY triage and momentum lesson)

- **Review evidence:** `artifacts/regression-monitor/latest-checks.json` at `2026-10-25T12:00:05+08:00` reports FAIL for interval/ReLU and later lesson widgets, saved cross-asset summary fixture, Guided next/back, and Loss pointer tooltip. Focused contracts passed before the feature work (`4 passed, 52 deselected`). Current saved-summary fixture rerun through the actual JS summary/compatibility functions in Node produced a compatible descriptive comparison. The local browser endpoint is unavailable (`127.0.0.1:8000` connection refused), so the remaining browser findings are not independently reproduced as product defects. No defect fix is claimed and the historical AGY JSON remains unchanged.
- **Exact change / roadmap:** Lesson 20 now always includes a visible fixed example where negative prior velocity opposes the current gradient: β=0.5, vₜ₋₁=−0.5, gₜ=1 gives −0.25 retained history, vₜ=0.75, and w: 2→1.925. `docs/learning-guide.md` and the renderer acceptance test describe/assert those values.
- **Verification:** Focused pytest `5 passed, 51 deselected`; Node-backed actual-renderer checks passed, as did JavaScript syntax, Python AST parsing, and scoped diff check. Browser visual acceptance remains unavailable.
- **Next checkpoint:** Run a browser-only monitor route when the local service is available, capture selectors/trace for the four reported failure groups, and inspect lesson 20 at desktop and 390px. Popular-stock expansion still needs an authorized source; real cross-symbol magnitude comparison requires comparable ordinary OOF summaries. No protected test data access or market refresh.
## 2026-10-25 — Loss pointer failure caused by monitor target

- **Review evidence:** `artifacts/regression-monitor/latest-checks.json` at 13:45:28+08:00 reports Loss pointer tooltip FAIL while keyboard tooltip succeeds.
- **Reproduction:** `renderLossChart()` creates `.loss-hit-area` at viewBox x=66..642, y=20..212. Monitor's x=354 target is in range, but y=`box.height * .45` converts to viewBox y=112.5, outside the 3px rendered hit-area height. The pointer handler itself uses the rendered SVG rectangle and viewBox scaling.
- **Correction:** Set the synthetic monitor pointer y fraction to `.5`, which lands at viewBox y=125 inside the plot hit area.
- **Verification:** Focused pytest: 3 passed, 53 deselected; includes the monitor pointer coordinate contract. `node --check web/app.js`, Python AST parsing, and scoped `git diff --check` passed. Browser execution was not performed; hover is not reported as visually verified.
- **Other current review failures:** Lesson widgets, saved comparison fixture, and Guided navigation remain pending independent browser reproduction. Latest review JSON retained as pre-change evidence.
- **Next checkpoint:** Run browser-only checks without training smoke or locked-test UI and record selectors for the remaining failures. Do not use holdout or final-test data. No model-quality inference is supported by these checks.
## 2026-10-25 14:22+08:00: browser findings could not be reproduced in current environment

The preceding AGY run (14:19:49+08:00) reported failures in interval/ReLU lesson interaction, saved-summary fixture, Guided navigation, and Loss pointer tooltip. Independent safe contracts for the saved comparison, prediction interval, ReLU, and Guided navigation passed (`7 passed, 51 deselected`); source inspection did not establish an application root cause. The scheduled monitor rerun failed before browser inspection because its local HTTP request was denied (`Operation not permitted`) and headless Chrome exited (`TargetClosedError`). Its safe pytest selection passed (`125 passed, 1 deselected`), training smoke was SKIP, and locked-data isolation PASS. Do not treat those browser findings as fixed or resolved; repeat a browser-only trace when the local HTTP/Chrome environment is available.

The zero-gradient clipping edge case is now visible in the four-component lesson: `(0,0,0,0)` remains zero with scale 1 and clipping does not invent a direction. This is a learning increment, not a product-defect repair or model-quality claim. Focused acceptance: `1 passed, 55 deselected`; JS syntax, monitor/test AST, and scoped diff checks passed. Browser visual acceptance is pending.
# 2026-10-25 latest review disposition (14:57:26+08:00)

The latest AGY report is FAIL for lesson interval/ReLU/later controls, saved cross-asset summary fixture, multi-mode guided navigation, and Loss pointer tooltip. Current source inspection did not independently establish a product root cause. The safe focused pytest selection passes (16 passed, 40 deselected), but it does not exercise the reported browser interactions. The full monitor includes training smoke and was not run. These reports remain unresolved and must not be marked fixed based on the previous monitor or source-only reasoning.

Next diagnostic: provide a browser-only acceptance path that omits training smoke and locked-test UI; capture the failing selector, active lesson/tab, and pointer coordinates for each failure. Then repair the first reproducible issue and add an acceptance contract. No market-data or locked-test state was touched.

# Scheduled maintenance update (2026-10-25 15:31 AGY review)

- **Review:** `latest-checks.json` reports FAIL for lesson interaction, saved-comparison fixture, Guided navigation, and Loss pointer tooltip. Current safe contracts pass for the lesson, saved-summary, and navigation logic; those browser failures are not independently reproduced as product defects.
- **Reproduced acceptance defect / fix:** The monitor's Loss pointer used a CSS-box vertical midpoint, which does not necessarily map to the chart's plot because the SVG viewBox is 660×250 and the responsive CSS box can have another ratio. It now targets `112.5/250` of the box height, matching the plot's viewBox center. The app clamps mapped pointer x to `[L, W-R]` before selecting the nearest epoch, including pointer moves over axis margins.
- **Roadmap feature:** The editable four-parameter clipping comparison has an executable visible-output acceptance. `(1,2,2,4)` at limit 2 gives norm-clipped `(0.4,0.8,0.8,1.6)` with norm 2, versus component-clipped `(1,2,2,2)` with norm √13. Synthetic learning example; no model-quality conclusion.
- **Evidence / limits:** Focused pytest `7 passed, 51 deselected`; JavaScript syntax, monitor/test AST, and scoped diff checks passed. No browser or responsive render was run. Full monitor/training smoke and locked-test UI were not invoked. Latest AGY JSON is preserved as pre-change evidence.
- **Next checkpoint:** Add/run a browser-only acceptance path excluding training and locked-test UI; capture active tab/lesson and pointer locator details for remaining FAILs; verify at desktop and 390px. Popular-stock expansion awaits an authorized source and real cross-symbol magnitude comparison awaits compatible ordinary OOF summaries. No protected observations or `final-test-*` files accessed, no final test, refresh, deploy, or publication.

## Scheduled maintenance update (2026-10-25, zero-limit gradient clipping boundary)

- **Latest AGY review:** `artifacts/regression-monitor/latest-checks.json` at 16:05:48+08:00 reports FAIL for lesson interaction, saved-summary fixture, multi-mode navigation, and Loss pointer tooltip. Current monitor reads the pointer tooltip before keyboard navigation, so this pointer failure is not independently reproduced as a current product defect. Browser traces remain needed for all listed groups.
- **Roadmap increment:** Lesson 22's four-dimensional clipping calculator now explains the zero-limit boundary: a nonzero gradient scales to zero, producing no weight update. The learning guide describes this as an edge case, not a recommended setting.
- **Observable acceptance:** Executable renderer acceptance sets the vector to the existing nonzero default and the limit to zero, then checks the visible explanation. Synthetic arithmetic only; no training or model-quality conclusion.
- **Next checkpoint:** Run focused safe contracts, JS syntax, Python AST and scoped diff checks; later trace browser FAILs without training smoke or locked-test UI and inspect desktop/390px. Popular-stock expansion awaits an authorized source; magnitude comparison awaits compatible ordinary OOF summaries. No protected-data access, final test, data refresh, deployment or publication.
## Scheduled maintenance update (2026-10-25, training-state mutation in routine monitor)

- **Reproduced defect:** Latest review JSON (`2026-10-25T16:39:41+08:00`) reports browser failures in lesson controls, saved-comparison fixture, multi-mode navigation, and Loss pointer; current safe checks do not localize those causes. Source inspection independently reproduced a monitor-reporting defect: `browser_check()` simulated running/completed UI state and described it as training animation, although no backend training was called.
- **Fix:** Removed the synthetic animation sequence. The monitor now verifies idle UI state at that checkpoint; its separate API-entry contract intercepts before backend execution. Existing JSON remains untouched pre-change evidence.
- **Roadmap feature:** Mini-batch lesson expanded from two to four editable sample gradients. It computes the average and a single update, validates missing inputs, and displays the arithmetic. Synthetic default: gradients `(-2,4,1,1)`, mean `1`, weight `2` to `1.9` at rate `0.1`.
- **Evidence:** Focused pytest `2 passed, 56 deselected`; actual JS calculator gives `{average:1, updated:1.9}` and rejects blank gradient; JS syntax, Python AST, scoped diff checks pass. Browser/viewport verification not run; no model-quality inference.
- **Remaining:** Trace the four AGY browser FAIL groups using a browser-only route that avoids training and locked-test UI; verify mini-batch lesson at desktop and 390px. Popular-stock expansion needs authorized data, and real cross-symbol magnitude reading needs comparable ordinary OOF summaries.
# Scheduled maintenance finding — 2026-10-25

## Reproduced monitor issue

The latest review artifact, `artifacts/regression-monitor/latest-checks.json` (`2026-10-25T17:48:57+08:00`), marks the saved cross-symbol comparison fixture as failed. The monitor compared the compatibility summary to a fixed prose prefix. That acceptance rule was unnecessarily dependent on exact wording and ordering instead of checking the six compatibility facts.

## Change and evidence

`scripts/regression_monitor.py` now checks for all six required terms: target protocol, model, training setup, forecast horizon, return definition, and validation dates. The source-contract test was updated, while legacy and mismatch branches remain covered. This fixes a monitor contract; it is not evidence of a product defect or predictive quality.

The batch-gradient lesson also now visibly compares mixed-sign gradients `(-2,4,1,1)` with aligned gradients `(1,1,1,1)`. Both average to 1 and update weight 2 to 1.9 at learning rate 0.1, but the sample directions differ. The guide and renderer test include this synthetic case.

Focused verification: `3 passed, 56 deselected`; safe system selection: `58 passed, 1 deselected`; `node --check web/app.js`, Python AST parsing, and scoped `git diff --check` passed. No browser monitor was rerun, so the review JSON is still pre-change evidence. Lesson widgets/navigation and Loss pointer tooltip failures remain open pending a safe browser-only trace.

## Next checkpoint and safety

Verify saved comparison, Guided navigation, the batch-gradient interaction, and Loss pointer/keyboard behavior at desktop and 390px with training smoke and locked-test UI excluded. Popular-stock coverage remains 10/10 locally; expansion needs an authorized source, and genuine cross-symbol magnitude reading needs comparable ordinary OOF summaries. No `final-test-*.json` or locked holdout observations were read, written, or consumed; no final test, market refresh, deployment, or publication occurred.
# Scheduled maintenance finding (2026-10-25, lesson-widget acceptance)

- Latest review `artifacts/regression-monitor/latest-checks.json` (`2026-10-25T18:29:00+08:00`) reports lesson/widget, saved-summary, learning-navigation, and Loss-pointer failures.
- Independently confirmed the lesson map in `web/app.js`: interval is step 11 (`lessonIndex=10`); ReLU local-gradient interaction is step 14 (`lessonIndex=13`). The monitor checks ReLU interaction separately but did not assert ReLU is hidden while interval is visible at step 11. This is a reproducible acceptance gap; it does not prove the app's lesson widgets are broken.
- Added an explicit index-10 interval-visible/ReLU-hidden monitor predicate and a focused pytest contract. User-facing product behavior is unchanged.
- Verification and roadmap evidence: focused pytest passed (`1 passed, 59 deselected`); monitor/test AST parsing and scoped `git diff --check` passed. `py_compile` was blocked because its bytecode cache is outside the permitted project; no-write AST parsing verified syntax. Latest JSON remains pre-change; no browser acceptance or model-quality claim is made. This only tightens acceptance for the existing neural-network learning lesson flow; broader milestone remains incomplete.
- Next: browser-only rerun excluding training smoke and locked-test UI. Local popular-stock coverage remains 10/10; expansion requires an authorized source. Cross-symbol magnitude learning still needs comparable ordinary OOF summaries. Do not access locked holdout observations or `final-test-*.json`, run final evaluation, refresh market data, deploy, or publish.

## Scheduled maintenance finding (2026-10-25, resume-state monitor contracts)

- **Review:** Latest JSON (`2026-10-25T19:37:33+08:00`) reports lesson interactions, saved-comparison fixture, and Guided navigation as FAIL; safe pytest is `2 failed, 129 passed, 1 deselected`.
- **Reproduction and fix:** The safe pytest selection reproduced both test failures. One monitor predicate had lost the requirement to show the saved-resume notice for a non-first lesson. A separate test expected reset of the loaded snapshot although the monitor source had changed. Restored the resume predicate and aligned the contract with the monitor's explicit in-memory progress/snapshot reset. This is monitor acceptance repair; browser product behavior remains unverified.
- **Roadmap advance:** The mini-batch lesson contrasts mixed gradients `(-2,4,1,1)` and aligned `(1,1,1,1)`: both average to 1 and update weight 2 to 1.9 at rate 0.1, despite different per-sample directions. Synthetic teaching only; broader neural-network learning remains incomplete.
- **Evidence:** Safe suite `131 passed, 1 deselected`; JS syntax, Python AST and scoped diff checks passed. No browser monitor rerun and no model-quality claim. The JSON remains pre-change evidence.
- **Next checkpoint:** Browser-only trace for lesson widgets, saved comparison and Guided navigation at desktop/390px, excluding training smoke and locked-test UI; separately inspect design-drift WARN. Popular-stock expansion requires authorized data and real cross-symbol magnitude interpretation requires comparable ordinary OOF summaries. No protected data or final test accessed; no market refresh, deployment or publication.
## 2026-10-25: magnitude exercise conflated signed error with magnitude bias

- **Finding:** Current `renderMagnitudeErrorExercise()` showed the signed prediction-minus-actual error and absolute error, but not whether predicted absolute return magnitude was larger/smaller/equal. For `−0.2%` predicted and `+0.2%` actual, the signed error is −0.4 percentage points even though magnitudes are equal; the output lacked that distinction.
- **Change:** Added an explicit predicted absolute-magnitude comparison label and documented this opposite-direction example in the learning guide.
- **Acceptance:** Renderer pytest passed (`1 passed, 61 deselected`) for larger, smaller, equal, and opposite-direction/equal-magnitude values. JS syntax and scoped diff checks passed.
- **Limits / next:** AGY's latest browser lesson, saved-summary, and navigation failures are still not independently localized; focused related pytest selection passed (`19 passed, 43 deselected`). Latest JSON remains pre-change evidence. No browser/390px claim or model-quality claim. Next, run a browser-only trace excluding training and locked-test UI.
## Scheduled maintenance update (2026-10-25, interval width scaling readout)

- **Latest review / reproduced defect:** `artifacts/regression-monitor/latest-checks.json` at `2026-10-25T22:34:30+08:00` reports pytest PASS (`139 passed, 1 deselected`) and browser FAILs for lesson widgets, saved-summary fixture, and Guided navigation. Reproduced a monitor predicate defect: the interval output formats positive values without a plus sign, but its browser predicate required plus signs for both default and changed bounds. Correct widget output therefore failed acceptance; this is not a product interval defect.
- **Exact change:** Updated the monitor predicate to match the renderer's positive endpoint format and guarded it with a source contract. Added a live user-facing scale-to-width statement to the interval lesson. Synthetic scale 0.40pp reports width 0.80pp; scale 0.80pp reports width 1.60pp. It states that doubling scale doubles width while the center is fixed. Added a renderer acceptance test for both values and the HTML output element.
- **Roadmap status:** Advanced one bounded neural-network learning subtask on uncertainty interval width. This is synthetic arithmetic, not calibration, model training, or quality evidence. Popular-stock local coverage remains 10/10 pending an authorized data source for expansion; genuine cross-symbol magnitude reading needs comparable ordinary OOF summaries.
- **Verification:** Monitor contract pytest `1 passed`; interval renderer/boundary pytest `2 passed, 7 deselected`; `node --check web/app.js`, Python AST parsing, and scoped `git diff --check` passed. Browser rerun and desktop/390px visual acceptance were not performed. Latest AGY JSON remains unchanged pre-change evidence.
- **Remaining / next checkpoint:** Capture fresh browser state/locators for interval, ReLU and later widgets, saved-summary fixture, and Guided navigation using a route without training smoke or locked-test UI. Inspect the new readout at desktop and 390px. No protected data, final test, market refresh, deployment, or publication.
# Scheduled maintenance triage (2026-10-25)

- **Latest evidence:** `artifacts/regression-monitor/latest-checks.json` (`2026-10-25T23:09:46+08:00`) reports failures in the lesson interaction, saved cross-asset summary fixture, and multi-mode navigation checks. Its safe test run reports `140 passed, 1 deselected`. Current source review did not reproduce a concrete cause for these browser failures, so they remain open. Focused execution independently exposed a calculator boundary mismatch for the new duplicated batch: length 8 was rejected by the helper. It now accepts exactly 4 or 8 gradients and continues to reject other lengths.
- **Resolved earlier monitor issue:** The step-19 fixture in current `scripts/regression_monitor.py` expects `第 19 / 22 步`, matching `lessonIndex=18` and `renderLesson()`'s one-based progress. This old mismatch is no longer present.
- **Bounded implementation:** The mini-batch lesson now repeats the same four gradients and compares average-based and sum-based updates. Observable synthetic default: four and eight copies both average to `1` and update `w=2` to `1.9`; raw sum grows from `4` to `8`, yielding `1.6` then `1.2`. Updated UI prompt, learning guide, and renderer contract.
- **Verification / limits:** Pre-edit safe selection: `140 passed, 1 deselected`; Focused renderer test passed (1 passed, 61 deselected); safe selection passed (140 passed, 1 deselected); JS syntax, Python AST, and scoped diff checks passed. No browser or responsive acceptance claimed. No locked observations or `final-test-*.json` read/changed, no one-time final test or market refresh.
- **Next action:** Next capture browser locator/state evidence for the three open groups in a browser-only route at desktop and 390px; focused and safe tests already pass. Do not invoke training smoke or locked-test UI.
## Scheduled maintenance update (2026-10-26)

- **Review evidence:** Latest check JSON (`2026-10-25T23:47:03+08:00`) reports safe pytest PASS (`140 passed, 1 deselected`) and browser FAIL for lesson interactions, saved-summary fixture, and Guided navigation. Inspection of current sources did not reproduce a specific product cause; all three remain unresolved.
- **Independently reproduced defect:** The learning guide described step 19 as accepting two sample gradients. Current lesson and widget use four gradients and display a repeated eight-item comparison.
- **Correction and user-visible milestone:** Updated the guide to describe the live four-gradient example and its average-versus-sum comparison. Existing executable renderer acceptance establishes the visible synthetic outcomes: four-gradient mean 1 updates weight 2 to 1.9; repeated eight-gradient mean still updates to 1.9; unnormalized sum 8 updates to 1.2. This advances the neural-network learning material, not model quality.
- **Verification:** Focused test `1 passed, 61 deselected`; `node --check web/app.js`, Python AST parse, and `git diff --check` passed. Browser rendering was not rerun.
- **Next action:** Add/use a browser-only check that skips training smoke and locked-test UI, then capture selectors/state for ReLU interaction, saved-summary compatibility, and Guided next/back at desktop and 390px. Do not infer pass from the previous JSON.

## 2026-10-26 01:34 AGY follow-up: stale multi-input expectation

- **Severity / reproduction:** The latest checks JSON reports `報酬與區間互動教學`, `跨標的方向與幅度讀圖練習`, and `多模式學習互動` as FAIL; safe pytest is PASS (`142 passed, 1 deselected`). Independently evaluated the current `calculateMultiForwardPass()` source at step 17 defaults. After the monitor changes the target to 0, the output remains `z=0.8`, so `δ=2(0.8−0)=1.6` and the bias gradient is `1.60`; the monitor was incorrectly checking `−0.40`. This makes `multi_forward_pass_ok` false and contributes to the lesson failure. A separate deterministic state leak left `lessonIndex=21` before monitor navigation assumed index 0 and advanced seven steps to lesson 8.
- **Fix:** Monitor now expects target-zero bias gradient `1.60` and resets/render lesson 1 before advancing seven times. Added regression contracts for both. Step 17 now visibly explains each weight gradient's dependence on its input and the bias gradient's equality to δ.
- **Verification:** Focused selection 3 passed, 62 deselected; safe selection 143 passed, 1 deselected. Node syntax, monitor/test AST parsing and scoped diff check pass. Latest JSON is pre-fix evidence; browser recheck remains outstanding.
- **Limits / next:** This synthetic learning task is not model-quality evidence. Trace all browser failures in browser-only mode at desktop and 390px, excluding training and locked-test UI. Do not read locked observations or `final-test-*.json`; no final test or market refresh is part of this checkpoint.
## Scheduled maintenance update (2026-10-26, reset contract and ReLU zero point)

- **Input evidence:** Latest regression JSON at `2026-10-26T02:46:06+08:00` reports FAIL, including safe pytest `1 failed, 143 passed, 1 deselected` and browser lesson/saved-summary/navigation failures.
- **Highest-priority reproduced defect:** Safe pytest independently failed because `test_guided_resume_notice_uses_saved_progress_and_monitor_reset_updates_snapshot` expected two reset occurrences while the monitor contains three. The third is the current lesson-navigation fixture reset. The contract now expects all three and separately pins two resets that disable persistence; this is acceptance-contract drift, not broken learner behavior.
- **Bounded implementation:** ReLU result for exactly `z=0` now states the nondifferentiable-point convention `ReLU′(0)=0`; for `y=3`, the shown values are output 0, loss 9 and local gradient 0. Updated guide and browser predicate. No market/model evaluation.
- **Verification:** Focused tests `2 passed, 65 deselected`; safe selection `145 passed, 1 deselected`; JS syntax, monitor/test AST and scoped diff checks passed. The JSON remains pre-change evidence; aggregate browser failures are not treated as newly fixed.
- **Open items / next checkpoint:** Verify safe tests and syntax, then browser-only lesson at desktop and 390px. Diagnose saved-summary and multi-mode navigation with fresh browser traces. Keep local stock coverage at 10/10 until a data source is authorized; compare cross-symbol magnitudes only with compatible ordinary OOF outputs. No locked data/final-test access, final test, refresh, training smoke, deploy or publish.


## Scheduled maintenance update (2026-10-26, ReLU chain-rule readout)

- **Latest AGY evidence:** `artifacts/regression-monitor/latest-checks.json` at `2026-10-26T03:22:01+08:00` reports FAIL for lesson interactions, saved-summary fixture, and multi-mode navigation; safe pytest PASS (`145 passed, 1 deselected`), local stock coverage 10/10, and training smoke/locked-test UI skipped.
- **Defect triage:** Current source inspection did not independently reproduce a product defect behind those browser failures. Current ReLU and one-step update expectations agree with calculator arithmetic; saved-summary FAIL still needs browser state/locator evidence. No defect fix is claimed.
- **Exact change / milestone:** The ReLU learning output now displays `ReLU′(z)` as a separate factor and shows `dL/dz = 2(ŷ−y) × derivative`. At z=0,y=3: derivative 0 and gradient 0; at z=−2,y=3: derivative 0 and gradient 0; at z=2,y=3: derivative 1 and gradient −2. Updated the guide, monitor predicate, and executable renderer acceptance. This is synthetic neural-network math instruction, not model training or quality evidence.
- **Verification:** Focused tests `2 passed, 65 deselected`; safe selection `145 passed, 1 deselected`; `node --check web/app.js` and `git diff --check` passed. No browser rerun or desktop/390px visual check.
- **Next checkpoint:** Obtain fresh browser locator/trace evidence for the three FAIL groups and inspect the ReLU output at desktop/390px. Popular-stock expansion still needs an authorized data source; real cross-symbol comparison needs compatible ordinary OOF summaries. No holdout/final-test file access, final test, market refresh, training smoke, deployment, or publication.

## Scheduled maintenance update (2026-10-26, monitor predicate drift and ReLU gradient gate)

- **Review evidence:** `artifacts/regression-monitor/latest-checks.json` at `2026-10-26T03:57:11+08:00` reports overall FAIL and three browser FAIL groups. The lesson group identifies false subchecks for ReLU interaction, step-15 direction/magnitude, and step-18 gradient update; saved-summary and Guided navigation remain separate failures.
- **Reproduced cause / exact fix:** The ReLU renderer's empty-input text includes `可計算的`, so the monitor's expected substring was absent. For predicted −0.1% vs actual +0.1%, absolute error 0.20 pp exceeds the 0.10 pp zero baseline; the monitor incorrectly expected equality. At η=0.5, the current multi-input update yields loss 1.0000, not 0.0400. Updated all three predicates to current output/arithmetic; no product bug is inferred from them.
- **Bounded learning change:** The step-16 forward-pass output now shows `ReLU′(z)` and whether the local gradient passes. Its acceptance checks default z=1.2 -> 1, negative z=−0.8 -> 0, and boundary z=0 -> 0. Guide and monitor updated. Synthetic lesson only; no training or quality claim.
- **Verification / limits:** Focused pytest `2 passed, 66 deselected`; safe suite `146 passed, 1 deselected`; JS syntax, Python AST, scoped diff checks passed. Browser rerun was not performed; latest JSON stays as pre-change evidence. Remaining saved-summary and Guided navigation failures require browser trace evidence.
- **Next checkpoint:** Run the browser-only lesson checks at desktop and 390px without training smoke or locked-test UI; capture locators/state for saved-summary and Guided navigation. Stock coverage remains local 10/10; expansion needs an authorized data source, and cross-symbol magnitude reading needs compatible ordinary OOF summaries.
# Scheduled maintenance update (2026-10-26, missing lesson predicate diagnostics)

- **Review input:** `artifacts/regression-monitor/latest-checks.json` (`2026-10-26T07:34:39+08:00`) is FAIL with lesson interaction, saved-summary fixture, and multi-mode navigation browser failures; safe pytest snapshot is PASS (`155 passed, 1 deselected`).
- **Independently reproduced defect:** The lesson interaction aggregate depends on `vector_clipping_ui_ok`, `vector_three_math_ok`, `vector_four_ui_ok`, and `vector_four_math_ok`; its report detail omitted those values. This prevents localization when one of those checks fails.
- **Fix:** Added the four vector check outcomes to the emitted diagnostic detail. The other browser failures are not yet independently localized and remain open.
- **Acceptance evidence:** The focused four-vector clipping test passes (`1 passed`) and asserts displayed direction cosines of `1.0000` and `0.9430`; JS syntax, monitor/test AST, and scoped diff checks pass. Latest JSON is pre-change and no browser rerun was done.
- **Milestone advanced:** Four-component clipping teaching quantifies direction change via cosine similarity for global norm and component clipping. Synthetic arithmetic only; no training/model-quality conclusion.
- **Next checkpoint:** Browser-only monitor run without training smoke or locked-test UI, then capture fresh selector/state evidence for the remaining saved-summary and Guided navigation failures at desktop and 390px.
## 2026-10-26 — Saved-summary browser fixture false failure

- **Evidence:** Latest AGY snapshot `2026-10-26T08:09:34+08:00`, check `跨標的方向與幅度讀圖練習` reports `已保存摘要 fixture=False`; overall monitor FAIL. The snapshot's safe pytest was `155 passed, 1 deselected`.
- **Reproduction:** `savedComparisonCompatibility()` returns `不可直接排名：至少一份紀錄未保存 next-close 目標協定...` when legacy execution metadata is absent. The browser fixture searched for `未保存 next-close 目標協定`, which is not a substring because `目標協定` is preceded by `至少一份紀錄`.
- **Fix:** Updated the fixture to assert the actual complete warning phrase. This corrects an acceptance predicate; it does not alter product compatibility behavior.
- **Verification:** Focused pytest `2 passed, 69 deselected`; `node --check web/app.js`; Python AST parsing for monitor/tests; scoped `git diff --check` all pass. Latest AGY JSON remains pre-change evidence, so browser acceptance is not claimed.
- **Other current FAILs:** Lesson interaction and multi-mode navigation are not resolved by this predicate fix; next checkpoint is fresh browser-only reproduction with state/locator details, followed by desktop/390px review. No protected holdout or `final-test-*.json` was accessed; no final test, training, refresh, deployment or publication occurred.
## 2026-10-26 maintenance review: loss predicate and clipping sweep

- **Review input:** `artifacts/regression-monitor/latest-checks.json` at `2026-10-26T09:19:58+08:00` reports overall FAIL. The recorded safe pytest snapshot is `156 passed, 1 deselected`; browser FAIL groups are lesson interactions, saved-summary fixture, and multi-mode navigation.
- **Confirmed defect:** The browser lesson predicate expected updated loss `9` when `w=2`, `g=0.5`, and `η=10`. The current update computes `w=-3`, giving `(w-1)^2=16`; the stale expected value caused the lesson group failure. Corrected the predicate to 16 and exposed four previously omitted subchecks in its detail string. A suspected strict-float issue for the two-step momentum fixture was tested directly in Node; both values compare exactly equal, so that change was reverted.
- **Bounded roadmap progress:** The clipping lesson now updates a four-limit comparison using the current `w`, `g`, and `η`; its default rows show clipped gradients `0, 0.5, 1, 4` and weights `2, 1.95, 1.9, 1.6`. Acceptance and guide updated. Synthetic math only, not a training or model-quality result.
- **Verification:** Focused acceptance `3 passed, 69 deselected`; safe suite `157 passed, 1 deselected`; `node --check web/app.js`, monitor/test AST parsing, and scoped `git diff --check` passed. No post-change browser result is claimed.
- **Next checkpoint:** Browser-only checks excluding training smoke and locked-test UI; investigate the remaining saved-summary and lesson interaction failures; inspect desktop and 390px. Stock coverage remains local 10/10 pending authorized sources; live cross-symbol comparison needs compatible ordinary OOF summaries.
# Maintenance finding — 2026-10-26 guided fixture state leak

- **Evidence:** Latest review snapshot at 11:08:57+08:00 shows the multi-mode browser check failing although next/back reads `1→2→1`; saved-summary and other checks pass in that snapshot. Snapshot is pre-fix.
- **Root cause reproduced in monitor code:** The later fixture reset lesson index but retained the tab saved by earlier checks and the loaded active-tab variable. This made the guided state/resume assertions depend on prior interactions.
- **Change:** Reset `savedLearningProgress.tabId` and `activeLearningTabId` to `tabGuided` alongside lesson index before rendering; expose resume-reset state in diagnostic detail. Added source-contract coverage.
- **Verification:** Focused 6 passed / 70 deselected; safe suite 161 passed / 1 deselected; JS syntax, Python AST and scoped diff checks pass. Fresh browser evidence remains outstanding.
- **Roadmap progress:** Step 20 momentum lesson now gives a gradient-reversal calculation (`1.45`, `−2`, `β=.9`, `η=.1` → velocity `−.695`, weight increase `.0695`), with executable copy acceptance. Synthetic teaching only.
- **Next:** Browser-only monitor acceptance without training smoke or locked-test UI; inspect fresh navigation detail. Popular-stock expansion needs an authorized data source; cross-symbol magnitude needs compatible ordinary OOF summaries.

## 2026-10-26 11:44 AGY review: Guided next/back

- **Observed failure:** latest check reports `多模式學習互動` FAIL only for Guided next/back; detail shows start 1, next 2, back 1. Other browser lesson interactions pass, safe pytest snapshot is 161 passed and 1 deselected.
- **Review finding:** The reported transition is `1→2→1`, so browser navigation itself ran. The aggregate also checks lesson catalog content, summary count, resume state and panel visibility, but the JSON does not identify which conjunct failed. I could not independently reproduce a concrete application defect without a browser rerun. The fixture has been hardened to select/await Guided before reset and to verify visibility after Back; this remains harness hardening, not a confirmed root-cause fix.
- **Change:** Select Guided and wait until selected/visible before resetting the monitor-only state; wait for step 2 and require Guided to remain visible after Back. Add an executable regression assertion for input-gradient sensitivity to the related two-input lesson.
- **Status:** 11:44 JSON is pre-change. Focused pytest `2 passed, 74 deselected`; safe suite `161 passed, 1 deselected`; JS syntax, monitor/test AST, and scoped diff checks pass. No user learning progress persistence is changed. Browser and responsive acceptance remain pending; use a browser-only route excluding training smoke and locked-test UI.


## Scheduled maintenance update (2026-10-26, Guided failure diagnostics)

- **Latest AGY evidence:** `artifacts/regression-monitor/latest-checks.json` at `2026-10-26T12:21:05+08:00` has one FAIL: multi-mode learning interaction. It records navigation `1→2→1`, while the aggregate also includes catalog, summary, resume and visibility conditions.
- **Highest-priority reproducible defect:** Current `scripts/regression_monitor.py` output omitted several aggregate conjuncts, and labeled the reset-hidden resume notice twice. Thus a failing aggregate could not identify its failed condition; the latest detail only exposed navigation values and unrelated checks. This is a monitor observability defect, independently confirmed by source. No product navigation fault is inferred.
- **Exact change / user-visible feature:** The failure detail now separately reports guided visibility, catalog acceptance, summary-step acceptance, actual resume notice, and reset-hidden notice. That makes the browser check actionable while preserving its pass/fail conditions.
- **Roadmap advance:** No learning or stock-coverage milestone was safely completed this turn; the bounded progress is improved diagnostic visibility for the existing Guided-learning acceptance path.
- **Verification:** Focused Guided monitor contract `2 passed, 74 deselected`; `node --check web/app.js`, monitor Python AST parsing, and `git diff --check` passed. `py_compile` could not write its bytecode cache outside the project (PermissionError); no browser rerun is claimed. The AGY JSON is pre-change.
- **Remaining / next checkpoint:** Run the focused monitor contract and safe suite; then run browser-only Guided acceptance with training smoke and locked-test UI excluded, and use the new detail to isolate any remaining false conjunct. Local popular-stock coverage remains 10/10; expansion needs an authorized source. No locked holdout/final-test data accessed or modified; no final test, market refresh, training, deployment or publication.
# 2026-10-26 maintenance review: stale Guided catalog predicates

- **Review evidence:** `latest-checks.json` at `2026-10-26T12:54:36+08:00` reports multi-mode learning FAIL with navigation `1→2→1` but catalog false; safe pytest snapshot is `161 passed, 1 deselected`. Popular-stock local coverage is 10/10; training smoke and locked-test UI were skipped, isolation passed.
- **Reproduction / defect:** Executed the current `LESSONS` declaration in Node and compared the relevant entries to the browser predicate. The monitor expected `鏈鎖律` in lesson 12's title and obsolete titles for lessons 14 and 15; all three checks are false against the current catalog. This explains `課程目錄=False` without implicating product navigation.
- **Fix:** Aligned the three monitor title predicates to `反向傳播`, `觀察 ReLU 如何傳遞梯度`, and `方向一致性和幅度誤差`. Added a source/renderer regression test.
- **Roadmap progress:** The two-input neuron readout now shows each weighted contribution before their sum, making the forward pass auditable by learners. Synthetic default `1.00−0.40+0.20=0.80`; changing x₁ to 4 changes its contribution to 2.00 and z to 1.80. Guide and executable acceptance updated; no training or model-quality claim.
- **Verification / limits:** Focused `2 passed, 75 deselected`; safe suite `162 passed, 1 deselected`; synthetic regression PASS with 2,484 generated samples/four folds; JS syntax, Python AST, and scoped diff checks PASS. No browser rerun; latest JSON is pre-edit evidence.
- **Next checkpoint:** Verify Guided catalog/navigation at desktop and 390px in browser-only mode excluding training smoke and locked-test UI. Popular-stock expansion awaits an authorized source; real cross-symbol magnitude reading requires compatible ordinary OOF summaries. No holdout/final-test access, final test, refresh, training, deployment, or publication.
## Scheduled maintenance update (2026-10-26, step-17 contribution shares)

- **Latest review:** `latest-checks.json` at `2026-10-26T13:30:36+08:00` reports FAIL for report/interval interactions and Guided navigation; the explicit step-17 multi-input forward check is false. Safe pytest snapshot: `162 passed, 1 deselected`; local stock coverage: 10/10.
- **Concrete defect:** Current-source comparison reproduced a stale string predicate: monitor expected `z = w₁x₁ + w₂x₂ + b = 0.80`, while the renderer displays the listed contribution terms followed by `z=0.80`. This caused a false browser failure.
- **Change:** Aligned the monitor predicate with `z=0.80` and expanded its checks for signed shares and zero-sum state. The visible step-17 output now shows each signed contribution as a share of z, and explicitly says the ratio is undefined when z is zero. Guide and Node-backed renderer acceptance updated.
- **Roadmap:** Advanced a bounded synthetic neural-network learning step. Default values yield 125%, −50%, and 25%; zero-sum input yields an undefined ratio notice. No model-quality claim.
- **Verification:** Focused pytest `2 passed, 75 deselected`; safe suite `162 passed, 1 deselected`. No post-change browser or viewport run; latest JSON remains pre-change.
- **Next:** Browser-only desktop/390px check, excluding training and locked-test UI; trace remaining Guided/report failures. Stock expansion needs an authorized data source; cross-symbol magnitude work needs comparable ordinary OOF summaries.

## 2026-10-26 maintenance review: Guided catalog aggregate remains unlocalized

- **Evidence:** Latest AGY snapshot at `2026-10-26T14:41:02+08:00` reports multi-mode learning FAIL. It shows next/back `1→2→1` and `課程目錄=False`, but reports only the aggregate catalog result.
- **Reproduction status:** Current catalog source and predicate were inspected; the report does not identify the false conjunct, and no concrete application defect was independently reproduced. No product fix is asserted. Fresh browser-only per-conjunct evidence is the next step.
- **Roadmap change:** Step-21 activation comparison now names the greatest local derivative dynamically: z=2 identifies ReLU; z=−2 identifies Sigmoid. The lesson guide and executable renderer test were updated.
- **Verification:** Focused tests `2 passed, 77 deselected`; `node --check web/app.js`, AST parsing, and scoped `git diff --check` pass. No fresh browser or responsive result; AGY JSON is pre-change.
- **Remaining:** Localize and correct the actual Guided catalog predicate failure. Stock coverage remains 10/10 pending authorized data; compatible ordinary OOF summaries remain a prerequisite for cross-symbol magnitude instruction. No holdout/final-test data accessed, final test, refresh, training, deployment, or publication.

## 2026-10-26 maintenance review: no current reported failure; batch-gradient interpretation

- **Review evidence:** Latest AGY snapshot (`2026-10-26T17:03:06+08:00`) is overall PASS, including the Guided learning group and safe pytest result (`167 passed, 1 deselected`). No failure in this check was independently reproducible as a current defect.
- **Exact change:** Extended the step-19 batch-gradient calculator and readout with `|Σgᵢ| / Σ|gᵢ|`; zero total magnitude returns an undefined ratio. Added monitor acceptance for mixed, fully canceled, and all-zero gradients, and renderer regression coverage.
- **Roadmap increment:** This provides an observable synthetic explanation of batch-gradient cancellation: default `(-2,4,1,1)` → 0.5; `(-1,1,0,0)` → 0; `(1,1,1,1)` → 1; all zeros → undefined. It is not training or model-quality evidence.
- **Verification:** Focused test `1 passed`; safe suite `167 passed, 1 deselected`; JS syntax, Python AST, and scoped diff checks pass. Latest AGY JSON is pre-change; no new browser or desktop/390px acceptance is claimed.
- **Next checkpoint:** Browser-only Guided check for this readout at desktop and 390px, excluding training smoke and locked-test UI. Popular-stock coverage remains 10/10 pending an authorized source; real cross-symbol magnitude reading requires compatible ordinary OOF summaries. No holdout/final-test data access, final test, market refresh, training, deployment, or publication.
## 2026-10-26 maintenance review: Guided catalog clause 61 and sample influence

- **Review evidence:** Latest AGY JSON (`2026-10-26T18:14:00+08:00`) reports one failure in multi-mode learning, catalog clause 61. The rest of browser checks pass; safe pytest snapshot is `167 passed, 1 deselected`, and holdout isolation passes. Training smoke and locked-test UI are skipped.
- **Reproduction / defect:** Clause 61 expects a fixed string for the default editable batch-gradient result. The monitor had not reset the editable inputs or rerendered the output before checking, allowing browser state to leave the result text stale and cause a false failure.
- **Fix:** Reset the six batch controls to declared defaults and rerender before catalog assertions. Tie the expected copy to the computed leave-one-out value and sample identity.
- **Roadmap progress:** Step 19 now tells the learner which individual gradient most changes the current batch mean when removed, and shows the removed gradient, new mean, and signed change. For `(-2,4,1,1)`, removing sample 1 (`−2`) changes the mean from `1` to `2` (`+1`). Ties select the first sample. This is synthetic batch sensitivity only, not a claim about data importance or model quality.
- **Verification:** Focused `2 passed`; safe suite `167 passed, 1 deselected`; JS syntax, monitor/test AST, and scoped diff checks pass. No browser rerun or desktop/390px verification is claimed; the AGY snapshot predates the fix.
- **Next:** Run browser-only Guided acceptance at desktop and 390px, excluding training smoke and locked-test UI. Popular-stock expansion needs an authorized source; actual cross-symbol magnitude reading needs comparable ordinary OOF summaries. No protected observations or `final-test-*.json` were accessed, modified, or consumed; no final test, market refresh, training, deployment, or publication.

## Scheduled maintenance update (2026-10-26, defect triage and gradient-descent lesson)

- **Review input:** `artifacts/regression-monitor/latest-checks.json` at `2026-10-26T18:49:56+08:00` reports overall PASS. Current reported checks provide no concrete failure to repair; relevant current calculator source was inspected and no higher-priority defect was independently reproduced. No defect fix is claimed.
- **Exact implementation:** Added Guided lesson 23 with a live multi-step gradient-descent trace. For synthetic `L(w)=(w−1)²`, defaults `w₀=3`, `η=0.25`, four updates yield weights `3, 2, 1.5, 1.25, 1.125` and losses `4, 1, 0.25, 0.0625, 0.015625`. At `η=1`, the weight oscillates between 3 and −1 while loss stays 4. Inputs are constrained to 1–10 steps and `η∈[0,1]`; invalid values are rejected.
- **Roadmap / acceptance:** This advances the unfinished neural-network learning objective through a visible and adjustable lesson, updates the learning guide, and adds browser-monitor and executable acceptance. The overall learning milestone remains incomplete. Values are synthetic and do not support model-quality claims.
- **Verification:** Focused tests `3 passed, 80 deselected`; learning-focused selection `25 passed, 58 deselected`; combined learning/data-guard/UI selection `30 passed, 68 deselected`; JS syntax, Python AST parsing, and scoped `git diff --check` passed. No post-change browser/viewport run; latest AGY JSON is pre-change.
- **Remaining / next checkpoint:** Verify lesson 23 in browser at desktop/390px, with training smoke and locked-test UI excluded. Local popular-stock coverage is 10/10; expansion awaits authorized source data. Genuine cross-symbol magnitude instruction needs comparable ordinary OOF summaries. No holdout/final-test access, final test, market refresh, training, deployment, or publication.
## 2026-10-26 scheduled maintenance: gradient-descent learning-rate comparison

- **Review / defect:** Latest AGY check JSON (`2026-10-26T19:28:53+08:00`) is PASS. Current code/check review did not reproduce a concrete defect; no fix is claimed. Training smoke and one-time locked-test confirmation UI remain intentionally skipped.
- **User-visible progress:** Guided step 23 now compares loss trajectories for η=0.25, 0.5, and 1 at a shared start weight and step count. With `w₀=3` and four updates, the paths are `4→1→0.25→0.0625→0.0156`, `4→0→0→0→0`, and `4→4→4→4→4`. Invalid shared inputs produce a clear prompt. Guide and browser-monitor acceptance updated.
- **Evidence:** Focused gradient-descent test `1 passed, 82 deselected`; safe suite `168 passed, 1 deselected`; `node --check web/app.js` and scoped `git diff --check` pass. No browser or responsive screenshot rerun is claimed. These are synthetic calculations, not model-quality evidence.
- **Next checkpoint:** Confirm the three trajectories and shared input updates in browser at desktop and 390px, excluding training smoke and locked-test UI. Popular-stock growth requires an authorized local-data source; real cross-symbol magnitude teaching requires comparable ordinary OOF summaries. No holdout/final-test data, final test, market refresh, training, deployment, or publication.


## 2026-10-26 scheduled maintenance: finite-difference gradient lesson

- **Review evidence:** Latest AGY JSON at `2026-10-26T20:04:04+08:00` reports overall PASS. Its safe suite is `168 passed, 1 deselected`; desktop/390px, holdout isolation, and current browser learning checks pass. Real-data training smoke and one-time locked-test confirmation UI are skipped by policy. No current concrete defect reproduced from code or checks, so no bug fix is claimed.
- **Exact implementation:** Added `calculateFiniteDifferenceGradientCheck()` and a rendered result to Guided step 18. It estimates each of `∂L/∂w₁`, `∂L/∂w₂`, and `∂L/∂b` using `[L(θ+ε)-L(θ-ε)]/(2ε)` and reports the analytic value, numerical value, absolute difference, and maximum difference. It reuses the visible neuron inputs/target, validates finite inputs and ε in `[1e-8,0.1]`, and explains potential mismatch across the ReLU kink. Updated `web/index.html`, `docs/learning-guide.md`, and the monitor acceptance; added the executable test in `tests/test_system.py`.
- **Roadmap advance:** Bounded neural-network learning increment connects backpropagation's symbolic gradient to a numerical check. Default synthetic gradients `(-0.8,-0.4,-0.4)` match within `2.3e-15`; target 0 changes the first gradient to `3.2`. No training or model-quality claim.
- **Verification:** Focused renderer/calculation tests `2 passed`; safe selection `169 passed, 1 deselected`; `node --check web/app.js`, Python AST parsing, and scoped `git diff --check` pass. The AGY JSON is pre-change; browser/viewport rerun remains outstanding. During test development an expected changed gradient was first set to `1.6`; the squared-loss formula gives `3.2`, and the test/monitor acceptance were corrected before the passing rerun.
- **Next checkpoint / boundaries:** Run post-change browser-only Guided step-18 acceptance at desktop and 390px, excluding training smoke and locked-test UI. Popular-stock growth still needs an authorized source; real cross-symbol magnitude work needs comparable ordinary OOF summaries. No locked observations or `final-test-*.json` were read/changed/consumed; no final test, refresh, training, deployment, or publication.
## Scheduled maintenance update (2026-10-26, stale review references and loss-direction labels)

- **Highest-priority concrete defect:** The current AGY artifact at `2026-10-26T21:24:27+08:00` reports PASS, but maintenance records in `scratchpad.md` and `CODEX.md` identified older 20:45 and 19:28 JSON snapshots as latest. Timestamp comparison reproduces the stale review record. The current snapshot contains no failing product check; no product bug is claimed.
- **Exact correction and roadmap work:** Updated the latest-review references in both records. Guided step 23's existing three-rate comparison now also labels per-step loss direction. The default synthetic η=.25 path descends four times, η=.5 descends once then remains flat, and η=1 remains flat throughout. Updated app renderer, visible hint, learning guide, and renderer test.
- **Verification:** Focused gradient-descent pytest `1 passed, 83 deselected`; JS syntax, Python AST, and scoped diff checks pass. Browser/desktop/390px rerun not performed; latest AGY JSON is pre-change. Synthetic instructional values are not model-quality evidence.
- **Remaining / next checkpoint:** Browser-only step-23 acceptance at desktop and 390px, omitting training smoke and locked-test UI. Local popular-stock set remains 10/10 pending authorized source data; real cross-symbol magnitude learning needs compatible ordinary OOF summaries. No `final-test-*.json` or locked observations accessed, no final test, market refresh, training, deployment, or publication.

## Scheduled maintenance update (2026-10-27, duplicate diagnostics and signed error multiplier)

- **Latest review data:** `artifacts/regression-monitor/latest-checks.json` at `2026-10-27T01:33:36+08:00` reports overall PASS, the safe pytest snapshot `170 passed, 1 deselected`, popular-stock local coverage 10/10, and locked-data isolation PASS. Training smoke and one-time locked-test UI are SKIP. The JSON contains the same `殘差、逐折誤差與預測幅度校準圖` PASS record twice with identical detail.
- **Highest-priority concrete defect independently reproduced:** `scripts/regression_monitor.py` appended the exact same calibration diagnostic twice in the same browser flow (duplicate predicate assignment and duplicate `checks.append`). This yields a misleading duplicated check in generated reports despite an overall PASS. Removed the second assignment and append; added a regression assertion that this check is emitted once.
- **Roadmap increment:** Guided step 23 now reports the *signed* error multiplier `(w_next−1)/(w_current−1)` alongside distance. Positive values stay on the same side of the minimum; negative values reveal a crossing. The synthetic default remains `+0.5000`; for `c=2, η=0.5`, the first step `w=3→−1` visibly reports `−1.0000`, exposing boundary oscillation directly. Updated UI explanation, learning guide, browser predicate, and executable renderer acceptance. This advances neural-network learning only; it is not model training or quality evidence.
- **Verification:** Focused pytest `2 passed, 84 deselected`; synthetic regression PASS (2,484 generated samples, four folds); safe suite `171 passed, 1 deselected`; `node --check web/app.js`, Python AST parsing, and scoped `git diff --check` pass. These are post-change code/synthetic checks. No post-change browser or desktop/390px render was run; the 01:33 AGY snapshot is pre-change evidence.
- **Remaining / next checkpoint:** Run browser-only diagnostics and Guided step-23 checks at desktop and 390px, without training smoke or locked-test UI, and confirm there is exactly one calibration row and the negative signed multiplier is visible. The broader neural-network learning objective remains incomplete. Popular-stock expansion still requires an authorized local source; real cross-symbol magnitude learning needs comparable ordinary OOF summaries. No credentials, locked observations, or `final-test-*.json` were accessed or changed; no final test, refresh, training, deployment, or publication occurred.

## Scheduled maintenance update (2026-10-27, account sync verification feedback)

- **Review evidence:** Latest AGY JSON (`2026-10-27T02:44:12+08:00`) reports `2 failed, 174 passed, 1 deselected`, without test names. Re-running the exact safe selection reproduced one failure: `test_paper_account_timeline_only_maps_persisted_event_kinds` (`1 failed, 175 passed, 1 deselected`); the second reported failure did not reproduce.
- **Defect:** `app/paper.py` returns `historyVerification` after sync, but the UI discarded it, leaving users without the reason submitted history could be shorter when saved anchors were reused.
- **Fix / acceptance:** `web/paper.js` now adds a distinct room-message explanation for `verified_with_saved_anchors` and `verified`. It does not represent verification as a persisted trade event. Updated the executable source contract to assert both branches and preserve allowed persisted event kinds.
- **Roadmap increment:** Step 23's live learning-rate comparison displays the signed error multiplier `1−2ηc`. Acceptance covers c=1 factors `.50/0/−1` and c=2 factors `0/−1/−3`, alongside existing loss paths. Guide updated; synthetic instruction, not training/model-quality evidence.
- **Verification:** Focused `2 passed`; safe selection `176 passed, 1 deselected`; `node --check web/app.js`, Python AST parsing, scoped `git diff --check` pass. No browser/viewport rerun; AGY JSON predates edits.
- **Remaining / next:** Browser-only sync feedback and Guided step-23 check at desktop and 390px, omitting training smoke and locked-test UI. Popular-stock expansion needs an authorized source; cross-symbol magnitude lesson needs compatible ordinary OOF summaries. No secrets, protected data, or `final-test-*.json` accessed; no final test, refresh, training, deploy, or publish.

## 2026-10-27 — Patrol timing test contract drift

- **Severity / reproduction:** Latest AGY check at `2026-10-27T03:57:46+08:00` reports one safe pytest failure. Reproduced `test_walk_interaction_uses_a_clear_foreground_lane_and_a_slow_ping_pong_route`: the assertion searched for 6200/2600 ms callback strings, while current code waits 6260/2660 ms, adding 60 ms after transitions.
- **Fix:** Updated the test contract to current buffered callback values and documented the transition buffer. No application timing changed.
- **Evidence:** Focused test `1 passed`; safe suite `177 passed, 1 deselected`; JS syntax and scoped diff check pass.
- **Roadmap:** No feature milestone advanced in this pass. Next checkpoint is a bounded neural-learning lesson increment with observable acceptance, followed by browser-only desktop/390px verification. Popular-stock expansion awaits authorized data; real cross-symbol magnitude learning needs comparable ordinary OOF summaries. No protected data/final-test access, final test, refresh, training, deployment, or publication.

## 2026-10-27 — Step-23 overflow recovery was unclear

- **Severity / reproduction:** The latest AGY check (`2026-10-27T04:32:55+08:00`) is PASS and does not list this edge case. Directly evaluated the current calculator with finite values `startWeight=1e308`, `η=1`, `steps=10`, `curvature=5`; the update exceeds JavaScript's numeric range and the calculator correctly rejects the trajectory, but the displayed prompt only described ordinary finite/range validation.
- **Correction:** Kept the fail-closed calculator behavior and added visible guidance that explains numeric-range overflow and suggests reducing the starting weight or learning rate. The learning guide now documents the boundary. Added executable acceptance that the extreme finite input returns no trace and that recovery guidance is present.
- **Verification:** Focused pytest `1 passed, 86 deselected`; safe suite `177 passed, 1 deselected`; `node --check web/app.js`, Python AST parsing, and scoped `git diff --check` passed. No fresh browser render; latest AGY snapshot is pre-change.
- **Next:** Verify the rendered recovery guidance at desktop and 390px through browser-only step-23 acceptance, omitting training smoke and locked-test UI. No model-quality claim.

## 2026-10-27 — review snapshot failure not reproduced; selected-rate lesson update

- **Review evidence / defect disposition:** Latest AGY check at `2026-10-27T05:10:32+08:00` reports pytest `1 failed, 176 passed, 1 deselected` but omits the test name. Re-running the safe pytest selection before and after edits yielded `177 passed, 1 deselected` each time. The reported failure is not independently reproducible from current code/checks; no source defect fix is claimed.
- **Roadmap advance:** Guided step 23 now reports the active learner-selected `ηc`, signed error multiplier `1−2ηc`, and matching dynamics label. Acceptance covers default `η=.25,c=1` (non-crossing convergence), `η=.75,c=1` (alternating convergence), and `η=0` (no update). This is a bounded synthetic learning interaction, not a model-quality result.
- **Verification:** Focused test `1 passed, 86 deselected`; safe suite `177 passed, 1 deselected`; `node --check web/app.js`, monitor/test AST parsing, and scoped `git diff --check` pass. No browser/desktop/390px rerun is claimed.
- **Next:** Keep the broader neural-network objective incomplete and verify step 23 in a browser at desktop and 390px, excluding training smoke and locked-test UI. Popular-stock expansion awaits an authorized source; genuine cross-symbol magnitude teaching needs comparable ordinary OOF summaries. No credentials, locked observations, or `final-test-*.json` accessed; no final test, refresh, training, deployment, or publication.

## 2026-10-27 — Direction-conditioned magnitude lesson

- **Review / defect:** Latest supplied AGY snapshot (`2026-10-27T05:48:58+08:00`) is overall PASS with safe pytest `177 passed, 1 deselected`; no FAIL/WARN. It reports popular-stock coverage 10/10 and locked-data isolation PASS; training smoke and locked-test confirmation UI are SKIP. No higher-priority current product defect was independently reproduced, so none is claimed.
- **Roadmap feature:** Guided step 15 previously showed only one sample's direction/magnitude and zero-return baseline difference. It now accepts paired comma-separated synthetic values and separately reports actual-up and actual-down group MAE, matching zero-return baseline MAE, and direction-error count. Zero-return cases are excluded from both groups; empty groups and malformed/unequal inputs have explicit output.
- **Acceptance example:** Predictions `(0.6,-0.4,0.1)` against actual `(0.2,-0.2,-0.1)` produce up n=1 MAE 0.40 pp vs baseline 0.20 pp; down n=2 MAE 0.20 pp vs baseline 0.15 pp and one direction error. This advances a bounded magnitude-reading learning subtask only; synthetic values do not establish model quality.
- **Verification:** Focused test `1 passed, 86 deselected`; safe suite `177 passed, 1 deselected`; `node --check web/app.js`, monitor/test AST parse, and diff check pass. No browser rerun; latest AGY is pre-change.
- **Next checkpoint / boundaries:** Browser-only lesson-15 acceptance at desktop and 390px, with training smoke and locked-test UI excluded. Popular-stock expansion awaits authorized local data; real cross-symbol magnitude learning needs comparable ordinary OOF summaries. No credentials, locked observations, or `final-test-*.json` accessed/changed/consumed; no final test, refresh, training, deployment, or publication.
## 2026-10-27 06:30 AGY report: false step-15 MAE failure

- **Severity:** P2 test/monitor correctness; no product defect.
- **Evidence:** The report showed step 15 false. The renderer's executable synthetic contract returns up MAE 0.40 pp and down MAE 0.20 pp for `(predicted=.6,-.4,.1; actual=.2,-.2,-.1)`. The monitor expected down MAE 0.15 pp, which is inconsistent with its two errors (0.20, 0.20).
- **Fix:** Changed the browser predicate expectation from 0.15 to 0.20 pp. The only reported failure is explained by this incorrect assertion; the report's pytest snapshot was 177 passed / 1 deselected.
- **Regression evidence:** Corrected predicate source and renderer acceptance pass; safe suite is 178 passed / 1 deselected. Snapshot is pre-fix and no fresh browser monitor run was performed.
- **Related roadmap change:** Step 18 now contrasts first-order predicted loss with recomputed loss for synthetic SGD updates. Detailed acceptance and next checkpoint are recorded in `scratchpad.md` and `docs/project-status-and-goals.md`.

## 2026-10-27 06:30 AGY report: false step-15 MAE failure

- **Severity:** P2 monitor correctness; no product defect.
- **Evidence:** The report showed step 15 false. The renderer's executable synthetic contract returns up MAE 0.40 pp and down MAE 0.20 pp for `(predicted=.6,-.4,.1; actual=.2,-.2,-.1)`. The monitor expected down MAE 0.15 pp, inconsistent with its two errors (0.20, 0.20).
- **Fix:** Changed the browser predicate expectation from 0.15 to 0.20 pp. Product calculation was already correct; report pytest snapshot was 177 passed / 1 deselected.
- **Regression evidence:** Corrected predicate source and renderer acceptance pass; safe suite is 178 passed / 1 deselected. Snapshot is pre-fix; no fresh browser monitor run was performed.
- **Related roadmap change:** Step 18 now contrasts first-order predicted loss with recomputed loss after synthetic SGD updates. Details and next checkpoint are recorded in `scratchpad.md` and `docs/project-status-and-goals.md`.
## 2026-10-27 08:22 CST — False step-18 learning check and blank-rate acceptance

- **Severity:** P2 regression-monitor correctness; step-18 calculation itself is correct.
- **Evidence:** Latest AGY snapshot (`2026-10-27T08:20:07+08:00`) fails the step-18 browser predicate. Current source executes η=0.5 as first-order estimate −0.4400 and recomputed squared loss 1.0000; the fixture expected −0.9200 and 4.8400, which are the η=1 outputs.
- **Fix:** Split browser acceptance into η=0.5 and η=1 assertions. Also reject an empty learning-rate field, which JavaScript otherwise converts to zero; regression acceptance requires the invalid-input message.
- **Evidence after correction:** Focused test `2 passed, 87 deselected`; safe suite `179 passed, 1 deselected`; JS syntax, Python AST, and scoped diff checks pass. Browser acceptance visibly confirmed η=.5, η=1, and blank-rate rejection at desktop 1504×1046 and mobile 390×844. The browser was restored to step 1 and its default viewport.
- **Roadmap:** Step 18 now explicitly contrasts the two rates and rejects blank input. This is synthetic instruction and interaction robustness, not training or model-quality evidence. The broader neural-network milestone remains incomplete.
- **Remaining / next checkpoint:** The broader learning milestone stays open; stock expansion needs an authorized source and real cross-symbol magnitude teaching needs comparable ordinary OOF summaries. Refresh the safe review snapshot using browser-only checks that exclude training smoke and locked-test UI. No protected-data access, final test, data refresh, training, deployment, or publication.


## Maintenance review (2026-10-27, latest AGY snapshot and Adam lesson)

- **Defect triage:** Latest review snapshot `2026-10-27T17:31:03+08:00` is PASS (179 passed / 1 deselected); popular-stock coverage 10/10 and direction/magnitude checks pass; holdout isolation passes. Training smoke and one-time locked-test UI are skipped. No concrete current defect was independently reproduced from the supplied checks and current code. No defect fix is claimed.
- **Roadmap work:** Added Guided step 25 to show two-step SGD/Adam behavior under a reversed second gradient. For synthetic defaults `2,-1,.1,.9,.999`, Adam's second-step moments are `.0800/.004996`, corrected moments `.4211/2.4992`, and weights `1→.9→.8734`; SGD reaches `.9` after its second step. Empty and invalid inputs are rejected. This does not connect to training or support model-quality claims.
- **Evidence:** Focused acceptance `1 passed, 88 deselected`; safe suite `179 passed, 1 deselected`; JS syntax, Python AST, and diff checks pass. Initial new assertion had an incorrect aligned-gradient expectation; corrected to `.3800`. No post-change browser or desktop/390px check.
- **Remaining / next checkpoint:** Browser-only verify steps 18, 24, and 25 at desktop/390px without training smoke or locked-test UI. Keep the broader learning goal open. Stock expansion needs authorized local data; actual cross-symbol magnitude instruction needs comparable ordinary OOF summaries. No credentials, holdout observations, or final-test files accessed; no final test, refresh, training, deployment, or publication.

## Scheduled maintenance checkpoint (2026-10-27, Adam near-cancellation precision)

- **Review status:** Latest supplied AGY artifact `artifacts/regression-monitor/latest-checks.json`, `2026-10-27T21:38:43+08:00`, overall PASS, no FAIL/WARN; safe pytest snapshot 179 passed / 1 deselected. Popular-stock coverage 10/10 and locked-data isolation PASS. Training smoke and one-time locked-test UI are SKIP. Older leading review record was 21:03.
- **Reproduced defect:** Step 25 with `g₁=2`, `g₂=−1.79999`, `β₁=.9` computes `m̂₂≈5.26e-6`, nonzero and opposite to `g₂`. Four-decimal output rounded it to `0.0000` while the explanation stated that the directions opposed.
- **Correction:** Render near-zero nonzero moments in scientific notation in the summary and direction explanation; exact zero continues to use the exact-cancellation explanation. Added executable test and browser-monitor predicate; documented the case in the learning guide.
- **Roadmap advance / limits:** This advances the incomplete neural-network learning objective with a fixed-gradient Adam near-cancellation lesson. It is not training or model-quality evidence. Popular-stock expansion still requires an authorized local source; cross-symbol magnitude learning still needs comparable ordinary OOF summaries.
- **Verification / next checkpoint:** Focused test passed `1 passed, 88 deselected`; safe selection passed `179 passed, 1 deselected`; `node --check web/app.js`, Python AST parsing, and `git diff --check` passed. No browser viewport verification is claimed; after safe checks, inspect step 25 at desktop and 390px. No credentials, locked observations, or `final-test-*.json` accessed; no final test, refresh, training, deployment, or publication.

## Scheduled maintenance checkpoint (2026-10-27, Adam second-moment decomposition)

- **Review data / defect disposition:** `artifacts/regression-monitor/latest-checks.json` at `2026-10-27T22:14:51+08:00` reports overall PASS and no FAIL/WARN. Popular-stock local coverage is 10/10; direction/magnitude and holdout-isolation checks pass. Training smoke and locked-test UI are SKIP. No concrete current defect was independently reproduced from the review data and current source.
- **Roadmap implementation:** Step 25 now displays `β₂v₁` and `(1−β₂)g₂²` separately, then their sum `v₂`. Synthetic default gives `0.003996 + 0.001000 = 0.004996`; aligned `g₂=2` gives `0.003996 + 0.004000 = 0.007996`. This exposes how the second moment feeds the Adam denominator; it does not establish training or model quality.
- **Files / verification:** Updated `web/app.js`, `tests/test_system.py`, and `docs/learning-guide.md`. Focused test `1 passed, 88 deselected`; safe suite `179 passed, 1 deselected`; `node --check web/app.js`, Python AST parsing, and scoped `git diff --check` passed. The first focused run found a stale assertion for old copy, which was corrected. Browser rendering was not rerun.
- **Next checkpoint / safety:** Verify the step at desktop and 390px with reverse/aligned gradients, cancellation, blank input, and ε. Broad learning goal remains incomplete. Stock expansion awaits an authorized local source; comparable ordinary OOF summaries are needed for real cross-symbol magnitude learning. No credentials, locked observations, or final-test files accessed/changed/consumed; no final test, refresh, training, deployment, or publication.
## Scheduled maintenance checkpoint (2026-10-28, Adam comparison boundary and epsilon lesson)

- **Review / defect:** The requested latest AGY snapshot (`2026-10-28T00:54:26+08:00`) reports FAIL in browser rendering. Current code reproduced it: selecting valid β₂=0 made the renderer's fixed “no square-gradient memory” comparison call the normal calculator with β₂=0; that call returned null, and `.denominator2` caused a TypeError.
- **Exact correction:** `web/app.js` now computes the β₂=0 limiting comparison directly, preserving the normal input range for selected β₂. Executable acceptance renders that boundary and checks denominator 1.0000 and update 0.0421.
- **Roadmap progress:** Step 25 now displays a fixed-gradient ε comparison alongside the selected value, clarifying how ε changes the denominator and update. Default synthetic `g₁=2,g₂=−1`: ε=0 and ε=1e−8 show 1.5809 / 0.0266; ε=.1 shows 1.6809 / .0250. Guide updated. This is synthetic instruction, not training or model-quality evidence; the larger learning objective remains open.
- **Verification:** Focused tests `2 passed`; safe selection `180 passed, 1 deselected`; `node --check web/app.js`, Python AST parsing, and scoped `git diff --check` pass. Initial expected-value assertion was corrected from 1.5811 to the rendered 1.5809. No browser recheck after edits.
- **Next checkpoint / constraints:** Verify step 25 in browser at desktop and 390px, including β₂=0, ε, cancellation, blanks and underflow. Popular-stock expansion requires authorized local data; cross-symbol magnitude teaching requires comparable ordinary OOF summaries. No credentials, locked observations, or `final-test-*.json` accessed/changed/consumed; no final test, data refresh, training, deployment, or publication.
## Scheduled maintenance checkpoint (2026-10-28, momentum acceptance and learning-path comparison)

- **Review evidence:** Latest supplied AGY artifact `artifacts/regression-monitor/latest-checks.json` (`2026-10-28T02:05:18+08:00`) is FAIL. It reports the step-20 momentum subcheck false, safe pytest `2 failed, 178 passed, 1 deselected`, and a Loss pointer tooltip failure. Training smoke and the one-time locked-test confirmation UI are SKIP; locked-data isolation is PASS.
- **Highest-priority reproduced defect:** The current renderer's fixed-gradient β=0 comparison is `1.9000→1.8500`, but the monitor and two pytest assertions expected `1.8500→1.7000`. With initial velocity .5, β=0 makes the retained contribution zero; it does not remove the first gradient update. Default β=.9 gives `1.8550→1.6745`. Thus the current defect was an incorrect acceptance oracle, not momentum arithmetic.
- **Exact correction / roadmap increment:** Updated `scripts/regression_monitor.py` and `tests/test_system.py` to assert both actual visible paths separately. Updated the step-20 learning guide with the β=0 explanation and the caveat that fixed gradients isolate the equation; real training recalculates gradients after each update. This advances neural-network learning through an observable synthetic comparison only; it is not model-quality evidence. No milestone is declared complete.
- **Verification:** Safe pytest reproduced the supplied failure before edits (`2 failed, 178 passed, 1 deselected`). After correction, focused momentum tests pass (`3 passed, 87 deselected`) and safe suite passes (`180 passed, 1 deselected`). `node --check web/app.js`, Python AST parsing for monitor/tests, and scoped `git diff --check` pass. Browser evidence is pre-change; Loss pointer tooltip remains unresolved and no post-edit desktop/390px render is claimed.
- **Next checkpoint / constraints:** Re-run browser-only step 20 at desktop and 390px, then trace the Loss tooltip. Exclude training smoke and locked-test UI. Popular-stock coverage remains local 10/10; expansion needs authorized data. Real cross-symbol magnitude reading needs comparable ordinary OOF summaries. No credentials, locked observations, or `final-test-*.json` accessed/changed/consumed; no final test, market refresh, training, deployment, or publication.
## Scheduled maintenance checkpoint (2026-10-28 03:40 +08:00)

- AGY review `2026-10-28T03:20:50+08:00`: single FAIL is Loss pointer Tooltip; keyboard path works. Local popular-stock coverage is 10/10; holdout isolation PASS; training smoke and locked-test UI SKIP.
- Independently traced current SVG output: transparent `.loss-hit-area` with `pointer-events: all` followed all plotted elements and could cover their hit targets. Moved it behind curves, cursor, and points; added a test asserting generated layer order. Browser reproduction/fix acceptance remains pending.
- Advanced Adam step 24 with visible gradient-scale explanation and larger-gradient exercise. `g₁=4`: SGD update `0.4000`, `w₁=0.6000`; Adam update `0.1000`, `w₁=0.9000`. Synthetic instructional arithmetic only, no model-quality claim.
- Evidence: focused acceptance `2 passed, 89 deselected`; safe suite `180 passed, 1 deselected` with async validation job excluded. Monitor artifact predates edits; desktop/390px not rerun.
- Next checkpoint: browser-only pointer hover and Adam exercise at desktop/390px without training smoke or locked-test UI; actual cross-symbol magnitude requires comparable ordinary OOF summaries; stock expansion requires authorized local data. No credentials, protected observations, or `final-test-*.json` touched; no final test, refresh, training, deployment, or publication.


- **Latest review evidence:** `artifacts/regression-monitor/latest-checks.json` at `2026-10-28T03:56:27+08:00` reports FAIL. Its pytest snapshot is `180 passed, 1 deselected`; Loss chart pointer tooltip is the remaining named failure (keyboard navigation works). The older stale paper-walk test failure is no longer present; independently rerun safe selection passes. Popular-stock local coverage 10/10 and locked-data isolation PASS; training smoke and one-time locked-test UI SKIP.
- **Exact correction:** `web/app.js` now ignores touch `pointermove` in the Loss chart to keep scroll gestures from opening/updating the tooltip. Mouse hover and keyboard epoch navigation remain. Added executable Node-backed pytest for these cases in `tests/test_system.py`.
- **Milestone / verification:** Bounded predicted-magnitude chart interaction milestone advanced; broad neural learning remains incomplete and this is not model-quality evidence. Focused Loss tests `3 passed, 89 deselected`; safe selection `181 passed, 1 deselected`; JS syntax and scoped diff checks pass. The monitor's live mouse-hover failure has not been reproduced or resolved in browser.
- **Remaining / next checkpoint:** Browser-only reproduce the monitor hover failure and verify chart at desktop/390px, excluding training and locked UI. Popular-stock expansion needs authorized local data; real cross-symbol magnitude lesson needs comparable ordinary OOF summaries. No secrets, protected observations, or `final-test-*.json` accessed; no final test, market refresh, training, deployment, or publication.


## Scheduled maintenance checkpoint (2026-10-28, Adam retained-moment precision and gradient scale)

- **Review data:** `artifacts/regression-monitor/latest-checks.json` at `2026-10-28T05:43:37+08:00` reports PASS, `181 passed, 1 deselected`, popular-stock local coverage 10/10, and locked-data isolation PASS. Training smoke and one-time locked-test UI are SKIP. No failure is present in the supplied snapshot.
- **Independently reproduced defect:** The Adam step-25 direction explanation formatted the retained first moment with `toFixed(4)` when `g₂=0`. Current calculator inputs `g₁=0.00001`, `g₂=0`, `β₁=0.9` produce a nonzero `m̂₂≈4.74e-6`, but the prior text displayed `0.0000` while claiming the prior direction remained.
- **Exact fix and roadmap increment:** `web/app.js` now uses scientific notation for this small nonzero moment, consistent with its near-cancellation path. The same two-step exercise now interactively compares Adam and SGD after multiplying both gradients by 10 while holding β, η, and ε fixed; default synthetic values show Adam update `0.0266` and SGD `w₂=0.0000` versus its original `0.9000`. The UI and `docs/learning-guide.md` describe this as approximate Adam scale invariance when ε is small, not a universal property. This advances a bounded neural-network learning subtask only; it is synthetic arithmetic and no model-quality claim.
- **Changed files and verification:** Updated `web/app.js`, `tests/test_system.py`, `scripts/regression_monitor.py`, and `docs/learning-guide.md`. Focused Adam renderer acceptance: `1 passed, 91 deselected`. Safe project selection: `181 passed, 1 deselected`. `node --check web/app.js`, Python AST parsing for monitor/tests, and scoped `git diff --check` passed. The supplied monitor snapshot predates the edits; no post-change browser or desktop/390px rendering is claimed.
- **Remaining / next checkpoint:** Verify step 25 in browser at desktop and 390px, including tiny retained moment, zero gradient, ε, and 10× comparison; rerun only browser checks that skip training smoke and locked-test UI. Neural-network learning remains incomplete. Expanding local popular-stock coverage requires an authorized local data source; real cross-symbol magnitude instruction needs comparable ordinary OOF summaries. No credentials, protected observations, or `final-test-*.json` were accessed; no one-time final test, market refresh, training, deployment, or publication occurred.

## Scheduled maintenance update (2026-10-28, L2 lesson)

- **Defect status:** Latest provided monitor data at `2026-10-28T08:38:50+08:00` is PASS (`182 passed, 1 deselected`), with Loss tooltip and holdout isolation passing. Training smoke and locked-test UI are skipped. The supplied snapshot has no failures. While implementing the new calculator, a finite-input overflow was independently reproduced at `w=1e154, λ=1`: data loss and penalty are individually finite near `1e308`, but total loss overflows to Infinity. The calculator now rejects non-finite aggregate totals; monitor data predates this implementation.
- **Roadmap work:** Implemented guided lesson 26, a live L2 regularization calculation separating data gradient and penalty gradient, showing their sum and data/total loss before and after. Default synthetic case: data gradient 2, penalty gradient 0.4, total gradient 2.4, updated weight 1.76, total loss 1.4→0.8874. λ=0 returns the unregularized update 1.8. This advances neural-network learning only; it is not training or model-quality evidence.
- **Verification / next:** Focused executable acceptance passed (`1 passed, 93 deselected`); safe project selection passed (`183 passed, 1 deselected`); browser showed step 26 and λ=0 response; JS syntax, Python AST and scoped diff checks passed. Next run browser-only L2 monitor acceptance and inspect desktop/390px without training smoke or locked-test UI. Popular-stock expansion needs an authorized source; real cross-symbol magnitude comparison needs compatible ordinary OOF summaries. No credentials, locked observations, or final-test files accessed; no final test, refresh, training, deployment, or publication.
## Scheduled maintenance checkpoint (2026-10-28, 09:16 review and L2 direction reading)

- **Latest review / reproduced defect:** `artifacts/regression-monitor/latest-checks.json` at `2026-10-28T09:16:53+08:00` reports FAIL: the lesson aggregate fails subchecks for step 15 magnitude, step 19 batch gradients, and Adam steps 24–25. Current `web/app.js` has 26 lessons, but the four corresponding browser predicates in `scripts/regression_monitor.py` still required `LESSONS.length===25`; this alone makes those predicates false. The snapshot records 183 passed / 1 deselected, popular-stock local coverage 10/10, and locked-data isolation PASS. Training smoke and locked-test UI are SKIP.
- **Exact defect fix:** Updated the four stale lesson-count guards to 26 and added `test_guided_lesson_monitor_lengths_match_current_catalog` so a later lesson addition cannot silently keep these checks stale. No lesson math was changed for this defect.
- **Roadmap advance:** Guided step 26 now explains whether data and L2 penalty gradients reinforce or oppose each other, and which term controls the net update. The rendered synthetic cases cover aligned gradients at the defaults, `w=0.5, λ=0.5` where data dominates (`−1` vs `+0.5`), `λ=1.5` where regularization dominates (`−1` vs `+1.5`), and `λ=1` where they cancel. Updated the guide and routine browser predicate. This is a bounded neural-network learning increment, not training or model-quality evidence.
- **Implementation / verification:** Updated `scripts/regression_monitor.py`, `web/app.js`, `web/index.html`, `tests/test_system.py`, and `docs/learning-guide.md`. Focused checks passed `2 passed, 93 deselected`. Safe suite passed `184 passed, 1 deselected` (`public_api_and_async_validation_job` excluded). Renderer-backed Node acceptance checks the visible direction text; `node --check web/app.js`, Python AST parse, and scoped `git diff --check` passed. The supplied browser snapshot predates the edits; no live post-edit desktop/mobile rendering is claimed.
- **Remaining / next checkpoint:** Run a browser-only acceptance route that excludes training smoke and locked-test UI; inspect steps 15, 19, 24, 25, and 26, including the four corrected guards and L2 direction changes, at desktop and 390px. Neural-network learning remains incomplete. Popular-stock expansion beyond the existing 10/10 needs an authorized local source; real cross-symbol magnitude comparisons still need compatible ordinary OOF summaries. No credentials, locked observations, or `final-test-*.json` were read or changed; no final test, market refresh, training, deployment, or publication occurred.
## Scheduled maintenance checkpoint (2026-10-28 10:21 +08:00, L2 loss-direction reading)

- **Review and priority:** The latest review JSON (`2026-10-28T09:53:53+08:00`) is overall PASS with `184 passed, 1 deselected`; real-data training smoke and one-time locked-test UI are intentional SKIPs. No current review failure was independently reproduced. A lesson defect was reproduced while adding acceptance: comparing the full data-loss and total-loss direction labels always classified them as different, even when both decreased.
- **Fix and roadmap progress:** `web/app.js` now compares signed numeric changes and gives an explicit explanation when the two losses move differently. Step 26 now teaches overshooting: synthetic `w=2, λ=0.1, η=2` produces `w=−3.6`, with data loss `1→21.16` and total loss `1.4→22.456`. Updated the visible exercise in `web/index.html` and its guide. This advances the incomplete neural-network learning goal; it is synthetic arithmetic, not training or predictive-quality evidence.
- **Evidence:** Focused test passes (`1 passed, 94 deselected`); JavaScript syntax, Python AST parsing, and scoped diff checks pass. The test also verifies default loss direction, overshoot, invalid-input handling and finite overflow rejection. Post-edit browser rendering has not been checked.
- **Next checkpoint / boundaries:** Verify step 26 in browser at desktop and 390px. Popular-stock expansion beyond local 10/10 still needs an authorized source; real cross-symbol magnitude instruction needs compatible ordinary OOF summaries. No credentials, locked observations, or final-test files were read/written; no final test, data refresh, training, deploy, or publish occurred.
# Scheduled maintenance checkpoint (2026-10-28, L2 micro-gradient ratio sweep)

- **Latest review:** `artifacts/regression-monitor/latest-checks.json` at `2026-10-28T12:16:59+08:00` reports overall PASS and no FAIL/WARN. Local popular-stock coverage 10/10 and locked-data isolation PASS; training smoke and locked-test UI SKIP.
- **Highest-priority defect check:** No current reported failure reproduced. Directly exercised current classifier with opposing gradients `(2e-13, -1e-13)` and equal-magnitude control; outputs were `data` and `cancel`. The earlier absolute tolerance defect was already fixed and has an existing assertion, so no redundant change was made.
- **Exact roadmap advance:** Added a visible three-point micro-gradient ratio scan to guided lesson 26 and extended classifier result copy for penalty dominance. Fixed data gradient `2×10⁻¹³`; ratios 0.5, 1.0 and 1.5 yield total gradients `+1×10⁻¹³`, 0 and `−1×10⁻¹³`. Updated `web/app.js`, `web/index.html`, `scripts/regression_monitor.py`, `tests/test_system.py`, and `docs/learning-guide.md`. This is synthetic neural-network instruction, not model-quality evidence.
- **Verification / remaining:** `python3 -m pytest -q tests/test_system.py -k l2_regularization_lesson_calculates_data_and_penalty_gradients` passes (`1 passed, 94 deselected`). Browser rendering after edits is unverified. Next run the browser-only guided check at desktop and 390px, with training smoke and locked-test UI excluded. Neural-network learning remains incomplete; stock expansion needs an authorized local source and real cross-symbol magnitude instruction needs compatible ordinary OOF summaries. No credentials, locked observations, or `final-test-*.json` accessed/changed; no final test, data refresh, training, deploy, or publish.
# Scheduled maintenance checkpoint (2026-10-28, review and L2 lesson)

- **Latest review:** `artifacts/regression-monitor/latest-checks.json` timestamp `2026-10-28T12:52:39+08:00`, overall PASS, no FAIL/WARN. Local popular-stock coverage 10/10; locked-data isolation PASS; training smoke and locked-test UI SKIP.
- **Defect triage:** Re-ran current Adam two-step, L2 lesson, and lesson-count acceptance (`3 passed, 92 deselected`). No current defect independently reproduced. A manual arithmetic concern about the expected `−0.0902` penalty delta was checked with an independent Node calculation: `0.1×1.76²−0.1×2² = −0.09024`, confirming the current expected display is correct.
- **Exact change / roadmap advance:** `web/app.js` now includes the L2 penalty's movement in the direction explanation, including the case where data loss decreases while penalty rises but the total still decreases. `tests/test_system.py` checks exact component values and the mixed-direction case; `docs/learning-guide.md` records the arithmetic. This is a bounded synthetic neural-network learning increment, not training or model-quality evidence.
- **Verification:** Focused test `1 passed, 94 deselected`; safe suite `184 passed, 1 deselected`; JS syntax and scoped diff checks pass. Renderer acceptance also covers an unchanged L2 penalty (`λ=0`); no post-edit browser rendering is claimed.
- **Next checkpoint:** Inspect lesson 26 in browser at desktop and 390px through a route excluding training smoke and locked-test UI. Keep neural-network learning incomplete. Popular-stock expansion requires an authorized local source; real cross-symbol magnitude teaching needs comparable ordinary OOF summaries. No credentials, locked observations, or `final-test-*.json` accessed; no final test, refresh, training, deployment, or publication.

## Scheduled maintenance checkpoint (2026-10-28 13:32 +08:00, exact versus near L2 cancellation)

- **Latest review:** `artifacts/regression-monitor/latest-checks.json` at `2026-10-28T13:30:49+08:00` is PASS with no FAIL/WARN across 45 checks. Popular-stock local coverage is 10/10; locked-data isolation passes; training smoke and one-time locked-test UI are SKIP.
- **Highest-priority independently reproduced defect:** Despite the clean snapshot, current `classifyOpposingGradients` treated any magnitude difference within `1e-12 × max(|g_data|, |g_penalty|)` as exact cancellation. Synthetic opposing gradients `2e-13` and `−2e-13×(1+5e-13)` produced a nonzero net gradient (`−1e-25`) but were classified as `cancel`, falsely saying the update direction was zero.
- **Exact fix:** `web/app.js` now reserves `cancel` for exactly equal absolute magnitudes. Unequal terms are classified by the larger magnitude, and relative differences below 0.005 display in scientific notation so they do not round to `0.00`. Added an explicit near-cancellation row to the step-26 sweep. The rendered synthetic example reports a `−1.0e−25` net gradient and `5.0e−13` relative difference, penalty term dominant; exact equality still reports zero and exact cancellation.
- **Roadmap increment:** Advanced the visible neural-network learning milestone with a direct comparison between exact and near cancellation in the existing L2 gradient lesson. Updated `web/app.js`, `scripts/regression_monitor.py`, `tests/test_system.py`, and `docs/learning-guide.md`. This is synthetic formula teaching, not training or model-quality evidence.
- **Verification:** Focused acceptance passes (`1 passed, 94 deselected`); safe selection passes (`94 passed, 1 deselected`). `node --check web/app.js`, Python AST checks for monitor/tests, and scoped `git diff --check` pass. The first test run caught a wrong expected relative-difference string (`1e−13` instead of the computed `5e−13`); the expectation was corrected without weakening the check. Latest monitor JSON predates these edits; post-edit browser and desktop/390px rendering are not verified.
- **Remaining / next checkpoint:** Run the browser-only step-26 predicate and inspect exact/near cancellation plus default, λ=0, blank input, and overshoot at desktop and 390px; exclude training smoke and locked-test UI. Keep neural-network learning incomplete. Popular-stock expansion beyond local 10/10 still needs an authorized local source; real cross-symbol magnitude lessons need comparable ordinary OOF summaries. No credentials, protected observations, or `final-test-*.json` accessed/changed/consumed; no final test, market refresh, training, deployment, or publication.


## Scheduled maintenance checkpoint (2026-10-28 14:43 +08:00, L2 lesson predicate)

- **Review data / defect:** `artifacts/regression-monitor/latest-checks.json` at `2026-10-28T14:42:08+08:00` reports FAIL only on the aggregate learning-lesson check; its L2 subcheck is false. The current renderer's near-cancellation row is ratio 1.0 with relative difference `5.0e-13`, but `scripts/regression_monitor.py` expected `1.0e-13`. Focused renderer acceptance independently confirmed the renderer output, identifying a stale check.
- **Fix and learning increment:** Corrected the browser predicate to expect the emitted near-cancellation output and assert that gradient descent weight displacement opposes total-gradient direction. The visible step-26 sweep now explains zero movement for exact cancellation and a small movement for near cancellation. Updated the monitor, `web/app.js`, `tests/test_system.py`, and `docs/learning-guide.md`. Synthetic instruction only.
- **Verification:** `python3 -m pytest -q tests/test_system.py -k l2_regularization_lesson_calculates_data_and_penalty_gradients` -> `1 passed, 94 deselected`; `node --check web/app.js`, Python AST parse for monitor/tests, and scoped `git diff --check` pass. No post-edit browser or viewport verification is claimed.
- **Next checkpoint:** Browser-only step-26 acceptance at desktop and 390px, excluding training smoke and locked-test UI. Broader neural-network learning remains incomplete; stock expansion awaits an authorized local source, and cross-symbol magnitude learning needs comparable ordinary OOF summaries. No locked data or `final-test-*.json` access; no final test, market refresh, training, deployment, publication, or messaging.
## Scheduled maintenance review (2026-10-28 16:30 +08:00, activation target reachability)

- **Review data / failure status:** `artifacts/regression-monitor/latest-checks.json` at `2026-10-28T16:28:32+08:00` reports PASS across 45 checks with no FAIL/WARN. Local popular-stock coverage 10/10 and locked-data isolation pass; training smoke and locked-test UI are SKIP. No reported monitor failure was reproduced.
- **Independently reproduced defect:** Guided step 21 accepted any finite target, but its output did not say whether the target was in the range of each activation. The functions are bounded differently: Sigmoid `(0,1)`, Tanh `(-1,1)`, and ReLU `[0,∞)`. Thus `y=2` is unreachable for the first two and `y=0` is unreachable for Sigmoid/Tanh, but the learner saw only loss and gradients. Formula arithmetic remains correct.
- **Exact change / milestone:** `web/app.js` now returns per-activation reachability and renders 「目標在／不在輸出範圍」. `web/index.html` and `docs/learning-guide.md` describe ranges and boundary examples; the browser predicate and `tests/test_system.py` assert default, `y=2`, `y=0`, boundary and blank-input cases. This advances the incomplete neural-network learning milestone with synthetic, visible output; it is not model-quality evidence.
- **Verification:** Focused tests: `2 passed, 93 deselected`; `node --check web/app.js` and scoped `git diff --check` pass. No post-edit browser rendering at desktop or 390px is claimed; monitor JSON predates the change.
- **Next checkpoint:** Run safe browser-only step-21 acceptance at desktop/390px, excluding training smoke and locked-test UI. Keep the broader learning goal incomplete. Popular-stock expansion beyond 10/10 needs an authorized local source; real cross-symbol magnitude teaching needs comparable ordinary OOF summaries. No credentials, protected observations, or `final-test-*.json` accessed; no final test, refresh, training, deployment, or publication.

## Scheduled maintenance checkpoint (2026-10-28 17:07 +08:00, stable activation gradients)

- **Latest review evidence:** `artifacts/regression-monitor/latest-checks.json` at `2026-10-28T17:04:37+08:00` is PASS across 45 checks; no FAIL/WARN. The recorded safe suite is 184 passed, 1 deselected. Local popular-stock coverage is 10/10 and locked-data isolation passes; real-data training smoke and one-time locked-test UI are SKIP. This snapshot predates the current edits.
- **Highest-priority concrete defect reproduced and fixed:** The step-21 activation calculator used `s(1−s)` and `1−tanh²(z)`; at finite saturation inputs `z=40` and `z=20`, output rounding makes the activation equal 1 and falsely zeroes nonzero local gradients. `web/app.js` now uses stable equivalent exponential forms and displays tiny nonzero derivatives in scientific notation.
- **Roadmap milestone advanced:** Step 21 now exposes saturation-tail numerical precision. Synthetic examples show Sigmoid derivative `4.248e-18` at `z=40` and Tanh derivative `1.699e-17` at `z=20`; the guide explains that this does not remove practical vanishing gradients. Updated `web/app.js`, `web/index.html`, `scripts/regression_monitor.py`, `tests/test_system.py`, and `docs/learning-guide.md`. This is synthetic neural-network instruction, not training or model-quality evidence.
- **Verification:** Focused acceptance `2 passed, 93 deselected`; `node --check web/app.js`, Python AST checks for monitor/tests, and scoped `git diff --check` pass. No live browser, desktop/390px rendering, or refreshed monitor run is claimed.
- **Remaining / next checkpoint:** Verify step 21 at desktop and 390px for ordinary, positive/negative saturation, target boundaries, and blank input using browser-only checks; keep training smoke and locked-test UI excluded. Keep the broader neural-network objective incomplete. Popular-stock expansion beyond local 10/10 needs an authorized local source; genuine cross-symbol magnitude instruction needs comparable ordinary OOF summaries. No credentials, locked observations, or `final-test-*.json` were read or changed; no final test, market refresh, training, deployment, publication, or external messaging occurred.


## Scheduled maintenance checkpoint (2026-10-28 17:41 +08:00, activation-tail precision)

- **Latest AGY review / defect reproduced:** `artifacts/regression-monitor/latest-checks.json` at `2026-10-28T17:41:16+08:00` is FAIL only on 「多模式學習互動」; catalog clause indices 20 and 21 fail. Mapping them to the current predicate identifies the stable sigmoid/tanh tail-gradient checks. Independent Node evaluation returns `4.248354255291589e-18` at `z=40` and `1.6993417021166355e-17` at `z=20`; the monitor compared rounded reference literals with absolute tolerances smaller than the literals' rounding error. Local popular-stock coverage is 10/10 and locked-data isolation passes; training smoke and one-time locked-test UI are SKIP.
- **Exact defect fix:** `scripts/regression_monitor.py` now checks relative error `<1e-9` for both reference gradients, keeping numeric acceptance while avoiding false failures from rounded literals.
- **Roadmap advance:** Guided step 21 explains that inputs `+|z|` and `−|z|` have different Sigmoid/Tanh outputs but equal local derivatives. Synthetic UI acceptance covers `z=+40` and `z=−40`, requiring the same nonzero Sigmoid derivative (`4.248e-18`), opposite saturated outputs, and visible explanation. Updated `web/app.js`, `scripts/regression_monitor.py`, `tests/test_system.py`, and `docs/learning-guide.md`. This is synthetic neural-network instruction, not training or model-quality evidence.
- **Verification:** `python3 -m pytest -q tests/test_system.py -k activation_lesson_explains_largest_local_gradient` passes (`1 passed, 94 deselected`). Initial acceptance runs caught a missing result fixture property and an invalid test-local variable reference; the setup was corrected and the focused acceptance passes. Browser monitor and desktop/390px rendering were not run after the change; the supplied JSON remains pre-change evidence.
- **Next checkpoint / remaining:** Run safe browser-only guided acceptance at desktop and 390px for positive/negative saturation, target boundaries, and blank input, excluding training smoke and locked-test UI. Keep neural-network learning incomplete. Popular-stock coverage remains 10/10 pending an authorized local source; real cross-symbol magnitude instruction still needs comparable ordinary OOF summaries. No credentials, protected observations, or `final-test-*.json` were accessed or changed; no final test, market refresh, training, deployment, publication, or external messaging occurred.


## Scheduled maintenance checkpoint (2026-10-28 18:32 +08:00, activation-gradient direction)

- **Latest review:** `artifacts/regression-monitor/latest-checks.json` at `2026-10-28T18:16:37+08:00` is PASS with 184 passed / 1 deselected in the safe suite. Popular-stock coverage is 10/10 and locked-data isolation passes; training smoke and locked-test UI are SKIP. I independently inspected the current activation-tail calculation and reproduced no defect; no fix is claimed.
- **Roadmap increment:** Guided step 21 now states how gradient descent moves synthetic input `z`: positive squared-loss gradient lowers `z`, negative gradient raises it, and zero gradient leaves it unchanged. Renderer acceptance checks positive and negative cases; the learning guide documents the rule. This is synthetic neural-network instruction, not training or model-quality evidence.
- **Verification:** Focused acceptance `python3 -m pytest -q tests/test_system.py -k activation_lesson_explains_largest_local_gradient` passes (`1 passed, 94 deselected`); `node --check web/app.js` and scoped `git diff --check` pass. The supplied snapshot predates the edit; no post-edit browser or desktop/390px rendering is claimed.
- **Next checkpoint / limits:** Keep neural-network learning incomplete. Verify step 21 at desktop and 390px for positive, negative, zero and saturated gradients. Popular stocks remain 10/10 pending an authorized local source; real cross-symbol magnitude teaching needs compatible ordinary OOF summaries. No credentials, protected observations or `final-test-*.json` accessed/changed/consumed; no final test, market refresh, training, deployment or publication.
## 2026-10-28 — Step-21 saturated Sigmoid residual lost tail precision

- **Priority:** P2, visible learning arithmetic inconsistency.
- **Evidence / reproduction:** Current `calculateActivationComparison(40, 1)` uses a stable nonzero Sigmoid derivative (`≈4.248e−18`) but computes residual as `sigmoid-y`; the returned sigmoid rounds to 1, erasing its nonzero tail. Thus the displayed loss is rounded to `0.0000` and the old gradient was exactly zero despite a tail-aware derivative. The mathematical tail gives gradient `≈−3.610e−35`.
- **Fix:** `web/app.js` computes the Sigmoid residual directly from `exp(−|z|)` and uses it for both loss and gradient. Added renderer acceptance for positive saturated Sigmoid and negative saturated Tanh.
- **Verification:** `python3 -m pytest -q tests/test_system.py -k activation_lesson_explains_largest_local_gradient` → 1 passed, 94 deselected; JS syntax and scoped diff checks pass. Full suite and browser viewports remain unverified. The supplied 18:52 monitor snapshot predates the edit and reports no failures.
- **Roadmap / next:** This is a bounded synthetic neural-network learning increment, not model-quality evidence. Verify browser rendering at desktop and 390px. Do not change the milestone to complete; popular-stock expansion still needs an authorized local source, and cross-symbol magnitude instruction needs compatible ordinary OOF summaries.


## Scheduled maintenance checkpoint (2026-10-28 19:28 +08:00, ReLU negative-region learning)

- **Latest review and defect disposition:** `artifacts/regression-monitor/latest-checks.json` is timestamped `2026-10-28T19:27:12+08:00`, overall PASS with no FAIL/WARN; local popular-stock coverage is 10/10 and locked-data isolation passes. Training smoke and one-time locked-test UI are SKIP. I independently reproduced a visible teaching omission in the current activation lesson: at synthetic `z=-2, y=1`, ReLU's target is in range and squared loss is 1, but its local derivative and loss gradient are zero; the lesson gave no explanation that gradient descent cannot move this neuron out of the negative region. This is a bounded learning defect, not a model-quality issue.
- **Exact change and milestone advanced:** `web/app.js` now adds a ReLU negative-region note when `z<=0` and `y>0`, including the boundary convention at `z=0`. Updated `tests/test_system.py` to assert the negative-input and boundary explanation, and `scripts/regression_monitor.py` to check this UI case and report it independently as `ReLU 負區零梯度`. `docs/learning-guide.md` records the calculation and limitation. This advances the incomplete neural-network learning objective with an observable activation-gradient example. It is synthetic instruction only, not training or model-quality evidence.
- **Verification:** `python3 -m pytest -q tests/test_system.py -k activation_lesson_explains_largest_local_gradient` passed (1 passed, 94 deselected); `node --check web/app.js`, Python AST parse of monitor/tests, and scoped `git diff --check` passed. The supplied AGY snapshot predates these edits. Post-edit browser/desktop/390px rendering and the full suite are not verified.
- **Remaining / next checkpoint:** Keep the neural-network milestone incomplete. Run safe browser-only step-21 checks at desktop and 390px for `z=-2,y=1`, `z=0,y=1`, ordinary inputs, saturation, and blank input, excluding training smoke and locked-test UI. Popular-stock coverage remains 10/10; expansion needs an authorized local source. Real cross-symbol rise/fall magnitude instruction still needs comparable ordinary OOF summaries. No credentials, protected observations, or `final-test-*.json` were accessed/changed/consumed; no one-time final test, market refresh, training, deployment, publication, or external messaging occurred.

## Scheduled maintenance checkpoint (2026-10-28, Tanh tail precision)

- **Review data:** Latest supplied AGY snapshot `2026-10-28T20:02:03+08:00` is PASS across 45 checks with no FAIL/WARN. Popular stocks are 10/10 locally and locked-data isolation passes; training smoke and locked-test UI are SKIP.
- **Highest-priority defect:** Current Step-21 Tanh derivative used `exp(-2*abs(z))`. Independent Node evaluation showed a false zero at `z=370`, where the derivative remains representable as a subnormal (`≈1.68e−321`).
- **Fix / bounded milestone:** `web/app.js` now squares `exp(-abs(z))`, and renderer acceptance requires `1.680e-321` at `z=370`. `docs/learning-guide.md` explains why this avoids premature underflow and notes the eventual floating-point limit. This is synthetic neural-network numerical instruction, not model-quality evidence.
- **Verification:** Focused test `1 passed, 94 deselected`; `node --check web/app.js`, Python AST parsing for tests/monitor, and scoped `git diff --check` pass. Supplied monitor predates edits; browser/desktop/390px and full-suite checks remain outstanding.
- **Next checkpoint / safety:** Run browser-only Step-21 acceptance at desktop and 390px; exclude training smoke and locked-test UI. Keep broader learning incomplete. Stock expansion still needs an authorized local source; cross-symbol magnitude teaching needs comparable ordinary OOF summaries. No credentials, protected observations, or final-test files accessed; no final test, market refresh, training, deployment, or publication.
# Maintenance finding (2026-10-28 20:50 +08:00)

- **Review status:** Latest AGY snapshot `2026-10-28T20:36:14+08:00` is PASS (45 checks, no FAIL/WARN; safe suite snapshot 184 passed / 1 deselected). Training smoke and one-time locked-test UI are SKIP; popular-stock local coverage 10/10; locked-data isolation PASS.
- **Reproduced defect:** `calculateActivationComparison(2, 1e200)` previously returned a result even though squared losses overflowed to Infinity. Finite inputs alone were checked; non-finite derived values could reach user-visible formatting.
- **Fix:** `web/app.js` now requires every derived activation, gradient and loss to be finite before returning a result. Overflow uses the existing finite-input prompt. Renderer test and browser predicate cover this exact case; guide documents the limit.
- **Evidence:** Focused pytest `2 passed, 93 deselected`; `node --check web/app.js` and Python AST checks pass. Pre-fix Node reproduction observed Infinity losses with a non-null result. Post-fix rendered output is asserted. The AGY snapshot predates edits; browser viewports are unverified.
- **Roadmap / next checkpoint:** Bounded synthetic neural-network numerical-stability instruction advanced; broader milestone remains incomplete and no training/model-quality claim is made. Check Step 21 at desktop/390px for overflow and existing boundary/saturation cases. Expansion beyond 10/10 popular stocks needs authorized local data; real cross-symbol magnitude instruction needs comparable ordinary OOF summaries. No protected observations/final-test files accessed or changed; no final test, refresh, training, deploy, or publish.

## Scheduled maintenance checkpoint (2026-10-28 23:05 +08:00, L2 predicate and minimum-loss breakdown)

- **Latest review / reproduced defect:** The supplied 23:02 `latest-checks.json` reports L2 interaction FAIL. Comparing the live renderer and browser fixture reproduced a stale-copy defect: the renderer's updated λ>0 optimum explanation did not match the monitor's older expected phrase.
- **Exact fix:** Corrected that monitor clause and added a test contract for the current explanation and minimum-loss output.
- **Bounded milestone:** Step 26 now shows the loss components at its analytic minimum. For λ=0.1, `w*=0.9091`, data loss `0.0083`, penalty `0.0826`, total `0.0909`; for λ=0, all losses are zero. Updated `web/app.js`, `web/index.html`, `scripts/regression_monitor.py`, `tests/test_system.py`, and `docs/learning-guide.md`. Synthetic instruction only.
- **Evidence and limitation:** Focused renderer acceptance passes (`1 passed, 95 deselected`); monitor safe suite passed (`206 passed, 1 deselected`); JS syntax, in-memory Python syntax, and scoped diff checks pass. Browser/desktop/390px acceptance remains unverified because the monitor's local HTTP request was denied and Playwright could not import Pillow. Holdout isolation passed; training smoke and locked-test UI were skipped.
- **Remaining / next checkpoint:** Repeat browser-only Step 26 viewport checks once local preview access and Pillow are available. Keep the larger neural-network goal incomplete. Popular-stock source expansion and comparable ordinary OOF cross-symbol magnitude summaries remain open. No protected files/data or credentials were read or changed; no final test, refresh, training, deploy, publish, or external messaging occurred.

## Scheduled maintenance review (2026-10-28 23:42 +08:00, L2 error-to-optimum readout)

- **AGY review:** Latest saved check at 2026-10-28 23:40 +08:00 is PASS with 206 passed / 1 deselected, desktop and 390px browser acceptance, local popular-symbol consistency 10/10, and locked-data isolation PASS. Training smoke and locked-test UI are intentionally SKIP. Independent review reproduced no current concrete defect; there is no bug fix claimed in this checkpoint.
- **Roadmap change:** Added a visible one-step error-to-optimum calculation to Step 26: `w_next−w*=[1−2η(1+λ)](w−w*)`. The UI displays before/after distance and the signed multiplier, making stable contraction, critical equal-distance reversal, and divergent overshoot directly inspectable. Added renderer and browser-monitor assertions and a guide explanation. The lesson is synthetic and does not establish model quality.
- **Verification:** Focused renderer test `1 passed, 95 deselected`; safe selection `206 passed, 1 deselected, 2 warnings` (existing Starlette/httpx deprecation and monitor-source invalid-escape SyntaxWarning); JS syntax, AST, and scoped diff checks pass. The saved monitor artifact predates this change and does not prove the new clause. Next: browser-only desktop/390px acceptance excluding training smoke and locked-test UI.

## Scheduled maintenance review (2026-10-29 00:18 +08:00, L2 stability boundary comparison)

- **AGY review:** `artifacts/regression-monitor/latest-checks.json` at 00:15:43 +08:00 is PASS; safe suite recorded 206 passed / 1 deselected and holdout isolation PASS. Training smoke and locked-test UI are SKIP. No active application defect was independently reproduced. Running pytest with system Python 3.9 did reproduce the known missing-`mcp` collection issue; the project `.venv` is the intended interpreter and its existing selection guard plus full safe suite pass.
- **Roadmap change:** Step 26 now directly compares 0.5×, 1×, and 1.5× of the current λ critical learning rate and reports each signed error multiplier and behavior. At λ=0.1 the values are η=0.4545 / 0.9091 / 1.3636 and multipliers 0 / −1 / −2. Added renderer and browser predicate assertions and guide explanation. This is a synthetic learning aid, not training or model-quality evidence.
- **Verification:** Focused L2 renderer acceptance `1 passed, 95 deselected`; safe `.venv` suite `206 passed, 1 deselected, 2 warnings`; `node --check`, Python AST parsing, and scoped diff check pass. Latest browser snapshot predates this change; no post-edit desktop/390px visual claim.
- **Next:** Run browser-only Step 26 at desktop and 390px for λ=0/0.1, boundary sweep, blank input, cancellation, and overshoot. Keep the broad learning objective open. Popular-stock expansion needs an authorized local source; real cross-symbol magnitude instruction needs comparable ordinary OOF summaries. No credentials, protected data, or final-test files touched; no final test, refresh, training, deployment, publication, or external messaging.


## Scheduled maintenance checkpoint (2026-10-29, weight-decay equivalence lesson)

- **Latest AGY review / defect disposition:** `artifacts/regression-monitor/latest-checks.json` at `2026-10-29T00:52:38+08:00` is PASS. Safe suite snapshot is 206 passed / 1 deselected; popular-stock local coverage and locked-data isolation PASS. Training smoke and locked-test UI are SKIP. I compared the current L2 calculator's finite-result guard with synthetic boundaries; overflow is rejected, while the largest representable finite example remains finite. No higher-priority current defect was independently reproduced, so no bug fix is claimed.
- **Roadmap increment / exact change:** Added a visible Step-26 pure-SGD comparison between coupled L2 `w−η(g+λw)` and decoupled weight decay `(1−ηλ)w−ηg`. The result shows both updated weights and their difference; synthetic cases with positive, negative, and zero gradients check equality. Copy states that this equivalence is limited to plain SGD and that adaptive optimizers generally differ. Updated `web/app.js`, `web/index.html`, `scripts/regression_monitor.py`, `tests/test_system.py`, and `docs/learning-guide.md`. This is a bounded neural-network learning aid, not model training or quality evidence.
- **Verification:** Initial focused tests caught two incorrect expected values (actual defaults are `1.93` and `0.43`); expectations were corrected. Final focused tests: `2 passed, 95 deselected`; safe suite: `207 passed, 1 deselected`. `node --check web/app.js`, monitor/test Python AST parsing, and scoped `git diff --check` pass. Warnings: existing Starlette/httpx deprecation and monitor-source invalid-escape SyntaxWarning. The saved AGY browser screenshot predates the edit; no post-edit browser/desktop/390px rendering is claimed.
- **Remaining / next checkpoint:** Keep the broader neural-network goal incomplete. Verify the new comparison in desktop and 390px browser acceptance when local preview/browser dependencies are available; monitor checks now assert default, changed inputs, and blank input. Popular-stock expansion beyond 10/10 still needs an authorized local source; cross-symbol magnitude lessons still need comparable ordinary OOF summaries. No credentials, locked observations, or `final-test-*.json` were accessed or changed; no final test, market refresh, training, deployment, publication, or external messaging.
## 2026-10-29 — weight-decay lesson output remained uninitialized

- **Evidence:** `artifacts/regression-monitor/latest-checks.json` at `2026-10-29T02:03:26+08:00` reports `純 SGD 權重衰減=False` while other lesson clauses pass.
- **Reproduction:** `renderLesson()` reveals `#weightDecayComparisonExercise` using the L2 lesson's title-derived index, but called `renderWeightDecayComparison()` only for numeric index 25. In the guided browser fixture the section was visible and its output was empty, contradicting the expected default `1.9300` comparison.
- **Correction:** Use `weightDecayLessonIndex` for render initialization too; add a regression assertion that rendering and visibility share the stable lesson locator.
- **Verification:** focused test `1 passed, 96 deselected`; safe suite `208 passed, 1 deselected, 1 warning`; JavaScript syntax passes. Existing deprecation warning is unrelated. No post-fix browser viewport run yet.
- **Next checkpoint:** Verify default/edited/blank-input behavior in desktop and 390px browser acceptance without training or locked-test UI.
## 2026-10-29: stale pure-SGD browser expectation

- **Reproduction:** Saved browser check failed `純 SGD 權重衰減`. For its changed fixture (`g=-1,w=0.25,η=0.2,λ=0.4`), the current pure-SGD expression is `0.25−0.2(−1+0.4×0.25)=0.4300`. The browser monitor expected `0.3300`, inconsistent with the executable renderer test's `0.43` expectation.
- **Correction:** Updated `scripts/regression_monitor.py` to expect `0.4300`. No learning calculation changed for this defect.
- **Related bounded feature:** The exercise now displays the independent gradient step `ηg` and decay step `ηλw` before the coupled/decoupled outputs. Acceptance covers default and changed inputs plus invalid blank input.
- **Verification:** Focused test `1 passed, 96 deselected`; safe project selection `208 passed, 1 deselected, 1 existing Starlette/httpx deprecation warning`; JS syntax, Python AST, and scoped diff checks pass. Saved monitor evidence is pre-fix and is not a post-fix browser pass.
- **Next checkpoint:** Verify with tests and run browser-only desktop/390px acceptance when available, without training smoke or locked-test UI. This does not establish real-model quality.


## Scheduled maintenance checkpoint (2026-10-29, signed SGD update labels)

- **Latest review / independently reproduced defect:** `artifacts/regression-monitor/latest-checks.json` at `2026-10-29T03:52:33+08:00` reports the combined learning interaction FAIL only at `純 SGD 權重衰減=False`; all other listed lesson clauses pass. The browser predicate expected default `ηg=+0.0500`, but the current calculator and focused renderer test compute the actual weight update `−ηg=−0.0500` for `g=0.5, η=0.1`. The same mismatch affects the decay label: the displayed value is `−ηλw`, not `ηλw`.
- **Exact defect fix:** Corrected the browser expectation to the signed default update and made the interface label both components as `−ηg` and `−ηλw`. The formulas/calculator values were already correct. The browser predicate now matches the corrected signed labels and keeps its default, changed, blank, and equivalence checks.
- **Bounded learning milestone advanced:** The visible pure-SGD lesson now explains the actual update directions from each signed component: positive/negative/zero gradient and decay contributions increase/decrease/leave weight unchanged. Added output and acceptance for default (`−0.0500`, `−0.0200`) and changed inputs (`+0.2000`, `−0.0200`), plus guide copy. This is a synthetic optimizer lesson, not training or model-quality evidence.
- **Verification:** Focused `weight_decay_comparison_matches_coupled_l2_for_sgd` → `1 passed, 97 deselected`; safe suite `./.venv/bin/python -m pytest -q -k 'not public_api_and_async_validation_job'` → `216 passed, 1 deselected, 1 existing Starlette/httpx deprecation warning`. `node --check web/app.js`, Python AST parsing, and scoped `git diff --check` pass. The saved monitor snapshot predates the fix; `127.0.0.1:8000` is unavailable, so post-edit browser viewport acceptance is not claimed.
- **Remaining / next checkpoint:** Re-run browser-only guided acceptance at desktop and 390px for default, changed, and blank inputs; keep training smoke and locked-test UI skipped. Popular-stock expansion beyond local 10/10 needs an authorized local data source; real cross-symbol magnitude instruction still needs comparable ordinary OOF summaries. No credentials, locked observations, or `final-test-*.json` accessed/changed/consumed; no final test, market refresh, training, deployment, publication, or external messaging.
## Scheduled maintenance triage (2026-10-29, 04:29 saved browser failure)

- **Finding:** Latest saved monitor JSON reports page HTTP failure and one aggregate learning failure whose final named clause is `純 SGD 權重衰減=False`. The snapshot is not a current browser reproduction.
- **Independent check:** Current source predicate expects default signed updates −0.0500 and −0.0200 and outputs 1.9300 under both plain-SGD formulas; edited inputs produce 0.4300 under both. These expectations match the renderer and focused test. A suspected L2 position mismatch was checked and ruled out: title lookup currently resolves to index 25, matching the main exercise's index.
- **Disposition:** No concrete current code defect reproduced; no code fix or completed milestone claimed. Existing renderer tests pass, but they cannot substitute for the missing live browser fixture.
- **Next:** Diagnose local page HTTP availability without training/holdout flows, then rerun only guided Step 26 desktop/390px browser acceptance and capture each subcondition. No credentials, protected data, or final-test assets touched.

## Scheduled maintenance triage (2026-10-29 05:30 +08:00)

- **Review finding:** Saved monitor `2026-10-29T05:06:41+08:00` is FAIL at the combined lesson check's `純 SGD 權重衰減` clause. The current source and focused renderer check agree on its signed values; focused acceptance passes. The snapshot is not a live reproduction, so no active defect is claimed.
- **Change made:** Advanced Step 26 with a fixed synthetic Adam illustration showing coupled L2 `w=1.9000` versus decoupled weight decay `w=1.8800` for the same base inputs. The browser predicate now checks that teaching copy; renderer and guide contracts cover the example.
- **Verification:** Focused pytest `1 passed, 97 deselected`; JS syntax, Python AST, and scoped diff checks pass. One initial assertion-order failure was corrected and retested. No post-edit browser viewports verified.
- **Next:** Run browser-only desktop/390px acceptance for the Step-26 interaction, with edited and blank input; keep training smoke and locked-test UI excluded. Broader learning remains incomplete; stock expansion needs an authorized local source and cross-symbol magnitude instruction needs comparable ordinary OOF summaries. No credential, protected observation, or `final-test-*.json` accessed/changed/consumed.


## Scheduled maintenance checkpoint (2026-10-29, dynamic Adam weight-decay comparison)

- **Latest review finding:** `artifacts/regression-monitor/latest-checks.json` at `2026-10-29T05:41:43+08:00` is FAIL only in the aggregate guided-learning check, whose final clause is `純 SGD 權重衰減=False`. It records popular-stock local coverage 10/10 and locked-data isolation PASS; training smoke and locked-test UI are SKIP. The current focused renderer acceptance agrees with the saved SGD arithmetic, so the underlying browser failure is not independently reproduced from current code.
- **Highest-priority reproduced defect and fix:** The current monitor collapses the SGD/weight-decay lesson's visible state, explanatory copy, default values, edited values, and blank-input recovery into one boolean. The saved FAIL therefore does not identify which assertion failed. Split the browser result into named `visible`, `noteOk`, `sgdDefault`, `sgdChanged`, `adamDefault`, `adamChanged`, and `blankOk` fields; the aggregate now reports those values individually.
- **Roadmap milestone advanced:** Step 26's Adam coupled-L2 versus decoupled-weight-decay comparison now recalculates from the same editable gradient, weight, learning-rate, and decay inputs as the SGD comparison. With ε=10⁻⁸, the default values produce `1.9000` versus `1.8800`; edited values `g=−1,w=0.25,η=0.2,λ=0.4` produce `0.4500` versus `0.4300`. Blank input produces a clear unavailable-result message. Added executable arithmetic/render acceptance, browser predicate clauses, and learning-guide explanation. This is a synthetic optimizer lesson, not training or model-quality evidence.
- **Verification:** Focused test `./.venv/bin/python -m pytest -q tests/test_system.py -k weight_decay_comparison_matches_coupled_l2_for_sgd` → `1 passed, 97 deselected` (one existing Starlette/httpx deprecation warning). Safe project suite `./.venv/bin/python -m pytest -q -k 'not public_api_and_async_validation_job'` → `216 passed, 1 deselected` (same warning). `node --check web/app.js`, Python AST parsing for monitor/tests, and scoped `git diff --check` pass. The first focused run caught stale assertions that still required the removed static Adam copy; I updated them to require the live calculation and explanatory copy, then reran successfully. The supplied monitor/browser snapshot predates these changes; post-edit browser rendering at desktop and 390px is not verified.
- **Remaining / next checkpoint:** Run browser-only Step-26 acceptance at desktop and 390px for default, edited, zero-gradient, and blank cases; keep training smoke and locked-test UI skipped. Keep the broader neural-network learning objective incomplete. Popular-stock expansion beyond 10/10 needs an authorized local source; real cross-symbol rise/fall magnitude instruction needs comparable ordinary OOF summaries. No credentials, protected observations, or `final-test-*.json` were accessed or consumed; no final test, market refresh, training, deployment, publication, or external messaging occurred.
## 2026-10-29 06:19 +08:00 — SGD equivalence displayed a negative zero

- **Review evidence:** `artifacts/regression-monitor/latest-checks.json` reports overall FAIL only in the guided weight-decay clause `sgdChanged=False`; pytest in that snapshot passed 217 tests and locked-data isolation passed. Training smoke and locked-test UI are SKIP.
- **Reproduction:** Current renderer inputs `g=-1,w=0.25,η=0.2,λ=0.4` produce coupled `0.43000000000000005`, decoupled `0.43`, difference `−5.55e−17`; `toFixed(4)` displays `−0.0000`. The browser predicate correctly expected mathematical equality as `0.0000`.
- **Fix:** Normalize differences no larger than four machine epsilons at the result scale to zero. The result now reports `差=0.0000` while retaining meaningful differences. Added test coverage for the exact edited case.
- **Related roadmap increment:** Display `1−ηλ` as the original-weight retention factor. It reads `0.9900` by default and `0.9200` for edited inputs. The monitor checks both values; the learning guide explains the quantity.
- **Verification:** Focused test `1 passed, 97 deselected`; safe suite `216 passed, 1 deselected` with one existing Starlette/httpx deprecation warning. `node --check`, Python AST parsing, and scoped `git diff --check` pass. The supplied browser snapshot is pre-fix; no post-edit viewport run is claimed.
- **Next:** Browser-only desktop/390px guided acceptance for default, edited, zero-gradient, and blank values. Preserve training-smoke and locked-test UI skips. No protected observations, credentials, or final-test files were accessed; no final test, market refresh, training, deployment, or publication occurred.
## Scheduled maintenance checkpoint (2026-10-29, 3D momentum direction example)

- **Latest review / reproduced maintenance defect:** The latest `artifacts/regression-monitor/latest-checks.json` is `2026-10-29T08:41:22+08:00`, PASS across 45 checks, with no FAIL/WARN; its recorded pytest run is 217 passed, 1 warning. Popular-stock local consistency 10/10 and locked-data isolation pass. Training smoke and one-time locked-test UI are skipped. The prior leading record cited 08:06, reproducing a stale-checkpoint defect by timestamp comparison; no current runtime issue is reported.
- **Exact change and milestone:** Step 20 advertised 3D momentum direction but initialized the third velocity and gradient components to zero. This made the default example only two-dimensional. Changed the example to `v=(1,2,2), g=(2,1,0)` and clarified its dimension in UI copy. Its rendered text now checks as `v·g=4`, cosine `0.5963`, parallel component `1.7889`, and perpendicular magnitude `2.4083`. Updated executable markup/renderer acceptance and `docs/learning-guide.md`. This advances synthetic learning only, with no training or model-quality claim.
- **Verification / remaining:** Focused test → 2 passed, 97 deselected, 1 existing deprecation warning; JS syntax and scoped diff checks pass. Latest browser snapshot is pre-edit, so desktop/390px post-edit rendering remains unverified. Next run browser-only Step 20 acceptance for 2D/3D and invalid/zero cases at both viewports. Keep training smoke and locked-test UI skipped. Popular-stock expansion needs an authorized local source; real cross-symbol rise/fall magnitude needs comparable ordinary OOF summaries. No credentials, locked observations, or `final-test-*.json` accessed/changed/consumed; no final test, refresh, training, deployment, publication, or external messaging.

## Scheduled maintenance checkpoint (2026-10-29, browser readiness and vector magnitude)

- **Latest review:** `artifacts/regression-monitor/latest-checks.json` at `2026-10-29T09:54:48+08:00` is FAIL only at browser navigation (`page.goto` timed out waiting for `networkidle`). API checks, safe pytest (219 passed, one warning), local popular-stock consistency 10/10, and locked-data isolation pass; training smoke skipped.
- **Reproduced defect and change:** The monitor waited for `networkidle`, which is not a reliable readiness condition for an app with background connections. Existing assertions have explicit UI/API waits. Changed navigation to `domcontentloaded` with the same timeout and added a source-contract test. Live browser acceptance has not been rerun.
- **Roadmap subtask:** Guided Step 20 now exposes `|v|` and `|g|` alongside direction cosine and projection, so magnitude and alignment are separately observable. Synthetic default: `|v|=3`, `|g|=√5`; cosine 0.5963; parallel component 1.7889. Renderer and browser-math acceptance updated. Not training or model-quality evidence.
- **Verification / next:** Focused `pytest` → 2 passed, 99 deselected; safe suite `pytest -q -k not public_api_and_async_validation_job` → 219 passed, 1 deselected, one existing Starlette/httpx deprecation warning. JS syntax, Python AST, and scoped diff checks pass. Next run browser-only desktop/390px for Step 20 once preview/browser prerequisites are available. Popular-stock expansion awaits an authorized local source; cross-symbol magnitude awaits comparable ordinary OOF summaries. Preserve skips for training smoke and locked-test UI; no holdout/final-test access or refresh.


## Scheduled maintenance checkpoint (2026-10-29, zero-vector direction readout)

- **Latest review evidence / maintenance defect:** The supplied AGY snapshot `artifacts/regression-monitor/latest-checks.json` at `2026-10-29T11:44:30+08:00` is PASS (43 PASS, 2 intentional SKIP). The three review records and roadmap still ended at 11:07, independently confirming stale maintenance status. Current code also reproduced a zero-vector display defect: null parallel/perpendicular components were exponentiated as zero in the decomposition check, despite the lesson correctly saying direction is undefined.
- **Exact fix:** `web/app.js` now reports the square-decomposition check as undefined whenever either vector has zero norm. The valid nonzero case still shows the numeric identity. Added a renderer assertion in `tests/test_system.py` and clarified the zero-vector limit in `docs/learning-guide.md`.
- **Roadmap advance:** Advanced the bounded synthetic neural-network learning lesson by making the zero-vector boundary mathematically consistent and visible. This is geometry instruction only, not training or model-quality evidence.
- **Verification:** `./.venv/bin/python -m pytest -q tests/test_system.py -k momentum_direction` → 2 passed, 99 deselected, one existing Starlette/httpx deprecation warning. `node --check web/app.js` and `git diff --check -- web/app.js tests/test_system.py` passed. Browser rerun is not claimed; the 11:44 snapshot predates this edit.
- **Remaining / next checkpoint:** Run browser-only Step 20 checks at desktop and 390px for nonzero 2D/3D, either zero vector, blank and invalid fields. Keep real-data training and locked-test UI skipped. Local popular-stock coverage is 10/10 and expansion needs an authorized local source; real cross-symbol magnitude teaching needs comparable ordinary OOF summaries. No credentials, locked observations, or `final-test-*.json` accessed/changed/consumed; no final test, data refresh, training, deployment, publication, or external messaging.
## 2026-10-29 12:18 — finite magnitude mean overflow; direction-group n guidance

- **Review context:** Latest `artifacts/regression-monitor/latest-checks.json` (12:18:45 +08:00) reports PASS, 220 tests passed/1 warning, local stock coverage 10/10, magnitude/direction and desktop/mobile PASS; training smoke and one-time locked-test UI SKIP. Top-level review notes were stale at 11:07.
- **Reproduced defect:** `renderMagnitudeErrorExercise` summed absolute errors before dividing by sample count. For finite synthetic pairs `p=[1e308,1e308]`, `a=[1,1]`, each error and the true mean MAE (`1e308`) are representable, but the raw sum exceeds `Number.MAX_VALUE`, producing `Infinity` in visible output.
- **Fix:** Scale each paired value by n before differencing and summing; scale baseline and magnitude terms before summing too. Added a renderer-level Node acceptance test in `tests/test_system.py` that rejects Infinity/NaN. This uses synthetic values only.
- **Roadmap increment:** Cross-asset reading now explicitly checks effective sample count for each actual-direction group and explains small-group sensitivity. Updated page copy, browser predicate, test, and learning guide. No model quality is inferred.
- **Evidence:** `./.venv/bin/python -m pytest -q tests/test_system.py -k 'magnitude or cross_asset or validation_direction'` → 7 passed, 96 deselected, one existing Starlette/httpx warning. `node --check web/app.js`, Python AST parsing, and scoped `git diff --check` pass. Saved browser snapshot predates edits; no post-edit viewport render claimed.
- **Remaining / next checkpoint:** Add/use ordinary OOF summaries grouped by actual direction and only compare compatible symbols with matching validation protocol. Popular-symbol expansion past local 10/10 needs an authorized local source. Keep training smoke and locked-test UI skipped. No credentials, locked observations, `final-test-*.json`, final test, market refresh, training, deployment, publication, or external message touched.
