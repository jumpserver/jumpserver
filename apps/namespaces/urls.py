from django.urls import path
from rest_framework_bulk.routes import BulkRouter

from namespaces.api import NamespaceViewSet, NamespaceUserView


app_name = 'namespaces'
router = BulkRouter()
router.register(r'namespaces', NamespaceViewSet, 'namespace')

urlpatterns = [
    path('namespace-users/', NamespaceUserView.as_view(), name='namespace-users'),
]

urlpatterns += router.urls
