from rest_framework import permissions


__all__ = ['IsRemoteApp']


class IsRemoteApp(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.category_remote_app
