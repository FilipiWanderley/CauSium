# CLAUDE.md - CauSium Engineering Guidelines

**Versão:** 2.0.0  
**Data:** 2026-06-11  
**Status:** Obrigatório para TODOS os ambientes  

---

## ⚠️ PRODUÇÃO É SAGRADA

O Dashboard do cliente é o **ativo mais importante** do sistema.

### Regras de Ouro

| Regra | Descrição |
|-------|-----------|
| **Produção é sagrada** | O Dashboard do cliente NUNCA pode ser derrubado |
| **Zero tolerance** | Nenhuma alteração pode colocar produção em risco |
| **Produção não é teste** | Produção NÃO é ambiente de testes |
| **Código validado** | Produção apenas recebe código já validado localmente |

---

## REGRA 1 - PRODUÇÃO É SAGRADA

O Dashboard do cliente é o ativo mais importante do sistema.

- Nenhuma alteração pode colocar produção em risco
- Produção NÃO é ambiente de testes
- Produção só recebe código já validado localmente

---

## REGRA 2 - FLUXO OBRIGATÓRIO DE QUALQUER ALTERAÇÃO

Antes de qualquer modificação, seguir **exatamente**:

```
1. DIAGNÓSTICO COMPLETO
2. Explicar causa raiz
3. APRESENTAR PLANO DE EXECUÇÃO
4. Listar arquivos afetados
5. MOSTRAR DIFF
6. Explicar riscos
7. Explicar rollback
8. EXECUTAR TESTES LOCAIS
9. APRESENTAR RESULTADO DOS TESTES
10. AGUARDAR APROVAÇÃO EXPLÍCITA
11. Commit
12. Deploy
```

**Nenhuma exceção.**

---

## REGRA 3 - BANCO DE DADOS

### É PROIBIDO executar em produção:

- ❌ migrations
- ❌ alter table
- ❌ drop table
- ❌ truncate
- ❌ delete em massa
- ❌ update em massa
- ❌ mudanças de schema

### Sem:

1. ✅ Backup validado
2. ✅ Teste local executado
3. ✅ Plano de rollback documentado
4. ✅ Aprovação explícita

**Se houver dúvida: NÃO EXECUTAR.**

---

## REGRA 4 - ALEMBIC

### Antes de qualquer migration, executar:

```bash
alembic heads
alembic branches
alembic current
```

### Se existir mais de uma head:

**PARAR IMEDIATAMENTE**

**NÃO executar:**

```bash
alembic upgrade head
```

até que o problema seja resolvido localmente.

---

## REGRA 5 - ÁREAS CRÍTICAS

Se a alteração impactar qualquer uma destas áreas:

| Área | Impacto |
|------|---------|
| Login | Autenticação de usuários |
| Dashboard | Visibilidade de custos |
| APIs | Comunicação cliente |
| FinOps | Recomendações de otimização |
| Ledger | Dados financeiros |
| Advisor | Recomendações |
| Billing | Cobrança |
| Ingestion | Dados进来的 |
| Workers | Processamento em background |
| Banco de Dados | Persistência |

**O Claude deve apresentar obrigatoriamente:**

1. Diagnóstico
2. Plano
3. Diff
4. Impacto
5. Riscos
6. Rollback

**antes de alterar qualquer arquivo.**

---

## REGRA 6 - TESTES

### Nenhum deploy pode ocorrer sem validação local.

#### Obrigatório:

- ✅ Testes unitários passando
- ✅ Testes de integração (quando aplicável)
- ✅ Validação manual da funcionalidade alterada

**Deploy não pode ser usado como teste.**

---

## REGRA 7 - ROLLBACK

### Toda alteração deve possuir:

- ✅ Estratégia de rollback documentada
- ✅ Commit de retorno identificado
- ✅ Passos documentados para reversão

---

## REGRA 8 - INCIDENTE DE 11/06/2026

### Registrar como lição permanente do projeto:

| Item | Descrição |
|------|-----------|
| **Incidente** | Dashboard indisponível devido a execução automática de Alembic no startup |
| **Root Cause** | Múltiplas heads no Alembic |
| **Ação Corretiva** | Remoção da execução automática de migrations do entrypoint |
| **Lição** | Migrations nunca devem ser executadas automaticamente em produção sem validação prévia |

---

## OBJETIVO FINAL

### Prioridade máxima:

1. ✅ **Disponibilidade do dashboard** - MÁXIMA PRIORIDADE
2. ✅ **Integridade dos dados** - Dados nunca devem ser perdidos
3. ✅ **Segurança do ambiente** - Ambientes devem estar protegidos
4. ✅ **Estabilidade do cliente** - Cliente deve poder confiar no sistema

> **Nenhuma funcionalidade nova vale mais que a estabilidade da produção.**

---

## Fluxo Detalhado de Alterações

### 1. Diagnóstico

```markdown
### Problema Identificado
- Descrição clara do problema
- Causa raiz identificada
- Impacto no sistema

### Arquivos Afetados
- Lista de arquivos que precisam mudar
```

### 2. Plano

```markdown
### Solução Proposta
- O que será alterado
- Como será feito

### Riscos
- O que pode dar errado
- Impacto se algo falhar

### Rollback
- Como reverter se algo der errado
- Commit anterior identificável
```

### 3. Diff

```bash
git diff arquivo.py
```

### 4. Testes Locais

```bash
# Backend
cd backend && pytest

# Frontend  
cd frontend && npm test

# Build
cd backend && python -c "from app.main import app"
```

### 5. Validação

```bash
# Health check
curl https://causium-api-2026.azurewebsites.net/health

# Verificar logs
az webapp log download --resource-group rg-causium-staging-01 --name causium-api-2026
```

