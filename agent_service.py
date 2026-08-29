"""
AI Agent Service with Claude Tool-Calling & Governance Verification.
Implements tools: check_inventory, generate_ad, launch_campaign, adjust_budget.
"""
import re
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Tuple
from sqlalchemy.orm import Session
import config
from models import Product, Campaign
from governance import check_policy, log_action_attempt
from routers.products import calculate_staleness

# Anthropic Tool Definitions Schema
CLAUDE_TOOLS = [
    {
        "name": "check_inventory",
        "description": "Reads product inventory data, stock levels, pricing, and determines if data is fresh (updated <= 24h) or stale.",
        "input_schema": {
            "type": "object",
            "properties": {
                "product_identifier": {
                    "type": "string",
                    "description": "Product ID or approximate product name"
                }
            },
            "required": ["product_identifier"]
        }
    },
    {
        "name": "generate_ad",
        "description": "Generates persuasive ad copy text tailored for a specific product and campaign goal.",
        "input_schema": {
            "type": "object",
            "properties": {
                "product_name": {
                    "type": "string",
                    "description": "The exact or common name of the product"
                },
                "target_benefit": {
                    "type": "string",
                    "description": "Key feature, discount, or value proposition to highlight"
                }
            },
            "required": ["product_name"]
        }
    },
    {
        "name": "launch_campaign",
        "description": "Proposes launching a new ad campaign with a budget. Enforces policy governance and blocks execution if product inventory is stale.",
        "input_schema": {
            "type": "object",
            "properties": {
                "product_identifier": {
                    "type": "string",
                    "description": "Product ID or name the campaign is promoting"
                },
                "campaign_name": {
                    "type": "string",
                    "description": "Title/name for the advertising campaign"
                },
                "budget": {
                    "type": "number",
                    "description": "Total campaign budget in INR"
                },
                "ad_copy": {
                    "type": "string",
                    "description": "The ad copy text to be displayed"
                }
            },
            "required": ["product_identifier", "campaign_name", "budget", "ad_copy"]
        }
    },
    {
        "name": "adjust_budget",
        "description": "Proposes a budget modification for an existing campaign. Enforces percentage-based governance rules.",
        "input_schema": {
            "type": "object",
            "properties": {
                "campaign_id": {
                    "type": "integer",
                    "description": "The ID of the campaign to adjust"
                },
                "new_budget": {
                    "type": "number",
                    "description": "The new desired budget in INR"
                }
            },
            "required": ["campaign_id", "new_budget"]
        }
    }
]

def find_product(db: Session, identifier: str) -> Product:
    """Helper to locate a product by exact/partial name or integer ID."""
    identifier_str = str(identifier).strip()
    
    # Try ID lookup
    if identifier_str.isdigit():
        prod = db.query(Product).filter(Product.id == int(identifier_str)).first()
        if prod:
            return prod
            
    # Try exact/partial name lookup
    prod = db.query(Product).filter(Product.name.ilike(f"%{identifier_str}%")).first()
    return prod

def tool_check_inventory(db: Session, product_identifier: str) -> Dict[str, Any]:
    """Tool: check_inventory implementation."""
    prod = find_product(db, product_identifier)
    if not prod:
        return {
            "found": False,
            "error": f"Product matching '{product_identifier}' not found in inventory."
        }
        
    status, hours = calculate_staleness(prod.last_updated)
    return {
        "found": True,
        "product_id": prod.id,
        "name": prod.name,
        "stock_count": prod.stock_count,
        "price": prod.price,
        "margin": prod.margin,
        "staleness_status": status,
        "hours_since_update": hours,
        "is_stale": status == "stale"
    }

def tool_generate_ad(db: Session, product_name: str, target_benefit: str = "") -> Dict[str, Any]:
    """Tool: generate_ad implementation."""
    prod = find_product(db, product_name)
    name = prod.name if prod else product_name
    price_info = f"Special offer at INR {prod.price:.2f}!" if prod else "Best price guaranteed!"
    benefit_info = f" - {target_benefit}" if target_benefit else ""
    
    ad_copy = f"Upgrade your lifestyle with {name}! {price_info}{benefit_info} Limited stock available. Order today!"
    return {
        "product_name": name,
        "ad_copy": ad_copy
    }

