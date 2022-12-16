import os
import zipfile

from django.conf import settings
from orgs.mixins.api import OrgBulkModelViewSet
from ..exception import PlaybookNoValidEntry
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

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.filter(creator=self.request.user)
        return queryset

    def perform_create(self, serializer):
        instance = serializer.save()
        src_path = os.path.join(settings.MEDIA_ROOT, instance.path.name)
        dest_path = os.path.join(settings.DATA_DIR, "ops", "playbook", instance.id.__str__())
        unzip_playbook(src_path, dest_path)
        valid_entry = ('main.yml', 'main.yaml', 'main')
        for f in os.listdir(dest_path):
            if f in valid_entry:
                return
        os.remove(dest_path)
        raise PlaybookNoValidEntry
