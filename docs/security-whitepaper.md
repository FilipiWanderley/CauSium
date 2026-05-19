# CauSium Security Whitepaper

## Document Control

| Field | Value |
|-------|-------|
| Version | 1.0 |
| Status | Draft — for customer and auditor consumption |
| Audience | Enterprise customers, security reviewers, procurement teams |
| Last Updated | 2025-01-01 |
| Classification | Public |

---

## 1. Executive Summary

CauSium is a cloud cost decision-support platform that helps organizations understand, optimize, and govern their multi-cloud spending. This document describes the security architecture, controls, and compliance posture of the platform.

**Key security principles:**
- **Read-only by design** — CauSium observes cloud infrastructure but never mutates it
- **Workspace isolation** — each customer organization operates in a cryptographically separated workspace
- **Defense in depth** — multiple independent security layers from CI to runtime
- **Transparency** — immutable audit trail with cryptographic integrity verification
- **LGPD compliance** — full implementation of data subject rights (Brazilian General Data Protection Law)

**What CauSium is NOT:**
- Not a cloud management platform (no write access to your infrastructure)
- Not a security tool (does not scan for vulnerabilities in your cloud)
- Not a data lake (does not store raw cloud API responses long-term)

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Customer Browser                              │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ HTTPS (TLS 1.2+)
┌──────────────────────────────▼──────────────────────────────────────┐
│                     Frontend (React SPA)                             │
│  • No server-side rendering  • No PII in client storage             │
│  • CSP headers enforced      • HttpOnly auth cookies                │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ HTTPS (TLS 1.2+)
┌──────────────────────────────▼──────────────────────────────────────┐
│                     Backend API (FastAPI)                            │
│  • JWT authentication        • RBAC (6 roles)                       │
│  • Input validation (Pydantic) • Rate limiting                      │
│  • Security headers (HSTS, CSP, X-Frame-Options)                    │
└───────┬──────────────┬───────────────┬──────────────┬───────────────┘
        │              │               │              │
   ┌────▼────┐   ┌────▼────┐   ┌─────▼─────┐  ┌────▼────┐
   │PostgreSQL│   │ClickHouse│   │   Redis   │  │ Worker  │
   │(encrypted│   │(analytics│   │(ephemeral │  │(async   │
   │ at rest) │   │ engine)  │   │ queues)   │  │ jobs)   │
   └──────────┘   └──────────┘   └───────────┘  └────┬────┘
                                                      │ Read-only
                                                 ┌────▼────────┐
                                                 │ Cloud APIs   │
                                                 │ (Azure/AWS/  │
                                                 │  GCP — Reader│
                                                 │  role only)  │
                                                 └──────────────┘
