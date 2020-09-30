
from rest_framework_bulk.routes import BulkRouter

from accounts.api import AccountViewSet, AccountTypeViewSet

app_name = 'accounts'
router = BulkRouter()
router.register(r'accounts', AccountViewSet, 'account')
router.register(r'account-types', AccountTypeViewSet, 'account-type')


urlpatterns = [
]

urlpatterns += router.urls
