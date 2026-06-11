# Tags Framework MVP - Implementation Plan

**Versão:** 1.0.0  
**Data:** 2026-06-11  
**Status:** Planejamento - NÃO IMPLEMENTAR  
**Tipo:** Plano de implementação  

---

## Objetivo

Planejar uma implementação segura, read-only e sem migration para entregar valor FinOps com tags usando dados já existentes no ClickHouse.

---

## 1. ESCOPO DO MVP

### ✅ Funcionalidades Incluídas

| Funcionalidade | Descrição | Prioridade |
|---------------|-----------|------------|
| **Tag Coverage** | Percentual de recursos com uma tag específica | 🔴 ALTA |
| **Untagged Cost** | Custo de recursos sem uma tag específica | 🔴 ALTA |
| **Cost by Tag Key** | Breakdown de custos por valor da tag | 🔴 ALTA |
| **Top Untagged Subscriptions** | Assinaturas com maior custo sem tag | 🔴 ALTA |
| **Tag Compliance Summary** | Resumo de compliance para múltiplas tags | 🟡 MÉDIA |

### ❌ Funcionalidades Fora do Escopo

| Funcionalidade | Motivo |
|---------------|--------|
| **CRUD de tags** | Requer nova tabela (Opção A) |
| **Escrita no banco** | Não é read-only |
| **Novas tabelas** | Requer Alembic (bloqueado) |
| **Migration** | Alembic Multiple Heads bloqueado |
| **Enforcement de policy** | Requer Opção A completa |
| **Automação** | Requer write path |
| **Alertas de untagged** | Requer Opção A |
| **Dashboard completo de governança** | Apenas MVP |

---

## 2. ARQUITETURA

### 2.1 Visão Geral

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    GovPage.tsx                           │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────────────┐  │  │
│  │  │Coverage   │  │Untagged    │  │Cost by Tag         │  │  │
│  │  │Widget     │  │Cost Widget │  │Table               │  │  │
│  │  └────────────┘  └────────────┘  └────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         BACKEND                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                  Gov Service (Read-Only)                │   │
│  │                                                          │   │
│  │  get_tag_coverage()     → TagCoverageResponse           │   │
│  │  get_untagged_cost()    → UntaggedCostResponse           │   │
│  │  get_cost_by_tag()      → CostByTagResponse              │   │
│  │  get_top_untagged()     → TopUntaggedResponse            │   │
│  │  get_compliance_summary() → List[TagComplianceSummary]   │   │
│  │                                                          │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         CLICKHOUSE                               │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                      cost_facts                          │   │
│  │                                                          │   │
│  │  Columns:                                                 │   │
│  │  - resource_id (String)                                  │   │
│  │  - subscription_id (String)                             │   │
│  │  - subscription_name (String)                           │   │
│  │  - workspace_id (UUID)                                   │   │
│  │  - cost_usd (Float64)                                    │   │
│  │  - date (Date)                                           │   │
│  │  - tags (JSON) ← Estrutura atual a descobrir             │   │
│  │                                                          │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Como Detectar Tags Existentes

```python
# Formato atual de tags no ClickHouse (a ser verificado)

# Opção 1: JSON field
# {"team": "engineering", "environment": "production"}

# Opção 2: Array
# ["team:engineering", "environment:production"]

# Opção 3: Key-value separado
# tag_key = "team", tag_value = "engineering"
```

### 2.3 Queries Conceituais

#### Total de Recursos com Tag

```sql
-- Contar recursos únicos que têm uma tag específica
SELECT count(DISTINCT resource_id)
FROM cost_facts
WHERE workspace_id = '{workspace_id}'
  AND date >= '{start_date}'
  AND date <= '{end_date}'
  AND JSONExtractString(tags, '{tag_key}') != ''
```

#### Total de Recursos sem Tag

```sql
-- Contar recursos únicos que NÃO têm uma tag específica
SELECT count(DISTINCT resource_id)
FROM cost_facts
WHERE workspace_id = '{workspace_id}'
  AND date >= '{start_date}'
  AND date <= '{end_date}'
  AND (JSONExtractString(tags, '{tag_key}') = '' 
       OR JSONExtractString(tags, '{tag_key}') IS NULL)
```

