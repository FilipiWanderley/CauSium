# Wave 0 - P0 Checklist (Semanas 1-3)

Objetivo: fechar lacunas críticas de segurança, isolamento e operação para habilitar trilho de produção do StratoPulse.

## Segurança e sessão

- [ ] SP-A03: Rate limiting por workspace e IP em auth
  - Backend: [backend/app/core/middleware.py](backend/app/core/middleware.py)
  - Evidência: testes de bloqueio por IP e por workspace

- [ ] SP-A05: Hardening completo de headers em produção
  - Backend: [backend/app/core/middleware.py](backend/app/core/middleware.py)
  - Evidência: validação OWASP headers checker em staging

- [ ] SP-A07: TLS 1.3 para datastores em produção
  - Backend config: [backend/app/core/config.py](backend/app/core/config.py)
  - Infra local: [docker-compose.yml](docker-compose.yml)
  - Evidência: teste de conexão sem TLS rejeitada

- [ ] OIDC seguro (pré-condição de produção)
  - Backend: [backend/app/domains/auth/service.py](backend/app/domains/auth/service.py)
  - Evidência: validação jwks, iss, aud, nonce e testes negativos

## Multi-workspace

- [ ] SP-MT01: Enforcement central de workspace
  - Backend dependencies/policies: [backend/app/core/dependencies.py](backend/app/core/dependencies.py)
  - Evidência: suíte cross-workspace com zero vazamento

- [ ] SP-MT02: Lifecycle completo de workspace
  - Backend domains: [backend/app/domains](backend/app/domains)
  - Evidência: criar/ativar/desativar/arquivar/restaurar/purgar em e2e

- [ ] SP-MT03: Cota de membros por workspace
  - Backend auth/members: [backend/app/domains/auth](backend/app/domains/auth)
  - Evidência: limite retorna 422 e é auditado

- [ ] SP-MT04: Workspace inativo bloqueia acesso
  - Backend dependencies: [backend/app/core/dependencies.py](backend/app/core/dependencies.py)
  - Evidência: qualquer endpoint protegido retorna 403

- [ ] SP-MT05: platform_admin global
  - Backend roles/models: [backend/app/domains/auth/models.py](backend/app/domains/auth/models.py)
  - Evidência: acesso global com auditoria

## API e frontend críticos

- [ ] SP-AP01: Paginação em todas as listas
  - Backend routers: [backend/app/api/v1](backend/app/api/v1)
  - Evidência: contrato page/page_size/total em todas as listagens

- [ ] SP-FE06: /app/platform/workspaces
  - Frontend pages: [frontend/src/pages](frontend/src/pages)
  - Evidência: CRUD de workspace e ações de status

- [ ] SP-FE08: /forgot-password e /reset-password completos
  - Frontend auth pages: [frontend/src/pages](frontend/src/pages)
  - Backend auth routes: [backend/app/domains/auth/router.py](backend/app/domains/auth/router.py)
  - Evidência: fluxo e2e ponta a ponta

## Operação

- [ ] SP-OP10: Backup/restore com RTO/RPO medidos
  - Scripts e operação: [scripts](scripts)
  - Evidência: runbook e relatório de restore em staging

## Definição de pronto da Wave 0

- Nenhum bloqueador crítico de autenticação aberto
- Suíte de isolamento cross-workspace com zero vazamentos
- Evidência de backup/restore documentada
- Todos os PRs da wave mapeados para requisito SP-*
