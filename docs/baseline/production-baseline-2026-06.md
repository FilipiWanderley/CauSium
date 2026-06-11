# Production Baseline - CauSium

**Data de Captura:** 2026-06-11  
**Versão do Documento:** 1.0.0  
**Status:** Baseline oficial antes de qualquer implementação FinOps  
**Autor:** Jefferson (DevOps) + Claude (AI Assistant)  

---

## Objetivo

Este documento serve como **fotografia oficial** do estado atual do CauSium antes de qualquer implementação futura.

Quando começarmos a implementar:
- Teams
- Tags
- Cost Allocation
- Untagged Resources

Poderemos responder: **"O que melhorou em relação ao baseline?"**

---

## 1. BASELINE EXECUTIVO

### Métricas Principais

| Métrica | Valor Atual | Fonte |
|---------|-------------|-------|
| **Health Check** | ✅ OK | `/health` |
| **Versão** | 0.1.0 | `/health` |
| **Alembic Current** | 0042 | PostgreSQL |
| **Alembic Heads** | 0044 | PROBLEMA: Múltiplas heads |
| **Total Migrations** | 45 | alembic/versions/ |
| **Migrations Applied** | 42 | PostgreSQL |
| **Workers Existentes** | 13 | backend/app/workers/ |
| **Pages Frontend** | 36 | frontend/src/pages/ |
| **APIs Registradas** | 21 | backend/app/api/v1/router.py |

### 1.1.1 Snapshot Operacional Atual

> **Data da Captura:** 2026-06-11  
> **Status:** Baseline não disponível na data da captura.

Os dados operacionais abaixo requerem acesso autenticado ao dashboard. Na data desta captura, não dispomos dos valores exatos do ambiente de produção.

| Métrica | Valor Atual | Status | Observação |
|---------|-------------|--------|------------|
| **Current Month Spend** | Baseline não disponível | ⚠️ | Requer acesso ao dashboard |
| **Estimated Savings Opportunity** | Baseline não disponível | ⚠️ | Requer acesso ao dashboard |
| **Number of Opportunities** | Baseline não disponível | ⚠️ | Requer acesso ao dashboard |
| **Number of Recommendations** | Baseline não disponível | ⚠️ | Requer acesso ao dashboard |
| **Number of Cloud Accounts** | Baseline não disponível | ⚠️ | Requer acesso à API |
| **Number of Subscriptions** | Baseline não disponível | ⚠️ | Requer acesso à API |
| **Number of Alerts** | Baseline não disponível | ⚠️ | Requer acesso à API |
| **Number of Resources Monitored** | Baseline não disponível | ⚠️ | Requer acesso ao ClickHouse |
| **Number of Workspaces** | Baseline não disponível | ⚠️ | Requer acesso à API |
| **Number of Members** | Baseline não disponível | ⚠️ | Requer acesso à API |

#### Como Preencher Estes Valores

Após implementar o baseline, acessar:

```bash
# 1. Health check
curl -s https://causium-api-2026.azurewebsites.net/health
# Esperado: {"status":"ok","version":"0.1.0"}

# 2. Dashboard (requer auth JWT)
curl -s -H "Authorization: Bearer <TOKEN>" \
  https://causium-api-2026.azurewebsites.net/api/v1/ledger/dashboard

# 3. Cloud Accounts
curl -s -H "Authorization: Bearer <TOKEN>" \
  https://causium-api-2026.azurewebsites.net/api/v1/cloud-accounts

# 4. Opportunities
curl -s -H "Authorization: Bearer <TOKEN>" \
  https://causium-api-2026.azurewebsites.net/api/v1/opportunities

# 5. ClickHouse - count resources
clickhouse-client --host k2xj32v350.westus3.azure.clickhouse.cloud \
  --port 8443 --secure \
  --query "SELECT count() FROM cost_facts"

# 6. ClickHouse - spend atual
clickhouse-client --host k2xj32v350.westus3.azure.clickhouse.cloud \
  --port 8443 --secure \
  --query "SELECT sum(cost_usd) FROM cost_facts WHERE date >= '2026-06-01'"
```

#### Responsável por Preencher

Após obter acesso ao ambiente, preencher esta tabela com os valores reais.

