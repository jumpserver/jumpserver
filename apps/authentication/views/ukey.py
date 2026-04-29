from django.views.generic import TemplateView

from common.utils import get_logger
from .utils import redirect_to_guard_view
from .. import errors, mixins

logger = get_logger(__name__)
__all__ = ["UserUKeyBindView"]


class UserUKeyBindView(mixins.AuthMixin, TemplateView):
    template_name = "authentication/bind_ukey.html"

    def get(self, request, *args, **kwargs):
        try:
            self.get_user_from_session()
        except errors.SessionEmptyError:
            return redirect_to_guard_view('session_empty')
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        user_id = kwargs.get("user_id", "")
        context = {"user_id": user_id}
        kwargs.update(context)
        return super().get_context_data(**kwargs)
