# FinOps Alignment Roadmap - CauSium

**Versão:** 1.0.0  
**Data:** 2026-06-11  
**Status:** Documento de planejamento - NENHUMA implementação  
**Autor:** Jefferson (DevOps) + Claude (AI Assistant)  

---

## ⚠️ REGRAS FUNDAMENTAIS

Este documento é apenas **PLANEJAMENTO**. Nenhuma implementação deve ser feita sem seguir o fluxo:

```
DIAGNÓSTICO → PLANO → DIFF → TESTE LOCAL → STAGING → VALIDAÇÃO → APROVAÇÃO → PRODUÇÃO
```

### Regras Obrigatórias

| Regra | Descrição |
|-------|-----------|
| **Produção é sagrada** | Dashboard do cliente NUNCA pode ser derrubado |
| **Zero alterações** | Este documento é apenas leitura e planejamento |
| **Staging primeiro** | Toda mudança deve ser validada em staging antes de produção |
| **Testes locais** | Nenhum deploy sem testes locais passando |
| **Aprovação explícita** | Aprovação do usuário é obrigatória antes de cada fase |

### O que NÃO fazer

- ❌ Alterar código
- ❌ Alterar banco
- ❌ Alterar infraestrutura
- ❌ Executar migrations
- ❌ Fazer deploy
- ❌ Tocar em produção

### O que FAZER

- ✅ Documentar
- ✅ Planejar
- ✅ Validar localmente
- ✅ Testar em staging
- ✅ Obter aprovação

---

## 1. ESTADO ATUAL DO SISTEMA

### 1.1 Sistema em Produção

| Componente | Status | Detalhes |
|-----------|--------|----------|
| Backend API | ✅ Funcional | Health check OK |
| Dashboard | ✅ Funcional | KPIs, trends, alerts |
| Database PostgreSQL | ⚠️ Parcial | Migrations bloqueadas (multiple heads) |
| ClickHouse | ✅ Funcional | Dados analíticos OK |
| Workers | ✅ Funcional | Ingestion, scoring, notifications |
| Auth | ✅ Funcional | Passkey, TOTP, MFA |

### 1.2 Alembic Status

```bash
$ alembic current
0042

$ alembic heads
0044 (head)
??? (head) # Múltiplas heads - PROBLEMA

$ alembic branches
0007 (branchpoint)
     -> 0008a_notifications_alerts
     -> 0008
```

### 1.3 Funcionalidades em Produção

| Funcionalidade | Status |
|---------------|--------|
| Dashboard | ✅ |
| Spend Analysis | ✅ |
| Spend by SKU | ✅ |
| Executive Summary | ✅ |
| Opportunities (Savings) | ✅ |
| Optimization Plan | ✅ |
| Change Events Log | ✅ |
| Reconciliation | ✅ |
| Notifications (SMTP + Slack) | ✅ |
| Auth (Passkey, TOTP, MFA) | ✅ |

### 1.4 Funcionalidades Parciais

| Funcionalidade | Status | Detalhes |
|---------------|--------|----------|
| Anomaly Detection | ⚠️ | Worker OK, UI em amadurecimento |
| AKS Rightsizing | ⚠️ | Engine OK, dados reais pendentes |
| Budget Alerts | ⚠️ | Modelo OK, alertas não disparam |
| Execution Plan | ⚠️ | Modelo OK, UI parcial |
| Teams/Cost Allocation | ❌ | Não implementado |
| Tags/Untagged | ❌ | Não implementado |
| Advisor Recommendations | ❌ | Não implementado |
| Reserved Instances | ❌ | Não implementado |
| Savings Plans | ❌ | Não implementado |

---

## 2. ROADMAP DE IMPLEMENTAÇÃO

### Visão Geral das Fases

```
FASE 0 ────────────────────────────────────────────────────────► 2 semanas
PROTEÇÃO E ESTABILIDADE
- Backup PostgreSQL
- Backup ClickHouse
- Plano de staging
- Documentação

FASE 1 ────────────────────────────────────────────────────────► 6 semanas
BASE TÉCNICA (ALEMBIC)
- Resolver múltiplas heads
- Validar migrations
- Reabilitar pipeline de migrations

FASE 2 ────────────────────────────────────────────────────────► 12 semanas
FINOPS ESSENCIAL
- Teams/Cost Allocation
- Tags/Untagged Resources
- Budget Alerts
- Anomaly Alerts

FASE 3 ────────────────────────────────────────────────────────► 20 semanas
OTIMIZAÇÃO FINOPS
- Advisor Recommendations
- Reserved Instances
- Savings Plans
- AKS Real Data

FASE 4 ────────────────────────────────────────────────────────► 21+ semanas
GOVERNANÇA AVANÇADA
- Governance Policies
- What-if Simulation
- AI Copilot
- Autonomous FinOps
```

---

## FASE 0: PROTEÇÃO E ESTABILIDADE

**Período:** Semanas 1-2  
**Prioridade:** 🔴 CRÍTICA  
**Objetivo:** Garantir que podemos reverter qualquer mudança  

### 0.1 Backup PostgreSQL

| Item | Descrição |
|------|----------|
| **Objetivo** | Garantir possibilidade de rollback do banco de dados |
| **Impacto** | 🔴 Crítico - Permite reverter erros |
| **Risco** | 🟢 Baixo - Apenas leitura/cópia |
| **Dependências** | Nenhuma |
| **Staging** | Não aplicável |
| **Critério de Aceite** | Backup restaurável em ambiente de teste |

#### Passos

```bash
# 1. Identificar servidor PostgreSQL
az postgres server list --resource-group rg-causium-staging-01

# 2. Criar backup
az postgres db export \
 --resource-group rg-causium-staging-01 \
  --server causium-pg-2026 \
  --name causium \
  --storage-uri https://causiumbackups.blob.core.windows.net/backups/backup-$(date +%Y%m%d).sql

# 3. Verificar backup
az postgres db show \
  --resource-group rg-causium-staging-01 \
  --server causium-pg-2026 \
  --name causium
```