#### Comparação Futura

Quando estes valores forem preenchidos, servirão como baseline para comparação com implementações futuras.

---

### Custos e Oportunidades

| Métrica | Valor | Status |
|---------|-------|--------|
| **Current Month Spend** | _A DEFINIR_ | ⚠️ Requer dashboard |
| **Estimated Savings Opportunity** | _A DEFINIR_ | ⚠️ Requer dashboard |
| **Número de Oportunidades** | _A DEFINIR_ | ⚠️ Requer dashboard |
| **Número de Subscriptions** | _A DEFINIR_ | ⚠️ Requer API |
| **Número de Cloud Accounts** | _A DEFINIR_ | ⚠️ Requer API |
| **Número de Recursos Monitorados** | _A DEFINIR_ | ⚠️ Requer ClickHouse |
| **Número de Recomendações** | _A DEFINIR_ | ⚠️ Requer API |
| **Número de Alertas** | _A DEFINIR_ | ⚠️ Requer API |
| **Número de Dashboards** | _A DEFINIR_ | ⚠️ Requer UI |

### Como Obter Valores Atuais

```bash
# 1. Health Check
curl -s https://causium-api-2026.azurewebsites.net/health
# Esperado: {"status":"ok","version":"0.1.0"}

# 2. Dashboard (requer auth)
# Acessar UI: https://app.causiumtech.com/dashboard

# 3. API de ledger (requer auth)
curl -s https://causium-api-2026.azurewebsites.net/api/v1/ledger/dashboard

# 4. Cloud Accounts
curl -s https://causium-api-2026.azurewebsites.net/api/v1/cloud-accounts

# 5. ClickHouse - count resources
clickhouse-client --host k2xj32v350.westus3.azure.clickhouse.cloud \
  --port 8443 --secure \
  --query "SELECT count() FROM cost_facts"
```

---

## 2. BASELINE FUNCIONAL

### Módulos Implementados

| Módulo | Status | Funcionando | Observações | Limitações |
|--------|--------|-------------|-------------|------------|
| **Dashboard** | ✅ | ✅ | Principal tela FinOps | Aguardar acesso para capturar valores |
| **Executive** | ✅ | ✅ | Resumo executivo | Requer auth |
| **Opportunities** | ✅ | ✅ | Savings opportunities | Requer auth |
| **Economics** | ✅ | ✅ | Cost Analysis | Requer auth |
| **Spend Analysis** | ✅ | ✅ | Parte de Economics | Requer auth |
| **Spend Stability** | ✅ | ⚠️ | Parcial - integrado com anomaly | Requer auth |
| **Spend by SKU** | ✅ | ✅ | Parte de Economics | Requer auth |
| **Governance (Gov)** | ⚠️ | ⚠️ | Parcial - business_mapping existe | Requer auth |
| **Notifications** | ✅ | ✅ | SMTP + Slack | Requer auth |
| **Reconciliation** | ✅ | ✅ | Multi-subscription | Requer auth |

### Detalhamento por Módulo

#### Dashboard
- **Status:** ✅ Implementado
- **Funcionando:** ✅
- **Arquivo:** `frontend/src/pages/Dashboard/DashboardPage.tsx`
- **Observações:** Página principal com KPIs, gráficos, alertas, tendências
- **Limitações:** Aguardar acesso para capturar métricas reais

#### Executive
- **Status:** ✅ Implementado
- **Funcionando:** ✅
- **Arquivo:** `frontend/src/pages/Executive/ExecutivePage.tsx`
- **Observações:** Resumo executivo com iniciativas, savings, trends
- **Limitações:** Requer auth

#### Opportunities (Savings)
- **Status:** ✅ Implementado
- **Funcionando:** ✅
- **Arquivo:** `frontend/src/pages/Opportunities/OpportunitiesPage.tsx`
- **Observações:** VM rightsizing, scoring, explain IA
- **Limitações:** Requer auth

#### Economics (Spend Analysis)
- **Status:** ✅ Implementado
- **Funcionando:** ✅
- **Arquivos:**
  - `EconomicsCosts/EconomicsCostsPage.tsx`
  - `EconomicsSkus/EconomicsSkusPage.tsx`
  - `EconomicsUsage/EconomicsUsagePage.tsx`
  - `EconomicsReports/EconomicsReportsPage.tsx`
