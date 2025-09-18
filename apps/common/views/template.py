import logging
import os

from django.conf import settings
from django.template import Context
from django.template import Engine, TemplateSyntaxError
from django.template.loader import render_to_string
from django.utils._os import safe_join

logger = logging.getLogger(__name__)


def safe_render_to_string(template_name, context=None, request=None, using=None):
    with open(template_name, encoding="utf-8") as f:
        template_code = f.read()
        safe_engine = Engine(
            debug=False,
            libraries={},  # 禁用自定义 tag 库
            builtins=[],  # 不自动加载内置标签
        )
        try:
            template = safe_engine.from_string(template_code)
        except TemplateSyntaxError as e:
            logger.error(e)
            return template_code
        return template.render(Context(context or {}))


def _get_data_template_path(template_name: str):
    # 保存到 data/template/<原路径>.html
    # 例如 template_name users/_msg_x.html -> data/template/users/_msg_x.html
    rel_path = template_name.replace('/', os.sep)
    return safe_join(settings.DATA_DIR, 'template', rel_path)


def _get_edit_template_path(template_name: str):
    return _get_data_template_path(template_name) + '.edit'


def custom_render_to_string(template_name, context=None, request=None, using=None):
    # 如果自定的义模板存在，则使用自定义模板，否则使用系统模板
    custom_template = _get_data_template_path(template_name)
    if os.path.exists(custom_template):
        template = safe_render_to_string(custom_template, context=context, request=request, using=using)
    else:
        template = render_to_string(template_name, context=context, request=request, using=using)
    return template
