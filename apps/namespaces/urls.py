from rest_framework_bulk.routes import BulkRouter

from namespaces.api import NamespaceViewSet


app_name = 'namespaces'
router = BulkRouter()
router.register(r'namespaces', NamespaceViewSet, 'namespace')

urlpatterns = [

]

urlpatterns += router.urls
