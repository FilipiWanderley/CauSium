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

## SWA PREVIEW (FRONTEND ONLY) — Feature `feature/staging-pipeline`

A partir de 2026-06-12, o workflow `deploy-frontend-swa.yml` foi estendido para
gerar **URLs de preview por Pull Request** no Azure Static Web Apps, sem custo
adicional de infra.

### O que isso faz

- Cada PR aberto contra `main` dispara o workflow de deploy do frontend.
- O SWA gera uma **URL de preview única** (anônima ou com auth, conforme config
  do SWA) com o build do branch.
- O comentário do bot no PR inclui a URL de preview.

### O que isso **NÃO** faz (limites)

- ❌ **Não valida backend.** O preview é só frontend estático (HTML/CSS/JS).
  Chamadas para `/api/v1/...` no preview **falham** porque não há staging
  backend deployado.
- ❌ **Não substitui staging real.** Esta é uma medida de validação visual/
  frontend apenas.
- ❌ **Não muda o fluxo de deploy em produção.** Merge em `main` continua
  deployando o frontend no SWA de produção, e o backend no App Service de
  produção, sem gate de aprovação.
- ❌ **Não protege contra deploy direto em produção.** Para isso, é preciso
  branch protection em `main` + GitHub environment `production` com required
  reviewers — trabalho de sprint futura (escopo desta branch é só o preview).

### Quando usar

- Para revisar **HTML/CSS/i18n strings** de um PR antes de mergear.
- Para validar **layout responsivo** sem subir backend.
- Para smoke visual rápido de uma feature UI-only.

### Quando **NÃO** usar como substituto

- Validação de fluxos que dependem de API (`/gov`, `/ledger`, `/auth`, etc.).
- Validação de novos endpoints ou mudanças de backend.
- Validação fim-a-fim de feature completa.
- Decisão de merge em `main`. **Merge em `main` continua exigindo staging
  backend real + gate manual, não implementado nesta branch.**

### Como abrir um PR para testar

1. Crie uma branch de feature.
2. Faça push.
3. Abra PR contra `main`.
4. Aguarde o workflow `Deploy Frontend – Azure Static Web Apps` rodar.
5. O bot do SWA comenta no PR com a URL de preview.
6. Abra a URL e valide.

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

## REGRA 9 - STAGING OBRIGATÓRIO

### Áreas que requerem validação em Staging

| Área | Requer Staging |
|------|----------------|
| Banco de Dados | ✅ |
| Autenticação | ✅ |
| Login | ✅ |
| Dashboard | ✅ |
| APIs Públicas | ✅ |
| FinOps | ✅ |
| Billing | ✅ |
| Ledger | ✅ |
| Advisor | ✅ |
| Workers | ✅ |
| Ingestion | ✅ |
| Segurança | ✅ |

### Fluxo obrigatório

```
Desenvolvimento Local → Testes Locais → Staging → Validação → Aprovação → Produção
```

---

## REGRA 10 - INCIDENTES E PÓS-MORTEM

### Todo incidente deve gerar documentação

1. ✅ Root Cause Analysis
2. ✅ Timeline do incidente
3. ✅ Impacto ao cliente
4. ✅ Ação corretiva
5. ✅ Ação preventiva
6. ✅ Plano para evitar recorrência

### Registro em: `docs/incidents/YYYY-MM-DD-descricao.md`

---

## REGRA 11 - PROTEÇÃO DE PRODUÇÃO

### Validações obrigatórias antes do deploy

| Validação | Status |
|-----------|--------|
| Health Check OK | ⬜ |
| Banco acessível | ⬜ |
| APIs funcionando | ⬜ |
| Login funcionando | ⬜ |
| Dashboard funcionando | ⬜ |
| Rollback disponível | ⬜ |

**Se qualquer validação falhar: PARAR O DEPLOY**

---

## REGRA 12 - MUDANÇAS DE ALTO RISCO

### Áreas de alto risco

| Área | Risco |
|------|-------|
| Alembic |可能导致停机 |
| Banco de dados | 数据丢失风险 |
| Autenticação | 影响用户访问 |
| Infraestrutura | 影响系统稳定性 |
| Deploy | 影响生产环境 |
| Billing | 影响计费系统 |

### 7 itens obrigatórios

1. Diagnóstico
2. Plano
3. Diff
4. Impacto
5. Riscos
6. Rollback
7. Evidências dos testes

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
- `docs/technical-tasks/alembic-multiple-heads.md` - Task técnica Alembic