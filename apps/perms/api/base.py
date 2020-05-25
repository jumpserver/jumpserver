from django.db.models import F
from orgs.mixins.api import OrgBulkModelViewSet
from orgs.utils import current_org

RELATION_QUERY_NAME = 'relation_query_name'


class RelationMixin(OrgBulkModelViewSet):
    def get_queryset(self):
        relation_query_name = getattr(self, RELATION_QUERY_NAME)

        assert relation_query_name, f'''
                                Your view should has {RELATION_QUERY_NAME} attr like:

                                class YouView:
                                    {RELATION_QUERY_NAME} = 'some name'
                            '''

        queryset = self.model.objects.all()
        org_id = current_org.org_id()

        if org_id is not None:
            queryset = queryset.filter(**{f'{relation_query_name}__org_id': org_id})

        queryset = queryset.annotate(**{f'{relation_query_name}_display': F(f'{relation_query_name}__name')})
        return queryset