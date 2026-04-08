from fastapi import APIRouter

from app.domains.auth.router import router as auth_router
from app.domains.cloud_accounts.router import router as accounts_router
from app.domains.cloud_ledger.router import router as ledger_router
from app.domains.decision_engine.router import router as opportunities_router
from app.domains.executive.router import router as executive_router
from app.domains.workflow.router import router as workflow_router
from app.domains.experiments.router import router as experiments_router
from app.domains.risk_budgets.router import router as risk_budgets_router
from app.domains.change_events.router import router as change_events_router
from app.domains.audit_chain.router import router as audit_chain_router
from app.domains.workspaces.router import router as workspaces_router
from app.domains.invites.router import router as invites_router
from app.domains.admin.router import router as admin_router
from app.domains.economics.router import router as economics_router
from app.domains.notifications.router import router as notifications_router
from app.domains.gov.router import router as gov_router
from app.domains.green.router import router as green_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth_router)
api_router.include_router(accounts_router)
api_router.include_router(ledger_router)
api_router.include_router(opportunities_router)
api_router.include_router(workflow_router)
api_router.include_router(executive_router)
api_router.include_router(experiments_router)
api_router.include_router(risk_budgets_router)
api_router.include_router(change_events_router)
api_router.include_router(audit_chain_router)
api_router.include_router(workspaces_router)
api_router.include_router(invites_router)
api_router.include_router(admin_router)
api_router.include_router(economics_router)
api_router.include_router(notifications_router)
api_router.include_router(gov_router)
api_router.include_router(green_router)
