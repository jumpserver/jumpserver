"""Build translated client guides; protocol names and examples stay identical."""

import argparse
import json
from pathlib import Path

CLIENTS = Path(__file__).resolve().parents[1]
LOCALES = ("en", "zh-hans", "zh-hant", "ja", "ko", "pt-br", "ru", "vi", "es", "fr")
EXAMPLES = {
    "go": (
        "Go",
        "go mod download\ngo run ./cmd/demo",
        "Go 1.23+ / coder/websocket",
        "cmd/demo/main.go",
    ),
    "java": (
        "Java",
        "mvn package dependency:copy-dependencies\njava -cp 'target/classes:target/dependency/*' org.jumpserver.pam.Demo",
        "JDK 11+ / Maven / Jackson",
        "src/main/java/org/jumpserver/pam/Demo.java",
    ),
    "node": ("Node.js", "npm ci\nnode demo.js", "Node.js 20.3+ / ws", "demo.js"),
    "curl": ("cURL", "bash demo.sh", "Bash / cURL / OpenSSL / base64", "demo.sh"),
}
NATIVE_METHODS = {
    "go": [
        "GetCredential(ctx, CredentialSelector{Key: ...})",
        "GetCredential(ctx, CredentialSelector{AccountID: ...})",
        "GetCredentialFresh(ctx, selector)",
        "ConfirmCredential(ctx, key, revision, accountID)",
        "WatchEvents(ctx, EventHandlers{...}) / StartEvents(ctx, handlers)",
        "EventWatcher.Stop() / EventWatcher.Wait()",
        "WatchCredentialEvents(ctx, handler)",
        "ListApplicationCommands(ctx)",
        "ReportApplicationCommandResult(ctx, commandID, status, errorCode)",
        "ExecuteApplicationCommand(ctx, event, handler)",
        "SyncAgent(ctx, AgentSyncOptions{...})",
        "Clone() / Close()",
    ],
    "java": [
        "getCredential(key)",
        "getCredentialByAccountId(accountId)",
        "getCredential(key, false) / getCredentialByAccountId(accountId, false)",
        "confirmCredential(key, revision, accountId)",
        "watchCredentialEvents()",
        "watchEvents(listener) / startEvents(listener)",
        "EventSubscription.stop() / close() / awaitTermination()",
        "listApplicationCommands()",
        "reportApplicationCommandResult(commandId, status, errorCode)",
        "executeApplicationCommand(event, handler)",
        "syncAgent(credentials, deliveredCredentials, configDigest, syncStatus, syncError)",
        "clone() / close()",
    ],
    "node": [
        "getCredential({key})",
        "getCredential({accountId})",
        "getCredential({key, allowLocalFallback: false})",
        "confirmCredential({key, revision, accountId})",
        "watchCredentialEvents({signal})",
        "watchEvents({signal}) / startEvents({signal}) / stopEvents()",
        "EventSubscription.stop() / done",
        "listApplicationCommands()",
        "reportApplicationCommandResult({commandId, status, errorCode})",
        "executeApplicationCommand(event, handler)",
        "syncAgent({credentials, deliveredCredentials, ...})",
        "clone() / close()",
    ],
}
NATIVE_EXAMPLES = {
    "go": ("go", "cmd/demo/main.go", "cmd/events/main.go"),
    "java": (
        "java",
        "src/main/java/org/jumpserver/pam/Demo.java",
        "src/main/java/org/jumpserver/pam/EventsDemo.java",
    ),
    "node": ("javascript", "demo.js", "events.js"),
}
HOOK_EXAMPLES = {
    "python": ("python", "subclass_demo.py"),
    "go": ("go", "cmd/hooks/main.go"),
    "java": ("java", "src/main/java/org/jumpserver/pam/HooksDemo.java"),
    "node": ("javascript", "hooks.js"),
}
LATEST_CREDENTIAL_APIS = {
    "python": """- `credential.from_local`
- `get_credential(key=..., allow_local_fallback=False)` / `get_credential(account_id=..., allow_local_fallback=False)`""",
    "go": """- `credential.FromLocal`
- `GetCredentialFresh(ctx, selector)`""",
    "java": """- `credential.isFromLocal()`
- `getCredential(key, false)` / `getCredentialByAccountId(accountId, false)`""",
    "node": """- `credential.fromLocal`
- `getCredential({key, allowLocalFallback: false})` / `getCredential({accountId, allowLocalFallback: false})`""",
}

