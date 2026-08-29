"""
AgentTrust - Main FastAPI Application
Entry point for the governance and execution backend.
"""
from fastapi import FastAPI
import config
from database import engine, Base, SessionLocal
from models import Product, ActionLog, Campaign, Order, WebhookLog
from routers import products, governance, agent, payments, analytics, audit
from seed import seed_database

# Initialize database tables
Base.metadata.create_all(bind=engine)

# Auto-seed database if empty on startup
db = SessionLocal()
try:
    if db.query(Product).count() == 0:
        seed_database()
finally:
    db.close()

app = FastAPI(
    title=config.APP_NAME,
    description="AgentTrust: AI Agent Ad & Sales Governance System with Razorpay & ROAS Analytics",
    version="1.0.0"
)

# Include routers
app.include_router(products.router)
app.include_router(governance.router)
app.include_router(agent.router)
app.include_router(payments.router)
app.include_router(analytics.router)
app.include_router(audit.router)

# Direct aliases for convenience
@app.get("/roas")
def direct_roas(db=analytics.Depends(analytics.get_db)):
    return analytics.get_roas_report(db=db)

@app.post("/webhooks/razorpay")
async def razorpay_direct_webhook(request: payments.Request, db=payments.Depends(payments.get_db)):
    return await payments.razorpay_webhook(request=request, x_razorpay_signature=None, db=db)

@app.get("/")
def root():
    return {"message": "hello", "service": "AgentTrust"}

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "database": "sqlite",
        "razorpay_configured": bool(config.RAZORPAY_KEY_ID and config.RAZORPAY_KEY_SECRET),
        "anthropic_configured": bool(config.ANTHROPIC_API_KEY)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=config.HOST, port=config.PORT, reload=config.DEBUG)
