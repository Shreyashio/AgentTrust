"""
Governance and Policy Enforcement Engine for AgentTrust.
Evaluates agent actions against rules in policies.json and logs all attempts.
"""
import json
import os
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from models import ActionLog

POLICY_FILE_PATH = os.path.join(os.path.dirname(__file__), "policies.json")

def load_policies() -> dict:
    """Loads the policy rules from policies.json."""
    if not os.path.exists(POLICY_FILE_PATH):
        return {
            "max_budget_adjustment_percent": 10.0,
            "max_campaign_launch_budget_inr": 1000.0
        }
    with open(POLICY_FILE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def check_policy(action: str, details: dict) -> dict:
    """
    Evaluates an intended action against governance policies.
    
    Returns a dictionary:
      {
        "status": "approved" | "needs_approval" | "blocked",
        "reason": str
      }
    """
    policies = load_policies()
    
    # 1. Action: adjust_ad_budget
    if action == "adjust_ad_budget":
        current_budget = float(details.get("current_budget", 0))
        new_budget = float(details.get("new_budget", 0))
        
        if current_budget <= 0:
            return {
                "status": "needs_approval",
                "reason": "Current budget is 0 or negative; manual baseline approval required."
            }
        
        # Calculate signed percentage change (positive = increase, negative = decrease)
        percent_change = ((new_budget - current_budget) / current_budget) * 100.0
        max_allowed_percent = float(policies.get("max_budget_adjustment_percent", 10.0))
        abs_change = abs(percent_change)
        direction = "increase" if percent_change >= 0 else "decrease"
        
        if abs_change <= max_allowed_percent:
            return {
                "status": "approved",
                "reason": f"Budget {direction} of {abs_change:.1f}% is within the allowed limit ({max_allowed_percent}%)."
            }
        else:
            return {
                "status": "needs_approval",
                "reason": f"Budget {direction} of {abs_change:.1f}% exceeds autonomous limit of {max_allowed_percent}%. Human approval required."
            }

    # 2. Action: launch_campaign
    elif action == "launch_campaign":
        budget = float(details.get("budget", 0))
        max_allowed_budget = float(policies.get("max_campaign_launch_budget_inr", 1000.0))
        
        if budget < max_allowed_budget:
            return {
                "status": "approved",
                "reason": f"Campaign budget INR {budget:.2f} is strictly under the autonomous limit of INR {max_allowed_budget:.2f}."
            }
        else:
            return {
                "status": "needs_approval",
                "reason": f"Campaign budget INR {budget:.2f} is at or above the INR {max_allowed_budget:.2f} limit. Human approval required."
            }

    # Default fallback for unknown actions: require human approval
    return {
        "status": "needs_approval",
        "reason": f"Unrecognized action '{action}'. Unregistered actions require human approval."
    }

def log_action_attempt(
    db: Session,
    action: str,
    details: dict,
    result: str,
    reason: str
) -> ActionLog:
    """
    Logs an action attempt and its governance evaluation result to the database.
    """
    log_entry = ActionLog(
        action=action,
        details=json.dumps(details),
        result=result,
        reason=reason,
        timestamp=datetime.now(timezone.utc)
    )
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)
    return log_entry
