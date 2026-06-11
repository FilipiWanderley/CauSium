# Cost Governance UI Enhancements - Plano

**Versão:** 1.0.0  
**Data:** 2026-06-11  
**Status:** Planejamento - NÃO IMPLEMENTAR  
**Tipo:** Plano de implementação  

---

## Objetivo

Adicionar 2 widgets de UI ao GovPage usando APIs existentes, sem criar novos endpoints, tabelas ou migrations.

---

## ESCOPO

### ✅ Dentro do Escopo

| # | Enhancement | Prioridade | Esforço |
|---|------------|------------|---------|
| 1 | Governance Score no KPI Strip | 🔴 ALTA | 0.5 dia |
| 2 | Nova tab "Top Resources" | 🟡 MÉDIA | 1 dia |

### ❌ Fora do Escopo

| Item | Motivo |
|------|--------|
| Environment Coverage | 100% 'unknown' - sem valor |
| Novo backend | Não necessário |
| Novos endpoints | Já existem |
| Novas tabelas | Não necessário |
| Migrations | Não necessário |
| Tags Framework | Não agora |
| Cost Allocation novo | Não agora |

---

## 1. GOVERNANCE SCORE NO KPI STRIP

### 1.1 Descrição

Adicionar card "Governance Score" ao KPI Strip existente no GovPage.

### 1.2 Fonte de Dados

```typescript
// API: /gov/summary
// Dados: unowned_pct (já disponível via summaryQ.data)

// Fórmula:
governance_score = 100 - unowned_pct
```

### 1.3 Classificação

| Score | Classificação | Cor |
|-------|---------------|-----|
| 0-25 | Crítico | 🔴 Vermelho |
| 26-50 | Baixo | 🟠 Laranja |
| 51-75 | Médio | 🟡 Amarelo |
| 76-100 | Bom | 🟢 Verde |

### 1.4 Design do Card

```tsx
// Dentro do KPI Strip (linha 240-254)
<div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
  {[
    // ... cards existentes ...
    // NOVO: Governance Score
    { 
      label: g.governanceScore, 
      value: s ? (100 - s.unowned_pct).toFixed(0) : '—',
      color: getScoreColor(100 - (s?.unowned_pct ?? 100)),
      sub: getScoreLabel(100 - (s?.unowned_pct ?? 100))
    },
  ].map((k) => (...))}
</div>

// Funções auxiliares
function getScoreColor(score: number): string {
  if (score >= 76) return 'border-emerald-100'
  if (score >= 51) return 'border-amber-100'
  if (score >= 26) return 'border-orange-100'
  return 'border-red-100'
}

function getScoreLabel(score: number): string {
  if (score >= 76) return g.scoreGood
  if (score >= 51) return g.scoreMedium
  if (score >= 26) return g.scoreLow
  return g.scoreCritical
}
```

### 1.5 Traduções Necessárias

```typescript
// Adicionar em i18n
governanceScore: "Governance Score"
scoreGood: "Bom"
scoreMedium: "Médio"
scoreLow: "Baixo"
scoreCritical: "Crítico"
```

---

## 2. NOVA TAB "TOP RESOURCES"

### 2.1 Descrição

Adicionar nova tab "Top Resources" ao GovPage mostrando os20 recursos mais custosos.

### 2.2 Fonte de Dados

```typescript
// API: /ledger/costs
// Client: ledgerApi.detailedCosts()

const topResourcesQ = useQuery({
  queryKey: ['ledger', 'top-resources', days],
  queryFn: () => ledgerApi.detailedCosts({ 
    days: days, 
    page: 1, 
    page_size: 20 
  }),
  enabled: tab === 'top-resources',
})
```

### 2.3 Colunas da Tabela

| Coluna | Campo | Descrição |
|--------|-------|-----------|
| Resource Name | `resource_name` | Nome do recurso |
| Service | `service` | Serviço cloud |
| Subscription | `subscription_id` | ID da subscription |
| Region | `region` | Região |
| Cost | `cost_usd` | Custo total |

