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

**Result — met.** Run medians 44.0, 43.9, 45.2, 43.2, 46.1 ms → **median 44.0 ms**, spread 43.2–46.1 ms
(slowest single request of 100: 72.9 ms). Raw output: [`evidence/mo1_stats_endpoint.txt`](evidence/mo1_stats_endpoint.txt),
script: [`evidence/measure_latency.sh`](evidence/measure_latency.sh).

Baseline, `GET /api/tasks/3/annotations` (5 single requests, 22.2 MB each): 3.71, 4.14, 4.15, 3.57, 3.58 s →
median 3.71 s, spread 3.57–4.15 s. Raw output: [`evidence/mo1_baseline_full_annotations.txt`](evidence/mo1_baseline_full_annotations.txt).

Honest reading: the target was cleared on the first measurement, with no tuning. The speed comes from the
decision to aggregate in SQL (three `GROUP BY` queries over the indexed `job_id`, plus one for the labels) instead of serialising
annotations, which is ~84× faster than the alternative and returns 4.6 KB instead of 22 MB. The target was set
before I knew the baseline; knowing it now, 100 ms was not ambitious for this data size. Where it would be
tested for real is a task 10–100× larger; I did not measure that.

## MO-2 — Live update delay

| Field | Entry |
|---|---|
| What is measured | Time from the response of an annotation save (`PATCH /api/jobs/{id}/annotations?action=create`, one rectangle) to the arrival of the updated counts on an already-open WebSocket for that task. |
| How | A script opens the WebSocket, waits for the initial snapshot, then sends the PATCH and timestamps both events with a monotonic clock. 5 runs. |
| Target | Median of 5 runs **≤ 500 ms**. |
| Why this number | Someone watching the chart while a colleague annotates should see the bar move within a breath of the save. Half a second is well inside that and catches regressions such as accidental polling. |
| Conditions | As MO-1. |
| Not included | Time spent by the annotation UI before it sends the save; browser rendering time of the chart. |

**Result — met.** 232.4, 233.6, 233.7, 233.3, 233.6 ms → **median 233.6 ms**, spread 232.4–233.7 ms, from the
host through Traefik. Raw output: [`evidence/mo2_live_update.txt`](evidence/mo2_live_update.txt), script:
[`evidence/measure_live_update.py`](evidence/measure_live_update.py).

Where the time goes: 200 ms is the server's deliberate debounce (`DEBOUNCE_SECONDS`, so a burst of
writes, such as an import touching the task once per job, is answered with one snapshot), and the
remaining ~34 ms is the recount (MO-1) plus the hop through Redis. The same flow seen from a real browser
page, including chart update, is in [`evidence/live_and_reconnect.txt`](evidence/live_and_reconnect.txt)
(250–314 ms). The debounce is the lever: halving it would roughly halve this number and double the
recounts during bursts.

## Dataset used

Task 3, `coco-val2017`: **all 5,000 images** of COCO 2017 val, segment size 500 (10 jobs), 80 labels,
`instances_val2017.json` imported as COCO 1.0.

COCO has 36,781 instances; CVAT stores **41,866 shapes** (41,420 polygons + 446 masks). The difference is
real, not a bug: CVAT turns each part of a multi-part COCO polygon into its own `LabeledShape` and links the
parts with the `group` field (3,522 instances have more than one part), and the 446 crowd regions become masks.
Collapsing grouped parts per frame in SQL gives exactly 36,781. The endpoint counts shapes, which is what CVAT
stores and what the annotation view lists as objects; the per-label check against the file is in
[`evidence/check_counts.txt`](evidence/check_counts.txt) (0 of 80 labels differ).
