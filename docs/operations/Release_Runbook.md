# Release Runbook (GA Minimo)

Data: 2026-04-11
Escopo: deploy controlado do StratoPulse com validacao tecnica objetiva.

## 1) Pre-flight obrigatorio

- Branch de release atualizada com `main/develop`.
- CI verde nas trilhas: `security`, `backend`, `frontend`.
- Nenhum alerta critico aberto em Platform SLO (`/app/platform/slo`).
- Baseline de seguranca validada (`.security/security_baseline.json`).
- Migracoes revisadas com plano de rollback.

## 2) Sequencia de deploy

1. Congelar merges na branch alvo.
2. Aplicar migracoes Alembic no ambiente alvo.
3. Deploy backend API.
4. Deploy workers.
5. Deploy frontend.
6. Executar smoke de release.

## 3) Smoke pos-deploy

Executar:

```bash
python backend/scripts/release_smoke.py --base-url https://<api-host> --output-json backend/benchmark_artifacts/release_smoke.json
```

Para rehearsal completo com decisao automatica GO/NO_GO:

```bash
python backend/scripts/release_rehearsal.py --base-url https://<api-host> --token <bearer-token> --output-json backend/benchmark_artifacts/release_rehearsal.json
```

Execucao recomendada (wrapper seguro para terminal local):

```bash
STAGING_API_URL="https://<api-host>" \
STAGING_BEARER_TOKEN="<bearer-token>" \
./scripts/run_release_rehearsal.sh
```

Criterio minimo:

- `/health` retorna `status=ok`.
- `/health/detailed` responde sem erro HTTP.
- `/metrics` responde em formato texto.
- Arquivos operacionais obrigatorios presentes.

## 4) Sinais de aceitação

- Erro 5xx controlado dentro do budget (< 1%).
- p95 de API crítica dentro da meta operacional.
- Workers sem taxa anormal de retry/failure.

## 5) Encerramento de release

- Registrar hash deployado.
- Anexar artefatos de smoke e benchmark no ticket de release.
- Publicar status final no canal operacional.
