# =============================================================================
# CauSium — Script de Deploy para Produção
# Executa: az CLI + gh CLI
# Uso: Abra PowerShell como Administrador e rode: .\deploy_producao.ps1
# =============================================================================

$ErrorActionPreference = "Continue"

# ---------------------------------------------------------------------------
# CONFIGURAÇÕES — não altere sem necessidade
# ---------------------------------------------------------------------------
$RESOURCE_GROUP     = "causium-rg"
$APP_SERVICE_RG     = "rg-causium-staging-01"
$APP_SERVICE_NAME   = "causium-api-2026"
$SWA_NAME           = "causium-frontend"
$LOCATION           = "eastus2"
$SWA_LOCATION       = "eastus2"
$GITHUB_REPO        = "FilipiWanderley/CauSium"

# Chaves geradas (únicas para este deploy)
$SECRET_KEY         = "0b770b9e10d7f0c7f0530c2d89d1858d56b5f5c8a2a8e57cafb645d0f7389eac"
$ENCRYPTION_KEY     = "nzoTeCn6WGUbqbju17LdnQC3Zi32P6WWRcm2XRxhIHY="
$MONITORING_KEY     = "6e60989c9fde45c47a3350cc41199f55ec517236bb1a70af3766363563f9f46d"

# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  CauSium — Deploy Producao" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ---------------------------------------------------------------------------
# PASSO 1 — Verificar login Azure e GitHub
# ---------------------------------------------------------------------------
Write-Host "[1/6] Verificando login Azure..." -ForegroundColor Yellow
az account show --query "{subscription:name, id:id}" -o table
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERRO: Faca login primeiro: az login" -ForegroundColor Red
    exit 1
}

Write-Host "[1/6] Verificando login GitHub..." -ForegroundColor Yellow
gh auth status
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERRO: Faca login primeiro: gh auth login" -ForegroundColor Red
    exit 1
}

# ---------------------------------------------------------------------------
# PASSO 2 — Criar Resource Group + Azure Static Web Apps
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "[2/6] Verificando Resource Group '$RESOURCE_GROUP'..." -ForegroundColor Yellow

$rgExists = az group show --name $RESOURCE_GROUP --query "name" -o tsv 2>$null
if ($rgExists -eq $RESOURCE_GROUP) {
    Write-Host "  Resource Group ja existe." -ForegroundColor Green
} else {
    Write-Host "  Criando Resource Group '$RESOURCE_GROUP' em '$LOCATION'..." -ForegroundColor Yellow
    az group create --name $RESOURCE_GROUP --location $LOCATION --output none
    if ($LASTEXITCODE -ne 0) { Write-Host "ERRO ao criar Resource Group" -ForegroundColor Red; exit 1 }
    Write-Host "  Resource Group criado." -ForegroundColor Green
}

Write-Host "[2/6] Criando Azure Static Web Apps '$SWA_NAME'..." -ForegroundColor Yellow

$swaExists = az staticwebapp show --name $SWA_NAME --resource-group $RESOURCE_GROUP --query "name" -o tsv 2>$null
if ($swaExists -eq $SWA_NAME) {
    Write-Host "  SWA ja existe, pulando criacao." -ForegroundColor Green
} else {
    az staticwebapp create `
        --name $SWA_NAME `
        --resource-group $RESOURCE_GROUP `
        --location $SWA_LOCATION `
        --sku Free
    if ($LASTEXITCODE -ne 0) { Write-Host "ERRO ao criar SWA" -ForegroundColor Red; exit 1 }
    Write-Host "  SWA criado com sucesso." -ForegroundColor Green
}

# Pegar domínio e token do SWA
$SWA_HOSTNAME = az staticwebapp show --name $SWA_NAME --resource-group $RESOURCE_GROUP --query "defaultHostname" -o tsv
$SWA_URL      = "https://$SWA_HOSTNAME"
$SWA_TOKEN    = az staticwebapp secrets list --name $SWA_NAME --resource-group $RESOURCE_GROUP --query "properties.apiKey" -o tsv

Write-Host "  URL do frontend: $SWA_URL" -ForegroundColor Green
Write-Host "  Token SWA obtido." -ForegroundColor Green

