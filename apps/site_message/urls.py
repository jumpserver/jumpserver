from rest_framework.routers import DefaultRouter

from . import api

app_name = 'site_message'

router = DefaultRouter()
router.register('site-message', api.SiteMessageViewSet, 'site-message')

urlpatterns = router.urls
