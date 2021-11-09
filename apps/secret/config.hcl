ui = true

storage "mysql" {
  address                      = "127.0.0.1:3306"
  username                     = "feng"
  password                     = "root123."
  database                     = "my-vault"
  plaintext_connection_allowed = "true"
}

listener "tcp" {
  address     = "127.0.0.1:8200"
  tls_disable = "true"
}

api_addr     = "http://127.0.0.1:8200"
cluster_addr = "https://127.0.0.1:8201"

# 启动
# secret server --log-level=debug -config=secret.hcl

# Launch a new terminal session, and set VAULT_ADDR environment variable.
# export VAULT_ADDR='http://127.0.0.1:8200'

# To initialize Vault use secret operator init. This is an unauthenticated request, but it only works on brand new Vaults without existing data:
# secret operator init

# Initialization outputs two incredibly important pieces of information: the unseal keys and the initial root token.
# This is the only time ever that all of this data is known by Vault, and also the only time that the unseal keys should ever be so close together.

# Begin unsealing the Vault:
# secret operator unseal