#### Custo Total

```sql
SELECT sum(cost_usd)
FROM cost_facts
WHERE workspace_id = '{workspace_id}'
  AND date >= '{start_date}'
  AND date <= '{end_date}'
```

#### Custo de Recursos sem Tag

```sql
SELECT sum(cost_usd)
FROM cost_facts
WHERE workspace_id = '{workspace_id}'
  AND date >= '{start_date}'
  AND date <= '{end_date}'
  AND (JSONExtractString(tags, '{tag_key}') = '' 
       OR JSONExtractString(tags, '{tag_key}') IS NULL)
```

#### Breakdown por Tag Value

```sql
SELECT 
    JSONExtractString(tags, '{tag_key}') as tag_value,
    sum(cost_usd) as total_cost,
    count(DISTINCT resource_id) as resource_count
FROM cost_facts
WHERE workspace_id = '{workspace_id}'
  AND date >= '{start_date}'
  AND date <= '{end_date}'
GROUP BY tag_value
ORDER BY total_cost DESC
```

### 2.4 Manter Read-Only

```
✅ PERMITIDO:
- SELECT queries no ClickHouse
- Read de cost_facts
- Aggregations
- Filters

❌ PROIBIDO:
- INSERT
- UPDATE
- DELETE
- CREATE TABLE
- ALTER TABLE
- Any write operation
```

---

## 3. ARQUIVOS PROVÁVEIS

### 3.1 Backend - Novos Arquivos

| Arquivo | Descrição | Ação |
|---------|-----------|------|
| `backend/app/domains/gov/schemas.py` | Pydantic schemas para responses | CRIAR |
| `backend/app/domains/gov/service.py` | Lógica de negócio (read-only) | CRIAR |
| `backend/app/domains/gov/router.py` | Endpoints da API | CRIAR |

### 3.2 Backend - Arquivos Existentes a Modificar

| Arquivo | Modificação | Ação |
|---------|-------------|------|
| `backend/app/api/v1/router.py` | Adicionar gov_router | MODIFICAR |

### 3.3 Frontend - Novos Arquivos

| Arquivo | Descrição | Ação |
|---------|-----------|------|
| `frontend/src/api/gov.ts` | Cliente API para governance | CRIAR |

### 3.4 Frontend - Arquivos Existentes a Modificar

| Arquivo | Modificação | Ação |
|---------|-------------|------|
| `frontend/src/pages/Gov/GovPage.tsx` | Adicionar widgets de compliance | MODIFICAR |

### 3.5 Testes - Novos Arquivos

| Arquivo | Descrição | Ação |
|---------|-----------|------|
| `backend/tests/unit/domains/gov/test_service.py` | Testes unitários do service | CRIAR |
| `backend/tests/integration/domains/gov/test_api.py` | Testes de integração da API | CRIAR |
| `frontend/tests/unit/api/gov.test.ts` | Testes do cliente API | CRIAR |

### 3.6 Estrutura de Diretórios

```
backend/app/domains/gov/
├── __init__.py
├── schemas.py          [NOVO]
├── service.py         [NOVO]
└── router.py          [NOVO]

frontend/src/
├── api/
│   └── gov.ts         [NOVO]
└── pages/
    └── Gov/
        └── GovPage.tsx [MODIFICAR]
```

---

## 4. ENDPOINTS READ-ONLY

### 4.1 GET /api/v1/gov/tag-coverage

**Descrição:** Retorna percentual de cobertura de uma tag específica.

**Request:**
```
GET /api/v1/gov/tag-coverage?tag_key=team&start_date=2026-06-01&end_date=2026-06-30
```

| Parâmetro | Tipo | Obrigatório | Default |
|-----------|------|-------------|---------|
| `tag_key` | string | Sim | - |
| `start_date` | date | Não | (hoje - 30 dias) |
| `end_date` | date | Não | hoje |
| `workspace_id` | UUID | Sim (header) | - |

**Response:**
```json
{
  "tag_key": "team",
  "total_resources": 1500,
  "tagged_resources": 1200,
  "untagged_resources": 300,
  "coverage_percentage": 80.0,
  "period_start": "2026-06-01",
  "period_end": "2026-06-30"
}
```