# ---------------------------------------------------------------------------
# PASSO 3 — Configurar secrets e variables no GitHub
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "[3/6] Configurando GitHub secrets e variables..." -ForegroundColor Yellow

gh secret set AZURE_STATIC_WEB_APPS_API_TOKEN --body $SWA_TOKEN --repo $GITHUB_REPO
Write-Host "  Secret AZURE_STATIC_WEB_APPS_API_TOKEN configurado." -ForegroundColor Green

gh variable set VITE_API_URL --body "https://causium-api-2026.azurewebsites.net" --repo $GITHUB_REPO
Write-Host "  Variable VITE_API_URL configurada." -ForegroundColor Green

# ---------------------------------------------------------------------------
# PASSO 4 — Atualizar variáveis do App Service (backend)
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "[4/6] Atualizando variaveis do App Service '$APP_SERVICE_NAME'..." -ForegroundColor Yellow

$CORS_ORIGINS = "http://localhost:3000,http://localhost:5173,http://localhost:5174,$SWA_URL"
$PASSKEY_ORIGINS = "http://localhost:5173,http://localhost:5174,$SWA_URL"
$SWA_DOMAIN = $SWA_HOSTNAME  # sem https://

az webapp config appsettings set `
    --name $APP_SERVICE_NAME `
    --resource-group $APP_SERVICE_RG `
    --settings `
        APP_ENV="production" `
        SECRET_KEY="$SECRET_KEY" `
        ENCRYPTION_KEY="$ENCRYPTION_KEY" `
        INTERNAL_MONITORING_KEY="$MONITORING_KEY" `
        CORS_ORIGINS="$CORS_ORIGINS" `
        FRONTEND_URL="$SWA_URL" `
        PASSKEY_RP_ID="$SWA_DOMAIN" `
        PASSKEY_ALLOWED_ORIGINS="$PASSKEY_ORIGINS" `
        AUTH_COOKIE_SAMESITE="none" `
        AUTH_COOKIE_SECURE="true" `
        AUTH_COOKIE_DOMAIN="" `
    --output none

if ($LASTEXITCODE -ne 0) { Write-Host "ERRO ao configurar App Service" -ForegroundColor Red; exit 1 }
Write-Host "  Variaveis do App Service atualizadas." -ForegroundColor Green

# ---------------------------------------------------------------------------
# PASSO 5 — Disparar deploy do backend (restart para pegar novas vars)
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "[5/6] Reiniciando App Service para aplicar variaveis..." -ForegroundColor Yellow
az webapp restart --name $APP_SERVICE_NAME --resource-group $APP_SERVICE_RG
if ($LASTEXITCODE -ne 0) { Write-Host "ERRO ao reiniciar App Service" -ForegroundColor Red; exit 1 }
Write-Host "  App Service reiniciado." -ForegroundColor Green

# ---------------------------------------------------------------------------
# PASSO 6 — Disparar deploy do frontend via GitHub Actions
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "[6/6] Disparando deploy do frontend via GitHub Actions..." -ForegroundColor Yellow
gh workflow run "Deploy Frontend - Azure Static Web Apps" --repo $GITHUB_REPO
if ($LASTEXITCODE -ne 0) {
    Write-Host "  Nao foi possivel disparar workflow automaticamente." -ForegroundColor Yellow
    Write-Host "  Acesse: https://github.com/$GITHUB_REPO/actions e dispare manualmente." -ForegroundColor Yellow
} else {
    Write-Host "  Workflow disparado." -ForegroundColor Green
}

# ---------------------------------------------------------------------------
# RESUMO FINAL
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  DEPLOY CONCLUIDO" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Backend:  https://causium-api-2026.azurewebsites.net/health" -ForegroundColor White
Write-Host "  Frontend: $SWA_URL" -ForegroundColor White
Write-Host ""
Write-Host "  Login de teste:" -ForegroundColor White
Write-Host "    Email: jefferson.20260423164812@causium.io" -ForegroundColor White
Write-Host "    Senha: Causium2026B" -ForegroundColor White
Write-Host "    Org:   empresa-20260423164812" -ForegroundColor White
Write-Host ""
Write-Host "  Acompanhe o deploy do frontend em:" -ForegroundColor White
Write-Host "  https://github.com/$GITHUB_REPO/actions" -ForegroundColor White
Write-Host ""
