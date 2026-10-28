# Copyright (C) CVAT.ai Corporation
#
# SPDX-License-Identifier: MIT

from django.urls import path

from .views import AnnotationStatsViewSet

urlpatterns = [
    path(
        "tasks/<int:pk>/annotation-stats",
        AnnotationStatsViewSet.as_view(
            {"get": "retrieve"}, detail=True, basename="annotation_stats"
        ),
        name="task-annotation-stats",
    ),
]