#### Rollback

```bash
# Restaurar backup
az postgres db import \
  --resource-group rg-causium-staging-01 \
  --server causium-pg-2026 \
  --name causium \
  --storage-uri https://causiumbackups.blob.core.windows.net/backups/backup-YYYYMMDD.sql
```

#### Checklist de Validação

- [ ] Backup criado com sucesso
- [ ] Backup verificável (checksum)
- [ ] Restore testado em ambiente isolado
- [ ] Tempo de restore documentado
- [ ] Responsável pelo restore identificado

---

### 0.2 Backup ClickHouse

| Item | Descrição |
|------|----------|
| **Objetivo** | Garantir possibilidade de rollback dos dados analíticos |
| **Impacto** | 🔴 Crítico - Dados de custos |
| **Risco** | 🟢 Baixo - Apenas leitura/cópia |
| **Dependências** | Nenhuma |
| **Staging** | Não aplicável |
| **Critério de Aceite** | Backup restaurável em ambiente de teste |

#### Passos

```bash
# 1. Identificar servidor ClickHouse
# ClickHouse Cloud: k2xj32v350.westus3.azure.clickhouse.cloud

# 2. Criar backup via ClickHouse native backup
clickhouse-client --host k2xj32v350.westus3.azure.clickhouse.cloud \
  --port 8443 --secure \
  --query "BACKUP TABLE cost_facts TO S3('s3://causium-backups/clickhouse/backup-$(date +%Y%m%d)/')"

# 3. Verificar backup
clickhouse-client --host k2xj32v350.westus3.azure.clickhouse.cloud \
  --port 8443 --secure \
  --query "SELECT * FROM system.backups"
```

#### Rollback

```bash
# Restaurar backup
clickhouse-client --host k2xj32v350.westus3.azure.clickhouse.cloud \
  --port 8443 --secure \
  --query "RESTORE TABLE cost_facts FROM S3('s3://causium-backups/clickhouse/backup-YYYYMMDD/')"
```

#### Checklist de Validação

- [ ] Backup criado com sucesso
- [ ] Tables incluídas: cost_facts, event_facts, carbon_records
- [ ] Backup verificável
- [ ] Tempo de restore documentado
- [ ] Responsável pelo restore identificado

---

### 0.3 Plano de Staging

| Item | Descrição |
|------|----------|
| **Objetivo** | Criar ambiente de teste isolado |
| **Impacto** | 🔴 Crítico - Validação pré-produção |
| **Risco** | 🟢 Baixo - Novo ambiente |
| **Dependências** | 0.1, 0.2 |
| **Staging** | Sim (é o ambiente) |
| **Critério de Aceite** | Deploy funcionando em staging |

#### Passos

```bash
# 1. Verificar slot de staging existente
az webapp slot list \
  --resource-group rg-causium-staging-01 \
  --name causium-api-2026

# 2. Configurar app settings de staging
az webapp config appsettings set \
  --resource-group rg-causium-staging-01 \
  --name causium-api-2026-staging \
  --settings \
    APP_ENV=staging \
    DATABASE_URL="postgresql://..." \
    CLICKHOUSE_HOST="..."

# 3. Validar health check
curl -s https://causium-api-2026-staging.azurewebsites.net/health
```

#### Checklist de Validação

- [ ] Staging deploy OK
- [ ] Health check retornando OK
- [ ] Database conectando
- [ ] ClickHouse conectando
- [ ] APIs respondendo

---

### 0.4 Documentar Configurações

| Item | Descrição |
|------|----------|
| **Objetivo** | Evitar perda de configuração |
| **Impacto** | 🟡 Médio - Recuperação mais rápida |
| **Risco** | 🟢 Baixo - Apenas documentação |
| **Dependências** | Nenhuma |
| **Staging** | Não aplicável |
| **Critério de Aceite** | Documento completo e verificável |

#### Passos

```bash
# 1. Exportar App Settings
az webapp config appsettings list \
  --resource-group rg-causium-staging-01 \
  --name causium-api-2026 \
  --output table > app_settings_prod.md

# 2. Documentar variáveis críticas
# - DATABASE_URL
# - CLICKHOUSE_HOST
# - CLICKHOUSE_PORT
# - REDIS_URL
# - JWT_SECRET
# - API Keys

# 3. Documentar recursos Azure
# - Resource group
# - App Service plan
# - PostgreSQL server
# - ClickHouse
# - Storage accounts
# - Redis
```

#### Checklist de Validação

- [ ] App Settings exportados
- [ ] Variáveis críticas documentadas
- [ ] Recursos Azure listados
- [ ] Credenciais seguras (Key Vault)
- [ ] Documento versionado

---

### 0.5 NÃO MEXER EM PRODUÇÃO

| Item | Descrição |
|------|----------|
| **Objetivo** | Proteger ambiente de produção |
| **Impacto** | 🔴 Crítico - Cliente não afetado |
| **Risco** | 🟢 Baixo - Zero alterações |
| **Dependências** | Nenhuma |
| **Staging** | N/A |
| **Critério de Aceite** | Zero alterações em produção |

#### Regras

1. ❌ Não fazer deploy manual para produção
2. ❌ Não executar comandos no App Service
3. ❌ Não alterar App Settings de produção
4. ❌ Não executar migrations em produção
5. ❌ Não alterar banco de produção
6. ❌ Não alterar infraestrutura

#### Checklist de Validação

- [ ] GitHub Actions CI/CD configurado
- [ ] Branch protection em main
- [ ] Deploy via CI/CD apenas
- [ ] Revisão de código obrigatória