### 6. Aprovação

Aguardar confirmação explícita do usuário antes de fazer commit.

### 7. Commit

```bash
git add .
git commit -m "tipo(scope): descrição"
git push origin main
```

### 8. Deploy

Via GitHub Actions (automático após push para main).

---

## REGRA 9 - STAGING OBRIGATÓRIO

### Mudanças que impactam áreas críticas devem passar por Staging:

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

### Fluxo obrigatório:

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

### Checklist de Staging

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

# 4. Verificar logs
az webapp log tail --resource-group rg-causium-staging-01 --name causium-api-2026-staging

# 5. Somente após validação → produção
```

---

## REGRA 10 - INCIDENTES E PÓS-MORTEM

### Todo incidente de produção deve gerar documentação completa:

1. ✅ **Root Cause Analysis** - Identificar causa raiz
2. ✅ **Timeline do incidente** - Cronologia de eventos
3. ✅ **Impacto ao cliente** - O que foi afetado
4. ✅ **Ação corretiva** - Como foi resolvido
5. ✅ **Ação preventiva** - O que fazer para evitar
6. ✅ **Plano para evitar recorrência** - Medidas implementadas

### Estrutura do registro de incidente:

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

### Local de registro:

```
docs/incidents/YYYY-MM-DD-descricao.md
```

---

## REGRA 11 - PROTEÇÃO DE PRODUÇÃO

### Antes de qualquer deploy em produção, o sistema deve validar:

| Validação | Comando |
|-----------|---------|
| Health Check OK | `curl /health` |
| Banco acessível | `alembic current` |
| APIs funcionando | `curl /api/v1/health` |
| Login funcionando | Teste manual |
| Dashboard funcionando | Teste manual |
| Rollback disponível | `git log --oneline -3` |

### Se qualquer validação falhar:

**🚨 PARAR O DEPLOY**

### Checklist de Proteção

```bash
# 1. Health check
curl -s https://causium-api-2026.azurewebsites.net/health
# Esperado: {"status":"ok","version":"0.1.0"}

# 2. Verificar banco
cd backend && alembic current
# Esperado: version_num

# 3. APIs
curl -s https://causium-api-2026.azurewebsites.net/api/v1/health

# 4. Verificar rollback
git log --oneline -3
# Esperado: commit anterior identificável

# 5. Verificar logs
az webapp log tail --resource-group rg-causium-staging-01 --name causium-api-2026
```

---

## REGRA 12 - MUDANÇAS DE ALTO RISCO

### Mudanças envolvendo estas áreas requerem 7 itens obrigatórios:

| Área | Risco |
|------|-------|
| Alembic |可能导致停机 |
| Banco de dados | 数据丢失风险 |
| Autenticação | 影响用户访问 |
| Infraestrutura | 影响系统稳定性 |
| Deploy | 影响生产环境 |
| Billing | 影响计费系统 |

### 7 itens obrigatórios antes de qualquer execução:

1. ✅ **Diagnóstico** - Causa raiz e problema
2. ✅ **Plano** - O que será alterado
3. ✅ **Diff** - Alterações específicas
4. ✅ **Impacto** - O que pode quebrar
5. ✅ **Riscos** - O que pode dar errado
6. ✅ **Rollback** - Como reverter
7. ✅ **Evidências dos testes** - Testes passaram localmente

### Template para mudanças de alto risco:

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

## TASK TÉCNICA - ALEMBIC MÚLTIPLAS HEADS

### Objetivo

Resolver múltiplas heads do Alembic para permitir migrations normais.

### Passos planejados (NÃO EXECUTAR AINDA):

1. Identificar heads existentes
   ```bash
   cd backend && alembic heads
   cd backend && alembic branches
   ```

2. Criar merge migration correta
   ```bash
   cd backend && alembic merge -m "merge branches"
   ```

3. Validar upgrade local
   ```bash
   cd backend && alembic upgrade head
   ```

4. Validar downgrade local
   ```bash
   cd backend && alembic downgrade -1
   cd backend && alembic upgrade head
   ```

5. Executar testes
   ```bash
   cd backend && pytest
   ```

6. Documentar rollback
   ```markdown
   ## Rollback
   - Commit: xxxxxxx
   - Passos: ...
   ```

7. Somente após aprovação considerar reabilitar migrations

### ⚠️ IMPORTANTE

**NÃO executar nenhuma ação em produção relacionada ao Alembic.**

**Apenas documentar e criar a task técnica.**

---

## Comandos Úteis

```bash
# Verificar estado do Alembic
cd backend && alembic current && alembic heads && alembic branches

# Testar healthcheck
curl https://causium-api-2026.azurewebsites.net/health

# Ver logs do Azure
az webapp log download --resource-group rg-causium-staging-01 --name causium-api-2026

# Ver status do App Service
az webapp show --resource-group rg-causium-staging-01 --name causium-api-2026
```

---

## Estrutura de Documentação

```
CauSium/
├── CLAUDE.md                              ← Este arquivo (regras de engenharia)
├── CONTRIBUTING.md                        ← Regras para contribuidores
├── README.md                              ← Documentação principal
├── docs/
│   ├── architecture/
│   │   └── engineering-policy.md          ← Políticas detalhadas
│   ├── runbooks/
│   │   ├── deployment-checklist.md         ← Checklist de deploy
│   │   └── backup-restore.md               ← Backup e restore
│   └── incidents/
│       └── 2026-06-11-dashboard-outage.md ← Registro do incidente
```

---

## Contato

Para dúvidas sobre as regras, consulte a documentação em `docs/architecture/engineering-policy.md`.