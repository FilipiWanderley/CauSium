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

# REGRA 9 - STAGING OBRIGATÓRIO

## Mudanças que impactam áreas críticas devem passar por Staging

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
Desenvolvimento Local
    ↓
Testes Locais
    ↓
Staging
    ↓
Validação
    ↓
Aprovação
    ↓
Produção
```

**Produção nunca deve ser o primeiro ambiente a receber alterações críticas.**

### Validação em Staging

```bash
# 1. Deploy para staging
az webapp deployment slot swap --resource-group rg-causium-staging-01 --name causium-api-2026 --slot staging --action swap

# 2. Validar em staging
curl -s https://causium-api-2026-staging.azurewebsites.net/health

# 3. Testar funcionalidades críticas
# - Login
# - Dashboard
# - APIs
# - Ledger
# - Ingestion

# 4. Somente após validação → produção
```

---

# REGRA 10 - INCIDENTES E PÓS-MORTEM

## Todo incidente de produção deve gerar documentação completa

### 6 itens obrigatórios

1. ✅ **Root Cause Analysis** - Identificar causa raiz
2. ✅ **Timeline do incidente** - Cronologia de eventos
3. ✅ **Impacto ao cliente** - O que foi afetado
4. ✅ **Ação corretiva** - Como foi resolvido
5. ✅ **Ação preventiva** - O que fazer para evitar
6. ✅ **Plano para evitar recorrência** - Medidas implementadas

### Estrutura do registro

```markdown
# Incidente: [Título]

**Data:** YYYY-MM-DD
**Severidade:** Alta/Média/Baixa
**Status:** Resolvido/Pendente

## Timeline
- HH:MM - Evento

## Root Cause
- Causa raiz identificada

## Impacto
- O que foi afetado

## Ação Corretiva
- Como foi resolvido

## Ação Preventiva
- O que fazer para evitar

## Plano
- Medidas implementadas
```

### Local de registro

```
docs/incidents/YYYY-MM-DD-descricao.md
```

---

# REGRA 11 - PROTEÇÃO DE PRODUÇÃO

## Antes de qualquer deploy em produção, validar

### Checklist de proteção

| Validação | Comando |
|-----------|---------|
| Health Check OK | `curl /health` |
| Banco acessível | `alembic current` |
| APIs funcionando | `curl /api/v1/health` |
| Login funcionando | Teste manual |
| Dashboard funcionando | Teste manual |
| Rollback disponível | `git log --oneline -3` |

### Se qualquer validação falhar

**🚨 PARAR O DEPLOY**

```bash
# Health check
curl -s https://causium-api-2026.azurewebsites.net/health

# Verificar banco
cd backend && alembic current

# APIs
curl -s https://causium-api-2026.azurewebsites.net/api/v1/health

# Verificar rollback
git log --oneline -3

# Verificar logs
az webapp log tail --resource-group rg-causium-staging-01 --name causium-api-2026
```

---

# REGRA 12 - MUDANÇAS DE ALTO RISCO

## Mudanças envolvendo áreas de risco alto

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

1. ✅ **Diagnóstico** - Causa raiz e problema
2. ✅ **Plano** - O que será alterado
3. ✅ **Diff** - Alterações específicas
4. ✅ **Impacto** - O que pode quebrar
5. ✅ **Riscos** - O que pode dar errado
6. ✅ **Rollback** - Como reverter
7. ✅ **Evidências dos testes** - Testes passaram localmente

### Template para mudanças de alto risco

```markdown
## Mudança de Alto Risco - [Título]

### 1. Diagnóstico
- Problema:
- Causa raiz:
- Impacto:

### 2. Plano
- O que será alterado:
- Como será feito:

### 3. Diff
\`\`\`diff
# mostrar alterações
\`\`\`

### 4. Impacto
- Funcionalidades afetadas:
- Usuários impactados:

### 5. Riscos
- O que pode dar errado:
- Probabilidade:
- Impacto:

### 6. Rollback
- Commit de retorno:
- Passos:

### 7. Evidências dos Testes
- [x] Testes unitários passando
- [x] Testes de integração passando
- [x] Validação manual concluída
```

---

# TASK TÉCNICA - ALEMBIC MÚLTIPLAS HEADS

## Objetivo

Resolver múltiplas heads do Alembic para permitir migrations normais.

## Passos planejados (NÃO EXECUTAR AINDA)

1. **Identificar heads existentes**
   ```bash
   cd backend && alembic heads
   cd backend && alembic branches
   ```

2. **Criar merge migration correta**
   ```bash
   cd backend && alembic merge -m "merge branches"
   ```

3. **Validar upgrade local**
   ```bash
   cd backend && alembic upgrade head
   ```

4. **Validar downgrade local**
   ```bash
   cd backend && alembic downgrade -1
   cd backend && alembic upgrade head
   ```

5. **Executar testes**
   ```bash
   cd backend && pytest
   ```

6. **Documentar rollback**
   ```markdown
   ## Rollback
   - Commit: xxxxxxx
   - Passos: ...
   ```

7. **Somente após aprovação considerar reabilitar migrations**

## ⚠️ IMPORTANTE

**NÃO executar nenhuma ação em produção relacionada ao Alembic.**

**Apenas documentar e criar a task técnica.**

---

# REFERÊNCIAS

| Documento | Descrição |
|-----------|-----------|
| `CLAUDE.md` | Regras de engenharia resumidas |
| `CONTRIBUTING.md` | Guia para contribuidores |
| `docs/runbooks/deployment-checklist.md` | Checklist de deploy |
| `docs/runbooks/backup-restore.md` | Backup e restore |
| `docs/incidents/2026-06-11-dashboard-outage.md` | Registro do incidente |