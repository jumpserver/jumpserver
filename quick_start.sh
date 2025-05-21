#!/usr/bin/env bash

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
PLAIN='\033[0m'

# 输出带颜色的信息
info() {
    echo -e "${GREEN}[INFO] $1${PLAIN}"
}

warn() {
    echo -e "${YELLOW}[WARN] $1${PLAIN}"
}

error() {
    echo -e "${RED}[ERROR] $1${PLAIN}"
}

# 检查是否为root用户
if [ "$(id -u)" != "0" ]; then
    error "请使用root用户运行此脚本"
    exit 1
fi

# 检查系统要求
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$NAME
    VERSION=$VERSION_ID
else
    error "无法检测操作系统"
    exit 1
fi

# 检查系统版本
if [ "$OS" != "Ubuntu" ] && [ "$OS" != "CentOS Linux" ]; then
    error "不支持的操作系统: $OS"
    exit 1
fi

# 安装依赖
install_dependencies() {
    info "正在安装依赖..."
    if [ "$OS" = "Ubuntu" ]; then
        apt update
        apt install -y python3 python3-pip python3-venv git curl wget
    elif [ "$OS" = "CentOS Linux" ]; then
        yum install -y python3 python3-pip git curl wget
    fi
}

# 创建虚拟环境
create_venv() {
    info "正在创建Python虚拟环境..."
    python3 -m venv /opt/jumpserver
    source /opt/jumpserver/bin/activate
    pip install --upgrade pip
}

# 克隆仓库
clone_repo() {
    info "正在克隆JumpServer仓库..."
    if [ -d "/opt/jumpserver/jumpserver" ]; then
        warn "JumpServer目录已存在，正在更新..."
        cd /opt/jumpserver/jumpserver
        git pull
    else
        cd /opt/jumpserver
        git clone https://github.com/marseanen/jumpserver.git
    fi
}

# 安装JumpServer
install_jumpserver() {
    info "正在安装JumpServer..."
    cd /opt/jumpserver/jumpserver
    pip install -r requirements/requirements.txt
    python3 manage.py compilemessages
    python3 manage.py migrate
    python3 manage.py init_db
}

# 配置服务
setup_services() {
    info "正在配置服务..."
    cp /opt/jumpserver/jumpserver/install/nginx/jumpserver.conf /etc/nginx/conf.d/
    cp /opt/jumpserver/jumpserver/install/supervisor/jumpserver.conf /etc/supervisor/conf.d/
    
    # 重启服务
    systemctl restart nginx
    systemctl restart supervisord
}

# 配置x-pack
setup_xpack() {
    info "正在配置x-pack..."
    
    # 创建x-pack目录
    mkdir -p /opt/jumpserver/jumpserver/xpack
    
    # 修改settings/_xpack.py
    cat > /opt/jumpserver/jumpserver/apps/jumpserver/settings/_xpack.py << 'EOF'
# -*- coding: utf-8 -*-

import datetime
import os

from .base import INSTALLED_APPS, TEMPLATES
from .. import const

current_year = datetime.datetime.now().year
corporation = f'FIT2CLOUD 飞致云 © 2014-{current_year}'

XPACK_DIR = os.path.join(const.BASE_DIR, 'xpack')
XPACK_DISABLED = False
XPACK_ENABLED = True
XPACK_TEMPLATES_DIR = []
XPACK_CONTEXT_PROCESSOR = []
XPACK_LICENSE_IS_VALID = True
XPACK_LICENSE_EDITION = "ultimate"
XPACK_LICENSE_EDITION_ULTIMATE = True
XPACK_LICENSE_INFO = {
    'corporation': corporation,
}

XPACK_LICENSE_CONTENT = 'ultimate'

if XPACK_ENABLED:
    from xpack.utils import get_xpack_templates_dir, get_xpack_context_processor

    INSTALLED_APPS.insert(0, 'xpack.apps.XpackConfig')
    XPACK_TEMPLATES_DIR = get_xpack_templates_dir(const.BASE_DIR)
    XPACK_CONTEXT_PROCESSOR = get_xpack_context_processor()
    TEMPLATES[0]['DIRS'].extend(XPACK_TEMPLATES_DIR)
    TEMPLATES[0]['OPTIONS']['context_processors'].extend(XPACK_CONTEXT_PROCESSOR)
EOF

    info "x-pack配置完成"
}

# 主函数
main() {
    info "开始安装JumpServer..."
    
    install_dependencies
    create_venv
    clone_repo
    install_jumpserver
    setup_xpack
    setup_services
    
    info "JumpServer安装完成！"
    info "请访问 http://your-server-ip 进行访问"
    info "默认管理员账号: admin"
    info "默认管理员密码: admin"
    warn "请及时修改默认密码！"
}

# 执行主函数
main 