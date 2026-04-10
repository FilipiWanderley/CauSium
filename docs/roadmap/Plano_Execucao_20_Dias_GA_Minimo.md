# Plano de Execucao 20 Dias - GA Minimo (Nivel Senior)

Data base: 2026-04-10
Objetivo: fechar um GA minimo operacional em 20 dias, com qualidade senior, sem reduzir seguranca e sem quebrar producao.

## 1) Escopo fechado do sprint de 20 dias

Itens obrigatorios (go-live minimo):

- SP-NT02 completo para todas as categorias de alerta (financial, optimization, governance, activity, security)
- SP-A06 MFA TOTP completo (setup, verify, enable, disable, reset por admin)
- SP-OP08 gates de seguranca no CI (SAST, SCA, secret scan bloqueando merge)
- SP-OP06 observabilidade operacional (tracing + metricas essenciais)
- SP-OP07 dashboards SLI/SLO com alertas acionaveis
- SP-EC03 exportacao assincrona de relatorios (CSV e Excel) com status e download
- SP-EC04 custo detalhado com filtros combinados + paginacao + validacao de performance
- SP-WK03 remocao de endpoints depreciados
- SP-MT06 baseline de chaves por workspace enterprise (isolamento pratico e auditavel)
- Hardening final: runbook, rollback, smoke, e2e critico, checklist de go/no-go

Fora do escopo para estes 20 dias:

- Wave 3 e Wave 4 completos
- GraphQL federation completo
- Multi-regiao e data residency enterprise
- Diferenciais P2/P3 de IA causal avancada

## 2) Definicao de pronto (DoD senior)

Todo item so pode ser considerado concluido quando tiver:

- Codigo com testes unitarios e de integracao cobrindo caminho feliz e erro critico
- Migracoes com validacao de upgrade e downgrade
- Telemetria basica (logs estruturados, metrica e span relevante)
- Revisao de seguranca do fluxo (authz, escopo workspace, validacao de input)
- Evidencia de aceite reproduzivel no CI e no ambiente docker
- Documentacao minima de operacao e troubleshooting

## 3) Estrutura de trilhas paralelas

Trilha Produto (Backend + Frontend):

- NT02, A06, EC03, EC04, WK03

Trilha Plataforma e SRE:

- OP06, OP07, hardening de release, runbook, rollback

Trilha Seguranca e Compliance:

- OP08, revisao de secrets e politica de branch/protecao

Regra operacional:

- Maximo 2 itens em progresso por trilha
- Nenhum item entra sem criterio de aceite definido
- Bloqueio acima de 4 horas vira acao imediata de destravamento

## 4) Cronograma diario D1-D20

### D1-D2 (Planejamento tecnico e congelamento)

- Congelar escopo final e dependencias tecnicas
- Quebrar historias em tarefas de 0.5 a 1.5 dia
- Definir matriz de risco por item
- Definir criterios de aceite executaveis e observaveis

Saida esperada:

- Backlog priorizado e sequenciado
- Quadro de dependencias e donos

### D3-D5 (Notificacoes e autenticacao)

- Completar SP-NT02 para todas categorias
- Consolidar endpoints de regra por categoria
- Completar SP-A06 (TOTP setup/verify/enable/disable + reset admin)

Saida esperada:

- Fluxos prontos com testes de integracao
- Auditoria de eventos criticos de MFA

### D6-D8 (Economics I)

- SP-EC03 export assicrono backend (job, status, download)
- SP-EC04 filtros combinados e paginacao padrao

Saida esperada:

- Export funcional por API
- Query de custo detalhado com contrato consistente

### D9-D10 (Economics II + performance)

- Benchmark e tuning de SP-EC04
- Meta de latencia p95 validada no dataset de referencia

Saida esperada:

- Relatorio de performance
- Ajustes em indice/query onde necessario

### D11-D12 (Plataforma e seguranca)

- SP-OP08 gates de seguranca no CI bloqueando merge
- SP-WK03 remocao de endpoints depreciados com compatibilidade controlada

Saida esperada:

- Pipeline falhando corretamente para vulnerabilidades criticas
- Inventario de endpoints removidos e substituidos

### D13-D14 (Isolamento de chave e observabilidade)

- SP-MT06 baseline de chave por workspace
- SP-OP06 tracing e metricas essenciais por request e job

Saida esperada:

- Evidencia de isolamento por workspace
- Traces/metricas visiveis e uteis para diagnostico

### D15-D16 (SLO e operacao)

- SP-OP07 dashboards SLI/SLO e alertas
- Runbook de incidente e rollback

Saida esperada:

- Painel de operacao com indicadores principais
- Procedimento de resposta testado

### D17-D18 (Integracao final)

- Testes E2E criticos de ponta a ponta
- Correcao de regressao
- Congelamento de novas features

Saida esperada:

- Candidata a release estavel

### D19-D20 (Go-live rehearsal)

- Ensaio completo de deploy
- Teste de rollback
- Smoke em ambiente alvo
- Reuniao go/no-go com checklist objetivo

Saida esperada:

- Decisao de release com evidencia tecnica

## 5) Backlog executavel (ordem de implementacao)

1. NT02-fase2: regras para financial, optimization, governance, security
2. A06-fase1: entidade TOTP + rotas de setup/verify
3. A06-fase2: enable/disable e reset admin com auditoria
4. EC03-fase1: modelo de job e endpoint de criacao de export
5. EC03-fase2: processamento assincrono e endpoint de download
6. EC04-fase1: filtros e paginacao padrao
7. EC04-fase2: tuning de consulta e indices
8. OP08-fase1: scanners no pipeline
9. OP08-fase2: politica de bloqueio e baseline de excecao
10. WK03-fase1: mapa de endpoints depreciados
11. WK03-fase2: remocao segura e comunicacao de contrato
12. MT06-fase1: chave por workspace enterprise
13. OP06-fase1: instrumentacao de API e workers
14. OP07-fase1: SLI/SLO dashboards e alertas
15. Release-hardening: runbook, rollback, smoke, e2e e go/no-go

## 6) Metas de controle diario

- Lead time medio por item critico: ate 2 dias
- Taxa de regressao por dia: zero bug bloqueante aberto por mais de 24h
- Falha de pipeline: resolver no mesmo dia
- Cobertura de testes em modulos alterados: manter ou aumentar

## 7) Riscos e mitigacao

Risco: escopo aumentar durante execucao
Mitigacao: gate de mudanca com aprovacao explicita

Risco: instabilidade de ambiente de testes
Mitigacao: padrao unico de execucao via docker + script fixo

Risco: dependencia externa atrasar
Mitigacao: usar mock/fallback com feature flag temporaria

Risco: acumulo de debito tecnico no final
Mitigacao: reservar 20% de capacidade diaria para estabilizacao

## 8) Cadencia de guerra

- Daily 15 min com status objetivo: feito, bloqueio, proximo
- Checkpoint tecnico ao fim do dia com semaforo por trilha
- Revisao de risco a cada 48h
- Freeze de feature no D17

## 9) Critico para bater prazo com nivel senior

- Nao aceitar tarefa sem criterio de aceite testavel
- Nao mergear sem teste e sem evidencias minimas
- Nao adiar observabilidade e seguranca para o fim
- Nao executar paralelismo sem dono claro
