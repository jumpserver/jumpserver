#!/bin/sh
set -eu

BASE_DIR="$(cd "$(dirname "$0")/../.." && pwd)"

OPENBAO_IMAGE="openbao/openbao:2.6.0"
OPENBAO_NETWORK="${OPENBAO_NETWORK:-jms-openbao-dev}"
OPENBAO_CONTAINER="${OPENBAO_CONTAINER:-jms-openbao}"
OPENBAO_INIT_CONTAINER="${OPENBAO_INIT_CONTAINER:-jms-openbao-init}"
OPENBAO_PORT="${OPENBAO_PORT:-8200}"
OPENBAO_CLUSTER_PORT="${OPENBAO_CLUSTER_PORT:-8201}"
OPENBAO_NETWORK_ALIAS="${OPENBAO_NETWORK_ALIAS:-openbao}"
OPENBAO_RAFT_NODE_ID="${OPENBAO_RAFT_NODE_ID:-openbao}"
OPENBAO_RAFT_API_ADDR="${OPENBAO_RAFT_API_ADDR:-http://${OPENBAO_NETWORK_ALIAS}:8200}"
OPENBAO_RAFT_CLUSTER_ADDR="${OPENBAO_RAFT_CLUSTER_ADDR:-http://${OPENBAO_NETWORK_ALIAS}:8201}"
OPENBAO_RAFT_RETRY_JOIN="${OPENBAO_RAFT_RETRY_JOIN:-}"
OPENBAO_RAFT_BOOTSTRAP="${OPENBAO_RAFT_BOOTSTRAP:-true}"
OPENBAO_UNSEAL_KEY_SHARES="${OPENBAO_UNSEAL_KEY_SHARES:-5}"
OPENBAO_UNSEAL_KEY_THRESHOLD="${OPENBAO_UNSEAL_KEY_THRESHOLD:-3}"
OPENBAO_BOOTSTRAP_ADDR="${OPENBAO_BOOTSTRAP_ADDR:-http://${OPENBAO_NETWORK_ALIAS}:8200}"

VAULT_OPENBAO_TOKEN="${VAULT_OPENBAO_TOKEN:-dev-root}"
VAULT_OPENBAO_MOUNT_POINT="${VAULT_OPENBAO_MOUNT_POINT:-pam}"

RUNTIME_DIR="${OPENBAO_RUNTIME_DIR:-${BASE_DIR}/data/openbao-dev}"
CONFIG_DIR="${RUNTIME_DIR}/config"
DATA_DIR="${RUNTIME_DIR}/data"

write_configs() {
  mkdir -p "${CONFIG_DIR}" "${DATA_DIR}"

  cat >"${CONFIG_DIR}/server.hcl" <<EOF
ui = true
disable_mlock = true

storage "raft" {
  path = "/openbao/data"
  node_id = "${OPENBAO_RAFT_NODE_ID}"
EOF

  old_ifs="${IFS}"
  IFS=","
  for addr in ${OPENBAO_RAFT_RETRY_JOIN}; do
    [ -z "${addr}" ] && continue
    cat >>"${CONFIG_DIR}/server.hcl" <<EOF

  retry_join {
    leader_api_addr = "${addr}"
  }
EOF
  done
  IFS="${old_ifs}"

  cat >>"${CONFIG_DIR}/server.hcl" <<EOF
}

listener "tcp" {
  address = "0.0.0.0:8200"
  cluster_address = "0.0.0.0:8201"
  tls_disable = true
}

api_addr = "${OPENBAO_RAFT_API_ADDR}"
cluster_addr = "${OPENBAO_RAFT_CLUSTER_ADDR}"
EOF

  cat >"${CONFIG_DIR}/bootstrap.sh" <<'EOF'
#!/bin/sh
set -eu

export BAO_ADDR="${BAO_ADDR:-http://openbao:8200}"

MOUNT_POINT="${VAULT_OPENBAO_MOUNT_POINT:-pam}"
SERVICE_TOKEN="${VAULT_OPENBAO_TOKEN:-}"
RAFT_BOOTSTRAP="${OPENBAO_RAFT_BOOTSTRAP:-true}"
UNSEAL_KEY_SHARES="${OPENBAO_UNSEAL_KEY_SHARES:-5}"
UNSEAL_KEY_THRESHOLD="${OPENBAO_UNSEAL_KEY_THRESHOLD:-3}"
INIT_FILE="/openbao/bootstrap/init.json"
SERVICE_TOKEN_FILE="/openbao/bootstrap/jumpserver-token.json"
POLICY_FILE="/tmp/jumpserver-policy.hcl"

wait_openbao() {
  i=0
  while [ "$i" -lt 60 ]; do
    if bao status >/tmp/openbao-status 2>&1; then
      return 0
    fi
    if grep -q "Initialized" /tmp/openbao-status 2>/dev/null; then
      return 0
    fi
    i=$((i + 1))
    sleep 1
  done
  cat /tmp/openbao-status 2>/dev/null || true
  echo "OpenBao is not reachable"
  exit 1
}

json_value() {
  key="$1"
  tr -d '\n ' <"${INIT_FILE}" | sed -n "s/.*\"${key}\":\"\\([^\"]*\\)\".*/\\1/p"
}

json_array_first() {
  key="$1"
  tr -d '\n ' <"${INIT_FILE}" | sed -n "s/.*\"${key}\":\\[\"\\([^\"]*\\)\".*/\\1/p"
}

json_array_values() {
  key="$1"
  tr -d '\n ' <"${INIT_FILE}" | sed -n "s/.*\"${key}\":\\[\\([^]]*\\)\\].*/\\1/p" | tr ',' '\n' | sed 's/^"//;s/"$//'
}

is_true() {
  case "$1" in
    1|true|True|TRUE|yes|Yes|YES) return 0 ;;
    *) return 1 ;;
  esac
}

