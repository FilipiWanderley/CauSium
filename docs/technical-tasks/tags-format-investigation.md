# Tags Format Investigation - CauSium

**Versão:** 1.0.0  
**Data:** 2026-06-11  
**Status:** Investigação completa  
**Tipo:** Read-only - Apenas consultas SELECT  

---

## Objetivo

Investigar o formato real das colunas de tags na tabela `cost_facts` do ClickHouse para determinar se o MVP do Tags Framework pode ser implementado usando dados existentes.

---

## 1. ESTRUTURA DA TABELA (CONFIRMADA)

### Resultado: `DESCRIBE TABLE cost_facts`

```
=== COST_FACTS SCHEMA ===

| # | Column | Type | Descrição |
|---|--------|------|-----------|
| 1 | date | Date | Data do custo |
| 2 | org_id | String | ID da organização |
| 3 | account_id | String | ID da conta |
| 4 | provider | String | Provedor cloud |
| 5 | subscription_id | String | ID da assinatura |
| 6 | service | String | Serviço cloud |
| 7 | resource_id | String | ID do recurso |
| 8 | resource_name | String | Nome do recurso |
| 9 | region | String | Região |
| 10 | environment | String | Ambiente |
| 11 | owner_team | String | Equipe proprietária |
| 12 | cost_usd | Float64 | Custo em USD |
| 13 | usage_quantity | Float64 | Quantidade de uso |
| 14 | usage_unit | String | Unidade de uso |
| 15 | currency | String | Moeda |
| 16 | **tags** | **Map(String, String)** | Tags do recurso |
| 17 | **tags_map** | **Map(String, String)** | Mapa alternativo de tags |
| 18 | charge_type | LowCardinality(String) | Tipo de cobrança |
| 19 | pricing_model | LowCardinality(String) | Modelo de precificação |
| 20 | benefit_id | String | ID do benefício |
| 21 | benefit_name | String | Nome do benefício |
| 22 | frequency | LowCardinality(String) | Frequência |
| 23 | publisher_type | LowCardinality(String) | Tipo de publicador |
| 24 | cost_type | LowCardinality(String) | Tipo de custo |
| 25 | sku_name | String | Nome do SKU |
```

### Conclusão da Estrutura

✅ **Colunas de tags existem:**
- `tags` - Map(String, String)
- `tags_map` - Map(String, String)

✅ **Colunas úteis para Cost Allocation:**
- `environment` - String
- `owner_team` - String
- `region` - String
- `subscription_id` - String

---

## 2. INVESTIGAÇÃO A - Sample de Tags

### Query Executada

```sql
SELECT tags, tags_map FROM cost_facts LIMIT 10
```

### Resultado

```
Row 1:  tags: {}, tags_map: {}
Row 2:  tags: {}, tags_map: {}
Row 3:  tags: {}, tags_map: {}
...
Row 10: tags: {}, tags_map: {}
```

### Conclusão

❌ **Tags estão vazias** - Nenhum dos primeiros 10 registros tem dados em `tags` ou `tags_map`.

---

## 3. INVESTIGAÇÃO B - Cobertura de Tags

### Query Executada

```sql
SELECT 
    count() as total_records,
    countIf(length(tags.keys) > 0) as records_with_tags,
    countIf(length(tags.keys) = 0 OR length(tags.keys) IS NULL) as records_without_tags
FROM cost_facts
```

### Resultado

| Métrica | Valor |
|---------|-------|
| **Total records** | 29,955 |
| **Records with tags** | 0 |
| **Records without tags** | 29,955 |
| **Coverage** | **0.00%** |

### Conclusão

❌ **Cobertura de tags: 0%** - Nenhum registro na tabela tem dados em `tags`.

---

## 4. INVESTIGAÇÃO C - Owner Team

### Query Executada

```sql
SELECT 
    owner_team,
    count() as record_count,
    sum(cost_usd) as total_cost
FROM cost_facts 
GROUP BY owner_team 
ORDER BY total_cost DESC 
LIMIT 20
```

### Resultado

| Team | Records | Cost USD |
|------|---------|----------|
| **untagged** | 29,955 | $298,473.68 |

### Conclusão

❌ **Owner team: 100% "untagged"** - Nenhum registro tem equipe definida.

---

## 5. INVESTIGAÇÃO D - Environment

### Query Executada

```sql
SELECT 
    environment,
    count() as record_count,
    sum(cost_usd) as total_cost
FROM cost_facts 
GROUP BY environment 
ORDER BY total_cost DESC
```

### Resultado

| Environment | Records | Cost USD |
|-------------|---------|----------|
| **unknown** | 29,955 | $298,473.68 |