```

### Deployment Model

- **Hosting:** Microsoft Azure (Brazil South region, primary)
- **Compute:** Containerized (Docker), orchestrated via Azure App Service or AKS
- **No multi-tenant shared database** — each organization has isolated data within the same database using workspace-level encryption keys

---

## 3. Data Safety and the DSS Principle

### Decision Support System (DSS) — Read-Only by Design

CauSium operates as a Decision Support System. It provides recommendations and visibility but **never executes changes** against customer cloud infrastructure.

**Enforcement mechanisms:**

| Layer | Control | Evidence |
|-------|---------|----------|
| Cloud credentials | Only Reader/Viewer roles accepted during onboarding | `docs/security/cloud-read-only-onboarding.md` |
| Code guardrail | CI blocks any code containing mutative cloud SDK patterns | `scripts/cloud_mutation_guardrail.py` |
| Allowlist | Narrow exceptions require documented justification | `.security/cloud_mutation_guardrail_allowlist.txt` |
| Architecture | Worker processes only call read APIs (list, get, describe) | `backend/app/workers/ingestion_worker.py` |

**What this means for customers:**
- CauSium cannot modify, delete, or create resources in your cloud accounts
- Even if CauSium were fully compromised, the attacker gains read-only access to billing data — not infrastructure control
- You can revoke access at any time by removing the Reader role assignment

---

## 4. Authentication and Access Control

### Authentication Methods

| Method | Description | Strength |
|--------|-------------|----------|
| Email + Password | Minimum 8 characters, bcrypt hashed | Standard |
| TOTP (MFA) | Time-based one-time passwords (RFC 6238) | Strong |
| Passkeys (WebAuthn) | FIDO2 hardware/platform authenticators | Very Strong |
| OIDC (Azure AD) | Federated SSO via OpenID Connect | Enterprise |

### Role-Based Access Control (RBAC)

| Role | Capabilities | Typical User |
|------|-------------|--------------|
| Viewer | Read dashboards and reports | Stakeholders |
| Engineer | View + manage cloud accounts | DevOps engineers |
| FinOps | View + financial reports + budgets | Finance team |
| Executive | View + executive dashboards | C-level |
| Admin | All above + manage members + workspace settings | Team lead |
| Platform Admin | Super-admin (CauSium internal only) | CauSium support |

### Session Security

- JWT access tokens (short-lived: 15 minutes)
- Refresh tokens (longer-lived, rotated on use)
- HttpOnly, Secure, SameSite=Strict cookies
- Token blacklisting on logout/password change
- Global session revocation (`/auth/logout-all`)

---

## 5. Encryption

### Data at Rest

| Data | Encryption Method | Key Management |
|------|-------------------|----------------|
| Sensitive fields (credentials, secrets) | Fernet (AES-128-CBC + HMAC-SHA256) | Per-workspace keys, automatically rotated |
| Database storage | Azure Storage Service Encryption (AES-256) | Azure-managed keys |
| Backup files | Inherited from storage encryption | Azure-managed |

### Data in Transit

| Path | Encryption | Configuration |
|------|-----------|---------------|
| Browser → Frontend | TLS 1.2+ | HSTS enforced |
| Frontend → Backend | TLS 1.2+ | Certificate pinning (optional) |
| Backend → Database | TLS (PostgreSQL `sslmode=require`) | Azure-enforced |
| Worker → Cloud APIs | TLS 1.2+ | Provider-enforced |

### Key Rotation

- Per-workspace encryption keys are automatically rotated by the `keyring_rotation_worker`
- Rotation interval and maximum key age are configurable
- Old keys are retained (read-only) until all data is re-encrypted
- Application secret key and encryption key must be unique per environment (enforced by startup guards)

---

## 6. Audit Trail

CauSium maintains an immutable, cryptographically verifiable audit chain for all security-relevant actions.

### Design

- **Hash chain:** Each event contains the SHA-256 hash of the previous event, forming a tamper-evident chain
- **HMAC checkpoints:** Periodic snapshots signed with the application secret key for independent verification
- **Per-organization:** Each workspace has its own audit chain (no cross-tenant leakage)

### Events Tracked

| Category | Examples |
|----------|----------|
| Identity | User creation, deactivation, role changes, MFA enable/disable |
| Access | Login, logout, password changes, passkey registration |
| Data | LGPD export, LGPD purge, data deletion |
| Cloud | Account onboarding, sync completion, ingestion failures |
| Governance | Budget alerts, anomaly detection, support access |
| Admin | Platform admin actions, force suspend/restore |

### Verification

- `GET /api/v1/audit-chain/verify` — recomputes all hashes from genesis and reports integrity
- `GET /api/v1/audit-chain/checkpoints` — lists HMAC-signed checkpoints
- JSONL export available for external audit tools

---

## 7. LGPD Compliance

CauSium is designed for compliance with the Brazilian General Data Protection Law (Lei nº 13.709/2018).

### Data Subject Rights (Art. 18)

| Right | Implementation | How to Exercise |
|-------|---------------|-----------------|
| Access | JSON export of all personal data | `GET /api/v1/auth/me/export` or contact DPO |
| Correction | Self-service profile edit | Platform UI or API |
| Deletion | Irreversible anonymization | `DELETE /api/v1/auth/me/data` or contact DPO |
| Portability | Machine-readable JSON export | `GET /api/v1/auth/me/export` |
| Consent revocation | Account deletion + data purge | Contact DPO |

### Consent Management

- Terms acceptance is recorded with version and timestamp
- When terms are updated, users must re-accept before accessing the platform
- Consent records are retained for 5 years (legal obligation) even after account deletion

### DPO Contact

- Public endpoint: `GET /legal/dpo-contact`
- Email: configurable per deployment (default: `dpo@causium.io`)
- Response time: 15 business days (LGPD Art. 18 §5)

### Data Minimization

- Only billing/cost data is ingested (not workload data, logs, or secrets)
- Cloud access is read-only (Reader/Viewer roles)
- PII is limited to user identity (name, email) — no sensitive categories (Art. 11)

---

## 8. Infrastructure Security

### CI/CD Pipeline Security

| Control | Description |
|---------|-------------|
| Secret scanning | Gitleaks blocks commits containing secrets |
| SAST | Bandit scans Python code for security issues |
| SCA | pip-audit + npm audit check for known vulnerabilities |
| Cloud guardrail | Blocks mutative cloud SDK patterns in code |
| Type checking | MyPy + TypeScript strict mode |
| Test gates | All tests must pass before merge |
| Security baseline | Known exceptions tracked with owner, ticket, and expiry |

### Runtime Security

| Control | Description |
|---------|-------------|
| Production startup guards | Application refuses to start with default keys |
| Security headers | HSTS, CSP, X-Frame-Options, X-Content-Type-Options |
| Rate limiting | Per-IP and per-user rate limits on auth endpoints |
| Input validation | Pydantic schemas on all API inputs |
| SQL injection prevention | SQLAlchemy ORM with parameterized queries |
| CORS | Strict origin allowlist |

### Monitoring and Alerting

| Signal | Detection | Response |
|--------|-----------|----------|
| API error rate > 1% | Prometheus alert rule | On-call notification |
| p95 latency > 500ms | Prometheus alert rule | Performance investigation |
| Worker crash | Heartbeat stale + crash alert | Auto-restart + notification |
| DLQ accumulation | Prometheus alert rule | Pipeline investigation |
| Backup overdue | Prometheus alert rule | Ops team notification |

---

## 9. Shared Responsibility Model

| Responsibility | CauSium | Customer |
|---------------|---------|----------|
| Platform application security | ✓ | |
| Data encryption (at rest and in transit) | ✓ | |
| Authentication and access control | ✓ | |
| Audit trail integrity | ✓ | |
| LGPD compliance (platform) | ✓ | |
| Cloud account credential management | | ✓ |
| Granting appropriate (read-only) roles | Guidance provided | ✓ |
| User access reviews within organization | Tools provided | ✓ |
| Compliance with own regulatory requirements | | ✓ |
| Network security of own cloud accounts | | ✓ |
| Incident response (own infrastructure) | | ✓ |
| Incident response (CauSium platform) | ✓ | Notification |

---

## 10. Customer Integration Guidelines

### Least Privilege Setup

1. **Cloud accounts:** Grant only Reader/Viewer roles (Azure Reader, AWS ReadOnlyAccess, GCP Viewer)
2. **User roles:** Assign the minimum role needed (Viewer for stakeholders, Engineer for operators)
3. **MFA:** Enforce MFA for all admin users (configurable per organization)
4. **SSO:** Use OIDC (Azure AD) for centralized identity management when available

### Workspace Isolation

- Each organization operates in an isolated workspace
- Data is encrypted with per-workspace keys
- No cross-workspace data access is possible (enforced at query layer)
- Platform Admin access is audited and time-bounded

### API Security

- All API calls require valid JWT authentication
- Tokens are short-lived (15 min) and must be refreshed
- Rate limits apply to prevent abuse
- All actions are logged in the audit chain

---

## 11. Incident Response

### Current Capabilities

- Operational alerting module dispatches notifications on critical events
- Audit chain provides forensic trail for investigation
- Backup/restore automation enables rapid recovery (RTO < 5 min self-managed)
- Token revocation enables immediate session termination

### Reporting Security Issues

- Email: security@causium.io (or DPO contact)
- Expected response time: 24 hours for acknowledgment
- Critical vulnerabilities: immediate escalation to engineering team

### Incident Communication

- Affected customers notified within 72 hours of confirmed data breach (LGPD Art. 48)
- Status page updates for service availability incidents
- Post-incident report provided for significant events

---

## 12. Compliance Status

| Framework | Status | Notes |
|-----------|--------|-------|
| LGPD (Lei 13.709/2018) | **Implemented** | Consent, rights, DPO, ROPA, purge |
| SOC 2 Type I | **In preparation** | Self-assessment complete; formal audit planned |
| SOC 2 Type II | **Roadmap** | Requires 6–12 months of operating evidence |
| ISO 27001 | **Not started** | Future consideration based on customer demand |
| PCI DSS | **Not applicable** | CauSium does not process payment card data |
| HIPAA | **Not applicable** | CauSium does not process health data |

### What We Do NOT Claim

- We do not claim SOC 2 certification (audit not yet completed)
- We do not claim ISO 27001 certification
- We do not guarantee zero vulnerabilities (no software can)
- We do not provide legal advice on customer compliance obligations

---

## 13. Limitations and Known Boundaries

| Area | Limitation | Mitigation |
|------|-----------|------------|
| Penetration testing | Not yet formally executed | Pentest plan drafted; engagement planned |
| Formal incident response plan | Documented but not drilled with external parties | DR drills conducted quarterly |
| Multi-region failover | Single-region deployment (Brazil South) | Azure availability zones; cross-region planned |
| Backup automation | ClickHouse backups are script-based, not fully automated | Cron scheduling documented; automation planned |
| Security training | No formal program yet | Planned for SOC 2 readiness |

---

## 14. Contact

| Purpose | Contact |
|---------|---------|
| Security issues | security@causium.io |
| Data protection (DPO) | dpo@causium.io |
| General inquiries | contact@causium.io |
| Platform status | `GET /health` |

---

*This document reflects the security posture as of the last updated date. Security is an ongoing process — controls are continuously evaluated and improved. For the most current information, contact the security team.*