- **Observações:** Multi-subscription, export CSV/Excel
- **Limitações:** Requer auth

#### Governance (Gov)
- **Status:** ⚠️ Parcial
- **Funcionando:** ⚠️
- **Arquivo:** `frontend/src/pages/Gov/GovPage.tsx`
- **Observações:** Business mapping existe, mas tags não implementadas
- **Limitações:** Tags não implementadas, Cost Allocation parcial

#### Notifications
- **Status:** ✅ Implementado
- **Funcionando:** ✅
- **Arquivo:** `frontend/src/pages/Notifications/NotificationsPage.tsx`
- **Observações:** SMTP + Slack, WebSocket stream
- **Limitações:** Requer auth

#### Reconciliation
- **Status:** ✅ Implementado
- **Funcionando:** ✅
- **Arquivo:** `frontend/src/pages/Reconciliation/ReconciliationPage.tsx`
- **Observações:** Multi-subscription reconciliation
- **Limitações:** Requer auth

---

## 3. BASELINE TÉCNICO

### Sistema em Produção

| Componente | Status | Detalhes |
|-----------|--------|----------|
| **Backend API** | ✅ OK | Health check passando |
| **Versão** | 0.1.0 | |
| **Frontend** | ✅ OK | Azure Static Web Apps |
| **Health Check** | ✅ OK | `{"status":"ok","version":"0.1.0"}` |

### Alembic Status

```bash
$ alembic current
0042

$ alembic heads
0044 (head)
??? (head) # PROBLEMA: Múltiplas heads

$ alembic branches
0007 (branchpoint)
     -> 0008a_notifications_alerts
     -> 0008
```

| Item | Valor | Observação |
|------|-------|------------|
| **Current Revision** | 0042 | |
| **Heads** | 0044 + ??? | Múltiplas heads - PROBLEMA |
| **Branch Point** | 0007 | |
| **Total Migrations** | 45 | |

### Workers Implementados

| Worker | Responsabilidade | Status |
|--------|-----------------|--------|
| `ingestion_worker` | Cost ingestion Azure/AWS/GCP | ✅ |
| `scoring_worker` | Generate optimization opportunities | ✅ |
| `anomaly_detection_worker` | Detect cost anomalies | ✅ |
| `notification_worker` | SMTP/Slack alerts | ✅ |
| `carbon_sync_worker` | Carbon emissions sync | ✅ |
| `export_worker` | CSV/Excel async export | ✅ |
| `audit_checkpoint_worker` | HMAC checkpoints | ✅ |
| `maintenance_worker` | LGPD anonymization | ✅ |
| `keyring_rotation_worker` | Fernet key rotation | ✅ |
| `usage_observation_worker` | Usage metrics for explain IA | ✅ |
| `ingestion_runner` | Runner para ingestion | ✅ |
| `job_runtime` | Job runtime utilities | ✅ |
| `runner` | Base runner | ✅ |

### APIs Registradas

| Domínio | Router | Status |
|---------|--------|--------|
| `auth` | ✅ | Backend authentication |
| `business_mapping` | ✅ | |
| `cloud_accounts` | ✅ | |
| `cloud_ledger` | ✅ | Dashboard, metrics, costs |
| `decision_engine` | ✅ | Opportunities, optimization |
| `executive` | ✅ | KPIs, initiatives |
| `workflow` | ✅ | |
| `experiments` | ✅ | PulseLab |
| `risk_budgets` | ✅ | Budget model |
| `change_events` | ✅ | |
| `audit_chain` | ✅ | |
| `workspaces` | ✅ | |
| `invites` | ✅ | |
| `admin` | ✅ | |
| `finops_readiness` | ✅ | |
| `economics` | ✅ | Costs, SKUs, reports |
| `notifications` | ✅ | Alerts, preferences |
| `gov` | ✅ | Governance |
| `green` | ✅ | Carbon |
| `intel` | ✅ | Anomaly, explain |
| `settings` | ✅ | |

### Páginas Frontend

