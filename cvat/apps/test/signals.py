# Copyright (C) CVAT.ai Corporation
#
# SPDX-License-Identifier: MIT

from functools import cache

from django.conf import settings
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from redis import Redis

from cvat.apps.engine.models import Task


def annotation_change_channel(task_id: int) -> str:
    return f"annotation-stats:task:{task_id}"


def make_redis_client(redis_class=Redis):
    return redis_class(
        host=settings.REDIS_INMEM_SETTINGS["HOST"],
        port=settings.REDIS_INMEM_SETTINGS["PORT"],
        password=settings.REDIS_INMEM_SETTINGS["PASSWORD"] or None,
    )


@cache
def _get_publisher() -> Redis:
    return make_redis_client()


@receiver(post_save, sender=Task)
def publish_task_change(sender, instance: Task, **kwargs):
    """
    Every annotation write ends with task.touch() (see TaskAnnotation._set_updated_date),
    so a saved Task is the signal that its counts may have changed, in whichever
    process did the write: the server or an import worker. Other task saves (labels,
    name) are published too; a snapshot nobody needed costs one GROUP BY.

    Published after commit, so subscribers recount committed data. robust=True keeps
    a Redis outage from failing an annotation save that has already been committed.
    """
    transaction.on_commit(
        lambda: _get_publisher().publish(annotation_change_channel(instance.id), ""),
        robust=True,
    )