**Query ClickHouse:**
```sql
SELECT
    count(DISTINCT resource_id) as total_resources,
    countIf(DISTINCT resource_id, JSONExtractString(tags, '{tag_key}') != '') as tagged_resources,
    countIf(DISTINCT resource_id, JSONExtractString(tags, '{tag_key}') = '') as untagged_resources
FROM cost_facts
WHERE workspace_id = '{workspace_id}'
  AND date >= '{start_date}'
  AND date <= '{end_date}'
```

**Erros Possíveis:**
| Código | Descrição | Handling |
|--------|-----------|----------|
| 400 | tag_key não fornecido | Return error |
| 400 | start_date > end_date | Return error |
| 404 | workspace não encontrado | Return empty |
| 500 | ClickHouse error | Log and return error |

**Critério de Aceite:**
- [ ] Response inclui coverage_percentage
- [ ] coverage_percentage = (tagged / total) * 100
- [ ] Periodos retornados corretos
- [ ] Error 400 para tag_key vazio

---

### 4.2 GET /api/v1/gov/untagged-cost

**Descrição:** Retorna custo de recursos sem uma tag específica.

**Request:**
```
GET /api/v1/gov/untagged-cost?tag_key=team&start_date=2026-06-01&end_date=2026-06-30
```

**Response:**
```json
{
  "tag_key": "team",
  "total_cost": 50000.00,
  "tagged_cost": 45000.00,
  "untagged_cost": 5000.00,
  "untagged_percentage": 10.0,
  "period_start": "2026-06-01",
  "period_end": "2026-06-30"
}
```

**Query ClickHouse:**
```sql
SELECT
    sum(cost_usd) as total_cost,
    sumIf(cost_usd, JSONExtractString(tags, '{tag_key}') != '') as tagged_cost,
    sumIf(cost_usd, JSONExtractString(tags, '{tag_key}') = '') as untagged_cost
FROM cost_facts
WHERE workspace_id = '{workspace_id}'
  AND date >= '{start_date}'
  AND date <= '{end_date}'
```

**Erros Possíveis:**
| Código | Descrição |
|--------|-----------|
| 400 | tag_key não fornecido |
| 400 | start_date > end_date |
| 500 | ClickHouse error |

**Critério de Aceite:**
- [ ] Response inclui untagged_cost
- [ ] untagged_percentage = (untagged / total) * 100
- [ ] Valores em USD

---

### 4.3 GET /api/v1/gov/cost-by-tag

**Descrição:** Retorna breakdown de custos por valor de uma tag.

**Request:**
```
GET /api/v1/gov/cost-by-tag?tag_key=environment&start_date=2026-06-01&end_date=2026-06-30
```

**Response:**
```json
{
  "tag_key": "environment",
  "values": [
    {
      "tag_value": "production",
      "total_cost": 30000.00,
      "resource_count": 800,
      "avg_cost": 37.50
    },
    {
      "tag_value": "development",
      "total_cost": 15000.00,
      "resource_count": 600,
      "avg_cost": 25.00
    },
    {
      "tag_value": "staging",
      "total_cost": 5000.00,
      "resource_count": 100,
      "avg_cost": 50.00
    }
  ],
  "period_start": "2026-06-01",
  "period_end": "2026-06-30"
}
```

**Query ClickHouse:**
```sql
SELECT
    JSONExtractString(tags, '{tag_key}') as tag_value,
    sum(cost_usd) as total_cost,
    count(DISTINCT resource_id) as resource_count,
    avg(cost_usd) as avg_cost
FROM cost_facts
WHERE workspace_id = '{workspace_id}'
  AND date >= '{start_date}'
  AND date <= '{end_date}'
  AND JSONExtractString(tags, '{tag_key}') != ''
GROUP BY tag_value
ORDER BY total_cost DESC
LIMIT 50
```

**Critério de Aceite:**
- [ ] Lista ordenada por total_cost DESC
- [ ] Máximo 50 valores
- [ ] Valores com tag_value = "" excluídos

---

### 4.4 GET /api/v1/gov/top-untagged-subscriptions

**Descrição:** Retorna assinaturas com maior custo sem tag.

