# Copyright (C) CVAT.ai Corporation
#
# SPDX-License-Identifier: MIT

from collections import Counter, defaultdict

from django.db.models import Count

from cvat.apps.engine.models import Job, JobType, LabeledImage, LabeledShape, LabeledTrack, Task


def get_annotation_stats(task: Task, *, group_by_type: bool = False) -> dict:
    """
    Counts the annotations of a task per label, in the database.

    Only regular annotation jobs are counted: ground truth and consensus replica
    jobs hold copies of the same objects. Skeleton elements are part of their
    skeleton, so only top-level shapes and tracks are counted. A track counts once.

    With group_by_type, each label also gets its count split by annotation type:
    the shape type (rectangle, polygon, mask, ...), "track" or "tag".
    """
    job_ids = Job.objects.filter(segment__task_id=task.id, type=JobType.ANNOTATION).values("id")

    counts = defaultdict(Counter)  # label id -> annotation type -> count
    shapes = LabeledShape.objects.filter(job_id__in=job_ids, parent__isnull=True)
    for row in shapes.order_by().values("label_id", "type").annotate(count=Count("id")):
        counts[row["label_id"]][row["type"]] += row["count"]

    for annotation_type, queryset in (
        ("track", LabeledTrack.objects.filter(job_id__in=job_ids, parent__isnull=True)),
        ("tag", LabeledImage.objects.filter(job_id__in=job_ids)),
    ):
        for row in queryset.order_by().values("label_id").annotate(count=Count("id")):
            counts[row["label_id"]][annotation_type] += row["count"]

    labels = []
    for label in task.get_labels():
        label_counts = counts[label.id]
        entry = {
            "id": label.id,
            "name": label.name,
            "color": label.color,
            "count": label_counts.total(),
        }
        if group_by_type:
            entry["by_type"] = dict(label_counts)
        labels.append(entry)
    labels.sort(key=lambda label: (-label["count"], label["name"]))

    return {
        "task_id": task.id,
        "total": sum(label["count"] for label in labels),
        "labels": labels,
    }
