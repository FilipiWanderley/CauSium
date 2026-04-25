# CauSium Backend

Status técnico consolidado (até Sprint 12):

- Produto em modo **SAFE DSS**: recomenda, prioriza, planeja, agenda e faz handoff controlado.
- Não existe execução automática de mutações cloud em Azure/AWS/GCP/AKS.
- `ExecutionPlan` persiste plano/status/aprovação/agendamento/handoff sem aplicar mudança real em provider.
- `PulseLab handoff` cria experimento e vínculo de controle, sem executar alteração de infraestrutura.
- Sprint 12 adiciona Adaptive Decision Engine para estratégia AKS (`recommended_strategy`, `alternative_strategy`, `confidence_boosted`) sem executor cloud.

## Segurança e Guardrails

- CI bloqueia assinaturas de mutação cloud em `backend/app` via:
  - `scripts/cloud_mutation_guardrail.py`
  - `.security/cloud_mutation_guardrail_allowlist.txt`
- Padrões monitorados: `begin_create_or_update`, `create_or_update`, `run_instances`, `stop_instances`, `delete_resource`, `delete_`, `.patch(`, `resize`, `scale`, `setIamPolicy`.
- Exceções só via allowlist com justificativa explícita.
- Checklist de revisão em PR exige confirmação de:
  - não mutação cloud,
  - não uso de APIs `create/update/delete/patch/scale`,
  - manutenção de credenciais read-only,
  - feature flag + aprovação explícita em caso de exceção.

## Onboarding Read-Only

Referência oficial: `docs/security/cloud-read-only-onboarding.md`

- Azure: `Reader` + `Cost Management Reader`
- AWS: `ReadOnlyAccess` + leitura de Billing/CUR
- GCP: `Viewer` + `Billing Viewer`
- AKS/Kubernetes: apenas `get/list/watch`

## Execução local do guardrail

```bash
python scripts/cloud_mutation_guardrail.py --target backend/app --allowlist .security/cloud_mutation_guardrail_allowlist.txt
```