is_initialized() {
  bao status 2>/dev/null | grep -q "Initialized[[:space:]]*true"
}

is_uninitialized() {
  bao status 2>/dev/null | grep -q "Initialized[[:space:]]*false"
}

is_sealed() {
  bao status 2>/dev/null | grep -q "Sealed[[:space:]]*true"
}

wait_unsealed() {
  i=0
  while [ "$i" -lt 30 ]; do
    if ! is_sealed; then
      return 0
    fi
    i=$((i + 1))
    sleep 1
  done
  return 1
}

unseal_openbao() {
  if ! is_sealed; then
    return 0
  fi

  json_array_values unseal_keys_b64 | while IFS= read -r key; do
    [ -z "${key}" ] && continue
    if ! is_sealed; then
      break
    fi
    bao operator unseal "${key}" >/dev/null
  done

  if ! wait_unsealed; then
    echo "OpenBao is still sealed after applying unseal keys from ${INIT_FILE}."
    exit 1
  fi
}

wait_openbao

if is_uninitialized; then
  if is_true "${RAFT_BOOTSTRAP}"; then
    bao operator init -key-shares="${UNSEAL_KEY_SHARES}" -key-threshold="${UNSEAL_KEY_THRESHOLD}" -format=json >"${INIT_FILE}"
    chmod 600 "${INIT_FILE}" 2>/dev/null || true
  else
    i=0
    while [ "$i" -lt 60 ]; do
      is_initialized && break
      i=$((i + 1))
      sleep 1
    done
    if is_uninitialized; then
      echo "OpenBao is not initialized. Set OPENBAO_RAFT_BOOTSTRAP=true on the first Raft node, or wait for retry_join to finish."
      exit 1
    fi
  fi
fi

if [ ! -f "${INIT_FILE}" ]; then
  echo "OpenBao is initialized, but ${INIT_FILE} is missing; cannot unseal automatically."
  exit 1
fi

UNSEAL_KEY="$(json_array_first unseal_keys_b64)"
ROOT_TOKEN="$(json_value root_token)"

if [ -z "${UNSEAL_KEY}" ] || [ -z "${ROOT_TOKEN}" ]; then
  echo "OpenBao init file is invalid: ${INIT_FILE}"
  exit 1
fi

unseal_openbao

export BAO_TOKEN="${ROOT_TOKEN}"

if ! bao secrets list -format=json | grep -q "\"${MOUNT_POINT}/\""; then
  bao secrets enable -path="${MOUNT_POINT}" -version=2 kv
fi

bao write "${MOUNT_POINT}/config" max_versions=20 >/dev/null

