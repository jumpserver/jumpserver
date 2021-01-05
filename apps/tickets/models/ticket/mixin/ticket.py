from . import base, meta

__all__ = ['TicketModelMixin']


class TicketSetDisplayFieldMixin(meta.ConstructDisplayFieldMixin, base.SetDisplayFieldMixin):
    """ 设置 ticket display 字段(只设置，不保存)"""
    pass


class TicketConstructBodyMixin(meta.ConstructBodyMixin, base.ConstructBodyMixin):
    """ 构造 ticket body 信息 """
    pass


class TicketCreatePermissionMixin(meta.CreatePermissionMixin, base.CreatePermissionMixin):
    """ 创建 ticket 相关授权规则"""
    pass


class TicketCreateCommentMixin(base.CreateCommentMixin):
    """ 创建 ticket 备注"""
    pass


class TicketModelMixin(
    TicketSetDisplayFieldMixin, TicketConstructBodyMixin, TicketCreatePermissionMixin,
    TicketCreateCommentMixin
):
    pass