---

### 0.6 Baseline de Produção

| Item | Descrição |
|------|----------|
| **Objetivo** | Registrar estado atual do sistema antes de qualquer implementação |
| **Impacto** | 🟡 Médio - Comprovação de ganho |
| **Risco** | 🟢 Baixo - Apenas leitura |
| **Dependências** | Nenhuma |
| **Staging** | Não aplicável |
| **Critério de Aceite** | Documento com evidências visuais e métricas |

#### Propósito

Este baseline permite **comparação ANTES vs DEPOIS** para comprovar ganho real ao cliente.

```
ANTES (este baseline)
    ↓
IMPLEMENTAÇÃO
    ↓
DEPOIS (comparação)
```

#### O que documentar

##### Screenshots das Telas Atuais

```
1. Dashboard Principal
   - https://app.causiumtech.com/dashboard
   - Capturar: KPIs, gráficos, tendências

2. Executive Summary
   - https://app.causiumtech.com/executive
   - Capturar: Savings, iniciativas

3. Opportunities
   - https://app.causiumtech.com/opportunities
   - Capturar: Lista de oportunidades

4. Economics (Spend Analysis)
   - https://app.causiumtech.com/economics
   - Capturar: Gráficos de custo

5. Governance
   - https://app.causiumtech.com/gov
   - Capturar: Compliance de tags
```

##### KPIs Atuais

```bash
# Health check atual
curl -s https://causium-api-2026.azurewebsites.net/health
# Esperado: {"status":"ok","version":"0.1.0"}

# Dashboard metrics
curl -s https://causium-api-2026.azurewebsites.net/api/v1/ledger/dashboard

# Contagem de oportunidades
# Via API ou UI

# Custos atuais
# Via dashboard
```

##### Métricas de Performance

```bash
# Tempo de resposta APIs
curl -w "\nTime: %{time_total}s\n" -s https://causium-api-2026.azurewebsites.net/health

# Quantidade de recursos monitorados
# Via API

# Quantidade de subscriptions
# Via API

# Quantidade de workspaces
# Via API
```

##### Quantidades Atuais

| Métrica | Valor |
|---------|-------|
| Oportunidades abertas | _ |
| Oportunidades resolvidas | _ |
| Recursos monitorados | _ |
| Subscriptions | _ |
| Workspaces | _ |
| Alertas ativos | _ |
| Membros | _ |

##### Custos Atuais

| Métrica | Valor |
|---------|-------|
| Custo mês atual | _ |
| Custo mês anterior | _ |
| Variação % | _ |
| Savings estimado | _ |
| Savings realizado | _ |

##### Health Check

```bash
# Verificar health check detalhado
curl -s https://causium-api-2026.azurewebsites.net/api/v1/health

# Verificar conectividade banco
az postgres server show \
  --resource-group rg-causium-staging-01 \
  --name causium-pg-2026

# Verificar conectividade ClickHouse
clickhouse-client --host k2xj32v350.westus3.azure.clickhouse.cloud \
  --port 8443 --secure \
  --query "SELECT count() FROM cost_facts"
```

#### Template de Baseline

```markdown
# Baseline de Produção - [DATA]

## Screenshots
[Adicionar screenshots aqui]

## KPIs
| Métrica | Valor |
|---------|-------|
| ... | ... |

## Métricas de Performance
| Métrica | Valor |
|---------|-------|
| Health check | OK/NOK |
| Tempo de resposta | Xs |
| Recursos monitorados | N |

## Quantidades
| Tipo | Quantidade |
|------|------------|
| Oportunidades | N |
| Recursos | N |
| Subscriptions | N |

## Custos
| Métrica | Valor |
|---------|-------|
| Mês atual | $X |
| Mês anterior | $Y |
| Variação | Z% |

## Validação
- [ ] Screenshots capturados
- [ ] KPIs documentados
- [ ] Métricas de performance registradas
- [ ] Quantidades atualizadas
- [ ] Custos registrados
- [ ] Documento salvo em docs/baseline/
```

#### Local de Armazenamento

```
docs/baseline/
├── 2026-06-11-baseline.md
├── 2026-06-11-dashboard.png
├── 2026-06-11-executive.png
├── 2026-06-11-opportunities.png
├── 2026-06-11-economics.png
└── 2026-06-11-gov.png
```

#### Checklist de Validação

- [ ] Screenshots de todas as telas capturados
- [ ] KPIs documentados
- [ ] Métricas de performance registradas
- [ ] Quantidades atualizadas
- [ ] Custos registrados
- [ ] Documento salvo em docs/baseline/
- [ ] Comparação futura possível

---

### Checklist Final - Fase 0

| Item | Status |
|------|--------|
| Backup PostgreSQL criado | ⬜ |
| Backup PostgreSQL verificável | ⬜ |
| Backup ClickHouse criado | ⬜ |
| Backup ClickHouse verificável | ⬜ |
| Staging configurado | ⬜ |
| Staging health check OK | ⬜ |
| Configurações documentadas | ⬜ |
| Regras de produção comunicadas | ⬜ |
| Baseline de produção documentado | ⬜ |

---

## FASE 1: BASE TÉCNICA (ALEMBIC)

**Período:** Semanas 3-6  
**Prioridade:** 🔴 CRÍTICA  
**Objetivo:** Resolver múltiplas heads do Alembic para reabilitar migrations  

### ⚠️ IMPORTANTE

**NÃO EXECUTAR NENHUMA MIGRATION EM PRODUÇÃO**

Esta fase deve ser executada **inteiramente em local/staging**.

### 1.1 Analisar Alembic Heads

| Item | Descrição |
|------|----------|
| **Objetivo** | Entender estrutura atual do graph de migrations |
| **Impacto** | 🟡 Médio - Compreensão do problema |
| **Risco** | 🟢 Baixo - Apenas leitura |
| **Dependências** | Fase 0 completa |
| **Staging** | Local apenas |
| **Critério de Aceite** | Estrutura do graph compreendida |

