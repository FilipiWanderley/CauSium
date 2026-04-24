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

## Testes (pytest) apos migracao

- O `pytest` ja esta declarado no codigo em `backend/pyproject.toml` no grupo de dependencias `dev`.
- Para instalar no ambiente local:
  - `cd backend`
  - `poetry install --with dev`
- Para executar os testes:
  - `python -m pytest`
