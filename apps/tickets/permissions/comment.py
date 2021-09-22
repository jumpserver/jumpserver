# -*- coding: utf-8 -*-
#
from rest_framework import permissions


class IsSwagger(permissions.BasePermission):
    def has_permission(self, request, view):
        return getattr(view, 'swagger_fake_view', False)


class IsApplicant(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user == view.ticket.applicant


class IsAssignee(permissions.BasePermission):
    def has_permission(self, request, view):
        return view.ticket.has_all_assignee(request.user)
