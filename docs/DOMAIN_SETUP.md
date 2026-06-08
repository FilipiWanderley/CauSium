# Cloudflare Domain Setup - CauSium

Este documento descreve a configuração de DNS e redirects para o domínio `causiumtech.com`.

## Arquitetura

```
causiumtech.com (root)     → 301 redirect → https://app.causiumtech.com
www.causiumtech.com         → 301 redirect → https://app.causiumtech.com
app.causiumtech.com         → Azure Static Web Apps (origin)
```

**Nota:** `app.causiumtech.com` é o domínio oficial da aplicação. Os domínios `causiumtech.com` e `www.causiumtech.com` são apenas aliases de redirect.

## DNS Records na Cloudflare

### Records Atuais

| Type  | Name          | Content                                | Proxy Status | Notes |
|-------|---------------|----------------------------------------|--------------|-------|
| CNAME | app           | gentle-sea-0b9925a0f.7.azurestaticapps.net | Proxied (orange) | App frontend |
| CNAME | www           | app.causiumtech.com                    | DNS Only (gray) | Redirect only |
| A     | @ (root)      | 172.67.188.76                          | DNS Only (gray) | Temporário - precisa redirect |

### Records Necessários

1. **app.causiumtech.com** (já existe e funciona):
   - Type: `CNAME`
   - Name: `app`
   - Target: `gentle-sea-0b9925a0f.7.azurestaticapps.net`
   - Proxy: `Proxied` (orange)
   - SSL/TLS: `Flexible` ou `Full`

2. **causiumtech.com** (root domain):
   - Type: `CNAME`
   - Name: `@`
   - Target: `causiumtech.com` (para redirect)
   - Proxy: `DNS Only` (gray) - **NÃO proxyar root domain para Azure**

3. **www.causiumtech.com**:
   - Type: `CNAME`
   - Name: `www`
   - Target: `causiumtech.com`
   - Proxy: `DNS Only` (gray)

## Redirect Rules (Cloudflare Dashboard)

### Opção 1: Redirect Rules (Recomendado - Cloudflare Dashboard)

1. Acesse [Cloudflare Dashboard](https://dash.cloudflare.com)
2. Selecione o domínio `causiumtech.com`
3. Navegue para **Rules → Redirect Rules**
4. Clique em **Create rule**

#### Rule 1: Root domain redirect

```
Name: Redirect root to app
When incoming matches:
  - Field: Hostname
  - Operator: equals
  - Value: causiumtech.com

Then:
  - Type: Dynamic
  - URL: concat("https://app.causiumtech.com", [uri])
```

#### Rule 2: www redirect

```
Name: Redirect www to app
When incoming matches:
  - Field: Hostname
  - Operator: equals
  - Value: www.causiumtech.com

Then:
  - Type: Dynamic
  - URL: concat("https://app.causiumtech.com", [uri])
```

**Importante:** Marque "Preserve query string" se necessário.

### Opção 2: Page Rules (Legacy - ainda funciona)

Se a opção Redirect Rules não estiver disponível:

1. Navegue para **Rules → Page Rules**
2. Crie as seguintes regras:

#### Page Rule 1:
```
URL: causiumtech.com/*
Settings:
  - Forwarding: 301
  - https://app.causiumtech.com/$1
```

#### Page Rule 2:
```
URL: www.causiumtech.com/*
Settings:
  - Forwarding: 301
  - https://app.causiumtech.com/$1
```

**Nota:** Page Rules estão sendo deprecadas em favor de Redirect Rules. Use Redirect Rules se disponível.

## Validação

Execute os seguintes comandos para validar:

```bash
# Test root domain redirect
curl -I https://causiumtech.com

# Esperado:
# HTTP/2 301
# location: https://app.causiumtech.com/

# Test www redirect
curl -I https://www.causiumtech.com

# Esperado:
# HTTP/2 301
# location: https://app.causiumtech.com/

# Test app domain (deve funcionar)
curl -I https://app.causiumtech.com

# Esperado:
# HTTP/2 200
```

## Configuração via API (Cloudflare API)

Se você tiver um token da API da Cloudflare, pode automatizar:

```bash
# Listar zones
curl -X GET "https://api.cloudflare.com/client/v4/zones" \
  -H "Authorization: Bearer YOUR_API_TOKEN" \
  -H "Content-Type: application/json"

# Listar DNS records
curl -X GET "https://api.cloudflare.com/client/v4/zones/{ZONE_ID}/dns_records" \
  -H "Authorization: Bearer YOUR_API_TOKEN"

# Criar redirect rule
curl -X POST "https://api.cloudflare.com/client/v4/zones/{ZONE_ID}/rulesets" \
  -H "Authorization: Bearer YOUR_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "redirect-root-to-app",
    "phase": "http_request_redirect",
    "rules": [{
      "expression": "hostname eq \"causiumtech.com\"",
      "action": "redirect",
      "action_parameters": {
        "to_url": "https://app.causiumtech.com${uri}"
      }
    }]
  }'
```

## Como Recuperar se Quebrar

### Se o redirect não funcionar:

1. Verifique se os DNS records estão corretos
2. Verifique se a regra de redirect está ativa
3. Teste com `curl -v` para ver o redirect completo

### Se a API parar de responder:

1. Acesse o Azure Portal diretamente: `https://gentle-sea-0b9925a0f.7.azurestaticapps.net`
2. O app funciona via URL direta do Azure

### Se o SSL quebrar:

1. No Cloudflare Dashboard, vá em **SSL/TLS**
2. Configure como `Full` ou `Flexible`
3. Aguarde propagação (pode levar até 5 minutos)

## Configuração Atual Verificada

- ✅ `app.causiumtech.com` → 200 OK (funcionando)
- ❌ `causiumtech.com` → 404 (precisa redirect)
- ❌ `www.causiumtech.com` → 404 (precisa redirect)

## Passos para Corrigir

1. Acesse Cloudflare Dashboard
2. Vá em **Rules → Redirect Rules**
3. Crie duas regras conforme especificado acima
4. Valide com curl

## Referências

- [Cloudflare Redirect Rules](https://developers.cloudflare.com/rules/redirect-quiries/)
- [Cloudflare Page Rules](https://developers.cloudflare.com/rules/page-rules/)
- [Azure Static Web Apps Custom Domains](https://learn.microsoft.com/azure/static-web-apps/custom-domain)