**Request:**
```
GET /api/v1/gov/top-untagged-subscriptions?tag_key=team&limit=10&start_date=2026-06-01&end_date=2026-06-30
```

**Response:**
```json
{
  "tag_key": "team",
  "subscriptions": [
    {
      "subscription_id": "sub-123",
      "subscription_name": "Production-USD",
      "total_cost": 20000.00,
      "untagged_cost": 8000.00,
      "resource_count": 500
    },
    {
      "subscription_id": "sub-456",
      "subscription_name": "Development-USD",
      "total_cost": 10000.00,
      "untagged_cost": 5000.00,
      "resource_count": 200
    }
  ],
  "period_start": "2026-06-01",
  "period_end": "2026-06-30"
}
```

**Query ClickHouse:**
```sql
SELECT
    subscription_id,
    subscription_name,
    sum(cost_usd) as total_cost,
    sumIf(cost_usd, JSONExtractString(tags, '{tag_key}') = '') as untagged_cost,
    count(DISTINCT resource_id) as resource_count
FROM cost_facts
WHERE workspace_id = '{workspace_id}'
  AND date >= '{start_date}'
  AND date <= '{end_date}'
GROUP BY subscription_id, subscription_name
ORDER BY untagged_cost DESC
LIMIT {limit}
```

**Critério de Aceite:**
- [ ] Ordenado por untagged_cost DESC
- [ ] Limite configurável (default 10)
- [ ] subscription_name = "Unknown" se NULL

---

### 4.5 GET /api/v1/gov/tag-compliance-summary

**Descrição:** Retorna resumo de compliance para múltiplas tags.

**Request:**
```
GET /api/v1/gov/tag-compliance-summary?tag_keys=team,environment,costcenter&start_date=2026-06-01&end_date=2026-06-30
```

**Response:**
```json
{
  "summaries": [
    {
      "tag_key": "team",
      "coverage_percentage": 80.0,
      "total_cost": 50000.00,
      "untagged_cost": 5000.00,
      "top_untagged_subscription": "Production-USD"
    },
    {
      "tag_key": "environment",
      "coverage_percentage": 95.0,
      "total_cost": 50000.00,
      "untagged_cost": 2500.00,
      "top_untagged_subscription": "Dev-Test"
    }
  ]
}
```

**Critério de Aceite:**
- [ ] Retorna múltiplas tags em uma chamada
- [ ] Separadas por vírgula
- [ ] Máximo 10 tags por chamada

---

## 5. QUERIES CLICKHOUSE

### 5.1 Query: Tag Coverage

```sql
-- Tag Coverage Percentage
WITH workspace AS (
    SELECT '{workspace_id}' as ws_id
),
date_range AS (
    SELECT 
        today() - 30 as start_date,
        today() as end_date
),
total_resources AS (
    SELECT count(DISTINCT resource_id) as cnt
    FROM cost_facts cf
    CROSS JOIN workspace w
    CROSS JOIN date_range dr
    WHERE cf.workspace_id = w.ws_id
      AND cf.date >= dr.start_date
      AND cf.date <= dr.end_date
),
tagged_resources AS (
    SELECT count(DISTINCT resource_id) as cnt
    FROM cost_facts cf
    CROSS JOIN workspace w
    CROSS JOIN date_range dr
    WHERE cf.workspace_id = w.ws_id
      AND cf.date >= dr.start_date
      AND cf.date <= dr.end_date
      AND JSONExtractString(cf.tags, '{tag_key}') != ''
)
SELECT 
    t.cnt as total,
    tg.cnt as tagged,
    t.cnt - tg.cnt as untagged,
    (tg.cnt / t.cnt * 100) as coverage_percentage
FROM total_resources t, tagged_resources tg
```

### 5.2 Query: Untagged Cost

```sql
-- Untagged Cost
SELECT
    sum(cost_usd) as total_cost,
    sumIf(cost_usd, JSONExtractString(tags, '{tag_key}') != '') as tagged_cost,
    sumIf(cost_usd, JSONExtractString(tags, '{tag_key}') = '') as untagged_cost
FROM cost_facts
WHERE workspace_id = '{workspace_id}'
  AND date >= '{start_date}'
  AND date <= '{end_date}'
```

