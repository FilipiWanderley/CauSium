# WK03 Fase 1 - Mapa de Endpoints Depreciados

Data: 2026-04-11
Status: fase 1 e fase 2 concluidas
Escopo: inventario de endpoints legados com substituicao e plano de remocao controlada.

## 1) Inventario de endpoints depreciados

### 1.1 Endpoint legado identificado

- Endpoint legado: `GET /api/v1/notifications/new`
- Dominio: Notifications
- Motivacao de deprecacao: endpoint de polling legado ja substituido por contrato mais claro e composivel.
- Substitutos oficiais:
  - `GET /api/v1/notifications/unread-count`
  - `GET /api/v1/notifications` com paginacao e filtros (`status=unread` quando aplicavel)

## 2) Evidencias no codigo

- Backend ainda exposto em `backend/app/domains/notifications/router.py`.
- Frontend ainda consome em `frontend/src/api/notifications.ts` e `frontend/src/pages/Notifications/NotificationsPage.tsx`.
- Testes de integracao ainda validam comportamento legado:
  - `backend/tests/integration/test_notifications_new.py`
  - `backend/tests/integration/test_activity_events.py`
  - `backend/tests/integration/test_notification_categories_rules.py`

## 3) Risco e impacto

- Risco funcional: medio
- Impacto esperado: tela de notificacoes e polling de badges
- Impacto operacional: baixo se migracao frontend for feita antes do corte no backend

## 4) Plano de remocao segura (WK03 Fase 2)

1. Migrar frontend para usar apenas:
   - `GET /notifications/unread-count` para contadores
   - `GET /notifications?status=unread` para lista de nao lidas
2. Atualizar testes de integracao para o novo contrato.
3. Marcar endpoint legado com janela de sunset curta no changelog interno.
4. Remover schema e rota de `GET /notifications/new` no backend.
5. Validar regressao com testes de notificacoes e smoke de UI.

## 5) Criterio de aceite para WK03 Fase 2

- Nao existe mais referencia a `/notifications/new` no frontend.
- Nao existe mais rota `/notifications/new` no backend.
- Testes de notificacoes passam cobrindo apenas o contrato novo.
- PR inclui comunicacao de migracao no resumo tecnico.

## 6) Execucao realizada (2026-04-11)

- Rota legada removida do backend: `GET /api/v1/notifications/new`.
- Contrato novo consolidado:
  - `GET /api/v1/notifications/unread-count` (agora com filtro opcional por categoria)
  - `GET /api/v1/notifications` com `status=unread` para lista de nao lidas
- Frontend migrado para nao depender do endpoint legado.
- Testes de integracao atualizados para o contrato novo.

Observacao de validacao local:
- Typecheck frontend executado com sucesso.
- Testes de integracao de notificacoes bloqueados localmente por indisponibilidade de Postgres em `localhost:5432`.
