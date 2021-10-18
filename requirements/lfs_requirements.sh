#!/bin/bash
#
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
PROJECT_DIR=$(dirname "$BASE_DIR")


echo "下载 IP 数据库"
ip_db_path="${PROJECT_DIR}/apps/common/utils/geoip/GeoLite2-City.mmdb"
wget "https://download.jumpserver.org/files/GeoLite2-City.mmdb" -O "${ip_db_path}"
