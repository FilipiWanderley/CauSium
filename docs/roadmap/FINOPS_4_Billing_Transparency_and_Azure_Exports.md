# FINOPS-4 — Billing Transparency, Azure Exports, and Reservation Readiness

Data base: 2026-05-12

Objetivo: consolidar a evolucao recente de FINOPS no CauSium sem alterar o comportamento atual de custo, registrando arquitetura resumida, limites conhecidos dos exports Azure e o roadmap incremental da trilha FINOPS-4.

---

## 1) Resumo arquitetural

O fluxo atual para custos Azure segue o mesmo desenho macro do produto:

```text
Azure Cost Management Export / APIs
-> ingestao read-only
-> normalizacao em cost_facts
-> metadados auxiliares de billing e cobertura
-> APIs ledger/economics
-> Dashboard / Executive / diagnostics
```

Camadas relevantes:

- **Origem:** Azure Cost Management Export CSV, com variacao entre formatos legacy e modernos
- **Ingestao:** pipeline read-only com protecao idempotente para exports cumulativos
- **Persistencia:** `cost_facts` no ClickHouse para analytics; PostgreSQL para catalogos e metadados operacionais
- **Servico de ledger:** agrega custo e anexa metadados de transparencia, como intervalo coberto, subscriptions consolidadas e moeda de billing
- **Frontend:** `Dashboard` e `Executive` exibem contexto de billing sem recalcular ou converter os valores exibidos

Principio operacional:

- **Transparencia primeiro**
- **Sem alterar o numero base**
- **Sem conversao cambial implicita**
- **Sem alterar `cost_usd` nesta etapa**

---

## 2) Por que Azure Portal e exports podem divergir

Nem toda divergencia entre CauSium e Azure Portal representa bug. Em billing Azure enterprise, a comparacao depende de varios fatores:

- A visao do Portal pode estar configurada para **ActualCost** ou **AmortizedCost**
- O Portal pode aplicar filtros, escopo, grouping e defaults de UI que nao aparecem no export bruto
- Alguns exports trazem somente subconjuntos de metadados de reserva, savings plan ou charges
- O recorte temporal do export pode ser parcial dentro do mes
- O billing currency do tenant pode nao coincidir com o nome historico da coluna `cost_usd`

Em termos praticos:

- **Azure Portal** e uma camada de visualizacao/analise
- **Export CSV** e a fonte operacional bruta
- **CauSium** precisa interpretar o export com seguranca, manter consistencia e deixar claro o contexto de leitura

Por isso a trilha recente priorizou:

- metadados de cobertura de datas
- visibilidade de consolidacao por subscription
- indicacao explicita de billing currency
- indicacao explicita de base **Actual Cost · Pre-tax**

---

## 3) ActualCost vs AmortizedCost

### ActualCost

Representa o custo faturado do periodo de forma direta, normalmente mais proximo de:

- consumo efetivo no periodo
- charges pre-tax
- leitura operacional de custo corrente

Uso recomendado no estado atual do produto:

- Dashboard executivo
- contexto financeiro corrente
- comparacao operacional com periodo selecionado

### AmortizedCost

Redistribui compromissos e beneficios ao longo do tempo, sendo mais apropriado para:

- analise de eficiencia de reservas
- leitura financeira alocada ao periodo
- comparacao enterprise de custo comprometido vs realizado

### Decisao atual do CauSium

Nesta etapa, o produto explicita a base **Actual Cost · Pre-tax** e nao troca a numerica base mostrada ao usuario. O objetivo e evitar ambiguidade antes da entrega completa da camada amortizada.

---

## 4) Limitacoes de legacy exports

Os exports Azure nao sao uniformes entre tenants. Ha cenarios em que o export:

- usa colunas antigas ou nomes diferentes
- nao traz metadados de reserva
- nao traz campos suficientes para separar custo operacional de custo amortizado
- nao entrega o mesmo nivel de detalhe visto no Portal

Limitacoes mais importantes:

- **legacy export format:** schema menos rico e menos previsivel
- **reservation metadata incompleta:** pode faltar `benefit_id`, `benefit_name` ou classificacoes equivalentes
- **charge typing parcial:** dificulta separar compra, uso, ajuste e credito
- **pricing model parcial:** dificulta distinguir on-demand, reservation e savings plan

Consequencia operacional:

- dois tenants Azure podem ter ingestao "saudavel", mas niveis diferentes de explicabilidade FINOPS
- o produto precisa detectar capacidade do export antes de prometer certas analises

---

## 5) Azure export capability detection

A evolucao recente adiciona uma camada de interpretacao de capacidade do export, para responder perguntas como:

- este tenant entrega base mais alinhada a **actual** ou **amortized**?
- o export e **legacy** ou **modern**?
- ha metadados suficientes para reservas e savings plans?
- a comparacao com o Azure Portal exige algum cuidado adicional?

Os sinais observados sao agrupados em diagnostico enterprise e usados como pistas para:

