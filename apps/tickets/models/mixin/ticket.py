from . import base, apply_asset, login_confirm

__all__ = ['TicketModelMixin']


class TicketConstructBodyMixin(
    base.ConstructBodyMixin,
    apply_asset.ConstructBodyMixin,
    login_confirm.ConstructBodyMixin
):
    pass


class TicketCreatePermissionMixin(
    base.CreatePermissionMixin,
    apply_asset.CreatePermissionMixin
):
    pass


class TicketCreateCommentMixin(
    base.CreateCommentMixin
):
    pass


class TicketModelMixin(
    TicketConstructBodyMixin, TicketCreatePermissionMixin, TicketCreateCommentMixin
):
    pass
