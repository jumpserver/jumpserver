# JumpServer PAM Python SDK / Agent

Python 3.9+ fournit le SDK de politiques d’identifiants et l’Agent Linux. Le SDK utilise AK/SK de l’application ; l’Agent distribue les identifiants localement aux applications d’autres langages.

<!-- agent-doc:start -->

## Intégration de l’Agent Linux

Préparez Linux avec systemd, Python 3.9+ et l’utilisateur de l’application. Associez une politique et autorisez ses comptes ; la rotation alternée exige les deux. Dans l’assistant d’accès, sélectionnez Agent, configurez utilisateur, chemin et mode de distribution, puis téléchargez jms_pam_agent.json. Installez le répertoire SDK téléchargé et exécutez la commande pour le chemin par défaut, en remplaçant les valeurs d’exemple. Chaque réplique nécessite un identifiant stable et unique.

```bash
sudo python3 -m venv /opt/jumpserver-pam/venv
sudo /opt/jumpserver-pam/venv/bin/python -m pip install '<sdk-directory>'
sudo /opt/jumpserver-pam/venv/bin/jms-pam-agent install \
  --bootstrap ./jms_pam_agent.json --instance-id app-node-1
```

Les chemins par défaut figurent ci-dessous. Récupérez configuration-id dans la configuration initiale téléchargée et credential-key dans la politique. Le chemin configuré peut différer. Le fichier initial contient AK/SK : limitez son accès, supprimez la copie téléchargée après installation et protégez la configuration installée.

- JSON: `/opt/jumpserver-pam/credentials/<configuration-id>/<credential-key>.json`
- EnvironmentFile: `/opt/jumpserver-pam/credentials/<configuration-id>/<credential-key>.env`
- Unix Socket: `/run/jumpserver-pam/<configuration-id>/agent.sock`

Choisissez JSON pour les fichiers, EnvironmentFile pour un service systemd fixé à l’installation ou Unix Socket pour l’API locale. L’Agent enregistre les révisions distribuées après distribution ; l’application valide et applique avant d’enregistrer la révision appliquée. Le socket appartient à l’utilisateur configuré avec le mode 0600 ; effectuez les requêtes avec cet utilisateur.

```ini
[Service]
EnvironmentFile=-/opt/jumpserver-pam/credentials/<configuration-id>/<credential-key>.env
```

L’unité systemd doit référencer EnvironmentFile. Utilisez reload uniquement si l’application relit le fichier ; il n’injecte pas de nouvelles variables d’environnement dans un processus existant. L’installation fixe chemins, utilisateur, service et action autorisés ; leur extension nécessite une réinstallation.

### API locale et confirmation

```bash
curl --fail --silent --show-error \
  --unix-socket '/run/jumpserver-pam/<configuration-id>/agent.sock' \
  http://localhost/v1/health

curl --fail --silent --show-error \
  --unix-socket '/run/jumpserver-pam/<configuration-id>/agent.sock' \
  'http://localhost/v1/credentials/<credential-key>'
```

Pour la rotation alternée, validez une connexion réelle, remplacez le pool et libérez les anciennes connexions avant de confirmer exactement key, revision et account_id. Les abonnements aux changements d’identifiants ne nécessitent aucune confirmation. Un échec du contrôle de connexion doit empêcher la confirmation.

```bash
/opt/jumpserver-pam/venv/bin/jms-pam-agent confirm '<credential-key>' \
  --revision '<revision>' \
  --socket '/run/jumpserver-pam/<configuration-id>/agent.sock'
```

Seule la rotation alternée utilise confirm. La confirmation locale est enregistrée d’abord ; confirmed signifie que Core l’a acceptée et pending qu’elle sera réessayée. Ne confirmez pas simplement parce qu’un fichier a été écrit ou un service redémarré.

### Dépannage

```bash
sudo systemctl status 'jms-pam-agent-<configuration-id>.service' --no-pager
sudo journalctl -u 'jms-pam-agent-<configuration-id>.service' -n 100 --no-pager
sudo systemctl restart 'jms-pam-agent-<configuration-id>.service'
```

L’Agent réconcilie au démarrage, lors d’événements pertinents et toutes les 300 secondes. Les pannes réseau conservent le cache autorisé. Un refus d’identité ou d’autorisation bloque la lecture par socket ; une synchronisation signée réussie la rétablit. Les fichiers déjà écrits restent présents. SIGINT/SIGTERM ferment serveur, connexions et thread de lecture.

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
from jms_pam_config import client_options


with Client(instance_id="app-node-1", **client_options) as client:
    credential = client.get_credential(account_id="<account-id>")
    username = credential.account.username
    secret = credential.account.secret
```

### Événements et application des identifiants

Traitez snapshot initial ou de reconnexion et credential.updated. L’exemple distingue subscription de alternating_rotation. Implémentez apply_credential pour valider une connexion réelle, remplacer le pool et libérer les anciennes connexions. Le code provisoire lève une exception pour empêcher de confirmer des identifiants non appliqués.

```python
from jms_pam import Client
from jms_pam_config import client_options


def apply_credential(credential):
    raise NotImplementedError('Implémentez et vérifiez le changement des identifiants de l’application')


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

Pour la rotation alternée, validez une connexion réelle, remplacez le pool et libérez les anciennes connexions avant de confirmer exactement key, revision et account_id. Les abonnements aux changements d’identifiants ne nécessitent aucune confirmation. Un échec du contrôle de connexion doit empêcher la confirmation.

Le SDK tente automatiquement d’envoyer un accusé received avant de transmettre un événement métier. L’application n’a pas à le renvoyer. Il indique uniquement la lecture, pas l’application des identifiants, et ne remplace pas la confirmation. Réconciliez les snapshots initiaux et de reconnexion ; snapshot et pong ne nécessitent aucun accusé.

### Commandes d’application

Utilisez list_application_commands pour interroger les demandes en attente et execute_application_command(event, handler) pour réclamer leur exécution. Seule une demande acceptée lance le handler. Celui de changement vérifie révision et compte, applique et confirme ; celui de redémarrage relance l’application et vérifie son état. Signalez le succès après la fin des opérations. Un échec du signalement conserve l’exception d’origine du handler.

### Méthodes courantes

- `get_credential(key=...)` / `get_credential(account_id=...)`
- `confirm_credential(key=..., revision=..., account_id=...)`
- `watch_credential_events(stop_event=...)`
- `list_application_commands()`
- `report_application_command_result(command_id=..., status=...)`
- `execute_application_command(event, handler)`
- `sync_agent(credentials=..., delivered_credentials=...)`
- `clone()` / `close()`

Le client ferme sessions HTTP et flux d’événements avec with ou close. clone crée une session indépendante. Les erreurs HTTP, réseau, authentification et décodage lèvent PAMError avec code, status_code, detail et original_error. Réessayez les erreurs transitoires dans l’application, gérez les refus d’autorisation et excluez les identifiants des journaux.

Le nouveau code utilise des méthodes snake_case avec arguments nommés et attributs de dataclass. L’API historique credential.v1 reste disponible avec DeprecationWarning. Le SDK version 1 utilise le protocole de l’Agent ; sync_agent accepte KnownRevision pour les révisions en cache et distribuées.

<!-- sdk-doc:end -->
