# JumpServer PAM Python SDK / Agent

Python 3.9+ fornece o SDK de políticas de credenciais. O jms-pam-agent em Go entrega credenciais por arquivos locais, ações fixas ou Socket local sem Python. A execução em primeiro plano funciona em Linux, macOS e Windows; a instalação systemd integrada é exclusiva do Linux.

<!-- agent-doc:start -->

## Integração com o Go Agent

Prepare Linux com systemd e o usuário da aplicação. Baixe jms_pam_agent.json no assistente, compile ou obtenha o binário Go e instale com um ID estável e único. A configuração local é /etc/jms-pam-agent/agent.json e o serviço fixo é jms-pam-agent.

```bash
cd apps/accounts/clients/go
CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -o jms-pam-agent ./cmd/jms-pam-agent
sudo install -m 0755 ./jms-pam-agent /usr/local/bin/jms-pam-agent
chmod 0600 ./jms_pam_agent.json
sudo /usr/local/bin/jms-pam-agent install \
  --bootstrap ./jms_pam_agent.json --instance-id app-node-1
```

O instalador integrado requer Linux e root. Em macOS, Linux sem root ou Windows, escolha JSON ou Socket no assistente e siga os comandos init-local e run --local --config. Inicialize uma vez e reutilize a configuração local privada; o modo em primeiro plano não executa ações systemd.

`/etc/jms-pam-agent/agent.json`: `0600`; `state_file`, `event_file`, `delivery.delivery_root`, `delivery.socket_path`.

- JSON: `/opt/jumpserver-pam/credentials/<credential-key>.json`
- EnvironmentFile: `/opt/jumpserver-pam/credentials/<credential-key>.env`
- Unix Socket: `/run/jms-pam-agent/agent.sock`

Escolha JSON para arquivos, EnvironmentFile para um serviço systemd definido na instalação ou Unix Socket para a API local. O Agent registra revisões entregues após a entrega; a aplicação valida e aplica antes de registrar a revisão aplicada. O socket pertence ao usuário configurado com modo 0600; faça requisições locais como esse usuário.

```ini
[Service]
EnvironmentFile=-/opt/jumpserver-pam/credentials/<credential-key>.env
```

A unidade systemd deve referenciar EnvironmentFile. Use reload apenas se a aplicação reler o arquivo; não injeta novas variáveis de ambiente em um processo existente. A instalação fixa caminhos, usuário, serviço e ação permitidos; ampliá-los exige reinstalação.

As rules locais definem arquivos, JSON/EnvironmentFile ou modelos confiáveis e uma ação systemd reload/restart ou executável fixo. Scripts recebem JSON via stdin, usam argumentos fixos e prazo limitado, e verificam a aplicação antes de retornar sucesso. Core não pode ampliar essas capacidades. Reinicie o Agent após editar a configuração privada.

A configuração baixada já inclui a identidade e a entrega do Agent. Em rules, declare os IDs das contas usadas pela aplicação, a atualização da configuração, a ativação e a verificação da conexão em execução. allow_account_switch permite a mesma regra na rotação A/B em ambos os sentidos. credential_check é opcional para testar o novo acesso antes de alterar arquivos. Há valores padrão para estado, eventos, Socket e reconciliação de 300 segundos. rules vazio grava um arquivo padrão por credencial.

```json
{
  "endpoint": "https://jumpserver.example.com",
  "app_id": "<application-id>",
  "app_secret": "<application-secret>",
  "org_id": "<org-id>",
  "instance_id": "orders-node-1",
  "delivery": {
    "delivery_mode": "json",
    "delivery_root": "/opt/jumpserver-pam/credentials",
    "app_user": "orders"
  },
  "rules": []
}
```

`rules`:

```json
[
  {
    "accounts": [
      {
        "account_id": "<primary-account-id>",
        "allow_account_switch": true
      }
    ],
    "config_update": {
      "file": "/etc/order-service/config.yml",
      "fields_map": {
        "DB_USER": "username",
        "DB_PASSWORD": "secret"
      }
    },
    "service_action": {
      "unit": "order-service.service",
      "operation": "restart"
    },
    "application_check": {
      "path": "/usr/local/libexec/jms-pam/check-running-db",
      "confirm_on_success": true
    }
  }
]
```

```bash
jms-pam-agent get_accounts
jms-pam-agent get_secret '<account-id>'
sudo jms-pam-agent check-config
sudo systemctl restart jms-pam-agent
```


### API local e confirmação

```bash
curl --fail --silent --show-error \
  --unix-socket '/run/jms-pam-agent/agent.sock' \
  http://localhost/v1/health

curl --fail --silent --show-error \
  --unix-socket '/run/jms-pam-agent/agent.sock' \
  'http://localhost/v1/credentials/<credential-key>'
```