#### Passos

```bash
cd backend

# 1. Verificar estado atual
alembic current
alembic heads
alembic branches
alembic history --verbose

# 2. Listar todas as migrations
ls -la alembic/versions/

# 3. Analisar cada migration
# Focar em:
# - 0007 (branchpoint)
# - 0008 (uma branch)
# - 0008a_notifications_alerts (outra branch)
# - 0024_provider_recommendation_sync (raiz separada)
# - 0025_merge_workspace_lifecycle (merge point)
```

#### Output Esperado

```
ALEMBIC CURRENT: 0042
ALEMBIC HEADS: 0044 + ???
ALEMBIC BRANCHES:
 0007 (branchpoint)
    -> 0008a_notifications_alerts
    -> 0008
```

#### Checklist de Validação

- [ ] `alembic current` executado
- [ ] `alembic heads` executado
- [ ] `alembic branches` executado
- [ ] Estrutura do graph documentada
- [ ] Migrations identificadas

---

### 1.2 Identificar Merge Point

| Item | Descrição |
|------|----------|
| **Objetivo** | Encontrar causa raiz das múltiplas heads |
| **Impacto** | 🟡 Médio - Identificar solução |
| **Risco** | 🟢 Baixo - Apenas análise |
| **Dependências** | 1.1 |
| **Staging** | Local apenas |
| **Critério de Aceite** | Merge point identificado e compreendido |

#### Passos

```bash
# 1. Verificar merge point atual
cat alembic/versions/0025_merge_workspace_lifecycle.py

# 2. Verificar down_revisions
# Esperado: "0008", "0023_aws_cur_ingestion_checkpoints", "provider_recommendation_sync"

# 3. Verificar se0024 tem down_revision correto
cat alembic/versions/0024_provider_recommendation_sync.py
# Deve ter: down_revision = None (ou referência correta)

# 4. Verificar chain após merge
cat alembic/versions/0026_lgpd_consent.py
# Deve ter: down_revision = "0025_merge_workspace_lifecycle"
```

#### Hipóteses do Problema

1. **Hipótese 1:** `0024_provider_recommendation_sync` tem `down_revision = None` mas deveria referenciar algo
2. **Hipótese 2:** Merge point 0025 não está resolvendo corretamente
3. **Hipótese 3:** Há uma branch órfã que não foi mergeada

#### Checklist de Validação

- [ ] Merge point 0025 analisado
- [ ] Down_revisions verificados
- [ ] Causa raiz identificada
- [ ] Solução proposta documentada

---

### 1.3 Criar Merge Migration Local

| Item | Descrição |
|------|----------|
| **Objetivo** | Resolver múltiplas heads criando merge migration |
| **Impacto** | 🔴 Crítico - Permite migrations |
| **Risco** | 🔴 Alto - Altera migrations |
| **Dependências** | 1.1, 1.2 |
| **Staging** | Local apenas |
| **Critério de Aceite** | `alembic heads` retorna apenas 1 head |

#### Passos

```bash
cd backend

# 1. Criar branch de trabalho
git checkout -b fix/alembic-multiple-heads

# 2. Criar merge migration
alembic merge -m "merge all heads to single chain"

# 3. Verificar resultado
alembic heads

# 4. Verificar estrutura
alembic branches
```

#### Output Esperado

```
ALEMBIC HEADS: 0045 (single head)
ALEMBIC BRANCHES: (vazio ou uma única chain)
```

#### Rollback

```bash
# Descartar branch
git checkout main
git branch -D fix/alembic-multiple-heads
```

#### Checklist de Validação

- [ ] Branch criada
- [ ] Merge migration gerada
- [ ] `alembic heads` retorna 1
- [ ] Estrutura do graph correta

---

### 1.4 Validar Upgrade/Downgrade

| Item | Descrição |
|------|----------|
| **Objetivo** | Garantir que migrations podem ser revertidas |
| **Impacto** | 🔴 Crítico - Rollback funcional |
| **Risco** | 🟡 Médio - Testa migrations |
| **Dependências** | 1.3 |
| **Staging** | Local apenas |
| **Critério de Aceite** | Upgrade e downgrade funcionam |

#### Passos

```bash
cd backend

# 1. Testar upgrade
alembic upgrade head
alembic current # Deve mostrar nova head

# 2. Testar downgrade
alembic downgrade -1
alembic current  # Deve mostrar versão anterior

# 3. Testar upgrade novamente
alembic upgrade head
alembic current  # Deve mostrar head novamente
```

#### Rollback

```bash
# Reverter para estado anterior
alembic downgrade -1
# Repetir até chegar ao estado desejado
```

#### Checklist de Validação

- [ ] `alembic upgrade head` funciona
- [ ] `alembic downgrade -1` funciona
- [ ] `alembic upgrade head` funciona novamente
- [ ] Banco verificável após cada operação

---

### 1.5 Testes Locais

| Item | Descrição |
|------|----------|
| **Objetivo** | Validar que sistema funciona após merge |
| **Impacto** | 🔴 Crítico - Sistema funcional |
| **Risco** | 🟡 Médio - Executa testes |
| **Dependências** | 1.4 |
| **Staging** | Local apenas |
| **Critério de Aceite** | pytest passando |

#### Passos

```bash
cd backend

# 1. Instalar dependências
poetry install

# 2. Executar testes unitários
pytest -v

# 3. Executar testes de integração
pytest tests/integration/ -v

# 4. Verificar type check
mypy app/

# 5. Verificar build
python -c "from app.main import app"
```

#### Rollback

```bash
# Reverter alterações
git checkout -- .
git checkout main
```

#### Checklist de Validação

