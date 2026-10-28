# Copyright (C) CVAT.ai Corporation
#
# SPDX-License-Identifier: MIT

from cvat.apps.engine.permissions import TaskPermission
from cvat.apps.iam.permissions import OpenPolicyAgentPermission


class AnnotationStatsPermission(OpenPolicyAgentPermission):
    """
    Counting a task's annotations reveals its annotations, so this reuses
    the task's own "view:annotations" rule instead of adding a new policy.
    """

    @classmethod
    def create(cls, request, view, obj, iam_context):
        return [
            TaskPermission.create_base_perm(
                request, view, TaskPermission.Scopes.VIEW_ANNOTATIONS, iam_context, obj
            )
        ]
