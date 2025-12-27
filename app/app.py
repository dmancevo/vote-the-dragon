"""Main FastAPI application for Dragonseeker game."""

import secrets
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from core.game_manager import game_manager
from middleware import RateLimitMiddleware, SecurityHeadersMiddleware
from routes import game, gameplay, lobby, websocket


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    print("🐉 Dragonseeker game server starting...")

    # Generate secret key for token signing (in memory, rotates on restart)
    app.state.secret_key = secrets.token_hex(32)
    print("🔐 Generated secret key for token signing")

    print("🔗 Game manager initialized")
    yield
    # Shutdown
    print("👋 Shutting down game server...")


# Initialize FastAPI app
app = FastAPI(
    title="Dragonseeker",
    description="A social deduction party game",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
# Note: type ignore needed due to Starlette's middleware type stub limitations
app.add_middleware(
    CORSMiddleware,  # type: ignore[arg-type]
    allow_origins=[
        "https://dragonseeker.win",
        "http://localhost:8000",  # Development
        "http://127.0.0.1:8000",  # Development
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add security headers middleware
# Note: type ignore needed due to Starlette's middleware type stub limitations
app.add_middleware(SecurityHeadersMiddleware)  # type: ignore[arg-type]

# Add rate limiting middleware
# Note: type ignore needed due to Starlette's middleware type stub limitations
app.add_middleware(RateLimitMiddleware)  # type: ignore[arg-type]

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Configure templates
templates = Jinja2Templates(directory="templates")

# Include routers
app.include_router(game.router, tags=["game"])
app.include_router(lobby.router, tags=["lobby"])
app.include_router(gameplay.router, tags=["gameplay"])
app.include_router(websocket.router, tags=["websocket"])


@app.get("/")
async def index(request: Request):
    """Landing page - create new game."""
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    # Cleanup stale/finished games
    cleaned = game_manager.cleanup_stale_games()
    if cleaned > 0:
        print(f"🧹 Cleaned up {cleaned} stale/finished games")

    stats = game_manager.get_stats()
    return {
        "status": "healthy",
        "active_games": stats["active_games"],
        "total_players": stats["total_players"],
    }
