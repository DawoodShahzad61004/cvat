# Copyright (C) CVAT.ai Corporation
#
# SPDX-License-Identifier: MIT

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.response import Response

from cvat.apps.engine.models import Task

from .permissions import AnnotationStatsPermission
from .serializers import AnnotationStatsQuerySerializer, AnnotationStatsSerializer
from .stats import get_annotation_stats


@extend_schema(tags=["tasks"])
class AnnotationStatsViewSet(viewsets.ViewSet):
    iam_permission_class = AnnotationStatsPermission

    @extend_schema(
        summary="Count the annotations of a task per label",
        parameters=[AnnotationStatsQuerySerializer],
        responses=AnnotationStatsSerializer,
    )
    def retrieve(self, request, pk):
        task = get_object_or_404(Task.objects.select_related("project", "organization"), pk=pk)
        self.check_object_permissions(request, task)

        query = AnnotationStatsQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        group_by_type = query.validated_data.get("group_by") == "type"

        stats = get_annotation_stats(task, group_by_type=group_by_type)
        return Response(AnnotationStatsSerializer(stats).data)
