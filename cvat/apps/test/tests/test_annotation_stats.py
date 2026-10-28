# Copyright (C) CVAT.ai Corporation
#
# SPDX-License-Identifier: MIT

from django.contrib.auth.models import Group
from rest_framework import status
from rest_framework.test import APITestCase

from cvat.apps.engine.models import (
    Job,
    JobType,
    Label,
    LabeledImage,
    LabeledShape,
    LabeledTrack,
    Segment,
    Task,
)
from cvat.apps.engine.tests.utils import ForceLogin
from cvat.apps.iam.models import User


class AnnotationStatsApiTest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        users = Group.objects.get(name="user")
        cls.owner = User.objects.create_user(username="owner")
        cls.outsider = User.objects.create_user(username="outsider")
        for user in (cls.owner, cls.outsider):
            user.groups.add(users)

        cls.task = Task.objects.create(name="stats", owner=cls.owner)
        segment = Segment.objects.create(task=cls.task, start_frame=0, stop_frame=9)
        job = Job.objects.create(segment=segment)
        gt_job = Job.objects.create(segment=segment, type=JobType.GROUND_TRUTH)

        cat = Label.objects.create(task=cls.task, name="cat")
        dog = Label.objects.create(task=cls.task, name="dog")
        Label.objects.create(task=cls.task, name="unused")
        body = Label.objects.create(task=cls.task, name="body", type="skeleton")
        nose = Label.objects.create(task=cls.task, name="nose", parent=body)

        box = dict(frame=0, type="rectangle", points=[0, 0, 1, 1])
        LabeledShape.objects.create(job=job, label=cat, **box)
        LabeledShape.objects.create(job=job, label=cat, **box)
        LabeledShape.objects.create(job=gt_job, label=cat, **box)
        LabeledTrack.objects.create(job=job, label=cat, frame=0)
        LabeledImage.objects.create(job=job, label=dog, frame=0)
        skeleton = LabeledShape.objects.create(job=job, label=body, frame=0, type="skeleton")
        LabeledShape.objects.create(
            job=job, label=nose, parent=skeleton, frame=0, type="points", points=[0, 0]
        )

    def _get_stats(self, user=None, query_params=None):
        url = f"/api/tasks/{self.task.id}/annotation-stats"
        if user is None:
            return self.client.get(url, query_params=query_params)

        with ForceLogin(user, self.client):
            return self.client.get(url, query_params=query_params)

    def test_counts_per_label(self):
        response = self._get_stats(self.owner)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        counts = {label["name"]: label["count"] for label in response.json()["labels"]}
        # ground truth copies and skeleton elements are not counted, a track counts once
        self.assertEqual(counts, {"cat": 3, "dog": 1, "body": 1, "unused": 0})
        self.assertEqual(response.json()["total"], 5)

    def test_labels_are_sorted_by_count(self):
        response = self._get_stats(self.owner)

        names = [label["name"] for label in response.json()["labels"]]
        self.assertEqual(names, ["cat", "body", "dog", "unused"])

    def test_group_by_type(self):
        response = self._get_stats(self.owner, {"group_by": "type"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        by_type = {label["name"]: label["by_type"] for label in response.json()["labels"]}
        self.assertEqual(
            by_type,
            {
                "cat": {"rectangle": 2, "track": 1},
                "dog": {"tag": 1},
                "body": {"skeleton": 1},
                "unused": {},
            },
        )

    def test_counts_are_not_split_by_default(self):
        response = self._get_stats(self.owner)

        self.assertNotIn("by_type", response.json()["labels"][0])

    def test_unknown_grouping_is_rejected(self):
        response = self._get_stats(self.owner, {"group_by": "job"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_anonymous_request_is_rejected(self):
        self.assertEqual(self._get_stats().status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_without_access_is_rejected(self):
        self.assertEqual(self._get_stats(self.outsider).status_code, status.HTTP_403_FORBIDDEN)