LIFECYCLES = {
    "python": "`watch_events(stop_event=...)` / `start_events(stop_event=...)`; `stop_events()` / `close()`",
    "go": "`WatchEvents(ctx, handlers)` / `StartEvents(ctx, handlers)`; `Stop()` / `Wait()`; `context.CancelFunc`",
    "java": "`watchEvents(listener)` / `startEvents(listener)`; `stop()` / `close()` / `awaitTermination()`",
    "node": "`watchEvents({signal})` / `startEvents({signal})`; `stopEvents()` / `await subscription.stop()` / `await subscription.done`",
}


def latest_credentials_section(language, texts):
    return f"""### {texts["latest_credentials_title"]}

{texts["latest_credentials_behavior"]}

{LATEST_CREDENTIAL_APIS[language]}

{texts["live_refresh"]}

{texts["event_liveness"]}
"""


def managed_section(language, texts):
    syntax, example = HOOK_EXAMPLES[language]
    return f"""## {texts["managed_title"]}

{texts["managed_intro"]}

```{syntax}
{(CLIENTS / language / example).read_text(encoding="utf-8").rstrip()}
```

{texts["managed_behavior"]}

{LIFECYCLES[language]}

{texts[f"managed_lifecycle_{language}"]}

{latest_credentials_section(language, texts)}
"""


NATIVE_INSTALL = {
    "go": """```bash
go mod edit -replace=github.com/jumpserver/jumpserver/apps/accounts/clients/go=/path/to/jumpserver/apps/accounts/clients/go
go get github.com/jumpserver/jumpserver/apps/accounts/clients/go@v0.0.0
```

```go
import pam "github.com/jumpserver/jumpserver/apps/accounts/clients/go"
```""",
    "java": """```bash
mvn -f /path/to/jumpserver/apps/accounts/clients/java/pom.xml install
```

```xml
<dependency>
  <groupId>org.jumpserver</groupId>
  <artifactId>jms-pam</artifactId>
  <version>1.0.0</version>
</dependency>
```

```java
import org.jumpserver.pam.Client;
```""",
    "node": """```bash
npm install /path/to/jumpserver/apps/accounts/clients/node
```

```javascript
const { Client } = require('@jumpserver/pam')
// ESM: import { Client } from '@jumpserver/pam'
```""",
}
NATIVE_ENVIRONMENT = """export JMS_ENDPOINT='https://jumpserver.example.com'
export JMS_APP_ID='<app-id>'
export JMS_APP_SECRET='<app-secret>'
export JMS_ORG_ID='<org-id>'
export JMS_INSTANCE_ID='app-node-1'
export JMS_ACCOUNT_ID='<account-id>'
"""

API_TABLE = """| HTTP | API | JSON / query |
| --- | --- | --- |
| GET | `/api/v1/accounts/credential-client/credential/` | `instance_id`, `key` / `account_id` |
| POST | `/api/v1/accounts/credential-client/confirm/` | `instance_id`, `key`, `revision`, `account_id` |
| GET | `/api/v1/accounts/credential-client/commands/` | `instance_id` |
| POST | `/api/v1/accounts/credential-client/command-result/` | `instance_id`, `command_id`, `status`, `error_code` |
| WebSocket | `/ws/accounts/credential-events/` | `instance_id` |
"""

ENVIRONMENT = """export API_URL='https://jumpserver.example.com'
export API_KEY_ID='<app-id>'
export API_KEY_SECRET='<app-secret>'
export ORG_ID='<org-id>'
"""

HEADERS = """(request-target) accept date digest x-jms-request-id x-jms-org
x-jms-client-version x-jms-protocol-version x-jms-config-schema-version"""


def legacy_guide(language, texts):
    label, command, runtime, example = EXAMPLES[language]
    extra = texts["curl_note"]
    return f"""# {label} — {texts["guide"]}

{texts["legacy_intro"]}

## {texts["requirements"]}

- {runtime}
- `{example}`

{extra}

## {texts["configure"]}

{texts["legacy_config"]}

```bash
cd apps/accounts/clients/{language}
{ENVIRONMENT}
{command}
```

{texts["targets"]}

## {texts["response"]}

```http
GET /api/v1/accounts/integration-applications/account-secret/?asset=ubuntu_docker&account=root
```

```json
{{"id":"<app-id>","secret":"<account-secret>"}}
```

{texts["legacy_response"]}

## {texts["troubleshooting"]}

{texts["legacy_errors"]}

## {texts["credential_policies"]}

{texts["policy_access"]}

{API_TABLE}
{texts["signature"]}

```text
{HEADERS}
```

{texts["confirmation"]}

{texts["receipts"]}
"""


