<div align="center">

# ⚡ CauSium

### Cloud Efficiency Intelligence Platform

**Otimize custo sem quebrar confiabilidade. Com governança forte e execução segura.**

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react&logoColor=black)](https://reactjs.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6?style=flat-square&logo=typescript&logoColor=white)](https://typescriptlang.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-4169E1?style=flat-square&logo=postgresql&logoColor=white)](https://postgresql.org)
[![ClickHouse](https://img.shields.io/badge/ClickHouse-OLAP-FFCC01?style=flat-square&logo=clickhouse&logoColor=black)](https://clickhouse.com)
[![OpenTelemetry](https://img.shields.io/badge/OpenTelemetry-Tracing-425CC7?style=flat-square&logo=opentelemetry&logoColor=white)](https://opentelemetry.io)
[![License](https://img.shields.io/badge/License-Proprietary-red?style=flat-square)](LICENSE)

</div>

---

> **Stop wasting money on cloud.**  
> CauSium turns cloud cost data into safe, governed optimization decisions.  
> **FinOps Intelligence & Governed Execution Platform — SAFE DSS até Sprint 12.**

---

## Índice

- [Por que CauSium?](#-por-que-causium)
- [Status Sprint 12 — SAFE DSS](#-status-sprint-12--safe-dss)
- [Arquitetura Geral do Sistema](#-arquitetura-geral-do-sistema)
- [Fluxo Principal do Produto](#-fluxo-principal-do-produto)
- [Fluxo SAFE DSS](#-fluxo-safe-dss)
- [Módulos do Produto](#-módulos-do-produto)
- [Status por Módulo](#-status-por-módulo)
- [Segurança](#-segurança)
- [LGPD — LGPD BASIC READY](#-lgpd--lgpd-basic-ready)
- [Platform Admin e Support Access](#-platform-admin-e-support-access)
- [Modelo de Dados](#-modelo-de-dados)
- [Workers e Processamento](#-workers-e-processamento)
- [Multi-Cloud Connectors](#-multi-cloud-connectors)
- [Convite e Primeiro Acesso](#-convite-e-primeiro-acesso)
- [APIs](#-apis)
- [PulseIntel IA](#-pulseintel-ia)
- [Observabilidade](#-observabilidade)
- [Infraestrutura e Deploy](#-infraestrutura-e-deploy)
- [Recent Enhancements](#-recent-enhancements)
- [Enterprise Multi-Subscription Support](#-enterprise-multi-subscription-support--may-2026)
- [Roadmap — Sprint 13–22](#-roadmap--sprint-1322)
- [Stack Tecnológica](#-stack-tecnológica)
- [Configuração e Setup](#-configuração-e-setup)
- [Testes](#-testes)
- [Métricas de Sucesso](#-métricas-de-sucesso)
- [Glossário](#-glossário)

---

## 💡 Por que CauSium?

Dashboards FinOps tradicionais mostram o problema mas não fecham o ciclo. Ferramentas de automação pura executam rápido mas sem governança aumentam risco operacional.

O CauSium resolve esse gap:

| Camada | O que entrega | Status |
|--------|--------------|--------|
| **Visibilidade** | Dashboard multi-cloud, KPIs, anomalias, forecast | ✅ DONE |
| **Inteligência** | VM rightsizing, AKS, anomaly detection, explain IA | ✅/⚠️ |
| **Governança** | Risk budgets, approval workflow, audit imutável | ✅ DONE |
| **Execução** | Execution plan, PulseLab handoff, tracking | ⚠️ PARTIAL |
| **Automação** | Execução cloud opt-in, policy engine, rollback | 🧭 Sprint 13+ |

---

## ✅ Status Sprint 12 — SAFE DSS

O CauSium no Sprint 12 opera como **Decision Support System (DSS) puro**.

```
✅ Recomenda      ✅ Prioriza       ✅ Planeja
✅ Aprova         ✅ Agenda         ✅ Handoff para PulseLab
✅ Rastreia       ✅ Mede resultado ✅ Feedback loop
❌ NÃO executa mutação automática em infraestrutura cloud
```

### Guardrails de Segurança Implementados

| Artefato | Localização | Propósito |
|----------|-------------|-----------|
| CI mutation guardrail | `scripts/cloud_mutation_guardrail.py` | Bloqueia padrões mutativos no PR |
| Allowlist auditável | `.security/cloud_mutation_guardrail_allowlist.txt` | Exceções com justificativa |
| PR template | `.github/pull_request_template.md` | Checklist cloud safety no PR |
| Onboarding guide | `docs/security/cloud-read-only-onboarding.md` | Credenciais somente leitura |

```bash
# Validação local do guardrail
python scripts/cloud_mutation_guardrail.py \
  --target backend/app \
  --allowlist .security/cloud_mutation_guardrail_allowlist.txt
```

**Padrões bloqueados pelo CI:**
`begin_create_or_update` · `create_or_update` · `run_instances` · `stop_instances` · `delete_resource` · `.patch(` · `resize` · `scale` · `setIamPolicy`

---

## 🏗️ Arquitetura Geral do Sistema

```mermaid
flowchart TB
    USR([Usuário])

    subgraph FE["Frontend — React + TypeScript"]
        UI[24 páginas React + Tailwind\nDashboard · Oportunidades · PulseLab\nPlan · Admin · Settings]
    end

    subgraph BE["Backend — FastAPI"]
        AUTH[Auth / RBAC\nPasskey · OIDC · JWT · MFA]
        DE[Decision Engine\nVM · AKS Nodepool · AKS Autoscaler]
        INTEL[PulseIntel\nExplain Cost · Anomaly Detection]
        PLAN[Optimization Plan\nExecution Plan]
        LAB[PulseLab\nExperimentos + State Machine]
        ADM[Admin Domain\nSupport Access · DLQ · Orgs]
    end

    subgraph WORKERS["Workers Assíncronos — 10 workers"]
        W1[ingestion_worker]
        W2[scoring_worker]
        W3[anomaly_detection_worker]
        W4[export_worker]
        W5[maintenance_worker LGPD]
        W6[audit_checkpoint_worker]
        W7[keyring_rotation_worker]
        W8[notification_worker]
        W9[carbon_sync_worker]
        W10[usage_observation_worker]
    end

    subgraph DB["Dados"]
        PG[(PostgreSQL\nOLTP — metadados\nauditoria · usuários)]
        CH[(ClickHouse\nOLAP — custos\nuso · carbono)]
        RD[(Redis\nQueues · Blacklist\nCache · Rate limit)]
    end

    subgraph CLOUD["Cloud Providers — READ ONLY"]
        AZ[Azure\nCost Mgmt · Advisor · Carbon]
        AWS[AWS\nCUR S3 · Trusted Advisor]
        GCP[GCP\nBigQuery · Recommender]
    end

    subgraph AUD["Auditoria + IA"]
        CHAIN[StratoAudit\nHash Chain SHA-256\nHMAC Checkpoints]
        AI[AI Explain Layer\nOpenAI / Mock]
    end

    USR --> FE --> BE
    BE --> PG & CH & RD
    BE --> CHAIN & AI
    CLOUD -->|read-only ingestion| WORKERS
    WORKERS --> PG & CH & RD
```

---

## 🔄 Fluxo Principal do Produto

```mermaid
flowchart LR
    A[☁️ Coletar\ndados cloud\nAzure · AWS · GCP] --> B[📊 Analisar\ncusto e uso\nClickHouse]
    B --> C[🔍 Detectar\nOportunidades\nanomaly + scoring]
    C --> D[🧠 Gerar\nRecomendações\nVM · AKS · Autoscaler]
    D --> E[📋 Optimization Plan\nPriorização\nConfidence Calibration]
    E --> F[📝 Execution Plan\ncriação + scheduling]
    F --> G{👤 Aprovação\nHumana}
    G -->|Rejeitado| E
    G -->|Aprovado| H[📅 Scheduling\nHandoff PulseLab]
    H --> I[🧪 PulseLab\nExperimento criado]
    I --> J[📈 Tracking\nresultado real]
    J --> K[🔁 Feedback Loop\nConfidence Calibration\natualizada]
    K --> E

    style G fill:#f0ad4e,color:#000
    style A fill:#d9edf7
    style K fill:#dff0d8
```

> ⚠️ **Sprint 12 SAFE DSS:** nenhuma etapa executa mutação real em cloud. A execução após aprovação é sempre responsabilidade do operador. Automação cloud opt-in chega no Sprint 13.

---

## 🛡️ Fluxo SAFE DSS

```mermaid
sequenceDiagram
    participant SYSTEM as CauSium
    participant HUMAN as Operador / FinOps
    participant CLOUD as Cloud Provider

    SYSTEM->>HUMAN: Recomendação gerada\n(savings · risk · confidence · evidence)
    HUMAN->>SYSTEM: Revisão da oportunidade
    HUMAN->>SYSTEM: Aprovação explícita no Execution Plan
    SYSTEM->>SYSTEM: Persiste plano + scheduling\n+ audit event
    SYSTEM->>HUMAN: Handoff — PulseLab experiment criado
    HUMAN->>CLOUD: Operador aplica mudança manualmente
    CLOUD-->>HUMAN: Resultado observado
    HUMAN->>SYSTEM: Resultado registrado no tracking
    SYSTEM->>SYSTEM: ConfidenceCalibration atualizada\npara categoria/region/provider

    Note over SYSTEM,CLOUD: ❌ CauSium NÃO executa mutação cloud automática até Sprint 13+
```

---

## 📦 Módulos do Produto

```
CauSium
├── PulseEconomics   → Dashboard financeiro, KPIs, SKUs, forecast, exportação async
├── PulseIntel       → Explain cost, explain opportunity, anomaly detection
├── PulseLab         → Criação e tracking de experimentos (state machine 7 estados)
├── PulseGov         → Governança de recursos, labels, inventário  [PARTIAL — Wave 3]
├── PulseGreen       → Emissões de carbono, tendências             [PARTIAL]
├── PulseLink        → Conectores multi-cloud (Azure, AWS CUR, GCP BigQuery)
├── DecisionEngine   → VM rightsizing, AKS nodepool, AKS autoscaler, confidence calibration
├── OptimizationPlan → Priorização, backlog adaptativo
├── ExecutionPlan    → Aprovação, scheduling, handoff, tracking    [PARTIAL]
├── Admin            → Support access, DLQ, org lifecycle (platform_admin)
├── StratoAudit      → Trilha imutável SHA-256 + HMAC checkpoints
└── PulseOps         → Infraestrutura, observabilidade, CI/CD
```

---

## 📊 Status por Módulo

| Módulo | Status | Detalhes |
|--------|:------:|---------|
| Autenticação (Passkey, TOTP, OIDC, backup codes) | ✅ | WebAuthn FIDO2, TOTP HMAC customizado, refresh tokens, blacklist JWT |
| Multi-tenant / Workspaces | ✅ | Lifecycle ACTIVE/SUSPENDED/ARCHIVED, member quota, workspace keyrings |
| Perfis, Membros e Convites | ✅ | CRUD, invite flow, must_change_password, LGPD consent |
| Cost Visibility (dashboard, KPIs, SKUs, export) | ✅ | Dashboard, costs, SKUs, async CSV/Excel export; subscription friendly names; cost variance alert banner; multi-subscription reconciliation; English-only UI |
| Alertas e Notificações (SMTP + Slack) | ✅ | AlertRecord, AlertRule, NotificationPreference, DLQ, WebSocket stream |
| VM Rightsizing | ✅ | Engine + scoring + oportunidade + explain IA |
| Anomaly Detection | ⚠️ | Worker + service implementados; UI de alertas em amadurecimento |
| AKS Nodepool Rightsizing | ⚠️ | Engine implementada; integração com dados reais AKS pendente |
| AKS Autoscaler Recommendation | ⚠️ | Engine implementada; integração com dados reais AKS pendente |
| Optimization Plan | ✅ | Priorização, backlog, confidence calibration |
| Execution Plan | ⚠️ | Modelo + serviço + tracking implementados; aprovação/scheduling UI parcial |
| Approval / Scheduling / Handoff | ⚠️ | Experiment approvals OK; Execution Plan approval parcial |
| Execution Tracking | ⚠️ | Status tracking implementado; automação Sprint 13 |
| Confidence Calibration / Adaptive Decision Engine | ⚠️ | Base implementada; ARI completo Wave 3 |
| Platform Admin (/admin) | ✅ | Org lifecycle, DLQ, support access auditado |
| Support Access | ✅ | Sessões time-bounded (≤60 min), reason obrigatório, read-only, auditado |
| LGPD | ✅ | **LGPD BASIC READY** — ver seção LGPD |
| Security Guardrails | ✅ | CI guardrail, /health/metrics protegidos, Azure mock bloqueado em prod |
| Cloud Read-only Model | ✅ | Todos os conectores read-only; zero create/update/delete cloud |
| PulseGov (governança) | ⚠️ | Backend domain + frontend page existem; features Wave 3 |
| PulseGreen (carbono) | ⚠️ | Carbon worker + modelo + frontend page; features Wave 3 |
| PulseIntel SCA/ARI avançado | 🧭 | Wave 3 |
| Semi-automação cloud opt-in | 🧭 | Sprint 13 |
| Policy Engine / guardrails avançados | 🧭 | Sprint 14 |
| Rollback / execution safety avançado | 🧭 | Sprint 15 |
| Controlled Automation | 🧭 | Sprint 16 |
| Cost Intelligence / Forecast P90 | 🧭 | Sprint 17 |
| What-if Simulation | 🧭 | Sprint 18 |
| Unit Economics | 🧭 | Sprint 19 |
| Enterprise Governance | 🧭 | Sprint 20 |
| AI Copilot | 🧭 | Sprint 21 |
| Autonomous FinOps | 🧭 | Sprint 22 |

---

## 🔐 Segurança

### Diagrama de Camadas de Proteção

```mermaid
flowchart TB
    subgraph L1["L1 — Perímetro"]
        RL[Rate Limiting Redis\nPor IP + Por Workspace]
        CORS[CORS Restritivo\npor ambiente]
        HDR[Security Headers\nCSP · HSTS · X-Frame · nosniff]
    end

    subgraph L2["L2 — Identidade"]
        PK[Passkey WebAuthn\nFIDO2 + ECDSA]
        OIDC[Azure OIDC\nEntra ID federation]
        JWT[JWT HS256\nAccess 60min + Refresh 7d]
        MFA[MFA TOTP customizado\n+ Backup Codes]
        BL[Token Blacklist\nRedis + PostgreSQL]
    end

    subgraph L3["L3 — Autorização"]
        RBAC[RBAC por Role\nplatform_admin · admin · engineer · viewer]
        ORG[Org Isolation\nmulti-tenant org-scoped]
        SA[Support Access\nRead-only · max 60min · Auditado]
    end

    subgraph L4["L4 — Dados"]
        ENC[Fernet Workspace Keyrings\nOrg-scoped + rotação 30d]
        TLS[TLS 1.3\nTodos datastores em produção]
        IDMPT[Idempotency Keys\nSHA-256 + TTL 24h]
        MON[Internal Monitoring Key\n/health/detailed e /metrics protegidos]
    end

    subgraph L5["L5 — Cloud Safety"]
        RO[Cloud Read-only\nZero mutação automática]
        CIG[CI Mutation Guardrail\nBloqueia padrões mutativos em PR]
        MOCK[Azure Mock\nBloqueado em APP_ENV=production]
        WARN[Azure Owner/Contributor\nWarning no onboarding]
    end

    subgraph L6["L6 — Auditoria"]
        CHAIN[StratoAudit SHA-256\nHash chain encadeado]
        HMAC[Checkpoints HMAC-SHA256\nPeríodos auditáveis]
    end

    L1 --> L2 --> L3 --> L4 --> L5 --> L6
```

### Fluxo de Autenticação — Passkey-First

```mermaid
sequenceDiagram
    participant USR as Usuário
    participant APP as Frontend
    participant API as FastAPI
    participant DB  as PostgreSQL

    USR->>APP: Clica Login com Passkey
    APP->>API: POST /auth/passkey/login/options {email}
    API->>DB: Busca user + PasskeyCredentials
    API->>APP: {challenge, credential_ids, rpId}
    APP->>USR: Prompt authenticator (Touch ID, Face ID)
    USR->>APP: Assina challenge com chave privada
    APP->>API: POST /auth/passkey/login/verify {assertion}
    API->>API: Verifica ECDSA + sign_count anti-replay
    API->>DB: Atualiza sign_count + last_login
    API->>APP: {access_token, refresh_token}
    APP->>USR: Redirect para /app
```

### Notas de Segurança

| Ponto | Detalhe |
|-------|---------|
| `/health/detailed` e `/metrics` | Protegidos por `_require_internal_monitoring_key` — não são públicos em produção |
| Azure Mock fallback | Bloqueado quando `APP_ENV=production` — sem dados simulados silenciosos |
| Azure Owner/Contributor | `validate_cost_management_scope` detecta e emite warning; role recomendada: `Cost Management Reader` |
| Payloads de auditoria | Operações administrativas usam `target_user_id` — sem email/nome nos eventos de audit |
| Audit Chain | SHA-256 encadeado; checkpoints HMAC-assinados; eventos individuais SHA-256 puro |

### Workspace Keyrings — Criptografia Org-Scoped

Cada organização possui um keyring Fernet isolado. O `keyring_rotation_worker` rotaciona automaticamente as chaves a cada 30 dias com re-cifragem transparente de todas as credenciais.

```
WorkspaceKeyring
├── org_id           → Isolamento por tenant
├── key_version      → Versão atual
├── key_material_encrypted → Chave Fernet cifrada com master key
└── rotated_at       → Timestamp da última rotação
```

### Audit Chain — Hash Encadeado

```
event_hash = SHA256(
  prev_hash | org_id | actor_user_id | event_type
  | entity_type | entity_id | canonical_payload | created_at
)
```

Integridade verificável via `GET /audit/verify`. Checkpoints periódicos HMAC-assinados criam períodos auditáveis independentes.

---

## 🛡️ LGPD — LGPD BASIC READY

> **Status: LGPD BASIC READY** — Os dois bloqueadores críticos (exclusão real + retenção automática) foram resolvidos no Sprint 12.

### Fluxo de Anonimização (Art. 18 LGPD)

```mermaid
flowchart TD
    A([Solicitação de exclusão\nou admin_delete_user]) --> B[anonymize_user_identity]
    B --> C["email → deleted_{sha256_hash}@deleted.invalid\nirreversível · sem PII"]
    B --> D["full_name → 'Deleted User'"]
    B --> E[deleted_at = now UTC]
    B --> F[is_active = False]
    C & D & E & F --> G[Audit event gravado\nSEM PII no payload\napenas target_user_id]
    G --> H{30 dias após\ndeleted_at?}
    H -->|Não| I[Aguarda]
    H -->|Sim| J[maintenance_worker\n_run_user_retention_anonymization\nroda a cada 6h]
    J --> K[anonymize_user_identity idempotente\ngarante estado final limpo]

    style C fill:#dff0d8
    style D fill:#dff0d8
    style G fill:#dff0d8
    style K fill:#dff0d8
```

### `lgpd_purge_user` — Direito ao Esquecimento (Art. 18 VI)

Endpoint de purga completa — vai além do soft-delete:

```
1. anonymize_user_identity  (email + full_name → hashes/placeholder)
2. hashed_password          → token aleatório seguro
3. totp_secret_encrypted    → None
4. PasskeyCredential        → deletados
5. RevokedToken             → deletados
6. deleted_at               = now
7. Audit event              SEM PII (actor_role + self_requested apenas)
```

Pode ser solicitado pelo próprio usuário ou por admin/platform_admin.

### Status LGPD por Categoria

| Categoria LGPD | Status | Detalhe |
|----------------|:------:|---------|
| Consentimento (Art. 7/8) | ✅ | `terms_accepted_at` + `terms_version` no modelo User |
| Criptografia de segredos | ✅ | Fernet org-scoped (TOTP, credenciais cloud), rotação 30d |
| Controle de acesso | ✅ | RBAC + support access auditado ≤60 min |
| Auditoria | ✅ | AuditChain SHA-256; payloads admin sem PII |
| Exclusão real (Art. 18) | ✅ | `anonymize_user_identity` + `lgpd_purge_user` |
| Retenção automática (Art. 15) | ✅ | `maintenance_worker` anonimiza 30 dias após `deleted_at` |
| Compartilhamento (OpenAI) | ⚠️ | Contexto de custos apenas (sem PII); DPA formal pendente |
| Audit chain HMAC por evento | ⚠️ | Apenas checkpoints HMAC-assinados; eventos individuais SHA-256 puro |
| LGPD FULL | 🧭 | Catálogo de bases legais, automação de prazos, relatórios de conformidade |

---

## 🏛️ Platform Admin e Support Access

### Domínio Admin (`/admin`) — exclusivo `platform_admin`

```
/admin/orgs                          → Lista todas as organizações
/admin/orgs/{id}                     → Detalhe de org
/admin/orgs/{id}/users               → Usuários da org
/admin/orgs/{id}/suspend             → Suspender workspace (+ reason)
/admin/orgs/{id}/restore             → Restaurar workspace (+ reason)
/admin/orgs/{id}/archive             → Arquivar workspace (irreversível, + reason)
/admin/dlq                           → Lista mensagens DLQ
/admin/dlq/{id}/requeue              → Reprocessar mensagem DLQ
/admin/observability/slo             → SLO snapshot
/admin/support-access                → Criar sessão de suporte
/admin/support-access/active         → Sessões ativas
/admin/support-access/{id}/end       → Encerrar sessão
/admin/orgs/{id}/subscriptions/discover → Preview subscriptions (read-only)
/admin/orgs/{id}/subscriptions/backfill → Backfill catálogo (dry_run=true default)
```

### Fluxo Support Access

```mermaid
sequenceDiagram
    participant PA as platform_admin
    participant API as Admin API
    participant DB as PostgreSQL
    participant AUD as AuditChain

    PA->>API: POST /admin/support-access\n{target_org_id, reason, duration_minutes ≤ 60}
    API->>API: Valida reason obrigatório\nduration entre 1 e 60 min
    API->>DB: Cria SupportAccessSession\nstatus=ACTIVE · expires_at calculado
    API->>AUD: support_access.started\n{session_id, actor, org, reason, expires_at}
    API->>PA: {session_id, expires_at}

    Note over PA,DB: Acesso read-only ao workspace do cliente durante a sessão

    alt Encerramento manual
        PA->>API: POST /admin/support-access/{id}/end {reason}
        API->>DB: status=ENDED · ended_at=now
        API->>AUD: support_access.ended {session_id, actor, reason}
    else Expiração automática
        Note over API,DB: maintenance_worker expira sessões vencidas
    end
```

### Workspace Lifecycle (Platform Admin)

```mermaid
stateDiagram-v2
    [*] --> ACTIVE : workspace criado
    ACTIVE --> SUSPENDED : force_suspend + reason
    SUSPENDED --> ACTIVE : force_restore + reason
    SUSPENDED --> ARCHIVED : force_archive + reason
    ACTIVE --> ARCHIVED : force_archive + reason
    ARCHIVED --> [*] : estado permanente

    SUSPENDED : SUSPENDED\nacesso bloqueado imediatamente
    ARCHIVED : ARCHIVED\ndados preservados · irreversível
```

> Todos os eventos de lifecycle são gravados no `AuditChain` com `actor_user_id`, `from_state`, `to_state` e `reason`.

---

## 🗄️ Modelo de Dados

### Diagrama ER — Entidades Principais

```mermaid
erDiagram
    Organization ||--o{ User : "tem"
    Organization ||--o{ CloudAccount : "tem"
    Organization ||--o{ WorkspaceKeyring : "tem"
    Organization ||--o{ SupportAccessSession : "recebe"
    Organization ||--o{ AuditChainEvent : "tem"

    User ||--o{ PasskeyCredential : "tem"
    User ||--o{ TotpBackupCode : "tem"

    CloudAccount ||--o{ CloudAccountSubscription : "tem"
    CloudAccount ||--o{ CostFact : "gera"
    CloudAccount ||--o{ UsageObservation : "gera"

    UsageObservation }o--|| Opportunity : "alimenta"
    Opportunity ||--o{ ExecutionPlan : "gera"
    Opportunity }o--|| ConfidenceCalibration : "atualiza"
    ExecutionPlan ||--o{ Experiment : "pode criar"

    Organization {
        uuid id PK
        string name
        string slug
        enum lifecycle_state
        int member_quota
    }

    User {
        uuid id PK
        uuid org_id FK
        string email
        string full_name
        bool is_active
        datetime deleted_at
        datetime terms_accepted_at
        string terms_version
    }

    Opportunity {
        uuid id PK
        string category
        float estimated_savings_usd
        float confidence
        string risk_level
        json decision_evidence
    }

    ExecutionPlan {
        uuid id PK
        uuid opportunity_id FK
        enum status
        datetime scheduled_at
        string handoff_type
    }

    ConfidenceCalibration {
        uuid id PK
        uuid org_id FK
        string dimension_type
        string dimension_key
        float calibration_factor
    }

    SupportAccessSession {
        uuid id PK
        uuid actor_user_id FK
        uuid target_org_id FK
        string reason
        enum status
        datetime expires_at
        datetime ended_at
    }
```

### Storage Políglota

```mermaid
graph LR
    subgraph PG["PostgreSQL — OLTP"]
        P1[Users · Orgs · Auth]
        P2[Experiments · ExecutionPlan]
        P3[Audit Chain · Checkpoints]
        P4[DLQ · Export Jobs]
        P5[SupportAccessSession]
        P6[ConfidenceCalibration]
    end

    subgraph CH["ClickHouse — OLAP"]
        C1[cost_facts]
        C2[event_facts]
        C3[sku_observations]
        C4[usage_observations]
        C5[carbon_records]
    end

    subgraph RD["Redis"]
        R1[Worker Queues]
        R2[Idempotency Keys SHA-256]
        R3[Token Blacklist]
        R4[Rate Limit Counters]
    end
```

### Migrações Alembic — 41 migrações (0001–0041)

| # | Arquivo | Conteúdo |
|---|---------|---------|
| 0001 | `initial_schema.py` | workspaces, users, cloud_accounts, opportunities, initiatives |
| 0002 | `experiments_risk_budgets_change_events.py` | risk_budgets, experiments, runs, change_events |
| 0003 | `audit_chain_events.py` | audit_chain_events (hash chain) |
| 0004 | `experiment_policy_approvals.py` | experiment_approvals, policy_bundles, policy_decision_evidences |
| 0005 | `policy_bundle_and_evidence.py` | Índices e constraints de política |
| 0006 | `passkey_first_auth.py` | auth_challenges, passkey_credentials |
| 0007 | `audit_chain_checkpoints.py` | audit_chain_checkpoints (HMAC snapshots) |
| 0008a | `workspace_lifecycle.py` | lifecycle_state, member_quota |
| 0008b | `notifications_alerts.py` | ActivityEvent, AlertRecord, NotificationPreference |
| 0009 | `workspace_invites.py` | MemberInvite, invite tokens |
| 0010 | `platform_admin_role.py` | platform_admin role, org scoping |
| 0011 | `force_password_change.py` | must_change_password flag |
| 0012 | `workspace_budget.py` | WorkspaceBudget |
| 0013 | `cloud_account_scope_validation.py` | Scope validation em cloud credentials |
| 0014 | `dlq_messages.py` | DlqMessage (dead letter queue) |
| 0015 | `notification_preferences.py` | NotificationPreference refinements |
| 0016 | `notification_slack_configs.py` | SlackNotificationConfig |
| 0017 | `activity_events.py` | ActivityEvent indexing |
| 0018 | `notification_alert_rules.py` | AlertRule por categoria |
| 0019 | `auth_totp_mfa.py` | TOTP setup/verify/enable/disable |
| 0020 | `report_export_jobs.py` | ReportExportJob (async export) |
| 0021 | `workspace_keyrings.py` | WorkspaceKeyring (Fernet org-scoped) |
| 0022 | `blob_ingestion_checkpoints.py` | BlobIngestionCheckpoint (Azure Blob) |
| 0023 | `aws_cur_ingestion_checkpoints.py` | AwsCurIngestionCheckpoint (AWS CUR S3) |
| 0024 | `provider_recommendation_sync.py` | ProviderRecommendation, SyncRecord |
| 0025 | `merge_workspace_lifecycle.py` | Merge de lifecycle |
| 0026 | `lgpd_consent.py` | LGPD consent (base legal, propósito, versão) |
| 0027 | `totp_backup_codes.py` | TotpBackupCode (10 códigos one-time) |
| 0028 | `alert_delivery_tracking.py` | AlertDeliveryLog |
| 0029 | `revoked_tokens.py` | RevokedToken (blacklist JWT PostgreSQL) |
| 0030 | `cost_anomalies.py` | Cost anomaly detection |
| 0031 | `opportunity_sku_family.py` | SKU family em oportunidades |
| 0032 | `usage_observations.py` | Usage observations table |
| 0033 | `opportunity_decision_evidence.py` | Decision evidence em oportunidades |
| 0034 | `opportunity_category_aks_nodepool_rightsizing.py` | Categoria AKS nodepool |
| 0035 | `opportunity_category_aks_autoscaler_recommendation.py` | Categoria AKS autoscaler |
| 0036 | `execution_plans.py` | Execution plans |
| 0037 | `confidence_calibrations.py` | Confidence calibration (Adaptive Engine) |
| 0038 | `support_access_sessions.py` | Support access sessions |
| 0039 | `user_deleted_at_retention.py` | LGPD — deleted_at + retenção |
| 0041 | `cloud_account_subscriptions.py` | cloud_account_subscriptions — catálogo multi-subscription enterprise |

---

## ⚙️ Workers e Processamento

### Diagrama dos 10 Workers

```mermaid
flowchart LR
    subgraph CLOUD["Cloud Providers — read-only"]
        AZ[Azure]
        AWS[AWS]
        GCP[GCP]
    end

    subgraph QUEUES["Redis Queues"]
        Q1[ingestion]
        Q2[scoring]
        Q3[notification]
        Q4[carbon]
        Q5[export]
        Q6[anomaly]
    end

    subgraph TIMERS["Timer Workers"]
        T1[audit_checkpoint\n60 min]
        T2[keyring_rotation\n30d]
        T3[maintenance\n6h LGPD]
        T4[usage_observation\nconfig interval]
    end

    subgraph STORAGE["Storage"]
        CH[(ClickHouse)]
        PG[(PostgreSQL)]
        BLOB[(Object Storage)]
    end

    AZ & AWS & GCP -->|read-only| Q1
    Q1 -->|ingestion_worker · cost_facts| CH
    Q1 -->|enqueue next| Q2
    Q2 -->|scoring_worker · Opportunities| PG
    Q3 -->|notification_worker · SMTP/Slack| BLOB
    Q4 -->|carbon_sync_worker · CarbonRecord| PG
    Q5 -->|export_worker · CSV/Excel| BLOB
    Q6 -->|anomaly_detection_worker · CostAnomaly| PG
    T1 -->|HMAC checkpoints| PG
    T2 -->|re-encrypt keyrings| PG
    T3 -->|LGPD retention + DLQ purge| PG
    T4 -->|usage_observations| PG
```

### Tabela de Workers

| Worker | Trigger | Responsabilidade |
|--------|---------|-----------------|
| `ingestion_worker` | Queue `ingestion` | Fetch custo + eventos (Azure Blob, AWS CUR S3, GCP BigQuery) → ClickHouse |
| `scoring_worker` | Queue `scoring` | Gera `OptimizationOpportunity` a partir de ClickHouse |
| `anomaly_detection_worker` | Queue `anomaly` | Detecta anomalias de custo; persiste alertas |
| `notification_worker` | Queue `notification` | Avalia regras; envia SMTP e Slack |
| `carbon_sync_worker` | Queue `carbon` | Ingere `CarbonRecord` dos provedores |
| `export_worker` | Queue `export` | Gera CSV/Excel async; upload para object storage |
| `audit_checkpoint_worker` | Timer 60 min | Cria checkpoints HMAC da StratoAudit |
| `keyring_rotation_worker` | Timer periódico | Rotaciona chaves Fernet; re-cifra credenciais |
| `maintenance_worker` | Timer 6h | **LGPD:** anonimiza usuários 30d+ após `deleted_at`; purge DLQ 30d |
| `usage_observation_worker` | Timer configurável | Consolida métricas de uso para explain IA |

### DLQ — Dead Letter Queue

Mensagens que falham 3× são movidas para DLQ e registradas em `DlqMessage`.

```
GET  /admin/dlq               → Lista mensagens
POST /admin/dlq/{id}/requeue  → Reprocessa mensagem
```

---

## ☁️ Multi-Cloud Connectors

### Diagrama de Ingestão Multi-Cloud

```mermaid
flowchart TB
    subgraph AZURE["Azure — Read Only"]
        AZ1[Cost Management API]
        AZ2[Azure Blob CUR export]
        AZ3[Carbon Emissions API]
        AZ4[Azure Advisor]
        AZ5[Resource Graph KQL]
        AZ6[Azure Monitor]
    end

    subgraph AWS["AWS — Read Only"]
        AW1[Cost Explorer API]
        AW2[S3 CUR files]
        AW3[CloudTrail Events]
        AW4[Trusted Advisor]
        AW5[Resource Tagging API]
    end

    subgraph GCP["GCP — Read Only"]
        GC1[BigQuery Billing Export]
        GC2[Carbon Footprint API]
        GC3[Cloud Logging]
        GC4[Recommender API]
        GC5[Compute Engine instances]
    end

    subgraph ENGINE["Normalized Model"]
        NORM[cost_facts · event_facts\ncarbon_records · sku_observations]
        OPP[Opportunity Generation\nVM · AKS Nodepool · AKS Autoscaler]
    end

    AZURE -->|read-only| NORM
    AWS -->|read-only| NORM
    GCP -->|read-only| NORM
    NORM --> OPP
```

> **❌ Nenhum conector executa operações de criação, alteração ou deleção de recursos cloud.**

### Segurança dos Conectores

| Ponto | Azure | AWS | GCP |
|-------|:-----:|:---:|:---:|
| Credenciais cifradas | Fernet | Fernet | Fernet |
| Mock fallback em prod | ❌ Bloqueado | N/A | N/A |
| Role warning | Owner/Contributor → warning | — | — |
| Sem credenciais | Mock (dev only) | ValueError | ADC/ValueError |

**Permissões mínimas recomendadas:**
- Azure: `Cost Management Reader`
- AWS: `ReadOnlyAccess` (ou política customizada de leitura de billing)
- GCP: `Viewer` + `BigQuery Data Viewer`

---

## 👤 Convite e Primeiro Acesso

```mermaid
sequenceDiagram
    participant ADM as Admin / platform_admin
    participant SYS as Sistema
    participant EMAIL as E-mail
    participant USR as Novo Usuário

    ADM->>SYS: POST /members/invite {email, role}
    SYS->>SYS: Gera token de convite (expires 7d)
    SYS->>EMAIL: Envia link de ativação
    EMAIL->>USR: Link /activate?token=...
    USR->>SYS: GET /activate?token — valida token
    USR->>SYS: Define senha + aceita termos
    SYS->>SYS: terms_accepted_at = now\nterms_version registrado
    SYS->>SYS: Conta ativa\nmust_change_password = false
    USR->>SYS: Login (passkey ou senha)
    SYS->>USR: access_token + redirect /app
```

---

## 🌐 APIs

### Mapa de Domínios

```
/api/v1/
├── /auth/*              → Passkey, OIDC, MFA TOTP, backup codes, LGPD purge/export
├── /cloud-accounts/*    → Conectores multi-cloud (Azure, AWS, GCP)
├── /economics/*         → Dashboard, budget, custos, SKUs, export async
├── /ledger/*            → Reservas, coverage, reconciliation, cobertura RI/Savings Plans
├── /intel/*             → Explain cost, explain opportunity, anomaly detection
├── /lab/*               → Experimentos, runs, approvals, state machine
├── /notifications/*     → Alertas, preferências, WebSocket stream
├── /gov/*               → Inventário, labels, compliance
├── /green/*             → Emissões, tendências, breakdown
├── /opportunities/*     → Scoring, status, explain IA
├── /decision-engine/*   → Optimization plan, execution plan
├── /workspaces/*        → Workspace lifecycle, membros
├── /audit/*             → StratoAudit events, checkpoints, verify
├── /risk-budgets/*      → Risk budgets por domínio/ambiente
├── /change-events/*     → Change event tracking
├── /admin/*             → platform_admin: orgs, DLQ, support-access, SLO
└── /metrics/slo         → SLO snapshot (Prometheus/Grafana)
```

> `/health/detailed` e `/metrics` requerem `X-Internal-Monitoring-Key` em produção.

### Padrão de Paginação

```json
{
  "items": [...],
  "page": 1,
  "page_size": 20,
  "total": 435,
  "has_next": true,
  "has_prev": false
}
```

### Idempotency Keys

Mutações críticas aceitam `Idempotency-Key: <uuid4>`. O backend armazena fingerprint SHA-256 no Redis (TTL 24h) — retentativas idênticas retornam o resultado original sem re-executar.

---

## 🤖 PulseIntel IA

### Explain Cost Change

```mermaid
flowchart LR
    UI[Dashboard\nExplain change CTA] --> API[POST /intel/explain-cost]
    API --> GATE{Plano\ncom IA?}
    GATE -->|Não| DENY[403 Forbidden]
    GATE -->|Sim| SVC[CostExplanationService]
    SVC --> CH1[cost_facts]
    SVC --> CH2[event_facts]
    SVC --> CH3[recommendation_facts]
    CH1 & CH2 & CH3 --> CTX[Context Builder]
    CTX --> LLM[LlmService\nmock / openai]
    LLM --> OUT[summary · causes\nimpact · recommendation\nconfidence]
    OUT --> UI
```

### Explain Recommendation (por Oportunidade)

- Endpoint: `GET /api/v1/opportunities/{opp_id}/explain?language=pt|en`
- Contexto: metadados da oportunidade + `usage_observations` 24h + `event_facts` recentes
- `decision_evidence` de AKS é interpretado automaticamente
- Fallback automático para `mock` em falha do provider

### Configuração

```bash
AI_PROVIDER=mock|openai
AI_ENABLED_PLANS=b,enterprise,growth_ai
AI_MODEL=gpt-4o-mini
AI_TIMEOUT_SECONDS=30
AI_OPENAI_API_KEY=<key>
AI_OPENAI_BASE_URL=https://api.openai.com/v1
```

---

## 📡 Observabilidade

```mermaid
flowchart LR
    APP[FastAPI] -->|OTLP gRPC| COLL[OTel Collector]
    COLL -->|traces| JAEGER[Jaeger :16686]
    COLL -->|metrics| PROM[Prometheus :9090]
    PROM --> GRAF[Grafana :3001\nDashboards + SLO]
```

**Spans instrumentados:** rotas HTTP · queries SQLAlchemy · operações Redis · chamadas cloud providers

| Serviço | URL dev | Credenciais |
|---------|---------|-------------|
| Jaeger UI | `http://localhost:16686` | — |
| Prometheus | `http://localhost:9090` | — |
| Grafana | `http://localhost:3001` | admin / admin |

**SLO endpoint:** `GET /metrics/slo` → `{api_availability_7d, p95_latency_ms, error_rate_1h, ingestion_success_rate_24h}`

---

## 🚀 Infraestrutura e Deploy

### Ambiente Local

```bash
docker compose up -d
```

| Serviço | Porta | Descrição |
|---------|-------|-----------|
| `backend` | 8000 | FastAPI + entrypoint.sh (auto-migration + uvicorn) |
| `frontend` | 3000 | nginx servindo build React |
| `postgres` | 5432 | PostgreSQL 15 |
| `redis` | 6379 | Redis 7 |
| `clickhouse` | 8123 | ClickHouse OLAP |
| `jaeger` | 16686 | Distributed Tracing UI |
| `prometheus` | 9090 | Métricas |
| `grafana` | 3001 | Dashboards + SLO |

### Produção (docker-compose.prod.yml)

- `restart: always` em todos os serviços
- Backend via **`entrypoint.sh`** — executa `alembic upgrade head` antes de iniciar uvicorn
- 4 uvicorn workers sem `--reload`
- Frontend via **nginx** (porta 80) com build de produção
- Jaeger e ferramentas de observabilidade em `profiles: [dev]`
- Sem bind-mounts de código

```bash
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml --profile dev up -d  # com observabilidade
```

### Target: Azure Enterprise (Wave 1)

```mermaid
graph TB
    USR([Usuário]) --> AFD[Azure Front Door\nWAF + Rate Limiting]

    subgraph VNet["Azure VNet Privada"]
        AFD --> NGINX[Ingress Nginx]
        NGINX --> AKS[AKS — API + Workers]

        subgraph PE["Private Endpoints"]
            PE1[(PostgreSQL)]
            PE2[(Redis)]
            PE3[(ClickHouse)]
        end

        AKS --> PE1 & PE2 & PE3
        KV[Azure Key Vault\nSegredos + KMS] --> AKS
        ARGO[ArgoCD GitOps] --> AKS
    end
```

---

## 🆕 Recent Enhancements

### Subscription Friendly Names (Backend + Frontend)

Azure subscriptions are now displayed with their human-readable `display_name` (e.g., "ALYA") instead of raw UUIDs in cost filter dropdowns.

- **Backend:** `AzureClient.list_accessible_subscriptions_with_names()` fetches names via `azure-mgmt-subscription` at request time. Lookup is best-effort — any failure is logged as a warning and the response falls back gracefully to `subscription_name: null`.
- **Schema:** `SubscriptionCostBreakdown.subscription_name: str | None` (Pydantic v2, optional, no migration required).
- **Frontend:** `EconomicsCostsPage` renders `"ALYA (a1b2c3d4…) · $1,234"` when a name is available, or `"a1b2c3d4… · $1,234"` as fallback.

### Cost Variance Alert Banner (Frontend-only)

The Dashboard shows an informational/warning banner when today's partial cost deviates significantly from the 30-day average.

- **Logic (`computeAlert`):** Fires only when today has data and the 30-day average is ≥ $50. Returns `warning` if delta ≥ +20%, `info` if delta ≥ +10% and today > $200, or `info` for any cost drop.
- **Microcopy:** "Today's partial cost is X% above/below the 30-day average" with a detail line showing today, avg, and absolute delta.
- **No backend changes.** Uses existing `todayCost` and `avgPrevious30d` values already fetched by the Dashboard.

### Dashboard Baseline vs. Monitoring Separation

The Dashboard KPI row now clearly separates the current monitoring period from the historical baseline:

- "Today vs average" delta card compares today's partial cost against the 30-day rolling average.
- Labels distinguish "Today (partial)" from "30d avg (baseline)" to avoid confusion with incomplete daily data.

### English-Only UI

The entire application is now fixed to English. The PT/EN language switcher has been removed.

- `I18nContext` hardcodes `lang = 'en'`, `setLang` is a no-op, and any previously stored locale preference is cleared from `localStorage` on load.
- The language switcher UI block has been removed from `Header`.
- The Dashboard uses a local hardcoded English copy object instead of the i18n `t.dashboard` lookup, keeping it immune to any future locale changes.

### Azure Cost Export Idempotent Ingestion (May 2026)

Azure Cost Management Exports generate **cumulative month-to-date CSVs** — each daily export contains all rows from day 1 through the export date. The ingestion pipeline now implements **delete-before-insert** to prevent duplication:

- Before inserting a new Azure cost batch, the overlapping date range is cleared (scoped to `org_id + account_id + provider + subscription_id + date range`)
- Safety guards prevent deletion without all required filters
- If the delete fails, the insert is aborted (no partial state)
- Self-healing: if insert fails after delete, the next sync cycle re-ingests

**Commit:** `a76d70c` — `fix: prevent duplicate azure cost export ingestion`  
**Full RCA:** [`docs/incidents/azure-cost-duplication-resolution.md`](docs/incidents/azure-cost-duplication-resolution.md)

---

## 🏢 Enterprise Multi-Subscription Support — May 2026

### Arquitetura Multi-Subscription

Enterprise cloud environments operate with multiple subscriptions under a single connector. CauSium now formally supports this pattern:

```
Organization
└── Cloud Account (connector + credentials)
    └── Cloud Account Subscriptions (N per connector)
        └── Cost Facts (ClickHouse — per subscription_id)
```

| Conceito | Papel |
|----------|-------|
| `cloud_accounts` | Conector/credencial — 1 por Service Principal ou IAM Role |
| `cloud_account_subscriptions` | Catálogo formal de subscriptions descobertas/registradas |
| `cost_facts` | Dados financeiros no ClickHouse — referência cruzada via `subscription_id` |

A separação permite que 1 conector Azure (com 1 Service Principal) ingira dados de N subscriptions sem duplicar credenciais ou cloud accounts.

### Fluxo Enterprise Azure

```mermaid
flowchart LR
    TENANT[Azure Tenant] --> CA[Cloud Account\nService Principal]
    CA --> SUB1[Subscription A]
    CA --> SUB2[Subscription B]
    CA --> SUB3[Subscription C]
    CA --> SUBN[Subscription N]
    SUB1 & SUB2 & SUB3 & SUBN --> INGEST[Cost Ingestion]
    INGEST --> CH[(ClickHouse\ncost_facts)]
    CH --> RECON[Reconciliation\nexternal_id_match]
```

### Reconciliação Auditável

O endpoint `GET /api/v1/ledger/reconciliation` fornece validação de integridade entre dados ingeridos e contas registradas:

| Campo | Descrição |
|-------|-----------|
| `total_cost` | Soma de custos no período (ClickHouse) |
| `dashboard_equivalent_total` | Valor equivalente no dashboard |
| `difference` | Divergência entre reconciliação e dashboard |
| `external_id_match` | `true` se subscription_id existe no catálogo |
| `account_mismatch` | Warning: subscription sem match no catálogo |
| `orphan_records` | Registros com account_id inexistente |
| `mixed_currency` | Múltiplas moedas detectadas |
| `partial_range` | Dados não cobrem o período completo |

Características:
- Read-only — não altera dados
- Uso interno admin/engineer
- Compara ClickHouse vs PostgreSQL para validação cruzada

### Currency-Aware Dashboard

O dashboard detecta automaticamente a moeda dominante da organização:

- Suporte a BRL e USD
- `dominant_currency` determinado pela moeda mais frequente nos registros
- `mixed_currency=true` quando múltiplas moedas coexistem
- Sem conversão cambial automática — valores preservados na moeda original

### Governança de Dados

| Mecanismo | Descrição |
|-----------|-----------|
| Placeholder filtering | `aaaaaaaa-0000-0000-0000-aaaaaaaaaaaa` ignorado em warnings de integridade |
| Orphan detection | Registros com `account_id` inexistente são contabilizados |
| External ID match | Validação cruzada subscription_id vs catálogo registrado |
| Idempotent backfill | `dry_run=true` default; upsert sem duplicação |

### Novas Tabelas e Conceitos

| Tabela/Conceito | Descrição |
|-----------------|-----------|
| `cloud_account_subscriptions` | Catálogo de subscriptions por conector (migration 0041) |
| `SubscriptionStatus` | Enum: `active`, `inactive`, `discovered`, `removed` |
| `external_id_match` | Flag de reconciliação: subscription reconhecida no catálogo |
| Discovered subscriptions | Subscriptions encontradas em cost_facts e registradas via backfill |

Constraint: `UNIQUE(org_id, cloud_account_id, provider, subscription_id)`

### Segurança Operacional

| Controle | Detalhe |
|----------|---------|
| `dry_run=true` default | Backfill não persiste sem confirmação explícita |
| Endpoints admin protegidos | `X-Internal-Key` obrigatório |
| Reconciliation read-only | Nenhuma mutação em ClickHouse ou PostgreSQL |
| Placeholder hardcoded | UUID reservado do sistema, imutável |
| Fallback automático | Se catálogo vazio, comportamento antigo preservado |

### Roadmap Multi-Subscription

| Prioridade | Feature | Status |
|------------|---------|--------|
| Alta | Auto-discovery no ingest | 🧭 Planejado |
| Alta | Admin subscription UI | 🧭 Planejado |
| Média | CSV export reconciliação | 🧭 Planejado |
| Média | Azure live reconciliation | 🧭 Planejado |
| Baixa | Subscription governance (ativar/desativar/renomear) | 🧭 Planejado |

---

## 🗺️ Roadmap — Sprint 13–22

### Sprint 13–16 — Execução Assistida → Automação Controlada

```mermaid
flowchart LR
    S12["✅ Sprint 12\nSAFE DSS\nDecision Support"] --> S13
    S13["🟡 Sprint 13\nAssisted Execution"] --> S14
    S14["🟡 Sprint 14\nPolicy Engine"] --> S15
    S15["🟡 Sprint 15\nSafety + Rollback"] --> S16
    S16["🟡 Sprint 16\nControlled Automation"]

    style S12 fill:#dff0d8,color:#000
    style S13 fill:#fcf8e3,color:#000
    style S14 fill:#fcf8e3,color:#000
    style S15 fill:#fcf8e3,color:#000
    style S16 fill:#fcf8e3,color:#000
```

| Sprint | Nome | Principais Features |
|--------|------|---------------------|
| **13** | Assisted Execution | Botão Apply real, double confirmation, feature flag por workspace, logs de execução, nenhuma ação automática |
| **14** | Policy Engine | Regras configuráveis por workspace, bloqueios por risco/ambiente, allow/deny por tipo de recurso, validação antes de execução |
| **15** | Safety & Rollback | Snapshot pré-execução, rollback automático em falha, monitoramento pós-execução, timeout/cancelamento |
| **16** | Controlled Automation | Auto-apply low-risk, janelas de manutenção, aprovação automática por policy, limites por workspace |

**Sprint 13 — Assisted Execution (fluxo detalhado):**

```mermaid
flowchart TD
    USR([Operador]) --> EP[Execution Plan\naprovado]
    EP --> REVIEW[Resumo da ação\nsavings · risk · resource]
    REVIEW --> CONFIRM[Double Confirmation\nexplícita na UI]
    CONFIRM --> FF{Feature flag\nhabilitado no workspace?}
    FF -->|Não| BLOCK[Bloqueado\nflag desabilitado]
    FF -->|Sim| EXEC[Operador executa\ncom suporte do sistema\nstep-by-step]
    EXEC --> TRACK[Tracking de resultado\nstatus · evidência]
    TRACK --> CALIB[ConfidenceCalibration\natualizada]
    CALIB --> PLAN[Optimization Plan\nrecalibrado]
```

### Sprint 17–22 — Premium Intelligence → Autonomous FinOps

```mermaid
flowchart LR
    S17["🟣 Sprint 17\nCost Intelligence"] --> S18
    S18["🟣 Sprint 18\nWhat-if Simulation"] --> S19
    S19["🟣 Sprint 19\nUnit Economics"] --> S20
    S20["🟣 Sprint 20\nEnterprise Governance"] --> S21
    S21["🟣 Sprint 21\nAI Copilot"] --> S22
    S22["🟣 Sprint 22\nAutonomous FinOps"]

    style S17 fill:#d9edf7,color:#000
    style S18 fill:#d9edf7,color:#000
    style S19 fill:#d9edf7,color:#000
    style S20 fill:#d9edf7,color:#000
    style S21 fill:#d9edf7,color:#000
    style S22 fill:#d9edf7,color:#000
```

| Sprint | Nome | Principais Features |
|--------|------|---------------------|
| **17** | Cost Intelligence | Forecast P90 probabilístico, anomaly trends, SKU deep analysis, projeção de economia |
| **18** | What-if Simulation | PulseLab Simulator, cenários de otimização, savings estimados com confiança, comparação de alternativas |
| **19** | Unit Economics | Custo por produto/feature/cliente, chargeback, showback por equipe/serviço, análise de margem |
| **20** | Enterprise Governance | SCA (Stratum Causal Attribution), TopologyMap, blast radius, PulseGov completo, orçamento por squad |
| **21** | AI Copilot | Chat assistido FinOps, recomendações em linguagem natural, "Top 3 ações para hoje", insights proativos |
| **22** | Autonomous FinOps | ARI completo, auto-apply com supervisão, loop fechado auditável, rollback integrado |

### Gantt — Wave 0–4

```mermaid
gantt
    title CauSium — Roadmap de Implementação
    dateFormat YYYY-MM-DD
    axisFormat %b %Y

    section Wave 0 — Hardening (CONCLUÍDO)
    Auth + Security + LGPD BASIC READY   :done, w0a, 2026-04-07, 3w
    Multi-cloud connectors + Workers      :done, w0b, 2026-04-14, 2w
    Observabilidade OTel + SLO            :done, w0c, 2026-04-14, 2w
    Decision Engine + Execution Plan      :done, w0d, 2026-04-14, 2w

    section Wave 1 — Produção Azure
    IaC Terraform Azure VNet/AKS          :w1a, 2026-04-28, 3w
    GitOps ArgoCD + Canário               :w1b, 2026-05-12, 2w
    Sprint 13 Assisted Execution          :w1c, 2026-05-19, 3w

    section Wave 2 — Paridade Enterprise
    Sprint 14 Policy Engine               :w2a, 2026-07-07, 3w
    Sprint 15 Safety + Rollback           :w2b, 2026-07-28, 3w
    Sprint 16 Controlled Automation       :w2c, 2026-08-18, 3w

    section Wave 3 — Diferenciais
    Sprint 17-19 Intelligence             :w3a, 2026-10-06, 8w
    Sprint 20 Enterprise Governance       :w3b, 2026-12-01, 4w
    Sprint 21 AI Copilot                  :w3c, 2026-12-29, 4w

    section Wave 4 — Escala Global
    Sprint 22 Autonomous FinOps           :w4a, 2027-01-26, 6w
    Multi-região + Chaos Drills           :w4b, 2027-03-09, 4w
```

---

## 🛠️ Stack Tecnológica

### Backend

| Tecnologia | Uso |
|-----------|-----|
| Python 3.12 | Runtime principal |
| FastAPI 0.115+ | Framework HTTP assíncrono |
| SQLAlchemy 2.x async | ORM async — 41 migrações Alembic |
| Pydantic v2 | Validação e serialização |
| Structlog | Logging estruturado JSON |
| clickhouse-driver | Client OLAP analytics |
| redis-py | Cache, queues, blacklist, rate limiting |
| cryptography | Fernet encryption + HMAC + workspace keyrings |
| bcrypt | Hash de senhas |
| python-jose | JWT tokens HS256 |
| httpx | HTTP client async |
| opentelemetry-sdk | Distributed tracing instrumentado |

> **Nota:** `pyotp` não é uma dependência ativa. O MFA TOTP é implementado com HMAC/SHA-1 customizado em `auth/service.py`.

### Frontend

| Tecnologia | Uso |
|-----------|-----|
| React 18 | Framework UI |
| TypeScript 5 | Type safety |
| Vite | Build tool |
| Tailwind CSS 3 | Styling utility-first |
| Axios | HTTP client com interceptors |
| React Router v6 | Navegação SPA |
| TanStack Query v5 | Cache de estado servidor |
| Recharts | Gráficos e visualizações |
| lucide-react | Ícones |

### Infraestrutura

| Tecnologia | Uso |
|-----------|-----|
| PostgreSQL 15 | OLTP — metadados, usuários, políticas, workflows |
| ClickHouse | OLAP — custo e uso de alta cardinalidade |
| Redis 7 | Queues, cache, blacklist, rate limiting |
| Docker Compose | Desenvolvimento local e produção |
| nginx | Reverse proxy prod com CSP, HSTS, gzip |
| OpenTelemetry Collector | Pipeline de traces e métricas |
| Jaeger | Distributed tracing UI |
| Prometheus | Coleta de métricas |
| Grafana | Dashboards operacionais + SLO |
| Kubernetes (AKS) | Produção Wave 1 |
| Azure Key Vault | Segredos e chaves KMS (Wave 1) |
| ArgoCD | GitOps + progressive delivery (Wave 1) |
| Terraform | IaC para infraestrutura Azure (Wave 1) |

---

## ⚙️ Configuração e Setup

### Pré-requisitos

- Docker e Docker Compose v2+
- Python 3.12+ (desenvolvimento local sem Docker)
- Node.js 20+ (desenvolvimento local sem Docker)

### Setup Local

```bash
git clone https://github.com/FilipiWanderley/CauSium.git
cd CauSium
cp .env.example .env
# Edite o .env com suas credenciais
docker compose up -d
# Migrações rodam automaticamente via entrypoint.sh
```

### Variáveis de Ambiente Principais

```bash
# Banco de dados
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/stratopulse
DATABASE_SSL=false   # true em produção

# Cache e filas
REDIS_URL=redis://localhost:6379

# ClickHouse
CLICKHOUSE_HOST=localhost
CLICKHOUSE_PORT=8123
CLICKHOUSE_DB=stratopulse

# Segurança — NUNCA commitar valores reais
SECRET_KEY=<chave-jwt-32-bytes-hex>
ENCRYPTION_KEY=<fernet-key-base64>

# Passkeys / WebAuthn
PASSKEY_RP_ID=localhost
PASSKEY_RP_NAME=CauSium
PASSKEY_ALLOWED_ORIGINS=http://localhost:5173

# AI
AI_PROVIDER=mock
AI_MODEL=gpt-4o-mini
AI_OPENAI_API_KEY=<key>

# OpenTelemetry
OTEL_ENABLED=true
OTEL_SERVICE_NAME=causium-backend
OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4317

# Workers
USAGE_OBSERVATION_INTERVAL_MINUTES=30
EXPORT_STORAGE_BACKEND=local   # ou azure_blob / s3

# SMTP
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASSWORD=<api-key>
SMTP_FROM=noreply@stratopulse.io
```

> ⚠️ **Nunca commite o arquivo `.env`** — está no `.gitignore`. Use apenas `.env.example`.

### Estrutura de Diretórios

```
CauSium/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI app + lifespan + OTel
│   │   ├── core/                      # Config, segurança, middleware
│   │   └── domains/                   # 14 domínios de negócio
│   │       ├── admin/                 # Support access · DLQ · org lifecycle
│   │       ├── auth/                  # Passkey · OIDC · MFA · LGPD · anonymization
│   │       ├── cloud_accounts/        # Azure · AWS · GCP connectors + subscription catalog
│   │       ├── cloud_ledger/          # Cost ingestion · reconciliation · dashboard metrics
│   │       ├── decision_engine/       # VM · AKS · Autoscaler · confidence calibration
│   │       ├── economics/             # Custos · SKUs · export async
│   │       ├── experiments/           # PulseLab · runs · approvals
│   │       ├── intel/                 # Explain cost · anomaly detection
│   │       ├── initiatives/           # Kanban de iniciativas
│   │       ├── notifications/         # Alertas · regras · Slack
│   │       ├── opportunities/         # Scoring · recomendações
│   │       ├── audit_chain/           # StratoAudit hash chain
│   │       ├── risk_budgets/          # Risk budgets
│   │       ├── workspaces/            # Workspace lifecycle
│   │       └── workflow/              # Workflow engine
│   ├── app/workers/                   # 10 workers assíncronos
│   ├── alembic/versions/              # 40 migrações (0001 → 0039)
│   ├── entrypoint.sh                  # Auto-migration no container start
│   └── tests/
│       ├── unit/
│       └── integration/
├── frontend/
│   ├── src/
│   │   ├── pages/                     # 24+ páginas implementadas
│   │   ├── api/                       # API client modules
│   │   ├── components/                # UI reutilizável
│   │   └── contexts/                  # AuthContext · I18nContext
│   └── nginx.prod.conf                # nginx prod (CSP, HSTS, gzip)
├── docker-compose.yml                 # Dev local + observabilidade
├── docker-compose.prod.yml            # Produção (4 workers, nginx)
├── .env.example
├── scripts/
│   ├── cloud_mutation_guardrail.py    # CI mutation guardrail
│   └── clickhouse_init.sql
└── docs/
    ├── security/
    │   ├── cloud-read-only-onboarding.md
    │   └── OP08_Security_Gates_Policy.md
    └── operations/
```

---

## 🧪 Testes

### Rodando os Testes

```bash
cd backend
poetry install --with dev
python -m pytest                       # todos
python -m pytest tests/unit/           # unitários
python -m pytest tests/integration/    # integração
python -m pytest --cov=app             # com cobertura

cd frontend
npm test
```

### Suítes Existentes

| Arquivo | Tipo | O que testa |
|---------|------|------------|
| `test_auth_service.py` | Unit | Login, refresh tokens, passkey flow, LGPD purge |
| `test_scorer.py` | Unit | Scoring engine (financial, risk, effort, composite) |
| `test_auth_api.py` | Integration | Endpoints de auth completos |
| `test_passkey_auth.py` | Integration | WebAuthn flow completo |
| `test_oidc_azure.py` | Integration | Azure OAuth2 callback |
| `test_experiment_policy.py` | Integration | Policy engine em transições |
| `test_opportunities.py` | Integration | Geração e scoring de oportunidades |
| `test_workflow.py` | Integration | Kanban board, transitions |
| `test_cloud_accounts.py` | Integration | Health checks, ingestion queue |
| `test_audit_chain.py` | Integration | Hash chain verification, checkpoints |
| `test_idempotency_keys.py` | Integration | Replay e fingerprint SHA-256 |
| `LoginPage.test.tsx` | Component | Login form, passkey button, error states |
| `MembersPage.test.tsx` | Component | Members CRUD |
| `SettingsPage.test.tsx` | Component | MFA TOTP setup, passkey management |
| `MfaTotpSettings.test.tsx` | Component | TOTP QR code, verify, disable |
| `ActivateInvitePage.test.tsx` | Component | Invite activation flow |

### Cobertura Target

| Domínio | Meta atual | Meta Wave 2 |
|---------|-----------|------------|
| auth | > 70% | > 85% |
| decision_engine | > 60% | > 80% |
| policy / audit | > 75% | > 90% |
| economics | > 40% | > 80% |
| workers | > 50% | > 75% |
| **Global** | **> 55%** | **> 80%** |

---

## 📊 Métricas de Sucesso

### Produto

| Métrica | Meta |
|---------|------|
| Tempo de criação de experimento no PulseLab | < 15 min |
| Recomendações com evidência causal | > 90% |
| Redução de desperdício cloud em 2 trimestres | 12–22% |
| Precisão do forecast P90 (erro vs realizado) | < 8% |

### Segurança

| Métrica | Meta |
|---------|------|
| Incidentes de autorização indevida críticos | 0 |
| MTTR de vulnerabilidade alta | < 48h |
| Zero vulnerabilidade crítica aberta em produção | 0 |

### Operação

| Métrica | Meta |
|---------|------|
| SLO da API em produção | 99.95% |
| Latência p95 de query operacional | < 900ms |
| RTO em falha crítica | ≤ 30 min |
| RPO para metadados críticos | ≤ 5 min |

---

## 📖 Glossário

| Termo | Significado |
|-------|------------|
| **SAFE DSS** | Decision Support System — modo operacional Sprint 12; sem mutação cloud automática |
| **workspace** | Conta isolada de um cliente (equiv. org/tenant) |
| **platform_admin** | Administrador global da plataforma (operação interna) |
| **workspace_admin** | Administrador do workspace do cliente |
| **CloudAccount** | Conector multi-cloud cifrado com WorkspaceKeyring — 1 por Service Principal/IAM Role |
| **CloudAccountSubscription** | Subscription registrada no catálogo formal — N por CloudAccount |
| **WorkspaceKeyring** | Chave Fernet org-scoped com rotação automática 30 dias |
| **ExecutionPlan** | Plano de execução de uma oportunidade: aprovação, scheduling, handoff |
| **ConfidenceCalibration** | Ajuste adaptativo do score de confiança por categoria/region/provider baseado em resultados reais |
| **SupportAccessSession** | Acesso temporário auditado de platform_admin a workspace (≤60 min, read-only) |
| **StratoAudit** | Trilha de auditoria imutável com hash SHA-256 encadeado |
| **anonymize_user_identity** | Anonimização irreversível: email → hash, full_name → "Deleted User" |
| **deleted_at** | Timestamp LGPD — marca exclusão e ativa contador de retenção 30 dias |
| **lgpd_purge_user** | Purga completa de dados do titular: anonymize + remove credenciais + audit sem PII |
| **DlqMessage** | Mensagem na dead letter queue após 3 falhas de processamento |
| **ReportExportJob** | Job async de exportação CSV/Excel com status e file_url |
| **IdempotencyKey** | Chave Redis SHA-256 para replay seguro de mutações críticas (TTL 24h) |
| **RevokedToken** | JWT revogado (blacklist Redis + PostgreSQL) |
| **TotpBackupCode** | Código one-time de recuperação de conta MFA (10 por usuário) |
| **SCA** | Stratum Causal Attribution — engine de atribuição causal de variações de custo (Wave 3) |
| **ARI** | Adaptive Recommendation Index — ranking adaptativo de oportunidades (Wave 3) |
| **PulseLab** | Módulo de criação e tracking de experimentos de otimização (state machine 7 estados) |
