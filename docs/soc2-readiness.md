# SOC 2 Type I Readiness Assessment

## Document Control

| Field | Value |
|-------|-------|
| Version | 1.0 (Draft) |
| Status | Self-assessment — not auditor-verified |
| Owner | Security Lead / CTO |
| Last Updated | 2025-01-01 |
| Target Audit Date | TBD (90-day roadmap item) |

## 1. Overview

This document maps CauSium's existing controls against SOC 2 Trust Service Criteria (TSC) to identify readiness for a Type I audit. SOC 2 Type I evaluates the design of controls at a point in time; Type II evaluates operating effectiveness over a period (typically 6–12 months).

**Target Trust Service Categories:**
- Security (Common Criteria) — required for all SOC 2
- Availability — relevant for SaaS platform
- Confidentiality — relevant for customer cost/financial data
- Processing Integrity — relevant for audit chain and data accuracy

**Not in initial scope:**
- Privacy — covered separately by LGPD ROPA (see `docs/lgpd-ropa.md`)

## 2. Control Mapping

### CC1 — Control Environment

| Criteria | Requirement | Current State | Evidence | Gap |
|----------|-------------|---------------|----------|-----|
| CC1.1 | Commitment to integrity and ethical values | Partial | Code of conduct (implicit in team culture) | No formal written code of conduct |
| CC1.2 | Board/management oversight | Partial | CTO oversight of security decisions | No formal security committee or charter |
| CC1.3 | Organizational structure with authority | Partial | Role-based access in platform (RBAC) | No formal org chart with security responsibilities |
| CC1.4 | Commitment to competence | Partial | Hiring practices, code review requirements | No formal security training program |
| CC1.5 | Accountability for controls | Partial | CI gates enforce security checks | No formal control owner matrix |

**Recommended actions:**
- [ ] Draft a security policy document (information security policy)
- [ ] Define a security committee (even if 2–3 people)
- [ ] Create a control owner matrix mapping controls to individuals

### CC2 — Communication and Information

| Criteria | Requirement | Current State | Evidence | Gap |
|----------|-------------|---------------|----------|-----|
| CC2.1 | Internal communication of objectives | Partial | PRD docs, roadmap docs in repo | No formal security awareness program |
| CC2.2 | Internal communication of responsibilities | Partial | CODEOWNERS, PR review requirements | No formal RACI for security |
| CC2.3 | External communication | Partial | `/legal/dpo-contact` endpoint, DPO email | No public security policy page or trust center |

**Recommended actions:**
- [ ] Publish a security policy page (trust center)
- [ ] Implement security awareness training (annual)
- [ ] Create a responsible disclosure / bug bounty policy

### CC3 — Risk Assessment

| Criteria | Requirement | Current State | Evidence | Gap |
|----------|-------------|---------------|----------|-----|
| CC3.1 | Risk identification | Partial | Pentest plan drafted, SAST in CI | No formal risk register |
| CC3.2 | Risk analysis (likelihood + impact) | Partial | SLO targets defined, RTO/RPO documented | No formal risk scoring methodology |
| CC3.3 | Fraud risk consideration | Minimal | Audit chain tracks admin actions | No formal fraud risk assessment |
| CC3.4 | Change management risk | Partial | CI gates, cloud mutation guardrail | No formal change advisory board |

**Recommended actions:**
- [ ] Create a risk register with likelihood/impact scoring
- [ ] Document change management process formally
- [ ] Conduct annual risk assessment

### CC4 — Monitoring Activities

| Criteria | Requirement | Current State | Evidence | Gap |
|----------|-------------|---------------|----------|-----|
| CC4.1 | Ongoing monitoring | Strong | Prometheus metrics, SLO snapshot, worker heartbeat, alerting rules | Need to verify alerts reach humans (Alertmanager routing) |
| CC4.2 | Deficiency evaluation | Partial | DLQ monitoring, health checks, CI failure blocking | No formal deficiency tracking process |

**Evidence in code:**
- `monitoring/rules.yml` — 9 alerting rules
- `backend/app/core/observability.py` — SLI/SLO computation
- `backend/app/core/alerting.py` — operational alert dispatch
- `backend/app/workers/runner.py` — worker heartbeat + crash alerting

