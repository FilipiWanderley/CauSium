# OP08 Security Gates Policy

## Objective
Define merge-blocking security policy and baseline exception governance.

## Merge Blocking Rules
- gitleaks: any finding blocks merge.
- bandit: high confidence/high severity findings block merge.
- pip-audit: any known vulnerability blocks merge unless exception exists.
- npm audit: critical vulnerabilities block merge unless exception exists.

## Exception Baseline
Baseline file: `.security/security_baseline.json`

Each exception entry must include:
- `id`: scanner finding identifier
- `reason`: technical justification
- `owner`: accountable engineer/team
- `ticket`: tracking ticket (Jira/GitHub issue)
- `expires_on`: ISO date (YYYY-MM-DD)

Expired exceptions fail CI automatically.

## Review Requirements
- Every exception must be approved in PR review.
- Every exception must have expiration and remediation plan.
- Security exceptions must be removed once remediation lands.

## Operational Runbook
1. Fix finding at source whenever feasible.
2. If temporary exception is needed, add entry to baseline with expiry.
3. Link the exception to a remediation ticket.
4. Validate baseline and CI security job before merge.
5. Remove exception after patch is released.
