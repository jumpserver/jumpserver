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



from .view_schema_generator import ViewSchemaGenerator
from .const import OUTPUT_FILE_DIR


if __name__ == '__main__':
    ViewSchemaGenerator(output_file_dir=OUTPUT_FILE_DIR).generate()