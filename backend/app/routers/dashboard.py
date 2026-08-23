from fastapi import APIRouter, Depends
from ..auth import require_internal, UserContext
from ..database import get_proactive_issues

router = APIRouter(tags=["dashboard"])


@router.get("/issues")
def get_issues(user: UserContext = Depends(require_internal)):
    """Proactive issue detection — internal users only."""
    issues = get_proactive_issues()
    return {"issues": issues, "total": len(issues)}
