# Instruções

## 1. Introdução

Esta API recupera senhas de contas de ativos do PAM, aceita solicitações RESTful e retorna dados no formato JSON.

## 2. Requisitos do ambiente

- `Node.js 16+`
- `axios ^1.7.9`
- `moment ^2.30.1`

## 3. Uso

**Método da requisição**: `GET api/v1/accounts/integration-applications/account-secret/`

**Parâmetros da requisição**

| Nome do parâmetro | Tipo | Obrigatório | Descrição |
|-------------------|------|-------------|-----------|
| asset             | str  | Sim         | Nome do ativo |
| account           | str  | Sim         | Nome da conta |

**Exemplo de resposta**:
```json
{
    "id": "72b0b0aa-ad82-4182-a631-ae4865e8ae0e",
    "secret": "123456"
}
```

## Perguntas frequentes (FAQ)

P: Como obtenho uma chave de API?

R: Crie uma aplicação em PAM - Gerenciamento de aplicações para gerar um KEY_ID e um KEY_SECRET.

## Histórico de alterações

| Versão | Alterações     | Data       |
|--------|---------------|------------|
| 1.0.0  | Versão inicial | 2025-02-11 |
