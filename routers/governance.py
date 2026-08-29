"""
API endpoints for Governance and Policy Evaluation.
"""
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import ActionLog
from schemas import PolicyCheckRequest, PolicyCheckResponse, ActionLogResponse
from governance import check_policy, log_action_attempt, load_policies

router = APIRouter(prefix="/governance", tags=["Governance"])

@router.get("/policies")
def get_policies():
    """Retrieve current governance policies and thresholds."""
    return load_policies()

@router.post("/check", response_model=PolicyCheckResponse)
def evaluate_and_log_action(payload: PolicyCheckRequest, db: Session = Depends(get_db)):
    """
    Evaluates an action against governance policies and logs the attempt to the database.
    """
    eval_result = check_policy(payload.action, payload.details)
    
    # Log attempt to SQLite
    log_entry = log_action_attempt(
        db=db,
        action=payload.action,
        details=payload.details,
        result=eval_result["status"],
        reason=eval_result["reason"]
    )
    
    return PolicyCheckResponse(
        action=payload.action,
        result=eval_result["status"],
        reason=eval_result["reason"],
        log_id=log_entry.id,
        timestamp=log_entry.timestamp
    )

@router.get("/logs", response_model=List[ActionLogResponse])
def get_action_logs(db: Session = Depends(get_db)):
    """List all action attempts and their governance evaluation results."""
    logs = db.query(ActionLog).order_by(ActionLog.id.desc()).all()
    return logs
