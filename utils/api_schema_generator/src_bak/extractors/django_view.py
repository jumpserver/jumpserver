from django.contrib.auth.mixins import LoginRequiredMixin
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.permissions import OperandHolder, AND, OR, NOT
from rbac.permissions import RBACPermission

from .base import BaseExtractor

__all__ = ['DjangoViewExtractor']


class DjangoViewExtractor(BaseExtractor):

    def view_requires_auth(self):
        if issubclass(self.view.view_class, LoginRequiredMixin):
            return True
        permission_classes = getattr(self.view.view_class, 'permission_classes', [])
        if not permission_classes:
            return False
        return self.check_view_permission_classes_requires_auth(permission_classes)
    
    def check_view_permission_classes_requires_auth(self, permission_classes, operator=AND):
        if operator == AND:
            for pc in permission_classes:
                if self.check_view_permission_class_requires_auth(pc):
                    return True
            return False
        elif operator == OR:
            for pc in permission_classes:
                if not self.check_view_permission_class_requires_auth(pc):
                    return False
            return True
        elif operator == NOT:
            raise ValueError('NOT operator is not supported in permission_classes')
        else:
            return False

    def check_view_permission_class_requires_auth(self, permission_class):
        if isinstance(permission_class, OperandHolder):
            operator  = permission_class.operator_class
            op1_class = permission_class.op1_class
            op2_class = permission_class.op2_class
            permission_classes = [op1_class, op2_class]
            return self.check_view_permission_classes_requires_auth(permission_classes, operator)
        else:
            if issubclass(permission_class, (IsAuthenticated, RBACPermission)):
                return True
            if issubclass(permission_class, (AllowAny, )):
                return False

            permission_class_name: str = getattr(permission_class, '__name__', None)
            if not permission_class_name:
                return False
            if 'Authenticated' in permission_class_name:
                return True
            if permission_class_name.startswith('UserConfirmation'):
                return True
            return False