def tool_launch_campaign(
    db: Session,
    product_identifier: str,
    campaign_name: str,
    budget: float,
    ad_copy: str
) -> Tuple[Dict[str, Any], str, str]:
    """
    Tool: launch_campaign implementation.
    Passes through inventory staleness check and governance policy engine.
    """
    prod = find_product(db, product_identifier)
    
    # Check 1: Block if product data is stale
    if prod:
        staleness_status, hours = calculate_staleness(prod.last_updated)
        if staleness_status == "stale":
            reason = f"Blocked: Product '{prod.name}' inventory is stale (last updated {hours:.1f}h ago > 24h). Refresh inventory data before launching ads."
            log_action_attempt(
                db=db,
                action="launch_campaign",
                details={"product": prod.name, "budget": budget, "campaign_name": campaign_name},
                result="blocked",
                reason=reason
            )
            return (
                {"status": "blocked", "reason": reason, "campaign_id": None},
                "blocked",
                reason
            )
            
    # Check 2: Governance policy evaluation
    eval_result = check_policy(
        action="launch_campaign",
        details={"budget": budget, "campaign_name": campaign_name, "product": prod.name if prod else product_identifier}
    )
    gov_status = eval_result["status"]  # 'approved' or 'needs_approval'
    gov_reason = eval_result["reason"]
    
    log_entry = log_action_attempt(
        db=db,
        action="launch_campaign",
        details={"product_id": prod.id if prod else None, "budget": budget, "campaign_name": campaign_name},
        result=gov_status,
        reason=gov_reason
    )
    
    # Execute according to governance result
    campaign_status = "active" if gov_status == "approved" else "pending_approval"
    
    new_campaign = Campaign(
        name=campaign_name,
        product_id=prod.id if prod else None,
        budget=budget,
        ad_spend=budget,
        ad_copy=ad_copy,
        status=campaign_status,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    db.add(new_campaign)
    db.commit()
    db.refresh(new_campaign)
    
    return (
        {
            "campaign_id": new_campaign.id,
            "campaign_name": new_campaign.name,
            "budget": new_campaign.budget,
            "status": new_campaign.status,
            "governance_result": gov_status,
            "governance_reason": gov_reason,
            "log_id": log_entry.id
        },
        gov_status,
        gov_reason
    )

def tool_adjust_budget(db: Session, campaign_id: int, new_budget: float) -> Tuple[Dict[str, Any], str, str]:
    """
    Tool: adjust_budget implementation.
    Passes through governance policy engine.
    """
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        reason = f"Campaign with ID {campaign_id} not found."
        return ({"error": reason}, "blocked", reason)
        
    eval_result = check_policy(
        action="adjust_ad_budget",
        details={"current_budget": campaign.budget, "new_budget": new_budget, "campaign_id": campaign_id}
    )
    gov_status = eval_result["status"]
    gov_reason = eval_result["reason"]
    
    log_entry = log_action_attempt(
        db=db,
        action="adjust_ad_budget",
        details={"campaign_id": campaign_id, "current_budget": campaign.budget, "new_budget": new_budget},
        result=gov_status,
        reason=gov_reason
    )
    
    if gov_status == "approved":
        campaign.budget = new_budget
        campaign.status = "active"
        campaign.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(campaign)
    else:
        campaign.status = "pending_approval"
        campaign.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(campaign)
        
    return (
        {
            "campaign_id": campaign.id,
            "campaign_name": campaign.name,
            "updated_budget": campaign.budget,
            "status": campaign.status,
            "governance_result": gov_status,
            "governance_reason": gov_reason,
            "log_id": log_entry.id
        },
        gov_status,
        gov_reason
    )

def execute_tool(tool_name: str, tool_input: dict, db: Session) -> Tuple[Dict[str, Any], str, str]:
    """Routes tool execution and collects governance results."""
    if tool_name == "check_inventory":
        output = tool_check_inventory(db, tool_input.get("product_identifier", ""))
        gov_status = "blocked" if output.get("is_stale") else "approved"
        gov_reason = "Product data is stale (>24h)" if output.get("is_stale") else "Inventory data is fresh"
        return output, gov_status, gov_reason
        
    elif tool_name == "generate_ad":
        output = tool_generate_ad(db, tool_input.get("product_name", ""), tool_input.get("target_benefit", ""))
        return output, "approved", "Ad generation does not require governance check"
        
    elif tool_name == "launch_campaign":
        return tool_launch_campaign(
            db,
            tool_input.get("product_identifier", ""),
            tool_input.get("campaign_name", "Automated Campaign"),
            float(tool_input.get("budget", 0)),
            tool_input.get("ad_copy", "")
        )
        
    elif tool_name == "adjust_budget":
        return tool_adjust_budget(
            db,
            int(tool_input.get("campaign_id", 0)),
            float(tool_input.get("new_budget", 0))
        )
        
    return {"error": f"Unknown tool '{tool_name}'"}, "blocked", "Unknown tool"

def fallback_heuristic_agent(instruction: str, db: Session) -> Dict[str, Any]:
    """
    Intelligent autonomous agent fallback used when no external Anthropic API key is supplied.
    Parses natural language instructions to call the exact same tool chain and governance checks.
    """
    steps = []
    text = instruction.lower()
    
    # 1. Budget adjustment intent
    if "adjust" in text or "increase budget" in text or "decrease budget" in text:
        camp_match = re.search(r"campaign\s*(?:id|#)?\s*(\d+)", text)
        camp_id = int(camp_match.group(1)) if camp_match else 1
        
        # Look for new budget amount
        budget_match = re.search(r"(?:₹|inr|to|by)\s*(\d+(?:\.\d+)?)", text)
        new_budget = float(budget_match.group(1)) if budget_match else 1050.0
        
        input_data = {"campaign_id": camp_id, "new_budget": new_budget}
        output, gov_res, gov_reason = execute_tool("adjust_budget", input_data, db)
        steps.append({
            "tool": "adjust_budget",
            "input": input_data,
            "governance_result": gov_res,
            "governance_reason": gov_reason,
            "output": output
        })
        
        final_status = "approved_and_executed" if gov_res == "approved" else "held_for_approval"
        summary = f"Adjusted Campaign #{camp_id} budget proposal to INR {new_budget}. Result: {gov_res} ({gov_reason})."
        return {"instruction": instruction, "status": final_status, "steps": steps, "final_summary": summary}
        
    # 2. Ad creation / Campaign launch intent
    # Find matching product in DB
    all_products = db.query(Product).all()
    target_product = None
    for p in all_products:
        if p.name.lower() in text or str(p.id) in text:
            target_product = p
            break
            
    # Fallback to first product or partial match
    if not target_product:
        for p in all_products:
            first_word = p.name.lower().split()[0]
            if first_word in text:
                target_product = p
                break
    if not target_product and all_products:
        target_product = all_products[0]
        
    # Extract budget from instruction (e.g., '₹500 budget', 'budget of 2500', '2500 INR', '500 budget')
    budget = 500.0
    budget_patterns = [
        r"(?:₹|inr|rs\.?)\s*(\d+(?:\.\d+)?)",
        r"(\d+(?:\.\d+)?)\s*(?:₹|inr|rs\.?)",
        r"budget\s*(?:of|is|:)?\s*(?:₹|inr|rs\.?)?\s*(\d+(?:\.\d+)?)",
        r"(\d+(?:\.\d+)?)\s*budget"
    ]
    for pattern in budget_patterns:
        m = re.search(pattern, text)
        if m:
            budget = float(m.group(1))
            break
    
    # Step 1: check_inventory
    inv_input = {"product_identifier": target_product.name}
    inv_output, inv_gov_res, inv_gov_reason = execute_tool("check_inventory", inv_input, db)
    steps.append({
        "tool": "check_inventory",
        "input": inv_input,
        "governance_result": inv_gov_res,
        "governance_reason": inv_gov_reason,
        "output": inv_output
    })
    
    if inv_output.get("is_stale"):
        summary = f"Action blocked: Product '{target_product.name}' has stale inventory data ({inv_output.get('hours_since_update')} hours old). Please refresh inventory before launching ads."
        return {
            "instruction": instruction,
            "status": "blocked_due_to_stale_data",
            "steps": steps,
            "final_summary": summary
        }
        
    # Step 2: generate_ad
    ad_input = {"product_name": target_product.name, "target_benefit": "Premium quality & best pricing"}
    ad_output, ad_gov_res, ad_gov_reason = execute_tool("generate_ad", ad_input, db)
    steps.append({
        "tool": "generate_ad",
        "input": ad_input,
        "governance_result": ad_gov_res,
        "governance_reason": ad_gov_reason,
        "output": ad_output
    })
    
    # Step 3: launch_campaign
    launch_input = {
        "product_identifier": target_product.name,
        "campaign_name": f"Promo - {target_product.name}",
        "budget": budget,
        "ad_copy": ad_output.get("ad_copy", "")
    }
    launch_output, launch_gov_res, launch_gov_reason = execute_tool("launch_campaign", launch_input, db)
    steps.append({
        "tool": "launch_campaign",
        "input": launch_input,
        "governance_result": launch_gov_res,
        "governance_reason": launch_gov_reason,
        "output": launch_output
    })
    
    final_status = "approved_and_executed" if launch_gov_res == "approved" else "held_for_approval"
    summary = f"Created ad and proposed campaign for '{target_product.name}' with budget INR {budget:.2f}. Governance Status: {launch_gov_res} ({launch_gov_reason})."
    
    return {
        "instruction": instruction,
        "status": final_status,
        "steps": steps,
        "final_summary": summary
    }

def run_agent_act(instruction: str, db: Session) -> Dict[str, Any]:
    """
    Main entry point for AI Agent execution.
    Uses Anthropic Claude API if configured; otherwise uses intelligent deterministic tool executor.
    """
    if config.ANTHROPIC_API_KEY:
        try:
            import anthropic
            headers = {}
            if config.ANTHROPIC_WORKSPACE_ID:
                headers["anthropic-workspace-id"] = config.ANTHROPIC_WORKSPACE_ID
                
            client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY, default_headers=headers if headers else None)
            
            system_prompt = (
                "You are an AI e-commerce ad and sales manager. "
                "You have access to tools: check_inventory, generate_ad, launch_campaign, and adjust_budget. "
                "Always check product inventory first before generating ads or launching campaigns. "
                "Respect governance rules strictly."
            )
            
            messages = [{"role": "user", "content": instruction}]
            steps = []
            
            # Initial LLM call
            response = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1024,
                system=system_prompt,
                messages=messages,
                tools=CLAUDE_TOOLS
            )
            
            # Tool calling loop
            while response.stop_reason == "tool_use":
                tool_results_for_claude = []
                for content_block in response.content:
                    if content_block.type == "tool_use":
                        t_name = content_block.name
                        t_input = content_block.input
                        t_id = content_block.id
                        
                        out, g_res, g_reason = execute_tool(t_name, t_input, db)
                        steps.append({
                            "tool": t_name,
                            "input": t_input,
                            "governance_result": g_res,
                            "governance_reason": g_reason,
                            "output": out
                        })
                        
                        tool_results_for_claude.append({
                            "type": "tool_result",
                            "tool_use_id": t_id,
                            "content": json.dumps(out)
                        })
                
                # Append assistant message with tool calls and user message with tool results
                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": tool_results_for_claude})
                
                # Next turn with Claude
                response = client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=1024,
                    system=system_prompt,
                    messages=messages,
                    tools=CLAUDE_TOOLS
                )
            
            # Extract final text
            final_text = ""
            for block in response.content:
                if hasattr(block, "text"):
                    final_text += block.text
                    
            # Determine overall status from steps
            has_blocked = any(s["governance_result"] == "blocked" for s in steps)
            has_pending = any(s["governance_result"] == "needs_approval" for s in steps)
            
            if has_blocked:
                overall_status = "blocked_due_to_stale_data"
            elif has_pending:
                overall_status = "held_for_approval"
            else:
                overall_status = "approved_and_executed"
                
            return {
                "instruction": instruction,
                "status": overall_status,
                "steps": steps,
                "final_summary": final_text or "Agent task completed."
            }
        except Exception as e:
            # Fallback to local heuristic agent on API error
            fallback_result = fallback_heuristic_agent(instruction, db)
            fallback_result["final_summary"] += f" (Note: Claude API fallback used: {str(e)})"
            return fallback_result
    else:
        # Anthropic key not supplied -> use intelligent local agent
        return fallback_heuristic_agent(instruction, db)
