# Migracao Stratopulse -> CauSium_push (2026-04-24)

## Objetivo

Migrar todos os dados e operacao do ambiente antigo `stratopulse` para `causium_push`, mantendo apenas o ambiente novo em uso.

## Escopo executado

- Migracao de dados PostgreSQL do `stratopulse` para o `causium_push`.
- Migracao de dados ClickHouse (analytics) do `stratopulse` para o `causium_push`.
- Validacao de login e de entidades principais apos restauracao.
- Desativacao e remocao dos containers `stratopulse-*`.
- Backup final dos volumes antigos `stratopulse_*`.
- Remocao dos volumes antigos `stratopulse_*` apos backup.

## Evidencias de validacao

- Login validado no backend com sucesso.
- Organizacoes presentes no PostgreSQL do `causium_push`.
- Tabelas ClickHouse presentes:
  - `carbon_facts`
  - `cost_facts`
  - `event_facts`
  - `recommendation_facts`
  - `resource_inventory`
  - `usage_facts`
- Contagens observadas no ClickHouse:
  - `carbon_facts`: 40
  - `resource_inventory`: 552
  - `recommendation_facts`: 1222
  - `usage_facts`: 3762
  - `event_facts`: 9591
  - `cost_facts`: 3817

## Backup de seguranca gerado

Diretorio:

- `_db_migration_backup/stratopulse_volumes_20260424_102252`

Arquivos:

- `stratopulse_clickhouse_data.tar.gz`
- `stratopulse_grafana_data.tar.gz`
- `stratopulse_postgres_data.tar.gz`
- `stratopulse_prometheus_data.tar.gz`
- `stratopulse_redis_data.tar.gz`

## Estado final

- Ambiente ativo: apenas `causium_push-*`.
- Containers `stratopulse-*`: removidos.
- Volumes `stratopulse_*`: removidos (apos backup final).
Sobre commit + push

Sim, faz isso agora — mas com padrão de produto (não só código).

Mensagem de commit recomendada
feat(decision-engine): add audit trail for opportunity status transitions

- track accept/ignore/dismiss actions in audit_chain
- include structured payload (savings, confidence, risk, decision_evidence)
- map lifecycle events to audit types (accepted, ignored, dismissed)
- pass actor_user_id from authenticated context
- add integration tests for audit events
🚀 Próximo épico (já pode começar)
EPIC: AKS Node Pool Rightsizing
Primeiro escopo (não complica ainda)
1. coletar métricas de node pool
2. calcular cpu/memória p95 por node
3. detectar nodes ociosos
4. sugerir redução de node count
5. calcular economia
6. gerar recommendation + decision_evidence
7. explain IA (reaproveita tudo)
🧭 Dica importante (pra não errar agora)

Não tente fazer tudo de AKS de uma vez.

Comece com:

node_count reduction

Depois evolui para:

autoscaler
spot nodepool
pod rightsizing
🧠 Resumo direto
Nível 1: COMPLETO ✅
Produto já entrega valor real

Próximo passo:
AKS optimization (Nível 2)
## Testes (pytest) apos migracao

- O `pytest` ja esta declarado no codigo em `backend/pyproject.toml` no grupo de dependencias `dev`.
- Para instalar no ambiente local:
  - `cd backend`
  - `poetry install --with dev`
- Para executar os testes:
  - `python -m pytest`
