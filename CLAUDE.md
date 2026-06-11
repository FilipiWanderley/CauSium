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