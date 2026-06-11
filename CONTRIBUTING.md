# CONTRIBUTING.md - CauSium

**Última atualização:** 2026-06-11

---

## Regras Obrigatórias

### 1. Fluxo de Trabalho

Todo código deve passar pelo fluxo:

```
Fork → Clone → Branch → Develop → Pull Request → Review → Merge
```

### 2. Antes de qualquer commit

- [ ] Tests passing
- [ ] Lint passing
- [ ] Type check passing
- [ ] Build succeeds

### 3. Antes de qualquer Pull Request

- [ ] Tests passing
- [ ] Documentation updated (se necessário)
- [ ] CHANGELOG updated (se necessário)
- [ ] PR description completa

### 4. Antes de qualquer deploy

**VER CLAUDE.md - Seção "Regras de Deploy"**

### 5. Branch Naming

```
feat/descricao-curta
fix/descricao-curta
hotfix/descricao-curta
docs/descricao-curta
```

### 6. Commit Messages

```
type(scope): description

Types:
- feat: Nova funcionalidade
- fix: Correção de bug
- hotfix: Correção urgente em produção
- docs: Documentação
- refactor: Refatoração
- test: Testes
- chore: Tarefas diversas
```

---

## Configuração do Ambiente

### Backend

```bash
cd backend
python -m venv antenv
source antenv/bin/activate  # Linux/Mac
# antenv\Scripts\activate  # Windows
poetry install
```

### Frontend

```bash
cd frontend
npm install
```

### Variáveis de Ambiente

Ver `.env.example` e copiar para `.env` com as configurações necessárias.

---

## Testes

### Backend

```bash
cd backend
pytest
```

### Frontend

```bash
cd frontend
npm test
```

---

## Segurança

- **NUNCA** commitar secrets no git
- Usar `.env` para variáveis sensitiveis
- Secrets devem estar no Azure Key Vault ou GitHub Secrets
- Ver `docs/security/` para políticas de segurança

---

## Problemas Comuns

### Alembic multiple heads

Se `alembic heads` retornar múltiplas heads:

1. **NÃO executar `alembic upgrade head`**
2. Verificar branches com `alembic branches`
3. Documentar o problema
4. Resolver antes de continuar

### Deploy falhando

1. Verificar GitHub Actions logs
2. Verificar Azure App Service logs
3. Verificar healthcheck
4. Em caso de dúvida, **não forçar deploy**

---

## Dúvidas?

Consulte:
- `CLAUDE.md` - Regras de engenharia
- `docs/architecture/engineering-policy.md` - Políticas detalhadas
- `docs/runbooks/deployment-checklist.md` - Checklist de deploy

---

## Incidentes

### 2026-06-11 - Dashboard Indisponível

O dashboard do cliente ficou indisponível porque o startup executava `alembic upgrade head` com múltiplas heads no Alembic.

**Lição:** Migrations automáticas em produção são proibidas.