from rest_framework.views import APIView
from rest_framework.permissions import OperandHolder, AND, OR, NOT
from django.views.generic.edit import FormView
from django.contrib.auth.mixins import LoginRequiredMixin

from rest_framework.permissions import AllowAny, IsAuthenticated
from rbac.permissions import RBACPermission
from common.utils import lazyproperty
from .body_fields_generator import (
    FieldsGenerator, FormFieldsGenerator, SerializerFieldsGenerator
)
from .const import fake_request


__all__ = ['CustomView']


class CustomView:

    def __init__(self, view_func):
        self.view_func = view_func
    
    @property
    def view_class(self):
        cls = getattr(self.view_func, 'view_class', None)
        if not cls:
            cls = getattr(self.view_func, 'cls', None)
        return cls
    
    @property
    def view_path(self):
        if self.view_class:
            v = self.view_class
        else:
            v = self.view_func
        return f'{v.__module__}.{v.__name__}'
    
    @property
    def view_type(self):
        if self.view_class:
            return 'class'
        else:
            return 'function'
    
    @lazyproperty
    def fields_generator(self):
        generator = None
        if self.view_class:
            if issubclass(self.view_class, FormView):
                generator = self.get_form_fields_generator()
            elif issubclass(self.view_class, APIView):
                generator= self.get_serializer_fields_generator()
            else:
                # 其他类视图暂不处理
                pass
        else:
            # 函数视图暂不处理
            pass
        if not generator:
            generator = FieldsGenerator()
        return generator
    
    @property
    def write_fields_schema(self):
         return self.fields_generator.write_fields_schema()
    
    @property
    def required_fields(self):
        return self.fields_generator.required_fields()
    
    def get_form_fields_generator(self):
        if hasattr(self.view_class, 'get_form_class_comprehensive'):
            view_instance = self.view_class(request=fake_request)
            form_class = view_instance.get_form_class_comprehensive()
        else:
            form_class = getattr(self.view_class, 'form_class', None)
            if not form_class:
                if hasattr(self.view_class, 'get_form_class'):
                    # TODO: 实例化 view 类需要传入 request 参数
                    view_instance = self.view_class(request=fake_request)
                    form_class = view_instance.get_form_class()
        if form_class:
            return FormFieldsGenerator(raw_class=form_class, view=self)

    def get_serializer_fields_generator(self):
        serializer_class = getattr(self.view_class, 'serializer_class', None)
        if not serializer_class:
            if hasattr(self.view_class, 'get_serializer_class'):
                # TODO: 实例化 view 类需要传入 request 参数
                view_instance = self.view_class(request=fake_request)
                serializer_class = view_instance.get_serializer_class()
        if serializer_class:
            return SerializerFieldsGenerator(raw_class=serializer_class, view=self)

    @property
    def query_fields_schema(self):
        return {}

    @lazyproperty
    def requires_auth(self):
        if self.view_class:
            return self.check_view_class_requires_auth()
        else:
            return self.check_view_func_requires_auth()
    
    def check_view_class_requires_auth(self):
        if issubclass(self.view_class, LoginRequiredMixin):
            return True

        permission_classes = getattr(self.view_class, 'permission_classes', [])
        if not permission_classes:
            return False
        
        return self.check_permission_classes_requires_auth(permission_classes)
    
    def check_permission_classes_requires_auth(self, permission_classes, operator=AND):
        if operator == AND:
            for pc in permission_classes:
                if self.check_permission_class_requires_auth(pc):
                    return True
            return False
        elif operator == OR:
            for pc in permission_classes:
                if not self.check_permission_class_requires_auth(pc):
                    return False
            return True
        elif operator == NOT:
            raise ValueError('NOT operator is not supported in permission_classes')
        else:
            return False
    
    def check_permission_class_requires_auth(self, permission_class):
        if isinstance(permission_class, OperandHolder):
            operator  = permission_class.operator_class
            op1_class = permission_class.op1_class
            op2_class = permission_class.op2_class
            permission_classes = [op1_class, op2_class]
            return self.check_permission_classes_requires_auth(permission_classes, operator)
        else:
            if issubclass(permission_class, (IsAuthenticated, RBACPermission)):
                return True
            if issubclass(permission_class, (AllowAny, )):
                return False
            if hasattr(permission_class, '__name__'):
                if 'Authenticated' in permission_class.__name__:
                    return True
                if permission_class.__name__.startswith('UserConfirmation'):
                    return True
            return False

    def check_view_func_requires_auth(self):
        if hasattr(self.view_func, '__wrapped__'):
            if hasattr(self.view_func, '__name__'):
                if 'login_required' in str(self.view_func):
                    return True
        return False