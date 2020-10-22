
class SerializeApplicationToTreeNodeMixin:

    @staticmethod
    def _serialize_db(db):
        return {
            'id': db.id,
            'name': db.name,
            'title': db.name,
            'pId': '',
            'open': False,
            'iconSkin': 'database',
            'meta': {'type': 'database_app'}
        }

    @staticmethod
    def _serialize_remote_app(remote_app):
        return {
            'id': remote_app.id,
            'name': remote_app.name,
            'title': remote_app.name,
            'pId': '',
            'open': False,
            'isParent': False,
            'iconSkin': 'chrome',
            'meta': {'type': 'remote_app'}
        }

    @staticmethod
    def _serialize_cloud(cloud):
        return {
            'id': cloud.id,
            'name': cloud.name,
            'title': cloud.name,
            'pId': '',
            'open': False,
            'isParent': False,
            'iconSkin': 'k8s',
            'meta': {'type': 'k8s_app'}
        }

    def dispatch_serialize(self, application):
        method_name = f'_serialize_{application.category}'
        data = getattr(self, method_name)(application)
        return data

    def serialize_applications(self, applications):
        data = [self.dispatch_serialize(application) for application in applications]
        return data
