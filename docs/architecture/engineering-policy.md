# Engineering Policy - CauSium

**Versão:** 2.0.0  
**Data:** 2026-06-11  
**Status:** OBRIGATÓRIO para todos os ambientes  

---

## PRIORIDADE MÁXIMA

| Prioridade | Descrição |
|------------|-----------|
| **1º** | Disponibilidade do dashboard |
| **2º** | Integridade dos dados |
| **3º** | Segurança do ambiente |
| **4º** | Estabilidade do cliente |

> **Nenhuma funcionalidade nova vale mais que a estabilidade da produção.**

---

# REGRAS DE ENGENHARIA

## REGRA 1 - PRODUÇÃO É SAGRADA

O Dashboard do cliente é o **ativo mais importante** do sistema.

- ✅ Nenhuma alteração pode colocar produção em risco
- ✅ Produção NÃO é ambiente de testes
- ✅ Produção apenas recebe código já validado localmente

### Proibido em produção:

- ❌ Deploy apenas para "testar"
- ❌ Assumir que funciona sem evidência
- ❌ Alterar produção diretamente
- ❌ Executar migrations automaticamente
- ❌ Alterar banco em produção sem validação local

---

## REGRA 2 - FLUXO OBRIGATÓRIO DE QUALQUER ALTERAÇÃO

Antes de qualquer modificação, seguir **exatamente**:

```
1. DIAGNÓSTICO COMPLETO
    ↓
2. Explicar causa raiz
    ↓
3. APRESENTAR PLANO DE EXECUÇÃO
    ↓
4. Listar arquivos afetados
    ↓
5. MOSTRAR DIFF
    ↓
6. Explicar riscos
    ↓
7. Explicar rollback
    ↓
8. EXECUTAR TESTES LOCAIS
    ↓
9. APRESENTAR RESULTADO DOS TESTES
    ↓
10. AGUARDAR APROVAÇÃO EXPLÍCITA
    ↓
11. Commit
    ↓
12. Deploy
```

**Nenhuma exceção.**

### Template de Diagnóstico

```markdown
## Diagnóstico

### Problema
- Descrição clara do problema
- Quando ocorreu
- Quem foi afetado

### Causa Raiz
- O que causou o problema
- Por que aconteceu
- Como foi identificado

### Arquivos Afetados
- Lista de arquivos que precisam mudar

### Impacto
- O que pode quebrar
- Quais funcionalidades são afetadas
- Severidade do impacto

## Plano

### Solução Proposta
- O que será alterado
- Como será feito

### Riscos
- O que pode dar errado
- Probabilidade de ocorrência
- Impacto se falhar

### Rollback
- Como reverter
- Commit de retorno
- Passos documentados
```

---

## REGRA 3 - BANCO DE DADOS

### É PROIBIDO executar em produção:

| Comando | Proibido |
|---------|----------|
| migrations | ❌ |
| alter table | ❌ |
| drop table | ❌ |
| truncate | ❌ |
| delete em massa | ❌ |
| update em massa | ❌ |
| mudanças de schema | ❌ |

### Sem todos estes itens:

1. ✅ **Backup validado** - backup recente foi restaurado e verificado
2. ✅ **Teste local executado** - testes passaram localmente
3. ✅ **Plano de rollback documentado** - rollback está escrito e testado
4. ✅ **Aprovação explícita** - usuário aprovou formalmente

**Se houver dúvida: NÃO EXECUTAR.**

### Checklist de Segurança para Banco

```bash
# 1. Backup
make backup

# 2. Verificar backup
make restore BACKUP=backups/YYYY-MM-DD_HHMMSS --dry-run

# 3. Testar localmente
cd backend && pytest

# 4. Documentar rollback
# - Identificar commit de retorno
# - Listar passos para reversão
# - Identificar quem pode executar
```

---

## REGRA 4 - ALEMBIC

### Antes de qualquer migration, executar:

```bash
cd backend
alembic current
alembic heads
alembic branches
alembic history --verbose
```

### Se existir mais de uma head:

**🚨 PARAR IMEDIATAMENTE**

**NÃO executar:**

```bash
alembic upgrade head
alembic upgrade heads
```

até que:
1. O problema seja identificado localmente
2. A solução seja implementada
3. Testes locais passem
4. Aprovação seja obtida

### Fluxo de Resolução de Múltiplas Heads

```
1. Identificar branches com: alembic branches
2. Identificar merge points: alembic history --verbose
3. Criar merge migration: alembic merge -m "merge branches"
4. Testar localmente: alembic upgrade head
5. Validar banco: alembic current
6. Commit e push
7. Deploy via CI/CD
```

---

## REGRA 5 - ÁREAS CRÍTICAS

Se a alteração impactar qualquer uma destas áreas:

