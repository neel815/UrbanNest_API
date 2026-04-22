from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "UrbanNest API"
    }

@router.get("/health/detailed")
async def detailed_health():
    """Detailed health check"""
    return {
        "status": "healthy",
        "service": "UrbanNest API",
        "version": "0.1.0",
        "timestamp": __import__("datetime").datetime.utcnow().isoformat()
    }
