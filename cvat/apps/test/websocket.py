# Copyright (C) CVAT.ai Corporation
#
# SPDX-License-Identifier: MIT

"""
Live annotation counts: ws://<host>/api/tasks/<id>/annotation-stats/ws[?group_by=type]

Each message is the body of GET /api/tasks/<id>/annotation-stats, produced by running
that request through Django's middleware as the connecting user. This reuses the login
(the browser's session cookie), the OPA check and the serializer, and re-checks access
on every push. The first message is sent on connect, the next ones whenever the task's
annotations change. If the request is refused, the socket is closed with code
4000 + HTTP status (4401, 4403, 4404, ...) so the client knows not to reconnect.
"""

import asyncio
import io
import re

from asgiref.sync import sync_to_async
from django.core.handlers.asgi import ASGIRequest
from django.core.handlers.base import BaseHandler
from django.db import close_old_connections
from redis.asyncio import Redis

from .signals import annotation_change_channel, make_redis_client

PATH_PATTERN = re.compile(r"^/api/tasks/(?P<task_id>\d+)/annotation-stats/ws$")

# changes arriving within this window are answered with one snapshot,
# e.g. an import that touches the task once per job
DEBOUNCE_SECONDS = 0.2

_handler: BaseHandler | None = None


def _get_stats_response(scope: dict) -> tuple[int, str]:
    global _handler
    if _handler is None:
        _handler = BaseHandler()
        _handler.load_middleware()

    http_scope = {
        **scope,
        "type": "http",
        "method": "GET",
        "path": scope["path"].removesuffix("/ws"),
        # browsers send Accept-Encoding with the upgrade request; without dropping it
        # GZipMiddleware would compress the body, and a WebSocket frame is sent as is
        "headers": [header for header in scope["headers"] if header[0] != b"accept-encoding"],
    }

    # this runs outside Django's request cycle, which normally does this cleanup
    close_old_connections()
    try:
        response = _handler.get_response(ASGIRequest(http_scope, io.BytesIO()))
        return response.status_code, response.content.decode()
    finally:
        close_old_connections()


get_stats_response = sync_to_async(_get_stats_response)


async def _send_stats(scope: dict, send) -> bool:
    status_code, body = await get_stats_response(scope)
    if status_code != 200:
        await send({"type": "websocket.close", "code": 4000 + status_code})
        return False

    await send({"type": "websocket.send", "text": body})
    return True


async def _wait_for_disconnect(receive) -> None:
    while (await receive())["type"] != "websocket.disconnect":
        pass


async def _push_changes(scope: dict, send, pubsub) -> None:
    async for message in pubsub.listen():
        if message["type"] != "message":
            continue

        await asyncio.sleep(DEBOUNCE_SECONDS)
        while await pubsub.get_message(ignore_subscribe_messages=True, timeout=0):
            pass

        if not await _send_stats(scope, send):
            return


async def annotation_stats_websocket(scope: dict, receive, send) -> None:
    if (await receive())["type"] != "websocket.connect":
        return

    await send({"type": "websocket.accept"})

    task_id = int(PATH_PATTERN.match(scope["path"])["task_id"])
    redis = make_redis_client(Redis)
    pubsub = redis.pubsub()
    tasks = []
    try:
        # subscribe before the first snapshot, so a change made in between is not lost
        await pubsub.subscribe(annotation_change_channel(task_id))
        if not await _send_stats(scope, send):
            return

        tasks = [
            asyncio.create_task(_push_changes(scope, send, pubsub)),
            asyncio.create_task(_wait_for_disconnect(receive)),
        ]
        await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    finally:
        for task in tasks:
            task.cancel()
        await pubsub.aclose()
        await redis.aclose()


def route_websockets(http_application):
    """Sends the stats WebSocket to its handler and everything else to Django."""

    async def application(scope, receive, send):
        if scope["type"] == "websocket" and PATH_PATTERN.match(scope["path"]):
            return await annotation_stats_websocket(scope, receive, send)

        return await http_application(scope, receive, send)

    return application
