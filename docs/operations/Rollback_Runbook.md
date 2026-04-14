# Rollback Runbook

Data: 2026-04-11
Objetivo: restaurar servico com menor impacto em caso de regressao critica.

## 1) Gatilhos de rollback

- Erro 5xx acima do budget por janela sustentada.
- Falha de autenticacao generalizada.
- Falha de worker com acúmulo de DLQ fora do normal.
- Degradacao severa de latencia sem mitigacao rapida.

## 2) Procedimento

1. Pausar rollout e bloquear novos deploys.
2. Reverter backend/worker para imagem/tag anterior estavel.
3. Se necessario, reverter frontend para versão anterior.
4. Se migracao for incompatível, aplicar downgrade Alembic validado.
5. Rodar smoke pós-rollback.

## 3) Validacao pos-rollback

- `/health` e `/health/detailed` saudaveis.
- Fluxos criticos de auth e notificacao funcionando.
- SLI/SLO estabilizados na baseline anterior.

## 4) Registro de incidente

- Timestamp de inicio/fim.
- Impacto percebido por cliente.
- Causa raiz preliminar.
- Ações corretivas e preventivas.
