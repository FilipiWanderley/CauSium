<div align="center">

# ⚡ CauSium

### Cloud Efficiency Intelligence Platform

**Otimize custo sem quebrar confiabilidade. Com prova causal e governança forte.**

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react&logoColor=black)](https://reactjs.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6?style=flat-square&logo=typescript&logoColor=white)](https://typescriptlang.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-4169E1?style=flat-square&logo=postgresql&logoColor=white)](https://postgresql.org)
[![ClickHouse](https://img.shields.io/badge/ClickHouse-OLAP-FFCC01?style=flat-square&logo=clickhouse&logoColor=black)](https://clickhouse.com)
[![License](https://img.shields.io/badge/License-Proprietary-red?style=flat-square)](LICENSE)

</div>

---

## Índice

- [Visão Geral](#-visão-geral)
- [Por que CauSium?](#-por-que-causium)
- [Módulos do Produto](#-módulos-do-produto)
- [Arquitetura do Sistema](#-arquitetura-do-sistema)
- [Stack Tecnológica](#-stack-tecnológica)
- [Segurança](#-segurança)
- [Modelo de Dados](#-modelo-de-dados)
- [APIs](#-apis)
- [Fluxos Principais](#-fluxos-principais)
- [Workers e Processamento](#-workers-e-processamento)
- [Infraestrutura e Deploy](#-infraestrutura-e-deploy)
- [Roadmap de Implementação](#-roadmap-de-implementação)
- [Configuração e Setup](#-configuração-e-setup)
- [Testes](#-testes)
- [Métricas de Sucesso](#-métricas-de-sucesso)
- [Glossário](#-glossário)

---

## 🎯 Visão Geral

O **CauSium** é uma plataforma de inteligência econômica de cloud que combina visibilidade FinOps operacional com decisões verificáveis baseadas em **causalidade**, governança por **risk budgets** e execução via **experimentos controlados**.

O diferencial competitivo está em três camadas:

| Camada | O que entrega | Módulos |
|--------|--------------|---------|
| **Paridade** | Tudo que um FinOps enterprise maduro oferece | PulseEconomics, PulseGov, PulseGreen, alertas, multi-tenant |
| **Inteligência** | Atribuição causal, otimização multiobjetivo, ranking adaptativo | SCA, ARI, simulador |
| **Execução** | Experimentos canário com guardrails, rollback e evidência imutável | PulseLab, StratoAudit |

---

## 💡 Por que CauSium?

Ferramentas FinOps convencionais mostram dashboards e recomendações. O CauSium vai além:

- **Prova causal** — toda recomendação inclui a engine SCA (Stratum Causal Attribution) apontando *o que causou* a variação de custo, com percentual de confiança
- **Execução segura** — ações em produção só ocorrem após experimento canário com guardrails automáticos e rollback se SLO for violado
- **Governança por risco** — risk budgets por domínio e ambiente restringem automaticamente ações acima do limiar configurado
- **Auditoria imutável** — toda decisão e ação gera evidência criptográfica verificável (hash SHA-256 encadeado)
- **Autenticação sem senha** — WebAuthn passkeys como método padrão, sem dependência de senhas em fluxos principais

---

## 📦 Módulos do Produto

```
CauSium
├── PulseEconomics   → Análise financeira, dashboard, KPIs, SKUs, forecast
├── PulseIntel       → Recomendações inteligentes, SCA, ARI, backlog adaptativo
├── PulseLab         → Criação e execução de experimentos de otimização
├── PulseGov         → Governança de recursos, labels, TopologyMap, blast radius
├── PulseGreen       → Sustentabilidade, emissões de carbono, tendências
├── PulseLink        → Conectores multi-cloud (Azure, AWS, GCP)
├── PulseOps         → Infraestrutura, observabilidade, CI/CD, operação
├── StratoAudit      → Trilha de auditoria imutável com hash encadeado
├── PulseStream      → Event log imutável para replay e auditoria de domínio
├── StratoGraph      → Gateway GraphQL Federation com subgraphs por domínio
└── StratoMesh       → mTLS interno entre serviços (SPIFFE-based)
```

---

## 🏗️ Arquitetura do Sistema

### Visão de Alto Nível — Planos

```mermaid
flowchart TB
  subgraph Sources["☁️ Cloud & Tooling Sources"]
    AZ[Azure APIs]
    AW[AWS APIs]
    GC[GCP APIs]
    CI[CI/CD Events]
    ITSM[ITSM / Tickets]
  end

  subgraph Ingress["📥 Event Ingress Plane"]
    GW[PulseLink\nConnector Gateway]
    BUS[(Event Mesh\nRedis → Kafka)]
    SCH[Schema Registry]
  end

  subgraph DataPlane["📊 Data Plane"]
    STR[Stream Processor\nWorkers]
    COL[(ClickHouse\nCost & SKU Store)]
    TMP[(Time-Series\nUsage Observations)]
    EVT[(PulseStream\nImmutable Event Log)]
    GRA[(TopologyMap\nGraph DB)]
  end

  subgraph ControlPlane["🔐 Control Plane"]
    PDP[Policy Decision Point\nPBAC + ABAC]
    WFE[PulseLab\nExperiment Engine]
    AUTH[Identity & Session Risk\nWebAuthn + OIDC]
    AUD[StratoAudit\nChain Service]
  end

  subgraph Intelligence["🧠 Intelligence Plane"]
    SCA[SCA\nStratum Causal Attribution]
    ARI[ARI\nAdaptive Recommendation Index]
    SIM[PulseLab Simulator\nScenario Engine]
    FORE[Forecast Engine\nP50/P90 Probabilistic]
  end

  subgraph Experience["🖥️ Experience Plane"]
    GQL[StratoGraph\nGraphQL Gateway]
    REST[REST API v1\nFastAPI]
    APP[Web App\nReact + TypeScript]
    BOT[Slack/Jira\nCopilot]
  end

  Sources --> GW --> BUS
  SCH --- BUS
  BUS --> STR --> COL
  STR --> TMP
  STR --> EVT
  STR --> GRA
  COL --> SCA
  GRA --> SCA
  SCA --> ARI
  ARI --> SIM
  SIM --> WFE
  AUTH --> PDP
  PDP --> WFE
  WFE --> AUD
  COL --> FORE
  WFE --> GQL
  WFE --> REST
  GQL --> APP
  REST --> APP
  GQL --> BOT
```

---

### Arquitetura de Domínios (DDD)

```mermaid
flowchart LR
  subgraph Identity["Identity Context"]
    A1[Auth Service]
    A2[Passkey / OIDC]
    A3[Session Risk]
    A4[Policy Engine]
  end

  subgraph Economics["Economics Context"]
    B1[Cost Ledger]
    B2[SKU Observations]
    B3[Workspace Budget]
    B4[Forecast Engine]
  end

  subgraph Experimentation["Experimentation Context"]
    C1[PulseLab]
    C2[Experiment Runs]
    C3[Risk Budgets]
    C4[Change Events]
  end

  subgraph Governance["Governance Context"]
    D1[PulseGov]
    D2[Resource Inventory]
    D3[TopologyMap]
    D4[PulseGreen]
  end

  subgraph Intelligence["Intelligence Context"]
    E1[SCA Engine]
    E2[ARI Ranking]
    E3[Provider Recs]
  end

  subgraph Audit["Audit Context"]
    F1[StratoAudit Chain]
    F2[Checkpoints]
    F3[Compliance Artifacts]
  end

  Identity --> Experimentation
  Economics --> Intelligence
  Intelligence --> Experimentation
  Experimentation --> Audit
  Governance --> Experimentation
  Identity --> Audit
```

---

### Fluxo de Dados Principal

```mermaid
sequenceDiagram
  participant CLD as Cloud Provider
  participant WRK as Ingestion Worker
  participant CH  as ClickHouse
  participant SCR as Scoring Worker
  participant DB  as PostgreSQL
  participant SCA as SCA Engine
  participant LAB as PulseLab
  participant AUD as StratoAudit

  CLD->>WRK: Cost + Event data
  WRK->>CH: INSERT cost_facts, event_facts
  WRK->>SCR: Enqueue account_id
  SCR->>CH: Query cost aggregates
  SCR->>DB: Generate OptimizationOpportunity[]
  DB->>SCA: Correlate with ChangeEvents
  SCA->>DB: CausalTrace (confidence %)
  DB->>LAB: Create Experiment
  LAB->>AUD: append_event(experiment.created)
  LAB->>DB: ExperimentRun (canary)
  LAB->>AUD: append_event(run.completed)
```

---

### State Machine — Experimentos (PulseLab)

```mermaid
stateDiagram-v2
  [*] --> DRAFT : create
  DRAFT --> HYPOTHESIS : transition
  DRAFT --> CANCELLED : cancel
  HYPOTHESIS --> SIMULATING : simulate
  HYPOTHESIS --> CANCELLED : cancel
  SIMULATING --> APPROVED : approve
  SIMULATING --> DRAFT : revise
  SIMULATING --> CANCELLED : cancel
  APPROVED --> RUNNING : execute
  APPROVED --> CANCELLED : cancel
  RUNNING --> MEASURING : collect_telemetry
  RUNNING --> CANCELLED : emergency_stop
  MEASURING --> CONCLUDED : conclude
  MEASURING --> RUNNING : continue
  CONCLUDED --> [*]
  CANCELLED --> [*]

  APPROVED: APPROVED\n(≥2 approvers se high-risk)
  RUNNING: RUNNING\n(canary % do tráfego)
  MEASURING: MEASURING\n(SLO monitoring ativo)
```

---

### State Machine — Workspace Lifecycle

```mermaid
stateDiagram-v2
  [*] --> ACTIVE : create
  ACTIVE --> INACTIVE : deactivate
  INACTIVE --> ACTIVE : reactivate
  INACTIVE --> ARCHIVED : archive
  ARCHIVED --> ACTIVE : restore
  ARCHIVED --> PURGED : purge
  PURGED --> [*]

  INACTIVE: INACTIVE\n(todos os membros\nbloqueados imediatamente)
  ARCHIVED: ARCHIVED\n(dados preservados,\nacesso suspenso)
  PURGED: PURGED\n(todos os dados\nremovidos permanentemente)
```

---

### Pipeline de Decisão de Política (PBAC/ABAC)

```mermaid
flowchart TD
  REQ[Request de Ação] --> R1{Role = VIEWER?}
  R1 -->|Sim| DENY1[❌ DENY]
  R1 -->|Não| R2{session_risk = HIGH?}
  R2 -->|Sim| DENY2[❌ DENY]
  R2 -->|Não| R3{geo_velocity HIGH\n+ ação crítica?}
  R3 -->|Sim| DENY3[❌ DENY]
  R3 -->|Não| R4{device não confiável\n+ ação crítica?}
  R4 -->|Sim| DENY4[❌ DENY]
  R4 -->|Não| R5{ambiente produção\n+ fora maintenance window?}
  R5 -->|Sim| DENY5[❌ DENY]
  R5 -->|Não| R6{ativo crítico\n+ session_risk ≠ LOW?}
  R6 -->|Sim| DENY6[❌ DENY]
  R6 -->|Não| R7{experimento high-risk\n+ approvals < 2?}
  R7 -->|Sim| DENY7[❌ DENY - JIT requerido]
  R7 -->|Não| ALLOW[✅ ALLOW\n+ log PolicyDecisionEvidence]
```

---

## 🛠️ Stack Tecnológica

### Backend

| Tecnologia | Versão | Uso |
|-----------|--------|-----|
| Python | 3.12 | Runtime principal |
| FastAPI | 0.115+ | Framework HTTP assíncrono |
| SQLAlchemy | 2.x (async) | ORM com suporte async |
| Alembic | Latest | Migrações de banco |
| Pydantic | v2 | Validação e serialização |
| Structlog | Latest | Logging estruturado em JSON |
| clickhouse-driver | Latest | Client OLAP analytics |
| redis-py | Latest | Cache e filas de workers |
| pywebauthn | Latest | WebAuthn/FIDO2 passkeys |
| cryptography | Latest | Fernet encryption + HMAC |
| bcrypt | Latest | Hash de senhas |
| python-jose | Latest | JWT tokens |
| httpx | Latest | HTTP client async |

### Frontend

| Tecnologia | Versão | Uso |
|-----------|--------|-----|
| React | 18 | Framework UI |
| TypeScript | 5 | Type safety |
| Vite | Latest | Build tool |
| Tailwind CSS | 3 | Styling utility-first |
| Axios | Latest | HTTP client com interceptors |
| React Router | v6 | Navegação SPA |
| TanStack Query | v5 | Cache de estado servidor |

### Infraestrutura

| Tecnologia | Uso |
|-----------|-----|
| PostgreSQL 15 | OLTP — metadados, usuários, políticas, workflows |
| ClickHouse | OLAP — custo e uso de alta cardinalidade |
| Redis 7 | Cache e filas de workers assíncronos |
| Docker Compose | Desenvolvimento local |
| Kubernetes (AKS) | Produção (Wave 1) |
| Azure Key Vault | Segredos e chaves de criptografia |
| ArgoCD / Flux | GitOps + progressive delivery |
| OpenTelemetry | Traces, metrics, logs distribuídos |
| Terraform | IaC para infraestrutura Azure |

---

## 🔐 Segurança

### Autenticação — Passkey-First

O CauSium adota **WebAuthn (FIDO2) passkeys** como método padrão de autenticação. Senhas são suportadas apenas como fallback, e podem ser desabilitadas por workspace com a política `passwordless_only`.

```mermaid
sequenceDiagram
  participant USR as Usuário
  participant APP as Frontend
  participant API as FastAPI
  participant DB  as PostgreSQL

  USR->>APP: Clica "Login com Passkey"
  APP->>API: POST /auth/passkey/login/options {email}
  API->>DB: Busca user + PasskeyCredentials
  API->>APP: {challenge, credential_ids, rpId}
  APP->>USR: Prompt authenticator (Touch ID, Face ID, etc.)
  USR->>APP: Assina challenge com chave privada
  APP->>API: POST /auth/passkey/login/verify {assertion}
  API->>API: Verifica assinatura ECDSA\nValida sign_count (anti-replay)
  API->>DB: Atualiza sign_count + last_used_at
  API->>APP: {access_token, refresh_token} em cookie httpOnly
  APP->>USR: Redireciona para /app
```

### Camadas de Segurança Implementadas

```mermaid
graph TB
  subgraph L1["Camada 1 — Perímetro"]
    WAF[WAF Azure\nOWASP Rules]
    RL[Rate Limiting\nPor IP + Por Workspace]
    CORS[CORS Restritivo\nPor ambiente]
    HDR[Security Headers\nCSP, HSTS, X-Frame]
  end

  subgraph L2["Camada 2 — Identidade"]
    PK[Passkey WebAuthn\nFIDO2 + ECDSA]
    OIDC[Azure OIDC\nEntra ID federation]
    JWT[JWT Tokens\nAccess 60min + Refresh 7d]
    MFA[MFA TOTP\nFallback 2FA]
  end

  subgraph L3["Camada 3 — Autorização"]
    PBAC[PBAC Runtime\nPolicy Bundles]
    ABAC[ABAC Contextual\nRisco de sessão + Ambiente]
    JIT[JIT Elevation\nDupla aprovação]
    RB[Risk Budgets\nBlast radius limits]
  end

  subgraph L4["Camada 4 — Dados"]
    ENC[Envelope Encryption\nAES-256 + KMS]
    TLS[TLS 1.3\nTodos os datastores]
    FERNET[Fernet\nCredenciais cloud]
    MTLS[StratoMesh\nmTLS interno]
  end

  subgraph L5["Camada 5 — Auditoria"]
    CHAIN[StratoAudit\nHash chain SHA-256]
    HMAC[Checkpoints\nHMAC-SHA256]
    EVID[PolicyDecisionEvidence\nTrilha de cada decisão]
  end

  L1 --> L2 --> L3 --> L4 --> L5
```

### Atributos de Sessão para Decisão de Acesso

O motor de políticas avalia em runtime os seguintes atributos da sessão atual:

| Atributo | Tipo | Impacto |
|---------|------|---------|
| `session_risk` | LOW / MEDIUM / HIGH | HIGH bloqueia ações críticas |
| `geo_velocity_high` | boolean | True bloqueia execuções em produção |
| `device_trusted` | boolean | False bloqueia transições de experimento |
| `maintenance_window` | boolean | False bloqueia ações em produção |
| `role` | enum | VIEWER não executa nenhuma ação |

### Audit Chain — Hash Encadeado

Toda operação crítica gera um evento na `StratoAudit` com hash SHA-256 encadeado:

```
event_hash = SHA256(
  prev_hash
  | org_id
  | actor_user_id
  | event_type
  | entity_type
  | entity_id
  | canonical_payload
  | created_at
)
```

A integridade pode ser verificada a qualquer momento via `GET /audit/verify`. Checkpoints periódicos com assinatura HMAC-SHA256 garantem períodos auditáveis específicos.

---

## 🗄️ Modelo de Dados

### Entidades Core (PostgreSQL OLTP)

```mermaid
erDiagram
  WORKSPACE ||--o{ WORKSPACE_MEMBER : "tem"
  WORKSPACE ||--o{ CLOUD_CREDENTIAL : "tem"
  WORKSPACE ||--o{ WORKSPACE_BUDGET : "tem um"
  WORKSPACE ||--o{ RISK_BUDGET : "tem vários"
  WORKSPACE ||--o{ OPTIMIZATION_EXPERIMENT : "tem"
  WORKSPACE ||--o{ ALERT_RECORD : "recebe"

  WORKSPACE_MEMBER ||--o{ PASSKEY_CREDENTIAL : "tem"
  WORKSPACE_MEMBER ||--o{ NOTIFICATION_PREFERENCE : "tem"
  WORKSPACE_MEMBER ||--o{ EXPERIMENT_APPROVAL : "aprova"

  OPTIMIZATION_EXPERIMENT ||--o{ EXPERIMENT_RUN : "tem"
  OPTIMIZATION_EXPERIMENT ||--o{ EXPERIMENT_APPROVAL : "requer"
  OPTIMIZATION_EXPERIMENT }o--|| OPTIMIZATION_OPPORTUNITY : "deriva de"
  OPTIMIZATION_EXPERIMENT }o--o| RISK_BUDGET : "respeita"

  OPTIMIZATION_OPPORTUNITY ||--o| CAUSAL_TRACE : "tem"
  CAUSAL_TRACE }o--|| CHANGE_EVENT : "correlaciona"

  INITIATIVE }o--|| OPTIMIZATION_OPPORTUNITY : "executa"
  INITIATIVE ||--o{ INITIATIVE_COMMENT : "tem"

  AUDIT_CHAIN_EVENT }o--|| WORKSPACE : "pertence a"
  AUDIT_CHAIN_CHECKPOINT }o--|| WORKSPACE : "pertence a"

  WORKSPACE {
    uuid id PK
    string name
    string slug
    enum lifecycle_state
    int member_quota
    int retention_days
    string plan_tier
    boolean passwordless_only
  }

  OPTIMIZATION_EXPERIMENT {
    uuid id PK
    uuid workspace_id FK
    string title
    string hypothesis
    enum status
    enum outcome
    float simulated_savings_usd
    float simulated_confidence
    json guardrails
    float estimated_risk_score
    float actual_savings_usd
  }

  CAUSAL_TRACE {
    uuid id PK
    uuid workspace_id FK
    uuid recommendation_id FK
    uuid change_event_id FK
    float contribution_pct
    float confidence
    string method
    timestamp computed_at
  }
```

### Storage Poliglota

```mermaid
graph LR
  subgraph PG["PostgreSQL (OLTP)"]
    P1[Workspaces\nMembros\nPolíticas]
    P2[Experiments\nInitiatives\nRisk Budgets]
    P3[Audit Chain\nCheckpoints]
    P4[Credenciais\nBudgets\nNotificações]
  end

  subgraph CH["ClickHouse (OLAP)"]
    C1[cost_facts\nDados de custo diário]
    C2[event_facts\nEventos de atividade]
    C3[sku_observations\nAnálise de SKUs]
    C4[usage_observations\nMétricas de uso]
    C5[carbon_records\nEmissões de CO₂]
  end

  subgraph GDB["Graph DB (Neo4j — Wave 3)"]
    G1[TopologyNode\nServiços e recursos]
    G2[TopologyEdge\nDependências]
  end

  subgraph TS["Time-Series"]
    T1[UsageObservation\nGranularidade minuto]
  end

  subgraph OBJ["Object Storage"]
    O1[ComplianceArtifacts\nRelatórios assinados]
  end
```

### Migrações Alembic

| # | Arquivo | Conteúdo |
|---|---------|---------|
| 0001 | `initial_schema.py` | workspaces, users, cloud_accounts, opportunities, initiatives |
| 0002 | `experiments_risk_budgets_change_events.py` | risk_budgets, experiments, runs, change_events |
| 0003 | `audit_chain_events.py` | audit_chain_events (hash chain) |
| 0004 | `experiment_policy_approvals.py` | experiment_approvals, policy_bundles, policy_decision_evidences |
| 0005 | `policy_bundle_and_evidence.py` | Índices e constraints de política |
| 0006 | `passkey_first_auth.py` | auth_challenges, passkey_credentials |
| 0007 | `audit_chain_checkpoints.py` | audit_chain_checkpoints (HMAC snapshots) |
| 0008 | `workspace_budget_password_reset.py` | WorkspaceBudget, PasswordResetToken *(a criar)* |
| 0009 | `mfa_totp_member_invite.py` | MfaTotpCredential, MemberInvite *(a criar)* |
| 0010 | `workspace_lifecycle.py` | lifecycle_state, member_quota, retention_days *(a criar)* |
| 0011 | `notifications_alerts.py` | ActivityEvent, AlertRecord, NotificationPreference *(a criar)* |
| 0012 | `provider_recommendations_sync.py` | ProviderRecommendation, SyncRecord, DlqMessage *(a criar)* |
| 0013 | `cost_forecast_skus.py` | CostForecastBand, (SkuObservation no CH) *(a criar)* |
| 0014 | `causal_traces.py` | CausalTrace *(a criar)* |
| 0015 | `resource_inventory_carbon.py` | ResourceInventory, CarbonRecord *(a criar)* |
| 0016 | `compliance_artifacts.py` | ComplianceArtifact *(a criar)* |
| 0017 | `topology_graph.py` | TopologyNode, TopologyEdge *(Wave 3)* |

---

## 🌐 APIs

### Estratégia de APIs

| Tipo | Protocolo | Uso | Status |
|------|----------|-----|--------|
| API pública | REST/JSON | Frontend + integrações (hoje) | ✅ |
| GraphQL Federation | StratoGraph | API pública unificada (Wave 3) | Roadmap |
| AsyncAPI | Eventos | Contratos públicos de eventos (Wave 3) | Roadmap |
| gRPC | Interno | Comunicação inter-serviço de baixa latência (Wave 3) | Roadmap |

### Domínios de API

```
/api/v1/
├── /auth/*              → Autenticação, passkey, OIDC, MFA, senhas
├── /economics/*         → Dashboard, budget, custos, SKUs, forecast, exportação
├── /intel/*             → Recomendações, SCA, ARI, backlog adaptativo
├── /lab/*               → Experimentos, runs, approvals, simulador
├── /notifications/*     → Alertas, preferências, polling
├── /gov/*               → Inventário, labels, compliance, blast radius
├── /green/*             → Emissões, tendências, breakdown
├── /sync/*              → Triggers manuais de sincronização por domínio
├── /workspaces/*        → Gestão de workspaces (platform_admin)
├── /members/*           → Gestão de membros do workspace
├── /settings/cloud/*    → Credenciais cloud
├── /audit/*             → Eventos StratoAudit, checkpoints, compliance report
├── /risk-budgets/*      → Risk budgets por domínio/ambiente
├── /change-events/*     → Eventos de mudança operacional
└── /platform/*          → Operação global (platform_admin)
```

### Padrão de Contrato

Todos os endpoints seguem contratos padronizados:

```json
// Erro padronizado
{
  "error": {
    "code": "POLICY_DENIED",
    "message": "Sessão com risco elevado. Ação bloqueada.",
    "trace_id": "uuid4",
    "policy_decision_id": "uuid4",
    "retry_hint": null
  }
}

// Lista paginada
{
  "items": [...],
  "page": 1,
  "page_size": 20,
  "total": 435,
  "has_next": true,
  "has_prev": false
}
```

Mutações críticas aceitam header `Idempotency-Key: <uuid4>` para garantir segurança em retentativas.

---

## 🔄 Fluxos Principais

### Fluxo 1 — Anomalia para Experimento

```mermaid
flowchart TD
  A[Worker identifica\nvariação anômala de custo] --> B[ClickHouse: cost_facts\nagregados por serviço]
  B --> C[SCA Engine correlaciona\ncom ChangeEvents]
  C --> D{Confiança\n> 70%?}
  D -->|Sim| E[CausalTrace criado\ncom % de confiança]
  D -->|Não| F[Oportunidade gerada\ncom flag low_confidence]
  E --> G[ARI rankeia oportunidade\nno backlog adaptativo]
  F --> G
  G --> H[Usuário cria\nExperimento no PulseLab]
  H --> I[Policy Engine valida\nPBAC + ABAC + Risk Budget]
  I -->|Bloqueado| J[❌ DENY + PolicyDecisionEvidence]
  I -->|Permitido| K[Simulador PulseLab\nestima savings + risco]
  K --> L{High-risk?\nestimated_risk ≥ 0.7?}
  L -->|Sim| M[JIT: requer 2 approvers\ndistintos]
  L -->|Não| N[1 approver suficiente]
  M --> O[ExperimentRun CANARY\n% configurável do tráfego]
  N --> O
  O --> P{SLO violado\ndurante canário?}
  P -->|Sim| Q[Rollback automático\nStratoAudit registra]
  P -->|Não| R[Rollout 100%\nMeasuring outcomes]
  R --> S[Concluded:\nactual_savings_usd registrado]
  S --> T[ARI atualiza ranking\ncom resultado real]
```

---

### Fluxo 2 — Onboarding de Workspace

```mermaid
flowchart LR
  A[platform_admin\ncria workspace] --> B[workspace_admin\nrecebe email de ativação]
  B --> C[workspace_admin\nconfigura CloudCredentials]
  C --> D[Sistema valida\nescopos de permissão]
  D -->|Escopos inválidos| E[Erro descritivo\nCredencial não persistida]
  D -->|Escopos OK| F[Sincronização inicial\ndispara automaticamente]
  F --> G1[cost_facts\nno ClickHouse]
  F --> G2[ActivityEvents\ndo provider]
  F --> G3[ProviderRecommendations\ndo Advisor]
  F --> G4[ResourceInventory\npara PulseGov]
  G1 & G2 & G3 & G4 --> H[workspace_admin define\norçamento + labels + alertas]
```

---

### Fluxo 3 — Operação Diária FinOps

```mermaid
flowchart TD
  A[Analyst abre\nPulseEconomics] --> B[Dashboard: KPIs,\ntendências, drivers]
  B --> C[Drill-down em\n/economics/costs\nfiltros combinados]
  C --> D[Central de notificações\ntrata alertas prioritários]
  D --> E[PulseIntel:\nbacklog ARI rankeado]
  E --> F[Cria experimento\nno PulseLab]
  F --> G[Acompanha resultado\ncom evidência SCA]
  G --> H[Exporta relatório\nCSV/Excel ou PDF auditado]
```

---

## ⚙️ Workers e Processamento

### Workers Existentes

| Worker | Fila (Redis) | Responsabilidade |
|--------|-------------|-----------------|
| `ingestion_worker` | `ingestion:queue` | Fetch de custo + eventos do Azure; INSERT no ClickHouse; lock por account |
| `scoring_worker` | `scoring:queue` | Gera `OptimizationOpportunity` a partir dos dados do ClickHouse |
| `audit_checkpoint_worker` | Timer (60min) | Cria checkpoints HMAC da StratoAudit para todos os workspaces |

### Workers a Criar (Roadmap)

| Worker | Prioridade | Responsabilidade |
|--------|-----------|-----------------|
| `recommendation_sync_worker` | P1 | Importa `ProviderRecommendation` do Azure Advisor a cada 4h |
| `alert_worker` | P1 | Avalia regras de `AlertRecord` por categoria |
| `notification_dispatcher` | P1 | Envia alertas por email (SMTP) e Slack (webhook) |
| `activity_sync_worker` | P1 | Ingere `ActivityEvent` do Azure Activity Log |
| `inventory_sync_worker` | P2 | Sincroniza `ResourceInventory` do Azure Resource Graph |
| `carbon_sync_worker` | P2 | Ingere `CarbonRecord` da Azure Carbon API |
| `dlq_monitor_worker` | P1 | Monitora DLQ; alerta operações após 3 falhas |
| `forecast_worker` | P2 | Gera `CostForecastBand` P50/P90 |
| `causal_attribution_worker` | P2 | Calcula `CausalTrace` entre `ChangeEvent` e variações de custo |
| `lgpd_purge_worker` | P2 | Executa purge de dados por `retention_days` por workspace |

### Diagrama de Fluxo dos Workers

```mermaid
graph LR
  subgraph Queues["Redis Queues"]
    Q1[ingestion:queue]
    Q2[scoring:queue]
    Q3[dlq:queue]
  end

  subgraph Workers["Workers Assíncronos"]
    W1[ingestion_worker]
    W2[scoring_worker]
    W3[audit_checkpoint]
    W4[alert_worker]
    W5[notification_dispatcher]
  end

  subgraph Storage["Storage"]
    CH[(ClickHouse)]
    PG[(PostgreSQL)]
    REDIS[(Redis)]
  end

  Q1 --> W1
  W1 -->|cost_facts, event_facts| CH
  W1 -->|enqueue| Q2
  W1 -->|3x failure| Q3
  Q2 --> W2
  W2 -->|Opportunities| PG
  PG --> W3
  W3 -->|Checkpoints HMAC| PG
  PG --> W4
  W4 -->|AlertRecord| PG
  W4 --> W5
  W5 -->|SMTP + Slack| External[Email / Slack]
```

---

## 🚀 Infraestrutura e Deploy

### Ambiente Local (Docker Compose)

```bash
docker compose up -d
```

Serviços iniciados:

| Serviço | Porta | Descrição |
|---------|-------|-----------|
| `backend` | 8000 | FastAPI API + Workers |
| `frontend` | 5173 | Vite dev server |
| `postgres` | 5432 | PostgreSQL 15 |
| `redis` | 6379 | Redis 7 |
| `clickhouse` | 8123 | ClickHouse OLAP |

### Target: Azure Enterprise (Wave 1+)

```mermaid
graph TB
  subgraph Internet
    USR[Usuário]
    DNS[DNS Público]
  end

  subgraph Azure["Azure Cloud"]
    AFD[Azure Front Door\nWAF + Rate Limiting]

    subgraph VNet["VNet Privada"]
      subgraph SubCP["subnet-control-plane"]
        AKS1[AKS Control Plane\nAPI + Workers]
        NGINX[Ingress Nginx]
      end

      subgraph SubDP["subnet-data-plane"]
        AKS2[AKS Data Plane\nClickHouse + Processors]
      end

      subgraph SubDS["subnet-datastores"]
        PE1[Private Endpoint\nPostgreSQL]
        PE2[Private Endpoint\nRedis]
        PE3[Private Endpoint\nClickHouse]
      end

      subgraph SubMGT["subnet-management"]
        ARGO[ArgoCD / Flux\nGitOps]
        KV[Azure Key Vault\nSegredos + KMS]
      end
    end
  end

  USR --> DNS --> AFD --> NGINX --> AKS1
  AKS1 --> PE1 & PE2 & PE3
  AKS2 --> PE3
  ARGO --> AKS1 & AKS2
  KV --> AKS1
```

### Pipeline GitOps (Wave 1)

```mermaid
flowchart LR
  DEV[Developer\nPush PR] --> GH[GitHub Actions CI]
  GH --> SAST[SAST\nBandit/Semgrep]
  GH --> SCA[SCA\nSafety/pip-audit]
  GH --> SEC[Secret Scan\ntrufflehog]
  GH --> TEST[Unit +\nIntegration Tests]
  GH --> BUILD[Docker Build\n+ Push Registry]

  SAST & SCA & SEC & TEST & BUILD -->|Todos passam| MERGE[Merge para main]
  SAST & SCA & SEC & TEST & BUILD -->|Qualquer falha| BLOCK[❌ Merge Bloqueado]

  MERGE --> ARGO[ArgoCD detecta\nmudança no repo]
  ARGO --> CANARY[Deploy Canário\n10% do tráfego]
  CANARY --> ANALYZE{p95 latência\ne error rate OK?}
  ANALYZE -->|OK| FULL[Rollout 100%]
  ANALYZE -->|NOK| ROLLBACK[Rollback Automático]
```

---

## 🗺️ Roadmap de Implementação

```mermaid
gantt
  title CauSium — Roadmap de Implementação
  dateFormat  YYYY-MM-DD
  axisFormat  %b %Y

  section Wave 0 — Hardening
  Security Headers & CORS        :w0a, 2026-04-07, 1w
  TLS 1.3 nos Datastores         :w0b, 2026-04-07, 1w
  Rate Limiting por Workspace    :w0c, 2026-04-07, 1w
  Token httpOnly Cookie          :w0d, 2026-04-14, 1w
  Scope Validation CloudCredential :w0e, 2026-04-14, 1w
  Paginação em todas as listas   :w0f, 2026-04-14, 1w

  section Wave 1 — Produção Azure
  IaC Terraform Azure (VNet/AKS) :w1a, 2026-04-28, 3w
  Private Endpoints + DNS        :w1b, 2026-05-05, 2w
  GitOps ArgoCD + Canário        :w1c, 2026-05-12, 2w
  Workspace Lifecycle Completo   :w1d, 2026-04-28, 2w
  Gestão de Membros + Email      :w1e, 2026-05-05, 2w
  WorkspaceBudget + SMTP         :w1f, 2026-05-12, 2w
  DLQ + Workers Resilientes      :w1g, 2026-05-19, 1w

  section Wave 2 — Paridade Enterprise
  OpenTelemetry End-to-End       :w2a, 2026-07-07, 2w
  SLI/SLO Dashboards             :w2b, 2026-07-14, 2w
  CI SAST/SCA/Secret Scan        :w2c, 2026-07-07, 1w
  WAF + Rate Limiting            :w2d, 2026-07-14, 2w
  Sistema de Notificações        :w2e, 2026-07-21, 3w
  PulseIntel (Azure Advisor)     :w2f, 2026-07-28, 2w
  PulseEconomics SKUs + Exportação :w2g, 2026-08-04, 3w
  MFA TOTP Completo              :w2h, 2026-08-11, 2w

  section Wave 3 — Diferenciais
  SCA (Stratum Causal Attribution) :w3a, 2026-10-06, 4w
  ARI (Adaptive Ranking Index)   :w3b, 2026-10-20, 3w
  PulseLab Simulator             :w3c, 2026-11-03, 3w
  PulseGov (Governança)          :w3d, 2026-10-06, 4w
  PulseGreen (Sustentabilidade)  :w3e, 2026-10-20, 3w
  StratoGraph (GraphQL)          :w3f, 2026-11-10, 4w
  Integrações Jira/GitHub/Slack  :w3g, 2026-11-17, 3w
  StratoMesh (mTLS)              :w3h, 2026-11-24, 2w

  section Wave 4 — Escala Global
  Multi-região Ativo-Passivo     :w4a, 2027-01-06, 4w
  Conector GCP Real              :w4b, 2027-01-13, 3w
  TopologyMap + Blast Radius     :w4c, 2027-01-20, 4w
  Chaos Drills + Pentest         :w4d, 2027-02-03, 2w
```

### Status Atual por Módulo

| Módulo | ✅ Impl. | 🔶 Parcial | ❌ Não iniciado | Prioridade |
|--------|---------|-----------|----------------|-----------|
| Autenticação e sessão | 5 | 5 | 3 | **P0** |
| Multi-tenant / workspaces | 0 | 3 | 5 | **P0** |
| Perfis e membros | 0 | 1 | 5 | **P0** |
| PulseEconomics | 1 | 5 | 4 | P1 |
| Alertas e notificações | 0 | 0 | 7 | P1 |
| PulseIntel | 0 | 3 | 3 | P1 |
| PulseGov | 0 | 0 | 6 | P2 |
| PulseGreen | 0 | 0 | 4 | P2 |
| PulseLink (conectores) | 1 | 5 | 4 | P1 |
| Sync / Workers | 0 | 3 | 4 | P1 |
| StratoAudit / Compliance | 1 | 2 | 3 | P1 |
| Credenciais / StratoMesh | 0 | 3 | 2 | **P0** |
| StratoGraph / Integrações | 0 | 1 | 7 | P2 |
| Frontend — páginas | 0 | 8 | 11 | P1 |
| PulseOps (infra) | 2 | 4 | 9 | **P0** |

---

## ⚙️ Configuração e Setup

### Pré-requisitos

- Docker e Docker Compose
- Python 3.12+
- Node.js 20+

### Setup Local

```bash
# 1. Clone o repositório
git clone https://github.com/FilipiWanderley/CauSium.git
cd CauSium

# 2. Configure as variáveis de ambiente
cp .env.example .env
# Edite o .env com suas credenciais

# 3. Suba os serviços de infraestrutura
docker compose up -d postgres redis clickhouse

# 4. Execute as migrações do banco
cd backend
pip install -r requirements.txt  # ou uv sync
alembic upgrade head

# 5. Inicie o backend
uvicorn app.main:app --reload --port 8000

# 6. Inicie o frontend (em outro terminal)
cd frontend
npm install
npm run dev
```

### Variáveis de Ambiente Principais

```bash
# Banco de dados
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/causium

# Cache e filas
REDIS_URL=redis://localhost:6379

# ClickHouse
CLICKHOUSE_HOST=localhost
CLICKHOUSE_PORT=8123
CLICKHOUSE_DB=causium

# Segurança — NUNCA commitar valores reais
SECRET_KEY=<chave-jwt-32-bytes>          # JWT signing
ENCRYPTION_KEY=<fernet-key-base64>       # Fernet encryption

# Azure OIDC (opcional para dev)
AZURE_TENANT_ID=<tenant-id>
AZURE_CLIENT_ID=<client-id>
AZURE_CLIENT_SECRET=<client-secret>

# Frontend
CORS_ORIGINS=http://localhost:5173
```

> ⚠️ **Nunca commite o arquivo `.env`** — ele está no `.gitignore`. Use apenas `.env.example` com valores de exemplo.

### Estrutura de Diretórios

```
CauSium/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI app + lifespan
│   │   ├── api/v1/                    # Routers por domínio
│   │   ├── core/                      # Config, segurança, middleware, política
│   │   ├── domains/                   # 11 domínios de negócio
│   │   └── workers/                   # Workers assíncronos
│   ├── alembic/versions/              # 7 migrações (→ 17 ao final)
│   ├── tests/
│   │   ├── unit/                      # test_auth_service, test_scorer
│   │   └── integration/               # 8 suítes de integração
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── pages/                     # 8 páginas (→ 20 ao final)
│   │   ├── api/                       # 10 módulos de API client
│   │   ├── components/                # UI reutilizável
│   │   ├── contexts/                  # AuthContext, I18nContext
│   │   └── hooks/                     # useAuth
│   └── vite.config.ts
├── docs/
│   ├── PRD_CauSium_Completo_v2.0.md
│   └── roadmap/
├── scripts/
│   ├── setup_dev.sh
│   └── clickhouse_init.sql
└── docker-compose.yml
```

---

## 🧪 Testes

### Rodando os Testes

```bash
# Backend — todos os testes
cd backend
pytest

# Apenas testes unitários
pytest tests/unit/

# Apenas testes de integração
pytest tests/integration/

# Com cobertura
pytest --cov=app --cov-report=html
```

### Suítes Existentes

| Arquivo | Tipo | O que testa |
|---------|------|------------|
| `test_auth_service.py` | Unit | Login, refresh tokens, passkey flow |
| `test_scorer.py` | Unit | Scoring engine (financial, risk, effort, composite) |
| `test_auth_api.py` | Integration | Endpoints de auth (register, login, passkey, OIDC) |
| `test_passkey_auth.py` | Integration | WebAuthn flow completo |
| `test_oidc_azure.py` | Integration | Azure OAuth2 callback |
| `test_experiment_policy.py` | Integration | Policy engine decisions em transições |
| `test_opportunities.py` | Integration | Geração de oportunidades, scoring |
| `test_workflow.py` | Integration | Kanban board, transitions |
| `test_cloud_accounts.py` | Integration | Health checks, ingestion queue |
| `test_audit_chain.py` | Integration | Hash chain verification, checkpoints |

### Cobertura Target

| Domínio | Meta atual | Meta Wave 2 |
|---------|-----------|------------|
| auth | > 70% | > 85% |
| experiments / lab | > 60% | > 80% |
| policy | > 75% | > 90% |
| economics | > 40% | > 80% |
| audit_chain | > 80% | > 90% |
| **Global** | > 50% | **> 80%** |

---

## 📊 Métricas de Sucesso

### Produto

| Métrica | Meta |
|---------|------|
| Tempo de criação de experimento no PulseLab | < 15 minutos |
| Recomendações com evidência causal (SCA) | > 90% |
| Adoção mensal do backlog ARI | > 65% |
| Redução de desperdício cloud em 2 trimestros | 12–22% |
| Precisão do forecast P90 (erro vs realizado) | < 8% |

### Segurança

| Métrica | Meta |
|---------|------|
| Cobertura de políticas PBAC/ABAC ativas | > 95% |
| Incidentes de autorização indevida críticos | 0 |
| MTTR de vulnerabilidade de severidade alta | < 48h |
| Taxa de pass nos testes de segurança automatizados | ≥ 98% |

### Operação

| Métrica | Meta |
|---------|------|
| SLO da API em produção | 99.95% |
| SLO da ingestão diária por conector | 99.7% |
| Latência p95 de query operacional | < 900 ms |
| RTO em falha crítica | ≤ 30 min |
| RPO para metadados críticos | ≤ 5 min |
| Zero vulnerabilidade crítica aberta em produção | 0 |

### Negócio

| Métrica | Meta |
|---------|------|
| Net Revenue Retention | > 115% |
| Cobertura de testes automatizados por domínio | > 80% |

---

## 📖 Glossário

| Termo | Significado |
|-------|------------|
| **workspace** | Conta isolada de um cliente no sistema |
| **platform_admin** | Administrador global sem workspace (operação interna) |
| **workspace_admin** | Administrador do workspace do cliente |
| **analyst** | Usuário operacional com permissões de escrita analítica |
| **viewer** | Usuário de leitura |
| **CloudCredential** | Credencial multi-cloud multi-registro por workspace |
| **WorkspaceBudget** | Orçamento financeiro configurável por workspace |
| **ActivityEvent** | Evento de log de atividade do cloud provider |
| **AlertRecord** | Alerta gerado por categoria no sistema |
| **ProviderRecommendation** | Recomendação importada do cloud provider (Advisor) |
| **SyncRecord** | Estado de sincronização por conector e workspace |
| **SkuObservation** | Observação de SKU por workspace e período |
| **ResourceInventory** | Inventário de recursos para governança |
| **CarbonRecord** | Emissão de carbono por conta e período |
| **CausalTrace** | Trilha de explicação causal por recomendação (SCA) |
| **OptimizationExperiment** | Experimento criado no PulseLab |
| **ExperimentRun** | Execução de experimento com telemetria coletada |
| **TopologyNode** | Nó no grafo TopologyMap (serviço ou recurso) |
| **ComplianceArtifact** | Relatório de auditoria exportável e assinado |
| **StratoAudit** | Sistema de trilha de auditoria imutável com hash encadeado |
| **PulseStream** | Event log imutável para replay e auditoria de domínio |
| **StratoGraph** | Gateway GraphQL Federation com subgraphs por domínio |
| **StratoMesh** | Camada de mTLS interno entre serviços (SPIFFE-based) |
| **SCA** | Stratum Causal Attribution — engine de atribuição causal |
| **ARI** | Adaptive Recommendation Index — ranking adaptativo com feedback |
| **DlqMessage** | Mensagem na dead letter queue após falhas repetidas |
| **PBAC** | Policy-Based Access Control — autorização por bundle de políticas |
| **ABAC** | Attribute-Based Access Control — autorização por atributos de contexto |
| **JIT** | Just-In-Time elevation — elevação temporária de acesso com aprovação |

---

## 📄 Documentação Adicional

- [PRD Completo v2.0](docs/PRD_CauSium_Completo_v2.0.md) — Gap analysis real, backlog de 75 requisitos e roadmap por wave
- [Wave 0 Checklist](docs/roadmap/Wave0_P0_Checklist.md) — Checklist de hardening imediato
- [Rastreabilidade de Requisitos](docs/traceability/SP-Requisitos-para-Issues.md) — Matriz de requisitos para issues

---

<div align="center">

**CauSium** — Cloud Efficiency Intelligence Platform

*Versão 2.0 · Abril 2026 · CONFIDENCIAL*

</div>