### CC5 — Control Activities

| Criteria | Requirement | Current State | Evidence | Gap |
|----------|-------------|---------------|----------|-----|
| CC5.1 | Selection of control activities | Strong | Multiple layers: CI gates, runtime guards, audit chain | Document the control selection rationale |
| CC5.2 | Technology general controls | Strong | See detailed mapping below | Minor gaps in formal documentation |
| CC5.3 | Deployment through policies | Partial | CI enforces; no written deployment policy | Formalize deployment/release policy |

### CC6 — Logical and Physical Access Controls

| Criteria | Requirement | Current State | Evidence | Gap |
|----------|-------------|---------------|----------|-----|
| CC6.1 | Logical access security | Strong | RBAC (6 roles), JWT tokens, MFA (TOTP), passkeys | ✓ |
| CC6.2 | Access provisioning | Strong | Invite-based onboarding, admin-controlled roles | ✓ |
| CC6.3 | Access removal | Strong | Soft-delete, deactivation, LGPD purge, token revocation | ✓ |
| CC6.4 | Access review | Partial | Admin can list members, no periodic review automation | Add periodic access review reminder |
| CC6.5 | Authentication mechanisms | Strong | Password + MFA + Passkeys + OIDC (Azure AD) | ✓ |
| CC6.6 | Encryption of data | Strong | Fernet encryption (at-rest), TLS (in-transit), per-workspace keys | ✓ |
| CC6.7 | Restriction of privileged access | Strong | Platform Admin role, support access audit trail | ✓ |
| CC6.8 | Physical access | N/A | Cloud-hosted (Azure responsibility) | N/A |

**Evidence in code:**
- `backend/app/domains/auth/models.py` — User model with roles, MFA fields
- `backend/app/core/security.py` — JWT, Fernet encryption, key rotation
- `backend/app/workers/keyring_rotation_worker.py` — automatic key rotation
- `backend/app/domains/auth/router.py` — MFA, passkey, OIDC endpoints
- `backend/app/core/config.py` — production startup guards (reject default keys)

### CC7 — System Operations

| Criteria | Requirement | Current State | Evidence | Gap |
|----------|-------------|---------------|----------|-----|
| CC7.1 | Detection of anomalies | Strong | Anomaly detection worker, SLO breach alerts, DLQ monitoring | ✓ |
| CC7.2 | Incident response | Partial | Alerting module exists, escalation via email | No formal incident response plan |
| CC7.3 | Recovery from incidents | Strong | Backup/restore scripts, DR drill checklist, RTO/RPO targets | ✓ |
| CC7.4 | Business continuity | Partial | DR runbook exists, automated drill script | No formal BCP document |

**Evidence in code:**
- `backend/app/workers/anomaly_detection_worker.py` — cost anomaly detection
- `scripts/backup.sh`, `scripts/restore.sh`, `scripts/rto_rpo_test.sh` — DR automation
- `docs/runbooks/backup-restore.md` — DR drill checklist
- `backend/app/core/alerting.py` — operational alerting

### CC8 — Change Management

| Criteria | Requirement | Current State | Evidence | Gap |
|----------|-------------|---------------|----------|-----|
| CC8.1 | Change authorization | Strong | PR-based workflow, CI gates block unauthorized changes | ✓ |
| CC8.2 | Change testing | Strong | Automated tests (pytest, vitest), typecheck, SAST | ✓ |
| CC8.3 | Change deployment | Partial | CI/CD pipeline exists | Formalize rollback procedures |

**Evidence in code:**
- `.github/workflows/ci.yml` — CI pipeline (security gates, tests, typecheck)
- `docs/security/OP08_Security_Gates_Policy.md` — merge-blocking policy
- `scripts/cloud_mutation_guardrail.py` — prevents accidental cloud mutations
- `docs/operations/Rollback_Runbook.md` — rollback procedures

### CC9 — Risk Mitigation (Vendor Management)