cat >"${POLICY_FILE}" <<POLICY
path "+/data/*" {
  capabilities = ["create", "read", "update", "patch"]
}

path "+/metadata/*" {
  capabilities = ["create", "update", "delete"]
}
POLICY

bao policy write jumpserver "${POLICY_FILE}" >/dev/null

if [ -n "${SERVICE_TOKEN}" ]; then
  if ! bao token lookup "${SERVICE_TOKEN}" >/dev/null 2>&1; then
    bao token create \
      -id="${SERVICE_TOKEN}" \
      -policy=jumpserver \
      -orphan \
      -no-default-policy \
      -format=json >"${SERVICE_TOKEN_FILE}"
    chmod 600 "${SERVICE_TOKEN_FILE}" 2>/dev/null || true
  fi
fi
EOF

  chmod +x "${CONFIG_DIR}/bootstrap.sh"
}

start_containers() {
  docker network create "${OPENBAO_NETWORK}" >/dev/null 2>&1 || true
  docker rm -f \
    "${OPENBAO_INIT_CONTAINER}" \
    "${OPENBAO_CONTAINER}" >/dev/null 2>&1 || true

  docker run -d \
    --name "${OPENBAO_CONTAINER}" \
    --network "${OPENBAO_NETWORK}" \
    --network-alias "${OPENBAO_NETWORK_ALIAS}" \
    -p "${OPENBAO_PORT}:8200" \
    -p "${OPENBAO_CLUSTER_PORT}:8201" \
    -e VAULT_API_ADDR="${OPENBAO_RAFT_API_ADDR}" \
    -e VAULT_CLUSTER_ADDR="${OPENBAO_RAFT_CLUSTER_ADDR}" \
    -e VAULT_RAFT_NODE_ID="${OPENBAO_RAFT_NODE_ID}" \
    -v "${DATA_DIR}:/openbao/data" \
    -v "${CONFIG_DIR}/server.hcl:/openbao/config/server.hcl:ro" \
    -v "${CONFIG_DIR}:/openbao/bootstrap:ro" \
    "${OPENBAO_IMAGE}" \
    server -config=/openbao/config/server.hcl >/dev/null

  docker run --rm \
    --name "${OPENBAO_INIT_CONTAINER}" \
    --network "${OPENBAO_NETWORK}" \
    -e BAO_ADDR="${OPENBAO_BOOTSTRAP_ADDR}" \
    -e VAULT_OPENBAO_TOKEN="${VAULT_OPENBAO_TOKEN}" \
    -e VAULT_OPENBAO_MOUNT_POINT="${VAULT_OPENBAO_MOUNT_POINT}" \
    -e OPENBAO_RAFT_BOOTSTRAP="${OPENBAO_RAFT_BOOTSTRAP}" \
    -e OPENBAO_UNSEAL_KEY_SHARES="${OPENBAO_UNSEAL_KEY_SHARES}" \
    -e OPENBAO_UNSEAL_KEY_THRESHOLD="${OPENBAO_UNSEAL_KEY_THRESHOLD}" \
    -v "${CONFIG_DIR}:/openbao/bootstrap" \
    "${OPENBAO_IMAGE}" \
    sh /openbao/bootstrap/bootstrap.sh
}

print_result() {
  cat <<EOF
OpenBao local dev is ready.

Server: http://127.0.0.1:${OPENBAO_PORT}
Cluster: http://127.0.0.1:${OPENBAO_CLUSTER_PORT}
Peer:   ${OPENBAO_RAFT_API_ADDR}
Data:   ${DATA_DIR}
Init:   ${CONFIG_DIR}/init.json
Unseal: ${OPENBAO_UNSEAL_KEY_SHARES} shares, ${OPENBAO_UNSEAL_KEY_THRESHOLD} threshold

JumpServer config.yml:
VAULT_ENABLED: True
VAULT_BACKEND: openbao
VAULT_OPENBAO_ADDR: http://127.0.0.1:${OPENBAO_PORT}
VAULT_OPENBAO_TOKEN: ${VAULT_OPENBAO_TOKEN}
VAULT_OPENBAO_MOUNT_POINT: ${VAULT_OPENBAO_MOUNT_POINT}
VAULT_OPENBAO_TIMEOUT: 10
EOF
}

main() {
  write_configs
  start_containers
  print_result
}

main "$@"