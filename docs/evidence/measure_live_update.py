"""
MO-2: time from an annotation save's response to the updated counts arriving on an
open stats WebSocket. Creates one rectangle per run and deletes it afterwards.

Needs the `websockets` package (pip install websockets).
usage: python measure_live_update.py HOST:PORT TASK_ID TOKEN
"""

import asyncio
import json
import statistics
import sys
import time
import urllib.request

from websockets.asyncio.client import connect

host, task_id, token = sys.argv[1], int(sys.argv[2]), sys.argv[3]
headers = {"Authorization": f"Token {token}", "Content-Type": "application/json"}


def api(method, path, body=None):
    request = urllib.request.Request(
        f"http://{host}{path}",
        method=method,
        headers=headers,
        data=json.dumps(body).encode() if body is not None else None,
    )
    with urllib.request.urlopen(request) as response:
        return json.load(response)


def counts(message):
    return {label["name"]: label["count"] for label in json.loads(message)["labels"]}


async def main():
    job_id = api("GET", f"/api/jobs?task_id={task_id}&page_size=1")["results"][0]["id"]
    label = api("GET", f"/api/labels?task_id={task_id}&page_size=1")["results"][0]
    shape = {
        "type": "rectangle",
        "frame": 0,
        "label_id": label["id"],
        "points": [10, 10, 50, 50],
        "occluded": False,
        "z_order": 0,
        "attributes": [],
        "group": 0,
        "source": "manual",
    }
    delays = []
    url = f"ws://{host}/api/tasks/{task_id}/annotation-stats/ws"
    async with connect(url, additional_headers={"Authorization": f"Token {token}"}) as ws:
        before = counts(await ws.recv())[label["name"]]
        for run in range(1, 6):
            created = api(
                "PATCH",
                f"/api/jobs/{job_id}/annotations?action=create",
                {"shapes": [shape], "tracks": [], "tags": []},
            )
            saved_at = time.monotonic()
            after = counts(await ws.recv())[label["name"]]
            delay_ms = (time.monotonic() - saved_at) * 1000
            delays.append(delay_ms)
            print(f"run {run}: {delay_ms:.1f} ms  ({label['name']}: {before} -> {after})")

            api(
                "PATCH",
                f"/api/jobs/{job_id}/annotations?action=delete",
                {"shapes": created["shapes"], "tracks": [], "tags": []},
            )
            before = counts(await ws.recv())[label["name"]]

    print(
        f"median {statistics.median(delays):.1f} ms, "
        f"spread {min(delays):.1f}-{max(delays):.1f} ms, n={len(delays)}"
    )


asyncio.run(main())
