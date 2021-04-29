from django.urls import path

from .. import views

app_name = 'common'

urlpatterns = [
    # login
    path('flash-message/', views.FlashMessageMsgView.as_view(), name='flash-message'),
]