| Área | Impacto |
|------|---------|
| **Login** | Autenticação de usuários |
| **Autenticação** | Sistema de login |
| **Dashboard** | Visibilidade de custos do cliente |
| **APIs** | Comunicação com cliente |
| **FinOps** | Recomendações de otimização |
| **Ledger** | Dados financeiros |
| **Advisor** | Sistema de recomendações |
| **Billing** | Sistema de cobrança |
| **Ingestion** | Ingestão de dados de custos |
| **Workers** | Processamento em background |
| **Banco de Dados** | Persistência de dados |

### O Claude deve apresentar **obrigatoriamente**:

1. ✅ **Diagnóstico** - Causa raiz e impacto
2. ✅ **Plano** - O que será alterado
3. ✅ **Diff** - Alterações específicas
4. ✅ **Impacto** - O que pode quebrar
5. ✅ **Riscos** - O que pode dar errado
6. ✅ **Rollback** - Como reverter

**antes de alterar qualquer arquivo.**

---

## REGRA 6 - TESTES

### Nenhum deploy pode ocorrer sem validação local.

#### Obrigatório para todo deploy:

- ✅ Testes unitários passando
- ✅ Testes de integração (quando aplicável)
- ✅ Validação manual da funcionalidade alterada

#### Checklist de Testes

```bash
# 1. Backend - Testes unitários
cd backend && pytest -v

# 2. Backend - Testes de integração
cd backend && pytest tests/integration/ -v

# 3. Backend - Build validation
cd backend && python -c "from app.main import app"

# 4. Backend - Type check
cd backend && mypy app/

# 5. Frontend - Testes
cd frontend && npm test

# 6. Frontend - Build
cd frontend && npm run build

# 7. Health check
curl -s https://causium-api-2026.azurewebsites.net/health
```

**Deploy não pode ser usado como teste.**

---

## REGRA 7 - ROLLBACK

### Toda alteração deve possuir:

- ✅ **Estratégia de rollback documentada**
- ✅ **Commit de retorno identificado**
- ✅ **Passos documentados para reversão**

#### Template de Rollback

```markdown
## Rollback

### Estratégia
- Descrição da estratégia de rollback

### Commit de Retorno
- SHA do commit anterior: xxxxxxx
- Tag se aplicável: v1.2.3

### Passos para Reversão

1. `git revert <sha>`
2. `git push origin main`
3. Aguardar GitHub Actions
4. Validar health check

### Validação
- Health check retorna OK
- Dashboard carrega
- APIs respondem

### Responsável
- Nome do responsável pelo rollback
```

---

## REGRA 8 - INCIDENTE DE 11/06/2026

### Registrar como lição permanente do projeto:

| Item | Descrição |
|------|-----------|
| **Data** | 2026-06-11 |
| **Incidente** | Dashboard indisponível |
| **Duração** | ~8 horas |
| **Causa** | Execução automática de Alembic no startup |
| **Root Cause** | Múltiplas heads no Alembic |
| **Ação Corretiva** | Remoção da execução automática de migrations do entrypoint |
| **Lição** | Migrations nunca devem ser executadas automaticamente em produção sem validação prévia |

### Evidências do Incidente

```
Site's appCommandLine: startup.sh
Launching oryx with: create-script -appPath /home/site/wwwroot -output /opt/startup/startup.sh
Writing output script to '/opt/startup/startup.sh'
[startup] PostgreSQL mode — running alembic upgrade head...
ERROR [alembic.util.messaging] Multiple head revisions are present for given argument 'head'
```

### Prevenção Implementada

1. ✅ Entrypoint desabilitou migrations
2. ✅ Políticas de engenharia documentadas
3. ✅ Checklist de deploy criado
4. ✅ Incidente registrado como lição aprendida

---

# CHECKLIST PRÉ-DEPLOY

## Obrigatório antes de qualquer deploy

- [ ] Diagnóstico completo apresentado
- [ ] Plano aprovado
- [ ] Diff mostrado e aprovado
- [ ] Testes locais passando
- [ ] Rollback documentado
- [ ] Aprovação explícita obtida

---

# CHECKLIST PÓS-DEPLOY

## Obrigatório após qualquer deploy

- [ ] Health check: `GET /health` retorna `{"status":"ok"}`
- [ ] Login funciona
- [ ] Dashboard carrega
- [ ] Spend Analysis funciona
- [ ] Spend Stability funciona
- [ ] Spend by SKU funciona
- [ ] Savings Opportunities funciona
- [ ] Sem erros nos logs

---

# REFERÊNCIAS

| Documento | Descrição |
|-----------|-----------|
| `CLAUDE.md` | Regras de engenharia resumidas |
| `CONTRIBUTING.md` | Guia para contribuidores |
| `docs/runbooks/deployment-checklist.md` | Checklist de deploy |
| `docs/runbooks/backup-restore.md` | Backup e restore |
| `docs/incidents/2026-06-11-dashboard-outage.md` | Registro do incidente |