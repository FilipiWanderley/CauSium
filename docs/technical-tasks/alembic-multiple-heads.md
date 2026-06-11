# Task Técnica: Resolver Múltiplas Heads do Alembic

**Task ID:** TECH-001  
**Data de Criação:** 2026-06-11  
**Status:** Pendente  
**Prioridade:** Alta  
**Origem:** Incidente 2026-06-11  

---

## Problema

O graph de migrations do Alembic possui múltiplas heads, causando falha na execução de `alembic upgrade head`.

### Sintomas

```
ERROR [alembic.util.messaging] Multiple head revisions are present for given argument 'head'
please specify a specific target revision, '<branchname>@head' to narrow to a specific head, or 'heads' for all heads
```

### Impacto

- Migrations automáticas em produção falham
- Backend não inicia corretamente
- Dashboard fica indisponível

---

## Estado Atual

### Alembic Status (11/06/2026)

```bash
$ alembic current
0042

$ alembic heads
0044 (head)

$ alembic branches
0007 (branchpoint)
     -> 0008a_notifications_alerts
     -> 0008
```

### Estrutura do Graph

```
<base>
  ├─> 0001 -> 0002 -> ... -> 0007 (branchpoint)
  | ├─> 0008a_notifications_alerts -> 0009 -> ... -> 0025_merge_workspace_lifecycle -> ... -> 0044
  |                       └─> 0008 ----> ... --------------->
  |
  └─> provider_recommendation_sync (raiz separada)
  
E tambem:
  0022_blob_ingestion_checkpoints -> 0023_aws_cur_ingestion_checkpoints -> 0025_merge_workspace_lifecycle
```

### Merge Point

`0025_merge_workspace_lifecycle` é um merge point que deveria unir:
- `0008`
- `0023_aws_cur_ingestion_checkpoints`
- `provider_recommendation_sync`

---

## Root Cause

O merge point `0025_merge_workspace_lifecycle` não está resolvendo corretamente as múltiplas branches no graph do Alembic.

### Análise

1. Migration `0024_provider_recommendation_sync.py` tem `down_revision = None`
2. Migration `0025_merge_workspace_lifecycle.py` referencia `provider_recommendation_sync` como um dos down_revisions
3. Mas a chain principal continua através de `0008` e `0023_aws_cur_ingestion_checkpoints`

### Hipótese

O merge point 0025 foi criado mas as migrations após ele (0026-0044) estão em uma branch separada que não está sendo considerada pelo merge.

---

## Solução Proposta

### Opção 1: Verificar e corrigir o merge point

1. Analisar se o merge point 0025 está correto
2. Verificar se todas as branches estão sendo unidas
3. Criar nova migration de merge se necessário

### Opção 2: Criar nova merge migration

1. Identificar a head correta (0044)
2. Criar merge migration que una todas as branches
3. Testar upgrade e downgrade

### Opção 3: Resolver via branch labels

1. Adicionar branch labels às migrations
2. Criar merge migration específica
3. Documentar a estrutura do graph

---

## Passos para Execução (NÃO EXECUTAR AINDA)

### Fase 1: Análise

```bash
# 1. Verificar estado atual
cd backend
alembic current
alembic heads
alembic branches
alembic history --verbose

# 2. Identificar todas as chains
# Listar todas as migrations e suas dependencies

# 3. Verificar merge point atual
cat alembic/versions/0025_merge_workspace_lifecycle.py
```

### Fase 2: Preparação

```bash
# 1. Fazer backup do banco
make backup

# 2. Criar branch de trabalho
git checkout -b fix/alembic-multiple-heads

# 3. Documentar estado atual
```

### Fase 3: Implementação

```bash
# 1. Criar merge migration
cd backend
alembic merge -m "merge all heads after 0025"

# 2. Verificar se只有一个 head
alembic heads

# 3. Testar upgrade
alembic upgrade head

# 4. Testar downgrade
alembic downgrade -1
alembic upgrade head

# 5. Verificar banco
alembic current
```

### Fase 4: Validação

```bash
# 1. Executar testes
pytest -v

# 2. Testar funcionalidades críticas
# - Login
# - Dashboard
# - APIs

# 3. Verificar logs
```

### Fase 5: Deploy

```bash
# 1. Commit
git add .
git commit -m "fix(alembic): resolve multiple heads by creating merge migration"

# 2. Push
git push origin fix/alembic-multiple-heads

# 3. Criar PR
# 4. Aguardar aprovação
# 5. Merge para main
# 6. Deploy via CI/CD
```

---

## Rollback

### Estratégia

Se algo der errado, reverter para o commit anterior ao merge.

### Commit de Retorno

```
# Identificar commit antes do merge
git log --oneline

# Rollback
git revert <merge-commit-sha>
git push origin main
```

### Passos de Rollback

1. Identificar SHA do commit com problema
2. `git revert<sha>`
3. `git push origin main`
4. Aguardar deploy via CI/CD
5. Validar health check
6. Validar dashboard

---

## Validações Necessárias

### Pré-execução

- [ ] Backup validado
- [ ] Estado do Alembic documentado
- [ ] Plano aprovado
- [ ] Rollback documentado

### Pós-execução

- [ ] `alembic heads` retorna apenas uma head
- [ ] `alembic current` funciona
- [ ] `alembic upgrade head` funciona
- [ ] `alembic downgrade -1` funciona
- [ ] Testes passando
- [ ] Health check OK
- [ ] Dashboard funcionando

---

## ⚠️ IMPORTANTE

### NÃO EXECUTAR

- ❌ Nenhuma migration em produção
- ❌ Nenhum `alembic upgrade head` em produção
- ❌ Nenhum merge sem validação local completa

### APENAS

- ✅ Documentar o problema
- ✅ Planejar a solução
- ✅ Preparar rollback
- ✅ Aguardar aprovação

---

## Status

| Fase | Status |
|------|--------|
| Análise | ⬜ Pendente |
| Preparação | ⬜ Pendente |
| Implementação | ⬜ Pendente |
| Validação | ⬜ Pendente |
| Deploy | ⬜ Pendente |

---

## Referências

- `docs/incidents/2026-06-11-dashboard-outage.md` - Incidente original
- `docs/architecture/engineering-policy.md` - Políticas de engenharia
- `CLAUDE.md` - Regras de engenharia

---

## Responsável

A definir após aprovação