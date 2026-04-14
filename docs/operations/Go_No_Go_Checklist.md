# Go / No-Go Checklist

Data: 2026-04-14
Decisao final de release: [ ] GO  [ ] NO-GO

---

## Build and Security

- [x] CI Security Gates verde
  - Secret scan: gitleaks-action@v2 no pipeline (`ci.yml`)
  - SAST: Bandit `-r app -ll -iii` com baseline de excecoes gerenciado em `.security/security_baseline.json`
  - SCA backend: pip-audit --strict --local
  - SCA frontend: npm audit --audit-level=critical
  - Evidencia: job `security` no `ci.yml` bloqueante em todos os PRs para `main`

- [x] Backend pipeline verde
  - Lint: ruff check app tests
  - Typecheck: mypy app --ignore-missing-imports
  - Testes: pytest tests/ com Postgres + Redis reais no CI
  - Perf smoke: benchmark_ledger_costs.py (p95 validado)
  - Release smoke: release_smoke.py + go_no_go_gate.py
  - Evidencia: job `backend` no `ci.yml`

- [x] Frontend pipeline verde
  - Typecheck: tsc --noEmit
  - Testes: vitest run (26 testes passando — Login, MFA TOTP, ActivateInvite, Settings, Members)
  - Build: vite build
  - SP-A02 gate: assert-no-auth-token-storage.mjs (nenhum token em localStorage/sessionStorage)
  - Evidencia: job `frontend` no `ci.yml` (npm test adicionado em 2026-04-14)

- [x] Sem vulnerabilidade critica sem excecao valida
  - Excecoes documentadas e versionadas em `.security/security_baseline.json`
  - Politica de excecao em `docs/security/OP08_Security_Gates_Policy.md`

---

## Quality and Testing

- [x] Unit tests dos modulos alterados passando
  - Backend: pytest tests/unit/ — rate limiter, security headers, TLS, OIDC, observabilidade,
    economics export runtime, email service, Slack service, workspace keyring, notification worker
  - Frontend: vitest run — Login, MFA TOTP backup codes, ActivateInvite (LGPD), Settings

- [x] Integration tests criticos passando
  - Auth: login, logout global, MFA TOTP (setup/enable/disable), MFA TOTP backup codes,
    passkey, forgot/reset password, change password, admin reset senha/MFA
  - Multi-workspace: cross-workspace isolation, platform_admin, quota de membros, lifecycle de org
  - Invites: criacao, preview, aceite com LGPD consent (terms_accepted obrigatorio)
  - Notifications: alertas, contagem de nao lidos, preferencias, Slack config, regras por categoria
  - Economics: export assincrono (job/status/download)
  - Audit chain: SHA-256 chain, plataforma
  - Workers/DLQ: api de reprocessamento

- [ ] E2E critical flows executados
  - Pendente: executar `docs/operations/E2E_Critical_Flows.md` em ambiente staging
  - Escopo minimo: login + MFA + convite + export + DLQ + notificacao

- [ ] Smoke de release executado e anexado
  - `scripts/release_smoke.py` deve ser rodado em staging (nao apenas --dry-run)
  - Anexar output JSON como artefato de release

---

## Operations and Reliability

- [x] Runbook revisado
  - `docs/operations/Release_Runbook.md` — procedimento de deploy, rollback, contatos
  - `docs/operations/Rollback_Runbook.md` — passos de rollback por componente

- [x] Rollback validado (procedimento)
  - Migrations com downgrade implementado (0001-0028)
  - Scripts de restore testados: `scripts/restore.sh` com RTO <= 300s, RPO <= 3600s
  - Drill automatizado: `scripts/rto_rpo_test.sh`

- [ ] Alertas SLO/SLA monitorados no dashboard
  - Observabilidade implementada (`app/core/observability.py`): metricas Prometheus, SLO breach detection
  - Pendente: confirmar que dashboard Grafana/equivalente esta configurado em staging com alertas ativos

- [x] Dependencias externas estaveis
  - PostgreSQL 16, Redis 7, ClickHouse — health checks no docker-compose.yml
  - SMTP: fallback no-op quando nao configurado
  - Slack: fallback no-op quando webhook nao configurado

---

## LGPD e Compliance

- [x] Consentimento de titular registrado
  - Aceite de convite requer `terms_accepted=True` (422 se ausente ou false)
  - `terms_accepted_at` e `terms_version` gravados no usuario
  - Auditado no evento de aceite de convite

- [x] Direito de acesso (Art. 18 LGPD)
  - `GET /auth/me/export` — retorna perfil, status MFA, passkeys cadastradas

- [x] Direito ao apagamento (Art. 18 LGPD)
  - `DELETE /auth/me/data` — anonimiza email/nome, desativa conta, limpa TOTP/passkeys/tokens
  - Auditado como `lgpd.purge`

- [x] Dados sensiveis nao expostos em logs
  - Senhas hasheadas (bcrypt), segredos TOTP criptografados (Fernet por workspace key)
  - Backup codes armazenados como SHA-256 (nunca plaintext no banco)
  - Reset token nao exposto no frontend (corrigido em 2026-04-13)

---

## Final Approval

- [ ] Engineering approval
- [ ] Platform/SRE approval
- [ ] Security approval
- [ ] Product/Business approval