- [ ] pytest passando
- [ ] mypy sem erros
- [ ] app importando corretamente
- [ ] APIs respondendo

---

### 1.6 Deploy para Staging

| Item | Descrição |
|------|----------|
| **Objetivo** | Validar em ambiente controlado |
| **Impacto** | 🔴 Crítico - Validação pré-produção |
| **Risco** | 🟡 Médio - Deploy em staging |
| **Dependências** | 1.5 |
| **Staging** | ✅ SIM |
| **Critério de Aceite** | Health check OK em staging |

#### Passos

```bash
# 1. Push branch
git push origin fix/alembic-multiple-heads

# 2. Criar PR
gh pr create --title "fix(alembic): resolve multiple heads" --body "..."

# 3. Merge PR (após aprovação)
gh pr merge --admin --merge

# 4. Aguardar deploy via CI/CD
gh run list --workflow="Build and deploy" --limit 3

# 5. Verificar staging
curl -s https://causium-api-2026-staging.azurewebsites.net/health
```

#### Rollback

```bash
# Reverter merge
gh pr revert <pr-number>
# Ou
git revert <commit-sha>
git push origin main
```

#### Checklist de Validação

- [ ] PR criado
- [ ] PR revisado
- [ ] PR mergeado
- [ ] CI/CD passando
- [ ] Staging health check OK

---

### 1.7 Validação em Staging

| Item | Descrição |
|------|----------|
| **Objetivo** | Confirmar funcionamento em staging |
| **Impacto** | 🔴 Crítico - Confirmação final |
| **Risco** | 🟡 Médio - Validação |
| **Dependências** | 1.6 |
| **Staging** | ✅ SIM |
| **Critério de Aceite** | Todas as APIs respondendo |

#### Passos

```bash
# 1. Health check
curl -s https://causium-api-2026-staging.azurewebsites.net/health

# 2. APIs principais
curl -s https://causium-api-2026-staging.azurewebsites.net/api/v1/health
curl -s https://causium-api-2026-staging.azurewebsites.net/api/v1/ledger/dashboard

# 3. Login
# Testar login via UI

# 4. Dashboard
# Verificar se dashboard carrega

# 5. Logs
az webapp log tail --resource-group rg-causium-staging-01 --name causium-api-2026-staging
```

#### Checklist de Validação

- [ ] Health check OK
- [ ] APIs respondendo
- [ ] Login funcionando
- [ ] Dashboard carregando
- [ ] Sem erros nos logs

---

### 1.8 Aprovação para Produção

| Item | Descrição |
|------|----------|
| **Objetivo** | Obter permissão explícita para produção |
| **Impacto** | 🔴 Crítico - Liberação |
| **Risco** | 🟢 Baixo - Apenas aprovação |
| **Dependências** | 1.7 |
| **Staging** | N/A |
| **Critério de Aceite** | Usuário aprovou explicitamente |

#### Template de Aprovação

```markdown
## Aprovação para Produção - Alembic Multiple Heads

### Resumo
- Branch: fix/alembic-multiple-heads
- Merge commit: xxxxxxx
- Staging: ✅ Validado

### Validações em Staging
- [x] Health check OK
- [x] Login funcionando
- [x] Dashboard carregando
- [x] APIs respondendo
- [x] Sem erros nos logs

### Risco
- 🟡 Médio - Alteração de migrations

### Rollback
- git revert xxxxxxx

### Aprovação

[ ] Eu aprovo o deploy para produção
[ ] Responsável: _______________
[ ] Data: _______________
```

---

### 1.9 Deploy Produção

| Item | Descrição |
|------|----------|
| **Objetivo** | Aplicar correção em produção |
| **Impacto** | 🔴 Crítico - Corrigir produção |
| **Risco** | 🟡 Médio - Deploy em produção |
| **Dependências** | 1.8 |
| **Staging** | NÃO |
| **Critério de Aceite** | Health check OK em produção |

#### Passos

```bash
# 1. Deploy via CI/CD (automático após merge para main)
gh run list --workflow="Build and deploy" --limit 3

# 2. Aguardar conclusão
# Verificar jobs: build + deploy

# 3. Validar produção
curl -s https://causium-api-2026.azurewebsites.net/health
```

#### Rollback

```bash
# Reverter
git revert <commit-sha>
git push origin main
# Aguardar CI/CD
```

#### Checklist de Validação

- [ ] CI/CD passando
- [ ] Health check OK
- [ ] Login funcionando
- [ ] Dashboard carregando
- [ ] Sem erros nos logs

---

### Checklist Final - Fase 1

| Item | Status |
|------|--------|
| Alembic heads analisado | ⬜ |
| Merge point identificado | ⬜ |
| Merge migration criada | ⬜ |
| Upgrade/downgrade validado | ⬜ |
| Testes locais passando | ⬜ |
| Deploy para staging | ⬜ |
| Validação staging OK | ⬜ |
| Aprovação obtida | ⬜ |
| Deploy produção OK | ⬜ |

---

## FASE 2: FINOPS ESSENCIAL

**Período:** Semanas 7-12  
**Prioridade:** 🔴 ALTA  
**Objetivo:** Funcionalidades FinOps essenciais para o cliente  

### Fluxo de Dependências

```
Tags Framework
    ↓
Untagged Resources
    ↓
Cost Allocation
    ↓
Teams
    ↓
Budget Alerts
    ↓
Anomaly Alerts
```

> **Justificativa:** Tags são a fundação da governança FinOps. Cada item subsequente depende dos anteriores para funcionar corretamente.

---

### 2.1 Tags Framework

| Item | Descrição |
|------|----------|
| **Objetivo** | Criar framework de tags para governança de custos |
| **Impacto** | 🔴 Alto - Fundação de toda a governança |
| **Risco** | 🟡 Médio - Novo modelo |
| **Dependências** | Fase 1 completa |
| **Staging** | ✅ SIM |
| **Critério de Aceite** | Tags appearing em recursos e sendo rastreadas |

