from django.views.generic import View
from django.shortcuts import redirect
from common.permissions import IsValidUser
from common.views.mixins import PermissionsMixin

__all__ = ['IndexView']


class IndexView(PermissionsMixin, View):
    permission_classes = [IsValidUser]

    def get(self, request, *args, **kwargs):
        return redirect('/ui/')
