import json
from pathlib import Path

from django.conf import settings
from django.contrib.staticfiles import finders
from django.templatetags.static import static

DEFAULT_VENDOR = "jumpserver"
DEFAULT_LOGIN_TEMPLATE = "authentication/login.html"
DEFAULT_THEME = "classic_green"

VENDOR_THEMES_DIR = settings.VENDOR_TEMPLATES_DIR / "themes"


def is_default_vendor() -> bool:
    return settings.VENDOR == DEFAULT_VENDOR


def find_theme_path(theme_dirs, theme_name: str) -> Path | None:
    filename = f"{theme_name}.json"
    for d in theme_dirs:
        p = d / filename
        if p.is_file():
            return p


def _default_theme_dir() -> Path:
    data_dir = Path(settings.BASE_DIR)
    return data_dir / "xpack" / "plugins" / "interface" / "themes"


def _build_theme() -> str:
    return DEFAULT_THEME if is_default_vendor() else settings.VENDOR


def _build_theme_info() -> dict:
    default_theme_path = find_theme_path([_default_theme_dir()], DEFAULT_THEME)

    search_dirs = [_default_theme_dir()] if is_default_vendor() else [
        settings.VENDOR_TEMPLATES_DIR / 'themes',
        _default_theme_dir(),
    ]
    theme_name = DEFAULT_THEME if is_default_vendor() else settings.VENDOR

    theme_path = find_theme_path(search_dirs, theme_name) or default_theme_path
    return json.loads(theme_path.read_text(encoding="utf-8"))


def _build_vendor_info() -> dict:
    if is_default_vendor():
        return {}
    info_path = settings.VENDOR_TEMPLATES_DIR / "info.json"
    if not info_path.exists():
        return {}
    return json.loads(info_path.read_text(encoding="utf-8"))


def _build_vendor_info_value(key: str, default=None):
    info = _build_vendor_info()
    return info.get(key, default)


def _build_asset(filename: str) -> str:
    if is_default_vendor():
        return static(filename)

    vendor_path = f"{settings.VENDOR}/{filename}"
    if finders.find(vendor_path):
        return static(vendor_path)
    return static(filename)


VENDOR_BUILDERS = {
    "theme": _build_theme,
    "theme_info": _build_theme_info,
    "logo_logout": lambda: _build_asset("img/logo.png"),
    "logo_index": lambda: _build_asset("img/logo_text_white.png"),
    "login_image": lambda: _build_asset("img/login_image.png"),
    "favicon": lambda: _build_asset("img/facio.ico"),
    "logo_white": lambda: _build_asset("img/logo_white.png"),
    "logo_text_white": lambda: _build_asset("img/logo_text_white.png"),
    "login_title": lambda: _build_vendor_info_value("login_title"),
    "footer_content": lambda: _build_vendor_info_value("footer_content"),
}


def get_vendor_value(kind: str, default=None):
    builder = VENDOR_BUILDERS.get(kind)
    if not builder:
        return default
    value = builder()
    return default if value is None else value