#### Por que primeiro?

Tags são a **fundação** da governança FinOps:
- Untagged Resources depende de Tags
- Cost Allocation depende de Tags
- Teams depende de Tags para alocação

#### Arquivos Prováveis

```
backend/app/domains/
├── tags/
│   ├── __init__.py
│   ├── models.py          # Tag model
│   ├── router.py         # API routes
│   ├── schemas.py         # Pydantic schemas
│   └── service.py        # Business logic

frontend/src/pages/
├── Tags/
│   └── TagsPage.tsx     # Tags UI

backend/alembic/versions/
├── XXXX_tags_framework.py # Migration
```

#### Passos

1. Criar modelo Tag (nome, valor, categoria, padrão)
2. Criar migration
3. Criar API de CRUD de tags
4. Criar UI de gerenciamento de tags
5. Integrar com ingestion (capturar tags dos recursos)
6. Criar relatório de compliance de tags
7. Testar em staging
8. Validar
9. Deploy produção

#### Rollback

```bash
git revert <commit-sha>
# Rollback migration se necessário
alembic downgrade -1
```

#### Checklist de Validação

- [ ] Modelo Tag criado
- [ ] Migration aplicada
- [ ] API CRUD funcionando
- [ ] UI de gerenciamento funcionando
- [ ] Tags sendo capturadas na ingestion
- [ ] Relatório de compliance disponível
- [ ] Testes passando
- [ ] Staging validado

---

### 2.2 Untagged Resources

| Item | Descrição |
|------|----------|
| **Objetivo** | Identificar e rastrear recursos sem tag |
| **Impacto** | 🔴 Alto - Governança básica |
| **Risco** | 🟡 Médio - Query |
| **Dependências** | 2.1 (Tags Framework) |
| **Staging** | ✅ SIM |
| **Critério de Aceite** | Lista de recursos sem tag visível |

#### Por que segundo?

Sem o framework de tags (2.1), não há como identificar quais recursos estão "tagged" vs "untagged".

#### Passos

1. Criar endpoint para listar recursos sem tags
2. Criar métricas de compliance (%)
3. Criar UI em GovPage mostrando untagged
4. Adicionar alertas para novos recursos untagged
5. Testar em staging
6. Validar
7. Deploy produção

#### Rollback

```bash
git revert <commit-sha>
```

#### Checklist de Validação

- [ ] Endpoint untagged funcionando
- [ ] Métricas de compliance calculando
- [ ] UI mostrando recursos untagged
- [ ] Alertas configuráveis
- [ ] Testes passando
- [ ] Staging validado

---

### 2.3 Cost Allocation

| Item | Descrição |
|------|----------|
| **Objetivo** | Alocar custos por tags, recursos e dimensões |
| **Impacto** | 🔴 Alto - Visibilidade de custos |
| **Risco** | 🟡 Médio - Query complexa |
| **Dependências** | 2.1 (Tags), 2.2 (Untagged) |
| **Staging** | ✅ SIM |
| **Critério de Aceite** | Dashboard mostrando custos alocados |

#### Por que terceiro?

Cost Allocation depende de Tags para fazer a alocação correta e de Untagged para saber quanto está "indeterminado".

#### Passos

1. Criar modelo de cost allocation rules
2. Criar API de alocação
3. Integrar com dashboard (segmentar por tags)
4. Criar UI de configuração de regras
5. Testar em staging
6. Validar
7. Deploy produção

#### Rollback

```bash
git revert <commit-sha>
```

#### Checklist de Validação

- [ ] Modelo de rules criado
- [ ] API de alocação funcionando
- [ ] Dashboard segmentando por tags
- [ ] UI de configuração disponível
- [ ] Testes passando
- [ ] Staging validado

---

### 2.4 Teams

| Item | Descrição |
|------|----------|
| **Objetivo** | Visibilidade de custos por equipe organizacional |
| **Impacto** | 🔴 Alto - Requisito do cliente |
| **Risco** | 🟡 Médio - Novo modelo |
| **Dependências** | 2.3 (Cost Allocation) |
| **Staging** | ✅ SIM |
| **Critério de Aceite** | UI mostrando custos por team |

#### Por que quarto?

Teams depende de Cost Allocation para associar custos a equipes através das tags/regras configuradas.

#### Arquivos Prováveis

```
backend/app/domains/
├── teams/
│   ├── __init__.py
│   ├── models.py          # Team model
│   ├── router.py         # API routes
│   ├── schemas.py         # Pydantic schemas
│   └── service.py        # Business logic

frontend/src/pages/
├── Teams/
│   └── TeamsPage.tsx     # Teams UI

backend/alembic/versions/
├── XXXX_teams.py # Migration
```

#### Passos

1. Criar modelo Team
2. Criar migration
3. Criar API de CRUD de teams
4. Integrar com Cost Allocation (team → tag mapping)
5. Criar UI de gerenciamento de teams
6. Mostrar custos por team no dashboard
7. Testar em staging
8. Validar
9. Deploy produção

#### Rollback

```bash
git revert <commit-sha>
# Rollback migration se necessário
alembic downgrade -1
```

#### Checklist de Validação

- [ ] Modelo Team criado
- [ ] Migration aplicada
- [ ] API CRUD funcionando
- [ ] Integração com Cost Allocation OK
- [ ] UI mostrando teams
- [ ] Dashboard segmentando por team
- [ ] Testes passando
- [ ] Staging validado

---

### 2.5 Budget Alerts

