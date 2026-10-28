# Definition of Done

Written before any code. Each line is ticked only with evidence beside it (a number, a file
under `docs/evidence/`, or a commit). A tick without evidence counts as unticked.

## Floor (requirements 1–4)

- [ ] Endpoint counts match an independent count of `instances_val2017.json` for the imported images, per class.
- [ ] Endpoint returns every label of the task, including labels with zero annotations.
- [ ] Ground-truth / replica jobs and skeleton child points are not counted.
- [ ] Page reachable from the task page, renders the bar chart with the COCO task.
- [ ] Empty case: a task with labels but no annotations shows an explicit empty state, not a blank chart.
- [ ] Error case: a failed request shows an error with a retry button (checked with the server stopped and with a 403).

## Access (requirement 5)

- [ ] No credentials → 401 (raw `curl` output saved).
- [ ] Logged-in user with no access to the task → 403 (raw `curl` output saved).
- [ ] Automated Django test covering counts, 401 and 403 passes.

## Speed (requirement 6)

- [ ] MO-1 measured: 5 runs, raw output saved, median and spread reported.
- [ ] Target met, or missed with the reason written down.

## Beyond the floor (7–10)

- [ ] `group_by=type` returns per-class counts split by annotation type; chart stacks them.
- [ ] Saving an annotation in a job updates an open stats page without reload (WebSocket).
- [ ] Restarting `cvat_server` while the page is open: page shows it is reconnecting, then resumes with fresh counts.
- [ ] Decision record at the end of `PLAN.md`.

## Hygiene

- [ ] Plan committed before any code; history shows the work in steps.
- [ ] Change contained to `cvat/apps/test`, a route + page in `cvat-ui`, and registration lines in settings/urls/asgi.
- [ ] No dead code, commented-out blocks or stray files in the diff.
- [ ] Everything not finished is listed below.

## Not finished

_(Filled in at the end.)_
