# CauSium — Guia de Onboarding para o Cliente

## URL da Plataforma

```
https://causium-api-2026-fea3frguggasbcg3.brazilsouth-01.azurewebsites.net
```

---

## 1. Criar sua conta

Acesse a URL acima e clique em **Sign In** → **Registrar nova organização**.

Preencha:
- **Nome da organização** — ex: `Empresa XYZ`
- **Slug da organização** — ex: `empresa-xyz` (identificador único, sem espaços)
- **Seu nome completo**
- **E-mail corporativo**
- **Senha** (mínimo 8 caracteres)

---

## 2. Conectar o tenant Azure

Para que o CauSium acesse os dados de custo do Azure, você precisa:

### 2.1 Criar um App Registration no Azure AD

1. Acesse o [Portal Azure](https://portal.azure.com)
2. Vá em **Azure Active Directory → App registrations → New registration**
3. Nome: `CauSium FinOps`
4. Tipo de conta: **Single tenant**
5. Clique em **Register**
6. Anote o **Application (client) ID** e o **Directory (tenant) ID**

### 2.2 Criar um Client Secret

1. No App Registration criado, vá em **Certificates & secrets → New client secret**
2. Descrição: `CauSium`
3. Expiração: **24 months**
4. Clique em **Add** e anote o **Value** (só aparece uma vez)

### 2.3 Atribuir permissões na Subscription

1. Vá em **Subscriptions** e selecione a subscription que deseja monitorar
2. Clique em **Access control (IAM) → Add role assignment**
3. Role: **Cost Management Reader**
4. Assign access to: **User, group, or service principal**
5. Selecione o App Registration `CauSium FinOps`
6. Clique em **Save**

### 2.4 Configurar exportação de custos (Cost Export)

O CauSium lê os dados de custo via Azure Cost Export para um Storage Account.

#### Criar Storage Account (se não tiver):
1. Vá em **Storage accounts → Create**
2. Nome: `causiumexports` (ou similar)
3. Region: mesma da subscription
4. Performance: **Standard**, Redundancy: **LRS**
5. Clique em **Review + Create**

#### Criar o Cost Export:
1. Vá em **Cost Management + Billing → Cost Management → Exports**
2. Clique em **Add**
3. Nome: `causium-daily-export`
4. Export type: **Daily export of month-to-date costs**
5. Storage account: selecione o criado acima
6. Container: `cost-exports`
7. Directory: `causium`
8. Format: **CSV**
9. Clique em **Create**

#### Dar acesso ao Storage Account:
1. Vá no Storage Account criado
2. **Access control (IAM) → Add role assignment**
3. Role: **Storage Blob Data Reader**
4. Selecione o App Registration `CauSium FinOps`

#### Pegar a URL do Storage Account:
1. No Storage Account, vá em **Endpoints**
2. Copie o **Blob service** URL — ex: `https://causiumexports.blob.core.windows.net`

### 2.5 Conectar no CauSium

No dashboard do CauSium, vá em **Settings → Cloud Accounts → Add Account** e preencha:

| Campo | Valor |
|-------|-------|
| Provider | Azure |
| Display Name | Azure Production |
| External ID | ID da sua Subscription (ex: `284e9c06-...`) |
| Tenant ID | Directory (tenant) ID do App Registration |
| Client ID | Application (client) ID do App Registration |
| Client Secret | Value do secret criado |
| Subscription ID | ID da Subscription |
| Storage Account URL | URL do Blob service (ex: `https://causiumexports.blob.core.windows.net`) |
| Cost Export Container | `cost-exports` |
| Cost Export Prefix | `causium` |

---

## 3. Conectar AWS (opcional)

### 3.1 Criar IAM User com permissões de leitura

1. Acesse o [AWS Console](https://console.aws.amazon.com)
2. Vá em **IAM → Users → Create user**
3. Nome: `causium-finops`
4. Attach policies: **ReadOnlyAccess** + **AWSBillingReadOnlyAccess**
5. Crie **Access Keys** e anote o **Access Key ID** e **Secret Access Key**

### 3.2 Configurar Cost and Usage Report (CUR)

1. Vá em **Billing → Cost & Usage Reports → Create report**
2. Nome: `causium-cur`
3. S3 bucket: crie ou selecione um bucket
4. Prefix: `causium`
5. Format: **CSV**, Compression: **GZIP**

### 3.3 Conectar no CauSium

| Campo | Valor |
|-------|-------|
| Provider | AWS |
| Display Name | AWS Production |
| External ID | Account ID (12 dígitos) |
| Access Key ID | Chave de acesso IAM |
| Secret Access Key | Chave secreta IAM |
| Region | `us-east-1` (ou sua região principal) |
| CUR Bucket | Nome do bucket S3 do CUR |
| CUR Prefix | `causium` |

---

## 4. SSO com Microsoft (opcional)

Para login com conta corporativa Microsoft:

1. No App Registration `CauSium FinOps`, vá em **Authentication → Add a platform → Web**
2. Redirect URI: `https://causium-api-2026-fea3frguggasbcg3.brazilsouth-01.azurewebsites.net/api/v1/auth/oidc/azure/callback`
3. Marque **ID tokens**
4. Em **API permissions**, adicione: `openid`, `profile`, `email`, `User.Read`
5. Clique em **Grant admin consent**

Informe ao time CauSium as seguintes variáveis para ativar o SSO:
- `AZURE_OIDC_CLIENT_ID` — Application (client) ID
- `AZURE_OIDC_CLIENT_SECRET` — Client secret
- `AZURE_OIDC_TENANT_ID` — Directory (tenant) ID

---

## 5. Suporte

Em caso de dúvidas, entre em contato com o time CauSium.

---

*Documento gerado em 2026-04-30*
