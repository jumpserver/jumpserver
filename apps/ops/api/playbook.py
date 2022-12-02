import os
import zipfile

from django.conf import settings

from orgs.mixins.api import OrgBulkModelViewSet
from ..models import Playbook
from ..serializers.playbook import PlaybookSerializer

__all__ = ["PlaybookViewSet"]


def unzip_playbook(src, dist):
    fz = zipfile.ZipFile(src, 'r')
    for file in fz.namelist():
        fz.extract(file, dist)


class PlaybookViewSet(OrgBulkModelViewSet):
    serializer_class = PlaybookSerializer
    permission_classes = ()
    model = Playbook

    def perform_create(self, serializer):
        instance = serializer.save()
        src_path = os.path.join(settings.MEDIA_ROOT, instance.path.name)
        dest_path = os.path.join(settings.DATA_DIR, "ops", "playbook", instance.id.__str__())
        if os.path.exists(dest_path):
            os.makedirs(dest_path)
        unzip_playbook(src_path, dest_path)
