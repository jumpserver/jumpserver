from . import base, apply_asset

__all__ = ['TicketModelMixin']


class TicketConstructBodyMixin(
    base.ConstructBodyMixin,
    apply_asset.ConstructBodyMixin
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