| Item | Descrição |
|------|----------|
| **Objetivo** | Notificar quando orçamento é atingido |
| **Impacto** | 🔴 Alto - Cliente espera alertas |
| **Risco** | 🟡 Médio - Integration |
| **Dependências** | 2.4 (Teams) |
| **Staging** | ✅ SIM |
| **Critério de Aceite** | Alertas disparando |

#### Por que quinto?

Budget Alerts gera mais valor quando a alocação de custos por Team já está funcionando corretamente, permitindo alertas por equipe.

#### Passos

1. Verificar modelo budget existente
2. Criar worker de budget alerts
3. Integrar com notification_worker
4. Criar UI de configuração (por team, por tag, global)
5. Adicionar métrica de spend vs budget
6. Testar em staging
7. Validar
8. Deploy produção

#### Rollback

```bash
git revert <commit-sha>
```

#### Checklist de Validação

- [ ] Worker budget alerts funcionando
- [ ] Integração com notification OK
- [ ] UI de configuração disponível
- [ ] Alertas disparando corretamente
- [ ] Métricas de budget visíveis
- [ ] Testes passando
- [ ] Staging validado

---

### 2.6 Anomaly Alerts

| Item | Descrição |
|------|----------|
| **Objetivo** | Notificar anomalias de custo |
| **Impacto** | 🔴 Alto - Cliente espera alertas |
| **Risco** | 🟡 Médio - Worker existente |
| **Dependências** | 2.5 (Budget Alerts) |
| **Staging** | ✅ SIM |
| **Critério de Aceite** | Alertas disparando |

#### Por que sexto?

Anomaly Alerts é o último item porque depende de toda a estrutura de alocação estar funcionando para contextualizar as anomalias.

#### Passos

1. Verificar anomaly_detection_worker existente
2. Criar UI de configuração de alertas
3. Integrar com notification_worker
4. Adicionar contexto de Team/Tag às anomalias
5. Testar em staging
6. Validar
7. Deploy produção

#### Rollback

```bash
git revert <commit-sha>
```

#### Checklist de Validação

- [ ] Worker anomaly detection OK
- [ ] UI de configuração disponível
- [ ] Integração com notification OK
- [ ] Anomalias com contexto (Team/Tag)
- [ ] Testes passando
- [ ] Staging validado

---

### Checklist Final - Fase 2

| Item | Status | Dependência |
|------|--------|-------------|
| Tags Framework | ⬜ | - |
| Untagged Resources | ⬜ | Tags |
| Cost Allocation | ⬜ | Tags, Untagged |
| Teams | ⬜ | Cost Allocation |
| Budget Alerts | ⬜ | Teams |
| Anomaly Alerts | ⬜ | Budget Alerts |

---

## FASE 3: OTIMIZAÇÃO FINOPS

**Período:** Semanas 13-20  
**Prioridade:** 🟡 MÉDIA  
**Objetivo:** Funcionalidades avançadas de otimização  

### 3.1 Advisor Recommendations

| Item | Descrição |
|------|----------|
| **Objetivo** | Mostrar recomendações nativas dos provedores |
| **Impacto** | 🟡 Médio - Valor agregado |
| **Risco** | 🟡 Médio - Integração |
| **Dependências** | Fase 1 completa |
| **Staging** | ✅ SIM |
| **Critério de Aceite** | Recomendações appearing |

#### Passos

1. Integrar Azure Advisor API
2. Integrar AWS Trusted Advisor API
3. Integrar GCP Recommender API
4. Criar UI unificada
5. Testar em staging
6. Validar
7. Deploy produção

#### Rollback

```bash
git revert <commit-sha>
```

---

### 3.2 Reserved Instances

| Item | Descrição |
|------|----------|
| **Objetivo** | Análise de Reserved Instances |
| **Impacto** | 🟡 Médio - Otimização de custo |
| **Risco** | 🟡 Médio - Modelo |
| **Dependências** | 3.1 |
| **Staging** | ✅ SIM |
| **Critério de Aceite** | Dados populados |

---

### 3.3 Savings Plans

| Item | Descrição |
|------|----------|
| **Objetivo** | Análise de Savings Plans |
| **Impacto** | 🟡 Médio - Otimização de custo |
| **Risco** | 🟡 Médio - Modelo |
| **Dependências** | 3.2 |
| **Staging** | ✅ SIM |
| **Critério de Aceite** | Dados populados |

---

### 3.4 AKS Real Data

| Item | Descrição |
|------|----------|
| **Objetivo** | Recomendações AKS com dados reais |
| **Impacto** | 🟡 Médio - Funcionalidade completa |
| **Risco** | 🟡 Médio - Integração |
| **Dependências** | 3.1 |
| **Staging** | ✅ SIM |
| **Critério de Aceite** | Recomendações com dados |

---

### Checklist Final - Fase 3

| Item | Status |
|------|--------|
| Advisor Recommendations | ⬜ |
| Reserved Instances | ⬜ |
| Savings Plans | ⬜ |
| AKS Real Data | ⬜ |

---

## FASE 4: GOVERNANÇA AVANÇADA

**Período:** Semanas 21+  
**Prioridade:** 🟢 BAIXA  
**Objetivo:** Funcionalidades avançadas de governança  

### 4.1 Governance Policies

| Item | Descrição |
|------|----------|
| **Objetivo** | Enforcement de políticas de governança |
| **Impacto** | 🟢 Baixo - Avançado |
| **Risco** | 🔴 Alto - Automação |
| **Dependências** | Fase 3 completa |
| **Staging** | ✅ SIM |
| **Critério de Aceite** | Políticas aplicadas |

---

### 4.2 What-if Simulation

| Item | Descrição |
|------|----------|
| **Objetivo** | Simulação de custos |
| **Impacto** | 🟢 Baixo - Avançado |
| **Risco** | 🔴 Alto - Complexidade |
| **Dependências** | 4.1 |
| **Staging** | ✅ SIM |
| **Critério de Aceite** | Simulação funcionando |