### 2.4 Design da Tab

```tsx
// Adicionar ao Tab type (linha 109)
type Tab = 'unowned' | 'compliance' | 'recommendations' | 'inventory' | 'tag-compliance' | 'top-resources'

// Adicionar à lista de TABS (linha 120-126)
const TABS: { id: Tab; label: string }[] = [
  // ... tabs existentes ...
  { id: 'top-resources', label: g.tabTopResources },
]

// Adicionar query (após linha 189)
const topResourcesQ = useQuery({
  queryKey: ['ledger', 'top-resources', days],
  queryFn: () => ledgerApi.detailedCosts({ 
    days: days, 
    page: 1, 
    page_size: 20 
  }),
  enabled: tab === 'top-resources',
})

// Adicionar renderização da tab (após tab-compliance)
{tab === 'top-resources' && (
  <div className="rounded-xl border border-gray-100 bg-white shadow-sm overflow-hidden">
    {topResourcesQ.isPending ? <SkeletonRows /> :
     topResourcesQ.isError ? (
      <div className="p-8 text-center text-sm text-red-500">{g.errorTopResources}</div>
     ) : (topResourcesQ.data?.items ?? []).length === 0 ? (
      <EmptyState icon={Server} message={g.noTopResources} />
     ) : (
      <table className="w-full text-sm">
        <thead className="border-b border-gray-100 bg-gray-50">
          <tr>
            <th>{g.colResourceName}</th>
            <th>{g.colService}</th>
            <th>{g.colSubscription}</th>
            <th>{g.colRegion}</th>
            <th>{g.colCost}</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-50">
          {topResourcesQ.data?.items.map((row, i) => (
            <tr key={i} className="hover:bg-gray-50">
              <td className="px-4 py-3 font-medium text-gray-800 truncate max-w-[200px]">
                {row.resource_name || row.resource_id}
              </td>
              <td className="px-4 py-3 text-gray-600">{row.service}</td>
              <td className="px-4 py-3 text-gray-500 text-xs truncate max-w-[150px]">
                {row.subscription_id}
              </td>
              <td className="px-4 py-3 text-gray-600">{row.region}</td>
              <td className="px-4 py-3 font-semibold text-gray-900">
                {formatMoney(row.cost_usd)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    )}
  </div>
)}
```

### 2.5 Traduções Necessárias

```typescript
// Adicionar em i18n
tabTopResources: "Top Resources"
colResourceName: "Resource Name"
colSubscription: "Subscription"
errorTopResources: "Error loading top resources"
noTopResources: "No resources found"
```

---

## 3. ARQUIVOS A ALTERAR

### 3.1 Frontend

| Arquivo | Alteração | Tipo |
|---------|-----------|------|
| `frontend/src/pages/Gov/GovPage.tsx` | Adicionar score + nova tab | MODIFICAR |
| `frontend/src/i18n/pt-BR.json` | Adicionar traduções | MODIFICAR |
| `frontend/src/i18n/en.json` | Adicionar traduções | MODIFICAR |

### 3.2 Nenhum Backend

| Item | Status |
|------|--------|
| Novos endpoints | ❌ Não |
| Novas APIs | ❌ Não |
| Novas tabelas | ❌ Não |
| Migrations | ❌ Não |

---

## 4. CRITÉRIOS DE ACEITE

### 4.1 Governance Score

| Critério | Descrição | Validação |
|---------|-----------|-----------|
| Score visível | Card aparece no KPI Strip | Visual |
| Score correto | Score = 100 - unowned_pct | API test |
| Classificação | Cor muda conforme score | Visual |
| Tradução | Label aparece em pt/en | Visual |

### 4.2 Top Resources Tab

| Critério | Descrição | Validação |
|---------|-----------|-----------|
| Tab existe | Tab "Top Resources" aparece | Visual |
| Tab funcional | Click mostra conteúdo | Visual |
| Dados carregam | 20 recursos aparecem | Visual |
| Colunas corretas | 5 colunas visíveis | Visual |
| Ordenação | Ordenado por custo DESC | Visual |
| Tradução | Labels em pt/en | Visual |

