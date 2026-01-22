import os
import sys
import django

# 获取项目根目录（jumpserver 目录）
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
APP_DIR = os.path.join(BASE_DIR, 'apps')


# 不改变工作目录，直接加入 sys.path
sys.path.insert(0, APP_DIR)
sys.path.insert(0, BASE_DIR)

# 设置 Django 环境
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "jumpserver.settings")
django.setup()


from routing.discover import discover_routes
from routing.resolver import resolve_view
from extractors.selector import select_extractor
from schema.renderer import render_schema


def generate_api_schema():
    # 发现所有路由
    routes = discover_routes()
    endpoints = []

    for route in routes:
        # 解析视图
        view = resolve_view(route)
        # 选择视图提取器
        extractor = select_extractor(view)
        # 提取端点信息
        endpoint = extractor.extract()
        if not endpoint:
            continue
        endpoints.append(endpoint)
    
    # 渲染最终的 API Schema
    schema = render_schema(endpoints)
    return schema


if __name__ == '__main__':
    api_schema = generate_api_schema()
    print(api_schema)