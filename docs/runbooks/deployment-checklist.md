# Deployment Checklist - CauSium

**Versão:** 2.0.0  
**Data:** 2026-06-11  
**Status:** OBRIGATÓRIO para todo deploy  

---

## ⚠️ REGRAS FUNDAMENTAIS

### Antes de qualquer deploy:

1. ✅ Diagnóstico completo
2. ✅ Plano aprovado
3. ✅ Diff mostrado e aprovado
4. ✅ Testes locais passando
5. ✅ Rollback documentado
6. ✅ Aprovação explícita obtida

### NUNCA fazer:

- ❌ Deploy apenas para "testar"
- ❌ Assumir que funciona sem evidência
- ❌ Alterar produção diretamente
- ❌ Executar migrations automaticamente
- ❌ Alterar banco em produção sem validação local

---

## PRÉ-DEPLOY

### 1. Código

```bash
# Ver estado do repositório
git status

# Ver últimos commits
git log --oneline -5

# Ver alterações pendentes
git diff

# Ver arquivos alterados
git diff --stat
```

### 2. Alembic (se houver mudanças de banco)

```bash
cd backend

# Verificar estado atual
alembic current

# Verificar heads
alembic heads

# Verificar branches
alembic branches

# Verificar history detalhado
alembic history --verbose
```

**⚠️ SE EXISTIREM MÚLTIPLAS HEADS: PARAR IMEDIATAMENTE**

```bash
# Se output mostrar mais de uma head:
# alembic heads
#  0044 (head)
#   ??? (head)<-- PROBLEMA!

# NÃO CONTINUAR
# Resolver múltiplas heads primeiro
```

### 3. Testes Locais

```bash
# Backend - Testes unitários
cd backend && pytest -v

# Backend - Type check
cd backend && mypy app/

# Backend - Build validation
cd backend && python -c "from app.main import app"

# Frontend - Testes
cd frontend && npm test

# Frontend - Build
cd frontend && npm run build
```

### 4. Backup (se alteração de banco)

```bash
# Fazer backup
make backup

# Verificar backup
ls -la backups/

# Documentar backup disponível
# Backup: backups/YYYY-MM-DD_HHMMSS
```

### 5. Rollback Documentado

```markdown
## Rollback

### Estratégia
- Descrição da estratégia de rollback

### Commit de Retorno
- SHA: xxxxxxx

### Passos
1. git revert <sha>
2. git push origin main
3. Aguardar GitHub Actions
4. Validar health check
```

---

## DEPLOY VIA GITHUB ACTIONS

O deploy é feito automaticamente via GitHub Actions quando há push para `main`.

### Verificar Status

```bash
gh run list --workflow="Build and deploy Python app to Azure Web App - causium-api-2026" --limit 3
```

### Esperar Conclusão

Aguardar jobs:
- [ ] build - OK
- [ ] deploy - OK

---

## PÓS-DEPLOY

### 1. Health Check

```bash
curl -s https://causium-api-2026-fea3frguggasbcg3.brazilsouth-01.azurewebsites.net/health
```

**Resposta esperada:**
```json
{"status":"ok","version":"0.1.0"}
```

### 2. APIs Validations

```bash
# Health detalhado
curl -s https://causium-api-2026.azurewebsites.net/api/v1/health

# Dashboard (requer auth)
curl -s https://causium-api-2026.azurewebsites.net/api/v1/ledger/dashboard
```

### 3. Dashboard Web

Abrir no navegador:
- [ ] https://app.causiumtech.com
- [ ] Login funciona
- [ ] Dashboard carrega
- [ ] Spend Analysis carrega
- [ ] Spend Stability carrega
- [ ] Spend by SKU carrega
- [ ] Savings Opportunities carrega

### 4. Logs

```bash
# Download de logs
az webapp log download --resource-group rg-causium-staging-01 --name causium-api-2026 --log-file ./logs.zip

# Verificar logs em tempo real
az webapp log tail --resource-group rg-causium-staging-01 --name causium-api-2026
```

### 5. Validação de Áreas Críticas

Se a alteração impactou alguma destas áreas, validar especificamente:

| Área | Como Validar |
|------|--------------|
| Login | Fazer login com usuário de teste |
| Dashboard | Verificar KPIs carregando |
| APIs | Testar endpoints principais |
| Ledger | Verificar dados financeiros |
| Ingestion | Verificar worker processando |
| Workers | Verificar logs de workers |

---

## ROLLBACK

### Se algo der errado

#### 1. Identificar a versão anterior

```bash
gh run list --workflow="Build and deploy Python app to Azure Web App - causium-api-2026" --limit 10
```

#### 2. Reverter o commit problemático

```bash
git revert <commit-sha>
git push origin main
```

#### 3. Aguardar novo deploy

```bash
gh run list --workflow="Build and deploy Python app to Azure Web App - causium-api-2026" --limit 3
```

#### 4. Validar que voltou ao normal

```bash
# Health check
curl -s https://causium-api-2026.azurewebsites.net/health

# Dashboard
# Abrir https://app.causiumtech.com
```

### Alternativa: Rollback via Azure Portal

1. Azure Portal → App Service → Deployment Center
2. Selecionar versão anterior
3. Deploy

---

## CHECKLIST FINAL

### Pré-Deploy

- [ ] `git status` - ver estado do repositório
- [ ] `git diff` - ver alterações pendentes
- [ ] `alembic current` - verificar estado do banco
- [ ] `alembic heads` - verificar heads (deve ser 1)
- [ ] `pytest` - testes passando
- [ ] `mypy app/` - type check passando
- [ ] Build succeeds
- [ ] Rollback documentado
- [ ] Aprovação obtida

### Pós-Deploy

- [ ] Health check OK
- [ ] Login funcionando
- [ ] Dashboard carregando
- [ ] APIs respondendo
- [ ] Sem erros nos logs
- [ ] Cliente notificado (se aplicável)

---

## REGRA 8 - INCIDENTE DE 11/06/2026

### Lição aprendida:

| Item | Descrição |
|------|-----------|
| **Problema** | Dashboard indisponível |
| **Causa** | `alembic upgrade head` no startup |
| **Root Cause** | Múltiplas heads no Alembic |
| **Lição** | Migrations nunca devem ser executadas automaticamente em produção |

### Prevenção:

- ✅ Migrations no startup: **PROIBIDAS**
- ✅ Verificar Alembic antes de deploy: **OBRIGATÓRIO**
- ✅ Testes locais: **OBRIGATÓRIO**
- ✅ Aprovação explícita: **OBRIGATÓRIO**

---

## CONTATOS DE EMERGÊNCIA

| Papel | Contato |
|-------|---------|
| Dev Lead | Via Teams |
| DevOps | Via Teams |
| Cliente | Via email/phone |

---

## REFERÊNCIAS

- `CLAUDE.md` - Regras de engenharia
- `docs/architecture/engineering-policy.md` - Políticas detalhadas
- `docs/runbooks/backup-restore.md` - Backup e restore
- `docs/incidents/2026-06-11-dashboard-outage.md` - Registro do incidente