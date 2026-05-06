import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import admin, auth, health, system_admin, resident, security
from app.config import settings
from app.services.scheduler_service import mark_overdue_payments

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler(timezone="Asia/Kolkata")

app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description="UrbanNest API - Next.js + FastAPI Backend"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(health.router, prefix="/api", tags=["Health"])
app.include_router(auth.router, prefix="/api", tags=["Auth"])
app.include_router(system_admin.router, prefix="/api/system-admin", tags=["System Admin"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
app.include_router(resident.router, prefix="/api/resident", tags=["Resident"])
app.include_router(security.router, prefix="/api/security", tags=["Security"])


@app.on_event("startup")
async def start_scheduler() -> None:
    if not scheduler.running:
        scheduler.add_job(
            func=mark_overdue_payments,
            trigger=CronTrigger(hour=0, minute=0, timezone="Asia/Kolkata"),
            id="mark_overdue_payments",
            replace_existing=True,
        )
        scheduler.start()
        logger.info("Scheduler started: overdue payment job scheduled daily at midnight IST")


@app.on_event("shutdown")
async def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler stopped")

@app.get("/")
async def root():
    return {
        "message": "Welcome to UrbanNest API",
        "version": settings.API_VERSION,
        "docs": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG
    )
