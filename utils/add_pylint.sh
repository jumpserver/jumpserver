#!/bin/bash
#
utils_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
project_dir=$(dirname "${utils_dir}")

pip install git-pylint-commit-hook==2.5.1
pre_check_file="${project_dir}/.git/hooks/pre-commit"

if [[ ! -f "${pre_check_file}" ]];then
    cat > "$pre_check_file" << EOF
#/bin/bash
git-pylint-commit-hook --limit=8.0
EOF

  chmod +x "${pre_check_file}"
fi

