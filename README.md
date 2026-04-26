# CauSium

---

> **Stop wasting money on cloud.**
>
> **CauSium turns cloud cost data into safe, governed optimization decisions.**
>
> **FinOps Intelligence & Governed Execution Platform**
>
> Plataforma de inteligência de eficiência cloud orientada a decisão segura (SAFE DSS).

- 💰 Reduce cloud costs safely
- ⚙️ Governed execution (no risky automation)
- 🔐 Enterprise-grade safety (SAFE DSS)
- 🤖 AI-powered insights

---

## 🎯 Why CauSium

Dashboards tradicionais ajudam a visualizar custos, mas não fecham o ciclo de decisão e execução.
Ferramentas de automação pura aceleram mudanças, porém podem aumentar risco operacional quando faltam governança e trilha de decisão.

O CauSium resolve esse gap combinando inteligência de custo, priorização orientada a impacto e execução governada, com controle humano e segurança.

---

## ✅ What You Get

- Identify waste automatically.
- Prioritize opportunities by impact and risk.
- Approve and schedule execution with governance.
- Track real savings with operational traceability.
- Learn and improve decisions over time.

---

## 📊 Product Preview

![Dashboard](./docs/images/dashboard.png)
![Opportunities](./docs/images/opportunities.png)
![Optimization Plan](./docs/images/plan.png)

> Preview placeholders: substitua as imagens conforme os assets oficiais do produto forem versionados.

---

## 🚀 How CauSium Is Different

- **Dashboards**: mostram dados, mas não governam execução.
- **Automation tools**: executam rápido, porém com risco quando não há controle robusto.
- **CauSium**: conecta visibilidade, inteligência e execução controlada com segurança enterprise.

---

```text
Detect -> Analyze -> Recommend -> Approve -> Execute -> Measure -> Learn
```

---

## Status Geral (Sprint 12 SAFE DSS)

O produto está em **Sprint 12** como **Decision Support System (DSS)**.

- **✅ DONE**: recomenda, prioriza, planeja, aprova, agenda, faz handoff e mede resultado.
- **✅ DONE**: trilha de auditoria e governança para decisões.
- **✅ DONE**: execução acompanhada por status e evidências.
- **⚠️ PARTIAL**: capacidades avançadas adaptativas em evolução.
- **NÃO IMPLEMENTADO**: mutação cloud automática (Azure/AWS/GCP/AKS) em produção.

---

## ✨ Visão de Produto

### 💰 Cost Visibility
Visibilidade de custos e sinais operacionais com suporte a análise de oportunidades e anomalias.

### ⚙️ Optimization Engine
Motor de priorização e planejamento orientado a execução controlada, com trilha de decisão e status de execução.

### 🔐 Security Layer
Governança de acesso, trilha auditável, guardrails de execução e proteção de endpoints sensíveis em produção.

---

## 🧱 Arquitetura Visual (Resumo)

```text
User
  ↓
Frontend (React)
  ↓
Backend (FastAPI)
  ↓
Decision Engine
  ↓
Workers → Cloud Providers
```

---

## Matriz de Módulos

