# CauSium Backend

Resumo técnico das últimas entregas:

- Ingestão em tempo real de notificações para eventos cloud críticos (VM start/stop e criação de recurso).
- Nova tabela PostgreSQL `usage_observations` com agregações operacionais de uso.
- Novo `usage_observation_worker` (intervalo configurável) para consolidar sinais de `usage_facts`.
- Novo endpoint IA: `GET /api/v1/opportunities/{opp_id}/explain`.
- Migração Alembic adicionada: `0032_usage_observations.py`.
- Audit trail de status de oportunidade no `PATCH /api/v1/opportunities/{opp_id}/status`.
- Eventos no `audit_chain`: `opportunity.accepted`, `opportunity.ignored`, `opportunity.dismissed`.
- Payload estruturado de auditoria com `estimated_savings_usd`, `confidence`, `risk_level` e `decision_evidence`.
- Mapeamento de transições: `open->resolved` (accepted), `open->dismissed` (ignored), `in_progress->dismissed` (dismissed).
- Teste de integração cobrindo os três eventos de auditoria.

## Próximo épico

`AKS Node Pool Rightsizing (Nível 2)` com implementação incremental começando por `node_count reduction`, seguido de `autoscaler`, `spot nodepool` e `pod rightsizing`.
