# Wave 0 - P0 Checklist (Semanas 1-3)

Objetivo: fechar lacunas críticas de segurança, isolamento e operação para habilitar trilho de produção do StratoPulse.

## Segurança e sessão

- [x] SP-A03: Rate limiting por workspace e IP em auth — `commit c8befb6`
  - Backend: [backend/app/core/middleware.py](backend/app/core/middleware.py)
  - Evidência: 20 unit tests + 10 integration tests (`test_rate_limiter.py`, `test_rate_limit.py`)
  - Algoritmo: Lua sliding-window atômico, regras por IP+email (login), IP+tenant (API)

- [x] SP-A05: Hardening completo de headers em produção — `commit 27bd39c`
  - Backend: [backend/app/core/middleware.py](backend/app/core/middleware.py)
  - Evidência: 28 unit tests (`test_security_headers.py`), 10 headers OWASP
  - Headers: X-Content-Type-Options, X-Frame-Options, CSP, COOP, CORP, COEP, Permissions-Policy, HSTS, Referrer-Policy, X-Permitted-Cross-Domain-Policies

- [x] SP-A07: TLS 1.3 para datastores em produção — `commit fa6c1a4`
  - Backend config: [backend/app/core/config.py](backend/app/core/config.py)
  - Módulo TLS: [backend/app/core/tls.py](backend/app/core/tls.py)
  - Evidência: 24 unit tests (`test_tls.py`); `validate_production_security()` rejeita versão < TLS 1.3
  - Escopo: asyncpg (SSLContext), redis.asyncio (SSLContext), ClickHouse (ca_cert + server-side disableProtocols)

- [x] OIDC seguro (pré-condição de produção) — `commit 394285d`
  - Backend: [backend/app/domains/auth/service.py](backend/app/domains/auth/service.py)
  - Config: [backend/app/core/config.py](backend/app/core/config.py) — `oidc_jwks_cache_ttl_seconds`
  - Evidência: 20 unit tests (`test_oidc.py`) + 10 route-level tests (`test_oidc_azure.py`)
  - Fixes: JWKS RS256 verification, alg-confusion prevention (HS256 rejeitado), nonce no URL + validação, iss/aud/exp via jose.jwt.decode, cache JWKS com TTL 300s

## Multi-workspace

- [x] SP-MT01: Enforcement central de workspace — `commit 67e5aee`
  - Backend dependencies/policies: [backend/app/core/dependencies.py](backend/app/core/dependencies.py)
  - Evidência: 13 cenários cross-workspace (`test_cross_workspace_isolation.py`) com zero vazamento

- [x] SP-MT02: Lifecycle completo de workspace — `commit e5d0536`
  - Backend domains: [backend/app/domains](backend/app/domains)
  - Evidência: criar/ativar/desativar/arquivar/restaurar/purgar implementados e testados e2e

- [x] SP-MT03: Cota de membros por workspace — `commit ab4aab7`
  - Backend auth/members: [backend/app/domains/auth](backend/app/domains/auth)
  - Evidência: `create_user()` aplica quota; limite retorna 422 e é auditado
  - Extra: fluxo completo de convites (`domains/invites/`) com 5 endpoints

- [x] SP-MT04: Workspace inativo bloqueia acesso — `commit e5d0536`
  - Backend dependencies: [backend/app/core/dependencies.py](backend/app/core/dependencies.py)
  - Evidência: qualquer endpoint protegido retorna 403 para workspace inativo/arquivado

- [x] SP-MT05: platform_admin global — `commit a221eb4`
  - Backend roles/models: [backend/app/domains/auth/models.py](backend/app/domains/auth/models.py)
  - Evidência: 11 cenários (`test_platform_admin.py`); acesso global com auditoria
  - Extra: domínio `admin/` com 6 endpoints de gestão global de orgs

## API e frontend críticos

- [x] SP-AP01: Paginação em todas as listas — `commit e5d0536`
  - Backend routers: [backend/app/api/v1](backend/app/api/v1)
  - Evidência: contrato `Page[T]` com `page/page_size/total` em todas as listagens

- [x] SP-FE06: /app/platform/workspaces — `commit 8307faa`
  - Frontend: [frontend/src/pages/Platform/WorkspacesPage.tsx](frontend/src/pages/Platform/WorkspacesPage.tsx)
  - API client: [frontend/src/api/admin.ts](frontend/src/api/admin.ts)
  - Evidência: tabela paginada de orgs com ações de lifecycle (suspender/restaurar/arquivar); expand inline para listar usuários; guard de rota (platform_admin only); item no Sidebar condicional

- [x] SP-FE08: /forgot-password e /reset-password completos — `commit 8307faa`
  - Frontend pages: [frontend/src/pages/ForgotPassword/ForgotPasswordPage.tsx](frontend/src/pages/ForgotPassword/ForgotPasswordPage.tsx), [frontend/src/pages/ResetPassword/ResetPasswordPage.tsx](frontend/src/pages/ResetPassword/ResetPasswordPage.tsx)
  - Backend auth routes: [backend/app/domains/auth/router.py](backend/app/domains/auth/router.py) — POST /auth/forgot-password, POST /auth/reset-password
  - Evidência: fluxo e2e ponta a ponta; token via AuthChallenge (1h TTL); prevenção de enumeração de e-mail; link 'Forgot password?' na tela de login; token retornado no response para teste sem SMTP (Wave 1: integrar serviço de e-mail)

## Operação

- [x] SP-OP10: Backup/restore com RTO/RPO medidos — `commit 83bbbc5`
  - Scripts e operação: [scripts/backup.sh](scripts/backup.sh), [scripts/restore.sh](scripts/restore.sh), [scripts/rto_rpo_test.sh](scripts/rto_rpo_test.sh)
  - Evidência: drill automatizado com targets configuráveis (RTO ≤ 300s, RPO ≤ 3600s); relatórios JSON por execução
  - Datastores: PostgreSQL (pg_dump custom), ClickHouse (Native binary), Redis (RDB snapshot)

## Definição de pronto da Wave 0

- [x] Nenhum bloqueador crítico de autenticação aberto
- [x] Suíte de isolamento cross-workspace com zero vazamentos
- [x] Evidência de backup/restore documentada
- [x] Todos os PRs da wave mapeados para requisito SP-*
- [x] OIDC seguro implementado e unit-tested (staging na Wave 1)
- [x] SP-FE06 e SP-FE08 entregues
