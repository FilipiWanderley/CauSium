# CauSium

Plataforma de inteligência de eficiência cloud orientada a decisão segura (SAFE DSS).

## Status Geral (Sprint 12 SAFE DSS)

O produto está em **Sprint 12** como **Decision Support System (DSS)**.

- **DONE**: recomenda, prioriza, planeja, aprova, agenda, faz handoff e mede resultado.
- **DONE**: trilha de auditoria e governança para decisões.
- **DONE**: execução acompanhada por status e evidências.
- **PARTIAL**: capacidades avançadas adaptativas em evolução.
- **NÃO IMPLEMENTADO**: mutação cloud automática (Azure/AWS/GCP/AKS) em produção.

## Matriz de Módulos

| Module | Status | Notes |
|---|---|---|
| VM rightsizing | DONE | Geração e priorização de oportunidades com evidência e confiança. |
| AKS nodepool rightsizing | PARTIAL | Categoria e pipeline presentes; cobertura funcional ainda evoluindo. |
| AKS autoscaler recommendation | PARTIAL | Categoria/modelagem presentes; maturidade operacional em evolução. |
| Optimization Plan | PARTIAL | Geração e priorização implementadas; execução cloud automática não existe. |
| Execution Plans | PARTIAL | Criação, status, aprovação/scheduling/handoff e tracking implementados no DSS. |
| Approval/Scheduling/Handoff/Execution tracking | DONE | Fluxos e auditoria de transição implementados. |
| Confidence Calibration / Adaptive Decision Engine (Sprint 12) | PARTIAL | Base de calibração e ajustes existentes, evolução contínua. |
| Cost Anomaly Detection | PARTIAL | Serviço + worker + endpoints; exposição e operação em amadurecimento. |
| Platform Admin (/admin) | DONE | Gestão cross-workspace, lifecycle, suporte auditado, DLQ. |
| LGPD BASIC READY | DONE | Consentimento, anonimização, retenção e auditoria administrativa sem PII. |
| Semi-automação cloud opt-in (Sprint 13) | ROADMAP | Próxima etapa, com guardrails. |
| Policy Engine / guardrails avançados | ROADMAP | Expansão de políticas de execução segura. |
| Rollback / execution safety avançado | ROADMAP | Mecanismos adicionais de proteção e reversão. |
| DB/storage optimizations | ROADMAP | Melhorias de performance e custo operacional. |
| Key Vault hardening | ROADMAP | Endurecimento de gestão de segredos em produção. |
| Production hardening | ROADMAP | Reforço operacional e de segurança para escala. |
| Observability expansion | ROADMAP | Ampliação de SLI/SLO, métricas e tracing. |
| Billing/Pricing | ROADMAP | Estrutura comercial e cobrança. |
| Onboarding refinements | ROADMAP | UX e fluxos de ativação aprimorados. |
| LGPD FULL | ROADMAP | Evolução para cobertura regulatória ampliada. |

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

## Segurança

Controles relevantes do estado atual:

- Cloud onboarding e operação em modo **read-only**.
- CI com guardrail de mutação cloud (`scripts/cloud_mutation_guardrail.py`).
- `/health/detailed` e `/metrics` protegidos por `X-Internal-Key` em produção.
- Fallback de Azure mock **bloqueado** em produção.
- Warning para permissões Azure elevadas (`Owner/Contributor`).
- Credenciais cloud criptografadas (escopo por workspace/keyring).
- Sessões de support access auditadas.

## Decision Engine e Execução SAFE DSS

Estado funcional até Sprint 12:

- **DONE**: geração/priorização de oportunidades e trilha auditável.
- **PARTIAL**: trilhas AKS (nodepool/autoscaler) em evolução.
- **PARTIAL**: optimization/execution plans com aprovação, scheduling, handoff e tracking no DSS.
- **NÃO IMPLEMENTADO**: aplicação automática de mutações cloud.

## Anomaly Detection

Implementado no backend com status **PARTIAL**:

- `anomaly_detection_worker` em execução no runner.
- serviço de anomalia de custo (`CostAnomalyDetectionService`).
- endpoints de detecção/listagem de anomalias.

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
