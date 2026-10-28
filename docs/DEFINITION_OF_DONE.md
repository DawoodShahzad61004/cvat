# Definition of Done

Written before any code (commit `1f39da99c`). Each line is ticked only with evidence beside it (a number, a file
under `docs/evidence/`, or a commit). A tick without evidence counts as unticked.

## Floor (requirements 1–4)

- [x] Endpoint counts match an independent count of `instances_val2017.json` for the imported images, per class.
  — 0 of 80 labels differ, total 41,866: [`evidence/check_counts.txt`](evidence/check_counts.txt).
  *Changed while doing it:* the match is against polygon parts per class, not COCO instances (36,781);
  CVAT stores each polygon part as a shape. Reason in `OBJECTIVES.md` → Dataset used.
- [x] Endpoint returns every label of the task, including labels with zero annotations.
  — task 1 returns `cat: 0, dog: 0` ([`evidence/page-empty.png`](evidence/page-empty.png));
  `test_counts_per_label` asserts `unused: 0`.
- [x] Ground-truth / replica jobs and skeleton child points are not counted.
  — `test_counts_per_label` (a GT copy and a skeleton element are present and excluded):
  [`evidence/backend_tests.txt`](evidence/backend_tests.txt).
- [x] Page reachable from the task page, renders the bar chart with the COCO task.
  — "Annotation statistics" in the task actions menu; [`evidence/page-chart.png`](evidence/page-chart.png).
- [x] Empty case: a task with labels but no annotations shows an explicit empty state, not a blank chart.
  — [`evidence/page-empty.png`](evidence/page-empty.png).
- [x] Error case: a failed request shows an error with a retry button (checked with the server stopped and with a 403).
  — 403: [`evidence/page-error-403.png`](evidence/page-error-403.png); server stopped: "Gateway Timeout" +
  Retry, and Retry recovers: [`evidence/page-error-server-down.png`](evidence/page-error-server-down.png),
  [`evidence/live_and_reconnect.txt`](evidence/live_and_reconnect.txt).
  *Changed while doing it:* reloading the page with the server down never reaches this page (CVAT's app shell
  needs the server first), so the failure is triggered by a refetch while the page is open.

## Access (requirement 5)

- [x] No credentials → 401 (raw `curl` output saved). — [`evidence/access_checks.txt`](evidence/access_checks.txt);
  the socket closes with 4401 for the same case.
- [x] Logged-in user with no access to the task → 403 (raw `curl` output saved).
  — [`evidence/access_checks.txt`](evidence/access_checks.txt); the socket closes with 4403.
- [x] Automated Django test covering counts, 401 and 403 passes. — 7/7:
  [`evidence/backend_tests.txt`](evidence/backend_tests.txt).

## Speed (requirement 6)

- [x] MO-1 measured: 5 runs, raw output saved, median and spread reported.
  — median 44.0 ms, spread 43.2–46.1 ms: [`evidence/mo1_stats_endpoint.txt`](evidence/mo1_stats_endpoint.txt).
- [x] Target met, or missed with the reason written down. — met (≤ 100 ms); cleared without tuning, which
  `OBJECTIVES.md` says plainly. MO-2 also met: 233.6 ms vs ≤ 500 ms,
  [`evidence/mo2_live_update.txt`](evidence/mo2_live_update.txt).

## Beyond the floor (7–10)

- [x] `group_by=type` returns per-class counts split by annotation type; chart stacks them.
  — `test_group_by_type`; [`evidence/page-chart-by-type.png`](evidence/page-chart-by-type.png) (person: 227 masks,
  12,224 polygons).
- [x] Saving an annotation in a job updates an open stats page without reload (WebSocket).
  — total 41866 → 41867 in 250 ms in a headless Chrome page:
  [`evidence/live_and_reconnect.txt`](evidence/live_and_reconnect.txt), [`evidence/page-live.png`](evidence/page-live.png).
- [x] Restarting `cvat_server` while the page is open: page shows it is reconnecting, then resumes with fresh counts.
  — reconnecting at +10.0 s, Live again at +25.1 s, next save shows in 314 ms:
  [`evidence/live_and_reconnect.txt`](evidence/live_and_reconnect.txt),
  [`evidence/page-reconnecting.png`](evidence/page-reconnecting.png).
- [x] Decision record at the end of `PLAN.md`. — [`PLAN.md`](PLAN.md#decision-record).

## Hygiene

- [x] Plan committed before any code; history shows the work in steps. — `1f39da99c` is first; `git log --oneline`
  shows one commit per step, each with what changed and why.
- [x] Change contained to `cvat/apps/test`, a route + page in `cvat-ui`, and registration lines in settings/urls/asgi.
  — plus two lines not foreseen: `ws: true` in the webpack dev proxy, and the regenerated `cvat/schema.yml`.
- [x] No dead code, commented-out blocks or stray files in the diff. — checked with
  `git diff 4a09e27ff --stat` before the last commit; the only non-code files are under `docs/`.
- [x] Everything not finished is listed below.

## Not finished

- **Production UI image not rebuilt.** The page was verified with the webpack dev server (`yarn start`) against the
  stack, and the socket also through Traefik on :8080 with a browser session cookie; I did not build
  `cvat/ui` with the change. Reason: the build is long and not on the path to any requirement.
- **No automated test for the socket or the signal.** Live updates and reconnect are proven by the browser
  scenario above, run by hand, not by CI. A Django test with `fakeredis` for `publish_task_change`, and a
  Cypress test for the page, are the next things I would add.
- **No UI unit tests.** The page's empty / error / live states are covered by screenshots only.
- **Backend tests need the dev requirements**, which the published `cvat/server` image does not contain; they
  were run only in the running container after installing them there.
- **Scaling of the live path is not measured.** One Redis connection and one recount per open socket (see the
  decision record); MO-1 was measured on 41,866 shapes only.
- **Stats for projects and single jobs** were skipped up front (task only).