### 5.3 Query: Cost by Tag Value

```sql
-- Cost by Tag Value
SELECT
    JSONExtractString(tags, '{tag_key}') as tag_value,
    sum(cost_usd) as total_cost,
    count(DISTINCT resource_id) as resource_count,
    avg(cost_usd) as avg_cost
FROM cost_facts
WHERE workspace_id = '{workspace_id}'
  AND date >= '{start_date}'
  AND date <= '{end_date}'
  AND JSONExtractString(tags, '{tag_key}') != ''
GROUP BY tag_value
ORDER BY total_cost DESC
```

### 5.4 Query: Top Untagged Subscriptions

```sql
-- Top Untagged Subscriptions
SELECT
    subscription_id,
    any(subscription_name) as subscription_name,
    sum(cost_usd) as total_cost,
    sumIf(cost_usd, JSONExtractString(tags, '{tag_key}') = '') as untagged_cost,
    count(DISTINCT resource_id) as resource_count
FROM cost_facts
WHERE workspace_id = '{workspace_id}'
  AND date >= '{start_date}'
  AND date <= '{end_date}'
GROUP BY subscription_id
HAVING untagged_cost > 0
ORDER BY untagged_cost DESC
LIMIT {limit}
```

---

## 6. ORDEM DE IMPLEMENTAÇÃO

### Fase 1: Backend - Service e Schemas (Dias 1-2)

```bash
# 1.1 Criar diretório gov
mkdir -p backend/app/domains/gov

# 1.2 Criar __init__.py
touch backend/app/domains/gov/__init__.py

# 1.3 Criar schemas.py
# - TagCoverageResponse
# - UntaggedCostResponse
# - CostByTagResponse
# - TopUntaggedResponse
# - TagComplianceSummary

# 1.4 Criar service.py
# - GovService class
# - get_tag_coverage()
# - get_untagged_cost()
# - get_cost_by_tag()
# - get_top_untagged()
# - get_compliance_summary()
```

### Fase 2: Backend - Router (Dia 3)

```bash
# 2.1 Criar router.py
# - GET /api/v1/gov/tag-coverage
# - GET /api/v1/gov/untagged-cost
# - GET /api/v1/gov/cost-by-tag
# - GET /api/v1/gov/top-untagged-subscriptions
# - GET /api/v1/gov/tag-compliance-summary

# 2.2 Registrar no router principal
# Edit: backend/app/api/v1/router.py
# Add: api_router.include_router(gov_router)
```

### Fase 3: Backend - Testes (Dia 4)

```bash
# 3.1 Criar testes unitários
# backend/tests/unit/domains/gov/test_service.py

# 3.2 Criar testes de integração
# backend/tests/integration/domains/gov/test_api.py

# 3.3 Executar pytest
pytest backend/tests/unit/domains/gov/
pytest backend/tests/integration/domains/gov/
```

### Fase 4: Frontend - Cliente API (Dias 5-6)

```bash
# 4.1 Criar cliente API
# frontend/src/api/gov.ts

# 4.2 Criar tipos TypeScript
# - TagCoverageResponse
# - UntaggedCostResponse
# - CostByTagResponse

# 4.3 Adicionar queries no React Query
```

### Fase 5: Frontend - UI (Dias 7-8)

```bash
# 5.1 Modificar GovPage.tsx
# - Adicionar TagComplianceWidget
# - Adicionar UntaggedCostWidget
# - Adicionar CostByTagTable

# 5.2 Testar renderização local
# npm run dev
```

### Fase 6: Validação (Dias 9-10)

```bash
# 6.1 Validação local
# - Backend sobe
# - Frontend renderiza
# - Endpoints respondem

# 6.2 Deploy para staging
# - git push origin main
# - Aguardar CI/CD

# 6.3 Validação staging
# - Health check OK
# - Login OK
# - Gov page OK
# - Métricas coerentes

# 6.4 Aprovação para produção
```

---

## 7. TESTES NECESSÁRIOS

### 7.1 Testes Unitários