---

## 5. TESTES LOCAIS

### 5.1 Checklist

- [ ] **GovPage carrega** sem erro
- [ ] **Governance Score card** aparece no KPI Strip
- [ ] **Score calculado** corretamente (100 - unowned_pct)
- [ ] **Classificação** muda cor conforme score
- [ ] **Nova tab "Top Resources"** aparece no switcher
- [ ] **Click na tab** mostra conteúdo
- [ ] **Tabela carrega** 20 recursos
- [ ] **Recursos ordenados** por custo DESC
- [ ] **Traduções** funcionam em pt/en
- [ ] **Sem erro no console**
- [ ] **Responsivo** em mobile

### 5.2 Teste de Performance

- [ ] Page load < 2s
- [ ] Tab switch < 500ms
- [ ] Sem re-renders excessivos

---

## 6. VALIDAÇÃO STAGING

### 6.1 Checklist

- [ ] **Health check** OK
- [ ] **Login** funciona
- [ ] **GovPage** carrega
- [ ] **Governance Score** visível
- [ ] **Top Resources tab** funcional
- [ ] **Dados corretos** (vs ClickHouse)
- [ ] **Sem erro 500**
- [ ] **Logs limpos**

### 6.2 Validação de Dados

```bash
# Verificar dados no ClickHouse
SELECT sum(cost_usd) as total, 
       count(DISTINCT resource_id) as resources
FROM cost_facts 
WHERE date >= today() - 30
```

---

## 7. ROLLBACK

### 7.1 Estratégia

```bash
# 1. Reverter GovPage.tsx
git checkout -- frontend/src/pages/Gov/GovPage.tsx

# 2. Reverter traduções
git checkout -- frontend/src/i18n/pt-BR.json
git checkout -- frontend/src/i18n/en.json

# 3. Deploy
git push origin main
```

### 7.2 Checkpoint

| Checkpoint | Descrição |
|-----------|-----------|
| Antes | Estado atual do repo |
| Depois | Estado com enhancements |

---

## 8. RISCOS

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| **Query performance** | 🟡 Média | 🟡 Médio | LIMIT 20 |
| **Dados vazios** | 🟡 Média | 🟢 Baixo | EmptyState |
| **Tradução missing** | 🟢 Baixa | 🟡 Médio | Fallback |

---

## 9. ESTIMATIVA DE ESFORÇO

| Enhancement | Esforço | Total |
|------------|---------|-------|
| Governance Score | 0.5 dia | 0.5 dia |
| Top Resources Tab | 1 dia | 1 dia |
| **TOTAL** | | **1.5 dias** |

---

## 10. PRÓXIMOS PASSOS

1. ✅ Criar plano
2. ⬜ Aprovar plano
3. ⬜ Implementar Governance Score
4. ⬜ Implementar Top Resources Tab
5. ⬜ Testar localmente
6. ⬜ Validar staging
7. ⬜ Aprovar produção
8. ⬜ Deploy

---

## 11. REFERÊNCIAS

| Documento | Descrição |
|-----------|-----------|
| `docs/technical-tasks/cost-governance-functional-audit.md` | Auditoria funcional |
| `docs/technical-tasks/cost-governance-gap-analysis.md` | GAP analysis |
| `frontend/src/pages/Gov/GovPage.tsx` | Código fonte |
| `frontend/src/api/gov.ts` | API client gov |
| `frontend/src/api/ledger.ts` | API client ledger |

---

## 12. HISTÓRICO

| Versão | Data | Autor | Mudanças |
|--------|------|-------|----------|
| 1.0.0 | 2026-06-11 | Jefferson + Claude | Versão inicial |

---

**FIM DO DOCUMENTO**

Este documento é plano de implementação. Nenhuma implementação foi feita.