# LGPD ROPA — Record of Processing Activities

## Document Control

| Field | Value |
|-------|-------|
| Version | 1.0 (Draft) |
| Status | Internal draft — requires DPO review |
| Owner | Data Protection Officer (DPO) |
| Last Updated | 2025-01-01 |
| Legal Basis | LGPD Art. 37 — Registro das Atividades de Tratamento |
| Controller | CauSium Tecnologia Ltda. |
| DPO Contact | dpo@causium.io |

## 1. Purpose

This document fulfills the requirement under LGPD Art. 37 for controllers to maintain a record of personal data processing activities. It describes what personal data CauSium processes, why, on what legal basis, for how long, and with what safeguards.

## 2. Processing Activities

### PA-01: User Registration and Authentication

| Field | Value |
|-------|-------|
| **Activity** | User account creation, authentication, and session management |
| **Data Subjects** | Platform users (employees of customer organizations) |
| **Personal Data** | Email address, full name, hashed password, MFA secrets (TOTP), passkey credentials, IP address (in logs) |
| **Purpose** | Provide secure access to the platform; enforce identity verification |
| **Legal Basis** | LGPD Art. 7, V — Execution of contract (SaaS subscription) |
| **Retention** | Active account: duration of contract. Deleted account: anonymized within 30 days of LGPD purge request |
| **Recipients** | None (processed internally only) |
| **International Transfer** | No (data stored in Azure Brazil South) |
| **Code Reference** | `backend/app/domains/auth/models.py`, `backend/app/domains/auth/service.py` |

### PA-02: Terms of Service Consent

| Field | Value |
|-------|-------|
| **Activity** | Recording user acceptance of terms of service and privacy policy |
| **Data Subjects** | Platform users |
| **Personal Data** | Consent timestamp (`terms_accepted_at`), terms version accepted |
| **Purpose** | Demonstrate lawful consent under LGPD Art. 8; enable re-consent on terms update |
| **Legal Basis** | LGPD Art. 7, I — Consent |
| **Retention** | Duration of account + 5 years (legal obligation for consent records) |
| **Recipients** | None |
| **International Transfer** | No |
| **Code Reference** | `backend/app/domains/auth/models.py` (fields: `terms_accepted_at`, `terms_version`), `backend/app/domains/auth/router.py` (`/accept-terms`) |

### PA-03: Audit Trail

| Field | Value |
|-------|-------|
| **Activity** | Recording security-relevant actions for accountability and non-repudiation |
| **Data Subjects** | Platform users (actors performing actions) |
| **Personal Data** | User ID (UUID), action performed, timestamp, IP address (in request context) |
| **Purpose** | Security monitoring, incident investigation, compliance evidence |
| **Legal Basis** | LGPD Art. 7, II — Legal obligation (security accountability) |
| **Retention** | 5 years (aligned with Brazilian commercial record-keeping requirements) |
| **Recipients** | Auditors (upon formal request, under NDA) |
| **International Transfer** | No |
| **Code Reference** | `backend/app/domains/audit_chain/models.py`, `backend/app/domains/audit_chain/service.py` |

### PA-04: Cloud Cost and Usage Data Ingestion