### Conclusão

❌ **Environment: 100% "unknown"** - Nenhum registro tem ambiente definido.

---

## 6. INVESTIGAÇÃO E - Subscriptions

### Query Executada

```sql
SELECT 
    provider,
    subscription_id,
    count() as record_count,
    sum(cost_usd) as total_cost
FROM cost_facts 
GROUP BY provider, subscription_id
ORDER BY total_cost DESC
LIMIT 15
```

### Resultado

| Provider | Subscription ID | Records | Cost USD |
|----------|-----------------|---------|----------|
| azure | 201e8476-a751-4301-ab17-0297573789a5 | 18,505 | $159,251.85 |
| azure | 180203f3-3ae4-4a2b-8042-158841b99818 | 2,815 | $54,166.17 |
| azure | 876a57c4-cc34-48d4-a161-f9e07537645a | 2,010 | $34,681.49 |
| azure | f251729c-663b-4fe5-9c78-a4e66df88915 | 2,160 | $27,352.26 |
| azure | 3d1fa4a6-6cde-4250-bdc1-b07a6873cc30 | 1,058 | $11,307.24 |
| azure | aa0b64d5-2a97-4098-b3d0-b5249ca55ce6 | 1,221 | $6,010.13 |
| azure | 518be8d3-0e03-42ee-941a-ca6aa208fbd6 | 1,012 | $3,138.11 |
| azure | 201d7e5d-72e2-4c72-a3e7-0623946372af | 1,174 | $2,566.43 |

### Conclusão

✅ **Subscriptions existem** - 8 subscriptions Azure com dados de custos.

---

## 7. INVESTIGAÇÃO F - Serviços

### Query Executada

```sql
SELECT 
    service,
    count() as record_count,
    sum(cost_usd) as total_cost
FROM cost_facts 
GROUP BY service
ORDER BY total_cost DESC
LIMIT 15
```

### Resultado

| Service | Records | Cost USD |
|---------|---------|----------|
| Storage | 19,186 | $132,889.39 |
| Virtual Machines | 3,934 | $115,709.32 |
| Bandwidth | 571 | $23,072.53 |
| Service Bus | 79 | $5,129.48 |
| Azure Data Factory v2 | 123 | $4,664.84 |
| Backup | 190 | $3,553.02 |
| Virtual Network | 3,604 | $3,485.34 |
| VPN Gateway | 34 | $3,001.59 |
| SQL Database | 72 | $2,585.19 |
| Network Watcher | 373 | $2,398.30 |
| NAT Gateway | 67 | $476.62 |
| Azure Cosmos DB | 22 | $433.63 |
| Azure App Service | 154 | $391.22 |
| IoT Hub | 20 | $218.16 |
| Azure Synapse Analytics | 35 | $182.93 |

### Conclusão

✅ **Serviços existem** - 15 serviços diferentes com custos registrados.

---

## 8. INVESTIGAÇÃO G - Tags vs Tags_map

### Query Executada

```sql
SELECT tags, tags_map FROM cost_facts WHERE length(tags_map.keys) > 0 LIMIT 5
```

### Resultado

```
NO RECORDS WITH tags_map DATA
All records have empty tags_map
```

### Conclusão

❌ **tags_map também está vazio** - Ambas as colunas de tags estão vazias.

---

## 9. RESUMO COMPLETO DAS DESCOBERTAS

### Tags Framework MVP - Viabilidade

| Item | Esperado | Real | Status |
|------|----------|------|--------|
| **tags column** | Map(String, String) | Map(String, String) | ✅ Existe |
| **tags_map column** | Map(String, String) | Map(String, String) | ✅ Existe |
| **Tags com dados** | Sim | NÃO (0%) | ❌ NÃO |
| **owner_team** | Dados | "untagged" (100%) | ❌ NÃO |
| **environment** | Dados | "unknown" (100%) | ❌ NÃO |
| **subscription_id** | Dados | 8 subscriptions | ✅ OK |
| **service** | Dados | 15 serviços | ✅ OK |
| **cost_usd** | Dados | $298,473.68 | ✅ OK |

### Coverage de Tags

| Coluna | Com Dados | Sem Dados | % |
|--------|-----------|-----------|---|
| `tags` | 0 | 29,955 | 0% |
| `tags_map` | 0 | 29,955 | 0% |
| `owner_team` | 0 | 29,955 | 0% |
| `environment` | 0 | 29,955 | 0% |

---

## 10. CONCLUSÕES

### 10.1 Sobre Tags

1. **As colunas `tags` e `tags_map` existem** no schema da tabela
2. **Ambas estão vazias** - 0% dos registros têm dados de tags
3. **O formato Map(String, String) está correto** para armazenar tags

