## Summary
- What changed and why?

## Security Findings
- [ ] No security findings introduced
- [ ] Findings introduced and fixed in this PR
- [ ] Exception requested (requires justification below)

If exception requested, fill all fields:
- Scanner: (bandit | pip_audit | npm_audit | gitleaks)
- Finding ID: 
- Severity: 
- Justification: 
- Owner: 
- Ticket: 
- Expiration (YYYY-MM-DD): 

## Validation Evidence
- [ ] Backend tests pass
- [ ] Frontend build/typecheck pass
- [ ] CI security job passes
- [ ] Relevant benchmark/latency evidence attached (when performance-related)

## Cloud Safety Checklist
- [ ] Nao adiciona mutacao cloud
- [ ] Nao chama APIs `create/update/delete/patch/scale`
- [ ] Mantem credenciais read-only
- [ ] Se houver excecao, exige feature flag + aprovacao explicita
