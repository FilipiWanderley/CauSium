# E2E Critical Flows (Release Hardening)

Data: 2026-04-11

## Fluxos obrigatorios

1. Auth + sessão
- Login com credencial valida.
- Refresh de token/cookie.
- Logout invalida sessão.

2. MFA TOTP
- Setup + verify + enable.
- Login exigindo código MFA.
- Disable/reset admin auditado.

3. Notifications
- Criação de evento crítico.
- Listagem de unread via contrato novo.
- Mark all read.

4. Economics
- Budget GET/PUT.
- Export assíncrono: create -> status -> download.
- Detailed costs com filtros e paginação.

5. Platform Admin
- Workspaces lifecycle (suspend/restore/archive).
- Sync status.
- Dashboard SLI/SLO + alertas.

## Evidência minima por fluxo

- Request/response principal (status code + payload-chave).
- Log correlacionável por trace_id.
- Resultado final esperado vs obtido.
