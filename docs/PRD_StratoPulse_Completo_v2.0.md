# StratoPulse — PRD de Implementação Completa v2.0
## Cloud Efficiency Intelligence Platform

*Gap Analysis Real (baseline auditado em 07/04/2026 + atualização incremental de código validada em 09/04/2026) + Roadmap de Fechamento Total*

Versão 2.0 | Abril 2026 | CONFIDENCIAL

Atualização incremental (09/04/2026):
- Delta validado nos commits de 08/04/2026: `23a1242`, `8a0f34a`, `00fa262`.
- Implementações confirmadas no código: módulos `notifications`, `gov`, `green` (backend + frontend) e rotas `/app/economics/costs`, `/app/economics/usage`, `/app/economics/skus`, `/app/economics/reports`.
- Este update reclassifica status de capacidade e rotas. Itens de backlog estratégico permanecem válidos quando marcados como "parcial".

---

## Índice

1. [Objetivo e Escopo](#1-objetivo-e-escopo)
2. [Visão e Posicionamento](#2-visão-e-posicionamento)
3. [Estado Real do Código — Auditoria Técnica](#3-estado-real-do-código--auditoria-técnica)
4. [Gap Analysis Detalhado por Bloco](#4-gap-analysis-detalhado-por-bloco)
5. [Backlog Completo de Requisitos](#5-backlog-completo-de-requisitos)
6. [Modelo de Dados — Entidades a Implementar/Migrar](#6-modelo-de-dados--entidades-a-implementarmigrar)
7. [Arquitetura de APIs — Catálogo Completo](#7-arquitetura-de-apis--catálogo-completo)
8. [Frontend — Estrutura de Rotas e Páginas](#8-frontend--estrutura-de-rotas-e-páginas)
9. [Workers e Event Processing](#9-workers-e-event-processing)
10. [Infraestrutura e Deployment](#10-infraestrutura-e-deployment)
11. [Plano de Implementação — Waves](#11-plano-de-implementação--waves)
12. [Requisitos Não Funcionais](#12-requisitos-não-funcionais)
13. [Glossário de Nomenclatura](#13-glossário-de-nomenclatura)
14. [Critérios de Go-Live](#14-critérios-de-go-live)

---

## 1. Objetivo e Escopo

Este PRD é a **fonte única de verdade** para o desenvolvimento completo do StratoPulse. Ele foi produzido a partir de:

1. Auditoria técnica completa do repositório atual (código, modelos, rotas, workers, testes, migrações)
2. Cruzamento linha a linha com o PRD estratégico v1.0
3. Identificação precisa do que está implementado, parcial ou ausente

O documento cobre tudo que o StratoPulse precisa para operar com paridade funcional de um produto FinOps enterprise maduro, mantendo sua arquitetura e nomenclatura 100% originais.

### O que já existe no código hoje

O repositório tem uma base técnica sólida. Não é um projeto vazio — é uma plataforma funcional com lacunas específicas:

**Implementado e funcionando:**
- Autenticação passkey-first (WebAuthn/FIDO2) com Azure OIDC
- Motor de políticas em runtime (PBAC/ABAC via `core/policy.py`)
- Ingestão de dados Azure com conector real
- Geração de oportunidades de otimização com scoring composto
- Sistema de experimentos com state machine e dupla aprovação
- Audit chain imutável com hash SHA-256 encadeado e checkpoints HMAC
- Risk budgets por domínio/ambiente
- Dashboard executivo com KPIs e scorecard por time
- Workers assíncronos (ingestion, scoring, audit checkpoint)
- Módulo de orçamento financeiro por workspace (`/economics/budget`)
- Módulos de Notifications, PulseGov e PulseGreen com rotas e páginas dedicadas
- Rotas PulseEconomics expandidas: costs, usage, skus e reports

**Não existe ou é insuficiente:**
- Sistema completo de workspaces (lifecycle, cotas, platform_admin)
- Notificações avançadas (preferências por membro e dispatch SMTP/Slack)
- PulseGov avançado (inventário persistente e governança com políticas automáticas)
- PulseGreen avançado (coleta de emissões por provider e consolidação histórica)
- Análise de SKUs e relatórios no backend dedicado (modelo/endpoint específicos)
- Conectores AWS/GCP reais
- Infraestrutura cloud (ainda em Docker Compose local)
- Observabilidade com OpenTelemetry
- CI/CD com gates de segurança

---

## 2. Visão e Posicionamento

### Tese de Produto

O StratoPulse é uma plataforma de inteligência econômica de cloud que combina visibilidade FinOps operacional com decisões verificáveis baseadas em causalidade, governança por risk budgets e execução via experimentos controlados.

**Três camadas de valor:**

| Camada | Descrição | Módulos |
|--------|-----------|---------|
| Paridade | Tudo que um FinOps enterprise maduro oferece | PulseEconomics, PulseGov, PulseGreen, alertas, multi-tenant |
| Inteligência | Atribuição causal, otimização multiobjetivo, ranking adaptativo | SCA, ARI, MORCO, simulador |
| Execução | Experimentos canário com guardrails, rollback, evidência imutável | PulseLab, StratoAudit |

### Nomenclatura do Produto

Todo o código, APIs, documentação e comunicações usam exclusivamente esta nomenclatura:

| Módulo | Nome Oficial |
|--------|-------------|
| Análise financeira | PulseEconomics |
| Otimização inteligente | PulseIntel |
| Governança | PulseGov |
| Sustentabilidade | PulseGreen |
| Experimentos | PulseLab |
| Conectores | PulseLink |
| Observabilidade e infra | PulseOps |
| Auditoria imutável | StratoAudit |
| Event log de domínio | PulseStream |
| GraphQL gateway | StratoGraph |
| mTLS interno | StratoMesh |
| Engine causal | SCA (Stratum Causal Attribution) |
| Ranking adaptativo | ARI (Adaptive Recommendation Index) |

### ICP e Personas

| Persona | Papel | Módulos principais |
|---------|-------|-------------------|
| Exec Sponsor | VP Engineering / CFO Tech | PulseEconomics, PulseLab (resultados), PulseGreen |
| FinOps Lead | Head of FinOps / FP&A Tech | PulseEconomics, PulseIntel, PulseGov, relatórios |
| Platform Engineer | Staff SRE / Platform | PulseLab, PulseLink, PulseOps, PulseIntel |
| Security Engineer | Sec / Compliance | StratoAudit, PBAC, PulseGov, compliance artifacts |
| Workspace Admin | Admin do cliente | Configuração, usuários, credenciais, orçamento |

---

## 3. Estado Real do Código — Auditoria Técnica

Esta seção documenta o que existe hoje no repositório com evidências concretas.

### 3.1 Stack Tecnológica Atual

| Camada | Tecnologia | Versão/Detalhes |
|--------|-----------|-----------------|
| Backend | FastAPI + Python | Async, Pydantic v2 |
| Banco relacional | PostgreSQL | Via SQLAlchemy async |
| Banco analítico | ClickHouse | Tabelas `cost_facts`, `event_facts` |
| Cache/Queue | Redis | Filas de ingestão e scoring |
| Frontend | React 18 + TypeScript | Vite + Tailwind CSS |
| Containerização | Docker Compose | 5 serviços: postgres, redis, clickhouse, backend, frontend |
| Logging | Structlog | Logs estruturados em JSON |

### 3.2 Domínios Implementados

#### Domínio: `auth`
**Status: ✅ Base sólida, lacunas em operações administrativas**

Modelos presentes:
- `User`: id, org_id, email, full_name, hashed_password, role, is_active, passkey_enabled
- `Organization`: id, name, slug, plan, is_active, passwordless_only
- `AuthChallenge`: challenge WebAuthn com TTL e consumed_at
- `PasskeyCredential`: credential_id, public_key_jwk (CBOR), sign_count, transports

Roles implementados: `ADMIN`, `ENGINEER`, `FINOPS`, `EXECUTIVE`, `VIEWER`

Endpoints existentes (16 rotas):
- POST /auth/register (cria org + admin)
- POST /auth/login, /refresh, /logout
- GET /auth/me
- POST /auth/users, GET /auth/users
- PATCH /auth/passwordless-policy
- POST /auth/passkey/register/options, /register/verify
- POST /auth/passkey/login/options, /login/verify
- GET /auth/passkeys, DELETE /auth/passkeys/{id}
- GET /auth/oidc/azure/start, /oidc/azure/callback

**Ausente:**
- MFA TOTP (setup, verify, enable, disable, reset)
- Forçar troca de senha
- Reset de senha por admin
- Convite de membro por email
- Soft-delete de membro
- `platform_admin` global (sem workspace)
- Rate limiting específico por org_id (existe por IP)

#### Domínio: `cloud_accounts` (mapeado como PulseLink)
**Status: 🔶 Azure funcional, AWS/GCP inexistentes**

Modelos: `CloudAccount` (org_id, provider, credentials_encrypted Fernet, status), `ConnectorHealth`

Endpoints existentes:
- CRUD de cloud accounts
- Health check
- Trigger de sync (enfileira na Redis)

Connector implementado: `AzureConnector` com `fetch_costs()` e `fetch_events()`

**Ausente:**
- Validação de escopos antes de persistir credencial
- Conector Azure Blob Storage
- Conector Azure Carbon API
- Conector AWS real (OIDC federation)
- Conector GCP real (workload identity)
- Schema Registry para contratos de evento

#### Domínio: `cloud_ledger` (mapeado como PulseEconomics backend)
**Status: 🔶 Base analítica presente, análises avançadas ausentes**

Storage ClickHouse: `cost_facts`, `event_facts`

Endpoints existentes:
- POST /ledger/ingest
- GET /ledger/dashboard, /costs/trend, /costs/services, /costs/teams

**Ausente:**
- `WorkspaceBudget` (orçamento financeiro — **existe apenas RiskBudget**)
- Custo detalhado por grupo de recursos com filtros combinados e paginação
- Análise de SKUs (`SkuObservation`)
- Métricas de uso por recurso (`UsageObservation`)
- Forecast probabilístico P50/P90
- Exportação CSV/Excel
- Painel de savings previsto vs realizado com intervalo de confiança

#### Domínio: `decision_engine` (mapeado como PulseIntel backend)
**Status: 🔶 Scoring heurístico presente, engine causal ausente**

Modelo: `OptimizationOpportunity` com composite_score (financial×0.45 + risk×0.25 + effort×0.20 + criticality×0.10)

Endpoints existentes:
- GET /opportunities (filtros status, category, owner_team)
- GET /opportunities/summary
- POST /opportunities (manual)
- GET /opportunities/{id}
- PATCH /opportunities/{id}/status
- POST /opportunities/generate/{account_id}

**Ausente:**
- `ProviderRecommendation` (importação do Azure Advisor real)
- `SyncRecord` (estado de sincronização)
- SCA (Stratum Causal Attribution) dedicada
- ARI (Adaptive Recommendation Index) com feedback loop
- Worker de sync periódico de recomendações do provider

#### Domínio: `experiments` (mapeado como PulseLab)
**Status: ✅ State machine completa, simulador limitado**

Modelos: `OptimizationExperiment`, `ExperimentRun`, `ExperimentApproval`

State machine: DRAFT→HYPOTHESIS→SIMULATING→APPROVED→RUNNING→MEASURING→CONCLUDED

Endpoint de policy check em runtime: `authorize_experiment_action()` em `core/policy.py`

**Ausente:**
- Simulador avançado com restrições de SLO e risco quantificado
- Execução canário real (integração com cloud provider)
- Guardrails automáticos com rollback baseado em thresholds de SLO
- `CausalTrace` dedicado por recomendação

#### Domínio: `risk_budgets`
**Status: ✅ CRUD completo**

Modelos: `RiskBudget` (blast_radius_pct, cost_variance_pct, error_rate, change_frequency)

Endpoints: CRUD completo

#### Domínio: `change_events`
**Status: ✅ Presente, causal attribution manual**

Modelo: `ChangeEvent` (event_type: DEPLOY/CONFIG_CHANGE/SCALING/INCIDENT/COST_ANOMALY/POLICY_CHANGE, causal_confidence)

PATCH /change-events/{id}/causal para linkar custo

**Ausente:** Engine causal automática

#### Domínio: `audit_chain` (StratoAudit)
**Status: ✅ Implementado e diferenciado**

Hash chain: SHA-256 encadeado com genesis event

Checkpoints: HMAC-SHA256 com snapshot_signature

Eventos auditados: auth.*, experiment.*, policy.decision.*

**Presente e funcionando:**
- verify_chain(): reconstrói todos os hashes, valida integridade
- create_checkpoint(): snapshot com HMAC
- Export JSONL
- cleanup por retention

**Ausente do StratoAudit:**
- Cobertura de eventos de reset de senha, MFA, operações admin
- Compliance report exportável em PDF/JSON assinado (ComplianceArtifact)

#### Domínio: `workflow` (Initiatives)
**Status: ✅ Kanban funcional**

Modelos: `Initiative`, `InitiativeComment`

State machine: BACKLOG→PLANNED→IN_PROGRESS→REVIEW→DONE

Kanban board endpoint com 6 colunas

**Ausente:**
- Integração real Jira/Linear (external_ref existe mas sem webhook)
- Integração GitHub (correlação deploy/custo)
- Integração Slack

#### Domínio: `executive`
**Status: 🔶 KPIs presentes, forecast rudimentar**

`get_summary()`: current_month_cost, mom_change_pct, ytd_cost, realized/potential savings, forecast_next_month (linear 3 meses + 5%)

`get_scorecard()`: efficiency score por time

**Ausente:**
- Forecast probabilístico com intervalo de confiança (P50/P90)
- Conteúdo por persona (UX cada persona)

#### Domínio: `policy`
**Status: ✅ PBAC/ABAC em runtime**

`PolicyBundle` com rules JSONB

`PolicyDecisionEvidence` com audit trail de cada decisão

`authorize_experiment_action()` com decision tree de 10 regras

### 3.3 Workers

| Worker | Status | Detalhes |
|--------|--------|---------|
| ingestion_worker | 🔶 Funcional, sem DLQ | Redis queue `ingestion:queue`, distributed lock por account_id |
| scoring_worker | 🔶 Funcional, sem isolamento por org | Redis queue `scoring:queue`, gera opportunities |
| audit_checkpoint_worker | ✅ Funcional | Intervalo configurável, retention configurável |

**Ausente:**
- DLQ para mensagens com falha repetida
- Workers resilientes por workspace (falha de uma org não afeta outras)
- Worker de sync de recomendações do provider
- Worker de sync de inventário de recursos
- Worker de emissões de carbono
- Worker de alertas

### 3.4 Frontend — Páginas Existentes

| Rota atual | Status | Mapeamento PRD |
|-----------|--------|---------------|
| /login | ✅ | /login |
| /dashboard | 🔶 | /app/economics |
| /opportunities | 🔶 | /app/intel |
| /initiatives | 🔶 | /app (Kanban) |
| /experiments | 🔶 | /app/lab |
| /risk-budgets | ✅ | /app/settings ou /app/gov |
| /change-events | ✅ | Integrado ao PulseIntel |
| /executive | 🔶 | Sub-view do /app/economics |
| /settings | 🔶 | /app/settings/* |

**Implementado (Wave 0):**
- /forgot-password ✅ (commit 8307faa)
- /reset-password ✅ (commit 8307faa)
- /platform/workspaces ✅ (commit 8307faa; movida para /app/platform/workspaces ✅ SP-FE01)

**Ainda ausente:**
- / (landing pública)

### 3.5 Segurança — Estado Real

| Controle | Status | Evidência |
|---------|--------|-----------|
| WebAuthn passkey | ✅ | `verify_passkey_login()` com ECDSA verificação |
| Azure OIDC federado | ✅ | `/auth/oidc/azure/start` + callback |
| JWT access/refresh | ✅ | HS256, TTL 60min/7dias |
| bcrypt password | ✅ | `create_user()` |
| Fernet encryption (credentials) | ✅ | `get_azure_credentials()` |
| PBAC/ABAC runtime | ✅ | `core/policy.py` com 10 regras |
| Dual approval | ✅ | `experiment_approvals` exige 2 aprovadores distintos |
| Rate limiting IP | 🔶 | 20 req/min auth, 300 req/min global, middleware |
| Rate limiting por tenant | ❌ | Não implementado por org_id |
| Security headers | 🔶 | X-Frame-Options, CSP, HSTS presentes mas sem enforcement CI |
| CORS | 🔶 | Configurável via CORS_ORIGINS, não restritivo por ambiente |
| Token httpOnly cookie | 🔶 | Logout limpa cookie, mas autenticação principal usa localStorage |
| Validação origin/referer | ❌ | Não implementado |
| MFA TOTP | ❌ | Não implementado |
| TLS datastores produção | 🔶 | Flags presentes (SSL mode, Rediss), não enforced em CI |
| mTLS interno (StratoMesh) | ❌ | Não implementado |
| Rotação automática segredos | ❌ | Não implementado |
| SAST/SCA no CI | ❌ | Sem CI configurado |

---

## 4. Gap Analysis Detalhado por Bloco

Legenda: ✅ Implementado | 🔶 Parcial | ❌ Não iniciado

### 4.1 Autenticação e Sessão

| Capacidade | Status Real | Evidência no Código | Gap |
|-----------|-------------|---------------------|-----|
| Login com passkey/WebAuthn | ✅ | `auth/service.py:verify_passkey_login()` | — |
| OIDC federado (Azure OIDC) | ✅ | `/auth/oidc/azure/callback` | Okta/Auth0 não suportados ainda |
| Refresh token rotativo | ✅ | `auth/service.py:refresh_tokens()` | — |
| MFA TOTP setup, verify, enable, disable | ❌ | Não existe | Implementar totalmente |
| Reset de MFA por admin | ❌ | Não existe | Dependência do MFA TOTP |
| Token em cookie httpOnly (não localStorage) | ✅ commit 745d828 | `_set_auth_cookies()` em todos os endpoints; `withCredentials: true` no frontend; sem localStorage | — |
| Forçar troca de senha configurável | ✅ SP-A01 | `must_change_password` em User; AppLayout bloqueia acesso; `POST /auth/change-password`; auditado | — |
| Rate limiting por workspace (org) | ❌ | Apenas por IP | Adicionar granularidade por org_id |
| Validação de origin/referer no login | ✅ SP-A04 | `_check_origin()` no middleware; rejeita origem desconhecida com 403; ausência de Origin tolerada fora de produção | — |
| Headers HTTP completos em produção | 🔶 | Implementados no middleware, sem validação CI | Gate automático no CI |
| CORS restritivo por ambiente | 🔶 | `CORS_ORIGINS` configurável | Separar dev/staging/prod |
| Logout revoga refresh e limpa cookies | ✅ | `/auth/logout` | — |
| PBAC + ABAC runtime | ✅ | `core/policy.py` | — |
| JIT elevation com dupla aprovação | ✅ | `experiment_approvals` | — |

### 4.2 Multi-tenant e Workspaces

> **Nota de nomenclatura:** O código atual usa `organization`/`org_id`. O PRD usa `workspace`. A migração de nomenclatura deve ser feita progressivamente sem quebrar o banco.

| Capacidade | Status Real | Gap |
|-----------|-------------|-----|
| Scoping por workspace em todas as queries | ✅ commit 67e5aee | Suite de isolamento cross-workspace com 0 vazamentos |
| Bloqueio cross-workspace por default | ✅ commit 67e5aee | Enforcement central em get_current_user + dependency |
| Lifecycle completo: criar, ativar, desativar, arquivar, purgar, restaurar | ✅ commit e5d0536 | Transitions ACTIVE↔SUSPENDED↔ARCHIVED; auditado |
| Cota de membros por workspace | ✅ commit ab4aab7 | Quota configurável; POST /auth/users retorna 422 quando atingido |
| Workspace inativo bloqueia acesso imediatamente | ✅ commit e5d0536 | get_current_user retorna 403 para workspace SUSPENDED/ARCHIVED |
| platform_admin global sem workspace | ✅ commit a221eb4 | role platform_admin; require_platform_admin dependency; acesso total auditado |
| Chaves de criptografia por workspace enterprise | ❌ | Fernet key é global (env var); pendente SP-MT06 / SP-SM02 |
| Data residency por região contratual | ❌ | Sem suporte; Wave 4 |

### 4.3 Perfis e Membros

> **Nota de nomenclatura:** Roles atuais (ADMIN/ENGINEER/FINOPS/EXECUTIVE/VIEWER) mapeiam para (workspace_admin/engineer/analyst/viewer). Adicionar `platform_admin` sem workspace.

| Capacidade | Status Real | Gap |
|-----------|-------------|-----|
| CRUD de membros operacional | 🔶 commit ab4aab7 | create_user + list_users + invites domain (5 endpoints); falta DELETE /users, PATCH /users |
| Reset de senha self-service | ✅ commit 8307faa | POST /auth/forgot-password + /auth/reset-password; token AuthChallenge TTL 1h |
| Reset de senha por workspace_admin (para outro usuário) | ⬜ | SP-U01: admin gera token para membro específico; pendente |
| Reset de MFA por workspace_admin | ❌ | SP-U02: dependência do MFA TOTP (SP-A06) |
| Regra: admin não reseta outro admin | ❌ | SP-U03; implementar junto com SP-U01 |
| Convite por email (SMTP + link ativação) | 🔶 commit ab4aab7 | invites domain com 5 endpoints; sem SMTP (SP-AP03 pendente) |
| Soft-delete com auditoria | ❌ | SP-U05 |

### 4.4 PulseEconomics — Dashboard e Análise Financeira

| Capacidade | Status Real | Gap |
|-----------|-------------|-----|
| Dashboard com KPIs e tendências | 🔶 | `cloud_ledger/service.py:get_dashboard_metrics()` funcional |
| Orçamento financeiro por workspace (WorkspaceBudget) | ✅ | `economics/router.py` com GET/PUT `/economics/budget` e consumo projetado |
| Tendência de custo por serviço | ✅ | `get_top_services()`, `get_cost_trend()` |
| Custo detalhado com filtros combinados e paginação | 🔶 | Filtros básicos sem paginação |
| Análise de SKUs (SkuObservation) | 🔶 | Frontend em produção consumindo agregação de serviços (SKU dedicado ainda pendente) |
| Métricas de uso por recurso (UsageObservation) | 🔶 | `event_facts` presente, sem model dedicado |
| Exportação CSV/Excel | 🔶 | Export CSV no frontend de reports (backend assíncrono dedicado ainda pendente) |
| Forecast probabilístico P50/P90 | 🔶 | Forecast linear básico em `executive/service.py` |
| Savings previsto vs realizado com confiança | 🔶 | `total_potential_savings_usd` vs `total_realized_savings_usd` presentes, sem intervalo |

### 4.5 Alertas e Notificações

| Capacidade | Status Real | Gap |
|-----------|-------------|-----|
| ActivityEvent (log de atividade do provider) | ❌ | `change_events` é diferente — cobre mudanças operacionais, não atividade de provider |
| AlertRecord por categoria | ✅ | Modelo/migração `alert_records` + API `/notifications` |
| NotificationPreference por membro | ❌ | Não existe |
| Endpoint GET /notifications/new (polling) | 🔶 | Substituído por `GET /notifications/unread-count` + listagem paginada |
| PATCH notificação lida/arquivada | ✅ | `PATCH /notifications/{id}` e `PATCH /notifications/mark-all-read` |
| Envio por email (SMTP) | ❌ | Não existe |
| Envio por Slack (webhook por workspace) | ❌ | Não existe |

### 4.6 PulseIntel — Recomendações e Otimização

| Capacidade | Status Real | Gap |
|-----------|-------------|-----|
| Importação de recomendações do provider (Azure Advisor) | 🔶 | Heurísticas locais geram opportunities, sem importação real do Advisor |
| ProviderRecommendation model dedicado | ❌ | Não existe separado do OptimizationOpportunity |
| ARI (ranking adaptativo com feedback) | ❌ | Scoring composto estático, sem feedback loop |
| SCA (engine causal dedicada) | 🔶 | `causal_confidence` em change_events, sem engine automática |
| CausalTrace por recomendação | ❌ | Não existe |
| PulseLab Simulator com restrições SLO | 🔶 | Estado SIMULATING existe, sem motor de simulação quantitativa |
| Execução canário com guardrails e rollback automático | 🔶 | ExperimentRun tem CANARY type, sem integração real com provider |

### 4.7 PulseGov — Governança

> MVP implementado (summary, unowned costs e label compliance). Itens avançados ainda pendentes.

| Capacidade | Status Real |
|-----------|-------------|
| ResourceInventory (inventário de recursos) | 🔶 |
| Compliance de labels obrigatórias | 🔶 |
| Configuração de labels por workspace | ❌ |
| Recursos sem owner com custo associado | ✅ |
| TopologyMap (grafo de dependências) | ❌ |
| Blast radius como restrição automática | ❌ |

### 4.8 PulseGreen — Sustentabilidade

> MVP implementado (summary, série temporal e breakdown com dados derivados). Integrações de emissões por provider ainda pendentes.

| Capacidade | Status Real |
|-----------|-------------|
| CarbonRecord (emissões por conta) | 🔶 |
| Série temporal de emissões com delta % | ✅ |
| Breakdown por dimensão | ✅ |
| Página PulseGreen no frontend | ✅ |

### 4.9 PulseLink — Conectores

| Capacidade | Status Real | Gap |
|-----------|-------------|-----|
| Azure Cost Management (real) | ✅ | `AzureConnector.fetch_costs()` funcional |
| Azure Resource Graph | 🔶 | Base presente, sem integração Resource Graph API |
| Azure Activity Log | 🔶 | `fetch_events()` presente, cobertura incompleta |
| Azure Advisor | 🔶 | Heurísticas locais, sem importação do Advisor real |
| Azure Blob Storage (ingestão de exports em escala) | ❌ | Não existe |
| Azure Carbon API | ❌ | Não existe |
| Multi-credenciais por workspace | 🔶 | CloudAccount suporta múltiplos registros |
| Validação de escopos antes de persistir | ❌ | SP-CL03 |
| Consolidação do modelo de credenciais | 🔶 | Legado pode coexistir — SP-CL04 |
| Conector AWS real (OIDC) | ❌ | Não existe |
| Conector GCP real (workload identity) | ❌ | Não existe |

### 4.10 Sync, Workers e PulseStream

| Capacidade | Status Real | Gap |
|-----------|-------------|-----|
| Sync manual por domínio | 🔶 | `/cloud-accounts/{id}/sync` enfileira na Redis |
| Workers automáticos com scheduler | 🔶 | Runner com loop, sem cron configurável |
| DLQ (fila de mensagens mortas) | ❌ | Mensagens falham silenciosamente |
| Workers resilientes por workspace | 🔶 | Lock por account_id, mas falha pode parar o worker inteiro |
| Schema Registry para contratos | ❌ | Não existe |
| Assinatura criptográfica de eventos de ingestão | 🔶 | StratoAudit tem hash chain, eventos de ingestão não assinados |
| PulseStream (event log imutável para replay) | ❌ | StratoAudit é para auditoria de ações, não replay de dados |

### 4.11 Auditoria e Compliance

| Capacidade | Status Real | Gap |
|-----------|-------------|-----|
| StratoAudit cobrindo operações críticas | ✅ | `audit_chain/service.py:append_event()` |
| Log de reset senha/MFA/operações admin | 🔶 | auth.* cobertos, operações admin não |
| Compliance report exportável (ComplianceArtifact) | 🔶 | Export JSONL existe, sem PDF/JSON assinado e estruturado |
| LGPD minimização e retenção configurável | ❌ | Sem `retention_days` por workspace |
| Data residency | ❌ | Sem suporte |

### 4.12 Credenciais e StratoMesh

| Capacidade | Status Real | Gap |
|-----------|-------------|-----|
| Envelope encryption com KMS/HSM | 🔶 | Fernet encryption local, Key Vault configurado mas sem envelope encryption |
| Rotação automática de segredos ≤ 30 dias | ❌ | Não existe |
| Managed identity para serviços | 🔶 | Azure Managed Identity parcial |
| StratoMesh (mTLS entre serviços) | ❌ | Não existe |
| TLS 1.3 obrigatório em todos datastores | 🔶 | Flags presentes, sem validação CI |

### 4.13 APIs e StratoGraph

| Capacidade | Status Real | Gap |
|-----------|-------------|-----|
| Paginação em todas as listas | 🔶 | Ausente na maioria dos endpoints |
| Idempotency keys em mutações críticas | ✅ | Implementado para `sync`, `experiments.create` e `experiments.approvals` (commit `7b7ff19`) |
| SMTP configurável | ❌ | Não existe |
| StratoGraph (GraphQL Federation) | ❌ | Não existe |
| AsyncAPI para contratos públicos | ❌ | Não existe |
| Integração Jira/Linear | ❌ | `external_ref` existe em Initiative, sem integração real |
| Integração GitHub (correlação deploy/custo) | ❌ | Não existe |
| Integração Slack/Teams | ❌ | Não existe |

### 4.14 Frontend — Páginas e Módulos

| Rota | Status | Observação |
|------|--------|-----------|
| / (landing pública) | ❌ | — |
| /login | 🔶 | Passkey e email/senha funcionais, UX melhorável |
| /forgot-password | ✅ | Implementada |
| /reset-password | ✅ | Implementada |
| /activate (convite) | ✅ | Implementada |
| /app/economics (rota estruturada) | ✅ SP-FE01 | /app/dashboard implementado; renomear para /app/economics é Wave 2 (SP-FE03) |
| /app/economics/costs | 🔶 | Era parte de /dashboard |
| /app/economics/usage | 🔶 | Parcial via /dashboard |
| /app/economics/skus | ✅ | Implementada com agregação temporária via ledger |
| /app/economics/reports | ✅ | Implementada com export CSV no frontend |
| /app/intel | 🔶 | Era /opportunities — renomear rota |
| /app/lab | 🔶 | Era /experiments — renomear rota |
| /app/notifications | ✅ | Implementada |
| /app/gov | ✅ | Implementada |
| /app/green | ✅ | Implementada |
| /app/settings/team | 🔶 | Era parte de /settings |
| /app/settings/cloud | 🔶 | Era parte de /settings |
| /app/settings/security | 🔶 | Era parte de /settings |
| /app/platform/workspaces | ✅ | Implementada |
| /app/platform/sync | ✅ | Implementada |

### 4.15 PulseOps — Infraestrutura

| Capacidade | Status Real | Gap |
|-----------|-------------|-----|
| Deploy cloud no Azure | ❌ | Ainda em Docker Compose local |
| IaC Terraform | ❌ | Não existe |
| AKS separado control/data plane | ❌ | Não existe |
| GitOps (ArgoCD/Flux) | ❌ | Não existe |
| Ambientes efêmeros por PR | ❌ | Não existe |
| OpenTelemetry end-to-end | 🔶 | Logs estruturados e health checks; traces/metrics desabilitados |
| SLI/SLO dashboards | ❌ | Não existe |
| CI com SAST/SCA/secret scan | ❌ | Sem CI configurado |
| Testes de carga (k6) | ❌ | Não existe |
| Backup RTO ≤ 30min / RPO ≤ 5min | ❌ | Sem procedimento validado |
| WAF + rate limiting comportamental | ❌ | Rate limiting local no middleware; sem WAF |
| NSGs + Private Endpoints | ❌ | Não existe |
| Pool de conexão SQL ajustável | 🔶 | SQLAlchemy pool configurado, sem tuning documentado |
| Healthcheck HTTP | ✅ | `/health` endpoint presente |
| Logs estruturados | ✅ | Structlog com metadados de request |

### 4.16 Resumo Quantitativo do Gap

| Bloco | ✅ Impl. | 🔶 Parcial | ❌ Não iniciado | Prioridade |
|-------|---------|-----------|----------------|-----------|
| Autenticação e sessão | 5 | 5 | 3 | P0 |
| Multi-tenant / workspaces | 0 | 3 | 5 | P0 |
| Perfis e membros | 0 | 1 | 5 | P0 |
| PulseEconomics (dashboard) | 1 | 5 | 4 | P1 |
| Alertas e notificações | 0 | 0 | 7 | P1 |
| PulseIntel (recomendações) | 0 | 3 | 3 | P1 |
| PulseGov (governança) | 0 | 0 | 6 | P2 |
| PulseGreen (sustentabilidade) | 0 | 0 | 4 | P2 |
| PulseLink (conectores) | 1 | 5 | 4 | P1 |
| Sync / Workers | 0 | 3 | 4 | P1 |
| StratoAudit / Compliance | 1 | 2 | 3 | P1 |
| Credenciais / StratoMesh | 0 | 3 | 2 | P0 |
| APIs / StratoGraph / Integrações | 0 | 1 | 7 | P2 |
| Frontend — páginas | 0 | 8 | 11 | P1 |
| PulseOps (infra e operação) | 2 | 4 | 9 | P0 |

---

## 5. Backlog Completo de Requisitos

### 5.1 Autenticação e Sessão

| ID | Requisito | Prioridade | Critério de aceite | Depende de |
|----|-----------|-----------|-------------------|-----------|
| SP-A01 | Forçar troca de senha em condições configuradas (first login, expiração, reset por admin) | P0 | Usuário redirecionado a /change-password; acesso bloqueado até conclusão; StratoAudit registra evento | SP-A03, SP-U01 | ✅ |
| SP-A02 | Migrar token do frontend de localStorage para cookie httpOnly | P0 | Zero ocorrências de token em localStorage no bundle de produção; verificado por teste e2e | — |
| SP-A03 | Rate limiting por workspace (org_id) e por IP em todos endpoints de autenticação | P0 | Bloqueia após N tentativas configuráveis; retorna 429 com Retry-After | — |
| SP-A04 | Validação de origin/referer no endpoint de login | P0 | Rejeita requests de origens não autorizadas com 403; configurável por ambiente | — | ✅ |
| SP-A05 | Headers de segurança HTTP completos em produção (CSP, HSTS, X-Frame, X-Content-Type, Permissions-Policy) | P0 | OWASP headers checker retorna 100% pass em staging e produção; gate automático no CI | — |
| SP-A06 | MFA TOTP completo: setup, verify, enable, disable, reset por workspace_admin | P1 | Admin reseta MFA de qualquer membro; membro forçado a reconfigurar; auditado | SP-U02 |
| SP-A07 | TLS 1.3 obrigatório para todos os datastores (PostgreSQL, Redis, ClickHouse) em produção | P0 | Conexões sem TLS 1.3 rejeitadas em produção; validado no CI de infra | — |

### 5.2 Multi-tenant / Workspaces

| ID | Requisito | Prioridade | Critério de aceite | Depende de |
|----|-----------|-----------|-------------------|-----------|
| SP-MT01 | Suite de testes de isolamento cross-workspace com enforcement central | P0 | Suite cross-workspace retorna 0 vazamentos; middleware/dependency rejeita request sem workspace válido | — |
| SP-MT02 | Lifecycle completo de workspace: criar, ativar, desativar, arquivar, purgar, restaurar | P0 | Cada transição testada e2e; purge remove todos os dados do workspace; restaurar recupera metadados | SP-MT05 |
| SP-MT03 | Cota de membros por workspace configurável e obrigatória | P0 | POST /workspaces/members retorna 422 quando cota atingida; cota configurável por plano | — |
| SP-MT04 | Workspace inativo bloqueia acesso de todos os membros imediatamente | P0 | Membros de workspace inativo recebem 403 em qualquer endpoint protegido; verificado em get_current_user | — |
| SP-MT05 | platform_admin com escopo global (sem workspace_id) operando em qualquer workspace | P0 | platform_admin acessa e opera qualquer workspace; sem impersonação; auditado | — |
| SP-MT06 | Chaves de criptografia dedicadas por workspace enterprise no Key Vault | P1 | Cada workspace enterprise tem keyring próprio; dados criptografados com chave isolada | SP-OP01, SP-SM02 |

### 5.3 Perfis e Membros

| ID | Requisito | Prioridade | Critério de aceite | Depende de |
|----|-----------|-----------|-------------------|-----------|
| SP-U01 | Reset de senha por workspace_admin via API | P0 | Admin gera token de reset; token expira em 24h; StratoAudit registra; SP-A01 ativado | SP-AP03 |
| SP-U02 | Reset de MFA por workspace_admin via API | P0 | Admin reseta MFA; membro forçado a reconfigurar; StratoAudit registra | SP-A06 |
| SP-U03 | Regra: admin não reseta credencial de admin de nível igual ou superior | P0 | API retorna 403 para reset cruzado entre admins do mesmo nível | SP-U01, SP-U02 |
| SP-U04 | Convite de membro com link de ativação enviado por email | P1 | Novo membro recebe email; link expira em 72h; senha definida no primeiro acesso | SP-AP03 |
| SP-U05 | Desativação de membro com soft-delete e auditoria | P1 | Membro desativado perde acesso imediatamente; registro preservado no StratoAudit | SP-MT04 |

### 5.4 PulseEconomics — Dashboard e Análise Financeira

| ID | Requisito | Prioridade | Critério de aceite | Depende de |
|----|-----------|-----------|-------------------|-----------|
| SP-EC01 | WorkspaceBudget: orçamento financeiro configurável (valor, período, moeda, alertas de %) | P0 | GET /economics/budget retorna orçamento; PUT persiste; painel exibe % consumido e projeção | — |
| SP-EC02 | Módulo de SKUs: SkuObservation com concentração de gasto, anomalias e sumário | P1 | Exibe top N SKUs por custo, variação % e alertas de concentração; filtrável por período | — |
| SP-EC03 | Exportação de relatórios em CSV e Excel com filtros aplicados | P1 | POST /economics/export gera arquivo assíncrono com status; GET retorna download | — |
| SP-EC04 | Custo detalhado por grupo de recursos, labels e filtros combinados com paginação | P1 | Filtros funcionam combinados; paginado (page, page_size, total); p95 < 900ms com 1M registros | SP-AP01 |
| SP-EC05 | UsageObservation: métricas de uso por recurso (utilização %, custo por unidade, tendência) | P1 | GET /economics/usage retorna métricas com tendência 30 dias | — |
| SP-EC06 | Forecast probabilístico P50/P90 com cenários (tráfego, câmbio, arquitetura) | P2 | Forecast exibe intervalo de confiança; erro < 8% no backtest de 30 dias | — |
| SP-EC07 | Painel executivo de savings: previsto vs realizado com intervalo de confiança | P1 | Exibe savings acumulado comparado previsto/realizado; dados de no mínimo 30 dias | — |

### 5.5 Alertas e Notificações

| ID | Requisito | Prioridade | Critério de aceite | Depende de |
|----|-----------|-----------|-------------------|-----------|
| SP-NT01 | ActivityEvent: storage de eventos de atividade do cloud provider por workspace | P1 | Worker ingere eventos do provider; consultáveis por tipo, período e recurso | SP-CL01 |
| SP-NT02 | AlertRecord: geração de alertas por categoria (financeiro, otimização, governança, atividade) | P1 | Cada categoria com regras configuráveis; alertas gerados em < 2h | SP-NT01 |
| SP-NT03 | NotificationPreference por membro (canal, categoria, frequência) | P1 | GET /notifications/preferences; PUT persiste; worker respeita ao enviar | — |
| SP-NT04 | GET /notifications/new para polling (count e lista de não lidas) | P1 | Retorna count e lista desde última checagem; usado pelo frontend para badge | SP-NT02 |
| SP-NT05 | PATCH /notifications/{id} para marcar lida ou arquivada | P1 | Status atualizado; operação idempotente | SP-NT02 |
| SP-NT06 | Envio de alertas críticos por email via SMTP configurável | P1 | Email enviado com template do produto; SMTP configurável por env var | SP-AP03 |
| SP-NT07 | Envio de alertas por Slack com webhook configurável por workspace | P2 | workspace_admin configura webhook; alertas de categoria crítica chegam no canal | — |

### 5.6 PulseIntel — Recomendações

| ID | Requisito | Prioridade | Critério de aceite | Depende de |
|----|-----------|-----------|-------------------|-----------|
| SP-RI01 | ProviderRecommendation: importação automática do provider (Azure Advisor) com sync periódico | P1 | Worker sincroniza a cada 4h; novas recomendações disponíveis em < 5h | — |
| SP-RI02 | Atualização de status de ProviderRecommendation: aceitar, dispensar, adiar com timestamp | P1 | PATCH /intel/provider-recommendations/{id}/status; auditado; filtro por status | SP-RI01 |
| SP-RI03 | SCA (Stratum Causal Attribution): explicação causal com % de confiança por recomendação | P2 | > 90% das recomendações com evidência causal; CausalTrace acessível na UI | — |
| SP-RI04 | ARI (Adaptive Recommendation Index): backlog com ranking autoajustável por feedback | P2 | Ranking muda após aceite/rejeição/resultado; modelo atualizado com dados de 30 dias | — |
| SP-RI05 | PulseLab Simulator: simular cenário com restrições de SLO e risco quantificado | P2 | Usuário define hipótese; simulador retorna custo estimado, risco e alternativas | — |
| SP-RI06 | Execução canário real com guardrails automáticos e rollback se SLO violado | P2 | Ação executada em % configurável do tráfego; rollback automático se limiar violado; auditado | SP-RI05 |

### 5.7 PulseGov — Governança

| ID | Requisito | Prioridade | Critério de aceite | Depende de |
|----|-----------|-----------|-------------------|-----------|
| SP-GV01 | ResourceInventory: inventário de recursos por workspace | P2 | Worker sincroniza inventário; consultável com filtros por tipo, grupo, label | SP-CL01 |
| SP-GV02 | Avaliação de compliance de labels obrigatórias | P2 | GET /gov/label-compliance retorna % por tipo e grupo; atualizado diariamente | SP-GV01 |
| SP-GV03 | Configuração de labels obrigatórias por workspace | P2 | workspace_admin define lista; avaliação reexecutada; auditado | SP-GV02 |
| SP-GV04 | Detecção de recursos sem owner com custo associado | P2 | GET /gov/unowned-costs retorna lista com custo acumulado; exportável | SP-GV01 |
| SP-GV05 | TopologyMap: grafo vivo de dependências serviço-recurso | P3 | Graph DB com nós e arestas atualizados; query de blast radius disponível | SP-GV01 |
| SP-GV06 | Blast radius como restrição automática em execuções do PulseLab | P3 | Ações bloqueadas se blast radius exceder limite configurado | SP-GV05 |

### 5.8 PulseGreen — Sustentabilidade

| ID | Requisito | Prioridade | Critério de aceite | Depende de |
|----|-----------|-----------|-------------------|-----------|
| SP-GR01 | CarbonRecord: sincronização de emissões por conta e período | P2 | Worker ingere dados da Carbon API; disponível em < 4h; falhas retryadas | SP-CL02 |
| SP-GR02 | Série temporal de emissões com variação mensal e delta % | P2 | GET /green/emissions retorna série por mês com delta % | SP-GR01 |
| SP-GR03 | Breakdown de emissões por dimensão configurável | P2 | GET /green/breakdown?by=service retorna decomposição | SP-GR01 |
| SP-GR04 | Página PulseGreen no frontend | P2 | Gráficos de trend e breakdown; exportação disponível; dados de no mínimo 3 meses | SP-GR02, SP-GR03 |

### 5.9 PulseLink — Conectores

| ID | Requisito | Prioridade | Critério de aceite | Depende de |
|----|-----------|-----------|-------------------|-----------|
| SP-CL01 | Conector Azure Blob Storage para ingestão de exports de custo em escala | P1 | Worker consome blobs; normaliza e ingere no store analítico; idempotente | — |
| SP-CL02 | Conector Azure Carbon API | P2 | Worker sincroniza emissões; erros retryados com backoff | — |
| SP-CL03 | Validação de escopos de credencial antes de persistir (CloudAccount) | P0 | POST valida escopos mínimos; retorna erro descritivo se insuficiente | — |
| SP-CL04 | Consolidação para CloudAccount multi-registro e remoção do legado | P1 | Apenas o novo modelo em uso; migração executada sem perda de dados | — |
| SP-CL05 | Conector AWS real (Cost Explorer + CloudWatch) com OIDC federation | P2 | Dados AWS ingeridos sem chaves estáticas em disco | — |
| SP-CL06 | Conector GCP real (Billing + Cloud Monitoring) com workload identity | P3 | Dados GCP ingeridos; sem service account key em disco | — |

### 5.10 Sync, Workers e PulseStream

| ID | Requisito | Prioridade | Critério de aceite | Depende de |
|----|-----------|-----------|-------------------|-----------|
| SP-WK01 | DLQ para mensagens com falha repetida e alertas para ops | P1 | Mensagens com 3 falhas vão para DLQ; alerta gerado; reprocessável via UI | — |
| SP-WK02 | Workers resilientes por workspace (falha isolada) | P1 | Falha injetada em workspace A; worker de workspace B continua | — |
| SP-WK03 | Remoção de endpoints depreciados com guia de migração | P1 | Endpoints legados removidos; documentação publicada | — |
| SP-WK04 | Schema Registry para contratos de evento versionados | P2 | Cada tipo de evento tem schema publicado; produtor valida antes de publicar | — |
| SP-WK05 | PulseStream: event log imutável com hash encadeado para replay | P2 | Eventos armazenados com hash; replay verificável em staging | — |

### 5.11 StratoAudit e Compliance

| ID | Requisito | Prioridade | Critério de aceite | Depende de |
|----|-----------|-----------|-------------------|-----------|
| SP-AU01 | StratoAudit cobrindo 100% das operações críticas por workspace | P0 | Todo evento crítico registrado com: membro, ação, timestamp, workspace, resultado | — |
| SP-AU02 | ComplianceArtifact: relatório por período exportável (PDF/JSON assinado) | P2 | GET /audit/report?from=&to= retorna artefato assinado; verificável por hash | — |
| SP-AU03 | LGPD: minimização de dados e retenção configurável por workspace | P2 | workspace_admin configura prazo; worker de purge executa ao atingir prazo; auditado | — |

### 5.12 Credenciais e StratoMesh

| ID | Requisito | Prioridade | Critério de aceite | Depende de |
|----|-----------|-----------|-------------------|-----------|
| SP-SM01 | Rotação automática de segredos ≤ 30 dias no Key Vault | P0 | Key Vault rotation policy configurada; alerta se segredo > 30 dias | SP-OP01 |
| SP-SM02 | Envelope encryption com KMS para dados sensíveis em repouso | P1 | Credenciais, PII e segredos criptografados com envelope; chave mestre em HSM | SP-OP01 |
| SP-SM03 | StratoMesh: mTLS entre todos os serviços internos | P2 | Certificados emitidos automaticamente; mTLS obrigatório; plaintext bloqueado | SP-OP03 |

### 5.13 APIs e StratoGraph

| ID | Requisito | Prioridade | Critério de aceite | Depende de |
|----|-----------|-----------|-------------------|-----------|
| SP-AP01 | Paginação em todas as listas (page, page_size, total) | P0 | Todas as GET de lista com paginação; testado com > 10k registros; p95 < 900ms | — |
| SP-AP02 | Idempotency keys em mutações críticas (sync, experiment, approval) | P1 | POST duplicado com mesmo key retorna resultado original sem efeito colateral | — |
| SP-AP03 | SMTP configurável para convites, resets e alertas | P1 | SMTP via env var; emails testados em staging com template do produto | — |
| SP-AP04 | StratoGraph: GraphQL Federation com subgraphs por domínio | P2 | Gateway expõe schemas unificados; subgraphs deployáveis independentemente | — |
| SP-AP05 | AsyncAPI para contratos de eventos públicos | P2 | Spec AsyncAPI publicada; validada contra Schema Registry | SP-WK04 |
| SP-AP06 | Integração Jira/Linear: criar tarefa a partir de recomendação | P2 | Botão na UI; tarefa criada no board configurado; link bidirecional | — |
| SP-AP07 | Integração GitHub: correlacionar deploys com variações de custo | P2 | Webhook GitHub ingerido; deploy event correlacionado com custo no SCA | SP-RI03 |

### 5.14 Frontend — Páginas Faltantes

| ID | Página | Prioridade | Critério de aceite |
|----|--------|-----------|-------------------|
| SP-FE01 | Reestruturação de rotas para /app/* (reestruturar Router sem perder estado) | P0 | Todas as rotas atuais migradas para /app/*; zero quebra de links existentes | ✅ |
| SP-FE02 | /forgot-password e /reset-password completos | P0 | Formulários funcionais; token validado; redirect para login com mensagem |
| SP-FE03 | /app/economics/skus — Análise de SKUs | P1 | Top N SKUs por custo, variação %; filtrável e exportável |
| SP-FE04 | /app/economics/reports — Relatórios com exportação | P1 | Visão analítica + botão export; download assíncrono com status |
| SP-FE05 | /app/notifications — Central de alertas | P1 | Lista de alertas; PATCH lida/arquiva; link para preferências |
| SP-FE06 | /app/gov — PulseGov | P2 | Tabela compliance %; lista recursos sem owner; configuração de labels |
| SP-FE07 | /app/green — PulseGreen | P2 | Gráficos trend e breakdown; exportação |
| SP-FE08 | /app/platform/workspaces — Admin de workspaces | P0 | CRUD workspace; ações lifecycle; log de operações |
| SP-FE09 | /app/platform/sync — Status operacional | P1 | Status por workspace e conector; trigger manual; indicador DLQ |
| SP-FE10 | UX por persona (Exec, FinOps, Platform, Security) | P2 | Dashboards distintos por papel; configurável por workspace_admin |
| SP-FE11 | Migração de token de localStorage para cookie httpOnly no frontend | P0 | Zero ocorrências de token em localStorage |

### 5.15 PulseOps — Infraestrutura

| ID | Requisito | Prioridade | Critério de aceite |
|----|-----------|-----------|-------------------|
| SP-OP01 | IaC Terraform Azure: VNet, subnets, NSGs, egress control | P0 | terraform apply sem erro; rede privada provisionada |
| SP-OP02 | Private Endpoints para PostgreSQL, Redis, ClickHouse + DNS privado | P0 | Datastores não expostos à internet; conexão apenas via private endpoint |
| SP-OP03 | AKS com separação control plane / data plane e network policies | P0 | Clusters separados; network policy bloqueia tráfego não autorizado |
| SP-OP04 | GitOps (ArgoCD ou Flux) com canário e rollback automático | P0 | Deploy canário em 10%; rollback automático se p95 violado |
| SP-OP05 | WAF + rate limiting comportamental (Azure Front Door / App Gateway) | P1 | WAF frente à API; regras OWASP ativas; rate limiting por IP e por workspace |
| SP-OP06 | OpenTelemetry end-to-end em produção (traces, metrics, logs) | P1 | 100% dos serviços instrumentados; traces distribuídos visíveis |
| SP-OP07 | SLI/SLO dashboards e alertas por error budget | P1 | Dashboards de SLO por serviço; alerta quando error budget < 20% |
| SP-OP08 | CI com SAST, SCA, secret scan e gates de merge bloqueantes | P1 | Pipeline bloqueia merge com CVE crítica ou segredo detectado |
| SP-OP09 | Ambientes efêmeros por PR para testes de contrato e segurança | P2 | PR cria ambiente; testes de contrato e security scan; destruído após merge |
| SP-OP10 | Backup com RTO ≤ 30min e RPO ≤ 5min validados em staging | P0 | Restore executado em staging; RTO e RPO medidos dentro da meta |
| SP-OP11 | Testes de carga k6 (smoke, load, stress) integrados ao pipeline | P2 | Smoke em todo deploy; load em staging semanal |

---

## 6. Modelo de Dados — Entidades a Implementar/Migrar

### 6.1 Entidades Existentes (manter com ajustes)

| Nome Atual no Código | Nome Canonical PRD | Ajuste Necessário |
|---------------------|-------------------|------------------|
| `Organization` | `Workspace` | Adicionar campos: lifecycle_state, member_quota, retention_days, plan_tier |
| `User` | `WorkspaceMember` | Adicionar: invited_at, activated_at, deactivated_at, must_change_password, totp_secret |
| `CloudAccount` | `CloudCredential` | Renomear + adicionar: scopes_validated_at, validated_scopes (JSONB) |
| `OptimizationOpportunity` | `OptimizationOpportunity` | Manter, adicionar: causal_trace_id, ari_score, evidence_summary |
| `OptimizationExperiment` | `OptimizationExperiment` | Manter, adicionar: blast_radius_pct_at_creation, slo_constraint_json |
| `ExperimentRun` | `ExperimentRun` | Manter, adicionar: canary_traffic_pct, slo_threshold_json |
| `Initiative` | `Initiative` | Manter, adicionar: linked_jira_id, linked_linear_id, linked_github_pr |
| `RiskBudget` | `RiskBudget` | Manter |
| `ChangeEvent` | `ChangeEvent` | Manter, adicionar: github_commit_sha, github_repo |
| `AuditChainEvent` | `AuditChainEvent` (StratoAudit) | Manter |
| `AuditChainCheckpoint` | `AuditChainCheckpoint` | Manter |
| `PolicyBundle` | `PolicyBundle` | Manter |
| `PolicyDecisionEvidence` | `PolicyDecisionEvidence` | Manter |
| `AuthChallenge` | `AuthChallenge` | Manter |
| `PasskeyCredential` | `PasskeyCredential` | Manter |

### 6.2 Entidades a Criar (migração 0008+)

| Entidade | Store | Prioridade | Campos Principais |
|---------|-------|-----------|------------------|
| `WorkspaceBudget` | PostgreSQL | P0 | workspace_id, amount, currency, period, alert_threshold_pct, activated_at |
| `PasswordResetToken` | PostgreSQL | P0 | user_id, token_hash, expires_at, consumed_at |
| `MfaTotpCredential` | PostgreSQL | P1 | user_id, totp_secret_encrypted, is_active, created_at |
| `MemberInvite` | PostgreSQL | P1 | workspace_id, email, invite_token_hash, expires_at, activated_at, invited_by |
| `ActivityEvent` | PostgreSQL + ClickHouse | P1 | workspace_id, account_id, event_type, resource_id, resource_name, resource_group, region, caller, operation_name, occurred_at |
| `AlertRecord` | PostgreSQL | P1 | workspace_id, category, severity, title, body, resource_ref, is_read, is_archived, delivered_at, created_at |
| `NotificationPreference` | PostgreSQL | P1 | user_id, workspace_id, channels (JSONB), categories (JSONB), frequency |
| `ProviderRecommendation` | PostgreSQL | P1 | workspace_id, account_id, external_id, provider, category, short_description, impact_level, annual_savings_usd, status, last_synced_at |
| `SyncRecord` | PostgreSQL | P1 | workspace_id, account_id, sync_type, status, started_at, completed_at, records_processed, error_message |
| `SkuObservation` | ClickHouse | P1 | workspace_id, account_id, sku_id, sku_name, service, date, cost_usd, quantity |
| `CostForecastBand` | PostgreSQL + ClickHouse | P1 | workspace_id, target_month, p50_usd, p90_usd, scenario, generated_at |
| `UsageObservation` | ClickHouse (granularidade minuto) | P1 | workspace_id, account_id, resource_id, metric_name, value, unit, recorded_at |
| `ResourceInventory` | PostgreSQL + ClickHouse | P2 | workspace_id, account_id, resource_id, resource_type, name, resource_group, location, tags (JSONB), required_labels_compliant, owner, last_synced_at |
| `CarbonRecord` | ClickHouse | P2 | workspace_id, account_id, year_month, kg_co2e, service, resource_group, synced_at |
| `CausalTrace` | PostgreSQL + ClickHouse | P2 | workspace_id, recommendation_id, change_event_id, contribution_pct, confidence, method, computed_at |
| `ComplianceArtifact` | Object Storage | P2 | workspace_id, period_from, period_to, artifact_url, hash_sha256, signature, generated_by, created_at |
| `TopologyNode` | Graph DB (Neo4j) | P3 | workspace_id, node_id, node_type (service/resource), name, attributes (JSONB) |
| `TopologyEdge` | Graph DB | P3 | workspace_id, from_node_id, to_node_id, relationship_type, weight |
| `DlqMessage` | PostgreSQL | P1 | queue_name, original_payload, error_message, retry_count, last_failed_at, status |

### 6.3 Migração de Banco Necessária

```
0008_workspace_budget_password_reset.py
  → WorkspaceBudget, PasswordResetToken

0009_mfa_totp_member_invite.py
  → MfaTotpCredential, MemberInvite, User.must_change_password, User.totp_enabled

0010_workspace_lifecycle.py
  → Organization: add lifecycle_state, member_quota, retention_days, plan_tier
  → User: add invited_at, activated_at, deactivated_at

0011_notifications_alerts.py
  → ActivityEvent, AlertRecord, NotificationPreference

0012_provider_recommendations_sync.py
  → ProviderRecommendation, SyncRecord, DlqMessage

0013_cost_forecast_skus.py
  → CostForecastBand, (SkuObservation e UsageObservation no ClickHouse)

0014_causal_traces.py
  → CausalTrace, OptimizationExperiment: add blast_radius_pct_at_creation

0015_resource_inventory_carbon.py
  → ResourceInventory, CarbonRecord (ClickHouse)

0016_compliance_artifacts.py
  → ComplianceArtifact

0017_topology_graph.py (ou Neo4j schemas)
  → TopologyNode, TopologyEdge
```

---

## 7. Arquitetura de APIs — Catálogo Completo

### 7.1 Estratégia de APIs

| Tipo | Protocolo | Uso |
|------|----------|-----|
| API pública | REST/JSON (hoje) → GraphQL Federation (Wave 3) | Frontend + integrações |
| API de baixa latência | REST hoje → gRPC (Wave 3) | Comunicação inter-serviço |
| Eventos assíncronos | Redis (hoje) → AsyncAPI/Kafka (Wave 3) | Workers e integrações |

### 7.2 Catálogo de Endpoints — Estado Atual + Target

#### Auth (`/api/v1/auth`)

| Método | Path | Status | Prioridade |
|--------|------|--------|-----------|
| POST | /login | ✅ Existe | — |
| POST | /refresh | ✅ Existe | — |
| POST | /logout | ✅ Existe | — |
| GET | /me | ✅ Existe | — |
| POST | /register | ✅ Existe | — |
| POST | /users | ✅ Existe | — |
| GET | /users | ✅ Existe | — |
| DELETE | /users/{user_id} | ❌ Falta | P1 |
| PATCH | /users/{user_id} | ❌ Falta | P1 |
| POST | /users/{user_id}/reset-password | ❌ Falta | P0 (SP-U01) |
| POST | /users/{user_id}/reset-mfa | ❌ Falta | P0 (SP-U02) |
| POST | /users/{user_id}/deactivate | ❌ Falta | P1 (SP-U05) |
| POST | /users/invite | ❌ Falta | P1 (SP-U04) |
| POST | /activate | ❌ Falta | P1 (SP-U04) |
| POST | /change-password | ❌ Falta | P0 (SP-A01) |
| POST | /forgot-password | ✅ commit 8307faa | — |
| POST | /reset-password | ✅ commit 8307faa | — |
| POST | /mfa/setup | ❌ Falta | P1 (SP-A06) |
| POST | /mfa/verify | ❌ Falta | P1 |
| PATCH | /mfa/enable | ❌ Falta | P1 |
| PATCH | /mfa/disable | ❌ Falta | P1 |
| POST | /passkey/register/options | ✅ Existe | — |
| POST | /passkey/register/verify | ✅ Existe | — |
| POST | /passkey/login/options | ✅ Existe | — |
| POST | /passkey/login/verify | ✅ Existe | — |
| GET | /passkeys | ✅ Existe | — |
| DELETE | /passkeys/{id} | ✅ Existe | — |
| GET | /oidc/azure/start | ✅ Existe | — |
| GET | /oidc/azure/callback | ✅ Existe | — |
| PATCH | /passwordless-policy | ✅ Existe | — |

#### Economics (`/api/v1/economics`)

| Método | Path | Status | Prioridade |
|--------|------|--------|-----------|
| GET | /dashboard | ✅ Existe (em /ledger/dashboard) | Mover para /economics |
| GET | /cost-trend | ✅ Existe | Mover |
| GET | /cost-trend-by-service | ✅ Existe | Mover |
| GET | /budget | ❌ Falta | P0 (SP-EC01) |
| PUT | /budget | ❌ Falta | P0 |
| GET | /costs | ❌ Falta | P1 (SP-EC04) |
| GET | /costs/detailed | ❌ Falta | P1 |
| GET | /usage | ❌ Falta | P1 (SP-EC05) |
| GET | /skus | ❌ Falta | P1 (SP-EC02) |
| GET | /reports | ❌ Falta | P1 |
| POST | /reports/export | ❌ Falta | P1 (SP-EC03) |
| GET | /reports/export-costs | ❌ Falta | P1 |
| GET | /forecast | ❌ Falta | P2 (SP-EC06) |
| GET | /savings-summary | ❌ Falta | P1 (SP-EC07) |

#### Intel (`/api/v1/intel`)

| Método | Path | Status | Prioridade |
|--------|------|--------|-----------|
| GET | /recommendations | ✅ Existe (em /opportunities) | Mover + unificar |
| GET | /recommendations/summary | ✅ Existe | Mover |
| POST | /recommendations | ✅ Existe | Mover |
| GET | /recommendations/{id} | ✅ Existe | Mover |
| PATCH | /recommendations/{id}/status | ✅ Existe | Mover |
| POST | /recommendations/generate/{account_id} | ✅ Existe | Mover |
| GET | /provider-recommendations | ❌ Falta | P1 (SP-RI01) |
| PATCH | /provider-recommendations/{id}/status | ❌ Falta | P1 |
| GET | /backlog | ❌ Falta | P2 (SP-RI04 - ARI) |
| GET | /causal-trace/{recommendation_id} | ❌ Falta | P2 (SP-RI03) |

#### Lab (`/api/v1/lab`)

| Método | Path | Status | Prioridade |
|--------|------|--------|-----------|
| POST | /experiments | ✅ Existe (em /experiments) | Mover |
| GET | /experiments | ✅ Existe | Mover |
| GET | /experiments/summary | ✅ Existe | Mover |
| GET | /experiments/{id} | ✅ Existe | Mover |
| PATCH | /experiments/{id} | ✅ Existe | Mover |
| POST | /experiments/{id}/transition | ✅ Existe | Mover |
| POST | /experiments/{id}/runs | ✅ Existe | Mover |
| GET | /experiments/{id}/runs | ✅ Existe | Mover |
| PATCH | /experiments/{id}/runs/{run_id} | ✅ Existe | Mover |
| POST | /experiments/{id}/approve | ✅ Existe (em /approvals) | Mover |
| GET | /experiments/{id}/approvals | ✅ Existe | Mover |
| POST | /experiments/{id}/simulate | ❌ Falta | P2 (SP-RI05) |
| POST | /experiments/{id}/rollback | ❌ Falta | P2 (SP-RI06) |

#### Notifications (`/api/v1/notifications`)

| Método | Path | Status | Prioridade |
|--------|------|--------|-----------|
| GET | / | ❌ Falta | P1 |
| GET | /new | ❌ Falta | P1 (SP-NT04) |
| GET | /summary | ❌ Falta | P1 |
| GET | /preferences | ❌ Falta | P1 (SP-NT03) |
| PUT | /preferences | ❌ Falta | P1 |
| PATCH | /{id} | ❌ Falta | P1 (SP-NT05) |

#### Gov (`/api/v1/gov`)

| Método | Path | Status | Prioridade |
|--------|------|--------|-----------|
| GET | /inventory | ❌ Falta | P2 |
| GET | /label-compliance | ❌ Falta | P2 |
| PUT | /required-labels | ❌ Falta | P2 |
| GET | /unowned-costs | ❌ Falta | P2 |
| GET | /topology/{node_id}/blast-radius | ❌ Falta | P3 |

#### Green (`/api/v1/green`)

| Método | Path | Status | Prioridade |
|--------|------|--------|-----------|
| GET | /emissions | ❌ Falta | P2 |
| GET | /breakdown | ❌ Falta | P2 |

#### Sync (`/api/v1/sync`)

| Método | Path | Status | Prioridade |
|--------|------|--------|-----------|
| POST | /costs | 🔶 Existe (em /ledger/ingest) | Mover |
| POST | /activity | ❌ Falta | P1 |
| POST | /recommendations | ❌ Falta | P1 |
| POST | /alerts | ❌ Falta | P1 |
| POST | /inventory | ❌ Falta | P2 |
| POST | /carbon | ❌ Falta | P2 |

#### Workspaces (`/api/v1/workspaces`)

| Método | Path | Status | Prioridade |
|--------|------|--------|-----------|
| GET | / | ❌ Falta | P0 |
| POST | / | ✅ Existe (em /auth/register) | Refatorar |
| GET | /{id} | ❌ Falta | P0 |
| PATCH | /{id} | ❌ Falta | P0 |
| PUT | /{id}/status | ❌ Falta | P0 (SP-MT02) |
| DELETE | /{id} | ❌ Falta | P0 |
| GET | /{id}/credentials | ❌ Falta | P0 |
| POST | /{id}/purge | ❌ Falta | P0 |
| POST | /{id}/restore | ❌ Falta | P0 |

#### Members (`/api/v1/members`)

| Método | Path | Status | Prioridade |
|--------|------|--------|-----------|
| GET | / | ✅ Existe (em /auth/users) | Mover |
| POST | / | ✅ Existe | Mover |
| DELETE | /{id} | ❌ Falta | P1 |
| POST | /{id}/reset-password | ❌ Falta | P0 |
| POST | /{id}/reset-mfa | ❌ Falta | P0 |
| POST | /{id}/deactivate | ❌ Falta | P1 |

#### Credentials (`/api/v1/settings/cloud`)

| Método | Path | Status | Prioridade |
|--------|------|--------|-----------|
| GET | /credentials | ✅ Existe (em /cloud-accounts) | Mover |
| POST | / | ✅ Existe | Mover |
| PUT | /{id} | ❌ Falta | P1 |
| DELETE | /{id} | ✅ Existe | Mover |
| POST | /{id}/validate | ❌ Falta | P0 (SP-CL03) |
| POST | /{id}/sync | ✅ Existe | Mover |

#### Audit (`/api/v1/audit`)

| Método | Path | Status | Prioridade |
|--------|------|--------|-----------|
| GET | /events | ✅ Existe (em /audit-chain/events) | Mover |
| GET | /events/auth | ✅ Existe | Mover |
| GET | /events/export/jsonl | ✅ Existe | Mover |
| GET | /verify | ✅ Existe | Mover |
| POST | /checkpoints | ✅ Existe | Mover |
| GET | /checkpoints | ✅ Existe | Mover |
| GET | /checkpoints/{id}/verify | ✅ Existe | Mover |
| GET | /report | ❌ Falta | P2 (SP-AU02) |

#### Platform (`/api/v1/platform`) — platform_admin only

| Método | Path | Status | Prioridade |
|--------|------|--------|-----------|
| GET | /workspaces | ❌ Falta | P0 |
| GET | /sync-status | ❌ Falta | P1 |
| POST | /workspaces/{id}/purge | ❌ Falta | P0 |
| POST | /workspaces/{id}/restore | ❌ Falta | P0 |

### 7.3 Padrões de Contrato de API

Todos os novos endpoints devem seguir:

```json
// Resposta de erro padronizada
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Descrição amigável",
    "trace_id": "uuid4",
    "policy_decision_id": "uuid4 | null",
    "retry_hint": "PT30S | null",
    "details": [...]
  }
}

// Resposta de lista paginada
{
  "items": [...],
  "page": 1,
  "page_size": 20,
  "total": 435,
  "has_next": true,
  "has_prev": false
}
```

Mutações críticas devem aceitar header `Idempotency-Key: uuid4`.

---

## 8. Frontend — Estrutura de Rotas e Páginas

### 8.1 Reestruturação de Rotas

A estrutura atual de rotas (`/dashboard`, `/opportunities`, etc.) deve ser migrada para a estrutura `/app/*` progressivamente, mantendo redirects temporários.

### 8.2 Rotas Públicas

| Rota | Componente | Status | Prioridade |
|------|-----------|--------|-----------|
| / | LandingPage | ❌ | P1 |
| /login | LoginPage | 🔶 | Melhorias |
| /forgot-password | ForgotPasswordPage | ✅ commit 8307faa | — |
| /reset-password | ResetPasswordPage | ✅ commit 8307faa | — |
| /activate | ActivatePage | ❌ | P1 |

### 8.3 Rotas Protegidas

| Rota | Módulo | Perfil Mínimo | Status | Prioridade |
|------|--------|-------------|--------|-----------|
| /app | Shell principal | viewer | ✅ SP-FE01 | — |
| /app/economics | PulseEconomics Dashboard | viewer | 🔶 | Mover de /dashboard |
| /app/economics/costs | Custos detalhados | viewer | 🔶 | Expandir |
| /app/economics/usage | Uso e eficiência | viewer | 🔶 | Expandir |
| /app/economics/skus | Análise de SKUs | viewer | ✅ | P1 (SP-FE03) |
| /app/economics/reports | Relatórios e exportação | analyst | ✅ | P1 (SP-FE04) |
| /app/intel | PulseIntel — Recomendações | viewer | 🔶 | Mover de /opportunities |
| /app/lab | PulseLab — Experimentos | analyst | 🔶 | Mover de /experiments |
| /app/notifications | Central de Alertas | viewer | ✅ | P1 (SP-FE05) |
| /app/gov | PulseGov — Governança | analyst | ✅ | P2 (SP-FE06) |
| /app/green | PulseGreen — Sustentabilidade | viewer | ✅ | P2 (SP-FE07) |
| /app/risk-budgets | Risk Budgets | analyst | ✅ | — |
| /app/change-events | Change Events | analyst | ✅ | — |
| /app/executive | Executive Summary | viewer | ✅ | — |
| /app/settings/team | Membros do workspace | workspace_admin | 🔶 | Expandir |
| /app/settings/cloud | Credenciais cloud | workspace_admin | 🔶 | Expandir |
| /app/settings/security | Segurança da conta | workspace_admin | 🔶 | Expandir |
| /app/platform/workspaces | Gestão de workspaces | platform_admin | ✅ commit 8307faa + SP-FE01 | — |
| /app/platform/sync | Monitor de sincronização | platform_admin | ✅ | — |

### 8.4 Migração de Token (SP-A02, SP-FE11)

O `apiClient` em `frontend/src/api/client.ts` atualmente adiciona o token via header `Authorization`. Isso implica que o token está armazenado em memória (se via variável React) ou localStorage.

**Ação necessária:**
1. Configurar FastAPI para setar token como `Set-Cookie: access_token=...; HttpOnly; Secure; SameSite=Strict`
2. Atualizar o `apiClient` para usar `withCredentials: true` (axios)
3. Remover toda leitura de token de localStorage no frontend
4. Atualizar o middleware de CORS para permitir cookies cross-origin em produção

---

## 9. Workers e Event Processing

### 9.1 Workers Existentes (ajustar)

| Worker | Ajuste Necessário |
|--------|-----------------|
| `ingestion_worker.py` | Adicionar DLQ, resilência por workspace isolado, tratamento de falha parcial |
| `scoring_worker.py` | Adicionar isolamento por workspace, logging de falhas |
| `audit_checkpoint_worker.py` | Manter, adicionar métricas de OpenTelemetry |

### 9.2 Workers a Criar

| Worker | Prioridade | Responsabilidade |
|--------|-----------|-----------------|
| `recommendation_sync_worker.py` | P1 | Importa ProviderRecommendation do Azure Advisor a cada 4h |
| `alert_worker.py` | P1 | Avalia regras de AlertRecord; gera alertas por categoria |
| `notification_dispatcher.py` | P1 | Envia alertas por email (SMTP) e Slack (webhook) |
| `activity_sync_worker.py` | P1 | Ingere ActivityEvent do Azure Activity Log |
| `inventory_sync_worker.py` | P2 | Sincroniza ResourceInventory do Azure Resource Graph |
| `carbon_sync_worker.py` | P2 | Ingere CarbonRecord da Azure Carbon API |
| `dlq_monitor_worker.py` | P1 | Monitora DlqMessage; alerta operações após N falhas |
| `forecast_worker.py` | P2 | Gera CostForecastBand com modelo probabilístico |
| `lgpd_purge_worker.py` | P2 | Executa purge de dados por retention_days por workspace |
| `causal_attribution_worker.py` | P2 | Calcula CausalTrace entre ChangeEvent e custos |

### 9.3 DLQ (Dead Letter Queue)

Implementar em `DlqMessage` (PostgreSQL):

```
Política de retenção:
- Máximo 3 tentativas antes de ir para DLQ
- Alerta gerado automaticamente ao atingir DLQ
- Reprocessamento manual via API: POST /platform/dlq/{id}/retry
- Expiração automática após 30 dias
```

---

## 10. Infraestrutura e Deployment

### 10.1 Estado Atual: Docker Compose (dev only)

```yaml
# Serviços atuais
postgres: PostgreSQL 15
redis: Redis 7  
clickhouse: ClickHouse
backend: FastAPI (porta 8000)
frontend: Vite/Nginx (porta 5173/80)
```

### 10.2 Target: AKS Multi-cluster (Waves 1+)

```
Rede Azure (VNet):
├── subnet-control-plane (AKS control plane cluster)
│   ├── backend (pods)
│   ├── workers (pods)
│   └── ingress-nginx
├── subnet-data-plane (AKS data cluster)
│   ├── clickhouse (pods)
│   └── data-processors
├── subnet-datastores
│   ├── Private Endpoint — PostgreSQL Flexible Server
│   ├── Private Endpoint — Azure Cache for Redis
│   └── Private Endpoint — ClickHouse Cloud (ou VM)
└── subnet-management
    └── ArgoCD / Flux

Azure Key Vault:
├── Segredos da aplicação
├── Fernet encryption keys (por workspace enterprise)
└── TLS certificates

Azure Front Door / Application Gateway:
├── WAF com regras OWASP
├── Rate limiting por IP e por workspace
└── TLS termination
```

### 10.3 GitOps Pipeline (Wave 1)

```
Developer Push → GitHub PR
  ↓
GitHub Actions CI:
  ├── SAST (Bandit/Semgrep)
  ├── SCA (Safety/pip-audit)
  ├── Secret scan (trufflehog/gitleaks)
  ├── Unit tests
  ├── Integration tests
  ├── Contract tests
  └── Docker build

Merge para main:
  ↓
ArgoCD / Flux detecta mudança no repo de manifests
  ↓
Progressive Delivery (Argo Rollouts):
  ├── Deploy 10% (canário)
  ├── Aguarda 5 min
  ├── Analisa p95 latência e error rate
  ├── Se OK: rollout 100%
  └── Se NOK: rollback automático

Ambientes:
  dev → preview-ephemeral-PR-{n} → staging → production
```

### 10.4 OpenTelemetry (Wave 2)

Instrumentar `backend/app/main.py` com:

```python
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

# Exportar para Azure Monitor / Grafana Tempo
```

SLIs a instrumentar:
- `api.request.duration_ms` (latência por endpoint)
- `api.request.error_rate` (taxa de erro por endpoint)
- `worker.ingest.lag_seconds` (lag de ingestão)
- `worker.command.success_rate` (sucesso de comandos)
- `audit.chain.events_per_min` (eventos por minuto)

---

## 11. Plano de Implementação — Waves

### Wave 0 — Hardening Imediato (P0 técnico, semanas 1–3)

**Objetivo:** Elevar o baseline de segurança sem bloquear evolução arquitetural. Trabalho paralelo ao restante do desenvolvimento.

| # | ID | Requisito | Status | Critério de Aceite |
|---|----|-----------|--------|-------------------|
| 1 | SP-A05 | Headers de segurança HTTP completos | ✅ commit 27bd39c | OWASP checker 100% em staging; gate automático |
| 2 | SP-A07 | TLS 1.3 obrigatório para datastores | ✅ commit fa6c1a4 | SSL mode obrigatório em PostgreSQL, Redis, ClickHouse |
| 3 | SP-A03 | Rate limiting por workspace e por IP | ✅ commit c8befb6 | 429 com Retry-After após N tentativas configuráveis |
| 4 | SP-A02 + SP-FE11 | Migração token para cookie httpOnly | ⬜ pendente | Zero token em localStorage; withCredentials: true |
| 5 | SP-CL03 | Validação de escopos antes de persistir credencial | ⬜ pendente | POST /settings/cloud/credentials valida escopos mínimos |
| 6 | SP-AU01 | StratoAudit 100% das operações críticas | 🔶 parcial | Cobrir operações admin hoje ausentes |
| 7 | SP-AP01 | Paginação em todas as listas da API | ✅ commit e5d0536 | Todas as GET de lista paginadas |
| 8 | SP-OP10 | Backup com RTO/RPO validados em staging | ✅ commit 83bbbc5 | Restore executado e medido em staging |
| 9 | — | OIDC Azure: verificação completa de assinatura JWKS | ✅ commit 394285d | RS256 verification, nonce, iss, aud, alg-confusion prevention |

**Entregáveis da Wave 0:**
- Nenhuma nova funcionalidade de negócio
- Zero vulnerabilidade P0 aberta
- Relatório de headers/TLS/rate-limiting validado

---

### Wave 1 — Plataforma de Produção (P0/P1 infraestrutura, semanas 4–10)

**Objetivo:** Sair do Docker Compose local para Azure enterprise com rede privada. Fechar lacunas de workspace e membros.

| # | ID | Requisito | Prioridade |
|---|----|-----------|-----------|
| 1 | SP-OP01 | IaC Terraform: VNet, subnets, NSGs | P0 |
| 2 | SP-OP02 | Private Endpoints + DNS privado | P0 |
| 3 | SP-OP03 | AKS control/data plane separados | P0 |
| 4 | SP-OP04 | GitOps com canário e rollback | P0 |
| 5 | SP-MT01 | Suite de testes de isolamento cross-workspace | P0 |
| 6 | SP-MT02 | Lifecycle completo de workspace | P0 |
| 7 | SP-MT03 | Cota de membros por workspace | P0 |
| 8 | SP-MT04 | Workspace inativo bloqueia acesso | P0 |
| 9 | SP-MT05 | platform_admin global | P0 |
| 10 | SP-U01 | Reset de senha por workspace_admin | P0 |
| 11 | SP-U02 | Reset de MFA por workspace_admin | P0 |
| 12 | SP-U03 | Regra: admin não reseta admin igual/superior | P0 |
| 13 | SP-A01 | Forçar troca de senha configurável | P0 |
| 14 | SP-A04 | Validação de origin/referer no login | P0 |
| 15 | SP-EC01 | WorkspaceBudget configurável | P0 |
| 16 | SP-SM01 | Rotação automática de segredos ≤ 30 dias | P0 |
| 17 | SP-AP03 | SMTP configurável | P1 |
| 18 | SP-U04 | Convite de membro com email | P1 |
| 19 | SP-WK01 | DLQ com alertas | P1 |
| 20 | SP-WK02 | Workers resilientes por workspace | P1 |
| 21 | SP-AP02 | Idempotency keys (✅ commit 7b7ff19) | P1 |
| 22 | SP-CL04 | Consolidação CloudAccount | P1 |
| 23 | SP-FE08 | /app/platform/workspaces | P0 |
| 24 | SP-FE02 | /forgot-password + /reset-password completos | P0 |
| 25 | SP-FE01 | Reestruturar rotas para /app/* | P0 |
| 26 | SP-SM02 | Envelope encryption com KMS | P1 |

**Migração de banco:** 0008, 0009, 0010

**Entregáveis da Wave 1:**
- Infra Azure provisionada com Terraform
- Deploy via GitOps funcional
- Lifecycle completo de workspace
- Gestão de membros completa com email
- Cookie httpOnly confirmado em produção

---

### Wave 2 — Segurança, Observabilidade e Paridade FinOps (P1, semanas 11–20)

**Objetivo:** Fechar paridade com produtos FinOps enterprise maduros. CI/CD com gates de segurança.

| # | ID | Requisito | Prioridade |
|---|----|-----------|-----------|
| 1 | SP-OP06 | OpenTelemetry end-to-end | P1 |
| 2 | SP-OP07 | SLI/SLO dashboards | P1 |
| 3 | SP-OP08 | CI com SAST/SCA/secret scan | P1 |
| 4 | SP-OP05 | WAF + rate limiting comportamental | P1 |
| 5 | SP-A06 | MFA TOTP completo | P1 |
| 6 | SP-U05 | Soft-delete de membro | P1 |
| 7 | SP-CL01 | Conector Azure Blob Storage | P1 |
| 8 | SP-RI01 | ProviderRecommendation sync (Azure Advisor) | P1 |
| 9 | SP-RI02 | Atualização de status de ProviderRecommendation | P1 |
| 10 | SP-NT01 | ActivityEvent storage | P1 |
| 11 | SP-NT02 | AlertRecord por categoria | P1 |
| 12 | SP-NT03 | NotificationPreference por membro | P1 |
| 13 | SP-NT04 | GET /notifications/new (polling) | P1 |
| 14 | SP-NT05 | PATCH notificação lida/arquivada | P1 |
| 15 | SP-NT06 | Envio por email SMTP | P1 |
| 16 | SP-EC02 | SkuObservation e módulo de SKUs | P1 |
| 17 | SP-EC03 | Exportação CSV/Excel | P1 |
| 18 | SP-EC04 | Custo detalhado com filtros e paginação | P1 |
| 19 | SP-EC05 | UsageObservation e métricas de uso | P1 |
| 20 | SP-EC07 | Painel de savings previsto vs realizado | P1 |
| 21 | SP-WK03 | Remoção de endpoints depreciados | P1 |
| 22 | SP-MT06 | Chaves de criptografia por workspace enterprise | P1 |
| 23 | SP-FE03 | /app/economics/skus | P1 |
| 24 | SP-FE04 | /app/economics/reports | P1 |
| 25 | SP-FE05 | /app/notifications | P1 |
| 26 | SP-FE09 | /app/platform/sync | P1 |

**Migração de banco:** 0011, 0012, 0013

**Entregáveis da Wave 2:**
- CI/CD com gates automáticos de segurança
- OpenTelemetry ativo em produção
- Sistema completo de notificações e alertas
- Análise de SKUs e exportação de relatórios
- Conector Azure Blob Storage funcional

---

### Wave 3 — Diferenciais Estratégicos (P2, semanas 21–32)

**Objetivo:** Entregar as capacidades de inteligência causal, experimentação avançada e ecossistema que diferenciam o StratoPulse.

| # | ID | Requisito | Prioridade |
|---|----|-----------|-----------|
| 1 | SP-WK04 | Schema Registry para contratos | P2 |
| 2 | SP-WK05 | PulseStream event log imutável | P2 |
| 3 | SP-CL05 | Conector AWS real (OIDC) | P2 |
| 4 | SP-GR01–GR04 | PulseGreen completo | P2 |
| 5 | SP-GV01–GV04 | PulseGov completo (sem grafo) | P2 |
| 6 | SP-RI03 | SCA (Stratum Causal Attribution) | P2 |
| 7 | SP-RI04 | ARI (Adaptive Recommendation Index) | P2 |
| 8 | SP-RI05 | PulseLab Simulator avançado | P2 |
| 9 | SP-RI06 | Execução canário com guardrails automáticos | P2 |
| 10 | SP-EC06 | Forecast probabilístico P50/P90 | P2 |
| 11 | SP-AU02 | ComplianceArtifact exportável e assinado | P2 |
| 12 | SP-AU03 | LGPD com retenção configurável | P2 |
| 13 | SP-AP04 | StratoGraph (GraphQL Federation) | P2 |
| 14 | SP-AP05 | AsyncAPI para contratos públicos | P2 |
| 15 | SP-AP06 | Integração Jira/Linear | P2 |
| 16 | SP-AP07 | Integração GitHub | P2 |
| 17 | SP-NT07 | Notificações por Slack | P2 |
| 18 | SP-SM03 | StratoMesh (mTLS interno) | P2 |
| 19 | SP-CL02 | Conector Azure Carbon API | P2 |
| 20 | SP-FE06 | /app/gov — PulseGov | P2 |
| 21 | SP-FE07 | /app/green — PulseGreen | P2 |
| 22 | SP-FE10 | UX por persona | P2 |
| 23 | SP-OP09 | Ambientes efêmeros por PR | P2 |

**Migração de banco:** 0014, 0015, 0016

**Entregáveis da Wave 3:**
- SCA, ARI e PulseLab Simulator operacionais
- PulseGov e PulseGreen completos
- StratoGraph (GraphQL Federation) publicado
- Integrações Jira/GitHub/Slack operacionais

---

### Wave 4 — Escala Global e Confiabilidade Enterprise (P3, semanas 33–44)

| # | ID | Requisito |
|---|----|-----------|
| 1 | SP-GV05–GV06 | TopologyMap e blast radius automático |
| 2 | SP-CL06 | Conector GCP real |
| 3 | — | Multi-região ativo-passivo com failover validado |
| 4 | — | Data residency por workspace |
| 5 | SP-OP11 | Testes de carga k6 no pipeline |
| 6 | — | Chaos engineering drills trimestrais |
| 7 | — | Pentest externo semestral |
| 8 | — | Consolidação total de nomenclatura — remover refs legadas |

**Migração de banco:** 0017 (TopologyNode/Edge no Graph DB)

---

## 12. Requisitos Não Funcionais

| ID | Requisito | Meta | Prioridade |
|----|-----------|------|-----------|
| NFR-01 | Disponibilidade da API | SLO 99.95% | P0 |
| NFR-02 | Disponibilidade da ingestão | SLO 99.7% diária por conector | P0 |
| NFR-03 | Latência p95 de query operacional | < 900 ms | P1 |
| NFR-04 | Latência p95 de mutation de workflow | < 700 ms | P1 |
| NFR-05 | Latência end-to-end de evento crítico | < 120 segundos | P1 |
| NFR-06 | Criptografia em repouso | AES-256 | P0 |
| NFR-07 | Criptografia em trânsito | TLS 1.3 | P0 |
| NFR-08 | Prazo máximo de rotação de segredos | 30 dias | P0 |
| NFR-09 | RTO em falha crítica | ≤ 30 minutos | P1 |
| NFR-10 | RPO para metadados críticos | ≤ 5 minutos | P1 |
| NFR-11 | Contas cloud por workspace enterprise | Até 2.000 | P2 |
| NFR-12 | Eventos por mês por workspace enterprise | Até 300M | P2 |
| NFR-13 | Queries sustentadas | 15k/min | P2 |
| NFR-14 | Mutações em pico | 4k/min | P2 |
| NFR-15 | Eventos de ingestão contínua | 80k/min | P2 |
| NFR-16 | Retenção de dados configurável por workspace | Por contrato (LGPD) | P1 |
| NFR-17 | MTTR de vulnerabilidade de severidade alta | < 48h | P0 |
| NFR-18 | Taxa de pass nos testes de segurança | ≥ 98% | P0 |
| NFR-19 | Cobertura de testes automatizados por domínio | > 80% | P1 |

---

## 13. Glossário de Nomenclatura

Todo o código, documentação e APIs usam exclusivamente esta nomenclatura. Referências ao legado devem ser substituídas progressivamente.

| Termo StratoPulse | Conceito | Não usar |
|------------------|---------|---------|
| `workspace` | Conta isolada de um cliente | tenant, organization, account |
| `platform_admin` | Administrador global sem workspace | super_admin, global_admin |
| `workspace_admin` | Administrador do workspace do cliente | tenant_admin, org_admin |
| `analyst` | Usuário operacional com permissões de escrita analítica | operator, editor |
| `viewer` | Usuário de leitura | read_only, consumer |
| `CloudCredential` | Credencial multi-cloud por workspace | AzureCredential, cloud_key, CloudAccount |
| `WorkspaceBudget` | Orçamento financeiro por workspace | DashboardBudgetConfig, budget |
| `ActivityEvent` | Evento de log de atividade do provider | ResourceNotification, activity_log |
| `AlertRecord` | Alerta gerado por categoria | AlertNotification, notification |
| `ProviderRecommendation` | Recomendação importada do cloud provider | AdvisorRecommendation |
| `SyncRecord` | Estado de sincronização por conector | SyncState, sync_status |
| `SkuObservation` | Observação de SKU por workspace e período | sku_fact, sku_record |
| `ResourceInventory` | Inventário de recursos para governança | GovernanceResource, resource_list |
| `CarbonRecord` | Emissão de carbono por conta e período | CarbonEmission, carbon_data |
| `CausalTrace` | Trilha de explicação causal por recomendação (SCA) | causal_explanation, attribution |
| `OptimizationExperiment` | Experimento criado no PulseLab | Initiative, optimization_task |
| `ExperimentRun` | Execução de experimento com telemetria | experiment_execution |
| `TopologyNode` | Nó no grafo TopologyMap | service_topology_node, graph_node |
| `ComplianceArtifact` | Relatório de auditoria exportável e assinado | compliance_report, audit_export |
| `StratoAudit` | Sistema de trilha de auditoria imutável | AuditLog, audit_chain |
| `PulseStream` | Event log imutável para replay | EventLog, event_store |
| `StratoGraph` | Gateway GraphQL Federation | GraphQL Gateway, api_gateway |
| `StratoMesh` | mTLS interno entre serviços (SPIFFE-based) | service_mesh, mTLS_layer |
| `SCA` | Stratum Causal Attribution — engine causal | HCA, causal_engine |
| `ARI` | Adaptive Recommendation Index — ranking adaptativo | AAR, adaptive_ranking |
| `DlqMessage` | Mensagem na dead letter queue | dead_letter, failed_message |

### 13.1 Mapeamento de Nomenclatura no Banco de Dados Atual

| Tabela/Campo Atual | Nome Target | Wave que Renomeia |
|--------------------|------------|------------------|
| `organizations` | `workspaces` | Wave 2 (migração 0010) |
| `Organization.name` | `Workspace.name` | Wave 2 |
| `cloud_accounts` | `cloud_credentials` | Wave 2 (migração 0012, SP-CL04) |
| `optimization_opportunities` | Manter + add fields | Wave 2 |
| `UserRole.ADMIN` | `UserRole.WORKSPACE_ADMIN` | Wave 1 |
| `UserRole.ENGINEER` | `UserRole.ENGINEER` | Manter |
| `UserRole.FINOPS` | `UserRole.ANALYST` | Wave 1 |
| `UserRole.EXECUTIVE` | `UserRole.VIEWER` | Wave 1 |
| `audit_chain_events` | `stratoaudit_events` | Wave 3 (renomear tabela) |

---

## 14. Critérios de Go-Live

### 14.1 Beta (ao final da Wave 1)

Condições obrigatórias:
- [ ] Todos os itens P0 das Waves 0 e 1 fechados
- [x] Lifecycle de workspace completo (criar, ativar, desativar, purgar, restaurar) ✅ commit e5d0536
- [x] Token em cookie httpOnly confirmado em staging ✅ commit 745d828 (SP-A02/SP-FE11)
- [x] Rate limiting por workspace e por IP em auth endpoints ✅ commit c8befb6
- [x] Headers de segurança passando em OWASP checker ✅ commit 27bd39c
- [ ] Deploy no AKS Azure com VNet + Private Endpoints ← pendente SP-OP01–03
- [ ] StratoAudit cobrindo 100% das operações críticas ← 🔶 parcial
- [x] Suite de testes de isolamento cross-workspace com zero vazamentos ✅ commit 67e5aee
- [x] Backup com RTO/RPO medidos e dentro das metas ✅ commit 83bbbc5
- [ ] Módulos core: PulseEconomics, alertas básicos, PulseIntel básico ← pendente Wave 2

### 14.2 GA (ao final da Wave 2)

Condições obrigatórias:
- [ ] Todos os P0/P1 fechados + Wave 2 completa
- [ ] OpenTelemetry e SLO dashboards ativos em produção
- [ ] Zero vulnerabilidade crítica aberta (SAST/SCA no CI)
- [ ] Sistema de notificações e alertas operacional
- [ ] PulseEconomics com SKUs, exportação e forecast básico
- [ ] Plano de Wave 3 com owners, datas e métricas de aceite aprovados
- [ ] Compliance artifact gerado e verificável

### 14.3 Enterprise (ao final da Wave 3)

Condições obrigatórias:
- [ ] Wave 3 completa
- [ ] SCA, ARI, PulseLab Simulator e execução canário em produção
- [ ] StratoGraph (GraphQL Federation) e AsyncAPI publicados
- [ ] Integrações Jira/Linear, GitHub e Slack operacionais
- [ ] StratoMesh (mTLS) ativo em todos os serviços
- [ ] PulseGov completo com inventário e compliance
- [ ] PulseGreen completo com emissões e breakdown

### 14.4 Métricas de Sucesso

| Categoria | Métrica | Meta |
|-----------|---------|------|
| Produto | Tempo de criação de experimento no PulseLab | < 15 minutos |
| Produto | Recomendações com evidência causal (SCA) | > 90% |
| Produto | Adoção mensal do backlog ARI | > 65% |
| Produto | Redução de desperdício cloud em 2 trimestros | 12–22% |
| Produto | Precisão do forecast P90 (erro vs realizado) | < 8% |
| Segurança | Cobertura PBAC/ABAC ativas | > 95% |
| Segurança | Incidentes de autorização indevida críticos | 0 |
| Segurança | MTTR de vulnerabilidade alta | < 48h |
| Segurança | Taxa de pass nos testes de segurança | ≥ 98% |
| Negócio | Net Revenue Retention | > 115% |
| Qualidade | Cobertura de testes por domínio | > 80% |
| Operação | SLO da API em produção | 99.95% |
| Operação | RTO em falha crítica | ≤ 30 min |
| Operação | Zero vulnerabilidade crítica aberta | 0 |

---

## Apêndice A — Estrutura de Diretórios Target

```
backend/
├── app/
│   ├── main.py
│   ├── api/
│   │   └── v1/
│   │       ├── router.py
│   │       └── (um router por domínio)
│   ├── core/
│   │   ├── config.py
│   │   ├── security.py          # JWT, Fernet, bcrypt, TOTP
│   │   ├── middleware.py         # Rate limit, headers, CORS
│   │   ├── policy.py             # PBAC/ABAC runtime
│   │   ├── dependencies.py       # DI: get_current_user, get_workspace
│   │   ├── database.py
│   │   ├── redis.py
│   │   ├── clickhouse.py
│   │   ├── smtp.py               # NOVO: email sending
│   │   ├── slack.py              # NOVO: Slack webhooks
│   │   └── logging.py
│   ├── domains/
│   │   ├── auth/                 # Existente
│   │   ├── workspaces/           # NOVO (extrai de auth, expande Organization)
│   │   ├── members/              # NOVO (extrai de auth/users, expande User)
│   │   ├── economics/            # NOVO (unifica cloud_ledger + executive + budget)
│   │   ├── intel/                # NOVO (renomeia decision_engine + provider recs)
│   │   ├── lab/                  # NOVO (renomeia experiments)
│   │   ├── notifications/        # NOVO (AlertRecord, NotificationPreference)
│   │   ├── gov/                  # NOVO (ResourceInventory, labels, TopologyMap)
│   │   ├── green/                # NOVO (CarbonRecord)
│   │   ├── pulse_link/           # NOVO (renomeia connectors + cloud_accounts)
│   │   ├── risk_budgets/         # Existente
│   │   ├── change_events/        # Existente
│   │   ├── policy/               # Existente
│   │   ├── audit_chain/          # Existente → StratoAudit
│   │   └── workflow/             # Existente → Initiatives
│   └── workers/
│       ├── runner.py
│       ├── ingestion_worker.py
│       ├── scoring_worker.py
│       ├── audit_checkpoint_worker.py
│       ├── recommendation_sync_worker.py   # NOVO
│       ├── alert_worker.py                 # NOVO
│       ├── notification_dispatcher.py      # NOVO
│       ├── activity_sync_worker.py         # NOVO
│       ├── inventory_sync_worker.py        # NOVO
│       ├── carbon_sync_worker.py           # NOVO
│       ├── dlq_monitor_worker.py           # NOVO
│       ├── forecast_worker.py              # NOVO
│       ├── causal_attribution_worker.py    # NOVO
│       └── lgpd_purge_worker.py            # NOVO
├── alembic/
│   └── versions/
│       ├── (0001–0007 já existem)
│       ├── 0008_workspace_budget_password_reset.py
│       ├── 0009_mfa_totp_member_invite.py
│       ├── 0010_workspace_lifecycle.py
│       ├── 0011_notifications_alerts.py
│       ├── 0012_provider_recommendations_sync.py
│       ├── 0013_cost_forecast_skus.py
│       ├── 0014_causal_traces.py
│       ├── 0015_resource_inventory_carbon.py
│       ├── 0016_compliance_artifacts.py
│       └── 0017_topology_graph.py
└── tests/
    ├── unit/
    └── integration/
        ├── (8 suítes existentes)
        ├── test_workspace_lifecycle.py
        ├── test_cross_workspace_isolation.py
        ├── test_notifications.py
        ├── test_economics.py
        ├── test_pulse_gov.py
        ├── test_pulse_green.py
        └── test_platform_admin.py
```

---

## Apêndice B — Segurança: Checklist por Wave

### Wave 0 (obrigatório antes de qualquer deploy em staging/prod)
- [x] OWASP headers 100% no middleware (commit 27bd39c)
- [x] TLS enforced em todos os datastores (commit fa6c1a4)
- [x] Rate limiting por org_id implementado (commit c8befb6)
- [ ] Token httpOnly em todo o frontend ← **pendente SP-A02/SP-FE11**
- [ ] Scope validation no CloudCredential ← **pendente SP-CL03**

### Wave 1 (obrigatório para Beta)
- [ ] Key Vault rotation policy ≤ 30 dias ← pendente SP-SM01
- [ ] Private Endpoints para todos os datastores ← pendente SP-OP02
- [ ] Network Policies no AKS (deny-all + allow-list) ← pendente SP-OP03
- [x] Workspace inativo retorna 403 imediatamente (commit e5d0536)
- [x] Suite cross-workspace zerada em CI (commit 67e5aee)

### Wave 2 (obrigatório para GA)
- [ ] SAST no CI (Bandit/Semgrep) sem criticals
- [ ] SCA no CI (Safety) sem CVEs críticas não mitigadas
- [ ] Secret scan no CI (trufflehog) sem segredos reais
- [ ] WAF com regras OWASP em frente à API
- [ ] OpenTelemetry capturando security events

### Wave 3 (obrigatório para Enterprise)
- [ ] StratoMesh (mTLS) ativo entre todos os serviços
- [ ] Certificados SPIFFE rotacionando automaticamente
- [ ] AsyncAPI spec sem exposição de dados sensíveis
- [ ] Pentest externo semestral documentado
- [ ] LGPD purge worker validado em staging

---

*StratoPulse — PRD de Implementação Completa v2.0 | Confidencial | Abril 2026*

*Documento gerado a partir de auditoria técnica real do repositório em 07/04/2026*
