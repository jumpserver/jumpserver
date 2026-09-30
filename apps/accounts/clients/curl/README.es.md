# cURL — Guía de uso

Este directorio contiene un script HTTP firmado para diagnosticar la API heredada account-secret. Para integrar aplicaciones, use el SDK de Python, Go, Java o Node.js.

## Requisitos

- Bash / cURL / OpenSSL / base64
- `demo.sh`

El script requiere Bash, cURL, OpenSSL y base64. Cambie ASSET y ACCOUNT y compruebe que la consulta firmada tenga exactamente la codificación enviada por cURL.

## Configuración y ejecución

Cree una aplicación en Administración de aplicaciones y autorice las cuentas de destino. Configure la URL, AK/SK de la aplicación y el ID de organización; sustituya todos los valores de ejemplo antes de ejecutar.

```bash
cd apps/accounts/clients/curl
export API_URL='https://jumpserver.example.com'
export API_KEY_ID='<app-id>'
export API_KEY_SECRET='<app-secret>'
export ORG_ID='<org-id>'

bash demo.sh
```

Los ejemplos consultan el activo ubuntu_docker y la cuenta root de forma predeterminada. Sustitúyalos por nombres autorizados reales. Ejecute los comandos desde la raíz del repositorio. La salida contiene secretos; no la envíe a los registros de la aplicación.

## Solicitud y respuesta

```http
GET /api/v1/accounts/integration-applications/account-secret/?asset=ubuntu_docker&account=root
```

```json
{"id":"<app-id>","secret":"<account-secret>"}
```

El campo id identifica la aplicación, no una revisión de cuenta. Un secreto null puede deberse al ajuste del servidor para visualizar secretos. Estos ejemplos no reciben eventos, no informan de revisiones aplicadas ni ejecutan comandos de aplicación.

## Solución de problemas

Para 401, compruebe AK/SK, organización, hora del equipo y URL firmada. Para 403, compruebe el estado de la aplicación y la autorización de cuentas. Para 400, compruebe los selectores y la codificación de la consulta. No registre secretos ni cabeceras Authorization. Los nombres deben corresponder a los recursos autorizados.

## Acceso a políticas de credenciales

Los detalles de firma y la tabla de protocolo siguientes son referencias de diagnóstico. Use métodos del SDK para las políticas de credenciales o Go jms-pam-agent mediante archivos JSON, EnvironmentFile o Unix Socket.

| HTTP | API | JSON / query |
| --- | --- | --- |
| GET | `/api/v1/accounts/credential-client/credential/` | `instance_id`, `key` / `account_id` |
| POST | `/api/v1/accounts/credential-client/confirm/` | `instance_id`, `key`, `revision`, `account_id` |
| GET | `/api/v1/accounts/credential-client/commands/` | `instance_id` |
| POST | `/api/v1/accounts/credential-client/command-result/` | `instance_id`, `command_id`, `status`, `error_code` |
| WebSocket | `/ws/accounts/credential-events/` | `instance_id` |

Firme con HMAC-SHA256 en el orden de cabeceras indicado. Incluya ruta y consulta codificadas en request-target, SHA-256 del cuerpo exacto en Digest, UUID único en X-JMS-Request-ID, fecha HTTP UTC, X-JMS-Client-Version, X-JMS-Protocol-Version: 1 y X-JMS-Config-Schema-Version: 0 para SDK. API y WebSocket usan AK/SK de la aplicación y un instance_id estable y único; renueve la firma en cada solicitud o reconexión.

```text
(request-target) accept date digest x-jms-request-id x-jms-org
x-jms-client-version x-jms-protocol-version x-jms-config-schema-version
```

En la rotación alternada, valide una conexión real, cambie el pool y cierre las conexiones anteriores antes de confirmar exactamente key, revision y account_id. Las suscripciones a cambios de credenciales no requieren confirmación. Un fallo de conexión debe impedir la confirmación.

Un recibo received solo indica que se leyó un evento. Envíe received con event_id en el mismo WebSocket antes de procesar eventos de negocio; snapshot y pong no requieren recibo. Concilie snapshot en cada conexión o reconexión, procese credential.updated y gestione revocaciones y cambios de configuración.
