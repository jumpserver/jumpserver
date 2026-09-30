# JumpServer PAM Node.js SDK

Este SDK acompanha o SDK Python de políticas de credenciais: consulta por conta autorizada ou política de rotação, confirmação de versões aplicadas, eventos, comandos e sincronização Agent. URL, assinatura HMAC, Digest, data UTC, ID de requisição e cabeçalhos são gerados automaticamente.

## Requisitos

- Node.js 20.3+ / ws
- `demo.js`

## Configurar e executar

Instale o SDK fonte e configure os valores abaixo. Autorize contas para pull em Gerenciamento de aplicações; vincule políticas somente quando precisar de push ou rotação. Obtenha AK/SK e ID da organização nos materiais de acesso. Substitua os exemplos e proteja os segredos de implantação. Cada réplica precisa de um ID estável e único. Use um só seletor: ID da conta ou key da política.

```bash
cd apps/accounts/clients/node
export JMS_ENDPOINT='https://jumpserver.example.com'
export JMS_APP_ID='<app-id>'
export JMS_APP_SECRET='<app-secret>'
export JMS_ORG_ID='<org-id>'
export JMS_INSTANCE_ID='app-node-1'
export JMS_ACCOUNT_ID='<account-id>'

npm ci
node demo.js
```

Os SDKs são instalados a partir deste repositório e ainda não foram publicados em registros públicos. Substitua /path/to/jumpserver por um caminho absoluto. Execute a instalação Go e Node.js no diretório da aplicação ou adicione a dependência Java ao pom.xml da aplicação. Substitua as importações locais dos exemplos pelas importações de pacote abaixo.

```bash
npm install /path/to/jumpserver/apps/accounts/clients/node
```

```javascript
const { Client } = require('@jumpserver/pam')
// ESM: import { Client } from '@jumpserver/pam'
```

## Requisição e resposta

```javascript
'use strict'

const { Client } = require('./index')

async function main() {
  const client = new Client({
    endpoint: process.env.JMS_ENDPOINT,
    appId: process.env.JMS_APP_ID,
    appSecret: process.env.JMS_APP_SECRET,
    instanceId: process.env.JMS_INSTANCE_ID,
    orgId: process.env.JMS_ORG_ID,
  })
  try {
    const credential = await client.getCredential({ accountId: process.env.JMS_ACCOUNT_ID })
    // Pass credential.account.username / secret to the application connection pool.
    console.log(
      `Fetched revision ${credential.revision}; implement application credential switching.`,
    )
  } finally {
    client.close()
  }
}

if (require.main === module)
  main().catch((error) => {
    console.error(error.code || error.name)
    process.exitCode = 1
  })
```

## Manipuladores de eventos

Inicialize o estado local antes de iniciar a escuta. Python e Node.js usam subclasses, Go usa EventHandlers e Java usa CredentialEventListener. Implemente a troca real de conexões do exemplo. A API anterior continua disponível.

```javascript
'use strict'
const { Client } = require('./index')

class MyClient extends Client {
  constructor(options) {
    super(options)
    this.credentials = new Map()
    this.modes = new Map()
  }
  async onEvent(event) {
    if (event.event === 'snapshot') {
      this.modes.clear()
      for (const update of event.credentials || [])
        this.modes.set(update.credentialKey || update.key, update.credentialMode)
      for (const key of this.credentials.keys())
        if (!this.modes.has(key)) this.credentials.delete(key) // Also release connections.
    } else if (event.event === 'credential.updated') {
      this.modes.set(event.credentialKey || event.key, event.credentialMode)
    }
    // Use executeApplicationCommand for command events; see events.js.
  }
  async onCredentialChanged(credential, { signal }) {
    await this.applyCredential(credential, { signal })
    if (this.modes.get(credential.key) === 'alternating_rotation')
      await this.confirmCredential({ key: credential.key, revision: credential.revision,
        accountId: credential.account.id, signal })
    this.credentials.set(credential.key, credential)
  }
  async applyCredential(credential, { signal }) {
    throw new Error('Implement connection validation, pool switching and old connection cleanup')
  }
  async onCredentialRevoked(event) {
    this.credentials.delete(event.credentialKey || event.key) // Also release affected connections.
  }
}

async function main() {
  const client = new MyClient({ endpoint: process.env.JMS_ENDPOINT, appId: process.env.JMS_APP_ID,
    appSecret: process.env.JMS_APP_SECRET, instanceId: process.env.JMS_INSTANCE_ID, orgId: process.env.JMS_ORG_ID })
  const stop = () => client.close()
  process.once('SIGINT', stop); process.once('SIGTERM', stop)
  try { await client.watchEvents() }
  finally {
    client.close(); await client.stopEvents()
    process.removeListener('SIGINT', stop); process.removeListener('SIGTERM', stop)
  }
}
if (require.main === module) main().catch((error) => {
  console.error(error.code || error.name); process.exitCode = 1
})
module.exports = { MyClient }
```

