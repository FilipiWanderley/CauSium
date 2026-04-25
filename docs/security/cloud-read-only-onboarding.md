# Cloud Read-Only Onboarding

## Objetivo
Padronizar o onboarding de contas cloud em modo somente leitura para manter o CauSium como Decision Support System (DSS), sem mutacao automatica de infraestrutura.

## Principios
- Credenciais iniciais devem ser sempre read-only.
- Qualquer excecao deve passar por revisao de seguranca e aprovacao explicita.
- A pipeline de CI bloqueia assinaturas de codigo mutativo em `backend/app`.

## Permissoes Minimas Recomendadas

### Azure
- `Reader`
- `Cost Management Reader`

Observacoes:
- Evitar papeis com permissao de escrita (`Contributor`, `Owner`) no onboarding inicial.
- Escopo preferencial: Subscription ou Resource Group conforme necessidade do cliente.

### AWS
- `ReadOnlyAccess`
- Permissao de leitura de Billing/CUR (Cost and Usage Report)

Observacoes:
- Garantir leitura para Cost Explorer/CUR e inventario sem permitir `RunInstances`, `StopInstances` ou alteracoes de recursos.

### GCP
- `Viewer`
- `Billing Viewer`

Observacoes:
- Credencial deve permitir consulta de custos/logs/inventario sem permissao de alteracao.

### AKS / Kubernetes
- Perfil somente leitura com verbos `get`, `list`, `watch`

Observacoes:
- Nao conceder `create`, `update`, `patch`, `delete`, `scale` no cluster durante onboarding.

## Guardrails Operacionais
- CI guardrail: bloqueia padroes mutativos (ex.: `begin_create_or_update`, `run_instances`, `create_or_update`).
- Allowlist: permitida apenas com justificativa documentada em `.security/cloud_mutation_guardrail_allowlist.txt`.
- PR deve declarar explicitamente que nao adiciona mutacao cloud.

## Excecoes
- Excecoes so podem ocorrer com:
  - feature flag dedicada;
  - aprovacao explicita de seguranca/plataforma;
  - plano de rollback;
  - registro no PR e ticket de rastreio.
