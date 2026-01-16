import json
from pathlib import Path

from django.conf import settings
from django.templatetags.static import static

DEFAULT_VENDOR = "jumpserver"
DEFAULT_LOGIN_TEMPLATE = "authentication/login.html"
DEFAULT_THEME = "classic_green"


def is_default_vendor() -> bool:
    return settings.VENDOR == DEFAULT_VENDOR


def find_theme_path(theme_dirs, theme_name: str) -> Path:
    filename = f"{theme_name}.json"
    for d in theme_dirs:
        p = d / filename
        if p.is_file():
            return p
    raise FileNotFoundError(f"Theme file not found: {filename} in {theme_dirs}")


def _default_theme_dir() -> Path:
    data_dir = Path(settings.BASE_DIR)
    return data_dir / "xpack" / "plugins" / "interface" / "themes"


def _vendor_media_dir() -> Path:
    data_dir = Path(settings.DATA_DIR)
    return data_dir / "media" / settings.VENDOR


def _build_theme() -> str:
    return DEFAULT_THEME if is_default_vendor() else settings.VENDOR


def _build_theme_info() -> dict:
    if is_default_vendor():
        theme_path = find_theme_path([_default_theme_dir()], DEFAULT_THEME)
    else:
        theme_path = find_theme_path([_vendor_media_dir() / 'themes'], settings.VENDOR)
    return json.loads(theme_path.read_text(encoding="utf-8"))


def _build_vendor_info() -> dict:
    if is_default_vendor():
        return {}
    info_path = _vendor_media_dir() / "info.json"
    if not info_path.exists():
        return {}
    return json.loads(info_path.read_text(encoding="utf-8"))


def _build_vendor_info_value(key: str, default=None):
    info = _build_vendor_info()
    return info.get(key, default)


def _build_asset(filename: str) -> str:
    if is_default_vendor():
        return static(filename)

    media_path = _vendor_media_dir() / filename
    if media_path.exists():
        media_url = settings.MEDIA_URL.rstrip("/")
        return f"{media_url}/{settings.VENDOR}/{filename}"
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
