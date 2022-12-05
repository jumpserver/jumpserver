# -*- coding: utf-8 -*-
#

from rest_framework.request import Request

__all__ = ['SerializerMixin']


class SerializerMixin:
    """ 根据用户请求动作的不同，获取不同的 `serializer_class `"""

    action: str
    request: Request

    serializer_classes = None
    single_actions = ['put', 'retrieve', 'patch']

    def get_serializer_classes(self):
        classes = getattr(self, 'serializer_classes', None) or {}
        return dict(classes)

    def get_serializer_class_by_view_action(self):
        serializer_classes = self.get_serializer_classes()
        if serializer_classes is None:
            return None
        if not isinstance(serializer_classes, dict):
            return None
        serializer_classes = dict(serializer_classes)
        view_action = self.request.query_params.get('action') or self.action or 'list'
        serializer_class = serializer_classes.get(view_action)

        if serializer_class is None:
            view_method = self.request.method.lower()
            serializer_class = serializer_classes.get(view_method)

        if serializer_class is None and view_action in self.single_actions:
            serializer_class = serializer_classes.get('single')
        if serializer_class is None:
            serializer_class = serializer_classes.get('display')
        if serializer_class is None:
            serializer_class = serializer_classes.get('default')
        return serializer_class

    def get_serializer_class(self):
        serializer_class = self.get_serializer_class_by_view_action()
        if serializer_class is None:
            serializer_class = super().get_serializer_class()
        return serializer_class
