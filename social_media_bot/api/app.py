from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import router
import logging

logger = logging.getLogger(__name__)

def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    app = FastAPI(
        title="Social Media Bot API",
        description="API for social media content management and analytics",
        version="1.0.0"
    )
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(router)
    
    @app.on_event("startup")
    async def startup_event():
        logger.info("Starting Social Media Bot API")
    
    @app.on_event("shutdown")
    async def shutdown_event():
        logger.info("Shutting down Social Media Bot API")
    
    return app 