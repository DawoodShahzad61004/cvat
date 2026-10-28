# Copyright (C) CVAT.ai Corporation
#
# SPDX-License-Identifier: MIT

from rest_framework import serializers


class LabelCountSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    color = serializers.CharField()
    count = serializers.IntegerField()
    by_type = serializers.DictField(child=serializers.IntegerField(), required=False)


class AnnotationStatsSerializer(serializers.Serializer):
    task_id = serializers.IntegerField()
    total = serializers.IntegerField()
    labels = LabelCountSerializer(many=True)


class AnnotationStatsQuerySerializer(serializers.Serializer):
    group_by = serializers.ChoiceField(choices=["type"], required=False)
