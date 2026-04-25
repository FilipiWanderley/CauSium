# Azure Staging Provisioning Plan

## Fase
Azure Staging

## Objetivo
Subir ambiente de staging com menor complexidade para validar fluxo real com cliente.

## Arquitetura recomendada (MVP staging)
- Regiao: `Brazil South`
- Resource Group: `rg-causium-staging`
- Backend: `Azure App Service` (Linux, Python 3.12, deploy direto)
- Frontend: `Azure Static Web Apps`
- Banco: `Azure PostgreSQL Flexible Server` (`B1ms`, 32 GB)
- Redis: nao obrigatorio na primeira subida
- Secrets: `App Settings` inicialmente; migrar para `Azure Key Vault` na etapa seguinte

## Nomes sugeridos
- Backend app: `causium-api-staging`
- Frontend app: `causium-web-staging`
- PostgreSQL server: `causium-pg-staging`
- Key Vault: `kv-causium-staging`

## Ordem de execucao
1. Criar recursos Azure base.
2. Configurar variaveis seguras.
3. Subir backend.
4. Aplicar migrations.
5. Subir frontend.
6. Validar `/health`, login e fluxo principal.
7. Conectar dados read-only da Queiroz Galvao.

## Checklist de definicoes antes do provisionamento
- [ ] Regiao Azure final confirmada.
- [ ] Nome dos apps e recursos confirmados.
- [ ] Dominio temporario Azure ou customizado definido.
- [ ] Estrategia de deploy (Docker ou deploy direto) confirmada.
- [ ] Tamanho inicial do PostgreSQL validado.
- [ ] Necessidade de Redis no runtime validada.

## Decisao atual recomendada
- Priorizar `Brazil South` por latencia para operacao no Brasil.
- Manter deploy sem Docker no staging para acelerar validacao.
- Entrar sem Redis no primeiro ciclo, habilitando apenas se houver necessidade real.
