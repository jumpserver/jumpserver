# Instrucciones

## 1. Introducción

Esta API recupera las contraseñas de las cuentas de activos de PAM, admite solicitudes RESTful y devuelve los datos en formato JSON.

## 2. Requisitos del entorno

- `Java 11+`
- `HttpClient`

## 3. Uso

**Método de solicitud**: `GET api/v1/accounts/integration-applications/account-secret/`

**Parámetros de solicitud**

| Nombre del parámetro | Tipo | Obligatorio | Descripción |
|----------------------|------|-------------|-------------|
| asset                | str  | Sí          | Nombre del activo |
| account              | str  | Sí          | Nombre de la cuenta |

**Ejemplo de respuesta**:
```json
{
    "id": "72b0b0aa-ad82-4182-a631-ae4865e8ae0e",
    "secret": "123456"
}
```

## Preguntas frecuentes (FAQ)

P: ¿Cómo obtengo una clave de API?

R: Cree una aplicación en PAM - Gestión de aplicaciones para generar un KEY_ID y un KEY_SECRET.

## Historial de cambios

| Versión | Cambios         | Fecha      |
|---------|-----------------|------------|
| 1.0.0   | Versión inicial | 2025-02-11 |
