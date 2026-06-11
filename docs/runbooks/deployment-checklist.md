# Deployment Checklist - CauSium

**Versão:** 1.0.0  
**Data:** 2026-06-11  
**Status:** Obrigatório para todo deploy  

---

## Pré-Deploy

### 1. Código

- [ ] `git status` - ver estado do repositório
- [ ] `git log --oneline -5` - ver últimos commits
- [ ] `git diff` - ver alterações pendentes

### 2. Build Local

- [ ] `cd backend && poetry install` - instalar dependências
- [ ] `cd backend && python -m pytest` - testes passando
- [ ] `cd backend && python -c "from app.main import app"` - app importa corretamente

### 3. Alembic (se houver mudanças de banco)

```bash
cd backend
alembic current
alembic heads
alembic branches
```

**ATENÇÃO:** Se existirem múltiplas heads, **NÃO CONTINUAR**.

### 4. Frontend (se aplicável)

```bash
cd frontend
npm run build
```

---

## Deploy via GitHub Actions

O deploy é feito automaticamente via GitHub Actions quando há push para `main`.

### Verificar Status

```bash
gh run list --workflow="Build and deploy Python app to Azure Web App - causium-api-2026" --limit 3
```

### Esperar Conclusão

Aguardar jobs:
- [ ] build
- [ ] deploy

---

## Pós-Deploy

### 1. Health Check

```bash
curl https://causium-api-2026-fea3frguggasbcg3.brazilsouth-01.azurewebsites.net/health
```

Resposta esperada:
```json
{"status":"ok","version":"0.1.0"}
```

### 2. APIs Validations

Testar os endpoints principais:

- [ ] `GET /api/v1/ledger/dashboard` - Dashboard (requer auth)
- [ ] `GET /api/v1/health` - Health detalhado

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

Verificar logs do Azure:

```bash
az webapp log download --resource-group rg-causium-staging-01 --name causium-api-2026 --log-file ./logs.zip
```

---

## Rollback

### Se algo der errado

1. **Identificar a versão anterior**

```bash
gh run list --workflow="Build and deploy Python app to Azure Web App - causium-api-2026" --limit 10
```

2. **Reverter o commit problemático**

```bash
git revert <commit-sha>
git push origin main
```

3. **Aguardar novo deploy**

4. **Validar que voltou ao normal**

### Alternativa: Rollback via Azure Portal

1. Azure Portal → App Service → Deployment Center
2. Selecionar versão anterior
3. Deploy

---

## Checklist Final

- [ ] Health check OK
- [ ] Login funcionando
- [ ] Dashboard carregando
- [ ] Sem erros nos logs
- [ ] Cliente notificado (se aplicável)

---

## Contatos de Emergência

| Papel | Contato |
|-------|---------|
| Dev Lead | Via Teams |
| DevOps | Via Teams |
| Cliente | Via email/phone |

---

## Referências

- `docs/architecture/engineering-policy.md` - Políticas de engenharia
- `docs/runbooks/backup-restore.md` - Backup e restore
- `docs/incidents/` - Registro de incidentes