| Página | Status | Observação |
|--------|--------|------------|
| Dashboard | ✅ | Principal |
| Executive | ✅ | Resumo |
| Opportunities | ✅ | Savings |
| EconomicsCosts | ✅ | Spend |
| EconomicsSkus | ✅ | SKU analysis |
| EconomicsUsage | ✅ | Usage |
| EconomicsReports | ✅ | Reports |
| Gov | ⚠️ | Parcial |
| Green | ⚠️ | Parcial |
| Notifications | ✅ | |
| Reconciliation | ✅ | |
| Experiments | ✅ | PulseLab |
| OptimizationPlan | ✅ | |
| RiskBudgets | ✅ | |
| ChangeEvents | ✅ | |
| Members | ✅ | |
| Settings | ✅ | |
| Login | ✅ | |
| AcceptTerms | ✅ | |
| ActivateInvite | ✅ | |
| Platform/IntegrationHealth | ✅ | |
| Platform/Slo | ✅ | |
| Platform/SyncStatus | ✅ | |
| Platform/Workspaces | ✅ | |
| ComingSoon | ✅ | Placeholder |

---

## 4. BASELINE FINOPS

### Status por Funcionalidade

| Funcionalidade | Status | Implementação | Dependências |
|---------------|--------|----------------|--------------|
| **Tags** | ❌ | Não implementado | - |
| **Untagged Resources** | ❌ | Não implementado | Tags |
| **Cost Allocation** | ⚠️ | Parcial - business_mapping | Tags |
| **Teams** | ❌ | Não implementado | Cost Allocation |
| **Budgets** | ⚠️ | Modelo existe (0012) | - |
| **Budget Alerts** | ❌ | Não funcionando | Budgets |
| **Advisor Recommendations** | ❌ | Não implementado | - |
| **Savings Plans** | ❌ | Não implementado | - |
| **Reserved Instances** | ❌ | Não implementado | - |
| **Governance Policies** | ⚠️ | Modelo parcial | - |

### Detalhamento

#### Tags Framework
- **Status:** ❌ NÃO IMPLEMENTADO
- **Modelo:** Não existe
- **API:** Não existe
- **UI:** Não existe
- **Impacto:** Não é possível fazer governança por tags
- **Meta Futura:** Framework completo de tags

#### Untagged Resources
- **Status:** ❌ NÃO IMPLEMENTADO
- **Dependência:** Tags Framework
- **Impacto:** Não é possível identificar recursos sem tag
- **Meta Futura:** Lista de recursos sem tag + alertas

#### Cost Allocation
- **Status:** ⚠️ PARCIAL
- **Existente:** business_mapping domain
- **Faltando:** Tags, Teams, Alocação automática
- **Impacto:** Alocação limitada
- **Meta Futura:** Alocação por Tags + Teams

#### Teams
- **Status:** ❌ NÃO IMPLEMENTADO
- **Dependência:** Cost Allocation
- **Impacto:** Não é possível ver custos por equipe
- **Meta Futura:** Custos segmentados por team

#### Budgets
- **Status:** ⚠️ PARCIAL
- **Existente:** Migration 0012, modelo RiskBudgets
- **Faltando:** Alerts, UI completa
- **Impacto:** Modelo existe mas alertas não funcionam
- **Meta Futura:** Budgets com alertas funcionando

#### Budget Alerts
- **Status:** ❌ NÃO FUNCIONANDO
- **Dependência:** Budgets, Notification Worker
- **Impacto:** Cliente não recebe alertas de orçamento
- **Meta Futura:** Alertas disparando por email/Slack

#### Advisor Recommendations
- **Status:** ❌ NÃO IMPLEMENTADO
- **Existente:** Migration 0024_provider_recommendation_sync (não aplicada)
- **Faltando:** Integração Azure/AWS/GCP Advisor APIs
- **Impacto:** Recomendações nativas não aparecem
- **Meta Futura:** Advisor Recommendations integradas

#### Savings Plans
- **Status:** ❌ NÃO IMPLEMENTADO
- **Impacto:** Não é possível analisar Savings Plans
- **Meta Futura:** Análise de Savings Plans