- suporte tecnico
- troubleshooting de divergencia
- calibracao da UX de billing transparency
- roadmap de enriquecimento por tenant

---

## 6) Azure Cost Export idempotent ingestion

O ponto mais critico de confiabilidade recente foi corrigir o comportamento de exports Azure cumulativos.

Problema:

- cada CSV diario do Azure pode conter o mes acumulado
- sem tratamento de sobreposicao, o mesmo custo entra varias vezes

Resolucao adotada:

- limpeza do range sobreposto antes do insert
- delete estritamente escopado por `org_id + account_id + provider + subscription_id + intervalo de datas`
- abortar ingestao se a limpeza falhar
- reprocessamento seguro no ciclo seguinte

Efeito:

- ingestao deduplication-safe
- prevencao de duplicacao acumulativa
- comportamento seguro em producao

Referencia complementar:

- `docs/incidents/azure-cost-duplication-resolution.md`

---

## 7) Billing transparency metadata

Para reduzir ambiguidade na leitura dos numeros, o produto passou a anexar metadados de transparencia ao payload e a exibi-los no frontend.

Campos principais:

- `data_min_date`
- `data_max_date`
- `subscriptions_included`
- `billing_currency`
- `cost_basis`

O que isso resolve:

- deixa claro o intervalo real coberto pelos dados
- mostra quando a visao esta consolidando varias subscriptions
- explicita a moeda de billing
- explicita que a base atual exibida e **Actual Cost · Pre-tax**

O que isso nao faz:

- nao recalcula custo
- nao converte moeda
- nao altera `cost_usd`
- nao implementa amortizacao completa

---

## 8) Reservation and Savings Plan readiness

Para preparar a proxima camada de analytics FINOPS, o pipeline normalizado agora suporta metadados estruturados de billing:

- `charge_type`
- `pricing_model`
- `benefit_id`
- `benefit_name`
- `publisher_type`
- `frequency`
- `cost_type`

Esses campos servem como base para:

- separar charges operacionais de beneficios amortizados
- distinguir compra, uso e ajuste
- diagnosticar cobertura de reservation e savings plan
- suportar analise futura de custo operacional vs amortizado

Estado atual:

- a base de metadados esta pronta
- a UX atual usa isso principalmente para diagnostico e preparacao
- a analise amortizada completa fica para incrementos posteriores

---

## 9) Enterprise diagnostics UX

O UX recente para enterprise diagnostics tem tres objetivos:

- explicar "o que estou vendo"
- explicar "qual cobertura tenho"
- explicar "por que este tenant pode divergir de outro"

Elementos de UX agora associados a esse objetivo:

- intervalo de cobertura exibivel
- consolidacao de subscriptions exibivel
- billing currency explicita
- base de custo explicita
- sinais de capacidade do export para troubleshooting enterprise

Isso reduz o risco de interpretacao errada sem tocar nos calculos existentes.

---

## 10) Roadmap incremental FINOPS-4

### Fase 1 — Transparencia de billing

Entregue:

- data coverage range
- subscription consolidation visibility
- billing currency transparency
- actual/pre-tax indication

### Fase 2 — Capability detection

Entregue/parcial:

- deteccao de export legacy vs modern
- pistas para actual vs amortized
- visibilidade de disponibilidade de metadados de reserva
- hints para comparacao com Azure Portal

### Fase 3 — Reservation analytics readiness

Entregue/parcial:

- suporte estruturado a `charge_type`, `pricing_model`, `benefit_*`, `publisher_type`, `frequency`, `cost_type`

Pendente:

- classificacao mais rica de charges por tenant
- paines dedicados de reservation/savings plan diagnostics

### Fase 4 — Operational vs amortized analytics

Planejado:

- comparacao lado a lado entre custo operacional e amortizado
- leitura de cobertura de beneficio por subscription e periodo
- reconciliacao orientada a benefit metadata
- hints de explainability financeira por tipo de charge

### Fase 5 — FINOPS enterprise drill-down

Planejado:

- diagnostico por tenant/export capability
- comparacao Portal vs export guiada por contexto
- score de qualidade do export para analytics avancado
- insights enterprise sobre maturidade de billing data

---

## 11) Guardrails desta trilha

As evolucoes documentadas aqui seguiram os mesmos guardrails operacionais recentes:

- sem mutacao cloud
- sem alteracao de ingestion fora do escopo aprovado
- sem alteracao de `cost_usd`
- sem mudanca silenciosa de base numerica
- transparencia visual adicionada sem alterar KPI calculado

---

## 12) Resumo executivo

As entregas recentes de FINOPS no CauSium melhoram quatro dimensoes ao mesmo tempo:

1. **Confiabilidade** da ingestao Azure
2. **Transparencia** da leitura financeira no frontend
3. **Diagnostico** de capacidade real dos exports enterprise
4. **Preparacao** para analytics de reservation e savings plans

O resultado e um produto mais explicavel e mais seguro para comparacoes enterprise, sem alterar a base numerica atual nem introduzir mutacoes operacionais fora de escopo.
