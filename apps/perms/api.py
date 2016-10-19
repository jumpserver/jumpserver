# ~*~ coding: utf-8 ~*~
# 

from rest_framework.views import APIView, Response
from users.backends import IsValidUser
from .utils import get_user_granted_assets, get_user_granted_asset_groups


class UserAssetsGrantedApi(APIView):
    permission_classes = (IsValidUser,)

    def get(self, request, *args, **kwargs):
        assets_json = []
        user = request.user

        if user:
            assets = get_user_granted_assets(user)

            for asset, system_users in assets.items():
                assets_json.append({
                    'id': asset.id,
                    'hostname': asset.hostname,
                    'ip': asset.ip,
                    'port': asset.port,
                    'system_users': [system_user.name for system_user in system_users],
                    'comment': asset.comment
                })

        return Response(assets_json, status=200)