#### Reserved Instances
- **Status:** ❌ NÃO IMPLEMENTADO
- **Impacto:** Não é possível analisar RIs
- **Meta Futura:** Análise de Reserved Instances

#### Governance Policies
- **Status:** ⚠️ PARCIAL
- **Existente:** policy/models.py
- **Faltando:** Enforcement, UI
- **Impacto:** Políticas existem mas não são aplicadas
- **Meta Futura:** Enforcement de políticas

---

## 5. BASELINE DE RISCOS

### Riscos Identificados

| Risco | Severidade | Status | Mitigação |
|-------|------------|--------|-----------|
| **Alembic Multiple Heads** | 🔴 CRÍTICA | ⚠️ Migrations bloqueadas | Task técnica criada, NÃO executar até aprovação |
| **Migrations Bloqueadas** | 🔴 CRÍTICA | ⚠️ Não pode aplicar | Resolver Alembic primeiro |
| **Budget Alerts não funcionam** | 🟡 MÉDIA | ❌ Não disparando | Investigar notification_worker |
| **Advisor APIs não integradas** | 🟡 MÉDIA | ❌ Não implementado | Planejado para Fase 3 |
| **Tags não implementadas** | 🟡 MÉDIA | ❌ Não implementado | Planejado para Fase 2 |
| **Cost Allocation parcial** | 🟡 MÉDIA | ⚠️ Parcial | Planejado para Fase 2 |
| **Teams não implementado** | 🟡 MÉDIA | ❌ Não implementado | Planejado para Fase 2 |

### Riscos de Produção

| Risco | Probabilidade | Impacto | Ação |
|-------|---------------|---------|------|
| Dashboard indisponível | 🟡 Média | 🔴 Crítico | Políticas de engenharia implementadas |
| Migrations falhando | 🔴 Alta | 🔴 Crítico | NÃO executar até resolver |
| Alertas não disparando | 🟡 Média | 🟡 Médio | Investigar notification_worker |
| Integração externa falhando | 🟡 Média | 🟡 Médio | Fallback implementado |

---

## 6. BASELINE VISUAL

### Screenshots Necessários

Documentar estado visual das seguintes telas:

```
docs/baseline/screenshots/
├── README.md                    # Instruções de captura
├── dashboard-YYYYMMDD.png       # Dashboard principal
├── executive-YYYYMMDD.png        # Executive summary
├── opportunities-YYYYMMDD.png    # Savings opportunities
├── economics-YYYYMMDD.png         # Economics/Spend
├── gov-YYYYMMDD.png              # Governance
├── notifications-YYYYMMDD.png    # Notifications
└── reconciliation-YYYYMMDD.png   # Reconciliation
```

### Como Capturar Screenshots

1. Acessar https://app.causiumtech.com
2. Fazer login
3. Navegar para cada página
4. Capturar screenshot (1920x1080 recomendado)
5. Salvar em formato PNG
6. Nomear com data: `dashboard-2026-06-11.png`

### Checklist de Screenshots

| Página | URL | Status |
|--------|-----|--------|
| Dashboard | /dashboard | ⬜ |
| Executive | /executive | ⬜ |
| Opportunities | /opportunities | ⬜ |
| Economics | /economics | ⬜ |
| Governance | /gov | ⬜ |
| Notifications | /notifications | ⬜ |
| Reconciliation | /reconciliation | ⬜ |
| Optimization Plan | /optimization-plan | ⬜ |
| Experiments | /experiments | ⬜ |

---

## 7. MÉTRICAS DE COMPARAÇÃO FUTURA

### Tabela de Comparação ANTES vs DEPOIS

| Métrica | Valor Atual | Meta Futura | Diferença | Status |
|---------|-------------|-------------|-----------|--------|
| **Tags Framework** | ❌ Não existe | ✅ Implementado | - | ⬜ |
| **Recursos com Tags** | 0 | TBD | - | ⬜ |
| **Recursos sem Tags** | TBD | Reduzir 50% | - | ⬜ |
| **Cost Allocation Coverage** | ⚠️ Parcial | ✅ Completo | - | ⬜ |
| **Teams Implementados** | ❌ Não existe | ✅ N teams | - | ⬜ |
| **Budget Alerts Disparam** | ❌ Não | ✅ Sim | - | ⬜ |
| **Advisor Recommendations** | ❌ Não existe | ✅ Integradas | - | ⬜ |
| **Savings Plans** | ❌ Não existe | ✅ Implementado | - | ⬜ |
| **Reserved Instances** | ❌ Não existe | ✅ Implementado | - | ⬜ |
| **Governance Policies** | ⚠️ Parcial | ✅ Ativas | - | ⬜ |

