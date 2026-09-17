from rest_framework import generics
from rest_framework.response import Response

from users.serializers import UserGroupTreeQuerySerializer
from users.tree import UserGroupTree


__all__ = ['UserGroupTreeApi']


class UserGroupTreeApi(generics.GenericAPIView):
    serializer_class = UserGroupTreeQuerySerializer
    rbac_perms = {
        'GET': 'perms.view_assetpermission',
    }

    def get(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        tree = UserGroupTree()

        if data.get('search'):
            nodes = tree.search(
                data['search'], order=data['order'], limit=data['limit']
            )
        elif data.get('parent_type'):
            nodes = tree.children(
                data['parent_type'], data['parent_id'], data['order'],
                data['limit'], data['offset'],
            )
        else:
            nodes = tree.root()
        return Response(nodes)