Os snapshot inicial e de reconexão e credential.updated consultam por modo e chamam o manipulador em série. A leitura usa uma fila limitada a 128 eventos; quando cheia, aplica contrapressão. Falhas de consulta ou aplicação tentam novamente com espera exponencial de 1–30 segundos e uma nova consulta. Atualizações substituem tentativas do mesmo destino; snapshot redefine o escopo e revogação ou configuração cancela tentativas. Os manipuladores devem ser idempotentes. Observadores e revogação não são repetidos automaticamente; comandos exigem reivindicação. received significa leitura; o SDK não confirma rotações automaticamente. Eventos de versões anteriores não cancelam a consulta pendente de uma versão mais recente.

`watchEvents({signal})` / `startEvents({signal})`; `stopEvents()` / `await subscription.stop()` / `await subscription.done`

watchEvents não bloqueia o loop de eventos; startEvents não garante a sincronização inicial. Um listener por cliente. Métodos async são aguardados em série com AbortSignal. close cancela; aguarde stop() ou done externamente. Não aguarde seu próprio done. clone retorna Client.

### Credenciais mais recentes e indisponibilidade do servidor

A consulta solicita primeiro a API. Uma resposta válida substitui a credencial retida; versões antigas não sobrescrevem novas e não há expiração por tempo. Apenas tempo limite, falha de rede ou HTTP 5xx permite retornar o último valor do mesmo seletor com a marca local. Sem valor anterior, propaga o erro. O SDK mantém os valores na memória até atualização, revogação ou fechamento; clone e reinício começam vazios. O Agent conserva os valores em seu estado local protegido. HTTP 401/403/404 ou client_upgrade_required apagam os valores do SDK e falham; uma resposta de sucesso inválida também falha. Revogação remove as credenciais afetadas e snapshot remove as não autorizadas. Uma mudança de configuração conserva os valores até conferir o snapshot seguinte. O Agent aplica revogações explícitas e reduções de escopo do snapshot antes da sincronização HTTP, salva esse escopo e bloqueia as leituras locais afetadas mesmo durante falhas ou após reiniciar. Uma resposta credential_not_found (HTTP 400) também apaga os valores mantidos pelo SDK. O pull direto por account_id sempre exige uma resposta ativa da API; snapshots de push não autorizam valores de pull em cache.

- `credential.fromLocal`
- `getCredential({key, allowLocalFallback: false})` / `getCredential({accountId, allowLocalFallback: false})`

Com escuta gerenciada ativa, snapshot e credential.updated consultam automaticamente, substituem o valor e chamam o manipulador. Falha na atualização mantém o anterior e tenta novamente. O Agent também consulta após notificações e mantém os dados durante falhas do servidor. Use as chamadas que exigem a API abaixo para atualizar ou trocar conexões; uma credencial retida não é uma versão recém-obtida nem confirma rotações automaticamente.

Quando ocioso, envia ping a cada 10 segundos; cerca de 30 segundos sem mensagens causam reconexão, com espera exponencial de 1–30 segundos e nova assinatura. O snapshot restaura o estado atual sem reproduzir eventos passados.



## Eventos e aplicação de credenciais

Processe snapshot inicial ou de reconexão e credential.updated. O exemplo completo trata subscription, alternating_rotation e comandos. Implemente verificação de conexão real, troca do pool e liberação das conexões antigas. O marcador lança uma exceção e impede confirmar antes de aplicar. Remova do estado da aplicação contas ausentes dos snapshots e trate revogações.

```javascript
'use strict'
const { Client } = require('./index')

async function applyCredential(credential) {
  // Validate a real connection, switch the pool, then release old connections.
  throw new Error('Implement application credential switching')
}
async function restartApplication() {
  throw new Error('Implement application restart and health check')
}
async function handleCommand(client, event) {
  if (event.event === 'application.restart.requested') return restartApplication()
  if (event.event !== 'credential.switch.requested')
    throw new Error('Unsupported application command')
  const credential = await client.getCredential({ key: event.credentialKey, allowLocalFallback: false })
  if (credential.revision !== event.revision || credential.account.id !== event.accountId)
    throw new Error('Requested account version is superseded')
  await applyCredential(credential)
  await client.confirmCredential({
    key: credential.key,
    revision: credential.revision,
    accountId: credential.account.id,
  })
}
async function main() {
  const client = new Client({
    endpoint: process.env.JMS_ENDPOINT,
    appId: process.env.JMS_APP_ID,
    appSecret: process.env.JMS_APP_SECRET,
    instanceId: process.env.JMS_INSTANCE_ID,
    orgId: process.env.JMS_ORG_ID,
  })
  const stop = () => client.close()
  process.once('SIGINT', stop)
  process.once('SIGTERM', stop)
  try {
    for await (const event of client.watchCredentialEvents()) {
      if (event.commandId) {
        try {
          await client.executeApplicationCommand(event, (command) => handleCommand(client, command))
        } catch {
          /* Failure is reported; keep secrets out of logs. */
        }
        continue
      }
      const updates =
        event.event === 'snapshot'
          ? event.credentials
          : event.event === 'credential.updated'
            ? [event]
            : []
      // On snapshots, remove application caches absent from the new authorized scope.
      for (const update of updates || []) {
        const mode = update.credentialMode
        const key = update.credentialKey || update.key
        let credential
        if (mode === 'subscription' && update.accountId && key) {
          const subscriptionKey = key.endsWith(`:${update.accountId}`) ? key : `${key}:${update.accountId}`
          credential = await client.getCredential({ key: subscriptionKey, allowLocalFallback: false })
        }
        else if (mode === 'alternating_rotation' && key)
          credential = await client.getCredential({ key, allowLocalFallback: false })
        else continue
        await applyCredential(credential)
        if (mode === 'alternating_rotation')
          await client.confirmCredential({
            key: credential.key,
            revision: credential.revision,
            accountId: credential.account.id,
          })
      }
    }
  } finally {
    client.close()
    process.removeListener('SIGINT', stop)
    process.removeListener('SIGTERM', stop)
  }
}
if (require.main === module)
  main().catch((error) => {
    console.error(error.code || error.name)
    process.exitCode = 1
  })
```

