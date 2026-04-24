# CauSium Backend

Resumo técnico das últimas entregas:

- Ingestão em tempo real de notificações para eventos cloud críticos (VM start/stop e criação de recurso).
- Nova tabela PostgreSQL `usage_observations` com agregações operacionais de uso.
- Novo `usage_observation_worker` (intervalo configurável) para consolidar sinais de `usage_facts`.
- Novo endpoint IA: `GET /api/v1/opportunities/{opp_id}/explain`.
- Migração Alembic adicionada: `0032_usage_observations.py`.