| Module | Status | Notes |
|:---|:---:|:---|
| VM rightsizing | ✅ DONE | Geração e priorização de oportunidades com evidência e confiança. |
| AKS nodepool rightsizing | ⚠️ PARTIAL | Categoria e pipeline presentes; cobertura funcional ainda evoluindo. |
| AKS autoscaler recommendation | ⚠️ PARTIAL | Categoria/modelagem presentes; maturidade operacional em evolução. |
| Optimization Plan | ⚠️ PARTIAL | Geração e priorização implementadas; execução cloud automática não existe. |
| Execution Plans | ⚠️ PARTIAL | Criação, status, aprovação/scheduling/handoff e tracking implementados no DSS. |
| Approval/Scheduling/Handoff/Execution tracking | ✅ DONE | Fluxos e auditoria de transição implementados. |
| Confidence Calibration / Adaptive Decision Engine (Sprint 12) | ⚠️ PARTIAL | Base de calibração e ajustes existentes, evolução contínua. |
| Cost Anomaly Detection | ⚠️ PARTIAL | Serviço + worker + endpoints; exposição e operação em amadurecimento. |
| Platform Admin (/admin) | ✅ DONE | Gestão cross-workspace, lifecycle, suporte auditado, DLQ. |
| LGPD BASIC READY | ✅ DONE | Consentimento, anonimização, retenção e auditoria administrativa sem PII. |
| Semi-automação cloud opt-in (Sprint 13) | 🧭 ROADMAP | Próxima etapa, com guardrails. |
| Policy Engine / guardrails avançados | 🧭 ROADMAP | Expansão de políticas de execução segura. |
| Rollback / execution safety avançado | 🧭 ROADMAP | Mecanismos adicionais de proteção e reversão. |
| DB/storage optimizations | 🧭 ROADMAP | Melhorias de performance e custo operacional. |
| Key Vault hardening | 🧭 ROADMAP | Endurecimento de gestão de segredos em produção. |
| Production hardening | 🧭 ROADMAP | Reforço operacional e de segurança para escala. |
| Observability expansion | 🧭 ROADMAP | Ampliação de SLI/SLO, métricas e tracing. |
| Billing/Pricing | 🧭 ROADMAP | Estrutura comercial e cobrança. |
| Onboarding refinements | 🧭 ROADMAP | UX e fluxos de ativação aprimorados. |
| LGPD FULL | 🧭 ROADMAP | Evolução para cobertura regulatória ampliada. |

---

## Workspace Lifecycle (Estado Real)

Estados atualmente suportados:

- `ACTIVE`
- `SUSPENDED`
- `ARCHIVED`

Transições principais:

- `ACTIVE -> SUSPENDED`
- `SUSPENDED -> ACTIVE`
- `SUSPENDED -> ARCHIVED`

> `INACTIVE` e `PURGED` **não** são estados reais do lifecycle de workspace no código atual.

---

## Migrações (Atualizado)

A última migração atualmente é:

- `0039_user_deleted_at_retention.py`

Resumo das migrações `0030` a `0039`:

- `0030_cost_anomalies.py` - tabela/base para anomalias de custo.
- `0031_opportunity_sku_family.py` - extensão de oportunidade por família de SKU.
- `0032_usage_observations.py` - observações de uso para inteligência operacional.
- `0033_opportunity_decision_evidence.py` - evidências de decisão em oportunidades.
- `0034_opportunity_category_aks_nodepool_rightsizing.py` - categoria AKS nodepool rightsizing.
- `0035_opportunity_category_aks_autoscaler_recommendation.py` - categoria AKS autoscaler recommendation.
- `0036_execution_plans.py` - estruturas de execution plans.
- `0037_confidence_calibrations.py` - calibrações de confiança do motor.
- `0038_support_access_sessions.py` - sessões de suporte administrativo.
- `0039_user_deleted_at_retention.py` - `deleted_at` para retenção/anonimização LGPD.

---

## LGPD

Status atual: **LGPD BASIC READY**.

Implementado:

- `terms_accepted_at` e `terms_version` para registro de aceite.
- `anonymize_user_identity` para anonimização irreversível de identidade.
- `deleted_at` para controle de retenção.
- `lgpd_purge_user` para fluxo de purga lógica com anonimização.
- Retention worker (30 dias) para usuários inativos com `deleted_at` elegível.
- Payloads administrativos de auditoria sem e-mail original (sem PII), com rastreabilidade por `target_user_id`.

LGPD FULL (roadmap):

- Catálogo ampliado de bases legais por domínio.
- Automação de prazos por tipo de dado.
- Relatórios de conformidade e rotinas operacionais avançadas.

---

## Platform Admin

Domínio administrativo: `/admin` (perfil `platform_admin`).

Capacidades implementadas:

