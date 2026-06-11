# CLAUDE.md - CauSium Engineering Guidelines

**Versão:** 1.0.0  
**Data:** 2026-06-11  
**Status:** Obrigatório para todos os ambientes  

---

## ⚠️ PRODUÇÃO É SAGRADA

O dashboard do cliente NUNCA pode ser derrubado por mudanças de desenvolvimento.

### Regras de Ouro

1. **Produção nunca é ambiente de teste**
2. **Toda alteração deve seguir o fluxo obrigatório**
3. **É proibido executar migrations automaticamente no startup**
4. **Nenhum deploy pode ocorrer sem validação local**

---

## Fluxo Obrigatório de Alterações

Para qualquer solicitação, siga exatamente esta sequência:

```
DIAGNÓSTICO
    ↓
PLANO
    ↓
DIFF
    ↓
TESTE LOCAL
    ↓
VALIDAÇÃO
    ↓
APROVAÇÃO
    ↓
COMMIT
    ↓
DEPLOY
```

### Antes de qualquer alteração, apresente:

- **Diagnóstico:** Causa raiz, impacto, arquivos afetados
- **Plano:** Exatamente o que será alterado, riscos, dependências
- **Diff:** Alterações propostas antes de executar
- **Impacto:** O que pode quebrar
- **Riscos:** O que pode dar errado

Se alguma etapa não puder ser executada, **pare e explique o motivo**.

---

## Regras de Database

### Antes de qualquer migration

```bash
# 1. Verificar estado atual
alembic current

# 2. Verificar heads
alembic heads

# 3. Verificar branches
alembic branches
```

### Se existir múltiplas heads

- **PARAR IMEDIATAMENTE**
- **NÃO executar upgrade**
- Documentar e resolver antes de continuar

### Durante migrations

- Toda mudança deve possuir **rollback documentado**
- Nunca assumir que migrations estão corretas
- Verificar merge points antes de executar

---

## Regras de Deploy

### Checklist Obrigatório (antes de qualquer deploy)

- [ ] Build OK
- [ ] Testes OK
- [ ] Banco validado
- [ ] Rollback definido
- [ ] Healthcheck validado
- [ ] APIs validadas
- [ ] Dashboard validado

### Após deploy, validar OBRIGATORIAMENTE

- [ ] Login
- [ ] Dashboard
- [ ] Spend Analysis
- [ ] Spend Stability
- [ ] Spend by SKU
- [ ] Savings Opportunities
- [ ] Health Check (`/health`)

---

## Regras de Produção

### NUNCA FAZER

- ❌ Deploy sem validação local
- ❌ Alterar banco de produção diretamente
- ❌ Executar migrations automaticamente em startup
- ❌ Executar comandos destrutivos
- ❌ Apagar tabelas
- ❌ Alterar schemas sem aprovação
- ❌ Fazer hotfix sem explicar o risco

---

## Incidentes Registrados

### 2026-06-11 - Dashboard Indisponível

| Item | Descrição |
|------|-----------|
| **Problema** | Dashboard do cliente indisponível |
| **Causa** | `alembic upgrade head` no startup falhou |
| **Root Cause** | Múltiplas heads no Alembic (0025_merge_workspace_lifecycle não resolve) |
| **Impacto** | Backend não iniciou, aplicação fora do ar por horas |
| **Resolução** | Entrypoint desabilitou migrations |

**Lição aprendida:** Migrations automáticas em produção são proibidas.

---

## Estrutura de Diretórios

```
CauSium/
├── CLAUDE.md              ← Este arquivo (regras de engenharia)
├── CONTRIBUTING.md         ← Regras para contribuidores
├── README.md              ← Documentação principal
├── docs/
│   ├── architecture/
│   │   └── engineering-policy.md  ← Políticas detalhadas
│   ├── runbooks/
│   │   ├── deployment-checklist.md  ← Checklist de deploy
│   │   └── backup-restore.md        ← Backup e restore
│   └── incidents/
│       └── 2026-06-11-dashboard-outage.md  ← Registro do incidente
```

---

## Comandos Úteis

```bash
# Verificar estado do Alembic
cd backend && alembic current && alembic heads && alembic branches

# Testar healthcheck
curl https://causium-api-2026.azurewebsites.net/health

# Ver logs do Azure
az webapp log download --resource-group rg-causium-staging-01 --name causium-api-2026
```

---

## Contato

Para dúvidas sobre as regras, consulte a documentação em `docs/architecture/engineering-policy.md`.