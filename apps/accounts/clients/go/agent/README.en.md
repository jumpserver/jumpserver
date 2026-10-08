# Go jms-pam-agent

The standalone Agent is implemented in Go and requires no Python runtime. The built-in systemd installer requires Linux and root; foreground runs use the current user on Linux, macOS and Windows. The Linux service stores private configuration in `/etc/jms-pam-agent/agent.json` and retained state in `/var/lib/jms-pam-agent/state.json` (0600). A subscription credential uses `account:<account-id>` as its key, independent of the policy that selected the account. Multiple matching push policies deliver one account credential. Rotation keeps its policy key. Local `rules.files.path` can give business files stable, readable names.

```bash
CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -o jms-pam-agent ./cmd/jms-pam-agent
sudo install -m 0755 ./jms-pam-agent /usr/local/bin/jms-pam-agent
chmod 0600 ./jms_pam_agent.json
sudo jms-pam-agent install --bootstrap ./jms_pam_agent.json --instance-id orders-node-1
sudo systemctl start jms-pam-agent
sudo systemctl restart jms-pam-agent
sudo journalctl -u jms-pam-agent
```

Run the build from the Go SDK directory; use GOARCH=arm64 for ARM64 targets. The fixed service is `jms-pam-agent.service`. Application AK/SK and a stable `instance_id` identify the Agent. Application account authorization defines on-demand pull access; bound credential policies define proactive sync and push.

New applications and account-scope updates may select specific accounts, all accounts, or accounts by attribute. The matched scope must stay within the system-wide application account limit (default 10), configured with `APPLICATION_ACCOUNT_SCOPE_LIMIT` in Core's `config.yml`. Restart Core after changing it. Existing scopes retain their current retrieval access until their account authorization is changed. If a newly limited dynamic scope later grows past the limit, account listing and credential retrieval fail until the scope is narrowed or the limit is raised; the server never silently selects the first 10 accounts. After a new scope is saved, the Agent revokes push account keys outside that scope on its next synchronization.

Update notifications and initial/reconnect snapshots trigger signed reconciliation and live credential retrieval. The Agent retains the latest successful credential without expiry, renders and atomically replaces files, executes configured actions, then records delivered revisions. Failed retrieval or delivery retries with 1–30 second backoff; periodic reconciliation defaults to 300 seconds. Retained credentials survive outages and process restarts. Explicit revocation reduces persisted authorization before HTTP synchronization.

Default delivery writes one JSON file per credential. For a business application, edit only the local `rules`: select the account IDs it uses, update its configuration, activate the change, and verify the running connection. Paths, scripts and service actions are fixed locally; Core cannot add them through events. Generated state, event and socket paths and the reconciliation interval have defaults.

A rule can select `"accounts":[{"account_id":"<account-A-id>","allow_account_switch":true}]` and map fields with `"config_update":{"file":"/path/config.txt","fields_map":{"DB_USER":"username","DB_PASSWORD":"secret"}}`. For an A/B rotation, the same rule applies in either direction, including a first sync that starts on B. The declared fields receive the active account's username and secret. Use a second rule with its own account and field mapping when one business file uses two accounts. Rules sharing a file must map distinct fields with the same format and owner.

The execution order is optional `credential_check`, backup of existing business configuration targets, `config_update`, `service_action`, then `application_check`. Backups are stored privately under `backups/` next to `state_file`, grouped by target path and named with a UTC timestamp. The Agent keeps at most 10 per target, skips identical consecutive contents, and stops delivery if backup fails. Targets larger than 32 MiB need their own backup handling. Restoring a backup and reloading the application are explicit operator actions. `config_update.file` edits declared top-level fields in an existing flat `.txt`, `.env`, `.yml` or `.yaml` file, preserving unrelated settings, permissions and ownership. Every mapped field must already exist exactly once. Use `files` with `template_file` to render a complete file, or `script` for complex formats. A fixed script receives `{"event":"credentials.updated","credentials":{...}}` on stdin. It has no implicit arguments; `args` supplies fixed ones. Script updates declare their destination with `target` or `targets`; neither is passed automatically. Actions infer script from `path` and systemd from `unit`, so `type` can be omitted.

The `application_check` must prove the running business uses the new database account, rather than just checking process liveness. Set `confirm_on_success` to confirm the exact alternating-rotation revision after this check. A failed step leaves delivery pending for retry; the Agent does not automatically roll business files back after an activation or check failure. JumpServer installer `config.txt` needs recreation of the readers, including Core and Celery containers. Direct `config.yml` deployment needs restart of its actual readers. The installer format cannot represent passwords containing quotes; such credentials require a custom updater. Old-account password changes must wait until JumpServer credential retrieval records show no old-account traffic after switching.

Scripts must be idempotent, use protected paths, and keep secrets out of arguments, environment variables and logs. The default action timeout is 120 seconds, with a maximum of 300 seconds. To apply changed local rules, run `sudo jms-pam-agent check-config` and restart the fixed service. An active systemd service alone does not prove the business database connection changed.

