# Objectives

Targets are fixed here before any measurement. Results are appended below each one,
with raw output under `docs/evidence/`.

**Machine:** Intel Core i5-13450HX (10 cores / 16 threads), 16 GB RAM (7.6 GB for Docker),
Windows 11 Home 10.0.26300, Docker Desktop 29.6.2.
**CVAT commit:** `4a09e27ff869b7aebbfdb07b29c4a34904a0221d` (images `cvat/server:dev`, `cvat/ui:dev`).

## MO-1 — Stats endpoint latency

| Field | Entry |
|---|---|
| What is measured | Wall time of `GET /api/tasks/{id}/annotation-stats` for the COCO val2017 task, from the request leaving the client to the last byte received. |
| How | `curl -w '%{time_total}'` from the host through Traefik (`localhost:8080`), token auth. One run = 1 warm-up request + 20 timed requests; the run's result is the median of the 20. 5 runs. |
| Target | Median of the 5 run results **≤ 100 ms**. |
| Why this number | With live updates the counts are recomputed after every annotation save, for every open stats page. 100 ms is the point below which an update reads as instant, and it leaves room for many open pages per save. The obvious alternative — fetch `GET /api/tasks/{id}/annotations` and count in the browser — is measured the same way as the baseline, so the number has something to be compared to. |
| Conditions | Local Docker stack, default compose file, the COCO task (image and annotation counts below), no other load, no other browser tabs on CVAT. |
| Not included | First request after a server restart (cold Python imports, cold DB cache); Basic auth (it hashes the password on every request and would measure PBKDF2, not the endpoint). |

## MO-2 — Live update delay

| Field | Entry |
|---|---|
| What is measured | Time from the response of an annotation save (`PATCH /api/jobs/{id}/annotations?action=create`, one rectangle) to the arrival of the updated counts on an already-open WebSocket for that task. |
| How | A script opens the WebSocket, waits for the initial snapshot, then sends the PATCH and timestamps both events with a monotonic clock. 5 runs. |
| Target | Median of 5 runs **≤ 500 ms**. |
| Why this number | Someone watching the chart while a colleague annotates should see the bar move within a breath of the save. Half a second is well inside that and catches regressions such as accidental polling. |
| Conditions | As MO-1. |
| Not included | Time spent by the annotation UI before it sends the save; browser rendering time of the chart. |

## Dataset used

_(Filled in after import: number of images, number of annotations, labels.)_