Na rotação alternada, valide uma conexão real, troque o pool e libere conexões antigas antes de confirmar exatamente key, revision e account_id. Assinaturas de alterações de credenciais não exigem confirmação. Falhas na verificação de conexão devem impedir a confirmação.

```bash
/usr/local/bin/jms-pam-agent confirm '<credential-key>' \
  --revision '<revision>' \
  --socket '/run/jms-pam-agent/agent.sock'
```

Somente a rotação alternada usa confirm. A confirmação local é persistida primeiro; confirmed significa que Core a aceitou e pending indica nova tentativa. Não confirme apenas porque um arquivo foi gravado ou um serviço reiniciado.

### Solução de problemas

```bash
sudo systemctl start jms-pam-agent
sudo systemctl status jms-pam-agent --no-pager
sudo journalctl -u jms-pam-agent -n 100 --no-pager
sudo systemctl restart jms-pam-agent
```

O Agent reconcilia ao iniciar, em eventos pertinentes e a cada 300 segundos. Falhas de rede preservam as últimas credenciais autorizadas. Rejeições de identidade ou autorização bloqueiam a leitura pelo socket; uma sincronização assinada bem-sucedida a restaura. Arquivos já gravados permanecem. SIGINT/SIGTERM encerram servidor, conexões e thread de leitura.

<!-- agent-doc:end -->

<!-- sdk-doc:start -->

## Integração com o SDK Python

Crie e vincule uma política, autorize contas e baixe jms_pam_config.py pelo assistente de acesso. É necessário Python 3.9+. Instale do repositório com o comando abaixo ou execute python3 -m pip install . no diretório SDK baixado.

```bash
python3 -m pip install ./apps/accounts/clients/python
```

Coloque jms_pam_config.py junto da aplicação. client_options contém material de identidade: não o inclua no repositório nem nos logs. Use instance_id estável e único por réplica. get_credential aceita exatamente um seletor: account_id para contas autorizadas ou key para política de rotação.

```python
from jms_pam import Client
from jms_pam_config import client_options, instance_id


with Client(instance_id=instance_id, **client_options) as client:
    credential = client.get_credential(account_id="<account-id>")
    username = credential.account.username
    secret = credential.account.secret
```

### Eventos e aplicação de credenciais

Processe snapshot inicial ou de reconexão e credential.updated. O exemplo distingue subscription de alternating_rotation. Implemente apply_credential para validar conexão real, trocar o pool e liberar conexões antigas. O marcador lança uma exceção para impedir a confirmação de credenciais não aplicadas.

```python
from jms_pam import Client
from jms_pam_config import client_options, instance_id


def apply_credential(credential):
    raise NotImplementedError('Implemente e verifique a troca de credenciais da aplicação')


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
                policy_key = key if key.endswith(f":{account_id}") else f"{key}:{account_id}"
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

Na rotação alternada, valide uma conexão real, troque o pool e libere conexões antigas antes de confirmar exatamente key, revision e account_id. Assinaturas de alterações de credenciais não exigem confirmação. Falhas na verificação de conexão devem impedir a confirmação.

O SDK envia automaticamente um recibo received, na medida do possível, antes de retornar um evento de negócio. A aplicação não precisa enviá-lo novamente. O recibo indica apenas leitura, não aplicação de credenciais, e não substitui a confirmação. Reconcilie snapshots iniciais e de reconexão; snapshot e pong não exigem recibo.

## Manipuladores de eventos

Inicialize o estado local antes de iniciar a escuta. Python e Node.js usam subclasses, Go usa EventHandlers e Java usa CredentialEventListener. Implemente a troca real de conexões do exemplo. A API anterior continua disponível.

```python
"""Subscription example using subclass hooks; demo.py retains the iterator API."""

from jms_pam import Client
from jms_pam_config import client_options


class MyClient(Client):
    def __init__(self, *args, **options):
        super().__init__(*args, **options)
        self.credentials = {}

    def on_event(self, event):
        if event.get("event") == "snapshot":
            authorized_keys = {item["key"] for item in event.get("credentials", [])}
            for key in self.credentials.keys() - authorized_keys:
                # Also release this key's application connections.
                del self.credentials[key]

    def on_credential_changed(self, credential):
        # Validate and switch application connections using credential.asset and
        # credential.account. The handler must be safe to repeat on retry/reconnect.
        # Never log credential.account.secret or authentication headers.
        raise NotImplementedError("Implement the application connection update first")
        # Save only after the application has successfully switched connections:
        # self.credentials[credential.key] = credential

    def on_credential_revoked(self, event):
        self.credentials.pop(event.get("credential_key"), None)
        # Also release the affected application connections.


