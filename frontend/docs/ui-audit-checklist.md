# UI Audit Checklist - CauSium Dashboard

## Objetivo
Auditoria visual e de acessibilidade do dashboard CauSium para garantir qualidade, responsividade e conformidade WCAG.

---

## 1. Responsividade Mobile

### Checkpoints
- [ ] **Sidebar**: Fecha ao navegar em mobile (< 1024px)
- [ ] **KPI Grid**: Quebra de 4 colunas para 2 ou 1 em telas menores
- [ ] **Filtros**: Provider filter e subscription select não extrapolam container
- [ ] **Gráficos**: Tooltip e eixos legíveis em 375px (iPhone SE)
- [ ] **Tables**: Colunas ocultas com `hideBelow` funcionam corretamente
- [ ] **Page header**: Actions não sobrepõem título em mobile

### Critério de Falha
- Overflow horizontal em qualquer viewport
- Texto truncado sem ellipsis
- Elementos sobrepostos

---

## 2. Contraste WCAG AA

### Cores Críticas a Verificar
| Seletor | Cor Atual | Ratio | WCAG AA |
|---------|-----------|-------|---------|
| `text-slate-400` | #94a3b8 | ~3.0:1 | ❌ Falha |
| `text-slate-500` | #64748b | ~4.5:1 | ⚠️ Quase |
| `text-slate-300` | #cbd5e1 | ~2.2:1 | ❌ Falha |
| `text-brand-600` | #2563eb | ~4.8:1 | ✅ Passa |
| `text-emerald-600` | #059669 | ~4.6:1 | ✅ Passa |
| `text-rose-600` | #dc2626 | ~5.2:1 | ✅ Passa |

### Critério de Falha
- Texto com contraste < 4.5:1 para texto normal
- Texto com contraste < 3:1 para texto grande (18px+)

### Ação Recomendada
Para `text-slate-400` em backgrounds claros:
```css
/* Antes (ratio ~3.0:1) */
text-slate-400

/* Recomendação para captions/diagnostics */
text-slate-500  /* ratio ~4.5:1 */
```

---

## 3. Acessibilidade ARIA

### Checkpoints
- [ ] **Filtros**: Provider dropdown tem `aria-label` ou `aria-labelledby`
- [ ] **Botões de ação**: Todos têm `aria-label` quando ícone puro
- [ ] **Modais**: Têm `role="dialog"`, `aria-modal="true"`, `aria-labelledby`
- [ ] **Tabelas**: Headers têm `scope="col"`
- [ ] **Gráficos**: SVG tem `role="img"` e `aria-label` descritivo
- [ ] **Loading**: Skeleton tem `aria-busy="true"` ou `role="status"`
- [ ] **Alertas/Banners**: Têm `role="alert"` ou `aria-live`
- [ ] **Links**: Todos têm texto visível ou `aria-label`

### Critério de Falha
- Falta de `aria-label` em botões de ícone
- Modal sem `aria-labelledby`
- Tabela sem headers acessíveis

---

## 4. Tamanho do Bundle

### Targets
| Métrica | Target | Atual | Status |
|---------|--------|-------|--------|
| JS (gzip) | < 250kb | ? | ⏳ |
| CSS (gzip) | < 50kb | ? | ⏳ |
| First Load JS | < 300kb | ? | ⏳ |
| Largest Contentful Paint | < 2.5s | ? | ⏳ |

### Componentes que mais pesam
- [ ] Recharts (~80kb gzip)
- [ ] Lucide React (~15kb gzip)
- [ ] React Router (~10kb gzip)
- [ ] TanStack Query (~35kb gzip)

### Análise
```bash
npm run analyze:bundle
```

---

## 5. Cards Quebrando Layout

### Checkpoints
- [ ] **KPI Cards**: Não overflow em 320px
- [ ] **Panel Grid**: Não quebra em 768px (iPad)
- [ ] **Anomaly items**: Texto truncado com ellipsis
- [ ] **Top services**: Barras de progresso não overflow
- [ ] **Activity feed**: Texto não挤在一起

