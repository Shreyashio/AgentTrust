"""
API endpoints for AI Agent execution and governance tool-calling.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from schemas import AgentActRequest, AgentActResponse
from agent_service import run_agent_act

router = APIRouter(prefix="/agent", tags=["AI Agent"])

@router.post("/act", response_model=AgentActResponse)
def agent_act(payload: AgentActRequest, db: Session = Depends(get_db)):
    """
    Accepts a natural language merchant instruction (e.g., 'Create an ad for Product X with a ₹500 budget').
    The agent decides which tools to invoke (check_inventory, generate_ad, launch_campaign, adjust_budget),
    evaluates actions against governance rules, and executes or holds according to policy.
    """
    result = run_agent_act(instruction=payload.instruction, db=db)
    return AgentActResponse(**result)