---

### 4.3 AI Copilot

| Item | Descrição |
|------|----------|
| **Objetivo** | Assistente IA para FinOps |
| **Impacto** | 🟢 Baixo - Experimental |
| **Risco** | 🔴 Alto - IA |
| **Dependências** | 4.2 |
| **Staging** | ✅ SIM |
| **Critério de Aceite** | Respostas relevantes |

---

### 4.4 Autonomous FinOps

| Item | Descrição |
|------|----------|
| **Objetivo** | Automação completa |
| **Impacto** | 🟢 Baixo - Experimental |
| **Risco** | 🔴 Alto - Automação |
| **Dependências** | 4.3 |
| **Staging** | ✅ SIM |
| **Critério de Aceite** | Decisões automatizadas |

---

### Checklist Final - Fase 4

| Item | Status |
|------|--------|
| Governance Policies | ⬜ |
| What-if Simulation | ⬜ |
| AI Copilot | ⬜ |
| Autonomous FinOps | ⬜ |

---

## 3. CRITÉRIOS DE PROGRESSÃO

### Fase 0 → Fase 1

| Critério | Status |
|----------|--------|
| Backup PostgreSQL validado | ⬜ |
| Backup ClickHouse validado | ⬜ |
| Staging configurado | ⬜ |
| Configurações documentadas | ⬜ |

### Fase 1 → Fase 2

| Critério | Status |
|----------|--------|
| `alembic heads` retorna 1 | ⬜ |
| `alembic upgrade head` funciona | ⬜ |
| `alembic downgrade -1` funciona | ⬜ |
| Testes locais passando | ⬜ |
| Staging validado | ⬜ |
| Aprovação obtida | ⬜ |

### Fase 2 → Fase 3

| Critério | Status |
|----------|--------|
| Teams/Cost Allocation funcionando | ⬜ |
| Tags appearing | ⬜ |
| Untagged Resources listados | ⬜ |
| Budget Alerts disparando | ⬜ |
| Anomaly Alerts disparando | ⬜ |

### Fase 3 → Fase 4

| Critério | Status |
|----------|--------|
| Advisor Recommendations appearing | ⬜ |
| Reserved Instances populados | ⬜ |
| Savings Plans populados | ⬜ |
| AKS Real Data funcionando | ⬜ |

---

## 4. RISCOS POR FASE

### Fase 0

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Nenhum | N/A | N/A | Apenas proteção |

### Fase 1

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Migration quebrar produção | 🟡 Média | 🔴 Crítico | Staging obrigatório |
| Banco ficar inconsistente | 🟡 Média | 🔴 Crítico | Backup validado |
| Downgrade falhar | 🟡 Média | 🟡 Médio | Testar local primeiro |

### Fase 2

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| UI quebrar | 🟡 Média | 🟡 Médio | Testes locais |
| Performance degradar | 🟡 Média | 🟡 Médio | Teste de carga |
| Alertas não dispararem | 🟡 Média | 🟡 Médio | Validação staging |

### Fase 3

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Integração falhar | 🟡 Média | 🟡 Médio | Staging |
| APIs externas indisponíveis | 🟡 Média | 🟡 Médio | Fallback |

### Fase 4

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Automação causar problemas | 🔴 Alta | 🔴 Crítico | Aprovação humana |
| IA dar respostas incorretas | 🔴 Alta | 🟡 Médio | Human-in-the-loop |

---

## 5. TEMPO ESTIMADO

| Fase | Semanas | Acumulado |
|------|---------|-----------|
| Fase 0 | 1-2 |1-2 |
| Fase 1 | 3-6 | 1-6 |
| Fase 2 | 7-12 | 7-12 |
| Fase 3 | 13-20 | 13-20 |
| Fase 4 | 21+ | 21+ |

**Total mínimo:** ~20 semanas (5 meses)  
**Total realista:** ~30 semanas (7 meses)  
**Total com delays:** ~40 semanas (10 meses)

---

## 6. ROLLBACK ESPERADO

### Por Fase

| Fase | Rollback |
|------|----------|
| **Fase 0** | N/A (proteção) |
| **Fase 1** | `git revert <commit>` + restore backup |
| **Fase 2** | `git revert <commit>` |
| **Fase 3** | `git revert <commit>` |
| **Fase 4** | Feature flags + `git revert` |

### Template de Rollback

```markdown
## Rollback - [Nome da Fase]

### Commit de Retorno
- SHA: xxxxxxx
- Tag: vX.Y.Z

### Passos
1. `git revert <sha>`
2. `git push origin main`
3. Aguardar CI/CD
4. Validar health check
5. Validar funcionalidades

### Validação
- [ ] Health check OK
- [ ] Dashboard carregando
- [ ] APIs respondendo
- [ ] Sem erros nos logs

### Responsável
- Nome: _______________
- Data: _______________
```

---

## 7. REFERÊNCIAS

| Documento | Descrição |
|-----------|-----------|
| `CLAUDE.md` | Regras de engenharia |
| `docs/architecture/engineering-policy.md` | Políticas detalhadas |
| `docs/runbooks/deployment-checklist.md` | Checklist de deploy |
| `docs/incidents/2026-06-11-dashboard-outage.md` | Incidente original |
| `docs/technical-tasks/alembic-multiple-heads.md` | Task técnica Alembic |

---

## 8. HISTÓRICO DE REVISÕES

| Versão | Data | Autor | Mudanças |
|--------|------|-------|----------|
| 1.0.0 | 2026-06-11 | Jefferson + Claude | Versão inicial |

---

**FIM DO DOCUMENTO**

Este documento é apenas planejamento. Nenhuma implementação deve ser feita sem seguir o fluxo:
**Diagnóstico → Plano → Diff → Teste Local → Staging → Validação → Aprovação → Produção**