### Métricas de Custo

| Métrica | Valor Atual | Meta Futura |
|---------|-------------|-------------|
| **Current Month Spend** | _A DEFINIR_ | Monitorado |
| **Estimated Savings** | _A DEFINIR_ | Aumentar |
| **Savings Realizado** | _A DEFINIR_ | Aumentar |
| **Cost per User** | _A DEFINIR_ | Otimizar |

### Métricas Técnicas

| Métrica | Valor Atual | Meta Futura |
|---------|-------------|-------------|
| **Alembic Heads** | 0044 + ??? | 1 (única) |
| **Migrations Pending** | 3 | 0 |
| **Workers Running** | 13 | 13+ |
| **APIs Available** | 21 | 21+ |
| **Pages Frontend** | 36 | 36+ |

### Métricas de Qualidade

| Métrica | Valor Atual | Meta Futura |
|---------|-------------|-------------|
| **Dashboard Uptime** | ✅ OK | Manter |
| **Health Check** | ✅ OK | Manter |
| **Alerts Delivery** | ⚠️ Parcial | 100% |
| **Data Freshness** | _A DEFINIR_ | <24h |

---

## 8. PRÓXIMOS PASSOS

### Antes de Qualquer Implementação

1. ✅ Roadmap documentado (`finops-alignment-roadmap.md`)
2. ⬜ Baseline de produção capturado (este documento)
3. ⬜ Screenshots capturados
4. ⬜ Métricas definidas
5. ⬜ Baseline commitado

### Ordem de Implementação (do Roadmap)

| Fase | Itens | Prioridade |
|------|-------|------------|
| **Fase 0** | Proteção + Baseline | 🔴 CRÍTICA |
| **Fase 1** | Alembic Multiple Heads | 🔴 CRÍTICA |
| **Fase 2** | Tags → Untagged → Cost → Teams → Budget → Anomaly | 🔴 ALTA |
| **Fase 3** | Advisor → RIs → SPs → AKS | 🟡 MÉDIA |
| **Fase 4** | Governance Policies → AI | 🟢 BAIXA |

---

## 9. REFERÊNCIAS

| Documento | Descrição |
|-----------|-----------|
| `CLAUDE.md` | Regras de engenharia |
| `docs/architecture/engineering-policy.md` | Políticas detalhadas |
| `docs/runbooks/deployment-checklist.md` | Checklist de deploy |
| `docs/roadmap/finops-alignment-roadmap.md` | Roadmap de implementação |
| `docs/incidents/2026-06-11-dashboard-outage.md` | Incidente original |
| `docs/technical-tasks/alembic-multiple-heads.md` | Task técnica Alembic |

---

## 10. HISTÓRICO DE REVISÕES

| Versão | Data | Autor | Mudanças |
|--------|------|-------|----------|
| 1.0.0 | 2026-06-11 | Jefferson + Claude | Versão inicial |

---

## 11. CHECKLIST DE VALIDAÇÃO

### Baseline Completo

- [ ] Documento criado
- [ ] Métricas executivas preenchidas
- [ ] Status de módulos documentado
- [ ] Status técnico documentado
- [ ] Status FinOps documentado
- [ ] Riscos identificados
- [ ] Screenshots organizados
- [ ] Métricas de comparação definidas
- [ ] Próximos passos documentados
- [ ] Baseline commitado

### Captura de Valores

- [ ] Health check verificado
- [ ] Alembic status documentado
- [ ] Workers listados
- [ ] APIs listadas
- [ ] Pages listadas
- [ ] Screenshots capturados
- [ ] Custos atuais documentados

---

**FIM DO DOCUMENTO**

Este baseline será atualizado quando implementações forem concluídas para permitir comparação ANTES vs DEPOIS.