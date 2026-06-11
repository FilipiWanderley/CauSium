# Incidente: Dashboard Indisponível

**Data:** 2026-06-11  
**Severidade:** Alta  
**Status:** Resolvido  
**Duração:** ~8 horas (00:00 - 08:00 BRT)  

---

## Timeline

| Horário | Evento |
|---------|--------|
| 2026-06-10 20:00 BRT | Último deploy funcional (commit 27297061422) |
| 2026-06-10 21:30 BRT | Deploy com alterações no Alembic (commit 27168190891) - FALHOU |
| 2026-06-10 21:31 BRT | Container começa a falhar |
| 2026-06-11 00:00 BRT | Alerta de produção recebido |
| 2026-06-11 08:00 BRT | Investigação iniciada |
| 2026-06-11 10:00 BRT | Causa raiz identificada |
| 2026-06-11 13:27 BRT | Hotfix deployed (commit dbe5ac1) |
| 2026-06-11 13:35 BRT | Dashboard restaurado |

---

## Impacto

| Item | Descrição |
|------|-----------|
| **Serviço Afetado** | Backend API + Dashboard |
| **Usuários Impactados** | Todos os usuários do CauSium |
| **Funcionalidades Indisponíveis** | Dashboard, Spend Analysis, Savings Opportunities |
| **Impacto Financeiro** | Cliente sem visibilidade de custos |

---

## Causa Raiz

### Problema

O startup da aplicação executava `alembic upgrade head` automaticamente.

### Root Cause

Existiam **múltiplas heads** no graph de migrations do Alembic:

```
alembic heads
0044 (head)
alembic branches
0007 (branchpoint)
     -> 0008a_notifications_alerts
     -> 0008
```

O merge point `0025_merge_workspace_lifecycle` não estava resolvendo corretamente as múltiplas branches, causando o erro:

```
Multiple head revisions are present for given argument 'head'
please specify a specific target revision, '<branchname>@head' to narrow to a specific head, or 'heads' for all heads
```

### Chain of Events

1. Commit 27168190891 fez push com alterações no Alembic
2. GitHub Actions deployou para Azure
3. Oryx (framework de build) gerou script `/opt/startup/startup.sh`
4. Script executou `alembic upgrade head`
5. Alembic falhou com erro de múltiplas heads
6. Container crashou
7. App Service reiniciava o container em loop

---

## Resolução

### Ação Imediata

1. Identificado que `backend/entrypoint.sh` executava migrations
2. Modificado entrypoint para apenas executar comando sem migrations:
   ```bash
   # Antes (98 linhas com alembic)
   # Depois (10 linhas simples)
   exec "$@"
   ```
3. Commit dbe5ac1 com hotfix
4. GitHub Actions deployou automaticamente
5. Dashboard restaurado

### Análise

O `/home/site/wwwroot/entrypoint.sh` continha:
```bash
echo "[entrypoint] Running migrations: alembic upgrade head"
alembic upgrade head
```

O Azure executa `startup.sh` que chama o entrypoint, causando as migrations.

---

## Lições Aprendidas

### 1. Migrations Automáticas em Produção são Perigosas

**Problema:** O startup executava migrations automaticamente sem verificar se era seguro.

**Solução:** Migrations devem ser executadas via CI/CD, não no startup.

### 2. Múltiplas Heads Devem Ser Resolvidas Antes de Deploy

**Problema:** O graph de migrations tinha múltiplas heads não resolvidas.

**Solução:** Verificar `alembic heads` e `alembic branches` antes de qualquer deploy.

### 3. Hotfix em Produção Tem Risco

**Problema:** A pressa para restaurar pode introduzir novos bugs.

**Solução:** Mesmo em emergência, seguir fluxo de diagnóstico → plano → diff.

---

## Ação Corretiva

### Implementado

- [x] Entrypoint desabilitou migrations (hotfix)
- [x] CLAUDE.md criado com regras de engenharia
- [x] CONTRIBUTING.md criado
- [x] docs/architecture/engineering-policy.md criado
- [x] docs/runbooks/deployment-checklist.md criado
- [x] Este registro de incidente criado

### Pendente

- [ ] Resolver múltiplas heads do Alembic (0025_merge_workspace_lifecycle)
- [ ] Reabilitar migrations via CI/CD (não no startup)
- [ ] Adicionar verificação de Alembic no CI/CD
- [ ] Testar migrations em staging antes de production

---

## Prevenção

### Regras Implementadas

1. ✅ Migrations automáticas em produção: **PROIBIDAS**
2. ✅ Verificar Alembic antes de qualquer deploy
3. ✅ Hotfix deve seguir fluxo completo
4. ✅ Dashboard protegido contra mudanças de desenvolvimento

### Checkpoints Futuros

- [ ] Adicionar `alembic heads` check no GitHub Actions
- [ ] Criar script de validação de migrations
- [ ] Documentar processo de merge de branches Alembic
- [ ] Treinar equipe sobre políticas de produção

---

## Evidências

### Log do Erro

```
Site's appCommandLine: startup.sh
Launching oryx with: create-script -appPath /home/site/wwwroot -output /opt/startup/startup.sh
Writing output script to '/opt/startup/startup.sh'
[startup] PostgreSQL mode — running alembic upgrade head...
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
UserWarning: Revision 0007 is present more than once
ERROR [alembic.util.messaging] Multiple head revisions are present for given argument 'head'
```

### Alembic Status

```
alembic current: 0042
alembic heads: 0044
alembic branches: 0007 (branchpoint)
     -> 0008a_notifications_alerts
     -> 0008
```

---

## Assinaturas

| Nome | Data | Papel |
|------|------|-------|
| Jefferson | 2026-06-11 | DevOps/Backend |
| Filipi | 2026-06-11 | Tech Lead |

---

## Referências

- `CLAUDE.md` - Regras de engenharia
- `docs/architecture/engineering-policy.md` - Políticas detalhadas
- `docs/runbooks/deployment-checklist.md` - Checklist de deploy
- Commit hotfix: `dbe5ac1`
- Run GitHub Actions: `27350198543`