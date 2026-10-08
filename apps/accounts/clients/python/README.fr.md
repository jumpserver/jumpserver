# JumpServer PAM Python SDK / Agent

Python 3.9+ fournit le SDK de politique d’identifiants. Le jms-pam-agent en Go livre les identifiants par fichiers locaux, actions fixes ou Socket local sans Python. Il fonctionne au premier plan sur Linux, macOS et Windows ; l’installation systemd intégrée est réservée à Linux.

<!-- agent-doc:start -->

## Intégration du Go Agent

Préparez Linux avec systemd et l’utilisateur de l’application. Téléchargez jms_pam_agent.json dans l’assistant, compilez ou obtenez le binaire Go et installez-le avec un identifiant stable et unique. La configuration locale est /etc/jms-pam-agent/agent.json et le service fixe est jms-pam-agent.

```bash
cd apps/accounts/clients/go
CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -o jms-pam-agent ./cmd/jms-pam-agent
sudo install -m 0755 ./jms-pam-agent /usr/local/bin/jms-pam-agent
chmod 0600 ./jms_pam_agent.json
sudo /usr/local/bin/jms-pam-agent install \
  --bootstrap ./jms_pam_agent.json --instance-id app-node-1
```

L’installateur intégré nécessite Linux et root. Sur macOS, Linux sans root ou Windows, choisissez JSON ou Socket dans l’assistant et suivez les commandes init-local et run --local --config. Initialisez une fois puis réutilisez la configuration locale privée ; le mode premier plan ne réalise pas d’actions systemd.

`/etc/jms-pam-agent/agent.json`: `0600`; `state_file`, `event_file`, `delivery.delivery_root`, `delivery.socket_path`.

- JSON: `/opt/jumpserver-pam/credentials/<credential-key>.json`
- EnvironmentFile: `/opt/jumpserver-pam/credentials/<credential-key>.env`
- Unix Socket: `/run/jms-pam-agent/agent.sock`

Choisissez JSON pour les fichiers, EnvironmentFile pour un service systemd fixé à l’installation ou Unix Socket pour l’API locale. L’Agent enregistre les révisions distribuées après distribution ; l’application valide et applique avant d’enregistrer la révision appliquée. Le socket appartient à l’utilisateur configuré avec le mode 0600 ; effectuez les requêtes avec cet utilisateur.

```ini
[Service]
EnvironmentFile=-/opt/jumpserver-pam/credentials/<credential-key>.env
```

L’unité systemd doit référencer EnvironmentFile. Utilisez reload uniquement si l’application relit le fichier ; il n’injecte pas de nouvelles variables d’environnement dans un processus existant. L’installation fixe chemins, utilisateur, service et action autorisés ; leur extension nécessite une réinstallation.

Les rules locales définissent fichiers, JSON/EnvironmentFile ou modèles fiables et une action systemd reload/restart ou un exécutable fixe. Les scripts reçoivent le JSON sur stdin, avec arguments fixes et délai limité, et vérifient l’application avant de réussir. Core ne peut pas étendre ces capacités. Redémarrez l’Agent après modification de sa configuration privée.

La configuration téléchargée contient déjà l’identité et les paramètres de livraison de l’Agent. Dans rules, indiquez les ID des comptes utilisés, la mise à jour de configuration, l’activation et la vérification de la connexion en cours. allow_account_switch permet la même règle pour la rotation A/B dans les deux sens. credential_check est facultatif pour tester le nouvel accès avant de modifier les fichiers. L’état, les événements, le Socket et la synchronisation de 300 secondes ont des valeurs par défaut. Un rules vide écrit un fichier par identifiant.

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


### API locale et confirmation

```bash
curl --fail --silent --show-error \
  --unix-socket '/run/jms-pam-agent/agent.sock' \
  http://localhost/v1/health

curl --fail --silent --show-error \
  --unix-socket '/run/jms-pam-agent/agent.sock' \
  'http://localhost/v1/credentials/<credential-key>'
```

Pour la rotation alternée, validez une connexion réelle, remplacez le pool et libérez les anciennes connexions avant de confirmer exactement key, revision et account_id. Les abonnements aux changements d’identifiants ne nécessitent aucune confirmation. Un échec du contrôle de connexion doit empêcher la confirmation.

