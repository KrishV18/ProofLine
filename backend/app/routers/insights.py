"""Insights router."""

from typing import Any, Dict, List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.roles import Role, get_current_user, require_role
from app.db import get_db
from app.models.user import User
from app.services.workflow.insights_service import get_rule_insights

router = APIRouter(prefix="/insights", tags=["insights"])


@router.get("/rules")
async def get_rule_performance(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Get rule performance analytics (most triggered rules, acceptance rates, health scores)."""
    insights = get_rule_insights(db, current_user.organisation_id)
    return insights