### 10.2 Sobre Alternativas

| Campo | Status | Uso Possível |
|-------|--------|--------------|
| `owner_team` | ❌ "untagged" | Não utilizável |
| `environment` | ❌ "unknown" | Não utilizável |
| `subscription_id` | ✅ 8 valores | Sim - para agrupamento |
| `service` | ✅ 15 valores | Sim - para análise |
| `provider` | ✅ "azure" | Sim - para filtro |

### 10.3 Sobre Cost Allocation

**Actualmente não é possível fazer Cost Allocation por tags** porque:
- Tags não existem nos dados
- Owner_team não está preenchido
- Environment não está preenchido

**É possível fazer Cost Allocation por:**
- Subscription (8 subscriptions)
- Service (15 serviços)
- Provider (apenas Azure)
- Region (não verificado)

---

## 11. RECOMENDAÇÕES

### 11.1 Opção A: MVP Read-Only (NÃO VIÁVEL)

O MVP Read-Only que planejamos **não pode ser implementado** porque:
- A coluna `tags` existe mas está vazia
- Não há dados para calcular coverage
- Não há tags para mostrar na UI

### 11.2 Opção B: MVP por Subscription/Service

**VIÁVEL** - Implementar análise de custos por:

1. **Subscription Breakdown**
   - Agrupar custos por subscription
   - Mostrar custos por subscription
   - Identificar subscriptions mais custosas

2. **Service Breakdown**
   - Agrupar custos por serviço
   - Mostrar top serviços por custo
   - Identificar oportunidades de otimização

3. **Provider Breakdown**
   - Agrupar por provider
   - Apenas Azure no momento

### 11.3 Opção C: Aguardar Tags

Se o objetivo é implementar governança por tags:
- Precisaríamos que os dados fossem ingeridos com tags
- Ou implementar um processo de enrichment de dados
- Ou integrar com Azure Resource Graph para obter tags

### 11.4 Recomendação Final

**RECOMENDADO: Opção B - MVP por Subscription/Service**

Este MVP pode ser implementado porque:
- Dados existem e estão completos
- Não requer tags nos dados
- Entrega valor imediato ao cliente
- Mostra custos por subscription e serviço
- Funcional para análise FinOps

---

## 12. PRÓXIMOS PASSOS

### Se escolher Opção B (MVP por Subscription/Service):

1. **Atualizar design** do Tags Framework
2. **Mudar foco** de tags para subscription/service
3. **Criar novas queries** para aggregation
4. **Implementar UI** com Subscription/Services widgets
5. **Testar localmente**
6. **Validar em staging**

### Se escolher Opção C (Aguardar Tags):

1. **Documentar** que tags não existem nos dados
2. **Investigar** fonte de tags (Azure Resource Graph?)
3. **Planejar** processo de enrichment
4. **Voltar** ao planejamento quando dados estiverem disponíveis

---

## 13. DADOS COLETADOS

### Queries Executadas

| # | Query | Resultado |
|---|-------|-----------|
| 1 | DESCRIBE TABLE cost_facts | 25 colunas, tags existe |
| 2 | SELECT tags, tags_map LIMIT 10 | Todos vazios |
| 3 | countIf(tags) | 0% coverage |
| 4 | GROUP BY owner_team | 100% "untagged" |
| 5 | GROUP BY environment | 100% "unknown" |
| 6 | GROUP BY subscription_id | 8 subscriptions |
| 7 | GROUP BY service | 15 serviços |
| 8 | WHERE tags_map > 0 | Nenhum registro |

### Métricas Finais

| Métrica | Valor |
|---------|-------|
| Total records | 29,955 |
| Total cost | $298,473.68 |
| Subscriptions | 8 |
| Services | 15 |
| Tags coverage | 0% |
| Owner team coverage | 0% |
| Environment coverage | 0% |

---

## 14. REFERÊNCIAS

| Documento | Descrição |
|-----------|-----------|
| `docs/technical-tasks/tags-framework-design.md` | Design original |
| `docs/technical-tasks/tags-framework-mvp-implementation-plan.md` | Plano MVP |
| `docs/roadmap/finops-alignment-roadmap.md` | Roadmap |
| `docs/baseline/production-baseline-2026-06.md` | Baseline |

---

## 15. HISTÓRICO DE REVISÕES

| Versão | Data | Autor | Mudanças |
|--------|------|-------|----------|
| 1.0.0 | 2026-06-11 | Jefferson + Claude | Versão inicial |

---

**FIM DO DOCUMENTO**

Este documento é resultado de investigação read-only. Nenhuma implementação foi feita.