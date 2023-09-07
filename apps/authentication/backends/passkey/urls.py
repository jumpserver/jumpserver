from rest_framework.routers import DefaultRouter

from . import api

router = DefaultRouter()
router.register('passkeys', api.PassKeyViewSet, 'passkey')

urlpatterns = []
urlpatterns += router.urls
