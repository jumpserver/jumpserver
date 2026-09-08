from django.urls import path

from .runtime_store import RuntimeStoreView

app_name = 'chat_ai'

urlpatterns = [
    path('runtime-store/', RuntimeStoreView.as_view(), name='runtime-store'),
]