Na rotação alternada, valide uma conexão real, troque o pool e libere conexões antigas antes de confirmar exatamente key, revision e account_id. Assinaturas de alterações de credenciais não exigem confirmação. Falhas na verificação de conexão devem impedir a confirmação.

## Comandos de aplicação

Consulta, solicitação de execução e resultados usam métodos SDK. Apenas uma solicitação aceita executa o handler. A troca verifica versão e conta, aplica e confirma; o reinício reinicia e verifica a saúde. Informe sucesso ao concluir. Falhas no relatório preservam a exceção original do handler.

## Métodos comuns

- `getCredential({key})`
- `getCredential({accountId})`
- `getCredential({key, allowLocalFallback: false})`
- `confirmCredential({key, revision, accountId})`
- `watchCredentialEvents({signal})`
- `watchEvents({signal}) / startEvents({signal}) / stopEvents()`
- `EventSubscription.stop() / done`
- `listApplicationCommands()`
- `reportApplicationCommandResult({commandId, status, errorCode})`
- `executeApplicationCommand(event, handler)`
- `syncAgent({credentials, deliveredCredentials, ...})`
- `clone() / close()`

## Solução de problemas

Falhas HTTP, rede, autenticação e decodificação usam o tipo de erro SDK com código e estado HTTP. Feche fluxos e clientes após usar; clones têm ciclos de vida independentes. Repita falhas transitórias na aplicação e não registre segredos nem cabeçalhos de autenticação.

`PAMError`

Todos os SDKs usam protocolo versão 1; Agent usa esquema de configuração versão 1. Em client_upgrade_required (HTTP 426), verifique compatibilidade e atualize. Campos opcionais e notificações desconhecidos são tolerados; não aplique nem confirme políticas não suportadas. Os recibos são automáticos e não provam aplicação de credenciais.

## Integração com o Go Agent

A identidade usa app_id, app_secret, org_id e instance_id estável; as permissões seguem as políticas da aplicação. Caminhos e ações são locais: state_file mantém as senhas atuais, event_file registra eventos sem segredos, delivery define a saída padrão e rules define arquivos, modelos e reload/restart ou scripts fixos. Ao receber uma atualização, o Agent busca e salva a senha atual, substitui os arquivos atomicamente e executa a ação; falhas são tentadas novamente. Use credentials[].key de get_accounts nas regras; chaves de assinatura incluem o ID da conta. rules vazio grava um arquivo por chave.

As rules locais definem arquivos, JSON/EnvironmentFile ou modelos confiáveis e uma ação systemd reload/restart ou executável fixo. Scripts recebem JSON via stdin, usam argumentos fixos e prazo limitado, e verificam a aplicação antes de retornar sucesso. Core não pode ampliar essas capacidades. Reinicie o Agent após editar a configuração privada.

A identidade usa app_id, app_secret, org_id e instance_id estável; as permissões seguem as políticas da aplicação. Caminhos e ações são locais: state_file mantém as senhas atuais, event_file registra eventos sem segredos, delivery define a saída padrão e rules define arquivos, modelos e reload/restart ou scripts fixos. Ao receber uma atualização, o Agent busca e salva a senha atual, substitui os arquivos atomicamente e executa a ação; falhas são tentadas novamente. Use credentials[].key de get_accounts nas regras; chaves de assinatura incluem o ID da conta. rules vazio grava um arquivo por chave.

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

`rules`:

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

`/etc/jms-pam-agent/orders-db.tmpl`:

```gotemplate
{
  "username": {{json (index .Credentials "<credential-key>").Username}},
  "password": {{json (index .Credentials "<credential-key>").Secret}}
}
```

```bash
jms-pam-agent get_accounts
jms-pam-agent get_secret '<account-id>'
sudo jms-pam-agent check-config
sudo systemctl restart jms-pam-agent
```