- Gestão cross-workspace (`/admin/orgs`, `/admin/orgs/{org_id}`, `/admin/orgs/{org_id}/users`).
- Lifecycle organizacional (`/admin/orgs/{org_id}/suspend|restore|archive`).
- Gestão de DLQ (`/admin/dlq`, `/admin/dlq/{dlq_id}/requeue`).
- Suporte operacional com sessões auditadas:
  - criação: `/admin/support-access`
  - listagem ativa: `/admin/support-access/active`
  - encerramento: `/admin/support-access/{session_id}/end`

Regras de support access (MVP atual):

- `read-only` (somente `GET/HEAD/OPTIONS` quando sessão está ativa).
- `reason` obrigatório para iniciar/encerrar sessão.
- duração máxima: **60 min**.
- eventos auditados (`support_access.started`, `support_access.ended`).

---

## Segurança

Controles relevantes do estado atual:

### 🔐 Security Layer
Proteções em runtime, guardrails de pipeline e auditoria contínua para operação enterprise.

### 🛡️ Cloud Safety Guardrails
Execução orientada a modo read-only e bloqueios explícitos para cenários de risco em produção.

### 📜 Compliance & Access Audit
Rastreabilidade de sessões administrativas, ações sensíveis e proteção de dados.

- Cloud onboarding e operação em modo **read-only**.
- CI com guardrail de mutação cloud (`scripts/cloud_mutation_guardrail.py`).
- `/health/detailed` e `/metrics` protegidos por `X-Internal-Key` em produção.
- Fallback de Azure mock **bloqueado** em produção.
- Warning para permissões Azure elevadas (`Owner/Contributor`).
- Credenciais cloud criptografadas (escopo por workspace/keyring).
- Sessões de support access auditadas.

---

## Decision Engine e Execução SAFE DSS

Estado funcional até Sprint 12:

### ⚙️ Optimization Engine
Pipeline de decisão e execução assistida com foco em governança, rastreabilidade e segurança operacional.

- **DONE**: geração/priorização de oportunidades e trilha auditável.
- **PARTIAL**: trilhas AKS (nodepool/autoscaler) em evolução.
- **PARTIAL**: optimization/execution plans com aprovação, scheduling, handoff e tracking no DSS.
- **NÃO IMPLEMENTADO**: aplicação automática de mutações cloud.

---

## Anomaly Detection

Implementado no backend com status **PARTIAL**:

- `anomaly_detection_worker` em execução no runner.
- serviço de anomalia de custo (`CostAnomalyDetectionService`).
- endpoints de detecção/listagem de anomalias.

---

## Workers

Runner atual contempla **10 workers**:

1. `ingestion`
2. `scoring`
3. `anomaly_detection`
4. `audit_checkpoint`
5. `economics_export`
6. `keyring_rotation`
7. `carbon_sync`
8. `maintenance`
9. `notification`
10. `usage_observation`

---

## Stack Tecnológica (Atualizada)

Backend e plataforma:

- FastAPI
- Python
- PostgreSQL
- ClickHouse
- Redis
- OpenTelemetry
- Prometheus/Grafana

Frontend:

- React
- TypeScript

Observação:

- `pyotp` não é listado como dependência ativa no estado atual do código.

---

## API (Resumo)

Principais grupos:

- `/api/v1/auth/*`
- `/api/v1/intel/*`
- `/api/v1/audit-chain/*`
- `/api/v1/admin/*`

Admin (`/api/v1/admin/*`) inclui:

- org listing/detail/users
- org lifecycle suspend/restore/archive
- support access sessions
- DLQ list/requeue

---

## Roadmap Sprint 13+

Prioridades planejadas:

- Semi-automação opt-in para execução cloud (com aprovação explícita).
- Policy Engine e guardrails avançados.
- Rollback e execution safety avançado.
- Otimizações de banco/storage.
- Integração e hardening de Key Vault.
- Production hardening.
- Expansão de observabilidade.
- Estrutura de billing/pricing.
- Refinamentos de onboarding.
- Evolução de LGPD BASIC READY para LGPD FULL.

---

## 🚀 Roadmap — Próximas Sprints (Execution -> Intelligence)

O CauSium evolui de um sistema de recomendação (SAFE DSS) para uma plataforma completa de execução governada e inteligência de custos.

---

