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

New applications and account-scope updates can authorize up to 10 explicit accounts. Existing all-account or dynamic scopes are not silently truncated; administrators must review and narrow them. After a new scope is saved, the Agent revokes push account keys outside that scope on its next synchronization.

Update notifications and initial/reconnect snapshots trigger signed reconciliation and live credential retrieval. The Agent retains the latest successful credential without expiry, renders and atomically replaces files, executes configured actions, then records delivered revisions. Failed retrieval or delivery retries with 1–30 second backoff; periodic reconciliation defaults to 300 seconds. Retained credentials survive outages and process restarts. Explicit revocation reduces persisted authorization before HTTP synchronization.

Default delivery writes one JSON file per credential. Local `rules` can select credential keys, JSON or EnvironmentFile targets, trusted `template_file` rendering, and a bounded systemd reload/restart or fixed executable. Templates receive `.Credentials` and provide a `json` helper. Rendered files are 0600 and belong to the configured application user or explicit file owner. Every changed key must be covered when explicit rules are configured.

Scripts receive `{"event":"credentials.updated","credentials":{...}}` as JSON on stdin, with fixed arguments and no secrets in arguments or environment. stdout/stderr are discarded. Scripts must validate and apply configuration, check application health, then return success; they must be idempotent for retries. Default timeout is 120 seconds, maximum 300 seconds. On Unix, cancellation terminates the process group; Windows supports trusted `.exe` actions and terminates the direct process on timeout. Script and template paths and writable targets require trusted ownership, protected parent directories and no symlinks. Core cannot introduce scripts, arguments, files or expanded local capabilities.

A successful file write, script or service action does not automatically confirm business application. After validating and switching the real connection, the application explicitly confirms the exact alternating-rotation revision using the protected Unix socket (`/v1/confirm` or `jms-pam-agent confirm KEY --revision N --socket PATH`). Confirmations persist before reporting and retry if Core is unavailable. Subscription credentials require no confirmation.

After editing local configuration, run `sudo jms-pam-agent check-config` and restart the fixed service. A systemd reload does not inject updated environment variables into a running process; services that read only their startup environment need restart. Completed systemd actions are followed by an active-state check. Real application connection switching still requires application validation.

The Go Agent uses its own state format. Existing Python services and state are not automatically deleted. When migrating an installed host, stop its old Agent and complete the first online synchronization before handing over the same delivery paths.

When upgrading from policy-prefixed subscription keys, the first successful online synchronization fetches the account key and removes old subscription entries from Agent state. With default delivery and no custom rules, it also removes old default files in the current delivery root. Update local `rules.keys` and any template references from `<policy-key>:<account-id>` to `account:<account-id>` before restarting an Agent that uses custom rules. Review custom file destinations and any previous delivery root separately.

See the [complete configuration, template and script examples](README.zh-hans.md). Local tests cover updates, retained-state recovery, revocation, templates, scripts, failure paths, confirmation and socket lifecycle. Linux systemd installation and real service actions need target-host validation.

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

Agent identity uses app_id, app_secret, org_id and a stable instance_id. Authorization follows application policy bindings. All file paths and service actions are local: state_file retains the latest passwords, event_file appends metadata without secrets, delivery selects default output, and rules configure files, templates and reload/restart or fixed scripts. On an update notification the Agent fetches the current password, persists it, atomically replaces output files, then runs the configured action. Failed delivery is retried. Use credentials[].key from get_accounts in rules; subscription keys include the account ID. Empty rules write one file per key by default.

```json
{
  "endpoint": "https://jumpserver.example.com",
  "app_id": "<application-id>",
  "app_secret": "<application-secret>",
  "org_id": "<org-id>",
  "instance_id": "orders-node-1",
  "state_file": "/var/lib/jms-pam-agent/state.json",
  "event_file": "/var/lib/jms-pam-agent/events.jsonl",
  "reconcile_interval": 300,
  "delivery": {
    "delivery_mode": "json",
    "delivery_root": "/opt/jumpserver-pam/credentials",
    "socket_path": "/run/jms-pam-agent/agent.sock",
    "app_user": "orders",
    "systemd_unit": "",
    "systemd_action": ""
  },
  "rules": []
}
```

Replace `rules` with this template/reload rule when the service needs its own configuration:

```json
[
  {
    "keys": [
      "<credential-key>"
    ],
    "files": [
      {
        "path": "/etc/order-service/database.json",
        "format": "template",
        "template_file": "/etc/jms-pam-agent/orders-db.tmpl",
        "owner": "orders"
      }
    ],
    "action": {
      "type": "systemd",
      "unit": "order-service.service",
      "operation": "reload",
      "timeout_seconds": 30
    }
  }
]
```

Template `/etc/jms-pam-agent/orders-db.tmpl`:

```gotemplate
{"username": {{json (index .Credentials "<credential-key>").Username}}, "password": {{json (index .Credentials "<credential-key>").Secret}}}
```

Use `operation: "restart"` for services that read startup environment only. For complex deployments, replace `action` with `{"type":"script","path":"/usr/local/libexec/jms-pam/apply-orders","args":["--config","/etc/order-service/database.json"],"timeout_seconds":60}`. Scripts receive current credentials on stdin and must be idempotent.