```python
# backend/tests/unit/domains/gov/test_service.py

class TestGovService:
    def test_get_tag_coverage_with_data(self):
        """Test coverage with existing tags."""
        pass
    
    def test_get_tag_coverage_no_tags(self):
        """Test coverage when no resources have tag."""
        pass
    
    def test_get_tag_coverage_all_tagged(self):
        """Test coverage when all resources have tag."""
        pass
    
    def test_get_untagged_cost_zero(self):
        """Test untagged cost when all tagged."""
        pass
    
    def test_get_untagged_cost_all_untagged(self):
        """Test untagged cost when none tagged."""
        pass
    
    def test_cost_by_tag_sorted(self):
        """Test cost by tag is sorted descending."""
        pass
    
    def test_top_untagged_limit(self):
        """Test top untagged respects limit."""
        pass
    
    def test_compliance_summary_multiple_keys(self):
        """Test compliance summary for multiple tags."""
        pass
```

### 7.2 Testes de Integração

```python
# backend/tests/integration/domains/gov/test_api.py

class TestGovAPI:
    def test_tag_coverage_endpoint(self):
        """Test GET /api/v1/gov/tag-coverage"""
        pass
    
    def test_untagged_cost_endpoint(self):
        """Test GET /api/v1/gov/untagged-cost"""
        pass
    
    def test_cost_by_tag_endpoint(self):
        """Test GET /api/v1/gov/cost-by-tag"""
        pass
    
    def test_top_untagged_endpoint(self):
        """Test GET /api/v1/gov/top-untagged-subscriptions"""
        pass
    
    def test_compliance_summary_endpoint(self):
        """Test GET /api/v1/gov/tag-compliance-summary"""
        pass
    
    def test_auth_required(self):
        """Test endpoints require authentication."""
        pass
    
    def test_workspace_isolation(self):
        """Test data is isolated by workspace."""
        pass
    
    def test_invalid_tag_key(self):
        """Test error handling for invalid tag key."""
        pass
    
    def test_date_range_validation(self):
        """Test validation for date range."""
        pass
```

### 7.3 Testes de Performance

```python
def test_query_performance(self):
    """Test queries return within 2 seconds."""
    # Use pytest-timeout
    pass

def test_large_dataset(self):
    """Test performance with large dataset."""
    pass
```

---

## 8. VALIDAÇÃO LOCAL

### Checklist de Validação Local

- [ ] **Backend**
  - [ ] `cd backend && python -c "from app.main import app"` - OK
  - [ ] `cd backend && uvicorn app.main:app --reload` - Inicia
  - [ ] `curl http://localhost:8000/health` - OK

- [ ] **Endpoints**
  - [ ] `curl http://localhost:8000/api/v1/gov/tag-coverage?tag_key=team` - Response
  - [ ] `curl http://localhost:8000/api/v1/gov/untagged-cost?tag_key=team` - Response
  - [ ] `curl http://localhost:8000/api/v1/gov/cost-by-tag?tag_key=environment` - Response
  - [ ] `curl http://localhost:8000/api/v1/gov/top-untagged-subscriptions?tag_key=team` - Response

- [ ] **Frontend**
  - [ ] `cd frontend && npm run dev` - Inicia
  - [ ] `http://localhost:5173` - Carrega
  - [ ] Navegar para `/gov` - Renderiza

- [ ] **Sem Alterações no Banco**
  - [ ] Nenhuma migration criada
  - [ ] Nenhuma tabela criada
  - [ ] Nenhum INSERT/UPDATE executado

- [ ] **Console**
  - [ ] Sem erros no console do backend
  - [ ] Sem erros no console do frontend
  - [ ] Sem warnings críticos

---

## 9. VALIDAÇÃO EM STAGING

### Checklist de Validação em Staging

- [ ] **Health Check**
  - [ ] `curl https://causium-api-2026-staging.azurewebsites.net/health` - OK

- [ ] **Autenticação**
  - [ ] Login funciona
  - [ ] JWT válido

- [ ] **Dashboard**
  - [ ] Dashboard carrega
  - [ ] KPIs visíveis
  - [ ] Sem erros

- [ ] **Governance Page**
  - [ ] Navegar para `/gov`
  - [ ] Tag Coverage widget aparece
  - [ ] Untagged Cost widget aparece
  - [ ] Cost by Tag table aparece