### 🟡 Sprint 13 — Assisted Execution (Execução Assistida)

Primeiro passo para execução real, mantendo controle humano total.

- Execução manual de ações diretamente pela interface (ex: resize de VM, ajustes de nodepool).
- Botão "Apply" real, integrado ao Execution Plan.
- Confirmação explícita antes de qualquer mudança (double confirmation).
- Execução limitada a ações seguras e bem definidas.
- Logs completos de execução (auditáveis).
- Feature flag para habilitação controlada (por plano/workspace).

Regra principal:
> Nenhuma ação é executada automaticamente. Toda execução é iniciada pelo usuário.

---

### 🟡 Sprint 14 — Policy Engine (Governança de Execução)

Camada de governança que define o que pode ou não ser executado.

- Regras configuráveis por workspace (policies).
- Bloqueio automático de ações de alto risco.
- Restrições por ambiente (produção, staging, dev).
- Limites configuráveis (ex: máximo de redução de recursos).
- Allow/Deny por tipo de recurso ou categoria de otimização.
- Validação obrigatória de policy antes de qualquer execução.

Exemplo:
> "Não reduzir CPU de workloads críticos em produção"

---

### 🟡 Sprint 15 — Safety & Rollback (Segurança de Execução)

Garantia de que nenhuma execução compromete o ambiente do cliente.

- Snapshot/checkpoint antes de aplicar mudanças.
- Rollback automático em caso de falha.
- Monitoramento pós-execução.
- Timeout e cancelamento de execuções.
- Mecanismo de fallback para restaurar estado anterior.

Exemplo:
> "Se a performance degradar após o resize, reverter automaticamente"

---

### 🟡 Sprint 16 — Controlled Automation (Automação Controlada)

Introdução de automação com limites e governança.

- Auto-apply para ações de baixo risco.
- Execução programada (ex: janelas de manutenção).
- Aprovação automática baseada em policy.
- Limites de execução por workspace.
- Execuções restritas a horários seguros.

Neste estágio:
> O sistema pode executar automaticamente, mas sempre dentro de regras definidas.

---

## 🏆 Roadmap Premium — Diferenciação do Produto

Após a base de execução, o foco evolui para inteligência e valor estratégico.

---

### 🟣 Sprint 17 — Cost Intelligence (Nível Executivo)

Transformar dados técnicos em insights estratégicos.

- Forecast de custos (previsão futura).
- Projeção de economia baseada em ações.
- Análise de tendências de gasto.
- Identificação automática de desperdício.

Exemplo:
> "Seu custo tende a crescer 18% no próximo mês"

---

### 🟣 Sprint 18 — What-if Simulation (Simulação de Cenários)

Capacidade de simular impacto antes de executar mudanças.

- Simulação de cenários de otimização.
- Comparação de alternativas.
- Previsão de economia antes da execução.

Exemplo:
> "Aplicando essa mudança, você economiza $12k/ano"

---

### 🟣 Sprint 19 — Unit Economics (Visão de Negócio)

Levar FinOps para o nível de negócio.

- Custo por produto.
- Custo por cliente.
- Custo por feature.
- Análise de margem por serviço.

Exemplo:
> "Esta feature custa $0.23 por usuário ativo"

---

### 🟣 Sprint 20 — FinOps Governance Enterprise

Governança para organizações complexas.

- Orçamento por equipe/squad.
- Ownership de recursos (accountability).
- Chargeback e showback.
- Controle distribuído de custos.

---

### 🟣 Sprint 21 — AI Copilot (Assistente Inteligente)

IA como copiloto de decisões de FinOps.

- Recomendações acionáveis em linguagem natural.
- "Top 3 ações para hoje".
- Identificação automática de oportunidades.
- Insights prontos para execução.

---

### 🟣 Sprint 22 — Autonomous FinOps (Opcional)

Automação avançada com supervisão.

- Execução automática baseada em policy.
- Decisão assistida por IA.
- Limites rígidos de segurança.
- Rollback automático integrado.

Nota:
> Esta etapa é opcional e depende do nível de maturidade do produto e dos clientes.

---
