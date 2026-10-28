# Copyright (C) CVAT.ai Corporation
#
# SPDX-License-Identifier: MIT

from collections import Counter

from django.db.models import Count

from cvat.apps.engine.models import Job, JobType, LabeledImage, LabeledShape, LabeledTrack, Task


def get_annotation_stats(task: Task) -> dict:
    """
    Counts the annotations of a task per label, in the database.

    Only regular annotation jobs are counted: ground truth and consensus replica
    jobs hold copies of the same objects. Skeleton elements are part of their
    skeleton, so only top-level shapes and tracks are counted. A track counts once.
    """
    job_ids = Job.objects.filter(segment__task_id=task.id, type=JobType.ANNOTATION).values("id")

    counts = Counter()
    for queryset in (
        LabeledShape.objects.filter(job_id__in=job_ids, parent__isnull=True),
        LabeledTrack.objects.filter(job_id__in=job_ids, parent__isnull=True),
        LabeledImage.objects.filter(job_id__in=job_ids),
    ):
        for row in queryset.order_by().values("label_id").annotate(count=Count("id")):
            counts[row["label_id"]] += row["count"]

    labels = [
        {"id": label.id, "name": label.name, "color": label.color, "count": counts[label.id]}
        for label in task.get_labels()
    ]
    labels.sort(key=lambda label: (-label["count"], label["name"]))

    return {
        "task_id": task.id,
        "total": sum(label["count"] for label in labels),
        "labels": labels,
    }
