"""
GAIME Backend - FastAPI Application Entry Point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import game, builder

app = FastAPI(
    title="GAIME",
    description="AI-powered text adventure game engine",
    version="0.1.0",
)

# Configure CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(game.router, prefix="/api/game", tags=["game"])
app.include_router(builder.router, prefix="/api/builder", tags=["builder"])


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "ok", "name": "GAIME", "version": "0.1.0"}


@app.get("/api/worlds")
async def list_worlds():
    """List available game worlds"""
    from app.engine.world import WorldLoader
    
    loader = WorldLoader()
    worlds = loader.list_worlds()
    return {"worlds": worlds}

