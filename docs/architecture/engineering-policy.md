# Engineering Policy - CauSium

**Versão:** 1.0.0  
**Data:** 2026-06-11  
**Status:** Obrigatório  

---

## 1. Princípios Fundamentais

### 1.1 Produção é Sagrada

O dashboard do cliente **NUNCA** pode ser derrubado por mudanças de desenvolvimento.

### 1.2 Zero Tolerance para Downtime Não Planejado

Cada incidente de produção deve ser documentado e aprendido.

### 1.3 Mudanças Graduais e Reversíveis

Toda alteração deve poder ser revertida.

---

## 2. Fluxo de Alterações

### 2.1 Fluxo Obrigatório

```
DIAGNÓSTICO → PLANO → DIFF → TESTE LOCAL → VALIDAÇÃO → APROVAÇÃO → COMMIT → DEPLOY
```

### 2.2 Diagnóstico

Antes de qualquer alteração, documentar:

- **Causa Raiz:** O que está causando o problema?
- **Impacto:** Quem será afetado? Por quanto tempo?
- **Arquivos Afetados:** Quais arquivos precisam mudar?
- **Alternativas:** Existem outras formas de resolver?

### 2.3 Plano

Apresentar antes de qualquer alteração:

- **O que será alterado:** Descrição clara
- **Riscos:** O que pode dar errado?
- **Dependências:** O que precisa estar pronto antes?
- **Impacto esperado:** O que vai melhorar?
- **Rollback:** Como reverter se algo der errado?

### 2.4 Diff

Mostrar as alterações propostas antes de executar.

### 2.5 Teste Local

Toda alteração deve ser testada localmente antes de qualquer commit:

- [ ] Testes unitários passando
- [ ] Testes de integração passando
- [ ] Build succeeds
- [ ] Lint passing
- [ ] Type check passing
- [ ] Startup da aplicação funciona

### 2.6 Validação

Verificar que a alteração funciona corretamente.

### 2.7 Aprovação

Obter aprovação explícita antes de fazer commit.

### 2.8 Commit

Fazer commit seguindoConventional Commits.

### 2.9 Deploy

Seguir checklist de deploy (ver `docs/runbooks/deployment-checklist.md`).

---

## 3. Regras de Database

### 3.1 Migrations Automáticas em Produção

**PROIBIDO** executar migrations automaticamente no startup.

### 3.2 Antes de qualquer migration

```bash
# Verificar estado atual
alembic current

# Verificar heads
alembic heads

# Verificar branches
alembic branches

# Verificar merge points
alembic history --verbose
```

### 3.3 Se existir múltiplas heads

1. **PARAR IMEDIATAMENTE**
2. **NÃO executar `alembic upgrade head`**
3. Documentar o problema
4. Resolver as múltiplas heads antes de continuar

### 3.4 Documentação de Migration

Toda migration deve incluir:

- **Descrição:** O que a migration faz?
- **Rollback:** Como reverter?
- **Impacto:** Quais tabelas são afetadas?
- **Tempo estimado:** Quanto tempo vai demorar?

### 3.5 Rollback

Toda mudança de banco deve possuir rollback documentado.

---

## 4. Regras de Deploy

### 4.1 Checklist Obrigatório

Ver `docs/runbooks/deployment-checklist.md`

### 4.2 Pré-Deploy

- [ ] Build OK
- [ ] Testes OK
- [ ] Banco validado
- [ ] Rollback definido
- [ ] Healthcheck validado

### 4.3 Pós-Deploy

Validar OBRIGATORIAMENTE:

- [ ] Login funciona
- [ ] Dashboard carrega
- [ ] Spend Analysis funciona
- [ ] Spend Stability funciona
- [ ] Spend by SKU funciona
- [ ] Savings Opportunities funciona
- [ ] Health Check (`/health`) retorna OK

### 4.4 Rollback

Se algo der errado:

1. Identificar a versão anterior
2. Executar rollback
3. Validar que o sistema voltou ao normal
4. Documentar o incidente

---

## 5. Regras de Produção

### 5.1 Proibido

- ❌ Deploy sem validação local
- ❌ Alterar banco de produção diretamente
- ❌ Executar migrations automaticamente em startup
- ❌ Executar comandos destrutivos
- ❌ Apagar tabelas
- ❌ Alterar schemas sem aprovação
- ❌ Fazer hotfix sem explicar o risco
- ❌ Testar em produção

### 5.2 Permitido (com aprovação)

- ✅ Deploy via GitHub Actions (CI/CD)
- ✅ Migrations via pipeline de deploy (não no startup)
- ✅ Rollback via GitHub Actions

---

## 6. Estrutura de Ambientes

| Ambiente | Propósito | Acesso |
|----------|-----------|--------|
| Production | Cliente real | Somente via CI/CD |
| Staging | Testes pré-deploy | Dev team |
| Local | Desenvolvimento | Dev |

---

## 7. Infraestrutura

### 7.1 Azure App Service

- **Backend:** `causium-api-2026`
- **Frontend:** Azure Static Web Apps
- **Database:** PostgreSQL (Azure)
- **Analytics:** ClickHouse (Azure)

### 7.2 Variáveis de Ambiente

Todas as variáveis de produção estão no Azure App Service Settings.

**NUNCA** commitar secrets no git.

---

## 8. Monitoramento

### 8.1 Health Check

```
GET /health
```

Resposta esperada:
```json
{"status": "ok", "version": "0.1.0"}
```

### 8.2 Logs

Ver `docs/runbooks/backup-restore.md` para instruções de acesso aos logs.

---

## 9. Incidentes

### 9.1 Registro de Incidentes

Todo incidente deve ser documentado em `docs/incidents/`.

Formato: `YYYY-MM-DD-descricao.md`

### 9.2 Estrutura do Registro

```markdown
# Incidente: [Título]

**Data:** YYYY-MM-DD  
**Severidade:** Alta/Média/Baixa  
**Status:** Resolvido/Pendente

## Timeline
- HH:MM - Evento

## Impacto
- O que foi afetado?

## Causa Raiz
- O que causou o problema?

## Resolução
- Como foi resolvido?

## Lições Aprendidas
- O que podemos melhorar?

## Ação Corretiva
- O que precisa ser feito para evitar recurrence?
```

---

## 10. Referências

- `CLAUDE.md` - Regras de engenharia resumidas
- `CONTRIBUTING.md` - Guia para contribuidores
- `docs/runbooks/deployment-checklist.md` - Checklist de deploy
- `docs/runbooks/backup-restore.md` - Backup e restore
- `docs/incidents/` - Registro de incidentes