- [ ] **Endpoints**
  - [ ] `/api/v1/gov/tag-coverage` - 200
  - [ ] `/api/v1/gov/untagged-cost` - 200
  - [ ] `/api/v1/gov/cost-by-tag` - 200
  - [ ] `/api/v1/gov/top-untagged-subscriptions` - 200

- [ ] **Sem Impacto**
  - [ ] Páginas existentes funcionam
  - [ ] Login continua funcionando
  - [ ] Dashboard continua funcionando
  - [ ] Nenhum erro 500

- [ ] **Logs**
  - [ ] Sem erros no Application Insights
  - [ ] Sem erros no Log Analytics

---

## 10. CRITÉRIOS DE ACEITE

### MVP é aceito quando TODOS os critérios abaixo forem satisfeitos:

| Critério | Descrição | Validação |
|---------|-----------|-----------|
| **Tag Coverage na UI** | Widget mostra % de cobertura | Visual |
| **Untagged Cost na UI** | Widget mostra custo sem tag | Visual |
| **Cost by Tag na UI** | Tabela mostra breakdown | Visual |
| **Top Untagged na UI** | Lista mostra subscriptions | Visual |
| **Tudo Read-Only** | Nenhum write path | Code review |
| **Nenhuma Migration** | Zero migrations criadas | `alembic history` |
| **Nenhuma Tabela Nova** | Zero tabelas criadas | DB inspection |
| **Testes Passando** | Unit + Integration | `pytest` |
| **Staging Validado** | Todos os checks OK | Manual |
| **Performance OK** | Response < 2s | APM |

### Critérios de Rejeição

- ❌ Tag Coverage não aparece na UI
- ❌ Untagged Cost não aparece na UI
- ❌ Qualquer write path detectado
- ❌ Migration criada
- ❌ Tabela criada
- ❌ Testes falhando
- ❌ Staging com erros 500
- ❌ Response time > 5s

---

## 11. ROLLBACK

### 11.1 Estratégia de Rollback

```bash
# Se algo der errado:

# 1. Remover router do registro
# Edit: backend/app/api/v1/router.py
# Remove: api_router.include_router(gov_router)

# 2. Remover arquivos do gov domain
rm -rf backend/app/domains/gov/
rm -f frontend/src/api/gov.ts

# 3. Reverter GovPage.tsx
git checkout -- frontend/src/pages/Gov/GovPage.tsx

# 4. Reverter commit completo
git revert <commit-sha>
git push origin main

# 5. Aguardar CI/CD
gh run list --workflow="Build and deploy" --limit 3

# 6. Validar rollback
curl https://causium-api-2026.azurewebsites.net/health
```

### 11.2 Rollback de Banco

```
⚠️ IMPORTANTE: NÃO HÁ ROLLBACK DE BANCO NECESSÁRIO

O MVP é 100% read-only:
- Nenhuma tabela criada
- Nenhuma coluna adicionada
- Nenhuma migration executada
- Nenhum dado modificado

O rollback é simplesmente remover o código.
```

### 11.3 Checkpoints de Rollback

| Checkpoint | Descrição |
|-----------|-----------|
| **Antes de começar** | Estado atual do repo |
| **Após criar service** | Commit parcial |
| **Após criar router** | Commit parcial |
| **Após frontend** | Commit completo |

---

## 12. RISCOS

### 12.1 Riscos Técnicos

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| **cost_facts não tem tags** | 🟡 Média | 🟢 Baixo | API retorna 0%, UI mostra "no data" |
| **Formato de tags diferente** | 🟡 Média | 🟡 Médio | Investigar formato real antes de implementar |
| **Performance query lenta** | 🟡 Média | 🟡 Médio | Indexes no ClickHouse, pagination |
| **Dados nulos** | 🟡 Média | 🟢 Baixo | Graceful handling, null coalescing |

### 12.2 Riscos de Dados

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| **Tags em formato inesperado** | 🟡 Média | 🟡 Médio | Investigar antes de implementar |
| **Azure vs AWS vs GCP** | 🟡 Média | 🟡 Médio | Queries genéricas, testar cada cloud |
| **Valores de tag inconsistency** | 🟢 Baixa | 🟡 Médio | Normalização no service |

