#!/bin/bash

CURRENT_DIR=$(cd "$(dirname "$0")" && pwd)
BASE_DIR=$(dirname "$CURRENT_DIR")

VERSION=v0.0.1
to_files="
  apps/common/utils/ip/geoip/GeoLite2-City.mmdb
  apps/common/utils/ip/ipip/ipipfree.ipdb
  apps/accounts/automations/check_account/leak_passwords.db
"

for file in $to_files; do
  # Check if the file already exists
  file_path="${BASE_DIR}/$file"
  rm -f $file_path
  if [ -f "$file_path" ]; then
    echo "File $file already exists, skipping download."
    continue
  fi

  filename=$(basename "$file")
  to_dir=$(dirname "$file_path")
  if [ ! -d "$to_dir" ]; then
    mkdir -p "$to_dir"
  fi
  url=""https://github.com/jumpserver/static/releases/download/${VERSION}/$filename""
  echo "Download $filename to $file_path"
  wget "$url" -O "${file_path}"
done