def native_guide(language, texts):
    label, command, runtime, example = EXAMPLES[language]
    syntax, quickstart, events = NATIVE_EXAMPLES[language]
    directory = CLIENTS / language
    methods = "\n".join(f"- `{method}`" for method in NATIVE_METHODS[language])
    return f"""# JumpServer PAM {label} SDK

{texts["native_intro"]}

## {texts["requirements"]}

- {runtime}
- `{example}`

## {texts["configure"]}

{texts["native_setup"]}

```bash
cd apps/accounts/clients/{language}
{NATIVE_ENVIRONMENT}
{command}
```

{texts["native_install"]}

{NATIVE_INSTALL[language]}

## {texts["response"]}

```{syntax}
{(directory / quickstart).read_text(encoding="utf-8").rstrip()}
```

{managed_section(language, texts)}

## {texts["events"]}

{texts["native_events"]}

```{syntax}
{(directory / events).read_text(encoding="utf-8").rstrip()}
```

{texts["confirmation"]}

## {texts["commands"]}

{texts["native_commands"]}

## {texts["methods"]}

{methods}

## {texts["troubleshooting"]}

{texts["native_errors"]}

`{"PAMException" if language == "java" else "PAMError"}`

{texts["native_compatibility"]}

## {texts["agent_title"]}

{texts["native_agent"]}

{texts["agent_rules"]}

{agent_configuration_section(texts)}
"""


AGENT_SAMPLE = {'endpoint': 'https://jumpserver.example.com', 'app_id': '<application-id>', 'app_secret': '<application-secret>', 'org_id': '<org-id>', 'instance_id': 'orders-node-1', 'state_file': '/var/lib/jms-pam-agent/state.json', 'event_file': '/var/lib/jms-pam-agent/events.jsonl', 'reconcile_interval': 300, 'delivery': {'delivery_mode': 'json', 'delivery_root': '/opt/jumpserver-pam/credentials', 'socket_path': '/run/jms-pam-agent/agent.sock', 'app_user': 'orders', 'systemd_unit': '', 'systemd_action': ''}, 'rules': []}
AGENT_RULE = {'keys': ['<credential-key>'], 'files': [{'path': '/etc/order-service/database.json', 'format': 'template', 'template_file': '/etc/jms-pam-agent/orders-db.tmpl', 'owner': 'orders'}], 'action': {'type': 'systemd', 'unit': 'order-service.service', 'operation': 'reload', 'timeout_seconds': 30}}


def agent_configuration_section(texts):
    return f"""{texts['agent_config']}

```json
{json.dumps(AGENT_SAMPLE, indent=2)}
```

`rules`:

```json
{json.dumps([AGENT_RULE], indent=2)}
```

`/etc/jms-pam-agent/orders-db.tmpl`:

```gotemplate
{{
  "username": {{{{json (index .Credentials "<credential-key>").Username}}}},
  "password": {{{{json (index .Credentials "<credential-key>").Secret}}}}
}}
```

```bash
jms-pam-agent get_accounts
jms-pam-agent get_secret '<account-id>'
sudo jms-pam-agent check-config
sudo systemctl restart jms-pam-agent
```
"""