| Field | Value |
|-------|-------|
| **Activity** | Ingesting cloud provider billing and usage data for cost optimization analysis |
| **Data Subjects** | Indirect — cloud resource metadata may contain resource names referencing individuals |
| **Personal Data** | Minimal: resource tags/names that may include personal identifiers (e.g., "vm-joao-dev") |
| **Purpose** | Provide cost visibility, optimization recommendations, and anomaly detection |
| **Legal Basis** | LGPD Art. 7, V — Execution of contract; Art. 7, IX — Legitimate interest (cost optimization) |
| **Retention** | 24 months rolling (configurable per organization) |
| **Recipients** | None (data stays within customer's workspace) |
| **International Transfer** | No (data stored in Azure Brazil South; read-only access to customer's cloud accounts) |
| **Code Reference** | `backend/app/workers/ingestion_worker.py`, `backend/app/domains/economics/` |

### PA-05: Notification and Communication

| Field | Value |
|-------|-------|
| **Activity** | Sending operational notifications (email, in-app) to users |
| **Data Subjects** | Platform users |
| **Personal Data** | Email address, notification preferences, notification content |
| **Purpose** | Inform users of relevant events (anomalies, budget alerts, system status) |
| **Legal Basis** | LGPD Art. 7, V — Execution of contract |
| **Retention** | 90 days (notification history), then purged |
| **Recipients** | SMTP provider (for email delivery) — see sub-processors |
| **International Transfer** | Depends on SMTP provider configuration (see Section 5) |
| **Code Reference** | `backend/app/workers/notification_worker.py`, `backend/app/core/email.py` |

### PA-06: Support Access (Privileged)

| Field | Value |
|-------|-------|
| **Activity** | Platform admin accessing customer workspace for support purposes |
| **Data Subjects** | Customer organization users (indirectly observed) |
| **Personal Data** | Workspace data visible during support session |
| **Purpose** | Technical support, incident resolution |
| **Legal Basis** | LGPD Art. 7, V — Execution of contract (support SLA) |
| **Retention** | Access event logged in audit chain indefinitely; no data copied |
| **Recipients** | None |
| **International Transfer** | No |
| **Code Reference** | Audit events: `platform.support_access.start`, `platform.support_access.end` |

### PA-07: LGPD Rights Exercise

| Field | Value |
|-------|-------|
| **Activity** | Processing data subject requests (access, export, deletion/anonymization) |
| **Data Subjects** | Platform users exercising LGPD Art. 18 rights |
| **Personal Data** | All personal data associated with the requesting user |
| **Purpose** | Fulfill legal obligation under LGPD Art. 18 |
| **Legal Basis** | LGPD Art. 7, II — Legal obligation |
| **Retention** | Request metadata: 5 years. Purged data: irreversibly anonymized |
| **Recipients** | Data subject (for export); none otherwise |
| **International Transfer** | No |
| **Code Reference** | `backend/app/domains/auth/service.py` (`export_user_data`, `lgpd_purge_user`), `backend/app/domains/auth/router.py` (`/me/export`, `/me/data`) |

## 3. Categories of Data Subjects

| Category | Description | Approximate Volume |
|----------|-------------|-------------------|
| Platform Users | Employees of customer organizations who use CauSium | Hundreds to low thousands |
| Organization Admins | Users with admin role managing their workspace | 1–5 per organization |
| Platform Admins | CauSium internal staff with super-admin access | < 5 |

## 4. Categories of Personal Data

| Category | Examples | Sensitivity |
|----------|----------|-------------|
| Identity Data | Full name, email address | Standard |
| Authentication Data | Hashed password, TOTP secret, passkey credentials | High (encrypted at rest) |
| Consent Records | Terms version, acceptance timestamp | Standard |
| Activity Logs | Actions performed, timestamps, IP addresses | Standard |
| Cloud Resource Metadata | Resource names/tags (may contain personal references) | Low (indirect) |
| Communication Data | Email addresses for notifications | Standard |

## 5. Sub-Processors

| Processor | Purpose | Data Accessed | Location | DPA Status |
|-----------|---------|---------------|----------|------------|
| Microsoft Azure | Infrastructure hosting (compute, storage, database) | All data (encrypted at rest) | Brazil South (primary) | Azure DPA in effect |
| SMTP Provider (TBD) | Email delivery for notifications and password resets | Email addresses, notification content | TBD | TBD — require DPA before production |
| Jaeger/OTLP Collector | Distributed tracing (operational) | Request metadata, trace IDs (no PII by design) | Self-hosted (Azure) | N/A (self-managed) |

**Note:** CauSium does NOT share personal data with advertising networks, analytics platforms, or data brokers.

## 6. Technical and Organizational Measures (TOMs)

| Measure | Implementation | Code Reference |
|---------|---------------|----------------|
| Encryption at rest | Fernet encryption for sensitive fields; Azure disk encryption | `backend/app/core/security.py` |
| Encryption in transit | TLS 1.2+ enforced; HSTS headers | `backend/app/core/middleware.py` |
| Access control | RBAC with 6 roles; principle of least privilege | `backend/app/domains/auth/models.py` (UserRole) |
| Authentication | Password + MFA (TOTP/Passkeys) + OIDC | `backend/app/domains/auth/router.py` |
| Key management | Automatic per-workspace key rotation | `backend/app/workers/keyring_rotation_worker.py` |
| Audit trail | Immutable hash chain with HMAC checkpoints | `backend/app/domains/audit_chain/` |
| Data minimization | Read-only cloud access; no customer infra mutation | `scripts/cloud_mutation_guardrail.py` |
| Pseudonymization | LGPD purge anonymizes all PII fields | `backend/app/domains/auth/service.py` (`lgpd_purge_user`) |
| Backup & recovery | Automated backup/restore with RTO/RPO measurement | `scripts/backup.sh`, `scripts/restore.sh` |
| Vulnerability management | SAST (Bandit), SCA (pip-audit, npm audit), secrets scanning (gitleaks) | `.github/workflows/ci.yml` |
| Incident detection | Prometheus alerting, SLO monitoring, DLQ alerts | `monitoring/rules.yml`, `backend/app/core/alerting.py` |

## 7. Data Subject Rights Implementation

| Right (LGPD Art. 18) | Implementation | Endpoint |
|----------------------|----------------|----------|
| II — Access | Full data export in JSON | `GET /api/v1/auth/me/export` |
| III — Correction | User can update profile; admin can edit | `PATCH /api/v1/auth/me`, `PATCH /api/v1/auth/users/{id}` |
| IV — Anonymization/deletion | LGPD purge (irreversible anonymization) | `DELETE /api/v1/auth/me/data` |
| V — Portability | JSON export (machine-readable) | `GET /api/v1/auth/me/export` |
| VI — Deletion of consent-based data | Same as IV (full purge) | `DELETE /api/v1/auth/me/data` |
| VII — Information about sharing | DPO contact endpoint lists processors | `GET /legal/dpo-contact` |
| IX — Revocation of consent | Account deletion + data purge | `DELETE /api/v1/auth/me/data` |

## 8. Data Flow Diagram (Simplified)

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│   Browser   │────▶│  Frontend    │────▶│   Backend API   │
│  (User)     │◀────│  (React SPA) │◀────│   (FastAPI)     │
└─────────────┘     └──────────────┘     └────────┬────────┘
                                                   │
                    ┌──────────────────────────────┼──────────────────┐
                    │                              │                  │
              ┌─────▼─────┐  ┌─────────────┐  ┌──▼──────────┐  ┌───▼────┐
              │ PostgreSQL │  │  ClickHouse │  │   Redis     │  │ Worker │
              │ (PII, auth │  │ (cost data, │  │ (queues,    │  │ (async │
              │  audit)    │  │  analytics) │  │  cache)     │  │  jobs) │
              └────────────┘  └─────────────┘  └─────────────┘  └────────┘
                                                                     │
                                                              ┌──────▼──────┐
                                                              │ Cloud APIs  │
                                                              │ (read-only) │
                                                              └─────────────┘
```

## 9. Retention Schedule

| Data Category | Retention Period | Deletion Method | Trigger |
|---------------|----------------|-----------------|---------|
| Active user accounts | Duration of contract | N/A (active) | — |
| Deleted user data | Anonymized within 30 days | `lgpd_purge_user()` | User request or admin action |
| Audit chain events | 5 years | Automated cleanup | Time-based |
| Cost/usage data | 24 months rolling | ClickHouse TTL or manual purge | Time-based |
| Notification history | 90 days | Automated cleanup | Time-based |
| Consent records | Account lifetime + 5 years | Retained even after purge (legal obligation) | — |
| Backup files | 30 days (production) | Automated rotation | Time-based |

## 10. DPIA Requirement Assessment

Under LGPD Art. 38, a Data Protection Impact Assessment (DPIA) may be required when processing presents high risk. Assessment:

| Factor | CauSium Context | Risk Level |
|--------|----------------|------------|
| Large-scale processing | No — limited to customer employees (not public) | Low |
| Sensitive data (Art. 11) | No — no health, biometric, political, religious data | Low |
| Automated decision-making | No — platform provides recommendations, humans decide | Low |
| Systematic monitoring | No — monitors cloud costs, not individuals | Low |
| Cross-referencing datasets | No — each workspace is isolated | Low |

**Conclusion:** A full DPIA is not currently required, but should be reassessed if:
- Processing volume exceeds 10,000 data subjects
- Automated decision-making is introduced (e.g., auto-remediation)
- Biometric authentication is added (beyond passkeys)

---

*This ROPA should be reviewed by the DPO annually or whenever a new processing activity is introduced. It must be made available to the ANPD (Autoridade Nacional de Proteção de Dados) upon request.*
