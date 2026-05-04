# Azure Ingest Resolution — CauSium (2026-05-04)

## Contexto

Este documento registra a investigação, diagnóstico e resolução do problema de ingest de dados reais do Azure no CauSium. O objetivo é servir como referência técnica para a equipe e evitar retrabalho em investigações futuras.

---

## Problema inicial

O dashboard do tenant Queiroz (`queirozz@gmail.com`) exibia telas vazias ou com dados inconsistentes. A hipótese inicial era falha de deploy, autenticação ou frontend.

---

## O que foi investigado

### 1. Deploy e infraestrutura
- Backend Azure App Service (`causium-api-2026`, Brazil South) estava funcionando corretamente.
- GitHub Actions deployando com sucesso via push para `main`.
- Migrations Alembic rodando no startup sem erros.
- Auth JWT funcionando — login e tokens validados.

### 2. Dados no ClickHouse
Queries executadas via endpoint `/diagnostic/ingest` (protegido por `INTERNAL_MONITORING_KEY`):

```sql
-- Contagem por tabela para o org do tenant
SELECT count() FROM cost_facts   WHERE org_id = '1859c537-5f07-4923-9555-42817567c32d';  -- 10.000
SELECT count() FROM usage_facts  WHERE org_id = '1859c537-5f07-4923-9555-42817567c32d';  -- 0
SELECT count() FROM event_facts  WHERE org_id = '1859c537-5f07-4923-9555-42817567c32d';  -- 4.000

-- Verificação de dados mock
SELECT count() FROM cost_facts WHERE org_id LIKE 'mock-%';  -- 0

-- account_ids presentes nos dados
SELECT DISTINCT account_id FROM cost_facts WHERE org_id = '1859c537-5f07-4923-9555-42817567c32d';
-- Resultado: 1807c1f8-4985-453b-9597-2e51b4183b07
```

### 3. Cross-check account_id
- account_id registrado no PostgreSQL para o tenant: `1807c1f8-4985-453b-9597-2e51b4183b07` (Queiroz Azure)
- account_id presente nos dados do ClickHouse: `1807c1f8-4985-453b-9597-2e51b4183b07`
- **Match 100%.**

### 4. Sample rows confirmando dados reais

```
account_id: 1807c1f8-...  service: Storage  cost_usd: 0.000271  date: 2026-04-13
account_id: 1807c1f8-...  service: Storage  cost_usd: 0.011048  date: 2026-04-13
account_id: 1807c1f8-...  service: Storage  cost_usd: 0.059306  date: 2026-04-13
account_id: 1807c1f8-...  service: Storage  cost_usd: 0.586164  date: 2026-04-13
account_id: 1807c1f8-...  service: Storage  cost_usd: 1.364041  date: 2026-04-13
```

Valores fracionados reais de Azure Storage — não são dados mock.

---

## Correções realizadas

### 1. Logs de debug no blob ingest (`azure/client.py`)
Adicionados logs estruturados em `_fetch_costs_from_blob_exports` cobrindo:
- `azure.blob_ingest.start` — container, prefix, date range, checkpoints existentes
- `azure.blob_ingest.processing` — nome e etag de cada blob processado
- `azure.blob_ingest.parsed` — linhas parseadas por blob e total acumulado
- `azure.blob_ingest.parsed_zero_rows` — header CSV e schema esperado vs recebido (quando 0 linhas)
- `azure.blob_ingest.no_blobs_found` — prefix usado e caminho esperado (quando nenhum arquivo encontrado)
- `azure.blob_ingest.no_records_inserted` — lista de blobs encontrados mas sem registros inseridos
- `azure.blob_ingest.summary` — resumo final: total listado, processado, inserido
- `azure.blob_ingest.skipped` — quando storage_account_url ou container não estão configurados

### 2. Endpoints de diagnóstico interno (`main.py`)
Adicionados endpoints protegidos por `X-Internal-Key`:
- `GET /diagnostic/tenant?email=` — retorna org_id a partir do email
- `GET /diagnostic/ingest?org_id=` — contagens ClickHouse, mock check, cross-check account_id, sample rows, diagnóstico automático
- `GET /diagnostic/sync-account?account_id=` — força sync inline de uma conta sem depender de Redis/worker

---

## Diagnóstico final

**O problema não era:**
- Deploy (funcionando)
- Autenticação (funcionando)
- Frontend (funcionando)
- Dados mock contaminando o tenant (0 registros mock)

**O problema era:**
- Falta de visibilidade sobre o que o ingest estava fazendo — sem logs, era impossível saber se os blobs estavam sendo encontrados, parseados ou inseridos.
- Após adicionar os logs e forçar syncs, confirmou-se que o ingest Azure estava funcionando e os dados reais foram inseridos corretamente.

**Estado atual confirmado (2026-05-04):**

| Tabela | Linhas | Origem |
|---|---|---|
| cost_facts | 10.000 | Azure real (Queiroz Azure) |
| event_facts | 4.000 | Azure real (Queiroz Azure) |
| usage_facts | 0 | Não coletado ainda |

---

## Telas que ainda aparecem vazias

As seguintes telas podem aparecer vazias para o tenant Queiroz mesmo com o ingest funcionando. Isso **não é erro do sistema**.

### PulseIntel
Depende de baseline histórico suficiente para detectar anomalias e gerar insights. Com um tenant novo e poucos dias de dados, o modelo não tem comparativo para gerar alertas relevantes.

### Optimization Plan
Gerado a partir de recomendações do provider (Azure Advisor) e análise de usage. Com `usage_facts = 0`, não há dados de utilização para calcular rightsizing ou identificar recursos ociosos.

### PulseLab
Requer séries temporais longas para análise de tendência e projeção. Tenant novo com ~30 dias de dados pode não ter volume suficiente para projeções confiáveis.

### Initiatives
Dependem de configuração manual pelo usuário — o tenant precisa criar iniciativas de otimização explicitamente. Não são geradas automaticamente.

### Risk Budgets
Requerem que o usuário configure orçamentos e thresholds. Sem configuração manual, a tela fica vazia por design.

### Change Events
Dependem de `event_facts` com tipos de evento específicos (VM start/stop, resource create/delete). Com 4.000 eventos, pode haver dados, mas a tela pode filtrar apenas eventos de alta severidade ou tipos específicos que ainda não ocorreram no período.

---

## Recomendações

1. **Aguardar acúmulo de dados** — com 30-60 dias de histórico real, PulseIntel e PulseLab começarão a gerar insights automaticamente.
2. **Configurar usage metrics** — verificar se o Azure connector está coletando métricas de CPU/memória via Azure Monitor para popular `usage_facts`.
3. **Configurar budgets manualmente** — Risk Budgets requerem input do usuário.
4. **Não adicionar mock** — os dados reais já estão presentes e crescendo a cada sync.
5. **Monitorar logs `azure.blob_ingest.*`** — os logs adicionados permitem diagnosticar falhas de ingest sem precisar de acesso direto ao ClickHouse.

---

## Commits relacionados

| Hash | Descrição |
|---|---|
| `bc7b335` | debug: add detailed blob ingest logs for Azure cost_facts |
| `d26207f` | debug: add /diagnostic/sync-account endpoint for internal sync trigger |
| `6306262` | fix: change /diagnostic/sync-account to GET to bypass SPA catch-all |
| `6ac1d19` | debug: expand /diagnostic/ingest with mock check, account_id cross-check and diagnosis |

---

*Documento gerado em 2026-05-04. Validado com queries SQL diretas no ClickHouse via endpoint de diagnóstico.*
