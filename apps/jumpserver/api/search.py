import re

from django.contrib.postgres.search import SearchVector
from rest_framework.views import APIView
from rest_framework.response import Response
from django.conf import settings
from django.db.models import Q
from rest_framework.permissions import IsAuthenticated


class GlobalSearchView(APIView):
    limits = 5
    permission_classes = [IsAuthenticated]
    
    def get_models(self):
        from users.models import User, UserGroup
        from assets.models import Asset
        from accounts.models import Account
        from perms.models import AssetPermission
        return [
            [User, ['name', 'username']],
            [UserGroup, ['name', 'comment']],
            [Asset, ['name', 'address']],
            [Account, ['name', 'username']],
            [AssetPermission, ['name', 'comment']],
        ]

    def search_model(self, model, fields, keyword):
        queryset = model.objects.all()
        if hasattr(model, 'get_queryset'):
            queryset = model.get_queryset()

        if settings.DB_ENGINE == 'postgres':
            qs = model.objects.annotate(
                search=SearchVector(*fields),
            ).filter(search=keyword)
        else:
            q = Q()
            for field in fields:
                q |= Q(**{field + '__icontains': keyword})
            qs = queryset.filter(q)
        return qs[:self.limits]

    def get_result(self, model, fields, item, keyword):
        d = {
            "id": item.id, "name": item.name, 
            "model": model.__name__, "model_label": model._meta.verbose_name,
        }
        content = ""
        value_list = [item.name]

        for field in fields:
            field_label = model._meta.get_field(field).verbose_name
            value = getattr(item, field)

            if value in value_list:
                continue
            value_list.append(value)

            if content:
                continue
            content += f"{field_label}: {value} "

        display = str(item).replace(item.name, '').replace('(', '').replace(')', '')
        if display not in value:
            content += f" {display} "

        d["content"] = content
        return d

    def get(self, request):
        q = request.query_params.get("q", "").strip()
        models = self.get_models()
        results = []

        for model, fields in models:
            perm = model._meta.app_label + '.' + 'view_' + model._meta.model_name
            if not request.user.has_perm(perm):
                continue
            qs = self.search_model(model, fields, q)
            for item in qs:
                d = self.get_result(model, fields, item, q)
                results.append(d)

        return Response(results)