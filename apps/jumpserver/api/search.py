from django.contrib.postgres.search import SearchVector
from rest_framework.views import APIView
from rest_framework.response import Response
from django.conf import settings
from django.db.models import Q


class GlobalSearchView(APIView):
    limits = 10
    rbac_perms = {
        'GET': 'assets.view_asset',
    }

    def get_models(self):
        from users.models import User
        from assets.models import Asset
        from accounts.models import Account
        return [
            [User, ['name', 'username', 'email']],
            [Asset, ['name', 'address']],
            [Account, ['name', 'username']],
        ]

    def search_model(self, model, fields, keyword):
        if settings.DB_ENGINE == 'postgres':
            qs = model.objects.annotate(
                search=SearchVector(*fields),
            ).filter(search=keyword)
        else:
            q = Q()
            for field in fields:
                q |= Q(**{field + '__icontains': keyword})
            qs = model.objects.filter(q)
        return qs[:self.limits]

    def get_result(self, model, fields, item, keyword):
        d = {
            "id": item.id, "name": item.name, 
            "model": model.__name__, "model_label": model._meta.verbose_name,
        }
        content = ""
        for field in fields:
            field_label = model._meta.get_field(field).verbose_name
            value = getattr(item, field)

            if isinstance(value, str) and keyword not in value:
                continue

            content += f"{field_label}: {value}; "
            d["content"] = content
        return d

    def get(self, request):
        q = request.query_params.get("q", "").strip()
        models = self.get_models()
        results = []

        for model, fields in models:
            qs = self.search_model(model, fields, q)
            for item in qs:
                d = self.get_result(model, fields, item, q)
                results.append(d)

        return Response(results)