See the [complete configuration and script contract](README.zh-hans.md). Local tests cover updates, retained-state recovery, revocation, templates, scripts, failure paths, confirmation and socket lifecycle. Linux systemd installation and real service actions need target-host validation.

## CLI and local foreground development

```bash
jms-pam-agent get_accounts --config /path/to/agent.json
jms-pam-agent get_secret ACCOUNT_ID --config /path/to/agent.json
# Alternatively use --socket PATH; get-secret is supported, and get_credential / get-credential remain aliases.
```

Queries use the running Agent's protected socket. Account listing returns metadata for the application's pull scope without fetching passwords; pull-only accounts have an empty `credentials` list. Policy entries identify the proactive push scope, with rotation marking only its current account. Credential queries use the account ID to check live application authorization and fetch on demand, without requiring a push policy. Pull-only passwords are not persisted and cannot be used offline; only still-authorized pushed credentials can be used for network failures, timeouts or HTTP 5xx. The account list API supports `limit`, `offset` and `search`. JSON output reports `source: api` or `source: local`. Credential queries intentionally print the password to stdout and never confirm business application.

`--config` accepts paths relative to the current working directory; private permissions and symlink checks still apply. Paths inside the configuration remain absolute. CLI diagnostics explain local validation failures or report HTTP status without logging backend response bodies.

For macOS/Linux foreground use, build the native binary, protect the downloaded bootstrap JSON with mode 0600, then run:

```bash
./jms-pam-agent init-local --bootstrap /private/path/jms_pam_agent.json \
  --directory "$HOME/.jms-pam-agent/orders" --instance-id local-orders-agent
./jms-pam-agent run --local --config "$HOME/.jms-pam-agent/orders/agent.json"
```

For Windows, build `jms-pam-agent.exe` with `GOOS=windows GOARCH=amd64 go build -o jms-pam-agent.exe ./cmd/jms-pam-agent`, then run in PowerShell from the directory containing the downloaded bootstrap:

```powershell
$agentDir = Join-Path $HOME 'jms-pam\orders'
.\jms-pam-agent.exe init-local --bootstrap (Join-Path $PWD 'jms_pam_agent.json') --directory $agentDir --instance-id $env:COMPUTERNAME
.\jms-pam-agent.exe run --local --config (Join-Path $agentDir 'agent.json')
```

Windows requires AF_UNIX stream socket support.

Initialize once and reuse `agent.json` for later starts. The bootstrap and all Windows credential paths must stay under the current user's home with a private ACL; the Agent rejects links and reparse points. Use a short directory so the local Unix socket path stays below 108 bytes. Windows default credential filenames use a SHA-256 hash of the key because `account:<id>` is not a valid Windows filename; the JSON content still includes the key. Foreground mode uses current-user paths and JSON or Socket delivery; it cannot execute systemd actions or EnvironmentFile delivery. Signed scope and execution capability checks remain enforced. The directory contains private `agent.json`, append-only metadata `events.jsonl`, retained `state.json`, a protected `run/agent.sock`, and default JSON credentials. Records distinguish received, saved and delivered phases, contain no secrets and provide no exactly-once/history replay guarantee. The Linux service remains `systemctl start jms-pam-agent`.

## Local configuration and update flow

The downloaded bootstrap is already a complete configuration. Keep its identity and delivery fields, then add a rule such as:

```json
{
  "accounts": [{"account_id": "<primary-account-id>", "allow_account_switch": true}],
  "config_update": {
    "file": "/opt/jumpserver/config/config.txt",
    "fields_map": {"DB_USER": "username", "DB_PASSWORD": "secret"}
  },
  "service_action": {"path": "/usr/local/libexec/jms-pam/recreate-jumpserver"},
  "application_check": {
    "path": "/usr/local/libexec/jms-pam/check-running-db",
    "confirm_on_success": true
  }
}
```

Put this object inside `rules`. The Agent edits only `DB_USER` and `DB_PASSWORD` and preserves other settings. The activation script makes the actual processes reread them. The final check must perform a real database operation through the running application. To precheck the new credential, add `"credential_check":{"path":"/usr/local/libexec/jms-pam/check-db-login"}`. For a systemd service use `"service_action":{"unit":"order-service.service"}`, which defaults to restart; set `operation` to `reload` only when the service rereads its configuration. A complete generated file can use `"config_update":{"files":[{"path":"/etc/order-service/database.json","template_file":"/etc/jms-pam-agent/orders-db.tmpl"}]}`.

For a test file that already contains `VERSION`, add `"VERSION":"revision"` to `fields_map` to keep the delivered policy revision visible. This is the credential delivery revision, not an account password history version.

To update two accounts in one file, write two rules, each with one account and its own flat `config_update.fields_map`. Their mapped fields must not overlap. The Agent applies all file updates before service actions and application checks. For a custom update script, stdin `credentials` is keyed by the configured account ID even when the active account changes. Check the [Chinese Agent guide](README.zh-hans.md) for full `config.txt` and `config.yml` behavior and the script input example.
