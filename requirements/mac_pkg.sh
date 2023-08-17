#!/bin/bash
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
PROJECT_DIR=$(dirname "$BASE_DIR")

echo "1. 安装依赖"
brew install libtiff libjpeg webp little-cms2 openssl gettext git \
   git-lfs libxml2 libxmlsec1 pkg-config postgresql freetds openssl \
   libffi freerdp
pip install daphne==4.0.0 channels channels-redis

echo "2. 下载 IP 数据库"
ip_db_path="${PROJECT_DIR}/apps/common/utils/geoip/GeoLite2-City.mmdb"
wget "https://download.jumpserver.org/files/GeoLite2-City.mmdb" -O "${ip_db_path}"

echo "3. 安装依赖的插件"
git lfs install

if ! uname -a | grep 'ARM64' &> /dev/null;then
  exit 0
fi

echo "4. For Apple processor"
LDFLAGS="-L$(brew --prefix freetds)/lib -L$(brew --prefix openssl@1.1)/lib"  CFLAGS="-I$(brew --prefix freetds)/include"  pip install $(grep 'pymssql' requirements.txt)
