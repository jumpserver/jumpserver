# JumpServer PAM Python SDK / Agent

Python 3.9+ fornece o SDK de políticas de credenciais e o Agent Linux. O SDK usa AK/SK da aplicação; o Agent entrega credenciais localmente para aplicações de outras linguagens.

<!-- agent-doc:start -->

## Integração com o Agent Linux

Prepare Linux com systemd, Python 3.9+ e o usuário da aplicação. Vincule uma política e autorize suas contas; a rotação alternada precisa das duas. No assistente de acesso selecione Agent, configure usuário, caminho e modo de entrega e baixe jms_pam_agent.json. Instale o diretório SDK baixado e execute o comando para o caminho padrão, substituindo os valores de exemplo. Cada réplica precisa de um ID estável e único.

```bash
sudo python3 -m venv /opt/jumpserver-pam/venv
sudo /opt/jumpserver-pam/venv/bin/python -m pip install '<sdk-directory>'
sudo /opt/jumpserver-pam/venv/bin/jms-pam-agent install \
  --bootstrap ./jms_pam_agent.json --instance-id app-node-1
```

Os caminhos padrão estão abaixo. Obtenha configuration-id da configuração inicial baixada e credential-key da política. O caminho configurado pode ser diferente. A configuração inicial contém AK/SK: restrinja seu acesso, remova a cópia baixada após instalar e proteja a configuração instalada.

- JSON: `/opt/jumpserver-pam/credentials/<configuration-id>/<credential-key>.json`
- EnvironmentFile: `/opt/jumpserver-pam/credentials/<configuration-id>/<credential-key>.env`
- Unix Socket: `/run/jumpserver-pam/<configuration-id>/agent.sock`

Escolha JSON para arquivos, EnvironmentFile para um serviço systemd definido na instalação ou Unix Socket para a API local. O Agent registra revisões entregues após a entrega; a aplicação valida e aplica antes de registrar a revisão aplicada. O socket pertence ao usuário configurado com modo 0600; faça requisições locais como esse usuário.

```ini
[Service]
EnvironmentFile=-/opt/jumpserver-pam/credentials/<configuration-id>/<credential-key>.env
```

A unidade systemd deve referenciar EnvironmentFile. Use reload apenas se a aplicação reler o arquivo; não injeta novas variáveis de ambiente em um processo existente. A instalação fixa caminhos, usuário, serviço e ação permitidos; ampliá-los exige reinstalação.

### API local e confirmação

```bash
curl --fail --silent --show-error \
  --unix-socket '/run/jumpserver-pam/<configuration-id>/agent.sock' \
  http://localhost/v1/health

curl --fail --silent --show-error \
  --unix-socket '/run/jumpserver-pam/<configuration-id>/agent.sock' \
  'http://localhost/v1/credentials/<credential-key>'
```

Na rotação alternada, valide uma conexão real, troque o pool e libere conexões antigas antes de confirmar exatamente key, revision e account_id. Assinaturas de alterações de credenciais não exigem confirmação. Falhas na verificação de conexão devem impedir a confirmação.

```bash
/opt/jumpserver-pam/venv/bin/jms-pam-agent confirm '<credential-key>' \
  --revision '<revision>' \
  --socket '/run/jumpserver-pam/<configuration-id>/agent.sock'
```

Somente a rotação alternada usa confirm. A confirmação local é persistida primeiro; confirmed significa que Core a aceitou e pending indica nova tentativa. Não confirme apenas porque um arquivo foi gravado ou um serviço reiniciado.

### Solução de problemas

```bash
sudo systemctl status 'jms-pam-agent-<configuration-id>.service' --no-pager
sudo journalctl -u 'jms-pam-agent-<configuration-id>.service' -n 100 --no-pager
sudo systemctl restart 'jms-pam-agent-<configuration-id>.service'
```

O Agent reconcilia ao iniciar, em eventos pertinentes e a cada 300 segundos. Falhas de rede preservam o cache autorizado. Rejeições de identidade ou autorização bloqueiam a leitura pelo socket; uma sincronização assinada bem-sucedida a restaura. Arquivos já gravados permanecem. SIGINT/SIGTERM encerram servidor, conexões e thread de leitura.

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
from jms_pam_config import client_options


with Client(instance_id="app-node-1", **client_options) as client:
    credential = client.get_credential(account_id="<account-id>")
    username = credential.account.username
    secret = credential.account.secret
```

### Eventos e aplicação de credenciais

Processe snapshot inicial ou de reconexão e credential.updated. O exemplo distingue subscription de alternating_rotation. Implemente apply_credential para validar conexão real, trocar o pool e liberar conexões antigas. O marcador lança uma exceção para impedir a confirmação de credenciais não aplicadas.

```python
from jms_pam import Client
from jms_pam_config import client_options


def apply_credential(credential):
    raise NotImplementedError('Implemente e verifique a troca de credenciais da aplicação')


with Client(instance_id="app-node-1", **client_options) as client:
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
            if mode == "subscription" and account_id:
                credential = client.get_credential(account_id=account_id)
            elif mode == "alternating_rotation" and key:
                credential = client.get_credential(key=key)
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

### Comandos de aplicação

Use list_application_commands para consultar solicitações pendentes e execute_application_command(event, handler) para solicitar a execução. Apenas uma solicitação aceita executa o handler. O de troca verifica revisão e conta, aplica e confirma; o de reinício reinicia e verifica a saúde. Informe sucesso somente ao concluir. Falhas ao informar o resultado preservam a exceção original do handler.

### Métodos comuns

- `get_credential(key=...)` / `get_credential(account_id=...)`
- `confirm_credential(key=..., revision=..., account_id=...)`
- `watch_credential_events(stop_event=...)`
- `list_application_commands()`
- `report_application_command_result(command_id=..., status=...)`
- `execute_application_command(event, handler)`
- `sync_agent(credentials=..., delivered_credentials=...)`
- `clone()` / `close()`

O cliente fecha sessões HTTP e fluxos de eventos com with ou close. clone cria uma sessão independente. Falhas HTTP, rede, autenticação e decodificação geram PAMError com code, status_code, detail e original_error. Repita erros transitórios na aplicação, trate rejeições de autorização e não registre credenciais.

Código novo usa métodos snake_case com argumentos nomeados e atributos de dataclass. A API original credential.v1 continua disponível com DeprecationWarning. SDK versão 1 usa o protocolo do Agent; sync_agent aceita KnownRevision para revisões em cache e entregues.

<!-- sdk-doc:end -->