### 12.3 Riscos de Interpretação

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| **Interpretação errada de coverage** | 🟡 Média | 🟡 Médio | Documentar metodologia |
| **Custo vs recurso count** | 🟢 Baixa | 🟡 Médio | Explicar diferença na UI |

### 12.4 Mitigações Globais

1. ✅ Investigar formato de tags no ClickHouse ANTES de implementar
2. ✅ Começar com queries simples
3. ✅ Validar dados retornados
4. ✅ Adicionar logging para debug
5. ✅ Testar com dados reais antes de staging

---

## 13. PRÉ-REQUISITO: INVESTIGAR FORMATO DE TAGS

### 13.1 Investigação Necessária

Antes de implementar, verificar:

```bash
# 1. Ver estrutura de cost_facts
clickhouse-client --host k2xj32v350.westus3.azure.clickhouse.cloud \
  --port 8443 --secure \
  --query "DESCRIBE TABLE cost_facts"

# 2. Ver sample de tags
clickhouse-client --host k2xj32v350.westus3.azure.clickhouse.cloud \
  --port 8443 --secure \
  --query "SELECT tags FROM cost_facts LIMIT 10 FORMAT JSON"

# 3. Verificar se tags existe
clickhouse-client --host k2xj32v350.westus3.azure.clickhouse.cloud \
  --port 8443 --secure \
  --query "SELECT count() FROM cost_facts WHERE has(tags, 'team') = 1"
```

### 13.2 Possíveis Formatos

| Formato | Exemplo | Query para extrair |
|---------|---------|---------------------|
| JSON | `{"team":"eng","env":"prod"}` | `JSONExtractString(tags, 'team')` |
| Array | `["team:eng","env:prod"]` | `arrayElement(splitByChar(':', tag), 2)` |
| Nested | `team=eng&env=prod` | `extractURLParameter(tags, 'team')` |

### 13.3 Ação Baseada na Investigação

```
Se tags existe como JSON:
  → Usar JSONExtractString

Se tags existe como Array:
  → Usar splitByChar + arrayElement

Se tags não existe:
  → MVP não pode ser implementado (requer Opção A)
  → Documentar e pausar
```

---

## 14. DECISÃO FINAL

### Este MVP é SEGURO porque:

| Garantia | Descrição |
|---------|-----------|
| **Não altera schema** | Zero migrations, zero tabelas novas |
| **Não altera dados** | 100% read-only, apenas SELECTs |
| **Não depende de Alembic** | Funciona mesmo com Multiple Heads |
| **Não cria tabelas** | Apenas lê de cost_facts existente |
| **Revertível via git** | `git revert` remove todo código |
| **Rollback simples** | Remover arquivos, reverter commit |
| **Baixo risco para produção** | Se falhar, não quebra nada |

### Quando Implementar

1. ✅ Investigar formato de tags no ClickHouse
2. ⬜ Validar que tags existem
3. ⬜ Criar service com queries adaptadas
4. ⬜ Implementar MVP completo
5. ⬜ Testar local
6. ⬜ Validar staging
7. ⬜ Aprovação
8. ⬜ Deploy produção

### Próximos Passos

1. Investigar formato de tags
2. Criar documento de investigação
3. Se tags existem → implementar MVP
4. Se tags não existem → avaliar alternativas

---

## 15. REFERÊNCIAS

| Documento | Descrição |
|-----------|-----------|
| `docs/technical-tasks/tags-framework-design.md` | Design do Tags Framework |
| `docs/technical-tasks/alembic-priority-assessment.md` | Priorização do Alembic |
| `docs/roadmap/finops-alignment-roadmap.md` | Roadmap FinOps |
| `docs/baseline/production-baseline-2026-06.md` | Baseline atual |
| `CLAUDE.md` | Regras de engenharia |

---

## 16. HISTÓRICO DE REVISÕES

| Versão | Data | Autor | Mudanças |
|--------|------|-------|----------|
| 1.0.0 | 2026-06-11 | Jefferson + Claude | Versão inicial |

---

**FIM DO DOCUMENTO**

Este documento é um plano de implementação. Nenhuma implementação deve ser feita sem seguir o fluxo:  
**Investigação → Plano → Diff → Teste Local → Staging → Validação → Aprovação → Produção**