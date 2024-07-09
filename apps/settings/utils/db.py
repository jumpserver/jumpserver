from django.apps import apps
from orgs.utils import tmp_to_root_org

__all__ = ['DBTableDataAnalyzer']


class DBTableDataAnalyzer(object):

    def get_tables_info(self):
        table_models = self.get_all_table_models()
        with tmp_to_root_org():
            table_info = self._fetch_tables_info(table_models)
        return table_info

    def get_all_table_models(self):
        # construct tables models
        table_models = set()
        for model in apps.get_models():
            table_models.add(model)
            for m2m_field in model._meta.many_to_many:
                table_models.add(m2m_field.remote_field.through)
        return table_models

    def _fetch_tables_info(self, table_models):
        """
            return: 
            info = {
                'table_name': {
                    'count': 100
                }
                ...
            }
        """
        info = {}
        for table_model in table_models:
            if table_model._meta.proxy == True:
                # skip proxy model
                continue
            count = self._fetch_row_count(table_model)
            data = {
                "count": count
            }
            table_name = table_model._meta.db_table
            info.update({f"{table_name}": data})
        return info

    def _fetch_row_count(self, table_model):
        # fetch table row count
        if hasattr(table_model, 'objects_raw'):
            # use objects_raw to count
            count = table_model.objects_raw.count()
        else:
            count = table_model.objects.count()
        return count
    