```bash
/usr/local/bin/jms-pam-agent confirm '<credential-key>' \
  --revision '<revision>' \
  --socket '/run/jms-pam-agent/agent.sock'
```

Seule la rotation alternée utilise confirm. La confirmation locale est enregistrée d’abord ; confirmed signifie que Core l’a acceptée et pending qu’elle sera réessayée. Ne confirmez pas simplement parce qu’un fichier a été écrit ou un service redémarré.

### Dépannage

```bash
sudo systemctl start jms-pam-agent
sudo systemctl status jms-pam-agent --no-pager
sudo journalctl -u jms-pam-agent -n 100 --no-pager
sudo systemctl restart jms-pam-agent
```

L’Agent réconcilie au démarrage, lors d’événements pertinents et toutes les 300 secondes. Les pannes réseau conservent les derniers identifiants autorisés. Un refus d’identité ou d’autorisation bloque la lecture par socket ; une synchronisation signée réussie la rétablit. Les fichiers déjà écrits restent présents. SIGINT/SIGTERM ferment serveur, connexions et thread de lecture.

<!-- agent-doc:end -->

<!-- sdk-doc:start -->

## Intégration du SDK Python

Créez et associez une politique, autorisez les comptes et téléchargez jms_pam_config.py dans l’assistant d’accès. Python 3.9+ est requis. Installez depuis le dépôt avec la commande ci-dessous ou exécutez python3 -m pip install . dans le répertoire SDK téléchargé.

```bash
python3 -m pip install ./apps/accounts/clients/python
```

Placez jms_pam_config.py à côté de l’application. client_options contient des éléments d’identité : ne les ajoutez ni au dépôt ni aux journaux. Utilisez instance_id stable et unique par réplique. get_credential accepte exactement un sélecteur : account_id pour les comptes autorisés ou key pour une politique de rotation.

```python
from jms_pam import Client
from jms_pam_config import client_options, instance_id


with Client(instance_id=instance_id, **client_options) as client:
    credential = client.get_credential(account_id="<account-id>")
    username = credential.account.username
    secret = credential.account.secret
```

### Événements et application des identifiants

Traitez snapshot initial ou de reconnexion et credential.updated. L’exemple distingue subscription de alternating_rotation. Implémentez apply_credential pour valider une connexion réelle, remplacer le pool et libérer les anciennes connexions. Le code provisoire lève une exception pour empêcher de confirmer des identifiants non appliqués.

