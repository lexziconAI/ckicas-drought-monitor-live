"""
CKCIAS Drought Monitor Backend
Main FastAPI application
"""

from fastapi import FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from dotenv import load_dotenv
import os
from datetime import datetime

# Load environment variables
load_dotenv(dotenv_path="../.env")
load_dotenv(dotenv_path="../.env.local")
load_dotenv(dotenv_path="../sidecar/.env")

# Initialize FastAPI app
app = FastAPI(
    title="CKCIAS Drought Monitor API",
    description="Real-time drought risk assessment for New Zealand",
    version="1.0.0"
)

# Configure CORS for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        # Production
        "https://ckicas-drought-monitor-live.onrender.com",
        # Local development
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "http://localhost:3003",
        "http://localhost:3005",
        "http://localhost:3010",
        "http://127.0.0.1:3010",
        "http://localhost:3006",
        "http://localhost:3007",
        "http://localhost:5500",
        "http://localhost:5501",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5500",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import API routes
from api_routes import router as api_router
app.include_router(api_router, prefix="/api")

# Import triggers router
from routes.triggers import router as triggers_router
app.include_router(triggers_router, prefix="/api")

# Import trigger engine router (for evaluation endpoint)
from services.trigger_engine import router as trigger_engine_router
app.include_router(trigger_engine_router, prefix="/api")

# Import system dynamics router
from system_dynamics import router as system_dynamics_router
app.include_router(system_dynamics_router, prefix="/api")

# Health check endpoint for Render.com monitoring
@app.get("/health")
async def health_check(response: Response):
    """
    Health check endpoint for deployment monitoring.
    Returns service status, timestamp, and database connectivity.

    Returns:
        - 200: Service is healthy
        - 503: Service is unhealthy
    """
    try:
        # Get current timestamp
        current_time = datetime.utcnow().isoformat() + "Z"

        # Database connectivity check
        # Note: Currently no database is configured for this application.
        # When a database (e.g., PostgreSQL, Supabase) is added, add connection check here.
        # For now, we'll return "not_configured" as the database is not yet set up.
        database_status = "not_configured"

        # TODO: Add database connectivity check when database is configured
        # Example for PostgreSQL:
        # try:
        #     await database.execute("SELECT 1")
        #     database_status = "connected"
        # except Exception as db_error:
        #     database_status = "disconnected"
        #     response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        #     return {
        #         "status": "unhealthy",
        #         "timestamp": current_time,
        #         "database": database_status,
        #         "error": str(db_error)
        #     }

        # Return healthy response
        response.status_code = status.HTTP_200_OK
        return {
            "status": "healthy",
            "timestamp": current_time,
            "database": database_status
        }

    except Exception as e:
        # Return unhealthy response if any error occurs
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "database": "error",
            "error": str(e)
        }

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "CKCIAS Drought Monitor Backend v1.0",
        "docs": "/docs",
        "health": "/health"
    }

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=9101,
        reload=True
    )