def python_guide(texts):
    return f"""# JumpServer PAM Python SDK / Agent

{texts["python_intro"]}

<!-- agent-doc:start -->

## {texts["agent_title"]}

{texts["agent_setup"]}

```bash
cd apps/accounts/clients/go
CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -o jms-pam-agent ./cmd/jms-pam-agent
sudo install -m 0755 ./jms-pam-agent /usr/local/bin/jms-pam-agent
chmod 0600 ./jms_pam_agent.json
sudo /usr/local/bin/jms-pam-agent install \\
  --bootstrap ./jms_pam_agent.json --instance-id app-node-1
```

{texts["agent_portable"]}

{texts["agent_paths"]}

- JSON: `/opt/jumpserver-pam/credentials/<credential-key>.json`
- EnvironmentFile: `/opt/jumpserver-pam/credentials/<credential-key>.env`
- Unix Socket: `/run/jms-pam-agent/agent.sock`

{texts["agent_delivery"]}

```ini
[Service]
EnvironmentFile=-/opt/jumpserver-pam/credentials/<credential-key>.env
```

{texts["agent_environment"]}

{texts["agent_rules"]}

{agent_configuration_section(texts)}

### {texts["local_api"]}

```bash
curl --fail --silent --show-error \\
  --unix-socket '/run/jms-pam-agent/agent.sock' \\
  http://localhost/v1/health

curl --fail --silent --show-error \\
  --unix-socket '/run/jms-pam-agent/agent.sock' \\
  'http://localhost/v1/credentials/<credential-key>'
```

{texts["confirmation"]}

```bash
/usr/local/bin/jms-pam-agent confirm '<credential-key>' \\
  --revision '<revision>' \\
  --socket '/run/jms-pam-agent/agent.sock'
```

{texts["agent_confirm"]}

### {texts["troubleshooting"]}

```bash
sudo systemctl start jms-pam-agent
sudo systemctl status jms-pam-agent --no-pager
sudo journalctl -u jms-pam-agent -n 100 --no-pager
sudo systemctl restart jms-pam-agent
```

{texts["recovery"]}

<!-- agent-doc:end -->

<!-- sdk-doc:start -->

## {texts["sdk_title"]}

{texts["sdk_setup"]}

```bash
python3 -m pip install ./apps/accounts/clients/python
```

{texts["sdk_config"]}

```python
from jms_pam import Client
from jms_pam_config import client_options, instance_id


with Client(instance_id=instance_id, **client_options) as client:
    credential = client.get_credential(account_id="<account-id>")
    username = credential.account.username
    secret = credential.account.secret
```

### {texts["events"]}

{texts["event_processing"]}

```python
from jms_pam import Client
from jms_pam_config import client_options, instance_id


def apply_credential(credential):
    raise NotImplementedError({texts["apply_error"]!r})


with Client(instance_id=instance_id, **client_options) as client:
    for event in client.watch_credential_events():
        if event.get("event") == "snapshot":
            updates = event.get("credentials", [])
        elif event.get("event") == "credential.updated":
            updates = [event]
        else:
            continue
        for update in updates:
            mode = update.get("credential_mode")
            key = update.get("credential_key") or update.get("key")
            account_id = update.get("account_id")
            if mode == "subscription" and account_id and key:
                policy_key = key if key.endswith(f":{{account_id}}") else f"{{key}}:{{account_id}}"
                credential = client.get_credential(key=policy_key, allow_local_fallback=False)
            elif mode == "alternating_rotation" and key:
                credential = client.get_credential(key=key, allow_local_fallback=False)
            else:
                continue
            apply_credential(credential)
            if mode == "alternating_rotation":
                client.confirm_credential(
                    key=credential.key,
                    revision=credential.revision,
                    account_id=credential.account.id,
                )
```

{texts["confirmation"]}

{texts["sdk_receipts"]}

{managed_section("python", texts)}

### {texts["commands"]}

{texts["command_processing"]}

### {texts["methods"]}

- `get_credential(key=...)` / `get_credential(account_id=...)`
- `confirm_credential(key=..., revision=..., account_id=...)`
- `watch_credential_events(stop_event=...)`
- `watch_events(stop_event=...)` / `start_events(stop_event=...)` / `stop_events()`
- `list_application_commands()`
- `report_application_command_result(command_id=..., status=...)`
- `execute_application_command(event, handler)`
- `sync_agent(credentials=..., delivered_credentials=...)`
- `clone()` / `close()`

{texts["sdk_errors"]}

{texts["compatibility"]}

<!-- sdk-doc:end -->
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    differences = []
    for locale in LOCALES:
        texts = json.loads(
            (Path(__file__).parent / "translations" / f"{locale}.json").read_text(
                encoding="utf-8"
            )
        )
        documents = {
            CLIENTS / language / f"README.{locale}.md": (
                legacy_guide(language, texts)
                if language == "curl"
                else native_guide(language, texts)
            )
            for language in EXAMPLES
        }
        # The complete English and Simplified Chinese Python references are maintained directly.
        if locale not in ("en", "zh-hans"):
            documents[CLIENTS / "python" / f"README.{locale}.md"] = python_guide(texts)
        for path, content in documents.items():
            content = content.rstrip() + "\n"
            if args.check:
                if not path.is_file() or path.read_text(encoding="utf-8") != content:
                    differences.append(str(path.relative_to(CLIENTS)))
            else:
                path.write_text(content, encoding="utf-8")
    if differences:
        parser.exit(1, "\n".join(differences) + "\n")


if __name__ == "__main__":
    main()