with MyClient(instance_id="order-service-node-1", **client_options) as client:
    client.watch_events()
```

Os snapshot inicial e de reconexão e credential.updated consultam por modo e chamam o manipulador em série. A leitura usa uma fila limitada a 128 eventos; quando cheia, aplica contrapressão. Falhas de consulta ou aplicação tentam novamente com espera exponencial de 1–30 segundos e uma nova consulta. Atualizações substituem tentativas do mesmo destino; snapshot redefine o escopo e revogação ou configuração cancela tentativas. Os manipuladores devem ser idempotentes. Observadores e revogação não são repetidos automaticamente; comandos exigem reivindicação. received significa leitura; o SDK não confirma rotações automaticamente. Eventos de versões anteriores não cancelam a consulta pendente de uma versão mais recente.

`watch_events(stop_event=...)` / `start_events(stop_event=...)`; `stop_events()` / `close()`

watch_events espera a parada; start_events não garante a sincronização inicial. Aguarde a aplicação estar pronta. Um listener por cliente. stop_events e close esperam o manipulador; ele pode parar seu próprio cliente. clone reinicializa a subclasse.

### Credenciais mais recentes e indisponibilidade do servidor

A consulta solicita primeiro a API. Uma resposta válida substitui a credencial retida; versões antigas não sobrescrevem novas e não há expiração por tempo. Apenas tempo limite, falha de rede ou HTTP 5xx permite retornar o último valor do mesmo seletor com a marca local. Sem valor anterior, propaga o erro. O SDK mantém os valores na memória até atualização, revogação ou fechamento; clone e reinício começam vazios. O Agent conserva os valores em seu estado local protegido. HTTP 401/403/404 ou client_upgrade_required apagam os valores do SDK e falham; uma resposta de sucesso inválida também falha. Revogação remove as credenciais afetadas e snapshot remove as não autorizadas. Uma mudança de configuração conserva os valores até conferir o snapshot seguinte. O Agent aplica revogações explícitas e reduções de escopo do snapshot antes da sincronização HTTP, salva esse escopo e bloqueia as leituras locais afetadas mesmo durante falhas ou após reiniciar. Uma resposta credential_not_found (HTTP 400) também apaga os valores mantidos pelo SDK. O pull direto por account_id sempre exige uma resposta ativa da API; snapshots de push não autorizam valores de pull em cache.

- `credential.from_local`
- `get_credential(key=..., allow_local_fallback=False)` / `get_credential(account_id=..., allow_local_fallback=False)`

Com escuta gerenciada ativa, snapshot e credential.updated consultam automaticamente, substituem o valor e chamam o manipulador. Falha na atualização mantém o anterior e tenta novamente. O Agent também consulta após notificações e mantém os dados durante falhas do servidor. Use as chamadas que exigem a API abaixo para atualizar ou trocar conexões; uma credencial retida não é uma versão recém-obtida nem confirma rotações automaticamente.

Quando ocioso, envia ping a cada 10 segundos; cerca de 30 segundos sem mensagens causam reconexão, com espera exponencial de 1–30 segundos e nova assinatura. O snapshot restaura o estado atual sem reproduzir eventos passados.



### Comandos de aplicação

Use list_application_commands para consultar solicitações pendentes e execute_application_command(event, handler) para solicitar a execução. Apenas uma solicitação aceita executa o handler. O de troca verifica revisão e conta, aplica e confirma; o de reinício reinicia e verifica a saúde. Informe sucesso somente ao concluir. Falhas ao informar o resultado preservam a exceção original do handler.

### Métodos comuns

- `get_credential(key=...)` / `get_credential(account_id=...)`
- `confirm_credential(key=..., revision=..., account_id=...)`
- `watch_credential_events(stop_event=...)`
- `watch_events(stop_event=...)` / `start_events(stop_event=...)` / `stop_events()`
- `list_application_commands()`
- `report_application_command_result(command_id=..., status=...)`
- `execute_application_command(event, handler)`
- `sync_agent(credentials=..., delivered_credentials=...)`
- `clone()` / `close()`

O cliente fecha sessões HTTP e fluxos de eventos com with ou close. clone cria uma sessão independente. Falhas HTTP, rede, autenticação e decodificação geram PAMError com code, status_code, detail e original_error. Repita erros transitórios na aplicação, trate rejeições de autorização e não registre credenciais.

Código novo usa métodos snake_case com argumentos nomeados e atributos de dataclass. A API original credential.v1 continua disponível com DeprecationWarning. SDK versão 1 usa o protocolo do Agent; sync_agent aceita KnownRevision para revisões mantidas e entregues.

<!-- sdk-doc:end -->