| Criteria | Requirement | Current State | Evidence | Gap |
|----------|-------------|---------------|----------|-----|
| CC9.1 | Vendor risk assessment | Minimal | Dependencies pinned, pip-audit + npm audit in CI | No formal vendor risk register |
| CC9.2 | Vendor monitoring | Partial | Automated SCA scanning in CI | No periodic vendor review process |

**Recommended actions:**
- [ ] Create a vendor/sub-processor register
- [ ] Document vendor selection criteria
- [ ] Implement periodic dependency review (quarterly)

## 3. Availability Criteria

| Criteria | Requirement | Current State | Evidence | Gap |
|----------|-------------|---------------|----------|-----|
| A1.1 | Capacity planning | Partial | Docker resource limits, uvicorn workers configurable | No formal capacity plan |
| A1.2 | Recovery objectives | Strong | RTO ≤ 5 min (self-managed), RPO ≤ 24h (ClickHouse) | ✓ |
| A1.3 | Backup and recovery testing | Strong | Automated DR drill script with pass/fail | ✓ |

## 4. Confidentiality Criteria

| Criteria | Requirement | Current State | Evidence | Gap |
|----------|-------------|---------------|----------|-----|
| C1.1 | Identification of confidential data | Partial | Cost data, credentials, PII identified in code | No formal data classification policy |
| C1.2 | Disposal of confidential data | Strong | LGPD purge (anonymization), soft-delete with retention | ✓ |

## 5. Processing Integrity Criteria

| Criteria | Requirement | Current State | Evidence | Gap |
|----------|-------------|---------------|----------|-----|
| PI1.1 | Accuracy and completeness | Strong | Audit chain with SHA-256 hash verification, HMAC checkpoints | ✓ |
| PI1.2 | Timely processing | Partial | SLO targets defined, worker monitoring | No formal SLA document |
| PI1.3 | Input validation | Strong | Pydantic schemas, field validators throughout API | ✓ |

**Evidence in code:**
- `backend/app/domains/audit_chain/` — full hash-chain implementation
- `backend/app/domains/audit_chain/service.py` — chain verification, HMAC checkpoints
- `backend/app/domains/auth/schemas.py` — Pydantic validation

## 6. Gap Summary and Prioritization

### Critical Gaps (must resolve before Type I)

| # | Gap | Effort | Owner |
|---|-----|--------|-------|
| 1 | No formal Information Security Policy | Medium | Security Lead |
| 2 | No formal Incident Response Plan | Medium | Security Lead |
| 3 | No formal Risk Register | Medium | CTO |
| 4 | No formal Change Management Policy (written) | Low | Engineering Lead |

### Important Gaps (should resolve before Type I)

| # | Gap | Effort | Owner |
|---|-----|--------|-------|
| 5 | No security awareness training program | Medium | HR / Security |
| 6 | No vendor/sub-processor risk register | Low | Security Lead |
| 7 | No formal data classification policy | Low | Security Lead |
| 8 | No public trust center / security page | Low | Marketing / Security |
| 9 | No periodic access review automation | Low | Engineering |
| 10 | No formal Business Continuity Plan | Medium | CTO |

### Strengths (ready for audit)

- Immutable audit chain with cryptographic verification
- Automated key rotation (per-workspace)
- Multi-factor authentication (TOTP + Passkeys + OIDC)
- Role-based access control (6 roles, least privilege)
- CI security gates (SAST, SCA, secrets scanning) — merge-blocking
- Cloud mutation guardrail (DSS principle)
- LGPD compliance (consent, export, purge, DPO contact)
- Backup/restore automation with RTO/RPO measurement
- Production startup guards (reject default keys)
- Prometheus alerting rules for SLO breaches

## 7. Recommended Timeline

| Week | Action |
|------|--------|
| 1–2 | Draft Information Security Policy, Incident Response Plan |
| 3–4 | Create Risk Register, Change Management Policy |
| 5–6 | Vendor register, data classification policy |
| 7–8 | Security awareness training (first session) |
| 9–10 | Internal readiness review (mock audit) |
| 11–12 | Engage SOC 2 auditor for Type I assessment |

---

*This is a self-assessment. Formal SOC 2 Type I certification requires engagement with an accredited CPA firm (e.g., Deloitte, EY, or specialized firms like Vanta/Drata-partnered auditors).*