### Layout Grid
```css
/* KPI Grid - atual */
.kpi-grid {
  @apply grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4;
}

/* Verificar breakpoints */
- 320px:  1 coluna
- 640px:  2 colunas
- 1280px: 4 colunas
```

---

## 6. Gráficos Legibilidade

### Cost Trend Chart
- [ ] Eixos legíveis em 375px
- [ ] Tooltip não corta em telas pequenas
- [ ] Labels não sobrepõem
- [ ] Legends legíveis

### Anomaly Items
- [ ] Severity badge legível
- [ ] Texto truncado corretamente
- [ ] Não quebra em 2 linhas

### Critério de Falha
- Texto < 10px (fonte muito pequena)
- Overflow horizontal
- Tooltip fora da viewport

---

## 7. Filtros Crescendo Demais

### Provider Filter
```tsx
// Verificar comportamento com muitas subscriptions
<select>
  <option value="">All Subscriptions</option>
  {subscriptionsData?.items.map((s) => (
    <option key={s.subscription_id} value={s.subscription_id}>
      {s.subscription_name || s.subscription_id.slice(0, 8)}
    </option>
  ))}
</select>
```

### Checkpoints
- [ ] Select não cresce verticalmente
- [ ] Dropdown menu tem max-height com scroll
- [ ] Longos nomes de subscription não quebram layout
- [ ] Contador de items visível

---

## 8. Loading/Skeleton

### Componentes com Skeleton
- [ ] `DashboardPage` loading state
- [ ] `DataTable` skeleton rows
- [ ] `KpiCard` skeleton
- [ ] `ChartPanel` skeleton

### Checkpoints
- [ ] Skeleton aparece instantaneamente (sem flash)
- [ ] Animação não causa motion sickness (recomendado: 1.5s)
- [ ] Skeleton corresponde ao layout final
- [ ] `aria-busy="true"` nos containers

---

## 9. Tabelas e Data Grid

### DataTable Features
- [ ] Ordenação funcional
- [ ] Responsive `hideBelow`
- [ ] Sticky header opcional
- [ ] Row click handler
- [ ] Loading skeleton
- [ ] Empty state

### Checkpoints
- [ ] Headers clicáveis com feedback visual
- [ ] Sort icon indica direção
- [ ] Coluna ativa tem estilo diferente
- [ ] Mobile: coluna primária mostra meta

---

## 10. Sidebar Mobile

### Checkpoints
- [ ] Sidebar oculta em < 1024px
- [ ] Botão hamburger abre sidebar
- [ ] Overlay fecha sidebar ao clicar fora
- [ ] Navegação fecha sidebar
- [ ] Animação suave (não jarring)

### Enterprise Shell
- [ ] Toggle density funciona
- [ ] Grupos expansíveis
- [ ] Badge de notificações
- [ ] Scroll fade nos extremos

---

## Checklist de Execução

```bash
# 1. Verificar responsividade
npm run dev
# Redimensionar para 375px, 768px, 1024px, 1440px

# 2. Verificar contraste
npm run test:a11y
# Ou usar Chrome DevTools > Elements > Accessibility

# 3. Verificar bundle
npm run analyze:bundle
# Abrir bundle-stats.html no navegador

# 4. Verificar acessibilidade
npm run test:a11y

# 5. Testes visuais
npm run test:visual

# 6. Lighthouse CI
npm run audit:lighthouse
```

---

## Histórico de Issues

| Issue | Severidade | Status | Data |
|-------|------------|--------|------|
| text-slate-400 contraste baixo | Média | Aberto | 2026-06-11 |
| Provider filter grow | Baixa | Aberto | 2026-06-11 |
| Gráfico tooltip em mobile | Média | Aberto | 2026-06-11 |

---

## Critérios de Aprovação

Para que a auditoria seja considerada completa:

1. ✅ Todos os checkpoints marcados
2. ✅ Lighthouse score > 90 em Performance, Accessibility, Best Practices
3. ✅ Bundle < targets definidos
4. ✅ Zero erros de console em mobile
5. ✅ Navegação por teclado funcional