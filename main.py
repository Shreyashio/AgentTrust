"""
AgentTrust - Main FastAPI Application
Entry point for the governance and execution backend.
"""
import os
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import config
from database import engine, Base, SessionLocal, get_db
from models import Product, ActionLog, Campaign, Order, WebhookLog
from routers import products, governance, agent, payments, analytics, audit
from seed import seed_database
from auth import get_current_merchant_id

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

# Enable CORS for local storefront testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(products.router)
app.include_router(governance.router)
app.include_router(agent.router)
app.include_router(payments.router)
app.include_router(analytics.router)
app.include_router(audit.router)

# Storefront direct route
STOREFRONT_PATH = os.path.join(os.path.dirname(__file__), "storefront", "index.html")

# Built React dashboard (frontend/dist). Served in production; optional locally.
FRONTEND_DIST = os.path.join(os.path.dirname(__file__), "frontend", "dist")
FRONTEND_INDEX = os.path.join(FRONTEND_DIST, "index.html")
FRONTEND_ASSETS = os.path.join(FRONTEND_DIST, "assets")

if os.path.isdir(FRONTEND_ASSETS):
    app.mount("/assets", StaticFiles(directory=FRONTEND_ASSETS), name="frontend-assets")


@app.get("/dashboard")
@app.get("/dashboard/{full_path:path}", include_in_schema=False)
def serve_dashboard_spa(full_path: str = ""):
    """Serves the built React dashboard with SPA fallback for client-side routes."""
    if os.path.exists(FRONTEND_INDEX):
        return FileResponse(FRONTEND_INDEX)
    return JSONResponse(
        status_code=404,
        content={"detail": "Frontend not built yet. Run: cd frontend && npm run build"},
    )


@app.get("/store")
@app.get("/storefront")
def serve_storefront():
    """Serves the test storefront directly from FastAPI."""
    if os.path.exists(STOREFRONT_PATH):
        return FileResponse(STOREFRONT_PATH)
    return {"error": "Storefront index.html not found"}

@app.get("/compare-orders")
def compare_orders_alias(
    db=Depends(get_db),
    merchant_id: str = Depends(get_current_merchant_id)
):
    """Direct alias for GET /analytics/compare-orders (scoped to logged-in merchant)."""
    return analytics.compare_recent_orders(db=db, merchant_id=merchant_id)

@app.get("/")
def root():
    return {"message": "hello", "service": "AgentTrust", "storefront_url": "/store"}

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "database": "sqlite",
        "razorpay_configured": bool(config.RAZORPAY_KEY_ID and config.RAZORPAY_KEY_SECRET),
        "anthropic_configured": bool(config.ANTHROPIC_API_KEY)
    }

# Quick test for auth: returns the logged-in merchant's Clerk user ID,
# or a 401 if the request has no valid token.
@app.get("/auth/me")
def auth_me(merchant_id: str = Depends(get_current_merchant_id)):
    return {"merchant_id": merchant_id}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=config.HOST, port=config.PORT, reload=config.DEBUG)
