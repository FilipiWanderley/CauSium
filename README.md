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
[![OpenTelemetry](https://img.shields.io/badge/OpenTelemetry-Tracing-425CC7?style=flat-square&logo=opentelemetry&logoColor=white)](https://opentelemetry.io)
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
- [PulseIntel IA](#-pulseintel-ia)
- [Fluxos Principais](#-fluxos-principais)
- [Análise de Eficiência de Reservas](#-análise-de-eficiência-de-reservas)
- [Workers e Processamento](#-workers-e-processamento)
- [Observabilidade](#-observabilidade)
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
- **Autenticação sem senha** — WebAuthn passkeys como método padrão, com MFA TOTP como fallback e backup codes para recuperação
- **Observabilidade de ponta** — distributed tracing com OpenTelemetry + Jaeger, métricas Prometheus e SLO dashboard no Grafana
- **Inteligência de reservas** — leitura de custos de compute e sinais de reserva/compromisso (RI/Savings Plan), com cálculo de cobertura e custo descoberto para orientar decisões de compra

---

## 📦 Módulos do Produto

```
CauSium
├── PulseEconomics   → Análise financeira, dashboard, KPIs, SKUs, forecast, exportação async
├── PulseIntel       → Recomendações inteligentes, SCA, ARI, backlog adaptativo
├── PulseLab         → Criação e execução de experimentos de otimização
├── PulseGov         → Governança de recursos, labels, TopologyMap, blast radius
├── PulseGreen       → Sustentabilidade, emissões de carbono, tendências
├── PulseLink        → Conectores multi-cloud (Azure, AWS CUR, GCP BigQuery)
├── PulseOps         → Infraestrutura, observabilidade, CI/CD, operação
├── StratoAudit      → Trilha de auditoria imutável com hash encadeado
├── PulseStream      → Event log imutável para replay e auditoria de domínio
├── StratoGraph      → Gateway GraphQL Federation com subgraphs por domínio
└── StratoMesh       → mTLS interno entre serviços (SPIFFE-based)
```

### PulseIntel — Explain Cost Change (IA)

A primeira capacidade de IA do produto está implementada em produção local: **explicação automática de variação de custo** para apoiar decisão operacional com contexto técnico e financeiro.

**O que faz no software**

- Explica variação de custo do período selecionado comparando janela atual vs janela anterior equivalente.
- Destaca causas prováveis com evidências e impacto estimado.
- Cruza dados de custos (`cost_facts`), eventos (`event_facts`) e recomendações (`recommendation_facts`).
- Retorna plano de ação objetivo para engenharia/FinOps.
- Respeita idioma da interface (`PT`/`EN`) para conteúdo gerado pela IA.
- Controla acesso por plano (`AI_ENABLED_PLANS` + regras default de plano com IA).

**Contrato de API**

- Endpoint: `POST /api/v1/intel/explain-cost`
- Entrada: `start_date`, `end_date`, `provider?`, `language?` (`pt` | `en`)
- Saída: `summary`, `causes[]`, `impact`, `recommendation`, `confidence`, `model?`, `debug?`
- Erros esperados: `422` (período inválido), `403` (IA não habilitada no plano)

**Arquitetura da feature (backend)**

```mermaid
flowchart LR
  UI[Dashboard CTA\nExplain change] --> API[POST /api/v1/intel/explain-cost]
  API --> GATE{Plano com IA?}
  GATE -->|Não| DENY[403]
  GATE -->|Sim| ORCH[CostExplanationService]
  ORCH --> CH1[ClickHouse\ncost_facts]
  ORCH --> CH2[ClickHouse\nevent_facts]
  ORCH --> CH3[ClickHouse\nrecommendation_facts]
  CH1 --> CTX[Context Builder]
  CH2 --> CTX
  CH3 --> CTX
  CTX --> LLM[LlmService\nprovider: mock/openai]
  LLM --> OUT[ExplainCostChangeOut]
  OUT --> UI
```

**Fluxo de execução da IA**

```mermaid
sequenceDiagram
  participant FE as Frontend
  participant BE as Intel Router
  participant SVC as CostExplanationService
  participant CH as ClickHouse
  participant LLM as LlmService

  FE->>BE: POST /intel/explain-cost {start_date,end_date,provider?}
  BE->>SVC: validate period + user/org
  SVC->>SVC: require_ai_feature(plan)
  SVC->>CH: Query delta + drivers + eventos + recomendações
  SVC->>LLM: explain_cost_change(contexto estruturado)
  LLM-->>SVC: JSON estruturado (ou fallback mock)
  SVC-->>BE: ExplainCostChangeOut
  BE-->>FE: 200 response
```

**Configuração operacional (ENV)**

- `AI_PROVIDER=mock|openai`
- `AI_ENABLED_PLANS=b,enterprise,growth_ai` (ou vazio para defaults)
- `AI_MODEL=gpt-4o-mini`
- `AI_TIMEOUT_SECONDS=30`
- `AI_OPENAI_API_KEY`
- `AI_OPENAI_BASE_URL=https://api.openai.com/v1`

---

## 🏗️ Arquitetura do Sistema

### Visão de Alto Nível — Planos

```mermaid
flowchart TB
  subgraph Sources["☁️ Cloud & Tooling Sources"]
    AZ[Azure APIs]
    AW[AWS CUR / S3]
    GC[GCP BigQuery]
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
    AUTH[Identity & Session Risk\nWebAuthn + OIDC + TOTP]
    AUD[StratoAudit\nChain Service]
  end

  subgraph Intelligence["🧠 Intelligence Plane"]
    SCA[SCA\nStratum Causal Attribution]
    ARI[ARI\nAdaptive Recommendation Index]
    SIM[PulseLab Simulator\nScenario Engine]
    FORE[Forecast Engine\nP50/P90 Probabilistic]
  end

  subgraph Observability["📡 Observability Plane"]
    OTEL[OpenTelemetry\nSDK + Collector]
    JAEGER[Jaeger\nDistributed Tracing]
    PROM[Prometheus\nMetrics]
    GRAF[Grafana\nDashboards + SLO]
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
  REST --> OTEL --> JAEGER
  REST --> PROM --> GRAF
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
    A3[MFA TOTP + Backup Codes]
    A4[Policy Engine]
  end

  subgraph Economics["Economics Context"]
    B1[Cost Ledger]
    B2[SKU Observations]
    B3[Workspace Budget]
    B4[Forecast Engine]
    B5[Export Worker]
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
    F4[LGPD Consent]
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
| Alembic | Latest | Migrações de banco (29 migrações) |
| Pydantic | v2 | Validação e serialização |
| Structlog | Latest | Logging estruturado em JSON |
| clickhouse-driver | Latest | Client OLAP analytics |
| redis-py | Latest | Cache, filas de workers e idempotency keys |
| pywebauthn | Latest | WebAuthn/FIDO2 passkeys |
| cryptography | Latest | Fernet encryption + HMAC + workspace keyrings |
| bcrypt | Latest | Hash de senhas |
| python-jose | Latest | JWT tokens |
| pyotp | Latest | MFA TOTP + backup codes |
| httpx | Latest | HTTP client async |
| opentelemetry-sdk | Latest | Distributed tracing instrumentado |
| opentelemetry-exporter-otlp | Latest | Export para Jaeger via OTLP |

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
| Recharts | Latest | Gráficos e visualizações |
| lucide-react | Latest | Ícones |

### Infraestrutura

| Tecnologia | Uso |
|-----------|-----|
| PostgreSQL 15 | OLTP — metadados, usuários, políticas, workflows |
| ClickHouse | OLAP — custo e uso de alta cardinalidade |
| Redis 7 | Cache, filas de workers, idempotency keys (SHA-256 fingerprint) |
| Docker Compose | Desenvolvimento local e produção (docker-compose.prod.yml) |
| nginx | Reverse proxy prod com CSP, HSTS, gzip e cache imutável |
| OpenTelemetry Collector | Pipeline de traces e métricas |
| Jaeger | Distributed tracing UI |
| Prometheus | Coleta de métricas + alertas |
| Grafana | Dashboards operacionais + SLO dashboard |
| Kubernetes (AKS) | Produção (Wave 1) |
| Azure Key Vault | Segredos e chaves de criptografia |
| ArgoCD / Flux | GitOps + progressive delivery |
| Terraform | IaC para infraestrutura Azure |

---

## 🔐 Segurança

### Autenticação — Passkey-First com MFA TOTP

O CauSium adota **WebAuthn (FIDO2) passkeys** como método padrão. Senhas são suportadas como fallback. MFA TOTP está disponível como segundo fator, com geração de **backup codes** para recuperação de conta.

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
    HDR[Security Headers\nCSP, HSTS, X-Frame, nosniff]
  end

  subgraph L2["Camada 2 — Identidade"]
    PK[Passkey WebAuthn\nFIDO2 + ECDSA]
    OIDC[Azure OIDC\nEntra ID federation]
    JWT[JWT Tokens\nAccess 60min + Refresh 7d]
    MFA[MFA TOTP\n+ Backup Codes]
    TOKVOKE[Token Revocation\nBlacklist no Redis]
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
    FERNET[Workspace Keyrings\nFernet org-scoped + rotação]
    IDMPT[Idempotency Keys\nRedis SHA-256 fingerprint + replay]
    LGPD[LGPD Consent\nRegistro e controle de consentimento]
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

### Workspace Keyrings — Criptografia Org-Scoped

Cada organização possui um keyring Fernet isolado para criptografia de credenciais cloud. O `keyring_rotation_worker` rotaciona automaticamente chaves por workspace, com re-encrypt transparente de todos os segredos.

```
WorkspaceKeyring
├── org_id           → Isolamento por tenant
├── key_version      → Versão atual da chave
├── encrypted_key    → Chave Fernet cifrada com master key
└── rotated_at       → Timestamp da última rotação
```

### Idempotency Keys

Mutações críticas aceitam o header `Idempotency-Key: <uuid4>`. O backend armazena no Redis um fingerprint SHA-256 do par `(key, request_hash)` com TTL de 24h — retentativas idênticas retornam o resultado original sem re-executar.

### LGPD Consent

Registro completo de consentimento LGPD por usuário: tipo de dado, base legal, propósito, versão da política e timestamp. Endpoints para consulta e revogação de consentimento por usuário.

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
  WORKSPACE ||--o{ WORKSPACE_KEYRING : "tem"
  WORKSPACE ||--o{ LGPD_CONSENT : "tem"

  WORKSPACE_MEMBER ||--o{ PASSKEY_CREDENTIAL : "tem"
  WORKSPACE_MEMBER ||--o{ NOTIFICATION_PREFERENCE : "tem"
  WORKSPACE_MEMBER ||--o{ EXPERIMENT_APPROVAL : "aprova"
  WORKSPACE_MEMBER ||--o{ MFA_TOTP_CREDENTIAL : "tem"
  WORKSPACE_MEMBER ||--o{ TOTP_BACKUP_CODE : "tem"

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

  REPORT_EXPORT_JOB }o--|| WORKSPACE : "pertence a"

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

  REPORT_EXPORT_JOB {
    uuid id PK
    uuid org_id FK
    enum status
    string format
    json filters
    string file_url
    timestamp completed_at
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
    P5[LGPD Consent\nWorkspace Keyrings]
    P6[Export Jobs\nDLQ Messages]
  end

  subgraph CH["ClickHouse (OLAP)"]
    C1[cost_facts\nDados de custo diário]
    C2[event_facts\nEventos de atividade]
    C3[sku_observations\nAnálise de SKUs]
    C4[usage_observations\nMétricas de uso]
    C5[carbon_records\nEmissões de CO₂]
  end

  subgraph REDIS["Redis"]
    R1[Workers Queues\ningestion, scoring, carbon]
    R2[Idempotency Keys\nSHA-256 + TTL 24h]
    R3[Token Blacklist\nRevogação de JWT]
    R4[Export Jobs\nStatus e progresso]
  end

  subgraph OBJ["Object Storage"]
    O1[Export Files\nCSV / Excel gerados]
    O2[ComplianceArtifacts\nRelatórios assinados]
  end
```

### Migrações Alembic (29 migrações)

| # | Arquivo | Conteúdo |
|---|---------|---------|
| 0001 | `initial_schema.py` | workspaces, users, cloud_accounts, opportunities, initiatives |
| 0002 | `experiments_risk_budgets_change_events.py` | risk_budgets, experiments, runs, change_events |
| 0003 | `audit_chain_events.py` | audit_chain_events (hash chain) |
| 0004 | `experiment_policy_approvals.py` | experiment_approvals, policy_bundles, policy_decision_evidences |
| 0005 | `policy_bundle_and_evidence.py` | Índices e constraints de política |
| 0006 | `passkey_first_auth.py` | auth_challenges, passkey_credentials |
| 0007 | `audit_chain_checkpoints.py` | audit_chain_checkpoints (HMAC snapshots) |
| 0008a | `workspace_lifecycle.py` | lifecycle_state, member_quota, retention_days |
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
| 0019 | `auth_totp_mfa.py` | MfaTotpCredential, setup/verify/enable/disable |
| 0020 | `report_export_jobs.py` | ReportExportJob (async export) |
| 0021 | `workspace_keyrings.py` | WorkspaceKeyring (Fernet org-scoped) |
| 0022 | `blob_ingestion_checkpoints.py` | BlobIngestionCheckpoint (Azure Blob) |
| 0023 | `aws_cur_ingestion_checkpoints.py` | AwsCurIngestionCheckpoint (AWS CUR S3) |
| 0024 | `provider_recommendation_sync.py` | ProviderRecommendation, SyncRecord |
| 0025 | `merge_workspace_lifecycle.py` | Merge branch de lifecycle |
| 0026 | `lgpd_consent.py` | LgpdConsent (base legal, propósito, versão) |
| 0027 | `totp_backup_codes.py` | TotpBackupCode (10 códigos one-time por usuário) |
| 0028 | `alert_delivery_tracking.py` | AlertDeliveryLog (rastreamento de envio) |
| 0029 | `revoked_tokens.py` | RevokedToken (blacklist JWT no PostgreSQL) |

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
/api/v1/  (prefixo real: /api/v1)
├── /auth/*              → Autenticação, passkey, OIDC, MFA TOTP, backup codes, LGPD
├── /cloud-accounts/*    → Multi-cloud connectors (Azure, AWS CUR, GCP BigQuery)
├── /economics/*         → Dashboard, budget, custos, SKUs, forecast, exportação async
├── /ledger/reservations/coverage → Cobertura de reservas (compute vs reservado vs descoberto)
├── /intel/*             → Recomendações, SCA, ARI, backlog adaptativo
├── /lab/*               → Experimentos, runs, approvals, simulador
├── /notifications/*     → Alertas, preferências, stream em tempo real (WebSocket)
├── /gov/*               → Inventário, labels, compliance, blast radius
├── /green/*             → Emissões, tendências, breakdown
├── /sync/*              → Triggers manuais de sincronização por domínio
├── /workspaces/*        → Gestão de workspaces (platform_admin)
├── /members/*           → Gestão de membros do workspace
├── /settings/cloud/*    → Credenciais cloud
├── /audit/*             → Eventos StratoAudit, checkpoints, compliance report
├── /risk-budgets/*      → Risk budgets por domínio/ambiente
├── /change-events/*     → Eventos de mudança operacional
├── /metrics/slo         → SLO snapshot para Prometheus/Grafana
└── /platform/*          → Operação global (platform_admin)
```

### Padrão de Contrato

Todos os endpoints de lista seguem paginação padronizada:

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

### Cobertura de Reservas (RI / Savings Plans)

Endpoint:

```
GET /ledger/reservations/coverage?days=30
```

Retorna, por workspace:

- `total_compute_cost_usd`: custo de compute no período
- `total_reserved_cost_usd`: custo detectado como reserva/compromisso
- `uncovered_compute_cost_usd`: parcela estimada ainda em on-demand
- `coverage_pct`: cobertura de reservas (%)
- `services[]`: breakdown por serviço para priorização operacional
- `recommendation`: recomendação textual objetiva para ação

Permissões:

- Leitura disponível para usuários autenticados do workspace (inclui perfis cliente/viewer).

### Eficiência de Reservas vs Recursos Utilizados

Objetivo:

- Identificar quando a reserva comprada (por família/SKU) está subutilizada em relação ao parque real de recursos.
- Recomendar a melhor ação financeira e operacional para cada caso: manter, redimensionar workload, trocar reserva (exchange) ou encerrar no ciclo de renovação.

Endpoint planejado:

```
GET /ledger/reservations/efficiency?days=30
```

Saída planejada:

- `family`: família de reserva (ex.: `Standard_B2s`)
- `reserved_capacity_units`: capacidade reservada contratada
- `effective_used_units`: capacidade efetivamente usada no período
- `idle_reserved_units`: capacidade ociosa da reserva
- `utilization_pct`: taxa de utilização da reserva
- `waste_cost_usd`: custo estimado de desperdício da reserva
- `payg_equivalent_cost_usd`: custo equivalente sem reserva (on-demand)
- `exchange_candidate`: indicador se há potencial de troca de reserva por perfil mais aderente
- `recommended_action`: ação recomendada (`keep`, `resize_resource`, `schedule_stop`, `exchange_reservation`, `do_not_renew`)
- `reason`: justificativa legível para usuário final
- `confidence`: confiança da recomendação (0-1)

Regras de decisão planejadas:

- Reserva com baixa utilização e workload não crítico: priorizar `schedule_stop` ou `resize_resource`.
- Reserva com ociosidade recorrente e mismatch de família/SKU: priorizar `exchange_reservation` quando elegível.
- Reserva próxima da expiração com baixa utilização histórica: priorizar `do_not_renew`.
- Workload estável e reserva bem aproveitada: manter `keep`.

Notas:

- A recomendação considera histórico de consumo, previsibilidade de uso e custo comparativo contra PAYG.
- Elegibilidade de exchange/refund depende de regras do provedor cloud e contrato vigente do cliente.

### Dashboard Multi-Cloud (Escopo Global por Provedor)

Para operação diária, o dashboard possui seletor global de escopo:

- `Todos os provedores`
- `Azure`
- `AWS`
- `GCP`

Comportamento:

- O filtro é aplicado aos KPIs, tendência de custo, top serviços/equipes, eficiência de reservas e tabela de contas conectadas.
- A preferência do usuário é persistida no navegador (`localStorage`) para manter contexto entre sessões.
- Se o filtro salvo não existir mais nas contas conectadas (ex.: só Azure ativo), o sistema faz fallback automático para o provedor válido ou para `Todos`.

### Onboarding Cloud Unificado (UX)

O onboarding de credenciais cloud foi consolidado em uma experiência única para reduzir ambiguidade:

- Rota direta no menu: `Cloud` (`/app/cloud`)
- Tela unificada com abas de provedor: `Azure | AWS | GCP`
- Formulário contextual por provedor, mantendo validação e sync no mesmo fluxo operacional

### Janela Histórica de Ingestão (Cloud Sync)

Regra de negócio padrão para onboarding e sincronização de contas cloud:

- O software sempre tenta analisar até os últimos `90 dias` (3 meses).
- Se o tenant tiver menos histórico disponível (ex.: 30 ou 60 dias), a ingestão traz somente o período existente.
- O limite máximo permitido por sync é `90 dias` para manter previsibilidade de performance.

Endpoint de sync:

```http
POST /cloud-accounts/{account_id}/sync?lookback_days=90
```

Restrições:

- `lookback_days` aceita valores de `7` a `90`.
- Valores acima de `90` não são aceitos pela API.

### Notificações em Tempo Real (In-App)

Funcionalidades implementadas no módulo de notificações:

- Stream em tempo real por workspace via WebSocket (`/notifications/stream`).
- Geração automática de alertas a partir de eventos auditados de ação do usuário (`create/update/delete`) e ciclo de sync cloud (queued/completed/failure).
- Classificação visual por tipo no frontend: `activity`, `created`, `updated`, `deleted`, `sync`, `security`.
- Filtros por categoria, tipo e status, com ordenação priorizando severidade e não lidas.
- Banner de ação imediata para alertas `critical + unread`.
- Alerta sonoro para notificações críticas em tempo real, com toggle `Som ligado / Som desligado` persistido no navegador.

Notas operacionais:

- O stream atual usa broker in-process (single-node). Para escala horizontal, substituir por Redis Pub/Sub ou event bus dedicado.
- O toggle de som é preferência local (localStorage), por usuário/navegador.

Erros seguem envelope padronizado:

```json
{
  "error": {
    "code": "POLICY_DENIED",
    "message": "Sessão com risco elevado. Ação bloqueada.",
    "trace_id": "uuid4",
    "policy_decision_id": "uuid4",
    "retry_hint": null
  }
}
```

Mutações críticas aceitam header `Idempotency-Key: <uuid4>` para garantia de segurança em retentativas com replay do resultado original.

---

## 🤖 PulseIntel IA

### Explain Cost Change — como trabalha no produto

No dashboard, o usuário pode clicar em **Explain change** no card de custo mensal. O frontend abre um modal e chama o endpoint de IA com a janela do mês atual. O backend monta contexto com dados reais de custo/evento/recomendação e retorna uma explicação estruturada para ação imediata.

**Resultado mostrado na UI**

- Resumo executivo da variação.
- Principais causas ordenadas com evidências.
- Impacto financeiro resumido.
- Recomendação prática de próximo passo.
- Nível de confiança da explicação.

### Arquitetura de integração Frontend + Backend

```mermaid
flowchart TB
  subgraph Frontend
    KPI[Current Month Cost Card]
    CTA[Botão Explain change]
    MODAL[Modal de explicação]
  end

  subgraph Backend
    R[Router /intel/explain-cost]
    S[CostExplanationService]
    L[LlmService]
  end

  subgraph Data
    C[(cost_facts)]
    E[(event_facts)]
    P[(recommendation_facts)]
  end

  KPI --> CTA --> R --> S
  S --> C
  S --> E
  S --> P
  S --> L
  L --> S --> MODAL
```

### Limites e comportamento de segurança

- A funcionalidade só responde para workspaces com plano habilitado para IA.
- Período inválido é bloqueado por validação de contrato (`end_date < start_date`).
- Se o provider LLM falhar, o serviço retorna fallback `mock` para manter continuidade da UX.
- O endpoint usa autenticação do usuário atual e escopo do workspace (`org_id`) para isolamento multi-tenant.

---

## 🔄 Fluxos Principais

## 🧠 Análise de Eficiência de Reservas

### Objetivo de Negócio

- Fechar o gap entre o que foi contratado em reserva e o que está realmente em execução no ambiente.
- Evitar desperdício por reserva ociosa e evitar decisões agressivas que gerem risco operacional.

### Matriz de Decisão (planejada)

| Situação detectada | Ação principal | Resultado esperado |
|--------------------|----------------|--------------------|
| Reserva bem utilizada (`utilization_pct` alto) | `keep` | Preserva economia já capturada |
| Reserva subutilizada + workload flexível | `resize_resource` | Melhor aderência da VM ao compromisso |
| Reserva subutilizada + janela ociosa previsível | `schedule_stop` | Redução de custo operacional adicional |
| Mismatch estrutural de família/SKU | `exchange_reservation` | Migração para reserva mais aderente |
| Baixa utilização recorrente no fim do termo | `do_not_renew` | Evita perpetuar desperdício no próximo ciclo |

### Escopo técnico da implementação

- Agregação por família/SKU a partir de custos e inventário de recursos.
- Simulação financeira comparando reserva atual vs cenário alternativo.
- Geração de recomendação explicável com score de confiança.

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

### Fluxo 3 — Exportação Assíncrona de Relatórios

```mermaid
sequenceDiagram
  participant USR as Usuário
  participant API as FastAPI
  participant REDIS as Redis
  participant WRK as export_worker
  participant BLOB as Object Storage

  USR->>API: POST /economics/export {format, filters}
  API->>REDIS: Enqueue export job
  API->>USR: 202 Accepted {job_id}
  USR->>API: GET /economics/export/{job_id}
  API->>USR: {status: "pending"}
  REDIS->>WRK: Dequeue job
  WRK->>WRK: Gera CSV/Excel com filtros
  WRK->>BLOB: Upload arquivo gerado
  WRK->>API: Update job status + file_url
  USR->>API: GET /economics/export/{job_id}
  API->>USR: {status: "done", file_url: "..."}
```

---

## ⚙️ Workers e Processamento

### Workers Implementados

| Worker | Fila (Redis) | Responsabilidade |
|--------|-------------|-----------------|
| `ingestion_worker` | `ingestion:queue` | Fetch de custo + eventos (Azure Blob, AWS CUR S3, GCP BigQuery); INSERT no ClickHouse; lock por account |
| `scoring_worker` | `scoring:queue` | Gera `OptimizationOpportunity` a partir dos dados do ClickHouse |
| `audit_checkpoint_worker` | Timer (60min) | Cria checkpoints HMAC da StratoAudit para todos os workspaces |
| `notification_worker` | `notification:queue` | Avalia regras de alerta; envia por email (SMTP) e Slack (webhook) |
| `carbon_sync_worker` | `carbon:queue` | Ingere `CarbonRecord` da Azure Carbon API e similares |
| `export_worker` | `export:queue` | Processa jobs de exportação async (CSV/Excel); upload para object storage |
| `keyring_rotation_worker` | Timer (periódico) | Rotaciona chaves Fernet por workspace; re-cifra credenciais transparentemente |
| `maintenance_worker` | Timer (diário) | Limpeza de registros expirados, tokens revogados, dados de retenção LGPD |

### Diagrama de Fluxo dos Workers

```mermaid
graph LR
  subgraph Queues["Redis Queues"]
    Q1[ingestion:queue]
    Q2[scoring:queue]
    Q3[notification:queue]
    Q4[carbon:queue]
    Q5[export:queue]
    Q6[dlq:queue]
  end

  subgraph Workers["Workers Assíncronos"]
    W1[ingestion_worker]
    W2[scoring_worker]
    W3[audit_checkpoint]
    W4[notification_worker]
    W5[carbon_sync_worker]
    W6[export_worker]
    W7[keyring_rotation_worker]
    W8[maintenance_worker]
  end

  subgraph Storage["Storage"]
    CH[(ClickHouse)]
    PG[(PostgreSQL)]
    REDIS[(Redis)]
    BLOB[(Object Storage)]
  end

  Q1 --> W1
  W1 -->|cost_facts, event_facts| CH
  W1 -->|enqueue| Q2
  W1 -->|3x failure| Q6
  Q2 --> W2
  W2 -->|Opportunities| PG
  PG --> W3
  W3 -->|Checkpoints HMAC| PG
  Q3 --> W4
  W4 -->|SMTP + Slack| External[Email / Slack]
  Q4 --> W5
  W5 -->|CarbonRecord| PG
  Q5 --> W6
  W6 -->|CSV/Excel| BLOB
  W7 -->|Re-encrypt keyrings| PG
  W8 -->|Purge expirados| PG
  W8 -->|Purge tokens| REDIS
```

### DLQ — Dead Letter Queue

Mensagens que falharam 3 vezes são movidas para `dlq:queue` e registradas em `DlqMessage` no PostgreSQL. A API expõe endpoints para inspeção e reprocessamento manual:

```
GET  /dlq/messages          → Lista mensagens com falha
POST /dlq/messages/{id}/retry → Reprocessa mensagem específica
DELETE /dlq/messages/{id}  → Descarta mensagem sem reprocessar
```

---

## 📡 Observabilidade

### OpenTelemetry — Distributed Tracing

O CauSium instrumenta automaticamente todas as requisições HTTP, chamadas ao banco de dados (SQLAlchemy), chamadas ao Redis e chamadas ao ClickHouse via OpenTelemetry SDK.

```mermaid
flowchart LR
  APP[FastAPI\nApp] -->|OTLP gRPC| COLL[OTel Collector]
  COLL -->|traces| JAEGER[Jaeger UI\n:16686]
  COLL -->|metrics| PROM[Prometheus\n:9090]
  PROM -->|datasource| GRAF[Grafana\n:3001]
```

**Spans instrumentados:**
- Todas as rotas HTTP (método, path, status, latência)
- Queries SQLAlchemy (statement, parâmetros sanitizados)
- Operações Redis (comando, chave)
- Chamadas externas aos cloud providers

**Configuração via `.env`:**
```bash
OTEL_ENABLED=true
OTEL_SERVICE_NAME=causium-backend
OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4317
OTEL_SAMPLE_RATIO=1.0   # 1.0 = 100% em dev; reduzir em prod
```

### SLO Dashboard — `/metrics/slo`

O endpoint `/metrics/slo` expõe um snapshot de SLO em formato compatível com Prometheus e Grafana:

```json
{
  "api_availability_7d": 99.97,
  "p95_latency_ms": 342,
  "error_rate_1h": 0.003,
  "ingestion_success_rate_24h": 99.8
}
```

O Grafana consome este endpoint via datasource JSON + painéis pré-configurados com alertas de violação de SLO.

### Acessos Locais

| Serviço | URL | Credenciais padrão |
|---------|-----|--------------------|
| Jaeger UI | http://localhost:16686 | — |
| Prometheus | http://localhost:9090 | — |
| Grafana | http://localhost:3001 | admin / admin |

---

## 🚀 Infraestrutura e Deploy

### Ambiente Local (Docker Compose)

```bash
# Sobe todos os serviços (backend com auto-migração, frontend dev, datastores, observabilidade)
docker compose up -d
```

Serviços iniciados:

| Serviço | Porta | Descrição |
|---------|-------|-----------|
| `backend` | 8000 | FastAPI + entrypoint.sh (auto-migration + uvicorn) |
| `frontend` | 3000 | nginx dev runtime servindo o build do frontend |
| `postgres` | 5432 | PostgreSQL 15 |
| `redis` | 6379 | Redis 7 |
| `clickhouse` | 8123 | ClickHouse OLAP |
| `jaeger` | 16686 | Distributed Tracing UI |
| `prometheus` | 9090 | Métricas |
| `grafana` | 3001 | Dashboards + SLO |

### Deploy em Produção (Docker Compose Prod)

O arquivo `docker-compose.prod.yml` é otimizado para ambientes de produção:

- `restart: always` em todos os serviços
- Backend com **4 uvicorn workers** (sem `--reload`)
- Frontend servido pelo **nginx** (porta 80) com build de produção
- Sem bind-mounts de código (apenas volumes de dados)
- Jaeger e ferramentas de observabilidade em `profiles: [dev]` (não sobem por padrão em prod)

```bash
# Deploy em produção
docker compose -f docker-compose.prod.yml up -d

# Com observabilidade ativa em staging
docker compose -f docker-compose.prod.yml --profile dev up -d
```

### Auto-migração na Inicialização — entrypoint.sh

O backend executa migrações Alembic automaticamente antes de iniciar:

```sh
#!/bin/sh
set -e
echo "[entrypoint] running alembic upgrade head..."
alembic upgrade head
echo "[entrypoint] migrations applied."
exec "$@"
```

Isso garante que qualquer scaling horizontal ou rollout de nova versão aplica as migrações antes de aceitar tráfego. Alembic é idempotente — safe para múltiplas instâncias simultâneas.

### nginx Produção — nginx.prod.conf

O frontend em produção é servido pelo nginx com:

| Feature | Detalhe |
|---------|---------|
| Security headers | CSP, HSTS (`max-age=31536000`), `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff` |
| Gzip | `js`, `css`, `json`, `svg`, `html` |
| Cache strategy | `Cache-Control: no-store` para `index.html`; `immutable` para assets com hash |
| API proxy | `/api/` e `/health` proxied para `http://backend:8000` |

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

  section Wave 0 — Hardening (CONCLUÍDO)
  Security Headers & CORS        :done, w0a, 2026-04-07, 1w
  TLS 1.3 nos Datastores         :done, w0b, 2026-04-07, 1w
  Rate Limiting por Workspace    :done, w0c, 2026-04-07, 1w
  Token httpOnly Cookie          :done, w0d, 2026-04-14, 1w
  Scope Validation CloudCredential :done, w0e, 2026-04-14, 1w
  Paginação em todas as listas   :done, w0f, 2026-04-14, 1w
  MFA TOTP + Backup Codes        :done, w0g, 2026-04-14, 1w
  Workspace Keyrings + Rotação   :done, w0h, 2026-04-14, 1w
  Idempotency Keys Redis         :done, w0i, 2026-04-14, 1w
  LGPD Consent                   :done, w0j, 2026-04-14, 1w
  Token Revocation Blacklist     :done, w0k, 2026-04-14, 1w
  OpenTelemetry + Jaeger         :done, w0l, 2026-04-14, 1w
  Prometheus + Grafana + SLO     :done, w0m, 2026-04-14, 1w
  Export Async Worker            :done, w0n, 2026-04-14, 1w
  Carbon Sync Worker             :done, w0o, 2026-04-14, 1w
  DLQ + Reprocessamento          :done, w0p, 2026-04-14, 1w
  Notification Worker (SMTP)     :done, w0q, 2026-04-14, 1w
  Docker Compose Prod + nginx    :done, w0r, 2026-04-14, 1w
  AWS CUR Connector              :done, w0s, 2026-04-14, 1w
  GCP BigQuery Connector         :done, w0t, 2026-04-14, 1w

  section Wave 1 — Produção Azure
  IaC Terraform Azure (VNet/AKS) :w1a, 2026-04-28, 3w
  Private Endpoints + DNS        :w1b, 2026-05-05, 2w
  GitOps ArgoCD + Canário        :w1c, 2026-05-12, 2w
  Workspace Lifecycle Completo   :w1d, 2026-04-28, 2w
  WorkspaceBudget + SMTP Full    :w1e, 2026-05-12, 2w
  CI SAST/SCA/Secret Scan        :w1f, 2026-05-19, 1w

  section Wave 2 — Paridade Enterprise
  WAF + DDoS Protection          :w2a, 2026-07-07, 2w
  SLI/SLO Avançado               :w2b, 2026-07-14, 2w
  PulseIntel (Azure Advisor Full) :w2c, 2026-07-28, 2w
  PulseEconomics SKUs + Forecast :w2d, 2026-08-04, 3w
  Sistema de Notificações Slack  :w2e, 2026-08-11, 2w

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
  TopologyMap + Blast Radius     :w4b, 2027-01-20, 4w
  Chaos Drills + Pentest         :w4c, 2027-02-03, 2w
```

### Status Atual por Módulo

| Módulo | Status | Detalhes |
|--------|--------|---------|
| Autenticação e sessão | ✅ Completo | Passkey WebAuthn, OIDC Azure, MFA TOTP, backup codes, refresh tokens, token revocation |
| Multi-tenant / workspaces | ✅ Completo | Lifecycle (ACTIVE→PURGED), member quota, retention, workspace keyrings |
| Perfis e membros | ✅ Completo | CRUD, invite flow, force password change, LGPD consent |
| Segurança | ✅ Completo | PBAC/ABAC, idempotency keys, TLS 1.3 todos os datastores, security headers |
| PulseEconomics | 🔶 Parcial | Dashboard, costs, SKUs, export async — forecast P90 no roadmap |
| Alertas e notificações | ✅ Completo | AlertRecord, AlertRule, NotificationPreference, SMTP + Slack, DLQ |
| PulseIntel | 🔶 Parcial | Explain Cost Change (IA) + ProviderRecommendation sync — SCA/ARI avançado no Wave 3 |
| PulseGov | 🔶 Parcial | UI placeholder — domínio Wave 3 |
| PulseGreen | 🔶 Parcial | Carbon sync worker e modelo — UI Wave 3 |
| PulseLink (conectores) | ✅ Completo | Azure (SP + Blob + Carbon), AWS CUR + Carbon Export (S3), GCP Billing + Carbon Footprint (BigQuery + Workload Identity) |
| Sync / Workers | ✅ Completo | 8 workers: ingestion, scoring, audit, notification, carbon, export, keyring, maintenance |
| StratoAudit / Compliance | ✅ Completo | Hash chain SHA-256, HMAC checkpoints, DLQ, audit log UI |
| Observabilidade | ✅ Completo | OTel tracing, Jaeger, Prometheus, Grafana, SLO endpoint |
| Infraestrutura prod | ✅ Completo | docker-compose.prod.yml, entrypoint.sh, nginx.prod.conf |
| Frontend — páginas | ✅ Completo | 27 páginas implementadas |
| StratoGraph / Integrações | ❌ Roadmap | Wave 3 |
| StratoMesh (mTLS) | ❌ Roadmap | Wave 3 |

---

## ⚙️ Configuração e Setup

### Pré-requisitos

- Docker e Docker Compose v2+
- Python 3.12+ (para desenvolvimento local sem Docker)
- Node.js 20+ (para desenvolvimento local sem Docker)

### Setup Local

```bash
# 1. Clone o repositório
git clone https://github.com/FilipiWanderley/CauSium.git
cd CauSium

# 2. Configure as variáveis de ambiente
cp .env.example .env
# Edite o .env com suas credenciais

# 3. Suba todos os serviços (migrações rodam automaticamente via entrypoint.sh)
docker compose up -d

# 4. (Opcional) Backend em modo dev sem Docker
cd backend
pip install poetry && poetry install
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# 5. (Opcional) Frontend em modo dev sem Docker
cd frontend
npm install
npm run dev
```

> As migrações são aplicadas automaticamente pelo `entrypoint.sh` ao subir o container do backend. Não é necessário rodar `alembic upgrade head` manualmente no fluxo Docker.

### Variáveis de Ambiente Principais

```bash
# Banco de dados
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/stratopulse
DATABASE_SSL=false   # true em produção com certificado

# Cache e filas
REDIS_URL=redis://localhost:6379
# Em produção: rediss://user:pass@host:6380 (TLS)

# ClickHouse
CLICKHOUSE_HOST=localhost
CLICKHOUSE_PORT=8123
CLICKHOUSE_DB=stratopulse
# CLICKHOUSE_CA_CERT=/path/to/ca.crt  (TLS em produção)

# Segurança — NUNCA commitar valores reais
SECRET_KEY=<chave-jwt-32-bytes-hex>
ENCRYPTION_KEY=<fernet-key-base64>

# MFA
MFA_ISSUER=CauSium

# Passkeys / WebAuthn
PASSKEY_RP_ID=localhost
PASSKEY_RP_NAME=CauSium
PASSKEY_ALLOWED_ORIGINS=http://localhost:5173,http://localhost:5174

# Azure OIDC (opcional para dev)
AZURE_TENANT_ID=<tenant-id>
AZURE_CLIENT_ID=<client-id>
AZURE_CLIENT_SECRET=<client-secret>

# Frontend
CORS_ORIGINS=http://localhost:5173

# SMTP (notificações)
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASSWORD=<api-key>
SMTP_FROM=noreply@stratopulse.io

# OpenTelemetry
OTEL_ENABLED=true
OTEL_SERVICE_NAME=causium-backend
OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4317
OTEL_SAMPLE_RATIO=1.0

# Workers
WORKER_CONCURRENCY=4
EXPORT_STORAGE_BACKEND=local   # ou "azure_blob" / "s3"

# Carbono AWS/GCP (official-first com fallback estimado)
AWS_CARBON_EXPORT_BUCKET=<bucket-opcional-com-export-oficial-de-carbono>
AWS_CARBON_EXPORT_PREFIX=<prefixo-opcional>
AWS_CARBON_FACTORS_JSON={"ec2":0.45,"s3":0.2,"default":0.3}
GCP_CARBON_FOOTPRINT_TABLE=<project.dataset.table-opcional>
GCP_CARBON_FACTORS_JSON={"compute":0.42,"storage":0.19,"default":0.29}

# Grafana
GRAFANA_ADMIN_PASSWORD=admin
```

> Para AWS e GCP, o módulo PulseGreen usa estratégia **official-first**: tenta primeiro o dataset oficial do provedor (S3 export no AWS, BigQuery Carbon Footprint no GCP). Se o dataset não estiver configurado ou falhar, aplica fallback por estimativa baseada em custo, mantendo continuidade operacional.

> ⚠️ **Nunca commite o arquivo `.env`** — ele está no `.gitignore`. Use apenas `.env.example` com valores de exemplo.

### Estrutura de Diretórios

```
CauSium/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI app + lifespan + OTel setup
│   │   ├── core/                      # Config, segurança, middleware, política, schemas
│   │   └── domains/                   # 12 domínios de negócio
│   │       ├── auth/                  # Passkey, OIDC, MFA, TOTP, backup codes, LGPD
│   │       ├── cloud_accounts/        # Azure, AWS CUR, GCP BigQuery connectors
│   │       ├── economics/             # Custos, SKUs, forecast, export async
│   │       ├── experiments/           # PulseLab, runs, approvals
│   │       ├── initiatives/           # Kanban de iniciativas
│   │       ├── notifications/         # Alertas, regras, preferências, Slack
│   │       ├── opportunities/         # Scoring, recomendações
│   │       ├── audit_chain/           # StratoAudit hash chain
│   │       ├── risk_budgets/          # Risk budgets por domínio
│   │       ├── change_events/         # ChangeEvent tracking
│   │       ├── workspaces/            # Workspace lifecycle
│   │       └── platform/             # Operação global
│   ├── app/workers/                   # 8 workers assíncronos
│   │   ├── ingestion_worker.py
│   │   ├── scoring_worker.py
│   │   ├── audit_checkpoint_worker.py
│   │   ├── notification_worker.py
│   │   ├── carbon_sync_worker.py
│   │   ├── export_worker.py
│   │   ├── keyring_rotation_worker.py
│   │   └── maintenance_worker.py
│   ├── alembic/versions/              # 29 migrações (0001 → 0029)
│   ├── entrypoint.sh                  # Auto-migration on container start
│   ├── tests/
│   │   ├── unit/
│   │   └── integration/               # 10+ suítes de integração
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── pages/                     # 27 páginas implementadas
│   │   ├── api/                       # 10+ módulos de API client
│   │   ├── components/                # UI reutilizável
│   │   ├── contexts/                  # AuthContext, I18nContext
│   │   └── hooks/                     # useAuth
│   ├── nginx.conf                     # nginx dev
│   ├── nginx.prod.conf                # nginx produção (CSP, HSTS, gzip, cache imutável)
│   └── vite.config.ts
├── docker-compose.yml                 # Desenvolvimento local + observabilidade
├── docker-compose.prod.yml            # Produção (4 workers, nginx, sem bind-mounts)
├── .env.example                       # Template de variáveis de ambiente
└── scripts/
    ├── setup_dev.sh
    └── clickhouse_init.sql
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

# Frontend — testes de componente
cd frontend
npm test
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
| `test_idempotency_keys.py` | Integration | Idempotency key replay e fingerprint SHA-256 |
| `LoginPage.test.tsx` | Component | Login form, passkey button, error states |
| `MembersPage.test.tsx` | Component | Members list, add/edit/delete |
| `SettingsPage.test.tsx` | Component | MFA TOTP setup, passkey management |
| `MfaTotpSettings.test.tsx` | Component | TOTP QR code, verify, disable |
| `ActivateInvitePage.test.tsx` | Component | Invite activation flow |

### Cobertura Target

| Domínio | Meta atual | Meta Wave 2 |
|---------|-----------|------------|
| auth | > 70% | > 85% |
| experiments / lab | > 60% | > 80% |
| policy | > 75% | > 90% |
| economics | > 40% | > 80% |
| audit_chain | > 80% | > 90% |
| workers | > 50% | > 75% |
| **Global** | > 55% | **> 80%** |

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
| **workspace** | Conta isolada de um cliente no sistema (equiv. org/tenant) |
| **platform_admin** | Administrador global sem workspace (operação interna) |
| **workspace_admin** | Administrador do workspace do cliente |
| **analyst** | Usuário operacional com permissões de escrita analítica |
| **viewer** | Usuário de leitura |
| **CloudCredential** | Credencial multi-cloud multi-registro por workspace (cifrada com WorkspaceKeyring) |
| **WorkspaceKeyring** | Chave Fernet org-scoped para criptografia de credenciais, com rotação automática |
| **WorkspaceBudget** | Orçamento financeiro configurável por workspace |
| **ActivityEvent** | Evento de log de atividade do cloud provider |
| **AlertRecord** | Alerta gerado por categoria no sistema |
| **ProviderRecommendation** | Recomendação importada do cloud provider (Advisor) |
| **SyncRecord** | Estado de sincronização por conector e workspace |
| **SkuObservation** | Observação de SKU por workspace e período |
| **ResourceInventory** | Inventário de recursos para governança |
| **CarbonRecord** | Emissão de carbono por conta e período |
| **DlqMessage** | Mensagem na dead letter queue após 3 falhas de processamento |
| **ReportExportJob** | Job assíncrono de exportação CSV/Excel com status e file_url |
| **LgpdConsent** | Registro de consentimento LGPD: base legal, propósito, versão, timestamp |
| **TotpBackupCode** | Código one-time de recuperação de conta (10 por usuário, invalidados após uso) |
| **RevokedToken** | JWT revogado explicitamente (blacklist Redis + PostgreSQL) |
| **IdempotencyKey** | Chave Redis SHA-256 para replay seguro de mutações críticas (TTL 24h) |
| **SCA** | Stratum Causal Attribution — engine de atribuição causal de variações de custo |
| **ARI** | Adaptive Recommendation Index — ranking adaptativo de oportunidades |
| **PulseLab** | Módulo de criação e execução de experimentos de otimização com canário |
| **StratoAudit** | Trilha de auditoria imutável com hash SHA-256 encadeado |
