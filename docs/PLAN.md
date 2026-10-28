# Plan — Annotation Analytics (per-class annotation counts)

Branch `dev-test01`, cut from upstream `develop` at `4a09e27ff869b7aebbfdb07b29c4a34904a0221d`.
Machine: Intel Core i5-13450HX (10 cores / 16 threads), 16 GB RAM (7.6 GB given to Docker),
Windows 11 Home 10.0.26300, Docker 29.6.2 / Compose v5.3.1.

## What I found before planning

- An annotation is a row in one of three tables, all subclasses of `engine.Annotation`
  (`job`, `label`, `source` fields): `LabeledShape` (boxes, polygons, masks…; has `type`),
  `LabeledTrack` (video tracks) and `LabeledImage` (tags). Skeleton points are child rows
  (`parent` not null) and must not be counted as separate objects.
- Task → label name: `Annotation.job → Job.segment → Segment.task`, and `Annotation.label → Label.name`.
  Labels may belong to the task's project instead of the task (`Task.get_labels()` handles both).
- Ground-truth and consensus-replica jobs hold copies of annotations; CVAT's own export
  counts only `JobType.ANNOTATION` jobs, so I will too.
- Access control is OPA based (`cvat/apps/iam`). The REST default permission classes are
  `IsAuthenticated` + `PolicyEnforcer`, which asks the view for an `iam_permission_class`.
  I will reuse `TaskPermission` with the existing `view:annotations` scope rather than write new rego.
- The server already runs under uvicorn with the `websockets` package, and the in-container nginx
  forwards `Upgrade` headers. A raw ASGI WebSocket route works without adding Django Channels.
- Every annotation write ends in `TaskAnnotation._set_updated_date()` → `task.touch()` →
  `post_save(Task)`. That is an existing hook I can listen to without editing engine code.
- The UI already ships `chart.js` + `react-chartjs-2`; no new dependency is needed for the graph.

## Order of work (8 h budget; image pulls and dataset import excluded)

| # | Step | Budget |
|---|------|--------|
| 0 | Read the codebase, write Plan / Objectives / Definition of Done, commit them | 0:45 |
| 1 | New Django app `cvat.apps.test`: `GET /api/tasks/{id}/annotation-stats`, one aggregate query per annotation table, OPA-checked | 1:00 |
| 5 | Prove auth: 401 without login, 403 for a user with no access to the task; automated test | 0:30 |
| 2–4 | UI page `/tasks/:tid/annotation-stats` (link from the task page), horizontal bar chart, empty state, error state with retry | 1:30 |
| 6 | Measure MO-1 (endpoint latency) 5 runs on the COCO task, compare to the naive alternative | 0:45 |
| 7 | `group_by=type` — stack each class bar by annotation type | 0:30 |
| 8 | WebSocket `/api/tasks/{id}/annotation-stats/ws`: `post_save(Task)` → Redis pub/sub → push fresh counts | 1:15 |
| 9 | Client reconnect with backoff, connection status shown, fresh snapshot on reconnect | 0:30 |
| 10 | Decision record, tick Definition of Done with evidence, list what is unfinished | 0:45 |
|   | Buffer | 0:30 |

Items 1–4 are the floor; I do not start 8 until 4 works.

## Decided to skip up front

- Project-level and job-level stats (task only, as asked).
- Counting the shapes *inside* a track frame by frame; a track counts as one object.
- Caching or materialising counts. I will first measure; I only add a cache if MO-1 is missed.
- Building the production UI image is not on the critical path: I develop against the webpack dev
  server and the published `cvat/server:dev` image with my app mounted in. A full image build
  happens at the end only if time remains.
- Browser E2E tests (Cypress). Backend gets a Django test; the UI is checked by hand with screenshots.

## Dataset

COCO 2017 val, all 5,000 images if the machine copes (fallback 1,000), one task, segment size 500.
The actual number used is recorded in `OBJECTIVES.md`.

## Changes to this plan

- **"Correct counts" needed a definition.** The first check against `instances_val2017.json` was off by
  5,085 (41,866 vs 36,781). Cause: CVAT stores each part of a multi-part COCO polygon as its own shape,
  linked by `group`. I kept counting shapes (what CVAT stores and shows) and changed the check to compare
  against polygon parts per category; it matches on all 80 labels. Counting instances instead is recorded
  as the rejected alternative in the decision record.
- **Dataset took longer than planned.** The image zip downloaded at ~0.2 MB/s over one connection; I switched
  to 24 parallel range requests (~10 MB/s). The default compose file has no share volume, so the images were
  copied into the import worker and the task created with `copy_data`. Setup time, not counted.
- **Order.** UI floor (2–4) was finished and committed before MO-1, as planned; MO-1 was cleared on the first
  measurement, so no caching work was needed.
- **Backend tests** run inside `cvat_server` after installing the dev requirements (`django-extensions`,
  `django-silk`, `fakeredis`) that the production image lacks, with OPA pointed at the stack's `opa` service.
- **Two bugs found only in a real browser**, after the script client passed: the browser's
  `Accept-Encoding: gzip` on the upgrade request made Django gzip the snapshot (fixed by dropping the header
  for the inner request), and during a `cvat_server` restart Traefik answers `/api/...` with the UI's
  `index.html` and status 200, which crashed the page on Retry (fixed by rejecting a body without `labels`).
- **Not planned, done:** regenerated `cvat/schema.yml` so the committed API schema matches the code.

## Decision record

**Context.** Requirement 8 needs the chart to move when annotations change. Two questions: how does the
server learn about a change, and how does it reach the browser.

**Taken.** The change signal is the existing `post_save(Task)` fired by `task.touch()` at the end of every
annotation write; it is published to Redis (already in the stack) after commit, so writes made in import
workers reach sockets held by server processes. The socket is a plain ASGI route in front of Django in
`cvat/asgi.py` (uvicorn already speaks WebSocket). Each push is produced by running the existing REST
request through Django's middleware as the connecting user, so authentication, the OPA check and the
serializer are the same code path as `GET /annotation-stats`, and losing access closes the socket.

**Rejected.** Django Channels: consumers, `AuthMiddlewareStack`, and a Redis channel layer with group
broadcasts — the conventional answer.

**What rejecting it cost.**
- 130 lines of hand-written ASGI plumbing (`websocket.py`) that Channels would have provided, including
  the two browser-only bugs above, which a mature stack has already met.
- No shared fan-out: every open socket holds its own Redis connection and recounts on its own, so N viewers of
  one task cost N `GROUP BY`s per change (44 ms each on COCO). Channels groups would have let one recount be
  broadcast. Fine for a handful of viewers; it is the first thing to change if this page became popular.
- Replaying the request through middleware is unusual; a reader has to know that the socket's answer is,
  literally, the REST endpoint's answer.

What it bought: no new dependency and no change to how CVAT's server process starts, and a single
definition of "who may see these counts".

**A second, smaller choice** — what to count. Counting CVAT shapes (41,866 on COCO) was taken over
collapsing grouped polygon parts into COCO instances (36,781). The cost: the headline number disagrees with
COCO's published count, and someone comparing them needs `OBJECTIVES.md` to know why.
