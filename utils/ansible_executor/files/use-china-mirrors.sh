#!/bin/bash
# Switch CentOS Stream / EPEL repos to Aliyun mirrors (for builds in China).
set -euo pipefail

mirror_centos() {
  for f in /etc/yum.repos.d/centos*.repo; do
    [ -f "$f" ] || continue
    sed -i \
      -e 's|^mirrorlist=|#mirrorlist=|g' \
      -e 's|^#baseurl=http://mirror.centos.org|baseurl=https://mirrors.aliyun.com|g' \
      -e 's|^#baseurl=https://mirror.centos.org|baseurl=https://mirrors.aliyun.com|g' \
      "$f"
  done
}

mirror_epel() {
  # epel-release 默认只有 metalink，sed 改 baseurl 会失效；直接覆盖为阿里云固定地址
  cat > /etc/yum.repos.d/epel.repo <<'EOF'
[epel]
name=Extra Packages for Enterprise Linux 9 - $basearch
baseurl=https://mirrors.aliyun.com/epel/9/Everything/$basearch
enabled=1
gpgcheck=1
countme=0
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-EPEL-9

[epel-debuginfo]
name=Extra Packages for Enterprise Linux 9 - $basearch - Debug
baseurl=https://mirrors.aliyun.com/epel/9/Everything/$basearch/debug
enabled=0
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-EPEL-9

[epel-source]
name=Extra Packages for Enterprise Linux 9 - $basearch - Source
baseurl=https://mirrors.aliyun.com/epel/9/Everything/source/tree
enabled=0
gpgcheck=1
gpgkey=file:///etc/pki/rpm-gpg/RPM-GPG-KEY-EPEL-9
EOF

  # epel-next 在阿里云 aarch64 上常 404，且 freetds-devel/sshpass 在 epel 主仓库即可
  rm -f /etc/yum.repos.d/epel-next.repo

  # 禁用可能仍指向官方源的其他 epel 附属 repo
  for f in /etc/yum.repos.d/epel*.repo; do
    case "$(basename "$f")" in
      epel.repo) ;;
      *)
        sed -i 's/^enabled=1/enabled=0/g' "$f" || true
        ;;
    esac
  done
}

case "${1:-all}" in
  centos) mirror_centos ;;
  epel) mirror_epel ;;
  all)
    mirror_centos
    mirror_epel
    ;;
  *)
    echo "usage: $0 [centos|epel|all]" >&2
    exit 2
    ;;
esac
