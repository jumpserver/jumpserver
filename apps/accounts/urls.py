
from rest_framework_bulk.routes import BulkRouter

from accounts.api import AccountViewSet, AccountTypeViewSet, PropFieldViewSet

app_name = 'accounts'
router = BulkRouter()
router.register(r'accounts', AccountViewSet, 'account')
router.register(r'account-types', AccountTypeViewSet, 'account-type')
router.register(r'account-prop-fields', PropFieldViewSet, 'account-prop-field')


urlpatterns = [
]

urlpatterns += router.urls