```python
from jms_pam import Client
from jms_pam_config import client_options, instance_id


def apply_credential(credential):
    raise NotImplementedError('Implémentez et vérifiez le changement des identifiants de l’application')


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

Pour la rotation alternée, validez une connexion réelle, remplacez le pool et libérez les anciennes connexions avant de confirmer exactement key, revision et account_id. Les abonnements aux changements d’identifiants ne nécessitent aucune confirmation. Un échec du contrôle de connexion doit empêcher la confirmation.

Le SDK tente automatiquement d’envoyer un accusé received avant de transmettre un événement métier. L’application n’a pas à le renvoyer. Il indique uniquement la lecture, pas l’application des identifiants, et ne remplace pas la confirmation. Réconciliez les snapshots initiaux et de reconnexion ; snapshot et pong ne nécessitent aucun accusé.

## Gestionnaires d’événements

Initialisez l’état local avant de démarrer l’écoute. Python et Node.js utilisent une sous-classe, Go EventHandlers et Java CredentialEventListener. Implémentez le changement réel de connexions de l’exemple. L’ancienne API reste disponible.

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

Les snapshot initiaux et de reconnexion et credential.updated récupèrent les identifiants selon le mode puis appellent le gestionnaire en série. La lecture utilise une file limitée à 128 événements, avec contre-pression si elle est pleine. Les échecs de récupération ou d’application sont retentés après 1–30 secondes de délai exponentiel, avec une nouvelle requête. Une mise à jour remplace les tentatives de la même cible ; snapshot réinitialise le périmètre, révocations et changements de configuration les annulent. Les gestionnaires doivent être idempotents. Observateurs et révocations ne sont pas retentés ; les commandes doivent être revendiquées. received signifie lu ; le SDK ne confirme jamais automatiquement une rotation. Un événement de révision antérieure n’annule pas la récupération en attente d’une révision plus récente.

`watch_events(stop_event=...)` / `start_events(stop_event=...)`; `stop_events()` / `close()`

watch_events attend l’arrêt ; start_events ne garantit pas la synchronisation initiale. Attendez que l’application soit prête. Un écouteur par client ; stop_events et close attendent le gestionnaire actif. Il peut arrêter son propre client. clone réinitialise la sous-classe.

### Identifiants les plus récents et panne du serveur

La récupération demande d’abord l’API. Une réussite remplace les identifiants retenus ; une version ancienne ne remplace pas une nouvelle et aucune expiration temporelle n’est appliquée. Seuls un délai dépassé, une panne réseau ou HTTP 5xx permettent de retourner la dernière valeur du même sélecteur avec un indicateur local. Sans valeur précédente, l’erreur est propagée. Le SDK conserve ces valeurs en mémoire jusqu’à mise à jour, révocation ou fermeture ; clone et redémarrage commencent vides. L’Agent les conserve dans son état local protégé. HTTP 401/403/404 ou client_upgrade_required effacent les valeurs du SDK et échouent ; une réponse réussie invalide échoue aussi. Une révocation supprime les valeurs concernées, snapshot celles hors autorisation. Un changement de configuration conserve les valeurs jusqu’au snapshot suivant. L’Agent applique les révocations explicites et les réductions du périmètre du snapshot avant la synchronisation HTTP, conserve ce périmètre et bloque les lectures locales concernées même en cas de panne ou après redémarrage. Une réponse credential_not_found (HTTP 400) efface également les valeurs conservées du SDK. Le pull direct par account_id exige toujours une réponse API en direct ; les snapshots push ne valident pas les valeurs pull en cache.

- `credential.from_local`
- `get_credential(key=..., allow_local_fallback=False)` / `get_credential(account_id=..., allow_local_fallback=False)`

Avec l’écoute gérée, snapshot et credential.updated récupèrent automatiquement les identifiants actuels, remplacent la valeur puis appellent le gestionnaire. Un échec conserve la valeur précédente et retente. L’Agent récupère aussi après notification et conserve les données pendant une panne du serveur. Utilisez les appels exigeant l’API ci-dessous pour actualiser ou changer les connexions ; une valeur retenue n’est pas une version nouvellement récupérée et ne confirme pas automatiquement une rotation.

Au repos, ping est envoyé toutes les 10 secondes ; environ 30 secondes sans message déclenchent une reconnexion avec délai exponentiel de 1–30 secondes et nouvelle signature. Le snapshot rétablit l’état actuel sans rejouer l’historique.



### Commandes d’application

Utilisez list_application_commands pour interroger les demandes en attente et execute_application_command(event, handler) pour réclamer leur exécution. Seule une demande acceptée lance le handler. Celui de changement vérifie révision et compte, applique et confirme ; celui de redémarrage relance l’application et vérifie son état. Signalez le succès après la fin des opérations. Un échec du signalement conserve l’exception d’origine du handler.

### Méthodes courantes

- `get_credential(key=...)` / `get_credential(account_id=...)`
- `confirm_credential(key=..., revision=..., account_id=...)`
- `watch_credential_events(stop_event=...)`
- `watch_events(stop_event=...)` / `start_events(stop_event=...)` / `stop_events()`
- `list_application_commands()`
- `report_application_command_result(command_id=..., status=...)`
- `execute_application_command(event, handler)`
- `sync_agent(credentials=..., delivered_credentials=...)`
- `clone()` / `close()`

Le client ferme sessions HTTP et flux d’événements avec with ou close. clone crée une session indépendante. Les erreurs HTTP, réseau, authentification et décodage lèvent PAMError avec code, status_code, detail et original_error. Réessayez les erreurs transitoires dans l’application, gérez les refus d’autorisation et excluez les identifiants des journaux.

Le nouveau code utilise des méthodes snake_case avec arguments nommés et attributs de dataclass. L’API historique credential.v1 reste disponible avec DeprecationWarning. Le SDK version 1 utilise le protocole de l’Agent ; sync_agent accepte KnownRevision pour les révisions conservées et distribuées.

<!-- sdk-doc:end -->
